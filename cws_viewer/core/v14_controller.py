"""V14 interaction extensions for the stable viewer core controller.

The base controller remains the renderer-neutral contract used by previous
releases.  V14 adds desktop interaction operations required by the professional
project viewer without changing canonical project data or production gates.
"""
from __future__ import annotations

from dataclasses import replace
import math

from cws_viewer.contracts.enums import RenderMode, SelectionOperation
from cws_viewer.contracts.state import ViewerDisplayPreferences
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.errors import ViewerError, ViewerErrorCode


class V14ViewerCoreController(ViewerCoreController):
    """ViewerCoreController plus V14 desktop camera/selection conveniences."""

    @staticmethod
    def _validate_display_preferences(preferences: ViewerDisplayPreferences) -> None:
        # True hidden-line is implemented by the real VTK mesh backend in V14.
        # Keep it blocked on synthetic/non-mesh backends so display remains honest.
        if preferences.render_mode == RenderMode.HIDDEN_LINE:
            # Validation is completed at instance level in set_display_preferences.
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
        raw = tuple(selector(int(x0), int(y0), int(x1), int(y1), index, crossing=bool(crossing)))
        requested: list[str] = []
        for node_id in raw:
            selectable = index.selectable_node_for_level(node_id, self.session.selection_level)
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
