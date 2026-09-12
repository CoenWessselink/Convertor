"""Action-specific W18 acceptance, using shipping Qt handlers and canonical data.

Every canonical action has a positive postcondition. Unimplemented scenarios are
PARTIAL; opening a workspace, enabling an action, or rejecting a synthetic input
never counts as its positive result. This is source/component evidence, not an
installed-main-window, native-GPU, physical-printer or machine acceptance claim.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

from cws_convertor.bom.production_hub import ACTION_DEFINITIONS, BOMHubState


# Explicitly describe the observable result, not a route name or enabled state.
POSTCONDITIONS = {
    "viewer.zoom": "Camera frames the exact selected geometry bounds.",
    "viewer.fit": "Camera fits the exact selected geometry bounds.",
    "viewer.isolate": "Only selected geometry remains visible; canonical geometry stays unchanged.",
    "viewer.ghost": "Unselected geometry becomes translucent; selected geometry remains opaque.",
    "viewer.hide": "Selected nodes become hidden; other node visibility stays unchanged.",
    "viewer.show_all": "Previously hidden nodes are visible again; canonical geometry stays unchanged.",
    "viewer.section": "A section plane intersects the selected geometry without changing canonical geometry.",
    "viewer.measure": "A measurement contains selected geometry references and the expected distance.",
    "inspect.properties": "The displayed properties match selected canonical entities.",
    "inspect.source": "Displayed source identity resolves the selected entity to its actual source object.",
    "inspect.assembly": "Displayed assembly membership matches the selected entity hierarchy.",
    "inspect.hashes": "Displayed geometry and manufacturing hashes match the selected entities.",
    "inspect.blockers": "Displayed blockers exactly match the selected rows.",
    "edit.profile": "Committed profile changes only selected entities and recomputes dependent state.",
    "edit.material": "Committed material changes only selected entities and recomputes dependent state.",
    "edit.length": "Committed length changes only selected entities and recomputes dependent state.",
    "edit.mark": "Only selected canonical marks change to W18-new.",
    "edit.phase": "Only selected entity phase changes to W18-new.",
    "edit.classification": "Only selected entity classification changes to reference.",
    "edit.assembly_add": "Selected parts and chosen assembly both gain reciprocal membership.",
    "edit.assembly_remove": "Selected parts and chosen assembly both lose reciprocal membership.",
    "edit.orientation": "The selected production orientation is applied to actual geometry and feature coordinates by a production consumer, with no unselected changes.",
    "edit.revision": "Only selected entity revision and revision status change to W18-new.",
    "edit.comment": "Only selected entity BOM comment changes to W18-new.",
    "drawing.open_part": "An actual selected-part drawing is rendered with its canonical identity.",
    "drawing.generate": "An actual selected drawing PDF is generated and independently read back.",
    "drawing.regenerate": "A changed drawing is regenerated, read back, and bound to the current revision.",
    "drawing.open_assembly": "An actual assembly drawing renders exactly its resolved member scope.",
    "drawing.preview": "An actual PDF/PNG preview depicts the selected canonical geometry.",
    "drawing.setup": "Committed sheet settings affect regenerated selected drawing output.",
    "drawing.format": "Committed sheet format appears in independently read drawing page dimensions.",
    "drawing.scale": "Committed scale changes selected drawing output and survives save/reopen.",
    "drawing.views": "Committed view choice changes actual selected drawing projections.",
    "drawing.dimension_check": "Actual selected drawing dimensions pass the linter without blocking issues.",
    "drawing.revision": "A new canonical drawing revision is created for the selected entity.",
    "drawing.approve": "The current selected drawing revision has a persisted released dimension document.",
    "drawing.batch_pdf": "Real selected-scope PDFs exist and independently exclude unselected entities.",
    "drawing.print": "A physical printer accepts and prints the current selected drawing.",
    "machine.recommend": "A fresh selected-only capability review contains recommendations without transfer authority.",
    "machine.explain": "A fresh selected-only review explains eligibility and stale/unbound evidence.",
    "machine.assign": "A selected-only manual assignment is persisted, with revalidation required.",
    "machine.auto_accept": "A selected-only automatic assignment uses current authoritative capability evidence.",
    "machine.manual_lock": "Only the selected existing manual assignment becomes locked.",
    "machine.reset": "Only the selected machine assignment is removed.",
    "machine.validate": "Selected-only capability evidence is reevaluated against current manufacturing hashes.",
    "machine.alternatives": "Selected-only alternative machines include eligibility and evidence binding.",
    "machine.blocker": "Displayed production blockers exactly match the selected rows.",
    "production.route": "The selected-only production route contains resolved parts and readiness decisions.",
    "production.operations": "The selected-only operation review contains the exact canonical operations.",
    "production.nc_preview": "An actual selected NC1/DSTV preview is parsed and matches the source operations.",
    "production.release": "The authorized selected release is committed by the real software release workflow and survives reopen.",
    "production.withdraw": "Only the selected entity release status becomes withdrawn.",
    "optimize.profile": "The real profile solver produces a selected-only complete cutting plan.",
    "optimize.plate": "The real plate solver places all selected quantities and no unselected quantities.",
    "optimize.trade_length": "The real solver uses chosen trade lengths for the exact selection.",
    "optimize.stock": "The real solver uses actual available stock for the exact selection.",
    "optimize.remnants_include": "The real solver includes eligible remnants for selected demand.",
    "optimize.remnants_exclude": "The real solver excludes remnants for selected demand.",
    "optimize.kerf": "Committed kerf changes an actual selected cutting plan including loss accounting.",
    "stock.plan": "Actual physical stock/remnant planning contains exactly the selected occurrences.",
    "stock.assign": "Selected-only physical stock allocation is reserved without double booking.",
    "stock.release": "The selected reservation releases its physical source and can be planned again.",
    "stock.shortage": "Displayed shortage equals the selected-only computed physical demand shortfall.",
    "purchase.generate": "A canonical purchase need is created for exactly the selected shortage.",
    "purchase.edit": "Only the selected canonical purchase supplier changes to W18-new.",
    "purchase.release": "Only selected purchase rows become released and their undo is locked.",
    "purchase.cancel": "Only selected purchase rows become cancelled with the supplied reason.",
    "optimize.alternatives": "Review contains actual declared selected alternatives without applying substitutions.",
    "optimize.compare": "Comparison uses two intact runs of exactly the selected scope and correct metric deltas.",
    "export.production": "Actual requested production artifacts parse successfully with exact selected scope.",
    "export.review": "Real XLSX/CSV/JSON/PDF/ZIP review artifacts match selected scope and manifest hashes.",
    "export.grouping": "Actual exports use the requested grouping and exact selected occurrence scope.",
    "export.nc1": "Actual selected NC1/DSTV output parses and matches canonical machining features.",
    "export.step": "Actual selected STEP output is independently parsed and geometry matches.",
    "export.ifc": "Actual selected IFC output is independently parsed and identities/geometry match.",
    "export.dxf": "Actual selected DXF output is independently parsed and geometry matches.",
    "export.pdf": "Actual selected PDF output is independently rendered and checked.",
    "export.xlsx": "Actual XLSX is reopened and contains only selected identities and quantities.",
    "export.csv": "Actual CSV is parsed and contains only selected identities and quantities.",
    "export.json": "Actual JSON is parsed and contains only selected identities and quantities.",
    "export.package": "Actual production package is validated with selected-only artifacts and hashes.",
    "export.occurrences": "Actual export contains only the selected occurrence within an aggregate group.",
    "export.per_part": "Actual files partition selected output by canonical part ID.",
    "export.per_mark": "Actual files partition selected output by mark without merging unrelated occurrences.",
    "export.per_assembly": "Actual packages partition selected output by assembly and exact member scope.",
    "export.per_machine": "Actual packages partition selected output by validated assigned machine.",
    "export.per_phase": "Actual packages partition selected output by phase/delivery.",
}
EXTERNAL_ACTIONS = {"drawing.print"}
SOURCE_FILES = (
    "tests/bom_w18_positive_matrix_smoke.py", "cws_convertor/bom/production_hub.py",
    "cws_convertor/bom/workspace.py", "cws_convertor/ui_qt/bom_workspace.py",
    "cws_convertor/ui_qt/bom_action_dispatch.py", "cws_convertor/ui_qt/bom_action_dispatch_base.py",
    "cws_convertor/machine_routing.py", "cws_convertor/project/storage.py",
    "cws_viewer/core/controller.py", "cws_viewer/core/session.py",
    "cws_convertor/ui_qt/v5_workspaces.py", "cws_convertor/optimization/plate_nesting/project_service.py",
    "cws_convertor/ui_qt/product_workspaces.py", "cws_convertor/ui_qt/phase3_workspaces.py",
    "cws_convertor/optimization/profile_nesting/phase5_job.py", "cws_convertor/optimization/profile_nesting/benchmark.py",
    "tests/bom_w18_negative_matrix_smoke.py",
    "tests/bom_w18_export_execution_smoke.py", "tests/bom_w18_edit_execution_smoke.py",
    "tests/bom_w18_drawing_execution_smoke.py", "cws_convertor/ui_qt/bom_export_evidence.py",
    "tests/bom_w18_machine_execution_smoke.py", "tests/viewer_v15_machine_capability_smoke.py",
    "tests/bom_w18_inspection_execution_smoke.py",
    "tests/bom_w18_freshness_smoke.py",
    "tests/bom_w18_multi_execution_smoke.py",
    "tests/bom_w18_kerf_execution_smoke.py",
    "tests/part_workbench_roundtrip_smoke.py", "tools/master_requirements_v2.py",
    "cws_convertor/ui_qt/functional_workspaces.py", "cws_convertor/project/service.py",
    "cws_convertor/project/roundtrip.py", "cws_convertor/project/workbench.py",
    "cws_viewer/export_center/service.py", "cws_convertor/production_export/verify.py",
)
# Bind transitive shipped Python implementations, not just visible UI adapters.
SOURCE_FILES = tuple(sorted(set(SOURCE_FILES).union(
    path.relative_to(ROOT).as_posix() for base in (ROOT / "cws_convertor", ROOT / "cws_viewer")
    for path in base.rglob("*.py")).union(path.name for path in ROOT.glob("*.py"))))
FIELDS = {
    "edit.mark": ("part_position", "W18-new"),
    "edit.phase": ("phase", "W18-new"),
    "edit.classification": ("category", "reference"),
    "edit.orientation": ("production_orientation", "rotated_90"),
    "edit.revision": ("revision", "W18-new"),
    "edit.comment": ("bom_comment", "W18-new"),
    "production.withdraw": ("release_status", "withdrawn"),
}
LOCAL_ACTIONS = set(FIELDS) | {
    "edit.assembly_add", "edit.assembly_remove", "stock.plan", "stock.assign", "stock.release",
    "stock.shortage", "purchase.generate", "purchase.edit", "purchase.release", "purchase.cancel",
    "machine.recommend", "machine.explain", "machine.validate", "machine.alternatives",
    "machine.assign", "machine.manual_lock", "machine.reset", "production.route", "production.operations",
    "optimize.alternatives", "optimize.compare", "inspect.properties", "inspect.blockers", "machine.blocker",
    "export.xlsx", "export.csv", "export.json", "export.review",
    "viewer.zoom", "viewer.fit", "viewer.isolate", "viewer.ghost", "viewer.hide", "viewer.show_all",
    "viewer.section", "viewer.measure", "optimize.plate", "optimize.remnants_include", "optimize.remnants_exclude",
    "optimize.profile", "optimize.trade_length", "optimize.stock",
}
PROFILE_ACTIONS = {"optimize.profile", "optimize.trade_length", "optimize.stock"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable_evidence_paths(value):
    """Make retained file/log references portable without rewriting file bytes."""
    if isinstance(value, list):
        return [portable_evidence_paths(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key in {"path", "log"} and isinstance(item, str) and item:
            path = Path(item)
            if path.is_absolute():
                resolved = path.resolve()
                if resolved.is_relative_to(ROOT):
                    item = resolved.relative_to(ROOT).as_posix()
        result[key] = portable_evidence_paths(item)
    return result


def fingerprint():
    payload = [asdict(item) for item in ACTION_DEFINITIONS]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def scenario_catalog():
    canonical = {item.action_id for item in ACTION_DEFINITIONS}
    assert len(canonical) == 87 and set(POSTCONDITIONS) == canonical
    return [{"action_id": item.action_id, "expected_postcondition": POSTCONDITIONS[item.action_id],
             "status": "BLOCKED_EXTERNAL" if item.action_id in EXTERNAL_ACTIONS else "PARTIAL",
             "executed": False, "qt_action_executed": False, "positive_postcondition": False,
             "selected_ids": [], "selection_widened": None, "nonselected_stable": False,
             "restart": False, "undo": False, "checks": [],
             "reason": "External printer/machine/operator acceptance is unavailable." if item.action_id in EXTERNAL_ACTIONS
             else "Positive execution/postcondition has not been demonstrated by this matrix."}
            for item in ACTION_DEFINITIONS]


def _entities(project):
    # Compare complete canonical JSON values, including Workbench revisions.
    # Runtime tuples and their serialized JSON arrays have the same identity.
    return json.loads(json.dumps({entity.internal_id: asdict(entity) for entity in project.iter_entities()}, sort_keys=True))


def helper(name):
    spec = importlib.util.spec_from_file_location("w18_" + name, ROOT / "tests" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fixture(action):
    from cws_convertor.project import Assembly, Fastener, Part, ProjectModel, PurchasedItem, Remnant, StockItem, Weld
    project = ProjectModel.new("W18 positive canonical fixture")
    for key, length in (("P1", 3000.0), ("P2", 2800.0)):
        value = Part(internal_id=key, name=key, part_position=key, profile="HEA200", normalized_profile="HEA200",
                     profile_type="I", material="S355J2", normalized_material="S355J2", material_grade="S355J2",
                     length_mm=length, quantity_total=1, mass_each_kg=80, surface_area_each_m2=1.5,
                     classification_status="confirmed", classification_confidence=1, profile_confidence=1,
                     material_confidence=1, geometry_descriptor={"bbox": [length, 200, 190]},
                     production_features=[{"kind": "hole", "diameter": 18, "face": "top"}],
                     properties={"phase": key + "-phase", "alternative_profiles": ["HEA220"]})
        value.recompute_hashes()
        project.add_entity(value)
    project.add_entity(Assembly(internal_id="A1", assembly_mark="A1", name="A1"))
    project.add_entity(Assembly(internal_id="A2", assembly_mark="A2", name="A2", part_ids=["P2"], main_part_id="P2"))
    project.parts["P2"].assembly_ids = ["A2"]
    project.parts["P2"].quantity_per_assembly = {"A2": 1}
    if action == "edit.assembly_remove":
        project.parts["P1"].assembly_ids = ["A1"]
        project.parts["P1"].quantity_per_assembly = {"A1": 1}
        project.assemblies["A1"].part_ids = ["P1"]
    for key in ("BUY1", "BUY2"):
        project.add_entity(PurchasedItem(internal_id=key, name=key, article_number=key, supplier=key + " supplier",
                                        material="8.8", quantity=4, unit_price=12.5, purchase_status="review_required"))
    project.add_entity(Fastener(internal_id="F1", name="M20", fastener_type="bolt", diameter_mm=20,
                                grade="8.8", length_mm=60, quantity=8, connected_part_ids=["P1", "P2"]))
    project.add_entity(Weld(internal_id="W1", name="fillet", weld_type="fillet", size_mm=6,
                            length_mm=240, connected_part_ids=["P1", "P2"]))
    if action != "purchase.generate" and action != "stock.shortage":
        project.add_entity(Remnant(internal_id="R1", name="R1", profile="HEA200", material="S355J2", grade="S355J2",
                                    remaining_length_mm=3200, minimum_reusable_mm=500, status="available"))
        project.add_entity(StockItem(internal_id="S1", name="S1", profile="HEA200", material="S355J2", grade="S355J2",
                                    stock_length_mm=6000, available_quantity=2, status="available"))
    if action in {"machine.manual_lock", "machine.reset"}:
        from cws_convertor.machine_routing import MachineRoutingService
        MachineRoutingService().assign(project, ("P1", "P2"), "W18-MACHINE", user="fixture", reason="test", manual_lock=False)
    if action == "machine.assign":
        from cws_convertor.project import MachineProfile
        project.add_entity(MachineProfile(internal_id="M1", machine_id="W18-MACHINE", name="Fixture machine", enabled=True))
    if action.startswith("viewer."):
        for key, left, length in (("P1", 0, 3000), ("P2", 10000, 2800)):
            project.parts[key].geometry_descriptor = {"bounding_box": {"minimum": [left, 0, 0], "maximum": [left + length, 200, 190]}}
            project.parts[key].recompute_hashes()
    if action in {"optimize.plate", "optimize.remnants_include", "optimize.remnants_exclude"}:
        selected = project.parts["P1"]
        selected.profile = selected.normalized_profile = "PL10"
        selected.part_type = "plate"
        selected.geometry_descriptor = {"bbox_mm": [3000, 200, 10]}
        selected.recompute_hashes()
        project.stock_items["S1"].plate_size_mm = [4000, 2000, 10]
        project.remnants["R1"].remaining_contour = {"outer_contour": [[0, 0], [3500, 0], [3500, 500], [0, 500]], "thickness_mm": 10}
    if action == "optimize.compare":
        from cws_convertor.optimization.plate_nesting.project_service import _record_digest
        selected = project.parts["P1"]
        selected.profile = selected.normalized_profile = "PL10"
        selected.part_type = "plate"
        selected.geometry_descriptor = {"bbox_mm": [3000, 200, 10]}
        selected.recompute_hashes()
        runs = {}
        for index, scope in ((1, ["P1"]), (2, ["P1"]), (3, ["P2"])):
            record = {"schema": "cws-project-plate-run-2", "project_id": project.project_id,
                      "inputs": {"entity_ids": scope}, "plan": {"run_id": str(index), "plan_sha256": str(index),
                      "utilization": index / 10, "scrap_area_mm2": 1000 - index * 100,
                      "cut_length_mm": 1000 - index * 10, "pierce_count": 10 - index}, "status": "reserved_planning"}
            record["record_sha256"] = _record_digest(record)
            runs[str(index)] = record
        project.settings["plate_nesting_runs"] = runs
    if action == "production.withdraw":
        project.parts["P1"].properties["release_status"] = "released"
    if action in PROFILE_ACTIONS:
        from cws_convertor.optimization.profile_nesting.benchmark import build_synthetic_benchmark_project
        benchmark = build_synthetic_benchmark_project(2, released_parts=False)
        for index, key in enumerate(("P1", "P2")):
            part = deepcopy(list(benchmark.parts.values())[index])
            part.internal_id = part.name = part.part_position = key
            part.assembly_ids = project.parts[key].assembly_ids
            part.quantity_per_assembly = project.parts[key].quantity_per_assembly
            part.quantity_total = 3 if key == "P1" else 1
            part.mass_each_kg, part.surface_area_each_m2 = 8, 1
            part.classification_status = "confirmed"
            part.classification_confidence = part.profile_confidence = part.material_confidence = 1
            part.recompute_hashes()
            project.parts[key] = part
        project.profile_nesting_machine_profiles.update(benchmark.profile_nesting_machine_profiles)
        project.profile_nesting_purchase_options.update(benchmark.profile_nesting_purchase_options)
        for value in (project.stock_items["S1"], project.remnants["R1"]):
            value.profile = "RHS100x50"
            value.material = value.grade = "S235JR"
            value.properties = {"profile_id": "RHS100x50", "section_hash": "sec-rhs100x50"}
    # Materialize schema defaults before comparing persisted entities; this is
    # the same canonical load normalization as a project entering the product.
    return ProjectModel.from_dict(project.to_dict())


def semantic_result(action, result):
    """Retain metadata regression evidence without claiming a production transform."""
    if action != "edit.orientation" or result.get("status") == "FAIL":
        return result
    result = dict(result)
    proven = set(result.get("proven_scenarios", ())) - {"valid_single", "valid_multiple", "positive_postcondition", "release_invalidation"}
    if result.get("executed") and result.get("checks") and all(check["status"] == "PASS" for check in result["checks"]):
        for name, asserted in (("exact_selected_ids", bool(result.get("selected_ids"))),
                ("no_unintended_widening", result.get("selection_widened") is False),
                ("non_selected_unchanged", result.get("nonselected_stable")),
                ("save_reopen", result.get("restart")), ("undo", result.get("undo"))):
            if asserted:
                proven.add(name)
    if result.get("scenario") in {"valid_single", "valid_multiple"}:
        result["scenario"] = "orientation_metadata_regression"
    result.update(status="PARTIAL", positive_postcondition=False, proven_scenarios=sorted(proven),
        reason="The actual QAction stores production_orientation metadata only. No production consumer applying the orientation to geometry and feature coordinates is proved; scope, persistence and undo checks cover that metadata transaction.")
    return result


def _execute_case(action, folder, app):
    from PySide6 import QtWidgets
    from cws_convertor.bom import build_bom_snapshot
    from cws_convertor.bom.production_hub import BOMScopeEngine, BOMStockAllocator
    from cws_convertor.bom.workspace import BOMWorkspaceReadModel
    from cws_convertor.integration.workspace import IntegratedProjectWorkspace
    from cws_convertor.project import ProjectStore
    from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
    from cws_convertor.machine_routing import MachineRoutingService

    project = _fixture(action)
    if action == "production.withdraw":
        from cws_convertor.ui_qt.bom_export_evidence import _released_project
        from cws_convertor.project import ProjectModel
        released = _released_project(folder / "synthetic-roundtrip", part_id="P1", part_position="P1", assembly_id="A1")
        released.project.parts["P2"] = project.parts["P2"]
        released.project.assemblies["A2"] = project.assemblies["A2"]
        project = ProjectModel.from_dict(released.project.to_dict())
        # Enter through the same persisted canonical precision contract as a
        # real opened project before comparing withdrawal and later undo.
        project = ProjectStore().open(ProjectStore().save(project, folder / "before.cwscproj")).project
    snapshot = build_bom_snapshot(project, classify_if_needed=False)
    ids = ("BUY1",) if action.startswith("purchase.") and action != "purchase.generate" else ("P1",)
    if action == "viewer.measure":
        ids = ("P1", "P2")
    if action == "stock.release":
        model = BOMWorkspaceReadModel(snapshot, project)
        row = next(row for row in model.family_rows("parts") if row.entity_ids == ("P1",))
        pf = BOMScopeEngine(model).preflight("stock", (row,), expected_snapshot_sha256=snapshot.snapshot_sha256,
                                            visible_rows=model.family_rows("parts"))
        state = BOMHubState(project)
        BOMStockAllocator.reserve_plan(project, state.data, BOMStockAllocator().plan(project, (row,)), pf)
        snapshot = build_bom_snapshot(project, classify_if_needed=False)
    workspace = SimpleNamespace(project=project, bom_snapshot=snapshot, session=SimpleNamespace(project=project, dirty=False))
    workspace.session.save = lambda **_kw: ProjectStore().save(project, folder / "solver-save.cwscproj")
    if action == "production.withdraw":
        from cws_convertor.project import ProjectSession
        workspace.session = ProjectSession(store=ProjectStore(), project=project)
    workspace.readiness_for_part = lambda key, formats=(): IntegratedProjectWorkspace.readiness_for_part(workspace, key, formats)
    host = QtWidgets.QMainWindow()
    host.project_page = None
    current = SimpleNamespace(entity_ids=ids, primary_entity_id=ids[0])
    host.application_context = SimpleNamespace(workspace=workspace, selection=current,
        request_selection=lambda *args, **kw: None, clear_selection=lambda **kw: None)
    host.workspace_router = SimpleNamespace(open_workspace=lambda _route: False)
    job_manager = None
    if action in {"optimize.compare", "optimize.plate", "optimize.remnants_include", "optimize.remnants_exclude"}:
        from cws_convertor.ui_qt.v5_workspaces import PlateNestingPanel
        from cws_convertor.project.jobs import JobManager
        host.job_manager = job_manager = JobManager(max_workers=1)
        host.plate_nesting_page = PlateNestingPanel(host)
        host.workspace_router.open_workspace = lambda route: route == "plate_nesting"
    if action in PROFILE_ACTIONS:
        from cws_convertor.ui_qt.phase3_workspaces import ProfileNestingPanel
        from cws_convertor.project.jobs import JobManager
        host.job_manager = job_manager = JobManager(max_workers=1)
        host.profiles_page = ProfileNestingPanel(host)
        host.workspace_router.open_workspace = lambda route: route == "profile_nesting"
    messages = []
    check_names = []
    def check(name, condition):
        assert condition, name + " | " + repr(messages[-3:])
        check_names.append(name)
    def dialog(*args, **kwargs):
        messages.append(str(args[2] if len(args) > 2 else args))
        return QtWidgets.QMessageBox.StandardButton.Yes
    def choose(*args, **kwargs):
        choices = args[3]
        desired = "Leverancier" if action == "purchase.edit" else FIELDS.get(action, (None, None))[1]
        return (desired if desired in choices else choices[0], True)
    def machine_dialog(dialog_widget):
        # Drive the actual assignment dialog's controls, never its executor.
        combos = dialog_widget.findChildren(QtWidgets.QComboBox)
        combos[0].setCurrentIndex(1)
        dialog_widget.findChild(QtWidgets.QLineEdit).setText("W18-new")
        return QtWidgets.QDialog.DialogCode.Accepted
    with ExitStack() as stack:
        stack.enter_context(patch.object(BomWorkspacePanel, "_restore_layout", lambda _self: None))
        for name in ("information", "warning", "question"):
            stack.enter_context(patch.object(QtWidgets.QMessageBox, name, dialog))
        stack.enter_context(patch.object(QtWidgets.QInputDialog, "getText", return_value=("W18-new", True)))
        stack.enter_context(patch.object(QtWidgets.QInputDialog, "getItem", side_effect=choose))
        stack.enter_context(patch.object(QtWidgets.QFileDialog, "getExistingDirectory", return_value=str(folder)))
        if action == "machine.assign":
            stack.enter_context(patch.object(QtWidgets.QDialog, "exec", machine_dialog))
        panel = BomWorkspacePanel(host)
        host.setCentralWidget(panel)
        try:
            panel.set_context(workspace, current)
            if ids[0].startswith("BUY"):
                panel.family_tabs.setCurrentIndex(next(index for index in range(panel.family_tabs.count())
                                                        if panel.family_tabs.tabData(index) == "purchase"))
                panel.set_context(workspace, current)
            app.processEvents()
            controller = None
            if action.startswith("viewer."):
                from cws_viewer.adapters import CwsProjectSceneAdapter
                from cws_viewer.backends.memory import MemoryRenderBackend
                from cws_viewer.core.controller import ViewerCoreController
                scene = CwsProjectSceneAdapter().build_scene(project)
                controller = ViewerCoreController(MemoryRenderBackend())
                controller.load_scene(scene)
                viewer_widget = QtWidgets.QWidget(panel.viewer)
                viewer_widget.controller = controller
                viewer_widget.backend = controller._backend
                panel.viewer._viewer = viewer_widget
                panel.viewer._nodes_by_entity = {key: tuple(node.node_id for node in scene.nodes if node.entity_id == key) for key in ids}
                panel.viewer._sync_selection()
                workspace.load_result = SimpleNamespace(scene=scene, repository={})
                if action == "viewer.show_all":
                    controller.hide(("entity:P1", "entity:P2"))
                controller.fit_all()
                camera_before = controller.get_camera()
            before = _entities(project)
            settings_before = deepcopy(project.settings)
            input_hash = hashlib.sha256(json.dumps(project.to_dict(), sort_keys=True).encode()).hexdigest()
            rows = tuple(panel._selected_rows())
            check("Exact selected canonical IDs before action", {key for row in rows for key in row.entity_ids} == set(ids))
            group_ids = {row.group_id for row in rows}
            panel._populate_action_matrix()
            qaction = panel._matrix_qactions[action]
            check("Shipping QAction enabled", qaction.isEnabled())
            qaction.trigger()
            app.processEvents()
            if action in PROFILE_ACTIONS:
                page = host.profiles_page
                deadline = time.monotonic() + 45
                while page._job_id and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.005)
                check("Real profile solver committed valid result", page._job_id is None and page._bom_last_solve_state == "committed")
                run = next(reversed(project.profile_nesting_runs.values()))
                plan = run["plan"]
                placed = [piece for bar in plan["bars"] for piece in bar["placements"]]
                check("Exact selected profile occurrences solved", len(placed) == 3 and {piece["part_id"] for piece in placed} == {"P1"}
                      and not plan["unassigned_instance_ids"])
                check("Independent solver validation and balanced material", run["validation_report"]["valid"]
                      and plan["material_balance"]["balance_delta_units"] == 0)
                if action == "optimize.trade_length":
                    check("Trade-length plan uses purchase catalog only", all(bar["source_type"] == "purchase_option" and bar["source_id"] == "bench-stock"
                          and bar["stock_length_units"] == 12000000 for bar in plan["bars"]))
                if action == "optimize.stock":
                    check("Stock plan uses only actual physical stock", all(bar["source_type"] == "full_stock" and bar["source_id"] == "S1" for bar in plan["bars"]))
            if action in {"optimize.plate", "optimize.remnants_include", "optimize.remnants_exclude"}:
                page = host.plate_nesting_page
                if action != "optimize.plate":
                    # The remnant action chooses a real solver option. Complete
                    # the normal solve after that choice, with the same scope.
                    page.solve()
                deadline = time.monotonic() + 45
                while page._job_id and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.005)
                check("Real plate solver completed", page._job_id is None and page._plan is not None)
                check("Plate solver placed only selected quantity", page._plan.placed_count == 1
                      and {value.part_id for layout in page._plan.layouts for value in layout.placements} == {"P1"})
                if action != "optimize.plate":
                    available = {page.inventory.item(index, 0).text() for index in range(page.inventory.rowCount())}
                    check("Actual solver inventory honors remnant choice", ("R1" in available) == action.endswith("include"))
            after = _entities(project)
            allowed_related = {"A1"} if action in {"edit.assembly_add", "edit.assembly_remove"} else set()
            if action in {"stock.assign", "stock.release"}:
                allowed_related.add("R1")
            stable_ids = set(before) - set(ids) - allowed_related
            check("All unselected unrelated canonical entities unchanged", all(before[key] == after[key] for key in stable_ids))
            if action.startswith("viewer."):
                selected_nodes = tuple("entity:" + key for key in ids)
                check("Viewer retains exact node selection", controller.get_selection() == selected_nodes)
                visible, ghosted = controller.session.visible_and_ghosted(controller.index)
                if action in {"viewer.zoom", "viewer.fit"}:
                    check("Camera target equals selected bounds center", controller.get_camera().target == controller.index.bounds_for(selected_nodes).center)
                    check("Camera changed from full-scene fit", controller.get_camera() != camera_before)
                elif action == "viewer.isolate":
                    check("Only selected renderable geometry visible", set(visible) == set(selected_nodes) and not ghosted)
                elif action == "viewer.ghost":
                    check("Selected geometry stays solid, context becomes ghosted", all(node in visible and node not in ghosted for node in selected_nodes)
                          and "entity:P2" in ghosted)
                elif action == "viewer.hide":
                    check("Selected geometry hidden and other part remains visible", "entity:P1" not in visible and "entity:P2" in visible)
                elif action == "viewer.show_all":
                    check("Previously hidden geometry restored", {"entity:P1", "entity:P2"}.issubset(visible))
                elif action == "viewer.section":
                    planes = tuple(controller.session.section_planes.values())
                    check("Real controller section at selected center", len(planes) == 1 and planes[0].origin == controller.index.bounds_for(selected_nodes).center)
                else:
                    measures = controller.list_measurements()
                    record = panel._hub_state.data["viewer_reviews"]["measure"]
                    check("Real controller owns selected distance measurement", len(measures) == 1 and record["entity_ids"] == list(ids))
                    check("Measured center distance equals 9900 mm", abs(float(measures[0].value) - 9900) < 1e-6)
                check("Viewer never changes canonical geometry", before == after)
                (folder / "viewer-state.json").write_text(json.dumps(controller.export_workspace_state().to_dict(), indent=2), encoding="utf-8")
            elif action in FIELDS:
                field, expected = FIELDS[action]
                entity = project.parts["P1"]
                actual = getattr(entity, field, entity.properties.get(field))
                check("Selected canonical field has expected committed value", actual == expected)
                if action == "edit.revision":
                    check("Revision status persisted together with revision", entity.properties["revision_status"] == expected)
                if action == "production.withdraw":
                    check("Real released Workbench production authority invalidated", before["P1"]["workbench"]["current_revision"]["review_status"] == "released"
                          and entity.workbench["current_revision"]["review_status"] != "released" and not entity.nc1_eligible)
            elif action in {"edit.assembly_add", "edit.assembly_remove"}:
                expected = action.endswith("add")
                check("Reciprocal part/assembly membership changed", ("P1" in project.assemblies["A1"].part_ids) == expected
                      and ("A1" in project.parts["P1"].assembly_ids) == expected
                      and ("A1" in project.parts["P1"].quantity_per_assembly) == expected)
            elif action.startswith("purchase."):
                if action == "purchase.generate":
                    added = set(project.purchased_items) - {"BUY1", "BUY2"}
                    check("Exactly one canonical purchase need created", len(added) == 1)
                    need = project.purchased_items[next(iter(added))]
                    check("Purchase need matches selected shortage", need.properties["source_bom_group"] in group_ids
                          and need.properties["required_length_mm"] == 3000)
                elif action == "purchase.edit":
                    check("Selected purchase supplier committed", project.purchased_items["BUY1"].supplier == "W18-new")
                else:
                    expected = "released" if action.endswith("release") else "cancelled"
                    check("Selected purchase status committed", project.purchased_items["BUY1"].purchase_status == expected)
                    if action.endswith("cancel"):
                        check("Cancellation reason committed", project.purchased_items["BUY1"].properties["purchase_cancel_reason"] == "W18-new")
            elif action == "machine.assign":
                assignments = MachineRoutingService.assignments(project)
                check("Manual assignment applies to exact selection", set(assignments) == {"P1"} and assignments["P1"].assigned_machine_id == "W18-MACHINE")
                check("Manual assignment requires revalidation", assignments["P1"].capability_status == "review_required"
                      and assignments["P1"].routing_status == "assigned_manual_review_required")
            elif action in {"machine.manual_lock", "machine.reset"}:
                assignments = MachineRoutingService.assignments(project)
                check("Unselected machine assignment unchanged", assignments["P2"].to_dict() == settings_before["machine_routing"]["assignments"]["P2"])
                check("Selected machine assignment changed", assignments["P1"].manual_lock if action.endswith("lock") else "P1" not in assignments)
            elif action.startswith("machine.") and action != "machine.blocker":
                review = panel._last_machine_review
                check("Fresh capability review has exact selected scope", review["action_id"] == action and review["entity_ids"] == ["P1"]
                      and [row["part_id"] for row in review["rows"]] == ["P1"])
                check("Capability review grants no release or transfer", not review["production_release_allowed"] and not review["machine_transfer_allowed"])
            elif action in {"production.route", "production.operations"}:
                record = panel._hub_state.data["production_reviews"][action.split(".")[1]]
                check("Production review resolves exact selected scope", record["source_entity_ids"] == ["P1"] and record["resolved_part_ids"] == ["P1"]
                      and record["selection_widened"] is False and record["production_release_allowed"] is False)
                if action.endswith("operations"):
                    check("Operation review includes selected hole", record["operation_count"] == 1)
                else:
                    check("Route evaluates selected part", record["workflow"]["part_count"] == 1)
            elif action in {"optimize.alternatives", "optimize.compare"}:
                if action.endswith("alternatives"):
                    record = panel._hub_state.data["optimization_reviews"]["alternatives"]
                    check("Actual selected alternatives reviewed without substitution", record["entity_ids"] == ["P1"]
                          and record["candidate_count"] == 1 and record["substitution_applied"] is False)
                else:
                    record = panel._hub_state.data["optimization_reviews"]["plate_compare"]
                    check("Comparison excludes unrelated latest run", record["previous_run_id"] == "1" and record["current_run_id"] == "2"
                          and record["entity_ids"] == ["P1"] and record["selection_widened"] is False)
                    check("Comparison computes correct metric delta", abs(record["metrics"]["utilization"]["delta"] - .1) < 1e-9
                          and record["metrics"]["scrap_area_mm2"]["delta"] == -100)
            elif action.startswith("stock."):
                if action == "stock.shortage":
                    check("Displayed exact selected shortage", any("Tekort in selectie: 3000 mm" in text or "Tekort in selectie: 3.000 mm" in text for text in messages))
                elif action == "stock.plan":
                    check("Physical plan displayed", any("R1" in text for text in messages))
                    plan = panel._stock_plan(rows)
                    check("Physical plan contains only selected occurrence", plan.complete and len(plan.allocations) == 1
                          and {piece.group_id for allocation in plan.allocations for piece in allocation.pieces} == group_ids)
                elif action == "stock.assign":
                    assigned = panel._hub_state.data["stock_assignments"]
                    check("Selected-only physical reservation committed", set(assigned) == group_ids and project.remnants["R1"].status == "reserved")
                    check("Reserved remnant cannot be booked again", all(value.source_id != "R1" for value in panel._stock_plan(rows).allocations))
                else:
                    check("Selected reservation released", not panel._hub_state.data["stock_assignments"] and project.remnants["R1"].status == "available")
                    check("Released remnant is plannable again", panel._stock_plan(rows).allocations[0].source_id == "R1")
            elif action == "inspect.properties":
                displayed = panel.detail_labels["properties"].text()
                check("Selected properties rendered from canonical data", "P1-phase" in displayed and "P2-phase" not in displayed and "HEA200" in displayed)
            elif action in {"inspect.blockers", "machine.blocker"}:
                blockers = tuple(dict.fromkeys(reason for row in rows for reason in row.blocking_reasons))
                check("Exact selected blockers displayed", panel.detail_labels["conflicts"].text() == ("\n".join(blockers) if blockers else "Geen blockers in de geselecteerde regels."))
            elif action.startswith("export."):
                result = panel._hub_state.data["batch_results"][-1]
                check("Exact export action completed", result["action"] == action and result["status"] == "passed")
                manifest_path = next(Path(value) for value in result["outputs"] if Path(value).name == "REVIEW_EXPORT.json")
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                check("Review manifest exact IDs and no production permission", manifest["scope"]["entity_ids"] == ["P1"]
                      and manifest["review_only"] and not manifest["machine_transfer_allowed"] and not manifest["production_release_allowed"])
                check("Actual output hashes match manifest", all(digest(manifest_path.parent / name) == value["sha256"] for name, value in manifest["files"].items()))
                if action in {"export.json", "export.review"}:
                    data = json.loads(next((manifest_path.parent / name for name in manifest["files"] if name.endswith("_BOM.json"))).read_text(encoding="utf-8"))
                    check("JSON reread has exact selected identities and quantities", {key for row in data["part_bom"] for key in row["part_ids"]} == {"P1"}
                          and sum(row["quantity"] for row in data["part_bom"]) == 1)
                if action in {"export.csv", "export.review"}:
                    import csv
                    with (manifest_path.parent / "part_bom.csv").open(encoding="utf-8-sig", newline="") as stream:
                        data = list(csv.DictReader(stream))
                    check("CSV reread has exact selected identities and quantity", len(data) == 1 and data[0]["part_ids"] == "P1" and data[0]["quantity"] == "1")
                if action in {"export.xlsx", "export.review"}:
                    import openpyxl
                    path = next(manifest_path.parent / name for name in manifest["files"] if name.endswith(".xlsx"))
                    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
                    try:
                        cells = [[value for row in sheet.iter_rows(values_only=True) for value in row] for sheet in book]
                        check("XLSX reread includes selected and excludes unrelated identity", any("P1" in values for values in cells)
                              and all("P2" not in values and "BUY2" not in values for values in cells))
                    finally:
                        book.close()
                if action == "export.review":
                    import fitz
                    import zipfile
                    pdf = next(manifest_path.parent / name for name in manifest["files"] if name.endswith(".pdf"))
                    with fitz.open(pdf) as document:
                        content = "\n".join(page.get_text() for page in document)
                        check("Review PDF independently renders exact selected identity", bool(document[0].get_pixmap().samples) and "P1" in content and "P2" not in content)
                    package = next(manifest_path.parent / name for name in manifest["files"] if name.endswith(".zip"))
                    with zipfile.ZipFile(package) as archive:
                        data = json.loads(archive.read(next(name for name in archive.namelist() if name.endswith("_BOM.json"))))
                        check("Review ZIP independently contains exact selected identities", {key for row in data["part_bom"] for key in row["part_ids"]} == {"P1"})
            results = panel._hub_state.data["batch_results"]
            if not action.startswith("viewer.") or action in {"viewer.section", "viewer.measure"}:
                check("Action records selected-only batch groups", bool(results) and set(results[-1]["eligible_group_ids"]) == group_ids)
            if action in FIELDS or action in {"edit.assembly_add", "edit.assembly_remove", "stock.assign", "stock.release",
                    "purchase.generate", "purchase.edit", "purchase.release", "purchase.cancel", "machine.assign", "machine.manual_lock", "machine.reset"}:
                check("Canonical action result records successful transaction", results[-1]["action"] == action and results[-1]["status"] == "passed")
            saved = ProjectStore().save(project, folder / "after.cwscproj")
            reopened = ProjectStore().open(saved).project
            check("Real project package reopen preserves canonical entities", _entities(reopened) == after)
            reopened_state = BOMHubState(reopened)
            check("Real project package reopen preserves action result", reopened_state.data["batch_results"] == results)
            check("Real project package reopen preserves complete hub state", reopened_state.data == panel._hub_state.data)
            if action in PROFILE_ACTIONS:
                from cws_convertor.optimization.profile_nesting.angle_validator import validate_angle_plan
                from cws_convertor.optimization.profile_nesting.serialization import input_snapshot_from_dict, plan_from_dict
                restored_run = next(reversed(reopened.profile_nesting_runs.values()))
                check("Profile plan and independent validation survive actual reopen", restored_run["plan"]["plan_hash"] == run["plan"]["plan_hash"]
                      and restored_run["input_snapshot"]["snapshot_hash"] == run["input_snapshot"]["snapshot_hash"]
                      and restored_run["validation_report"]["report_hash"] == run["validation_report"]["report_hash"])
                check("Reopened profile output independently revalidates", validate_angle_plan(
                    input_snapshot_from_dict(restored_run["input_snapshot"]), plan_from_dict(restored_run["plan"])).valid)
            if action.startswith("machine."):
                check("Machine assignments survive actual reopen", reopened.settings.get("machine_routing") == project.settings.get("machine_routing"))
            definition = next(item for item in ACTION_DEFINITIONS if item.action_id == action)
            undo = False
            if definition.mutating and action != "purchase.release":
                reopened_state.undo_last()
                check("Undo after restart restores all original canonical entities", _entities(reopened) == before)
                if action in {"machine.assign", "machine.manual_lock", "machine.reset"}:
                    check("Undo restores original machine assignments", reopened.settings.get("machine_routing") == settings_before.get("machine_routing"))
                undo = True
            elif action == "purchase.release":
                try:
                    reopened_state.undo_last()
                except ValueError as exc:
                    check("Released purchase rejects undo after reopen", "vrijgave" in str(exc).casefold())
                else:
                    raise AssertionError("Externally released purchase unexpectedly allowed undo")
            return semantic_result(action, {"status": "PASS", "executed": True, "qt_action_executed": True,
                    "positive_postcondition": True, "selected_ids": list(ids), "selection_widened": False,
                    "nonselected_stable": True, "restart": not action.startswith("viewer."), "undo": undo,
                    "input_hash": input_hash, "output_hash": digest(saved),
                    "artifacts": [{"path": str(path.resolve()), "sha256": digest(path)} for path in folder.rglob("*") if path.is_file()],
                    "renderer": "memory-v2 controller state; native GPU not proved" if controller else None,
                    "proven_scenarios": ["release_invalidation"] if action == "production.withdraw" else [],
                    "checks": [{"name": name, "status": "PASS"} for name in check_names], "reason": ""})
        finally:
            host.close()
            host.deleteLater()
            app.processEvents()
            if job_manager is not None:
                job_manager.shutdown(wait=True)


def run(output=None):
    sources_before = {name: digest(ROOT / name) for name in SOURCE_FILES}
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    actions = scenario_catalog()
    negative = None
    with ExitStack() as stack:
        if output:
            temp = Path(output).resolve().parent / (Path(output).stem + "-artifacts-" + uuid4().hex[:8])
            temp.mkdir(parents=True)
        else:
            temp = stack.enter_context(tempfile.TemporaryDirectory(prefix="cws-w18-positive-"))
        negative_process = subprocess.run([sys.executable, str(ROOT / "tests/bom_w18_negative_matrix_smoke.py")],
                                          cwd=ROOT, capture_output=True, env=dict(os.environ, PYTHONUTF8="1"))
        negative_log = Path(temp) / "negative-matrix.txt"
        negative_log.write_bytes(negative_process.stdout + b"\n" + negative_process.stderr)
        negative_text = negative_log.read_text(encoding="utf-8", errors="replace")
        negative = {"result": "PASS" if negative_process.returncode == 0 and "BOM_W18_EMPTY_SELECTION_NEGATIVE = 87/87 PASS" in negative_text else "FAIL",
                    "returncode": negative_process.returncode, "scenario": "tests/bom_w18_negative_matrix_smoke.py",
                    "source_sha256": digest(ROOT / "tests/bom_w18_negative_matrix_smoke.py"),
                    "log": str(negative_log.resolve()), "output_hash": digest(negative_log)}
        freshness_process = subprocess.run([sys.executable, str(ROOT / "tests/bom_w18_freshness_smoke.py")],
            cwd=ROOT, capture_output=True, env=dict(os.environ, PYTHONUTF8="1"))
        freshness_log = Path(temp) / "freshness-matrix.txt"
        freshness_log.write_bytes(freshness_process.stdout + b"\n" + freshness_process.stderr)
        freshness_text = freshness_log.read_text(encoding="utf-8", errors="replace")
        markers = ["BOM_W18_FRESHNESS_" + mode + " = 87/87 PASS" for mode in ("STALE", "MISSING_BINDING", "CORRUPT_SNAPSHOT")]
        freshness = {"result": "PASS" if freshness_process.returncode == 0 and all(marker in freshness_text for marker in markers) else "FAIL",
            "returncode": freshness_process.returncode, "scenario": "tests/bom_w18_freshness_smoke.py",
            "source_sha256": digest(ROOT / "tests/bom_w18_freshness_smoke.py"),
            "log": str(freshness_log.resolve()), "output_hash": digest(freshness_log)}
        exports = helper("bom_w18_export_execution_smoke")
        for row in actions:
            action = row["action_id"]
            if action not in LOCAL_ACTIONS | exports.EXPORT_ACTIONS:
                continue
            folder = Path(temp) / action
            folder.mkdir()
            try:
                row.update(exports.run_case(action, folder, app) if action in exports.EXPORT_ACTIONS else _execute_case(action, folder, app))
            except Exception as exc:
                row.update(status="FAIL", executed=True, reason=f"{type(exc).__name__}: {exc}")
            print(action + " = " + row["status"] + (" | " + row["reason"] if row["reason"] else ""), flush=True)
        # These independent suites execute real downstream controls and retain
        # their own action/scenario evidence; no suite-wide PASS is propagated.
        drawing = helper("bom_w18_drawing_execution_smoke").run(Path(temp) / "drawing.json")
        editor = helper("bom_w18_edit_execution_smoke").run(Path(temp) / "editor")
        inspection = helper("bom_w18_inspection_execution_smoke").run(Path(temp) / "inspection.json")
        multiple = helper("bom_w18_multi_execution_smoke").run(Path(temp) / "multiple")
        kerf = helper("bom_w18_kerf_execution_smoke").run(Path(temp) / "kerf")
        machine_cases = [helper("bom_w18_machine_execution_smoke").run_case("machine.auto_accept", Path(temp) / "machine-auto" / scenario, app, scenario)
                         for scenario in ("valid_single", "valid_multiple", "empty_selection", "blocked", "stale", "invalid", "mixed_selection")]
        for row in actions:
            action = row["action_id"]
            if action == "optimize.kerf":
                row.update(kerf["actions"][0])
            elif action == "machine.auto_accept":
                row.update(machine_cases[0])
                row.update(cases=machine_cases, proven_scenarios=[case["scenario"] for case in machine_cases],
                    checks=[check for case in machine_cases for check in case["checks"]],
                    artifacts=[artifact for case in machine_cases for artifact in case["artifacts"]])
            elif action.startswith("drawing.") or action in {"inspect.source", "inspect.assembly", "inspect.hashes"}:
                suite = drawing if action.startswith("drawing.") else inspection
                cases = [case for case in suite["actions"] if case["action_id"] == action]
                if action == "drawing.regenerate":
                    # Require the changed canonical source case; repeated
                    # rendering of unchanged geometry cannot satisfy this.
                    cases = [case for case in cases if {"release_invalidation", "save_reopen"}.issubset(case["scenarios"])]
                if not cases:
                    continue
                positive = suite["result"] == "PASS" and all(case["positive_postcondition"] and case["selection_widened"] is False and case["nonselected_stable"] for case in cases)
                row.update(executed=True, qt_action_executed=action.startswith("inspect."), positive_postcondition=positive,
                    selected_ids=list(dict.fromkeys(key for case in cases for key in case["selected_ids"])),
                    selection_widened=False if all(case["selection_widened"] is False for case in cases) else None,
                    nonselected_stable=all(case["nonselected_stable"] for case in cases),
                    restart=all(case["restart"] for case in cases), undo=all(case["undo"] for case in cases),
                    checks=[check for case in cases for check in case["checks"]],
                    artifacts=[artifact for case in cases for artifact in case["outputs"]],
                    execution_layer="Actual downstream dispatcher/drawing panel; no shipping QAction claim" if action.startswith("drawing.") else "Actual shipping inspector QAction", cases=cases,
                    proven_scenarios=sorted(set(name for case in cases for name in case["scenarios"])),
                    status="BLOCKED_EXTERNAL" if action == "drawing.print" else "PASS" if positive else "PARTIAL",
                    reason="Physical printer acceptance unavailable." if action == "drawing.print" else "")
            elif action in {"edit.profile", "edit.material", "edit.length"}:
                cases = [case for case in editor["cases"] if case["action_id"] == action]
                successful = [case for case in cases if case["restart"] and case["undo"]]
                positive = bool(successful) and editor["status"] == "PASS"
                proven = ["valid_single", "positive_postcondition", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged", "save_reopen", "undo", "release_invalidation"] if positive else []
                if any(case["scenario"] == "stale_source" and case["status"] == "PASS" for case in cases):
                    proven.append("stale")
                row.update(status="PASS" if positive else "FAIL", executed=True, qt_action_executed=True,
                    positive_postcondition=positive, selected_ids=list(dict.fromkeys(key for case in successful for key in case["selected_ids"])),
                    selection_widened=False, nonselected_stable=positive, restart=positive, undo=positive,
                    checks=[{"name": check, "status": case["status"]} for case in cases for check in case["checks"]],
                    cases=cases, proven_scenarios=proven,
                    artifacts=[{"path": str(path.resolve()), "sha256": digest(path)} for path in (Path(temp)/"editor").rglob("*") if path.is_file()], reason="")
        for case in multiple["actions"]:
            case = semantic_result(case["action_id"], case)
            row = next(row for row in actions if row["action_id"] == case["action_id"])
            implicit = ["valid_single" if len(row["selected_ids"]) == 1 else "valid_multiple"] if row["positive_postcondition"] and not row.get("cases") else []
            row["cases"] = [*row.get("cases", ()), case]
            row["checks"].extend(case["checks"])
            row.setdefault("artifacts", []).extend(case["artifacts"])
            row["proven_scenarios"] = sorted(set(row.get("proven_scenarios", ())) | set(case["proven_scenarios"]) | set(implicit))
    report = {"schema": "cws-bom-w18-positive-matrix-1", "matrix_sha256": fingerprint(),
              "sources": sources_before,
              "source_unchanged_during_run": sources_before == {name: digest(ROOT / name) for name in SOURCE_FILES},
              "fixture": "synthetic canonical multi-family source/component fixture; only dialogs driven",
              "installed_main_window": False, "native_gpu_proven": False, "external_acceptance_proven": False,
              "negative_matrix": negative,
              "freshness_matrix": freshness,
              "supplemental_suites": {"drawing": drawing["result"], "editor": editor["status"], "inspection": inspection["result"], "multiple": multiple["result"], "kerf": kerf["result"]},
              "actions": actions, "summary": {name: sum(row["status"] == name for row in actions)
                                               for name in ("PASS", "FAIL", "PARTIAL", "BLOCKED_EXTERNAL")}}
    from cws_convertor import APP_VERSION
    report.update(commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  app_version=APP_VERSION, environment={"python": sys.version, "executable": sys.executable,
                  "platform": platform.platform(), "qt_platform": os.environ.get("QT_QPA_PLATFORM")},
                  input_hash=report["matrix_sha256"], scenario="W18 exact 87-action source/component positive matrix",
                  external_machine_acceptance={"status": "BLOCKED_EXTERNAL", "reason": "Physical machine acceptance not available; no simulated capability grants transfer authority."})
    report = portable_evidence_paths(report)
    report["status"] = "FAIL" if (report["summary"]["FAIL"] or negative["result"] != "PASS" or freshness["result"] != "PASS"
        or any(result != "PASS" for result in report["supplemental_suites"].values()) or not report["source_unchanged_during_run"]) else "PARTIAL" if report["summary"]["PARTIAL"] or report["summary"]["BLOCKED_EXTERNAL"] else "PASS"
    report["result"] = report["status"]
    report["output_hash"] = hashlib.sha256(json.dumps(report["actions"], sort_keys=True).encode()).hexdigest()
    if output:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print("BOM_W18_POSITIVE_MATRIX = " + report["status"], report["summary"])
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = run(args.output)
    raise SystemExit(1 if report["status"] == "FAIL" else 2 if args.require_complete and report["status"] != "PASS" else 0)
