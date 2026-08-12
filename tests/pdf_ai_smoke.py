from __future__ import annotations

from pathlib import Path
import json
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq
import fitz

from ai_support import OpenAIResponsesProvider, validate_ai_payload
from drawing_templates import MM_TO_PT
from pdf_support import (
    PDFProductionBlockedError,
    analyze_external_pdf,
    inspect_pdf,
    nc1_to_pdf,
    pdf_to_ifc,
    pdf_to_nc1,
    pdf_to_step,
    step_to_pdf,
    visible_pdf_sha256,
)

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
        "holes": sorted((hole.face, round(hole.x, 4), round(hole.q, 4), round(hole.diameter, 4)) for hole in part.holes),
        "contours": [
            (contour.kind, contour.face, [(round(point.x, 4), round(point.q, 4)) for point in contour.geometry_points])
            for contour in part.contours
        ],
    }


def _make_external_lo4(path: Path) -> None:
    document = fitz.open()
    page = document.new_page(width=297 * MM_TO_PT, height=210 * MM_TO_PT)
    page.draw_rect(fitz.Rect(25, 25, 817, 570), color=(0, 0, 0), width=0.8)
    page.draw_rect(fitz.Rect(120, 90, 440, 330), color=(0, 0, 0), width=1.0)
    page.draw_circle(fitz.Point(200, 190), 14, color=(0, 0, 0), width=1.0)
    page.insert_text(fitz.Point(55, 430), "Pos Profiel Materiaal Lengte Aantal Merk", fontsize=10)
    page.insert_text(fitz.Point(55, 448), "LO4 STRIP5*120 S235JR 160 4 MLO4", fontsize=10)
    page.insert_text(fitz.Point(55, 466), "Totaal aantal keer uit te voeren: 4", fontsize=10)
    page.insert_text(fitz.Point(55, 485), "LOSSE PLAAT", fontsize=12)
    page.insert_text(fitz.Point(55, 505), "Schaal: 1:2   Formaat: A4", fontsize=10)
    page.insert_text(fitz.Point(480, 150), "1*Ø14", fontsize=10)
    page.insert_text(fitz.Point(480, 175), "R 13,5", fontsize=10)
    page.insert_text(fitz.Point(480, 195), "R 13,5", fontsize=10)
    document.save(path)
    document.close()


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
            {"name": "subject", "value": "LOSSE PLAAT", "confidence": 0.99, "page": 1, "evidence": "titelblok"},
            {"name": "profile", "value": "STRIP5*120", "confidence": 0.98, "page": 1, "evidence": "stukregel"},
        ],
        "views": [{"page": 1, "view_type": "front", "confidence": 0.91, "evidence": "hoofdaanzicht"}],
        "conflicts": [],
        "questions": [
            {"field": "geometry", "question": "Bevestig de productiereferentiezijde.", "options": [], "blocking": True}
        ],
        "layout_suggestions": ["Plaats het hoofdaanzicht links van het titelblok."],
    }
    response = {
        "id": "resp_test_123",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(answer)}]}],
    }
    return 200, json.dumps(response).encode("utf-8"), {"x-request-id": "req_test_123"}


def main() -> None:
    assert NC1_SOURCE.exists(), NC1_SOURCE
    assert STEP_SOURCE.exists(), STEP_SOURCE
    with tempfile.TemporaryDirectory(prefix="pdf_ai_smoke_") as folder:
        out = Path(folder)

        # NC1 -> Trusted PDF -> NC1 / STEP / IFC.
        trusted = out / "P1811_trusted.pdf"
        result = nc1_to_pdf(NC1_SOURCE, trusted)
        inspection = inspect_pdf(trusted, strict=True)
        assert inspection.trusted_exact
        assert inspection.classification == "trusted_exact"
        assert visible_pdf_sha256(trusted) == result.details["visible_drawing_sha256"]
        with fitz.open(trusted) as document:
            embedded_names = document.embfile_names()
            assert "converter-model.json" in embedded_names
            assert any(name.startswith("source-") for name in embedded_names)
            assert document[0].get_drawings(), "Werktekening moet vectorpaden bevatten"
            text = document[0].get_text("text")
            for label in ("Pos", "Profiel", "Materiaal", "Lengte", "Aantal", "Merk"):
                assert label in text
            assert "130" in text and "123" in text, "Hoofdmaten moeten als tekst aanwezig zijn"
            assert "Schaal: 1:2" in text, "Getekende en gerapporteerde standaardschaal moeten gelijk zijn"
            assert "P1811" in text, "Positie moet als merk-fallback worden gebruikt"

        reverse_nc1 = out / "P1811_reverse.nc1"
        pdf_to_nc1(trusted, reverse_nc1)
        assert _semantic_nc1(NC1_SOURCE) == _semantic_nc1(reverse_nc1)

        reverse_step = out / "P1811_reverse.step"
        step_result = pdf_to_step(trusted, reverse_step)
        assert step_result.details["volume_mm3"] > 0
        assert cq.importers.importStep(str(reverse_step)).val().isValid()

        reverse_ifc = out / "P1811_reverse.ifc"
        ifc_result = pdf_to_ifc(trusted, reverse_ifc)
        assert reverse_ifc.exists() and reverse_ifc.stat().st_size > 1000
        assert ifc_result.details.get("payload_schema") == "1.1"

        # STEP -> Trusted PDF -> exact STEP attachment.
        step_pdf = out / "D20_trusted.pdf"
        step_to_pdf(STEP_SOURCE, step_pdf)
        assert inspect_pdf(step_pdf, strict=True).trusted_exact
        with fitz.open(step_pdf) as document:
            assert "CONCEPT - NIET VOOR PRODUCTIE" not in document[0].get_text("text")
            assert "Status: RELEASED" in document[0].get_text("text")
        step_roundtrip = out / "D20_roundtrip.step"
        pdf_to_step(step_pdf, step_roundtrip)
        original_shape = cq.importers.importStep(str(STEP_SOURCE)).val()
        returned_shape = cq.importers.importStep(str(step_roundtrip)).val()
        volume_delta = (returned_shape.Volume() - original_shape.Volume()) / original_shape.Volume() * 100
        assert abs(volume_delta) < 1e-9

        # Visual tampering must invalidate Trusted status.
        tampered = out / "tampered.pdf"
        with fitz.open(trusted) as document:
            document[0].insert_text(fitz.Point(70, 70), "TAMPERED", fontsize=18)
            document.save(tampered)
        tampered_inspection = inspect_pdf(tampered)
        assert not tampered_inspection.trusted_exact
        assert any("Zichtbare tekening" in error for error in tampered_inspection.errors)
        try:
            pdf_to_nc1(tampered, out / "tampered.nc1")
        except PDFProductionBlockedError:
            pass
        else:
            raise AssertionError("Productie-export uit zichtbaar gewijzigde PDF had geblokkeerd moeten zijn")

        # Corrupt manifest must invalidate Trusted status.
        corrupt = out / "corrupt_manifest.pdf"
        with fitz.open(trusted) as document:
            manifest = json.loads(document.embfile_get("converter-model.json").decode("utf-8"))
            manifest["canonical_sha256"] = "0" * 64
            document.embfile_del("converter-model.json")
            document.embfile_add(
                "converter-model.json",
                json.dumps(manifest).encode("utf-8"),
                filename="converter-model.json",
                ufilename="converter-model.json",
                desc="corrupt test",
            )
            document.save(corrupt)
        corrupt_inspection = inspect_pdf(corrupt)
        assert not corrupt_inspection.trusted_exact
        assert any("Canonieke PDF-checksum" in error for error in corrupt_inspection.errors)

        # External LO4-like vector drawing: metadata recognised but production blocked.
        external = out / "LO4_external_vector.pdf"
        _make_external_lo4(external)
        analysis = analyze_external_pdf(external)
        values = {key: item.value for key, item in analysis.part.field_values.items()}
        assert values["position"] == "LO4"
        assert values["profile"] == "STRIP5*120"
        assert values["material"] == "S235JR"
        assert values["length_text"] == 160.0
        assert values["quantity"] == 4
        assert values["mark"] == "MLO4"
        assert values["total_quantity"] == 4
        assert values["hole_callouts"] == ["1x Ø14"]
        assert values["radius_callouts"] == [13.5, 13.5]
        assert values["scale"] == "1:2"
        assert values["sheet_format"] == "A4"
        assert values["subject"] == "LOSSE PLAAT"
        assert not analysis.part.validation.production_export_allowed
        try:
            pdf_to_step(external, out / "external.step")
        except PDFProductionBlockedError:
            pass
        else:
            raise AssertionError("External PDF zonder bevestigde geometrie had geblokkeerd moeten zijn")

        # Optional cloud AI requires consent and uses structured semantic-only output.
        provider = OpenAIResponsesProvider(
            model="test-vision-model",
            api_key="test-key",
            transport=_fake_openai_transport,
        )
        try:
            provider.interpret({"detected_fields": {}}, [b"png"], cloud_consent=False)
        except PermissionError:
            pass
        else:
            raise AssertionError("Cloud-AI zonder expliciete toestemming had geblokkeerd moeten zijn")
        cloud_analysis = analyze_external_pdf(external, ai_provider=provider, cloud_consent=True)
        assert cloud_analysis.ai is not None
        assert cloud_analysis.ai.provider == "openai-responses"
        assert cloud_analysis.ai.audit["store"] is False
        assert cloud_analysis.part.audit_log[-1]["request_id"] == "resp_test_123"

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
            "trusted_exact": inspection.trusted_exact,
            "visible_hash": result.details["visible_drawing_sha256"],
            "nc1_semantic_roundtrip": True,
            "step_volume_delta_percent": volume_delta,
            "ifc_payload_schema": ifc_result.details.get("payload_schema"),
            "tamper_blocked": True,
            "corrupt_manifest_blocked": True,
            "external_lo4_fields": values,
            "external_production_blocked": True,
            "cloud_ai_consent_required": True,
            "cloud_ai_store": False,
            "ai_geometry_guard": True,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
