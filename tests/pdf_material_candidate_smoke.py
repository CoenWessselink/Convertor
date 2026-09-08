"""Real PDF integration checks; textual analysis does not need a CAD kernel."""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_MODULES = ("pymupdf", "pypdf", "reportlab", "numpy")
MISSING_MODULES = tuple(name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None)


@unittest.skipIf(MISSING_MODULES, "PDF analysis runtime missing: " + ", ".join(MISSING_MODULES))
class ExternalPDFMaterialIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="cws_pdf_material_gate_")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def analyze_lines(self, lines: list[str]):
        import pymupdf
        from pdf_support import analyze_external_pdf

        path = self.root / "external.pdf"
        with pymupdf.open() as document:
            page = document.new_page()
            for index, text in enumerate(lines):
                page.insert_text((20, 40 + index * 25), text)
            document.save(path)
        return analyze_external_pdf(path)

    def test_multifamily_material_text_is_a_review_candidate(self) -> None:
        for material in ("C24", "C30/37", "1.4404", "8.8", "ERTALON6PLA", "EN AW-6082-T6"):
            with self.subTest(material=material):
                result = self.analyze_lines([f"Materiaal: {material}"])
                self.assertEqual(result.part.properties["material_candidate_evidence"]["status"], "candidate")
                self.assertLess(result.part.field_evidence["material"].confidence, 0.95)
                self.assertFalse(result.part.validation.production_export_allowed)
                self.assertTrue(any(question.field_path == "material" for question in result.part.validation.blocking_questions()))

    def test_conflicting_materials_clear_header_and_block(self) -> None:
        result = self.analyze_lines(["Materiaal: S355JR", "Materiaal: S235JR"])
        self.assertEqual(result.part.header.material, "")
        self.assertEqual(result.part.product.material_grade, "")
        self.assertEqual(result.part.properties["material_candidate_evidence"]["status"], "conflict")
        self.assertIn("material", result.details["conflicts"])
        self.assertNotIn("material", result.part.field_evidence)
        self.assertFalse(result.part.validation.production_export_allowed)

    def test_bom_row_no_longer_auto_accepts_material(self) -> None:
        result = self.analyze_lines(["A1 STRIP5*120 S355JR 1000 1 A1"])
        self.assertEqual(result.part.header.material, "S355JR")
        self.assertEqual(result.part.field_evidence["material"].status, "candidate")
        self.assertLess(result.part.field_evidence["material"].confidence, 0.95)
        self.assertFalse(result.part.validation.production_export_allowed)

    def test_unknown_grade_is_not_partially_read_as_known_steel(self) -> None:
        result = self.analyze_lines(["A1 IPE200 S355J2UNKNOWN 1000 1 A1"])
        self.assertEqual(result.part.header.material, "")
        self.assertEqual(result.part.properties["material_candidate_evidence"]["status"], "unresolved")
        self.assertFalse(result.part.validation.production_export_allowed)

    def test_material_correction_resolves_conflict_with_human_audit(self) -> None:
        from pdf_support import apply_review
        result = self.analyze_lines(["Materiaal: S355JR", "Materiaal: S235JR"])
        reviewed = apply_review(result, {"reviewed_by": "engineer", "values": {"header.material": "S355JR"}})
        self.assertEqual(reviewed.part.header.material, "S355JR")
        self.assertEqual(reviewed.part.product.material_grade, "S355JR")
        evidence = reviewed.part.properties["material_candidate_evidence"]
        self.assertEqual(evidence["source_status"], "conflict")
        self.assertEqual(evidence["review_status"], "confirmed")
        self.assertEqual(evidence["human_confirmation"]["reviewer"], "engineer")
        self.assertFalse(any(question.field_path == "material" for question in reviewed.part.validation.blocking_questions()))
        # Confirming a grade does not approve missing geometry or other fields.
        self.assertFalse(reviewed.part.validation.production_export_allowed)

    def test_answering_question_does_not_bypass_explicit_grade_confirmation(self) -> None:
        from pdf_support import apply_review
        result = self.analyze_lines(["Materiaal: S355JR"])
        reviewed = apply_review(result, {
            "reviewed_by": "engineer",
            "answers": {question.question_id: "ok" for question in result.part.validation.unresolved_questions},
        })
        self.assertFalse(reviewed.part.validation.production_export_allowed)
        self.assertTrue(any("expliciete menselijke bevestiging" in error for error in reviewed.errors))

    def test_pdf_model_routes_have_no_implicit_steel_grade(self) -> None:
        import pdf_support
        for name in ("canonical_from_step", "canonical_parts_from_ifc", "step_to_pdf", "ifc_to_pdf", "pdf_to_ifc"):
            with self.subTest(route=name):
                self.assertEqual(inspect.signature(getattr(pdf_support, name)).parameters["material"].default, "")

    def test_canonical_step_payload_material_is_preserved_without_override(self) -> None:
        from canonical_model import CanonicalHeader, CanonicalPart, CanonicalProductData, embed_part_in_step
        from pdf_support import canonical_from_step

        path = self.root / "semantic_payload.step"
        path.write_text("ISO-10303-21;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n", encoding="ascii")
        part = CanonicalPart(
            part_id="PAYLOAD", source_format="STEP",
            header=CanonicalHeader(material="1.4404"),
            product=CanonicalProductData(material_code="1.4404", material_grade="1.4404"),
        )
        embed_part_in_step(path, part)
        restored = canonical_from_step(path, material="S355JR")
        self.assertEqual(restored.header.material, "1.4404")
        self.assertEqual(restored.product.material_grade, "1.4404")


if __name__ == "__main__":
    unittest.main(verbosity=2)
