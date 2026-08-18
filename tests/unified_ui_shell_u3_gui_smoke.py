from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CWS_HEADLESS_GUI_SMOKE"] = "1"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.integration import create_synthetic_integration_project
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


@unittest.skipUnless(qt_available(), "PySide6 is required for the U3 GUI smoke")
class UnifiedUiShellU3GuiTests(unittest.TestCase):
    def test_default_shell_uses_one_context_for_viewer_scribing_bom_and_export(self) -> None:
        QtCore, _QtGui, QtWidgets = require_qt()
        from cws_convertor.ui_qt import CWSMainWindow, U3_CONTEXT_PROPERTY, U3_CONTEXT_TOKEN
        from cws_convertor.ui_qt.unified_shell import CWSMainWindow as U3MainWindow

        # U4 is allowed to layer a production-workflow shell on top of the U3
        # central context.  What matters for this regression is that the public
        # shell still inherits that one canonical U3 application context.
        self.assertTrue(issubclass(CWSMainWindow, U3MainWindow))
        self.assertIn(CWSMainWindow.__module__.rsplit(".", 1)[-1], {"unified_shell", "u4_shell"})
        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        application.setApplicationName("CWS Convertor U3 smoke")

        with tempfile.TemporaryDirectory(prefix="cws-u3-gui-") as folder:
            project_path = create_synthetic_integration_project(Path(folder) / "u3-gui.cwscproj")
            window = CWSMainWindow()
            window.show()
            window.project_page.open_project(project_path, load_geometry=False)
            deadline = time.monotonic() + 30.0
            while time.monotonic() < deadline:
                application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
                if window.workspace is not None and window.application_context.workspace is window.workspace:
                    break
                time.sleep(0.01)
            self.assertIsNotNone(window.workspace)
            self.assertIs(window.application_context.workspace, window.workspace)
            self.assertEqual("2.25", window.context_snapshot.project_schema)
            self.assertEqual((), window.context_snapshot.integrity_blocking_codes)

            for page in (
                window.project_page,
                window.edit_page,
                window.scribing_page,
                window.bom_excel_page,
                window.export_page,
                window.converter_page,
                window.pdf_page,
            ):
                self.assertEqual(U3_CONTEXT_TOKEN, page.property(U3_CONTEXT_PROPERTY))

            window.application_context.request_selection(("part-v9",), origin="u3-gui")
            application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
            self.assertEqual("part-v9", window.workspace.interaction.selection.primary_entity_id)
            self.assertEqual("part-v9", window.edit_page._selection.primary_entity_id)
            self.assertEqual("part-v9", window.scribing_page._selection.primary_entity_id)
            self.assertEqual("part-v9", window.export_page._selection.primary_entity_id)
            self.assertIn("part-v9", window._u3_bom_context.text())
            self.assertIn("part-v9", window.context_strip.selection.text())

            for page, expected_surface in (
                (window.project_page, "viewer"),
                (window.edit_page, "workbench"),
                (window.scribing_page, "scribing"),
                (window.bom_excel_page, "bom"),
                (window.export_page, "export"),
            ):
                window.tabs.setCurrentWidget(page)
                application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
                self.assertEqual(expected_surface, window.application_context.active_surface)
                self.assertEqual("part-v9", window.context_snapshot.selection.primary_entity_id)

            # PDF feature selection must update both application context and the
            # same viewer interaction selection, not a parallel highlight state.
            window.application_context.request_selection(("assembly-v9",), origin="pre-pdf")
            window._highlight_pdf_feature("part-v9", "feature:u3-gui")
            application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
            self.assertEqual(("part-v9",), window.workspace.interaction.selection.entity_ids)
            self.assertEqual("feature:u3-gui", window.context_snapshot.selection.feature_id)
            self.assertEqual("pdf", window.context_snapshot.selection.origin)
            window.application_context.assert_consistent()

            window.close()
            application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
