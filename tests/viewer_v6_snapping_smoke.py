from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.exact import anchor_from_candidate, candidates_for_subshape, line_intersection, load_step_exact
from cws_viewer.math3d import Vector3
from cws_viewer.measurements import SnapType

class ViewerV6SnappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.runtime=load_step_exact(ROOT/'validation'/'v0.2_generated_step'/'P1811.step',part_id='P1811')
    def test_circle_center_is_exact_analytical_anchor(self):
        edge=next(item for item in self.runtime.snapshot.subshapes if item.kind.value=='edge' and item.geometry_type=='CIRCLE')
        candidates=candidates_for_subshape(self.runtime,edge.stable_id,edge.axis_origin)
        center=next(item for item in candidates if item.snap_type==SnapType.CENTER)
        anchor=anchor_from_candidate(self.runtime,center)
        self.assertTrue(anchor.world_point.almost_equal(edge.axis_origin, tolerance=1e-9))
        self.assertEqual('analytical_brep',anchor.proof.value)
        self.assertAlmostEqual(9,float(anchor.analytical['radius']),places=9)
    def test_line_endpoint_midpoint_and_perpendicular(self):
        edge=next(item for item in self.runtime.snapshot.subshapes if item.kind.value=='edge' and item.geometry_type=='LINE' and item.measure>120)
        query=edge.center+Vector3(0,0,5)
        candidates=candidates_for_subshape(self.runtime,edge.stable_id,query)
        kinds={item.snap_type for item in candidates}
        self.assertTrue({SnapType.ENDPOINT,SnapType.MIDPOINT,SnapType.PERPENDICULAR}.issubset(kinds))
    def test_two_perpendicular_outer_edges_intersect(self):
        lines=[item for item in self.runtime.snapshot.subshapes if item.kind.value=='edge' and item.geometry_type=='LINE']
        point=None
        for first in lines:
            for second in lines:
                if first.stable_id>=second.stable_id: continue
                point=line_intersection(first,second)
                if point is not None: break
            if point is not None: break
        self.assertIsNotNone(point)

if __name__=='__main__': unittest.main(verbosity=2)
