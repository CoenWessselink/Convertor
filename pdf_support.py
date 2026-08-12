"""Bidirectional technical PDF support for the converter.

This module implements the first production-safe PDF layer in the order
required by the project specification:

1. one canonical model;
2. deterministic vector drawing generation;
3. Trusted Converter PDF with exact embedded model and hashes;
4. external PDF classification/vector/text extraction;
5. an advisory AI hook that never writes production geometry;
6. strict export gates and roundtrip validation.

External drawings are not silently guessed.  They remain blocked until all
critical geometry is deterministically reconstructed or explicitly confirmed.
"""
from __future__ import annotations

from cws_branding import PRODUCT_NAME

from dataclasses import asdict, dataclass, field
from pathlib import Path
import copy
import hashlib
import io
import json
import math
import re
import tempfile
from typing import Any, Iterable, Sequence

import cadquery as cq
import numpy as np
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    ByteStringObject,
    DictionaryObject,
    FloatObject,
    IndirectObject,
    NameObject,
    NullObject,
    NumberObject,
    StreamObject,
    TextStringObject,
)
from reportlab.lib.pagesizes import A1, A2, A3, A4, landscape, portrait
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from ai_support import AIInterpretation, AISettings, interpret_drawing
from canonical_model import (
    CanonicalContour,
    CanonicalContourPoint,
    CanonicalDrawingData,
    CanonicalEvidence,
    CanonicalHeader,
    CanonicalHole,
    CanonicalPart,
    CanonicalPayloadError,
    CanonicalProductData,
    CanonicalQuestion,
    CanonicalValidationData,
    DEFAULT_CONVERTER_VERSION,
    SCHEMA_VERSION,
    canonical_from_nc1_part,
    extract_part_from_ifc,
    extract_part_from_step,
    sha256_bytes,
    sha256_file,
    utc_now_iso,
)
from dimension_graph import populate_dimension_graph, validate_dimension_graph

TRUSTED_MODEL_NAME = "converter-model.json"
TRUSTED_MANIFEST_NAME = "converter-manifest.json"
TRUSTED_PDF_FORMAT = "NC1_STEP_IFC_TRUSTED_PDF_V1"
VISIBLE_HASH_ALGORITHM = "pdf-page-content-resources-sha256-v1"


class PDFSupportError(RuntimeError):
    pass


class TrustedPDFError(PDFSupportError):
    pass


class ExternalPDFExportBlocked(PDFSupportError):
    """Production export was requested while critical questions remain."""


@dataclass
class PDFPageAnalysis:
    page: int
    classification: str
    width_pt: float
    height_pt: float
    sheet_format: str
    orientation: str
    word_count: int
    vector_path_count: int
    image_count: int
    quality_score: float
    text: str = ""


@dataclass
class PDFAnalysisResult:
    source: Path
    source_sha256: str
    mode: str
    part: CanonicalPart
    pages: list[PDFPageAnalysis] = field(default_factory=list)
    detected_fields: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    ai: AIInterpretation | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def production_export_allowed(self) -> bool:
        return bool(self.part.validation.production_export_allowed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "source_sha256": self.source_sha256,
            "mode": self.mode,
            "production_export_allowed": self.production_export_allowed,
            "pages": [asdict(item) for item in self.pages],
            "detected_fields": self.detected_fields,
            "warnings": self.warnings,
            "errors": self.errors,
            "questions": [asdict(item) for item in self.part.validation.unresolved_questions],
            "ai": self.ai.to_dict() if self.ai else None,
            "details": self.details,
            "part": self.part.to_dict(),
        }


@dataclass
class PDFConversionResult:
    source: Path
    outputs: list[Path]
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def primary_output(self) -> Path | None:
        return self.outputs[0] if self.outputs else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "outputs": [str(item) for item in self.outputs],
            "warnings": self.warnings,
            "failures": self.failures,
            "details": self.details,
        }


@dataclass
class DrawingTemplate:
    template_id: str = "default-a4"
    sheet_format: str = "A4"
    orientation: str = "landscape"
    company_name: str = ""
    company_address: str = ""
    logo_path: str = ""
    default_status: str = "CONCEPT"
    project: str = ""
    client: str = ""
    drawn_by: str = ""
    checked_by: str = ""
    projection_method: str = "first_angle"
    decimal_places: int = 1
    general_notes: list[str] = field(default_factory=list)


@dataclass
class _LineRecord:
    text: str
    bbox: list[float]
    page: int


@dataclass
class _VectorPath:
    page: int
    rect: list[float]
    items: list[tuple]
    close_path: bool
    fill: Any
    stroke: Any
    width: float

    @property
    def width_pt(self) -> float:
        return max(0.0, self.rect[2] - self.rect[0])

    @property
    def height_pt(self) -> float:
        return max(0.0, self.rect[3] - self.rect[1])


# ---------------------------------------------------------------------------
# Canonical source adapters
# ---------------------------------------------------------------------------


def _with_dimension_graph(part: CanonicalPart) -> CanonicalPart:
    """Ensure every source adapter exposes feature-linked drawing dimensions."""

    populate_dimension_graph(part, overwrite=True, strict=False)
    return part


def canonical_from_nc1(path: str | Path) -> CanonicalPart:
    import converter as core
    from conversion import build_shape

    source = Path(path)
    parsed = core.parse_nc1(source)
    shape = build_shape(parsed).val()
    box = shape.BoundingBox()
    return _with_dimension_graph(canonical_from_nc1_part(
        parsed,
        source_bytes=source.read_bytes(),
        converter_version=DEFAULT_CONVERTER_VERSION,
        geometry={
            "volume_mm3": float(shape.Volume()),
            "area_mm2": float(shape.Area()),
            "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
            "solids": len(shape.Solids()),
        },
    ))


def canonical_from_step(
    path: str | Path,
    *,
    material: str = "S355JR",
    preferred_profile: str = "",
    tolerance_mm: float = 1.0,
) -> CanonicalPart:
    """Return an exact payload or a safely classified STEP canonical model."""

    source = Path(path)
    payload = extract_part_from_step(source, strict=False)
    if payload is not None:
        result = payload.clone()
        result.converter_version = DEFAULT_CONVERTER_VERSION
        if result.attachment("step") is None:
            result.add_attachment("step", source.name, "model/step", source.read_bytes())
        return _with_dimension_graph(result)

    from conversion import step_to_nc1
    from profile_database import ProfileDatabase

    shape = cq.importers.importStep(str(source)).val()
    box = shape.BoundingBox()
    try:
        with tempfile.TemporaryDirectory(prefix="pdf_step_canonical_") as folder:
            nc1 = Path(folder) / f"{source.stem}.nc1"
            result = step_to_nc1(
                source,
                nc1,
                material=material,
                order_number="PDF",
                profile_database=ProfileDatabase(),
                preferred_profile=preferred_profile,
                tolerance_mm=tolerance_mm,
                strict_validation=True,
                embed_converter_payload=True,
            )
            from canonical_model import extract_part_from_nc1

            canonical = extract_part_from_nc1(nc1, strict=True)
            if canonical is None:
                raise CanonicalPayloadError("STEP-classificatie leverde geen canonieke payload")
            canonical = canonical.clone()
            canonical.converter_version = DEFAULT_CONVERTER_VERSION
            canonical.recognition.update(
                {
                    "method": result.matched_by,
                    "confidence": float(result.confidence),
                    "production_export_allowed": True,
                }
            )
            canonical.validation.warnings.extend(result.warnings)
            canonical.validation.export_status = "validated"
            canonical.validation.production_export_allowed = True
            canonical.refresh_export_gate()
            return _with_dimension_graph(canonical)
    except Exception as exc:
        warning = (
            "STEP kon niet veilig als DSTV-plaat of standaardprofiel worden geclassificeerd. "
            "De technische PDF is daarom conceptueel en terugconversie naar NC1 blijft geblokkeerd: "
            f"{exc}"
        )
        canonical = CanonicalPart(
            converter_version=DEFAULT_CONVERTER_VERSION,
            source_format="STEP",
            source_file=source.name,
            source_sha256=sha256_file(source),
            imported_at=utc_now_iso(),
            import_method="exact_geometry_unclassified",
            part_id=source.stem,
            header=CanonicalHeader(
                part_number=source.stem,
                position_number=source.stem,
                material=material,
                quantity=1,
            ),
            product=CanonicalProductData(
                name=source.stem,
                material_code=material,
                material_grade=material,
                main_dimensions_mm=[float(box.xlen), float(box.ylen), float(box.zlen)],
            ),
            geometry={
                "volume_mm3": float(shape.Volume()),
                "area_mm2": float(shape.Area()),
                "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
                "solids": len(shape.Solids()),
            },
            recognition={
                "method": "unclassified analytic STEP",
                "confidence": 0.0,
                "production_export_allowed": False,
            },
            warnings=[warning],
            validation=CanonicalValidationData(
                warnings=[warning],
                errors=[],
                export_status="concept",
                production_export_allowed=False,
            ),
        )
        canonical.add_attachment("step", source.name, "model/step", source.read_bytes())
        canonical.add_question(
            CanonicalQuestion(
                question_id="step-profile-classification",
                field_path="header.profile",
                prompt="Welk profiel en welke lokale productie-orientatie horen bij dit STEP-model?",
                reason="Automatische STEP-classificatie voldeed niet aan de veiligheidscriteria.",
            )
        )
        return _with_dimension_graph(canonical)


def canonical_parts_from_ifc(path: str | Path, *, material: str = "S355JR") -> list[CanonicalPart]:
    source = Path(path)
    payload = extract_part_from_ifc(source, strict=False)
    if payload is not None:
        part = payload.clone()
        part.converter_version = DEFAULT_CONVERTER_VERSION
        if part.attachment("ifc") is None and source.stat().st_size <= 32 * 1024 * 1024:
            part.add_attachment("ifc", source.name, "model/ifc", source.read_bytes())
        return [_with_dimension_graph(part)]

    from ifc_support import load_ifc_geometry

    model = load_ifc_geometry(source)
    parts: list[CanonicalPart] = []
    for index, item in enumerate(model.items, start=1):
        dims = [float(value) for value in item.bbox_mm]
        warning = (
            "Extern IFC-element heeft geen geverifieerde converterpayload. De PDF kan als concept "
            "worden gemaakt, maar productie-terugconversie blijft geblokkeerd tot profiel en features "
            "deterministisch zijn bevestigd."
        )
        part = CanonicalPart(
            converter_version=DEFAULT_CONVERTER_VERSION,
            source_format="IFC",
            source_file=source.name,
            source_sha256=sha256_file(source),
            imported_at=utc_now_iso(),
            import_method="ifc_geometry",
            part_id=item.name or item.guid or f"{source.stem}_{index}",
            header=CanonicalHeader(
                part_number=item.name or f"{source.stem}_{index}",
                position_number=item.name or f"{source.stem}_{index}",
                material=item.material or material,
                quantity=1,
                length=max(dims) if dims else 0.0,
            ),
            product=CanonicalProductData(
                name=item.name or f"{source.stem}_{index}",
                material_code=item.material or material,
                material_grade=item.material or material,
                main_dimensions_mm=dims,
            ),
            geometry={
                "volume_mm3": float(item.volume_mm3),
                "area_mm2": float(item.area_mm2),
                "bbox_mm": dims,
                "ifc_guid": item.guid,
                "ifc_class": item.ifc_class,
            },
            recognition={
                "method": "external IFC geometry",
                "confidence": 0.0,
                "production_export_allowed": False,
            },
            warnings=[warning],
            validation=CanonicalValidationData(
                warnings=[warning],
                export_status="concept",
                production_export_allowed=False,
            ),
        )
        part.add_question(
            CanonicalQuestion(
                question_id=f"ifc-feature-classification-{index}",
                field_path="geometry.features",
                prompt="Bevestig profiel, productiezijden en alle gaten/contourbewerkingen voor dit IFC-element.",
                reason="Extern IFC bevat geen lossless productiedata van de converter.",
            )
        )
        parts.append(_with_dimension_graph(part))
    return parts


# ---------------------------------------------------------------------------
# Deterministic drawing generation
# ---------------------------------------------------------------------------


_PAGE_SIZES = {"A4": A4, "A3": A3, "A2": A2, "A1": A1}


def _page_size(sheet_format: str, orientation: str) -> tuple[float, float]:
    base = _PAGE_SIZES.get(sheet_format.upper(), A4)
    return portrait(base) if orientation.lower() == "portrait" else landscape(base)


def _fmt(value: float, decimals: int = 1) -> str:
    if abs(value - round(value)) < 10 ** (-(decimals + 1)):
        return str(int(round(value)))
    return f"{value:.{decimals}f}".replace(".", ",")


def _effective_title(part: CanonicalPart) -> str:
    for value in (
        part.product.name,
        part.drawing.title_block.get("subject", ""),
        part.header.position_number,
        part.header.part_number,
        part.part_id,
    ):
        if str(value).strip():
            return str(value).strip()
    return "ONDERDEEL"


def _main_contour(part: CanonicalPart) -> CanonicalContour | None:
    candidates = [item for item in part.contours if item.kind.upper() in {"AK", "OUTER", "OUTER_CONTOUR"}]
    if not candidates:
        candidates = list(part.contours)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            (max((point.x for point in item.points), default=0.0) - min((point.x for point in item.points), default=0.0))
            * (max((point.q for point in item.points), default=0.0) - min((point.q for point in item.points), default=0.0))
        ),
    )


def _contour_bounds(contour: CanonicalContour | None, part: CanonicalPart) -> tuple[float, float, float, float]:
    if contour and contour.points:
        xs = [float(point.x) for point in contour.points]
        ys = [float(point.q) for point in contour.points]
        return min(xs), min(ys), max(xs), max(ys)
    length = float(part.header.length or (part.geometry.get("bbox_mm") or [0.0])[0] or 100.0)
    span = float(part.header.dim1 or (part.geometry.get("bbox_mm") or [0.0, 0.0])[1] or 50.0)
    return 0.0, 0.0, max(length, 1.0), max(span, 1.0)


def _transform_point(
    x: float,
    y: float,
    *,
    bounds: tuple[float, float, float, float],
    origin: tuple[float, float],
    scale: float,
) -> tuple[float, float]:
    x0, y0, _x1, _y1 = bounds
    return origin[0] + (x - x0) * scale, origin[1] + (y - y0) * scale


def _line_intersection(
    p1: np.ndarray,
    direction1: np.ndarray,
    p2: np.ndarray,
    direction2: np.ndarray,
) -> np.ndarray | None:
    matrix = np.column_stack((direction1, -direction2))
    determinant = float(np.linalg.det(matrix))
    if abs(determinant) < 1e-10:
        return None
    factors = np.linalg.solve(matrix, p2 - p1)
    return p1 + direction1 * factors[0]


def _rounded_vertex_geometry(
    previous: np.ndarray,
    current: np.ndarray,
    following: np.ndarray,
    radius: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float] | None:
    incoming = previous - current
    outgoing = following - current
    lin = float(np.linalg.norm(incoming))
    lout = float(np.linalg.norm(outgoing))
    if radius <= 0 or lin <= 1e-9 or lout <= 1e-9:
        return None
    incoming /= lin
    outgoing /= lout
    cosine = float(np.clip(np.dot(incoming, outgoing), -1.0, 1.0))
    angle = math.acos(cosine)
    if angle <= 1e-4 or abs(math.pi - angle) <= 1e-4:
        return None
    tangent_distance = radius / math.tan(angle / 2.0)
    tangent_distance = min(tangent_distance, lin * 0.45, lout * 0.45)
    if tangent_distance <= 1e-8:
        return None
    actual_radius = tangent_distance * math.tan(angle / 2.0)
    tangent_in = current + incoming * tangent_distance
    tangent_out = current + outgoing * tangent_distance
    bisector = incoming + outgoing
    bnorm = float(np.linalg.norm(bisector))
    if bnorm <= 1e-9:
        return None
    bisector /= bnorm
    center_distance = actual_radius / math.sin(angle / 2.0)
    center = current + bisector * center_distance
    start_angle = math.degrees(math.atan2(tangent_in[1] - center[1], tangent_in[0] - center[0]))
    end_angle = math.degrees(math.atan2(tangent_out[1] - center[1], tangent_out[0] - center[0]))
    cross = float(np.cross(np.append(tangent_in - center, 0), np.append(tangent_out - center, 0))[2])
    if cross >= 0:
        extent = (end_angle - start_angle) % 360.0
    else:
        extent = -((start_angle - end_angle) % 360.0)
    if abs(extent) > 180.0:
        extent = extent - 360.0 if extent > 0 else extent + 360.0
    return tangent_in, tangent_out, center, start_angle, extent


def _draw_contour(
    pdf: canvas.Canvas,
    contour: CanonicalContour | None,
    part: CanonicalPart,
    *,
    bounds: tuple[float, float, float, float],
    origin: tuple[float, float],
    scale: float,
) -> None:
    if contour is None or len(contour.points) < 3:
        x0, y0, x1, y1 = bounds
        px0, py0 = _transform_point(x0, y0, bounds=bounds, origin=origin, scale=scale)
        px1, py1 = _transform_point(x1, y1, bounds=bounds, origin=origin, scale=scale)
        pdf.rect(px0, py0, px1 - px0, py1 - py0, stroke=1, fill=0)
        return

    points = [np.asarray((float(item.x), float(item.q)), dtype=float) for item in contour.points]
    radii = [max(0.0, float(item.radius)) for item in contour.points]
    if len(points) > 1 and np.linalg.norm(points[0] - points[-1]) <= 1e-7:
        points.pop()
        radii.pop()
    count = len(points)
    rounded: list[tuple[np.ndarray, np.ndarray, np.ndarray, float, float] | None] = []
    for index, point in enumerate(points):
        rounded.append(
            _rounded_vertex_geometry(points[index - 1], point, points[(index + 1) % count], radii[index])
        )

    for index in range(count):
        current = points[index]
        following = points[(index + 1) % count]
        current_arc = rounded[index]
        next_arc = rounded[(index + 1) % count]
        start = current_arc[1] if current_arc else current
        end = next_arc[0] if next_arc else following
        sx, sy = _transform_point(*start, bounds=bounds, origin=origin, scale=scale)
        ex, ey = _transform_point(*end, bounds=bounds, origin=origin, scale=scale)
        pdf.line(sx, sy, ex, ey)
        if next_arc:
            _tin, _tout, center, start_angle, extent = next_arc
            radius = float(np.linalg.norm(next_arc[0] - center)) * scale
            cx, cy = _transform_point(*center, bounds=bounds, origin=origin, scale=scale)
            pdf.arc(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                startAng=start_angle,
                extent=extent,
            )


def _draw_arrow(pdf: canvas.Canvas, x: float, y: float, angle: float, size: float = 4.0) -> None:
    left = angle + math.radians(155)
    right = angle - math.radians(155)
    pdf.line(x, y, x + size * math.cos(left), y + size * math.sin(left))
    pdf.line(x, y, x + size * math.cos(right), y + size * math.sin(right))


def _draw_horizontal_dimension(
    pdf: canvas.Canvas,
    x1: float,
    x2: float,
    object_y: float,
    dimension_y: float,
    label: str,
) -> None:
    pdf.setLineWidth(0.45)
    pdf.line(x1, object_y, x1, dimension_y)
    pdf.line(x2, object_y, x2, dimension_y)
    pdf.line(x1, dimension_y, x2, dimension_y)
    _draw_arrow(pdf, x1, dimension_y, 0.0)
    _draw_arrow(pdf, x2, dimension_y, math.pi)
    width = stringWidth(label, "Helvetica", 7)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect((x1 + x2 - width) / 2 - 2, dimension_y - 4, width + 4, 8, stroke=0, fill=1)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString((x1 + x2) / 2, dimension_y - 2.4, label)


def _draw_vertical_dimension(
    pdf: canvas.Canvas,
    y1: float,
    y2: float,
    object_x: float,
    dimension_x: float,
    label: str,
) -> None:
    pdf.setLineWidth(0.45)
    pdf.line(object_x, y1, dimension_x, y1)
    pdf.line(object_x, y2, dimension_x, y2)
    pdf.line(dimension_x, y1, dimension_x, y2)
    _draw_arrow(pdf, dimension_x, y1, math.pi / 2)
    _draw_arrow(pdf, dimension_x, y2, -math.pi / 2)
    pdf.saveState()
    pdf.translate(dimension_x - 2.4, (y1 + y2) / 2)
    pdf.rotate(90)
    width = stringWidth(label, "Helvetica", 7)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect(-width / 2 - 2, -4, width + 4, 8, stroke=0, fill=1)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(0, -2.4, label)
    pdf.restoreState()


def _draw_horizontal_dimension_between(
    pdf: canvas.Canvas,
    first: tuple[float, float],
    second: tuple[float, float],
    dimension_y: float,
    label: str,
) -> None:
    """Horizontal dimension with independent geometric anchor heights."""

    x1, y1 = first
    x2, y2 = second
    pdf.setLineWidth(0.4)
    pdf.line(x1, y1, x1, dimension_y)
    pdf.line(x2, y2, x2, dimension_y)
    pdf.line(x1, dimension_y, x2, dimension_y)
    direction = 0.0 if x2 >= x1 else math.pi
    _draw_arrow(pdf, x1, dimension_y, direction)
    _draw_arrow(pdf, x2, dimension_y, direction + math.pi)
    center = (x1 + x2) / 2
    width = stringWidth(label, "Helvetica", 6.4)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect(center - width / 2 - 1.7, dimension_y - 3.6, width + 3.4, 7.2, stroke=0, fill=1)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 6.4)
    pdf.drawCentredString(center, dimension_y - 2.1, label)


def _draw_vertical_dimension_between(
    pdf: canvas.Canvas,
    first: tuple[float, float],
    second: tuple[float, float],
    dimension_x: float,
    label: str,
) -> None:
    """Vertical dimension with independent geometric anchor widths."""

    x1, y1 = first
    x2, y2 = second
    pdf.setLineWidth(0.4)
    pdf.line(x1, y1, dimension_x, y1)
    pdf.line(x2, y2, dimension_x, y2)
    pdf.line(dimension_x, y1, dimension_x, y2)
    direction = math.pi / 2 if y2 >= y1 else -math.pi / 2
    _draw_arrow(pdf, dimension_x, y1, direction)
    _draw_arrow(pdf, dimension_x, y2, direction + math.pi)
    center = (y1 + y2) / 2
    pdf.saveState()
    pdf.translate(dimension_x - 2.1, center)
    pdf.rotate(90)
    width = stringWidth(label, "Helvetica", 6.4)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.rect(-width / 2 - 1.7, -3.6, width + 3.4, 7.2, stroke=0, fill=1)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica", 6.4)
    pdf.drawCentredString(0, -2.1, label)
    pdf.restoreState()


def _draw_hole_position_dimensions(
    pdf: canvas.Canvas,
    part: CanonicalPart,
    *,
    bounds: tuple[float, float, float, float],
    origin: tuple[float, float],
    scale: float,
    px0: float,
    py0: float,
    drawing_left: float,
    table_top: float,
) -> None:
    """Draw datum-based hole coordinates from the semantic dimension graph.

    A small number of unique ordinates is drawn directly.  Dense patterns are
    kept in the embedded dimension graph and are represented by a note instead
    of producing an unreadable forest of overlapping lines.
    """

    if not part.holes:
        return
    graph = {str(item.get("id")): item for item in part.drawing.dimensions}
    x_rows: list[tuple[float, float, float, str]] = []
    y_rows: list[tuple[float, float, float, str]] = []
    seen_x: set[float] = set()
    seen_y: set[float] = set()
    for index, hole in enumerate(part.holes, start=1):
        hx, hy = _transform_point(hole.x, hole.q, bounds=bounds, origin=origin, scale=scale)
        x_item = graph.get(f"hole-{index:03d}-x")
        y_item = graph.get(f"hole-{index:03d}-y")
        if x_item is not None:
            value = round(float(x_item["value_mm"]), 3)
            if value not in seen_x and value > 0.001:
                seen_x.add(value)
                x_rows.append((value, hx, hy, str(x_item.get("label", value))))
        if y_item is not None:
            value = round(float(y_item["value_mm"]), 3)
            if value not in seen_y and value > 0.001:
                seen_y.add(value)
                y_rows.append((value, hx, hy, str(y_item.get("label", value))))

    x_rows.sort(key=lambda item: item[0])
    y_rows.sort(key=lambda item: item[0])
    max_direct = 4
    for row, (_value, hx, hy, label) in enumerate(x_rows[:max_direct]):
        dimension_y = py0 - (18 + row * 5.2) * mm
        if dimension_y <= table_top + 2 * mm:
            break
        _draw_horizontal_dimension_between(pdf, (px0, py0), (hx, hy), dimension_y, label)
    for row, (_value, hx, hy, label) in enumerate(y_rows[:max_direct]):
        dimension_x = px0 - (20 + row * 5.2) * mm
        if dimension_x <= drawing_left - 20 * mm:
            break
        _draw_vertical_dimension_between(pdf, (px0, py0), (hx, hy), dimension_x, label)

    if len(x_rows) > max_direct or len(y_rows) > max_direct:
        pdf.setFont("Helvetica", 5.8)
        pdf.drawString(
            drawing_left,
            table_top + 2.5 * mm,
            "Dicht gatpatroon: volledige X/Y-maatgrafiek is opgenomen in de Trusted PDF-data.",
        )


def _draw_profile_end_view(
    pdf: canvas.Canvas,
    part: CanonicalPart,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    ptype = part.header.profile_type.upper()
    h = max(float(part.header.dim1), 1.0)
    b = max(float(part.header.dim2), 1.0)
    tf = max(float(part.header.dim3), 1.0)
    tw = max(float(part.header.dim4), 1.0)
    factor = min(width / b, height / h)
    bx = b * factor
    hy = h * factor
    ox = x + (width - bx) / 2
    oy = y + (height - hy) / 2
    pdf.setLineWidth(0.8)
    if ptype == "I":
        flange = min(tf * factor, hy / 3)
        web = min(tw * factor, bx / 3)
        pdf.rect(ox, oy, bx, flange, stroke=1, fill=0)
        pdf.rect(ox, oy + hy - flange, bx, flange, stroke=1, fill=0)
        pdf.rect(ox + (bx - web) / 2, oy + flange, web, hy - 2 * flange, stroke=1, fill=0)
    elif ptype in {"U", "C"}:
        flange = min(tf * factor, hy / 3)
        web = min(tw * factor, bx / 3)
        pdf.rect(ox, oy, web, hy, stroke=1, fill=0)
        pdf.rect(ox, oy, bx, flange, stroke=1, fill=0)
        pdf.rect(ox, oy + hy - flange, bx, flange, stroke=1, fill=0)
    elif ptype == "L":
        thickness = min(max(tf, tw) * factor, min(bx, hy) / 3)
        pdf.rect(ox, oy, thickness, hy, stroke=1, fill=0)
        pdf.rect(ox, oy, bx, thickness, stroke=1, fill=0)
    elif ptype in {"RU", "RO"}:
        diameter = min(bx, hy)
        pdf.circle(ox + bx / 2, oy + hy / 2, diameter / 2, stroke=1, fill=0)
        if ptype == "RO" and tf > 0:
            inner = max(0.0, diameter - 2 * tf * factor)
            if inner > 0:
                pdf.circle(ox + bx / 2, oy + hy / 2, inner / 2, stroke=1, fill=0)
    else:
        pdf.rect(ox, oy, bx, hy, stroke=1, fill=0)


def _draw_title_block(
    pdf: canvas.Canvas,
    part: CanonicalPart,
    template: DrawingTemplate,
    page_width: float,
    page_height: float,
    *,
    scale_label: str,
) -> None:
    margin = 10 * mm
    block_width = 116 * mm
    block_height = 43 * mm
    x0 = page_width - margin - block_width
    y0 = margin
    pdf.setLineWidth(0.55)
    pdf.rect(x0, y0, block_width, block_height, stroke=1, fill=0)
    split = x0 + 37 * mm
    pdf.line(split, y0, split, y0 + block_height)
    for offset in (11, 22, 32):
        pdf.line(split, y0 + offset * mm, x0 + block_width, y0 + offset * mm)

    if template.company_name:
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(x0 + 18.5 * mm, y0 + 31 * mm, template.company_name[:32])
    pdf.setFont("Helvetica", 6.4)
    if template.company_address:
        pdf.drawCentredString(x0 + 18.5 * mm, y0 + 25 * mm, template.company_address[:40])
    pdf.drawCentredString(x0 + 18.5 * mm, y0 + 8 * mm, f"CWS Convertor v{DEFAULT_CONVERTER_VERSION}")

    values = {
        "Onderwerp": _effective_title(part),
        "Project": part.product.project_name or template.project,
        "Opdrachtgever": part.product.client or template.client,
        "Positie": part.header.position_number or part.part_id,
        "Profiel": part.header.profile,
        "Materiaal": part.header.material,
        "Schaal": scale_label,
        "Status": part.drawing.drawing_status.upper() or template.default_status,
    }
    rows = [
        ("Onderwerp", y0 + 35.2 * mm, 8.0, True),
        ("Project", y0 + 25.2 * mm, 6.4, False),
        ("Opdrachtgever", y0 + 14.2 * mm, 6.4, False),
    ]
    for key, baseline, size, bold in rows:
        pdf.setFont("Helvetica", 5.4)
        pdf.drawString(split + 2 * mm, baseline + 3.2 * mm, key)
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(split + 2 * mm, baseline, str(values[key])[:70])

    y = y0 + 4.5 * mm
    right_width_mm = 79.0
    columns = [
        ("Pos", values["Positie"], 0.00, 0.20),
        ("Profiel", values["Profiel"], 0.20, 0.52),
        ("Materiaal", values["Materiaal"], 0.52, 0.70),
        ("Schaal", values["Schaal"], 0.70, 0.84),
        ("Status", values["Status"], 0.84, 1.00),
    ]
    for label, value, start_fraction, end_fraction in columns:
        x = split + start_fraction * right_width_mm * mm
        if start_fraction:
            pdf.line(x, y0, x, y0 + 11 * mm)
        pdf.setFont("Helvetica", 5)
        pdf.drawString(x + 1.2 * mm, y0 + 7.5 * mm, label)
        cell_width = (end_fraction - start_fraction) * right_width_mm * mm
        text = str(value)
        font_size = 6.2
        while font_size > 4.6 and stringWidth(text, "Helvetica-Bold", font_size) > cell_width - 2.4 * mm:
            font_size -= 0.3
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.drawString(x + 1.2 * mm, y, text[:32])


def _draw_part_table(
    pdf: canvas.Canvas,
    part: CanonicalPart,
    *,
    x: float,
    y: float,
    width: float,
) -> None:
    row_height = 8 * mm
    headers = ["Pos", "Profiel", "Materiaal", "Lengte", "Aantal", "Merk"]
    fractions = [0.12, 0.28, 0.18, 0.16, 0.12, 0.14]
    pdf.setLineWidth(0.45)
    pdf.rect(x, y, width, row_height * 2, stroke=1, fill=0)
    current = x
    positions = [x]
    for fraction in fractions[:-1]:
        current += width * fraction
        positions.append(current)
        pdf.line(current, y, current, y + row_height * 2)
    pdf.line(x, y + row_height, x + width, y + row_height)
    current = x
    for index, header in enumerate(headers):
        cell_width = width * fractions[index]
        pdf.setFont("Helvetica-Bold", 6)
        pdf.drawCentredString(current + cell_width / 2, y + row_height + 2.3 * mm, header)
        current += cell_width
    values = [
        part.header.position_number or part.part_id,
        part.header.profile,
        part.header.material,
        _fmt(float(part.header.length), 2),
        str(int(part.header.quantity or 1)),
        part.product.mark,
    ]
    current = x
    for index, value in enumerate(values):
        cell_width = width * fractions[index]
        pdf.setFont("Helvetica", 6.3)
        pdf.drawCentredString(current + cell_width / 2, y + 2.3 * mm, str(value)[:24])
        current += cell_width


def render_part_pdf(
    part: CanonicalPart,
    output_path: str | Path,
    *,
    template: DrawingTemplate | None = None,
) -> Path:
    """Render a deterministic, vector-only technical part drawing."""

    populate_dimension_graph(part, overwrite=True, strict=False)
    active = copy.deepcopy(template or DrawingTemplate())
    if part.drawing.sheet_format:
        active.sheet_format = part.drawing.sheet_format
    if part.drawing.orientation:
        active.orientation = part.drawing.orientation
    page_width, page_height = _page_size(active.sheet_format, active.orientation)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output), pagesize=(page_width, page_height), pageCompression=1)
    pdf.setTitle(_effective_title(part))
    pdf.setAuthor(active.company_name or PRODUCT_NAME)
    pdf.setSubject("Technical part drawing")
    pdf.setCreator(f"{PRODUCT_NAME} v{DEFAULT_CONVERTER_VERSION}")

    margin = 10 * mm
    title_height = 46 * mm
    table_height = 18 * mm
    table_y = margin + 47 * mm
    drawing_left = margin + 22 * mm
    drawing_bottom = margin + title_height + table_height + 18 * mm
    drawing_right = page_width - margin - 18 * mm
    drawing_top = page_height - margin - 16 * mm
    available_width = drawing_right - drawing_left
    available_height = drawing_top - drawing_bottom
    has_profile_end_view = part.header.profile_type.upper() not in {"", "B"}
    # Reserve a dedicated right-hand column for the profile cross-section.
    # Without this reservation, long slender profiles can geometrically overlap
    # the end view even though both individually fit inside the drawing area.
    section_reserve = 52 * mm if has_profile_end_view else 0.0
    main_available_width = max(available_width - section_reserve, 40 * mm)

    contour = _main_contour(part)
    bounds = _contour_bounds(contour, part)
    model_width = max(bounds[2] - bounds[0], 1e-6)
    model_height = max(bounds[3] - bounds[1], 1e-6)
    factor = min(main_available_width / model_width, available_height / model_height)
    factor *= 0.78
    origin = (
        drawing_left + (main_available_width - model_width * factor) / 2,
        drawing_bottom + (available_height - model_height * factor) / 2,
    )
    scale_ratio = 72.0 / 25.4 / factor if factor > 0 else 1.0
    common_scales = [1, 2, 2.5, 5, 10, 20, 25, 50, 100]
    denominator = min(common_scales, key=lambda value: abs(value - scale_ratio))
    scale_label = part.drawing.scale or f"1:{_fmt(float(denominator), 1)}"

    # Sheet border and heading.
    pdf.setLineWidth(0.8)
    pdf.rect(margin, margin, page_width - 2 * margin, page_height - 2 * margin, stroke=1, fill=0)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin + 4 * mm, page_height - margin - 8 * mm, _effective_title(part).upper())
    pdf.setFont("Helvetica", 6.5)
    pdf.drawRightString(page_width - margin - 4 * mm, page_height - margin - 7.5 * mm, f"Bron: {part.source_file}")

    # Drawing status is explicit. A reviewed drawing is not silently presented
    # as released, while a blocked concept remains unmistakably non-production.
    drawing_status = (part.drawing.drawing_status or "concept").strip().lower()
    watermark = ""
    if drawing_status in {"expired", "obsolete", "vervallen"}:
        watermark = "VERVALLEN - NIET GEBRUIKEN"
    elif not part.validation.production_export_allowed or drawing_status == "concept":
        watermark = "CONCEPT - NIET VOOR PRODUCTIE"
    elif drawing_status in {"review", "check", "ter controle"}:
        watermark = "TER CONTROLE - NIET VRIJGEGEVEN"
    if watermark:
        pdf.saveState()
        pdf.setFillColorRGB(0.82, 0.82, 0.82)
        pdf.setFont("Helvetica-Bold", 38 if len(watermark) > 27 else 42)
        pdf.translate(page_width / 2, page_height / 2)
        pdf.rotate(28)
        pdf.drawCentredString(0, 0, watermark)
        pdf.restoreState()

    pdf.setStrokeColorRGB(0, 0, 0)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setLineWidth(0.9)
    _draw_contour(pdf, contour, part, bounds=bounds, origin=origin, scale=factor)

    for hole in part.holes:
        hx, hy = _transform_point(hole.x, hole.q, bounds=bounds, origin=origin, scale=factor)
        radius = max(0.5, float(hole.diameter) * factor / 2)
        pdf.circle(hx, hy, radius, stroke=1, fill=0)
        pdf.setLineWidth(0.3)
        pdf.line(hx - radius * 1.3, hy, hx + radius * 1.3, hy)
        pdf.line(hx, hy - radius * 1.3, hx, hy + radius * 1.3)
        pdf.setLineWidth(0.9)

    px0, py0 = _transform_point(bounds[0], bounds[1], bounds=bounds, origin=origin, scale=factor)
    px1, py1 = _transform_point(bounds[2], bounds[3], bounds=bounds, origin=origin, scale=factor)
    _draw_horizontal_dimension(pdf, px0, px1, py0, py0 - 11 * mm, _fmt(model_width, active.decimal_places))
    _draw_vertical_dimension(pdf, py0, py1, px0, px0 - 12 * mm, _fmt(model_height, active.decimal_places))
    _draw_hole_position_dimensions(
        pdf,
        part,
        bounds=bounds,
        origin=origin,
        scale=factor,
        px0=px0,
        py0=py0,
        drawing_left=drawing_left,
        table_top=table_y + 16 * mm,
    )

    if part.holes:
        groups: dict[float, int] = {}
        for hole in part.holes:
            groups[round(float(hole.diameter), 3)] = groups.get(round(float(hole.diameter), 3), 0) + 1
        labels = [f"{count}x Ø{_fmt(diameter, active.decimal_places)}" for diameter, count in sorted(groups.items())]
        label = "; ".join(labels)
        anchor = part.holes[0]
        hx, hy = _transform_point(anchor.x, anchor.q, bounds=bounds, origin=origin, scale=factor)
        tx, ty = min(hx + 28 * mm, drawing_right - 30 * mm), min(hy + 20 * mm, drawing_top - 10 * mm)
        pdf.setLineWidth(0.45)
        pdf.line(hx, hy, tx, ty)
        pdf.line(tx, ty, tx + 18 * mm, ty)
        pdf.setFont("Helvetica", 7)
        pdf.drawString(tx + 1 * mm, ty + 1.3 * mm, label)

    radius_groups: dict[float, int] = {}
    for item in part.contours:
        for point in item.points:
            if point.radius > 0:
                key = round(float(point.radius), 3)
                radius_groups[key] = radius_groups.get(key, 0) + 1
    if radius_groups:
        labels = [
            (f"{count}x R {_fmt(value, active.decimal_places)}" if count > 1 else f"R {_fmt(value, active.decimal_places)}")
            for value, count in sorted(radius_groups.items())
        ]
        pdf.setFont("Helvetica", 7)
        pdf.drawString(drawing_left, drawing_top + 4 * mm, "Radii: " + ", ".join(labels))

    # For profiles, add a deterministic end view to convey the cross-section.
    if has_profile_end_view:
        _draw_profile_end_view(pdf, part, drawing_right - 48 * mm, drawing_top - 42 * mm, 40 * mm, 34 * mm)
        pdf.setFont("Helvetica", 6.5)
        pdf.drawCentredString(drawing_right - 28 * mm, drawing_top - 46 * mm, "Doorsnede")

    _draw_part_table(pdf, part, x=margin + 3 * mm, y=table_y, width=page_width - 2 * margin - 6 * mm)
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.drawString(margin + 3 * mm, table_y - 5 * mm, f"Totaal aantal keer uit te voeren: {int(part.header.quantity or 1)}")

    _draw_title_block(pdf, part, active, page_width, page_height, scale_label=scale_label)

    warnings = list(dict.fromkeys(part.validation.warnings + part.warnings))
    questions = [item for item in part.validation.unresolved_questions if item.status == "open"]
    if warnings or questions:
        x = margin + 3 * mm
        y = margin + 37 * mm
        pdf.setFont("Helvetica-Bold", 5.6)
        pdf.drawString(x, y, "Controlepunten:")
        pdf.setFont("Helvetica", 5.2)
        line = 0
        for text in warnings[:3] + [item.prompt for item in questions[:3]]:
            line += 1
            pdf.drawString(x, y - line * 3.7 * mm, f"- {str(text)[:115]}")

    pdf.showPage()
    pdf.save()
    return output


# ---------------------------------------------------------------------------
# Trusted PDF hash, embedding and import
# ---------------------------------------------------------------------------


def _canonical_pdf_object(obj: Any, seen: set[tuple[int, int]]) -> bytes:
    if isinstance(obj, IndirectObject):
        key = (int(obj.idnum), int(obj.generation))
        if key in seen:
            return b"<cycle>"
        seen.add(key)
        try:
            return _canonical_pdf_object(obj.get_object(), seen)
        finally:
            seen.remove(key)
    if obj is None or isinstance(obj, NullObject):
        return b"null"
    if isinstance(obj, (BooleanObject, bool)):
        return b"true" if bool(obj) else b"false"
    if isinstance(obj, (NumberObject, FloatObject, int, float)):
        return f"{float(obj):.12g}".encode("ascii")
    if isinstance(obj, (TextStringObject, str, NameObject)):
        return str(obj).encode("utf-8", errors="replace")
    if isinstance(obj, ByteStringObject):
        return bytes(obj)
    if isinstance(obj, StreamObject):
        dictionary = DictionaryObject({key: value for key, value in obj.items() if str(key) not in {"/Length", "/Filter", "/DecodeParms"}})
        return b"stream{" + _canonical_pdf_object(dictionary, seen) + b"}" + obj.get_data()
    if isinstance(obj, (ArrayObject, list, tuple)):
        return b"[" + b"|".join(_canonical_pdf_object(item, seen) for item in obj) + b"]"
    if isinstance(obj, (DictionaryObject, dict)):
        chunks = []
        for key in sorted(obj.keys(), key=lambda item: str(item)):
            if str(key) in {"/Metadata", "/PieceInfo", "/LastModified"}:
                continue
            chunks.append(str(key).encode("utf-8") + b":" + _canonical_pdf_object(obj[key], seen))
        return b"{" + b"|".join(chunks) + b"}"
    return repr(obj).encode("utf-8", errors="replace")


def visible_pdf_sha256(path: str | Path) -> str:
    """Hash visible page content and resources, excluding attachments/metadata."""

    reader = PdfReader(str(path))
    digest = hashlib.sha256()
    digest.update(VISIBLE_HASH_ALGORITHM.encode("ascii"))
    for page_number, page in enumerate(reader.pages, start=1):
        digest.update(f"page:{page_number}".encode("ascii"))
        digest.update(_canonical_pdf_object(page.mediabox, set()))
        digest.update(_canonical_pdf_object(page.cropbox, set()))
        digest.update(str(page.get("/Rotate", 0)).encode("ascii"))
        contents = page.get_contents()
        if contents is not None:
            digest.update(contents.get_data())
        resources = page.get("/Resources")
        if resources is not None:
            digest.update(_canonical_pdf_object(resources, set()))
    return digest.hexdigest()


def _xmp_packet(part: CanonicalPart, manifest: dict[str, Any]) -> bytes:
    # Values inserted here are hashes/identifiers produced by this application;
    # XML escaping still protects user-defined part IDs.
    from xml.sax.saxutils import escape

    fields = {
        "format": TRUSTED_PDF_FORMAT,
        "schemaVersion": part.schema_version,
        "softwareVersion": part.converter_version,
        "partId": part.part_id,
        "sourceSHA256": part.source_sha256,
        "canonicalSHA256": manifest["canonical_sha256"],
        "geometrySHA256": manifest["geometry_sha256"],
        "visibleSHA256": manifest["visible_sha256"],
    }
    properties = "\n".join(
        f"      <converter:{key}>{escape(str(value))}</converter:{key}>" for key, value in fields.items()
    )
    return (
        "<?xpacket begin='﻿' id='W5M0MpCehiHzreSzNTczkc9d'?>\n"
        "<x:xmpmeta xmlns:x='adobe:ns:meta/'>\n"
        "  <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>\n"
        "    <rdf:Description rdf:about='' xmlns:converter='https://local.nc1-step-ifc-converter/schema/pdf/1.0/'>\n"
        f"{properties}\n"
        "    </rdf:Description>\n"
        "  </rdf:RDF>\n"
        "</x:xmpmeta>\n"
        "<?xpacket end='w'?>"
    ).encode("utf-8")


def _attach_json(
    writer: PdfWriter,
    filename: str,
    data: bytes,
    *,
    description: str,
) -> DictionaryObject:
    from pypdf.generic import TextStringObject

    embedded = writer.add_attachment(filename, data)
    embedded.description = TextStringObject(description)
    embedded.associated_file_relationship = NameObject("/Data")
    embedded.subtype = NameObject("/application#2Fjson")
    return embedded.pdf_object


def create_trusted_pdf(
    part: CanonicalPart,
    output_path: str | Path,
    *,
    template: DrawingTemplate | None = None,
) -> PDFConversionResult:
    """Create a vector drawing with exact canonical JSON and integrity hashes."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    prepared = part.clone()
    prepared.schema_version = SCHEMA_VERSION
    prepared.converter_version = DEFAULT_CONVERTER_VERSION
    prepared.drawing = copy.deepcopy(prepared.drawing or CanonicalDrawingData())
    if not prepared.drawing.drawing_status:
        prepared.drawing.drawing_status = "released" if prepared.validation.production_export_allowed else "concept"
    populate_dimension_graph(prepared, overwrite=True, strict=False)

    with tempfile.TemporaryDirectory(prefix="trusted_pdf_") as folder:
        base = Path(folder) / "visible.pdf"
        render_part_pdf(prepared, base, template=template)
        visible_hash = visible_pdf_sha256(base)
        prepared.drawing.visible_content_sha256 = visible_hash
        prepared.properties.setdefault("trusted_pdf", {})
        prepared.properties["trusted_pdf"].update(
            {
                "format": TRUSTED_PDF_FORMAT,
                "visible_hash_algorithm": VISIBLE_HASH_ALGORITHM,
                "created_at": utc_now_iso(),
            }
        )
        prepared.validate()
        model_bytes = prepared.to_json_bytes(include_attachments=True)
        manifest = {
            "format": TRUSTED_PDF_FORMAT,
            "schema_version": prepared.schema_version,
            "software_version": prepared.converter_version,
            "part_id": prepared.part_id,
            "source_format": prepared.source_format,
            "source_sha256": prepared.source_sha256,
            "model_filename": TRUSTED_MODEL_NAME,
            "model_sha256": sha256_bytes(model_bytes),
            "canonical_sha256": prepared.semantic_sha256(include_attachments=True),
            "geometry_sha256": prepared.geometry_sha256(),
            "visible_sha256": visible_hash,
            "visible_hash_algorithm": VISIBLE_HASH_ALGORITHM,
            "created_at": utc_now_iso(),
        }
        manifest_bytes = json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        reader = PdfReader(str(base))
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        model_spec = _attach_json(
            writer,
            TRUSTED_MODEL_NAME,
            model_bytes,
            description="Exact canonical production model",
        )
        manifest_spec = _attach_json(
            writer,
            TRUSTED_MANIFEST_NAME,
            manifest_bytes,
            description="Trusted PDF integrity manifest",
        )
        writer.root_object[NameObject("/AF")] = ArrayObject([model_spec, manifest_spec])
        writer.add_metadata(
            {
                "/Title": _effective_title(prepared),
                "/Author": (template.company_name if template else "") or PRODUCT_NAME,
                "/Creator": f"{PRODUCT_NAME} v{DEFAULT_CONVERTER_VERSION}",
                "/Producer": f"{PRODUCT_NAME} v{DEFAULT_CONVERTER_VERSION}",
                "/ConverterFormat": TRUSTED_PDF_FORMAT,
                "/ConverterSchemaVersion": prepared.schema_version,
                "/ConverterPartID": prepared.part_id,
                "/ConverterCanonicalSHA256": manifest["canonical_sha256"],
                "/ConverterGeometrySHA256": manifest["geometry_sha256"],
                "/ConverterVisibleSHA256": visible_hash,
            }
        )
        writer.xmp_metadata = _xmp_packet(prepared, manifest)
        with output.open("wb") as handle:
            writer.write(handle)

    final_visible_hash = visible_pdf_sha256(output)
    if final_visible_hash != visible_hash:
        output.unlink(missing_ok=True)
        raise TrustedPDFError("Zichtbare PDF-hash veranderde tijdens het insluiten van converterdata")
    verification = load_trusted_pdf(output, strict=True)
    return PDFConversionResult(
        source=Path(part.source_file or part.part_id),
        outputs=[output],
        warnings=list(dict.fromkeys(prepared.warnings + prepared.validation.warnings)),
        details={
            "route": "canonical->vector-pdf+embedded-model",
            "mode": verification.mode,
            "manifest": verification.details.get("manifest", {}),
            "production_export_allowed": prepared.validation.production_export_allowed,
        },
    )


def _attachment_bytes(reader: PdfReader, name: str) -> bytes | None:
    values = reader.attachments.get(name)
    if not values:
        return None
    if len(values) != 1:
        raise TrustedPDFError(f"Trusted PDF bevat {len(values)} bijlagen met naam {name!r}")
    return bytes(values[0])


def load_trusted_pdf(path: str | Path, *, strict: bool = True) -> PDFAnalysisResult:
    source = Path(path)
    reader = PdfReader(str(source))
    model_bytes = _attachment_bytes(reader, TRUSTED_MODEL_NAME)
    manifest_bytes = _attachment_bytes(reader, TRUSTED_MANIFEST_NAME)
    if model_bytes is None or manifest_bytes is None:
        raise TrustedPDFError("Geen volledige Trusted Converter PDF-payload gevonden")
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        model_data = json.loads(model_bytes.decode("utf-8"))
    except Exception as exc:
        raise TrustedPDFError("Trusted PDF bevat ongeldige JSON-bijlagen") from exc
    if manifest.get("format") != TRUSTED_PDF_FORMAT:
        raise TrustedPDFError("Onbekend Trusted PDF-formaat")
    if sha256_bytes(model_bytes) != manifest.get("model_sha256"):
        raise TrustedPDFError("Checksum van converter-model.json klopt niet")
    part = CanonicalPart.from_dict(model_data)
    checks = {
        "canonical_sha256": part.semantic_sha256(include_attachments=True),
        "geometry_sha256": part.geometry_sha256(),
        "visible_sha256": visible_pdf_sha256(source),
    }
    for key, value in checks.items():
        if value != manifest.get(key):
            raise TrustedPDFError(f"Trusted PDF-controle mislukt voor {key}")
    if part.drawing.visible_content_sha256 and part.drawing.visible_content_sha256 != checks["visible_sha256"]:
        raise TrustedPDFError("Zichtbare PDF-hash wijkt af van de canonieke tekeningdata")
    if manifest.get("source_sha256", "") != part.source_sha256:
        raise TrustedPDFError("Bronhash in manifest en canoniek model zijn niet gelijk")
    part.import_method = "trusted_exact"
    part.recognition.update({"method": "trusted PDF payload", "confidence": 1.0})
    part.refresh_export_gate()
    result = PDFAnalysisResult(
        source=source,
        source_sha256=sha256_file(source),
        mode="trusted_exact",
        part=part,
        pages=[],
        detected_fields={
            "part_id": part.part_id,
            "profile": part.header.profile,
            "material": part.header.material,
            "quantity": part.header.quantity,
            "length": part.header.length,
        },
        warnings=[],
        errors=[],
        details={"manifest": manifest, "checks": checks},
    )
    return result


# ---------------------------------------------------------------------------
# External PDF analysis
# ---------------------------------------------------------------------------


def _sheet_format(width_pt: float, height_pt: float) -> str:
    actual = sorted((float(width_pt), float(height_pt)))
    best = "CUSTOM"
    error = float("inf")
    for name, size in _PAGE_SIZES.items():
        candidate = sorted(size)
        relative = max(abs(actual[0] - candidate[0]) / candidate[0], abs(actual[1] - candidate[1]) / candidate[1])
        if relative < error:
            best, error = name, relative
    return best if error <= 0.035 else "CUSTOM"


def _extract_lines(words: list[tuple], page_number: int) -> list[_LineRecord]:
    grouped: dict[tuple[int, int], list[tuple]] = {}
    for word in words:
        if len(word) < 8:
            continue
        grouped.setdefault((int(word[5]), int(word[6])), []).append(word)
    lines: list[_LineRecord] = []
    for key in sorted(grouped):
        items = sorted(grouped[key], key=lambda item: int(item[7]))
        text = " ".join(str(item[4]) for item in items).strip()
        bbox = [
            min(float(item[0]) for item in items),
            min(float(item[1]) for item in items),
            max(float(item[2]) for item in items),
            max(float(item[3]) for item in items),
        ]
        if text:
            lines.append(_LineRecord(text=text, bbox=bbox, page=page_number))
    return lines


def _normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("×", "x").replace("ø", "Ø")).strip()


def _float_text(value: str) -> float:
    return float(value.replace(" ", "").replace(",", "."))


def _find_line(lines: Sequence[_LineRecord], pattern: re.Pattern[str]) -> tuple[re.Match[str], _LineRecord] | None:
    for line in lines:
        match = pattern.search(_normalise_text(line.text))
        if match:
            return match, line
    return None


def _parse_profile(profile: str) -> dict[str, Any]:
    value = profile.upper().replace("×", "*").replace("X", "*")
    result: dict[str, Any] = {"designation": profile}
    match = re.fullmatch(r"(?:STRIP|PL|PLAAT)\s*(\d+(?:[.,]\d+)?)\s*\*\s*(\d+(?:[.,]\d+)?)", value)
    if match:
        thickness = _float_text(match.group(1))
        width = _float_text(match.group(2))
        result.update(
            {
                "profile_type": "B",
                "plate_thickness_mm": thickness,
                "width_mm": width,
                "dim1": width,
                "dim2": thickness,
            }
        )
        return result
    if value.startswith(("HEA", "HEB", "HEM", "IPE", "IPN")):
        result["profile_type"] = "I"
    elif value.startswith(("UPN", "UNP", "UPE", "U")):
        result["profile_type"] = "U"
    elif value.startswith(("RHS", "SHS", "KOKER")):
        result["profile_type"] = "M"
    elif value.startswith(("CHS", "RO")):
        result["profile_type"] = "RO"
    elif re.fullmatch(r"D\s*\d+(?:[.,]\d+)?", value):
        result["profile_type"] = "RU"
    elif value.startswith("L"):
        result["profile_type"] = "L"
    return result


_TABLE_ROW_RE = re.compile(
    r"\b(?P<position>[A-Za-z][A-Za-z0-9_.-]{1,20})\s+"
    r"(?P<profile>(?:STRIP|PL|PLAAT|HEA|HEB|HEM|IPE|IPN|UPN|UNP|UPE|RHS|SHS|CHS|KOKER|D|L)[A-Za-z0-9*×x/.,-]*)\s+"
    r"(?P<material>S\d{3}[A-Za-z0-9+.-]*)\s+"
    r"(?P<length>\d+(?:[.,]\d+)?)\s+"
    r"(?P<quantity>\d+)\s+"
    r"(?P<mark>[A-Za-z0-9_.-]+)\b",
    re.IGNORECASE,
)
_SCALE_RE = re.compile(r"\b1\s*:\s*(\d+(?:[.,]\d+)?)\b")
_TOTAL_QTY_RE = re.compile(r"totaal\s+aantal(?:\s+keer\s+uit\s+te\s+voeren)?\s*[:=]?\s*(\d+)", re.IGNORECASE)
_HOLE_RE = re.compile(r"\b(\d+)\s*[x*]\s*Ø\s*(\d+(?:[.,]\d+)?)\b", re.IGNORECASE)
_RADIUS_RE = re.compile(r"\bR\s*(\d+(?:[.,]\d+)?)\b", re.IGNORECASE)
_MATERIAL_RE = re.compile(r"\bS\d{3}(?:JR|J0|J2|N|NL|M|ML|MC|NC|QL|Q)?\b", re.IGNORECASE)
_BARE_DIMENSION_SEQUENCE_RE = re.compile(
    r"^\s*-?\d+(?:[.,]\d+)?(?:\s+-?\d+(?:[.,]\d+)?){0,11}\s*$"
)
_PROFILE_RE = re.compile(
    r"\b(?:STRIP|PL|PLAAT|HEA|HEB|HEM|IPE|IPN|UPN|UNP|UPE|RHS|SHS|CHS|KOKER|D|L)[A-Za-z0-9*×x/.,-]+\b",
    re.IGNORECASE,
)


def _written_dimension_candidates(lines: Sequence[_LineRecord]) -> list[dict[str, Any]]:
    """Collect isolated written numbers without assigning them to geometry.

    This is intentionally a candidate list.  A number is not a production
    dimension until a deterministic dimension-line/feature relation or an
    explicit human confirmation exists.
    """

    result: list[dict[str, Any]] = []
    for line in lines:
        text = _normalise_text(line.text)
        if not _BARE_DIMENSION_SEQUENCE_RE.fullmatch(text):
            continue
        values = [_float_text(token) for token in text.split()]
        for token_index, value in enumerate(values):
            result.append(
                {
                    "value_mm_text": float(value),
                    "page": int(line.page),
                    "bbox": list(line.bbox),
                    "source_text": text,
                    "token_index": token_index,
                    "method": "isolated_vector_text_candidate",
                    "confidence": 0.35,
                    "status": "unlinked",
                }
            )
    return result


def _vector_paths(page: Any, page_number: int) -> list[_VectorPath]:
    result: list[_VectorPath] = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue
        result.append(
            _VectorPath(
                page=page_number,
                rect=[float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)],
                items=list(drawing.get("items") or []),
                close_path=bool(drawing.get("closePath", False)),
                fill=drawing.get("fill"),
                stroke=drawing.get("color"),
                width=float(drawing.get("width") or 0.0),
            )
        )
    return result


def _point_xy(value: Any) -> np.ndarray:
    if hasattr(value, "x") and hasattr(value, "y"):
        return np.asarray((float(value.x), float(value.y)), dtype=float)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return np.asarray((float(value[0]), float(value[1])), dtype=float)
    raise TypeError(f"Onbekend PDF-punttype: {type(value)!r}")


def _path_segments(path: _VectorPath) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for item in path.items:
        if not item:
            continue
        kind = str(item[0]).lower()
        if kind == "l" and len(item) >= 3:
            segments.append({"kind": "line", "start": _point_xy(item[1]), "end": _point_xy(item[2])})
        elif kind == "c" and len(item) >= 5:
            segments.append(
                {
                    "kind": "cubic",
                    "p0": _point_xy(item[1]),
                    "p1": _point_xy(item[2]),
                    "p2": _point_xy(item[3]),
                    "p3": _point_xy(item[4]),
                }
            )
        elif kind == "re" and len(item) >= 2:
            rect = item[1]
            corners = [
                np.asarray((float(rect.x0), float(rect.y0))),
                np.asarray((float(rect.x1), float(rect.y0))),
                np.asarray((float(rect.x1), float(rect.y1))),
                np.asarray((float(rect.x0), float(rect.y1))),
            ]
            for index in range(4):
                segments.append({"kind": "line", "start": corners[index], "end": corners[(index + 1) % 4]})
        elif kind == "qu" and len(item) >= 2:
            quad = item[1]
            points = [_point_xy(getattr(quad, name)) for name in ("ul", "ur", "lr", "ll")]
            for index in range(4):
                segments.append({"kind": "line", "start": points[index], "end": points[(index + 1) % 4]})
    return segments


def _cubic_point(segment: dict[str, Any], t: float) -> np.ndarray:
    one = 1.0 - t
    return (
        one**3 * segment["p0"]
        + 3 * one**2 * t * segment["p1"]
        + 3 * one * t**2 * segment["p2"]
        + t**3 * segment["p3"]
    )


def _circle_from_three_points(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> tuple[np.ndarray, float] | None:
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(float(d)) < 1e-9:
        return None
    aa = float(np.dot(a, a))
    bb = float(np.dot(b, b))
    cc = float(np.dot(c, c))
    ux = (aa * (b[1] - c[1]) + bb * (c[1] - a[1]) + cc * (a[1] - b[1])) / d
    uy = (aa * (c[0] - b[0]) + bb * (a[0] - c[0]) + cc * (b[0] - a[0])) / d
    center = np.asarray((ux, uy), dtype=float)
    return center, float(np.linalg.norm(a - center))


def _is_closed_segments(segments: Sequence[dict[str, Any]], tolerance: float = 1.0) -> bool:
    if not segments:
        return False
    first = segments[0].get("start", segments[0].get("p0"))
    last = segments[-1].get("end", segments[-1].get("p3"))
    return float(np.linalg.norm(np.asarray(first) - np.asarray(last))) <= tolerance


def _candidate_outline_path(
    paths: Sequence[_VectorPath],
    *,
    page_width: float,
    page_height: float,
    expected_ratio: float | None,
) -> _VectorPath | None:
    candidates: list[tuple[float, _VectorPath]] = []
    page_area = page_width * page_height
    for path in paths:
        width, height = path.width_pt, path.height_pt
        area = width * height
        segments = _path_segments(path)
        if width < 18 or height < 12 or area > page_area * 0.55:
            continue
        if path.rect[0] < 4 and path.rect[1] < 4 and path.rect[2] > page_width - 4 and path.rect[3] > page_height - 4:
            continue
        if len(segments) < 3 or not (_is_closed_segments(segments) or path.close_path):
            continue
        aspect = max(width, height) / max(min(width, height), 1e-9)
        ratio_score = 1.0
        if expected_ratio:
            ratio_score = math.exp(-abs(math.log(max(aspect, 1e-9) / max(expected_ratio, 1e-9))))
        complexity = min(1.0, len(segments) / 8.0)
        score = math.sqrt(area / page_area) * 3.0 + ratio_score * 2.0 + complexity
        candidates.append((score, path))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def _outline_from_vector_path(
    path: _VectorPath,
    *,
    model_length: float,
    model_width: float,
) -> tuple[CanonicalContour | None, dict[str, Any], list[str]]:
    segments = _path_segments(path)
    warnings: list[str] = []
    if not segments:
        return None, {}, ["Geselecteerde vectorcontour bevat geen ondersteunde lijn-/boogsegmenten."]
    rect_width = path.width_pt
    rect_height = path.height_pt
    orientations = [
        (model_length / rect_width, model_width / rect_height, False),
        (model_length / rect_height, model_width / rect_width, True),
    ]
    sx, sy, swap = min(orientations, key=lambda item: abs(item[0] - item[1]) / max(item[0], item[1]))
    mismatch = abs(sx - sy) / max(sx, sy)
    if mismatch > 0.035:
        return None, {"scale_x_mm_per_pt": sx, "scale_y_mm_per_pt": sy, "mismatch": mismatch}, [
            "Vectorcontour en geschreven hoofdafmetingen geven geen consistente schaal."
        ]
    scale = (sx + sy) / 2.0
    x0, y0, _x1, _y1 = path.rect

    def convert(point: np.ndarray) -> np.ndarray:
        local = np.asarray((point[0] - x0, path.rect[3] - point[1]), dtype=float) * scale
        return local[::-1] if swap else local

    points: list[CanonicalContourPoint] = []
    count = len(segments)
    for index, segment in enumerate(segments):
        if segment["kind"] == "cubic":
            p0 = segment["p0"]
            p3 = segment["p3"]
            midpoint = _cubic_point(segment, 0.5)
            circle = _circle_from_three_points(p0, midpoint, p3)
            tangent_start = segment["p1"] - p0
            tangent_end = p3 - segment["p2"]
            corner = _line_intersection(p0, tangent_start, p3, tangent_end)
            if circle is None or corner is None:
                warnings.append("Een PDF-Bezierboog kon niet betrouwbaar als cirkelboog worden gefit.")
                points.append(CanonicalContourPoint(x=float(convert(p3)[0]), q=float(convert(p3)[1])))
                continue
            _center, radius_pt = circle
            converted = convert(corner)
            radius_mm = radius_pt * scale
            points.append(
                CanonicalContourPoint(
                    x=float(converted[0]),
                    q=float(converted[1]),
                    radius=float(radius_mm),
                )
            )
        elif segment["kind"] == "line":
            next_segment = segments[(index + 1) % count]
            if next_segment["kind"] == "cubic":
                continue
            converted = convert(segment["end"])
            points.append(CanonicalContourPoint(x=float(converted[0]), q=float(converted[1])))

    # For a closed path the loop above yields theoretical line/arc vertices.
    # Inserting the first PDF start point would add a tangent point next to a
    # rounded corner and would make the radius geometrically impossible.
    if not (_is_closed_segments(segments) or path.close_path):
        start_pdf = segments[0].get("start", segments[0].get("p0"))
        start = convert(np.asarray(start_pdf))
        if not points or math.hypot(points[0].x - start[0], points[0].q - start[1]) > 0.1:
            points.insert(0, CanonicalContourPoint(x=float(start[0]), q=float(start[1])))

    compact: list[CanonicalContourPoint] = []
    for point in points:
        if compact and math.hypot(compact[-1].x - point.x, compact[-1].q - point.q) < 0.05:
            compact[-1].radius = max(compact[-1].radius, point.radius)
            continue
        compact.append(point)
    if len(compact) > 2 and math.hypot(compact[0].x - compact[-1].x, compact[0].q - compact[-1].q) < 0.05:
        compact.pop()
    if len(compact) < 3:
        return None, {"scale_mm_per_pt": scale, "mismatch": mismatch}, warnings + [
            "Vectorcontour bevat na vereenvoudiging minder dan drie punten."
        ]
    return (
        CanonicalContour(kind="AK", face="v", points=compact),
        {"scale_mm_per_pt": scale, "mismatch": mismatch, "swapped_axes": swap},
        warnings,
    )


def _detect_vector_holes(
    paths: Sequence[_VectorPath],
    outline: _VectorPath,
    *,
    scale_mm_per_pt: float,
    swapped_axes: bool,
    expected_diameters: Sequence[float],
) -> list[CanonicalHole]:
    result: list[CanonicalHole] = []
    ox0, oy0, ox1, oy1 = outline.rect
    for path in paths:
        if path is outline:
            continue
        width, height = path.width_pt, path.height_pt
        if min(width, height) < 2 or max(width, height) > min(outline.width_pt, outline.height_pt) * 0.45:
            continue
        if not (ox0 <= path.rect[0] and oy0 <= path.rect[1] and path.rect[2] <= ox1 and path.rect[3] <= oy1):
            continue
        circularity = abs(width - height) / max(width, height)
        segments = _path_segments(path)
        curve_count = sum(item["kind"] == "cubic" for item in segments)
        if circularity > 0.12 or curve_count < 2:
            continue
        center_pdf = np.asarray(((path.rect[0] + path.rect[2]) / 2, (path.rect[1] + path.rect[3]) / 2))
        local = np.asarray((center_pdf[0] - ox0, oy1 - center_pdf[1])) * scale_mm_per_pt
        if swapped_axes:
            local = local[::-1]
        measured = (width + height) / 2 * scale_mm_per_pt
        diameter = measured
        if expected_diameters:
            best = min(expected_diameters, key=lambda value: abs(value - measured))
            if abs(best - measured) <= max(0.6, best * 0.08):
                diameter = best
        candidate = CanonicalHole(face="v", x=float(local[0]), q=float(local[1]), diameter=float(diameter))
        if not any(
            abs(item.x - candidate.x) < 0.2
            and abs(item.q - candidate.q) < 0.2
            and abs(item.diameter - candidate.diameter) < 0.2
            for item in result
        ):
            result.append(candidate)
    return result


def _critical_missing(part: CanonicalPart) -> list[str]:
    missing: list[str] = []
    if not (part.header.position_number or part.part_id):
        missing.append("position")
    if not part.header.profile:
        missing.append("profile")
    if not part.header.material:
        missing.append("material")
    if part.header.length <= 0:
        missing.append("length")
    if part.header.profile_type == "B" and part.header.dim2 <= 0:
        missing.append("plate_thickness")
    if not _main_contour(part):
        missing.append("outer_contour")
    expected_holes = int(part.properties.get("drawing_callouts", {}).get("hole_count", 0) or 0)
    if expected_holes and len(part.holes) != expected_holes:
        missing.append("hole_positions")
    if part.header.profile_type == "B" and not part.properties.get("reference_side"):
        missing.append("reference_side")
    return missing


def _question_for_missing(name: str) -> CanonicalQuestion:
    prompts = {
        "position": "Wat is het onderdeel-/positienummer?",
        "profile": "Welk profiel of welke plaatmaat geldt voor dit onderdeel?",
        "material": "Welke materiaalkwaliteit geldt voor dit onderdeel?",
        "length": "Wat is de exacte productielengte in millimeters?",
        "plate_thickness": "Wat is de exacte plaatdikte in millimeters?",
        "outer_contour": "Welke gesloten buitencontour hoort bij het productieonderdeel?",
        "hole_positions": "Bevestig de exacte posities en referentiezijde van alle gaten.",
        "reference_side": "Welke plaatzijde en oorsprong gelden als DSTV-productiereferentie?",
    }
    return CanonicalQuestion(
        question_id=f"pdf-missing-{name}",
        field_path=name,
        prompt=prompts.get(name, f"Bevestig het kritische gegeven {name}."),
        reason="Het kritische gegeven kon niet betrouwbaar uit de externe PDF worden bepaald.",
    )


def _apply_ai_advice(part: CanonicalPart, interpretation: AIInterpretation) -> None:
    suggestions = part.properties.setdefault("ai_suggestions", [])
    for item in interpretation.fields:
        suggestions.append(asdict(item))
        path = f"ai.{item.field_path}"
        part.set_evidence(
            path,
            CanonicalEvidence(
                value=item.value,
                page=item.page,
                method=f"ai:{interpretation.provider}:{interpretation.model}",
                confidence=item.confidence,
                status="automatic",
                source_text=item.source_text,
                notes=[item.reason] if item.reason else [],
            ),
        )
    for index, item in enumerate(interpretation.questions, start=1):
        part.add_question(
            CanonicalQuestion(
                question_id=f"ai-{interpretation.provider}-{index}-{re.sub(r'[^a-z0-9]+', '-', item.field_path.lower()).strip('-')}",
                field_path=item.field_path,
                prompt=item.question,
                severity=item.severity,
                alternatives=item.alternatives,
                page=item.page,
                reason=item.reason,
            )
        )
    part.validation.warnings.extend(interpretation.warnings)
    part.refresh_export_gate()


def analyze_external_pdf(
    path: str | Path,
    *,
    ai_settings: AISettings | None = None,
) -> PDFAnalysisResult:
    try:
        import pymupdf
    except Exception as exc:
        raise PDFSupportError("PyMuPDF ontbreekt; externe PDF-analyse is niet beschikbaar") from exc

    source = Path(path)
    document = pymupdf.open(source)
    pages: list[PDFPageAnalysis] = []
    all_lines: list[_LineRecord] = []
    all_paths: list[_VectorPath] = []
    try:
        for index, page in enumerate(document, start=1):
            words = page.get_text("words", sort=True)
            lines = _extract_lines(words, index)
            all_lines.extend(lines)
            paths = _vector_paths(page, index)
            all_paths.extend(paths)
            image_count = len(page.get_images(full=True))
            classification = "hybrid" if paths and image_count else "vector" if paths else "raster" if image_count else "text_only"
            text = page.get_text("text", sort=True)
            quality = min(
                1.0,
                0.20
                + min(0.35, len(words) / 400)
                + min(0.35, len(paths) / 250)
                + (0.1 if classification in {"vector", "hybrid"} else 0.0),
            )
            pages.append(
                PDFPageAnalysis(
                    page=index,
                    classification=classification,
                    width_pt=float(page.rect.width),
                    height_pt=float(page.rect.height),
                    sheet_format=_sheet_format(page.rect.width, page.rect.height),
                    orientation="landscape" if page.rect.width > page.rect.height else "portrait",
                    word_count=len(words),
                    vector_path_count=len(paths),
                    image_count=image_count,
                    quality_score=quality,
                    text=text,
                )
            )
    finally:
        document.close()

    normalized_lines = [_LineRecord(_normalise_text(line.text), line.bbox, line.page) for line in all_lines]
    detected: dict[str, Any] = {}
    evidence: dict[str, CanonicalEvidence] = {}
    warnings: list[str] = []
    conflicts: list[str] = []

    table = _find_line(normalized_lines, _TABLE_ROW_RE)
    if table:
        match, line = table
        values = match.groupdict()
        detected.update(
            {
                "position": values["position"],
                "profile": values["profile"],
                "material": values["material"].upper(),
                "length": _float_text(values["length"]),
                "quantity": int(values["quantity"]),
                "mark": values["mark"],
            }
        )
        for key, value in detected.items():
            evidence[key] = CanonicalEvidence(
                value=value,
                page=line.page,
                bbox=line.bbox,
                method="vector_text_table_row",
                confidence=0.98,
                status="automatic",
                source_text=line.text,
            )
    else:
        profile = _find_line(normalized_lines, _PROFILE_RE)
        material = _find_line(normalized_lines, _MATERIAL_RE)
        if profile:
            match, line = profile
            detected["profile"] = match.group(0)
            evidence["profile"] = CanonicalEvidence(
                value=match.group(0), page=line.page, bbox=line.bbox, method="vector_text_regex", confidence=0.88, source_text=line.text
            )
        if material:
            match, line = material
            detected["material"] = match.group(0).upper()
            evidence["material"] = CanonicalEvidence(
                value=match.group(0).upper(), page=line.page, bbox=line.bbox, method="vector_text_regex", confidence=0.90, source_text=line.text
            )

    scale_match = _find_line(normalized_lines, _SCALE_RE)
    if scale_match:
        match, line = scale_match
        detected["scale"] = f"1:{_fmt(_float_text(match.group(1)), 2)}"
        evidence["scale"] = CanonicalEvidence(
            value=detected["scale"], page=line.page, bbox=line.bbox, method="vector_text_regex", confidence=0.96, source_text=line.text
        )
    total_match = _find_line(normalized_lines, _TOTAL_QTY_RE)
    if total_match:
        match, line = total_match
        detected["total_quantity"] = int(match.group(1))
        evidence["total_quantity"] = CanonicalEvidence(
            value=detected["total_quantity"], page=line.page, bbox=line.bbox, method="vector_text_regex", confidence=0.98, source_text=line.text
        )
        if "quantity" in detected and detected["quantity"] != detected["total_quantity"]:
            conflicts.append("quantity")
            warnings.append("Stukregelaantal en totaal aantal zijn niet gelijk.")

    hole_callouts: list[dict[str, Any]] = []
    radius_callouts: list[dict[str, Any]] = []
    for line in normalized_lines:
        for match in _HOLE_RE.finditer(line.text):
            hole_callouts.append(
                {
                    "count": int(match.group(1)),
                    "diameter_mm": _float_text(match.group(2)),
                    "page": line.page,
                    "bbox": line.bbox,
                    "source_text": line.text,
                }
            )
        for match in _RADIUS_RE.finditer(line.text):
            radius_callouts.append(
                {
                    "radius_mm": _float_text(match.group(1)),
                    "page": line.page,
                    "bbox": line.bbox,
                    "source_text": line.text,
                }
            )
    if hole_callouts:
        detected["hole_callouts"] = hole_callouts
    if radius_callouts:
        detected["radius_callouts"] = radius_callouts
    dimension_candidates = _written_dimension_candidates(normalized_lines)
    if dimension_candidates:
        # Keep only source text/value/page in the public field summary.  PDF
        # coordinates stay in the canonical provenance data for local review.
        detected["written_dimension_candidates"] = [
            {
                "value_mm_text": item["value_mm_text"],
                "page": item["page"],
                "source_text": item["source_text"],
                "status": item["status"],
            }
            for item in dimension_candidates
        ]

    # Subject/title heuristic: high-information uppercase line, excluding labels.
    labels = {
        "POS PROFIEL MATERIAAL LENGTE AANTAL MERK",
        "ONDERWERP:",
        "PROJECT:",
        "OPDRACHTGEVER:",
        "SCHAAL:",
        "GETEKEND:",
        "DATUM:",
        "STATUS:",
        "TEKENING:",
        "FORMAAT:",
    }
    title_candidates = []
    for line in normalized_lines:
        value = line.text.strip()
        letters = [char for char in value if char.isalpha()]
        if (
            4 <= len(value) <= 60
            and len(letters) >= 4
            and value.upper() == value
            and value not in labels
            and not _MATERIAL_RE.fullmatch(value)
            and not _PROFILE_RE.fullmatch(value)
        ):
            score = len(letters) + (6 if "PLAAT" in value or "LIGGER" in value or "KOLOM" in value else 0)
            title_candidates.append((score, line))
    if title_candidates:
        title_line = max(title_candidates, key=lambda item: item[0])[1]
        detected["subject"] = title_line.text
        evidence["subject"] = CanonicalEvidence(
            value=title_line.text, page=title_line.page, bbox=title_line.bbox, method="title_text_heuristic", confidence=0.78, source_text=title_line.text
        )

    profile_info = _parse_profile(str(detected.get("profile", ""))) if detected.get("profile") else {}
    header = CanonicalHeader(
        part_number=str(detected.get("position", "")),
        position_number=str(detected.get("position", "")),
        material=str(detected.get("material", "")),
        quantity=int(detected.get("quantity", detected.get("total_quantity", 1)) or 1),
        profile=str(detected.get("profile", "")),
        profile_type=str(profile_info.get("profile_type", "")),
        length=float(detected.get("length", 0.0) or 0.0),
        saw_length=float(detected.get("length", 0.0) or 0.0),
        dim1=float(profile_info.get("dim1", 0.0) or 0.0),
        dim2=float(profile_info.get("dim2", 0.0) or 0.0),
    )
    sheet = pages[0].sheet_format if pages else "A4"
    orientation = pages[0].orientation if pages else "landscape"
    part = CanonicalPart(
        converter_version=DEFAULT_CONVERTER_VERSION,
        source_format="PDF",
        source_file=source.name,
        source_sha256=sha256_file(source),
        imported_at=utc_now_iso(),
        import_method="vector" if any(item.classification in {"vector", "hybrid"} for item in pages) else "ocr_required",
        part_id=str(detected.get("position", source.stem)),
        header=header,
        product=CanonicalProductData(
            name=str(detected.get("subject", "")),
            mark=str(detected.get("mark", "")),
            material_code=header.material,
            material_grade=header.material,
            profile_designation=header.profile,
            length_mm=header.length,
            plate_thickness_mm=float(profile_info.get("plate_thickness_mm", 0.0) or 0.0),
            main_dimensions_mm=[value for value in (header.length, header.dim1, header.dim2) if value > 0],
        ),
        drawing=CanonicalDrawingData(
            scale=str(detected.get("scale", "")),
            sheet_format=sheet,
            orientation=orientation,
            title_block={"subject": str(detected.get("subject", ""))},
            drawing_status="concept",
        ),
        recognition={
            "method": "external PDF hybrid deterministic analysis",
            "confidence": 0.0,
            "production_export_allowed": False,
        },
        properties={
            "drawing_callouts": {
                "holes": hole_callouts,
                "hole_count": sum(int(item["count"]) for item in hole_callouts),
                "radii": radius_callouts,
                "dimension_candidates": dimension_candidates,
            },
            "nominal_stock_envelope": {
                "length_mm": header.length,
                "width_mm": float(profile_info.get("width_mm", 0.0) or 0.0),
                "thickness_mm": float(profile_info.get("plate_thickness_mm", 0.0) or 0.0),
            },
        },
        validation=CanonicalValidationData(
            warnings=warnings.copy(),
            errors=[],
            export_status="blocked",
            production_export_allowed=False,
        ),
    )
    for key, item in evidence.items():
        part.set_evidence(key, item)

    vector_details: dict[str, Any] = {}
    if header.profile_type == "B" and header.length > 0 and header.dim1 > 0 and pages:
        page_paths = [item for item in all_paths if item.page == 1]
        outline_path = _candidate_outline_path(
            page_paths,
            page_width=pages[0].width_pt,
            page_height=pages[0].height_pt,
            expected_ratio=max(header.length, header.dim1) / min(header.length, header.dim1),
        )
        if outline_path is not None:
            contour, calibration, vector_warnings = _outline_from_vector_path(
                outline_path,
                model_length=header.length,
                model_width=header.dim1,
            )
            warnings.extend(vector_warnings)
            part.validation.warnings.extend(vector_warnings)
            vector_details["outline_rect_pt"] = outline_path.rect
            vector_details["calibration"] = calibration
            if contour is not None:
                part.contours = [contour]
                part.set_evidence(
                    "contours[0]",
                    CanonicalEvidence(
                        value="vector contour",
                        page=1,
                        bbox=outline_path.rect,
                        method="pdf_vector_path_fit",
                        confidence=max(0.0, 0.96 - 4 * float(calibration.get("mismatch", 0.0))),
                        source_text="",
                    ),
                )
                expected_diameters = [float(item["diameter_mm"]) for item in hole_callouts]
                part.holes = _detect_vector_holes(
                    page_paths,
                    outline_path,
                    scale_mm_per_pt=float(calibration.get("scale_mm_per_pt", 0.0)),
                    swapped_axes=bool(calibration.get("swapped_axes", False)),
                    expected_diameters=expected_diameters,
                )
                for index, hole in enumerate(part.holes):
                    part.set_evidence(
                        f"holes[{index}]",
                        CanonicalEvidence(
                            value=asdict(hole),
                            page=1,
                            method="pdf_vector_circle_fit",
                            confidence=0.92 if expected_diameters else 0.84,
                            status="automatic",
                        ),
                    )
                    part.set_evidence(
                        f"holes[{index}].diameter",
                        CanonicalEvidence(
                            value=float(hole.diameter),
                            page=1,
                            method="pdf_vector_circle_fit",
                            confidence=0.92 if expected_diameters else 0.84,
                            status="automatic",
                        ),
                    )
                # A written diameter callout and a measured vector circle are
                # two independent evidence sources.  They must agree before a
                # production release; a human confirmation of the generic hole
                # alone may not silently resolve a diameter contradiction.
                expanded_expected = [
                    float(item["diameter_mm"])
                    for item in hole_callouts
                    for _ in range(max(0, int(item.get("count", 0))))
                ]
                unmatched_expected = list(expanded_expected)
                for index, hole in enumerate(part.holes):
                    if not unmatched_expected:
                        break
                    nearest = min(unmatched_expected, key=lambda value: abs(value - hole.diameter))
                    unmatched_expected.remove(nearest)
                    tolerance = max(0.6, abs(nearest) * 0.02)
                    field_path = f"holes[{index}].diameter"
                    if abs(float(hole.diameter) - nearest) <= tolerance:
                        item = part.field_evidence[field_path]
                        item.method = "pdf_vector_circle+text_callout_consistent"
                        item.confidence = max(item.confidence, 0.96)
                        item.notes.append(
                            f"Vectorcirkel en geschreven callout komen overeen binnen {tolerance:.2f} mm."
                        )
                    else:
                        conflicts.append(field_path)
                        message = (
                            f"Geschreven gatdiameter Ø{nearest:g} en gemeten vectorcirkel "
                            f"Ø{float(hole.diameter):.2f} zijn tegenstrijdig."
                        )
                        warnings.append(message)
                        item = part.field_evidence[field_path]
                        item.method = "pdf_vector_circle_vs_text_conflict"
                        item.confidence = min(item.confidence, 0.50)
                        item.notes.append(message)
                if part.contours:
                    radii_detected = sorted(round(point.radius, 2) for point in part.contours[0].points if point.radius > 0)
                    radii_expected = sorted(round(float(item["radius_mm"]), 2) for item in radius_callouts)
                    vector_details["detected_radii_mm"] = radii_detected
                    if radii_expected and not all(any(abs(actual - expected) <= 0.6 for actual in radii_detected) for expected in radii_expected):
                        conflicts.append("radii")
                        warnings.append("Vectorboogradii en geschreven radiuscallouts zijn niet volledig consistent.")
                if not conflicts and len(part.holes) == int(part.properties["drawing_callouts"]["hole_count"] or len(part.holes)):
                    part.properties["reference_side"] = "v: lower-left of primary plate view"
        else:
            warnings.append("Geen eenduidige gesloten hoofdcontour in de vectorlaag gevonden.")
            part.validation.warnings.append(warnings[-1])

    dimension_graph_report = populate_dimension_graph(part, overwrite=True, strict=False)
    missing = _critical_missing(part)
    for name in missing:
        part.add_question(_question_for_missing(name))
    for name in conflicts:
        part.add_question(
            CanonicalQuestion(
                question_id=f"pdf-conflict-{name}",
                field_path=name,
                prompt=f"Welke broninterpretatie voor {name.replace('_', ' ')} is correct?",
                reason="De externe PDF bevat tegenstrijdige tekst- of geometriegegevens.",
            )
        )

    critical_evidence_paths = {
        "position": "Bevestig het herkende onderdeel-/positienummer.",
        "profile": "Bevestig het herkende profiel en de plaatdikte.",
        "material": "Bevestig de herkende materiaalkwaliteit.",
        "length": "Bevestig de herkende productielengte.",
        "contours[0]": "Bevestig dat de gemarkeerde vectorcontour de volledige productiecontour is.",
    }
    for field_path, prompt in critical_evidence_paths.items():
        item = part.field_evidence.get(field_path)
        if item is not None and item.confidence < 0.95 and item.status != "confirmed":
            part.add_question(
                CanonicalQuestion(
                    question_id=f"pdf-review-{re.sub(r'[^a-z0-9]+', '-', field_path.lower()).strip('-')}",
                    field_path=field_path,
                    prompt=prompt,
                    severity="blocking",
                    page=item.page,
                    bbox=item.bbox,
                    reason=f"Confidence {item.confidence:.0%} ligt onder de automatische acceptatiegrens van 95%.",
                )
            )
    for field_path, item in list(part.field_evidence.items()):
        if field_path.startswith("holes[") and item.confidence < 0.95 and item.status != "confirmed":
            part.add_question(
                CanonicalQuestion(
                    question_id=f"pdf-review-{re.sub(r'[^a-z0-9]+', '-', field_path.lower()).strip('-')}",
                    field_path=field_path,
                    prompt="Bevestig gatdiameter, gatpositie en referentiezijde van dit gat.",
                    severity="blocking",
                    page=item.page,
                    bbox=item.bbox,
                    reason=f"Confidence {item.confidence:.0%} ligt onder de automatische acceptatiegrens van 95%.",
                )
            )

    # Deterministic consistency can release a vector plate only at very high
    # confidence; otherwise it remains a review item.
    critical_confidences = [
        item.confidence
        for key, item in part.field_evidence.items()
        if key in {"position", "profile", "material", "length", "contours[0]"} or key.startswith("holes[")
    ]
    min_confidence = min(critical_confidences) if critical_confidences else 0.0
    complete_geometry = (
        not missing
        and not conflicts
        and bool(part.contours)
        and not part.validation.blocking_questions()
    )
    if complete_geometry and min_confidence >= 0.95:
        part.recognition.update({"confidence": min_confidence, "production_export_allowed": True})
        part.validation.export_status = "validated"
        part.validation.production_export_allowed = True
        part.drawing.drawing_status = "review"
    else:
        part.recognition.update({"confidence": min_confidence, "production_export_allowed": False})
        part.validation.export_status = "blocked"
        part.validation.production_export_allowed = False
    part.refresh_export_gate()

    context = {
        "page_count": len(pages),
        "page_classification": [item.classification for item in pages],
        "sheet_format": sheet,
        "orientation": orientation,
        "detected_fields": detected,
        "missing_critical": missing,
        "conflicts": conflicts,
        "vector_path_count": sum(item.vector_path_count for item in pages),
        "image_count": sum(item.image_count for item in pages),
        "written_dimension_candidates": [
            {
                "value_mm_text": item["value_mm_text"],
                "page": item["page"],
                "source_text": item["source_text"],
            }
            for item in dimension_candidates[:80]
        ],
        "dimension_graph_summary": dimension_graph_report.to_dict(),
    }
    ai_result = None
    if ai_settings and ai_settings.provider.lower() not in {"", "none", "off"}:
        ai_result = interpret_drawing(source, deterministic_context=context, settings=ai_settings)
        _apply_ai_advice(part, ai_result)

    mode_types = {item.classification for item in pages}
    if "hybrid" in mode_types:
        mode = "external_hybrid"
    elif "vector" in mode_types:
        mode = "external_vector"
    elif "raster" in mode_types:
        mode = "external_raster_review"
    else:
        mode = "external_text_review"
    return PDFAnalysisResult(
        source=source,
        source_sha256=sha256_file(source),
        mode=mode,
        part=part,
        pages=pages,
        detected_fields=detected,
        warnings=list(dict.fromkeys(warnings + part.validation.warnings)),
        errors=list(part.validation.errors),
        ai=ai_result,
        details={
            "vector": vector_details,
            "missing_critical": missing,
            "conflicts": conflicts,
            "analysis_context": context,
            "dimension_graph": dimension_graph_report.to_dict(),
        },
    )


def _has_trusted_pdf_markers(path: str | Path) -> bool:
    """Return True when a PDF claims to be a Trusted Converter PDF.

    A damaged or partially stripped Trusted PDF must never be silently
    downgraded to an ordinary external drawing.  Presence of either converter
    attachment or converter metadata is therefore enough to make integrity
    failures fatal.
    """

    reader = PdfReader(str(path))
    attachment_names = set(reader.attachments)
    if attachment_names.intersection({TRUSTED_MODEL_NAME, TRUSTED_MANIFEST_NAME}):
        return True
    metadata = reader.metadata or {}
    return str(metadata.get("/ConverterFormat", "")) == TRUSTED_PDF_FORMAT


def analyze_pdf(
    path: str | Path,
    *,
    ai_settings: AISettings | None = None,
) -> PDFAnalysisResult:
    try:
        return load_trusted_pdf(path, strict=True)
    except TrustedPDFError:
        if _has_trusted_pdf_markers(path):
            raise
        return analyze_external_pdf(path, ai_settings=ai_settings)


# ---------------------------------------------------------------------------
# Human review / correction workflow for external PDF
# ---------------------------------------------------------------------------


def _set_review_value(part: CanonicalPart, field_path: str, value: Any) -> None:
    """Apply one explicitly reviewed value through a strict allowlist."""

    header_fields = {
        "order_number",
        "drawing_number",
        "part_number",
        "position_number",
        "material",
        "quantity",
        "profile",
        "profile_type",
        "length",
        "saw_length",
        "dim1",
        "dim2",
        "dim3",
        "dim4",
        "radius",
    }
    product_fields = set(CanonicalProductData.__dataclass_fields__)
    drawing_fields = {
        "scale",
        "sheet_format",
        "orientation",
        "projection_method",
        "drawing_status",
        "template_id",
        "company_style_id",
    }
    if field_path.startswith("header."):
        name = field_path.split(".", 1)[1]
        if name not in header_fields:
            raise ValueError(f"Review mag header-veld {name!r} niet wijzigen")
        current = getattr(part.header, name)
        if isinstance(current, int):
            value = int(value)
        elif isinstance(current, float):
            value = float(value)
        else:
            value = str(value)
        setattr(part.header, name, value)
        return
    if field_path.startswith("product."):
        name = field_path.split(".", 1)[1]
        if name not in product_fields:
            raise ValueError(f"Review mag productveld {name!r} niet wijzigen")
        current = getattr(part.product, name)
        if isinstance(current, int):
            value = int(value)
        elif isinstance(current, float):
            value = float(value)
        elif isinstance(current, list):
            value = list(value)
        else:
            value = str(value)
        setattr(part.product, name, value)
        return
    if field_path.startswith("drawing."):
        name = field_path.split(".", 1)[1]
        if name not in drawing_fields:
            raise ValueError(f"Review mag tekeningveld {name!r} niet wijzigen")
        setattr(part.drawing, name, int(value) if name in {"sheet_number", "sheet_count"} else str(value))
        return
    if field_path in {"reference_side", "properties.reference_side"}:
        part.properties["reference_side"] = str(value)
        return
    hole_match = re.fullmatch(r"holes\[(\d+)]\.(face|x|q|diameter|datum|operation|depth)", field_path)
    if hole_match:
        index, name = int(hole_match.group(1)), hole_match.group(2)
        if not 0 <= index < len(part.holes):
            raise IndexError(f"Gatindex {index} bestaat niet")
        current = getattr(part.holes[index], name)
        setattr(part.holes[index], name, float(value) if isinstance(current, float) else str(value))
        return
    point_match = re.fullmatch(r"contours\[(\d+)]\.points\[(\d+)]\.(x|q|radius|datum|notch)", field_path)
    if point_match:
        contour_index, point_index, name = int(point_match.group(1)), int(point_match.group(2)), point_match.group(3)
        if not 0 <= contour_index < len(part.contours):
            raise IndexError(f"Contourindex {contour_index} bestaat niet")
        points = part.contours[contour_index].points
        if not 0 <= point_index < len(points):
            raise IndexError(f"Contourpuntindex {point_index} bestaat niet")
        current = getattr(points[point_index], name)
        setattr(points[point_index], name, float(value) if isinstance(current, float) else str(value))
        return
    raise ValueError(f"Onbekend of niet-toegestaan reviewveld: {field_path!r}")


def _polygon_xy(contour: CanonicalContour) -> list[tuple[float, float]]:
    points = [(float(item.x), float(item.q)) for item in contour.points]
    if len(points) > 1 and math.dist(points[0], points[-1]) < 1e-7:
        points.pop()
    return points


def _polygon_signed_area(points: Sequence[tuple[float, float]]) -> float:
    return 0.5 * sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
    tolerance: float = 1e-8,
) -> bool:
    o1, o2, o3, o4 = _orientation(a, b, c), _orientation(a, b, d), _orientation(c, d, a), _orientation(c, d, b)
    return (o1 * o2 < -tolerance) and (o3 * o4 < -tolerance)


def _point_in_polygon(point: tuple[float, float], polygon: Sequence[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = previous
        x2, y2 = current
        if ((y1 > y) != (y2 > y)) and x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-30) + x1:
            inside = not inside
        previous = current
    return inside


def _distance_point_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    p = np.asarray(point, dtype=float)
    a = np.asarray(start, dtype=float)
    b = np.asarray(end, dtype=float)
    delta = b - a
    denominator = float(np.dot(delta, delta))
    if denominator <= 1e-12:
        return float(np.linalg.norm(p - a))
    factor = float(np.clip(np.dot(p - a, delta) / denominator, 0.0, 1.0))
    return float(np.linalg.norm(p - (a + factor * delta)))


def validate_reviewed_part(part: CanonicalPart) -> tuple[list[str], list[str]]:
    """Run deterministic document/geometry checks before release."""

    errors: list[str] = []
    warnings: list[str] = []
    missing = _critical_missing(part)
    if missing:
        errors.append("Kritische gegevens ontbreken: " + ", ".join(missing))
    for contour_index, contour in enumerate(part.contours):
        points = _polygon_xy(contour)
        if len(points) < 3:
            errors.append(f"Contour {contour_index + 1} heeft minder dan drie punten")
            continue
        area = _polygon_signed_area(points)
        if abs(area) <= 1e-6:
            errors.append(f"Contour {contour_index + 1} heeft nul oppervlak")
        count = len(points)
        for first in range(count):
            a, b = points[first], points[(first + 1) % count]
            for second in range(first + 1, count):
                if second in {first, (first + 1) % count} or (second + 1) % count in {first, (first + 1) % count}:
                    continue
                c, d = points[second], points[(second + 1) % count]
                if _segments_intersect(a, b, c, d):
                    errors.append(f"Contour {contour_index + 1} kruist zichzelf")
                    break
            if errors and errors[-1].endswith("kruist zichzelf"):
                break
        for index, point in enumerate(contour.points):
            if point.radius <= 0:
                continue
            previous = contour.points[index - 1]
            following = contour.points[(index + 1) % len(contour.points)]
            limit = 0.49 * min(math.hypot(point.x - previous.x, point.q - previous.q), math.hypot(point.x - following.x, point.q - following.q))
            if point.radius > limit + 0.1:
                errors.append(
                    f"Radius R{point.radius:g} bij contourpunt {index + 1} past niet binnen de aangrenzende segmenten"
                )
    outer = _main_contour(part)
    polygon = _polygon_xy(outer) if outer else []
    if polygon:
        for index, hole in enumerate(part.holes):
            center = (float(hole.x), float(hole.q))
            if hole.diameter <= 0:
                errors.append(f"Gat {index + 1} heeft geen geldige diameter")
                continue
            if not _point_in_polygon(center, polygon):
                errors.append(f"Gat {index + 1} ligt buiten de buitencontour")
                continue
            clearance = min(
                _distance_point_segment(center, polygon[edge], polygon[(edge + 1) % len(polygon)])
                for edge in range(len(polygon))
            )
            if clearance + 0.15 < hole.diameter / 2.0:
                errors.append(f"Gat {index + 1} snijdt de buitencontour")
    for first, hole in enumerate(part.holes):
        for second in range(first + 1, len(part.holes)):
            other = part.holes[second]
            if math.hypot(hole.x - other.x, hole.q - other.q) < 0.05 and abs(hole.diameter - other.diameter) < 0.05:
                errors.append(f"Gaten {first + 1} en {second + 1} zijn dubbel")
    if part.header.profile_type == "B" and min(part.header.length, part.header.dim1, part.header.dim2) <= 0:
        errors.append("Plaatlengte, plaatbreedte en plaatdikte moeten positief zijn")
    if part.header.quantity <= 0:
        errors.append("Aantal moet minimaal 1 zijn")
    graph_report = populate_dimension_graph(part, overwrite=True, strict=False)
    errors.extend(graph_report.errors)
    warnings.extend(graph_report.warnings)
    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))


def apply_review(
    analysis: PDFAnalysisResult,
    review: dict[str, Any],
) -> PDFAnalysisResult:
    """Apply explicit confirmations/corrections and recalculate the release gate."""

    result = copy.deepcopy(analysis)
    part = result.part
    reviewer = str(review.get("reviewed_by", "")).strip()
    if not reviewer:
        raise ValueError("Reviewbestand mist 'reviewed_by'")
    reviewed_at = utc_now_iso()
    for field_path, value in dict(review.get("values") or {}).items():
        _set_review_value(part, str(field_path), value)
        part.set_evidence(
            str(field_path),
            CanonicalEvidence(
                value=value,
                method="human_review",
                confidence=1.0,
                status="corrected",
                confirmed_by=reviewer,
                confirmed_at=reviewed_at,
            ),
        )
    confirmed = {str(item) for item in review.get("confirm", [])}
    for field_path in confirmed:
        evidence = part.field_evidence.get(field_path)
        if evidence is None:
            raise ValueError(f"Te bevestigen evidencepad bestaat niet: {field_path!r}")
        evidence.status = "confirmed"
        evidence.confidence = 1.0
        evidence.confirmed_by = reviewer
        evidence.confirmed_at = reviewed_at
    answers = dict(review.get("answers") or {})
    for question in part.validation.unresolved_questions:
        answer = answers.get(question.question_id)
        if answer is not None:
            value = answer.get("value") if isinstance(answer, dict) else answer
            if value is not None and value != "" and question.field_path in {"reference_side", "properties.reference_side"}:
                _set_review_value(part, question.field_path, value)
            question.answer = value
            question.status = "answered"
            question.answered_by = reviewer
            question.answered_at = reviewed_at
        elif question.field_path in confirmed:
            question.answer = part.field_evidence[question.field_path].value
            question.status = "answered"
            question.answered_by = reviewer
            question.answered_at = reviewed_at

    part.properties.setdefault("review", {})
    part.properties["review"].update(
        {
            "reviewed_by": reviewer,
            "reviewed_at": reviewed_at,
            "source_pdf_sha256": analysis.source_sha256,
            "comment": str(review.get("comment", "")),
        }
    )
    errors, warnings = validate_reviewed_part(part)
    open_questions = part.validation.blocking_questions()
    if open_questions:
        errors.append("Niet alle blokkerende reviewvragen zijn beantwoord")
    part.validation.errors = list(dict.fromkeys(errors))
    part.validation.warnings = list(dict.fromkeys(part.validation.warnings + warnings))
    if not part.validation.errors and not open_questions:
        part.recognition["production_export_allowed"] = True
        part.recognition["confidence"] = 1.0
        part.validation.export_status = "validated"
        part.validation.production_export_allowed = True
        part.drawing.drawing_status = "review"
    else:
        part.recognition["production_export_allowed"] = False
        part.validation.export_status = "blocked"
        part.validation.production_export_allowed = False
    part.refresh_export_gate()
    result.warnings = list(dict.fromkeys(result.warnings + part.validation.warnings))
    result.errors = list(part.validation.errors)
    result.mode = "external_reviewed" if part.validation.production_export_allowed else "external_review_incomplete"
    result.details["review"] = copy.deepcopy(part.properties["review"])
    result.details["dimension_graph"] = dict(part.properties.get("dimension_graph") or {})
    return result


def finalize_reviewed_analysis(
    reviewed: PDFAnalysisResult,
    output_pdf: str | Path,
    *,
    template: DrawingTemplate | None = None,
) -> PDFConversionResult:
    """Create a Trusted PDF from an already applied and validated human review.

    This entry point is used by the interactive GUI.  It deliberately does not
    analyse the source a second time (and therefore never repeats an optional
    cloud-AI request).  The same production gate, source hash and exact
    attachment checks as the file-based review route remain mandatory.
    """

    if not reviewed.production_export_allowed:
        raise ExternalPDFExportBlocked(
            "Review is nog niet volledig: "
            + " | ".join(
                reviewed.errors
                + [item.prompt for item in reviewed.part.validation.blocking_questions()]
            )
        )
    source = Path(reviewed.source)
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise FileNotFoundError(f"Externe bron-PDF ontbreekt: {source}")
    source_bytes = source.read_bytes()
    part = reviewed.part.clone()
    if len(source_bytes) <= 8 * 1024 * 1024:
        part.add_attachment("source_pdf", source.name, "application/pdf", source_bytes)
    part.source_format = "PDF"
    part.source_file = source.name
    part.source_sha256 = sha256_bytes(source_bytes)
    result = create_trusted_pdf(part, output_pdf, template=template)
    result.source = source
    result.details["route"] = "external-pdf->human-review->validated-canonical->trusted-pdf"
    result.details["review_mode"] = reviewed.mode
    return result


def review_external_pdf(
    input_pdf: str | Path,
    review_json: str | Path,
    output_pdf: str | Path,
    *,
    ai_settings: AISettings | None = None,
    template: DrawingTemplate | None = None,
) -> PDFConversionResult:
    analysis = analyze_external_pdf(input_pdf, ai_settings=ai_settings)
    review_data = json.loads(Path(review_json).read_text(encoding="utf-8"))
    reviewed = apply_review(analysis, review_data)
    return finalize_reviewed_analysis(reviewed, output_pdf, template=template)


# ---------------------------------------------------------------------------
# Canonical -> NC1 and strict conversion gates
# ---------------------------------------------------------------------------


def _ascii_safe(value: Any, fallback: str = "-") -> str:
    text = str(value or fallback).encode("ascii", errors="replace").decode("ascii")
    return text.strip() or fallback


def canonical_to_nc1(part: CanonicalPart, output_path: str | Path) -> Path:
    """Serialize validated canonical plate/profile data and re-read it strictly."""

    graph_report = populate_dimension_graph(part, overwrite=True, strict=False)
    if graph_report.errors:
        raise ExternalPDFExportBlocked(
            "Productie-export is geblokkeerd door de maatgrafiek: " + " | ".join(graph_report.errors)
        )
    if not part.refresh_export_gate():
        questions = [item.prompt for item in part.validation.blocking_questions()]
        raise ExternalPDFExportBlocked(
            "Productie-export is geblokkeerd"
            + (": " + " | ".join(questions) if questions else ".")
        )
    if not part.contours:
        raise ExternalPDFExportBlocked("Productie-export vereist ten minste één gesloten contour")
    header = part.header
    lines = [
        "ST",
        f"** Generated from validated canonical model by CWS Convertor v{DEFAULT_CONVERTER_VERSION}",
        f"  {_ascii_safe(header.order_number, 'PDF')}",
        f"  {_ascii_safe(header.drawing_number or header.position_number or part.part_id, 'PART')}",
        "  1",
        f"  {_ascii_safe(header.part_number or header.position_number or part.part_id, 'PART')}",
        f"  {_ascii_safe(header.material, 'S235JR')}",
        f"  {int(header.quantity or 1)}",
        f"  {_ascii_safe(header.profile, 'PROFILE')}",
        f"  {_ascii_safe(header.profile_type, 'B')}",
        f"  {float(header.length):9.2f},{float(header.saw_length or header.length):.2f}",
        f"  {float(header.dim1):9.2f}",
        f"  {float(header.dim2):9.2f}",
        f"  {float(header.dim3):9.2f}",
        f"  {float(header.dim4):9.2f}",
        f"  {float(header.radius):9.2f}",
        f"  {float(header.weight):8.3f}",
        f"  {float(header.paint_area):8.3f}",
        f"  {float(header.web_miter_front):8.3f}",
        f"  {float(header.web_miter_rear):8.3f}",
        f"  {float(header.flange_miter_front):8.3f}",
        f"  {float(header.flange_miter_rear):8.3f}",
        "",
        "",
        "",
        "",
    ]
    import converter as core

    for contour in part.contours:
        if len(contour.points) < 3:
            raise ExternalPDFExportBlocked("Contour bevat minder dan drie punten")
        lines.append("AK" if contour.kind.upper() not in {"IK", "INNER"} else "IK")
        points = list(contour.points)
        if math.hypot(points[0].x - points[-1].x, points[0].q - points[-1].q) > 0.01:
            points = points + [copy.deepcopy(points[0])]
        for index, point in enumerate(points):
            lines.append(
                core._ak_line(
                    contour.face if index == 0 else "",
                    round(float(point.x), 2),
                    "s" if index == 0 else point.datum,
                    round(float(point.q), 2),
                    point.notch,
                    round(float(point.radius), 2),
                )
            )
    if part.holes:
        lines.append("BO")
        for hole in sorted(part.holes, key=lambda item: (item.face, item.x, item.q, item.diameter)):
            lines.append(
                core._bo_line(
                    hole.face,
                    round(float(hole.x), 2),
                    "s" if not hole.datum else hole.datum,
                    round(float(hole.q), 2),
                    round(float(hole.diameter), 2),
                )
            )
    lines.append("EN")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\r\n".join(lines) + "\r\n", encoding="ascii", newline="")

    # Hard validation: parser + solid reconstruction + feature equality.
    from conversion import build_shape

    parsed = core.parse_nc1(target)
    shape = build_shape(parsed).val()
    if not shape.Solids() or shape.Volume() <= 1e-6:
        target.unlink(missing_ok=True)
        raise ValueError("NC1-roundtrip leverde geen geldige productie-solid")
    if parsed.header.profile != part.header.profile or parsed.header.profile_type != part.header.profile_type:
        target.unlink(missing_ok=True)
        raise ValueError("NC1-roundtrip veranderde profiel of profieltype")
    if len(parsed.holes) != len(part.holes):
        target.unlink(missing_ok=True)
        raise ValueError("NC1-roundtrip veranderde het aantal gaten")
    if len(parsed.contours) != len(part.contours):
        target.unlink(missing_ok=True)
        raise ValueError("NC1-roundtrip veranderde het aantal contouren")
    return target


def _trusted_or_validated(path: str | Path, *, ai_settings: AISettings | None = None) -> PDFAnalysisResult:
    analysis = analyze_pdf(path, ai_settings=ai_settings)
    if analysis.mode != "trusted_exact" and not analysis.production_export_allowed:
        raise ExternalPDFExportBlocked(
            "Externe PDF is nog niet productie-vrijgegeven. Openstaande vragen: "
            + " | ".join(item.prompt for item in analysis.part.validation.blocking_questions())
        )
    return analysis


def pdf_to_nc1(
    input_path: str | Path,
    output_path: str | Path,
    *,
    ai_settings: AISettings | None = None,
) -> PDFConversionResult:
    source, target = Path(input_path), Path(output_path)
    analysis = _trusted_or_validated(source, ai_settings=ai_settings)
    nc1_bytes = analysis.part.attachment_bytes("nc1")
    if nc1_bytes is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(nc1_bytes)
        import converter as core
        from conversion import build_shape

        parsed = core.parse_nc1(target)
        shape = build_shape(parsed).val()
        if shape.Volume() <= 1e-6:
            target.unlink(missing_ok=True)
            raise ValueError("Trusted PDF bevat een NC1-bijlage zonder geldige solid")
        route = "trusted-pdf->exact-nc1-attachment"
    else:
        canonical_to_nc1(analysis.part, target)
        route = "validated-pdf->canonical->nc1->validation"
    return PDFConversionResult(
        source=source,
        outputs=[target],
        warnings=analysis.warnings,
        details={"route": route, "pdf_mode": analysis.mode, "part_id": analysis.part.part_id},
    )


def pdf_to_step(
    input_path: str | Path,
    output_path: str | Path,
    *,
    ai_settings: AISettings | None = None,
) -> PDFConversionResult:
    source, target = Path(input_path), Path(output_path)
    analysis = _trusted_or_validated(source, ai_settings=ai_settings)
    step_bytes = analysis.part.attachment_bytes("step")
    if step_bytes is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(step_bytes)
        shape = cq.importers.importStep(str(target)).val()
        if shape.Volume() <= 1e-6:
            target.unlink(missing_ok=True)
            raise ValueError("Trusted PDF bevat een STEP-bijlage zonder geldige solid")
        route = "trusted-pdf->exact-step-attachment"
    else:
        from conversion import build_shape, convert_nc1_to_step

        with tempfile.TemporaryDirectory(prefix="pdf_to_step_") as folder:
            nc1 = canonical_to_nc1(analysis.part, Path(folder) / "validated.nc1")
            convert_nc1_to_step(nc1, target)
        route = "validated-pdf->canonical->nc1->analytic-step"
    return PDFConversionResult(source, [target], analysis.warnings, details={"route": route, "pdf_mode": analysis.mode})


def pdf_to_ifc(
    input_path: str | Path,
    output_path: str | Path,
    *,
    material: str = "S355JR",
    ai_settings: AISettings | None = None,
) -> PDFConversionResult:
    source, target = Path(input_path), Path(output_path)
    analysis = _trusted_or_validated(source, ai_settings=ai_settings)
    ifc_bytes = analysis.part.attachment_bytes("ifc")
    if ifc_bytes is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(ifc_bytes)
        route = "trusted-pdf->exact-ifc-attachment"
    else:
        from conversion import build_shape, convert_nc1_to_step
        from ifc_native import write_native_ifc
        from ifc_semantic import SemanticIFCError, write_semantic_plate_ifc
        from ifc_support import load_ifc_geometry
        from canonical_model import extract_part_from_ifc

        with tempfile.TemporaryDirectory(prefix="pdf_to_ifc_") as folder:
            # Preserve exact source attachments of Trusted PDFs.  Regenerating
            # an NC1/STEP intermediary and then overwriting the attachment in
            # ``export_part`` would make ``source_sha256`` disagree with the
            # source attachment and correctly trip the canonical integrity
            # check.  Use an exact NC1 attachment when it exists; otherwise
            # create a strictly validated NC1 from the reviewed canonical
            # model.
            nc1 = Path(folder) / "validated.nc1"
            exact_nc1 = analysis.part.attachment_bytes("nc1")
            if exact_nc1 is not None:
                nc1.write_bytes(exact_nc1)
                import converter as core

                parsed = core.parse_nc1(nc1)
                if build_shape(parsed).val().Volume() <= 1e-6:
                    raise ValueError("Trusted PDF bevat een NC1-bijlage zonder geldige solid")
            else:
                canonical_to_nc1(analysis.part, nc1)
            generated_step = Path(folder) / "validated.step"
            exact_step = analysis.part.attachment_bytes("step")
            if exact_step is not None:
                generated_step.write_bytes(exact_step)
            else:
                convert_nc1_to_step(nc1, generated_step)
            shape = cq.importers.importStep(str(generated_step)).val()
            if shape.Volume() <= 1e-6 or not shape.Solids():
                raise ValueError("PDF->IFC tussencontrole leverde geen geldige plaat-solid")

            export_part = analysis.part.clone()
            if export_part.attachment("nc1") is None:
                export_part.add_attachment("nc1", nc1.name, "application/x-dstv", nc1.read_bytes())
            # Keep an original STEP source attachment intact when the Trusted
            # PDF originated from STEP.  The generated STEP remains the
            # validated geometric intermediary, but it is not allowed to
            # replace the source attachment whose hash is part of provenance.
            if export_part.attachment("step") is None:
                export_part.add_attachment("step", generated_step.name, "model/step", generated_step.read_bytes())
            box = shape.BoundingBox()
            export_part.geometry.update(
                {
                    "volume_mm3": float(shape.Volume()),
                    "area_mm2": float(shape.Area()),
                    "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
                    "solids": len(shape.Solids()),
                }
            )

            semantic_error = ""
            if export_part.header.profile_type == "B":
                try:
                    write_semantic_plate_ifc(export_part, shape, target)
                    route = "validated-pdf->canonical->semantic-ifcplate-sweptsolid+payload"
                except SemanticIFCError as exc:
                    semantic_error = str(exc)
                    write_native_ifc(
                        shape,
                        target,
                        name=export_part.part_id or target.stem,
                        material=analysis.part.material or material,
                        canonical=export_part,
                    )
                    route = "validated-pdf->canonical->analytic-step->ifc-tessellation+payload-fallback"
            else:
                write_native_ifc(
                    shape,
                    target,
                    name=export_part.part_id or target.stem,
                    material=analysis.part.material or material,
                    canonical=export_part,
                )
                route = "validated-pdf->canonical->analytic-step->ifc-tessellation+payload"

            restored = extract_part_from_ifc(target, strict=True)
            if restored is None or restored.attachment_bytes("nc1") is None:
                target.unlink(missing_ok=True)
                raise ValueError("PDF->IFC payloadcontrole kon de exacte NC1-bijlage niet herstellen")
            preview = load_ifc_geometry(target)
            preview_volume = sum(item.volume_mm3 for item in preview.items)
            delta = (preview_volume - float(shape.Volume())) / float(shape.Volume()) * 100.0
            if abs(delta) > 1.0:
                target.unlink(missing_ok=True)
                raise ValueError(
                    f"PDF->IFC previewvolume wijkt {delta:+.6f}% af; grens is 1,0%"
                )
        warnings = list(analysis.warnings)
        if semantic_error:
            warnings.append(
                "Semantische IfcPlate/SweptSolid-route was niet toepasbaar; "
                f"veilige tessellatiefallback gebruikt: {semantic_error}"
            )
        return PDFConversionResult(
            source,
            [target],
            warnings,
            details={
                "route": route,
                "pdf_mode": analysis.mode,
                "ifc_class": "IfcPlate" if "semantic-ifcplate" in route else "fallback",
                "preview_volume_delta_percent": delta,
                "payload_schema": restored.schema_version,
            },
        )
    return PDFConversionResult(source, [target], analysis.warnings, details={"route": route, "pdf_mode": analysis.mode})


# ---------------------------------------------------------------------------
# Model -> PDF wrappers
# ---------------------------------------------------------------------------


def nc1_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    *,
    template: DrawingTemplate | None = None,
) -> PDFConversionResult:
    part = canonical_from_nc1(input_path)
    part.drawing.drawing_status = "released"
    part.validation.export_status = "released"
    part.validation.production_export_allowed = True
    return create_trusted_pdf(part, output_path, template=template)


def step_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    *,
    material: str = "S355JR",
    preferred_profile: str = "",
    tolerance_mm: float = 1.0,
    template: DrawingTemplate | None = None,
) -> PDFConversionResult:
    part = canonical_from_step(
        input_path,
        material=material,
        preferred_profile=preferred_profile,
        tolerance_mm=tolerance_mm,
    )
    part.drawing.drawing_status = "released" if part.validation.production_export_allowed else "concept"
    return create_trusted_pdf(part, output_path, template=template)


def ifc_to_pdf(
    input_path: str | Path,
    output: str | Path,
    *,
    material: str = "S355JR",
    template: DrawingTemplate | None = None,
) -> PDFConversionResult:
    source = Path(input_path)
    parts = canonical_parts_from_ifc(source, material=material)
    target = Path(output)
    outputs: list[Path] = []
    warnings: list[str] = []
    if len(parts) == 1 and target.suffix.lower() == ".pdf":
        result = create_trusted_pdf(parts[0], target, template=template)
        return PDFConversionResult(source, result.outputs, result.warnings, result.failures, {"parts": 1, **result.details})
    target.mkdir(parents=True, exist_ok=True)
    for index, part in enumerate(parts, start=1):
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", part.part_id or f"part_{index}").strip("_.") or f"part_{index}"
        result = create_trusted_pdf(part, target / f"{safe}.pdf", template=template)
        outputs.extend(result.outputs)
        warnings.extend(result.warnings)
    return PDFConversionResult(
        source=source,
        outputs=outputs,
        warnings=list(dict.fromkeys(warnings)),
        details={"route": "ifc-parts->trusted-pdf", "parts": len(parts)},
    )


def write_analysis_report(result: PDFAnalysisResult, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return target
