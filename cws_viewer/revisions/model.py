"""Revision, correspondence and impact contracts for CWS Viewer V7.

The contracts are renderer-neutral and deliberately separate display review from
production decisions.  They can describe source/canonical, revision/revision and
canonical/roundtrip comparisons without turning display geometry into a new
manufacturing truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Mapping

from cws_viewer.core.serialization import stable_sha256
from cws_viewer.math3d import Vector3


class CompareRelation(StrEnum):
    SOURCE_CANONICAL = "source_canonical"
    REVISION = "revision"
    ROUNDTRIP = "roundtrip"


class ChangeKind(StrEnum):
    UNCHANGED = "unchanged"
    ADDED = "added"
    REMOVED = "removed"
    MOVED = "moved"
    CHANGED = "changed"
    AMBIGUOUS = "ambiguous"


class CorrespondenceMethod(StrEnum):
    STABLE_ID = "stable_id"
    SOURCE_IDENTITY = "source_identity"
    MANUFACTURING_HASH = "manufacturing_hash"
    GEOMETRY_HASH = "geometry_hash"
    SIGNATURE = "signature"
    GEOMETRIC = "geometric"
    SEMANTIC = "semantic"
    UNMATCHED = "unmatched"
    AMBIGUOUS = "ambiguous"


class ImpactKind(StrEnum):
    PLACEMENT = "placement"
    GEOMETRY = "geometry"
    MATERIAL = "material"
    PROFILE = "profile"
    FEATURE = "feature"
    MIRROR = "mirror"
    REFERENCE = "reference_side"
    TOLERANCE = "tolerance"
    COATING = "coating"
    QUANTITY = "quantity"
    CLASSIFICATION = "classification"
    ASSEMBLY_RELATION = "assembly_relation"
    SOURCE_IDENTITY = "source_identity"
    OTHER_MANUFACTURING = "other_manufacturing"


class ArtifactAction(StrEnum):
    KEEP = "keep"
    REVIEW = "review"
    INVALIDATE = "invalidate"
    REMOVE_REFERENCE = "remove_reference"


class CorrespondenceStatus(StrEnum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    UNMATCHED = "unmatched"


@dataclass(frozen=True, slots=True)
class SubshapeCorrespondence:
    source_id: str | None
    target_id: str | None
    kind: str
    status: CorrespondenceStatus
    method: CorrespondenceMethod
    confidence: float
    score: float
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", CorrespondenceStatus(self.status))
        object.__setattr__(self, "method", CorrespondenceMethod(self.method))
        object.__setattr__(self, "reasons", tuple(str(item) for item in self.reasons))
        for label, value in (("confidence", self.confidence), ("score", self.score)):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{label} moet tussen 0 en 1 liggen")
        if self.status == CorrespondenceStatus.MATCHED and (not self.source_id or not self.target_id):
            raise ValueError("Matched correspondence vereist source_id en target_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "kind": self.kind,
            "status": self.status.value,
            "method": self.method.value,
            "confidence": self.confidence,
            "score": self.score,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class CorrespondenceReport:
    relation: CompareRelation
    source_geometry_hash: str
    target_geometry_hash: str
    subshapes: tuple[SubshapeCorrespondence, ...]
    features: tuple[SubshapeCorrespondence, ...]
    blocking_codes: tuple[str, ...] = ()
    schema_version: str = "cws-correspondence-1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "relation", CompareRelation(self.relation))
        object.__setattr__(self, "subshapes", tuple(self.subshapes))
        object.__setattr__(self, "features", tuple(self.features))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(self.blocking_codes)))

    @property
    def matched_count(self) -> int:
        return sum(item.status == CorrespondenceStatus.MATCHED for item in (*self.subshapes, *self.features))

    @property
    def ambiguous_count(self) -> int:
        return sum(item.status == CorrespondenceStatus.AMBIGUOUS for item in (*self.subshapes, *self.features))

    @property
    def unmatched_count(self) -> int:
        return sum(item.status == CorrespondenceStatus.UNMATCHED for item in (*self.subshapes, *self.features))

    @property
    def production_safe(self) -> bool:
        return not self.blocking_codes and self.ambiguous_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "relation": self.relation.value,
            "source_geometry_hash": self.source_geometry_hash,
            "target_geometry_hash": self.target_geometry_hash,
            "subshapes": [item.to_dict() for item in self.subshapes],
            "features": [item.to_dict() for item in self.features],
            "summary": {
                "matched": self.matched_count,
                "ambiguous": self.ambiguous_count,
                "unmatched": self.unmatched_count,
                "production_safe": self.production_safe,
            },
            "blocking_codes": list(self.blocking_codes),
        }


@dataclass(frozen=True, slots=True)
class PlacementDelta:
    translation_mm: Vector3
    translation_distance_mm: float
    rotation_delta_deg: float
    matrix_max_delta: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "translation_mm": self.translation_mm.to_tuple(),
            "translation_distance_mm": self.translation_distance_mm,
            "rotation_delta_deg": self.rotation_delta_deg,
            "matrix_max_delta": self.matrix_max_delta,
        }


@dataclass(frozen=True, slots=True)
class RevisionObjectChange:
    change_id: str
    kind: ChangeKind
    old_entity_id: str | None
    new_entity_id: str | None
    old_source_id: str | None
    new_source_id: str | None
    correspondence_method: CorrespondenceMethod
    confidence: float
    impacts: tuple[ImpactKind, ...]
    old_geometry_hash: str = ""
    new_geometry_hash: str = ""
    old_manufacturing_hash: str = ""
    new_manufacturing_hash: str = ""
    placement_delta: PlacementDelta | None = None
    reasons: tuple[str, ...] = ()
    blocking_codes: tuple[str, ...] = ()
    old_part_position: str = ""
    new_part_position: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", ChangeKind(self.kind))
        object.__setattr__(self, "correspondence_method", CorrespondenceMethod(self.correspondence_method))
        object.__setattr__(self, "impacts", tuple(ImpactKind(item) for item in self.impacts))
        object.__setattr__(self, "reasons", tuple(str(item) for item in self.reasons))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(self.blocking_codes)))
        if not self.change_id.strip():
            raise ValueError("change_id ontbreekt")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence moet tussen 0 en 1 liggen")

    @property
    def placement_only(self) -> bool:
        return self.kind == ChangeKind.MOVED and set(self.impacts) <= {ImpactKind.PLACEMENT}

    @property
    def manufacturing_changed(self) -> bool:
        return any(item not in {ImpactKind.PLACEMENT, ImpactKind.QUANTITY, ImpactKind.ASSEMBLY_RELATION} for item in self.impacts)

    @property
    def planning_changed(self) -> bool:
        """Return whether non-geometric planning/BOM data changed.

        Quantity and assembly-membership changes deliberately do not alter the
        manufacturing identity of a single part.  They *do* invalidate or put
        under review derived planning evidence such as assembly drawings,
        BOMs, optimization results, production orders and queued machine jobs.
        Keeping this signal separate prevents needless destruction of proven
        NC1/STEP/IFC part artefacts while still closing the downstream safety
        gates.
        """

        return any(item in {ImpactKind.QUANTITY, ImpactKind.ASSEMBLY_RELATION} for item in self.impacts)

    @property
    def production_reuse_allowed(self) -> bool:
        return (
            self.kind not in {ChangeKind.ADDED, ChangeKind.REMOVED, ChangeKind.AMBIGUOUS}
            and self.old_entity_id is not None
            and self.new_entity_id is not None
            and not self.manufacturing_changed
            and not self.blocking_codes
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_id": self.change_id,
            "kind": self.kind.value,
            "old_entity_id": self.old_entity_id,
            "new_entity_id": self.new_entity_id,
            "old_source_id": self.old_source_id,
            "new_source_id": self.new_source_id,
            "old_part_position": self.old_part_position,
            "new_part_position": self.new_part_position,
            "correspondence_method": self.correspondence_method.value,
            "confidence": self.confidence,
            "impacts": [item.value for item in self.impacts],
            "old_geometry_hash": self.old_geometry_hash,
            "new_geometry_hash": self.new_geometry_hash,
            "old_manufacturing_hash": self.old_manufacturing_hash,
            "new_manufacturing_hash": self.new_manufacturing_hash,
            "placement_delta": None if self.placement_delta is None else self.placement_delta.to_dict(),
            "reasons": list(self.reasons),
            "blocking_codes": list(self.blocking_codes),
            "placement_only": self.placement_only,
            "manufacturing_changed": self.manufacturing_changed,
            "planning_changed": self.planning_changed,
            "production_reuse_allowed": self.production_reuse_allowed,
        }


@dataclass(frozen=True, slots=True)
class ProjectRevisionCompareReport:
    project_id: str
    old_revision_id: str
    new_revision_id: str
    changes: tuple[RevisionObjectChange, ...]
    relation: CompareRelation = CompareRelation.REVISION
    blocking_codes: tuple[str, ...] = ()
    schema_version: str = "cws-project-revision-compare-1.0"
    manifest_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "relation", CompareRelation(self.relation))
        object.__setattr__(self, "changes", tuple(self.changes))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(self.blocking_codes)))
        if not self.project_id.strip():
            raise ValueError("project_id ontbreekt")
        if self.manifest_sha256:
            expected = self.calculate_hash()
            if self.manifest_sha256 != expected:
                raise ValueError("Revision compare manifest hash klopt niet")

    @classmethod
    def create(cls, **kwargs: Any) -> "ProjectRevisionCompareReport":
        result = cls(manifest_sha256="", **kwargs)
        return cls(**{**kwargs, "manifest_sha256": result.calculate_hash()})

    @property
    def counts(self) -> Mapping[str, int]:
        return {kind.value: sum(item.kind == kind for item in self.changes) for kind in ChangeKind}

    @property
    def production_safe(self) -> bool:
        return not self.blocking_codes and not any(item.kind == ChangeKind.AMBIGUOUS for item in self.changes)

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "old_revision_id": self.old_revision_id,
            "new_revision_id": self.new_revision_id,
            "relation": self.relation.value,
            "changes": [item.to_dict() for item in self.changes],
            "counts": dict(self.counts),
            "blocking_codes": list(self.blocking_codes),
            "production_safe": self.production_safe,
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_dict()
        payload["manifest_sha256"] = self.manifest_sha256
        return payload


@dataclass(frozen=True, slots=True)
class DeviationSample:
    point: Vector3
    distance_mm: float
    normalized: float
    source: str
    subshape_id: str = ""

    def __post_init__(self) -> None:
        if self.distance_mm < 0:
            raise ValueError("Deviation distance mag niet negatief zijn")
        if not 0.0 <= self.normalized <= 1.0:
            raise ValueError("Deviation normalized moet 0..1 zijn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "point": self.point.to_tuple(),
            "distance_mm": self.distance_mm,
            "normalized": self.normalized,
            "source": self.source,
            "subshape_id": self.subshape_id,
        }


@dataclass(frozen=True, slots=True)
class DeviationField:
    source_hash: str
    target_hash: str
    tolerance_mm: float
    maximum_mm: float
    p95_mm: float
    mean_mm: float
    samples: tuple[DeviationSample, ...]
    schema_version: str = "cws-deviation-field-1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "samples", tuple(self.samples))
        if self.tolerance_mm <= 0:
            raise ValueError("Deviation tolerance moet positief zijn")

    @property
    def passed(self) -> bool:
        return self.maximum_mm <= self.tolerance_mm

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_hash": self.source_hash,
            "target_hash": self.target_hash,
            "tolerance_mm": self.tolerance_mm,
            "maximum_mm": self.maximum_mm,
            "p95_mm": self.p95_mm,
            "mean_mm": self.mean_mm,
            "passed": self.passed,
            "samples": [item.to_dict() for item in self.samples],
        }


@dataclass(frozen=True, slots=True)
class ArtifactInvalidationRecord:
    entity_id: str
    artifact_type: str
    action: ArtifactAction
    reason_codes: tuple[str, ...]
    previous_hash: str = ""
    new_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", ArtifactAction(self.action))
        object.__setattr__(self, "reason_codes", tuple(dict.fromkeys(self.reason_codes)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "artifact_type": self.artifact_type,
            "action": self.action.value,
            "reason_codes": list(self.reason_codes),
            "previous_hash": self.previous_hash,
            "new_hash": self.new_hash,
        }


@dataclass(frozen=True, slots=True)
class RevisionImpactPlan:
    project_id: str
    old_revision_id: str
    new_revision_id: str
    records: tuple[ArtifactInvalidationRecord, ...]
    changed_part_ids: tuple[str, ...]
    planning_changed_part_ids: tuple[str, ...]
    placement_only_part_ids: tuple[str, ...]
    blocked_machine_job_ids: tuple[str, ...]
    review_machine_job_ids: tuple[str, ...]
    invalidated_assembly_ids: tuple[str, ...]
    invalidated_optimization_ids: tuple[str, ...] = ()
    invalidated_scribing_review_ids: tuple[str, ...] = ()
    invalidated_production_order_ids: tuple[str, ...] = ()
    schema_version: str = "cws-revision-impact-1.2"

    def __post_init__(self) -> None:
        for name in (
            "records",
            "changed_part_ids",
            "planning_changed_part_ids",
            "placement_only_part_ids",
            "blocked_machine_job_ids",
            "review_machine_job_ids",
            "invalidated_assembly_ids",
            "invalidated_optimization_ids",
            "invalidated_scribing_review_ids",
            "invalidated_production_order_ids",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "old_revision_id": self.old_revision_id,
            "new_revision_id": self.new_revision_id,
            "records": [item.to_dict() for item in self.records],
            "changed_part_ids": list(self.changed_part_ids),
            "planning_changed_part_ids": list(self.planning_changed_part_ids),
            "placement_only_part_ids": list(self.placement_only_part_ids),
            "blocked_machine_job_ids": list(self.blocked_machine_job_ids),
            "review_machine_job_ids": list(self.review_machine_job_ids),
            "invalidated_assembly_ids": list(self.invalidated_assembly_ids),
            "invalidated_optimization_ids": list(self.invalidated_optimization_ids),
            "invalidated_scribing_review_ids": list(self.invalidated_scribing_review_ids),
            "invalidated_production_order_ids": list(self.invalidated_production_order_ids),
        }


@dataclass(frozen=True, slots=True)
class RevisionStateReconciliation:
    old_revision_id: str
    new_revision_id: str
    preserved_viewpoint_ids: tuple[str, ...]
    review_viewpoint_ids: tuple[str, ...]
    invalidated_measurement_ids: tuple[str, ...]
    preserved_measurement_ids: tuple[str, ...]
    invalidated_review_ids: tuple[str, ...]
    blocking_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "preserved_viewpoint_ids",
            "review_viewpoint_ids",
            "invalidated_measurement_ids",
            "preserved_measurement_ids",
            "invalidated_review_ids",
            "blocking_codes",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "old_revision_id": self.old_revision_id,
            "new_revision_id": self.new_revision_id,
            "preserved_viewpoint_ids": list(self.preserved_viewpoint_ids),
            "review_viewpoint_ids": list(self.review_viewpoint_ids),
            "invalidated_measurement_ids": list(self.invalidated_measurement_ids),
            "preserved_measurement_ids": list(self.preserved_measurement_ids),
            "invalidated_review_ids": list(self.invalidated_review_ids),
            "blocking_codes": list(self.blocking_codes),
        }


__all__ = [
    "CompareRelation",
    "ChangeKind",
    "CorrespondenceMethod",
    "ImpactKind",
    "ArtifactAction",
    "CorrespondenceStatus",
    "SubshapeCorrespondence",
    "CorrespondenceReport",
    "PlacementDelta",
    "RevisionObjectChange",
    "ProjectRevisionCompareReport",
    "DeviationSample",
    "DeviationField",
    "ArtifactInvalidationRecord",
    "RevisionImpactPlan",
    "RevisionStateReconciliation",
]
