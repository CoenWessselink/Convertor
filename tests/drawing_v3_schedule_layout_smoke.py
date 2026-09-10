"""Native vector schedule layout: no dropped IDs, values, rows or columns."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reportlab.pdfbase.pdfmetrics import stringWidth
from cws_convertor.drawings import DrawingBuildRequest, ProductionDrawingEngine, ProductionDrawingRenderer
from tests.production_drawing_engine_smoke import _box_mesh


class DrawingScheduleLayoutTests(unittest.TestCase):
    def request(self, count=1, **kwargs):
        vertices, triangles = _box_mesh()
        dimensions = tuple({"id": f"550e8400-e29b-41d4-a716-{index:012d}", "kind": "linear",
                            "source_field": "volledige bronverwijzing " * 4,
                            "value_mm": 550 + index, "critical": True} for index in range(count))
        bom = tuple({"mark": f"ASSEMBLY-POSITIE-{index:04d}-LANG", "quantity": index + 1,
                     "description": "uitgebreide materiaalomschrijving " * 3} for index in range(count))
        values = dict(entity_id="TABLE-QA", vertices=vertices, triangles=triangles,
                      dimensions=dimensions, bom=bom, views=("front",), sheet_format="A4",
                      include_sections=False, include_details=False, dimension_mode="Productiematen")
        values.update(kwargs)
        return DrawingBuildRequest(**values)

    def assert_columns_and_reconstruction(self, document):
        values = defaultdict(lambda: defaultdict(list))
        for page in document.pages:
            half = page.width_mm * 0.5
            for primitive in page.primitives:
                marker = "schedule:" + primitive.layer
                if primitive.kind != "text" or marker not in primitive.refs:
                    continue
                left, right = (10.0, half - 4.0) if primitive.layer == "dimensions" else (half + 4.0, page.width_mm - 10.0)
                width = right - left
                edges = (left, left + width * .28, left + width * .70, right)
                x, y = primitive.points[0]
                column = min(range(3), key=lambda i: abs(x - edges[i] - 1.0))
                self.assertAlmostEqual(x, edges[column] + 1.0)
                self.assertLessEqual(x + stringWidth(primitive.text, "Helvetica", primitive.font_size), edges[column + 1] - 1.0 + 1e-9)
                self.assertLessEqual(primitive.bounds()[2], edges[column + 1] - 1.0 + 1e-9)
                self.assertLessEqual(y, page.height_mm - 42.0)
                self.assertGreaterEqual(primitive.font_size, 2.1)
                row = next(r[4:] for r in primitive.refs if r.startswith("row:"))
                if primitive.layer == "dimensions":
                    self.assertEqual(primitive.semantic_id, row)
                values[(primitive.layer, row)][column].append((page.number, y, primitive.text))
        reconstructed = {key: tuple("".join(record[2] for record in sorted(columns[i])) for i in range(3)) for key, columns in values.items()}
        for item in document.dimensions:
            self.assertEqual(reconstructed[("dimensions", item["id"])],
                             (item["id"], f'{item["value_mm"]:g} mm', item.get("source_field") or item["kind"]))
        for item in document.bom:
            self.assertEqual(reconstructed[("bom", item["mark"])],
                             (item["mark"], str(item["quantity"]), item["description"]))
        self.assertEqual(document.lint["dimension_coverage_percent"], 100)
        return reconstructed

    def test_uuid_and_full_sources_wrap_without_truncation(self):
        document = ProductionDrawingEngine.build(self.request())
        self.assert_columns_and_reconstruction(document)
        fragments = [p for page in document.pages for p in page.primitives
                     if "schedule:dimensions" in p.refs and abs(p.points[0][0] - 11.0) < 1e-6]
        self.assertGreater(len(fragments), 1)

    def test_wrapped_rows_paginate_without_duplicates_or_missing_rows(self):
        document = ProductionDrawingEngine.build(self.request(count=80))
        rows = self.assert_columns_and_reconstruction(document)
        self.assertEqual(len(rows), len(document.dimensions) + len(document.bom))
        self.assertEqual(len(document.bom), 80)
        self.assertGreater(len(document.pages), 3)

    def test_every_standard_paper_size_and_orientation_keeps_column_bounds(self):
        for size in ("A4", "A3", "A2", "A1", "A0"):
            for orientation in ("landscape", "portrait"):
                with self.subTest(size=size, orientation=orientation):
                    self.assert_columns_and_reconstruction(ProductionDrawingEngine.build(self.request(count=9, sheet_format=size, orientation=orientation)))

    def test_wide_glyphs_are_measured_not_only_character_counted(self):
        value = "WMWMWM1234567890-" * 9
        lines = ProductionDrawingEngine._schedule_lines(value, 18.0, 2.1)
        self.assertEqual("".join(lines), value)
        self.assertTrue(all(stringWidth(line, "Helvetica", 2.1) <= 18.0 for line in lines))

    def test_impossibly_tall_row_is_refused_not_silently_dropped(self):
        request = self.request(bom=({"mark": "LONG", "description": "W" * 10000},))
        with self.assertRaisesRegex(ValueError, "BOM-tabel.*niet leesbaar"):
            ProductionDrawingEngine.build(request)

    def test_real_pdf_retains_exact_embedded_rows(self):
        document = ProductionDrawingEngine.build(self.request(count=5))
        with tempfile.TemporaryDirectory() as tmp:
            path = ProductionDrawingRenderer.render_pdf(document, Path(tmp) / "wrapped.pdf")
            restored = ProductionDrawingRenderer.load_embedded_document(path)
            self.assertEqual(restored.dimensions, document.dimensions)
            self.assertEqual(restored.bom, document.bom)
            self.assert_columns_and_reconstruction(restored)


if __name__ == "__main__":
    unittest.main(verbosity=2)
