from __future__ import annotations
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from cws_viewer.exact import CanonicalPlateEditor, RoundHole, p1811_definition


class ViewerV6CanonicalEditorTests(unittest.TestCase):
    def test_edit_is_deterministic_audited_and_undoable(self):
        editor=CanonicalPlateEditor(p1811_definition(),part_id='P1811',material='S235JR',profile='PL10*123')
        original_hash=editor.review_geometry_fingerprint()
        editor.update_hole(0,RoundHole(31.5,35.0,20.0),user='tester',reason='test wijziging')
        changed_hash=editor.review_geometry_fingerprint()
        self.assertNotEqual(original_hash,changed_hash)
        self.assertEqual(1,len(editor.audit))
        self.assertTrue(editor.undo(user='tester'))
        self.assertEqual(original_hash,editor.review_geometry_fingerprint())
        self.assertTrue(editor.redo(user='tester'))
        self.assertEqual(changed_hash,editor.review_geometry_fingerprint())
        with self.assertRaises(RuntimeError):
            editor.manufacturing_hash()
        runtime=editor.runtime()
        holes=[item for item in runtime.snapshot.features if item.feature_type=='through_hole']
        self.assertEqual(4,len(holes))
        self.assertIn(20.0,{round(item.diameter or 0,6) for item in holes})

    def test_invalid_hole_is_rejected(self):
        editor=CanonicalPlateEditor(p1811_definition(),part_id='P1811')
        with self.assertRaises(ValueError):
            editor.add_hole(RoundHole(1.0,1.0,20.0),user='tester',reason='outside')
        with self.assertRaises(ValueError):
            editor.update_hole(0,RoundHole(31.5,35.0,-2.0),user='tester',reason='negative')


if __name__=='__main__': unittest.main(verbosity=2)
