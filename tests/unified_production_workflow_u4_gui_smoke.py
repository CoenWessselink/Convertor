from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CWS_HEADLESS_GUI_SMOKE"] = "1"

from cws_convertor.integration import create_synthetic_integration_project
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


@unittest.skipUnless(qt_available(), "PySide6 is required for the U4 GUI smoke")
class UnifiedProductionWorkflowU4GuiTests(unittest.TestCase):
    def test_central_shell_exposes_context_bound_production_surface(self) -> None:
        QtCore, _QtGui, QtWidgets = require_qt()
        from cws_convertor.ui_qt import (
            CWSMainWindow,
            U3_CONTEXT_PROPERTY,
            U3_CONTEXT_TOKEN,
            U4_WORKFLOW_PROPERTY,
            U4_WORKFLOW_TOKEN,
        )

        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with tempfile.TemporaryDirectory(prefix="cws-u4-gui-") as folder:
            project_path = create_synthetic_integration_project(Path(folder) / "u4-gui.cwscproj")
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
            self.assertEqual(U3_CONTEXT_TOKEN, window.production_page.property(U3_CONTEXT_PROPERTY))
            self.assertEqual(U4_WORKFLOW_TOKEN, window.production_page.property(U4_WORKFLOW_PROPERTY))
            self.assertIs(window.production_page.coordinator.application_context, window.application_context)

            window.application_context.request_selection(("part-v9",), origin="u4-gui")
            window.tabs.setCurrentWidget(window.production_page)
            application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
            self.assertEqual("production", window.application_context.active_surface)

            window.production_page.selection_only.setChecked(True)
            for fmt, check in window.production_page.format_checks.items():
                check.setChecked(fmt in {"json", "review_pdf"})
            plan = window.production_page.refresh_plan()
            self.assertTrue(plan.can_execute, plan.to_dict())
            self.assertEqual(("part-v9",), plan.part_ids)
            self.assertTrue(window.production_page.export_button.isEnabled())
            self.assertIn("machine-transfer", window.production_page.findChildren(QtWidgets.QLabel)[2].text().lower())
            window.application_context.assert_consistent()

            window.close()
            application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
