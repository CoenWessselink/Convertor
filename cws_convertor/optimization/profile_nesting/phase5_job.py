"""Background-safe phase-5 solve preparation/execution/commit bridge.

Preparation captures an immutable solver snapshot on the UI thread. The worker
only receives that snapshot and therefore never mutates the live project. A
completed result is committed only after the current project revision is still
identical to the captured revision. This is the generation/stale guard required
for responsive desktop optimisation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from .angle_solver import solve_angle_cut
from .angle_validator import validate_angle_plan
from .models import NestingRunStatus, ProfileNestingRun
from .objective import default_objective_configuration, validate_objective_configuration
from .phase2 import create_phase2_input_snapshot
from .results import SolverResultStatus
from .service import register_solved_run
from .transition_matrix import build_transition_matrix


@dataclass
class PreparedPhase5Solve:
    run: ProfileNestingRun
    snapshot: Any
    demand_report: Any
    context: dict[str, Any]
    backend: str
    scenario_family: str
    objective_configuration: dict[str, Any]
    solver_configuration: dict[str, Any]
    random_seed: int
    timeout_seconds: float


@dataclass
class Phase5SolveOutcome:
    prepared: PreparedPhase5Solve
    plan: Any | None
    evidence: Any
    validation: Any | None
    transition_matrix: Any | None

    @property
    def cancelled(self) -> bool:
        return str(getattr(self.evidence, "status", "")) == SolverResultStatus.CANCELLED.value


def prepare_phase5_solve(
    project,
    *,
    mode: str = "production",
    stock_policy: str = "stock_remnants_purchase",
    created_by: str = "gui",
    scenario_id: str = "ui-waste",
    scenario_family: str = "waste",
    backend: str = "auto",
    objective_configuration: dict[str, Any] | None = None,
    solver_configuration: dict[str, Any] | None = None,
    random_seed: int = 0,
    timeout_seconds: float = 0.0,
) -> PreparedPhase5Solve:
    objective = validate_objective_configuration(
        objective_configuration or default_objective_configuration(scenario_family),
        family=scenario_family,
    )
    solver_config = dict(solver_configuration or {})
    solver_config.setdefault("backend", backend)
    solver_config.setdefault("cut_scope", "geometry_backed_angle_sequence")
    solver_config.setdefault("angle_exact_max_pieces", 7)
    snapshot, demand, context = create_phase2_input_snapshot(
        project,
        mode=mode,
        stock_policy=stock_policy,
        created_by=created_by,
        objective_configuration=objective,
        solver_configuration=solver_config,
    )
    run = ProfileNestingRun(
        project_id=project.project_id,
        project_revision_hash=snapshot.project_revision_hash,
        created_by=created_by,
        input_snapshot_hash=snapshot.snapshot_hash,
        part_demand_snapshot_hash=snapshot.demand_snapshot_hash,
        stock_snapshot_hash=snapshot.stock_snapshot_hash,
        machine_snapshot_hash=snapshot.machine_snapshot_hash,
        solver_configuration=solver_config,
        objective_configuration=objective,
        random_seed=int(random_seed),
        timeout_seconds=float(timeout_seconds),
        scenario_id=scenario_id,
        scenario_family=scenario_family,
        status=NestingRunStatus.SOLVING.value,
    )
    return PreparedPhase5Solve(
        run=run,
        snapshot=snapshot,
        demand_report=demand,
        context=context,
        backend=backend,
        scenario_family=scenario_family,
        objective_configuration=objective,
        solver_configuration=solver_config,
        random_seed=int(random_seed),
        timeout_seconds=float(timeout_seconds),
    )


def execute_phase5_solve(
    prepared: PreparedPhase5Solve,
    *,
    cancel_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> Phase5SolveOutcome:
    plan, evidence = solve_angle_cut(
        prepared.snapshot,
        backend=prepared.backend,
        scenario_family=prepared.scenario_family,
        objective_configuration=prepared.objective_configuration,
        solver_configuration=prepared.solver_configuration,
        random_seed=prepared.random_seed,
        timeout_seconds=prepared.timeout_seconds,
        cancel_check=cancel_check,
        progress_callback=progress_callback,
    )
    transition_matrix = None
    validation = None
    run = prepared.run
    run.solver_version = str(getattr(evidence, "backend_version", "") or "")
    run.runtime_seconds = float(getattr(evidence, "runtime_seconds", 0.0) or 0.0)
    run.lower_bound = float(evidence.lower_bound) if getattr(evidence, "lower_bound", None) is not None else None
    run.upper_bound = float(evidence.upper_bound) if getattr(evidence, "upper_bound", None) is not None else None
    run.gap = float(evidence.relative_gap) if getattr(evidence, "relative_gap", None) is not None else None
    run.simplifications = list(getattr(evidence, "simplifications", []) or [])
    run.result_status = str(getattr(evidence, "status", SolverResultStatus.UNKNOWN.value))

    if run.result_status == SolverResultStatus.CANCELLED.value:
        run.status = NestingRunStatus.CANCELLED.value
        return Phase5SolveOutcome(prepared, None, evidence, None, None)

    if plan is not None:
        transition_matrix = build_transition_matrix(
            prepared.snapshot,
            max_unique_lines=int(prepared.solver_configuration.get("transition_matrix_max_unique_lines") or 50),
        )
        evidence.transition_matrix_hash = transition_matrix.matrix_hash
        evidence.refresh_hash()
        validation = validate_angle_plan(prepared.snapshot, plan)
        if validation.valid:
            run.status = NestingRunStatus.FEASIBLE.value
            run.plan_hash = plan.plan_hash
            run.validation_report_hash = validation.report_hash
        else:
            run.status = NestingRunStatus.FAILED.value
            run.result_status = SolverResultStatus.FAILED.value
            evidence.status = SolverResultStatus.FAILED.value
            evidence.simplifications.append("independent_angle_validation_failed")
            evidence.refresh_hash()
    else:
        if run.result_status in {SolverResultStatus.INFEASIBLE_DETECTED.value, SolverResultStatus.INFEASIBLE_PROVEN.value}:
            run.status = NestingRunStatus.INFEASIBLE.value
        elif run.result_status == SolverResultStatus.CANCELLED.value:
            run.status = NestingRunStatus.CANCELLED.value
        else:
            run.status = NestingRunStatus.FAILED.value
    return Phase5SolveOutcome(prepared, plan, evidence, validation, transition_matrix)


def commit_phase5_outcome(project, outcome: Phase5SolveOutcome, *, user: str = "gui") -> str:
    if outcome.cancelled:
        return "cancelled"
    current_revision = project.revision_content_sha256()
    expected_revision = str(outcome.prepared.snapshot.project_revision_hash or "")
    if current_revision != expected_revision:
        return "stale"
    register_solved_run(
        project,
        outcome.prepared.run,
        outcome.prepared.snapshot,
        plan=outcome.plan,
        solver_evidence=outcome.evidence,
        validation_report=outcome.validation,
        user=user,
    )
    return "committed"


__all__ = [
    "PreparedPhase5Solve", "Phase5SolveOutcome", "prepare_phase5_solve",
    "execute_phase5_solve", "commit_phase5_outcome",
]
