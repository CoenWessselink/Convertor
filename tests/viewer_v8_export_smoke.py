from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from types import SimpleNamespace
import csv
import hashlib
import tempfile
import unittest
import zipfile

from cws_viewer.properties import GridQuery, ProjectGridModel, export_grid_csv, export_grid_xlsx, formula_safe


def _part(entity_id: str, name: str):
    return SimpleNamespace(
        internal_id=entity_id,
        status="validated",
        category="make_part",
        part_position=entity_id,
        assembly_ids=[],
        name=name,
        profile="HEA140",
        normalized_profile="HEA140",
        material="S355JR",
        normalized_material="S355JR",
        length_mm=1000.0,
        quantity_total=2,
        mass_each_kg=10.0,
        surface_area_each_m2=1.0,
        classification_status="confirmed",
        export_status="ready",
        nc1_eligible=True,
        validation_issues=(),
        source_identity=SimpleNamespace(source_entity_id="1", source_format="ifc", assembly_mark="M1", part_position=entity_id),
        confidence=1.0,
        geometry_hash="a" * 64,
        manufacturing_hash="b" * 64,
    )


class ViewerV8ExportTests(unittest.TestCase):
    def test_formula_safe_csv_and_xlsx(self) -> None:
        project = SimpleNamespace(
            project_phase="",
            parts={
                "P1": _part("P1", '=HYPERLINK("https://example.invalid")'),
                "P2": _part("P2", "+1+1"),
                "P3": _part("P3", "@malicious"),
            },
            assemblies={}, purchased_items={}, fasteners={}, welds={},
        )
        model = ProjectGridModel(project)
        result = model.execute(GridQuery())
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "grid.csv"
            xlsx_path = Path(directory) / "grid.xlsx"
            csv_result = export_grid_csv(result, csv_path)
            xlsx_result = export_grid_xlsx(result, xlsx_path)
            self.assertEqual(3, csv_result["rows"])
            self.assertEqual(3, xlsx_result["rows"])
            self.assertEqual(hashlib.sha256(csv_path.read_bytes()).hexdigest(), csv_result["sha256"])
            self.assertEqual(hashlib.sha256(xlsx_path.read_bytes()).hexdigest(), xlsx_result["sha256"])
            with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter=";"))
            self.assertTrue(rows[0]["Naam"].startswith("'="))
            self.assertTrue(rows[1]["Naam"].startswith("'+"))
            self.assertTrue(rows[2]["Naam"].startswith("'@"))
            with zipfile.ZipFile(xlsx_path) as archive:
                self.assertIsNone(archive.testzip())
                sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
                # User values must not be emitted as Excel cell formulas.
                self.assertNotIn("<f>HYPERLINK", sheet_xml)
                combined = "".join(
                    archive.read(name).decode("utf-8", errors="ignore")
                    for name in archive.namelist()
                    if name.endswith(".xml")
                )
                self.assertIn("HYPERLINK", combined)
                self.assertIn("'=HYPERLINK", combined)

    def test_formula_safe_keeps_numbers_numeric(self) -> None:
        self.assertEqual(12.5, formula_safe(12.5))
        self.assertEqual("'=1+1", formula_safe("=1+1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
