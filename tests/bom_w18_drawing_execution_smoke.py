"""W18 drawing dispatch into the real drawing panel, store and rendering engine.

Declared synthetic two-member geometry; no rendering/linter/store handler is
mocked. The shell is a small route/selection adapter, so this is integration
evidence, not proof of the shipping BOM QAction or installed/hardware acceptance.
Settings routes must produce a persisted edit through native controls; merely
opening a workspace is never counted as a completed edit. Printing stays PREPARED.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import platform
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

import fitz
from PySide6 import QtCore, QtTest, QtWidgets
from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.production_hub import ACTION_DEFINITIONS, BOMHubState, BOMScopeEngine
from cws_convertor.bom.workspace import BOMWorkspaceReadModel
from cws_convertor.drawings import DrawingRole
from cws_convertor.drawings.interactive import DimensionDocumentStore, DIMENSION_SETTINGS_KEY
from cws_convertor.project.jobs import JobManager
from cws_convertor.project.model import stable_sha256
from cws_convertor.project.service import ProjectSession
from cws_convertor.ui_qt.bom_action_dispatch import _dispatch
from cws_convertor.ui_qt.functional_workspaces import DrawingWorkspacePanel
from cws_convertor.ui_qt.pdf_v3_completion_evidence import assembly_workspace


class DrawingExecutionTests(unittest.TestCase):
    output_root = None
    action_evidence = []

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.folder = TemporaryDirectory(prefix="cws-w18-drawing-") if self.output_root is None else None
        self.output = Path(self.folder.name) if self.folder else self.output_root / self._testMethodName
        self.output.mkdir(parents=True, exist_ok=True)
        self.workspace = assembly_workspace()
        self.workspace.project.settings.update(
            drawing_output_directory=str(self.output),
            drawing_user_roles={"v3-test": DrawingRole.RELEASER.value},
        )
        self.page = DrawingWorkspacePanel()
        self.page.resize(1680, 1050)
        self.page.show()
        self.harness = QtWidgets.QWidget()
        self.harness._workspace = self.workspace
        self.harness._hub_state = BOMHubState(self.workspace.project)
        self.harness.status = QtWidgets.QLabel()
        self.context = SimpleNamespace(workspace=self.workspace, selection=None)
        self.routes = []
        self.manager = JobManager(max_workers=1)
        self.harness.window = SimpleNamespace(
            pdf_page=self.page, application_context=self.context, job_manager=self.manager,
            workspace_router=SimpleNamespace(open_workspace=self.open_workspace),
        )
        self.warnings = []
        self.dialog_timer = QtCore.QTimer()
        self.dialog_timer.timeout.connect(self.answer_dialogs)
        self.dialog_timer.start(10)
        self.select(("P1",))

    def tearDown(self):
        self.dialog_timer.stop()
        self.manager.shutdown(wait=True, cancel_pending=True)
        self.page.close()
        self.page.deleteLater()
        self.harness.close()
        self.harness.deleteLater()
        self.flush()
        self.workspace.session.close()
        if self.folder:
            self.folder.cleanup()

    def flush(self):
        for _ in range(4):
            self.app.processEvents()

    def open_workspace(self, route):
        if route != "pdf_review":
            return False
        self.routes.append(route)
        self.page.show()
        return True

    def answer_dialogs(self):
        for dialog in self.app.topLevelWidgets():
            if isinstance(dialog, QtWidgets.QInputDialog) and dialog.isVisible():
                editor = dialog.findChild(QtWidgets.QLineEdit)
                if editor is not None and not editor.text():
                    QtTest.QTest.keyClicks(editor, "W18 deliberate drawing revision")
                box = dialog.findChild(QtWidgets.QDialogButtonBox)
                if box is not None:
                    QtTest.QTest.mouseClick(box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok), QtCore.Qt.MouseButton.LeftButton)
            elif isinstance(dialog, QtWidgets.QMessageBox) and dialog.isVisible():
                self.warnings.append(dialog.text())
                dialog.accept()

    def select(self, ids):
        self.context.selection = SimpleNamespace(entity_ids=tuple(ids), primary_entity_id=ids[0] if ids else "")
        self.workspace.bom_snapshot = build_bom_snapshot(self.workspace.project)
        self.page.set_context(self.workspace, self.context.selection)
        self.flush()

    def preflight(self, action, ids):
        model = BOMWorkspaceReadModel(self.workspace.bom_snapshot, self.workspace.project)
        rows = tuple(row for family in ("parts", "assemblies") for row in model.family_rows(family)
                     if set(row.entity_ids).intersection(ids))
        return BOMScopeEngine(model).preflight(
            "drawing", rows, expected_snapshot_sha256=self.workspace.bom_snapshot.snapshot_sha256,
            allow_blocked_review_export=True,
        )

    def execute(self, action, ids=("P1",)):
        self.select(ids)
        definition = next(item for item in ACTION_DEFINITIONS if item.action_id == action)
        result = _dispatch(self.harness, action, definition.route, tuple(ids), self.preflight(action, ids))
        self.flush()
        self.assertEqual(tuple(self.context.selection.entity_ids), tuple(ids))
        return result

    def click(self, widget):
        QtTest.QTest.mouseClick(widget, QtCore.Qt.MouseButton.LeftButton)
        self.flush()

    def non_selected(self):
        return stable_sha256(self.workspace.project.to_dict()["parts"]["P2"])

    def nonselected_entities(self, ids):
        data = self.workspace.project.to_dict()
        return stable_sha256({family: {key: value for key, value in data.get(family, {}).items() if key not in ids}
                              for family in ("parts", "assemblies", "purchased_items", "fasteners", "welds")})

    def record(self, action, ids, scenarios, outputs=(), *, external=False):
        retained = []
        for index, path in enumerate(outputs):
            path = Path(path)
            # Later preview/save actions can replace the same live output path.
            # Copy each observed result into a separate immutable evidence slot.
            target = self.output / "observed" / f"{len(self.action_evidence):03d}-{action}" / f"{index}-{path.name}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            retained.append({"path": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        self.action_evidence.append({
            "action_id": action, "result": "BLOCKED_EXTERNAL" if external else "PASS",
            "entity_ids": list(ids), "selected_ids": list(ids), "scenarios": list(scenarios),
            "positive_postcondition": "positive_postcondition" in scenarios,
            "selection_widened": False if "no_unintended_widening" in scenarios else None,
            "nonselected_stable": "non_selected_unchanged" in scenarios,
            "restart": "save_reopen" in scenarios, "undo": "undo" in scenarios,
            "checks": [{"name": scenario, "status": "PASS"} for scenario in scenarios],
            "outputs": retained,
            "external_acceptance": "Physical printer/operator acceptance is not executed" if external else None,
            "execution_layer": "real downstream dispatcher and native drawing panel; shell adapter only",
            "shipping_qaction_executed": False, "installed_tested": False,
        })

    def assert_document(self, key):
        document = self.page._drawing_document
        self.assertIsNotNone(document, self.page.status.text())
        document.validate()
        self.assertEqual(document.entity_id, key)
        self.assertGreater(sum(len(page.primitives) for page in document.pages), 0)
        self.assertTrue(self.page._last_png.is_file())
        self.assertFalse(self.page.preview.grab().isNull())

    def assert_pdf(self, path):
        with fitz.open(path) as document:
            self.assertGreater(document.page_count, 0)
            self.assertGreater(sum(len(page.get_drawings()) for page in document), 0)
            self.assertGreater(len(document[0].get_pixmap().samples), 0)

    def reopen_document(self, key="P1"):
        expected = DimensionDocumentStore.load(self.workspace.project, entity_id=key)
        path = self.workspace.session.save(self.output / "w18-drawing.cwscproj", create_backup=False)
        # ProjectSession.save returns a verified project instance. The production
        # workspace reads session.project dynamically; update this fixture adapter
        # too, otherwise later edits would target the detached pre-save model.
        self.workspace.project = self.workspace.session.project
        self.harness._hub_state = BOMHubState(self.workspace.project)
        with ProjectSession.open(path) as reopened:
            actual = DimensionDocumentStore.load(reopened.project, entity_id=key)
            self.assertEqual(actual.drawing_id, expected.drawing_id)
            self.assertEqual(actual.drawing_revision, expected.drawing_revision)
            self.assertEqual(actual.status, expected.status)
            self.assertEqual(actual.extensions, expected.extensions)
            self.assertEqual([item.dimension_id for item in actual.dimensions], [item.dimension_id for item in expected.dimensions])
            self.assertEqual(reopened.project.to_dict()["parts"]["P2"], self.workspace.project.to_dict()["parts"]["P2"])
        return path

    def test_open_preview_generate_regenerate_render_real_exact_documents(self):
        before = self.non_selected()
        for action in ("drawing.open_part", "drawing.preview", "drawing.generate", "drawing.regenerate"):
            with self.subTest(action=action):
                result = self.execute(action)
                self.assertEqual(result.status, "passed", result.message)
                self.assert_document("P1")
                self.assertTrue(result.outputs)
                if action in {"drawing.generate", "drawing.regenerate"}:
                    pdfs = [path for path in result.outputs if Path(path).suffix.lower() == ".pdf"]
                    self.assertEqual(len(pdfs), 1)
                    self.assert_pdf(pdfs[0])
                self.assertEqual(before, self.non_selected())
                self.record(action, ("P1",), ("valid_single", "positive_postcondition", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged"), result.outputs)
                print("W18_DRAWING_EXECUTED", action, "exact_document=P1", flush=True)

    def test_assembly_open_retains_both_components_without_parent_fallback(self):
        before = self.nonselected_entities(("A1",))
        result = self.execute("drawing.open_assembly", ("A1",))
        self.assertEqual(result.status, "passed", result.message)
        self.assert_document("A1")
        document = self.page._drawing_document
        self.assertEqual(document.document_type, "assembly")
        refs = {ref for page in document.pages for primitive in page.primitives for ref in primitive.refs}
        self.assertTrue({"entity:P1", "entity:P2"}.issubset(refs))
        self.assertEqual(before, self.nonselected_entities(("A1",)))
        self.record("drawing.open_assembly", ("A1",), ("valid_single", "positive_postcondition", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged"), result.outputs)
        print("W18_DRAWING_EXECUTED drawing.open_assembly exact_document=A1 components=P1,P2", flush=True)

    def test_settings_require_real_edit_persistence_and_native_undo(self):
        for action in ("drawing.setup", "drawing.format", "drawing.scale", "drawing.views"):
            with self.subTest(action=action):
                result = self.execute(action)
                self.assertEqual(result.status, "prepared")
                before = self.page._sheet_settings()
                other = self.non_selected()
                if action in {"drawing.setup", "drawing.format"}:
                    control = self.page.format
                    control.setFocus()
                    QtTest.QTest.keyClick(control, QtCore.Qt.Key.Key_End)
                elif action == "drawing.scale":
                    self.page.scale.setFocus()
                    QtTest.QTest.keyClick(self.page.scale, QtCore.Qt.Key.Key_End)
                else:
                    if not self.page.view_buttons["top"].isVisible():
                        self.click(self.page.view_options_toggle)
                    self.click(self.page.view_buttons["top"])
                self.flush()
                after = self.page._sheet_settings()
                self.assertNotEqual(after, before)
                stored = DimensionDocumentStore.load(self.workspace.project, entity_id="P1")
                self.assertEqual(stored.extensions["sheet_settings"], after)
                self.reopen_document()
                self.assertEqual(other, self.non_selected())
                self.click(self.page.dimension_action_buttons["Ongedaan maken (Ctrl+Z)"])
                self.assertEqual(self.page._sheet_settings(), before)
                self.reopen_document()
                self.assertEqual(other, self.non_selected())
                self.record(action, ("P1",), ("valid_single", "positive_postcondition", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged", "save_reopen", "undo"), (self.output / "w18-drawing.cwscproj",))
                print("W18_DRAWING_EXECUTED", action, "native_edit_save_reopen_undo=P1", flush=True)

    def make_current_canonical_plate(self):
        from tests.part_workbench_roundtrip_smoke import make_part, plate_source_metrics, plate_changes
        session = self.workspace.session
        self.workspace.project.parts["P1"] = make_part("P1", metrics=plate_source_metrics())
        self.workspace.project.parts["P1"].assembly_ids = ["A1"]
        self.workspace.project.parts["P1"].quantity_per_assembly = {"A1": 1}
        session.start_part_workbench("P1", user="v3-test")
        session.update_part_workbench("P1", plate_changes(), user="v3-test", reason="Declared synthetic W18 plate")
        self.assertEqual(session.rebuild_part_canonical("P1", user="v3-test").report["status"], "passed")
        roundtrip = session.validate_part_roundtrips("P1", self.output, user="v3-test")
        self.assertEqual(roundtrip["status"], "passed")
        self.assertEqual(set(roundtrip["formats"]), {"nc1", "step", "ifc", "pdf"})
        session.review_part_workbench("P1", user="v3-test")
        session.review_part_workbench("P1", user="v3-test", release=True)
        self.page.set_context(None)
        self.select(("P1",))
        if not self.page.dimension_mode.isVisible():
            self.click(self.page.view_options_toggle)
        self.page.dimension_mode.setFocus()
        QtTest.QTest.keyClick(self.page.dimension_mode, QtCore.Qt.Key.Key_End)
        self.flush()
        self.assertEqual(self.page.dimension_mode.currentText(), "Productiematen")
        self.assertTrue(self.page._drawing_document.lint["release_ready"], self.page._drawing_document.lint)

    def test_canonical_dimension_check_approve_and_new_revision_reopen(self):
        self.make_current_canonical_plate()
        before = self.non_selected()
        result = self.execute("drawing.dimension_check")
        self.assertEqual(result.status, "passed", result.message)
        lint = json.loads(result.message)
        self.assertGreater(lint["checked_primitives"], 0)
        self.assertFalse(any(item.get("blocking", True) for item in lint["issues"]))
        self.assertEqual(self.page._drawing_document.entity_id, "P1")
        self.assertEqual(before, self.non_selected())
        self.record("drawing.dimension_check", ("P1",), ("valid_single", "positive_postcondition", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged"), result.outputs)
        result = self.execute("drawing.approve")
        self.assertEqual(result.status, "passed", result.message)
        self.assertEqual(self.page._dimension_document.status, "released")
        self.assertEqual(self.page._dimension_document.entity_id, "P1")
        self.assertEqual(before, self.non_selected())
        self.reopen_document()
        self.record("drawing.approve", ("P1",), ("valid_single", "positive_postcondition", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged", "save_reopen"), (self.output / "w18-drawing.cwscproj",))
        revision = self.page._dimension_document.drawing_revision
        result = self.execute("drawing.revision")
        self.assertEqual(result.status, "passed", result.message)
        self.assertNotEqual(self.page._dimension_document.drawing_revision, revision)
        self.assertNotEqual(self.page._dimension_document.status, "released")
        self.assertEqual(self.page._dimension_document.entity_id, "P1")
        self.reopen_document()
        self.assertEqual(before, self.non_selected())
        self.assertFalse(self.warnings)
        self.record("drawing.revision", ("P1",), ("valid_single", "positive_postcondition", "exact_selected_ids", "no_unintended_widening", "save_reopen", "non_selected_unchanged"), (self.output / "w18-drawing.cwscproj",))
        print("W18_DRAWING_EXECUTED drawing.dimension_check,drawing.approve,drawing.revision canonical_plate_exact=P1", flush=True)

    def test_batch_runs_real_job_for_single_multiple_and_assembly(self):
        for ids in (("P1",), ("P1", "P2"), ("A1",)):
            with self.subTest(ids=ids):
                before = deepcopy(self.workspace.project.settings.get(DIMENSION_SETTINGS_KEY, {}))
                entities_before = self.nonselected_entities(ids)
                with patch.object(QtWidgets.QFileDialog, "getExistingDirectory", return_value=str(self.output)):
                    outcome = self.execute("drawing.batch_pdf", ids)
                self.assertEqual(outcome.status, "prepared")
                self.assertIsNotNone(outcome.start)
                outcome.start()
                deadline = time.monotonic() + 45
                while getattr(self.harness, "_drawing_batch_job", "") and time.monotonic() < deadline:
                    self.flush()
                    QtTest.QTest.qWait(10)
                self.assertFalse(getattr(self.harness, "_drawing_batch_job", ""), "Drawing batch timed out")
                result = self.harness._last_drawing_batch
                self.assertEqual(result["status"], "passed", result)
                self.assertEqual(result["entity_ids"], sorted(ids))
                manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
                self.assertEqual([item["entity_id"] for item in manifest["documents"]], sorted(ids))
                self.assertFalse(manifest["production_release_granted"])
                self.assertEqual(self.workspace.project.settings.get(DIMENSION_SETTINGS_KEY, {}), before)
                self.assertEqual(entities_before, self.nonselected_entities(ids))
                self.assert_pdf(result["pdf"])
                self.record("drawing.batch_pdf", ids, ("valid_multiple" if len(ids) > 1 else "valid_single", "positive_postcondition", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged"), (result["pdf"], result["manifest"]))
                print("W18_DRAWING_EXECUTED drawing.batch_pdf exact_ids=" + ",".join(ids), flush=True)

    def test_print_prepares_actual_pdf_without_claiming_physical_acceptance(self):
        before = self.non_selected()
        result = self.execute("drawing.print")
        self.assertEqual(result.status, "prepared")
        self.assertEqual(len(result.outputs), 1)
        self.assert_pdf(result.outputs[0])
        self.assertEqual(before, self.non_selected())
        self.record("drawing.print", ("P1",), ("valid_single", "exact_selected_ids", "non_selected_unchanged", "actual_pdf_prepared"), result.outputs, external=True)
        print("W18_DRAWING_EXTERNAL drawing.print physical_acceptance=BLOCKED_EXTERNAL actual_pdf_prepared=P1", flush=True)

    def test_stale_invalid_and_widened_selection_reject_before_drawing_mutation(self):
        self.select(("P1",))
        preflight = self.preflight("drawing.generate", ("P1",))
        before = stable_sha256(self.workspace.project.to_dict())
        for ids, current in (((), preflight), (("deleted",), preflight), (("P1", "P2"), preflight), (("P1",), replace(preflight, snapshot_sha256="stale"))):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                _dispatch(self.harness, "drawing.generate", "drawings", ids, current)
        self.assertEqual(before, stable_sha256(self.workspace.project.to_dict()))
        self.assertFalse(list(self.output.glob("*.pdf")))

    def test_review_geometry_cannot_be_approved(self):
        result = self.execute("drawing.approve", ("A1",))
        self.assertEqual(result.status, "blocked")
        self.assertNotEqual(self.page._dimension_document.status, "released")
        self.assertFalse(any(row.get("action") == "drawing.dimension_revision_released" for row in self.page._dimension_document.audit))


def run(output=None):
    """Return observed scenario evidence; a generic green suite proves no extra dimensions."""
    output = Path(output).resolve() if output is not None else None
    report_path = output if output and output.suffix.lower() == ".json" else (output / "DRAWING_EXECUTION.json" if output else None)
    DrawingExecutionTests.output_root = output.with_suffix("") if output and output.suffix.lower() == ".json" else output
    DrawingExecutionTests.action_evidence = []
    source_paths = (
        Path(__file__), ROOT / "cws_convertor/ui_qt/bom_action_dispatch.py",
        ROOT / "cws_convertor/ui_qt/bom_action_dispatch_base.py",
        ROOT / "cws_convertor/ui_qt/functional_workspaces.py",
        ROOT / "cws_convertor/ui_qt/engineering_drawing.py",
        ROOT / "cws_convertor/drawings/interactive.py", ROOT / "cws_convertor/project/storage.py",
        ROOT / "cws_convertor/ui_qt/pdf_v3_completion_evidence.py", ROOT / "tests/part_workbench_roundtrip_smoke.py",
        ROOT / "cws_convertor/project/model.py", ROOT / "cws_convertor/project/service.py",
        ROOT / "cws_convertor/project/jobs.py", ROOT / "cws_convertor/ui_qt/bom_drawing_batch.py",
        ROOT / "cws_convertor/bom/engine.py", ROOT / "cws_convertor/bom/production_hub.py",
    )
    source_paths = tuple(sorted(set(source_paths).union((ROOT / "cws_convertor/drawings").rglob("*.py"))))
    source_hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True)
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DrawingExecutionTests))
    actions = DrawingExecutionTests.action_evidence
    source_unchanged = source_hashes == {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
    source_unchanged = source_unchanged and commit == subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    artifacts_verified = bool(output) and all(Path(item["path"]).is_file() and hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"] for row in actions for item in row["outputs"])
    status = "PASS" if result.wasSuccessful() and source_unchanged and (not output or artifacts_verified) else "FAIL"
    from product_info import VERSION
    report = {
        "schema": "cws-bom-w18-drawing-execution-1.0",
        "commit": commit, "source_unchanged_during_run": source_unchanged, "tracked_dirty": bool(dirty.strip()),
        "app_version": VERSION, "environment": {"platform": platform.platform(), "python": sys.version, "qt_platform": os.environ.get("QT_QPA_PLATFORM"), "geometry": "declared synthetic assembly and independently roundtripped canonical plate"},
        "input_hash": stable_sha256(source_hashes), "source_hashes": source_hashes,
        "scenario": "W18 downstream drawing execution and native edit persistence",
        "result": status, "status": status, "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "actions": actions, "output_hash": stable_sha256(actions),
        "artifacts_retained": bool(output), "artifacts_verified": artifacts_verified,
        "limits": ["No shipping BOM QAction claim", "No installed EXE claim", "No physical printer acceptance", "No undo proof for drawing release/revision; no release-invalidation claim"],
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    raise SystemExit(0 if run()["result"] == "PASS" else 1)
