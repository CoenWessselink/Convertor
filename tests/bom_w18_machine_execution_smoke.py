"""Shipping automatic-routing QAction with computed M5 software evidence.

Synthetic geometry and machine facts are explicit; six real M5 mark decisions
are evaluated. This proves software routing, never physical machine acceptance.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")


def _fixture():
    import viewer_v15_machine_capability_smoke as m5_fixture
    from viewer_v15_machine_capability_smoke import ViewerV15MachineCapabilityTests
    from cws_convertor.project import ProjectModel, Part
    part = m5_fixture._part()
    part.material = part.material_grade = part.normalized_material = "S355J2"
    part.material_confidence = 1
    part.recompute_hashes()
    fixture = ViewerV15MachineCapabilityTests()
    with patch.object(m5_fixture, "_part", return_value=part):
        fixture.setUp()
    part = fixture.part
    part.classification_status = "confirmed"
    part.classification_confidence = 1
    machine = fixture._machine()
    report = fixture._evaluate(machine)
    assert report.ready_for_neutral_job and len(report.decisions) == 6
    assert not report.machine_transfer_allowed
    project = ProjectModel.new("Explicit synthetic M5 routing acceptance")
    project.add_entity(part)
    project.add_entity(machine)
    second = Part(internal_id="P-OTHER", part_position="OTHER", profile="HEA200", length_mm=100,
                  material="S355J2", material_grade="S355J2", normalized_material="S355J2", material_confidence=1,
                  classification_status="confirmed", classification_confidence=1)
    second.recompute_hashes()
    project.add_entity(second)
    project.settings["manufacturing_machine_capabilities"] = {part.internal_id: {machine.machine_id: report.to_dict()}}
    return project, fixture, machine


def run_case(action, folder, app, scenario="valid_single"):
    from PySide6 import QtWidgets
    from cws_convertor.bom import build_bom_snapshot
    from cws_convertor.bom.production_hub import BOMHubState
    from cws_convertor.machine_routing import MachineRoutingService
    from cws_convertor.project import ProjectStore
    from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
    assert action == "machine.auto_accept"
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    project, fixture, machine = _fixture()
    key = fixture.part.internal_id
    report = project.settings["manufacturing_machine_capabilities"][key][machine.machine_id]
    ids = (key,)
    if scenario == "valid_multiple":
        from viewer_v15_machine_capability_smoke import _face_report
        from cws_convertor.manufacturing.machine_capability import MachineCapabilityEvaluator
        second = project.parts["P-OTHER"]
        second_report = MachineCapabilityEvaluator(machine).evaluate(second, _face_report(second))
        assert second_report.ready_for_neutral_job
        project.settings["manufacturing_machine_capabilities"][second.internal_id] = {machine.machine_id: second_report.to_dict()}
        ids = (key, second.internal_id)
    elif scenario == "stale":
        project.parts[key].length_mm += 1
        project.parts[key].recompute_hashes()
    elif scenario == "invalid":
        report["part_id"] = "P-OTHER"
    elif scenario == "machine_profile_stale":
        machine.tools[0]["max_segment_length_mm"] = 1.0
    elif scenario == "blocked":
        blocked = fixture._evaluate(fixture._machine(operations=["saw"]))
        assert not blocked.ready_for_neutral_job
        project.settings["manufacturing_machine_capabilities"][key][machine.machine_id] = blocked.to_dict()
    elif scenario == "empty_selection":
        ids = ()
    elif scenario == "mixed_selection":
        ids = (key, "P-OTHER")
    elif scenario != "valid_single":
        raise ValueError(scenario)
    # Establish the canonical on-disk input schema before comparing mutations;
    # the normal loader adds its compatibility envelope on first import.
    project = ProjectStore().open(ProjectStore().save(project, folder / "input.cwscproj")).project
    snapshot = build_bom_snapshot(project, classify_if_needed=False)
    workspace = SimpleNamespace(project=project, bom_snapshot=snapshot, session=SimpleNamespace(project=project, dirty=False))
    selected = SimpleNamespace(entity_ids=ids, primary_entity_id=ids[0] if ids else None)
    host = QtWidgets.QMainWindow()
    host.project_page = None
    host.application_context = SimpleNamespace(workspace=workspace, selection=selected,
        request_selection=lambda *args, **kw: None, clear_selection=lambda **kw: None)
    host.workspace_router = SimpleNamespace(open_workspace=lambda _route: False)
    checks = []
    messages = []
    def check(name, value):
        assert value, name + ": " + repr(messages[-2:])
        checks.append({"name": name, "status": "PASS"})
    def modal(*args, **kw):
        messages.append(str(args[2] if len(args) > 2 else args))
        return QtWidgets.QMessageBox.StandardButton.Yes
    try:
        with patch.object(BomWorkspacePanel, "_restore_layout", lambda _self: None), \
                patch.object(QtWidgets.QMessageBox, "warning", modal), \
                patch.object(QtWidgets.QMessageBox, "information", modal):
            panel = BomWorkspacePanel(host)
            host.setCentralWidget(panel)
            panel.set_context(workspace, selected)
            app.processEvents()
            before = {entity.internal_id: asdict(entity) for entity in project.iter_entities()}
            routing_before = deepcopy(project.settings.get("machine_routing"))
            input_hash = hashlib.sha256(json.dumps(project.to_dict(), sort_keys=True).encode()).hexdigest()
            panel._populate_action_matrix()
            qaction = panel._matrix_qactions[action]
            if scenario in {"valid_single", "valid_multiple"}:
                check("Shipping automatic-routing QAction enabled", qaction.isEnabled())
            elif not ids:
                check("Empty selection disables action", not qaction.isEnabled())
            qaction.trigger()
            app.processEvents()
            positive = scenario in {"valid_single", "valid_multiple"}
            assignments = MachineRoutingService.assignments(project)
            results = panel._hub_state.data["batch_results"]
            check("Canonical entities including non-selected part and machine unchanged",
                  before == {entity.internal_id: asdict(entity) for entity in project.iter_entities()})
            if positive:
                check("Exactly selected parts assigned from current M5 report", set(assignments) == set(ids)
                      and all(value.routing_status == "ready" and value.assigned_machine_id == machine.machine_id for value in assignments.values()))
                check("Assignments bind actual evaluated reports", all(value.capability_report_sha256
                    and value.manufacturing_hash == project.parts[part_id].manufacturing_hash for part_id, value in assignments.items()))
                check("Canonical successful action result matches exact scope", results[-1]["action"] == action
                      and results[-1]["status"] == "passed" and set(results[-1]["changed_entity_ids"]) == set(ids))
                saved = ProjectStore().save(project, folder / "machine-assigned.cwscproj")
                reopened = ProjectStore().open(saved).project
                check("Actual project package reopen preserves current assignments", MachineRoutingService.assignments(reopened) == assignments)
                BOMHubState(reopened).undo_last()
                check("Undo after actual reopen restores assignment state", reopened.settings.get("machine_routing") == routing_before)
                restored = {entity.internal_id: asdict(entity) for entity in reopened.iter_entities()}
                check("Undo preserves all original canonical entities",
                      json.dumps(before, sort_keys=True) == json.dumps(restored, sort_keys=True))
            else:
                check("No partial or invalid automatic assignment is persisted", project.settings.get("machine_routing") == routing_before)
                check("Rejected acceptance cannot record success", not results or results[-1]["status"] != "passed")
            check("M5 computed evidence grants no physical transfer", not report["machine_transfer_allowed"])
            proof = {"action_id": action, "scenario": scenario, "status": "PASS", "executed": True,
                "positive_postcondition": positive, "qt_action_executed": True, "selected_ids": list(ids),
                "selection_widened": False, "nonselected_stable": True, "restart": positive, "undo": positive,
                "input_hash": input_hash, "checks": checks, "reason": "M5 software evidence from explicit synthetic machine/geometry facts; physical acceptance remains external."}
            proof["output_hash"] = hashlib.sha256(json.dumps(proof, sort_keys=True).encode()).hexdigest()
            (folder / "checks.json").write_bytes((json.dumps(proof, indent=2) + "\n").encode())
            proof["artifacts"] = [{"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                                  for path in folder.iterdir() if path.is_file()]
            return proof
    finally:
        host.close()
        app.processEvents()


def run():
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with tempfile.TemporaryDirectory(prefix="w18-machine-") as folder:
        for scenario in ("valid_single", "valid_multiple", "empty_selection", "blocked", "stale", "machine_profile_stale", "invalid", "mixed_selection"):
            run_case("machine.auto_accept", Path(folder) / scenario, app, scenario)
            print("BOM_W18_MACHINE " + scenario + " PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
