"""Actual multi-selection mutation outcomes, including a non-selected control."""
from __future__ import annotations
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

FIELDS = {"edit.mark": "part_position", "edit.phase": "phase", "edit.classification": "category",
          "edit.orientation": "production_orientation", "edit.revision": "revision", "edit.comment": "bom_comment"}
ACTIONS = tuple(FIELDS) + ("edit.assembly_add", "edit.assembly_remove", "purchase.edit", "purchase.release", "purchase.cancel",
                           "machine.assign", "machine.manual_lock", "machine.reset")
SOURCE_FILES = ("tests/bom_w18_multi_execution_smoke.py", "tests/bom_w18_positive_matrix_smoke.py",
                "cws_convertor/ui_qt/bom_workspace.py", "cws_convertor/bom/production_hub.py",
                "cws_convertor/bom/freshness.py", "cws_convertor/bom/engine.py", "cws_convertor/bom/workspace.py",
                "cws_convertor/project/model.py", "cws_convertor/project/storage.py", "cws_convertor/machine_routing.py")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def run_case(action, folder, app):
    from PySide6 import QtWidgets
    from bom_w18_positive_matrix_smoke import _fixture
    from cws_convertor.bom import build_bom_snapshot
    from cws_convertor.bom.production_hub import BOMHubState
    from cws_convertor.machine_routing import MachineRoutingService
    from cws_convertor.project import ProjectStore
    from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    project = _fixture(action)
    key = "BUY2" if action.startswith("purchase.") else "P2"
    extra = deepcopy(project.get_entity(key))
    extra.internal_id = "BUY3" if key.startswith("BUY") else "P3"
    extra.name = extra.internal_id
    if key == "P2":
        extra.part_position = extra.internal_id
        extra.length_mm += 50
        extra.assembly_ids, extra.quantity_per_assembly = [], {}
        extra.recompute_hashes()
    project.add_entity(extra)
    ids = ("BUY1", "BUY2") if key.startswith("BUY") else ("P1", "P2")
    if action == "edit.assembly_remove":
        project.assemblies["A1"].part_ids = ["P1", "P2"]
        project.parts["P2"].assembly_ids.append("A1")
        project.parts["P2"].quantity_per_assembly["A1"] = 1
    project = ProjectStore().open(ProjectStore().save(project, folder / "input.cwscproj")).project
    workspace = SimpleNamespace(project=project, bom_snapshot=build_bom_snapshot(project, classify_if_needed=False),
                                session=SimpleNamespace(project=project, dirty=False))
    selected = SimpleNamespace(entity_ids=ids, primary_entity_id=ids[0])
    host = QtWidgets.QMainWindow()
    host.project_page = None
    host.application_context = SimpleNamespace(workspace=workspace, selection=selected,
        request_selection=lambda *args, **kw: None, clear_selection=lambda **kw: None)
    messages, checks = [], []
    expected = "reference" if action == "edit.classification" else "rotated_90" if action == "edit.orientation" else "W18-multiple"
    def check(name, value):
        assert value, name + " | " + repr(messages[-2:])
        checks.append({"name": name, "status": "PASS"})
    def message(*args, **kwargs):
        messages.append(str(args[2] if len(args) > 2 else args))
        return QtWidgets.QMessageBox.StandardButton.Yes
    def choice(*args, **kwargs):
        choices = args[3]
        value = "Leverancier" if action == "purchase.edit" else expected
        return (value if value in choices else choices[0], True)
    def machine_dialog(dialog):
        dialog.findChildren(QtWidgets.QComboBox)[0].setCurrentIndex(1)
        dialog.findChild(QtWidgets.QLineEdit).setText("Explicit synthetic multiple assignment")
        return QtWidgets.QDialog.DialogCode.Accepted
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(BomWorkspacePanel, "_restore_layout", lambda _self: None))
            for name in ("warning", "information", "question"):
                stack.enter_context(patch.object(QtWidgets.QMessageBox, name, message))
            stack.enter_context(patch.object(QtWidgets.QInputDialog, "getText", return_value=(expected, True)))
            stack.enter_context(patch.object(QtWidgets.QInputDialog, "getItem", side_effect=choice))
            if action == "machine.assign":
                stack.enter_context(patch.object(QtWidgets.QDialog, "exec", machine_dialog))
            panel = BomWorkspacePanel(host)
            host.setCentralWidget(panel)
            panel.set_context(workspace, selected)
            if key.startswith("BUY"):
                panel.family_tabs.setCurrentIndex(next(i for i in range(panel.family_tabs.count()) if panel.family_tabs.tabData(i) == "purchase"))
                panel.set_context(workspace, selected)
            app.processEvents()
            panel._hub_state.data
            before = {entity.internal_id: asdict(entity) for entity in project.iter_entities()}
            routing = deepcopy(project.settings.get("machine_routing"))
            input_hash = digest(project.to_dict())
            panel._populate_action_matrix()
            qaction = panel._matrix_qactions[action]
            check("Multiple-selection shipping QAction enabled", qaction.isEnabled())
            qaction.trigger()
            app.processEvents()
            result = panel._hub_state.data["batch_results"][-1]
            check("Actual requested action completes", result["action"] == action and result["status"] == "passed")
            related = {"A1"} if action.startswith("edit.assembly_") else set()
            check("Exact selected mutation IDs plus explicit relationship target", set(result["changed_entity_ids"]) == set(ids) | related)
            after = {entity.internal_id: asdict(entity) for entity in project.iter_entities()}
            check("Every unselected unrelated canonical entity stays unchanged", all(before[k] == after[k] for k in before.keys() - set(ids) - related))
            if action in FIELDS:
                field = FIELDS[action]
                check("Both selected fields have requested value", all(getattr(project.get_entity(k), field, project.get_entity(k).properties.get(field)) == expected for k in ids))
            elif action.startswith("edit.assembly_"):
                exists = action.endswith("add")
                check("Both selected reciprocal memberships reflect intent", all((k in project.assemblies["A1"].part_ids) == exists
                    and ("A1" in project.parts[k].assembly_ids) == exists for k in ids))
            elif action.startswith("purchase."):
                if action == "purchase.edit":
                    check("Both selected suppliers changed", all(project.purchased_items[k].supplier == expected for k in ids))
                else:
                    state = "released" if action.endswith("release") else "cancelled"
                    check("Both selected purchase statuses changed", all(project.purchased_items[k].purchase_status == state for k in ids))
            else:
                assignments = MachineRoutingService.assignments(project)
                if action == "machine.reset":
                    check("Both selected assignments removed", all(k not in assignments for k in ids))
                elif action == "machine.manual_lock":
                    check("Both selected existing manual assignments locked", all(assignments[k].manual_lock for k in ids))
                else:
                    check("Both selected assignments use actual chosen machine and require review", all(assignments[k].assigned_machine_id == "W18-MACHINE"
                        and assignments[k].routing_status == "assigned_manual_review_required" for k in ids))
            saved = ProjectStore().save(project, folder / "after.cwscproj")
            reopened = ProjectStore().open(saved).project
            check("Real project package preserves actual result", {entity.internal_id: asdict(entity) for entity in reopened.iter_entities()} == after
                  and BOMHubState(reopened).data["batch_results"] == panel._hub_state.data["batch_results"])
            if action != "purchase.release":
                BOMHubState(reopened).undo_last()
                check("Undo after reopen restores selected and unrelated canonical entities", {entity.internal_id: asdict(entity) for entity in reopened.iter_entities()} == before)
                if action.startswith("machine."):
                    check("Undo restores complete routing state", reopened.settings.get("machine_routing") == routing)
            else:
                try:
                    BOMHubState(reopened).undo_last()
                except ValueError:
                    check("Released purchase cannot silently undo supplier commitment", True)
                else:
                    check("Released purchase undo must be locked", False)
            return {"action_id": action, "scenario": "valid_multiple", "status": "PASS", "executed": True,
                "qt_action_executed": True, "selected_ids": list(ids), "selection_widened": False, "nonselected_stable": True,
                "proven_scenarios": ["valid_multiple", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged", "save_reopen"],
                "restart": True, "undo": action != "purchase.release", "checks": checks, "input_hash": input_hash,
                "output_hash": hashlib.sha256(saved.read_bytes()).hexdigest(),
                "artifacts": [{"path": str(p.resolve()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in folder.iterdir() if p.is_file()]}
    finally:
        host.close()
        host.deleteLater()
        app.processEvents()


def run(output=None):
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    owned = tempfile.TemporaryDirectory(prefix="w18-multi-") if output is None else None
    folder = Path(owned.name) if owned else Path(output)
    folder.mkdir(parents=True, exist_ok=True)
    sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_FILES}
    actions = [run_case(action, folder / action, app) for action in ACTIONS]
    from cws_convertor.product import APP_VERSION
    report = {"schema": "cws-w18-multiple-execution-1", "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "app_version": APP_VERSION, "environment": {"python": sys.version, "os": platform.platform(), "qt": "offscreen", "synthetic": True},
        "sources": sources, "source_unchanged_during_run": sources == {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_FILES},
        "input_hash": digest(sources), "scenario": "Shipping multiple-selection mutation outcomes", "result": "PASS",
        "output_hash": digest(actions), "actions": actions, "artifacts_retained": owned is None}
    if not report["source_unchanged_during_run"]:
        report["result"] = "FAIL"
    (folder / "MULTIPLE_EXECUTION.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    if owned:
        owned.cleanup()
    return report


if __name__ == "__main__":
    report = run(sys.argv[1] if len(sys.argv) > 1 else None)
    print(json.dumps({"result": report["result"], "scenarios": len(report["actions"])}))
    raise SystemExit(0 if report["result"] == "PASS" else 1)
