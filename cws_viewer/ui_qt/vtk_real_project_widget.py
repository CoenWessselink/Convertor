"""PySide6/QVTK host for the real-project mesh renderer.

Desktop interaction is explicit and deterministic.  The widget uses actual
visible VTK mesh surfaces for picking whenever possible; the historical
centre-point picker remains a fallback only.  This makes selection and review
measurements behave like a professional BIM viewer without pretending a
triangulated display mesh is exact manufacturing BREP.
"""
from __future__ import annotations

import math
from typing import Any

from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend
from cws_viewer.contracts.enums import NodeKind, SelectionLevel
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.contracts.state import PickResult
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.math3d import BoundingBox, Vector3
from cws_viewer.model_grids import ModelGridCatalog
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()
    try:
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    except Exception as _vtk_qt_error:  # pragma: no cover
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
            measurement_status = QtCore.Signal(str)
            measurement_completed = QtCore.Signal(str, object)

            NAVIGATION_MODES = ("rotate", "pan", "walk", "look")
            MEASUREMENT_MODES = ("distance", "horizontal", "vertical", "coordinates")

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
                self._measurement_mode: str | None = None
                self._measurement_picks: list[PickResult] = []
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

            @property
            def measurement_mode(self) -> str | None:
                return self._measurement_mode

            def set_navigation_mode(self, mode: str) -> None:
                value = str(mode).strip().lower()
                if value not in self.NAVIGATION_MODES:
                    raise ValueError(f"Onbekende navigatiemodus: {mode}")
                if value != self._navigation_mode:
                    self._navigation_mode = value
                    self.navigation_mode_changed.emit(value)
                self.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

            def start_measurement(self, mode: str) -> None:
                value = str(mode).strip().lower()
                if value not in self.MEASUREMENT_MODES:
                    raise ValueError(f"Onbekende meetmodus: {mode}")
                self._measurement_mode = value
                self._measurement_picks.clear()
                if value == "coordinates":
                    text = "XYZ: klik een punt op het model · Esc annuleert"
                else:
                    text = f"{value}: klik punt 1 en punt 2 · Esc annuleert"
                self.measurement_status.emit(text)
                self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
                self.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)

            def cancel_measurement(self) -> None:
                if self._measurement_mode is not None:
                    self._measurement_mode = None
                    self._measurement_picks.clear()
                    self.unsetCursor()
                    self.measurement_status.emit("Meetmodus beëindigd")

            def load_scene(self, scene: ProjectScene) -> None:
                self._controller.load_scene(scene)

            # -----------------------------------------------------------------
            # IFC model-grid overlay.  Reference presentation only.
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
            # Real surface picking over instanced mesh actors.
            # -----------------------------------------------------------------
            @staticmethod
            def _point_box_distance_squared(point: Vector3, bounds: BoundingBox) -> float:
                dx = max(bounds.minimum.x - point.x, 0.0, point.x - bounds.maximum.x)
                dy = max(bounds.minimum.y - point.y, 0.0, point.y - bounds.maximum.y)
                dz = max(bounds.minimum.z - point.z, 0.0, point.z - bounds.maximum.z)
                return dx * dx + dy * dy + dz * dz

            def _surface_pick_at(self, x: int, y: int) -> PickResult | None:
                backend = self._backend
                renderer = getattr(backend, "_renderer", None)
                vtk = getattr(backend, "_vtk", None)
                index = self._controller.index
                if renderer is None or vtk is None:
                    return None
                groups = tuple(getattr(backend, "_mesh_groups", ()) or ())
                if not groups:
                    return None
                picker = vtk.vtkCellPicker()
                picker.SetTolerance(0.0008)
                picker.PickFromListOn()
                for group in groups:
                    picker.AddPickList(group.actor)
                if not picker.Pick(float(x), float(y), 0.0, renderer):
                    return None
                actor = picker.GetActor()
                group = getattr(backend, "_actor_to_group", {}).get(id(actor))
                if group is None:
                    return None
                world = Vector3(*picker.GetPickPosition())
                state = getattr(backend, "_state", None)
                visible = set(index.renderable_node_ids) if state is None else set(state.visible_set)
                candidates: list[tuple[float, float, str]] = []
                for node_id in group.node_ids:
                    if node_id not in visible:
                        continue
                    bounds = index.world_bounds_by_node[node_id]
                    if state is not None:
                        offset = state.explode_offsets.get(node_id, Vector3.zero())
                        bounds = BoundingBox(bounds.minimum + offset, bounds.maximum + offset)
                    box_distance = self._point_box_distance_squared(world, bounds)
                    center_distance = (bounds.center - world).dot(bounds.center - world)
                    candidates.append((box_distance, center_distance, node_id))
                if not candidates:
                    return None
                _, _, node_id = min(candidates)
                node = index.node(node_id)
                try:
                    inverse = index.world_transform_by_node[node_id].inverse_rigid()
                    local = inverse.transform_point(world)
                except Exception:
                    local = node.local_bounds.center
                try:
                    normal_values = picker.GetPickNormal()
                    normal = Vector3(*normal_values).normalized()
                except Exception:
                    normal = None
                return PickResult(
                    node_id=node_id,
                    entity_id=node.entity_id,
                    part_id=(
                        node.entity_id
                        if node.kind in {NodeKind.PART, NodeKind.PURCHASED_ITEM}
                        else None
                    ),
                    feature_id=(node.entity_id if node.kind == NodeKind.FEATURE else None),
                    source_entity_id=node.source_entity_id,
                    subshape_type=None,
                    subshape_id=None,
                    world_point=world,
                    local_point=local,
                    normal=normal,
                )

            def pick_result_at(self, x: int, y: int) -> PickResult | None:
                result = self._surface_pick_at(x, y)
                if result is not None:
                    return result
                # Safe fallback for drivers/VTK versions that cannot cell-pick
                # vtkGlyph3DMapper actors.
                return self._backend.pick_at(x, y, self._controller.index)

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
                self._controller.set_camera(
                    type(camera)(
                        position=camera.position + shift,
                        target=camera.target + shift,
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

            def _display_xy(self, event: Any) -> tuple[int, int]:
                point = event.position()
                return int(point.x()), max(0, self.height() - int(point.y()) - 1)

            def _pick_selection(self, event: Any) -> PickResult | None:
                x, y = self._display_xy(event)
                result = self.pick_result_at(x, y)
                if result is None:
                    if self._selection_mode(event) == "replace":
                        self._controller.set_selection((), mode="replace")
                    return None
                old_level = self._controller.session.selection_level
                if event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier:
                    self._controller.set_selection_level(SelectionLevel.ASSEMBLY)
                try:
                    selectable = self._controller.index.selectable_node_for_level(
                        result.node_id,
                        self._controller.session.selection_level,
                    )
                    self._controller.set_selection(
                        (selectable,), mode=self._selection_mode(event)
                    )
                finally:
                    if self._controller.session.selection_level != old_level:
                        self._controller.set_selection_level(old_level)
                self.node_picked.emit(result.node_id)
                return result

            def _rectangle_select(self, start: Any, end: Any, mode: str) -> None:
                y0 = max(0, self.height() - int(start.y()) - 1)
                y1 = max(0, self.height() - int(end.y()) - 1)
                crossing = int(end.x()) < int(start.x())
                method = getattr(self._controller, "select_rectangle", None)
                if method is not None:
                    method(
                        int(start.x()), y0, int(end.x()), y1,
                        mode=mode, crossing=crossing,
                    )
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

            def _measurement_pick(self, event: Any) -> bool:
                if self._measurement_mode is None:
                    return False
                x, y = self._display_xy(event)
                result = self.pick_result_at(x, y)
                if result is None:
                    self.measurement_status.emit("Geen modeloppervlak onder cursor")
                    return True
                self._measurement_picks.append(result)
                required = 1 if self._measurement_mode == "coordinates" else 2
                if len(self._measurement_picks) < required:
                    self.measurement_status.emit("Punt 1 vastgelegd · klik punt 2 · Esc annuleert")
                    return True
                picks = tuple(self._measurement_picks[:required])
                self._measurement_picks.clear()
                self.measurement_completed.emit(self._measurement_mode, picks)
                if required == 1:
                    self.measurement_status.emit("XYZ gemeten · klik opnieuw of Esc om te stoppen")
                else:
                    self.measurement_status.emit("Meting toegevoegd · klik opnieuw voor volgende meting of Esc")
                return True

            # -----------------------------------------------------------------
            # Qt input. Do not also let QVTK run a second camera system.
            # -----------------------------------------------------------------
            def mousePressEvent(self, event: Any) -> None:
                self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
                self._press_pos = event.position()
                self._last_pos = event.position()
                self._press_button = event.button()
                self._dragged = False
                if (
                    self._measurement_mode is None
                    and event.button() == QtCore.Qt.MouseButton.LeftButton
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
                if self._measurement_mode is not None and self._press_button == QtCore.Qt.MouseButton.LeftButton:
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
                            if not self._measurement_pick(event):
                                self._pick_selection(event)
                        elif event.button() == QtCore.Qt.MouseButton.RightButton:
                            self.context_requested.emit(event.globalPosition().toPoint())
                    self._press_pos = self._last_pos = self._press_button = None
                    self._dragged = False
                    event.accept()
                    return
                super().mouseReleaseEvent(event)

            def mouseDoubleClickEvent(self, event: Any) -> None:
                if event.button() == QtCore.Qt.MouseButton.LeftButton and self._measurement_mode is None:
                    self._pick_selection(event)
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
                    self._controller.zoom(1.16 ** (float(delta) / 120.0))
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
                    if self._measurement_mode is not None:
                        self.cancel_measurement()
                    else:
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
                self.cancel_measurement()
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
