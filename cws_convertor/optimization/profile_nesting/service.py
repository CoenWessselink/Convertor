"""Project persistence bridge for profile nesting runs (phases 1-5)."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from cws_convertor.project.model import ProjectModel, stable_sha256
from .models import ProfileNestingInputSnapshot, ProfileNestingRun
from .snapshot import create_run


def register_run(
    project: ProjectModel,
    run: ProfileNestingRun,
    snapshot: ProfileNestingInputSnapshot,
    *,
    user: str = "system",
) -> None:
    if run.project_id != project.project_id or snapshot.project_id != project.project_id:
        raise ValueError("Nestingrun hoort niet bij dit project")
    if run.input_snapshot_hash != snapshot.snapshot_hash:
        raise ValueError("Run verwijst niet naar de aangeleverde inputsnapshot")
    before = stable_sha256(project.profile_nesting_runs) if project.profile_nesting_runs else ""
    project.profile_nesting_runs[run.run_id] = {
        "run": run.to_dict(),
        "input_snapshot": asdict(snapshot),
    }
    after = stable_sha256(project.profile_nesting_runs)
    project.audit(
        "profile_nesting.run_created",
        user=user,
        entity_id=run.run_id,
        before_hash=before,
        after_hash=after,
        details={"input_snapshot_hash": snapshot.snapshot_hash},
    )


def create_and_register_run(project: ProjectModel, **kwargs: Any):
    user = str(kwargs.get("created_by") or "system")
    run, snapshot, report = create_run(project, **kwargs)
    register_run(project, run, snapshot, user=user)
    return run, snapshot, report


def register_solved_run(
    project: ProjectModel,
    run: ProfileNestingRun,
    snapshot: ProfileNestingInputSnapshot,
    *,
    plan=None,
    solver_evidence=None,
    validation_report=None,
    user: str = "system",
) -> None:
    """Persist one solved profile-nesting result atomically in the project graph.

    Result records stay bound to the immutable input snapshot. The project
    package writer performs the later atomic ZIP/SQLite write and checksum gate.
    """
    if run.project_id != project.project_id or snapshot.project_id != project.project_id:
        raise ValueError("Nestingrun hoort niet bij dit project")
    if run.input_snapshot_hash != snapshot.snapshot_hash:
        raise ValueError("Run verwijst niet naar de aangeleverde inputsnapshot")
    if plan is not None and str(plan.input_snapshot_hash) != snapshot.snapshot_hash:
        raise ValueError("Nestingplan hoort niet bij de aangeleverde inputsnapshot")
    if validation_report is not None and str(validation_report.input_snapshot_hash) != snapshot.snapshot_hash:
        raise ValueError("Validatierapport hoort niet bij de aangeleverde inputsnapshot")
    record = {
        "run": run.to_dict(),
        "input_snapshot": asdict(snapshot),
        "plan": plan.to_dict() if plan is not None else None,
        "solver_evidence": solver_evidence.to_dict() if solver_evidence is not None else None,
        "validation_report": validation_report.to_dict() if validation_report is not None else None,
    }
    before = stable_sha256(project.profile_nesting_runs) if project.profile_nesting_runs else ""
    project.profile_nesting_runs[run.run_id] = record
    after = stable_sha256(project.profile_nesting_runs)
    project.audit(
        "profile_nesting.run_solved",
        user=user,
        entity_id=run.run_id,
        before_hash=before,
        after_hash=after,
        details={
            "input_snapshot_hash": snapshot.snapshot_hash,
            "plan_hash": str(getattr(plan, "plan_hash", "") or ""),
            "validation_report_hash": str(getattr(validation_report, "report_hash", "") or ""),
            "solver_evidence_hash": str(getattr(solver_evidence, "evidence_hash", "") or ""),
            "result_status": run.result_status,
        },
    )
