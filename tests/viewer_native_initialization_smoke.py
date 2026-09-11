"""Native Qt/VTK construction regressions, including a deterministic early DPI resize."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows"
else:
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb" if os.environ.get("DISPLAY") else "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets, QtTest
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2


class ResizeDuringNativeHandleCreation(VtkRealProjectWidgetFeelV2):
    """Reproduce Windows' winId-triggered event before QVTK creates _Iren."""

    def winId(self):
        if self.__dict__.get("_Iren") is None:
            self.__dict__["early_resize_count"] = self.__dict__.get("early_resize_count", 0) + 1
            self.resizeEvent(QtGui.QResizeEvent(QtCore.QSize(640, 480), QtCore.QSize()))
        return super().winId()


class NativeInitializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_early_resize_keeps_full_native_viewer_and_overlays(self):
        widget = ResizeDuringNativeHandleCreation(MeshRepository())
        try:
            self.assertGreaterEqual(widget.__dict__.get("early_resize_count", 0), 1)
            self.assertIsNotNone(widget.__dict__.get("_Iren"))
            self.assertIsNotNone(widget.backend)
            controller = widget.controller
            widget.resize(960, 640)
            widget.show()
            QtTest.QTest.qWait(200)
            widget.resize(1000, 660)
            QtTest.QTest.qWait(200)
            self.assertIs(widget.controller, controller)
            self.assertEqual(widget._lasso_overlay.geometry(), widget.rect())
            self.assertEqual(widget._phase2_markup_overlay.geometry(), widget.rect())
            self.assertEqual(widget._viewport_controls.pos(), QtCore.QPoint(12, 12))
            self.assertTrue(widget.isVisible())
        finally:
            widget.close()
            widget.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main(verbosity=2)
