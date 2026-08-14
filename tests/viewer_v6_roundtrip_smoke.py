from __future__ import annotations
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from cws_viewer.exact import (
    ExactPartWorkbenchService,
    ExactRoundtripValidator,
    build_exact_runtime,
    build_plate,
    p1811_definition,
)


class ViewerV6RoundtripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811')

    def test_step_nc1_ifc_and_trusted_pdf_roundtrips(self):
        with tempfile.TemporaryDirectory(prefix='viewer_v6_roundtrip_') as folder:
            results=ExactRoundtripValidator(self.runtime).run(folder)
            self.assertEqual({'STEP','NC1','IFC','TRUSTED_PDF'},set(results))
            for name,result in results.items():
                self.assertTrue(result.passed,(name,result.to_dict()))
                self.assertIsNotNone(result.comparison)
                self.assertTrue(result.output_files)

    def test_format_gates_require_each_roundtrip(self):
        source=build_exact_runtime(self.runtime.shape,part_id='P1811-source')
        service=ExactPartWorkbenchService(source,self.runtime)
        service.confirm_frame(user='tester',reason='frame checked')
        refs={item.role:item.face_id for item in source.snapshot.reference_faces}
        service.confirm_reference_face('top',refs['top'],user='tester',reason='top checked')
        service.confirm_reference_face('start',refs['start'],user='tester',reason='start checked')
        service.validate()
        self.assertFalse(service.format_gates()['STEP']['review_ready'])
        with tempfile.TemporaryDirectory(prefix='viewer_v6_gate_') as folder:
            service.run_roundtrips(folder,formats=('STEP',))
        self.assertTrue(service.format_gates()['STEP']['review_ready'])
        self.assertFalse(service.format_gates()['STEP']['allowed'])
        self.assertFalse(service.format_gates()['NC1']['review_ready'])
        self.assertFalse(service.format_gates()['PRODUCTION_PDF']['allowed'])


if __name__=='__main__': unittest.main(verbosity=2)
