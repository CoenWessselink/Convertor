from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
import hashlib
import json
from typing import Any


ENGINE_VERSION = "mgi-v3"
ALGORITHM_VERSIONS = (
    ("topology", "mgi-topology-v3"),
    ("axis", "mgi-axis-v3"),
    ("section", "mgi-section-v3"),
    ("profile", "mgi-profile-v3"),
    ("feature", "mgi-feature-v3"),
    ("solver", "mgi-solver-v3"),
    ("proof", "mgi-proof-v3"),
)


class SurfaceType(str, Enum):
    PLANE = "PLANE"
    CYLINDER = "CYLINDER"
    CONE = "CONE"
    SPHERE = "SPHERE"
    TORUS = "TORUS"
    BSPLINE = "BSPLINE"
    BEZIER = "BEZIER"
    SURFACE_OF_EXTRUSION = "SURFACE_OF_EXTRUSION"
    SURFACE_OF_REVOLUTION = "SURFACE_OF_REVOLUTION"
    OTHER = "OTHER"


class GeometricFeatureType(str, Enum):
    CYLINDRICAL_SUBTRACTION = "CYLINDRICAL_SUBTRACTION"
    OBROUND_SUBTRACTION = "OBROUND_SUBTRACTION"
    PRISMATIC_SUBTRACTION = "PRISMATIC_SUBTRACTION"
    PLANAR_HALFSPACE_CUT = "PLANAR_HALFSPACE_CUT"
    POSITIVE_PRISM = "POSITIVE_PRISM"
    NEGATIVE_PRISM = "NEGATIVE_PRISM"
    REVOLVED_VOLUME = "REVOLVED_VOLUME"
    CUSTOM_BOOLEAN = "CUSTOM_BOOLEAN"
    UNKNOWN_GEOMETRIC_FEATURE = "UNKNOWN_GEOMETRIC_FEATURE"


class ManufacturingSemanticType(str, Enum):
    HOLE = "HOLE"
    COUNTERSINK = "COUNTERSINK"
    COUNTERBORE = "COUNTERBORE"
    SLOT = "SLOT"
    COPE = "COPE"
    NOTCH = "NOTCH"
    END_CUT = "END_CUT"
    MITER_CUT = "MITER_CUT"
    POCKET = "POCKET"
    FLANGE_REMOVAL = "FLANGE_REMOVAL"
    WEB_REMOVAL = "WEB_REMOVAL"
    BOSS = "BOSS"
    RIB = "RIB"
    ATTACHMENT_VOLUME = "ATTACHMENT_VOLUME"
    CUSTOM_FEATURE = "CUSTOM_FEATURE"
    UNKNOWN = "UNKNOWN"


class RepresentabilityStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    SUPPORTED_WITH_LIMITS = "SUPPORTED_WITH_LIMITS"
    REVIEW = "REVIEW"
    UNSUPPORTED = "UNSUPPORTED"
    NOT_EVALUATED = "NOT_EVALUATED"


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
    curve_parameters: tuple[tuple[str, float], ...] = ()
    orientation: str = "FORWARD"
    source_geometry_hash: str = ""
    algorithm_version: str = "mgi-topology-v3"


@dataclass(frozen=True)
class FaceEvidence:
    face_id: str
    surface_type: str
    area_mm2: float
    centroid_mm: tuple[float, float, float]
    normal: tuple[float, float, float]
    boundary_edge_ids: tuple[str, ...]
    inner_wire_count: int
    analytic_parameters: tuple[tuple[str, str], ...] = ()
    outer_wire_signature: str = ""
    inner_wire_signatures: tuple[str, ...] = ()
    orientation: str = "FORWARD"
    curvature_class: str = "UNKNOWN"
    adjacency_signature: str = ""
    source_geometry_hash: str = ""
    algorithm_version: str = "mgi-topology-v3"


@dataclass(frozen=True)
class SourceTopologyEvidence:
    topology_id: str
    solid_count: int
    faces: tuple[FaceEvidence, ...]
    edges: tuple[EdgeEvidence, ...]
    face_adjacency: tuple[tuple[str, str, str], ...]
    analytic_groups: tuple["AnalyticFaceGroup", ...] = ()


@dataclass(frozen=True)
class AxisCandidate:
    axis_id: str
    direction: tuple[float, float, float]
    origin_mm: tuple[float, float, float]
    end_mm: tuple[float, float, float]
    length_mm: float
    support: str
    score: float
    signal_scores: tuple[tuple[str, float], ...] = ()
    supporting_face_ids: tuple[str, ...] = ()
    supporting_edge_ids: tuple[str, ...] = ()


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
    residual_component_count: int = 0
    boundary_distance_p50_mm: float = 0.0
    boundary_distance_p95_mm: float = 0.0
    boundary_distance_max_mm: float = 0.0
    boolean_kernel_status: str = "NOT_RUN"


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
    manufacturing_frame: "ManufacturingFrame | None" = None
    section_stations: tuple["SectionStation", ...] = ()
    section_intervals: tuple["SectionInterval", ...] = ()
    extrusion_regions: tuple["ExtrusionRegionCandidate", ...] = ()
    features: tuple["RecognizedGeometricFeature", ...] = ()
    feature_graph: "FeatureGraph | None" = None
    hypotheses: tuple["DecompositionHypothesis", ...] = ()
    residual_report: "ResidualGeometryReport | None" = None
    representability_report: "RepresentabilityReport | None" = None
    algorithm_versions: tuple[tuple[str, str], ...] = ALGORITHM_VERSIONS
    tolerance_policy_id: str = ""
    tolerance_policy_version: str = ""
    tolerance_policy_hash: str = ""
    profile_database_hash: str = ""

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


def content_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class AnalyticFaceGroup:
    group_id: str
    surface_type: str
    member_face_ids: tuple[str, ...]
    analytic_parameters: tuple[tuple[str, str], ...] = ()
    boundary_signature: str = ""


@dataclass(frozen=True)
class ManufacturingFrame:
    frame_id: str
    origin_mm: tuple[float, float, float]
    x_axis: tuple[float, float, float]
    y_axis: tuple[float, float, float]
    z_axis: tuple[float, float, float]
    handedness: str = "RIGHT"
    evidence: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class SectionStation:
    station_id: str
    position_mm: float
    safe: bool
    signature: CrossSectionSignature
    contour_signature: str
    loop_count: int
    void_count: int
    centroid_2d_mm: tuple[float, float] = (0.0, 0.0)
    moments: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class SectionInterval:
    interval_id: str
    start_mm: float
    end_mm: float
    station_ids: tuple[str, ...]
    classification: str
    invariant: bool
    change_score: float = 0.0


@dataclass(frozen=True)
class ExtrusionRegionCandidate:
    region_id: str
    frame_id: str
    start_mm: float
    end_mm: float
    length_mm: float
    section_id: str
    supporting_face_ids: tuple[str, ...]
    source_coverage: float
    unexplained_positive_volume_mm3: float
    unexplained_negative_volume_mm3: float
    score: float


@dataclass(frozen=True)
class ProfileMatchCandidate:
    designation: str
    dimension_residual_mm: float
    area_residual_mm2: float
    perimeter_residual_mm: float
    moment_residual: float
    radius_residual_mm: float
    contour_distance_mm: float
    topology_match: bool
    score: float


@dataclass(frozen=True)
class RecognizedGeometricFeature:
    feature_id: str
    geometric_type: GeometricFeatureType
    semantic_type: ManufacturingSemanticType
    parameters: tuple[tuple[str, Any], ...]
    source_support: tuple[str, ...]
    residual_component_ids: tuple[str, ...]
    confidence_score: float
    proof_status: GeometryProofStatus
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeatureDependency:
    feature_id: str
    depends_on: tuple[str, ...] = ()
    overlaps: tuple[str, ...] = ()
    invalidates: tuple[str, ...] = ()
    consumes_regions: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeatureGraph:
    graph_id: str
    feature_ids: tuple[str, ...]
    dependencies: tuple[FeatureDependency, ...]
    duplicate_attribution_count: int = 0


@dataclass(frozen=True)
class HypothesisScoreBreakdown:
    geometry_proof: float
    residual: float
    boundary_distance: float
    profile_proof: float
    feature_evidence: float
    source_coverage: float
    manufacturing_plausibility: float
    complexity_penalty: float
    unknown_penalty: float
    representability: float
    ambiguity_penalty: float
    total: float


@dataclass(frozen=True)
class DecompositionHypothesis:
    hypothesis_id: str
    base_region_ids: tuple[str, ...]
    positive_feature_ids: tuple[str, ...]
    negative_feature_ids: tuple[str, ...]
    feature_graph_id: str
    unknown_region_ids: tuple[str, ...]
    score: HypothesisScoreBreakdown
    proof_status: GeometryProofStatus
    runtime_cost_seconds: float


@dataclass(frozen=True)
class ResidualComponent:
    component_id: str
    direction: str
    volume_mm3: float
    bbox_mm: tuple[float, float, float, float, float, float]
    centroid_mm: tuple[float, float, float]
    classification: str = "UNKNOWN"


@dataclass(frozen=True)
class ResidualGeometryReport:
    report_id: str
    source_minus_reconstruction_status: str
    reconstruction_minus_source_status: str
    source_minus_reconstruction_mm3: float
    reconstruction_minus_source_mm3: float
    components: tuple[ResidualComponent, ...]
    boundary_distance_p50_mm: float
    boundary_distance_p95_mm: float
    boundary_distance_max_mm: float
    boolean_kernel_status: str
    unmatched_source_regions: tuple[str, ...] = ()
    overbuilt_regions: tuple[str, ...] = ()


@dataclass(frozen=True)
class TargetRepresentability:
    target: str
    status: RepresentabilityStatus
    supported_features: tuple[str, ...] = ()
    unsupported_features: tuple[str, ...] = ()
    lossless: bool = False
    roundtrip_available: bool = False
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepresentabilityReport:
    report_id: str
    targets: tuple[TargetRepresentability, ...]


@dataclass(frozen=True)
class InterpretationConfirmation:
    confirmation_id: str
    report_hash: str
    hypothesis_id: str
    user: str
    semantic_overrides: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class WorkbenchPromotionResult:
    status: str
    report_hash: str
    hypothesis_id: str
    revision_hash: str = ""
    rolled_back: bool = False
    blockers: tuple[str, ...] = ()
