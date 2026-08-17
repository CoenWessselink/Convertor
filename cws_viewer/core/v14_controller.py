"""V14 interaction extensions for the stable viewer core controller.

The base controller remains the renderer-neutral contract used by previous
releases. V14 adds desktop interaction operations required by the professional
project viewer without changing canonical project data or production gates.
"""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Iterable

from cws_viewer.contracts.enums import ProjectionType, RenderMode, SelectionLevel, SelectionOperation
from cws_viewer.contracts.state import PickResult, ViewerDisplayPreferences
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import BoundingBox, Vector3


class V14ViewerCoreController(ViewerCoreController):
    """ViewerCoreController plus professional desktop camera/selection behavior."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._orbit_pivot: Vector3 | None = None

    @staticmethod
    def _validate_display_preferences(preferences: ViewerDisplayPreferences) -> None:
        if preferences.render_mode == RenderMode.HIDDEN_LINE:
            return

    def set_display_preferences(self, preferences: ViewerDisplayPreferences) -> None:
        if preferences.render_mode == RenderMode.HIDDEN_LINE:
            backend_name = str(getattr(self.capabilities(), "renderer_backend", ""))
            if "mesh" not in backend_name:
                raise ViewerError(
                    "Hidden Line vereist de echte project-meshrenderer",
                    code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
                    context={"renderer_backend": backend_name},
                )
        super().set_display_preferences(preferences)

    def _sync_orbit_pivot_after_state_restore(self) -> None:
        if self._index is None:
            self._orbit_pivot = None
            return
        if self.session.selection:
            self.focus_orbit_on_selection()
        else:
            self.reset_orbit_pivot()

    def undo(self) -> bool:
        return self.undo_viewer()

    def redo(self) -> bool:
        return self.redo_viewer()

    def undo_viewer(self) -> bool:
        changed = super().undo_viewer()
        if changed:
            self._sync_orbit_pivot_after_state_restore()
        return changed

    def redo_viewer(self) -> bool:
        changed = super().redo_viewer()
        if changed:
            self._sync_orbit_pivot_after_state_restore()
        return changed

    def activate_viewpoint(self, viewpoint, *, allow_scene_mismatch: bool = False) -> None:
        super().activate_viewpoint(viewpoint, allow_scene_mismatch=allow_scene_mismatch)
        self._sync_orbit_pivot_after_state_restore()

    def restore_workspace_state(self, state, *, allow_scene_mismatch: bool = False):
        report = super().restore_workspace_state(
            state, allow_scene_mismatch=allow_scene_mismatch
        )
        self._sync_orbit_pivot_after_state_restore()
        return report

    @property
    def orbit_pivot(self) -> Vector3:
        if self._orbit_pivot is not None:
            return self._orbit_pivot
        return self.get_camera().target

    def set_orbit_pivot(self, point: Vector3) -> Vector3:
        pivot = Vector3(float(point.x), float(point.y), float(point.z))
        if not all(math.isfinite(value) for value in (pivot.x, pivot.y, pivot.z)):
            raise ValueError("Orbitpivot moet eindige wereldcoordinaten bevatten")
        self._orbit_pivot = pivot
        return pivot

    def reset_orbit_pivot(self) -> Vector3:
        self._orbit_pivot = self.get_camera().target
        return self._orbit_pivot

    @staticmethod
    def _translated_bounds(bounds: BoundingBox, offset: Vector3) -> BoundingBox:
        return BoundingBox(bounds.minimum + offset, bounds.maximum + offset)

    def display_bounds_for(
        self,
        node_ids: Iterable[str],
        *,
        include_descendants: bool = True,
        visible_only: bool = False,
    ) -> BoundingBox | None:
        """Return bounds at the positions the user actually sees.

        ``SceneIndex`` stores immutable canonical world bounds. Explode is
        viewer-only state and is therefore applied here instead of mutating the
        scene. Camera fit/focus must nevertheless follow exploded objects on
        screen rather than their pre-explode canonical positions.
        """
        index = self.index
        requested = tuple(dict.fromkeys(str(value) for value in node_ids))
        if not requested:
            return None
        if include_descendants:
            ids = index.descendants(
                requested, include_self=True, renderable_only=True
            )
        else:
            ids = tuple(
                node_id
                for node_id in requested
                if node_id in index.nodes_by_id
                and index.node(node_id).geometry_id is not None
            )
        if visible_only:
            visible, _ghosted = self.session.visible_and_ghosted(index)
            visible_set = set(visible)
            ids = tuple(node_id for node_id in ids if node_id in visible_set)
        if not ids:
            return None

        combined: BoundingBox | None = None
        for node_id in ids:
            bounds = index.world_bounds_by_node[node_id]
            offset = self.session.explode_offsets.get(node_id)
            if offset is not None and offset.length() > 1e-12:
                bounds = self._translated_bounds(bounds, offset)
            combined = bounds if combined is None else combined.union(bounds)
        return combined

    def focus_orbit_on_selection(self) -> Vector3 | None:
        if not self.session.selection:
            return None
        bounds = self.display_bounds_for(self.session.selection, include_descendants=True)
        if bounds is None:
            return None
        return self.set_orbit_pivot(bounds.center)

    def set_selection(self, ids: Iterable[str], *, mode: str = "replace") -> None:
        super().set_selection(ids, mode=mode)
        if self.session.selection:
            self.focus_orbit_on_selection()

    def probe_at(self, x: int, y: int) -> PickResult | None:
        index = self.index
        return self._backend.pick_at(int(x), int(y), index)

    def pick_at_level(
        self,
        x: int,
        y: int,
        *,
        level: SelectionLevel,
        mode: str = "replace",
    ) -> PickResult | None:
        """Pick once at a temporary hierarchy level, preserving the user's mode."""
        persistent = self.session.selection_level
        try:
            self.set_selection_level(SelectionLevel(level))
            return super().pick_at(int(x), int(y), mode=mode)
        finally:
            self.set_selection_level(persistent)

    def fit_all(self) -> None:
        visible, _ghosted = self.session.visible_and_ghosted(self.index)
        bounds = self.display_bounds_for(
            visible, include_descendants=False, visible_only=False
        )
        self._fit_bounds(bounds)
        self.reset_orbit_pivot()

    def fit_selection(self) -> None:
        if not self.session.selection:
            return
        bounds = self.display_bounds_for(self.session.selection, include_descendants=True)
        self._fit_bounds(bounds)
        self.focus_orbit_on_selection()

    def clear_scene(self) -> None:
        super().clear_scene()
        self._orbit_pivot = None

    def orbit(self, azimuth_deg: float, elevation_deg: float = 0.0) -> None:
        """Rigidly rotate the camera around the active picked/selection pivot."""
        camera = self.get_camera()
        pivot = self.orbit_pivot
        yaw = math.radians(float(azimuth_deg))
        pitch = math.radians(float(elevation_deg))

        position_offset = camera.position - pivot
        target_offset = camera.target - pivot
        yaw_position = position_offset.rotated_about_axis(camera.up, yaw)
        yaw_target = target_offset.rotated_about_axis(camera.up, yaw)
        yaw_view = (yaw_target - yaw_position).normalized()
        right = yaw_view.cross(camera.up).normalized()

        rotated_position = yaw_position.rotated_about_axis(right, pitch)
        rotated_target = yaw_target.rotated_about_axis(right, pitch)
        view = (rotated_target - rotated_position).normalized()
        corrected_up = right.cross(view).normalized()

        self.set_camera(
            replace(
                camera,
                position=pivot + rotated_position,
                target=pivot + rotated_target,
                up=corrected_up,
            )
        )

    def pan_pixels(
        self,
        delta_x_px: float,
        delta_y_px: float,
        *,
        anchor: Vector3 | None = None,
    ) -> Vector3:
        """Pan in screen pixels at the depth of the point picked on mouse-down.

        In perspective projection, apparent movement per pixel depends on depth.
        Using the picked model point makes the object under the cursor track the
        drag naturally instead of applying one arbitrary speed to every model
        scale. Orthographic movement uses the exact configured vertical extent.
        """
        camera = self.get_camera()
        view = (camera.target - camera.position).normalized()
        right = view.cross(camera.up).normalized()
        up = right.cross(view).normalized()

        if camera.projection == ProjectionType.ORTHOGRAPHIC:
            vertical_extent = max(float(camera.ortho_scale), 1e-9)
        else:
            default_depth = max((camera.target - camera.position).length(), 1.0)
            depth = default_depth
            if anchor is not None:
                candidate = (anchor - camera.position).dot(view)
                if math.isfinite(candidate) and candidate > camera.near_plane * 2.0:
                    depth = candidate
            vertical_extent = max(
                2.0 * depth * math.tan(math.radians(camera.field_of_view_deg) * 0.5),
                1e-9,
            )

        world_per_pixel = vertical_extent / max(float(self._height), 1.0)
        shift = (
            right * (-float(delta_x_px) * world_per_pixel)
            + up * (float(delta_y_px) * world_per_pixel)
        )
        if shift.length() > 1e-12:
            self.set_camera(
                replace(
                    camera,
                    position=camera.position + shift,
                    target=camera.target + shift,
                )
            )
        return shift

    def look(self, azimuth_deg: float, elevation_deg: float = 0.0) -> None:
        camera = self.get_camera()
        direction = camera.target - camera.position
        distance = max(direction.length(), 1e-9)
        yaw = math.radians(float(azimuth_deg))
        pitch = math.radians(float(elevation_deg))
        rotated = direction.rotated_about_axis(camera.up, yaw)
        right = rotated.normalized().cross(camera.up).normalized()
        rotated = rotated.rotated_about_axis(right, pitch)
        new_direction = rotated.normalized()
        up = right.cross(new_direction).normalized()
        self.set_camera(
            replace(
                camera,
                target=camera.position + new_direction * distance,
                up=up,
            )
        )

    def walk(
        self,
        *,
        forward: float = 0.0,
        right: float = 0.0,
        up: float = 0.0,
        yaw_deg: float = 0.0,
        pitch_deg: float = 0.0,
    ) -> None:
        if yaw_deg or pitch_deg:
            self.look(yaw_deg, pitch_deg)
        camera = self.get_camera()
        view = (camera.target - camera.position).normalized()
        right_vector = view.cross(camera.up).normalized()
        up_vector = right_vector.cross(view).normalized()
        shift = (
            view * float(forward)
            + right_vector * float(right)
            + up_vector * float(up)
        )
        if shift.length() <= 1e-12:
            return
        self.set_camera(
            replace(
                camera,
                position=camera.position + shift,
                target=camera.target + shift,
            )
        )

    def select_rectangle(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        *,
        mode: str = "replace",
        crossing: bool = True,
    ) -> tuple[str, ...]:
        index = self.index
        selector = getattr(self._backend, "nodes_in_screen_rect", None)
        if not callable(selector):
            raise ViewerError(
                "Vensterselectie wordt niet door deze renderer ondersteund",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            )
        raw = tuple(
            selector(
                int(x0), int(y0), int(x1), int(y1), index,
                crossing=bool(crossing),
            )
        )
        requested: list[str] = []
        for node_id in raw:
            selectable = index.selectable_node_for_level(
                node_id, self.session.selection_level
            )
            if selectable not in requested:
                requested.append(selectable)
        operation = SelectionOperation(mode)
        self.set_selection(tuple(requested), mode=operation.value)
        return tuple(requested)

    def clear_measurements(self) -> None:
        self._ensure_index()
        if not self._measurements.records:
            return
        self._push_history()
        self._measurements.records.clear()


__all__ = ["V14ViewerCoreController"]
