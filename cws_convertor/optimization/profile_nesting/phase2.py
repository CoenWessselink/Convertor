"""Phase-2 orchestration: immutable machine/tool/stock context, no solver."""
from __future__ import annotations
from dataclasses import asdict
from typing import Any

from cws_convertor.project.model import stable_sha256
from .configuration import load_formulas, load_machine_profiles, load_purchase_options, load_tools
from .eligibility import extract_demand
from .machine import build_machine_snapshot, evaluate_machine_capability, evaluate_machine_stock_compatibility
from .models import EligibilityStatus, NestingMessage
from .snapshot import create_input_snapshot
from .stock import build_stock_snapshot, evaluate_stock_compatibility, stock_snapshot_to_dict


def prepare_phase2_context(project, *, mode: str = "production", stock_policy: str = "stock_remnants_purchase") -> dict[str, Any]:
    profiles, tools, formulas = load_machine_profiles(project), load_tools(project), load_formulas(project)
    purchases = load_purchase_options(project)
    preliminary = extract_demand(project, mode=mode, defer_machine_compatibility=True)
    reports = []
    candidates_by_part: dict[str, list[str]] = {}
    for line in preliminary.demand_lines:
        feasible_ids = []
        for profile in profiles:
            report = evaluate_machine_capability(line, profile, tools, formulas)
            reports.append(report)
            if report.feasible:
                feasible_ids.append(profile.machine_id)
        candidates_by_part[line.part_id] = sorted(set(feasible_ids))
    demand = extract_demand(project, mode=mode, candidate_machine_ids_by_part=candidates_by_part)
    machine_snapshot = build_machine_snapshot(profiles, tools, formulas)
    tool_payload = {"schema_version": "1.0", "tools": [asdict(t) for t in sorted(tools, key=lambda x: x.tool_id)]}
    tool_payload["snapshot_hash"] = stable_sha256(tool_payload)
    stock = build_stock_snapshot(project, purchase_options=purchases, policy=stock_policy)
    stock_dict = stock_snapshot_to_dict(stock)

    # Phase-2 stock gate: prove that every otherwise eligible line has at least
    # one individually compatible source. Exact multi-piece packing belongs to phase 3.
    for line in demand.demand_lines:
        if line.eligibility_status == EligibilityStatus.BLOCKED.value:
            continue
        compatible = []
        machine_candidates = [p for p in profiles if p.machine_id in line.candidate_machine_ids]
        for candidate in stock.candidates:
            # conservative single-piece allowance: use the least restrictive proven machine
            allowance_sets = [(0.0, 0.0, 0.0)] if not machine_candidates else [
                (p.head_trim_mm, p.tail_trim_mm, p.kerf_mm) for p in machine_candidates
            ]
            for machine_profile, (h, t, k) in zip(machine_candidates or [None], allowance_sets):
                stock_issues = evaluate_stock_compatibility(line, candidate, head_trim_mm=h, tail_trim_mm=t, kerf_mm=k)
                machine_stock_issues = [] if machine_profile is None else evaluate_machine_stock_compatibility(candidate, machine_profile)
                if not stock_issues and not machine_stock_issues:
                    compatible.append(candidate.candidate_id)
                    break
        if not compatible:
            msg = NestingMessage(code="CWS-NEST-011", severity="error",
                                 message="Geen stock-, reststuk- of purchase candidate past bij dit onderdeel.",
                                 blocking=(mode == "production"), object_ids=[line.part_id])
            line.eligibility_reasons.append(msg)
            line.eligibility_status = EligibilityStatus.BLOCKED.value if mode == "production" else EligibilityStatus.REVIEW.value
        setattr(line, "compatible_stock_candidate_ids", compatible)
    demand.messages = [m for line in demand.demand_lines for m in line.eligibility_reasons]
    demand.refresh_hash()
    return {
        "demand_report": demand,
        "machine_capability_reports": reports,
        "machine_snapshot": machine_snapshot,
        "tool_snapshot": tool_payload,
        "stock_snapshot": stock_dict,
        "reservation_version": str(project.profile_nesting_reservation_revision),
    }


def create_phase2_input_snapshot(project, *, mode: str = "production", stock_policy: str = "stock_remnants_purchase", created_by: str = "", objective_configuration: dict | None = None, solver_configuration: dict | None = None):
    context = prepare_phase2_context(project, mode=mode, stock_policy=stock_policy)
    # create_input_snapshot re-extracts demand; preserve the phase-2 proven
    # demand explicitly afterwards and refresh the binding hash.
    snapshot, _ = create_input_snapshot(
        project, mode=mode, created_by=created_by,
        objective_configuration=objective_configuration, solver_configuration=solver_configuration,
        machine_snapshot=context["machine_snapshot"], tool_snapshot=context["tool_snapshot"],
        stock_snapshot=context["stock_snapshot"], reservation_version=context["reservation_version"],
    )
    report = context["demand_report"]
    snapshot.demand_snapshot_hash = report.demand_snapshot_hash
    snapshot.demand_lines = [asdict(x) for x in report.demand_lines]
    snapshot.piece_instances = [asdict(x) for x in report.piece_instances]
    snapshot.refresh_hash()
    return snapshot, report, context


def create_and_register_phase2_run(project, *, mode: str = "production", stock_policy: str = "stock_remnants_purchase", created_by: str = "", scenario_id: str = "default", scenario_family: str = "waste", objective_configuration: dict | None = None, solver_configuration: dict | None = None):
    """Create a draft, fully bound phase-2 run without solving it."""
    from .models import ProfileNestingRun
    from .service import register_run
    snapshot, report, context = create_phase2_input_snapshot(
        project, mode=mode, stock_policy=stock_policy, created_by=created_by,
        objective_configuration=objective_configuration, solver_configuration=solver_configuration,
    )
    run = ProfileNestingRun(
        project_id=project.project_id, project_revision_hash=snapshot.project_revision_hash,
        created_by=created_by, input_snapshot_hash=snapshot.snapshot_hash,
        part_demand_snapshot_hash=snapshot.demand_snapshot_hash,
        stock_snapshot_hash=snapshot.stock_snapshot_hash, machine_snapshot_hash=snapshot.machine_snapshot_hash,
        solver_configuration=dict(solver_configuration or {}), objective_configuration=dict(objective_configuration or {}),
        scenario_id=scenario_id, scenario_family=scenario_family, result_status="not_solved",
    )
    register_run(project, run, snapshot, user=created_by or "system")
    return run, snapshot, report, context
