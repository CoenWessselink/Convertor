from __future__ import annotations
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.ui_qt.qt_compat import qt_available
import cws_viewer.ui_qt as ui

class ViewerV7QtContractTests(unittest.TestCase):
    def test_compare_panel_is_lazy_and_import_safe(self):
        cls=ui.RevisionComparePanel
        exact_cls=ui.ExactComparePanel
        self.assertEqual('RevisionComparePanel',cls.__name__)
        self.assertEqual('ExactComparePanel',exact_cls.__name__)
        source=(ROOT/'cws_viewer'/'ui_qt'/'revision_compare.py').read_text(encoding='utf-8')
        for token in ('Revisievergelijking','correspondence_method','production_reuse_allowed','BLOKKADES','Exacte metrics','productie veilig'):
            self.assertIn(token,source)
        if not qt_available():
            with self.assertRaises(Exception): cls(None)
            with self.assertRaises(Exception): exact_cls(None)
if __name__=='__main__': unittest.main(verbosity=2)
