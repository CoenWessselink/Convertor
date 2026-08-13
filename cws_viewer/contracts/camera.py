"""Camera and capture contracts shared by all future renderer backends."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from cws_viewer.api.errors import ViewerContractError
from ._validation import finite_float, require_text
from .primitives import Vector3, nonzero_vector3, vector3


class ProjectionType(str, Enum):
    PERSPECTIVE = "perspective"
    ORTHOGRAPHIC = "orthographic"


class StandardView(str, Enum):
    FRONT = "front"
    BACK = "back"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    ISOMETRIC = "isometric"


@dataclass(frozen=True, slots=True)
class CameraState:
    position: Vector3
    target: Vector3
    up: Vector3
    projection: ProjectionType = ProjectionType.PERSPECTIVE
    field_of_view_deg: float = 45.0
    ortho_scale: float = 1.0
    near_plane: float = 0.1
    far_plane: float = 1_000_000.0
    coordinate_system: str = "world"
    version: int = 1

    def __post_init__(self) -> None:
        position = vector3(self.position, "camera.position")
        target = vector3(self.target, "camera.target")
        up = nonzero_vector3(self.up, "camera.up")
        if position == target:
            raise ViewerContractError("Camera position en target mogen niet gelijk zijn")
        projection = ProjectionType(self.projection)
        fov = finite_float(self.field_of_view_deg, "field_of_view_deg")
        ortho = finite_float(self.ortho_scale, "ortho_scale")
        near = finite_float(self.near_plane, "near_plane")
        far = finite_float(self.far_plane, "far_plane")
        if not 0.0 < fov < 180.0:
            raise ViewerContractError("field_of_view_deg moet tussen 0 en 180 liggen")
        if ortho <= 0.0 or near <= 0.0 or far <= near:
            raise ViewerContractError("Camera clipping- en orthografische waarden zijn ongeldig")
        if int(self.version) < 1:
            raise ViewerContractError("Camera version moet positief zijn")
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "up", up)
        object.__setattr__(self, "projection", projection)
        object.__setattr__(self, "field_of_view_deg", fov)
        object.__setattr__(self, "ortho_scale", ortho)
        object.__setattr__(self, "near_plane", near)
        object.__setattr__(self, "far_plane", far)
        object.__setattr__(
            self,
            "coordinate_system",
            require_text(self.coordinate_system, "camera.coordinate_system"),
        )
        object.__setattr__(self, "version", int(self.version))

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": list(self.position),
            "target": list(self.target),
            "up": list(self.up),
            "projection": self.projection.value,
            "field_of_view_deg": self.field_of_view_deg,
            "ortho_scale": self.ortho_scale,
            "near_plane": self.near_plane,
            "far_plane": self.far_plane,
            "coordinate_system": self.coordinate_system,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CameraState":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class ScreenshotOptions:
    width: int
    height: int
    transparent_background: bool = False

    def __post_init__(self) -> None:
        if int(self.width) < 1 or int(self.height) < 1:
            raise ViewerContractError("Screenshotafmetingen moeten positief zijn")
        object.__setattr__(self, "width", int(self.width))
        object.__setattr__(self, "height", int(self.height))


__all__ = ["CameraState", "ProjectionType", "ScreenshotOptions", "StandardView"]
