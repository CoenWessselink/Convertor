"""Phase-3 orchestration for validated straight-cut optimisation."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import NestingRunStatus, ProfileNestingRun, ReservationRequest
from .objective import default_objective_configuration, validate_objective_configuration
from .phase2 import create_phase2_input_snapshot
from .reservation import reserve_physical_stock
from .results import SolverResultStatus
from .service import register_solved_run
from .straight_solver import solve_straight_cut
from .validator import validate_straight_plan


def _reservation_requests(plan) -> list[ReservationRequest]:
    grouped: dict[tuple[str, str], int] = {}
    for bar in plan.bars:
        if bar.source_type not in {"full_stock", "remnant"}:
            continue
        key = (bar.source_type, bar.source_id)
        grouped[key] = grouped.get(key, 0) + 1
    return [
        ReservationRequest(source_type=source_type, source_id=source_id, quantity=quantity)
        for (source_type, source_id), quantity in sorted(grouped.items())
    ]


def solve_and_register_phase3(
    project,
    *,
    mode: str = "production",
    stock_policy: str = "stock_remnants_purchase",
    created_by: str = "",
    scenario_id: str = "default",
    scenario_family: str = "waste",
    backend: str = "auto",
    objective_configuration: dict[str, Any] | None = None,
    solver_configuration: dict[str, Any] | None = None,
    random_seed: int = 0,
    timeout_seconds: float = 0.0,
    reserve_stock: bool = False,
):
    """Create an immutable input snapshot, solve, independently validate and persist.

    Stock reservation is optional and occurs only *after* a valid plan exists.
    Purchase options are planning records and are not reserved by this service.
    """
    objective = validate_objective_configuration(
        objective_configuration or default_objective_configuration(scenario_family),
        family=scenario_family,
    )
    solver_config = dict(solver_configuration or {})
    solver_config.setdefault("backend", backend)
    solver_config.setdefault("straight_cut_scope", "square_exact_only")
    snapshot, demand_report, context = create_phase2_input_snapshot(
        project, mode=mode, stock_policy=stock_policy, created_by=created_by,
        objective_configuration=objective, solver_configuration=solver_config,
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
    plan, evidence = solve_straight_cut(
        snapshot, backend=backend, scenario_family=scenario_family,
        objective_configuration=objective, solver_configuration=solver_config,
        random_seed=random_seed, timeout_seconds=timeout_seconds,
    )
    validation = None
    if plan is not None:
        validation = validate_straight_plan(snapshot, plan)
        if not validation.valid:
            evidence.status = SolverResultStatus.FAILED.value
            evidence.simplifications.append("independent_validation_failed")
            evidence.refresh_hash()
            run.status = NestingRunStatus.FAILED.value
            run.result_status = SolverResultStatus.FAILED.value
        else:
            run.status = NestingRunStatus.FEASIBLE.value
            run.result_status = evidence.status
            run.plan_hash = plan.plan_hash
            run.validation_report_hash = validation.report_hash
    else:
        run.result_status = evidence.status
        if evidence.status in {SolverResultStatus.INFEASIBLE_DETECTED.value, SolverResultStatus.INFEASIBLE_PROVEN.value}:
            run.status = NestingRunStatus.INFEASIBLE.value
        elif evidence.status == SolverResultStatus.CANCELLED.value:
            run.status = NestingRunStatus.CANCELLED.value
        else:
            run.status = NestingRunStatus.FAILED.value
    run.solver_version = evidence.backend_version
    run.runtime_seconds = float(evidence.runtime_seconds)
    run.lower_bound = float(evidence.lower_bound) if evidence.lower_bound is not None else None
    run.upper_bound = float(evidence.upper_bound) if evidence.upper_bound is not None else None
    run.gap = float(evidence.relative_gap) if evidence.relative_gap is not None else None
    run.simplifications = list(evidence.simplifications)

    reservation_record = None
    if reserve_stock and plan is not None and validation is not None and validation.valid:
        requests = _reservation_requests(plan)
        if requests:
            reservation_record = reserve_physical_stock(
                project, requests, run_id=run.run_id, user=created_by or "system"
            )
            run.stock_reservations.append(asdict(reservation_record))
    register_solved_run(
        project, run, snapshot, plan=plan, solver_evidence=evidence,
        validation_report=validation, user=created_by or "system",
    )
    return run, snapshot, demand_report, context, plan, evidence, validation, reservation_record
