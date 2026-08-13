from __future__ import annotations
from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.project.classification import classify_project
from cws_convertor.project.storage import ProjectStore

CANDIDATES = [
    Path(os.environ.get("CWS_REFERENCE_PROJECT", "")),
    Path("/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"),
    ROOT / "validation_data" / "CWS_Convertor_REFERENCE_PROJECT.cwscproj",
]
REFERENCE = next((path for path in CANDIDATES if str(path) and path.is_file()), None)


@unittest.skipUnless(REFERENCE is not None, "CWS reference project not available")
class ReferenceClassificationBOMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = ProjectStore().open(REFERENCE, read_only=True).project
        cls.classification = classify_project(cls.project, user="validation")
        cls.snapshot = build_bom_snapshot(cls.project, user="validation", classify_if_needed=False)

    def test_classification_reference_counts(self) -> None:
        self.assertEqual(self.classification.category_counts, {
            "make_part": 1497,
            "non_steel": 102,
            "purchased_item": 831,
            "unknown": 2,
        })
        self.assertEqual(self.classification.identity_conflict_count, 59)

    def test_bom_reference_counts_and_balances(self) -> None:
        expected = {
            "part_group_count": 315,
            "assembly_group_count": 139,
            "purchase_group_count": 13,
            "fastener_group_count": 35,
            "material_group_count": 122,
            "traceability_record_count": 6162,
            "blocking_conflict_count": 52,
            "warning_conflict_count": 1,
            "fastener_quantity": 1977,
            "weld_object_count": 2654,
        }
        for key, value in expected.items():
            self.assertEqual(self.snapshot.summary[key], value, key)
        self.assertAlmostEqual(self.snapshot.summary["total_part_mass_kg"], 147480.02, places=2)
        self.assertAlmostEqual(self.snapshot.summary["total_part_surface_m2"], 1134.720327727, places=9)
        self.assertTrue(self.snapshot.validation.passed)
        self.assertFalse(self.snapshot.validation.production_ready)

    def test_lo4_is_one_group_of_four(self) -> None:
        rows = [row for row in self.snapshot.part_bom if row.part_position == "LO4"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.quantity, 4)
        self.assertEqual(row.profile, "STRIP5*120")
        self.assertEqual(row.material, "S235JR")
        self.assertEqual(row.length_mm, 160.0)
        self.assertEqual(row.assembly_marks, ["MLO4"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
