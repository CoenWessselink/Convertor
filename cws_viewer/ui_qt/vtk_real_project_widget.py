"""PySide6/QVTK host for the V3 real-project mesh renderer."""
from __future__ import annotations

from typing import Any

from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()
    try:
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    except Exception as _vtk_qt_error:  # pragma: no cover - packaged diagnostics
        _VTK_QT_ERROR_TEXT = f"{type(_vtk_qt_error).__name__}: {_vtk_qt_error}"
        QVTKRenderWindowInteractor = None  # type: ignore[assignment]

    if QVTKRenderWindowInteractor is not None:

        class VtkRealProjectWidget(QVTKRenderWindowInteractor):  # type: ignore[misc]
            backend_ready = QtCore.Signal()
            backend_failed = QtCore.Signal(str)
            node_picked = QtCore.Signal(str)

            def __init__(self, repository: MeshRepository, parent: Any | None = None) -> None:
                super().__init__(parent)
                self.setObjectName("cwsVtkRealProjectWidget")
                self.setMinimumSize(620, 420)
                self.setMouseTracking(True)
                self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
                self._backend = VtkProjectMeshBackend(
                    repository,
                    render_window=self.GetRenderWindow(),
                    offscreen=False,
                )
                self._controller = ViewerCoreController(
                    self._backend,
                    width=max(1, self.width()),
                    height=max(1, self.height()),
                )
                interactor = self.GetRenderWindow().GetInteractor()
                if interactor is not None:
                    interactor.Initialize()
                self.backend_ready.emit()

            @property
            def backend(self) -> VtkProjectMeshBackend:
                return self._backend

            @property
            def controller(self) -> ViewerCoreController:
                return self._controller

            def load_scene(self, scene: ProjectScene) -> None:
                self._controller.load_scene(scene)

            def mousePressEvent(self, event: Any) -> None:
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    point = event.position()
                    pick = self._controller.pick_at(
                        int(point.x()), max(0, self.height() - int(point.y()) - 1)
                    )
                    if pick is not None:
                        self._controller.set_selection((pick.node_id,))
                        self.node_picked.emit(pick.node_id)
                super().mousePressEvent(event)

            def resizeEvent(self, event: Any) -> None:
                super().resizeEvent(event)
                size = event.size()
                if size.width() > 0 and size.height() > 0:
                    self._controller.resize(size.width(), size.height())

            def closeEvent(self, event: Any) -> None:
                self._controller.shutdown()
                super().closeEvent(event)

    else:

        class VtkRealProjectWidget:  # pragma: no cover
            def __init__(self, *_: Any, **__: Any) -> None:
                raise RuntimeError(
                    f"QVTKRenderWindowInteractor ontbreekt: {_VTK_QT_ERROR_TEXT}"
                )

else:

    class VtkRealProjectWidget:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["VtkRealProjectWidget"]
