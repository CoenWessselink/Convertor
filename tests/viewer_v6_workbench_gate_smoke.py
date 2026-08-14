from __future__ import annotations
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.exact import ExactPartWorkbenchService, build_exact_runtime, build_plate, load_step_exact, p1811_definition

class ViewerV6WorkbenchGateTests(unittest.TestCase):
    def _service(self,changed=None):
        source=load_step_exact(ROOT/'validation'/'v0.2_generated_step'/'P1811.step',part_id='P1811')
        canonical=build_exact_runtime(build_plate(p1811_definition(changed_hole_diameter=changed)),part_id='P1811-canonical')
        return ExactPartWorkbenchService(source,canonical,owner_manufacturing_hash="a"*64)
    def _confirm(self,service):
        service.confirm_frame(user='tester',reason='assen gecontroleerd')
        refs={item.role:item.face_id for item in service.source.snapshot.reference_faces}
        service.confirm_reference_face('top',refs['top'],user='tester',reason='bovenkant gecontroleerd')
        service.confirm_reference_face('start',refs['start'],user='tester',reason='startzijde gecontroleerd')
    def test_exact_part_can_pass_only_after_review_and_compare(self):
        service=self._service(); self.assertFalse(service.gate()['review_ready'])
        self._confirm(service); service.validate()
        self.assertTrue(service.gate()['review_ready'],service.gate())
        self.assertFalse(service.gate()['production_ready'])
        self.assertIn('CWS-EXACT-VIEWER-CANNOT-RELEASE-PRODUCTION',service.gate()['blocking_codes'])
        self.assertEqual(64,len(service.manufacturing_hash(material='S235JR',profile='PL10')))
    def test_changed_hole_remains_blocked(self):
        service=self._service(20); self._confirm(service); service.validate()
        gate=service.gate(); self.assertFalse(gate['review_ready'])
        self.assertIn('CWS-EXACT-GEOMETRY-DELTA',gate['review_blocking_codes'])

if __name__=='__main__': unittest.main(verbosity=2)
