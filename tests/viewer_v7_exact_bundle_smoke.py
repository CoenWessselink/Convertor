from __future__ import annotations
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.exact import build_exact_runtime,build_plate,p1811_definition
from cws_viewer.revisions import CompareRelation,build_exact_compare_bundle

class ViewerV7ExactBundleTests(unittest.TestCase):
    def test_source_canonical_and_roundtrip_use_same_deterministic_metrics(self):
        source=build_exact_runtime(build_plate(p1811_definition()),part_id='source')
        target=build_exact_runtime(build_plate(p1811_definition()),part_id='target')
        a=build_exact_compare_bundle(source,target,relation=CompareRelation.SOURCE_CANONICAL)
        b=build_exact_compare_bundle(source,target,relation=CompareRelation.ROUNDTRIP)
        self.assertTrue(a.production_safe,a.to_dict())
        self.assertTrue(b.production_safe,b.to_dict())
        self.assertEqual(a.exact_report.to_dict(),b.exact_report.to_dict())
        self.assertEqual(a.deviation.to_dict(),b.deviation.to_dict())
        self.assertNotEqual(a.bundle_sha256,b.bundle_sha256)
if __name__=='__main__': unittest.main(verbosity=2)
