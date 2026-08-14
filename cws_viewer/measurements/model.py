"""Deterministic measurement contracts shared by project and exact-part viewers.

The contracts deliberately keep measurement evidence separate from display
geometry.  Values derived from a display proxy can be shown for orientation,
but they can never satisfy a production validation gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Mapping
from uuid import uuid4

from cws_viewer.math3d import Vector3


def _vector_from_dict(value: Mapping[str, Any] | None) -> Vector3 | None:
    if value is None:
        return None
    return Vector3(float(value["x"]), float(value["y"]), float(value["z"]))


class MeasurementProof(StrEnum):
    ANALYTICAL_BREP = "analytical_brep"
    CANONICAL_FEATURE = "canonical_feature"
    VERIFIED_MESH = "verified_mesh"
    MANUAL = "manual"
    DISPLAY_PROXY = "display_proxy"

    @property
    def production_eligible(self) -> bool:
        return self in {self.ANALYTICAL_BREP, self.CANONICAL_FEATURE}


class SnapType(StrEnum):
    FREE = "free"
    VERTEX = "vertex"
    ENDPOINT = "endpoint"
    MIDPOINT = "midpoint"
    CENTER = "center"
    PERPENDICULAR = "perpendicular"
    INTERSECTION = "intersection"
    NEAREST = "nearest"
    FACE_CENTER = "face_center"


class MeasurementStatus(StrEnum):
    VALID = "valid"
    REVIEW = "review"
    INVALIDATED = "invalidated"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ExactMeasurementAnchor:
    node_id: str
    entity_id: str
    world_point: Vector3
    source_entity_id: str = ""
    feature_id: str | None = None
    subshape_type: str | None = None
    subshape_id: str | None = None
    local_point: Vector3 | None = None
    geometry_hash: str | None = None
    snap_type: SnapType = SnapType.FREE
    proof: MeasurementProof = MeasurementProof.MANUAL
    direction: Vector3 | None = None
    normal: Vector3 | None = None
    analytical_data: tuple[tuple[str, float | str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "snap_type", SnapType(self.snap_type))
        object.__setattr__(self, "proof", MeasurementProof(self.proof))
        object.__setattr__(
            self,
            "analytical_data",
            tuple((str(key), value) for key, value in self.analytical_data),
        )
        if not self.node_id.strip() or not self.entity_id.strip():
            raise ValueError("Measurement anchor vereist node_id en entity_id")

    @property
    def analytical(self) -> Mapping[str, float | str]:
        return dict(self.analytical_data)

    def to_dict(self) -> dict[str, Any]:
        def vec(value: Vector3 | None):
            return None if value is None else {"x": value.x, "y": value.y, "z": value.z}

        return {
            "node_id": self.node_id,
            "entity_id": self.entity_id,
            "source_entity_id": self.source_entity_id,
            "feature_id": self.feature_id,
            "subshape_type": self.subshape_type,
            "subshape_id": self.subshape_id,
            "world_point": vec(self.world_point),
            "local_point": vec(self.local_point),
            "geometry_hash": self.geometry_hash,
            "snap_type": self.snap_type.value,
            "proof": self.proof.value,
            "direction": vec(self.direction),
            "normal": vec(self.normal),
            "analytical_data": dict(self.analytical_data),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactMeasurementAnchor":
        analytical = value.get("analytical_data", {})
        if isinstance(analytical, Mapping):
            analytical_items = tuple((str(key), item) for key, item in analytical.items())
        else:
            analytical_items = tuple((str(key), item) for key, item in analytical)
        world = _vector_from_dict(value.get("world_point"))
        if world is None:
            raise ValueError("Measurement anchor world_point ontbreekt")
        return cls(
            node_id=str(value["node_id"]),
            entity_id=str(value["entity_id"]),
            source_entity_id=str(value.get("source_entity_id", "")),
            feature_id=None if value.get("feature_id") is None else str(value["feature_id"]),
            subshape_type=None if value.get("subshape_type") is None else str(value["subshape_type"]),
            subshape_id=None if value.get("subshape_id") is None else str(value["subshape_id"]),
            world_point=world,
            local_point=_vector_from_dict(value.get("local_point")),
            geometry_hash=None if value.get("geometry_hash") is None else str(value["geometry_hash"]),
            snap_type=SnapType(str(value.get("snap_type", SnapType.FREE.value))),
            proof=MeasurementProof(str(value.get("proof", MeasurementProof.MANUAL.value))),
            direction=_vector_from_dict(value.get("direction")),
            normal=_vector_from_dict(value.get("normal")),
            analytical_data=analytical_items,
        )


@dataclass(frozen=True, slots=True)
class MeasurementRecord:
    kind: str
    value: float
    unit: str
    anchors: tuple[ExactMeasurementAnchor, ...]
    formatted_text: str
    validity_hash: str
    proof: MeasurementProof
    measurement_id: str = ""
    name: str = ""
    note: str = ""
    visible: bool = True
    status: MeasurementStatus = MeasurementStatus.VALID
    invalid_reason: str = ""
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "anchors", tuple(self.anchors))
        object.__setattr__(self, "proof", MeasurementProof(self.proof))
        object.__setattr__(self, "status", MeasurementStatus(self.status))
        object.__setattr__(self, "metadata", tuple((str(k), str(v)) for k, v in self.metadata))
        if not self.measurement_id:
            object.__setattr__(self, "measurement_id", f"measurement-{uuid4()}")
        if not self.anchors:
            raise ValueError("Een meting vereist minimaal één anker")
        if self.status == MeasurementStatus.INVALIDATED and not self.invalid_reason:
            raise ValueError("Een geïnvalideerde meting vereist een reden")

    @property
    def production_eligible(self) -> bool:
        return self.status == MeasurementStatus.VALID and self.proof.production_eligible

    def to_dict(self) -> dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "kind": self.kind,
            "value": self.value,
            "unit": self.unit,
            "formatted_text": self.formatted_text,
            "anchors": [anchor.to_dict() for anchor in self.anchors],
            "validity_hash": self.validity_hash,
            "proof": self.proof.value,
            "name": self.name,
            "note": self.note,
            "visible": self.visible,
            "status": self.status.value,
            "invalid_reason": self.invalid_reason,
            "production_eligible": self.production_eligible,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MeasurementRecord":
        metadata = value.get("metadata", {})
        if isinstance(metadata, Mapping):
            metadata_items = tuple((str(key), str(item)) for key, item in metadata.items())
        else:
            metadata_items = tuple((str(key), str(item)) for key, item in metadata)
        return cls(
            measurement_id=str(value.get("measurement_id", "")),
            kind=str(value["kind"]),
            value=float(value["value"]),
            unit=str(value["unit"]),
            anchors=tuple(ExactMeasurementAnchor.from_dict(item) for item in value.get("anchors", ())),
            formatted_text=str(value.get("formatted_text", "")),
            validity_hash=str(value.get("validity_hash", "")),
            proof=MeasurementProof(str(value.get("proof", MeasurementProof.MANUAL.value))),
            name=str(value.get("name", "")),
            note=str(value.get("note", "")),
            visible=bool(value.get("visible", True)),
            status=MeasurementStatus(str(value.get("status", MeasurementStatus.VALID.value))),
            invalid_reason=str(value.get("invalid_reason", "")),
            metadata=metadata_items,
        )


@dataclass(frozen=True, slots=True)
class MeasurementSettings:
    length_unit: str = "mm"
    area_unit: str = "mm2"
    volume_unit: str = "mm3"
    angle_unit: str = "deg"
    mass_unit: str = "kg"
    precision: int = 3
    trailing_zeroes: bool = False

    def __post_init__(self) -> None:
        if self.length_unit not in {"mm", "cm", "m", "in", "ft"}:
            raise ValueError("Niet-ondersteunde lengteeenheid")
        if not 0 <= int(self.precision) <= 9:
            raise ValueError("Measurement precision moet 0..9 zijn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "length_unit": self.length_unit,
            "area_unit": self.area_unit,
            "volume_unit": self.volume_unit,
            "angle_unit": self.angle_unit,
            "mass_unit": self.mass_unit,
            "precision": self.precision,
            "trailing_zeroes": self.trailing_zeroes,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "MeasurementSettings":
        data = value or {}
        return cls(
            length_unit=str(data.get("length_unit", "mm")),
            area_unit=str(data.get("area_unit", "mm2")),
            volume_unit=str(data.get("volume_unit", "mm3")),
            angle_unit=str(data.get("angle_unit", "deg")),
            mass_unit=str(data.get("mass_unit", "kg")),
            precision=int(data.get("precision", 3)),
            trailing_zeroes=bool(data.get("trailing_zeroes", False)),
        )


@dataclass(slots=True)
class MeasurementCollection:
    records: dict[str, MeasurementRecord] = field(default_factory=dict)

    def add(self, record: MeasurementRecord) -> MeasurementRecord:
        self.records[record.measurement_id] = record
        return record

    def remove(self, measurement_id: str) -> MeasurementRecord | None:
        return self.records.pop(str(measurement_id), None)

    def values(self) -> tuple[MeasurementRecord, ...]:
        return tuple(self.records[key] for key in sorted(self.records))

    def invalidate_for_geometry(self, current_hashes: Mapping[str, str]) -> tuple[str, ...]:
        from dataclasses import replace

        invalidated: list[str] = []
        for key, record in list(self.records.items()):
            reasons: list[str] = []
            for anchor in record.anchors:
                expected = anchor.geometry_hash
                actual = current_hashes.get(anchor.node_id)
                if actual is None:
                    reasons.append(f"object {anchor.node_id} ontbreekt")
                elif expected and actual != expected:
                    reasons.append(f"geometry hash gewijzigd voor {anchor.node_id}")
            if reasons:
                self.records[key] = replace(
                    record,
                    status=MeasurementStatus.INVALIDATED,
                    invalid_reason="; ".join(dict.fromkeys(reasons)),
                )
                invalidated.append(key)
        return tuple(invalidated)


__all__ = [
    "MeasurementProof",
    "SnapType",
    "MeasurementStatus",
    "ExactMeasurementAnchor",
    "MeasurementRecord",
    "MeasurementSettings",
    "MeasurementCollection",
]
