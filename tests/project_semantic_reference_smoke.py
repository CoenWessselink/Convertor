from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession

REFERENCE_ROOT = Path(os.environ.get("CWS_REFERENCE_ROOT", "/mnt/data"))
IFC_NAME = "TAS_RVB Defensie onderbouw te Leeuwarden- Rev4 [definitief].ifc"
STEP_NAMES = (
    "Samenstel nieuw - 11864_Predeterminado (1).step",
    "Samenstel nieuw - 11881_Predeterminado (1).step",
    "Samenstel nieuw - 2x voetplaat hoog.step",
)
ALL_PRESENT = (REFERENCE_ROOT / IFC_NAME).is_file() and all(
    (REFERENCE_ROOT / name).is_file() for name in STEP_NAMES
)


@unittest.skipUnless(ALL_PRESENT, "Semantische referentiemodellen niet aanwezig")
class ProjectSemanticReferenceTests(unittest.TestCase):
    def test_real_ifc_and_step_sources_materialise_without_fiction(self) -> None:
        sources = [REFERENCE_ROOT / IFC_NAME, *(REFERENCE_ROOT / name for name in STEP_NAMES)]
        session = ProjectSession.new("Real semantic references")
        registrations = session.register_sources(
            sources,
            include_step_geometry=False,
            user="reference-test",
        )
        source_ids = [item.source.source_id for item in registrations]
        results = session.semantic_import_sources(source_ids, user="reference-test")
        by_name = {item.file_name: item for item in results}

        ifc = by_name[IFC_NAME]
        self.assertEqual(
            ifc.entity_counts,
            {
                "assemblies": 353,
                "parts": 2429,
                "fasteners": 723,
                "welds": 2654,
                "total_materialised": 6159,
            },
        )
        expected_classes = {
            "IFCELEMENTASSEMBLY": 353,
            "IFCPLATE": 1293,
            "IFCBEAM": 707,
            "IFCCOLUMN": 369,
            "IFCMECHANICALFASTENER": 723,
            "IFCFASTENER": 2654,
            "IFCFOOTING": 38,
            "IFCBUILDINGELEMENTPROXY": 19,
            "IFCSLAB": 3,
        }
        for key, value in expected_classes.items():
            self.assertEqual(ifc.source_class_counts[key], value, key)
        self.assertEqual(ifc.relationship_counts["IFCRELAGGREGATES"], 356)
        self.assertEqual(ifc.evidence["MLO4_assembly_count"], 4)
        self.assertEqual(len(ifc.evidence["MLO4_LO4_links"]), 4)
        self.assertEqual(ifc.evidence["bolt_or_hole_diameter_14_count"], 4)
        self.assertEqual(ifc.evidence["connected_weld_count"], 2654)
        self.assertEqual(
            ifc.evidence["repeated_marks"],
            {"LA1": 71, "A1": 37, "MP1": 18, "MP2": 16},
        )
        lo4 = ifc.evidence["LO4_parts"]
        self.assertEqual(len(lo4), 4)
        for item in lo4:
            self.assertEqual(item["profile"], "STRIP5*120")
            self.assertEqual(item["material"], "S235JR")
            self.assertAlmostEqual(item["length_mm"], 160.0)
            self.assertAlmostEqual(item["mass_each_kg"], 0.62)
        self.assertEqual(len({item["geometry_hash"] for item in lo4}), 1)
        self.assertEqual(len({item["manufacturing_hash"] for item in lo4}), 1)

        for step_name in STEP_NAMES:
            with self.subTest(step=step_name):
                step = by_name[step_name]
                self.assertEqual(step.strategy, "B_separate_solids")
                self.assertEqual(step.entity_counts["parts"], 1)
                self.assertEqual(step.entity_counts["assemblies"], 0)
                self.assertEqual(step.evidence["product_count"], 1)
                self.assertEqual(step.evidence["solid_root_count"], 1)
                self.assertEqual(step.evidence["materialised_part_count"], 1)
                self.assertTrue(step.evidence["filename_not_used_for_splitting"])
                if "11881" in step_name:
                    self.assertEqual(
                        step.evidence["profile_recognition"]["status"],
                        "deferred_large_model",
                    )

        self.assertEqual(session.project.entity_counts()["assembly"], 353)
        self.assertEqual(session.project.entity_counts()["part"], 2432)
        self.assertEqual(session.project.entity_counts()["fastener"], 723)
        self.assertEqual(session.project.entity_counts()["weld"], 2654)
        self.assertFalse(session.project.production_gate()["allowed"])
        session.project.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
