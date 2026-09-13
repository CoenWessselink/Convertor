"""Actual Qt application control route, synthetic inputs, no mocked geometry.

Captures the existing hosted workspace widget, not a renderer mockup. The test
viewer probe records overlay calls only; these are NOT complete Viewer images.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

class RecognitionReviewUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def test_existing_source_open_analyze_review_and_evidence_save(self):
        import cadquery as cq
        from cws_convertor.ui_qt.manufacturing_geometry_workspace import ManufacturingGeometryWorkspace
        from cws_convertor.manufacturing_interpreter.report_store import save_report,load_report_envelope
        with tempfile.TemporaryDirectory(prefix='cws-recognition-ui-') as folder:
            root=Path(folder);source=root/'Body_348.step'
            # Geometry oracle: 20 x 10 rectangle, 200 area, length 100. No grade.
            cq.exporters.export(cq.Solid.makeBox(20,10,100),str(source))
            workspace=ManufacturingGeometryWorkspace(SimpleNamespace())
            workspace.resize(1700,950);workspace.show()
            try:
                workspace.source_edit.setText(str(source))
                workspace.analyze_button.click()
                deadline=time.monotonic()+90
                while workspace.current_report is None and time.monotonic()<deadline:
                    self.app.processEvents();time.sleep(.02)
                    if workspace.status_badge.text()=='FAILED':
                        self.fail(workspace.progress.format())
                report=workspace.current_report
                self.assertIsNotNone(report,'Real Analyseren control did not publish a report')
                self.assertEqual(9,workspace.tabs.count())
                self.assertGreater(workspace.section_table.rowCount(),0)
                self.assertTrue(all(s.safe for s in report.section_stations))
                self.assertAlmostEqual(200,report.section_stations[0].signature.area_mm2,places=5)
                self.assertFalse(report.material_evidence.confirmed)
                self.assertFalse(workspace.promote_button.isEnabled())
                saved=save_report(report,root/'review.json')
                reloaded=load_report_envelope(saved,source_sha256=report.source_sha256,
                    source_geometry_hash=report.source_geometry_hash,tolerance_policy_hash=report.tolerance_policy_hash,
                    profile_database_hash=report.profile_database_hash)
                self.assertEqual(report.semantic_sha256,reloaded['semantic_sha256'])
                evidence=os.environ.get('CWS_RECOGNITION_EVIDENCE_DIR')
                if evidence:
                    output=Path(evidence)/'recognition-ui';output.mkdir(parents=True,exist_ok=True)
                    files=[]
                    for table,name in ((workspace.section_table,'sections'),(workspace.catalogue_table,'catalogue'),
                                       (workspace.material_table,'material')):
                        workspace.tabs.setCurrentWidget(table);self.app.processEvents()
                        path=output/(name+'.png')
                        self.assertTrue(workspace.grab().save(str(path),'PNG'))
                        files.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
                    save_report(report,output/'report.json')
                    (output/'CAPTURE.json').write_text(json.dumps({'scope':'actual existing Qt workspace controls; synthetic STEP; no full Viewer claim',
                        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                        'scenario':'source field -> Analyseren button -> real isolated worker -> review -> save/reopen',
                        'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                        'expectation':{'area_mm2':200,'material_confirmed':False,'tabs':9},'status':'PASS','screenshots':files},indent=2),encoding='utf-8')
            finally:
                workspace.close();self.app.processEvents()

    def test_selection_binding_invalidation_is_visible_without_mutation(self):
        from cws_convertor.ui_qt.manufacturing_geometry_workspace import ManufacturingGeometryWorkspace
        from cws_convertor.project.model import Part
        workspace=ManufacturingGeometryWorkspace(SimpleNamespace())
        try:
            part=Part(internal_id='test');project=SimpleNamespace(parts={'test':part})
            workspace.project=project;workspace._selected_part_id='test'
            from cws_convertor.manufacturing_interpreter.recognition_cache import stable_sha256
            workspace._selected_part_hash=stable_sha256(part.base_to_dict())
            self.assertTrue(workspace._binding_current())
            part.revision='new'
            self.assertFalse(workspace._binding_current())
            self.assertEqual('new',part.revision)
        finally:
            workspace.close();self.app.processEvents()

if __name__=='__main__':unittest.main(verbosity=2)
