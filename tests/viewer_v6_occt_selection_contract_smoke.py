from __future__ import annotations
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.exact import OcctSubshapeSelectionBridge, SubshapeKind, load_step_exact

class ViewerV6OcctSelectionTests(unittest.TestCase):
    def test_selection_modes_and_stable_mapping(self):
        runtime=load_step_exact(ROOT/'validation'/'v0.2_generated_step'/'P1811.step')
        bridge=OcctSubshapeSelectionBridge(runtime)
        self.assertEqual(1,bridge.selection_mode(SubshapeKind.VERTEX))
        self.assertEqual(2,bridge.selection_mode(SubshapeKind.EDGE))
        self.assertEqual(4,bridge.selection_mode(SubshapeKind.FACE))
        stable_id=next(item.stable_id for item in runtime.snapshot.subshapes if item.kind==SubshapeKind.FACE)
        wrapped=bridge.shape_for_stable_id(stable_id).wrapped
        self.assertEqual(stable_id,bridge.stable_id_for_shape(wrapped))

if __name__=='__main__': unittest.main(verbosity=2)
