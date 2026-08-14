from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.exact import build_exact_runtime, build_plate, build_round_bar, compare_exact_parts, load_step_exact, p1811_definition

class ViewerV6CompareTests(unittest.TestCase):
    def test_exact_p1811_rebuild_passes(self):
        source=load_step_exact(ROOT/'validation'/'v0.2_generated_step'/'P1811.step',part_id='P1811')
        canonical=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811-canonical')
        report=compare_exact_parts(source,canonical)
        self.assertEqual('pass',report.overall.value)
        self.assertLess(report.source_to_canonical_max_mm,1e-9)
        self.assertFalse(report.blocking_codes)
        self.assertEqual(5,report.matched_features)
    def test_changed_hole_is_blocked(self):
        source=load_step_exact(ROOT/'validation'/'v0.2_generated_step'/'P1811.step',part_id='P1811')
        changed=build_exact_runtime(build_plate(p1811_definition(changed_hole_diameter=20)),part_id='P1811-changed')
        report=compare_exact_parts(source,changed)
        self.assertEqual('fail',report.overall.value)
        self.assertIn('CWS-EXACT-GEOMETRY-DELTA',report.blocking_codes)
        self.assertIn('CWS-EXACT-FEATURE-MISSING',report.blocking_codes)
        self.assertGreaterEqual(report.source_to_canonical_max_mm,0.99)
    def test_round_bar_rebuild_passes(self):
        source=load_step_exact(ROOT/'validation'/'v0.2_generated_step'/'Pr1527.step',part_id='D20')
        canonical=build_exact_runtime(build_round_bar(120,20),part_id='D20-canonical')
        report=compare_exact_parts(source,canonical)
        self.assertEqual('pass',report.overall.value,report.to_dict())

if __name__=='__main__': unittest.main(verbosity=2)
