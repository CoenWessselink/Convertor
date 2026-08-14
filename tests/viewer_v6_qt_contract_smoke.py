from __future__ import annotations
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.ui_qt.exact_part_workbench import ExactOcctWidget,ExactPartWorkbenchPanel
from cws_viewer.ui_qt.qt_compat import qt_available

class ViewerV6QtContractTests(unittest.TestCase):
    def test_classes_are_import_safe_without_qt(self):
        self.assertTrue(ExactOcctWidget); self.assertTrue(ExactPartWorkbenchPanel)
    def test_source_contains_required_functional_tabs(self):
        text=(ROOT/'cws_viewer'/'ui_qt'/'exact_part_workbench.py').read_text(encoding='utf-8')
        for token in ('Geometrie','Bewerkingen','Assen / referentiezijden','Algemeen','Herkomst / validatie','ExactOcctWidget'):
            self.assertIn(token,text)
        self.assertIn('subshape_picked',text)

if __name__=='__main__': unittest.main(verbosity=2)
