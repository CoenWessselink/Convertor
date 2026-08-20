"""Immutable input snapshots and hash binding for profile nesting."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import uuid4

from cws_convertor.project.model import ProjectModel, stable_sha256
from .eligibility import extract_demand
from .models import ProfileNestingInputSnapshot, ProfileNestingRun
from .units import LengthKernel


def create_input_snapshot(
    project: ProjectModel,
    *,
    mode: str = "production",
    created_by: str = "",
    objective_configuration: dict[str, Any] | None = None,
    solver_configuration: dict[str, Any] | None = None,
    machine_snapshot: dict[str, Any] | None = None,
    tool_snapshot: dict[str, Any] | None = None,
    stock_snapshot: dict[str, Any] | None = None,
    reservation_version: str = "",
    feature_flags: dict[str, Any] | None = None,
    user_locks: list[dict[str, Any]] | None = None,
    kernel: LengthKernel | None = None,
) -> tuple[ProfileNestingInputSnapshot, Any]:
    kernel = kernel or LengthKernel()
    report = extract_demand(project, mode=mode, kernel=kernel)
    snapshot = ProfileNestingInputSnapshot(
        snapshot_id=str(uuid4()),
        project_id=project.project_id,
        project_revision_hash=report.project_revision_hash,
        demand_snapshot_hash=report.demand_snapshot_hash,
        demand_lines=[asdict(item) for item in report.demand_lines],
        piece_instances=[asdict(item) for item in report.piece_instances],
        machine_snapshot_hash=str((machine_snapshot or {}).get("snapshot_hash") or stable_sha256(machine_snapshot or {})),
        tool_snapshot_hash=str((tool_snapshot or {}).get("snapshot_hash") or stable_sha256(tool_snapshot or {})),
        stock_snapshot_hash=str((stock_snapshot or {}).get("snapshot_hash") or stable_sha256(stock_snapshot or {})),
        machine_snapshot=dict(machine_snapshot or {}),
        tool_snapshot=dict(tool_snapshot or {}),
        stock_snapshot=dict(stock_snapshot or {}),
        reservation_version=reservation_version,
        objective_configuration=dict(objective_configuration or {}),
        solver_configuration=dict(solver_configuration or {}),
        units=kernel.snapshot(),
        tolerances={"source": "project_part_tolerances"},
        feature_flags=dict(feature_flags or {}),
        user_locks=list(user_locks or []),
        created_by=created_by,
    )
    snapshot.refresh_hash()
    return snapshot, report


def create_run(
    project: ProjectModel,
    *,
    mode: str = "production",
    created_by: str = "",
    scenario_id: str = "default",
    scenario_family: str = "waste",
    objective_configuration: dict[str, Any] | None = None,
    solver_configuration: dict[str, Any] | None = None,
    random_seed: int = 0,
    timeout_seconds: float = 0.0,
    machine_snapshot: dict[str, Any] | None = None,
    tool_snapshot: dict[str, Any] | None = None,
    stock_snapshot: dict[str, Any] | None = None,
    reservation_version: str = "",
) -> tuple[ProfileNestingRun, ProfileNestingInputSnapshot, Any]:
    snapshot, report = create_input_snapshot(
        project,
        mode=mode,
        created_by=created_by,
        objective_configuration=objective_configuration,
        solver_configuration=solver_configuration,
        machine_snapshot=machine_snapshot,
        tool_snapshot=tool_snapshot,
        stock_snapshot=stock_snapshot,
        reservation_version=reservation_version,
    )
    run = ProfileNestingRun(
        project_id=project.project_id,
        project_revision_hash=snapshot.project_revision_hash,
        created_by=created_by,
        input_snapshot_hash=snapshot.snapshot_hash,
        part_demand_snapshot_hash=snapshot.demand_snapshot_hash,
        stock_snapshot_hash=snapshot.stock_snapshot_hash,
        machine_snapshot_hash=snapshot.machine_snapshot_hash,
        solver_configuration=dict(solver_configuration or {}),
        objective_configuration=dict(objective_configuration or {}),
        random_seed=int(random_seed),
        timeout_seconds=float(timeout_seconds),
        scenario_id=scenario_id,
        scenario_family=scenario_family,
    )
    return run, snapshot, report
