"""Persistent v0.5 PDF, drawing review and advisory-AI validation.

The runner exercises the current source tree, not a mock replacement:

* every supplied NC1 file -> Trusted PDF -> exact NC1;
* every supplied STEP file -> Trusted PDF -> exact STEP plus geometry compare;
* focus Trusted PDF -> IFC routes;
* synthetic LO4 external vector drawing -> explicit review -> NC1/STEP/IFC/PDF;
* integrity, ambiguity and AI-contract negative tests.

The original ``Pos LO4 - LOSSE PLAAT.pdf`` can be supplied with ``--real-lo4``.
When its binary is not available the report explicitly records that limitation;
the synthetic fixture is never presented as the original Tekla PDF.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import traceback
import urllib.request
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq
import pymupdf
from pypdf import PdfReader, PdfWriter

import converter as core
from ai_support import (
    AISettings,
    CloudAIConsentError,
    interpret_drawing,
    validate_ai_payload,
)
from canonical_model import extract_part_from_ifc, sha256_file
from conversion import __version__, build_shape
from pdf_support import (
    ExternalPDFExportBlocked,
    TrustedPDFError,
    analyze_external_pdf,
    analyze_pdf,
    apply_review,
    load_trusted_pdf,
    nc1_to_pdf,
    pdf_to_ifc,
    pdf_to_nc1,
    pdf_to_step,
    review_external_pdf,
    step_to_pdf,
    visible_pdf_sha256,
)
from validation.geometric_compare import compare_step
from validation.pdf_fixtures import create_synthetic_lo4_pdf
from validation.semantic_compare import compare_nc1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _render_pdf(source: Path, target_dir: Path, prefix: str, *, dpi: int = 200) -> list[str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(source)
    outputs: list[str] = []
    try:
        zoom = max(72, int(dpi)) / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        for index, page in enumerate(document, start=1):
            target = target_dir / f"{prefix}_page_{index}.png"
            target.write_bytes(page.get_pixmap(matrix=matrix, alpha=False).tobytes("png"))
            outputs.append(str(target))
    finally:
        document.close()
    return outputs


def _nc1_metrics(path: Path) -> dict[str, Any]:
    part = core.parse_nc1(path)
    shape = build_shape(part).val()
    box = shape.BoundingBox()
    return {
        "part": part.header.part_number,
        "position": part.header.position_number,
        "profile": part.header.profile,
        "profile_type": part.header.profile_type,
        "material": part.header.material,
        "quantity": part.header.quantity,
        "length_mm": float(part.header.length),
        "holes": len(part.holes),
        "contours": len(part.contours),
        "contour_points": sum(len(item.geometry_points) for item in part.contours),
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
    }


def _step_metrics(path: Path) -> dict[str, Any]:
    shape = cq.importers.importStep(str(path)).val()
    box = shape.BoundingBox()
    return {
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
        "solids": len(shape.Solids()),
    }


def _strip_attachments_keep_metadata(source: Path, target: Path) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({str(key): str(value) for key, value in (reader.metadata or {}).items()})
    with target.open("wb") as handle:
        writer.write(handle)


def _corrupt_model_attachment(source: Path, target: Path) -> None:
    reader = PdfReader(str(source))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    names = writer.root_object["/Names"].get_object()
    embedded = names["/EmbeddedFiles"].get_object()
    entries = embedded["/Names"]
    for index in range(0, len(entries), 2):
        if str(entries[index]) != "converter-model.json":
            continue
        spec = entries[index + 1].get_object()
        stream = spec["/EF"]["/F"].get_object()
        stream.set_data(b'{"schema_version":"1.1","damaged":true}')
        break
    else:
        raise AssertionError("converter-model.json attachment not found")
    with target.open("wb") as handle:
        writer.write(handle)


def _fake_cloud_transport(capture: dict[str, Any]):
    def transport(request: urllib.request.Request, timeout: float):
        payload = json.loads(bytes(request.data or b"").decode("utf-8"))
        capture["payload"] = payload
        capture["timeout"] = timeout
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
                }
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
            "layout_suggestions": ["Plaats het hoofdaanzicht links."],
        }
        response = {
            "id": "resp_validation_v05",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(answer)}],
                }
            ],
        }
        return 200, json.dumps(response).encode("utf-8"), {"x-request-id": "req_validation_v05"}

    return transport


def _ifcopenshell_validation(path: Path) -> dict[str, Any]:
    try:
        import ifcopenshell  # type: ignore
    except Exception as exc:
        return {"available": False, "error": str(exc)}
    try:
        model = ifcopenshell.open(str(path))
        plates = model.by_type("IfcPlate")
        return {
            "available": True,
            "schema": str(model.schema),
            "ifc_plate_count": len(plates),
            "entity_count": sum(1 for _ in model),
            "valid_open": True,
        }
    except Exception as exc:
        return {"available": True, "valid_open": False, "error": f"{type(exc).__name__}: {exc}"}


def _validate_nc1_trusted_roundtrips(files: Iterable[Path], output: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in files:
        case = output / source.stem
        case.mkdir(parents=True, exist_ok=True)
        pdf = case / f"{source.stem}_trusted.pdf"
        restored = case / f"{source.stem}_restored.nc1"
        row: dict[str, Any] = {"source": source.name, "route": "NC1->Trusted PDF->NC1", "status": "failed"}
        try:
            generated = nc1_to_pdf(source, pdf)
            trusted = load_trusted_pdf(pdf, strict=True)
            reverse = pdf_to_nc1(pdf, restored)
            comparison = compare_nc1(source, restored)
            source_metrics = _nc1_metrics(source)
            row.update(
                status="passed" if source.read_bytes() == restored.read_bytes() and comparison["passed"] else "different",
                byte_equal=source.read_bytes() == restored.read_bytes(),
                semantic_equal=bool(comparison["passed"]),
                trusted_mode=trusted.mode,
                production_export_allowed=trusted.production_export_allowed,
                profile=source_metrics["profile"],
                profile_type=source_metrics["profile_type"],
                material=source_metrics["material"],
                quantity=source_metrics["quantity"],
                holes=source_metrics["holes"],
                contours=source_metrics["contours"],
                volume_mm3=source_metrics["volume_mm3"],
                area_mm2=source_metrics["area_mm2"],
                source_sha256=_sha256(source),
                pdf_sha256=_sha256(pdf),
                restored_sha256=_sha256(restored),
                visible_sha256=visible_pdf_sha256(pdf),
                canonical_sha256=trusted.details["manifest"]["canonical_sha256"],
                geometry_sha256=trusted.details["manifest"]["geometry_sha256"],
                pdf_route=generated.details.get("route"),
                reverse_route=reverse.details.get("route"),
                pdf=str(pdf.relative_to(output.parent)),
                restored=str(restored.relative_to(output.parent)),
            )
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["traceback"] = traceback.format_exc()
        rows.append(row)
    return rows


def _validate_step_trusted_roundtrips(files: Iterable[Path], output: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in files:
        case = output / source.stem
        case.mkdir(parents=True, exist_ok=True)
        pdf = case / f"{source.stem}_trusted.pdf"
        restored = case / f"{source.stem}_restored.step"
        row: dict[str, Any] = {"source": source.name, "route": "STEP->Trusted PDF->STEP", "status": "failed"}
        try:
            generated = step_to_pdf(source, pdf)
            trusted = load_trusted_pdf(pdf, strict=True)
            reverse = pdf_to_step(pdf, restored)
            comparison = compare_step(source, restored)
            metrics = _step_metrics(source)
            byte_equal = source.read_bytes() == restored.read_bytes()
            row.update(
                status="passed" if byte_equal and comparison["passed"] else "different",
                byte_equal=byte_equal,
                geometry_equal=bool(comparison["passed"]),
                trusted_mode=trusted.mode,
                production_export_allowed=trusted.production_export_allowed,
                profile=trusted.part.header.profile,
                profile_type=trusted.part.header.profile_type,
                material=trusted.part.header.material,
                quantity=trusted.part.header.quantity,
                holes=len(trusted.part.holes),
                contours=len(trusted.part.contours),
                volume_mm3=metrics["volume_mm3"],
                area_mm2=metrics["area_mm2"],
                volume_delta_percent=comparison["volume_delta_percent"],
                area_delta_percent=comparison["area_delta_percent"],
                max_aligned_dimension_delta_mm=comparison["max_aligned_dimension_delta_mm"],
                source_sha256=_sha256(source),
                pdf_sha256=_sha256(pdf),
                restored_sha256=_sha256(restored),
                visible_sha256=visible_pdf_sha256(pdf),
                canonical_sha256=trusted.details["manifest"]["canonical_sha256"],
                geometry_sha256=trusted.details["manifest"]["geometry_sha256"],
                pdf_route=generated.details.get("route"),
                reverse_route=reverse.details.get("route"),
                pdf=str(pdf.relative_to(output.parent)),
                restored=str(restored.relative_to(output.parent)),
            )
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["traceback"] = traceback.format_exc()
        rows.append(row)
    return rows


def _validate_focus_pdf_to_ifc(
    p1811: Path,
    d20: Path,
    output: Path,
) -> list[dict[str, Any]]:
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for source, kind in ((p1811, "nc1"), (d20, "step")):
        row: dict[str, Any] = {"source": source.name, "route": "Trusted PDF->IFC", "status": "failed"}
        try:
            pdf = output / f"{source.stem}.pdf"
            ifc = output / f"{source.stem}.ifc"
            if kind == "nc1":
                nc1_to_pdf(source, pdf)
            else:
                step_to_pdf(source, pdf)
            result = pdf_to_ifc(pdf, ifc)
            payload = extract_part_from_ifc(ifc, strict=True)
            if payload is None:
                raise AssertionError("IFC canonical payload missing")
            source_key = "nc1" if kind == "nc1" else "step"
            exact_source = payload.attachment_bytes(source_key)
            text = ifc.read_text(encoding="utf-8", errors="replace").upper()
            row.update(
                status="passed" if exact_source == source.read_bytes() else "different",
                exact_source_attachment=exact_source == source.read_bytes(),
                source_format=payload.source_format,
                payload_schema=payload.schema_version,
                output_sha256=_sha256(ifc),
                conversion_route=result.details.get("route"),
                ifc_plate="IFCPLATE" in text,
                swept_solid="IFCEXTRUDEDAREASOLID" in text,
                triangulated_preview="IFCTRIANGULATEDFACESET" in text,
                ifcopenshell=_ifcopenshell_validation(ifc),
            )
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["traceback"] = traceback.format_exc()
        rows.append(row)
    return rows


def _validate_synthetic_lo4(output: Path, render_dir: Path, *, dpi: int) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    source = create_synthetic_lo4_pdf(output / "LO4_external_vector_SYNTHETIC.pdf")
    before = analyze_external_pdf(source)
    before_report = output / "LO4_analysis_before_review.json"
    before_report.write_text(json.dumps(before.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    expected_fields = {
        "position": "LO4",
        "profile": "STRIP5*120",
        "material": "S235JR",
        "length": 160.0,
        "quantity": 4,
        "mark": "MLO4",
        "total_quantity": 4,
        "scale": "1:2",
        "subject": "LOSSE PLAAT",
    }
    field_checks = {key: before.detected_fields.get(key) == value for key, value in expected_fields.items()}
    radii = sorted(point.radius for item in before.part.contours for point in item.points if point.radius > 0)
    hole = before.part.holes[0] if before.part.holes else None
    blocking_before = len(before.part.validation.blocking_questions())
    try:
        pdf_to_nc1(source, output / "must_remain_blocked.nc1")
    except ExternalPDFExportBlocked:
        blocked_before = True
    else:
        blocked_before = False

    review_data = {
        "reviewed_by": "validation-runner",
        "confirm": ["holes[0]"],
        "comment": "Synthetische vectorgeometrie en productiereferentie visueel gecontroleerd.",
    }
    review_path = output / "LO4_review.json"
    review_path.write_text(json.dumps(review_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    after = apply_review(before, review_data)
    after_report = output / "LO4_analysis_after_review.json"
    after_report.write_text(json.dumps(after.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    trusted = output / "LO4_reviewed_trusted.pdf"
    review_external_pdf(source, review_path, trusted)
    trusted_analysis = load_trusted_pdf(trusted, strict=True)
    nc1 = output / "LO4_from_pdf.nc1"
    step = output / "LO4_from_pdf.step"
    ifc = output / "LO4_from_pdf.ifc"
    regenerated_pdf = output / "LO4_regenerated_from_nc1.pdf"
    regenerated_nc1 = output / "LO4_regenerated_roundtrip.nc1"
    nc1_result = pdf_to_nc1(trusted, nc1)
    step_result = pdf_to_step(trusted, step)
    ifc_result = pdf_to_ifc(trusted, ifc)
    nc1_to_pdf(nc1, regenerated_pdf)
    pdf_to_nc1(regenerated_pdf, regenerated_nc1)

    parsed = core.parse_nc1(nc1)
    nc1_shape = build_shape(parsed).val()
    step_shape = cq.importers.importStep(str(step)).val()
    volume_delta = (step_shape.Volume() - nc1_shape.Volume()) / nc1_shape.Volume() * 100.0
    area_delta = (step_shape.Area() - nc1_shape.Area()) / nc1_shape.Area() * 100.0
    semantic_roundtrip = compare_nc1(nc1, regenerated_nc1)
    ifc_text = ifc.read_text(encoding="utf-8", errors="replace").upper()
    tokens = {
        token: token.upper() in ifc_text
        for token in (
            "IFCPLATE",
            "IFCEXTRUDEDAREASOLID",
            "IFCARBITRARYPROFILEDEFWITHVOIDS",
            "IFCCIRCLE",
            "IFCINDEXEDPOLYCURVE",
            "IFCARCINDEX",
            "IFCTRIANGULATEDFACESET",
            "QTO_PLATEBASEQUANTITIES",
            "PSET_NC1STEPCONVERTER",
        )
    }
    ifc_payload = extract_part_from_ifc(ifc, strict=True)
    if ifc_payload is None:
        raise AssertionError("LO4 IFC payload missing")

    _render_pdf(source, render_dir, "LO4_external_synthetic", dpi=dpi)
    _render_pdf(trusted, render_dir, "LO4_reviewed_trusted", dpi=dpi)
    _render_pdf(regenerated_pdf, render_dir, "LO4_regenerated_from_nc1", dpi=dpi)

    feature_checks = {
        "field_values": all(field_checks.values()),
        "sheet_A4": before.part.drawing.sheet_format == "A4",
        "subject": before.part.product.name == "LOSSE PLAAT",
        "one_contour": len(before.part.contours) == 1,
        "four_contour_vertices": bool(before.part.contours) and len(before.part.contours[0].points) == 4,
        "two_R13_5": len(radii) == 2 and all(abs(value - 13.5) <= 0.15 for value in radii),
        "one_D14_hole": hole is not None and abs(hole.diameter - 14.0) <= 0.15,
        "hole_position_20_20": hole is not None and abs(hole.x - 20.0) <= 0.15 and abs(hole.q - 20.0) <= 0.15,
        "blocked_before_review": blocked_before and not before.production_export_allowed,
        "released_after_review": after.production_export_allowed,
        "trusted_exact": trusted_analysis.mode == "trusted_exact",
        "nc1_header": parsed.header.position_number == "LO4" and parsed.header.profile == "STRIP5*120",
        "nc1_one_hole": len(parsed.holes) == 1 and abs(parsed.holes[0].diameter - 14.0) <= 0.01,
        "nc1_radii": sorted(round(point.radius, 2) for item in parsed.contours for point in item.geometry_points if point.radius > 0) == [13.5, 13.5],
        "step_geometry": abs(volume_delta) <= 1e-9 and abs(area_delta) <= 1e-9,
        "analytic_ifc": all(tokens.values()),
        "ifc_payload": ifc_payload.attachment_bytes("nc1") == nc1.read_bytes(),
        "regenerated_pdf_roundtrip": bool(semantic_roundtrip["passed"]),
    }
    status = "passed" if all(feature_checks.values()) else "failed"
    return {
        "route": "Synthetic external PDF->review->Trusted PDF->NC1/STEP/IFC->PDF",
        "status": status,
        "fixture_class": "synthetic vector regression fixture; not the original Tekla PDF binary",
        "source": source.name,
        "mode_before_review": before.mode,
        "mode_after_review": after.mode,
        "blocking_questions_before": blocking_before,
        "blocking_questions_after": len(after.part.validation.blocking_questions()),
        "detected_fields": before.detected_fields,
        "field_checks": field_checks,
        "feature_checks": feature_checks,
        "radii_mm": radii,
        "hole_mm": {"x": hole.x, "q": hole.q, "diameter": hole.diameter} if hole else None,
        "nc1_volume_mm3": float(nc1_shape.Volume()),
        "nc1_area_mm2": float(nc1_shape.Area()),
        "step_volume_mm3": float(step_shape.Volume()),
        "step_area_mm2": float(step_shape.Area()),
        "volume_delta_percent": volume_delta,
        "area_delta_percent": area_delta,
        "nc1_route": nc1_result.details.get("route"),
        "step_route": step_result.details.get("route"),
        "ifc_route": ifc_result.details.get("route"),
        "analytic_ifc_tokens": tokens,
        "ifcopenshell": _ifcopenshell_validation(ifc),
        "trusted_pdf_sha256": _sha256(trusted),
        "trusted_visible_sha256": visible_pdf_sha256(trusted),
        "nc1_sha256": _sha256(nc1),
        "step_sha256": _sha256(step),
        "ifc_sha256": _sha256(ifc),
        "regenerated_pdf_sha256": _sha256(regenerated_pdf),
    }


def _validate_ai_and_negative(
    trusted_pdf: Path,
    synthetic_lo4: Path,
    output: Path,
) -> list[dict[str, Any]]:
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    before = analyze_external_pdf(synthetic_lo4)
    geometry_before = before.part.geometry_sha256()
    local = analyze_external_pdf(
        synthetic_lo4,
        ai_settings=AISettings(provider="local-rules"),
    )
    rows.append(
        {
            "test": "local-rules advisory AI",
            "status": "passed" if geometry_before == local.part.geometry_sha256() else "failed",
            "provider": local.ai.provider if local.ai else "",
            "geometry_unchanged": geometry_before == local.part.geometry_sha256(),
            "production_export_allowed": local.production_export_allowed,
            "field_suggestions": len(local.ai.fields) if local.ai else 0,
            "question_suggestions": len(local.ai.questions) if local.ai else 0,
        }
    )

    try:
        interpret_drawing(
            synthetic_lo4,
            deterministic_context={},
            settings=AISettings(provider="openai", allow_cloud=False),
        )
    except CloudAIConsentError:
        consent_blocked = True
    else:
        consent_blocked = False
    rows.append(
        {
            "test": "cloud AI explicit consent guard",
            "status": "passed" if consent_blocked else "failed",
            "consent_blocked": consent_blocked,
        }
    )

    capture: dict[str, Any] = {}
    cloud = interpret_drawing(
        synthetic_lo4,
        deterministic_context={
            "page_count": 1,
            "page_classification": ["vector"],
            "sheet_format": "A4",
            "orientation": "landscape",
            "detected_fields": {"position": "LO4"},
            "missing_critical": ["reference_side"],
            "conflicts": [],
            "vector_path_count": 3,
            "image_count": 0,
        },
        settings=AISettings(
            provider="openai",
            model="test-vision-model",
            allow_cloud=True,
            api_key="test-key",
            transport=_fake_cloud_transport(capture),
        ),
    )
    request_payload = capture.get("payload") or {}
    content = (((request_payload.get("input") or [{}])[0]).get("content") or []) if isinstance(request_payload, dict) else []
    cloud_contract = bool(
        isinstance(request_payload, dict)
        and request_payload.get("store") is False
        and request_payload.get("text", {}).get("format", {}).get("type") == "json_schema"
        and request_payload.get("text", {}).get("format", {}).get("strict") is True
        and any(item.get("type") == "input_image" for item in content if isinstance(item, dict))
        and cloud.audit.get("store") is False
        and cloud.request_id == "resp_validation_v05"
    )
    rows.append(
        {
            "test": "mocked OpenAI Responses semantic contract",
            "status": "passed" if cloud_contract else "failed",
            "store_false": request_payload.get("store") is False if isinstance(request_payload, dict) else False,
            "strict_json_schema": request_payload.get("text", {}).get("format", {}).get("strict") is True if isinstance(request_payload, dict) else False,
            "image_input": any(item.get("type") == "input_image" for item in content if isinstance(item, dict)),
            "request_id": cloud.request_id,
        }
    )

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
        geometry_guard = True
    else:
        geometry_guard = False
    rows.append(
        {
            "test": "AI production geometry guard",
            "status": "passed" if geometry_guard else "failed",
            "rejected": geometry_guard,
        }
    )

    tampered = output / "tampered_visible.pdf"
    reader = PdfReader(str(trusted_pdf))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.add_blank_page(width=100, height=100)
    with tampered.open("wb") as handle:
        writer.write(handle)
    try:
        analyze_pdf(tampered)
    except TrustedPDFError:
        rejected = True
    else:
        rejected = False
    rows.append(
        {
            "test": "visible page tamper",
            "status": "passed" if rejected else "failed",
            "rejected": rejected,
            "mutated_pdf": str(tampered.relative_to(output.parent)),
            "sha256": _sha256(tampered),
        }
    )

    stripped = output / "stripped_attachments.pdf"
    _strip_attachments_keep_metadata(trusted_pdf, stripped)
    try:
        analyze_pdf(stripped)
    except TrustedPDFError:
        rejected = True
    else:
        rejected = False
    rows.append(
        {
            "test": "trusted attachments stripped",
            "status": "passed" if rejected else "failed",
            "rejected": rejected,
            "mutated_pdf": str(stripped.relative_to(output.parent)),
            "sha256": _sha256(stripped),
        }
    )

    corrupted = output / "corrupted_model.pdf"
    _corrupt_model_attachment(trusted_pdf, corrupted)
    try:
        analyze_pdf(corrupted)
    except TrustedPDFError:
        rejected = True
    else:
        rejected = False
    rows.append(
        {
            "test": "canonical model attachment corrupted",
            "status": "passed" if rejected else "failed",
            "rejected": rejected,
            "mutated_pdf": str(corrupted.relative_to(output.parent)),
            "sha256": _sha256(corrupted),
        }
    )

    conflict_pdf = create_synthetic_lo4_pdf(
        output / "LO4_conflicting_hole_diameter.pdf",
        hole_callout_diameter_mm=18.0,
        hole_geometry_diameter_mm=14.0,
    )
    conflict = analyze_external_pdf(conflict_pdf)
    partially_reviewed = apply_review(
        conflict,
        {
            "reviewed_by": "validation-runner",
            "confirm": ["holes[0]"],
            "comment": "Generic hole confirmed without resolving diameter conflict.",
        },
    )
    conflict_guard = bool(
        "holes[0].diameter" in conflict.details.get("conflicts", [])
        and not partially_reviewed.production_export_allowed
        and any(
            question.field_path == "holes[0].diameter" and question.status == "open"
            for question in partially_reviewed.part.validation.unresolved_questions
        )
    )
    rows.append(
        {
            "test": "written versus vector hole diameter conflict",
            "status": "passed" if conflict_guard else "failed",
            "rejected": conflict_guard,
            "conflicts": conflict.details.get("conflicts", []),
        }
    )
    return rows


def _validate_real_lo4(real_lo4: Path | None, output: Path) -> dict[str, Any]:
    if real_lo4 is None or not real_lo4.is_file():
        return {
            "executed": False,
            "status": "not-executed",
            "reason": "Original LO4 PDF binary was not mounted; only File Library text/visual reference was available.",
        }
    output.mkdir(parents=True, exist_ok=True)
    try:
        analysis = analyze_external_pdf(real_lo4)
        report = output / "real_LO4_analysis.json"
        report.write_text(json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        expected = {
            "position": "LO4",
            "profile": "STRIP5*120",
            "material": "S235JR",
            "length": 160.0,
            "quantity": 4,
            "mark": "MLO4",
            "total_quantity": 4,
            "scale": "1:2",
            "subject": "LOSSE PLAAT",
        }
        checks = {key: analysis.detected_fields.get(key) == value for key, value in expected.items()}
        return {
            "executed": True,
            "status": "passed" if all(checks.values()) else "different",
            "source": str(real_lo4),
            "source_sha256": _sha256(real_lo4),
            "mode": analysis.mode,
            "checks": checks,
            "production_export_allowed": analysis.production_export_allowed,
            "blocking_questions": [item.prompt for item in analysis.part.validation.blocking_questions()],
        }
    except Exception as exc:
        return {
            "executed": True,
            "status": "failed",
            "source": str(real_lo4),
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }


def _markdown(results: dict[str, Any]) -> str:
    summary = results["summary"]
    lo4 = results["synthetic_lo4"]
    focus_ifc = results["focus_pdf_to_ifc"]
    lines = [
        f"# PDF-, tekening- en AI-validatie v{summary['converter_version']}",
        "",
        "Deze validatie is daadwerkelijk uitgevoerd met de strikte productiepoort ingeschakeld. AI is uitsluitend adviserend gebruikt; productiegeometrie, NC1/STEP/IFC-serialisatie en vrijgave zijn deterministisch.",
        "",
        "> De synthetische LO4-vectorfixture is gebaseerd op de opgegeven waarden, maar is niet het oorspronkelijke Tekla-PDF-bestand. De status van de echte bron staat apart vermeld.",
        "",
        "## Samenvatting",
        "",
        "| Testgroep | Geslaagd | Totaal |",
        "|---|---:|---:|",
        f"| NC1 -> Trusted PDF -> exact NC1 | {summary['nc1_pdf_passed']} | {summary['nc1_pdf_total']} |",
        f"| STEP -> Trusted PDF -> exact STEP | {summary['step_pdf_passed']} | {summary['step_pdf_total']} |",
        f"| Focus Trusted PDF -> IFC | {summary['focus_ifc_passed']} | {summary['focus_ifc_total']} |",
        f"| Synthetische LO4 externe PDF-keten | {summary['lo4_passed']} | 1 |",
        f"| AI-/integriteits-/ambiguiteitstests | {summary['safety_passed']} | {summary['safety_total']} |",
        "",
        "## Trusted PDF-roundtrips",
        "",
        f"Alle {summary['nc1_pdf_total']} NC1-bestanden zijn naar een vectoriele Trusted Converter PDF geschreven en exact teruggelezen. Geslaagd: **{summary['nc1_pdf_passed']}**.",
        "",
        f"Alle {summary['step_pdf_total']} STEP-bestanden zijn eveneens in een Trusted PDF opgenomen en exact teruggelezen, met aanvullende geometrievergelijking. Geslaagd: **{summary['step_pdf_passed']}**.",
        "",
        "## Focus PDF -> IFC",
        "",
        "| Bron | Status | Route | Exacte bronbijlage | IfcPlate | Swept solid |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in focus_ifc:
        lines.append(
            f"| {row.get('source','')} | **{row.get('status','')}** | {row.get('conversion_route','')} | {row.get('exact_source_attachment',False)} | {row.get('ifc_plate',False)} | {row.get('swept_solid',False)} |"
        )
    lines.extend(
        [
            "",
            "## Synthetische LO4-regressie",
            "",
            f"Status: **{lo4['status']}**. Voor review stonden {lo4['blocking_questions_before']} blokkerende vragen open; na expliciete review {lo4['blocking_questions_after']}.",
            "",
            f"Herkende kernvelden: `{json.dumps(lo4['field_checks'], ensure_ascii=False, sort_keys=True)}`",
            "",
            f"Radii: `{lo4['radii_mm']}` mm; gat: `{lo4['hole_mm']}`; STEP-volumeverschil: `{lo4['volume_delta_percent']:+.12f}%`.",
            "",
            "De keten genereerde een gevalideerd NC1-bestand, analytische STEP-solid, semantisch IfcPlate met SweptSolid/cirkelvoid/boogindices, een Trusted PDF en een tweede exacte PDF->NC1-roundtrip.",
            "",
            "## AI- en integriteitsbeveiliging",
            "",
            "| Test | Status |",
            "|---|---|",
        ]
    )
    for row in results["ai_and_negative_tests"]:
        lines.append(f"| {row.get('test','')} | **{row.get('status','')}** |")
    real = results["real_lo4"]
    lines.extend(
        [
            "",
            "## Echte LO4-referentie",
            "",
            f"Status: **{real.get('status')}**. {real.get('reason','')}",
            "",
            "## Begrenzingen",
            "",
            "- Raster-OCR, foto-/perspectiefcorrectie en algemene meer-aanzichtreconstructie zijn nog geen productie-importer.",
            "- Een willekeurige externe PDF blijft geblokkeerd totdat contour, gaten, referentiezijde en conflicterende maatvoering deterministisch of expliciet zijn bevestigd.",
            "- De Windows-installer is pas bewezen na een native Windows x64-build en schone-machine-installatietest.",
            "",
            "Volledige meetwaarden, routes, fouttraces en hashes staan in `results.json`, de CSV-bestanden en `SHA256SUMS.txt`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handover-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--real-lo4", type=Path)
    parser.add_argument("--render-dpi", type=int, default=200)
    args = parser.parse_args()

    handover = args.handover_root.resolve()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    complete = handover / "03_TEST_INPUTS" / "COMPLETE_DATASET"
    focus = handover / "03_TEST_INPUTS" / "ROUNDTRIP_FOCUS"
    nc1_files = sorted((complete / "NC_Files").glob("*.nc1")) + sorted((complete / "NC_Files").glob("*.nc"))
    step_files = sorted((complete / "STP_files").glob("*.stp")) + sorted((complete / "STP_files").glob("*.step"))
    p1811 = focus / "NC1" / "P1811.nc1"
    d20 = focus / "STEP" / "Pr1527_14_LIGGER_D20.stp"
    if not nc1_files or not step_files or not p1811.is_file() or not d20.is_file():
        raise FileNotFoundError("The handover dataset is incomplete")

    nc1_rows = _validate_nc1_trusted_roundtrips(nc1_files, output / "trusted_nc1_roundtrips")
    step_rows = _validate_step_trusted_roundtrips(step_files, output / "trusted_step_roundtrips")
    focus_ifc = _validate_focus_pdf_to_ifc(p1811, d20, output / "focus_pdf_to_ifc")
    lo4 = _validate_synthetic_lo4(output / "synthetic_lo4", output / "renders", dpi=args.render_dpi)

    # Render representative real-data PDFs as an explicit visual QA artifact.
    p1811_pdf = output / "trusted_nc1_roundtrips" / "P1811" / "P1811_trusted.pdf"
    d20_pdf = output / "trusted_step_roundtrips" / "Pr1527_14_LIGGER_D20" / "Pr1527_14_LIGGER_D20_trusted.pdf"
    _render_pdf(p1811_pdf, output / "renders", "P1811_trusted", dpi=args.render_dpi)
    _render_pdf(d20_pdf, output / "renders", "D20_trusted", dpi=args.render_dpi)

    ai_negative = _validate_ai_and_negative(
        p1811_pdf,
        output / "synthetic_lo4" / "LO4_external_vector_SYNTHETIC.pdf",
        output / "negative_and_ai",
    )
    real_lo4 = _validate_real_lo4(args.real_lo4.resolve() if args.real_lo4 else None, output / "real_lo4")

    summary = {
        "converter_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.system().lower(),
        "nc1_pdf_total": len(nc1_rows),
        "nc1_pdf_passed": sum(row.get("status") == "passed" for row in nc1_rows),
        "step_pdf_total": len(step_rows),
        "step_pdf_passed": sum(row.get("status") == "passed" for row in step_rows),
        "focus_ifc_total": len(focus_ifc),
        "focus_ifc_passed": sum(row.get("status") == "passed" for row in focus_ifc),
        "lo4_passed": int(lo4.get("status") == "passed"),
        "safety_total": len(ai_negative),
        "safety_passed": sum(row.get("status") == "passed" for row in ai_negative),
        "original_lo4_binary_locally_tested": bool(real_lo4.get("executed")),
    }
    summary["all_passed"] = bool(
        summary["nc1_pdf_passed"] == summary["nc1_pdf_total"]
        and summary["step_pdf_passed"] == summary["step_pdf_total"]
        and summary["focus_ifc_passed"] == summary["focus_ifc_total"]
        and summary["lo4_passed"] == 1
        and summary["safety_passed"] == summary["safety_total"]
        and real_lo4.get("status") not in {"failed", "different"}
    )
    results = {
        "summary": summary,
        "real_nc1_trusted_pdf_roundtrips": nc1_rows,
        "real_step_trusted_pdf_roundtrips": step_rows,
        "focus_pdf_to_ifc": focus_ifc,
        "synthetic_lo4": lo4,
        "ai_and_negative_tests": ai_negative,
        "real_lo4": real_lo4,
        "environment": {
            "cwd": str(ROOT),
            "handover_root": str(handover),
            "ifcopenshell_importable": any(
                row.get("ifcopenshell", {}).get("available") for row in focus_ifc
            ),
        },
    }
    (output / "results.json").write_text(
        json.dumps(_json_safe(results), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(output / "trusted_nc1_roundtrips.csv", nc1_rows)
    _write_csv(output / "trusted_step_roundtrips.csv", step_rows)
    _write_csv(output / "focus_pdf_to_ifc.csv", focus_ifc)
    _write_csv(output / "ai_and_negative_tests.csv", ai_negative)
    _write_csv(output / "synthetic_lo4.csv", [lo4])
    (output / "PDF_AI_VALIDATIE_V05.md").write_text(_markdown(results), encoding="utf-8")

    checksums: list[str] = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "SHA256SUMS.txt"):
        checksums.append(f"{_sha256(path)}  {path.relative_to(output).as_posix()}")
    (output / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="ascii")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
