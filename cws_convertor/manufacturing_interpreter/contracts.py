from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
import hashlib
import json
from typing import Any


ENGINE_VERSION = "mgi-v2-phase1"


class GeometryProofStatus(str, Enum):
    PROVEN_BREP_EQUIVALENT = "PROVEN_BREP_EQUIVALENT"
    PROVEN_WITHIN_POLICY = "PROVEN_WITHIN_POLICY"
    METRIC_ONLY = "METRIC_ONLY"
    PLAUSIBLE = "PLAUSIBLE"
    AMBIGUOUS = "AMBIGUOUS"
    FAILED = "FAILED"
    BLOCKED_SOURCE_NOT_EXACT = "BLOCKED_SOURCE_NOT_EXACT"
    RECOGNITION_INCOMPLETE = "RECOGNITION_INCOMPLETE"


class InterpretationReadiness(str, Enum):
    READY = "READY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, float):
        return round(value, 12)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _plain(value), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


def stable_id(namespace: str, value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{namespace}:{digest[:24]}"


@dataclass(frozen=True)
class EdgeEvidence:
    edge_id: str
    curve_type: str
    length_mm: float
    start_mm: tuple[float, float, float]
    end_mm: tuple[float, float, float]
    tangent: tuple[float, float, float]


@dataclass(frozen=True)
class FaceEvidence:
    face_id: str
    surface_type: str
    area_mm2: float
    centroid_mm: tuple[float, float, float]
    normal: tuple[float, float, float]
    boundary_edge_ids: tuple[str, ...]
    inner_wire_count: int


@dataclass(frozen=True)
class SourceTopologyEvidence:
    topology_id: str
    solid_count: int
    faces: tuple[FaceEvidence, ...]
    edges: tuple[EdgeEvidence, ...]
    face_adjacency: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True)
class AxisCandidate:
    axis_id: str
    direction: tuple[float, float, float]
    origin_mm: tuple[float, float, float]
    end_mm: tuple[float, float, float]
    length_mm: float
    support: str
    score: float


@dataclass(frozen=True)
class CrossSectionSignature:
    section_id: str
    face_id: str
    area_mm2: float
    perimeter_mm: float
    width_mm: float
    height_mm: float
    outer_edge_count: int
    inner_wire_count: int
    edge_type_counts: tuple[tuple[str, int], ...]
    inferred_family: str


@dataclass(frozen=True)
class ProfileRecognition:
    status: GeometryProofStatus
    designation: str = ""
    profile_type: str = ""
    family: str = ""
    confidence: float = 0.0
    dimension_delta_mm: float = 0.0
    area_delta_mm2: float = 0.0
    candidates: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class EquivalenceProof:
    status: GeometryProofStatus
    validator: str
    independent_reconstruction: bool
    two_way: bool
    source_volume_mm3: float
    reconstructed_volume_mm3: float
    source_minus_reconstruction_mm3: float
    reconstruction_minus_source_mm3: float
    volume_delta_mm3: float
    area_delta_mm2: float
    bbox_delta_mm: float
    centroid_delta_mm: float
    reason: str = ""


@dataclass(frozen=True)
class ManufacturingInterpretationRequest:
    inspection: Any
    preferred_profile: str = ""
    requested_outputs: tuple[str, ...] = ("STEP", "IFC", "NC1")


@dataclass(frozen=True)
class ManufacturingInterpretationReport:
    interpretation_id: str
    engine_version: str
    part_id: str
    source_file_id: str
    source_sha256: str
    source_geometry_hash: str
    source_gate: GeometryProofStatus
    topology: SourceTopologyEvidence | None
    axis_candidates: tuple[AxisCandidate, ...]
    selected_axis_id: str
    section: CrossSectionSignature | None
    profile: ProfileRecognition
    equivalence: EquivalenceProof
    representability: tuple[tuple[str, str], ...]
    readiness: InterpretationReadiness
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _plain(self)

    @property
    def semantic_sha256(self) -> str:
        return hashlib.sha256(canonical_json(self).encode("utf-8")).hexdigest()


def empty_proof(status: GeometryProofStatus, reason: str) -> EquivalenceProof:
    return EquivalenceProof(
        status=status,
        validator="independent-two-way-brep-residual-v1",
        independent_reconstruction=False,
        two_way=False,
        source_volume_mm3=0.0,
        reconstructed_volume_mm3=0.0,
        source_minus_reconstruction_mm3=0.0,
        reconstruction_minus_source_mm3=0.0,
        volume_delta_mm3=0.0,
        area_delta_mm2=0.0,
        bbox_delta_mm=0.0,
        centroid_delta_mm=0.0,
        reason=reason,
    )

