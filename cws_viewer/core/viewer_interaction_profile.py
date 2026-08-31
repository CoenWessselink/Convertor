"""Single source of truth for observable CWS viewer interaction behaviour."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ViewerInteractionProfile:
    """Calibrated public interaction profile for the desktop viewer."""

    profile_id: str
    orbit_deg_per_pixel: float
    look_deg_per_pixel: float
    walk_distance_per_pixel: float
    wheel_zoom_factor_per_notch: float
    navigation_frame_ms: int
    measurement_preview_ms: int
    interaction_idle_ms: int
    maximum_elevation_deg: float
    selection_plain: str = "replace"
    selection_control: str = "toggle"
    selection_shift: str = "add"

    def selection_mode(self, *, control: bool, shift: bool) -> str:
        if control:
            return self.selection_control
        if shift:
            return self.selection_shift
        return self.selection_plain

    def validate(self) -> None:
        if self.orbit_deg_per_pixel <= 0.0:
            raise ValueError("orbit_deg_per_pixel must be positive")
        if self.look_deg_per_pixel <= 0.0:
            raise ValueError("look_deg_per_pixel must be positive")
        if self.walk_distance_per_pixel <= 0.0:
            raise ValueError("walk_distance_per_pixel must be positive")
        if self.wheel_zoom_factor_per_notch <= 1.0:
            raise ValueError("wheel_zoom_factor_per_notch must exceed one")
        if min(
            self.navigation_frame_ms,
            self.measurement_preview_ms,
            self.interaction_idle_ms,
        ) <= 0:
            raise ValueError("interaction timings must be positive")
        if not 0.0 < self.maximum_elevation_deg < 90.0:
            raise ValueError("maximum_elevation_deg must be between zero and 90")
        modes = {self.selection_plain, self.selection_control, self.selection_shift}
        if modes != {"replace", "toggle", "add"}:
            raise ValueError("selection modes must cover replace, toggle and add")

    def contract(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema": "cws-viewer-interaction-profile-1.0",
            "target": "CWS Viewer Observable Trimble-Style Parity",
            "profile": asdict(self),
            "input_matrix": {
                "left_click": "select at configured part/assembly level",
                "control_left_click": "toggle item in multi-selection",
                "shift_left_click": "add item to multi-selection",
                "left_drag_orbit_mode": "upright orbit around picked cursor pivot",
                "left_drag_pan_mode": "pan at picked display depth",
                "middle_drag": "pan at picked display depth",
                "wheel": "incremental zoom about cursor surface point",
                "empty_space_orbit": "preserve last valid model pivot",
            },
        }


TRIMBLE_STYLE_INTERACTION_PROFILE = ViewerInteractionProfile(
    profile_id="cws-observable-trimble-style-v1",
    orbit_deg_per_pixel=0.22,
    look_deg_per_pixel=0.20,
    walk_distance_per_pixel=0.0018,
    wheel_zoom_factor_per_notch=1.08,
    navigation_frame_ms=16,
    measurement_preview_ms=45,
    interaction_idle_ms=180,
    maximum_elevation_deg=88.5,
)


__all__ = [
    "TRIMBLE_STYLE_INTERACTION_PROFILE",
    "ViewerInteractionProfile",
]
