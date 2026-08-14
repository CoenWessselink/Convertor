from __future__ import annotations

import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.errors import ViewerError
from cws_viewer.ui_qt.project_viewer import RealProjectViewerWindow, run_real_project_viewer
from cws_viewer.ui_qt.qt_compat import qt_available


class ViewerV4QtContractTests(unittest.TestCase):
    def test_qt_shell_is_import_safe_and_contains_v4_controls(self) -> None:
        self.assertTrue(callable(run_real_project_viewer))
        self.assertIsNotNone(RealProjectViewerWindow)
        source_path = ROOT / "cws_viewer" / "ui_qt" / "project_viewer.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        methods = {
            node.name
            for class_node in ast.walk(tree)
            if isinstance(class_node, ast.ClassDef)
            and class_node.name == "RealProjectViewerWindow"
            for node in class_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        required = {
            "_create_workspace_dock",
            "_on_color_scheme_changed",
            "_on_render_mode_changed",
            "_save_viewpoint_dialog",
            "_save_visibility_dialog",
            "_save_workspace_now",
            "_restore_workspace_if_available",
            "_save_screenshot_dialog",
            "_show_accuracy",
        }
        self.assertTrue(required.issubset(methods), sorted(required - methods))
        text = source_path.read_text(encoding="utf-8")
        for token in (
            "Viewpoints",
            "Visibility",
            "Accuracy/Debug",
            "Wireframe",
            "Orthografisch",
            "Werkruimte opslaan",
        ):
            self.assertIn(token, text)
        if not qt_available():
            with self.assertRaises(ViewerError):
                RealProjectViewerWindow(None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
