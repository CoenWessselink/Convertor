from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QSlider, QStackedWidget, QToolButton

from cws_convertor.ui_qt.u4_shell import CWSMainWindow
from cws_viewer.ui_qt.vtk_real_project_widget import NavigationMode
from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2


class ViewerV15LayoutNavigationAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.window = CWSMainWindow()
        cls.window.resize(1600, 900)
        cls.window.show()
        cls._settle(12)
        configured = os.environ.get("CWS_VIEWER_ACCEPTANCE_PROJECT", "").strip()
        project = Path(configured) if configured else next(
            Path(r"C:\CONVERTOR\validation_097").glob("Powerspex*.cwscproj"),
            Path(r"C:\Users\c.wesselink\Desktop\IFC_files\Powerspex te Oldenzaal_Fase 3 _3.ifc"),
        )
        if not project.exists():
            raise unittest.SkipTest(f"Acceptance project ontbreekt: {project}")
        cls.window.open_initial_paths([project])
        deadline = time.monotonic() + 90.0
        while time.monotonic() < deadline:
            cls._settle(3)
            if cls.window.findChild(VtkRealProjectWidgetFeelV2, "cwsVtkRealProjectWidget") is not None:
                break
        else:
            raise AssertionError("Viewer V15 is niet aangemaakt binnen 90 seconden")
        cls._settle(20)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.window.close()
        cls._settle(3)

    @classmethod
    def _settle(cls, cycles: int = 8) -> None:
        for _ in range(cycles):
            cls.app.processEvents()
            time.sleep(0.01)

    def _show_route(self, route: str) -> VtkRealProjectWidgetFeelV2:
        self.assertTrue(self.window.workspace_router.open_workspace(route))
        self._settle(10)
        viewer = self.window.findChild(VtkRealProjectWidgetFeelV2, "cwsVtkRealProjectWidget")
        self.assertIsNotNone(viewer)
        return viewer

    def test_01_all_intended_routes_have_a_real_non_overflowing_viewer(self) -> None:
        routes = (
            "viewer",
            "edit",
            "converter",
            "control",
            "pdf_review",
            "drawing",
            "scribing",
            "bom",
            "profile_nesting",
            "report",
            "export",
        )
        for route in routes:
            with self.subTest(route=route):
                viewer = self._show_route(route)
                parent = viewer.parentWidget()
                self.assertTrue(viewer.isVisibleTo(self.window))
                self.assertGreaterEqual(viewer.width(), 300)
                self.assertGreaterEqual(viewer.height(), 120)
                self.assertLessEqual(viewer.width(), parent.contentsRect().width() + 2)
                self.assertLessEqual(viewer.height(), parent.contentsRect().height() + 2)
                self.assertFalse(any(w.isVisibleTo(self.window) for w in self.window.findChildren(QFrame, "module3dViewerPreview")))

    def test_02_navigation_controls_drive_the_v15_contract(self) -> None:
        viewer = self._show_route("viewer")
        overlay = getattr(viewer, "_trimble_navigation_overlay", None)
        self.assertIsNotNone(overlay)
        expected = (
            (QToolButton, "trimbleNavFit"),
            (QToolButton, "trimbleNavPan"),
            (QToolButton, "trimbleNavWalk"),
            (QToolButton, "trimbleNavOrbit"),
            (QToolButton, "trimbleNavFullscreen"),
            (QPushButton, "trimbleOrbitUp"),
            (QPushButton, "trimbleOrbitDown"),
            (QPushButton, "trimbleOrbitLeft"),
            (QPushButton, "trimbleOrbitRight"),
            (QPushButton, "trimbleOrbitCenter"),
            (QPushButton, "trimbleZoomIn"),
            (QPushButton, "trimbleZoomOut"),
            (QSlider, "trimbleZoomSlider"),
        )
        for widget_type, name in expected:
            self.assertIsNotNone(viewer.findChild(widget_type, name), name)

        viewer.findChild(QToolButton, "trimbleNavPan").click()
        self.assertEqual(viewer.navigation_mode, NavigationMode.PAN)
        viewer.findChild(QToolButton, "trimbleNavWalk").click()
        self.assertEqual(viewer.navigation_mode, NavigationMode.WALK)
        viewer.findChild(QToolButton, "trimbleNavOrbit").click()
        self.assertEqual(viewer.navigation_mode, NavigationMode.ORBIT)

        camera_before = repr(viewer._controller.get_camera())
        viewer.findChild(QPushButton, "trimbleOrbitRight").click()
        self._settle(3)
        camera_after = repr(viewer._controller.get_camera())
        self.assertNotEqual(camera_before, camera_after)

        camera_before = camera_after
        viewer.findChild(QPushButton, "trimbleZoomIn").click()
        self._settle(3)
        camera_after = repr(viewer._controller.get_camera())
        self.assertNotEqual(camera_before, camera_after)

    def test_03_camera_interaction_has_no_stall(self) -> None:
        viewer = self._show_route("viewer")
        started = time.perf_counter()
        frames = 48
        for _ in range(frames):
            viewer._controller.orbit(2.0, 0.25)
            self.app.processEvents()
        elapsed = time.perf_counter() - started
        fps = frames / max(elapsed, 0.001)
        print(f"V15 camera acceptance: {fps:.1f} controller updates/s")
        self.assertGreater(fps, 8.0)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ViewerV15LayoutNavigationAcceptance)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if result.wasSuccessful() else 1)
