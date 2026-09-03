"""Professional PySide6/QVTK host for the real-project renderer.

V14 deliberately separates *click selection* from *drag navigation*.  V13 sent
one left-mouse press both to the CWS picker and to VTK's default interactor,
which made orbiting/panning feel unpredictable.  The widget now owns the input
contract explicitly and mirrors familiar engineering-viewer behaviour without
copying third-party UI assets or implementation code.
"""
from __future__ import annotations

from enum import StrEnum
import math
from typing import Any

from cws_viewer.backends.vtk_project_mesh_v14 import VtkProjectMeshV14Backend
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


class NavigationMode(StrEnum):
    SELECT = "select"
    ORBIT = "orbit"
    PAN = "pan"
    WALK = "walk"
    LOOK = "look"


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
            pick_result = QtCore.Signal(object)
            context_requested = QtCore.Signal(object, object)
            navigation_mode_changed = QtCore.Signal(str)
            tool_cancelled = QtCore.Signal()
            interaction_message = QtCore.Signal(str)

            def __init__(self, repository: MeshRepository, parent: Any | None = None) -> None:
                super().__init__(parent)
                self.setObjectName("cwsVtkRealProjectWidget")
                self.setMinimumSize(620, 420)
                self.setMouseTracking(True)
                self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
                self._backend = VtkProjectMeshV14Backend(
                    repository,
                    render_window=self.GetRenderWindow(),
                    offscreen=False,
                )
                self._controller = V14ViewerCoreController(
                    self._backend,
                    width=max(1, self.width()),
                    height=max(1, self.height()),
                )
                # QVTK owns its vtkGenericRenderWindowInteractor lifecycle.
                # Calling Initialize() here (or from showEvent) duplicates that
                # native lifecycle and access-violates on supported Windows GPU
                # drivers. CWS navigation is controller-driven and needs no
                # second VTK interactor initialization.

                self._navigation_mode = NavigationMode.ORBIT
                self._area_selection = False
                self._press_pos: Any | None = None
                self._last_pos: Any | None = None
                self._pressed_button: Any | None = None
                self._dragging = False
                self._drag_threshold_px = 5.0
                self._rubber_band = QtWidgets.QRubberBand(
                    QtWidgets.QRubberBand.Shape.Rectangle, self
                )
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
                self.backend_ready.emit()

            @property
            def backend(self) -> VtkProjectMeshV14Backend:
                return self._backend

            @property
            def controller(self) -> V14ViewerCoreController:
                return self._controller

            @property
            def navigation_mode(self) -> NavigationMode:
                return self._navigation_mode

            @property
            def area_selection_enabled(self) -> bool:
                return self._area_selection

            def load_scene(self, scene: ProjectScene) -> None:
                self._controller.load_scene(scene)

            def set_navigation_mode(self, mode: NavigationMode | str) -> None:
                self._navigation_mode = NavigationMode(mode)
                self._area_selection = False
                self._rubber_band.hide()
                cursor = {
                    NavigationMode.ORBIT: QtCore.Qt.CursorShape.OpenHandCursor,
                    NavigationMode.PAN: QtCore.Qt.CursorShape.SizeAllCursor,
                    NavigationMode.WALK: QtCore.Qt.CursorShape.SizeVerCursor,
                    NavigationMode.LOOK: QtCore.Qt.CursorShape.CrossCursor,
                }[self._navigation_mode]
                self.setCursor(cursor)
                self.navigation_mode_changed.emit(self._navigation_mode.value)
                self.interaction_message.emit(
                    {
                        NavigationMode.ORBIT: "Roteren: sleep links · klik selecteert · middel = pan · wiel = zoom",
                        NavigationMode.PAN: "Pannen: sleep links of middel · wiel = zoom",
                        NavigationMode.WALK: "Lopen: sleep links of gebruik WASD/QE · wiel = zoom",
                        NavigationMode.LOOK: "Rondkijken: sleep links · camerapositie blijft staan",
                    }[self._navigation_mode]
                )

            def set_area_selection(self, enabled: bool = True) -> None:
                self._area_selection = bool(enabled)
                self._rubber_band.hide()
                self.setCursor(
                    QtCore.Qt.CursorShape.CrossCursor
                    if self._area_selection
                    else QtCore.Qt.CursorShape.OpenHandCursor
                )
                self.interaction_message.emit(
                    "Vensterselectie: sleep links→rechts = volledig binnen; rechts→links = kruisen"
                    if self._area_selection
                    else "Vensterselectie beëindigd"
                )

            def _vtk_xy(self, pos: Any) -> tuple[int, int]:
                return int(pos.x()), max(0, self.height() - int(pos.y()) - 1)

            def _selection_mode(self, modifiers: Any) -> str:
                if modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
                    return "add"
                if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier:
                    return "toggle"
                return "replace"

            def _pick(self, pos: Any, modifiers: Any, *, emit: bool = True):
                x, y = self._vtk_xy(pos)
                pick = self._controller.pick_at(
                    x, y, mode=self._selection_mode(modifiers)
                )
                if pick is not None and emit:
                    self.node_picked.emit(pick.node_id)
                    self.pick_result.emit(pick)
                return pick

            @staticmethod
            def _distance(a: Any, b: Any) -> float:
                return math.hypot(float(a.x() - b.x()), float(a.y() - b.y()))

            def mousePressEvent(self, event: Any) -> None:
                if event.button() in {
                    QtCore.Qt.MouseButton.LeftButton,
                    QtCore.Qt.MouseButton.MiddleButton,
                    QtCore.Qt.MouseButton.RightButton,
                }:
                    self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
                    self._press_pos = event.position()
                    self._last_pos = event.position()
                    self._pressed_button = event.button()
                    self._dragging = False
                    if self._area_selection and event.button() == QtCore.Qt.MouseButton.LeftButton:
                        origin = event.position().toPoint()
                        self._rubber_band.setGeometry(QtCore.QRect(origin, origin))
                        self._rubber_band.show()
                    event.accept()
                    return
                super().mousePressEvent(event)

            def mouseMoveEvent(self, event: Any) -> None:
                if self._press_pos is None or self._last_pos is None or self._pressed_button is None:
                    super().mouseMoveEvent(event)
                    return
                current = event.position()
                if not self._dragging and self._distance(current, self._press_pos) >= self._drag_threshold_px:
                    self._dragging = True
                if not self._dragging:
                    event.accept()
                    return

                if self._area_selection and self._pressed_button == QtCore.Qt.MouseButton.LeftButton:
                    self._rubber_band.setGeometry(
                        QtCore.QRect(self._press_pos.toPoint(), current.toPoint()).normalized()
                    )
                    event.accept()
                    return

                dx = float(current.x() - self._last_pos.x())
                dy = float(current.y() - self._last_pos.y())
                width = max(float(self.width()), 1.0)
                height = max(float(self.height()), 1.0)
                camera = self._controller.get_camera()
                distance = max((camera.target - camera.position).length(), 1.0)

                try:
                    if self._pressed_button == QtCore.Qt.MouseButton.MiddleButton:
                        self._controller.pan(-dx / width * 1.35, dy / height * 1.35)
                    elif self._pressed_button == QtCore.Qt.MouseButton.LeftButton:
                        if self._navigation_mode == NavigationMode.ORBIT:
                            self._controller.orbit(-dx * 0.32, -dy * 0.32)
                        elif self._navigation_mode == NavigationMode.PAN:
                            self._controller.pan(-dx / width * 1.35, dy / height * 1.35)
                        elif self._navigation_mode == NavigationMode.LOOK:
                            self._controller.look(-dx * 0.28, -dy * 0.28)
                        elif self._navigation_mode == NavigationMode.WALK:
                            self._controller.walk(
                                forward=-dy * distance * 0.0025,
                                right=dx * distance * 0.0025,
                            )
                    self._last_pos = current
                except Exception as exc:
                    self.backend_failed.emit(f"{type(exc).__name__}: {exc}")
                event.accept()

            def mouseReleaseEvent(self, event: Any) -> None:
                if self._press_pos is None or self._pressed_button is None:
                    super().mouseReleaseEvent(event)
                    return
                start = self._press_pos
                button = self._pressed_button
                dragged = self._dragging
                self._press_pos = None
                self._last_pos = None
                self._pressed_button = None
                self._dragging = False

                if button == QtCore.Qt.MouseButton.LeftButton and self._area_selection:
                    self._rubber_band.hide()
                    if dragged:
                        end = event.position()
                        x0, y0 = self._vtk_xy(start)
                        x1, y1 = self._vtk_xy(end)
                        crossing = float(end.x()) < float(start.x())
                        try:
                            ids = self._controller.select_rectangle(
                                x0,
                                y0,
                                x1,
                                y1,
                                mode=self._selection_mode(event.modifiers()),
                                crossing=crossing,
                            )
                            self.interaction_message.emit(
                                f"Vensterselectie: {len(ids):,} object(en)"
                            )
                        except Exception as exc:
                            self.backend_failed.emit(f"{type(exc).__name__}: {exc}")
                    self.set_area_selection(False)
                    event.accept()
                    return

                if button == QtCore.Qt.MouseButton.LeftButton and not dragged:
                    self._pick(event.position(), event.modifiers())
                    event.accept()
                    return

                if button == QtCore.Qt.MouseButton.RightButton and not dragged:
                    pick = self._pick(event.position(), event.modifiers(), emit=False)
                    self.context_requested.emit(event.globalPosition().toPoint(), pick)
                    event.accept()
                    return

                event.accept()

            def mouseDoubleClickEvent(self, event: Any) -> None:
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    pick = self._pick(event.position(), event.modifiers())
                    if pick is not None:
                        self._controller.fit_selection()
                    event.accept()
                    return
                super().mouseDoubleClickEvent(event)

            def wheelEvent(self, event: Any) -> None:
                steps = float(event.angleDelta().y()) / 120.0
                if abs(steps) <= 1e-12:
                    return
                self._controller.zoom(1.15 ** steps)
                event.accept()

            def keyPressEvent(self, event: Any) -> None:
                key = event.key()
                if key == QtCore.Qt.Key.Key_Escape:
                    self.set_area_selection(False)
                    self._controller.cancel_tool()
                    self.tool_cancelled.emit()
                    event.accept()
                    return
                if key == QtCore.Qt.Key.Key_Space:
                    self._controller.fit_selection()
                    event.accept()
                    return
                if self._navigation_mode == NavigationMode.WALK and key in {
                    QtCore.Qt.Key.Key_W,
                    QtCore.Qt.Key.Key_A,
                    QtCore.Qt.Key.Key_S,
                    QtCore.Qt.Key.Key_D,
                    QtCore.Qt.Key.Key_Q,
                    QtCore.Qt.Key.Key_E,
                }:
                    camera = self._controller.get_camera()
                    distance = max((camera.target - camera.position).length(), 1.0)
                    step = max(distance * 0.04, 100.0)
                    if key == QtCore.Qt.Key.Key_W:
                        self._controller.walk(forward=step)
                    elif key == QtCore.Qt.Key.Key_S:
                        self._controller.walk(forward=-step)
                    elif key == QtCore.Qt.Key.Key_A:
                        self._controller.walk(right=-step)
                    elif key == QtCore.Qt.Key.Key_D:
                        self._controller.walk(right=step)
                    elif key == QtCore.Qt.Key.Key_Q:
                        self._controller.walk(up=step)
                    elif key == QtCore.Qt.Key.Key_E:
                        self._controller.walk(up=-step)
                    event.accept()
                    return
                super().keyPressEvent(event)

            def resizeEvent(self, event: Any) -> None:
                super().resizeEvent(event)
                size = event.size()
                if size.width() > 0 and size.height() > 0:
                    self._cws_pending_resize = (size.width(), size.height())
                    timer = getattr(self, "_cws_resize_timer", None)
                    if timer is None:
                        timer = QtCore.QTimer(self)
                        timer.setSingleShot(True)
                        timer.timeout.connect(self._apply_cws_pending_resize)
                        self._cws_resize_timer = timer
                    timer.start(60)

            def _apply_cws_pending_resize(self) -> None:
                pending = getattr(self, "_cws_pending_resize", None)
                if pending is None or not self.isVisible():
                    return
                self._cws_pending_resize = None
                # QVTKRenderWindowInteractor already converts Qt logical sizes
                # to its device-pixel render surface. Multiplying the HWND size
                # by devicePixelRatioF a second time made the native viewer
                # overlap its neighbour by 47 px at 125% Windows scaling.
                logical_size = (
                    max(1, int(pending[0])),
                    max(1, int(pending[1])),
                )
                self._controller.resize(*logical_size)
                # The controller/backend already owns the VTK size. A second
                # unconditional Render() here can run before QVTK has a stable
                # native OpenGL context in a freshly copied portable runtime.
                # Scene loads and normal paint/input paths perform rendering.
                self.update()

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


__all__ = ["NavigationMode", "VtkRealProjectWidget"]
