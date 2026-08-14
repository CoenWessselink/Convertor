from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.exact import build_exact_runtime, build_plate, p1811_definition
from cws_viewer.revisions import build_correspondence, CorrespondenceStatus
from cws_viewer.revisions.correspondence import _hungarian_minimize

class ViewerV7CorrespondenceTests(unittest.TestCase):
    def test_signature_and_geometry_survive_id_reordering(self):
        source=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811-A').snapshot
        id_map={item.stable_id:f'revision-b-{index:04d}' for index,item in enumerate(reversed(source.subshapes))}
        target_subshapes=tuple(replace(item,stable_id=id_map[item.stable_id],parent_ids=tuple(id_map.get(p,p) for p in item.parent_ids)) for item in reversed(source.subshapes))
        target_features=tuple(replace(item,feature_id=f'rev-b-{index:03d}',subshape_ids=tuple(id_map.get(s,s) for s in item.subshape_ids)) for index,item in enumerate(reversed(source.features)))
        target=replace(source,part_id='P1811-B',subshapes=target_subshapes,features=target_features)
        report=build_correspondence(source,target)
        self.assertEqual(0,report.ambiguous_count,report.to_dict())
        self.assertEqual(0,report.unmatched_count,report.to_dict())
        self.assertTrue(report.production_safe)
        self.assertGreater(report.matched_count,20)
    def test_global_assignment_avoids_greedy_target_stealing(self):
        # Greedy would choose row 0 -> column 0 (0.05) and leave row 1 with
        # column 1 (0.50).  The global optimum is 0->1 and 1->0.
        pairs = _hungarian_minimize(((0.05, 0.06), (0.07, 0.50)))
        self.assertEqual(((0, 1), (1, 0)), pairs)

    def test_changed_hole_is_not_silently_corresponded(self):
        source=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811-A').snapshot
        target=build_exact_runtime(build_plate(p1811_definition(changed_hole_diameter=20)),part_id='P1811-B').snapshot
        report=build_correspondence(source,target)
        self.assertIn('CWS-V7-FEATURE-CORRESPONDENCE-INCOMPLETE',report.blocking_codes)
        self.assertFalse(report.production_safe)
    def test_equal_duplicate_candidates_are_ambiguous(self):
        base=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811').snapshot
        edge=next(item for item in base.subshapes if item.kind.value=='edge')
        source=replace(base,subshapes=(replace(edge,stable_id='src-a',signature_hash='sig-a'),replace(edge,stable_id='src-b',signature_hash='sig-b')))
        target=replace(base,subshapes=(replace(edge,stable_id='dst-a',signature_hash='sig-c'),replace(edge,stable_id='dst-b',signature_hash='sig-d')))
        report=build_correspondence(source,target)
        self.assertGreater(report.ambiguous_count,0,report.to_dict())
        self.assertIn('CWS-V7-CORRESPONDENCE-AMBIGUOUS',report.blocking_codes)
if __name__=='__main__': unittest.main(verbosity=2)
