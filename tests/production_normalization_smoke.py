from __future__ import annotations

import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.model import Part, ReviewStatus, SourceIdentity
from cws_convertor.project.production_normalization import (
    infer_profile_type,
    prepare_exact_imported_part,
)


class ProductionNormalizationSmoke(unittest.TestCase):
    def _part(self, primitives: dict[str, int]) -> Part:
        part = Part(
            internal_id="normalization-part",
            name="K60/3",
            part_position="P1",
            part_type="IFCBEAM",
            profile="K60/3",
            material="S235JR",
            material_grade="S235JR",
            length_mm=4959.25,
            source_identity=SourceIdentity(
                source_format="IFC",
                source_file_id="source-1",
                source_sha256="a" * 64,
                source_entity_id="34855",
            ),
            geometry_descriptor={
                "status": "semantic_source_geometry",
                "source_semantics_preserved": True,
                "source_geometry_hash": "b" * 64,
                "item_count": 1,
                "primitive_counts": primitives,
            },
            properties={
                "semantic_import": {
                    "identity_exact": True,
                    "placement_exact": True,
                    "property_mapping_exact": True,
                    "source_geometry_semantics_preserved": True,
                }
            },
        )
        part.recompute_hashes()
        return part

    def test_exact_straight_profile_gets_editable_workbench_but_not_false_release(self) -> None:
        part = self._part({"IFCEXTRUDEDAREASOLID": 1})
        part.profile = "HEA200"
        part.recompute_hashes()
        self.assertTrue(prepare_exact_imported_part(part))
        self.assertEqual("i", part.profile_type)
        self.assertEqual(ReviewStatus.REVIEW_REQUIRED.value, part.status)
        self.assertEqual([], part.workbench["current_revision"]["validation_issues"])
        self.assertTrue(part.properties["square_end_cuts_confirmed"])

    def test_boolean_geometry_stays_review_required(self) -> None:
        part = self._part({"IFCEXTRUDEDAREASOLID": 1, "IFCBOOLEANCLIPPINGRESULT": 1})
        self.assertFalse(prepare_exact_imported_part(part))
        self.assertFalse(part.workbench)
        self.assertNotEqual(ReviewStatus.VALIDATED.value, part.status)

    def test_profile_family_mapping(self) -> None:
        self.assertEqual("i", infer_profile_type("HEA200", "IFCCOLUMN"))
        self.assertEqual("flat", infer_profile_type("STRIP10*100", "IFCBEAM"))
        self.assertEqual("rhs", infer_profile_type("K100/5", "IFCCOLUMN"))
        self.assertEqual("fastener", infer_profile_type("MOER_M16", "IFCBEAM"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
