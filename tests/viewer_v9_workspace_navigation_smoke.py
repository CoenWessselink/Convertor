from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cws_viewer.ui_qt.qt_compat import qt_available


@unittest.skipUnless(qt_available(), "PySide6 is niet geinstalleerd")
class ViewerV9WorkspaceNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from PySide6 import QtWidgets

        cls.QtWidgets = QtWidgets
        cls.application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_twelve_target_workspaces_and_routes_are_stable(self) -> None:
        from cws_convertor.ui_qt.main_window import CWSMainWindow

        window = CWSMainWindow()
        try:
            expected = [
                "Inlezen",
                "Viewer / Project",
                "Bewerken",
                "Converteren",
                "Controleren",
                "PDF review",
                "Profielen",
                "Tekeningen",
                "Scribing",
                "Hoeveelheden / Excel",
                "Rapport",
                "Exporteren",
            ]
            self.assertEqual(expected, [window.tabs.tabText(i) for i in range(window.tabs.count())])

            routes = {
                "viewer": window.viewer_page,
                "edit": window.edit_page,
                "convert": window.converter_page,
                "validate": window.control_page,
                "pdf": window.pdf_page,
                "profiles": window.profiles_page,
                "drawings": window.drawings_page,
                "scribing": window.scribing_page,
                "quantities": window.bom_excel_page,
                "report": window.production_workflow_page,
                "export": window.export_page,
            }
            for action, expected_page in routes.items():
                window._route_action(action)
                self.assertIs(expected_page, window.tabs.currentWidget(), action)

            window._show_optimization()
            self.assertIs(window.control_page, window.tabs.currentWidget())
            self.assertIs(window.optimization_page, window.control_page.currentWidget())
            labels = [item.text() for item in window.optimization_page.findChildren(self.QtWidgets.QLabel)]
            self.assertIn("Profile Nesting / Optimalisatie 0.8.12", labels)
            self.assertNotIn("UI integration gap", labels)
        finally:
            window.close()
            self.application.processEvents()


if __name__ == "__main__":
    unittest.main(verbosity=2)
