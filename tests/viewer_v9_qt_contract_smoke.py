from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.ui_qt import CwsConvertorMainWindow, IntegratedProjectPage
from cws_viewer.ui_qt.qt_compat import qt_available


class ViewerV9QtContractTests(unittest.TestCase):
    def test_qt_classes_are_import_safe(self) -> None:
        self.assertTrue(CwsConvertorMainWindow)
        self.assertTrue(IntegratedProjectPage)
        self.assertIsInstance(qt_available(), bool)

    def test_main_window_source_contains_integrated_surfaces_and_no_release_bypass(self) -> None:
        text = (ROOT / "cws_convertor" / "ui_qt" / "main_window.py").read_text(encoding="utf-8")
        for token in (
            "Project / Productie",
            "Part Workbench",
            "PDF review",
            "BOM / Excel",
            "Revisies / Compare",
            "ProfessionalPropertyGridPanel",
            "VtkRealProjectWidget",
            "ExactPartWorkbenchPanel",
            "production release vanuit viewer = NEE",
            "feature_highlight_requested",
            "compare_project_revisions",
            "RevisionComparePanel",
        ):
            self.assertIn(token, text)
        self.assertNotIn("allow-unrelated-histories", text)

    def test_integrated_viewer_tools_source_contains_real_v5_runtime_actions(self) -> None:
        text = (ROOT / "cws_convertor" / "ui_qt" / "viewer_tools.py").read_text(encoding="utf-8")
        for token in (
            "add_section_plane",
            "set_clipping_box",
            "explode",
            "undo_viewer",
            "redo_viewer",
            "begin_measurement",
            "save_workspace",
            "export_pdf",
            "display/review-only",
        ):
            self.assertIn(token, text)
        self.assertNotIn("production_release_allowed = True", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
