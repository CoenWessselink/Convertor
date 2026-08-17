"""V14 interaction extensions for the stable viewer core controller.

The base controller remains the renderer-neutral contract used by previous
releases. V14 adds desktop interaction operations required by the professional
project viewer without changing canonical project data or production gates.
"""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Iterable

from cws_viewer.contracts.enums import RenderMode, SelectionOperation
from cws_viewer.contracts.state import PickResult, ViewerDisplayPreferences
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import Vector3


class V14ViewerCoreController(ViewerCoreController):
    """ViewerCoreController plus professional desktop camera/selection behavior.

    Orbit has its own world-space pivot.  Keeping that pivot separate from the
    camera focal target is deliberate: selecting a part must not make the view
    jump, yet the next orbit gesture must revolve around the selected part.
    During an orbit drag the UI may replace the selection pivot with the exact
    picked world point, matching the point-based rotate behavior used by the
    Trimble Connect reference workflow.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._orbit_pivot: Vector3 | None = None

    @staticmethod
    def _validate_display_preferences(preferences: ViewerDisplayPreferences) -> None:
        # True hidden-line is implemented by the real VTK mesh backend in V14.
        # Keep it blocked on synthetic/non-mesh backends so display remains honest.
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

    # Friendly aliases used by the V14 cockpit and standard desktop shortcuts.
    # The stable core keeps its explicit undo_viewer/redo_viewer names.
    def undo(self) -> bool:
        return self.undo_viewer()

    def redo(self) -> bool:
        return self.redo_viewer()

    @property
    def orbit_pivot(self) -> Vector3:
        """Return the active world-space point around which orbit rotates."""
        if self._orbit_pivot is not None:
            return self._orbit_pivot
        return self.get_camera().target

    def set_orbit_pivot(self, point: Vector3) -> Vector3:
        """Set orbit focus without changing camera position, target or zoom."""
        pivot = Vector3(float(point.x), float(point.y), float(point.z))
        if not all(math.isfinite(value) for value in (pivot.x, pivot.y, pivot.z)):
            raise ValueError("Orbitpivot moet eindige wereldcoordinaten bevatten")
        self._orbit_pivot = pivot
        return pivot

    def reset_orbit_pivot(self) -> Vector3:
        """Fall back to the current camera target as orbit focus."""
        self._orbit_pivot = self.get_camera().target
        return self._orbit_pivot

    def focus_orbit_on_selection(self) -> Vector3 | None:
        """Use the combined selected-object bounds center as persistent pivot.

        This method intentionally does not fit, pan or otherwise mutate the
        camera.  A selection therefore remains visually stable while subsequent
        orbit gestures revolve around that part/assembly/selection.
        """
        if not self.session.selection:
            return None
        bounds = self.index.bounds_for(self.session.selection, include_descendants=True)
        if bounds is None:
            return None
        return self.set_orbit_pivot(bounds.center)

    def set_selection(self, ids: Iterable[str], *, mode: str = "replace") -> None:
        """Preserve base selection semantics and bind orbit to non-empty selection."""
        super().set_selection(ids, mode=mode)
        if self.session.selection:
            self.focus_orbit_on_selection()
        # Clearing a selection deliberately keeps the last useful pivot.  This
        # avoids a surprising camera-focus jump back to the project origin.

    def probe_at(self, x: int, y: int) -> PickResult | None:
        """Read the exact renderer pick without changing selection or emitting events."""
        index = self.index
        return self._backend.pick_at(int(x), int(y), index)

    def fit_all(self) -> None:
        super().fit_all()
        self.reset_orbit_pivot()

    def fit_selection(self) -> None:
        if not self.session.selection:
            return
        super().fit_selection()
        self.focus_orbit_on_selection()

    def clear_scene(self) -> None:
        super().clear_scene()
        self._orbit_pivot = None

    def orbit(self, azimuth_deg: float, elevation_deg: float = 0.0) -> None:
        """Rigidly rotate the camera around the active picked/selection pivot.

        Position *and* focal target rotate around the pivot.  This is the key
        difference from the old implementation, which implicitly used only the
        camera target and therefore kept orbiting around a stale scene center.
        """
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

    def look(self, azimuth_deg: float, elevation_deg: float = 0.0) -> None:
        """Rotate camera direction around its fixed eye position."""
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
        """Translate the camera in view coordinates, optionally looking around."""
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
        """Select project nodes inside/crossing a screen rectangle."""
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
