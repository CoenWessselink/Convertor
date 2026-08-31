"""Real IFC benchmark and VTK soak, callable from the packaged product."""
from __future__ import annotations
import argparse,ctypes,hashlib,json,math,sys,time
from ctypes import wintypes
from pathlib import Path

from cws_viewer.cache import MeshCache
from cws_viewer.contracts.geometry import GeometryRequest,TessellationSettings
from cws_viewer.contracts.scene import GeometryRepresentation,GeometryResource,Matrix4,MeshLod,NodeKind,ProjectScene,RenderMode,Rgba,SceneModel,SceneNode,StyleDefinition
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.geometry.worker_pool import PersistentGeometryWorkerPool
from cws_viewer.performance import GeometryPriorityScheduler,LoadingPerformancePolicy
from cws_viewer.performance.frame_metrics import FrameTimeRecorder
from cws_viewer.version import SCENE_SCHEMA_VERSION,VIEWER_API_VERSION

def _sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()

def build_requests(path,limit=96):
    import ifcopenshell
    from ifcopenshell.util.placement import get_local_placement
    from ifcopenshell.util.unit import calculate_unit_scale
    source=Path(path).resolve(strict=True);source_hash=_sha(source);model=ifcopenshell.open(str(source));result=[]
    translation_scale=float(calculate_unit_scale(model))*1000.0
    for entity in model.by_type('IfcProduct'):
        if getattr(entity,'Representation',None) is None:continue
        representations=tuple(getattr(entity.Representation,'Representations',()) or ())
        representation_types={str(getattr(value,'RepresentationType','') or '').lower() for value in representations}
        if representation_types and representation_types <= {'geometriccurveset','curve2d','curve3d'}:continue
        entity_id=str(entity.id());global_id=str(getattr(entity,'GlobalId','') or '')
        geometry_id=f'{global_id}#{entity_id}' if global_id else f'ifc-{entity_id}'
        geometry_hash=hashlib.sha256(f'{source_hash}:{entity_id}'.encode('ascii')).hexdigest()
        placement=get_local_placement(getattr(entity,'ObjectPlacement',None))
        rows=[[float(placement[row][column]) for column in range(4)] for row in range(4)]
        for axis in range(3):rows[axis][3]*=translation_scale
        transform=tuple(value for row in rows for value in row)
        result.append(GeometryRequest(geometry_id,geometry_hash,'IFC',source_hash,str(source),source_hash,entity_id,
                                      metadata=(('ifc_type',str(entity.is_a())),
                                                ('ifc_transform_mm',json.dumps(transform,separators=(',',':')))),
                                      source_path_verified=True))
        if len(result)>=max(1,int(limit)):break
    if not result:raise RuntimeError(f'Geen IFC-producten met representatie: {source}')
    return tuple(result)

def _scheduler(requests):
    ids=[value.geometry_id for value in requests];count=len(ids);scheduler=GeometryPriorityScheduler()
    scheduler.update_context(selected=ids[:1],under_cursor=ids[1:2],visible=ids[2:max(3,count//2)],
        near_camera=ids[max(3,count//2):max(4,count*2//3)],large_silhouette=ids[max(4,count*2//3):max(5,count*5//6)],
        current_assembly=ids[max(5,count*5//6):],camera_distances={value:float(index+1) for index,value in enumerate(ids)})
    return scheduler

def _load(requests,cache_root):
    policy=LoadingPerformancePolicy.detect(len(requests),source_format='IFC')
    settings=TessellationSettings(linear_deflection_mm=.35,angular_deflection_rad=.16,circle_segments=48)
    scheduler=_scheduler(requests);ordered=scheduler.order(requests);pool=PersistentGeometryWorkerPool(policy.worker_count)
    try:
        cache=MeshCache(cache_root,max_memory_items=max(128,len(requests)*2));started=time.perf_counter()
        meshes=pool.load_many(ordered,settings);cold=time.perf_counter()-started;version=pool.provider_version
        persist_started=time.perf_counter();cache_entries=[]
        for request in ordered:
            mesh=meshes.get(request.geometry_id)
            if mesh is not None:cache_entries.append((request.cache_key(settings,version),mesh,version,settings))
        cache.put_many_async(cache_entries);cache.flush();persist_s=time.perf_counter()-persist_started
        cache_async=cache.async_diagnostics();cache.close(wait=True)
        workers=pool.diagnostics()
    finally:
        pool.close(force=True)
    closed_workers=pool.diagnostics()
    workers={**workers,'closed':bool(closed_workers.get('closed',True)),
             'active_process_count_after_close':int(closed_workers.get('active_process_count',0)),
             'active_process_ids_after_close':list(closed_workers.get('active_process_ids',()))}
    disk=MeshCache(cache_root,max_memory_items=max(128,len(requests)*2));keys=[value.cache_key(settings,version) for value in ordered];started=time.perf_counter()
    warm_by_key=disk.get_many(keys,max_workers=min(12,max(1,policy.worker_count*4)))
    warm=[warm_by_key.get(key) for key in keys];warm_s=time.perf_counter()-started;started=time.perf_counter()
    same=[disk.get(value.cache_key(settings,version)) for value in ordered];same_s=time.perf_counter()-started
    same_runs=[]
    for _index in range(10):
        started=time.perf_counter();values=[disk.get(value.cache_key(settings,version)) for value in ordered]
        same_runs.append(time.perf_counter()-started)
        if sum(value is not None for value in values)!=len(ordered):raise RuntimeError('MeshCache V2 same-session miss')
    return meshes,{'request_count':len(requests),'exact_mesh_count':len(meshes),'cold_seconds':cold,'warm_seconds':warm_s,
        'same_session_seconds':same_s,'same_session_runs_seconds':same_runs,
        'warm_hit_count':sum(v is not None for v in warm),'same_session_hit_count':sum(v is not None for v in same),
        'worker_pool':workers,'scheduler':scheduler.diagnostics(),
        'cache':{'engine':'MeshCache V2','root':str(Path(cache_root).resolve()),
                 'storage_mode':str(getattr(disk,'storage_mode','mmap')),
                 'persist_seconds':persist_s,'async_persistence':cache_async},
        'tessellation':{'linear_deflection_mm':.35,'angular_deflection_rad':.16,'circle_segments':48}}

def _base(kind,ifc):
    return {'schema':kind,'generated_at_epoch':time.time(),'executable':str(Path(sys.executable).resolve()),
            'frozen':bool(getattr(sys,'frozen',False)),'ifc':str(Path(ifc).resolve())}

def benchmark(ifc,output,cache_root,limit):
    requests=build_requests(ifc,limit);_,measure=_load(requests,cache_root);workers=measure['worker_pool']
    gates={'real_ifc_exact_geometry':measure['exact_mesh_count']==len(requests),
           'persistent_process_workers':workers['active_process_count']>=max(1,int(workers.get('dispatch_worker_count',workers['worker_count']))),
           'worker_delivery_complete':workers['completed_requests']==len(requests),
           'worker_pool_clean_run':workers['failed_requests']==0 and workers['restarted_workers']==0 and workers['retry_successes']==0,
           'seven_tier_priority_scheduler':len(measure['scheduler']['bands'])==6,
           'mesh_cache_v2_warm':measure['warm_hit_count']==len(requests),
           'mesh_cache_v2_same_session':measure['same_session_hit_count']==len(requests),
           'same_session_faster_than_cold':measure['same_session_seconds']<measure['cold_seconds']}
    result={**_base('cws.real_packaged_performance.v2',ifc),'measurements':measure,'gates':gates,'status':'PASS' if all(gates.values()) else 'FAIL'}
    _write(output,result);return result

def cache_read_probe(ifc,output,cache_root,limit,iterations):
    requests=build_requests(ifc,limit);settings=TessellationSettings(linear_deflection_mm=.35,angular_deflection_rad=.16,circle_segments=48)
    pool=PersistentGeometryWorkerPool(1);version=pool.provider_version;pool.close(force=True)
    cache=MeshCache(cache_root,max_memory_items=max(128,len(requests)*2));runs=[];hits=[]
    keys=[value.cache_key(settings,version) for value in requests]
    for _index in range(max(1,int(iterations))):
        started=time.perf_counter();values=cache.get_many(keys,max_workers=min(12,max(1,len(keys))))
        runs.append(time.perf_counter()-started);hits.append(sum(key in values for key in keys))
    result={**_base('cws.real_cache_read.v2',ifc),'request_count':len(requests),'iterations':len(runs),
            'runs_seconds':runs,'hits':hits,'cache_stats':cache.stats.to_dict(),
            'status':'PASS' if hits and min(hits)==len(requests) else 'FAIL'}
    _write(output,result);return result

def _rss():
    class C(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD),('peak',ctypes.c_size_t),('working',ctypes.c_size_t),
                  ('qpp',ctypes.c_size_t),('qp',ctypes.c_size_t),('qnpp',ctypes.c_size_t),('qnp',ctypes.c_size_t),
                  ('page',ctypes.c_size_t),('peakpage',ctypes.c_size_t)]
    kernel32=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel32.GetCurrentProcess.argtypes=[];kernel32.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(C),wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
    value=C();value.cb=ctypes.sizeof(value)
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(),ctypes.byref(value),value.cb):
        raise OSError(ctypes.get_last_error(),'GetProcessMemoryInfo failed')
    if value.working<=0:
        raise RuntimeError('GetProcessMemoryInfo returned an invalid zero working set')
    return int(value.working)

def _scene(requests,meshes):
    repository=MeshRepository();nodes=[];resources=[];roots=[];identity=Matrix4.identity();placed=0
    world_min=[float('inf')]*3;world_max=[float('-inf')]*3
    for index,request in enumerate(requests):
        mesh=meshes.get(request.geometry_id)
        if mesh is None or mesh.bounds is None:continue
        encoded=dict(request.metadata).get('ifc_transform_mm')
        transform=Matrix4(tuple(float(value) for value in json.loads(encoded))) if encoded else identity
        if any(abs(left-right)>1e-9 for left,right in zip(transform.values,identity.values)):placed+=1
        world=mesh.bounds.transformed(transform)
        for axis,value in enumerate((world.minimum.x,world.minimum.y,world.minimum.z)):world_min[axis]=min(world_min[axis],value)
        for axis,value in enumerate((world.maximum.x,world.maximum.y,world.maximum.z)):world_max[axis]=max(world_max[axis],value)
        repository.put(request.geometry_id,mesh);node_id=f'n-{index}-{request.geometry_id}';roots.append(node_id)
        nodes.append(SceneNode(node_id,request.geometry_id,request.source_entity_id,None,NodeKind.PART,request.geometry_id,
                               transform,mesh.bounds,request.geometry_id,geometry_hash=mesh.mesh_hash,style_id='ifc'))
        payload_ref=f'memory://mesh/{request.geometry_id}'
        lod=MeshLod(0,mesh.mesh_hash,payload_ref,mesh.vertex_count,mesh.triangle_count,mesh.byte_length,None)
        resources.append(GeometryResource(request.geometry_id,GeometryRepresentation.MESH_LOD,mesh.mesh_hash,'mm',payload_ref,lods=(lod,),byte_length=mesh.byte_length))
    model=SceneModel('real-ifc','Real IFC performance scene',None,tuple(roots));style=StyleDefinition('ifc',Rgba(.42,.58,.72,1),RenderMode.SHADED_EDGES,1)
    scene=ProjectScene.create(project_id='real-ifc',revision_id=None,models=(model,),nodes=tuple(nodes),
                              geometry=tuple(resources),styles=(style,))
    extent=[world_max[axis]-world_min[axis] for axis in range(3)] if nodes else [0.0,0.0,0.0]
    metrics={'node_count':len(nodes),'placed_node_count':placed,
             'world_min_mm':world_min if nodes else [0.0,0.0,0.0],
             'world_max_mm':world_max if nodes else [0.0,0.0,0.0],'world_extent_mm':extent}
    return scene,repository,metrics

def aa_benchmark(ifc,output,cache_root,screenshot_dir,limit):
    requests=build_requests(ifc,limit);meshes,loader=_load(requests,cache_root);scene,repository,scene_metrics=_scene(requests,meshes)
    from cws_viewer.ui_qt.qt_compat import require_qt
    from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2
    QtCore,_QtGui,QtWidgets=require_qt();app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget=VtkRealProjectWidgetFeelV2(repository=repository);widget.setWindowTitle('CWS Viewer real AA benchmark')
    widget.resize(1440,900);widget.show();widget.load_scene(scene);widget.controller.fit_all();app.processEvents()
    captures=Path(screenshot_dir);captures.mkdir(parents=True,exist_ok=True);rows=[]
    render_window=widget.GetRenderWindow();renderer=render_window.GetRenderers().GetFirstRenderer()
    for samples,fxaa in ((0,True),(2,False),(4,False),(8,False)):
        render_window.SetMultiSamples(samples)
        if fxaa:renderer.UseFXAAOn()
        else:renderer.UseFXAAOff()
        for _warmup in range(6):widget.controller.render();app.processEvents()
        recorder=FrameTimeRecorder(max_samples=256)
        for index in range(72):
            started=time.perf_counter();widget.controller.orbit(.18 if index%2 else -.18,.04);widget.controller.render();app.processEvents()
            recorder.record((time.perf_counter()-started)*1000.0)
        metrics=recorder.to_dict();image=widget.controller.screenshot_to_file(captures/f'msaa_{samples}x_fxaa_{int(fxaa)}.png')
        rows.append({'msaa_samples':samples,'fxaa':fxaa,'metrics':metrics,'screenshot':str(image)})
    widget.close();app.processEvents();eligible=[row for row in rows if float(row['metrics'].get('frame_ms_p95',1e9))<=33.0]
    interactive=min(rows,key=lambda row:float(row['metrics'].get('frame_ms_p95',1e9)))
    idle=max(eligible,key=lambda row:int(row['msaa_samples'])) if eligible else interactive
    result={**_base('cws.real_msaa_fxaa_matrix.v1',ifc),'loader':loader,'scene':scene_metrics,'rows':rows,
            'selected_policy':{'interactive_msaa':interactive['msaa_samples'],'interactive_fxaa':interactive['fxaa'],
                               'recovery_msaa':2,'idle_msaa':idle['msaa_samples']},
            'status':'PASS' if len(rows)==4 and all(Path(row['screenshot']).is_file() for row in rows) else 'FAIL'}
    _write(output,result);return result

def _resource_snapshot(widget):
    import threading
    try:
        import psutil
        process=psutil.Process();rss=process.memory_info().rss/(1024.0*1024.0);children=process.children(recursive=True)
    except Exception:
        rss=0.0;children=[]
    child_details=[];worker_children=[]
    for child in children:
        try:
            command=' '.join(child.cmdline());name=child.name();pid=child.pid
        except Exception:
            command='';name='';pid=getattr(child,'pid',None)
        is_worker=any(marker in command.lower() for marker in ('spawn_main','multiprocessing-fork','cws_viewer.geometry.worker_pool'))
        child_details.append({'pid':pid,'name':name,'command':command,'ifc_worker':is_worker})
        if is_worker:worker_children.append(child)
    renderer=widget.GetRenderWindow().GetRenderers().GetFirstRenderer()
    actors=int(renderer.GetActors().GetNumberOfItems()) if renderer is not None else 0
    return {'rss_mb':rss,'vram_mb':None,'vram_status':'NOT_TESTED','thread_count':threading.active_count(),
            'process_count':1+len(children),'worker_process_count':len(worker_children),'child_processes':child_details,'actor_count':actors,
            'mesh_group_count':len(getattr(widget.backend,'_mesh_groups',{}))}

def soak(ifc,output,cache_root,screenshot_dir,duration,limit):
    requests=build_requests(ifc,limit);meshes,loader=_load(requests,cache_root);scene,repository,scene_metrics=_scene(requests,meshes)
    from cws_viewer.ui_qt.qt_compat import require_qt
    from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2
    from cws_viewer.contracts.enums import MeasurementKind,SelectionLevel,StandardView
    from cws_viewer.contracts.state import SectionPlane
    from cws_viewer.math3d import Vector3
    QtCore,_QtGui,QtWidgets=require_qt();app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    widget=VtkRealProjectWidgetFeelV2(repository=repository);widget.setWindowTitle(f'CWS Viewer real soak - {Path(ifc).name}')
    widget.resize(1440,900);widget.show();widget.load_scene(scene);widget.controller.fit_all();app.processEvents()
    node_ids=tuple(widget.controller.index.renderable_node_ids);primary=node_ids[0] if node_ids else '';views=tuple(StandardView)
    # Prime lazy VTK/OpenGL allocations and every transient interaction actor before
    # taking the leak/memory baseline. The measured interval then represents a
    # steady-state Viewer session rather than first-use driver allocation.
    for warmup in range(24):
        widget.controller.orbit(.25,.04);widget.controller.pan(.001,0);widget.controller.zoom(1.002)
        widget.controller.render();app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents,10)
    warm_section=widget.controller.add_section_plane(SectionPlane(Vector3(0,0,0),Vector3(1,0,0)))
    widget.controller.remove_section_plane(warm_section);widget.controller.begin_measurement(MeasurementKind.DISTANCE);widget.controller.cancel_tool()
    if primary:
        widget.controller.set_selection_level(SelectionLevel.PART);widget.controller.set_selection((primary,),mode='replace')
        widget.controller.hide((primary,));widget.controller.show((primary,));widget.controller.isolate((primary,));widget.controller.show_all()
        widget.controller.isolate((primary,),ghost_context=True);widget.controller.show_all()
    widget.controller.fit_all();widget.controller.render();app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents,25)
    screenshots=Path(screenshot_dir);screenshots.mkdir(parents=True,exist_ok=True);start_image=widget.controller.screenshot_to_file(screenshots/'real_soak_start.png')
    baseline=_resource_snapshot(widget);recorder=FrameTimeRecorder(max_samples=65536);started=time.perf_counter();actions=0
    input_samples=[];unintended_input_samples=[];transition_input_samples=[];pick_samples=[];selection_samples=[];wrong_picks=0;hidden_false_picks=0
    coverage={name:0 for name in ('orbit','pan','zoom','fit','standard_views','part_selection','assembly_selection','multiselect','hide_show','isolate','ghost','section','measure')}
    section_id=''
    while time.perf_counter()-started<float(duration):
        explicit_transition=any(actions%interval==0 for interval in (150,220,260,520,780,1040,1300,1560,1820,2080))
        frame=time.perf_counter();widget.controller.orbit(.45 if actions%120<60 else -.45,.08*math.sin(actions/12));coverage['orbit']+=1
        if actions%50==0:widget.controller.pan(.002 if (actions//50)%2==0 else -.002,0);coverage['pan']+=1
        if actions%90==0:widget.controller.zoom(1.015 if (actions//90)%2==0 else 1/1.015);coverage['zoom']+=1
        if actions%150==0:widget.controller.fit_all();coverage['fit']+=1
        if actions%220==0:widget.controller.set_standard_view(views[(actions//220)%len(views)]);coverage['standard_views']+=1
        if primary and actions%260==0:
            tick=time.perf_counter();widget.controller.set_selection_level(SelectionLevel.PART);widget.controller.set_selection((primary,),mode='replace')
            selection_samples.append((time.perf_counter()-tick)*1000.0);coverage['part_selection']+=1
        if primary and actions%520==0:widget.controller.set_selection_level(SelectionLevel.ASSEMBLY);widget.controller.set_selection((primary,),mode='replace');coverage['assembly_selection']+=1
        if len(node_ids)>1 and actions%780==0:widget.controller.set_selection(node_ids[:2],mode='replace');coverage['multiselect']+=1
        if primary and actions%1040==0:
            widget.controller.hide((primary,));widget.controller.render();app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents,10)
            hidden_bounds=widget.controller.index.world_bounds_by_node.get(primary)
            if hidden_bounds is not None:
                hidden_x,hidden_y=widget.backend.world_to_display(hidden_bounds.center);hidden_pick=widget.controller.pick_at(int(hidden_x),int(hidden_y),mode='replace')
                hidden_id=str(getattr(hidden_pick,'node_id','') or getattr(hidden_pick,'object_id','')) if hidden_pick is not None else ''
                if hidden_id==primary:hidden_false_picks+=1
            widget.controller.show((primary,));coverage['hide_show']+=1
        if primary and actions%1300==0:widget.controller.isolate((primary,));widget.controller.show_all();coverage['isolate']+=1
        if primary and actions%1560==0:widget.controller.isolate((primary,),ghost_context=True);widget.controller.show_all();coverage['ghost']+=1
        if actions%1820==0:
            if section_id:widget.controller.remove_section_plane(section_id)
            section_id=widget.controller.add_section_plane(SectionPlane(Vector3(0,0,0),Vector3(1,0,0)));coverage['section']+=1
        if actions%2080==0:widget.controller.begin_measurement(MeasurementKind.DISTANCE);widget.controller.cancel_tool();coverage['measure']+=1
        widget.controller.render();app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents,10)
        elapsed_frame=(time.perf_counter()-frame)*1000.0;recorder.record(elapsed_frame);input_samples.append(elapsed_frame)
        (transition_input_samples if explicit_transition else unintended_input_samples).append(elapsed_frame)
        if primary and actions%300==0:
            bounds=widget.controller.index.world_bounds_by_node.get(primary)
            if bounds is not None:
                x,y=widget.backend.world_to_display(bounds.center);tick=time.perf_counter();picked=widget.controller.pick_at(int(x),int(y),mode='replace')
                pick_samples.append((time.perf_counter()-tick)*1000.0)
                picked_id=str(getattr(picked,'node_id','') or getattr(picked,'object_id','')) if picked is not None else ''
                if picked_id and picked_id!=primary:wrong_picks+=1
        actions+=1;time.sleep(.02)
    elapsed=time.perf_counter()-started
    if section_id:widget.controller.remove_section_plane(section_id)
    widget.controller.cancel_tool();widget.controller.show_all();widget.controller.render();app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents,25)
    final=_resource_snapshot(widget);end_image=widget.controller.screenshot_to_file(screenshots/'real_soak_end.png')
    telemetry=getattr(widget.backend,'telemetry_snapshot',None);backend=telemetry() if callable(telemetry) else {};widget.close();app.processEvents()
    frames=recorder.to_dict();drift=(final['rss_mb']-baseline['rss_mb'])/max(baseline['rss_mb'],1);p95=float(frames.get('frame_ms_p95',0))
    percentile=lambda values,ratio: sorted(values)[min(len(values)-1,int((len(values)-1)*ratio))] if values else None
    stall100=sum(value>100.0 for value in input_samples)
    unintended_stall100=sum(value>100.0 for value in unintended_input_samples)
    transition_stall100=sum(value>100.0 for value in transition_input_samples)
    gates={'real_vtk_viewer':len(scene.nodes)>0,'duration_reached':elapsed>=float(duration),'frame_instrumentation':frames['sample_count']>0,
           'rss_measurement_valid':baseline['rss_mb']>0 and final['rss_mb']>0,
           'memory_drift_lte_10pct':baseline['rss_mb']>0 and final['rss_mb']>0 and drift<.10,
           'start_screenshot':Path(start_image).is_file(),'end_screenshot':Path(end_image).is_file(),
           'exact_geometry':loader['exact_mesh_count']==len(requests),
           'ifc_world_placements_applied':scene_metrics['placed_node_count']>0,
           'full_project_world_extent':max(scene_metrics['world_extent_mm'])>1000.0,
           'action_cycle_complete':all(value>0 for value in coverage.values()),
           'worker_leak_zero':final['worker_process_count']<=baseline['worker_process_count'],
           'thread_leak_zero':final['thread_count']<=baseline['thread_count'],
           'actor_leak_zero':final['actor_count']==baseline['actor_count'],
           'unintended_stall_over_100ms_zero':unintended_stall100==0,'wrong_instance_picks_zero':wrong_picks==0}
    result={**_base('cws.real_viewer_soak.v2',ifc),'duration_seconds':elapsed,'actions':actions,'frame_metrics':frames,
            'memory':{'baseline':baseline,'final':final,'drift_ratio':drift},'backend':backend,'action_coverage':coverage,
            'interaction_metrics':{'input_to_render_p50_ms':percentile(input_samples,.50),'input_to_render_p95_ms':percentile(input_samples,.95),
                                   'pick_p50_ms':percentile(pick_samples,.50),'pick_p95_ms':percentile(pick_samples,.95),
                                   'selection_p95_ms':percentile(selection_samples,.95),'wrong_instance_picks':wrong_picks,
                                   'hidden_object_false_picks':hidden_false_picks,'stall_33ms_count':sum(v>33 for v in input_samples),
                                   'stall_50ms_count':sum(v>50 for v in input_samples),'stall_100ms_count':stall100,
                                   'unintended_stall_100ms_count':unintended_stall100,
                                   'explicit_transition_stall_100ms_count':transition_stall100},
            'msaa_microtuning':{'interaction_samples':0 if p95>16.7 else 2,'idle_samples':8,'basis':'real_soak_p95','p95_ms':p95},
            'loader':loader,'scene':scene_metrics,'screenshots':{'start':str(start_image),'end':str(end_image)},
            'gates':gates,'status':'PASS' if all(gates.values()) else 'FAIL'}
    _write(output,result);return result

def _write(path,value):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(value,indent=2,sort_keys=True,default=str),encoding='utf-8')

def main(argv=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='mode',required=True)
    b=sub.add_parser('benchmark');s=sub.add_parser('soak');w=sub.add_parser('warm');session=sub.add_parser('session');aa=sub.add_parser('aa')
    for command in (b,s,w,session,aa):
        command.add_argument('--ifc',required=True,type=Path);command.add_argument('--output',required=True,type=Path)
        command.add_argument('--cache-dir',required=True,type=Path);command.add_argument('--limit',type=int,default=96)
    s.add_argument('--duration-seconds',type=float,default=600);s.add_argument('--screenshot-dir',required=True,type=Path)
    session.add_argument('--iterations',type=int,default=10);aa.add_argument('--screenshot-dir',required=True,type=Path);args=parser.parse_args(argv)
    if args.mode=='benchmark':result=benchmark(args.ifc,args.output,args.cache_dir,args.limit)
    elif args.mode=='soak':result=soak(args.ifc,args.output,args.cache_dir,args.screenshot_dir,args.duration_seconds,args.limit)
    elif args.mode=='warm':result=cache_read_probe(args.ifc,args.output,args.cache_dir,args.limit,1)
    elif args.mode=='session':result=cache_read_probe(args.ifc,args.output,args.cache_dir,args.limit,args.iterations)
    else:result=aa_benchmark(args.ifc,args.output,args.cache_dir,args.screenshot_dir,args.limit)
    print(json.dumps({'status':result['status'],'output':str(args.output.resolve())}));return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
