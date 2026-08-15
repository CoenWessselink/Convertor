"""PySide6/QVTK host for the real-project mesh renderer.

This widget owns desktop interaction only.  The viewer controller remains the
single state authority.  Mouse/keyboard behaviour intentionally follows the
interaction model familiar from professional BIM viewers: explicit rotate,
pan, walk and look modes, wheel zoom, middle-button orbit, right-button look,
rectangle selection and discoverable keyboard shortcuts.
"""
from __future__ import annotations

import math
from typing import Any

from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend
from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.math3d import Vector3
from cws_viewer.model_grids import ModelGridCatalog
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
            navigation_mode_changed = QtCore.Signal(str)
            context_requested = QtCore.Signal(object)
            grids_changed = QtCore.Signal(bool, object)

            NAVIGATION_MODES = ("rotate", "pan", "walk", "look")

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

                self._navigation_mode = "rotate"
                self._press_pos: Any | None = None
                self._last_pos: Any | None = None
                self._press_button: Any | None = None
                self._dragged = False
                self._rectangle_start: Any | None = None
                self._grid_catalog = ModelGridCatalog()
                self._grid_actors_by_level: dict[float, list[Any]] = {}
                self._grid_labels_by_level: dict[float, list[Any]] = {}
                self._grid_levels_visible: set[float] = set()
                self._grids_enabled = True
                self.backend_ready.emit()

            @property
            def backend(self) -> VtkProjectMeshBackend:
                return self._backend

            @property
            def controller(self) -> ViewerCoreController:
                return self._controller

            @property
            def navigation_mode(self) -> str:
                return self._navigation_mode

            def set_navigation_mode(self, mode: str) -> None:
                value = str(mode).strip().lower()
                if value not in self.NAVIGATION_MODES:
                    raise ValueError(f"Onbekende navigatiemodus: {mode}")
                if value != self._navigation_mode:
                    self._navigation_mode = value
                    self.navigation_mode_changed.emit(value)
                self.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

            def load_scene(self, scene: ProjectScene) -> None:
                self._controller.load_scene(scene)

            # -----------------------------------------------------------------
            # IFC model grids — separate read-only reference presentation.
            # -----------------------------------------------------------------
            def _renderer(self):
                collection = self.GetRenderWindow().GetRenderers()
                return None if collection is None else collection.GetFirstRenderer()

            def _remove_grid_actors(self) -> None:
                renderer = self._renderer()
                if renderer is not None:
                    for actors in self._grid_actors_by_level.values():
                        for actor in actors:
                            renderer.RemoveActor(actor)
                    for actors in self._grid_labels_by_level.values():
                        for actor in actors:
                            renderer.RemoveActor(actor)
                self._grid_actors_by_level.clear()
                self._grid_labels_by_level.clear()

            def set_model_grids(self, catalog: ModelGridCatalog) -> None:
                self._remove_grid_actors()
                self._grid_catalog = catalog
                self._grid_levels_visible = set(catalog.default_visible_levels)
                if not catalog.axes:
                    self.grids_changed.emit(False, ())
                    return
                try:
                    import vtk
                except Exception as exc:
                    self.backend_failed.emit(f"VTK gridlaag niet beschikbaar: {exc}")
                    return
                renderer = self._renderer()
                if renderer is None:
                    return
                grouped: dict[float, list[Any]] = {}
                for axis in catalog.axes:
                    grouped.setdefault(round(axis.level_mm, 3), []).append(axis)
                for level, axes in grouped.items():
                    points = vtk.vtkPoints()
                    lines = vtk.vtkCellArray()
                    for axis in axes:
                        start_index = points.GetNumberOfPoints()
                        for point in axis.points:
                            points.InsertNextPoint(point.x, point.y, point.z)
                        for offset in range(len(axis.points) - 1):
                            line = vtk.vtkLine()
                            line.GetPointIds().SetId(0, start_index + offset)
                            line.GetPointIds().SetId(1, start_index + offset + 1)
                            lines.InsertNextCell(line)
                    poly = vtk.vtkPolyData()
                    poly.SetPoints(points)
                    poly.SetLines(lines)
                    mapper = vtk.vtkPolyDataMapper()
                    mapper.SetInputData(poly)
                    actor = vtk.vtkActor()
                    actor.SetMapper(mapper)
                    prop = actor.GetProperty()
                    prop.SetColor(0.36, 0.49, 0.60)
                    prop.SetOpacity(0.72)
                    prop.SetLineWidth(1.15)
                    prop.LightingOff()
                    actor.SetPickable(False)
                    renderer.AddActor(actor)
                    self._grid_actors_by_level[level] = [actor]

                    labels: list[Any] = []
                    for axis in axes:
                        if not axis.points:
                            continue
                        anchor = axis.points[0]
                        label = vtk.vtkBillboardTextActor3D()
                        label.SetInput(axis.axis_tag)
                        label.SetPosition(anchor.x, anchor.y, anchor.z)
                        text = label.GetTextProperty()
                        text.SetColor(0.18, 0.31, 0.40)
                        text.SetFontSize(14)
                        text.SetBold(True)
                        label.SetPickable(False)
                        renderer.AddActor(label)
                        labels.append(label)
                    self._grid_labels_by_level[level] = labels
                self._apply_grid_visibility(render=False)
                self._controller.render()
                self.grids_changed.emit(True, tuple(sorted(grouped)))

            def grid_levels(self) -> tuple[float, ...]:
                return tuple(sorted(self._grid_actors_by_level))

            def visible_grid_levels(self) -> tuple[float, ...]:
                return tuple(sorted(self._grid_levels_visible))

            def set_grids_visible(self, visible: bool) -> None:
                self._grids_enabled = bool(visible)
                self._apply_grid_visibility(render=True)
                self.grids_changed.emit(self._grids_enabled, self.visible_grid_levels())

            def set_grid_level_visible(self, level: float, visible: bool) -> None:
                key = round(float(level), 3)
                if visible:
                    self._grid_levels_visible.add(key)
                else:
                    self._grid_levels_visible.discard(key)
                self._apply_grid_visibility(render=True)
                self.grids_changed.emit(self._grids_enabled, self.visible_grid_levels())

            def _apply_grid_visibility(self, *, render: bool) -> None:
                for level, actors in self._grid_actors_by_level.items():
                    enabled = self._grids_enabled and level in self._grid_levels_visible
                    for actor in actors:
                        actor.SetVisibility(1 if enabled else 0)
                    for actor in self._grid_labels_by_level.get(level, ()): 
                        actor.SetVisibility(1 if enabled else 0)
                if render:
                    self._controller.render()

            # -----------------------------------------------------------------
            # Navigation helpers.
            # -----------------------------------------------------------------
            @staticmethod
            def _distance(a: Any, b: Any) -> float:
                return math.hypot(float(a.x()) - float(b.x()), float(a.y()) - float(b.y()))

            def _look_around(self, yaw_deg: float, pitch_deg: float) -> None:
                camera = self._controller.get_camera()
                view = camera.target - camera.position
                distance = max(view.length(), 1.0)
                direction = view.normalized()
                yawed = direction.rotated_about_axis(camera.up, math.radians(float(yaw_deg)))
                right = yawed.cross(camera.up).normalized()
                pitched = yawed.rotated_about_axis(right, math.radians(float(pitch_deg)))
                up = right.cross(pitched).normalized()
                self._controller.set_camera(
                    type(camera)(
                        position=camera.position,
                        target=camera.position + pitched.normalized() * distance,
                        up=up,
                        projection=camera.projection,
                        field_of_view_deg=camera.field_of_view_deg,
                        ortho_scale=camera.ortho_scale,
                        near_plane=camera.near_plane,
                        far_plane=camera.far_plane,
                    )
                )

            def _walk_drag(self, dx: float, dy: float) -> None:
                camera = self._controller.get_camera()
                distance = max((camera.target - camera.position).length(), 100.0)
                forward = -dy / max(float(self.height()), 1.0) * distance * 1.4
                yaw = -dx * 0.18
                view = (camera.target - camera.position).normalized()
                shift = view * forward
                moved_position = camera.position + shift
                moved_target = camera.target + shift
                self._controller.set_camera(
                    type(camera)(
                        position=moved_position,
                        target=moved_target,
                        up=camera.up,
                        projection=camera.projection,
                        field_of_view_deg=camera.field_of_view_deg,
                        ortho_scale=camera.ortho_scale,
                        near_plane=camera.near_plane,
                        far_plane=camera.far_plane,
                    )
                )
                if yaw:
                    self._look_around(yaw, 0.0)

            def _drag_navigation(self, dx: float, dy: float, *, forced: str | None = None) -> None:
                mode = forced or self._navigation_mode
                if mode == "rotate":
                    self._controller.orbit(-dx * 0.28, dy * 0.28)
                elif mode == "pan":
                    self._controller.pan(
                        -dx / max(float(self.width()), 1.0) * 1.25,
                        dy / max(float(self.height()), 1.0) * 1.25,
                    )
                elif mode == "walk":
                    self._walk_drag(dx, dy)
                else:
                    self._look_around(-dx * 0.22, dy * 0.22)

            def _selection_mode(self, event: Any) -> str:
                modifiers = event.modifiers()
                if modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
                    return "add"
                if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier:
                    return "toggle"
                return "replace"

            def _pick(self, event: Any) -> None:
                point = event.position()
                mode = self._selection_mode(event)
                old_level = self._controller.session.selection_level
                if event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier:
                    self._controller.set_selection_level(SelectionLevel.ASSEMBLY)
                try:
                    pick = self._controller.pick_at(
                        int(point.x()),
                        max(0, self.height() - int(point.y()) - 1),
                        mode=mode,
                    )
                finally:
                    if self._controller.session.selection_level != old_level:
                        self._controller.set_selection_level(old_level)
                if pick is not None:
                    self.node_picked.emit(pick.node_id)

            def _rectangle_select(self, start: Any, end: Any, mode: str) -> None:
                y0 = max(0, self.height() - int(start.y()) - 1)
                y1 = max(0, self.height() - int(end.y()) - 1)
                crossing = int(end.x()) < int(start.x())
                method = getattr(self._controller, "select_rectangle", None)
                if method is not None:
                    method(int(start.x()), y0, int(end.x()), y1, mode=mode, crossing=crossing)
                    return
                backend_method = getattr(self._backend, "nodes_in_screen_rect", None)
                if backend_method is None:
                    return
                nodes = tuple(
                    backend_method(
                        int(start.x()), y0, int(end.x()), y1,
                        self._controller.index,
                        crossing=crossing,
                    )
                )
                mapped = tuple(
                    dict.fromkeys(
                        self._controller.index.selectable_node_for_level(
                            node, self._controller.session.selection_level
                        )
                        for node in nodes
                    )
                )
                self._controller.set_selection(mapped, mode=mode)

            # -----------------------------------------------------------------
            # Qt input.  We intentionally do not call the default QVTK camera
            # handlers for handled events, otherwise two camera systems fight.
            # -----------------------------------------------------------------
            def mousePressEvent(self, event: Any) -> None:
                self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
                self._press_pos = event.position()
                self._last_pos = event.position()
                self._press_button = event.button()
                self._dragged = False
                if (
                    event.button() == QtCore.Qt.MouseButton.LeftButton
                    and event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier
                    and not event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    self._rectangle_start = event.position()
                    event.accept()
                    return
                if event.button() in {
                    QtCore.Qt.MouseButton.LeftButton,
                    QtCore.Qt.MouseButton.MiddleButton,
                    QtCore.Qt.MouseButton.RightButton,
                }:
                    event.accept()
                    return
                super().mousePressEvent(event)

            def mouseMoveEvent(self, event: Any) -> None:
                if self._last_pos is None or self._press_button is None:
                    return super().mouseMoveEvent(event)
                current = event.position()
                dx = float(current.x() - self._last_pos.x())
                dy = float(current.y() - self._last_pos.y())
                if self._press_pos is not None and self._distance(current, self._press_pos) > 3.5:
                    self._dragged = True
                self._last_pos = current
                if self._rectangle_start is not None:
                    event.accept()
                    return
                if self._press_button == QtCore.Qt.MouseButton.MiddleButton:
                    self._drag_navigation(dx, dy, forced="rotate")
                elif self._press_button == QtCore.Qt.MouseButton.RightButton:
                    self._drag_navigation(dx, dy, forced="look")
                elif self._press_button == QtCore.Qt.MouseButton.LeftButton:
                    self._drag_navigation(dx, dy)
                event.accept()

            def mouseReleaseEvent(self, event: Any) -> None:
                if event.button() == QtCore.Qt.MouseButton.LeftButton and self._rectangle_start is not None:
                    start = self._rectangle_start
                    self._rectangle_start = None
                    self._rectangle_select(start, event.position(), self._selection_mode(event))
                    self._press_pos = self._last_pos = self._press_button = None
                    event.accept()
                    return
                if event.button() == self._press_button:
                    if not self._dragged:
                        if event.button() == QtCore.Qt.MouseButton.LeftButton:
                            self._pick(event)
                        elif event.button() == QtCore.Qt.MouseButton.RightButton:
                            self.context_requested.emit(event.globalPosition().toPoint())
                    self._press_pos = self._last_pos = self._press_button = None
                    self._dragged = False
                    event.accept()
                    return
                super().mouseReleaseEvent(event)

            def mouseDoubleClickEvent(self, event: Any) -> None:
                if event.button() == QtCore.Qt.MouseButton.LeftButton:
                    self._pick(event)
                    if self._controller.get_selection():
                        self._controller.fit_selection()
                    else:
                        self._controller.fit_all()
                    event.accept()
                    return
                super().mouseDoubleClickEvent(event)

            def wheelEvent(self, event: Any) -> None:
                delta = event.angleDelta().y()
                if delta:
                    steps = float(delta) / 120.0
                    self._controller.zoom(1.16 ** steps)
                    event.accept()
                    return
                super().wheelEvent(event)

            def keyPressEvent(self, event: Any) -> None:
                key = event.key()
                modifiers = event.modifiers()
                ctrl = bool(modifiers & QtCore.Qt.KeyboardModifier.ControlModifier)
                shift = bool(modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier)
                if ctrl and key == QtCore.Qt.Key.Key_U:
                    self.set_navigation_mode("rotate")
                elif ctrl and key == QtCore.Qt.Key.Key_I:
                    self.set_navigation_mode("pan")
                elif ctrl and key == QtCore.Qt.Key.Key_O:
                    self.set_navigation_mode("walk")
                elif ctrl and key == QtCore.Qt.Key.Key_P:
                    self.set_navigation_mode("look")
                elif ctrl and key == QtCore.Qt.Key.Key_Z:
                    self._controller.undo_viewer()
                elif ctrl and key == QtCore.Qt.Key.Key_Y:
                    self._controller.redo_viewer()
                elif key == QtCore.Qt.Key.Key_Space:
                    if self._controller.get_selection():
                        self._controller.fit_selection()
                    else:
                        self._controller.fit_all()
                elif key == QtCore.Qt.Key.Key_Backspace:
                    selected = self._controller.get_selection()
                    if selected:
                        if shift:
                            self._controller.isolate(selected)
                        else:
                            self._controller.hide(selected)
                elif key == QtCore.Qt.Key.Key_Escape:
                    self._controller.cancel_tool()
                    self._controller.set_selection((), mode="replace")
                elif key == QtCore.Qt.Key.Key_F11:
                    window = self.window()
                    if window.isFullScreen():
                        window.showNormal()
                    else:
                        window.showFullScreen()
                elif key == QtCore.Qt.Key.Key_W:
                    self._walk_drag(0.0, -25.0)
                elif key == QtCore.Qt.Key.Key_S:
                    self._walk_drag(0.0, 25.0)
                elif key == QtCore.Qt.Key.Key_A:
                    self._controller.pan(0.025, 0.0)
                elif key == QtCore.Qt.Key.Key_D:
                    self._controller.pan(-0.025, 0.0)
                elif key == QtCore.Qt.Key.Key_Q:
                    self._controller.pan(0.0, -0.025)
                elif key == QtCore.Qt.Key.Key_E:
                    self._controller.pan(0.0, 0.025)
                elif key == QtCore.Qt.Key.Key_Left:
                    self._look_around(-4.0, 0.0)
                elif key == QtCore.Qt.Key.Key_Right:
                    self._look_around(4.0, 0.0)
                elif key == QtCore.Qt.Key.Key_Up:
                    self._look_around(0.0, 4.0)
                elif key == QtCore.Qt.Key.Key_Down:
                    self._look_around(0.0, -4.0)
                else:
                    return super().keyPressEvent(event)
                event.accept()

            def resizeEvent(self, event: Any) -> None:
                super().resizeEvent(event)
                size = event.size()
                if size.width() > 0 and size.height() > 0:
                    self._controller.resize(size.width(), size.height())

            def closeEvent(self, event: Any) -> None:
                self._remove_grid_actors()
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
