"""Stable measurement records with geometry-hash validity anchors."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from cws_viewer.api.errors import ViewerContractError
from ._validation import finite_float, require_sha256, require_text
from .primitives import Vector3, vector3


class MeasurementKind(str, Enum):
    POINT = "point"
    DISTANCE = "distance"
    POLYLINE = "polyline"
    EDGE_LENGTH = "edge_length"
    PERPENDICULAR_DISTANCE = "perpendicular_distance"
    FACE_DISTANCE = "face_distance"
    ANGLE = "angle"
    RADIUS = "radius"
    DIAMETER = "diameter"
    COORDINATE = "coordinate"
    AREA = "area"
    VOLUME = "volume"
    MASS = "mass"


class MeasurementStatus(str, Enum):
    VALID = "valid"
    STALE = "stale"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class MeasurementAnchor:
    entity_id: str
    world_point: Vector3
    feature_id: str | None = None
    subshape_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", require_text(self.entity_id, "entity_id"))
        object.__setattr__(self, "world_point", vector3(self.world_point, "world_point"))
        for field_name in ("feature_id", "subshape_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_text(value, field_name))

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "world_point": list(self.world_point),
            "feature_id": self.feature_id,
            "subshape_id": self.subshape_id,
        }


@dataclass(frozen=True, slots=True)
class Measurement:
    measurement_id: str
    kind: MeasurementKind
    anchors: tuple[MeasurementAnchor, ...]
    value: float
    unit: str
    provenance: str
    validity_hash: str
    status: MeasurementStatus = MeasurementStatus.VALID

    def __post_init__(self) -> None:
        anchors = tuple(self.anchors)
        if not anchors:
            raise ViewerContractError("Measurement vereist minimaal een anchor")
        object.__setattr__(self, "measurement_id", require_text(self.measurement_id, "measurement_id"))
        object.__setattr__(self, "kind", MeasurementKind(self.kind))
        object.__setattr__(self, "anchors", anchors)
        object.__setattr__(self, "value", finite_float(self.value, "measurement.value"))
        object.__setattr__(self, "unit", require_text(self.unit, "measurement.unit"))
        object.__setattr__(self, "provenance", require_text(self.provenance, "measurement.provenance"))
        object.__setattr__(self, "validity_hash", require_sha256(self.validity_hash, "validity_hash"))
        object.__setattr__(self, "status", MeasurementStatus(self.status))


__all__ = [
    "Measurement",
    "MeasurementAnchor",
    "MeasurementKind",
    "MeasurementStatus",
]
