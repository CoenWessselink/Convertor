"""Requirements-register corruption and false acceptance regression checks."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.master_requirements_v2 import (  # noqa: E402
    DIMENSIONS, SCENARIOS, build_register, canonical_actions, read_json,
    statements, summarize, validate_register, PROMPT,
)


class MasterRequirementsV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.register = build_register()

    def errors(self, register):
        register["summary"] = summarize(register)
        return validate_register(register, check_source_hashes=False)

    def test_complete_sources_and_all_ten_blocks(self):
        self.assertEqual(validate_register(self.register), [])
        source_rows = [row for row in self.register["requirements"] if row["source"] == PROMPT]
        self.assertEqual(len(source_rows), len(statements(ROOT / PROMPT)))
        self.assertEqual({row["block"] for row in source_rows if row["block"]}, set(range(1, 11)))

    def test_historical_pass_is_not_acceptance(self):
        historical = [row for row in self.register["requirements"] if row.get("historical_status") == "PASS"]
        self.assertGreater(len(historical), 290)
        self.assertTrue(all(row["status"] != "PASS" and not row["evidence"] for row in historical))
        self.assertTrue(all(self.register["summary"]["dimensions"][key]["proven"] == 0 for key in DIMENSIONS))

    def test_all_87_actions_all_15_scenarios_and_mutating_obligations(self):
        expected = {item["action_id"] for item in canonical_actions()}
        rows = [row for row in self.register["requirements"] if row.get("action_id")]
        self.assertEqual(len(rows), 87)
        self.assertEqual({row["action_id"] for row in rows}, expected)
        for row in rows:
            self.assertEqual(set(row["scenarios"]), set(SCENARIOS))
            self.assertTrue(all(value["state"] == "UNVERIFIED" for value in row["scenarios"].values()))
            if row["action_definition"]["mutating"]:
                self.assertTrue(row["scenarios"]["undo"]["required"])
                self.assertTrue(row["scenarios"]["save_reopen"]["required"])

    def test_duplicate_and_missing_ids_are_rejected(self):
        duplicate = deepcopy(self.register)
        duplicate["requirements"].append(deepcopy(duplicate["requirements"][0]))
        self.assertTrue(any("Duplicate" in error for error in self.errors(duplicate)))
        missing = deepcopy(self.register)
        missing["requirements"] = [row for row in missing["requirements"] if row.get("action_id") != "edit.length"]
        self.assertTrue(any("87 canonical" in error for error in self.errors(missing)))
        missing_source = deepcopy(self.register)
        missing_source["requirements"] = [row for row in missing_source["requirements"] if row["requirement_id"] != "PI-0001"]
        self.assertTrue(any("Missing source statements" in error for error in self.errors(missing_source)))

    def test_missing_required_field_rejected(self):
        register = deepcopy(self.register)
        del register["requirements"][0]["installed_commit"]
        self.assertTrue(any("missing fields" in error for error in self.errors(register)))

    def test_source_only_and_fabricated_green_claims_rejected(self):
        register = deepcopy(self.register)
        row = register["requirements"][0]
        row.update(status="PASS", blocker="")
        self.assertTrue(any("unsupported PASS" in error for error in self.errors(register)))
        row["evidence"] = ["validation/historical_green_report.json"]
        row["dimensions"] = {key: {"state": "PASS", "evidence": ["claimed"]} for key in DIMENSIONS}
        self.assertTrue(any("invalid evidence envelope" in error for error in self.errors(register)))
        self.assertTrue(any("unresolved applicability" in error for error in self.errors(register)))

    def test_unknown_runtime_applicability_is_not_counted_as_required(self):
        row = next(row for row in self.register["requirements"] if row["requirement_id"] == "PI-0001")
        self.assertIsNone(row["dimensions"]["installed_tested"]["applicable"])
        self.assertIsNone(row["dimensions"]["real_world_tested"]["applicable"])
        self.assertNotIn("real_world_tested", row["required_dimensions"])
        real_world = self.register["summary"]["dimensions"]["real_world_tested"]
        self.assertGreater(real_world["applicability_unknown"], 0)
        self.assertLess(real_world["required"], self.register["summary"]["applicable"])
        self.assertIsNone(real_world["product_completion_percent"])

    def test_dimension_and_scenario_presence_cannot_claim_pass(self):
        register = deepcopy(self.register)
        row = next(row for row in register["requirements"] if row.get("action_id") == "edit.length")
        row["dimensions"]["integration_tested"]["state"] = "PASS"
        row["scenarios"]["positive_postcondition"]["state"] = "PASS"
        errors = self.errors(register)
        self.assertTrue(any("integration_tested PASS lacks evidence" in error for error in errors))
        self.assertTrue(any("positive_postcondition has no current evidence" in error for error in errors))

    def test_generic_green_report_cannot_promote_requirement_dimension(self):
        register = deepcopy(self.register)
        row = register["requirements"][0]
        report = {
            "commit": register["source_commit"], "app_version": "test-fixture",
            "environment": {"declared_fixture": True}, "input_hash": "1" * 64,
            "scenario": "generic_script_success", "result": "PASS", "output_hash": "2" * 64,
        }
        with tempfile.TemporaryDirectory(prefix="mrr-v2-test-", dir=ROOT / "tests") as directory:
            path = Path(directory) / "generic-proof.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            relative = path.relative_to(ROOT).as_posix()
            row["evidence"] = [{**report, "path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
            row["dimensions"]["integration_tested"] = {"state": "PASS", "evidence": [relative]}
            errors = self.errors(register)
            self.assertTrue(any("lacks matching requirement/envelope binding" in error for error in errors))
            self.assertTrue(any("references unverified evidence" in error for error in errors))

    def test_disabling_acceptance_dimensions_cannot_create_pass(self):
        register = deepcopy(self.register)
        row = register["requirements"][0]
        row.update(status="PASS", required_dimensions=[])
        self.assertTrue(any("removed dimension" in error for error in self.errors(register)))

    def test_false_external_and_scope_acceptance_rejected(self):
        register = deepcopy(self.register)
        row = next(row for row in register["requirements"] if row.get("action_id") == "drawing.print")
        self.assertEqual(row["status"], "BLOCKED_EXTERNAL")
        row["status"] = "PASS"
        self.assertTrue(any("external acceptance not proven" in error for error in self.errors(register)))
        row.update(status="OUT_OF_SCOPE_APPROVED", applicable=False)
        self.assertTrue(any("explicit source approval" in error for error in self.errors(register)))

    def test_summary_and_source_tampering_rejected(self):
        register = deepcopy(self.register)
        register["summary"]["dimensions"]["release_ready"]["evidence_coverage_percent"] = 100
        self.assertTrue(any("Summary" in error for error in validate_register(register)))
        register = deepcopy(self.register)
        register["sources"][0]["sha256"] = "0" * 64
        self.assertTrue(any("Source hash changed" in error for error in validate_register(register)))

    def test_checked_in_register_is_valid(self):
        path = ROOT / "requirements/MASTER_REQUIREMENTS_V2.json"
        self.assertTrue(path.is_file())
        self.assertEqual(validate_register(read_json(path)), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
