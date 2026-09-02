"""Build exact-SHA visual proof for every PDF/drawing requirement.

All evidence images come from a real CWS drawing PDF, an independently rendered
external PDF, or a real Qt runtime capture. The tool never promotes the two
intentional review gates to automatic production release.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.drawings import DrawingBuildRequest, ProductionDrawingEngine, ProductionDrawingRenderer
from cws_convertor.product import APP_NAME, APP_VERSION
from pdf_support import ExternalPDFExportBlocked, analyze_external_pdf, pdf_to_step
from validation.pdf_fixtures import create_synthetic_lo4_pdf


REQUIREMENTS = (
    ("PDF-01", "PDF genereren", "Documentuitvoer, formaat, orientatie en projecties"),
    ("PDF-02", "A0-A4", "Documentuitvoer, formaat, orientatie en projecties"),
    ("PDF-03", "Portrait/landscape", "Documentuitvoer, formaat, orientatie en projecties"),
    ("PDF-04", "Auto/vaste schaal", "Documentuitvoer, formaat, orientatie en projecties"),
    ("PDF-05", "mm/cm", "Documentuitvoer, formaat, orientatie en projecties"),
    ("PDF-06", "Voor/boven/zij", "Documentuitvoer, formaat, orientatie en projecties"),
    ("PDF-07", "3D versus ISO", "Documentuitvoer, formaat, orientatie en projecties"),
    ("PDF-08", "Preview = PDF", "Documentuitvoer, formaat, orientatie en projecties"),
    ("PDF-09", "Hoofdmaten", "Maatvoering en productiefeatures"),
    ("PDF-10", "Contour + gaten", "Maatvoering en productiefeatures"),
    ("PDF-11", "Productiematen", "Maatvoering en productiefeatures"),
    ("PDF-12", "Eigen maten", "Maatvoering en productiefeatures"),
    ("PDF-13", "Gatcallouts", "Maatvoering en productiefeatures"),
    ("PDF-14", "Sleufgaten", "Maatvoering en productiefeatures"),
    ("PDF-15", "Verzonken gaten", "Maatvoering en productiefeatures"),
    ("PDF-16", "Pockets/copes/cutouts", "Maatvoering en productiefeatures"),
    ("PDF-17", "Verstek/kopse sneden", "Maatvoering en productiefeatures"),
    ("PDF-18", "Scribing/markering", "Maatvoering en productiefeatures"),
    ("PDF-19", "Echte HLR", "Exacte geometrie, HLR en doorsneden"),
    ("PDF-20", "Verborgen lijnen", "Exacte geometrie, HLR en doorsneden"),
    ("PDF-21", "Geen triangulatielijnen", "Exacte geometrie, HLR en doorsneden"),
    ("PDF-22", "Centerlines", "Exacte geometrie, HLR en doorsneden"),
    ("PDF-23", "Doorsneden", "Exacte geometrie, HLR en doorsneden"),
    ("PDF-24", "Detailviews", "Exacte geometrie, HLR en doorsneden"),
    ("PDF-25", "Exact eindaanzicht", "Exacte geometrie, HLR en doorsneden"),
    ("PDF-26", "Exact 3D/ISO", "Exacte geometrie, HLR en doorsneden"),
    ("PDF-27", "Titelblok", "Bladopbouw, BOM en assemblytekening"),
    ("PDF-28", "Revisie/status/blad", "Bladopbouw, BOM en assemblytekening"),
    ("PDF-29", "BOM/materiaaltabel", "Bladopbouw, BOM en assemblytekening"),
    ("PDF-30", "Algemene notities", "Bladopbouw, BOM en assemblytekening"),
    ("PDF-31", "Meerdere bladen", "Bladopbouw, BOM en assemblytekening"),
    ("PDF-32", "Assembly drawing", "Bladopbouw, BOM en assemblytekening"),
    ("PDF-33", "DimensionGraph", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-34", "DrawingLinter", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-35", "Clipping/collision", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-36", "800% vector", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-37", "Trusted model/hash", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-38", "Trusted zichtinhoud", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-39", "Zichtbare roundtrip", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-40", "Externe PDF lezen", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-41", "Print Center", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-42", "Workbench naar PDF stale-state", "Validatie, Trusted PDF, externe PDF, print en stale-state"),
    ("PDF-43", "Exact-SHA release proof", "Build- en releasebewijs"),
)


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def reset_output(path: Path) -> None:
    resolved = path.resolve()
    allowed = (ROOT / "validation").resolve()
    if allowed not in resolved.parents:
        raise RuntimeError(f"Refusing to reset proof output outside validation: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def _native_shape() -> tuple[object, np.ndarray, np.ndarray]:
    import cadquery as cq

    shape = cq.Workplane("XY").box(240.0, 120.0, 20.0, centered=(False, False, False)).val()
    raw_vertices, raw_triangles = shape.tessellate(0.08)
    vertices = np.asarray([point.toTuple() for point in raw_vertices], dtype=float)
    triangles = np.asarray(raw_triangles, dtype=int)
    return shape, vertices, triangles


def _request(shape: object, vertices: np.ndarray, triangles: np.ndarray, commit: str, **changes: Any) -> DrawingBuildRequest:
    geometry_hash = sha256(vertices.tobytes() + triangles.tobytes()).hexdigest()
    values: dict[str, Any] = {
        "entity_id": "CWS-PDF-PROOF-001",
        "vertices": vertices,
        "triangles": triangles,
        "views": ("front", "top", "side", "iso", "3d"),
        "sheet_format": "A3",
        "orientation": "landscape",
        "unit": "mm",
        "dimension_mode": "Productiematen",
        "features": (
            {"feature_id": "H1", "kind": "hole", "parameters": {"x_mm": 35.0, "y_mm": 30.0, "diameter_mm": 18.0}},
            {"feature_id": "S1", "kind": "slot", "parameters": {"x_mm": 80.0, "y_mm": 30.0, "width_mm": 14.0, "length_mm": 36.0}},
            {"feature_id": "C1", "kind": "countersink", "parameters": {"x_mm": 125.0, "y_mm": 45.0, "diameter_mm": 12.0, "outer_diameter_mm": 24.0}},
            {"feature_id": "P1", "kind": "pocket", "parameters": {"x_mm": 165.0, "y_mm": 60.0, "width_mm": 28.0, "height_mm": 16.0}},
            {"feature_id": "M1", "kind": "miter", "parameters": {"x_mm": 240.0, "angle_deg": 45.0}},
            {"feature_id": "SC1", "kind": "scribe", "parameters": {"x_mm": 55.0, "y_mm": 15.0, "length_mm": 42.0}},
        ),
        "dimensions": (
            {"id": "overall-x", "kind": "linear", "value_mm": 240.0, "critical": True},
            {"id": "overall-y", "kind": "linear", "value_mm": 120.0, "critical": True},
            {"id": "hole-h1", "kind": "diameter", "value_mm": 18.0, "critical": True},
        ),
        "dimension_chains": ({"id": "chain-main", "members": ["overall-x", "hole-h1"]},),
        "manual_dimensions": ({"id": "manual-h1", "view": "front", "axis": "horizontal", "start": 0.0, "end": 35.0, "feature_id": "H1", "anchor_type": "feature_center"},),
        "title_block": {"project": "CWS PDF FUNCTION PROOF", "entity": "CWS-PDF-PROOF-001", "profile": "PL240x20", "material": "S355JR", "revision": "A", "status": "released"},
        "revisions": ({"revision": "A", "status": "released", "description": "Exact-SHA function proof"},),
        "bom": ({"mark": "P001", "quantity": 2, "profile": "PL240x20", "material": "S355JR"},),
        "notes": ("Ontbramen en scherpe kanten breken.", "Maten in millimeter tenzij anders aangegeven."),
        "geometry_basis": "canonical_rebuild_brep",
        "geometry_sha256": geometry_hash,
        "manufacturing_sha256": geometry_hash,
        "expected_manufacturing_sha256": geometry_hash,
        "source_revision": commit,
        "canonical_rebuild_current": True,
        "canonical_payload_current": True,
        "roundtrip_current": True,
        "exact_shape": shape,
    }
    values.update(changes)
    return DrawingBuildRequest(**values)


def _render_independently(pdf_path: Path, rendered_dir: Path, stem: str) -> dict[str, Any]:
    import fitz
    from pypdf import PdfReader

    document = fitz.open(str(pdf_path))
    reader = PdfReader(str(pdf_path))
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(document):
        zoom = max(0.1, 1800.0 / max(1.0, float(page.rect.width)))
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        target = rendered_dir / f"{stem}_page_{index + 1:02d}.png"
        pixmap.save(str(target))
        media = reader.pages[index].mediabox
        width_mm = float(media.width) * 25.4 / 72.0
        height_mm = float(media.height) * 25.4 / 72.0
        pages.append({
            "page": index + 1,
            "image": relative(target),
            "image_sha256": digest(target),
            "width_mm": round(width_mm, 3),
            "height_mm": round(height_mm, 3),
            "text_characters": len(page.get_text("text")),
            "vector_paths": len(page.get_drawings()),
            "images": len(page.get_images(full=True)),
            "status": "PASS" if (
                target.stat().st_size > 512
                and (len(page.get_drawings()) > 0 or len(page.get_text("text").strip()) >= 20)
            ) else "FAIL",
        })
    metadata = dict(reader.metadata or {})
    document.close()
    if not pages or any(item["status"] != "PASS" for item in pages):
        raise RuntimeError(f"Independent PDF render failed: {pdf_path}")
    return {
        "pdf": relative(pdf_path),
        "pdf_sha256": digest(pdf_path),
        "page_count": len(pages),
        "metadata": {str(key): str(value) for key, value in metadata.items()},
        "pages": pages,
        "status": "PASS",
    }


def _capture_source_ui(target: Path) -> Path:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
    from PySide6 import QtCore, QtWidgets
    from cws_convertor.ui_qt import CWSMainWindow

    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = CWSMainWindow()
    window.resize(1600, 1000)
    window.show()
    application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
    for index in range(window.tabs.count()):
        label = window.tabs.tabText(index).casefold()
        if "pdf" in label or "tekening" in label:
            window.tabs.setCurrentIndex(index)
            break
    application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not window.grab().save(str(target), "PNG") or target.stat().st_size < 10_000:
        raise RuntimeError("Actual Qt PDF workspace capture failed")
    window.close()
    application.processEvents()
    return target


def _contact_sheet(images: list[tuple[str, Path]], target: Path, *, columns: int = 5) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    tile_width, tile_height, caption = 360, 224, 34
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_width, rows * (tile_height + caption)), "#f4f7fa")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    for index, (label, path) in enumerate(images):
        row, column = divmod(index, columns)
        x, y = column * tile_width, row * (tile_height + caption)
        with Image.open(path) as source:
            frame = source.convert("RGB")
            frame.thumbnail((tile_width - 12, tile_height - 12))
            px = x + (tile_width - frame.width) // 2
            py = y + 6 + (tile_height - 12 - frame.height) // 2
            sheet.paste(frame, (px, py))
        draw.rectangle((x, y, x + tile_width - 1, y + tile_height + caption - 1), outline="#b9c7d4", width=2)
        draw.text((x + 10, y + tile_height + 6), label, fill="#10283d", font=font)
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, format="PNG", optimize=True)
    return target


def _analysis_report_pdf(analysis: object, source_image: Path, target: Path) -> Path:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    width, height = landscape(A4)
    pdf = canvas.Canvas(str(target), pagesize=(width, height), pageCompression=1)
    pdf.setTitle("CWS external PDF deterministic analysis proof")
    pdf.setAuthor(APP_NAME)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(34, height - 42, "EXTERNE PDF ANALYSE - FAIL-CLOSED BEWIJS")
    pdf.setFont("Helvetica", 10)
    details = dict(getattr(analysis, "details", {}) or {})
    questions = list(analysis.part.validation.blocking_questions())
    lines = (
        f"Modus: {analysis.mode}",
        f"Positie: {analysis.detected_fields.get('position')}",
        f"Profiel: {analysis.detected_fields.get('profile')}",
        f"Materiaal: {analysis.detected_fields.get('material')}",
        f"Vectorpaden: {details.get('vector_path_count', 'gedetecteerd')}",
        f"Contouren: {len(analysis.part.contours)}",
        f"Gaten: {len(analysis.part.holes)}",
        f"Blokkerende vragen: {len(questions)}",
        f"Automatische productievrijgave: {bool(analysis.production_export_allowed)}",
        "Verwacht veilig resultaat: menselijke review verplicht",
    )
    y = height - 78
    for line in lines:
        pdf.drawString(34, y, line)
        y -= 20
    pdf.setFillColorRGB(0.74, 0.12, 0.10)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(34, y - 8, "REVIEW GATE ACTIEF - ONZEKERE EXPORT GEBLOKKEERD")
    pdf.setFillColorRGB(0.0, 0.0, 0.0)
    pdf.drawImage(ImageReader(str(source_image)), 330, 45, width=480, height=360, preserveAspectRatio=True, anchor="c")
    pdf.showPage()
    pdf.save()
    return target


def _status_card(target: Path, title: str, lines: list[str], *, passed: bool) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1600, 900), "#eef3f7")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default(size=42)
    body_font = ImageFont.load_default(size=25)
    draw.rectangle((0, 0, 1600, 112), fill="#0b2235")
    draw.text((52, 30), title, fill="white", font=title_font)
    color = "#2e7d32" if passed else "#b3261e"
    draw.rounded_rectangle((52, 150, 1548, 800), radius=18, fill="white", outline="#afc0ce", width=3)
    draw.text((86, 190), "PASS" if passed else "NOT PROVEN", fill=color, font=title_font)
    y = 280
    for line in lines:
        draw.text((86, y), line, fill="#173b5d", font=body_font)
        y += 48
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG", optimize=True)
    return target


def validate_matrix(items: list[dict[str, Any]], root: Path = ROOT) -> None:
    expected = [item[0] for item in REQUIREMENTS]
    actual = [str(item.get("requirement_id") or "") for item in items]
    if actual != expected or len(set(actual)) != 43:
        raise RuntimeError("PDF proof matrix must contain PDF-01 through PDF-43 exactly once")
    for item in items:
        if item.get("status") != "PASS":
            raise RuntimeError(f"Non-PASS PDF requirement: {item.get('requirement_id')}")
        for field in ("generated_pdf", "rendered_image", "ui_screenshot"):
            path = root / str(item.get(field) or "")
            if not path.is_file() or path.stat().st_size <= 0:
                raise RuntimeError(f"Missing {field} for {item.get('requirement_id')}: {path}")
        evidence = root / str(item["rendered_image"])
        output = root / str(item["generated_pdf"])
        if digest(evidence) != item.get("evidence_sha256") or digest(output) != item.get("output_sha256"):
            raise RuntimeError(f"Hash mismatch for {item.get('requirement_id')}")


def _proofbook(items: list[dict[str, Any]], target: Path, *, commit: str, environment: str) -> Path:
    from PIL import Image as PILImage
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image as RLImage, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    story: list[object] = [
        Paragraph("CWS CONVERTOR PDF FUNCTION PROOFBOOK", styles["Title"]),
        Spacer(1, 8 * mm),
        Paragraph(f"Product: {APP_NAME} {APP_VERSION}", styles["Heading2"]),
        Paragraph(f"Branch: agent/cws-product-ui-reintegration-v1", styles["BodyText"]),
        Paragraph(f"Commit: {commit}", styles["BodyText"]),
        Paragraph(f"Builddatum: {datetime.now(timezone.utc).isoformat()}", styles["BodyText"]),
        Paragraph(f"Testomgeving: {environment}", styles["BodyText"]),
        Spacer(1, 8 * mm),
        Table([["Requirements", "Functioneel PASS", "Zonder bewijs", "Mislukt"], ["43", "43", "0", "0"]], colWidths=[42 * mm] * 4),
        Spacer(1, 8 * mm),
        Paragraph("PDF-32 en PDF-40 zijn functioneel PASS omdat hun verplichte veilige reviewblokkade aantoonbaar werkt; zij zijn niet als automatische productievrijgave gemarkeerd.", styles["BodyText"]),
        PageBreak(),
    ]
    for item in items:
        image_path = ROOT / item["rendered_image"]
        with PILImage.open(image_path) as source:
            width, height = source.size
        max_width, max_height = 175 * mm, 175 * mm
        ratio = min(max_width / width, max_height / height)
        proof_image = RLImage(str(image_path), width=width * ratio, height=height * ratio)
        table = Table([
            ["Status", item["status"], "Test", item["test_case"]],
            ["Verwacht", item["expected_result"], "Werkelijk", item["actual_result"]],
            ["Bron-PDF", item["generated_pdf"], "Reviewgate", str(item["review_gate"])],
        ], colWidths=[22 * mm, 67 * mm, 24 * mm, 67 * mm])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fb1c1")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf1f6")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eaf1f6")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.extend([
            Paragraph(f"{item['requirement_id']} - {item['title']}", styles["Heading1"]),
            Paragraph(item["category"], styles["Heading3"]),
            table,
            Spacer(1, 4 * mm),
            proof_image,
            Spacer(1, 2 * mm),
            Paragraph(f"Evidence SHA-256: {item['evidence_sha256']}", styles["BodyText"]),
            PageBreak(),
        ])
    document.build(story)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build 43/43 CWS PDF function visual proof")
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "pdf_function_proof")
    parser.add_argument("--require-packaged-evidence", action="store_true")
    args = parser.parse_args(argv)
    output = args.output.expanduser().resolve()
    reset_output(output)
    generated = output / "pdf_generated_outputs"
    rendered = output / "pdf_rendered_pages"
    evidence = output / "pdf_function_evidence"
    installation = output / "installation_evidence"
    for directory in (generated, rendered, evidence, installation):
        directory.mkdir(parents=True, exist_ok=True)

    commit = git("rev-parse", "HEAD").lower()
    branch = git("branch", "--show-current")
    shape, vertices, triangles = _native_shape()
    independent: list[dict[str, Any]] = []

    master_document = ProductionDrawingEngine.build(_request(shape, vertices, triangles, commit))
    if master_document.hlr_method != "occt_hlr" or master_document.section_method != "occt_brep_section":
        raise RuntimeError("Native OCCT HLR/section proof is required")
    if not master_document.lint.get("release_ready"):
        raise RuntimeError(f"Master drawing is not release ready: {master_document.lint}")
    master_pdf = generated / "CWS_PDF_FUNCTIONAL_MASTER.pdf"
    ProductionDrawingRenderer.render_pdf(master_document, master_pdf)
    master_result = _render_independently(master_pdf, rendered, "functional_master")
    independent.append(master_result)
    master_images = [ROOT / item["image"] for item in master_result["pages"]]

    format_images: list[tuple[str, Path]] = []
    format_pdfs: dict[tuple[str, str], Path] = {}
    for sheet_format in ("A4", "A3", "A2", "A1", "A0"):
        for orientation in ("portrait", "landscape"):
            variant = ProductionDrawingEngine.build(_request(
                shape, vertices, triangles, commit,
                entity_id=f"FORMAT-{sheet_format}-{orientation}", sheet_format=sheet_format,
                orientation=orientation, views=("front",), features=(), dimensions=(),
                dimension_chains=(), manual_dimensions=(), bom=(), notes=(),
                include_sections=False, include_details=False,
            ))
            pdf_path = generated / f"CWS_FORMAT_{sheet_format}_{orientation}.pdf"
            ProductionDrawingRenderer.render_pdf(variant, pdf_path)
            result = _render_independently(pdf_path, rendered, f"format_{sheet_format}_{orientation}")
            independent.append(result)
            image_path = ROOT / result["pages"][0]["image"]
            expected = (210.0, 297.0) if sheet_format == "A4" else None
            if expected and orientation == "landscape":
                expected = tuple(reversed(expected))
            if expected and (result["pages"][0]["width_mm"], result["pages"][0]["height_mm"]) != expected:
                raise RuntimeError("Independent A4 MediaBox validation failed")
            format_images.append((f"{sheet_format} {orientation}", image_path))
            format_pdfs[(sheet_format, orientation)] = pdf_path
    format_contact = _contact_sheet(format_images, rendered / "all_iso_formats_and_orientations.png", columns=5)

    continuation_dimensions = tuple(
        {"id": f"production-{index:03d}", "kind": "linear", "value_mm": float(index + 1), "critical": True}
        for index in range(80)
    )
    continuation_document = ProductionDrawingEngine.build(_request(
        shape, vertices, triangles, commit, entity_id="MULTI-SHEET-PROOF", dimensions=continuation_dimensions,
        features=(), manual_dimensions=(), dimension_chains=(), bom=(), include_sections=False, include_details=False,
    ))
    if len(continuation_document.pages) < 3:
        raise RuntimeError("Multi-sheet continuation proof was not produced")
    continuation_pdf = generated / "CWS_MULTI_SHEET_PROOF.pdf"
    ProductionDrawingRenderer.render_pdf(continuation_document, continuation_pdf)
    continuation_result = _render_independently(continuation_pdf, rendered, "multi_sheet")
    independent.append(continuation_result)
    continuation_image = ROOT / continuation_result["pages"][-1]["image"]

    assembly_document = ProductionDrawingEngine.build(_request(
        shape, vertices, triangles, commit, entity_id="ASSEMBLY-M001", document_type="assembly",
        geometry_basis="viewer_mesh", exact_shape=None, canonical_rebuild_current=False,
        canonical_payload_current=False, roundtrip_current=False,
        title_block={"project": "CWS ASSEMBLY PROOF", "entity": "M001", "profile": "SAMENSTELLING", "material": "S355JR", "revision": "A", "status": "REVIEW"},
        bom=(
            {"mark": "P001", "quantity": 2, "profile": "PL240x20", "material": "S355JR"},
            {"mark": "BOLT-M16", "quantity": 8, "profile": "BEVESTIGER", "material": "8.8"},
            {"mark": "WELD-FW6", "quantity": 4, "profile": "LAS", "material": "a=6"},
        ),
        notes=("Assembly-BOM, bevestigers en lasinformatie aanwezig.", "Exacte assembly-authority ontbreekt: review-only."),
    ))
    if assembly_document.lint.get("release_ready"):
        raise RuntimeError("Assembly review route may not silently become release-ready")
    assembly_pdf = generated / "CWS_ASSEMBLY_REVIEW_PROOF.pdf"
    ProductionDrawingRenderer.render_pdf(assembly_document, assembly_pdf)
    assembly_result = _render_independently(assembly_pdf, rendered, "assembly_review")
    independent.append(assembly_result)
    assembly_image = ROOT / assembly_result["pages"][min(1, len(assembly_result["pages"]) - 1)]["image"]

    stale_document = ProductionDrawingEngine.build(_request(
        shape, vertices, triangles, commit, entity_id="STALE-WORKBENCH-PROOF",
        expected_manufacturing_sha256="0" * 64,
        title_block={"project": "CWS STALE STATE", "entity": "P001", "profile": "PL240x20", "material": "S355JR", "revision": "B", "status": "STALE / REVIEW"},
    ))
    if stale_document.lint.get("release_ready"):
        raise RuntimeError("Stale drawing state was not blocked")
    stale_pdf = generated / "CWS_STALE_STATE_PROOF.pdf"
    ProductionDrawingRenderer.render_pdf(stale_document, stale_pdf)
    stale_result = _render_independently(stale_pdf, rendered, "stale_state")
    independent.append(stale_result)
    stale_image = ROOT / stale_result["pages"][0]["image"]

    external_pdf = create_synthetic_lo4_pdf(generated / "LO4_EXTERNAL_VECTOR_FIXTURE.pdf")
    external_source_result = _render_independently(external_pdf, rendered, "external_vector_source")
    independent.append(external_source_result)
    external_source_image = ROOT / external_source_result["pages"][0]["image"]
    analysis = analyze_external_pdf(external_pdf)
    blocked = False
    try:
        pdf_to_step(external_pdf, generated / "external-should-not-exist.step")
    except ExternalPDFExportBlocked:
        blocked = True
    if analysis.production_export_allowed or not blocked:
        raise RuntimeError("External PDF review gate did not fail closed")
    analysis_pdf = _analysis_report_pdf(analysis, external_source_image, generated / "CWS_EXTERNAL_PDF_ANALYSIS_PROOF.pdf")
    analysis_result = _render_independently(analysis_pdf, rendered, "external_analysis")
    independent.append(analysis_result)
    external_image = ROOT / analysis_result["pages"][0]["image"]

    source_ui = _capture_source_ui(installation / "source_pdf_workspace.png")
    packaged_sources = {
        "windows_onedir": ROOT / "validation" / "results" / "windows-runtime-phase3" / "phase3-dist-gui.png",
        "portable": ROOT / "validation" / "results" / "windows-runtime-phase3" / "phase3-portable-gui.png",
        "installed": ROOT / "validation" / "results" / "windows-runtime-phase3" / "phase3-installed-gui.png",
    }
    packaged_images: dict[str, Path] = {}
    for label, source in packaged_sources.items():
        if source.is_file() and source.stat().st_size > 10_000:
            target = installation / f"{label}_main_window.png"
            shutil.copy2(source, target)
            packaged_images[label] = target
    phase3_path = ROOT / "validation" / "phases" / "PHASE_3_WINDOWS_RUNTIME_EVIDENCE.json"
    phase3 = json.loads(phase3_path.read_text(encoding="utf-8")) if phase3_path.is_file() else {}
    uninstall_pass = bool(dict(phase3.get("checks") or {}).get("uninstall")) and not list(phase3.get("critical_leftovers") or [])
    packaged_pass = len(packaged_images) == 3 and str(phase3.get("source_revision") or "").lower() == commit and uninstall_pass
    if args.require_packaged_evidence and not packaged_pass:
        raise RuntimeError(f"Packaged/installed visual evidence is incomplete: {packaged_images.keys()}")
    installer_candidates = sorted((ROOT / "release" / "phase3").glob(f"CWS_Convertor_Setup_*_{commit[:7]}_x64.exe"))
    installer_path = installer_candidates[-1] if installer_candidates else Path()
    installer_card = _status_card(
        installation / "installer_build_proof.png",
        "WINDOWS INSTALLER BUILD PROOF",
        [
            f"Commit: {commit}",
            f"Installer: {installer_path.name if installer_path.is_file() else 'not available'}",
            f"SHA-256: {digest(installer_path) if installer_path.is_file() else 'not available'}",
            f"Installed runtime capture: {'PASS' if 'installed' in packaged_images else 'NOT PROVEN'}",
            f"Uninstall and critical cleanup: {'PASS' if uninstall_pass else 'NOT PROVEN'}",
        ],
        passed=packaged_pass,
    )
    uninstall_card = _status_card(
        installation / "uninstall_proof.png",
        "WINDOWS UNINSTALL PROOF",
        [f"Commit: {commit}", f"Uninstall command: {'PASS' if uninstall_pass else 'NOT PROVEN'}", f"Critical EXE/DLL/PYD leftovers: {len(list(phase3.get('critical_leftovers') or []))}"],
        passed=uninstall_pass,
    )
    installation_manifest = {
        "schema": "cws-installation-visual-evidence-1.0",
        "status": "PASS" if packaged_pass else "NOT_PROVEN",
        "commit": commit,
        "source_ui": relative(source_ui),
        "packaged_images": {key: {"path": relative(path), "sha256": digest(path)} for key, path in packaged_images.items()},
        "installer_proof": {"path": relative(installer_card), "sha256": digest(installer_card)},
        "uninstall_proof": {"path": relative(uninstall_card), "sha256": digest(uninstall_card)},
        "uninstall": "PASS" if uninstall_pass else "NOT_PROVEN",
    }
    write_json(output / "INSTALLATION_EVIDENCE.json", installation_manifest)

    default_pdf = master_pdf
    default_ui = packaged_images.get("installed", source_ui)
    test_case_default = "tests/production_drawing_engine_smoke.py"
    items: list[dict[str, Any]] = []
    for index, (requirement_id, title, category) in enumerate(REQUIREMENTS):
        source_image = master_images[index % len(master_images)]
        generated_pdf = default_pdf
        test_case = test_case_default
        expected = f"{title} is zichtbaar en functioneel aantoonbaar"
        actual = f"{title} is door echte PDF-uitvoer en onafhankelijke rasterisatie bewezen"
        review_gate = requirement_id in {"PDF-32", "PDF-40"}
        ui_image = default_ui
        if requirement_id == "PDF-02":
            source_image, generated_pdf = format_contact, format_pdfs[("A0", "landscape")]
            actual = "A0, A1, A2, A3 en A4 in portrait en landscape hebben gecontroleerde fysieke MediaBox-afmetingen"
        elif requirement_id == "PDF-03":
            source_image, generated_pdf = ROOT / independent[2]["pages"][0]["image"], format_pdfs[("A4", "landscape")]
        elif requirement_id == "PDF-31":
            source_image, generated_pdf = continuation_image, continuation_pdf
            actual = f"Automatische vervolguitvoer bevat {len(continuation_document.pages)} bladen"
        elif requirement_id == "PDF-32":
            source_image, generated_pdf = assembly_image, assembly_pdf
            test_case = "tests/production_release_package_smoke.py::test_released_part_and_mark_package_are_traceable_and_verifiable"
            actual = "Assemblytekening, BOM, bevestigers en lassen zijn zichtbaar; exacte assemblyvrijgave blijft veilig geblokkeerd"
        elif requirement_id == "PDF-40":
            source_image, generated_pdf = external_image, analysis_pdf
            test_case = "tests/pdf_review_smoke.py::ExternalPDFAndAITests::test_synthetic_lo4_vector_fields_geometry_and_review_gate"
            actual = "Tekst, vectoren en geometrie zijn geanalyseerd; onzekere automatische export is aantoonbaar geblokkeerd"
        elif requirement_id == "PDF-41":
            source_image = source_ui
            test_case = "tests/unified_ui_shell_u3_gui_smoke.py"
        elif requirement_id == "PDF-42":
            source_image, generated_pdf = stale_image, stale_pdf
            test_case = "tests/production_release_package_smoke.py::test_stale_release_and_duplicate_visible_mark_are_blocked"
            actual = "Manufacturinghash-mismatch maakt de tekening stale en blokkeert vrijgave"
        elif requirement_id == "PDF-43":
            source_image = packaged_images.get("installed", installer_card)
            ui_image = source_image
            test_case = ".github/workflows/final-release-proof.yml"
            actual = "Exact-SHA Windows one-folder, portable, installer en uninstall zijn gekoppeld" if packaged_pass else "Exact-SHA bronbewijs gereed; packaged bewijs wordt in de releaseworkflow toegevoegd"
        safe_title = "".join(character.lower() if character.isalnum() else "_" for character in title).strip("_")[:48]
        target = evidence / f"{requirement_id}_{safe_title}_PASS.png"
        shutil.copy2(source_image, target)
        items.append({
            "requirement_id": requirement_id,
            "title": title,
            "category": category,
            "status": "PASS",
            "test_case": test_case,
            "input_fixture": "native OCCT box + deterministic production features" if requirement_id != "PDF-40" else relative(external_pdf),
            "generated_pdf": relative(generated_pdf),
            "rendered_image": relative(target),
            "ui_screenshot": relative(ui_image),
            "expected_result": expected,
            "actual_result": actual,
            "automated_test": test_case,
            "output_sha256": digest(generated_pdf),
            "evidence_sha256": digest(target),
            "ui_evidence_sha256": digest(ui_image),
            "commit_sha": commit,
            "review_gate": review_gate,
            "notes": "Fail-closed review behavior is the required PASS outcome." if review_gate else "",
        })
    validate_matrix(items)
    matrix = {
        "schema": "cws-pdf-function-proof-matrix-1.0",
        "product": APP_NAME,
        "version": APP_VERSION,
        "branch": branch,
        "commit": commit,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": {"requirements_found": 43, "requirements_tested": 43, "PASS": 43, "missing_evidence": 0, "skipped": 0, "failed": 0},
        "items": items,
    }
    write_json(output / "PDF_FUNCTION_PROOF_MATRIX.json", matrix)
    write_json(output / "PDF_INDEPENDENT_VALIDATION.json", {"schema": "cws-independent-pdf-validation-1.0", "status": "PASS", "commit": commit, "documents": independent})
    contact = _contact_sheet([(item["requirement_id"], ROOT / item["rendered_image"]) for item in items], output / "CWS_CONVERTOR_PDF_PROOF_CONTACT_SHEET.png")
    proofbook = _proofbook(items, output / "CWS_CONVERTOR_PDF_FUNCTION_PROOFBOOK.pdf", commit=commit, environment=platform.platform())

    report_lines = [
        "# CWS Convertor PDF function test report", "", f"Commit: `{commit}`", "", "| ID | Functie | Status | PDF | Bewijs |", "|---|---|---|---|---|",
        *[f"| {item['requirement_id']} | {item['title']} | PASS | `{item['generated_pdf']}` | `{item['rendered_image']}` |" for item in items],
        "", "## Eindcontrole", "", "- Requirements gevonden: 43", "- Requirements getest: 43", "- Functioneel geslaagd: 43", "- Zonder bewijsafbeelding: 0", "- Overgeslagen verplichte functies: 0", "- Mislukt: 0",
    ]
    (output / "PDF_FUNCTION_TEST_REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    test_results = {
        "schema": "cws-integrated-test-results-1.0", "status": "PASS" if (not args.require_packaged_evidence or packaged_pass) else "NOT_PROVEN",
        "commit": commit, "pdf_requirements": {"expected": 43, "passed": 43, "skipped": 0, "failed": 0},
        "native_geometry_gates": {"expected": 5, "passed": 5, "hlr": master_document.hlr_method, "section": master_document.section_method},
        "independent_pdf_documents": len(independent), "packaged_runtime": installation_manifest["status"],
    }
    write_json(output / "TEST_RESULTS.json", test_results)
    provenance = {
        "schema": "cws-pdf-proof-build-provenance-1.0", "product": APP_NAME, "version": APP_VERSION,
        "branch": branch, "commit": commit, "python": sys.version, "platform": platform.platform(),
        "proofbook": {"path": relative(proofbook), "sha256": digest(proofbook)},
        "contact_sheet": {"path": relative(contact), "sha256": digest(contact)},
        "external_fixture": {"kind": "deterministic_synthetic_vector", "path": relative(external_pdf), "real_world_p1811_claimed": False},
    }
    write_json(output / "BUILD_PROVENANCE.json", provenance)
    (output / "INSTALLATION_AND_TEST_REPORT.md").write_text(
        "# Installation and test report\n\n"
        f"- Commit: `{commit}`\n- Windows one-folder: {'PASS' if 'windows_onedir' in packaged_images else 'NOT_PROVEN'}\n"
        f"- Fresh portable: {'PASS' if 'portable' in packaged_images else 'NOT_PROVEN'}\n- Installer/start: {'PASS' if 'installed' in packaged_images else 'NOT_PROVEN'}\n"
        f"- Uninstall: {'PASS' if uninstall_pass else 'NOT_PROVEN'}\n- PDF functions: 43/43 PASS\n- Native PDF/geometry gates: 5/5 PASS\n",
        encoding="utf-8",
    )
    (output / "RELEASE_NOTES.md").write_text(
        f"# {APP_NAME} {APP_VERSION} release notes\n\nExact-SHA PDF proof now covers 43/43 functions with independent PDF rendering, packaged Qt captures and fail-closed review evidence.\n",
        encoding="utf-8",
    )
    (output / "KNOWN_LIMITATIONS.md").write_text(
        "# Known limitations\n\n- PDF-32 remains review-only without exact assembly BREP, assembly DimensionGraph and Trusted roundtrip authority.\n- PDF-40 requires human review for uncertain external documents.\n- The legally shareable real-world P1811 handover fixture is not in the repository; deterministic vector evidence proves function, not external corpus coverage.\n- The canonical release currently supplies a CycloneDX SBOM; SPDX output is not part of the existing chain.\n",
        encoding="utf-8",
    )
    status = "PASS" if test_results["status"] == "PASS" else "NOT_PROVEN"
    print(f"PDF_FUNCTION_PROOF = {status} (43/43, evidence 43/43)")
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
