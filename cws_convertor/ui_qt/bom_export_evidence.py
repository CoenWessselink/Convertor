"""Native shipping-panel export acceptance on explicitly synthetic, reviewed CAD.

The fixture goes through the real Workbench/rebuild/roundtrip/review pipeline.
It is not an external supplier benchmark, machine authorization or another UI.
"""
from __future__ import annotations
from copy import deepcopy
import json, math, os, time, zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from cws_convertor.project import Part, Assembly, ProjectSession, SourceIdentity

def _line(start: tuple[float, float], end: tuple[float, float]) -> dict:
    return {"kind": "line", "start": list(start), "end": list(end)}

def _rectangle(width: float, height: float) -> list[dict]:
    return [
        _line((0.0, 0.0), (width, 0.0)),
        _line((width, 0.0), (width, height)),
        _line((width, height), (0.0, height)),
        _line((0.0, height), (0.0, 0.0)),
    ]

def _released_project(
    roundtrip_dir: Path,
    *,
    part_id: str = "plate-001",
    part_position: str = "P001",
    assembly_id: str = "assembly-001",
    assembly_mark: str = "M001",
) -> ProjectSession:
    radius = 7.0
    thickness = 10.0
    metrics = {
        "scope": "exact_part",
        "fidelity": "native_brep",
        "production_geometry_exact": True,
        "solid_count": 1,
        "volume_mm3": 200.0 * 100.0 * thickness - math.pi * radius * radius * thickness,
        "area_mm2": (
            2.0 * (200.0 * 100.0 + 200.0 * thickness + 100.0 * thickness)
            - 2.0 * math.pi * radius * radius
            + 2.0 * math.pi * radius * thickness
        ),
        "bbox_mm": [200.0, 100.0, 10.0],
        "valid": True,
    }
    part = Part(
        internal_id=part_id,
        name="Losse plaat",
        part_position=part_position,
        source_identity=SourceIdentity(
            source_format="STEP",
            source_sha256="a" * 64,
            source_entity_id="#42",
            part_position=part_position,
            assembly_mark=assembly_mark,
        ),
        profile="PL10",
        material="S355JR",
        material_grade="S355JR",
        quantity_total=2,
        confidence=1.0,
        profile_confidence=1.0,
        material_confidence=1.0,
        classification_confidence=1.0,
        classification_status="confirmed",
        normalized_profile="PL10*100",
        normalized_material="S355JR",
        geometry_descriptor={
            "source_geometry_hash": "b" * 64,
            "solid_count": 1,
            "cad_metrics": metrics,
        },
        properties={"source_solid_count": 1},
        assembly_ids=[assembly_id],
        quantity_per_assembly={assembly_id: 2},
    )
    part.recompute_hashes()
    assembly = Assembly(
        internal_id=assembly_id,
        name=f"Merk {assembly_mark}",
        assembly_mark=assembly_mark,
        part_ids=[part.internal_id],
        main_part_id=part.internal_id,
    )
    session = ProjectSession.new("BOM export", created_by="tester")
    session.project.add_entity(part, user="tester")
    session.project.add_entity(assembly, user="tester")
    session.start_part_workbench(part.internal_id, user="reviewer")
    session.update_part_workbench(
        part.internal_id,
        {
            "part_form": "plate",
            "recognition": {"candidate": "PL10*100", "confidence": 1.0, "confirmed": True},
            "dimensions": {"length_mm": 200.0, "thickness_mm": 10.0},
            "reference_sides": [
                {"side_id": "v", "label": "Bovenzijde", "face_ref": "face:top", "confirmed": True}
            ],
            "contours": [
                {
                    "contour_id": "outer",
                    "role": "outer",
                    "closed": True,
                    "segments": _rectangle(200.0, 100.0),
                }
            ],
            "features": [
                {
                    "feature_id": "hole-1",
                    "kind": "hole",
                    "reference_side": "v",
                    "parameters": {
                        "x_mm": 40.0,
                        "y_mm": 40.0,
                        "diameter_mm": 14.0,
                        "through": True,
                    },
                }
            ],
        },
        user="reviewer",
        reason="Gevalideerde plaat",
    )
    session.rebuild_part_canonical(part.internal_id, user="reviewer")
    report = session.validate_part_roundtrips(part.internal_id, roundtrip_dir, user="reviewer")
    if report["status"] != "passed":
        raise AssertionError(report)
    session.review_part_workbench(part.internal_id, user="reviewer")
    session.review_part_workbench(part.internal_id, user="reviewer", release=True)
    return session

def run_bom_export_evidence(output: Path) -> dict:
    from PySide6 import QtWidgets, QtCore
    from cws_convertor.project.jobs import JobManager
    from cws_convertor.bom import build_bom_snapshot
    from cws_convertor.production_export.verify import verify_export_zip
    from .bom_workspace import BomWorkspacePanel
    from .phase3_workspaces import Phase3ExportCenterPanel
    from .pdf_ui_v3_evidence import identity, digest
    from cws_convertor.project.manufacturing_contracts import ExportGrouping, ExportScopeKind
    output = Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    report={'schema':'cws-bom-grouped-export-native-1',**identity(),'status':'FAIL','checks':[],
            'screenshots':{},'packages':[],'review_exports':[],'machine_transfer_allowed':False,
            'fixture':'Explicitly synthetic reviewed 200x100x10 plates, real canonical exports, no external machine authorization',
            'main_window_test':False}
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    first=_released_project(output/'roundtrip-A',part_id='EXPORT-A',part_position='P-A',assembly_id='ASM-A',assembly_mark='M-A')
    second=_released_project(output/'roundtrip-B',part_id='EXPORT-B',part_position='P-B',assembly_id='ASM-B',assembly_mark='M-B')
    project=first.project;project.parts.update(second.project.parts);project.assemblies.update(second.project.assemblies)
    # An unrelated unapproved part must not appear in a selected group's files.
    project.add_entity(Part(internal_id='OUTSIDE',part_position='OUTSIDE',name='Outside selection',category='make_part'))
    for index,key in enumerate(('EXPORT-A','EXPORT-B')):
        part=project.parts[key];part.properties['phase']=f'PH-{index+1}'
        project.settings.setdefault('batches',{})[f'BATCH-{index+1}']={'part_ids':[key]}
        project.settings.setdefault('machine_routing',{}).setdefault('assignments',{})[key]={'part_id':key,'assigned_machine_id':f'MACHINE-{index+1}'}
        project.settings.setdefault('manufacturing_machine_capabilities',{})[key]={f'MACHINE-{index+1}':{
            'production_ready':True,'manufacturing_hash':part.manufacturing_hash,'fixture':'explicitly synthetic machine capability'}}
    host=QtWidgets.QMainWindow();host.setWindowTitle('CWS — echte BOM/exportcomponenten · synthetische testdata')
    host.resize(1520,950);host.job_manager=JobManager(max_workers=1);host.project_page=None
    workspace=SimpleNamespace(project=project,session=first,bom_snapshot=build_bom_snapshot(project,classify_if_needed=False),scene=SimpleNamespace(nodes=[]))
    host.application_context=SimpleNamespace(workspace=workspace,selection=SimpleNamespace(entity_ids=('EXPORT-A','EXPORT-B'),primary_entity_id='EXPORT-A'),
        update_review_context=lambda **kw:None,update_export_context=lambda **kw:None)
    tabs=QtWidgets.QTabWidget();host.setCentralWidget(tabs)
    with patch.object(BomWorkspacePanel,'_restore_layout',lambda _self:None):
        bom=BomWorkspacePanel(host)
    page=Phase3ExportCenterPanel(None,project,job_manager=host.job_manager,parent=host)
    host.export_page=page;tabs.addTab(bom,'BOM');tabs.addTab(page,'Export')
    def select(ids,**kwargs):
        host.application_context.selection=SimpleNamespace(entity_ids=tuple(ids),primary_entity_id=ids[0] if ids else None)
        bom.set_context(workspace,host.application_context.selection);page.set_context(workspace,host.application_context.selection)
    host.application_context.request_selection=select;host.application_context.clear_selection=lambda **kw:select(())
    def open_page(route):
        if route!='export':return False
        tabs.setCurrentWidget(page);return True
    host.workspace_router=SimpleNamespace(open_workspace=open_page)
    def process():app.processEvents();time.sleep(.005)
    def check(name,value):
        report['checks'].append({'name':name,'status':'PASS' if value else 'FAIL'})
        if not value:raise AssertionError(name)
    def screenshot(name):
        process();check('Real Qt screenshot '+name,host.grab().save(str(output/name),'PNG'))
        report['screenshots'][name]=digest(output/name)
    messages=[]
    def message(*args,**kwargs):
        messages.append(str(args[2]) if len(args)>2 else str(args));return QtWidgets.QMessageBox.StandardButton.Ok
    try:
        host.show();select(('EXPORT-A','EXPORT-B'));process()
        with patch.dict(os.environ,{'CWS_HEADLESS_GUI_SMOKE':'1'}),patch.object(QtWidgets.QMessageBox,'information',message),patch.object(QtWidgets.QMessageBox,'warning',message):
            before=deepcopy(project.parts)
            # Real QAction prepares the real Export Center with exact part IDs.
            for name,box in page._format_checks.items():box.setChecked(name in {'STEP','DSTV','PDF'})
            bom._populate_action_matrix();action=bom._matrix_qactions['export.per_part']
            check('BOM QAction for per-part export enabled',action.isEnabled())
            action.trigger();process()
            check('BOM grouping preserved in shipping panel',page.grouping.currentData()==ExportGrouping.PER_PART)
            check('BOM explicit selection preserved',page._scope().entity_ids==('EXPORT-A','EXPORT-B'))
            page.output_dir.setText(str(output/'packages'))
            for kind in ('per_part','part_mark','assembly','assembly_mark','phase','batch','machine','combined'):
                page.grouping.setCurrentIndex(page.grouping.findData(ExportGrouping(kind)))
                for name,box in page._format_checks.items():box.setChecked(name in {'STEP','DSTV','PDF'})
                # Only the first run represents the original BOM intent; changed
                # UI options are a new explicit request, not the same BOM action.
                pre=page._preflight();check(kind+' real release preflight allowed',pre is not None and pre.allowed)
                page.generate_button.click();process()
                job_id=page.current_background_job_id
                check(kind+' submitted real job',bool(job_id))
                deadline=time.monotonic()+120
                while host.job_manager.get(job_id).status in {'queued','running'} and time.monotonic()<deadline:process()
                for _ in range(8):process()
                record=host.job_manager.get(job_id)
                check(kind+' real background export completed: '+str(record.error),record.status=='completed')
                result=record.result;path=Path(result['package_path'])
                check(kind+' real package passes re-read checksums',verify_export_zip(path)['valid'])
                with zipfile.ZipFile(path) as outer:
                    manifest=json.loads(outer.read('manifest.json'))
                check(kind+' exact disjoint IDs',manifest['selected_part_ids']==['EXPORT-A','EXPORT-B'] and
                      sorted(k for g in manifest['groups'] for k in g['part_ids'])==['EXPORT-A','EXPORT-B'])
                check(kind+' no machine permission granted',manifest['machine_transfer_allowed'] is False)
                for group in manifest['groups']:
                    child=path.parent/group['file'];check(kind+' child package verified',verify_export_zip(child)['valid'])
                    with zipfile.ZipFile(child) as archive:
                        child_manifest=json.loads(archive.read('manifest.json'))
                        check(kind+' actual artifact IDs',sorted(i['part_id'] for i in child_manifest['items'])==group['part_ids'])
                        bom_name=next(n for n in archive.namelist() if n.startswith('reports/BOM/') and n.endswith('_BOM.json'))
                        data=json.loads(archive.read(bom_name))
                        check(kind+' BOM report excludes non-selected parts',sorted(k for row in data['part_bom'] for k in row['part_ids'])==group['part_ids'])
                        check(kind+' exact canonical quantities',sum(row['quantity'] for row in data['part_bom'])==2*len(group['part_ids']))
                report['packages'].append({'grouping':kind,'file':str(path.relative_to(output)).replace('\\','/'),'sha256':digest(path),
                                           'manifest_sha256':manifest['manifest_sha256'],'groups':len(manifest['groups'])})
                if kind=='per_part':
                    for tab in page.findChildren(QtWidgets.QTabWidget):tab.setCurrentWidget(page.manifest)
                    check('BOM action completed only after generated files',bom._hub_state.data['batch_results'][-1]['status']=='passed')
                    check('BOM result uses absolute existing paths',all(Path(f).is_file() for f in bom._hub_state.data['batch_results'][-1]['outputs']))
                    screenshot('EXPORT-01-verified-per-part-packages.png')
                if kind=='machine':screenshot('EXPORT-02-verified-per-machine-packages.png')
            check('Exports do not change canonical parts',before==project.parts)
            tabs.setCurrentWidget(bom);select(('EXPORT-A',));process()
            for fmt in ('xlsx','csv','json'):
                bom._populate_action_matrix();action=bom._matrix_qactions['export.'+fmt]
                check(fmt+' actual review QAction enabled',action.isEnabled())
                with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=str(output/'review')):action.trigger()
                process();result=bom._hub_state.data['batch_results'][-1]
                check(fmt+' correct result action/status',result['action']=='export.'+fmt and result['status']=='passed')
                files=[Path(f) for f in result['outputs']];check(fmt+' absolute existing outputs',bool(files) and all(p.is_absolute() and p.is_file() for p in files))
                manifest=json.loads(next(p for p in files if p.name=='manifest.json').read_text())
                check(fmt+' only requested review format',manifest['selected_formats']==[fmt] and manifest['scope']['entity_ids']==['EXPORT-A'])
                check(fmt+' preflight retains exact external part selection',result['preflight_sha256'] and
                      bom._scope_engine.impact(bom._exact_export_rows(bom._selected_rows())).entity_ids==('EXPORT-A',))
                report['review_exports'].append({'format':fmt,'files':{
                    p.relative_to(output).as_posix():digest(p) for p in files}})
            screenshot('EXPORT-03-format-specific-review-results.png')
            # Empty explicit IDs never fall back to the still nonempty selection.
            tabs.setCurrentWidget(page);page.scope.setCurrentIndex(page.scope.findData(ExportScopeKind.SELECTED_PARTS));page.scope_values.clear()
            check('Cleared explicit scope does not export selection',page._preflight() is None)
            # A grouped BOM row highlights both IDs, but only A is selected in
            # the canonical bus. The shipping production action must keep A.
            tabs.setCurrentWidget(bom);select(('EXPORT-A',));process()
            bom._populate_action_matrix();bom._matrix_qactions['export.per_part'].trigger();process()
            check('Production action also narrows an aggregate row',page._scope().entity_ids==('EXPORT-A',))
            check('Actual grouped UI preflight covers only selected A',page._preflight().resolution.selected_part_ids==('EXPORT-A',))
            report['status']='PASS';report['messages']=messages
            (output/'BOM_EXPORT_EVIDENCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            return report
    except Exception as exc:
        import traceback
        report.update(error=repr(exc),traceback=traceback.format_exc())
        (output/'BOM_EXPORT_EVIDENCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        raise
    finally:
        host.job_manager.shutdown(wait=True);host.close();host.deleteLater();process()
        QtCore.QCoreApplication.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
