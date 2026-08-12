from __future__ import annotations

from pathlib import Path
import json
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq
from pypdf import PdfReader, PdfWriter

from ai_support import (
    AISettings,
    CloudAIConsentError,
    interpret_drawing,
    validate_ai_payload,
)
from canonical_model import extract_part_from_ifc
from pdf_support import (
    ExternalPDFExportBlocked,
    TrustedPDFError,
    analyze_external_pdf,
    analyze_pdf,
    load_trusted_pdf,
    nc1_to_pdf,
    pdf_to_ifc,
    pdf_to_nc1,
    pdf_to_step,
    step_to_pdf,
    visible_pdf_sha256,
)
from validation.pdf_fixtures import create_synthetic_lo4_pdf

NC1_SOURCE = ROOT / "validation" / "v0.2_generated_nc1" / "P1811_3_PLAAT_PL10_130.nc1"
STEP_SOURCE = ROOT / "validation" / "v0.2_generated_step" / "Pr1527.step"


def _semantic_nc1(path: Path) -> dict:
    import converter as core

    part = core.parse_nc1(path)
    return {
        "part": part.header.part_number,
        "position": part.header.position_number,
        "profile": part.header.profile,
        "profile_type": part.header.profile_type,
        "material": part.header.material,
        "quantity": part.header.quantity,
        "length": part.header.length,
        "holes": sorted(
            (hole.face, round(hole.x, 4), round(hole.q, 4), round(hole.diameter, 4))
            for hole in part.holes
        ),
        "contours": [
            (
                contour.kind,
                contour.face,
                [
                    (round(point.x, 4), round(point.q, 4), round(point.radius, 4))
                    for point in contour.geometry_points
                ],
            )
            for contour in part.contours
        ],
    }


def _fake_openai_transport(request, timeout):
    assert timeout > 0
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["store"] is False
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    content = payload["input"][0]["content"]
    assert any(item["type"] == "input_image" for item in content)
    answer = {
        "document_type": "single_part_drawing",
        "language": "nl",
        "fields": [
            {
                "name": "subject",
                "value": "LOSSE PLAAT",
                "confidence": 0.99,
                "page": 1,
                "evidence": "titelblok",
            },
            {
                "name": "profile",
                "value": "STRIP5*120",
                "confidence": 0.98,
                "page": 1,
                "evidence": "stukregel",
            },
        ],
        "views": [
            {
                "page": 1,
                "view_type": "front",
                "confidence": 0.91,
                "evidence": "hoofdaanzicht",
            }
        ],
        "conflicts": [],
        "questions": [
            {
                "field": "reference_side",
                "question": "Bevestig de productiereferentiezijde.",
                "options": [],
                "blocking": True,
            }
        ],
        "layout_suggestions": ["Plaats het hoofdaanzicht links van het titelblok."],
    }
    response = {
        "id": "resp_test_123",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(answer)}],
            }
        ],
    }
    return 200, json.dumps(response).encode("utf-8"), {"x-request-id": "req_test_123"}


def _tamper_visible_pdf(source: Path, target: Path) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.add_blank_page(width=100, height=100)
    with target.open("wb") as handle:
        writer.write(handle)


def main() -> None:
    assert NC1_SOURCE.exists(), NC1_SOURCE
    assert STEP_SOURCE.exists(), STEP_SOURCE
    with tempfile.TemporaryDirectory(prefix="pdf_ai_smoke_") as folder:
        out = Path(folder)

        # NC1 -> Trusted PDF -> NC1 / STEP / IFC.
        trusted = out / "P1811_trusted.pdf"
        result = nc1_to_pdf(NC1_SOURCE, trusted)
        inspection = load_trusted_pdf(trusted, strict=True)
        assert inspection.mode == "trusted_exact"
        assert inspection.production_export_allowed
        assert visible_pdf_sha256(trusted) == result.details["manifest"]["visible_sha256"]
        attachments = set(PdfReader(str(trusted)).attachments)
        assert "converter-model.json" in attachments
        assert "converter-manifest.json" in attachments

        reverse_nc1 = out / "P1811_reverse.nc1"
        pdf_to_nc1(trusted, reverse_nc1)
        assert _semantic_nc1(NC1_SOURCE) == _semantic_nc1(reverse_nc1)

        reverse_step = out / "P1811_reverse.step"
        pdf_to_step(trusted, reverse_step)
        assert cq.importers.importStep(str(reverse_step)).val().isValid()

        reverse_ifc = out / "P1811_reverse.ifc"
        pdf_to_ifc(trusted, reverse_ifc)
        assert reverse_ifc.exists() and reverse_ifc.stat().st_size > 1000
        payload = extract_part_from_ifc(reverse_ifc, strict=True)
        assert payload is not None and payload.schema_version == "1.1"

        # STEP -> Trusted PDF -> exact STEP attachment.
        step_pdf = out / "D20_trusted.pdf"
        step_to_pdf(STEP_SOURCE, step_pdf)
        assert load_trusted_pdf(step_pdf, strict=True).mode == "trusted_exact"
        step_roundtrip = out / "D20_roundtrip.step"
        pdf_to_step(step_pdf, step_roundtrip)
        original_shape = cq.importers.importStep(str(STEP_SOURCE)).val()
        returned_shape = cq.importers.importStep(str(step_roundtrip)).val()
        volume_delta = (
            (returned_shape.Volume() - original_shape.Volume())
            / original_shape.Volume()
            * 100.0
        )
        assert abs(volume_delta) < 1e-9

        # Visible tampering must invalidate Trusted status and may not fall back.
        tampered = out / "tampered.pdf"
        _tamper_visible_pdf(trusted, tampered)
        try:
            analyze_pdf(tampered)
        except TrustedPDFError:
            pass
        else:
            raise AssertionError("Zichtbaar gewijzigde Trusted PDF had geweigerd moeten zijn")

        # External LO4-like vector drawing: metadata/geometry recognised but review required.
        external = create_synthetic_lo4_pdf(out / "LO4_external_vector.pdf")
        analysis = analyze_external_pdf(external)
        values = analysis.detected_fields
        expected = {
            "position": "LO4",
            "profile": "STRIP5*120",
            "material": "S235JR",
            "length": 160.0,
            "quantity": 4,
            "mark": "MLO4",
            "total_quantity": 4,
            "scale": "1:2",
        }
        for key, value in expected.items():
            assert values[key] == value, (key, values.get(key), value)
        assert analysis.part.drawing.sheet_format == "A4"
        assert analysis.part.product.name == "LOSSE PLAAT"
        assert len(analysis.part.contours) == 1
        assert len(analysis.part.holes) == 1
        assert not analysis.production_export_allowed
        try:
            pdf_to_step(external, out / "external.step")
        except ExternalPDFExportBlocked:
            pass
        else:
            raise AssertionError("Externe PDF zonder review had geblokkeerd moeten zijn")

        # Optional cloud AI requires consent and uses structured semantic-only output.
        no_consent = AISettings(
            provider="openai",
            model="test-vision-model",
            allow_cloud=False,
            api_key="test-key",
            transport=_fake_openai_transport,
        )
        try:
            interpret_drawing(external, deterministic_context={}, settings=no_consent)
        except CloudAIConsentError:
            pass
        else:
            raise AssertionError("Cloud-AI zonder expliciete toestemming had geblokkeerd moeten zijn")

        cloud_settings = AISettings(
            provider="openai",
            model="test-vision-model",
            allow_cloud=True,
            api_key="test-key",
            transport=_fake_openai_transport,
        )
        cloud = interpret_drawing(
            external,
            deterministic_context={
                "page_count": 1,
                "page_classification": ["vector"],
                "sheet_format": "A4",
                "orientation": "landscape",
                "detected_fields": values,
                "missing_critical": ["reference_side"],
                "conflicts": [],
                "vector_path_count": 3,
                "image_count": 0,
            },
            settings=cloud_settings,
        )
        assert cloud.provider == "openai-responses"
        assert cloud.audit["store"] is False
        assert cloud.request_id == "resp_test_123"

        # AI may not smuggle production geometry through arbitrary keys.
        try:
            validate_ai_payload(
                {
                    "document_type": "drawing",
                    "language": "nl",
                    "fields": [],
                    "views": [],
                    "conflicts": [],
                    "questions": [],
                    "layout_suggestions": [],
                    "contour_coordinates": [[0, 0], [1, 0]],
                }
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Verboden AI-geometrie had afgewezen moeten zijn")

        report = {
            "trusted_pdf": str(trusted),
            "trusted_exact": inspection.mode == "trusted_exact",
            "visible_hash": result.details["manifest"]["visible_sha256"],
            "nc1_semantic_roundtrip": True,
            "step_volume_delta_percent": volume_delta,
            "ifc_payload_schema": payload.schema_version,
            "tamper_blocked": True,
            "external_lo4_fields": values,
            "external_vector_geometry_detected": True,
            "external_production_blocked_pending_review": True,
            "cloud_ai_consent_required": True,
            "cloud_ai_store": False,
            "ai_geometry_guard": True,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
