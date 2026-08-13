"""Display-only sectioning contracts."""
from __future__ import annotations

from dataclasses import dataclass

from ._validation import require_text
from .primitives import BoundingBox, Rgba, Vector3, nonzero_vector3, rgba, vector3


@dataclass(frozen=True, slots=True)
class SectionPlane:
    plane_id: str
    origin: Vector3
    normal: Vector3
    enabled: bool = True
    flipped: bool = False
    cap_mode: str = "none"
    display_color: Rgba = (0.95, 0.45, 0.1, 1.0)
    coordinate_system: str = "world"

    def __post_init__(self) -> None:
        object.__setattr__(self, "plane_id", require_text(self.plane_id, "plane_id"))
        object.__setattr__(self, "origin", vector3(self.origin, "section.origin"))
        object.__setattr__(self, "normal", nonzero_vector3(self.normal, "section.normal"))
        object.__setattr__(self, "display_color", rgba(self.display_color, "display_color"))
        object.__setattr__(self, "cap_mode", require_text(self.cap_mode, "cap_mode"))
        object.__setattr__(
            self,
            "coordinate_system",
            require_text(self.coordinate_system, "coordinate_system"),
        )


@dataclass(frozen=True, slots=True)
class ClippingBox:
    bounds: BoundingBox
    enabled: bool = True
    inverted: bool = False


__all__ = ["ClippingBox", "SectionPlane"]
