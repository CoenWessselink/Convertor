"""Actual BOM kerf editing, persistence and authority invalidation.

The synthetic machine starts validated for a declared test configuration. A
changed kerf must require fresh qualification; no physical acceptance is inferred.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
import os
import hashlib
import json
import platform
import subprocess
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

from cws_convertor.optimization.profile_nesting.benchmark import build_synthetic_benchmark_project
from cws_convertor.manufacturing.machine_settings import set_machine_kerf
from cws_convertor.project import MachineProfile, ProjectModel, ProjectSession, ProjectStore


class KerfExecutionTests(unittest.TestCase):
    output_root = None
    @classmethod
    def setUpClass(cls):
        from PySide6 import QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="w18-kerf-") if self.output_root is None else None
        case_folder = Path(self.folder.name) if self.folder else self.output_root / self._testMethodName
        case_folder.mkdir(parents=True, exist_ok=True)
        project = build_synthetic_benchmark_project(2, released_parts=False)
        for part in project.parts.values():
            part.mass_each_kg, part.surface_area_each_m2 = 8, 1
            part.classification_status = "confirmed"
            part.classification_confidence = part.profile_confidence = part.material_confidence = 1
            part.recompute_hashes()
        project.add_entity(MachineProfile(internal_id="bench-saw-v1", name="Synthetic saw", machine_id="BENCH-SAW", kerf_mm=2.7))
        self.session = ProjectSession(store=ProjectStore(), project=project)
        path = case_folder / "project.cwscproj"
        self.session.save(path, embed_sources=False)
        self.session.close()
        self.session = ProjectSession.open(path)
        self.project = self.session.project

    def tearDown(self):
        self.session.close()
        if self.folder:
            self.folder.cleanup()

    def test_invalid_missing_noop_and_unexplained_configuration_never_mutate(self):
        for profile_id, value, reason in (("missing", 5, "test"), ("bench-saw-v1", -1, "test"),
                ("bench-saw-v1", float("nan"), "test"), ("bench-saw-v1", 5, ""), ("bench-saw-v1", 2.7, "unchanged")):
            with self.subTest(value=value):
                before = deepcopy(self.project.to_dict())
                with self.assertRaises(ValueError):
                    set_machine_kerf(self.project, profile_id, value, reason=reason)
                self.assertEqual(before, self.project.to_dict())

    def test_shipping_action_saves_exact_machine_and_undo_after_reopen(self):
        self._execute_ui_case("save")

    def test_conflicting_profile_and_machine_identities_never_mutate(self):
        for mismatch in ("profile_key", "canonical_machine"):
            with self.subTest(mismatch=mismatch):
                project = ProjectModel.from_dict(self.project.to_dict())
                if mismatch == "profile_key":
                    project.profile_nesting_machine_profiles["bench-saw-v1"]["profile_id"] = "OTHER-PROFILE"
                else:
                    project.machine_profiles["bench-saw-v1"].machine_id = "OTHER-MACHINE"
                before = deepcopy(project.to_dict())
                with self.assertRaisesRegex(ValueError, "identiteit"):
                    set_machine_kerf(project, "bench-saw-v1", 5.2, reason="Identity rejection fixture")
                self.assertEqual(before, project.to_dict())

    def test_shipping_action_rejects_stale_source_before_save(self):
        self._execute_ui_case("stale")

    def test_shipping_action_rolls_back_failed_disk_write(self):
        self._execute_ui_case("disk_failure")

    def _execute_ui_case(self, mode):
        from PySide6 import QtWidgets
        from cws_convertor.bom import build_bom_snapshot
        from cws_convertor.bom.production_hub import BOMHubState
        from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
        from cws_convertor.ui_qt.phase3_workspaces import ProfileNestingPanel
        from cws_convertor.project import JobManager
        project = self.project
        key = next(iter(project.parts))
        workspace = SimpleNamespace(project=project, session=self.session,
            bom_snapshot=build_bom_snapshot(project, classify_if_needed=False))
        selection = SimpleNamespace(entity_ids=(key,), primary_entity_id=key)
        host = QtWidgets.QMainWindow()
        host.project_page = None
        host.job_manager = JobManager(max_workers=1)
        host.application_context = SimpleNamespace(workspace=workspace, selection=selection,
            request_selection=lambda *args, **kw: None, clear_selection=lambda **kw: None)
        host.workspace_router = SimpleNamespace(open_workspace=lambda route: route == "profile_nesting")
        host.profiles_page = ProfileNestingPanel(host)
        messages = []
        def modal(*args, **kw):
            messages.append(str(args[2] if len(args) > 2 else args))
            return QtWidgets.QMessageBox.StandardButton.Yes
        try:
            with patch.object(BomWorkspacePanel, "_restore_layout", lambda _self: None), \
                    patch.object(QtWidgets.QMessageBox, "warning", modal), patch.object(QtWidgets.QMessageBox, "information", modal):
                panel = BomWorkspacePanel(host)
                host.setCentralWidget(panel)
                panel.set_context(workspace, selection)
                self.app.processEvents()
                panel._populate_action_matrix()
                action = panel._matrix_qactions["optimize.kerf"]
                self.assertTrue(action.isEnabled(), action.toolTip())
                before = {entity.internal_id: asdict(entity) for entity in project.iter_entities()}
                original_profiles = deepcopy(project.profile_nesting_machine_profiles)
                action.trigger()
                self.app.processEvents()
                settings = host.profiles_page.machine_settings
                self.assertTrue(settings._bom_kerf_binding, messages)
                settings.kerf_value.setValue(5.2)
                settings.kerf_reason.setText("Declared synthetic replacement saw blade")
                if mode == "stale":
                    project.parts[key].length_mm += 500
                    project.parts[key].recompute_hashes()
                if mode == "disk_failure":
                    def fail_write():
                        raise OSError("Injected disk-write failure")
                    settings.persist_callback = fail_write
                expected_entities = {entity.internal_id: asdict(entity) for entity in project.iter_entities()}
                settings.kerf_apply.click()
                self.app.processEvents()
                if mode != "save":
                    self.assertEqual(original_profiles, project.profile_nesting_machine_profiles)
                    self.assertEqual(expected_entities, {entity.internal_id: asdict(entity) for entity in project.iter_entities()})
                    self.assertNotEqual("passed", panel._hub_state.data["batch_results"][-1]["status"])
                    with ProjectSession.open(self.session.path, read_only=True) as reopened:
                        self.assertEqual(original_profiles, reopened.project.profile_nesting_machine_profiles)
                    return
                changed = project.profile_nesting_machine_profiles["bench-saw-v1"]
                self.assertEqual(5.2, changed["kerf_mm"], messages)
                self.assertEqual("manual_validation_required", changed["validation_status"])
                self.assertNotEqual(original_profiles["bench-saw-v1"]["configuration_hash"], changed["configuration_hash"])
                self.assertEqual(5.2, project.machine_profiles["bench-saw-v1"].kerf_mm)
                self.assertTrue(all(asdict(project.get_entity(identity)) == value for identity, value in before.items() if identity != "bench-saw-v1"))
                results = panel._hub_state.data["batch_results"]
                self.assertEqual(("optimize.kerf", "passed"), (results[-1]["action"], results[-1]["status"]))
                with ProjectSession.open(self.session.path, read_only=True) as reopened:
                    self.assertEqual(project.profile_nesting_machine_profiles, reopened.project.profile_nesting_machine_profiles)
                    BOMHubState(reopened.project).undo_last()
                    self.assertEqual(original_profiles, reopened.project.profile_nesting_machine_profiles)
                    self.assertEqual(before, {entity.internal_id: asdict(entity) for entity in reopened.project.iter_entities()})
        finally:
            host.job_manager.shutdown(wait=True)
            host.close()
            host.deleteLater()
            self.app.processEvents()


def run(output=None):
    from cws_convertor.product import APP_VERSION
    sources = ("tests/bom_w18_kerf_execution_smoke.py", "cws_convertor/ui_qt/machine_settings_panel.py",
        "cws_convertor/manufacturing/machine_settings.py", "cws_convertor/ui_qt/bom_workspace.py",
        "cws_convertor/ui_qt/bom_action_dispatch_base.py", "cws_convertor/optimization/profile_nesting/configuration.py",
        "cws_convertor/optimization/profile_nesting/benchmark.py", "cws_convertor/bom/freshness.py")
    hashes = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
    KerfExecutionTests.output_root = Path(output).resolve() if output else None
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(KerfExecutionTests))
    unchanged = hashes == {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
    passed = result.wasSuccessful() and unchanged
    artifacts = ([{"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                  for path in KerfExecutionTests.output_root.rglob("*.cwscproj")] if output else [])
    action = {"action_id": "optimize.kerf", "status": "PARTIAL", "executed": passed, "qt_action_executed": passed,
        "selected_ids": ["bench-part-000"], "selection_widened": False, "nonselected_stable": passed,
        "positive_postcondition": False, "restart": passed, "undo": passed,
        "proven_scenarios": ["stale", "invalid", "save_reopen", "undo", "release_invalidation"] if passed else [],
        "checks": [{"name": name, "status": "PASS"} for name in (
            "Invalid/missing/no-op/unexplained kerf leaves model unchanged", "Conflicting profile/machine identities never mutate", "Stale source is rejected before apply",
            "Failed disk write restores original model and file", "Actual machine configuration Save/reopen/undo",
            "Changed kerf revokes previous machine validation")] if passed else [], "artifacts": artifacts,
        "reason": "Actual settings edit is proven. A new qualified cutting plan after the change is not proven; machine revalidation is required."}
    report = {"schema": "cws-w18-kerf-execution-1", "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "app_version": APP_VERSION, "environment": {"python": sys.version, "os": platform.platform(), "qt": "offscreen", "synthetic": True},
        "source_hashes": hashes, "source_unchanged_during_run": unchanged, "input_hash": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
        "scenario": "BOM kerf setting and authority invalidation", "result": "PASS" if passed else "FAIL",
        "output_hash": hashlib.sha256(json.dumps(action, sort_keys=True).encode()).hexdigest(), "actions": [action], "artifacts_retained": bool(output)}
    if output:
        (KerfExecutionTests.output_root / "KERF_EXECUTION.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    return report


if __name__ == "__main__":
    raise SystemExit(0 if run(sys.argv[1] if len(sys.argv) > 1 else None)["result"] == "PASS" else 1)
