from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from material_database import MaterialDatabase
from cws_convertor.project import Part, ProjectModel, ProjectValidationError
from cws_convertor.project.classification import decide_part_classification, set_manual_part_classification


class MaterialClassificationSafetyTests(unittest.TestCase):
    def test_every_catalog_family_has_a_deterministic_category(self):
        for definition in MaterialDatabase().materials:
            with self.subTest(material=definition.code):
                part = Part(internal_id="p1", part_position="P1", profile="HEA140", material=definition.code,
                            material_grade=definition.code)
                result = decide_part_classification(part)
                self.assertNotEqual(result.category, "unknown")
                self.assertEqual(result.normalized_material, definition.code)
                self.assertEqual(result.material_confidence, 1.0)

    def test_geometry_or_source_class_never_proves_unknown_material(self):
        for source_class in ("IFCSLAB", "IFCFOOTING", "IFCBEAM", "IFCPLATE"):
            part = Part(internal_id="p1", part_position="P1", profile="HEA140", material="DUMMY",
                        geometry_hash="a" * 64, properties={"ifc_entity_type": source_class})
            result = decide_part_classification(part)
            self.assertEqual(result.status, "review_required")
            self.assertEqual(result.normalized_material, "")
            self.assertEqual(result.material_confidence, 0.0)
            self.assertTrue(result.blocking_reasons)

    def test_generic_steel_family_does_not_invent_toughness_grade(self):
        for raw in ("S235", "S355", "STEEL/S355"):
            part = Part(internal_id="p1", part_position="P1", profile="HEA140", material=raw)
            result = decide_part_classification(part)
            self.assertEqual(result.status, "review_required")
            self.assertEqual(result.normalized_material, "")
            self.assertEqual(result.material_confidence, 0.0)

    def test_material_grade_conflict_is_not_normalized_away(self):
        part = Part(internal_id="p1", part_position="P1", profile="HEA140", material="S235JR", material_grade="S355JR")
        result = decide_part_classification(part)
        self.assertEqual(result.status, "review_required")
        self.assertEqual(result.normalized_material, "")
        self.assertEqual(result.material_confidence, 0.0)

    def test_category_review_never_confirms_unreviewed_fields(self):
        project = ProjectModel.new("Independent evidence")
        part = Part(internal_id="p1", part_position="P1", profile="HEA140", material="S355JR")
        part.recompute_hashes()
        project.add_entity(part)
        set_manual_part_classification(project, "p1", "make_part", user="reviewer", reason="Category checked")
        self.assertEqual(part.material_confidence, 0.0)
        self.assertEqual(part.profile_confidence, 0.0)
        with self.assertRaises(ProjectValidationError):
            set_manual_part_classification(project, "p1", "make_part", user="reviewer",
                                           reason="Unknown", normalized_material="DUMMY")
        with self.assertRaises(ProjectValidationError):
            set_manual_part_classification(project, "p1", "make_part", user=" ", reason="Checked")
        set_manual_part_classification(project, "p1", "make_part", user="reviewer",
                                       reason="Certificate checked", normalized_material="S355JR")
        self.assertEqual(part.material_confidence, 1.0)
        self.assertEqual(part.profile_confidence, 0.0)
        self.assertEqual(part.field_provenance["normalized_material"].confirmed_by, "reviewer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
