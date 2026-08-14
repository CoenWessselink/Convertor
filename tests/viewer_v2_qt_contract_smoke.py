from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.errors import ViewerError
from cws_viewer.ui_qt.qt_compat import qt_available
from cws_viewer.ui_qt.viewer_shell import ViewerMainWindow, create_viewer_window, run_viewer_shell
from cws_viewer.ui_qt.vtk_project_widget import VtkProjectWidget


class ViewerV2QtContractTests(unittest.TestCase):
    def test_qt_shell_contract_is_import_safe(self) -> None:
        self.assertTrue(callable(create_viewer_window))
        self.assertTrue(callable(run_viewer_shell))
        self.assertIsNotNone(ViewerMainWindow)
        self.assertIsNotNone(VtkProjectWidget)
        if not qt_available():
            with self.assertRaises(ViewerError):
                ViewerMainWindow()


if __name__ == "__main__":
    unittest.main(verbosity=2)
