"""PySide6/QVTK host for :class:`VtkMeshSpikeBackend`."""
from __future__ import annotations

from typing import Any

from cws_viewer.backends.vtk_mesh import VtkMeshSpikeBackend
from cws_viewer.technology.contracts import TechnologyScene
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()
    try:
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    except Exception as _vtk_qt_error:  # pragma: no cover - packaged diagnostics
        _VTK_QT_ERROR_TEXT = f"{type(_vtk_qt_error).__name__}: {_vtk_qt_error}"
        QVTKRenderWindowInteractor = None  # type: ignore[assignment]

    if QVTKRenderWindowInteractor is not None:

        class VtkMeshWidget(QVTKRenderWindowInteractor):  # type: ignore[misc]
            backend_ready = QtCore.Signal()
            backend_failed = QtCore.Signal(str)
            node_picked = QtCore.Signal(str)

            def __init__(self, parent: Any | None = None) -> None:
                super().__init__(parent)
                self.setObjectName("cwsVtkMeshWidget")
                self.setMinimumSize(320, 240)
                self.setMouseTracking(True)
                self._backend = VtkMeshSpikeBackend(
                    render_window=self.GetRenderWindow(), offscreen=False
                )
                self._backend.initialize(width=max(1, self.width()), height=max(1, self.height()))
                self._interactor = self.GetRenderWindow().GetInteractor()
                if self._interactor is not None:
                    self._interactor.Initialize()
                self.backend_ready.emit()

            @property
            def backend(self) -> VtkMeshSpikeBackend:
                return self._backend

            def load_scene(self, scene: TechnologyScene) -> None:
                self._backend.load_scene(scene)
                self._backend.set_isometric_view()
                self._backend.fit_all()
                self._backend.render()

            def mousePressEvent(self, event: Any) -> None:
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    point = event.position()
                    # VTK display coordinates have their origin at the lower-left.
                    picked = self._backend.pick_at(
                        int(point.x()), max(0, self.height() - int(point.y()) - 1)
                    )
                    if picked:
                        self.node_picked.emit(picked)
                super().mousePressEvent(event)

            def resizeEvent(self, event: Any) -> None:
                super().resizeEvent(event)
                size = event.size()
                self._backend.resize(size.width(), size.height())

            def closeEvent(self, event: Any) -> None:
                self._backend.dispose()
                super().closeEvent(event)

    else:

        class VtkMeshWidget:  # pragma: no cover
            def __init__(self, *_: Any, **__: Any) -> None:
                raise RuntimeError(f"QVTKRenderWindowInteractor ontbreekt: {_VTK_QT_ERROR_TEXT}")

else:

    class VtkMeshWidget:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["VtkMeshWidget"]
