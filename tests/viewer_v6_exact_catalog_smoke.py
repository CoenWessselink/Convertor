from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.exact import load_step_exact

class ViewerV6ExactCatalogTests(unittest.TestCase):
    def _load(self,name): return load_step_exact(ROOT/'validation'/'v0.2_generated_step'/name)
    def test_p1811_stable_subshapes_and_holes(self):
        first=self._load('P1811.step'); second=self._load('P1811.step')
        self.assertEqual(first.snapshot.exact_geometry_hash,second.snapshot.exact_geometry_hash)
        self.assertEqual([x.stable_id for x in first.snapshot.subshapes],[x.stable_id for x in second.snapshot.subshapes])
        holes=[f for f in first.snapshot.features if f.feature_type=='through_hole']
        self.assertEqual(4,len(holes)); self.assertTrue(all(abs((h.diameter or 0)-18)<1e-9 for h in holes))
        self.assertEqual(10,first.snapshot.properties.face_count)
        frame=first.snapshot.production_frame
        self.assertAlmostEqual(1.0,frame.x_axis.cross(frame.y_axis).dot(frame.z_axis),places=9)
        self.assertGreaterEqual(len(first.snapshot.reference_faces),4)
    def test_round_bar_and_hea_are_exact_brep(self):
        round_bar=self._load('Pr1527.step')
        feature=[f for f in round_bar.snapshot.features if f.feature_type=='round_profile']
        self.assertEqual(1,len(feature)); self.assertAlmostEqual(20,feature[0].diameter or 0,places=6)
        self.assertAlmostEqual(120,round_bar.snapshot.properties.principal_dimensions[0],places=6)
        hea=self._load('Pr1298.step')
        self.assertTrue(hea.snapshot.properties.valid)
        self.assertGreater(hea.snapshot.properties.face_count,20)
        self.assertGreater(len(hea.snapshot.subshapes),100)

if __name__=='__main__': unittest.main(verbosity=2)
