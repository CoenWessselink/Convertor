"""Exact Part Workbench contracts.

The objects in this module describe exact BREP evidence and user-reviewed
manufacturing interpretation.  Renderer-specific objects are intentionally not
stored in the persistent contracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from cws_viewer.math3d import BoundingBox, Vector3


class SubshapeKind(StrEnum):
    SOLID = "solid"
    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"


class ExactnessLevel(StrEnum):
    SOURCE_BREP = "source_brep"
    CANONICAL_BREP = "canonical_brep"
    ANALYTICAL_FEATURE = "analytical_feature"
    VERIFIED_MESH = "verified_mesh"
    DISPLAY_PROXY = "display_proxy"


class WorkbenchStatus(StrEnum):
    BLOCKED = "blocked"
    REVIEW_REQUIRED = "review_required"
    GEOMETRY_VALIDATED = "geometry_validated"
    ROUNDTRIP_VALIDATED = "roundtrip_validated"
    RELEASED = "released"


class CompareSeverity(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class ExactShapeProperties:
    volume_mm3: float
    surface_area_mm2: float
    center_of_mass: Vector3
    bounds: BoundingBox
    solid_count: int
    face_count: int
    edge_count: int
    vertex_count: int
    valid: bool

    @property
    def principal_dimensions(self) -> tuple[float, float, float]:
        size = self.bounds.size
        return tuple(sorted((size.x, size.y, size.z), reverse=True))

    def to_dict(self) -> dict[str, Any]:
        return {
            "volume_mm3": self.volume_mm3,
            "surface_area_mm2": self.surface_area_mm2,
            "center_of_mass": self.center_of_mass.to_tuple(),
            "bounds": {
                "minimum": self.bounds.minimum.to_tuple(),
                "maximum": self.bounds.maximum.to_tuple(),
                "size": self.bounds.size.to_tuple(),
            },
            "solid_count": self.solid_count,
            "face_count": self.face_count,
            "edge_count": self.edge_count,
            "vertex_count": self.vertex_count,
            "valid": self.valid,
        }


@dataclass(frozen=True, slots=True)
class SubshapeDescriptor:
    stable_id: str
    kind: SubshapeKind
    geometry_type: str
    signature_hash: str
    center: Vector3
    bounds: BoundingBox
    measure: float
    ordinal: int = 0
    normal: Vector3 | None = None
    direction: Vector3 | None = None
    start: Vector3 | None = None
    end: Vector3 | None = None
    radius: float | None = None
    axis_origin: Vector3 | None = None
    axis_direction: Vector3 | None = None
    parent_ids: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", SubshapeKind(self.kind))
        object.__setattr__(self, "parent_ids", tuple(self.parent_ids))
        object.__setattr__(self, "metadata", tuple((str(k), str(v)) for k, v in self.metadata))

    @property
    def metadata_dict(self) -> Mapping[str, str]:
        return dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        def vec(value: Vector3 | None):
            return None if value is None else value.to_tuple()

        return {
            "stable_id": self.stable_id,
            "kind": self.kind.value,
            "geometry_type": self.geometry_type,
            "signature_hash": self.signature_hash,
            "center": vec(self.center),
            "bounds": {"minimum": vec(self.bounds.minimum), "maximum": vec(self.bounds.maximum)},
            "measure": self.measure,
            "ordinal": self.ordinal,
            "normal": vec(self.normal),
            "direction": vec(self.direction),
            "start": vec(self.start),
            "end": vec(self.end),
            "radius": self.radius,
            "axis_origin": vec(self.axis_origin),
            "axis_direction": vec(self.axis_direction),
            "parent_ids": list(self.parent_ids),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class FeatureDescriptor:
    feature_id: str
    feature_type: str
    subshape_ids: tuple[str, ...]
    center: Vector3
    evidence: ExactnessLevel
    axis: Vector3 | None = None
    radius: float | None = None
    diameter: float | None = None
    depth: float | None = None
    side: str = ""
    confidence: float = 1.0
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "subshape_ids", tuple(self.subshape_ids))
        object.__setattr__(self, "evidence", ExactnessLevel(self.evidence))
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("Feature confidence moet tussen 0 en 1 liggen")

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "feature_type": self.feature_type,
            "subshape_ids": list(self.subshape_ids),
            "center": self.center.to_tuple(),
            "evidence": self.evidence.value,
            "axis": None if self.axis is None else self.axis.to_tuple(),
            "radius": self.radius,
            "diameter": self.diameter,
            "depth": self.depth,
            "side": self.side,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ProductionFrame:
    origin: Vector3
    x_axis: Vector3
    y_axis: Vector3
    z_axis: Vector3
    source: str = "automatic"
    confirmed: bool = False

    def __post_init__(self) -> None:
        x = self.x_axis.normalized()
        y = self.y_axis.normalized()
        z = self.z_axis.normalized()
        if abs(x.dot(y)) > 1e-7 or abs(x.dot(z)) > 1e-7 or abs(y.dot(z)) > 1e-7:
            raise ValueError("Production frame assen moeten orthogonaal zijn")
        handed = x.cross(y).dot(z)
        if handed < 0.999999:
            raise ValueError("Production frame moet rechterhandig zijn")
        object.__setattr__(self, "x_axis", x)
        object.__setattr__(self, "y_axis", y)
        object.__setattr__(self, "z_axis", z)

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin": self.origin.to_tuple(),
            "x_axis": self.x_axis.to_tuple(),
            "y_axis": self.y_axis.to_tuple(),
            "z_axis": self.z_axis.to_tuple(),
            "source": self.source,
            "confirmed": self.confirmed,
        }


@dataclass(frozen=True, slots=True)
class ReferenceFace:
    role: str
    face_id: str
    normal: Vector3
    confirmed: bool = False
    provenance: str = "automatic"
    reviewer: str = ""


@dataclass(frozen=True, slots=True)
class ExactPartSnapshot:
    part_id: str
    source_name: str
    source_sha256: str
    exact_geometry_hash: str
    properties: ExactShapeProperties
    subshapes: tuple[SubshapeDescriptor, ...]
    features: tuple[FeatureDescriptor, ...]
    production_frame: ProductionFrame
    reference_faces: tuple[ReferenceFace, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    status: WorkbenchStatus = WorkbenchStatus.REVIEW_REQUIRED
    schema_version: str = "cws-exact-part-1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "subshapes", tuple(self.subshapes))
        object.__setattr__(self, "features", tuple(self.features))
        object.__setattr__(self, "reference_faces", tuple(self.reference_faces))
        object.__setattr__(self, "unresolved_questions", tuple(self.unresolved_questions))
        object.__setattr__(self, "status", WorkbenchStatus(self.status))

    @property
    def subshape_by_id(self) -> Mapping[str, SubshapeDescriptor]:
        return {item.stable_id: item for item in self.subshapes}

    @property
    def feature_by_id(self) -> Mapping[str, FeatureDescriptor]:
        return {item.feature_id: item for item in self.features}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "part_id": self.part_id,
            "source_name": self.source_name,
            "source_sha256": self.source_sha256,
            "exact_geometry_hash": self.exact_geometry_hash,
            "properties": self.properties.to_dict(),
            "subshapes": [item.to_dict() for item in self.subshapes],
            "features": [item.to_dict() for item in self.features],
            "production_frame": self.production_frame.to_dict(),
            "reference_faces": [
                {
                    "role": item.role,
                    "face_id": item.face_id,
                    "normal": item.normal.to_tuple(),
                    "confirmed": item.confirmed,
                    "provenance": item.provenance,
                    "reviewer": item.reviewer,
                }
                for item in self.reference_faces
            ],
            "unresolved_questions": list(self.unresolved_questions),
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class ComparisonMetric:
    name: str
    source_value: float
    canonical_value: float
    absolute_delta: float
    relative_delta: float
    tolerance: float
    severity: CompareSeverity
    unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", CompareSeverity(self.severity))


@dataclass(frozen=True, slots=True)
class ExactComparisonReport:
    source_hash: str
    canonical_hash: str
    metrics: tuple[ComparisonMetric, ...]
    source_to_canonical_max_mm: float
    canonical_to_source_max_mm: float
    matched_features: int
    missing_features: tuple[str, ...]
    added_features: tuple[str, ...]
    overall: CompareSeverity
    blocking_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", tuple(self.metrics))
        object.__setattr__(self, "missing_features", tuple(self.missing_features))
        object.__setattr__(self, "added_features", tuple(self.added_features))
        object.__setattr__(self, "blocking_codes", tuple(self.blocking_codes))
        object.__setattr__(self, "overall", CompareSeverity(self.overall))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_hash": self.source_hash,
            "canonical_hash": self.canonical_hash,
            "metrics": [
                {
                    "name": item.name,
                    "source_value": item.source_value,
                    "canonical_value": item.canonical_value,
                    "absolute_delta": item.absolute_delta,
                    "relative_delta": item.relative_delta,
                    "tolerance": item.tolerance,
                    "severity": item.severity.value,
                    "unit": item.unit,
                }
                for item in self.metrics
            ],
            "source_to_canonical_max_mm": self.source_to_canonical_max_mm,
            "canonical_to_source_max_mm": self.canonical_to_source_max_mm,
            "matched_features": self.matched_features,
            "missing_features": list(self.missing_features),
            "added_features": list(self.added_features),
            "overall": self.overall.value,
            "blocking_codes": list(self.blocking_codes),
        }


@dataclass(slots=True)
class ExactPartRuntime:
    snapshot: ExactPartSnapshot
    shape: Any
    shape_by_subshape_id: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "SubshapeKind",
    "ExactnessLevel",
    "WorkbenchStatus",
    "CompareSeverity",
    "ExactShapeProperties",
    "SubshapeDescriptor",
    "FeatureDescriptor",
    "ProductionFrame",
    "ReferenceFace",
    "ExactPartSnapshot",
    "ComparisonMetric",
    "ExactComparisonReport",
    "ExactPartRuntime",
]
