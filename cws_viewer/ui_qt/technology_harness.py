"""Side-by-side Qt technology harness for the V1 renderer decision."""
from __future__ import annotations

from typing import Any

from cws_viewer.technology.fixtures import build_box_grid_scene
from cws_viewer.ui_qt.occt_widget import OcctAisWidget
from cws_viewer.ui_qt.qt_compat import require_qt
from cws_viewer.ui_qt.vtk_widget import VtkMeshWidget


def create_harness_window(*, node_count: int = 1000) -> Any:
    QtCore, QtGui, QtWidgets = require_qt()

    class TechnologyHarnessWindow(QtWidgets.QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("CWS Viewer V1 — OCCT/AIS ↔ VTK technologieproef")
            self.resize(1500, 820)
            self._scene = build_box_grid_scene(node_count)
            central = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(central)
            header = QtWidgets.QLabel(
                f"Dezelfde deterministische scene — {node_count:,} instances — één CWS scenecontract"
            )
            header.setObjectName("cwsTechnologyHeader")
            layout.addWidget(header)
            splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            self.occt = OcctAisWidget()
            self.vtk = VtkMeshWidget()
            splitter.addWidget(self._panel("OCCT/AIS — exact BREP-pad", self.occt))
            splitter.addWidget(self._panel("VTK — project-meshpad", self.vtk))
            splitter.setSizes([750, 750])
            layout.addWidget(splitter, 1)
            self.status = QtWidgets.QLabel("Initialiseren…")
            layout.addWidget(self.status)
            self.setCentralWidget(central)
            self.occt.node_picked.connect(lambda node: self._picked("OCCT", node))
            self.vtk.node_picked.connect(lambda node: self._picked("VTK", node))
            QtCore.QTimer.singleShot(50, self._load)
            self.setStyleSheet(
                """
                QMainWindow, QWidget { background: #17202b; color: #e8eef5; }
                QLabel#cwsTechnologyHeader { font-size: 16px; font-weight: 600; padding: 8px; }
                QGroupBox { border: 1px solid #40536a; border-radius: 5px; margin-top: 8px; font-weight: 600; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                """
            )

        @staticmethod
        def _panel(title: str, widget: Any) -> Any:
            box = QtWidgets.QGroupBox(title)
            box_layout = QtWidgets.QVBoxLayout(box)
            box_layout.addWidget(widget)
            return box

        def _load(self) -> None:
            self.occt.load_scene(self._scene)
            self.vtk.load_scene(self._scene)
            self.status.setText("Beide backends tonen dezelfde scene. Klik op een box voor stable node-ID picking.")

        def _picked(self, backend: str, node_id: str) -> None:
            self.status.setText(f"{backend} geselecteerd: {node_id}")

    return TechnologyHarnessWindow()


def run_harness(*, node_count: int = 1000) -> int:
    QtCore, QtGui, QtWidgets = require_qt()
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = create_harness_window(node_count=node_count)
    window.show()
    return int(application.exec())


__all__ = ["create_harness_window", "run_harness"]
