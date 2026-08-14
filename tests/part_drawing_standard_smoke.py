from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import fitz
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical_model import CanonicalHole
from pdf_support import canonical_from_nc1, create_trusted_pdf
from tests.regression_smoke import write_sample_nc1


class PartDrawingStandardTests(unittest.TestCase):
    def test_tasche_sheet_dimensions_every_hole_with_fixed_axis_rules(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-part-drawing-") as folder:
            root = Path(folder)
            source = root / "sample.nc1"
            target = root / "sample.pdf"
            write_sample_nc1(source)
            part = canonical_from_nc1(source)
            part.product.project_name = "Warehouse extension"
            part.product.project_number = "WE-2024-118"
            part.product.client = "Tasche Staalbouw"
            part.header.position_number = "B-102"
            part.header.profile = "HEA300"
            part.header.profile_type = "I"
            part.header.dim1 = 300.0
            part.header.dim2 = 300.0
            part.header.dim3 = 16.0
            part.header.dim4 = 10.0
            part.drawing.title_block["subject"] = "BEAM HEA300 - 6250"
            part.holes = [
                CanonicalHole(face="v", x=40.0, q=45.0, diameter=22.0),
                CanonicalHole(face="v", x=100.0, q=45.0, diameter=22.0),
                CanonicalHole(face="v", x=180.0, q=45.0, diameter=22.0),
                CanonicalHole(face="v", x=180.0, q=155.0, diameter=22.0),
            ]
            create_trusted_pdf(part, target)

            document = fitz.open(target)
            try:
                self.assertEqual(1, document.page_count)
                page = document[0]
                text = page.get_text()
                images = page.get_images(full=True)
                self.assertAlmostEqual(420.0, page.rect.width * 25.4 / 72.0, delta=0.2)
                self.assertAlmostEqual(297.0, page.rect.height * 25.4 / 72.0, delta=0.2)
            finally:
                document.close()

            for required_text in (
                "ELEVATION / MAIN VIEW",
                "BEAM HEA300 - 6250",
                "PLAN - TOP FLANGE",
                "PLAN - BOTTOM FLANGE",
                "DETAIL - HOLE H1",
                "SECTION A-A",
                "3D VIEW - REVIEW",
                "MATERIAL / PROFILE",
                "BILL OF MATERIALS",
                "HOLES",
                "CUTS",
                "GENERAL NOTES",
                "X INCR.",
                "X ABS.",
                "Y ABS.",
                "4x",
                "H1",
                "H2",
                "H3",
                "H4",
            ):
                self.assertIn(required_text, text)
            self.assertGreaterEqual(len(images), 1, "Tasche-logo ontbreekt als afbeeldingsresource")

            metadata = PdfReader(target).metadata
            self.assertEqual("Tasche Staalbouw", metadata.author)
            keywords = str(metadata.get("/Keywords", ""))
            self.assertIn("CWS-DIM-X=INCREMENTAL+ABSOLUTE", keywords)
            self.assertIn("CWS-DIM-Y=ABSOLUTE", keywords)
            self.assertIn("CWS-HOLES=ALL-DIMENSIONED", keywords)


if __name__ == "__main__":
    unittest.main(verbosity=2)
