"""Shipping BOM QActions display exact source, assembly and hash information.

Synthetic canonical objects refer to actual independently parsed DXF handles and
actual file bytes. This proves the native BOM panel, not installed EXE acceptance.
Only layout preferences are isolated and informational dialogs are acknowledged.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

import ezdxf
from PySide6 import QtCore, QtWidgets
from cws_convertor.bom import build_bom_snapshot
from cws_convertor.project.model import Assembly, Part, SourceFileRecord, SourceIdentity, stable_sha256
from cws_convertor.project.service import ProjectSession
from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
from cws_convertor.ui_qt.bom_inspection import inspect_entities

ACTIONS = ("inspect.source", "inspect.assembly", "inspect.hashes")
SOURCE_FILES = (
    "tests/bom_w18_inspection_execution_smoke.py", "cws_convertor/ui_qt/bom_inspection.py",
    "cws_convertor/ui_qt/bom_workspace.py", "cws_convertor/bom/production_hub.py",
    "cws_convertor/bom/workspace.py", "cws_convertor/bom/engine.py",
    "cws_convertor/project/model.py", "cws_convertor/project/storage.py", "cws_convertor/project/service.py",
)


class InspectionExecutionTests(unittest.TestCase):
    output_root = None
    evidence = []

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.temp = TemporaryDirectory(prefix="cws-w18-inspect-") if self.output_root is None else None
        self.output = Path(self.temp.name) if self.temp else self.output_root / self._testMethodName
        self.output.mkdir(parents=True, exist_ok=True)
        self.source_path = self.output / "two_actual_source_objects.dxf"
        document = ezdxf.new("R2018")
        first = document.modelspace().add_line((0, 0), (200, 0))
        second = document.modelspace().add_line((0, 50), (300, 50))
        self.handles = {"P1": first.dxf.handle, "P2": second.dxf.handle}
        document.saveas(self.source_path)
        self.source_hash = hashlib.sha256(self.source_path.read_bytes()).hexdigest()
        self.session = ProjectSession.new("W18 actual source inspection")
        project = self.session.project
        source = SourceFileRecord.from_path(project.project_id, self.source_path)
        project.sources[source.source_id] = source
        self.session.source_paths[source.source_id] = self.source_path
        for index, key in enumerate(("P1", "P2"), 1):
            assembly = "A" + str(index)
            part = Part(internal_id=key, name=key + " unique name", part_position=key,
                        profile="HEA200", material="S355JR", length_mm=200.0 + index,
                        quantity_total=1, assembly_ids=[assembly], quantity_per_assembly={assembly: 1},
                        source_identity=SourceIdentity(source_format="DXF", source_file_id=source.source_id,
                            source_sha256=self.source_hash, source_entity_id=self.handles[key], occurrence_id="occ-" + key),
                        geometry_descriptor={"bbox": [200.0 + index, 200, 190]})
            part.recompute_hashes()
            project.add_entity(part)
            project.add_entity(Assembly(internal_id=assembly, name=assembly, assembly_mark=assembly, part_ids=[key], main_part_id=key))
        self.workspace = SimpleNamespace(project=project, session=self.session, bom_snapshot=build_bom_snapshot(project, classify_if_needed=False))
        self.host = QtWidgets.QMainWindow()
        self.host.resize(1680, 1000)
        self.host.project_page = None
        self.context = SimpleNamespace(workspace=self.workspace, selection=None, request_selection=lambda *args, **kw: None, clear_selection=lambda **kw: None)
        self.host.application_context = self.context
        self.host.workspace_router = SimpleNamespace(open_workspace=lambda _route: False)
        self.layout_patches = [patch.object(BomWorkspacePanel, name, lambda _self: None) for name in ("_restore_layout", "_save_layout")]
        for item in self.layout_patches:
            item.start()
        self.panel = BomWorkspacePanel(self.host)
        self.host.setCentralWidget(self.panel)
        self.host.show()
        self.dialogs = []
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.answer_dialogs)
        self.timer.start(10)
        self.select(("P1",))

    def tearDown(self):
        self.timer.stop()
        self.host.close()
        self.host.deleteLater()
        self.flush()
        for item in self.layout_patches:
            item.stop()
        self.session.close()
        if self.temp:
            self.temp.cleanup()

    def flush(self):
        for _ in range(4):
            self.app.processEvents()

    def answer_dialogs(self):
        for widget in self.app.topLevelWidgets():
            if isinstance(widget, QtWidgets.QMessageBox) and widget.isVisible():
                self.dialogs.append(widget.text())
                widget.accept()

    def select(self, ids):
        self.context.selection = SimpleNamespace(entity_ids=ids, primary_entity_id=ids[0] if ids else "")
        self.panel.set_context(self.workspace, self.context.selection)
        self.flush()
        self.panel._populate_action_matrix()

    def entities(self):
        return {item.internal_id: deepcopy(asdict(item)) for item in self.workspace.project.iter_entities()}

    def trigger(self, action, ids):
        self.select(ids)
        before = self.entities()
        qaction = self.panel._matrix_qactions[action]
        self.assertTrue(qaction.isEnabled(), qaction.toolTip())
        qaction.trigger()
        self.flush()
        report = self.panel._last_bom_inspection
        self.assertEqual(report["action_id"], action)
        self.assertEqual(sorted(report["entity_ids"]), sorted(ids))
        self.assertEqual(self.context.selection.entity_ids, ids)
        self.assertEqual(self.entities(), before)
        label = self.panel.detail_labels["traceability" if action == "inspect.hashes" else "properties"]
        self.assertEqual(label.textFormat(), QtCore.Qt.TextFormat.PlainText)
        self.assertTrue(label.isVisible())
        self.assertEqual(label.text(), report["text"])
        self.assertEqual(sorted(row["entity_id"] for row in report["records"]), sorted(ids))
        self.assertFalse(report["production_release_allowed"])
        return report, label.text()

    def record(self, action, ids, text):
        path = self.output / (action + "-" + "-".join(ids) + ".json")
        path.write_text(json.dumps({"action_id": action, "selected_ids": ids, "displayed_text": text,
            "source_sha256": self.source_hash, "entity_hash": stable_sha256(self.entities())}, indent=2), encoding="utf-8")
        self.evidence.append({"action_id": action, "result": "PASS", "positive_postcondition": True,
            "qt_action_executed": True, "shipping_qaction_executed": True, "selected_ids": list(ids),
            "selection_widened": False, "nonselected_stable": True, "restart": False, "undo": False,
            "scenarios": ["valid_single" if len(ids) == 1 else "valid_multiple", "positive_postcondition", "exact_selected_ids", "no_unintended_widening", "non_selected_unchanged"],
            "checks": [{"name": "Shipping QAction displays independently checked current canonical details", "status": "PASS"}],
            "outputs": [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}],
            "installed_tested": False})

    def test_shipping_source_action_displays_real_file_and_actual_object_handles(self):
        parsed = ezdxf.readfile(self.source_path)
        for ids in (("P1",), ("P1", "P2")):
            with self.subTest(ids=ids):
                report, text = self.trigger("inspect.source", ids)
                for row in report["records"]:
                    key = row["entity_id"]
                    self.assertIsNotNone(parsed.entitydb.get(self.handles[key]))
                    self.assertEqual(row["source_identity"]["source_entity_id"], self.handles[key])
                    self.assertEqual(row["actual_source_sha256"], hashlib.sha256(self.source_path.read_bytes()).hexdigest())
                    self.assertEqual(row["binding"], "MATCH")
                    self.assertIn("Bronobject-ID: " + self.handles[key], text)
                self.assertIn(self.source_hash, text)
                if len(ids) == 1:
                    self.assertNotIn("Object: P2", text)
                    self.assertNotIn("Occurrence: occ-P2", text)
                self.record("inspect.source", ids, text)

    def test_shipping_assembly_action_displays_exact_reciprocal_membership(self):
        for ids in (("P1",), ("P1", "P2")):
            with self.subTest(ids=ids):
                report, text = self.trigger("inspect.assembly", ids)
                for row in report["records"]:
                    expected = "A" + row["entity_id"][-1]
                    self.assertEqual(row["assembly_ids"], [expected])
                    self.assertEqual(row["parent_assembly_ids"], [expected])
                    self.assertTrue(row["reciprocal_memberships"][expected])
                    self.assertIn("Ouderassemblies: " + expected, text)
                if len(ids) == 1:
                    self.assertNotIn("A2", text)
                self.record("inspect.assembly", ids, text)

    def test_shipping_hash_action_displays_each_actual_entity_hash(self):
        for ids in (("P1",), ("P1", "P2")):
            with self.subTest(ids=ids):
                report, text = self.trigger("inspect.hashes", ids)
                for row in report["records"]:
                    part = self.workspace.project.parts[row["entity_id"]]
                    self.assertEqual(row["geometry_hash"], part.geometry_hash)
                    self.assertEqual(row["manufacturing_hash"], part.manufacturing_hash)
                    self.assertIn("Geometrie-SHA256: " + part.geometry_hash, text)
                    self.assertIn("Productie-SHA256: " + part.manufacturing_hash, text)
                if len(ids) == 1:
                    self.assertNotIn(self.workspace.project.parts["P2"].geometry_hash, text)
                self.record("inspect.hashes", ids, text)

    def test_changed_and_missing_source_are_displayed_without_false_matching_claim(self):
        self.source_path.write_bytes(self.source_path.read_bytes() + b"\n999\nchanged after import\n")
        report, text = self.trigger("inspect.source", ("P1",))
        self.assertEqual(report["records"][0]["binding"], "CHANGED_OR_UNBOUND")
        self.assertNotIn("Bronbinding: MATCH", text)
        self.source_path.unlink()
        report, text = self.trigger("inspect.source", ("P1",))
        self.assertEqual(report["records"][0]["binding"], "UNAVAILABLE")
        self.assertIsNone(report["records"][0]["actual_source_sha256"])

    def test_empty_deleted_and_mismatching_scope_never_reuses_previous_report(self):
        self.trigger("inspect.hashes", ("P1",))
        before = deepcopy(self.panel._last_bom_inspection)
        for ids in ((), ("deleted",), ("P1", "deleted")):
            with self.subTest(ids=ids):
                self.select(ids)
                entities_before = self.entities()
                if not ids or ids == ("deleted",):
                    self.assertFalse(self.panel._matrix_qactions["inspect.hashes"].isEnabled())
                self.panel._matrix_qactions["inspect.hashes"].trigger()
                self.assertEqual(self.panel._last_bom_inspection, before)
                self.assertEqual(self.entities(), entities_before)
                self.assertNotIn("Geometrie-SHA256:", self.panel.detail_labels["traceability"].text())
                with self.assertRaises(ValueError):
                    inspect_entities(self.workspace, "inspect.hashes", ids)


def run(output=None):
    output = Path(output).resolve() if output is not None else None
    report_path = output if output and output.suffix.lower() == ".json" else (output / "INSPECTION_EXECUTION.json" if output else None)
    InspectionExecutionTests.output_root = output.with_suffix("") if output and output.suffix.lower() == ".json" else output
    InspectionExecutionTests.evidence = []
    source_hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_FILES}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InspectionExecutionTests))
    unchanged = source_hashes == {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_FILES}
    unchanged = unchanged and commit == subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    actions = InspectionExecutionTests.evidence
    from product_info import VERSION
    status = "PASS" if result.wasSuccessful() and unchanged else "FAIL"
    report = {"schema": "cws-bom-w18-inspection-execution-1.0", "commit": commit, "app_version": VERSION,
        "environment": {"platform": platform.platform(), "python": sys.version, "qt_platform": os.environ.get("QT_QPA_PLATFORM"), "fixture": "Synthetic canonical objects with actual parsed DXF source handles"},
        "input_hash": stable_sha256(source_hashes), "source_hashes": source_hashes, "source_unchanged_during_run": unchanged,
        "scenario": "Shipping BOM inspector source/assembly/hash QActions", "result": status, "status": status,
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "actions": actions, "output_hash": stable_sha256(actions), "artifacts_retained": bool(output),
        "limits": ["Native BOM panel only; no installed EXE claim", "Read-only canonical inspection; audit metadata may be recorded"]}
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    raise SystemExit(0 if run()["result"] == "PASS" else 1)
