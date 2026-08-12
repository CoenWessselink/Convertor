"""Bidirectionele technische PDF-laag met Trusted Converter PDF.

Belangrijkste veiligheidsgrenzen:
- converter-eigen PDF's dragen een gehashte canonieke JSON-bijlage;
- zichtbare tekeninhoud wordt afzonderlijk gerenderd en gehasht;
- externe PDF's leveren uitsluitend een reviewmodel totdat geometrie en
  kritische velden deterministisch zijn bevestigd;
- AI mag semantische voorstellen leveren, maar schrijft nooit productiecode.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import html
import json
import math
import re
import tempfile
from typing import Any, Iterable

import cadquery as cq
import fitz  # PyMuPDF

from ai_support import AIInterpretation, AIProvider, LocalSemanticProvider
from canonical_model import (
    CanonicalContour,
    CanonicalContourPoint,
    CanonicalDrawing,
    CanonicalFieldValue,
    CanonicalHeader,
    CanonicalHole,
    CanonicalPart,
    CanonicalPayloadError,
    CanonicalQuestion,
    CanonicalValidation,
    canonical_from_nc1_part,
    canonical_sha256,
    geometry_sha256,
    production_export_allowed,
    sha256_bytes,
    sha256_file,
)
from drawing_templates import DrawingTemplate, MM_TO_PT, SHEET_SIZES_MM, load_template

TRUSTED_PDF_ATTACHMENT = "converter-model.json"
TRUSTED_PDF_FORMAT = "nc1-step-ifc-converter/trusted-pdf"
TRUSTED_PDF_MANIFEST_VERSION = "1.0"
XMP_NAMESPACE = "https://local.nc1-step-ifc-converter/schema/trusted-pdf/1.0/"
VISIBLE_RENDER_DPI = 144


class PDFError(RuntimeError):
    pass


class PDFProductionBlockedError(PDFError):
    def __init__(self, message: str, reasons: Iterable[str] = ()) -> None:
        self.reasons = [str(item) for item in reasons]
        suffix = "" if not self.reasons else "\n- " + "\n- ".join(self.reasons)
        super().__init__(message + suffix)


@dataclass
class PDFInspection:
    source: Path
    classification: str
    trusted_exact: bool
    part: CanonicalPart | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "classification": self.classification,
            "trusted_exact": self.trusted_exact,
            "warnings": self.warnings,
            "errors": self.errors,
            "details": self.details,
            "part": self.part.to_dict() if self.part else None,
        }


@dataclass
class PDFAnalysisResult:
    source: Path
    part: CanonicalPart
    page_results: list[dict[str, Any]]
    extracted_text: str
    ai: AIInterpretation | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "page_results": self.page_results,
            "extracted_text": self.extracted_text,
            "warnings": self.warnings,
            "ai": self.ai.to_dict() if self.ai else None,
            "part": self.part.to_dict(),
        }


@dataclass
class PDFConversionResult:
    source: Path
    outputs: list[Path]
    classification: str
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def primary_output(self) -> Path | None:
        return self.outputs[0] if self.outputs else None


# ---------------------------------------------------------------------------
# PDF hashing / attachments / XMP
# ---------------------------------------------------------------------------


def _visible_hash_document(document: fitz.Document, dpi: int = VISIBLE_RENDER_DPI) -> str:
    digest = hashlib.sha256()
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    digest.update(f"pages:{document.page_count};dpi:{dpi};".encode("ascii"))
    for index in range(document.page_count):
        page = document.load_page(index)
        digest.update(
            f"page:{index};rect:{page.rect.width:.6f},{page.rect.height:.6f};".encode("ascii")
        )
        pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY, alpha=False, annots=True)
        digest.update(pixmap.samples)
    return digest.hexdigest()


def visible_pdf_sha256(path: str | Path, dpi: int = VISIBLE_RENDER_DPI) -> str:
    with fitz.open(path) as document:
        return _visible_hash_document(document, dpi=dpi)


def render_pdf_pages(path: str | Path, *, dpi: int = 160, max_pages: int = 8) -> list[bytes]:
    images: list[bytes] = []
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    with fitz.open(path) as document:
        for index in range(min(document.page_count, max_pages)):
            page = document.load_page(index)
            pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False, annots=True)
            images.append(pixmap.tobytes("png"))
    return images


def _xmp_packet(manifest: dict[str, Any]) -> str:
    values = {
        "schemaVersion": manifest["schema_version"],
        "manifestVersion": manifest["manifest_version"],
        "partId": manifest["part_id"],
        "canonicalSHA256": manifest["canonical_sha256"],
        "geometrySHA256": manifest["geometry_sha256"],
        "visibleDrawingSHA256": manifest["visible_drawing_sha256"],
        "sourceSHA256": manifest.get("source_sha256", ""),
        "softwareVersion": manifest["software_version"],
    }
    props = "\n".join(
        f"      <conv:{key}>{html.escape(str(value))}</conv:{key}>" for key, value in values.items()
    )
    return f"""<?xpacket begin='\ufeff' id='W5M0MpCehiHzreSzNTczkc9d'?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
  <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
    <rdf:Description rdf:about='' xmlns:conv='{XMP_NAMESPACE}'>
{props}
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""


def _xmp_value(xml: str, key: str) -> str:
    match = re.search(rf"<conv:{re.escape(key)}>(.*?)</conv:{re.escape(key)}>", xml, re.DOTALL)
    return html.unescape(match.group(1).strip()) if match else ""


def _manifest_for_part(part: CanonicalPart, visible_hash: str, software_version: str) -> dict[str, Any]:
    part = part.clone()
    part.converter_version = software_version
    part.drawing.visible_drawing_sha256 = visible_hash
    # Validate before hashing: a production part with open blocking questions is invalid by design.
    part.validate()
    return {
        "format": TRUSTED_PDF_FORMAT,
        "manifest_version": TRUSTED_PDF_MANIFEST_VERSION,
        "software_version": software_version,
        "schema_version": part.schema_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "part_id": part.part_id,
        "source_format": part.source_format,
        "source_file": part.source_file,
        "source_sha256": part.source_sha256,
        "canonical_sha256": canonical_sha256(part),
        "geometry_sha256": geometry_sha256(part),
        "visible_drawing_sha256": visible_hash,
        "visible_hash_method": f"grayscale-render-{VISIBLE_RENDER_DPI}dpi-v1",
        "profile_id": part.header.profile,
        "material_id": part.header.material,
        "units": "mm",
        "features": {
            "contours": len(part.contours),
            "holes": len(part.holes),
            "profile_type": part.header.profile_type,
        },
        "canonical_model": part.to_dict(),
    }


def _add_embedded_files(document: fitz.Document, manifest: dict[str, Any]) -> None:
    raw = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    document.embfile_add(
        TRUSTED_PDF_ATTACHMENT,
        raw,
        filename=TRUSTED_PDF_ATTACHMENT,
        ufilename=TRUSTED_PDF_ATTACHMENT,
        desc="Exact canoniek productiemodel met checksums",
    )
    part = CanonicalPart.from_dict(manifest["canonical_model"])
    source_key = {"NC1": "nc1", "DSTV": "nc1", "STEP": "step", "STP": "step", "IFC": "ifc"}.get(
        part.source_format.upper()
    )
    if source_key and part.attachment(source_key):
        attachment = part.attachment(source_key)
        assert attachment is not None
        embedded_name = f"source-{attachment.name}"
        if embedded_name not in document.embfile_names():
            document.embfile_add(
                embedded_name,
                attachment.bytes(),
                filename=attachment.name,
                ufilename=attachment.name,
                desc="Origineel bronbestand van Trusted Converter PDF",
            )
    document.set_xml_metadata(_xmp_packet(manifest))


# ---------------------------------------------------------------------------
# Canonicalisatie van bestaande formaten
# ---------------------------------------------------------------------------


def _shape_metrics(shape: cq.Shape) -> dict[str, Any]:
    box = shape.BoundingBox()
    return {
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
        "solids": len(shape.Solids()),
    }


def canonicalize_nc1(path: str | Path) -> tuple[CanonicalPart, cq.Shape]:
    import converter as core
    from conversion import __version__, build_shape

    source = Path(path)
    part = core.parse_nc1(source)
    shape = build_shape(part).val()
    canonical = canonical_from_nc1_part(
        part,
        source_bytes=source.read_bytes(),
        converter_version=__version__,
        geometry=_shape_metrics(shape),
        recognition={"method": "native NC1 parser", "confidence": 1.0, "production_nc1_allowed": True},
    )
    canonical.imported_at = datetime.now(timezone.utc).isoformat()
    canonical.drawing = CanonicalDrawing(status="released", scale="auto")
    canonical.validation = CanonicalValidation(
        export_status="validated",
        production_export_allowed=True,
        geometric_comparison={"source": "native NC1 build"},
    )
    return canonical, shape


def _minimal_step_part(source: Path, shape: cq.Shape, warning: str) -> CanonicalPart:
    from conversion import __version__

    box = shape.BoundingBox()
    dimensions = sorted([float(box.xlen), float(box.ylen), float(box.zlen)], reverse=True)
    part = CanonicalPart(
        converter_version=__version__,
        source_format="STEP",
        source_file=source.name,
        source_sha256=sha256_file(source),
        part_id=source.stem,
        imported_at=datetime.now(timezone.utc).isoformat(),
        import_method="exact-solid-unclassified",
        header=CanonicalHeader(
            part_number=source.stem,
            position_number=source.stem,
            length=dimensions[0],
            dim1=dimensions[1],
            dim2=dimensions[2],
            thickness=dimensions[2],
            quantity=1,
        ),
        geometry=_shape_metrics(shape),
        warnings=[warning],
        recognition={"method": "unclassified analytic STEP", "confidence": 0.0},
        validation=CanonicalValidation(
            errors=["STEP-solid is nog niet als veilig productieprofiel of plaat geclassificeerd"],
            export_status="review-required",
            production_export_allowed=False,
        ),
    )
    part.add_attachment("step", source.name, "model/step", source.read_bytes())
    return part


def canonicalize_step(path: str | Path, *, material: str = "S355JR") -> tuple[CanonicalPart, cq.Shape]:
    from canonical_model import extract_part_from_step, extract_part_from_nc1
    from conversion import __version__, step_to_nc1
    from profile_database import ProfileDatabase

    source = Path(path)
    shape = cq.importers.importStep(str(source)).val()
    existing = extract_part_from_step(source, strict=False)
    if existing is not None:
        existing = existing.clone()
        existing.converter_version = __version__
        if existing.attachment("step") is None:
            existing.add_attachment("step", source.name, "model/step", source.read_bytes())
        if existing.validation.production_export_allowed:
            existing.drawing.status = "released"
            existing.validation.export_status = "validated"
        return existing, shape

    try:
        with tempfile.TemporaryDirectory(prefix="step_pdf_canonical_") as folder:
            nc1_path = Path(folder) / f"{source.stem}.nc1"
            result = step_to_nc1(
                source,
                nc1_path,
                material=material,
                profile_database=ProfileDatabase(),
                strict_validation=True,
                embed_converter_payload=True,
            )
            canonical = extract_part_from_nc1(nc1_path, strict=True)
            if canonical is None:
                raise CanonicalPayloadError("STEP->NC1 leverde geen canoniek model")
            canonical = canonical.clone()
            canonical.converter_version = __version__
            canonical.source_format = "STEP"
            canonical.source_file = source.name
            canonical.source_sha256 = sha256_file(source)
            canonical.import_method = "exact-solid-profile-recognition"
            canonical.add_attachment("step", source.name, "model/step", source.read_bytes())
            canonical.recognition.update(
                {
                    "method": result.matched_by,
                    "confidence": float(result.confidence),
                    "production_nc1_allowed": True,
                }
            )
            canonical.validation = CanonicalValidation(
                export_status="validated",
                production_export_allowed=True,
                geometric_comparison={"volume_delta_percent": result.volume_delta_percent},
            )
            canonical.drawing.status = "released"
            return canonical, shape
    except Exception as exc:
        return _minimal_step_part(source, shape, f"Veilige STEP-classificatie niet afgerond: {exc}"), shape


def canonicalize_ifc(path: str | Path) -> list[tuple[CanonicalPart, cq.Shape]]:
    from canonical_model import extract_part_from_ifc
    from ifc_support import load_ifc_geometry, mesh_to_cq_shape
    from conversion import __version__

    source = Path(path)
    payload = extract_part_from_ifc(source, strict=False)
    if payload is not None:
        payload = payload.clone()
        payload.converter_version = __version__
        step_bytes = payload.attachment_bytes("step")
        if step_bytes:
            with tempfile.TemporaryDirectory(prefix="ifc_pdf_step_") as folder:
                step_path = Path(folder) / "payload.step"
                step_path.write_bytes(step_bytes)
                return [(payload, cq.importers.importStep(str(step_path)).val())]
        nc1_bytes = payload.attachment_bytes("nc1")
        if nc1_bytes:
            with tempfile.TemporaryDirectory(prefix="ifc_pdf_nc1_") as folder:
                nc1_path = Path(folder) / "payload.nc1"
                nc1_path.write_bytes(nc1_bytes)
                _part, shape = canonicalize_nc1(nc1_path)
                return [(payload, shape)]

    model = load_ifc_geometry(source)
    results: list[tuple[CanonicalPart, cq.Shape]] = []
    for index, item in enumerate(model.items, start=1):
        shape = mesh_to_cq_shape(item.vertices_mm, item.triangles, make_solid=True)
        bbox = sorted([float(v) for v in item.bbox_mm], reverse=True)
        part = CanonicalPart(
            converter_version=__version__,
            source_format="IFC",
            source_file=source.name,
            source_sha256=sha256_file(source),
            part_id=item.tag or item.name or f"element_{index:03d}",
            imported_at=datetime.now(timezone.utc).isoformat(),
            import_method=f"external-ifc-{model.reader}",
            header=CanonicalHeader(
                part_number=item.tag or item.name or f"element_{index:03d}",
                position_number=item.tag or item.name or f"element_{index:03d}",
                material=item.material_name,
                quantity=1,
                length=bbox[0] if bbox else 0.0,
                dim1=bbox[1] if len(bbox) > 1 else 0.0,
                dim2=bbox[2] if len(bbox) > 2 else 0.0,
                thickness=bbox[2] if len(bbox) > 2 else 0.0,
            ),
            geometry=_shape_metrics(shape),
            properties={"ifc_guid": item.guid, "ifc_class": item.ifc_class, **item.properties},
            recognition={"method": "external IFC geometry", "confidence": 0.0},
            validation=CanonicalValidation(
                errors=["Extern IFC-element mist geverifieerde converterpayload"],
                export_status="review-required",
                production_export_allowed=False,
            ),
        )
        results.append((part, shape))
    return results


# ---------------------------------------------------------------------------
# Vectoriële werktekening
# ---------------------------------------------------------------------------


def _fmt(value: float, decimals: int = 1) -> str:
    rounded = round(float(value), decimals)
    if abs(rounded - round(rounded)) < 10 ** (-(decimals + 1)):
        return str(int(round(rounded)))
    return f"{rounded:.{decimals}f}".replace(".", ",")


def _first_contour(part: CanonicalPart) -> CanonicalContour | None:
    for face in ("v", "o", "u", "h"):
        for contour in part.contours:
            if contour.face == face and contour.kind == "AK" and len(contour.points) >= 3:
                return contour
    return next((item for item in part.contours if len(item.points) >= 3), None)


def _model_2d(part: CanonicalPart) -> tuple[list[tuple[float, float]], list[CanonicalHole], float, float]:
    contour = _first_contour(part)
    if contour is not None:
        points = [(float(item.x), float(item.q)) for item in contour.points]
        if points and points[0] == points[-1]:
            points = points[:-1]
    else:
        draft = part.geometry.get("draft_contour_mm") or []
        points = [(float(item[0]), float(item[1])) for item in draft if len(item) >= 2]
    if len(points) < 3:
        length = float(part.header.length or 0.0)
        width = float(part.header.dim1 or 0.0)
        if length <= 0 or width <= 0:
            bbox = [float(v) for v in part.geometry.get("bbox_mm") or []]
            bbox = sorted(bbox, reverse=True)
            length = length or (bbox[0] if bbox else 100.0)
            width = width or (bbox[1] if len(bbox) > 1 else 50.0)
        points = [(0.0, 0.0), (length, 0.0), (length, width), (0.0, width)]
    xs = [value[0] for value in points]
    ys = [value[1] for value in points]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    face = contour.face if contour else "v"
    holes = [item for item in part.holes if not item.face or item.face == face]
    return points, holes, max(width, 1e-6), max(height, 1e-6)


def _draw_line(page: fitz.Page, p1: tuple[float, float], p2: tuple[float, float], width_pt: float = 0.6, dashes: str | None = None) -> None:
    page.draw_line(fitz.Point(*p1), fitz.Point(*p2), color=(0, 0, 0), width=width_pt, dashes=dashes)


def _select_standard_scale(max_pt_per_mm: float) -> tuple[float, str]:
    """Kies de grootste gangbare tekenschaal die binnen de beschikbare ruimte past.

    De factor is bladmaat / modelmaat. Een factor 0.5 betekent dus 1:2 en
    een factor 2.0 betekent 2:1. De geometrie wordt met exact dezelfde factor
    getekend als in het titelblok wordt gerapporteerd.
    """

    if not math.isfinite(max_pt_per_mm) or max_pt_per_mm <= 0:
        raise ValueError("Ongeldige beschikbare tekenschaal")
    max_factor = max_pt_per_mm / MM_TO_PT
    standards: tuple[tuple[float, str], ...] = (
        (10.0, "10:1"),
        (5.0, "5:1"),
        (2.0, "2:1"),
        (1.0, "1:1"),
        (0.5, "1:2"),
        (0.4, "1:2,5"),
        (0.2, "1:5"),
        (0.1, "1:10"),
        (0.05, "1:20"),
        (0.02, "1:50"),
        (0.01, "1:100"),
    )
    for factor, label in standards:
        if factor <= max_factor + 1e-9:
            return factor * MM_TO_PT, label

    denominator = max(100, int(math.ceil(1.0 / max_factor / 10.0) * 10))
    return MM_TO_PT / denominator, f"1:{denominator}"


def _draw_dimension(
    page: fitz.Page,
    p1: tuple[float, float],
    p2: tuple[float, float],
    offset: float,
    text: str,
    *,
    horizontal: bool,
    font_size: float,
) -> None:
    tick = 3.0
    if horizontal:
        y = p1[1] + offset
        _draw_line(page, p1, (p1[0], y), 0.35)
        _draw_line(page, p2, (p2[0], y), 0.35)
        _draw_line(page, (p1[0], y), (p2[0], y), 0.45)
        for x in (p1[0], p2[0]):
            _draw_line(page, (x - tick, y + tick), (x + tick, y - tick), 0.45)
        left, right = min(p1[0], p2[0]), max(p1[0], p2[0])
        text_width = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
        text_x = max(left + 1.0, (left + right - text_width) / 2.0)
        text_x = min(text_x, right - text_width - 1.0)
        baseline_y = y - 2.0
        background = fitz.Rect(
            text_x - 2.0,
            baseline_y - font_size - 1.5,
            text_x + text_width + 2.0,
            baseline_y + 1.5,
        )
        page.draw_rect(background, color=None, fill=(1, 1, 1), overlay=True)
        page.insert_text(
            fitz.Point(text_x, baseline_y),
            text,
            fontsize=font_size,
            fontname="helv",
            overlay=True,
        )
    else:
        x = p1[0] + offset
        _draw_line(page, p1, (x, p1[1]), 0.35)
        _draw_line(page, p2, (x, p2[1]), 0.35)
        _draw_line(page, (x, p1[1]), (x, p2[1]), 0.45)
        for y in (p1[1], p2[1]):
            _draw_line(page, (x - tick, y + tick), (x + tick, y - tick), 0.45)
        midpoint = (p1[1] + p2[1]) / 2.0
        page.insert_text(fitz.Point(x + 3, midpoint + font_size / 3), text, fontsize=font_size, fontname="helv", rotate=90)


def _draw_profile_end(page: fitz.Page, rect: fitz.Rect, profile_type: str) -> None:
    profile_type = (profile_type or "").upper()
    if profile_type == "I":
        flange = rect.height * 0.18
        web = rect.width * 0.18
        page.draw_rect(fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + flange), color=(0, 0, 0), width=0.7)
        page.draw_rect(fitz.Rect(rect.x0, rect.y1 - flange, rect.x1, rect.y1), color=(0, 0, 0), width=0.7)
        page.draw_rect(fitz.Rect(rect.x0 + (rect.width - web) / 2, rect.y0 + flange, rect.x0 + (rect.width + web) / 2, rect.y1 - flange), color=(0, 0, 0), width=0.7)
    elif profile_type in {"RU", "RO"}:
        page.draw_circle(rect.tl + (rect.width / 2, rect.height / 2), min(rect.width, rect.height) / 2, color=(0, 0, 0), width=0.7)
        if profile_type == "RO":
            page.draw_circle(rect.tl + (rect.width / 2, rect.height / 2), min(rect.width, rect.height) * 0.36, color=(0, 0, 0), width=0.5)
    else:
        page.draw_rect(rect, color=(0, 0, 0), width=0.7)


def _draw_technical_page(page: fitz.Page, part: CanonicalPart, template: DrawingTemplate) -> dict[str, Any]:
    width_pt, height_pt = page.rect.width, page.rect.height
    margin = template.margin_mm * MM_TO_PT
    title_h = template.title_block_height_mm * MM_TO_PT
    table_h = template.parts_table_height_mm * MM_TO_PT
    font = max(6.5, template.normal_text_height_mm * MM_TO_PT)
    dim_font = max(7.0, template.dimension_text_height_mm * MM_TO_PT)
    title_font = max(9.0, template.title_text_height_mm * MM_TO_PT)

    page.draw_rect(fitz.Rect(margin, margin, width_pt - margin, height_pt - margin), color=(0, 0, 0), width=0.7)
    drawing_bottom = height_pt - margin - title_h - table_h - 8
    drawing_rect = fitz.Rect(margin + 20, margin + 20, width_pt - margin - 80, drawing_bottom - 20)

    points, holes, model_w, model_h = _model_2d(part)
    left_pad, right_pad, top_pad, bottom_pad = 25.0, 25.0, 25.0, 35.0
    fit_w = max(10.0, drawing_rect.width - left_pad - right_pad)
    fit_h = max(10.0, drawing_rect.height - top_pad - bottom_pad)
    max_scale_pt_per_mm = min(fit_w / model_w, fit_h / model_h)
    # Use a reproducible standard scale. This keeps the title block and the
    # actual vector geometry technically consistent.
    scale_pt_per_mm, reported_scale = _select_standard_scale(max_scale_pt_per_mm)
    x0 = drawing_rect.x0 + left_pad + (fit_w - model_w * scale_pt_per_mm) / 2
    y0 = drawing_rect.y0 + top_pad + (fit_h - model_h * scale_pt_per_mm) / 2
    min_x = min(x for x, _ in points)
    min_y = min(y for _, y in points)

    def map_point(point: tuple[float, float]) -> tuple[float, float]:
        x, y = point
        return x0 + (x - min_x) * scale_pt_per_mm, y0 + (model_h - (y - min_y)) * scale_pt_per_mm

    mapped = [map_point(point) for point in points]
    for first, second in zip(mapped, mapped[1:] + mapped[:1]):
        _draw_line(page, first, second, max(0.55, template.line_width_mm * MM_TO_PT))

    for hole in holes:
        center = map_point((hole.x, hole.q))
        radius = max(1.0, hole.diameter / 2.0 * scale_pt_per_mm)
        page.draw_circle(fitz.Point(*center), radius, color=(0, 0, 0), width=0.65)
        _draw_line(page, (center[0] - radius - 3, center[1]), (center[0] + radius + 3, center[1]), 0.3, "[2 2]")
        _draw_line(page, (center[0], center[1] - radius - 3), (center[0], center[1] + radius + 3), 0.3, "[2 2]")

    bbox_x0, bbox_x1 = min(x for x, _ in mapped), max(x for x, _ in mapped)
    bbox_y0, bbox_y1 = min(y for _, y in mapped), max(y for _, y in mapped)
    _draw_dimension(
        page,
        (bbox_x0, bbox_y1),
        (bbox_x1, bbox_y1),
        22.0,
        _fmt(model_w, template.decimal_places),
        horizontal=True,
        font_size=dim_font,
    )
    _draw_dimension(
        page,
        (bbox_x0, bbox_y0),
        (bbox_x0, bbox_y1),
        -22.0,
        _fmt(model_h, template.decimal_places),
        horizontal=False,
        font_size=dim_font,
    )

    if holes:
        grouped: dict[float, int] = {}
        for hole in holes:
            grouped[round(hole.diameter, 3)] = grouped.get(round(hole.diameter, 3), 0) + 1
        callouts = ", ".join(f"{count}x Ø{_fmt(diameter, template.decimal_places)}" for diameter, count in sorted(grouped.items()))
        page.insert_text(fitz.Point(bbox_x1 + 8, bbox_y0 + 12), callouts, fontsize=font, fontname="helv")

    radius_values = sorted({round(point.radius, 3) for contour in part.contours for point in contour.points if point.radius > 0})
    if radius_values:
        page.insert_text(
            fitz.Point(bbox_x1 + 8, bbox_y0 + 26),
            ", ".join(f"R {_fmt(value, template.decimal_places)}" for value in radius_values),
            fontsize=font,
            fontname="helv",
        )

    # Side/end view: thickness or generic profile section.
    side_rect = fitz.Rect(width_pt - margin - 62, margin + 50, width_pt - margin - 24, margin + 110)
    _draw_profile_end(page, side_rect, part.header.profile_type)
    thickness = part.header.thickness or min(
        [value for value in (part.header.dim2, part.header.dim3, part.header.dim4) if value > 0] or [0.0]
    )
    label = f"t={_fmt(thickness, template.decimal_places)}" if thickness > 0 else "Doorsnede"
    page.insert_textbox(fitz.Rect(side_rect.x0 - 6, side_rect.y1 + 4, side_rect.x1 + 6, side_rect.y1 + 18), label, fontsize=font, fontname="helv", align=fitz.TEXT_ALIGN_CENTER)

    # Parts row.
    table_top = height_pt - margin - title_h - table_h
    table_rect = fitz.Rect(margin, table_top, width_pt - margin, table_top + table_h)
    page.draw_rect(table_rect, color=(0, 0, 0), width=0.6)
    columns = [
        ("Pos", 0.10),
        ("Profiel", 0.25),
        ("Materiaal", 0.16),
        ("Lengte", 0.13),
        ("Aantal", 0.10),
        ("Merk", 0.26),
    ]
    x = table_rect.x0
    values = [
        part.header.position_number or part.header.part_number or part.part_id,
        part.header.profile,
        part.header.material,
        _fmt(part.header.length or model_w, template.decimal_places),
        str(part.header.quantity or 1),
        part.header.mark or part.header.position_number or part.header.part_number or part.part_id,
    ]
    for index, ((heading, fraction), value) in enumerate(zip(columns, values)):
        next_x = table_rect.x1 if index == len(columns) - 1 else x + table_rect.width * fraction
        if index:
            _draw_line(page, (x, table_rect.y0), (x, table_rect.y1), 0.4)
        mid_y = table_rect.y0 + table_rect.height * 0.42
        _draw_line(page, (x, mid_y), (next_x, mid_y), 0.35)
        page.insert_textbox(fitz.Rect(x + 2, table_rect.y0 + 1, next_x - 2, mid_y - 1), heading, fontsize=font * 0.82, fontname="helv", align=fitz.TEXT_ALIGN_CENTER)
        page.insert_textbox(fitz.Rect(x + 2, mid_y + 1, next_x - 2, table_rect.y1 - 1), str(value), fontsize=font * 0.92, fontname="helv", align=fitz.TEXT_ALIGN_CENTER)
        x = next_x

    # Title block.
    title_rect = fitz.Rect(margin, height_pt - margin - title_h, width_pt - margin, height_pt - margin)
    page.draw_rect(title_rect, color=(0, 0, 0), width=0.7)
    split = title_rect.x0 + title_rect.width * 0.62
    _draw_line(page, (split, title_rect.y0), (split, title_rect.y1), 0.5)
    right_mid = title_rect.y0 + title_rect.height * 0.52
    _draw_line(page, (split, right_mid), (title_rect.x1, right_mid), 0.4)

    title_data = dict(template.title_block_defaults)
    title_data.update(part.drawing.title_block)
    subject = title_data.get("subject") or part.header.part_name or template.default_subject
    company = template.company_name or ""
    page.insert_textbox(fitz.Rect(title_rect.x0 + 5, title_rect.y0 + 4, split - 5, title_rect.y0 + 22), company, fontsize=title_font, fontname="helv")
    page.insert_textbox(fitz.Rect(title_rect.x0 + 5, title_rect.y0 + 22, split - 5, title_rect.y0 + 42), str(subject), fontsize=title_font * 0.9, fontname="helv")
    project = title_data.get("project") or part.header.project_number
    page.insert_textbox(fitz.Rect(title_rect.x0 + 5, title_rect.y0 + 43, split - 5, title_rect.y1 - 4), f"Project: {project}\nBron: {part.source_file}", fontsize=font * 0.82, fontname="helv")

    right_lines = [
        f"Tekening: {part.header.drawing_number or part.part_id}",
        f"Positie: {part.header.position_number or part.part_id}",
        f"Schaal: {reported_scale}",
        f"Formaat: {template.sheet_format}",
    ]
    page.insert_textbox(fitz.Rect(split + 5, title_rect.y0 + 4, title_rect.x1 - 5, right_mid - 3), "\n".join(right_lines), fontsize=font * 0.82, fontname="helv")
    status = (part.drawing.status or template.default_status).upper()
    bottom_lines = [
        f"Status: {status}",
        f"Datum: {datetime.now().date().isoformat()}",
        f"Aantal: {part.header.quantity or 1}",
    ]
    page.insert_textbox(fitz.Rect(split + 5, right_mid + 3, title_rect.x1 - 5, title_rect.y1 - 3), "\n".join(bottom_lines), fontsize=font * 0.82, fontname="helv")

    if status not in {"VRIJGEGEVEN", "RELEASED", "VALIDATED"} or not part.validation.production_export_allowed:
        page.insert_textbox(
            fitz.Rect(margin, margin + drawing_rect.height * 0.35, width_pt - margin, margin + drawing_rect.height * 0.65),
            "CONCEPT - NIET VOOR PRODUCTIE",
            fontsize=min(34, width_pt / 14),
            fontname="helv",
            color=(0.65, 0.65, 0.65),
            align=fitz.TEXT_ALIGN_CENTER,
            rotate=0,
            overlay=True,
        )

    return {
        "scale_pt_per_mm": scale_pt_per_mm,
        "reported_scale": reported_scale,
        "model_bbox_mm": [model_w, model_h, thickness],
        "views": ["primary", "section"],
        "vector": True,
    }


def create_trusted_pdf(
    part: CanonicalPart,
    output_path: str | Path,
    *,
    template: DrawingTemplate | str | Path | None = None,
    software_version: str = "0.5.0",
) -> PDFConversionResult:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tpl = template if isinstance(template, DrawingTemplate) else load_template(template)
    part = part.clone()
    part.converter_version = software_version
    part.drawing.sheet_format = tpl.sheet_format
    part.drawing.orientation = tpl.orientation
    part.drawing.template_id = tpl.template_id

    with tempfile.TemporaryDirectory(prefix="trusted_pdf_") as folder:
        visible_path = Path(folder) / "visible.pdf"
        width, height = tpl.page_size_points()
        document = fitz.open()
        page = document.new_page(width=width, height=height)
        layout = _draw_technical_page(page, part, tpl)
        part.drawing.views = [{"type": value} for value in layout["views"]]
        part.drawing.scale = layout["reported_scale"]
        document.set_metadata(
            {
                "title": part.header.part_name or part.part_id or "Onderdeeltekening",
                "subject": "Technische vectoriele onderdeeltekening",
                "author": tpl.company_name or "NC1 STEP IFC Converter",
                "creator": f"NC1 STEP IFC Converter {software_version}",
                "producer": "PyMuPDF",
                "keywords": "NC1,DSTV,STEP,IFC,Trusted Converter PDF",
            }
        )
        document.save(visible_path, deflate=True, garbage=4, clean=True)
        document.close()

        visible_hash = visible_pdf_sha256(visible_path)
        manifest = _manifest_for_part(part, visible_hash, software_version)
        with fitz.open(visible_path) as final_document:
            _add_embedded_files(final_document, manifest)
            final_document.save(target, deflate=True, garbage=4, clean=True)

    final_visible_hash = visible_pdf_sha256(target)
    if final_visible_hash != visible_hash:
        target.unlink(missing_ok=True)
        raise PDFError("Insluiten van Trusted PDF-data heeft de zichtbare tekening gewijzigd")
    inspection = inspect_pdf(target, strict=True)
    if not inspection.trusted_exact:
        target.unlink(missing_ok=True)
        raise PDFError("Gegenereerde Trusted Converter PDF kon niet exact worden gevalideerd")
    return PDFConversionResult(
        source=Path(part.source_file or part.part_id),
        outputs=[target],
        classification="trusted_exact",
        warnings=inspection.warnings,
        details={
            "visible_drawing_sha256": visible_hash,
            "canonical_sha256": inspection.details.get("canonical_sha256"),
            "geometry_sha256": inspection.details.get("geometry_sha256"),
            "layout": layout,
        },
    )


# ---------------------------------------------------------------------------
# Trusted PDF inspectie
# ---------------------------------------------------------------------------


def inspect_pdf(path: str | Path, *, strict: bool = False) -> PDFInspection:
    source = Path(path)
    warnings: list[str] = []
    errors: list[str] = []
    details: dict[str, Any] = {}
    part: CanonicalPart | None = None
    classification = "external"
    try:
        with fitz.open(source) as document:
            names = list(document.embfile_names())
            details["page_count"] = document.page_count
            details["embedded_files"] = names
            if TRUSTED_PDF_ATTACHMENT not in names:
                return PDFInspection(source, "external", False, details=details)
            classification = "trusted-invalid"
            raw = document.embfile_get(TRUSTED_PDF_ATTACHMENT)
            manifest = json.loads(raw.decode("utf-8"))
            if manifest.get("format") != TRUSTED_PDF_FORMAT:
                raise CanonicalPayloadError("Onbekend Trusted PDF-manifestformaat")
            if manifest.get("manifest_version") != TRUSTED_PDF_MANIFEST_VERSION:
                raise CanonicalPayloadError("Niet-ondersteunde Trusted PDF-manifestversie")
            part = CanonicalPart.from_dict(manifest["canonical_model"])
            source_key = {
                "NC1": "nc1",
                "DSTV": "nc1",
                "STEP": "step",
                "STP": "step",
                "IFC": "ifc",
            }.get(part.source_format.upper())
            if source_key and part.attachment(source_key) is not None:
                attachment = part.attachment(source_key)
                assert attachment is not None
                embedded_name = f"source-{attachment.name}"
                if embedded_name not in names:
                    raise CanonicalPayloadError(
                        f"Trusted PDF mist de gekoppelde bronbijlage {embedded_name!r}"
                    )
                embedded_source = document.embfile_get(embedded_name)
                if sha256_bytes(embedded_source) != attachment.sha256:
                    raise CanonicalPayloadError(
                        f"Checksum van gekoppelde bronbijlage {embedded_name!r} klopt niet"
                    )
                details["source_attachment"] = embedded_name
                details["source_attachment_sha256"] = attachment.sha256
            expected_canonical = str(manifest.get("canonical_sha256", ""))
            actual_canonical = canonical_sha256(part)
            expected_geometry = str(manifest.get("geometry_sha256", ""))
            actual_geometry = geometry_sha256(part)
            expected_visible = str(manifest.get("visible_drawing_sha256", ""))
            actual_visible = _visible_hash_document(document)
            if expected_canonical != actual_canonical:
                raise CanonicalPayloadError("Canonieke PDF-checksum klopt niet")
            if expected_geometry != actual_geometry:
                raise CanonicalPayloadError("Geometriechecksum in PDF klopt niet")
            if expected_visible != actual_visible:
                raise CanonicalPayloadError("Zichtbare tekening wijkt af van de ingebedde productiedata")
            xmp = document.get_xml_metadata() or ""
            for key, expected in (
                ("schemaVersion", part.schema_version),
                ("partId", part.part_id),
                ("canonicalSHA256", actual_canonical),
                ("geometrySHA256", actual_geometry),
                ("visibleDrawingSHA256", actual_visible),
                ("sourceSHA256", part.source_sha256),
            ):
                actual = _xmp_value(xmp, key)
                if actual != str(expected):
                    raise CanonicalPayloadError(f"XMP-veld {key} ontbreekt of wijkt af")
            classification = "trusted_exact"
            details.update(
                {
                    "canonical_sha256": actual_canonical,
                    "geometry_sha256": actual_geometry,
                    "visible_drawing_sha256": actual_visible,
                    "manifest_version": manifest["manifest_version"],
                    "software_version": manifest.get("software_version", ""),
                }
            )
            return PDFInspection(source, classification, True, part, warnings, errors, details)
    except Exception as exc:
        errors.append(str(exc))
        if strict:
            raise
        return PDFInspection(source, classification, False, part, warnings, errors, details)


# ---------------------------------------------------------------------------
# Externe PDF-analyse (vector + tekst + optionele AI)
# ---------------------------------------------------------------------------


def _sheet_format(width_mm: float, height_mm: float) -> tuple[str, str, float]:
    orientation = "landscape" if width_mm >= height_mm else "portrait"
    short, long = sorted((width_mm, height_mm))
    best = ("unknown", 999.0)
    for name, (target_short, target_long) in SHEET_SIZES_MM.items():
        error = abs(short - target_short) + abs(long - target_long)
        if error < best[1]:
            best = (name, error)
    return best[0] if best[1] <= 12.0 else "unknown", orientation, best[1]


def _candidate(
    part: CanonicalPart,
    field_name: str,
    value: Any,
    confidence: float,
    evidence: str,
    *,
    page: int = 1,
    method: str = "vector-text-regex",
) -> None:
    current = part.field_values.get(field_name)
    if current is None or confidence > current.confidence:
        part.field_values[field_name] = CanonicalFieldValue(
            value=value,
            source_page=page,
            method=method,
            confidence=confidence,
            status="automatic" if confidence >= 0.95 else "review",
            evidence=evidence[:500],
        )


def _number(text: str) -> float:
    return float(text.replace(" ", "").replace(",", "."))


def _detect_text_fields(text: str, part: CanonicalPart) -> None:
    normalized = " ".join(text.replace("\u00d8", "Ø").split())
    scale = re.search(r"(?:Schaal\s*:?[ ]*)?(\d+)\s*:\s*(\d+)", normalized, re.IGNORECASE)
    if scale:
        _candidate(part, "scale", f"{scale.group(1)}:{scale.group(2)}", 0.98, scale.group(0))

    materials = re.findall(r"\bS(?:235|275|355|420|460)(?:JR|J0|J2|N|NL|M|ML|MC)?\b", normalized, re.IGNORECASE)
    if materials:
        material = max(materials, key=len).upper()
        _candidate(part, "material", material, 0.98, material)
        part.header.material = material
        part.header.material_grade = material

    profile_pattern = re.compile(
        r"\b(?:STRIP|PL|HEA|HEB|HEM|IPE|IPN|UPN|UNP|UPE|RHS|SHS|CHS|L|K|D)\s*"
        r"\d+(?:[.,]\d+)?(?:\s*[*xX/]\s*\d+(?:[.,]\d+)?){0,3}\b",
        re.IGNORECASE,
    )
    profiles = [re.sub(r"\s+", "", item.upper()).replace("X", "*") for item in profile_pattern.findall(normalized)]
    if profiles:
        profile = profiles[0]
        _candidate(part, "profile", profile, 0.97, profile)
        part.header.profile = profile
        if profile.startswith(("STRIP", "PL")):
            part.header.profile_type = "B"
            numbers = [_number(item) for item in re.findall(r"\d+(?:[.,]\d+)?", profile)]
            if len(numbers) >= 2:
                part.header.thickness = numbers[0]
                part.header.dim1 = numbers[1]
                part.header.dim2 = numbers[0]

    # Prefer a row that resembles: LO4 STRIP5*120 S235JR 160 4 MLO4
    row = re.search(
        r"\b([A-Z]{1,6}\d+)\s+((?:STRIP|PL|HEA|HEB|HEM|IPE|UPN|UNP|UPE|RHS|SHS|CHS|L|K|D)[^\s]*)\s+"
        r"(S\d{3}[A-Z0-9]*)\s+(\d+(?:[.,]\d+)?)\s+(\d+)\s+([A-Z][A-Z0-9_-]*)\b",
        normalized,
        re.IGNORECASE,
    )
    if row:
        position, profile, material, length, quantity, mark = row.groups()
        _candidate(part, "position", position.upper(), 0.995, row.group(0))
        _candidate(part, "profile", profile.upper(), 0.995, row.group(0))
        _candidate(part, "material", material.upper(), 0.995, row.group(0))
        _candidate(part, "length_text", _number(length), 0.995, row.group(0))
        _candidate(part, "quantity", int(quantity), 0.995, row.group(0))
        _candidate(part, "mark", mark.upper(), 0.995, row.group(0))
        part.part_id = position.upper()
        part.header.part_number = position.upper()
        part.header.position_number = position.upper()
        part.header.profile = profile.upper()
        part.header.material = material.upper()
        part.header.length = _number(length)
        part.header.quantity = int(quantity)
        part.header.mark = mark.upper()

    total = re.search(r"Totaal\s+aantal\s+keer\s+uit\s+te\s+voeren\s*:\s*(\d+)", normalized, re.IGNORECASE)
    if total:
        _candidate(part, "total_quantity", int(total.group(1)), 0.99, total.group(0))

    holes = re.findall(r"(\d+)\s*[*xX×]\s*[Øø⌀]\s*(\d+(?:[.,]\d+)?)", normalized)
    if holes:
        callouts = [f"{int(count)}x Ø{_fmt(_number(diameter), 2)}" for count, diameter in holes]
        _candidate(part, "hole_callouts", callouts, 0.96, ", ".join(callouts))
        part.properties["hole_callouts"] = [
            {"count": int(count), "diameter_mm": _number(diameter)} for count, diameter in holes
        ]

    radii = [_number(item) for item in re.findall(r"\bR\s*(\d+(?:[.,]\d+)?)", normalized, re.IGNORECASE)]
    if radii:
        _candidate(part, "radius_callouts", radii, 0.95, ", ".join(f"R {value:g}" for value in radii))
        part.properties["radius_callouts_mm"] = radii

    if re.search(r"\bLOSSE\s+PLAAT\b", normalized, re.IGNORECASE):
        _candidate(part, "subject", "LOSSE PLAAT", 0.98, "LOSSE PLAAT")
        part.header.part_name = "LOSSE PLAAT"


def _drawing_summary(path: dict[str, Any]) -> dict[str, Any]:
    rect = path.get("rect")
    return {
        "type": path.get("type"),
        "close_path": bool(path.get("closePath")),
        "fill": path.get("fill") is not None,
        "stroke": path.get("color") is not None,
        "items": len(path.get("items") or []),
        "bbox_pt": [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)] if rect else [],
    }


def analyze_external_pdf(
    path: str | Path,
    *,
    ai_provider: AIProvider | None = None,
    cloud_consent: bool = False,
) -> PDFAnalysisResult:
    source = Path(path)
    inspection = inspect_pdf(source)
    if inspection.trusted_exact and inspection.part is not None:
        return PDFAnalysisResult(
            source,
            inspection.part,
            [{"classification": "trusted_exact"}],
            "",
            warnings=["Trusted Converter PDF exact uit embedded model geladen."],
        )

    page_results: list[dict[str, Any]] = []
    texts: list[str] = []
    with fitz.open(source) as document:
        for index in range(document.page_count):
            page = document.load_page(index)
            page_text = page.get_text("text")
            texts.append(page_text)
            drawings = page.get_drawings()
            images = page.get_images(full=True)
            words = page.get_text("words")
            vector_count = len(drawings)
            image_count = len(images)
            if vector_count and image_count:
                classification = "hybrid"
            elif vector_count:
                classification = "vector"
            elif image_count:
                classification = "raster"
            else:
                classification = "text-only"
            width_mm = page.rect.width / MM_TO_PT
            height_mm = page.rect.height / MM_TO_PT
            sheet, orientation, sheet_error = _sheet_format(width_mm, height_mm)
            page_results.append(
                {
                    "page": index + 1,
                    "classification": classification,
                    "width_mm": width_mm,
                    "height_mm": height_mm,
                    "sheet_format": sheet,
                    "orientation": orientation,
                    "sheet_match_error_mm": sheet_error,
                    "text_characters": len(page_text),
                    "word_count": len(words),
                    "vector_path_count": vector_count,
                    "image_count": image_count,
                    "quality_score": min(1.0, 0.35 + min(vector_count, 50) / 100 + min(len(words), 200) / 400),
                    "vector_candidates": [_drawing_summary(item) for item in drawings[:200]],
                }
            )

    full_text = "\n".join(texts)
    page0 = page_results[0] if page_results else {}
    source_hash = sha256_file(source)
    part = CanonicalPart(
        converter_version="0.5.0",
        source_format="PDF",
        source_file=source.name,
        source_sha256=source_hash,
        part_id=source.stem,
        imported_at=datetime.now(timezone.utc).isoformat(),
        import_method="vector-text" if any(item["classification"] in {"vector", "hybrid"} for item in page_results) else "raster-review",
        header=CanonicalHeader(part_number=source.stem, position_number=source.stem, quantity=1),
        drawing=CanonicalDrawing(
            sheet_format=str(page0.get("sheet_format", "unknown")),
            orientation=str(page0.get("orientation", "landscape")),
            status="draft",
            views=[],
        ),
        properties={
            "pdf_page_analysis": page_results,
            "text_sha256": sha256_bytes(full_text.encode("utf-8")),
        },
        recognition={"method": "deterministic PDF vector/text analysis", "confidence": 0.0},
        validation=CanonicalValidation(
            errors=[
                "Externe PDF mist een geverifieerde Trusted Converter payload",
                "Gesloten productiecontour, featurekoppeling en referentiezijden zijn nog niet deterministisch bevestigd",
            ],
            unresolved_questions=[
                CanonicalQuestion(
                    "pdf_geometry_review",
                    "geometry",
                    "Bevestig de gesloten buitencontour, gatposities, radii en productiereferentiezijde in de reviewinterface.",
                    blocking=True,
                )
            ],
            export_status="review-required",
            production_export_allowed=False,
        ),
    )
    part.add_attachment("pdf", source.name, "application/pdf", source.read_bytes())
    _candidate(part, "sheet_format", part.drawing.sheet_format, 0.99 if part.drawing.sheet_format != "unknown" else 0.2, f"PDF-paginamaten: {page0.get('width_mm', 0):.1f} x {page0.get('height_mm', 0):.1f} mm")
    _detect_text_fields(full_text, part)

    critical = {
        "position": part.header.position_number,
        "profile": part.header.profile,
        "material": part.header.material,
        "quantity": part.header.quantity if "quantity" in part.field_values else None,
        "length_text": part.header.length or None,
    }
    missing = [name for name, value in critical.items() if value in (None, "", 0)]
    detected_context = {
        key: {
            "value": value.value,
            "confidence": value.confidence,
            "page": value.source_page,
            "evidence": value.evidence,
        }
        for key, value in part.field_values.items()
    }
    context = {
        "source_file": source.name,
        "page_analysis": page_results,
        "detected_fields": detected_context,
        "missing_critical_fields": missing,
        "deterministic_conflicts": [],
        "extracted_text": full_text[:40000],
        "safety_rule": "AI may not generate geometry, coordinates, NC1, STEP or IFC data",
    }
    provider = ai_provider or LocalSemanticProvider()
    images = render_pdf_pages(source, max_pages=4) if ai_provider is not None else []
    ai = provider.interpret(context, images, cloud_consent=cloud_consent)

    # Merge AI proposals only into semantically allowed fields; deterministic values
    # win at equal/higher confidence.
    for proposed in ai.fields:
        existing = part.field_values.get(proposed.name)
        # Een deterministisch uit PDF-tekst/vectoren gelezen veld blijft leidend.
        # AI mag ontbrekende semantiek aanvullen en conflicten signaleren, maar
        # mag een reeds gelezen maat-/stuklijstwaarde niet stilzwijgend vervangen.
        if existing is not None and not str(existing.method).startswith("AI:"):
            if (
                proposed.value not in (None, "", [])
                and proposed.value != existing.value
                and float(proposed.confidence) >= 0.80
            ):
                part.validation.unresolved_questions.append(
                    CanonicalQuestion(
                        f"ai_conflict_{proposed.name}",
                        proposed.name,
                        (
                            f"AI stelt {proposed.name}={proposed.value!r} voor, maar de "
                            f"deterministische PDF-extractie vond {existing.value!r}. "
                            "Bevestig de juiste waarde."
                        ),
                        [str(existing.value), str(proposed.value)],
                        True,
                    )
                )
            continue
        _candidate(
            part,
            proposed.name,
            proposed.value,
            proposed.confidence,
            proposed.evidence,
            page=proposed.page or 1,
            method=f"AI:{ai.provider}",
        )
    for index, question in enumerate(ai.questions, start=1):
        part.validation.unresolved_questions.append(
            CanonicalQuestion(
                f"ai_question_{index}",
                question.field,
                question.question,
                question.options,
                question.blocking,
            )
        )
    for conflict in ai.conflicts:
        message = f"{conflict.field}: {conflict.message}"
        if conflict.blocking:
            part.validation.errors.append(message)
        else:
            part.warnings.append(message)
    part.audit_log.append(ai.audit)
    part.recognition["confidence"] = max(
        [float(item.confidence) for item in part.field_values.values()] or [0.0]
    )
    part.validate()
    warnings = list(part.warnings)
    if any(item["classification"] == "raster" for item in page_results):
        warnings.append("Rasterpagina gevonden: OCR/vision-resultaten blijven reviewplichtig.")
    return PDFAnalysisResult(source, part, page_results, full_text, ai, warnings)


# ---------------------------------------------------------------------------
# Formaatconversies
# ---------------------------------------------------------------------------


def nc1_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    *,
    template: DrawingTemplate | str | Path | None = None,
) -> PDFConversionResult:
    from conversion import __version__

    part, _shape = canonicalize_nc1(input_path)
    return create_trusted_pdf(part, output_path, template=template, software_version=__version__)


def step_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    *,
    material: str = "S355JR",
    template: DrawingTemplate | str | Path | None = None,
) -> PDFConversionResult:
    from conversion import __version__

    part, _shape = canonicalize_step(input_path, material=material)
    return create_trusted_pdf(part, output_path, template=template, software_version=__version__)


def ifc_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    *,
    template: DrawingTemplate | str | Path | None = None,
) -> PDFConversionResult:
    from conversion import __version__

    source, target = Path(input_path), Path(output_path)
    parts = canonicalize_ifc(source)
    outputs: list[Path] = []
    warnings: list[str] = []
    if len(parts) == 1 and target.suffix.lower() == ".pdf":
        result = create_trusted_pdf(parts[0][0], target, template=template, software_version=__version__)
        return result
    output_directory = target if target.suffix.lower() != ".pdf" else target.parent / target.stem
    output_directory.mkdir(parents=True, exist_ok=True)
    for index, (part, _shape) in enumerate(parts, start=1):
        name = re.sub(r"[^A-Za-z0-9_.-]+", "_", part.part_id or f"element_{index:03d}").strip("_.")
        item_target = output_directory / f"{name or f'element_{index:03d}'}.pdf"
        result = create_trusted_pdf(part, item_target, template=template, software_version=__version__)
        outputs.extend(result.outputs)
        warnings.extend(result.warnings)
    return PDFConversionResult(source, outputs, "trusted_exact", warnings, {"parts": len(parts)})


def _trusted_part_for_export(path: str | Path) -> CanonicalPart:
    inspection = inspect_pdf(path, strict=False)
    if not inspection.trusted_exact or inspection.part is None:
        reasons = inspection.errors or ["PDF is geen ongewijzigde Trusted Converter PDF"]
        if inspection.classification == "external":
            analysis = analyze_external_pdf(path)
            reasons.extend(analysis.part.validation.errors)
            reasons.extend(
                item.message
                for item in analysis.part.validation.unresolved_questions
                if item.blocking and item.status == "open"
            )
        raise PDFProductionBlockedError("Productie-export uit PDF is geblokkeerd.", reasons)
    allowed, reasons = production_export_allowed(inspection.part)
    if not allowed:
        raise PDFProductionBlockedError("Trusted PDF is nog niet vrijgegeven voor productie-export.", reasons)
    return inspection.part


def pdf_to_nc1(input_path: str | Path, output_path: str | Path) -> PDFConversionResult:
    from conversion import step_to_nc1

    source, target = Path(input_path), Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = _trusted_part_for_export(source)
    nc1_bytes = part.attachment_bytes("nc1")
    if nc1_bytes is not None:
        target.write_bytes(nc1_bytes)
        # Parse is a hard structural check; no free AI output is involved.
        import converter as core

        parsed = core.parse_nc1(target)
        return PDFConversionResult(
            source,
            [target],
            "trusted_exact",
            details={"route": "embedded-nc1", "profile": parsed.header.profile, "holes": len(parsed.holes)},
        )
    step_bytes = part.attachment_bytes("step")
    if step_bytes is None:
        raise PDFProductionBlockedError("Trusted PDF bevat geen NC1- of STEP-bijlage voor veilige productie-export")
    with tempfile.TemporaryDirectory(prefix="pdf_to_nc1_") as folder:
        step_path = Path(folder) / "source.step"
        step_path.write_bytes(step_bytes)
        result = step_to_nc1(step_path, target, material=part.header.material or "S355JR", strict_validation=True)
    return PDFConversionResult(
        source,
        [target],
        "trusted_exact",
        warnings=result.warnings,
        details={"route": "embedded-step-to-nc1", "volume_delta_percent": result.volume_delta_percent},
    )


def pdf_to_step(input_path: str | Path, output_path: str | Path) -> PDFConversionResult:
    from conversion import convert_nc1_to_step

    source, target = Path(input_path), Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = _trusted_part_for_export(source)
    step_bytes = part.attachment_bytes("step")
    if step_bytes is not None:
        target.write_bytes(step_bytes)
        shape = cq.importers.importStep(str(target)).val()
        return PDFConversionResult(source, [target], "trusted_exact", details={"route": "embedded-step", **_shape_metrics(shape)})
    nc1_bytes = part.attachment_bytes("nc1")
    if nc1_bytes is None:
        raise PDFProductionBlockedError("Trusted PDF bevat geen NC1- of STEP-bijlage voor veilige STEP-export")
    with tempfile.TemporaryDirectory(prefix="pdf_to_step_") as folder:
        nc1_path = Path(folder) / "source.nc1"
        nc1_path.write_bytes(nc1_bytes)
        convert_nc1_to_step(nc1_path, target)
    shape = cq.importers.importStep(str(target)).val()
    return PDFConversionResult(source, [target], "trusted_exact", details={"route": "embedded-nc1-to-step", **_shape_metrics(shape)})


def pdf_to_ifc(input_path: str | Path, output_path: str | Path) -> PDFConversionResult:
    from ifc_support import dstv_to_ifc, step_to_ifc

    source, target = Path(input_path), Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = _trusted_part_for_export(source)
    step_bytes = part.attachment_bytes("step")
    if step_bytes is not None:
        with tempfile.TemporaryDirectory(prefix="pdf_to_ifc_step_") as folder:
            step_path = Path(folder) / "source.step"
            step_path.write_bytes(step_bytes)
            result = step_to_ifc(step_path, target, material=part.header.material or "S355JR")
        return PDFConversionResult(source, result.outputs, "trusted_exact", result.warnings, result.details)
    nc1_bytes = part.attachment_bytes("nc1")
    if nc1_bytes is None:
        raise PDFProductionBlockedError("Trusted PDF bevat geen NC1- of STEP-bijlage voor veilige IFC-export")
    with tempfile.TemporaryDirectory(prefix="pdf_to_ifc_nc1_") as folder:
        nc1_path = Path(folder) / "source.nc1"
        nc1_path.write_bytes(nc1_bytes)
        result = dstv_to_ifc(nc1_path, target, material=part.header.material or "S355JR")
    return PDFConversionResult(source, result.outputs, "trusted_exact", result.warnings, result.details)
