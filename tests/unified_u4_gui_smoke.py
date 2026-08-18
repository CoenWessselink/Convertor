from __future__ import annotations

import os
import tempfile
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

from cws_convertor.integration.selftest import create_synthetic_integration_project
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


@unittest.skipUnless(qt_available(), "PySide6 unavailable")
class UnifiedU4GuiSmoke(unittest.TestCase):
    def test_u4_shell_exposes_production_workflow_and_u3_context(self) -> None:
        QtCore, _QtGui, QtWidgets = require_qt()
        from cws_convertor.ui_qt import CwsConvertorMainWindow, U4_WORKFLOW_TOKEN

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with tempfile.TemporaryDirectory(prefix="cws-u4-gui-") as directory:
            path = create_synthetic_integration_project(Path(directory) / "u4-gui.cwscproj")
            window = CwsConvertorMainWindow((path,))
            window.show()
            deadline = QtCore.QDeadlineTimer(60_000)
            while not deadline.hasExpired():
                app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
                if window.workspace is not None:
                    break
            self.assertIsNotNone(window.workspace)
            titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
            self.assertIn("Productieworkflow", titles)
            self.assertEqual(window.objectName(), "cwsConvertorUnifiedU4MainWindow")
            self.assertEqual(
                window.production_workflow_page.property("cwsUnifiedProductionWorkflow"),
                U4_WORKFLOW_TOKEN,
            )
            window.tabs.setCurrentWidget(window.production_workflow_page)
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
            self.assertEqual(window.application_context.active_surface, "production_workflow")
            window.production_workflow_page.refresh()
            self.assertIsNotNone(window.production_workflow_page._last_snapshot)
            self.assertFalse(window.production_workflow_page._last_snapshot.to_dict()["machine_transfer_allowed"])
            window.close()
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
