from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import FieldProvenance, Part, ProjectSession, ProjectValidationError
from cws_convertor.project.workbench import evaluate_workbench_revision


class MaterialWorkbenchGateTests(unittest.TestCase):
    @staticmethod
    def _session() -> ProjectSession:
        session = ProjectSession.new("Material gate")
        part = Part(
            internal_id="p1",
            name="Profile",
            part_position="P1",
            profile="HEA140",
            material="S355JR",
            material_grade="S355JR",
            normalized_profile="HEA140",
            normalized_material="S355JR",
            profile_confidence=1.0,
            material_confidence=1.0,
            geometry_descriptor={"source_geometry_hash": "a" * 64},
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="test")
        return session

    def test_entity_confidence_does_not_fake_profile_confidence(self) -> None:
        session = self._session()
        part = session.project.parts["p1"]
        part.profile_confidence = 0.0
        part.confidence = 1.0
        state = session.start_part_workbench("p1", user="reviewer")
        self.assertEqual(state["current_revision"]["recognition"]["confidence"], 0.0)

    def test_missing_material_and_grade_block_review(self) -> None:
        session = self._session()
        session.start_part_workbench("p1", user="reviewer")
        session.update_part_workbench(
            "p1",
            {
                "part_form": "profile",
                "recognition": {"candidate": "HEA140", "confidence": 1.0, "confirmed": True},
                "production_properties": {
                    "profile": "HEA140",
                    "material": "",
                    "material_grade": "",
                    "part_position": "P1",
                },
            },
            user="reviewer",
            reason="Material deliberately removed",
        )
        revision = session.project.parts["p1"].workbench["current_revision"]
        codes = {item["code"] for item in evaluate_workbench_revision(revision)}
        self.assertIn("CWS-WB-MISSING-MATERIAL", codes)
        self.assertIn("CWS-WB-MISSING-MATERIAL-GRADE", codes)
        with self.assertRaises(ProjectValidationError):
            session.review_part_workbench("p1", user="reviewer")

    def test_human_review_confirms_material_identity_and_provenance(self) -> None:
        session = self._session()
        session.start_part_workbench("p1", user="reviewer")
        session.update_part_workbench(
            "p1",
            {
                "part_form": "profile",
                "recognition": {"candidate": "HEA140", "confidence": 1.0, "confirmed": True},
                "reference_sides": [
                    {
                        "side_id": "v",
                        "label": "Web",
                        "face_ref": "source:face:v",
                        "confirmed": True,
                    }
                ],
            },
            user="reviewer",
            reason="Profile and material checked",
        )
        session.review_part_workbench("p1", user="reviewer")
        part = session.project.parts["p1"]
        self.assertEqual(part.classification_status, "confirmed")
        self.assertEqual(part.material_confidence, 1.0)
        self.assertEqual(part.profile_confidence, 1.0)
        self.assertEqual(len(part.production_identity_hash), 64)
        self.assertEqual(part.field_provenance["material"].confirmed_by, "reviewer")
        self.assertEqual(part.field_provenance["material"].status, "confirmed")

    def test_conflicting_and_unknown_grades_block_workbench_review(self) -> None:
        session = self._session()
        session.start_part_workbench("p1", user="reviewer")
        for grade, expected in (("S235JR", "CWS-WB-MATERIAL-CONFLICT"),
                                ("DUMMY", "CWS-WB-UNKNOWN-MATERIAL-GRADE")):
            session.update_part_workbench(
                "p1", {"production_properties": {"profile": "HEA140", "material": "S355JR",
                                                 "material_grade": grade}},
                user="reviewer", reason="Negative material test",
            )
            codes = {item["code"] for item in evaluate_workbench_revision(
                session.project.parts["p1"].workbench["current_revision"])}
            self.assertIn(expected, codes)
            with self.assertRaises(ProjectValidationError):
                session.review_part_workbench("p1", user="reviewer")

    def test_material_edit_invalidates_old_field_confirmation(self) -> None:
        session = self._session()
        session.start_part_workbench("p1", user="reviewer")
        part = session.project.parts["p1"]
        part.field_provenance["material"] = FieldProvenance(
            method="manual_review", confidence=1.0, status="confirmed", confirmed_by="previous-reviewer")
        session.update_part_workbench(
            "p1", {"production_properties": {"profile": "HEA140", "material": "S235JR",
                                             "material_grade": "S235JR"}},
            user="editor", reason="Material changed",
        )
        part = session.project.parts["p1"]
        self.assertEqual(part.material_confidence, 0.0)
        self.assertEqual(part.field_provenance["material"].confidence, 0.0)
        self.assertEqual(part.field_provenance["material"].confirmed_by, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
