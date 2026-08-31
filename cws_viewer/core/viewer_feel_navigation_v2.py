"""Upright CAD-style navigation refinements for the CWS Viewer."""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Any

from cws_viewer.core.viewer_feel_navigation import ViewerFeelNavigationService
from cws_viewer.core.viewer_interaction_profile import (
    TRIMBLE_STYLE_INTERACTION_PROFILE,
)
from cws_viewer.math3d import Vector3

WORLD_UP = Vector3(0.0, 0.0, 1.0)
MAX_ELEVATION_DEG = TRIMBLE_STYLE_INTERACTION_PROFILE.maximum_elevation_deg


class ViewerFeelNavigationV2Service(ViewerFeelNavigationService):
    """Use world-up yaw so horizontal mouse movement never introduces roll."""

    def orbit_upright(self, azimuth_deg: float, elevation_deg: float = 0.0):
        camera = self.controller.get_camera()
        pivot = self.controller.orbit_pivot
        position_offset = camera.position - pivot
        target_offset = camera.target - pivot

        yaw = math.radians(float(azimuth_deg))
        yaw_position = position_offset.rotated_about_axis(WORLD_UP, yaw)
        yaw_target = target_offset.rotated_about_axis(WORLD_UP, yaw)
        yaw_view = (yaw_target - yaw_position).normalized()

        # Pitch is clamped relative to the global horizontal plane.  The camera
        # cannot cross the zenith/nadir where the right vector flips and the
        # complete building suddenly appears tilted.
        current_elevation = math.degrees(
            math.asin(max(-1.0, min(1.0, yaw_view.dot(WORLD_UP))))
        )
        requested_elevation = max(
            -MAX_ELEVATION_DEG,
            min(MAX_ELEVATION_DEG, current_elevation + float(elevation_deg)),
        )
        pitch = math.radians(requested_elevation - current_elevation)

        right = yaw_view.cross(WORLD_UP)
        if right.length() <= 1e-9:
            # The elevation clamp normally prevents this path; use the camera's
            # last stable horizontal right direction as a defensive fallback.
            right = yaw_view.cross(camera.up)
        right = right.normalized()

        rotated_position = yaw_position.rotated_about_axis(right, pitch)
        rotated_target = yaw_target.rotated_about_axis(right, pitch)
        new_view = (rotated_target - rotated_position).normalized()
        new_right = new_view.cross(WORLD_UP)
        if new_right.length() <= 1e-9:
            new_right = right
        else:
            new_right = new_right.normalized()
        corrected_up = new_right.cross(new_view).normalized()

        updated = replace(
            camera,
            position=pivot + rotated_position,
            target=pivot + rotated_target,
            up=corrected_up,
        )
        self.controller.set_camera(updated)
        return updated


def viewer_feel_navigation_v2_contract() -> dict[str, Any]:
    return {
        "schema": "cws-viewer-feel-navigation-2.0",
        "capabilities": {
            "world_up_horizontal_orbit": True,
            "orbit_roll_suppressed": True,
            "orbit_pole_flip_clamped": True,
            "selected_object_pivot_preserved": True,
            "cursor_anchored_wheel_zoom_preserved": True,
        },
    }


__all__ = [
    "MAX_ELEVATION_DEG",
    "ViewerFeelNavigationV2Service",
    "WORLD_UP",
    "viewer_feel_navigation_v2_contract",
]
