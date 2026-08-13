"""Semantic selection and pick results, independent of renderer handles."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ._validation import require_text
from .primitives import Vector3, vector3


class SelectionLevel(str, Enum):
    MODEL = "model"
    ASSEMBLY = "assembly"
    PART = "part"
    FASTENER = "fastener"
    WELD = "weld"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"
    FEATURE = "feature"
    POINT = "point"


@dataclass(frozen=True, slots=True)
class PickResult:
    node_id: str
    entity_id: str
    world_point: Vector3
    part_id: str | None = None
    feature_id: str | None = None
    source_entity_id: str | None = None
    subshape_type: str | None = None
    subshape_id: str | None = None
    local_point: Vector3 | None = None
    normal: Vector3 | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", require_text(self.node_id, "node_id"))
        object.__setattr__(self, "entity_id", require_text(self.entity_id, "entity_id"))
        object.__setattr__(self, "world_point", vector3(self.world_point, "world_point"))
        if self.local_point is not None:
            object.__setattr__(self, "local_point", vector3(self.local_point, "local_point"))
        if self.normal is not None:
            object.__setattr__(self, "normal", vector3(self.normal, "normal"))
        for field_name in (
            "part_id",
            "feature_id",
            "source_entity_id",
            "subshape_type",
            "subshape_id",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_text(value, field_name))


__all__ = ["PickResult", "SelectionLevel"]
