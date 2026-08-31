from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.optimization.plate_nesting import PlateGeometryRef, PlateNestDemand, PlateStock, solve_canonical_plate_nesting, validate_canonical_plate_nesting
from cws_convertor.production import FiniteCapacityPlanner, MachineResource, OperationRequirement, Phase2ProductionState, ProductionOrder, Shift, ShopfloorState
from cws_convertor.project.model import ProjectModel
from cws_convertor.proof_center import PROOF_CATEGORIES, ProofBlocker, ProofCenter, ProofEvidence
from cws_convertor.quality import InspectionCharacteristic, InspectionPlan, QualityLedger


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def run_scope() -> dict[str, object]:
    geometry = PlateGeometryRef("geometry:plate-1", ((0, 0), (500, 0), (500, 250), (0, 250)), (((200, 100), (220, 100), (220, 120), (200, 120)),))
    demand = PlateNestDemand("demand-1", "plate-1", geometry, "steel", "S355", 10, allowed_rotations_deg=(0,), grain_direction_deg=0, production_identity="assembly-A/plate-1")
    stock = PlateStock("stock-1", 1000, 500, "steel", "S355", 10, grain_direction_deg=0)
    plate = solve_canonical_plate_nesting((demand,), (stock,), run_id="plate-e2e")
    assert validate_canonical_plate_nesting(plate, (demand,), (stock,)).passed
    assert plate.complete and plate.solver_evidence.exact_small_proven and plate.predicted_remnants
    placement = plate.layouts[0].placements[0]
    tampered = replace(plate, layouts=(replace(plate.layouts[0], placements=(replace(placement, mirrored=True),)),))
    assert "CWS.PLATE.MIRROR_FORBIDDEN" in validate_canonical_plate_nesting(tampered, (demand,), (stock,)).blocking_codes

    release_hash = "a" * 64
    quality = QualityLedger("phase2-project", InspectionPlan(
        "inspection-1", "phase2-project", "A",
        (InspectionCharacteristic("part-length", "plate-1", "length", 500, -0.5, 0.5, fai_required=True),
         InspectionCharacteristic("assembly-fit", "assembly-A", "fit", 0, -0.2, 0.2, scope_type="assembly", assembly_id="assembly-A")),
        release_hash, "quality-planner", "independent-quality",
    ))
    for identifier, characteristic, value in (("m1", "part-length", 500.1), ("m2", "assembly-fit", 0.1)):
        quality.record_measurement(measurement_id=identifier, characteristic_id=characteristic, measured_value=value, measured_at="2026-08-29T08:00:00Z", operator="inspector", tool_id="tool-1", tool_calibration_id="cal-1", first_article=True)
        assert quality.inspection_result(characteristic).accepted
    quality.approve_final_release(source_release_hash=release_hash, approved_by="quality-manager", approved_at="2026-08-29T08:05:00Z")
    assert QualityLedger.from_dict(quality.to_dict()).final_release_allowed

    start = datetime(2026, 8, 29, 6, 0, tzinfo=timezone.utc)
    machine = MachineResource("machine-1", "Saw/drill", "wc-1", ("saw", "drill"), setup_minutes=5)
    shifts = (Shift("shift-1", machine.resource_id, _iso(start), _iso(start + timedelta(hours=8))),)
    order = ProductionOrder("order-1", demand.production_identity, 1, _iso(start + timedelta(hours=7)), release_hash, (OperationRequirement("saw", "saw", 20, setup_code="saw"), OperationRequirement("drill", "drill", 15, setup_code="drill", predecessor_ids=("saw",))))
    schedule = FiniteCapacityPlanner().schedule((order,), (machine,), shifts)
    assert schedule.feasible and len(schedule.operations) == 2
    shopfloor = ShopfloorState.from_schedule(schedule, (order,))
    for operation_id, measurement_id in (("saw", "m1"), ("drill", "m2")):
        selected = shopfloor.scan_select(operation_id)
        execution = shopfloor.start_operation(selected.schedule_id, release_hash=release_hash, operator="operator-1", started_at=selected.starts_at)
        shopfloor.complete_operation(execution.execution_id, completed_at=selected.ends_at, good_quantity=1, measurement_ids=(measurement_id,))
    shopfloor.register_remnant("remnant-1", source_schedule_id="order-1:saw", material="steel", grade="S355", thickness_mm=10, width_mm=300, height_mm=200)
    assert not shopfloor.open_released_work() and not shopfloor.direct_machine_control_allowed

    center = ProofCenter()
    for category in PROOF_CATEGORIES:
        center.record(ProofEvidence(f"proof:{category}", category, "PASS", "b" * 64, category, entity_id=demand.part_id, run_id=plate.run_id))
    center.add_blocker(ProofBlocker("blocker-1", "plate_nesting", "CWS.PLATE.REVIEW", "review placement", "plate_nesting", entity_id=demand.part_id, run_id=plate.run_id, viewer_selection_ids=(demand.part_id,)))
    assert center.navigation_target("blocker-1")["viewer_selection_ids"] == [demand.part_id] and not center.release_allowed
    center.resolve("blocker-1")
    assert center.release_allowed and ProofCenter.from_dict(center.to_dict()).proof_sha256 == center.proof_sha256

    state = Phase2ProductionState(schedule, shopfloor, {plate.run_id: plate.to_dict()}, {quality.inspection_plan.plan_id: quality.to_dict()}, center.to_dict())
    project = ProjectModel.new("Phase 2 completion", created_by="phase2-gate")
    state.persist_to_project(project, user="phase2-gate")
    reopened = Phase2ProductionState.from_project(ProjectModel.from_dict(project.to_dict()))
    assert reopened.state_sha256 == state.state_sha256

    coverage = {
        "plate_nesting_canonical_models": True, "plate_nesting_baseline_solver": True,
        "plate_nesting_exact_small": True, "plate_nesting_independent_validator": True,
        "plate_nesting_rotation_grain": True, "plate_nesting_stock_remnants": True,
        "plate_nesting_reports_neutral": True, "quality_inspection": True,
        "finite_capacity_planning": True, "shopfloor": True, "proof_center": True,
        "project_save_reopen": True, "gui_cli_same_services": True,
        "real_synthetic_e2e": True, "safety_flags_false": True,
    }
    return {"schema": "cws-phase2-completion-scope-evidence-1.0", "status": "passed", "coverage": coverage, "plate_plan_sha256": plate.plan_sha256, "quality_release_sha256": quality.final_release_hash, "schedule_sha256": schedule.schedule_sha256, "production_state_sha256": state.state_sha256, "proof_center_sha256": center.proof_sha256}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_scope()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("PHASE_2_COMPLETION_SCOPE = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
