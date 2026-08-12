from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pdf_support import (
    analyze_external_pdf,
    apply_review,
    finalize_reviewed_analysis,
    load_trusted_pdf,
)
from review_workflow import build_review_payload, collect_review_fields
from validation.pdf_fixtures import create_synthetic_lo4_pdf


class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="converter_review_workflow_")
        self.folder = Path(self.temp.name)
        self.source = create_synthetic_lo4_pdf(self.folder / "LO4_external.pdf")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_review_rows_map_detector_aliases_to_canonical_fields(self) -> None:
        analysis = analyze_external_pdf(self.source)
        fields = collect_review_fields(analysis.part)
        by_path = {item.path: item for item in fields}
        self.assertEqual(by_path["header.position_number"].current_value, "LO4")
        self.assertEqual(by_path["header.position_number"].evidence_path, "position")
        self.assertEqual(by_path["header.profile"].current_value, "STRIP5*120")
        self.assertEqual(by_path["header.dim2"].current_value, 5.0)
        self.assertTrue(by_path["holes[0]"].confirmable)
        self.assertTrue(by_path["holes[0].diameter"].editable)
        self.assertTrue(any(item.path.endswith(".radius") for item in fields))

    def test_review_payload_is_explicit_and_unlocks_only_after_validation(self) -> None:
        analysis = analyze_external_pdf(self.source)
        payload = build_review_payload(
            analysis.part,
            reviewed_by="Review Tester",
            confirm=["holes[0]"],
            comment="Visueel gecontroleerd in interactieve review",
        )
        reviewed = apply_review(analysis, payload)
        self.assertTrue(reviewed.production_export_allowed)
        self.assertEqual(reviewed.part.properties["review"]["reviewed_by"], "Review Tester")
        self.assertEqual(reviewed.part.field_evidence["holes[0]"].status, "confirmed")

    def test_comma_decimal_correction_resolves_written_diameter_conflict(self) -> None:
        source = create_synthetic_lo4_pdf(
            self.folder / "LO4_conflict.pdf",
            hole_callout_diameter_mm=18.0,
            hole_geometry_diameter_mm=14.0,
        )
        analysis = analyze_external_pdf(source)
        diameter_questions = [
            item
            for item in analysis.part.validation.unresolved_questions
            if item.field_path == "holes[0].diameter"
        ]
        conflict = next(item for item in diameter_questions if item.question_id.startswith("pdf-conflict-"))
        reference = next(
            item
            for item in analysis.part.validation.unresolved_questions
            if item.field_path == "reference_side"
        )
        answers = {item.question_id: "18,0" for item in diameter_questions}
        answers[reference.question_id] = "v: lower-left of primary plate view"
        payload = build_review_payload(
            analysis.part,
            reviewed_by="Review Tester",
            values={"holes[0].diameter": "18,0"},
            confirm=["holes[0]"],
            answers=answers,
        )
        reviewed = apply_review(analysis, payload)
        self.assertTrue(reviewed.production_export_allowed)
        self.assertAlmostEqual(reviewed.part.holes[0].diameter, 18.0)
        self.assertTrue(
            any(
                item.question_id == conflict.question_id and item.status == "answered"
                for item in reviewed.part.validation.unresolved_questions
            )
        )

    def test_unknown_confirmation_is_rejected(self) -> None:
        analysis = analyze_external_pdf(self.source)
        with self.assertRaises(ValueError):
            build_review_payload(
                analysis.part,
                reviewed_by="Review Tester",
                confirm=["holes[999]"],
            )

    def test_validated_in_memory_review_can_be_finalized_without_reanalysis(self) -> None:
        analysis = analyze_external_pdf(self.source)
        reviewed = apply_review(
            analysis,
            build_review_payload(
                analysis.part,
                reviewed_by="Review Tester",
                confirm=["holes[0]"],
            ),
        )
        target = self.folder / "LO4_reviewed_trusted.pdf"
        result = finalize_reviewed_analysis(reviewed, target)
        self.assertEqual(result.primary_output, target)
        trusted = load_trusted_pdf(target)
        self.assertTrue(trusted.production_export_allowed)
        self.assertEqual(trusted.part.header.position_number, "LO4")
        self.assertEqual(trusted.part.properties["review"]["reviewed_by"], "Review Tester")


if __name__ == "__main__":
    unittest.main(verbosity=2)
