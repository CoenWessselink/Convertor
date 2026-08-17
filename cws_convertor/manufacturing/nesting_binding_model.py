"""M6 nesting-aware marking contracts.

Nesting is a late-binding layer. Canonical part geometry and ManufacturingFace
identity stay unchanged; only a proven rigid part-to-stock transform may bind
manufacturing intents to one physical production instance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Any, Iterable

from cws_convertor.project.model import Transform3D, stable_sha256

NESTING_PLACEMENT_SCHEMA = "cws-nesting-placement-1.0"
NESTED_FEATURE_SCHEMA = "cws-nested-mark-feature-1.0"
NESTING_MARKING_SCHEMA = "cws-nesting-marking-report-1.0"
NESTING_BINDING_ALGORITHM = "cws-nesting-mark-binding-1.0"


class NestedFeatureStatus(StrEnum):
    BOUND = "bound"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class NestedFeatureKind(StrEnum):
    SCRIBE_SEGMENT = "scribe_segment"
    HOLE_REFERENCE = "hole_reference"
    IDENTIFICATION_TEXT = "identification_text"


def _vec3(value: Iterable[float], label: str) -> tuple[float, float, float]:
    items = tuple(float(item) for item in value)
    if len(items) != 3 or not all(math.isfinite(item) for item in items):
        raise ValueError(f"{label} vereist drie eindige coordinaten")
    return items


@dataclass(frozen=True, slots=True)
class NestingPlacement:
    nesting_run_id: str
    stock_id: str
    stock_kind: str
    part_id: str
    production_instance_id: str
    manufacturing_hash: str
    part_to_stock: Transform3D | dict[str, Any] | list[float] | tuple[float, ...]
    assembly_id: str = ""
    assembly_mark: str = ""
    orientation_variant: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    placement_sha256: str = ""
    schema_version: str = NESTING_PLACEMENT_SCHEMA

    def __post_init__(self) -> None:
        transform = Transform3D.from_dict(self.part_to_stock)
        object.__setattr__(self, "part_to_stock", transform)
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        for label, value in (
            ("nesting_run_id", self.nesting_run_id),
            ("stock_id", self.stock_id),
            ("stock_kind", self.stock_kind),
            ("part_id", self.part_id),
            ("production_instance_id", self.production_instance_id),
            ("manufacturing_hash", self.manufacturing_hash),
        ):
            if not str(value).strip():
                raise ValueError(f"NestingPlacement mist {label}")
        expected = stable_sha256(self.identity_payload())
        if self.placement_sha256 and self.placement_sha256 != expected:
            raise ValueError("NestingPlacement placement_sha256 klopt niet")
        object.__setattr__(self, "placement_sha256", expected)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "nesting_run_id": self.nesting_run_id,
            "stock_id": self.stock_id,
            "stock_kind": self.stock_kind,
            "part_id": self.part_id,
            "production_instance_id": self.production_instance_id,
            "manufacturing_hash": self.manufacturing_hash,
            "part_to_stock_matrix": self.part_to_stock.flat(),
            "assembly_id": self.assembly_id,
            "assembly_mark": self.assembly_mark,
            "orientation_variant": self.orientation_variant,
            "provenance": dict(self.provenance),
        }

    def to_dict(self) -> dict[str, Any]:
        result = self.identity_payload()
        result["placement_sha256"] = self.placement_sha256
        return result

    def point_to_stock(self, point_part_mm: Iterable[float]) -> tuple[float, float, float]:
        point = _vec3(point_part_mm, "Part-punt")
        m = self.part_to_stock.matrix
        return tuple(
            float(m[row][0]) * point[0]
            + float(m[row][1]) * point[1]
            + float(m[row][2]) * point[2]
            + float(m[row][3])
            for row in range(3)
        )

    def vector_to_stock(self, vector_part: Iterable[float]) -> tuple[float, float, float]:
        vector = _vec3(vector_part, "Part-vector")
        m = self.part_to_stock.matrix
        return tuple(
            float(m[row][0]) * vector[0]
            + float(m[row][1]) * vector[1]
            + float(m[row][2]) * vector[2]
            for row in range(3)
        )


@dataclass(frozen=True, slots=True)
class StockClampZone:
    zone_id: str
    stock_id: str
    minimum_stock_mm: tuple[float, float, float]
    maximum_stock_mm: tuple[float, float, float]
    clearance_mm: float = 0.0
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "minimum_stock_mm", _vec3(self.minimum_stock_mm, "Clamp minimum"))
        object.__setattr__(self, "maximum_stock_mm", _vec3(self.maximum_stock_mm, "Clamp maximum"))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        if not self.zone_id.strip() or not self.stock_id.strip():
            raise ValueError("StockClampZone mist zone_id of stock_id")
        if any(a > b for a, b in zip(self.minimum_stock_mm, self.maximum_stock_mm)):
            raise ValueError("StockClampZone minimum is groter dan maximum")
        if not math.isfinite(float(self.clearance_mm)) or float(self.clearance_mm) < 0.0:
            raise ValueError("StockClampZone clearance_mm is ongeldig")

    @property
    def zone_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "stock_id": self.stock_id,
            "minimum_stock_mm": list(self.minimum_stock_mm),
            "maximum_stock_mm": list(self.maximum_stock_mm),
            "clearance_mm": float(self.clearance_mm),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class CommonCutZone:
    common_cut_id: str
    stock_id: str
    member_production_instance_ids: tuple[str, ...]
    minimum_stock_mm: tuple[float, float, float]
    maximum_stock_mm: tuple[float, float, float]
    exact_geometry: bool
    evidence_sha256: str
    clearance_mm: float = 0.0
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "member_production_instance_ids", tuple(dict.fromkeys(self.member_production_instance_ids)))
        object.__setattr__(self, "minimum_stock_mm", _vec3(self.minimum_stock_mm, "Common-cut minimum"))
        object.__setattr__(self, "maximum_stock_mm", _vec3(self.maximum_stock_mm, "Common-cut maximum"))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        if not self.common_cut_id.strip() or not self.stock_id.strip():
            raise ValueError("CommonCutZone mist common_cut_id of stock_id")
        if any(a > b for a, b in zip(self.minimum_stock_mm, self.maximum_stock_mm)):
            raise ValueError("CommonCutZone minimum is groter dan maximum")
        if not math.isfinite(float(self.clearance_mm)) or float(self.clearance_mm) < 0.0:
            raise ValueError("CommonCutZone clearance_mm is ongeldig")
        if self.exact_geometry and not self.evidence_sha256.strip():
            raise ValueError("Exact CommonCutZone vereist evidence_sha256")

    @property
    def zone_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "common_cut_id": self.common_cut_id,
            "stock_id": self.stock_id,
            "member_production_instance_ids": list(self.member_production_instance_ids),
            "minimum_stock_mm": list(self.minimum_stock_mm),
            "maximum_stock_mm": list(self.maximum_stock_mm),
            "exact_geometry": bool(self.exact_geometry),
            "evidence_sha256": self.evidence_sha256,
            "clearance_mm": float(self.clearance_mm),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class NestedManufacturingFeature:
    feature_id: str
    source_feature_id: str
    source_intent_sha256: str
    feature_kind: NestedFeatureKind | str
    part_id: str
    production_instance_id: str
    stock_id: str
    face_id: str
    geometry_stock_mm: dict[str, Any]
    machine_decision_sha256: str
    status: NestedFeatureStatus | str
    conflict_zone_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    blocking_codes: tuple[str, ...] = ()
    feature_sha256: str = ""
    schema_version: str = NESTED_FEATURE_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_kind", NestedFeatureKind(self.feature_kind))
        object.__setattr__(self, "status", NestedFeatureStatus(self.status))
        object.__setattr__(self, "geometry_stock_mm", dict(self.geometry_stock_mm or {}))
        object.__setattr__(self, "conflict_zone_ids", tuple(dict.fromkeys(self.conflict_zone_ids)))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        for label, value in (
            ("feature_id", self.feature_id),
            ("source_feature_id", self.source_feature_id),
            ("source_intent_sha256", self.source_intent_sha256),
            ("part_id", self.part_id),
            ("production_instance_id", self.production_instance_id),
            ("stock_id", self.stock_id),
            ("face_id", self.face_id),
        ):
            if not str(value).strip():
                raise ValueError(f"NestedManufacturingFeature mist {label}")
        if self.status == NestedFeatureStatus.BOUND and not self.machine_decision_sha256.strip():
            raise ValueError("Gebonden NestedManufacturingFeature vereist machine decision bewijs")
        expected = stable_sha256(self.identity_payload())
        if self.feature_sha256 and self.feature_sha256 != expected:
            raise ValueError("NestedManufacturingFeature feature_sha256 klopt niet")
        object.__setattr__(self, "feature_sha256", expected)

    @property
    def production_usable(self) -> bool:
        return (
            self.status == NestedFeatureStatus.BOUND
            and bool(self.machine_decision_sha256.strip())
            and not self.blocking_codes
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "feature_id": self.feature_id,
            "source_feature_id": self.source_feature_id,
            "source_intent_sha256": self.source_intent_sha256,
            "feature_kind": self.feature_kind.value,
            "part_id": self.part_id,
            "production_instance_id": self.production_instance_id,
            "stock_id": self.stock_id,
            "face_id": self.face_id,
            "geometry_stock_mm": dict(self.geometry_stock_mm),
            "machine_decision_sha256": self.machine_decision_sha256,
            "status": self.status.value,
            "conflict_zone_ids": list(self.conflict_zone_ids),
            "warnings": list(self.warnings),
            "blocking_codes": list(self.blocking_codes),
        }

    def to_dict(self) -> dict[str, Any]:
        result = self.identity_payload()
        result["feature_sha256"] = self.feature_sha256
        result["production_usable"] = self.production_usable
        return result


@dataclass(frozen=True, slots=True)
class NestingMarkingReport:
    part_id: str
    manufacturing_hash: str
    production_instance_id: str
    assembly_id: str
    assembly_mark: str
    nesting_run_id: str
    stock_id: str
    placement_sha256: str
    face_report_sha256: str
    mark_set_sha256: str
    identification_set_sha256: str
    machine_capability_sha256: str
    clamp_zone_sha256s: tuple[str, ...]
    common_cut_zone_sha256s: tuple[str, ...]
    features: tuple[NestedManufacturingFeature, ...]
    blocking_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    instance_variant_sha256: str = ""
    report_sha256: str = ""
    schema_version: str = NESTING_MARKING_SCHEMA
    algorithm_version: str = NESTING_BINDING_ALGORITHM

    def __post_init__(self) -> None:
        object.__setattr__(self, "clamp_zone_sha256s", tuple(self.clamp_zone_sha256s))
        object.__setattr__(self, "common_cut_zone_sha256s", tuple(self.common_cut_zone_sha256s))
        object.__setattr__(self, "features", tuple(self.features))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        object.__setattr__(self, "warnings", tuple(dict.fromkeys(str(item) for item in self.warnings)))
        for label, value in (
            ("part_id", self.part_id),
            ("manufacturing_hash", self.manufacturing_hash),
            ("production_instance_id", self.production_instance_id),
            ("nesting_run_id", self.nesting_run_id),
            ("stock_id", self.stock_id),
            ("placement_sha256", self.placement_sha256),
            ("face_report_sha256", self.face_report_sha256),
            ("machine_capability_sha256", self.machine_capability_sha256),
        ):
            if not str(value).strip():
                raise ValueError(f"NestingMarkingReport mist {label}")
        variant = stable_sha256(self.variant_payload())
        if self.instance_variant_sha256 and self.instance_variant_sha256 != variant:
            raise ValueError("NestingMarkingReport instance_variant_sha256 klopt niet")
        object.__setattr__(self, "instance_variant_sha256", variant)
        expected = self.calculate_hash()
        if self.report_sha256 and self.report_sha256 != expected:
            raise ValueError("NestingMarkingReport report_sha256 klopt niet")

    def variant_payload(self) -> dict[str, Any]:
        return {
            "part_id": self.part_id,
            "manufacturing_hash": self.manufacturing_hash,
            "production_instance_id": self.production_instance_id,
            "assembly_id": self.assembly_id,
            "assembly_mark": self.assembly_mark,
            "placement_sha256": self.placement_sha256,
            "mark_set_sha256": self.mark_set_sha256,
            "identification_set_sha256": self.identification_set_sha256,
            "machine_capability_sha256": self.machine_capability_sha256,
        }

    @property
    def nesting_bound(self) -> bool:
        return not self.blocking_codes and all(item.production_usable for item in self.features)

    @property
    def ready_for_neutral_job(self) -> bool:
        return self.nesting_bound

    @property
    def machine_transfer_allowed(self) -> bool:
        return False

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "algorithm_version": self.algorithm_version,
            **self.variant_payload(),
            "instance_variant_sha256": self.instance_variant_sha256,
            "nesting_run_id": self.nesting_run_id,
            "stock_id": self.stock_id,
            "face_report_sha256": self.face_report_sha256,
            "clamp_zone_sha256s": list(self.clamp_zone_sha256s),
            "common_cut_zone_sha256s": list(self.common_cut_zone_sha256s),
            "features": [item.to_dict() for item in self.features],
            "blocking_codes": list(self.blocking_codes),
            "warnings": list(self.warnings),
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "NestingMarkingReport":
        result = cls(report_sha256="", **kwargs)
        return cls(**kwargs, report_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        result = self.payload_dict()
        result.update(
            {
                "report_sha256": self.report_sha256,
                "nesting_bound": self.nesting_bound,
                "ready_for_neutral_job": self.ready_for_neutral_job,
                "machine_transfer_allowed": self.machine_transfer_allowed,
            }
        )
        return result


__all__ = [
    "NESTING_PLACEMENT_SCHEMA", "NESTED_FEATURE_SCHEMA", "NESTING_MARKING_SCHEMA",
    "NESTING_BINDING_ALGORITHM", "NestedFeatureStatus", "NestedFeatureKind",
    "NestingPlacement", "StockClampZone", "CommonCutZone",
    "NestedManufacturingFeature", "NestingMarkingReport",
]
