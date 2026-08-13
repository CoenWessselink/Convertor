from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import Assembly, Part, ProjectModel
from cws_convertor.project.classification import (
    classify_project,
    normalize_material,
    normalize_profile,
    set_manual_part_classification,
)


class ClassificationTests(unittest.TestCase):
    def test_normalisation_is_conservative(self) -> None:
        self.assertEqual(normalize_material("STEEL/S235JR"), "S235JR")
        self.assertEqual(normalize_material("s355 jr"), "S355JR")
        self.assertEqual(normalize_profile("STRIP 5 × 120"), "STRIP5*120")
        self.assertEqual(normalize_profile("HEA-140"), "HEA140")

    def test_rules_production_identity_and_manual_review(self) -> None:
        project = ProjectModel.new("Classification")
        parts = [
            Part(internal_id="steel", name="PLAAT", part_position="P1", profile="STRIP5*120", material="S235JR", material_grade="S235JR", length_mm=160, geometry_descriptor={"bbox": [160,120,5]}),
            Part(internal_id="nut", name="MOER", part_position="N1", profile="MOER_M16", material="8.8", material_grade="8.8", length_mm=13, geometry_descriptor={"bbox": [24,24,13]}),
            Part(internal_id="wood", name="VUREN REGEL", part_position="W1", profile="45*70", material="VUREN", material_grade="VUREN", length_mm=1000, geometry_descriptor={"bbox": [1000,70,45]}),
            Part(internal_id="step", name="11864_Predeterminado", part_type="step_brep", geometry_descriptor={"source_geometry_hash": "a"*64}),
        ]
        for part in parts:
            part.recompute_hashes()
            project.add_entity(part)
        report = classify_project(project, user="test")
        self.assertEqual(report.category_counts, {"make_part": 1, "non_steel": 1, "purchased_item": 1, "unknown": 1})
        self.assertEqual(project.parts["steel"].classification_status, "automatic")
        self.assertEqual(len(project.parts["steel"].production_identity_hash), 64)
        self.assertTrue(project.parts["step"].blocking_issues())
        report2 = set_manual_part_classification(
            project, "step", "purchased_item", user="reviewer", reason="Leveranciersdeel volgens artikelkaart"
        )
        self.assertEqual(project.parts["step"].classification_status, "confirmed")
        self.assertEqual(project.parts["step"].category, "purchased_item")
        self.assertEqual(report2.unknown_part_count, 0)

    def test_same_mark_different_geometry_is_blocking(self) -> None:
        project = ProjectModel.new("Conflicts")
        for index, length in enumerate((100.0, 120.0), 1):
            part = Part(
                internal_id=f"p{index}", name="PLAAT", part_position="P1", profile="STRIP5*50",
                material="S235JR", material_grade="S235JR", length_mm=length,
                geometry_descriptor={"bbox": [length,50,5]},
            )
            part.recompute_hashes(); project.add_entity(part)
        report = classify_project(project)
        conflicts = [x for x in report.conflicts if x.conflict_type == "same_mark_different_manufacturing"]
        self.assertEqual(len(conflicts), 1)
        self.assertTrue(conflicts[0].blocking)


if __name__ == "__main__":
    unittest.main(verbosity=2)
