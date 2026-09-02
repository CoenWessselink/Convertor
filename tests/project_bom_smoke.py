from __future__ import annotations
from pathlib import Path
import tempfile
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom import build_bom_snapshot, export_bom_package
from cws_convertor.bom.export import safe_spreadsheet_value
from cws_convertor.project import Assembly, Fastener, Part, ProjectModel, Weld


class BOMTests(unittest.TestCase):
    def _project(self) -> ProjectModel:
        project = ProjectModel.new("BOM test")
        part_ids = []
        for index in range(2):
            part = Part(
                internal_id=f"part-{index}", name="PLAAT", part_position="LO4", profile="STRIP5*120",
                material="S235JR", material_grade="S235JR", length_mm=160.0,
                mass_each_kg=0.62, surface_area_each_m2=0.035,
                geometry_descriptor={"bbox": [160,120,5]},
            )
            part.recompute_hashes(); project.add_entity(part); part_ids.append(part.internal_id)
        bought = Part(
            internal_id="nut", name="MOER", part_position="N1", profile="MOER_M16",
            material="8.8", material_grade="8.8", length_mm=13,
            geometry_descriptor={"bbox": [24,24,13]},
        )
        bought.recompute_hashes(); project.add_entity(bought)
        fastener = Fastener(internal_id="f1", name="BOUT", fastener_type="BOUT", diameter_mm=16, grade="8.8", length_mm=40, quantity=4)
        weld = Weld(internal_id="w1", name="Weld", weld_type="fillet", length_mm=100)
        project.add_entity(fastener); project.add_entity(weld)
        assembly = Assembly(
            internal_id="a1", assembly_mark="MLO4", name="MLO4",
            part_ids=part_ids + [bought.internal_id], fastener_ids=[fastener.internal_id], weld_ids=[weld.internal_id],
        )
        project.add_entity(assembly)
        for pid in assembly.part_ids:
            project.parts[pid].assembly_ids.append(assembly.internal_id)
        weld.connected_part_ids = part_ids
        project.validate()
        return project

    def test_bom_balances_and_traceability(self) -> None:
        project = self._project()
        snapshot = build_bom_snapshot(project, user="test")
        self.assertEqual(snapshot.summary["part_group_count"], 1)
        self.assertEqual(snapshot.summary["purchase_group_count"], 1)
        self.assertEqual(snapshot.summary["assembly_group_count"], 1)
        self.assertEqual(snapshot.summary["fastener_quantity"], 4)
        self.assertEqual(snapshot.summary["weld_object_count"], 1)
        self.assertEqual(snapshot.summary["traceability_record_count"], 6)
        self.assertTrue(snapshot.validation.passed)
        self.assertFalse(snapshot.validation.production_ready)
        self.assertIn("Bronbewijs ontbreekt", " ".join(snapshot.validation.messages))
        lo4 = snapshot.part_bom[0]
        self.assertEqual(lo4.quantity, 2)
        self.assertAlmostEqual(lo4.total_mass_kg, 1.24, places=6)

    def test_export_package_and_formula_injection_guard(self) -> None:
        self.assertEqual(safe_spreadsheet_value("=2+2"), "'=2+2")
        self.assertEqual(safe_spreadsheet_value(" @SUM(A1:A2)"), "' @SUM(A1:A2)")
        snapshot = build_bom_snapshot(self._project(), user="test")
        with tempfile.TemporaryDirectory(prefix="cws_bom_test_") as folder:
            outputs = export_bom_package(snapshot, folder, package_name="BOM_Test")
            xlsx = outputs["BOM_Test_BOM.xlsx"]
            package = outputs["BOM_Test_BOM_PACKAGE.zip"]
            self.assertTrue(xlsx.is_file())
            self.assertTrue(package.is_file())
            with zipfile.ZipFile(package) as archive:
                self.assertIn("manifest.json", archive.namelist())
                self.assertIn("SHA256SUMS.txt", archive.namelist())
                self.assertIn("part_bom.csv", archive.namelist())


if __name__ == "__main__":
    unittest.main(verbosity=2)
