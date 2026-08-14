from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.core.explode import radial_explode
from cws_viewer.core.history import ViewerHistory
from cws_viewer.math3d import BoundingBox, Vector3

class ViewerV5HistoryExplodeTests(unittest.TestCase):
    def test_history_is_bounded_and_reversible(self):
        history=ViewerHistory[int](limit=2)
        history.record("a",0,1); history.record("b",1,2); history.record("c",2,3)
        self.assertEqual(2,history.undo()); self.assertEqual(1,history.undo())
        self.assertEqual(2,history.redo())
    def test_explode_is_display_only_offset(self):
        bounds={
            "a": BoundingBox.from_dimensions(10,10,10,origin=Vector3(0,0,0)),
            "b": BoundingBox.from_dimensions(10,10,10,origin=Vector3(100,0,0)),
        }
        result=radial_explode(bounds,25)
        self.assertAlmostEqual(25,result["a"].length(),places=9)
        self.assertAlmostEqual(25,result["b"].length(),places=9)
        self.assertLess(result["a"].x,0); self.assertGreater(result["b"].x,0)

if __name__=="__main__": unittest.main(verbosity=2)
