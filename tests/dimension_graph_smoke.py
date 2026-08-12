from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dimension_graph import (
    build_dimension_graph,
    populate_dimension_graph,
    validate_dimension_graph,
)
from pdf_support import (
    analyze_external_pdf,
    apply_review,
    canonical_from_nc1,
    create_trusted_pdf,
    load_trusted_pdf,
)
from tests.regression_smoke import write_sample_nc1
from validation.pdf_fixtures import create_synthetic_lo4_pdf


class DimensionGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="converter_dimension_graph_")
        self.folder = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_nc1_graph_covers_overall_plate_and_every_hole(self) -> None:
        source = self.folder / "sample.nc1"
        write_sample_nc1(source)
        part = canonical_from_nc1(source)
        report = validate_dimension_graph(part)
        self.assertTrue(report.valid, report.errors)
        self.assertEqual(report.coverage_percent, 100.0)
        ids = {item["id"] for item in part.drawing.dimensions}
        self.assertTrue({"overall-x", "overall-y", "plate-thickness"}.issubset(ids))
        for index in range(1, len(part.holes) + 1):
            self.assertIn(f"hole-{index:03d}-diameter", ids)
            self.assertIn(f"hole-{index:03d}-x", ids)
            self.assertIn(f"hole-{index:03d}-y", ids)
        self.assertTrue(part.drawing.dimension_chains)

    def test_tampered_dimension_value_is_rejected(self) -> None:
        source = self.folder / "sample.nc1"
        write_sample_nc1(source)
        part = canonical_from_nc1(source)
        tampered = [dict(item) for item in part.drawing.dimensions]
        target = next(item for item in tampered if item["id"] == "overall-x")
        target["value_mm"] = float(target["value_mm"]) + 5.0
        report = validate_dimension_graph(part, tampered, part.drawing.dimension_chains)
        self.assertFalse(report.valid)
        self.assertTrue(any("overall-x" in error and "canonieke model" in error for error in report.errors))

    def test_external_lo4_graph_is_feature_linked_before_and_after_review(self) -> None:
        source = create_synthetic_lo4_pdf(self.folder / "LO4_external.pdf")
        analysis = analyze_external_pdf(source)
        report = validate_dimension_graph(analysis.part)
        self.assertTrue(report.valid, report.errors)
        self.assertFalse(analysis.production_export_allowed)
        ids = {item["id"] for item in analysis.part.drawing.dimensions}
        self.assertIn("hole-001-x", ids)
        self.assertIn("hole-001-y", ids)
        self.assertIn("hole-001-diameter", ids)
        radii = sorted(
            item["value_mm"]
            for item in analysis.part.drawing.dimensions
            if item["kind"] == "radius"
        )
        self.assertEqual(len(radii), 2)
        for radius in radii:
            self.assertAlmostEqual(radius, 13.5, delta=0.001)
        reviewed = apply_review(
            analysis,
            {
                "reviewed_by": "dimension-unittest",
                "confirm": ["holes[0]"],
                "comment": "Feature-linked dimensions checked",
            },
        )
        self.assertTrue(reviewed.production_export_allowed)
        reviewed_report = validate_dimension_graph(reviewed.part)
        self.assertTrue(reviewed_report.valid, reviewed_report.errors)
        self.assertEqual(reviewed_report.coverage_percent, 100.0)

    def test_trusted_pdf_embeds_dimension_graph(self) -> None:
        source = self.folder / "sample.nc1"
        write_sample_nc1(source)
        part = canonical_from_nc1(source)
        target = self.folder / "sample.pdf"
        create_trusted_pdf(part, target)
        restored = load_trusted_pdf(target).part
        self.assertTrue(restored.drawing.dimensions)
        self.assertTrue(restored.drawing.dimension_chains)
        self.assertEqual(restored.properties["dimension_graph"]["version"], "1.0")
        self.assertTrue(restored.properties["dimension_graph"]["validation"]["valid"])

    def test_build_is_deterministic(self) -> None:
        source = self.folder / "sample.nc1"
        write_sample_nc1(source)
        part = canonical_from_nc1(source)
        first = json.dumps(build_dimension_graph(part), sort_keys=True, separators=(",", ":"))
        populate_dimension_graph(part, overwrite=True)
        second = json.dumps(build_dimension_graph(part), sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
