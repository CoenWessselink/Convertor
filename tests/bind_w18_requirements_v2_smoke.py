"""Real-Git corruption checks for the optional W18 requirement evidence binder.

The audit boundary is replaced by an explicit test catalog here. These tests
verify binding and provenance rejection; they do not execute BOM actions or
create product acceptance evidence.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import bind_w18_requirements_v2 as binder
from tools import master_requirements_v2 as master


class W18RequirementsBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="cws-w18-binding-")
        cls.root = Path(cls.temporary.name).resolve()
        cls.source = cls.root / "source.py"
        cls.source.write_bytes(b"VALUE = 1\n")
        definitions = cls.root / master.ACTIONS
        definitions.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / master.ACTIONS, definitions)
        cls.git("init", "-q")
        cls.git("config", "core.autocrlf", "false")
        cls.git("config", "user.name", "W18 binding test fixture")
        cls.git("config", "user.email", "fixture@example.invalid")
        cls.git("add", "source.py", master.ACTIONS)
        cls.git("commit", "-qm", "Synthetic source binding fixture")
        cls.commit = cls.git("rev-parse", "HEAD").strip()
        cls.base_report = {
            "schema": "cws-bom-w18-positive-matrix-1", "commit": cls.commit,
            "app_version": "test-fixture", "environment": {"synthetic_binding_test": True},
            "input_hash": "1" * 64, "output_hash": "2" * 64,
            "scenario": "Binding test fixture, no BOM acceptance", "result": "PARTIAL",
            "source_unchanged_during_run": True, "installed_main_window": False,
            "sources": {"source.py": master.sha256(cls.source), master.ACTIONS: master.sha256(definitions)},
        }
        cls.base_catalog = {"schema": binder.AUDIT_SCHEMA, "installed_main_window_proven": False, "actions": []}
        for definition in master.canonical_actions(cls.root):
            cls.base_catalog["actions"].append({"action_id": definition["action_id"], "status": "PARTIAL",
                "scenarios": {name: {"status": "PARTIAL", "applicable": True,
                                      "reason": "Unverified fixture scenario", "evidence": []}
                              for name in master.SCENARIOS}})
        action = next(row for row in cls.base_catalog["actions"] if row["action_id"] == "edit.length")
        for name in ("valid_single", "positive_postcondition"):
            action["scenarios"][name] = {"status": "PASS", "applicable": True,
                "reason": "Explicit fixture assertion for binding tests only",
                "evidence": [{"kind": "fixture", "source": "explicit synthetic test assertion"}]}
        action = next(row for row in cls.base_catalog["actions"] if row["action_id"] == "inspect.hashes")
        action["scenarios"]["undo"] = {"status": "NOT_APPLICABLE", "applicable": False,
            "reason": "Synthetic reviewed read-only snapshot fixture; not product evidence",
            "evidence": [{"kind": "fixture-effects-review", "source": "synthetic snapshot comparison"}]}
        cls.base_report["actions"] = [{"action_id": row["action_id"]} for row in cls.base_catalog["actions"]]
        cls.base_report["matrix_sha256"] = cls.base_report["input_hash"]
        cls.base_report["output_hash"] = hashlib.sha256(json.dumps(cls.base_report["actions"], sort_keys=True).encode()).hexdigest()
        cls.baseline = master.build_register(ROOT, cls.commit)
        # Retain the actual source documents so the integration check exercises
        # the unmodified generator and validator against a separate workspace.
        for source in cls.baseline["sources"]:
            if source["present"]:
                destination = cls.root / source["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / source["path"], destination)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    @classmethod
    def git(cls, *args):
        return subprocess.check_output(["git", *args], cwd=cls.root, text=True, stderr=subprocess.PIPE)

    def setUp(self):
        self.source.write_bytes(b"VALUE = 1\n")
        self.report = deepcopy(self.base_report)
        self.catalog = deepcopy(self.base_catalog)
        self.path = self.root / "positive.json"
        self.audit = patch.object(binder, "_audit_catalog", return_value=self.catalog)
        self.audit_mock = self.audit.start()
        self.addCleanup(self.audit.stop)

    def build(self):
        self.path.write_bytes(binder._json_bytes(self.report))
        return binder.build_evidence(self.path, self.root)

    def test_partial_report_binds_only_explicit_scenarios(self):
        evidence = self.build()
        self.audit_mock.assert_called_once_with(self.path)
        self.assertEqual(evidence["result"], "PASS")
        self.assertEqual(evidence["source_report"]["result"], "PARTIAL")
        self.assertEqual(len(evidence["requirements"]), 87)
        self.assertEqual(evidence["requirements"]["W18-edit.length"]["scenarios"],
                         {"valid_single": "PASS", "positive_postcondition": "PASS"})
        self.assertEqual(evidence["requirements"]["W18-inspect.hashes"]["scenarios"], {"undo": "NOT_APPLICABLE"})
        self.assertEqual(evidence["requirements"]["W18-drawing.print"]["scenarios"], {})
        self.assertEqual(evidence["scenario_counts"], {"NOT_APPLICABLE": 1, "PARTIAL": 1302, "PASS": 2})
        self.assertTrue(all(not row["dimensions"] for row in evidence["requirements"].values()))

    def test_no_dimension_installed_or_historical_promotion(self):
        evidence = self.build()
        path = self.root / "binding.json"
        path.write_bytes(binder._json_bytes(evidence))
        bound = binder.attach_evidence(self.baseline, evidence, path, self.root)
        before = {row["requirement_id"]: row for row in self.baseline["requirements"]}
        for row in bound["requirements"]:
            self.assertEqual(row["dimensions"], before[row["requirement_id"]]["dimensions"])
            self.assertEqual(row["status"], before[row["requirement_id"]]["status"])
            self.assertIsNone(row["installed_commit"])
            if not row.get("action_id"):
                self.assertEqual(row, before[row["requirement_id"]])
        length = next(row for row in bound["requirements"] if row.get("action_id") == "edit.length")
        self.assertEqual(length["status"], "PARTIAL")
        self.assertEqual(length["scenarios"]["valid_single"]["state"], "PASS")
        self.assertEqual(length["scenarios"]["valid_multiple"]["state"], "UNVERIFIED")
        self.assertEqual(bound["summary"]["w18"]["scenario_proven"]["positive_postcondition"], 1)
        self.assertTrue(all(value["proven"] == 0 for value in bound["summary"]["dimensions"].values()))
        self.assertTrue(all(value["product_completion_percent"] is None for value in bound["summary"]["dimensions"].values()))

    def test_opt_in_output_passes_real_register_validator(self):
        self.path.write_bytes(binder._json_bytes(self.report))
        output = self.root / "validation/bound-register.json"
        bound = binder.write_binding(self.path, output, markdown_output=output.with_suffix(".md"), root=self.root)
        self.assertEqual(master.validate_register(bound, self.root), [])
        self.assertEqual(master.read_json(output), bound)
        proof = self.root / bound["w18_evidence_binding"]["path"]
        self.assertEqual(binder.verify_evidence(proof, self.root)["scenario_counts"]["PASS"], 2)
        self.assertTrue(output.with_suffix(".md").is_file())
        self.assertFalse(any(row["status"] == "PASS" for row in bound["requirements"]))

    def test_ordinary_register_check_reaudits_shared_binding_once(self):
        self.path.write_bytes(binder._json_bytes(self.report))
        bound = binder.write_binding(self.path, self.root / "validation/cached-register.json", root=self.root)
        with patch.object(binder, "verify_evidence", wraps=binder.verify_evidence) as verify:
            self.assertEqual(master.validate_register(bound, self.root), [])
            self.assertEqual(verify.call_count, 1, "87 requirement rows must not cause repeated source/Git audits")
        self.path.unlink()
        with patch.object(binder, "verify_evidence", wraps=binder.verify_evidence) as verify:
            errors = master.validate_register(bound, self.root)
            self.assertEqual(verify.call_count, 1)
            self.assertTrue(any("Bound positive input is missing or changed" in error for error in errors))
            self.assertTrue(any("references unverified evidence" in error for error in errors))

    def test_ordinary_register_check_rejects_changed_transitive_source(self):
        self.path.write_bytes(binder._json_bytes(self.report))
        bound = binder.write_binding(self.path, self.root / "validation/source-register.json", root=self.root)
        self.assertNotIn("source.py", {item["path"] for item in bound["sources"]},
                         "The changed runtime source is outside the requirement-document manifest")
        self.source.write_bytes(b"VALUE = 3\n")
        errors = master.validate_register(bound, self.root)
        self.assertTrue(any("Missing or changed current source: source.py" in error for error in errors))

    def test_ordinary_register_check_rejects_deleted_actual_output_artifact(self):
        # Exercise the real audit artifact loader with a declared synthetic
        # report. Only canonical action postcondition descriptions and source
        # inventory are fixture data; no acceptance outcome is being asserted.
        from tools import audit_bom_w18_scenario_coverage as audit
        artifact = self.root / "selected-output.json"
        artifact.write_bytes(b'{"entity_id":"P1","synthetic_validator_fixture":true}\n')
        for action in self.report["actions"]:
            action.update(expected_postcondition=action["action_id"], status="PARTIAL", executed=False,
                          positive_postcondition=False, artifacts=[])
        action = next(row for row in self.report["actions"] if row["action_id"] == "edit.length")
        action.update(status="PASS", executed=True, positive_postcondition=True, selected_ids=["P1"],
                      selection_widened=False, nonselected_stable=True,
                      checks=[{"name": "Synthetic validator fixture", "status": "PASS"}],
                      artifacts=[{"path": "selected-output.json", "sha256": master.sha256(artifact)}])
        self.report["output_hash"] = hashlib.sha256(json.dumps(self.report["actions"], sort_keys=True).encode()).hexdigest()
        matrix = SimpleNamespace(SOURCE_FILES=tuple(self.report["sources"]), digest=master.sha256,
                                 fingerprint=lambda: self.report["matrix_sha256"],
                                 POSTCONDITIONS={row["action_id"]: row["action_id"] for row in self.report["actions"]})

        def audited_fixture(path):
            audit._load_results(path, matrix)
            return self.catalog

        self.audit_mock.side_effect = audited_fixture
        self.path.write_bytes(binder._json_bytes(self.report))
        with patch.object(audit, "ROOT", self.root):
            bound = binder.write_binding(self.path, self.root / "validation/artifact-register.json", root=self.root)
            self.assertEqual(master.validate_register(bound, self.root), [])
            artifact.unlink()
            errors = master.validate_register(bound, self.root)
        self.assertTrue(any("artifact" in error.lower() and ("missing" in error.lower() or "outside" in error.lower())
                            for error in errors), errors)

    def test_nonexistent_or_noncommit_sha_rejected(self):
        for commit in ("0" * 40, self.git("hash-object", "source.py").strip(), self.commit[:7]):
            with self.subTest(commit=commit):
                self.report["commit"] = commit
                with self.assertRaisesRegex(ValueError, "commit|Git SHA"):
                    self.build()

    def test_changed_source_rejected_even_if_report_hash_is_updated(self):
        self.source.write_bytes(b"VALUE = 2\n")
        with self.assertRaisesRegex(ValueError, "changed current source"):
            self.build()
        self.report["sources"]["source.py"] = master.sha256(self.source)
        with self.assertRaisesRegex(ValueError, "differs from evidence commit"):
            self.build()

    def test_missing_current_and_untracked_source_rejected(self):
        self.source.unlink()
        with self.assertRaisesRegex(ValueError, "Missing or changed current source"):
            self.build()
        self.source.write_bytes(b"VALUE = 1\n")
        untracked = self.root / "untracked.py"
        untracked.write_bytes(b"NOT_IN_COMMIT = True\n")
        self.report["sources"]["untracked.py"] = master.sha256(untracked)
        with self.assertRaisesRegex(ValueError, "absent from the evidence commit"):
            self.build()

    def test_crlf_normalization_cannot_hide_changed_execution_bytes(self):
        self.source.write_bytes(b"VALUE = 1\r\n")
        self.report["sources"]["source.py"] = master.sha256(self.source)
        with self.assertRaisesRegex(ValueError, "differs from evidence commit"):
            self.build()

    def test_unstable_failed_and_false_installed_reports_rejected(self):
        variants = [{"source_unchanged_during_run": False}, {"result": "FAIL"},
                    {"installed_main_window": True}, {"installed_commit": self.commit},
                    {"installed_tested": "PASS"}, {"release_ready": True},
                    {"external_acceptance_proven": True}]
        for variant in variants:
            with self.subTest(variant=variant):
                self.report = {**deepcopy(self.base_report), **variant}
                with self.assertRaises(ValueError):
                    self.build()
        self.report = deepcopy(self.base_report)
        self.catalog["installed_main_window_proven"] = True
        with self.assertRaisesRegex(ValueError, "installed_main_window_proven"):
            self.build()

    def test_missing_envelope_and_malformed_source_rejected(self):
        for key in binder.ENVELOPE:
            with self.subTest(missing=key):
                self.report = deepcopy(self.base_report)
                del self.report[key]
                with self.assertRaisesRegex(ValueError, "seven required"):
                    self.build()
        self.report = deepcopy(self.base_report)
        self.report["sources"]["../outside.py"] = "1" * 64
        with self.assertRaisesRegex(ValueError, "Invalid relative source path"):
            self.build()

    def test_mismatched_matrix_input_output_and_nested_installed_rejected(self):
        self.report["input_hash"] = "3" * 64
        with self.assertRaisesRegex(ValueError, "input hash differs"):
            self.build()
        self.report = deepcopy(self.base_report)
        self.report["actions"][0]["forged"] = True
        with self.assertRaisesRegex(ValueError, "output hash does not match"):
            self.build()
        self.report = deepcopy(self.base_report)
        self.report["actions"][0]["installed_tested"] = True
        self.report["output_hash"] = hashlib.sha256(json.dumps(self.report["actions"], sort_keys=True).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "cannot assert installed acceptance"):
            self.build()

    def test_incomplete_scenario_matrix_and_unsupported_waivers_rejected(self):
        for change in ("missing", "unsupported_status", "missing_evidence", "unreviewed_waiver", "false_na", "duplicate_action"):
            with self.subTest(change=change):
                self.catalog.clear()
                self.catalog.update(deepcopy(self.base_catalog))
                action = self.catalog["actions"][0]
                entry = action["scenarios"]["valid_single"]
                if change == "missing":
                    del action["scenarios"]["undo"]
                elif change == "unsupported_status":
                    entry["status"] = "COMPLETE"
                elif change == "missing_evidence":
                    entry["status"] = "PASS"
                elif change == "unreviewed_waiver":
                    entry["applicable"] = False
                elif change == "false_na":
                    entry["status"] = "NOT_APPLICABLE"
                else:
                    self.catalog["actions"][-1] = deepcopy(action)
                with self.assertRaises(ValueError):
                    self.build()

    def test_reaudit_detects_changed_input_and_tampered_bound_report(self):
        evidence = self.build()
        path = self.root / "bound.json"
        path.write_bytes(binder._json_bytes(evidence))
        self.assertEqual(binder.verify_evidence(path, self.root), evidence)
        tampered = deepcopy(evidence)
        tampered["requirements"]["W18-edit.length"]["scenarios"]["undo"] = "PASS"
        path.write_bytes(binder._json_bytes(tampered))
        with self.assertRaisesRegex(ValueError, "does not match freshly audited"):
            binder.verify_evidence(path, self.root)
        path.write_bytes(binder._json_bytes(evidence))
        self.path.write_bytes(self.path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "input is missing or changed"):
            binder.verify_evidence(path, self.root)
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "input is missing or changed"):
            binder.verify_evidence(path, self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
