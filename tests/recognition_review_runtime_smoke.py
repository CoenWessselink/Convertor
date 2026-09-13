"""Actual CWS application recognition controls, using labelled synthetic files.

The existing headless switch may replace the VTK viewport, never these controls
or the native import/analysis job. Screenshots prove this UI route, not a native
Windows installer, 3D rendering fidelity, or machine qualification.
"""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import cadquery as cq
from PySide6 import QtCore,QtWidgets
from cws_convertor.ui_qt.u4_shell import CWSMainWindow
from cws_convertor.project.model import ProjectModel
from cws_convertor.manufacturing_interpreter.cli import _step_inspection
from cws_convertor.manufacturing_interpreter.contracts import ManufacturingInterpretationRequest
from cws_convertor.manufacturing_interpreter.pipeline import ManufacturingGeometryInterpreter


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RecognitionRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.window=CWSMainWindow();self.window.resize(1880,1060);self.window.show()
        self.workspace=self.window.manufacturing_geometry_page
        self.assertTrue(self.window.workspace_router.open_workspace('manufacturing_geometry'))
        self.app.processEvents()
    def tearDown(self):
        self.workspace.job_manager.shutdown(wait=True,cancel_pending=True)
        self.window.close();self.app.processEvents()
    def pump_until(self,predicate,seconds=110):
        deadline=time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:
            self.app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents,50)
            time.sleep(.02)
        self.assertTrue(predicate(),self.workspace.status_badge.text()+' / '+self.workspace.progress.format())
    def analyze(self,shape,name):
        source=self.root/(name+'.step');cq.exporters.export(shape,str(source))
        self.workspace.source_edit.setText(str(source))
        self.workspace.analyze_button.click()
        self.pump_until(lambda:self.workspace.current_report is not None)
        self.assertEqual(sha(source),self.workspace.current_report.source_sha256)
        return source,self.workspace.current_report
    def capture(self,name,source,expected,outcome):
        output=Path(os.environ.get('CWS_RECOGNITION_EVIDENCE_DIR',self.root/'runtime-proof'))
        output.mkdir(parents=True,exist_ok=True)
        for _ in range(5):self.app.processEvents()
        target=output/(name+'.png')
        self.assertTrue(self.window.grab().save(str(target),'PNG'))
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        payload={'source_commit':commit,'environment':{'platform':platform.platform(),'python':sys.version},
            'utc':datetime.now(timezone.utc).isoformat(),'scenario':name,'synthetic':True,
            'input_sha256':sha(source),'expectation':expected,'outcome':outcome,
            'output_sha256':sha(target),'runtime':'CWSMainWindow production application',
            'route':('real shared MGI report bound to existing UI' if name == '05_material_conflict' else
                     'existing Analyseren button -> JobManager -> isolated native STEP import -> shared MGI'),
            'vtk_viewport_headless':os.environ.get('CWS_HEADLESS_GUI_SMOKE')=='1',
            'installer_tested':False,'machine_qualified':False}
        (output/(name+'.json')).write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')

    def test_compound_user_route_retains_bodies_and_review_gate(self):
        first=cq.Solid.makeBox(20,30,100)
        source,report=self.analyze(cq.Compound.makeCompound([first,first.translate((20,0,0))]),'compound')
        self.assertEqual(2,self.workspace.body_table.rowCount())
        self.assertEqual(1,self.workspace.interface_table.rowCount())
        self.assertEqual('TOUCHING',self.workspace.interface_table.item(0,2).text())
        self.assertFalse(self.workspace.promote_button.isEnabled())
        self.assertEqual(2,len(report.body_reports))
        self.workspace.tabs.setCurrentWidget(self.workspace.body_table)
        self.capture('01_source_bodies',source,{'source_bodies':2,'physical_parts':None},
                     {'source_bodies':report.body_inventory.body_count,'physical_parts':report.body_inventory.physical_part_count})
        self.workspace.tabs.setCurrentWidget(self.workspace.interface_table)
        self.capture('02_contact_not_weld',source,{'relation':'TOUCHING','fabrication':'UNPROVEN'},
                     {'relation':report.body_inventory.interfaces[0].relation,'fabrication':report.body_inventory.fabrication_status})

    def test_real_user_analysis_populates_measured_sections_and_features(self):
        shape=cq.Workplane('XY').box(200,60,12).faces('>Z').workplane().hole(10).val()
        source,report=self.analyze(shape,'drilled')
        self.assertGreater(self.workspace.section_table.rowCount(),0)
        self.assertTrue(all(s.safe for s in report.section_stations))
        self.assertEqual(1,sum(f.semantic_type.value=='HOLE' for f in report.features))
        self.assertEqual('UNRESOLVED',self.workspace.material_table.item(0,1).text())
        self.workspace.tabs.setCurrentWidget(self.workspace.section_table)
        self.capture('03_measured_sections',source,{'hole_count':1,'all_sections_measured':True},
                     {'hole_count':sum(f.semantic_type.value=='HOLE' for f in report.features),
                      'all_sections_measured':all(s.safe for s in report.section_stations)})
        self.assertEqual('PROVEN_BREP_EQUIVALENT', report.equivalence.status.value)
        self.workspace.tabs.setCurrentWidget(self.workspace.proof_table)
        self.capture('04_residual_reconstruction',source,{'equivalence':'PROVEN_BREP_EQUIVALENT'},
                     {'equivalence':report.equivalence.status.value})

    def test_project_switch_makes_pending_ui_result_stale(self):
        source=self.root/'stale.step';cq.exporters.export(cq.Solid.makeBox(20,30,100),str(source))
        self.workspace.source_edit.setText(str(source));self.workspace.analyze_button.click()
        self.workspace.set_context(SimpleNamespace(project=ProjectModel.new('Changed project')))
        self.pump_until(lambda:self.workspace.status_badge.text()=='STALE')
        self.assertIsNone(self.workspace.current_report)
        self.assertFalse(self.workspace.promote_button.isEnabled())
        self.assertFalse(self.workspace.save_button.isEnabled())

    def test_conflicting_grades_visible_with_both_sources(self):
        from cws_convertor.manufacturing_interpreter.contracts import MaterialEvidence, MaterialEvidenceStatus
        source=self.root/'conflict.step';cq.exporters.export(cq.Solid.makeBox(20,30,100),str(source))
        ins=_step_inspection(source)
        def material(grade):
            return MaterialEvidence(status=MaterialEvidenceStatus.SOURCE_CONFIRMED,material=grade,
                grade=grade,confidence=1,source='ifc_material_association_exact',
                source_entity_id='#22',source_path='synthetic-declared-assignment')
        ins.evidence['material_evidence']=material('S355J2')
        report=ManufacturingGeometryInterpreter(cache_root=self.root/'cache').analyze(
            ManufacturingInterpretationRequest(ins,material_evidence=material('S235JR')))
        self.assertEqual('CONFLICT',report.material_evidence.status.value)
        self.workspace.set_report(report);self.workspace.tabs.setCurrentWidget(self.workspace.material_table)
        values=' '.join(self.workspace.material_table.item(r,1).text() for r in range(self.workspace.material_table.rowCount()))
        self.assertIn('S235JR',values);self.assertIn('S355J2',values)
        self.assertFalse(self.workspace.promote_button.isEnabled())
        self.capture('05_material_conflict',source,{'material_status':'CONFLICT'},
                     {'material_status':report.material_evidence.status.value})

if __name__=='__main__':unittest.main(verbosity=2)
