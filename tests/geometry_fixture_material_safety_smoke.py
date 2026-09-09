"""Fixture correction must not reintroduce inferred grades or weaken safety gates."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.manufacturing_contact_core_smoke import _workbench_part, _transform
from cws_convertor.project.workbench import evaluate_workbench_revision


class GeometryFixtureMaterialSafetyTests(unittest.TestCase):
    def revision(self):
        part = _workbench_part("P1", _transform())
        return deepcopy(part.workbench["current_revision"])

    def test_exact_reviewed_fixture_is_valid(self):
        revision = self.revision()
        self.assertEqual(revision["production_properties"]["material"], "S235JR")
        self.assertEqual(evaluate_workbench_revision(revision), [])

    def test_grade_free_source_still_blocks_production(self):
        revision = self.revision()
        revision["production_properties"].update(material="", material_grade="")
        issues = evaluate_workbench_revision(revision)
        blocking = {item["code"] for item in issues if item["blocking"]}
        self.assertTrue({"CWS-WB-MISSING-MATERIAL", "CWS-WB-MISSING-MATERIAL-GRADE"} <= blocking)
        self.assertEqual(revision["production_properties"]["material"], "")

    def test_material_grade_conflict_still_blocks_production(self):
        revision = self.revision()
        revision["production_properties"]["material_grade"] = "S355JR"
        issues = evaluate_workbench_revision(revision)
        self.assertTrue(any(i["code"] == "CWS-WB-MATERIAL-CONFLICT" and i["blocking"] for i in issues))

    def test_missing_profile_still_blocks_production(self):
        revision = self.revision()
        revision["production_properties"]["profile"] = ""
        self.assertTrue(any(i["code"] == "CWS-WB-MISSING-PROFILE" and i["blocking"] for i in evaluate_workbench_revision(revision)))

    def test_ambiguous_historical_fixture_is_not_silently_accepted(self):
        revision = self.revision()
        revision["production_properties"]["material"] = "S235"
        self.assertTrue(any(i["blocking"] for i in evaluate_workbench_revision(revision)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
