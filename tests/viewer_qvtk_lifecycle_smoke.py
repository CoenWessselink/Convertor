from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ViewerQvtkLifecycleSmoke(unittest.TestCase):
    def test_qvtk_owns_native_interactor_show_and_close_lifecycle(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6 import QtTest, QtWidgets
        from cws_viewer.geometry.loader import MeshRepository
        from cws_viewer.ui_qt.vtk_real_project_widget import VtkRealProjectWidget

        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        widget = VtkRealProjectWidget(MeshRepository())
        self.assertIsNotNone(widget.GetRenderWindow())
        self.assertIsNotNone(widget.GetRenderWindow().GetInteractor())
        widget.resize(640, 420)
        widget.show()
        application.processEvents()
        QtTest.QTest.qWait(90)
        application.processEvents()
        widget.close()
        application.processEvents()

    def test_performance_host_renders_without_qvtk_child_window(self) -> None:
        from cws_viewer.core.real_performance_evidence import _OffscreenBenchmarkHost
        from cws_viewer.geometry.loader import MeshRepository

        host = _OffscreenBenchmarkHost(MeshRepository(), width=640, height=420)
        try:
            window = host.GetRenderWindow()
            self.assertEqual(int(window.GetOffScreenRendering()), 1)
            host.backend.render()
        finally:
            host.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
