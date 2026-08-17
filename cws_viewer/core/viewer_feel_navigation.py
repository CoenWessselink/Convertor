"""Cursor-anchored camera helpers for the CWS viewer handling repair build."""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Any

from cws_viewer.contracts.enums import ProjectionType
from cws_viewer.contracts.state import CameraState
from cws_viewer.core.v15_navigation import V15ViewNavigationService
from cws_viewer.math3d import Vector3

WHEEL_ZOOM_PER_NOTCH = 1.08


class ViewerFeelNavigationService(V15ViewNavigationService):
    """Preserve V15 orbit semantics while zooming through the cursor point."""

    def zoom_about_point(self, factor: float, pivot: Vector3) -> CameraState:
        zoom_factor = float(factor)
        if not math.isfinite(zoom_factor) or zoom_factor <= 0.0:
            raise ValueError("Zoomfactor moet een positief eindig getal zijn")
        camera = self.controller.get_camera()
        scale = 1.0 / zoom_factor

        if camera.projection == ProjectionType.ORTHOGRAPHIC:
            target_offset = camera.target - pivot
            eye_from_target = camera.position - camera.target
            new_target = pivot + target_offset * scale
            updated = replace(
                camera,
                target=new_target,
                position=new_target + eye_from_target,
                ortho_scale=max(float(camera.ortho_scale) * scale, 1e-6),
            )
        else:
            eye_offset = camera.position - pivot
            target_offset = camera.target - pivot
            eye_radius = eye_offset.length()
            if eye_radius <= 1e-12:
                return camera
            minimum_radius = max(float(camera.near_plane) * 2.0, 1e-6)
            requested_radius = eye_radius * scale
            new_radius = max(requested_radius, minimum_radius)
            effective_scale = new_radius / eye_radius
            updated = replace(
                camera,
                position=pivot + eye_offset * effective_scale,
                target=pivot + target_offset * effective_scale,
                far_plane=max(float(camera.far_plane), new_radius * 8.0, 10_000.0),
            )

        # Do not replace the semantic orbit pivot here. Selection remains the
        # orbit focus; no-selection orbit still binds its pivot on mouse-down.
        self.controller.set_camera(updated)
        return updated


def viewer_feel_navigation_contract() -> dict[str, Any]:
    return {
        "schema": "cws-viewer-feel-navigation-1.0",
        "capabilities": {
            "zoom_to_cursor_surface_point": True,
            "zoom_to_cursor_reference_depth_fallback": True,
            "wheel_notch_incremental_zoom": True,
            "wheel_zoom_factor_per_notch": WHEEL_ZOOM_PER_NOTCH,
            "zoom_does_not_replace_semantic_orbit_pivot": True,
            "coalesced_navigation_input": True,
            "selection_cursor_arrow": True,
            "pan_cursor_hand": True,
        },
    }


__all__ = [
    "ViewerFeelNavigationService",
    "WHEEL_ZOOM_PER_NOTCH",
    "viewer_feel_navigation_contract",
]
