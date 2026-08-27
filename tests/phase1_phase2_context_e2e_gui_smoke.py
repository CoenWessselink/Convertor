from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.integration import create_synthetic_integration_project
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


@unittest.skipUnless(qt_available(), "PySide6 is required")
class Phase1Phase2ContextE2E(unittest.TestCase):
    def test_all_workspaces_keep_one_project_viewer_and_full_state(self) -> None:
        QtCore, _QtGui, QtWidgets = require_qt()
        from cws_convertor.ui_qt import CWSMainWindow

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with tempfile.TemporaryDirectory(prefix="cws-phase12-e2e-") as folder:
            path = create_synthetic_integration_project(Path(folder) / "phase12.cwscproj")
            window = CWSMainWindow()
            window.show()
            window.project_page.open_project(path, load_geometry=False)
            deadline = time.monotonic() + 30.0
            while time.monotonic() < deadline:
                app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
                if window.workspace is not None:
                    break
            self.assertIsNotNone(window.workspace)
            workspace = window.workspace
            project = workspace.project
            viewer_host = window.viewer_host
            viewer_controller = window.project_page.viewer
            self.assertIs(window.job_manager, window.converter_page._job_manager)
            self.assertIs(window.job_manager, window.optimization_page._job_manager)
            window.application_context.request_selection(("assembly-v9",), origin="e2e")
            window.application_context.request_selection(("part-v9",), origin="e2e")
            window.application_context.update_viewer_context(
                camera_state={"position": [900.0, 700.0, 500.0]},
                camera_target=(0.0, 0.0, 0.0),
                visibility_state={"model": "ghosted", "part-v9": "visible"},
                ghosted_entities=("assembly-v9",),
                section_planes=({"id": "section-e2e", "offset": 25.0},),
            )
            baseline = window.context_snapshot.viewer_context
            sequence = (
                window.viewer_page,
                window.edit_page,
                window.viewer_page,
                window.converter_page,
                window.viewer_page,
                window.scribing_page,
                window.viewer_page,
                window.bom_excel_page,
                window.viewer_page,
                window.production_workflow_page,
                window.viewer_page,
                window.export_page,
                window.viewer_page,
            )
            for page in sequence:
                window.tabs.setCurrentWidget(page)
                app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
                self.assertIs(workspace, window.workspace)
                self.assertIs(project, window.workspace.project)
                self.assertEqual(project.project_id, window.context_snapshot.project_id)
                self.assertEqual("part-v9", window.context_snapshot.selection.primary_entity_id)
                self.assertEqual(baseline.camera_state, window.context_snapshot.viewer_context.camera_state)
                self.assertEqual(baseline.visibility_state, window.context_snapshot.viewer_context.visibility_state)
                self.assertEqual(baseline.section_planes, window.context_snapshot.viewer_context.section_planes)
                self.assertIs(viewer_host, window.viewer_host)
                self.assertIs(viewer_controller, window.project_page.viewer)
            self.assertFalse(window.context_snapshot.to_dict()["safety"]["machine_transfer_allowed"])
            window.close()
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
