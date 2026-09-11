"""Real BOM QActions -> existing panels -> solver, without fabricated production permission.

This diagnostic composes the shipping panels in a test host. It is not a second
product or a claim of main-window/GPU parity. Source and installed EXE run the
same diagnostic; ordinary CWSMainWindow acceptance remains a separate gate.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import json
import os
import time
from types import SimpleNamespace
from unittest.mock import patch


def run_bom_action_evidence(output: Path) -> dict:
    from PySide6 import QtCore, QtGui, QtWidgets, QtTest
    from cws_convertor.bom import build_bom_snapshot
    from cws_convertor.bom.production_hub import ACTION_DEFINITIONS, BOMHubState
    from cws_convertor.project import Part, ProjectModel
    from cws_convertor.project.model import StockItem, Remnant, stable_sha256
    from cws_convertor.project.jobs import JobManager
    from cws_convertor.integration.workspace import IntegratedProjectWorkspace
    from .bom_workspace import BomWorkspacePanel
    from .v5_workspaces import PlateNestingPanel
    from .phase3_workspaces import Phase3ExportCenterPanel, ProfileNestingPanel
    from .pdf_ui_v3_evidence import identity, digest
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    report={'schema':'cws-bom-scoped-actions-1', **identity(), 'status':'FAIL', 'checks':[], 'screenshots':{},
            'fixture':'synthetic declared S355JR/S235JR 5+3 plates; actual shipping BOM/nesting/export panels',
            'main_window_test':False, 'native_gpu_proven':False, 'machine_transfer_allowed':False}
    host=QtWidgets.QMainWindow();host.setWindowTitle('CWS | BOM-acties — echte componententest, geen productievrijgave')
    host.resize(1680,1050);host.job_manager=JobManager(max_workers=1);host.project_page=None
    project=ProjectModel.new('BOM scope integration — synthetic declared data')
    for key,qty,grade,t in [('A',5,'S355JR',10),('B',3,'S235JR',20)]:
        part=Part(internal_id=key,part_position=key,name=key,profile=f'PL{t}',normalized_profile=f'PL{t}',part_type='plate',
                  category='make_part', material=grade,material_grade=grade,normalized_material=grade,material_confidence=1,
                  classification_status='confirmed',classification_confidence=1,profile_confidence=1,
                  length_mm=240,quantity_total=qty,mass_each_kg=4.0,surface_area_each_m2=.12,
                  geometry_descriptor={'bbox_mm':[240,220,t]})
        part.recompute_hashes();project.add_entity(part)
        project.add_entity(StockItem(internal_id='S'+key,material=grade,grade=grade,plate_size_mm=[1500,1000,t],available_quantity=2))
    project.add_entity(Remnant(internal_id='RA',material='S355JR',grade='S355JR',remaining_contour={
        'outer_contour':[[0,0],[1500,0],[1500,1000],[0,1000]],'thickness_mm':10}))
    checked=[]
    def readiness(key,formats):
        checked.append(key)
        return IntegratedProjectWorkspace.readiness_for_part(workspace,key,formats)
    workspace=SimpleNamespace(project=project,bom_snapshot=build_bom_snapshot(project,classify_if_needed=False),
                              session=SimpleNamespace(dirty=False),readiness_for_part=readiness)
    host.workspace=workspace
    tabs=QtWidgets.QTabWidget();host.setCentralWidget(tabs)
    with patch.object(BomWorkspacePanel,'_restore_layout',lambda _self:None):
        panel=BomWorkspacePanel(host);tabs.addTab(panel,'BOM')
    host.bom_excel_page=panel
    host.plate_nesting_page=PlateNestingPanel(host);tabs.addTab(host.plate_nesting_page,'Plaatnesting')
    host.profiles_page=ProfileNestingPanel(host);tabs.addTab(host.profiles_page,'Profielnesting')
    host.export_page=Phase3ExportCenterPanel(None,project,job_manager=host.job_manager,parent=host);tabs.addTab(host.export_page,'Export')
    selection=SimpleNamespace(entity_ids=(),primary_entity_id=None)
    updates=[];routes=[]
    def select(ids,**_kwargs):
        nonlocal selection
        selection=SimpleNamespace(entity_ids=tuple(ids),primary_entity_id=ids[0] if ids else None)
        host.application_context.selection=selection
        panel.set_context(workspace,selection)
        host.plate_nesting_page.set_context(workspace,selection)
        host.profiles_page.set_context(workspace,selection)
    host.application_context=SimpleNamespace(workspace=workspace,selection=selection,request_selection=select,
        clear_selection=lambda **kw:select(()),update_review_context=lambda **kw:None,
        update_export_context=lambda **kw:updates.append(kw))
    pages={'plate_nesting':host.plate_nesting_page,'profile_nesting':host.profiles_page,'export':host.export_page,'bom':panel}
    def open_page(route):
        routes.append(route)
        if route not in pages:return False
        tabs.setCurrentWidget(pages[route]);return True
    host.workspace_router=SimpleNamespace(open_workspace=open_page)
    host.show();select(());app.processEvents()
    warnings=[]
    def warning(*args,**_kwargs):
        warnings.append(str(args[2] if len(args)>2 else args));return QtWidgets.QMessageBox.StandardButton.Ok
    def check(name,ok):
        report['checks'].append({'name':name,'status':'PASS' if ok else 'FAIL'})
        if not ok:raise AssertionError(name + ' | recent messages: ' + repr(warnings[-4:]))
    def process(seconds=.05):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.002)
    def trigger(action,ids):
        tabs.setCurrentWidget(panel);select(ids);process()
        panel._populate_action_matrix()
        actions=[item for key,item in panel._matrix_qactions.items() if key==action]
        check('Shipping matrix contains '+action,len(actions)==1)
        check('Shipping matrix enables '+action,actions[0].isEnabled())
        actions[0].trigger();process()
    def screenshot(name):
        check('Real Qt capture '+name,host.grab().save(str(output/name),'PNG'))
        report['screenshots'][name]=digest(output/name)
    try:
        with patch.dict(os.environ,{'CWS_HEADLESS_GUI_SMOKE':'1'}),patch.object(QtWidgets.QMessageBox,'warning',warning):
            check('Fixture remains unapproved',not workspace.bom_snapshot.validation.production_ready)
            check('BOM has exact A and B identities',{key for row in panel._visible_rows for key in row.entity_ids}=={'A','B'})
            before_parts={key:stable_sha256(asdict(p)) for key,p in project.parts.items()}
            trigger('optimize.plate',('A',))
            check('Plate action opens plate, not profile nesting',routes[-1]=='plate_nesting' and tabs.currentWidget() is host.plate_nesting_page)
            page=host.plate_nesting_page
            deadline=time.monotonic()+45
            while (page._job_id or panel._hub_state.data['batch_results'][-1]['status']=='prepared') and time.monotonic()<deadline:process(.05)
            check('Existing plate solver finishes',page._job_id is None and page._plan is not None)
            check('Exactly five A instances, no B',page._plan.placed_count==5 and {p.part_id for lay in page._plan.layouts for p in lay.placements}=={'A'})
            check('Completion, not navigation, records passed',panel._hub_state.data['batch_results'][-1]['status']=='passed')
            check('Prepared precedes completed result',[r['status'] for r in panel._hub_state.data['batch_results'][-2:]]==['prepared','passed'])
            check('Original quantity fields unchanged',before_parts=={key:stable_sha256(asdict(p)) for key,p in project.parts.items()})
            check('Planning never silently reserves stock',not project.profile_nesting_reservations)
            screenshot('BOM-01-five-selected-plate-instances.png')
            trigger('optimize.remnants_exclude',('A',))
            check('Exclude choice reaches actual plate stock',not page.include_remnants.isChecked() and 'RA' not in {page.inventory.item(i,0).text() for i in range(page.inventory.rowCount())})
            check('Choice invalidates prior plan',page._plan is None)
            check('Choice is prepared, not falsely completed',panel._hub_state.data['batch_results'][-1]['status']=='prepared')
            trigger('optimize.remnants_include',('A',))
            check('Include reaches actual remnant inventory',page.include_remnants.isChecked() and 'RA' in {page.inventory.item(i,0).text() for i in range(page.inventory.rowCount())})
            # Current capabilities are explicitly synthetic. They cannot grant production permission.
            project.settings['manufacturing_machine_capabilities']={'A':{
                'current-synthetic':{'production_ready':True,'manufacturing_hash':project.parts['A'].manufacturing_hash},
                'stale-synthetic':{'production_ready':True,'manufacturing_hash':'stale'},
                'unbound-synthetic':{'production_ready':True}}}
            assignment_before=deepcopy(project.settings.get('machine_routing',{}))
            for action in ('machine.recommend','machine.validate','machine.alternatives'):
                checked.clear();trigger(action,('A',))
                check(action+' reruns canonical gate only for A',checked==['A'])
                check(action+' result exists: '+str(warnings),hasattr(panel,'_last_machine_review'))
                review=panel._last_machine_review
                check(action+' persists exact action and scope',review['action_id']==action and review['entity_ids']==['A'])
                check(action+' does not authorize transfer',not review['machine_transfer_allowed'] and not review['production_release_allowed'])
            bindings={row['machine_id']:row['binding'] for row in review['rows'][0]['candidates']}
            check('Stale and unbound capability reports identified',bindings=={'current-synthetic':'current','stale-synthetic':'stale','unbound-synthetic':'unproven'})
            check('Advice does not change machine assignments',project.settings.get('machine_routing',{})==assignment_before)
            panel.refresh();process()
            check('Machine report visible in existing BOM detail',panel.detail_tabs.currentIndex()==2 and 'Alleen controle/advies' in panel.detail_labels['machine'].text())
            screenshot('BOM-02-machine-advice-no-authorization.png')
            project.settings['manufacturing_machine_capabilities']['A']['current-synthetic']['manufacturing_hash']='changed'
            panel.refresh();process()
            check('Changed capability evidence invalidates displayed advice','verouderd' in panel.detail_labels['machine'].text())
            for action,formats in [('export.step',('step',)),('export.ifc',('ifc',)),('export.dxf',('dxf',))]:
                trigger(action,('A',))
                check(action+' exact formats',host.export_page._formats()==formats)
                check(action+' exact IDs',host.export_page._scope().entity_ids==('A',) and updates[-1]['active_export_scope']==('A',))
                check(action+' no false success without generated output',panel._hub_state.data['batch_results'][-1]['status'] in {'prepared','blocked'})
            trigger('export.per_machine',('A',))
            check('Machine grouping without assignment fails preflight',panel._hub_state.data['batch_results'][-1]['status']=='blocked' and host.export_page.grouping.currentData()=='machine')
            check('Original grouping intent retained',updates[-1]['grouping']=='machine')
            screenshot('BOM-03-machine-group-missing-evidence-blocked.png')
            # This component host has no exact viewer geometry. Drive the real
            # directory dialog, then require a visible, clean preflight refusal.
            # Positive part/subset/assembly batches run in CWSMainWindow proof.
            host.pdf_page=SimpleNamespace(_default_sheet_settings={})
            rejected_batch=output/'drawing-without-geometry';rejected_batch.mkdir(exist_ok=True)
            with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=str(rejected_batch)):
                trigger('drawing.batch_pdf',('A',))
            check('Batch without component geometry blocks explicitly',panel._hub_state.data['batch_results'][-1]['status']=='blocked' and any('componentgeometrie' in message for message in warnings))
            check('Rejected batch publishes no files or running job',not list(rejected_batch.iterdir()) and not getattr(panel,'_drawing_batch_job',''))
            # Actual format-specific writers, invoked by the shipping BOM QActions.
            # Only dialogs are driven by the harness; file production is not mocked.
            review_root=output/'review-exports';review_root.mkdir(exist_ok=True)
            review_bindings=[]
            for action in ('export.xlsx','export.csv','export.json','export.review'):
                destination=review_root/action.replace('.','-');destination.mkdir(exist_ok=True)
                with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=str(destination)), patch.object(QtWidgets.QMessageBox,'information',warning):
                    trigger(action,('A',))
                result=panel._hub_state.data['batch_results'][-1]
                check(action+' records its own completed review action',result['action']==action and result['status']=='passed')
                paths=[Path(name) for name in result['outputs']]
                check(action+' records actual absolute output paths',bool(paths) and all(p.is_absolute() and p.is_file() for p in paths))
                manifest_path=next(p for p in paths if p.name=='REVIEW_EXPORT.json')
                manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
                check(action+' review has exact A scope and no production permission',manifest['scope']['entity_ids']==['A'] and manifest['review_only'] and not manifest['production_release_allowed'] and not manifest['machine_transfer_allowed'])
                suffixes={Path(name).suffix for name in manifest['files'] if name not in {'manifest.json','validation.json','SHA256SUMS.txt'}}
                expected={'.xlsx'} if action=='export.xlsx' else {'.csv'} if action=='export.csv' else {'.json'} if action=='export.json' else {'.xlsx','.csv','.json','.pdf','.zip'}
                check(action+' produces only requested representations',suffixes==expected)
                check(action+' output hashes independently match',all(digest(manifest_path.parent/name)==item['sha256'] for name,item in manifest['files'].items()))
                if action in {'export.json','export.review'}:
                    data_path=next(manifest_path.parent/name for name in manifest['files'] if name.endswith('_BOM.json'))
                    data=json.loads(data_path.read_text(encoding='utf-8'))
                    check(action+' preserves five A instances and excludes three B instances',sum(r['quantity'] for r in data['part_bom'])==5 and {key for r in data['part_bom'] for key in r['part_ids']}=={'A'})
                if action=='export.csv':
                    import csv
                    with (manifest_path.parent/'part_bom.csv').open(encoding='utf-8-sig',newline='') as stream:
                        rows=list(csv.DictReader(stream))
                    check('CSV re-read preserves five A instances',len(rows)==1 and rows[0]['quantity']=='5' and rows[0]['part_ids']=='A')
                if action=='export.json': json_result=panel._last_review_export_result
                review_bindings.append({'action_id':action,'manifest':manifest_path.relative_to(output).as_posix(),'manifest_sha256':digest(manifest_path)})
            report['review_exports']=review_bindings
            panel.detail_tabs.setCurrentIndex(7); panel.refresh(); process()
            screenshot('BOM-04-review-export-exact-action-and-paths.png')
            captured=[]
            def close_review_result():
                dialog=QtWidgets.QApplication.activeModalWidget()
                if isinstance(dialog,QtWidgets.QMessageBox):
                    name='BOM-05-json-result-real-dialog.png'
                    if dialog.grab().save(str(output/name),'PNG'):
                        report['screenshots'][name]=digest(output/name)
                        captured.append(dialog.text())
                    dialog.accept()
            QtCore.QTimer.singleShot(150,close_review_result)
            panel._show_batch_result(json_result)
            check('Real review result dialog shows action status and absolute paths',bool(captured) and 'export.json' in captured[0] and 'passed' in captured[0] and str(review_root) in captured[0])
            before_files={str(p) for p in review_root.rglob('*') if p.is_file()}
            with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',return_value=''),patch.object(QtWidgets.QMessageBox,'information',warning):
                trigger('export.json',('A',))
            check('Cancelled review creates no files and is not passed',panel._hub_state.data['batch_results'][-1]['status']=='cancelled' and before_files=={str(p) for p in review_root.rglob('*') if p.is_file()})
            old_name=project.project_name
            def changed_source(*args,**kwargs):
                project.project_name='Changed during review dialog'
                return str(review_root)
            with patch.object(QtWidgets.QFileDialog,'getExistingDirectory',side_effect=changed_source),patch.object(QtWidgets.QMessageBox,'information',warning):
                trigger('export.json',('A',))
            check('Changed project during review dialog creates no files',panel._hub_state.data['batch_results'][-1]['status']=='failed' and before_files=={str(p) for p in review_root.rglob('*') if p.is_file()})
            project.project_name=old_name
            select(());process()
            with patch.object(QtWidgets.QMessageBox,'information',warning),patch.object(QtWidgets.QFileDialog,'getExistingDirectory') as choose:
                panel._export_scope('export.json')
                check('Empty explicit review selection does not open output or widen scope',not choose.called and before_files=={str(p) for p in review_root.rglob('*') if p.is_file()})
            requests=deepcopy(panel._hub_state.data['scoped_requests'])
            reopened=ProjectModel.from_dict(json.loads(json.dumps(project.to_dict())))
            restored=BOMHubState(reopened)
            check('Scoped requests survive canonical save/reopen',restored.data['scoped_requests']==requests)
            check('Review audit survives canonical save/reopen',restored.data['batch_results']==panel._hub_state.data['batch_results'])
            check('All persisted request hashes recompute',all(r['request_sha256']==stable_sha256({k:v for k,v in r.items() if k!='request_sha256'}) for r in requests))
            report['requests']=requests;report['machine_review']=review
            report['result_statuses']=[{'action':r['action'],'status':r['status']} for r in panel._hub_state.data['batch_results']]
            report['warnings']=warnings
            from .bom_export_evidence import run_bom_export_evidence
            followup = run_bom_export_evidence(output/'exports')
            check('Real reviewed CAD exports pass all grouping modes',followup['status']=='PASS')
            check('Follow-up runs in identical source and executable',all(followup[k]==report[k] for k in ('source_commit','source_dirty','frozen','executable_sha256')))
            report['export_followup']={'report':'exports/BOM_EXPORT_EVIDENCE.json',
                'sha256':digest(output/'exports/BOM_EXPORT_EVIDENCE.json'),'checks':len(followup['checks'])}
            report['status']='PASS'
            (output/'BOM_ACTION_EVIDENCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            return report
    finally:
        host.plate_nesting_page._cancel_job()
        host.job_manager.shutdown(wait=True)
        host.close();host.deleteLater();process()
        QtCore.QCoreApplication.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
