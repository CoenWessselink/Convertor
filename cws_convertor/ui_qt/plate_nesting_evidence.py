"""Real Qt click-to-reservation-to-reopen proof; callable inside frozen app."""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import time


def run_plate_nesting_evidence(output: Path):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6 import QtCore, QtWidgets, QtTest
    from cws_convertor.ui_qt.v5_workspaces import PlateNestingPanel
    from cws_convertor.ui_qt.design_system.stylesheet import apply_v52_design_system
    from cws_convertor.ui_qt.ui_fonts import verify_widget_text_fonts
    from cws_convertor.project import Part, ProjectModel
    from cws_convertor.project.model import StockItem
    from cws_convertor.project.jobs import JobManager
    from cws_convertor.optimization.plate_nesting.project_service import verify_saved_plan
    from cws_convertor.optimization.plate_nesting.report import export_planning_pdf
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    apply_v52_design_system(app)
    project=ProjectModel.new('Synthetische acceptatie | 5 + 3 plaatdelen')
    for key,quantity,grade,t in [('A',5,'S355JR',10),('B',3,'S235JR',20)]:
        part=Part(internal_id=key,part_position=key,name=key,profile=f'PL{t}',normalized_profile=f'PL{t}',part_type='plate',
                  material=grade,material_grade=grade,normalized_material=grade,material_confidence=1,
                  length_mm=240,quantity_total=quantity,geometry_descriptor={'bbox_mm':[240,220,t]})
        part.recompute_hashes();project.add_entity(part)
        project.add_entity(StockItem(internal_id='stock-'+key,material=grade,grade=grade,plate_size_mm=[1500,1000,t],available_quantity=2))
    workspace=SimpleNamespace(project=project,session=SimpleNamespace(dirty=False))
    host=QtWidgets.QMainWindow();host.resize(1500,1000);host.job_manager=JobManager(max_workers=1)
    host.setWindowTitle('CWS plaatnesting | echte bediening, synthetisch project')
    panel=PlateNestingPanel(host);host.setCentralWidget(panel);panel.set_context(workspace,SimpleNamespace(entity_ids=('A',)))
    host.show();app.processEvents()
    checks=[]
    def check(name,truth):
        if not truth:raise AssertionError(name)
        checks.append({'name':name,'status':'PASS'})
    def click(button):
        QtTest.QTest.mouseClick(button,QtCore.Qt.MouseButton.LeftButton);app.processEvents()
    def solve():
        click(panel.run_button)
        deadline=time.monotonic()+30
        while panel._job_id and time.monotonic()<deadline:
            app.processEvents();time.sleep(.01)
        check('background job finished',panel._job_id is None)
    try:
        check('stock table reads actual two lots',panel.inventory.rowCount()==2)
        solve();check('whole project 5+3=8',panel._plan is not None and panel._plan.placed_count==8)
        check('two materials produce separate sheets',len(panel._plan.layouts)==2 and all(len({(p.grade,p.thickness_mm) for p in l.placements})==1 for l in panel._plan.layouts))
        check('no premature reservation',not project.profile_nesting_reservations)
        check('all sheets selectable',panel.sheet_combo.count()==2)
        panel.sheet_combo.setCurrentIndex(1);app.processEvents()
        check('second sheet actually displayed',panel.visual._plan['layouts'][0]['stock_id']=='stock-B')
        panel.sheet_combo.setCurrentIndex(0)
        click(panel.reserve_button)
        check('click reserves real stock',project.stock_items['stock-A'].reserved_quantity==1 and project.stock_items['stock-B'].reserved_quantity==1)
        check('workspace marked dirty',workspace.session.dirty)
        check('machine release not granted',panel._saved['machine_release_allowed'] is False)
        check('shared ledger used',panel._saved['reservation_id'] in project.profile_nesting_reservations)
        plan_id=panel._plan.run_id;expected_hash=panel._plan.plan_sha256
        check('visible fonts readable',verify_widget_text_fonts(host)['status']=='PASS')
        check('actual Qt screenshot saved',host.grab().save(str(output/'plate-project-eight.png'),'PNG'))
        pdf=export_planning_pdf(project,panel._saved,output/'plate-planning.pdf')
        import fitz
        with fitz.open(pdf) as document:
            check('report has two sheets plus quantities',len(document)==3)
            check('report quantity is eight','Vraag: 8' in document[0].get_text())
            pix=document[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5));pix.save(str(output/'plate-report-page1.png'))
        project_file=output/'synthetic-plate-project.json';project_file.write_text(json.dumps(project.to_dict()),encoding='utf-8')
        reopened=ProjectModel.from_dict(json.loads(project_file.read_text(encoding='utf-8')))
        workspace2=SimpleNamespace(project=reopened,session=SimpleNamespace(dirty=False))
        panel.set_context(workspace2,SimpleNamespace(entity_ids=('A',)));app.processEvents()
        check('saved plan restored in real panel',panel._plan is not None and panel._plan.plan_sha256==expected_hash)
        check('reopened plan independently valid',verify_saved_plan(reopened,reopened.settings['plate_nesting_runs'][plan_id]).plan_sha256==expected_hash)
        check('real reopen screenshot',host.grab().save(str(output/'plate-reopened.png'),'PNG'))
        click(panel.undo_button)
        check('cancel returns quantities to common stock',reopened.stock_items['stock-A'].reserved_quantity==0 and reopened.stock_items['stock-B'].reserved_quantity==0)
        check('cancel persisted audit state',reopened.settings['plate_nesting_runs'][plan_id]['status']=='cancelled')
        panel.scope_combo.setCurrentIndex(1);solve()
        check('selection only five A parts',panel._plan.placed_count==5 and {p.part_id for l in panel._plan.layouts for p in l.placements}=={'A'})
        reopened.stock_items['stock-A'].plate_size_mm=[100,100,10]
        before=len(reopened.profile_nesting_reservations);click(panel.reserve_button)
        check('stale stock cannot be reserved',len(reopened.profile_nesting_reservations)==before and panel._saved is None)
        panel.set_context(workspace2,SimpleNamespace(entity_ids=()))
        panel._scope_changed();solve()
        check('empty selection never expands scope',panel._plan is None)
        result={'schema':'cws-installed-plate-integration-1','status':'PASS','checks':checks,
                'fixture':'synthetic two-grade 5+3 plates; no machine transfer',
                'qt_platform':app.platformName(),'native_gpu_proven':False,
                'frozen':bool(getattr(sys,'frozen',False)),
                'production_release_allowed':False,'plan_sha256':expected_hash}
        if result['frozen']:
            binding=json.loads((Path(sys.executable).parent/'BUILD_SOURCE.json').read_text(encoding='utf-8'))
            result['source_commit']=binding['source_commit']
            result['executable_sha256']=sha256(Path(sys.executable).read_bytes()).hexdigest()
        else:
            result['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
        result['screenshots']={p.name:sha256(p.read_bytes()).hexdigest() for p in output.glob('*.png')}
        (output/'PLATE_INTEGRATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        return result
    finally:
        host.close();app.processEvents();host.job_manager.shutdown(wait=True)
