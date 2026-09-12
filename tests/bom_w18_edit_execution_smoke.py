"""Shipping BOM QAction -> Production Editor Save, on explicit synthetic input.

This verifies local software changes only, never supplier or machine approval.
"""
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
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


SOURCE_FILES = (
    "tests/bom_w18_edit_execution_smoke.py", "cws_convertor/ui_qt/functional_workspaces.py",
    "cws_convertor/ui_qt/bom_workspace.py", "cws_convertor/ui_qt/bom_action_dispatch.py",
    "cws_convertor/bom/production_hub.py", "cws_convertor/bom/workspace.py",
    "cws_convertor/project/workbench.py", "cws_convertor/project/storage.py",
    "cws_convertor/project/service.py", "cws_convertor/ui_qt/bom_export_evidence.py",
)


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def run(output: Path) -> dict:
    source_before = source_hashes()
    from PySide6 import QtWidgets
    from cws_convertor.bom import build_bom_snapshot
    from cws_convertor.bom.production_hub import BOMHubState
    from cws_convertor.project import ProjectModel, ProjectSession, ProjectStore, PurchasedItem
    from cws_convertor.project.workbench import roundtrip_is_current
    from cws_convertor.ui_qt.bom_export_evidence import _released_project
    from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
    from cws_convertor.ui_qt.functional_workspaces import EditWorkspacePanel

    output.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    base = _released_project(output / "synthetic-roundtrip", part_id="P1", part_position="P1")
    second = deepcopy(base.project.parts["P1"])
    second.internal_id = second.name = second.part_position = "P2"
    second.assembly_ids, second.quantity_per_assembly = [], {}
    second.workbench = {}
    second.nc1_eligible = False
    second.recompute_hashes()
    base.project.add_entity(second, user="synthetic-fixture")
    for key in ("BUY1", "BUY2"):
        base.project.add_entity(PurchasedItem(internal_id=key, name=key, material="S235JR", grade="S235JR",
                                             dimensions={"length_mm": 250.0}, quantity=2), user="synthetic-fixture")
    cases = []
    for kind, action, mode in (
        ("part", "edit.profile", "change"), ("part", "edit.material", "change"), ("part", "edit.length", "change"),
        ("purchase", "edit.material", "change"), ("purchase", "edit.length", "change"),
        ("purchase", "edit.material", "no_initial_length"),
        ("part", "edit.length", "stale_source"), ("part", "edit.length", "stale_selection"),
        ("part", "edit.length", "unchanged"), ("purchase", "edit.length", "readonly"),
        ("purchase", "edit.length", "no_project_path"),
        ("part", "edit.length", "save_io_failure"),
    ):
        folder = output / (kind + "-" + action + "-" + mode)
        folder.mkdir(exist_ok=True)
        project = ProjectModel.from_dict(base.project.to_dict())
        key = "P1" if kind == "part" else "BUY1"
        if mode == "no_initial_length":
            project.purchased_items[key].dimensions = {}
        session = ProjectSession(store=ProjectStore(), project=project)
        session.save(folder / "editor.cwscproj", embed_sources=False, user="synthetic-fixture")
        session.close()
        session = ProjectSession.open(folder / "editor.cwscproj")
        project = session.project
        workspace = SimpleNamespace(project=project, session=session,
                                    bom_snapshot=build_bom_snapshot(project, classify_if_needed=False))
        selection = SimpleNamespace(entity_ids=(key,), primary_entity_id=key)
        host = QtWidgets.QMainWindow()
        host.project_page = None
        host.application_context = SimpleNamespace(workspace=workspace, selection=selection,
            request_selection=lambda *args, **kw: None, clear_selection=lambda **kw: None)
        host.workspace_router = SimpleNamespace(open_workspace=lambda route: route == "edit")
        host.edit_page = EditWorkspacePanel(host)
        messages, checks = [], []
        def check(name, value):
            assert value, f"{kind}/{action}/{mode}: {name}; messages={messages[-3:]}"
            checks.append(name)
        def dialog(*args, **kwargs):
            messages.append(str(args[2] if len(args) > 2 else args))
            return QtWidgets.QMessageBox.StandardButton.Yes
        with ExitStack() as stack:
            stack.enter_context(patch.object(BomWorkspacePanel, "_restore_layout", lambda self: None))
            for name in ("information", "warning", "critical", "question"):
                stack.enter_context(patch.object(QtWidgets.QMessageBox, name, dialog))
            panel = BomWorkspacePanel(host)
            host.setCentralWidget(panel)
            try:
                panel.set_context(workspace, selection)
                if kind == "purchase":
                    panel.family_tabs.setCurrentIndex(next(i for i in range(panel.family_tabs.count())
                                                          if panel.family_tabs.tabData(i) == "purchase"))
                    panel.set_context(workspace, selection)
                app.processEvents()
                before = {entity.internal_id: deepcopy(asdict(entity)) for entity in project.iter_entities()}
                input_sha = digest(project.to_dict())
                panel._populate_action_matrix()
                qaction = panel._matrix_qactions[action]
                check("Shipping QAction enabled", qaction.isEnabled())
                qaction.trigger()
                app.processEvents()
                editor = host.edit_page
                check("Exact requested editor target and deferred result", editor._entity_id == key
                      and editor._bom_edit_binding["action"] == action
                      and panel._hub_state.data["batch_results"][-1]["status"] == "prepared")
                if kind == "purchase":
                    check("Purchase length loaded from canonical dimensions", editor.length.value() == (0 if mode == "no_initial_length" else 250))
                if mode != "unchanged":
                    if action == "edit.profile": editor.profile.setCurrentText("PL12")
                    elif action == "edit.material": editor.material.setCurrentText("S355J2")
                    else: editor.length.setValue(350)
                if mode == "stale_source":
                    project.parts["P2"].properties["unrelated_new_input"] = True
                elif mode == "stale_selection":
                    panel._selection = SimpleNamespace(entity_ids=("P2",), primary_entity_id="P2")
                elif mode == "readonly":
                    session.read_only = True
                elif mode == "no_project_path":
                    session.path = None
                elif mode == "save_io_failure":
                    stack.enter_context(patch.object(session, "save", side_effect=OSError("Injected disk write failure")))
                editor.save.click()
                app.processEvents()
                result = panel._hub_state.data["batch_results"][-1]
                negative = mode in {"stale_source", "stale_selection", "unchanged", "readonly", "no_project_path", "save_io_failure"}
                if negative:
                    check("Unsafe or no-op Save never passes", result["status"] == "failed")
                    check("Failed Save restores selected canonical entity", asdict(project.get_entity(key)) == before[key])
                    check("Failed Save never adds undo success", not panel._hub_state.data["undo"])
                    if mode == "save_io_failure":
                        with ProjectSession.open(session.path) as reopened:
                            check("Failed disk write preserves previously saved entity", asdict(reopened.project.get_entity(key)) == before[key])
                else:
                    check("Real Save completes canonical action", result["action"] == action and result["status"] == "passed")
                    check("Result mutation IDs remain exact", result["changed_entity_ids"] == [key])
                    check("Intent proves actual Save mutation", panel._hub_state.data["edit_intents"][action]["mutation_applied"])
                    entity = project.get_entity(key)
                    actual = entity.dimensions.get("length_mm") if kind == "purchase" and action == "edit.length" else getattr(entity, action.split(".")[1] + ("_mm" if action == "edit.length" else ""))
                    check("Requested field actually changed", actual == {"edit.profile": "PL12", "edit.material": "S355J2", "edit.length": 350}[action])
                    check("Unselected canonical entities unchanged", all(asdict(project.get_entity(k)) == value for k, value in before.items() if k != key))
                    if kind == "part":
                        check("Manufacturing edits invalidate prior local review and roundtrip", entity.workbench["current_revision"]["review_status"] != "released"
                              and not entity.nc1_eligible and not roundtrip_is_current(entity))
                    if mode == "no_initial_length":
                        check("Material Save preserves absent purchase length", "length_mm" not in entity.dimensions)
                    with ProjectSession.open(session.path) as reopened:
                        check("Actual cwscproj reopen preserves canonical mutation", asdict(reopened.project.get_entity(key)) == asdict(entity))
                        reopened_state = BOMHubState(reopened.project)
                        reopened_state.undo_last(user="acceptance")
                        check("Undo after reopen restores selected canonical entity", asdict(reopened.project.get_entity(key)) == before[key])
                        check("Undo after reopen preserves all nonselected entities", all(asdict(reopened.project.get_entity(k)) == value for k, value in before.items() if k != key))
                cases.append({"action_id": action, "family": kind, "scenario": mode, "status": "PASS", "checks": checks,
                              "selected_ids": [key], "selection_widened": False, "input_sha256": input_sha,
                              "output_sha256": digest(project.to_dict()), "qt_action_executed": True,
                              "save_button_executed": True, "restart": not negative, "undo": not negative})
            finally:
                host.close()
                host.deleteLater()
                session.close()
                app.processEvents()
    source_after = source_hashes()
    result = {"schema": "cws-bom-editor-execution-1", "status": "PASS" if source_before == source_after else "STALE", "cases": cases,
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "python": sys.version, "platform": platform.platform(), "synthetic_input": True,
              "scope": "Local canonical software edit execution; no source/machine production release asserted",
              "source_hashes_before": source_before, "source_hashes_after": source_after,
              "source_hashes_unchanged": source_before == source_after, "source_hashes": source_after}
    (output / "result.json").write_bytes((json.dumps(result, indent=2) + "\n").encode("utf-8"))
    return result


if __name__ == "__main__":
    result = run(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts/w18-editor")
    print(json.dumps({"status": result["status"], "cases": len(result["cases"])}))
