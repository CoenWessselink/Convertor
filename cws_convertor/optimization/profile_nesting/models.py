"""Versioned data contracts for SteelConverter profile nesting phases 1-7."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from cws_convertor.project.model import stable_sha256, utc_now_iso

PROFILE_NESTING_SCHEMA_VERSION = "1.4"


class NestingRunStatus(str, Enum):
    DRAFT = "draft"
    SOLVING = "solving"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    REVIEW = "review"
    ACCEPTED = "accepted"
    RELEASED = "released"
    STALE = "stale"
    CANCELLED = "cancelled"
    OBSOLETE = "obsolete"
    FAILED = "failed"


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    REVIEW = "review"
    BLOCKED = "blocked"


class CutStatus(str, Enum):
    EXACT = "exact"
    REVIEW = "review"
    UNSUPPORTED = "unsupported"


@dataclass
class NestingMessage:
    code: str
    severity: str
    message: str
    blocking: bool
    object_ids: list[str] = field(default_factory=list)
    technical_details: dict[str, Any] = field(default_factory=dict)
    probable_cause: str = ""
    suggested_action: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_by: str = ""


@dataclass
class CutRequirement:
    status: str = CutStatus.REVIEW.value
    plane: list[float] = field(default_factory=list)
    primary_angle_deg: float = 0.0
    secondary_angle_deg: float = 0.0
    reference: str = ""
    plane_reference_offset_mm: float = 0.0
    plane_convention: str = "local_xyz_unit_normal"
    face_mapping: dict[str, str] = field(default_factory=dict)
    long_point_mm: float | None = None
    short_point_mm: float | None = None
    tolerance_mm: float = 0.0
    finish_allowance_mm: float = 0.0
    common_cut_allowed: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)
    machine_constraints: dict[str, Any] = field(default_factory=dict)
    requirement_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("requirement_hash", None)
        self.requirement_hash = stable_sha256(payload)
        return self.requirement_hash


@dataclass
class OrientationVariant:
    variant_id: str
    transform: dict[str, Any]
    end_for_end: bool = False
    rotation_about_length_deg: float = 0.0
    face_mapping: dict[str, str] = field(default_factory=dict)
    start_cut: CutRequirement = field(default_factory=CutRequirement)
    end_cut: CutRequirement = field(default_factory=CutRequirement)
    reachable_features: list[str] = field(default_factory=list)
    compatible_machine_ids: list[str] = field(default_factory=list)
    production_equivalence: str = "review"
    equivalence_evidence: dict[str, Any] = field(default_factory=dict)
    mirrored: bool = False
    variant_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("variant_hash", None)
        self.variant_hash = stable_sha256(payload)
        return self.variant_hash


@dataclass
class CutTransition:
    transition_id: str
    left_instance_id: str
    right_instance_id: str
    left_variant_id: str
    right_variant_id: str
    machine_id: str
    geometry_delta_units: int = 0
    kerf_projection_units: int = 0
    extra_loss_units: int = 0
    required_reference_gap_units: int = 0
    physical_spacing_units: int = 0
    cut_count: int = 2
    common_cut: bool = False
    cut_angles_deg: list[list[float]] = field(default_factory=list)
    tool_change: bool = False
    estimated_time_seconds: float = 0.0
    estimated_cost_micros: int = 0
    proof_status: str = CutStatus.REVIEW.value
    proof: dict[str, Any] = field(default_factory=dict)
    transition_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("transition_hash", None)
        self.transition_hash = stable_sha256(payload)
        return self.transition_hash


@dataclass
class NestingDemandLine:
    demand_line_id: str
    group_key: str
    part_id: str
    part_position: str
    manufacturing_hash: str
    assembly_marks: list[str]
    profile_id: str
    profile_name: str
    section_hash: str
    profile_type: str
    profile_dimensions_mm: dict[str, float] = field(default_factory=dict)
    section_geometry: dict[str, Any] = field(default_factory=dict)
    material: str = ""
    material_grade: str = ""
    heat_requirement: str = ""
    certificate_requirement: str = ""
    nominal_length_mm: float = 0.0
    nominal_length_units: int = 0
    quantity: int = 1
    start_cut: CutRequirement = field(default_factory=CutRequirement)
    end_cut: CutRequirement = field(default_factory=CutRequirement)
    production_tolerance_mm: float = 0.0
    finish_allowance_mm: float = 0.0
    relevant_features: list[dict[str, Any]] = field(default_factory=list)
    allowed_orientations: list[str] = field(default_factory=lambda: ["as_modeled"])
    orientation_equivalence_evidence: dict[str, Any] = field(default_factory=dict)
    candidate_machine_ids: list[str] = field(default_factory=list)
    production_batch: str = ""
    priority: int = 0
    due_date: str = ""
    eligibility_status: str = EligibilityStatus.BLOCKED.value
    eligibility_reasons: list[NestingMessage] = field(default_factory=list)

    def snapshot_hash(self) -> str:
        return stable_sha256(asdict(self))


@dataclass
class PieceInstance:
    instance_id: str
    demand_line_id: str
    part_id: str
    manufacturing_hash: str
    quantity_ordinal: int
    part_position: str = ""
    assembly_context: list[str] = field(default_factory=list)
    project_phase: str = ""
    production_batch: str = ""
    priority: int = 0
    due_date: str = ""


@dataclass
class NestingEligibilityReport:
    mode: str
    generated_at: str
    project_id: str
    project_revision_hash: str
    demand_lines: list[NestingDemandLine] = field(default_factory=list)
    piece_instances: list[PieceInstance] = field(default_factory=list)
    messages: list[NestingMessage] = field(default_factory=list)
    demand_snapshot_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("generated_at", None)
        payload.pop("demand_snapshot_hash", None)
        self.demand_snapshot_hash = stable_sha256(payload)
        return self.demand_snapshot_hash


@dataclass
class ToolDefinition:
    tool_id: str
    tool_type: str
    material: str = ""
    diameter_mm: float = 0.0
    length_mm: float = 0.0
    point_angle_deg: float = 0.0
    shank_segments: list[dict[str, float]] = field(default_factory=list)
    allowed_machine_ids: list[str] = field(default_factory=list)
    allowed_station_ids: list[str] = field(default_factory=list)
    status: str = "active"
    maintenance_status: str = "ok"
    speed: float = 0.0
    feed: float = 0.0
    tool_change_seconds: float = 0.0
    tolerance_mm: float = 0.05
    configuration_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self); payload.pop("configuration_hash", None)
        self.configuration_hash = stable_sha256(payload)
        return self.configuration_hash


@dataclass
class FormulaDefinition:
    formula_id: str
    purpose: str
    expression: str
    allowed_variables: list[str] = field(default_factory=list)
    result_unit: str = "seconds"
    revision: str = "1"
    enabled: bool = True
    formula_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self); payload.pop("formula_hash", None)
        self.formula_hash = stable_sha256(payload)
        return self.formula_hash


@dataclass
class MachineOptimizationProfile:
    profile_id: str
    machine_id: str
    machine_group: str = ""
    station_id: str = ""
    controller_profile: str = ""
    company_scope: str = ""
    site_scope: str = ""
    revision: str = "1"
    enabled: bool = True
    validation_status: str = "manual_validation_required"
    supported_profile_types: list[str] = field(default_factory=list)
    supported_materials: list[str] = field(default_factory=list)
    supported_operations: list[str] = field(default_factory=lambda: ["saw"])
    supported_sides: list[str] = field(default_factory=list)
    allowed_rotations_deg: list[float] = field(default_factory=lambda: [0.0])
    feed_direction: str = "left_to_right"
    min_dimensions_mm: dict[str, float] = field(default_factory=dict)
    max_dimensions_mm: dict[str, float] = field(default_factory=dict)
    min_part_length_mm: float = 0.0
    max_part_length_mm: float = 0.0
    max_stock_length_mm: float = 0.0
    kerf_mm: float = 0.0
    head_trim_mm: float = 0.0
    tail_trim_mm: float = 0.0
    extra_miter_loss_mm: float = 0.0
    min_saw_angle_deg: float = -90.0
    max_saw_angle_deg: float = 90.0
    angle_tolerance_deg: float = 0.01
    preferred_start_angle_range_deg: list[float] = field(default_factory=list)
    preferred_end_angle_range_deg: list[float] = field(default_factory=list)
    min_feed_y_mm: float = 0.0
    max_feed_y_mm: float = 0.0
    min_feed_z_mm: float = 0.0
    max_feed_z_mm: float = 0.0
    pivot_to_stop_mm: float = 0.0
    blade_to_measurement_mm: float = 0.0
    blade_to_clamp_center_mm: float = 0.0
    clamp_width_left_mm: float = 0.0
    clamp_width_right_mm: float = 0.0
    safety_length_mm: float = 0.0
    forbidden_clamp_zones: list[dict[str, float]] = field(default_factory=list)
    minimum_end_remnant_mm: float = 0.0
    stock_first: bool = False
    sort_rules: list[dict[str, Any]] = field(default_factory=list)
    compound_cut_policy: str = "blocked"
    common_cut_policy: str = "blocked"
    max_hole_diameter_mm: float = 0.0
    machine_tolerance_mm: float = 0.1
    position_tolerance_mm: float = 0.1
    handling_cost: float = 0.0
    setup_cost: float = 0.0
    tool_ids: list[str] = field(default_factory=list)
    formula_ids: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    configuration_hash: str = ""

    def refresh_hash(self, *, tool_hashes: dict[str, str] | None = None, formula_hashes: dict[str, str] | None = None) -> str:
        payload = asdict(self); payload.pop("configuration_hash", None)
        payload["effective_tool_hashes"] = {k: (tool_hashes or {}).get(k, "") for k in sorted(self.tool_ids)}
        payload["effective_formula_hashes"] = {k: (formula_hashes or {}).get(k, "") for k in sorted(self.formula_ids)}
        self.configuration_hash = stable_sha256(payload)
        return self.configuration_hash


@dataclass
class MachineCapabilityReport:
    machine_profile_id: str
    machine_id: str
    demand_line_id: str
    feasible: bool
    review_required: bool = False
    messages: list[NestingMessage] = field(default_factory=list)
    required_tool_ids: list[str] = field(default_factory=list)
    matched_tool_ids: list[str] = field(default_factory=list)
    effective_machine_hash: str = ""
    report_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self); payload.pop("report_hash", None)
        self.report_hash = stable_sha256(payload)
        return self.report_hash


@dataclass
class PurchaseOption:
    purchase_option_id: str
    supplier_article: str
    profile_id: str
    section_hash: str
    material: str
    material_grade: str
    length_mm: float
    available_quantity: int | None = None
    moq: int = 1
    unit_price: float = 0.0
    lead_time_days: int = 0
    transport_cost: float = 0.0
    cutting_cost: float = 0.0
    certificate_options: list[str] = field(default_factory=list)
    supplier: str = ""
    valid_from: str = ""
    valid_until: str = ""
    minimum_reusable_mm: float = 0.0
    provenance: dict[str, Any] = field(default_factory=dict)
    snapshot_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self); payload.pop("snapshot_hash", None)
        self.snapshot_hash = stable_sha256(payload)
        return self.snapshot_hash


@dataclass
class StockCandidate:
    candidate_id: str
    source_type: str
    source_id: str
    physical: bool
    profile_id: str
    section_hash: str
    material: str
    material_grade: str
    length_mm: float
    length_units: int
    available_quantity: int | None
    heat: str = ""
    batch: str = ""
    certificate: str = ""
    supplier: str = ""
    location: str = ""
    lead_time_days: int = 0
    unit_price: float = 0.0
    extra_cost: float = 0.0
    minimum_reusable_mm: float = 0.0
    reservation_status: str = "available"
    reservation_revision: int = 0
    measurement_reliability: str = "administrative"
    provenance: dict[str, Any] = field(default_factory=dict)
    snapshot_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self); payload.pop("snapshot_hash", None)
        self.snapshot_hash = stable_sha256(payload)
        return self.snapshot_hash


@dataclass
class StockSnapshot:
    project_id: str
    policy: str
    reservation_revision: int
    candidates: list[StockCandidate]
    created_at: str = field(default_factory=utc_now_iso)
    snapshot_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self); payload.pop("created_at", None); payload.pop("snapshot_hash", None)
        self.snapshot_hash = stable_sha256(payload)
        return self.snapshot_hash


@dataclass
class ReservationRequest:
    source_type: str
    source_id: str
    quantity: int = 1
    expected_reservation_revision: int | None = None


@dataclass
class ReservationRecord:
    reservation_id: str
    run_id: str
    project_id: str
    requests: list[dict[str, Any]]
    status: str = "reserved"
    created_at: str = field(default_factory=utc_now_iso)
    created_by: str = ""
    project_reservation_revision: int = 0
    record_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self); payload.pop("record_hash", None)
        self.record_hash = stable_sha256(payload)
        return self.record_hash


@dataclass
class ProfileNestingInputSnapshot:
    snapshot_id: str
    project_id: str
    project_revision_hash: str
    demand_snapshot_hash: str
    demand_lines: list[dict[str, Any]]
    piece_instances: list[dict[str, Any]] = field(default_factory=list)
    machine_snapshot_hash: str = ""
    tool_snapshot_hash: str = ""
    stock_snapshot_hash: str = ""
    machine_snapshot: dict[str, Any] = field(default_factory=dict)
    tool_snapshot: dict[str, Any] = field(default_factory=dict)
    stock_snapshot: dict[str, Any] = field(default_factory=dict)
    reservation_version: str = ""
    objective_configuration: dict[str, Any] = field(default_factory=dict)
    solver_configuration: dict[str, Any] = field(default_factory=dict)
    units: dict[str, Any] = field(default_factory=dict)
    tolerances: dict[str, Any] = field(default_factory=dict)
    feature_flags: dict[str, Any] = field(default_factory=dict)
    user_locks: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    created_by: str = ""
    snapshot_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("created_at", None)
        payload.pop("snapshot_hash", None)
        self.snapshot_hash = stable_sha256(payload)
        return self.snapshot_hash


@dataclass
class ProfileNestingRun:
    run_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: str = PROFILE_NESTING_SCHEMA_VERSION
    project_id: str = ""
    project_revision_hash: str = ""
    status: str = NestingRunStatus.DRAFT.value
    created_at: str = field(default_factory=utc_now_iso)
    modified_at: str = field(default_factory=utc_now_iso)
    accepted_at: str = ""
    released_at: str = ""
    created_by: str = ""
    input_snapshot_hash: str = ""
    part_demand_snapshot_hash: str = ""
    stock_snapshot_hash: str = ""
    machine_snapshot_hash: str = ""
    solver_configuration: dict[str, Any] = field(default_factory=dict)
    solver_version: str = ""
    objective_configuration: dict[str, Any] = field(default_factory=dict)
    random_seed: int = 0
    timeout_seconds: float = 0.0
    scenario_id: str = "default"
    scenario_family: str = "waste"
    result_status: str = "not_solved"
    lower_bound: float | None = None
    upper_bound: float | None = None
    gap: float | None = None
    runtime_seconds: float = 0.0
    simplifications: list[str] = field(default_factory=list)
    plan_hash: str = ""
    validation_report_hash: str = ""
    stock_reservations: list[dict[str, Any]] = field(default_factory=list)
    output_artifacts: list[dict[str, Any]] = field(default_factory=list)
    audit: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProfileNestingRun":
        payload = dict(value)
        if str(payload.get("schema_version") or "") in {"1.0", "1.1", "1.2", "1.3", "1.4"}:
            payload["schema_version"] = PROFILE_NESTING_SCHEMA_VERSION
        return cls(**payload)
