"""CAD-runtime evidence for material-safe bare STEP -> PDF canonical import."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@unittest.skipUnless(importlib.util.find_spec("cadquery"), "CadQuery native runtime missing")
class NativePDFModelMaterialGateTests(unittest.TestCase):
    def setUp(self) -> None:
        import cadquery as cq
        self.temp = tempfile.TemporaryDirectory(prefix="cws_native_pdf_material_")
        self.root = Path(self.temp.name)
        self.source = self.root / "bare_plate.step"
        cq.exporters.export(cq.Workplane("XY").box(1000, 120, 10), str(self.source))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_bare_step_without_material_is_concept_not_default_steel(self) -> None:
        from pdf_support import canonical_from_step
        part = canonical_from_step(self.source)
        self.assertEqual(part.header.material, "")
        self.assertEqual(part.product.material_grade, "")
        self.assertFalse(part.validation.production_export_allowed)
        self.assertEqual(part.properties["material_resolution"]["status"], "unresolved")
        self.assertTrue(any(question.field_path == "header.material" for question in part.validation.blocking_questions()))

    def test_explicit_catalog_material_is_preserved_with_provenance(self) -> None:
        from pdf_support import canonical_from_step
        part = canonical_from_step(self.source, material="S355JR")
        self.assertEqual(part.header.material, "S355JR")
        self.assertEqual(part.properties["material_resolution"]["material_code"], "S355JR")
        self.assertEqual(part.properties["material_resolution"]["provenance"]["source_kind"], "explicit_conversion_argument")


if __name__ == "__main__":
    unittest.main(verbosity=2)
