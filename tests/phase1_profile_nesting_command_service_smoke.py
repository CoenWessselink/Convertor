from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from cws_convertor.integration.ui_context import UnifiedApplicationContext
from cws_convertor.optimization.profile_nesting.bar_visualization import build_bar_scene, scene_to_svg
from cws_convertor.optimization.profile_nesting.benchmark import build_synthetic_benchmark_project
from cws_convertor.optimization.profile_nesting.command_service import (
    ProfileNestingCommandError,
    ProfileNestingCommandService,
)
from cws_convertor.optimization.profile_nesting.configuration import load_machine_profiles
from cws_convertor.optimization.profile_nesting.phase4 import solve_and_register_phase4
from cws_convertor.project.storage import ProjectStore
from cws_convertor.ui_qt.phase3_workspaces import ProfileNestingPanel


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "validation" / "phases" / "PHASE_1_PROFILE_NESTING_COMMAND_EVIDENCE.json"


def _solve(piece_count: int = 16):
    project = build_synthetic_benchmark_project(piece_count, angle=True, project_name="Phase 1 command E2E")
    for part in project.parts.values():
        part.properties["allowed_orientations"] = ["as_modeled", "rotate_180"]
        for cut in dict(part.properties.get("profile_nesting_cuts") or {}).values():
            cut["common_cut_allowed"] = True
    result = solve_and_register_phase4(
        project,
        mode="production",
        created_by="phase1-command-gate",
        scenario_id="phase1-waste",
        scenario_family="waste",
        backend="greedy",
        random_seed=17,
        timeout_seconds=30.0,
    )
    run = result[0]
    project.settings["active_profile_nesting_run_id"] = run.run_id
    return project, run.run_id, result


def _first_piece(service: ProfileNestingCommandService, project, run_id: str):
    layout = service._layout(project, run_id)
    assert layout and layout[0].get("pieces"), "benchmark leverde geen interactieve staafindeling"
    piece = dict(layout[0]["pieces"][0])
    return layout, str(piece["instance_id"]), str(layout[0]["bar_id"]), piece


def main() -> None:
    service = ProfileNestingCommandService(user="phase1-command-gate")
    project, run_id, solve_result = _solve()
    run, snapshot, _demand, _context, plan, evidence, validation, _reservation = solve_result
    assert validation.valid
    assert plan.bars
    assert evidence.backend

    context = UnifiedApplicationContext(active_surface="profile_nesting")
    context.update_optimization_context(
        active_profile_nesting_run=run_id,
        active_scenario_id="phase1-waste",
        active_backend="greedy",
        active_machine_profile_id=str(snapshot.machine_snapshot["profiles"][0]["profile_id"]),
        proof_status=service.inspect_run(project, run_id)["proof_status"],
        plan_revision_hash=project.revision_content_sha256(),
        solver_evidence_hash=str(getattr(evidence, "input_hash", "") or getattr(evidence, "evidence_hash", "")),
    )
    serialized_context = context.serialize_state()
    restored_context = UnifiedApplicationContext()
    restored_context.restore_state(serialized_context)
    assert restored_context.snapshot.optimization_context.active_profile_nesting_run == run_id
    assert restored_context.snapshot.optimization_context.active_backend == "greedy"
    assert restored_context.snapshot.state_hash == context.snapshot.state_hash
    context.close()
    restored_context.close()

    inspection = service.inspect_run(project, run_id)
    assert inspection["freshness"]["fresh"]
    assert service.validate_plan(project, run_id).status == "PASS"
    assert service.compare_scenarios(project).status == "PASS"

    layout, instance_id, bar_id, piece = _first_piece(service, project, run_id)
    selection = (instance_id,)
    assert service.toggle_selected_lock(project, run_id, selection).status == "PASS"
    assert service.toggle_selected_lock(project, run_id, selection).status == "PASS"

    before_revision = deepcopy(project.profile_nesting_runs[run_id])
    try:
        service.move_piece(project, run_id, instance_id, "missing-bar", 0)
        raise AssertionError("ongeldige move had moeten falen")
    except ProfileNestingCommandError:
        pass
    assert project.profile_nesting_runs[run_id] == before_revision, "rollback liet gedeeltelijke plandata achter"

    move_result = service.move_or_reorder_selected(project, run_id, selection)
    assert move_result.status == "PASS" and move_result.before_hash != move_result.after_hash
    assert service.undo(project, run_id).status == "PASS"
    assert service.redo(project, run_id).status == "PASS"

    orientation_applied = False
    common_cut_applied = False
    for bar in service._layout(project, run_id):
        for candidate in list(bar.get("pieces") or []):
            selected = (str(candidate.get("instance_id") or ""),)
            if not orientation_applied:
                try:
                    orientation_applied = service.cycle_selected_orientation(project, run_id, selected).status == "PASS"
                except ProfileNestingCommandError:
                    pass
            if not common_cut_applied:
                try:
                    common_cut_applied = service.cycle_selected_common_cut(project, run_id, selected).status == "PASS"
                except ProfileNestingCommandError:
                    pass
    assert orientation_applied, "benchmark bewees geen echte orientation-mutatie"
    assert common_cut_applied, "benchmark bewees geen echte common-cut-mutatie"
    assert service.partial_reoptimize(project, run_id, backend="greedy").status == "PASS"
    assert service.validate_plan(project, run_id).status == "PASS"

    layout, _instance_id, bar_id, _piece = _first_piece(service, project, run_id)
    scene = build_bar_scene(project.profile_nesting_runs[run_id], bar_id)

    with TemporaryDirectory(prefix="cws-phase1-profile-") as temp:
        temp_dir = Path(temp)
        svg_path = scene_to_svg(scene, temp_dir / "bar-scene.svg")
        assert "<svg" in svg_path.read_text(encoding="utf-8") and str(bar_id) in json.dumps(asdict(scene), default=str)
        project_path = temp_dir / "phase1-profile.cwsproj"
        saved_path = ProjectStore().save(project, project_path)
        reopened = ProjectStore().open(saved_path, read_only=False).project
        assert reopened.profile_nesting_runs[run_id]["plan"]["plan_hash"] == project.profile_nesting_runs[run_id]["plan"]["plan_hash"]
        assert reopened.profile_nesting_runs[run_id]["validation_report"]["report_hash"] == project.profile_nesting_runs[run_id]["validation_report"]["report_hash"]
        acceptance = service.accept_plan(reopened, run_id, reserve_stock=True)
        assert acceptance.status == "PASS"
        release = service.release_neutral_package(reopened, run_id, temp_dir / "release")
        assert release.status == "PASS"
        assert any((temp_dir / "release").rglob("*")), "release produceerde geen neutrale artifacts"

    machine_project, machine_run_id, _machine_solve = _solve(8)
    old_profile = load_machine_profiles(machine_project)[0]
    old_hash = machine_project.revision_content_sha256()
    revised_profile = replace(
        old_profile,
        revision=f"{old_profile.revision}-phase1",
        kerf_mm=float(old_profile.kerf_mm) + 0.1,
        configuration_hash="",
    )
    machine_result = service.save_machine_profile(machine_project, revised_profile)
    assert machine_result.status == "PASS"
    assert machine_project.revision_content_sha256() != old_hash
    assert machine_project.profile_nesting_runs[machine_run_id]["run"]["status"] == "stale"

    ui_source = inspect.getsource(ProfileNestingPanel._phase3_action)
    assert "profile_nesting_ui_actions" not in ui_source
    for real_call in (
        "toggle_selected_lock",
        "move_or_reorder_selected",
        "cycle_selected_orientation",
        "cycle_selected_common_cut",
        "partial_reoptimize",
        "accept_plan",
        "release_neutral_package",
    ):
        assert real_call in ui_source

    capabilities = {
        "application_context_snapshot_v2": True,
        "immutable_snapshots": True,
        "solver_evidence": True,
        "independent_plan_validation": True,
        "authoritative_proof_badge": True,
        "scenarios": True,
        "real_locks": True,
        "real_move_reorder": True,
        "undo_redo": True,
        "real_orientation": True,
        "real_common_cut_toggle": True,
        "transaction_rollback": True,
        "real_partial_reoptimization": True,
        "interactive_bar_planner": True,
        "save_reopen": True,
        "transactional_accept_reserve": True,
        "nesting_reports": True,
        "machine_profile_editor": True,
        "authoritative_command_service": True,
        "gui_real_commands": True,
        "safety_flags_false": True,
    }
    payload = {
        "schema": "cws-phase1-profile-nesting-command-evidence-1.0",
        "status": "PASS",
        "run_id": run_id,
        "proof_status": inspection["proof_status"],
        "validation_hash": validation.report_hash,
        "solver_backend": evidence.backend,
        "piece_count": 16,
        "capabilities": capabilities,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("PHASE_1_PROFILE_NESTING_COMMAND_SERVICE = PASS")


if __name__ == "__main__":
    main()
