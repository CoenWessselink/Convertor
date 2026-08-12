from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq
from pypdf import PdfReader, PdfWriter

from ai_support import AISettings, CloudAIConsentError, interpret_drawing
from canonical_model import CanonicalHeader, CanonicalPart, SCHEMA_VERSION
from pdf_support import (
    ExternalPDFExportBlocked,
    TrustedPDFError,
    analyze_external_pdf,
    analyze_pdf,
    apply_review,
    create_trusted_pdf,
    load_trusted_pdf,
    nc1_to_pdf,
    pdf_to_ifc,
    pdf_to_nc1,
    pdf_to_step,
    review_external_pdf,
)
from tests.regression_smoke import write_sample_nc1


HANDOVER_ROOT = Path(
    os.environ.get(
        "CONVERTER_HANDOVER_ROOT",
        "/mnt/data/CONVERTER_WORK/NC1_STEP_IFC_CONVERTER_OVERDRACHT",
    )
)
REAL_P1811 = (
    HANDOVER_ROOT
    / "03_TEST_INPUTS"
    / "ROUNDTRIP_FOCUS"
    / "NC1"
    / "P1811.nc1"
)


from validation.pdf_fixtures import create_synthetic_lo4_pdf

def _strip_attachments_keep_trusted_metadata(source: Path, target: Path) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({str(k): str(v) for k, v in (reader.metadata or {}).items()})
    with target.open("wb") as handle:
        writer.write(handle)


def _corrupt_model_attachment(source: Path, target: Path) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    names = writer.root_object["/Names"].get_object()
    embedded = names["/EmbeddedFiles"].get_object()
    entries = embedded["/Names"]
    changed = False
    for index in range(0, len(entries), 2):
        if str(entries[index]) != "converter-model.json":
            continue
        spec = entries[index + 1].get_object()
        stream = spec["/EF"]["/F"].get_object()
        stream.set_data(b'{"schema_version":"1.1","damaged":true}')
        changed = True
        break
    if not changed:
        raise AssertionError("converter-model.json attachment not found")
    with target.open("wb") as handle:
        writer.write(handle)


class CanonicalSchemaTests(unittest.TestCase):
    def test_v10_payload_remains_readable_and_future_minor_fields_are_ignored(self) -> None:
        data = CanonicalPart(
            part_id="LEGACY",
            source_format="PDF",
            header=CanonicalHeader(position_number="LEGACY", profile="STRIP5*120"),
        ).to_dict()
        data["schema_version"] = "1.0"
        data.pop("product", None)
        data.pop("drawing", None)
        data.pop("field_evidence", None)
        data.pop("validation", None)
        data["future_minor_field"] = {"ignored": True}
        restored = CanonicalPart.from_dict(data)
        self.assertEqual(restored.schema_version, "1.0")
        self.assertEqual(restored.part_id, "LEGACY")
        self.assertEqual(restored.header.profile, "STRIP5*120")
        self.assertEqual(restored.drawing.sheet_format, "A4")

    def test_geometry_hash_changes_only_when_production_geometry_changes(self) -> None:
        part = CanonicalPart(part_id="HASH", header=CanonicalHeader(profile="B", length=100.0))
        first = part.geometry_sha256()
        part.product.project_name = "Metadata only"
        self.assertEqual(first, part.geometry_sha256())
        part.header.length = 101.0
        self.assertNotEqual(first, part.geometry_sha256())
        self.assertEqual(SCHEMA_VERSION, "1.1")


class TrustedPDFTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="converter_pdf_ai_test_")
        self.folder = Path(self.temp.name)
        self.sample_nc1 = self.folder / "SAMPLE_PLATE.nc1"
        write_sample_nc1(self.sample_nc1)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_nc1_to_trusted_pdf_to_nc1_restores_exact_source_bytes(self) -> None:
        trusted = self.folder / "sample_trusted.pdf"
        nc1_to_pdf(self.sample_nc1, trusted)
        analysis = load_trusted_pdf(trusted)
        self.assertEqual(analysis.mode, "trusted_exact")
        self.assertTrue(analysis.production_export_allowed)
        restored = self.folder / "restored.nc1"
        pdf_to_nc1(trusted, restored)
        self.assertEqual(self.sample_nc1.read_bytes(), restored.read_bytes())

    @unittest.skipUnless(REAL_P1811.is_file(), "P1811 handover fixture is not available")
    def test_real_p1811_trusted_roundtrip_is_exact(self) -> None:
        trusted = self.folder / "P1811.pdf"
        restored = self.folder / "P1811_back.nc1"
        nc1_to_pdf(REAL_P1811, trusted)
        pdf_to_nc1(trusted, restored)
        self.assertEqual(REAL_P1811.read_bytes(), restored.read_bytes())
        analysis = load_trusted_pdf(trusted)
        self.assertEqual(len(analysis.part.holes), 4)

    def test_visible_tamper_is_rejected_and_not_downgraded_to_external_pdf(self) -> None:
        trusted = self.folder / "sample_trusted.pdf"
        nc1_to_pdf(self.sample_nc1, trusted)
        reader = PdfReader(str(trusted))
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        writer.add_blank_page(width=100, height=100)
        tampered = self.folder / "tampered_visible.pdf"
        with tampered.open("wb") as handle:
            writer.write(handle)
        with self.assertRaises(TrustedPDFError):
            analyze_pdf(tampered)

    def test_partial_trusted_pdf_with_stripped_attachments_is_rejected(self) -> None:
        trusted = self.folder / "sample_trusted.pdf"
        nc1_to_pdf(self.sample_nc1, trusted)
        stripped = self.folder / "stripped.pdf"
        _strip_attachments_keep_trusted_metadata(trusted, stripped)
        with self.assertRaises(TrustedPDFError):
            analyze_pdf(stripped)

    def test_corrupted_model_attachment_is_rejected(self) -> None:
        trusted = self.folder / "sample_trusted.pdf"
        nc1_to_pdf(self.sample_nc1, trusted)
        corrupt = self.folder / "corrupt_model.pdf"
        _corrupt_model_attachment(trusted, corrupt)
        with self.assertRaises(TrustedPDFError):
            analyze_pdf(corrupt)


class ExternalPDFAndAITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="converter_external_pdf_test_")
        self.folder = Path(self.temp.name)
        self.fixture = create_synthetic_lo4_pdf(self.folder / "LO4_external_vector_synthetic.pdf")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_synthetic_lo4_vector_fields_geometry_and_review_gate(self) -> None:
        analysis = analyze_external_pdf(self.fixture)
        self.assertEqual(analysis.mode, "external_vector")
        self.assertEqual(analysis.detected_fields["position"], "LO4")
        self.assertEqual(analysis.detected_fields["profile"], "STRIP5*120")
        self.assertEqual(analysis.detected_fields["material"], "S235JR")
        self.assertEqual(analysis.detected_fields["length"], 160.0)
        self.assertEqual(analysis.detected_fields["quantity"], 4)
        self.assertEqual(analysis.detected_fields["mark"], "MLO4")
        self.assertEqual(analysis.detected_fields["total_quantity"], 4)
        self.assertEqual(analysis.detected_fields["scale"], "1:2")
        self.assertEqual(analysis.part.drawing.sheet_format, "A4")
        self.assertEqual(analysis.part.product.name, "LOSSE PLAAT")
        self.assertEqual(len(analysis.part.contours), 1)
        self.assertEqual(len(analysis.part.contours[0].points), 4)
        radii = sorted(point.radius for point in analysis.part.contours[0].points if point.radius > 0)
        self.assertEqual(len(radii), 2)
        for value in radii:
            self.assertAlmostEqual(value, 13.5, delta=0.15)
        self.assertEqual(len(analysis.part.holes), 1)
        hole = analysis.part.holes[0]
        self.assertAlmostEqual(hole.x, 20.0, delta=0.15)
        self.assertAlmostEqual(hole.q, 20.0, delta=0.15)
        self.assertAlmostEqual(hole.diameter, 14.0, delta=0.15)
        self.assertFalse(analysis.production_export_allowed)
        self.assertTrue(any(question.field_path == "holes[0]" for question in analysis.part.validation.blocking_questions()))
        with self.assertRaises(ExternalPDFExportBlocked):
            pdf_to_nc1(self.fixture, self.folder / "blocked.nc1")

    def test_explicit_review_unlocks_nc1_step_ifc_and_trusted_pdf_roundtrip(self) -> None:
        analysis = analyze_external_pdf(self.fixture)
        reviewed = apply_review(
            analysis,
            {
                "reviewed_by": "unittest",
                "confirm": ["holes[0]"],
                "comment": "Synthetic vector geometry visually checked",
            },
        )
        self.assertTrue(reviewed.production_export_allowed)
        review_path = self.folder / "review.json"
        review_path.write_text(
            json.dumps(
                {
                    "reviewed_by": "unittest",
                    "confirm": ["holes[0]"],
                    "comment": "Synthetic vector geometry visually checked",
                }
            ),
            encoding="utf-8",
        )
        trusted = self.folder / "LO4_reviewed_trusted.pdf"
        review_external_pdf(self.fixture, review_path, trusted)
        trusted_analysis = load_trusted_pdf(trusted)
        self.assertTrue(trusted_analysis.production_export_allowed)
        self.assertEqual(trusted_analysis.part.header.position_number, "LO4")

        nc1 = self.folder / "LO4.nc1"
        step = self.folder / "LO4.step"
        ifc = self.folder / "LO4.ifc"
        pdf_to_nc1(trusted, nc1)
        pdf_to_step(trusted, step)
        pdf_to_ifc(trusted, ifc)
        self.assertGreater(nc1.stat().st_size, 0)
        self.assertGreater(step.stat().st_size, 0)
        self.assertGreater(ifc.stat().st_size, 0)
        self.assertGreater(cq.importers.importStep(str(step)).val().Volume(), 0)
        ifc_text = ifc.read_text(encoding="utf-8")
        self.assertIn("IFCPLATE", ifc_text)
        self.assertIn("IFCEXTRUDEDAREASOLID", ifc_text)
        self.assertIn("IFCARBITRARYPROFILEDEFWITHVOIDS", ifc_text)
        self.assertIn("IFCCIRCLE", ifc_text)
        self.assertIn("IFCINDEXEDPOLYCURVE", ifc_text)
        self.assertIn("IFCTRIANGULATEDFACESET", ifc_text)
        self.assertIn("Qto_PlateBaseQuantities", ifc_text)

    def test_local_rules_ai_only_adds_questions(self) -> None:
        result = interpret_drawing(
            self.fixture,
            deterministic_context={
                "missing_critical": ["reference_side", "plate_thickness"],
                "conflicts": ["material"],
            },
            settings=AISettings(provider="local-rules"),
        )
        self.assertEqual(result.provider, "local-rules")
        self.assertEqual(result.fields, [])
        self.assertEqual(len(result.questions), 3)

    def test_openai_provider_requires_explicit_cloud_consent_before_api_key(self) -> None:
        with self.assertRaises(CloudAIConsentError):
            interpret_drawing(
                self.fixture,
                deterministic_context={},
                settings=AISettings(provider="openai", allow_cloud=False),
            )

    def test_cli_has_no_unsafe_validation_bypass(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "cli.py"), "step-to-nc1", "--help"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.assertNotIn("no-strict-validation", completed.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
