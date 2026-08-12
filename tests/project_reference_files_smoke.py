from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ImportStrategy, inspect_model_file

REFERENCE_ROOT = Path(os.environ.get("CWS_REFERENCE_ROOT", "/mnt/data"))
IFC_NAME = "TAS_RVB Defensie onderbouw te Leeuwarden- Rev4 [definitief].ifc"
STEP_EXPECTATIONS = {
    "Samenstel nieuw - 11864_Predeterminado (1).step": {
        "product": "11864_Predeterminado",
        "advanced_faces": 118,
        "circles": 117,
        "cylindrical_surfaces": 37,
    },
    "Samenstel nieuw - 11881_Predeterminado (1).step": {
        "product": "11881_Predeterminado",
        "advanced_faces": 2582,
        "circles": 662,
        "cylindrical_surfaces": 341,
    },
    "Samenstel nieuw - 2x voetplaat hoog.step": {
        "product": "2x voetplaat hoog",
        "advanced_faces": 14,
        "circles": 16,
        "cylindrical_surfaces": 8,
    },
}


@unittest.skipUnless((REFERENCE_ROOT / IFC_NAME).is_file(), "Grote referentiebestanden niet aanwezig")
class ProjectReferenceFileTests(unittest.TestCase):
    def test_tekla_ifc_reference_counts_and_search_evidence(self) -> None:
        result = inspect_model_file(REFERENCE_ROOT / IFC_NAME)
        self.assertEqual(result.schema, "IFC2X3")
        self.assertEqual(result.import_strategy, ImportStrategy.SEMANTIC_STRUCTURE)
        expected = {
            "assemblies": 353,
            "plates": 1293,
            "beams": 707,
            "columns": 369,
            "mechanical_fasteners": 723,
            "weld_fastener_objects": 2654,
            "footings": 38,
            "building_element_proxies": 19,
            "slabs": 3,
        }
        for key, value in expected.items():
            self.assertEqual(result.class_summary[key], value, key)
        checks = result.reference_checks
        for key in (
            "MLO4_found",
            "LO4_found",
            "STRIP5*120_found",
            "S235JR_found",
            "length_160_mm_found",
            "assembly_weight_0_6_kg_found",
            "bolt_or_hole_diameter_14_mm_found",
        ):
            self.assertTrue(checks[key], key)
        self.assertEqual(
            checks["repeated_mark_counts"],
            {"LA1": 71, "A1": 37, "MP1": 18, "MP2": 16},
        )
        self.assertEqual(result.entity_counts["IFCFACETEDBREP"], 328)
        self.assertTrue(any("gefacetteerde BREP" in item for item in result.warnings))

    def test_step_references_are_one_product_one_solid_without_fiction(self) -> None:
        for file_name, expected in STEP_EXPECTATIONS.items():
            with self.subTest(file_name=file_name):
                source = REFERENCE_ROOT / file_name
                self.assertTrue(source.is_file(), file_name)
                result = inspect_model_file(source, include_geometry=False)
                self.assertTrue(result.schema.startswith("AP242"))
                self.assertEqual(result.product_count, 1)
                self.assertEqual(result.solid_count, 1)
                self.assertEqual(result.assembly_relation_count, 0)
                self.assertEqual(result.import_strategy, ImportStrategy.SEPARATE_SOLIDS)
                self.assertEqual(
                    result.reference_checks["product_names"],
                    [expected["product"]],
                )
                for key in ("advanced_faces", "circles", "cylindrical_surfaces"):
                    self.assertEqual(result.class_summary[key], expected[key], key)
                self.assertIn("één productrecord en één BREP-solid", result.strategy_reason)

    def test_two_footplates_name_does_not_trigger_automatic_split(self) -> None:
        result = inspect_model_file(REFERENCE_ROOT / "Samenstel nieuw - 2x voetplaat hoog.step")
        self.assertEqual(result.product_count, 1)
        self.assertEqual(result.solid_count, 1)
        self.assertTrue(any("niet automatisch opsplitsen" in item for item in result.warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
