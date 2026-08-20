"""Versioned, solver-neutral result contracts for profile nesting phases 3-4.

The contracts in this module intentionally contain no optimisation algorithm.
They are the persistence and validation boundary between solvers, project
storage, future UI code and exporters.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .models import CutTransition

from cws_convertor.project.model import stable_sha256, utc_now_iso

PROFILE_NESTING_RESULT_SCHEMA_VERSION = "1.1"


class SolverResultStatus(str, Enum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    TIMEOUT_FEASIBLE = "timeout_feasible"
    MANUAL_FEASIBLE = "manual_feasible"
    INFEASIBLE_PROVEN = "infeasible_proven"
    INFEASIBLE_DETECTED = "infeasible_detected"
    UNKNOWN = "unknown"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class PiecePlacement:
    instance_id: str
    demand_line_id: str
    part_id: str
    manufacturing_hash: str
    part_position: str
    stock_bar_id: str
    sequence_index: int
    start_units: int
    end_units: int
    cut_position_units: int
    length_units: int
    kerf_units: int
    machine_id: str
    machine_profile_id: str
    orientation_id: str = "as_modeled"
    orientation_hash: str = ""
    reference_start_units: int = 0
    reference_end_units: int = 0
    physical_min_units: int = 0
    physical_max_units: int = 0
    start_envelope_min_units: int = 0
    start_envelope_max_units: int = 0
    end_envelope_min_units: int = 0
    end_envelope_max_units: int = 0
    start_cut_hash: str = ""
    end_cut_hash: str = ""
    transition_before_id: str = ""
    transition_after_id: str = ""
    final_cut_kerf_units: int = 0


@dataclass
class StockBarPlan:
    bar_id: str
    candidate_id: str
    source_type: str
    source_id: str
    stock_length_units: int
    machine_id: str
    machine_profile_id: str
    head_trim_units: int
    tail_trim_units: int
    safety_length_units: int
    kerf_units: int
    minimum_reusable_units: int
    placements: list[PiecePlacement] = field(default_factory=list)
    transitions: list[CutTransition] = field(default_factory=list)
    occupied_span_units: int = 0
    nominal_sum_units: int = 0
    transition_effect_units: int = 0
    projected_kerf_units: int = 0
    cut_count: int = 0
    common_cut_count: int = 0
    raw_residual_units: int = 0
    reusable_remnant_units: int = 0
    waste_units: int = 0
    source_cost_micros: int = 0
    machine_cost_micros: int = 0
    total_cost_micros: int = 0
    bar_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("bar_hash", None)
        self.bar_hash = stable_sha256(payload)
        return self.bar_hash


@dataclass
class MaterialBalance:
    gross_stock_units: int = 0
    net_part_units: int = 0
    kerf_units: int = 0
    head_trim_units: int = 0
    tail_trim_units: int = 0
    reusable_remnant_units: int = 0
    waste_units: int = 0
    transition_effect_units: int = 0
    balance_delta_units: int = 0

    @property
    def trim_units(self) -> int:
        return int(self.head_trim_units) + int(self.tail_trim_units)

    @property
    def material_loss_units(self) -> int:
        return int(self.kerf_units) + self.trim_units + int(self.waste_units) + int(self.transition_effect_units)


@dataclass
class ObjectiveBreakdown:
    mode: str
    components: list[dict[str, Any]]
    raw_metrics: dict[str, int]
    comparison_key: list[str] = field(default_factory=list)
    weighted_score: str = ""
    configuration_hash: str = ""


@dataclass
class NestingPlan:
    input_snapshot_hash: str
    status: str
    bars: list[StockBarPlan] = field(default_factory=list)
    unassigned_instance_ids: list[str] = field(default_factory=list)
    material_balance: MaterialBalance = field(default_factory=MaterialBalance)
    objective: ObjectiveBreakdown | None = None
    result_schema_version: str = PROFILE_NESTING_RESULT_SCHEMA_VERSION
    origin_plan_hash: str = ""
    best_known_plan_hash: str = ""
    manual_revision: int = 0
    manual_modifications: list[dict[str, Any]] = field(default_factory=list)
    lock_snapshot_hash: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    plan_hash: str = ""

    def refresh_hash(self) -> str:
        for bar in self.bars:
            bar.refresh_hash()
        payload = asdict(self)
        payload.pop("created_at", None)
        payload.pop("plan_hash", None)
        self.plan_hash = stable_sha256(payload)
        return self.plan_hash

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SolverEvidence:
    input_snapshot_hash: str
    backend: str
    backend_version: str
    status: str
    deterministic_seed: int = 0
    exact_scope: bool = False
    exact_scope_reason: str = ""
    lower_bound: int | None = None
    upper_bound: int | None = None
    absolute_gap: int | None = None
    relative_gap: float | None = None
    gap_metric: str = ""
    nodes_explored: int = 0
    states_pruned: int = 0
    incumbent_updates: int = 0
    runtime_seconds: float = 0.0
    best_solution_seconds: float | None = None
    limit_reached: str = ""
    objective_components: list[dict[str, Any]] = field(default_factory=list)
    simplifications: list[str] = field(default_factory=list)
    transition_matrix_hash: str = ""
    plan_hash: str = ""
    generated_at: str = field(default_factory=utc_now_iso)
    evidence_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("evidence_hash", None)
        self.evidence_hash = stable_sha256(payload)
        return self.evidence_hash

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlanValidationReport:
    input_snapshot_hash: str
    plan_hash: str
    valid: bool
    status: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    material_balance: dict[str, Any] = field(default_factory=dict)
    assigned_instance_count: int = 0
    required_instance_count: int = 0
    checked_bar_count: int = 0
    generated_at: str = field(default_factory=utc_now_iso)
    report_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("generated_at", None)
        payload.pop("report_hash", None)
        self.report_hash = stable_sha256(payload)
        return self.report_hash

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
