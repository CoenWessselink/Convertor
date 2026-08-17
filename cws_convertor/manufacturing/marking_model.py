"""Canonical M3 scribing/marking contracts.

Marking is derived manufacturing evidence. It never mutates imported/canonical
part geometry, never silently drops invalid geometry and never treats a DSTV
side label as manufacturing truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Any, Iterable

from cws_convertor.project.model import stable_sha256

MARK_FEATURE_SCHEMA = "cws-mark-feature-1.0"
MARK_SET_SCHEMA = "cws-mark-set-1.0"
MARKING_ALGORITHM = "cws-contact-scribing-1.0"


class MarkKind(StrEnum):
    SCRIBE_SEGMENT = "scribe_segment"
    REFERENCE_SEGMENT = "reference_segment"


class MarkStatus(StrEnum):
    ACCEPTED = "accepted"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class ExclusionKind(StrEnum):
    HOLE = "hole"
    WELD = "weld"
    CLAMP = "clamp"
    USER = "user"


def _point2(value: Iterable[float], label: str = "2D-punt") -> tuple[float, float]:
    values = tuple(float(item) for item in value)
    if len(values) != 2 or not all(math.isfinite(item) for item in values):
        raise ValueError(f"{label} vereist twee eindige coordinaten")
    return values


@dataclass(frozen=True, slots=True)
class MarkSegment2D:
    start: tuple[float, float]
    end: tuple[float, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "start", _point2(self.start, "Mark start"))
        object.__setattr__(self, "end", _point2(self.end, "Mark einde"))

    @property
    def length_mm(self) -> float:
        return math.dist(self.start, self.end)

    @property
    def midpoint(self) -> tuple[float, float]:
        return ((self.start[0] + self.end[0]) * 0.5, (self.start[1] + self.end[1]) * 0.5)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": [float(self.start[0]), float(self.start[1])],
            "end": [float(self.end[0]), float(self.end[1])],
            "length_mm": float(self.length_mm),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "MarkSegment2D":
        raw = dict(value or {})
        return cls(start=tuple(raw.get("start") or (0.0, 0.0)), end=tuple(raw.get("end") or (0.0, 0.0)))


@dataclass(frozen=True, slots=True)
class MarkExclusionZone:
    zone_id: str
    face_id: str
    kind: ExclusionKind | str
    center_2d: tuple[float, float]
    radius_mm: float
    source_id: str = ""
    clearance_mm: float = 0.0
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", ExclusionKind(self.kind))
        object.__setattr__(self, "center_2d", _point2(self.center_2d, "Exclusion center"))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        if not self.zone_id.strip() or not self.face_id.strip():
            raise ValueError("MarkExclusionZone mist zone_id of face_id")
        for label, value in (("radius_mm", self.radius_mm), ("clearance_mm", self.clearance_mm)):
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(f"MarkExclusionZone {label} is ongeldig")
        if self.radius_mm <= 0.0:
            raise ValueError("MarkExclusionZone vereist een positieve radius")

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "face_id": self.face_id,
            "kind": self.kind.value,
            "center_2d": list(self.center_2d),
            "radius_mm": float(self.radius_mm),
            "source_id": self.source_id,
            "clearance_mm": float(self.clearance_mm),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class MarkingRuleSet:
    ruleset_id: str = "CWS-M3-SCRIBING"
    version: str = "1.0"
    edge_clearance_mm: float = 0.0
    hole_clearance_mm: float = 2.0
    weld_clearance_mm: float = 2.0
    clamp_clearance_mm: float = 2.0
    min_segment_length_mm: float = 1.0
    max_segment_length_mm: float = 10000.0
    point_tolerance_mm: float = 1e-6
    minimum_contact_area_mm2: float = 1e-4
    require_verified_contact: bool = True
    require_planar_face: bool = True

    def __post_init__(self) -> None:
        if not self.ruleset_id.strip() or not self.version.strip():
            raise ValueError("MarkingRuleSet vereist ruleset_id en version")
        for label, value in (
            ("edge_clearance_mm", self.edge_clearance_mm),
            ("hole_clearance_mm", self.hole_clearance_mm),
            ("weld_clearance_mm", self.weld_clearance_mm),
            ("clamp_clearance_mm", self.clamp_clearance_mm),
            ("min_segment_length_mm", self.min_segment_length_mm),
            ("max_segment_length_mm", self.max_segment_length_mm),
            ("point_tolerance_mm", self.point_tolerance_mm),
            ("minimum_contact_area_mm2", self.minimum_contact_area_mm2),
        ):
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(f"MarkingRuleSet {label} is ongeldig")
        if self.min_segment_length_mm <= 0.0 or self.max_segment_length_mm < self.min_segment_length_mm:
            raise ValueError("MarkingRuleSet segmentlengtes zijn ongeldig")
        if self.point_tolerance_mm <= 0.0:
            raise ValueError("MarkingRuleSet point_tolerance_mm moet positief zijn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ruleset_id": self.ruleset_id,
            "version": self.version,
            "edge_clearance_mm": float(self.edge_clearance_mm),
            "hole_clearance_mm": float(self.hole_clearance_mm),
            "weld_clearance_mm": float(self.weld_clearance_mm),
            "clamp_clearance_mm": float(self.clamp_clearance_mm),
            "min_segment_length_mm": float(self.min_segment_length_mm),
            "max_segment_length_mm": float(self.max_segment_length_mm),
            "point_tolerance_mm": float(self.point_tolerance_mm),
            "minimum_contact_area_mm2": float(self.minimum_contact_area_mm2),
            "require_verified_contact": bool(self.require_verified_contact),
            "require_planar_face": bool(self.require_planar_face),
        }

    @property
    def ruleset_sha256(self) -> str:
        return stable_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class MarkFeature:
    mark_id: str
    part_id: str
    face_id: str
    kind: MarkKind | str
    status: MarkStatus | str
    segment: MarkSegment2D
    source_contact_id: str
    source_secondary_part_id: str
    ruleset_sha256: str
    source_geometry_hash: str = ""
    exact_geometry: bool = True
    confidence: float = 1.0
    provenance: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    blocking_codes: tuple[str, ...] = ()
    feature_sha256: str = ""
    schema_version: str = MARK_FEATURE_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", MarkKind(self.kind))
        object.__setattr__(self, "status", MarkStatus(self.status))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        if not self.mark_id.strip() or not self.part_id.strip() or not self.face_id.strip():
            raise ValueError("MarkFeature mist mark_id, part_id of face_id")
        if not self.source_contact_id.strip() or not self.ruleset_sha256.strip():
            raise ValueError("MarkFeature mist broncontact of ruleset hash")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("MarkFeature confidence moet 0..1 zijn")
        expected = stable_sha256(self.identity_payload())
        if self.feature_sha256 and self.feature_sha256 != expected:
            raise ValueError("MarkFeature feature_sha256 klopt niet")
        object.__setattr__(self, "feature_sha256", expected)

    @property
    def production_usable(self) -> bool:
        return self.status == MarkStatus.ACCEPTED and self.exact_geometry and not self.blocking_codes

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "part_id": self.part_id,
            "face_id": self.face_id,
            "kind": self.kind.value,
            "segment": self.segment.to_dict(),
            "source_contact_id": self.source_contact_id,
            "source_secondary_part_id": self.source_secondary_part_id,
            "ruleset_sha256": self.ruleset_sha256,
            "source_geometry_hash": self.source_geometry_hash,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "mark_id": self.mark_id,
            "status": self.status.value,
            "exact_geometry": bool(self.exact_geometry),
            "confidence": float(self.confidence),
            "provenance": dict(self.provenance),
            "warnings": list(self.warnings),
            "blocking_codes": list(self.blocking_codes),
            "feature_sha256": self.feature_sha256,
            "production_usable": self.production_usable,
        }


@dataclass(frozen=True, slots=True)
class MarkSet:
    part_id: str
    manufacturing_hash: str
    face_report_sha256: str
    contact_report_sha256: str
    ruleset_sha256: str
    features: tuple[MarkFeature, ...]
    exclusions: tuple[MarkExclusionZone, ...] = ()
    blocking_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    algorithm_version: str = MARKING_ALGORITHM
    report_sha256: str = ""
    schema_version: str = MARK_SET_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "features", tuple(self.features))
        object.__setattr__(self, "exclusions", tuple(self.exclusions))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        if not self.part_id.strip() or not self.manufacturing_hash.strip():
            raise ValueError("MarkSet mist onderdeel- of manufacturing identiteit")
        expected = self.calculate_hash()
        if self.report_sha256 and self.report_sha256 != expected:
            raise ValueError("MarkSet report_sha256 klopt niet")

    @property
    def accepted_features(self) -> tuple[MarkFeature, ...]:
        return tuple(item for item in self.features if item.status == MarkStatus.ACCEPTED)

    @property
    def production_usable(self) -> bool:
        return (
            bool(self.features)
            and not self.blocking_codes
            and all(item.production_usable for item in self.features)
        )

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "algorithm_version": self.algorithm_version,
            "part_id": self.part_id,
            "manufacturing_hash": self.manufacturing_hash,
            "face_report_sha256": self.face_report_sha256,
            "contact_report_sha256": self.contact_report_sha256,
            "ruleset_sha256": self.ruleset_sha256,
            "features": [item.to_dict() for item in self.features],
            "exclusions": [item.to_dict() for item in self.exclusions],
            "blocking_codes": list(self.blocking_codes),
            "warnings": list(self.warnings),
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "MarkSet":
        result = cls(report_sha256="", **kwargs)
        return cls(**kwargs, report_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        result = self.payload_dict()
        result["report_sha256"] = self.report_sha256
        result["production_usable"] = self.production_usable
        return result


__all__ = [
    "MARK_FEATURE_SCHEMA", "MARK_SET_SCHEMA", "MARKING_ALGORITHM",
    "MarkKind", "MarkStatus", "ExclusionKind", "MarkSegment2D",
    "MarkExclusionZone", "MarkingRuleSet", "MarkFeature", "MarkSet",
]
