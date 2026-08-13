"""Released production packages built from the canonical Project Model."""
from __future__ import annotations

import csv
import io
import json
import math
import os
import shutil
import tempfile
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

import cadquery as cq
import fitz
from pypdf import PdfReader, PdfWriter
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from canonical_model import CanonicalPart, embed_part_in_step
from ifc_native import _escape_ifc, _guid22, write_native_ifc

from cws_convertor.bom.engine import build_bom_snapshot
from cws_convertor.bom.export import export_bom_package, safe_spreadsheet_value
from cws_convertor.product import APP_NAME, APP_VERSION
from cws_convertor.project.canonical_rebuild import rebuild_and_compare
from cws_convertor.project.model import EntityCategory, Part, ProjectModel, ProjectValidationError
from cws_convertor.project.roundtrip import canonical_part_from_workbench, validate_roundtrips
from cws_convertor.project.workbench import roundtrip_is_current

from .artifacts import media_type
from .engine import ExportRequest, ProductionExportEngine, SUPPORTED_FORMATS
from .models import (
    ArtifactResult,
    ArtifactStatus,
    AssemblyPackageResult,
    ExportItemResult,
    ExportManifest,
    ExportStatus,
    GateMessage,
)
from .pdf_report import create_review_pdf
from .utils import (
    atomic_directory,
    atomic_write,
    canonical_json_bytes,
    safe_filename,
    safe_relative_path,
    sha256_bytes,
    sha256_file,
    stable_hash,
    utc_now_iso,
)


CORE_FORMATS = ("nc1", "step", "ifc", "production_pdf")
RELEASE_FORMATS = (
    "nc1",
    "step",
    "ifc",
    "production_pdf",
    "dxf",
    "csv",
    "label_pdf",
    "preview_png",
    "json",
)


def _part_marks(project: ProjectModel, part: Part) -> list[str]:
    marks = {
        project.assemblies[assembly_id].assembly_mark
        for assembly_id in part.assembly_ids
        if assembly_id in project.assemblies and project.assemblies[assembly_id].assembly_mark
    }
    if part.source_identity.assembly_mark:
        marks.add(part.source_identity.assembly_mark)
    return sorted(marks)


def _filename_conflicts(parts: Iterable[Part]) -> dict[str, set[str]]:
    by_position: dict[str, list[Part]] = defaultdict(list)
    for part in parts:
        by_position[part.part_position.strip().upper()].append(part)
    result: dict[str, set[str]] = {}
    for position, group in by_position.items():
        identities = {part.manufacturing_hash for part in group if part.manufacturing_hash}
        if position and len(identities) > 1:
            for part in group:
                result.setdefault(part.internal_id, set()).add(position)
    return result


def _assembly_composition(project: ProjectModel, assembly: Any) -> dict[str, Any]:
    def part_position(part_id: str) -> str:
        part = project.parts.get(part_id)
        return (part.part_position or part.internal_id) if part else part_id

    parts = []
    for part_id in assembly.part_ids:
        part = project.parts.get(part_id)
        if part is None:
            continue
        parts.append(
            {
                "position": part.part_position,
                "manufacturing_hash": part.manufacturing_hash,
                "quantity": max(1, int(part.quantity_per_assembly.get(assembly.internal_id, 1))),
            }
        )
    purchased = []
    for item_id in assembly.purchased_item_ids:
        item = project.purchased_items.get(item_id)
        if item is None:
            continue
        purchased.append(
            {
                "name": item.name,
                "description": item.description,
                "standard": item.standard,
                "material": item.material,
                "grade": item.grade,
                "dimensions": item.dimensions,
                "quantity": item.quantity,
                "unit": item.unit,
            }
        )
    fasteners = []
    for item_id in assembly.fastener_ids:
        item = project.fasteners.get(item_id)
        if item is None:
            continue
        fasteners.append(
            {
                "type": item.fastener_type,
                "diameter_mm": item.diameter_mm,
                "grade": item.grade,
                "length_mm": item.length_mm,
                "standard": item.standard,
                "quantity": item.quantity,
                "connected_positions": sorted(part_position(value) for value in item.connected_part_ids),
            }
        )
    welds = []
    for item_id in assembly.weld_ids:
        item = project.welds.get(item_id)
        if item is None:
            continue
        welds.append(
            {
                "type": item.weld_type,
                "size_mm": item.size_mm,
                "length_mm": item.length_mm,
                "process": item.process,
                "side": item.side,
                "location": item.location,
                "connected_positions": sorted(part_position(value) for value in item.connected_part_ids),
            }
        )
    return {
        "parts": sorted(parts, key=stable_hash),
        "purchased": sorted(purchased, key=stable_hash),
        "fasteners": sorted(fasteners, key=stable_hash),
        "welds": sorted(welds, key=stable_hash),
        "child_marks": sorted(
            project.assemblies[item].assembly_mark
            for item in assembly.child_assembly_ids
            if item in project.assemblies
        ),
    }


def _render_name(project: ProjectModel, part: Part, marks: list[str], request: ExportRequest) -> str:
    values = {
        "project": project.project_name,
        "project_id": project.project_id,
        "assembly_mark": marks[0] if marks else "ZONDER_MERK",
        "part_position": part.part_position or part.internal_id,
        "part_id": part.internal_id,
        "profile": part.normalized_profile or part.profile or "GEEN_PROFIEL",
        "material": part.normalized_material or part.material_grade or part.material or "GEEN_MATERIAAL",
        "revision": part.revision or "0",
        "identity": (part.manufacturing_hash or part.production_identity_hash or part.internal_id)[:12],
    }
    try:
        rendered = request.filename_template.format_map(values)
    except KeyError as exc:
        raise ProjectValidationError(f"Onbekend veld in bestandsnaamsjabloon: {exc.args[0]}") from exc
    return safe_filename(rendered, fallback=part.internal_id, max_length=150)


def _artifact(
    root: Path,
    path: Path,
    fmt: str,
    *,
    part: Part | None = None,
    assembly_id: str = "",
    canonical_signature: str = "",
    roundtrip_hash: str = "",
    source: str,
) -> ArtifactResult:
    return ArtifactResult(
        format=fmt,
        status=ArtifactStatus.EXPORTED,
        relative_path=path.relative_to(root).as_posix(),
        sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
        media_type=media_type(fmt),
        production_artifact=fmt in CORE_FORMATS or fmt.startswith("assembly_"),
        source=source,
        object_id=part.internal_id if part else assembly_id,
        revision=part.revision if part else "",
        manufacturing_hash=part.manufacturing_hash if part else "",
        canonical_signature=canonical_signature,
        roundtrip_report_sha256=roundtrip_hash,
    )


def _write_part_csv(part: Part, marks: list[str], path: Path) -> None:
    row = {
        "part_id": part.internal_id,
        "part_position": part.part_position,
        "assembly_marks": ",".join(marks),
        "profile": part.normalized_profile or part.profile,
        "material": part.normalized_material or part.material_grade or part.material,
        "length_mm": part.length_mm,
        "quantity_total": part.quantity_total,
        "mass_each_kg": part.mass_each_kg,
        "surface_area_each_m2": part.surface_area_each_m2,
        "revision": part.revision,
        "manufacturing_hash": part.manufacturing_hash,
        "production_identity_hash": part.production_identity_hash,
    }
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(row), delimiter=";")
    writer.writeheader()
    writer.writerow({key: safe_spreadsheet_value(value) for key, value in row.items()})
    atomic_write(path, output.getvalue().encode("utf-8-sig"))


def _write_label_pdf(project: ProjectModel, part: Part, marks: list[str], path: Path) -> None:
    width, height = 100 * mm, 50 * mm
    pdf = canvas.Canvas(str(path), pagesize=(width, height), pageCompression=1)
    pdf.setTitle(f"Label {part.part_position or part.internal_id}")
    pdf.setFillColor(colors.HexColor("#16324F"))
    pdf.rect(0, height - 10 * mm, width, 10 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(5 * mm, height - 6.7 * mm, APP_NAME)
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(5 * mm, height - 20 * mm, part.part_position or part.internal_id)
    pdf.setFont("Helvetica", 8)
    rows = [
        f"Merk: {', '.join(marks) or '-'}",
        f"Profiel: {part.normalized_profile or part.profile or '-'}",
        f"Materiaal: {part.normalized_material or part.material_grade or part.material or '-'}",
        f"Lengte: {part.length_mm:.2f} mm    Aantal: {part.quantity_total}",
        f"Rev: {part.revision or '0'}    ID: {part.internal_id[:16]}",
    ]
    for index, value in enumerate(rows):
        pdf.drawString(5 * mm, height - (27 + index * 4.2) * mm, value[:78])
    uri = f"cws://project/{project.project_id}/part/{part.internal_id}?revision={part.revision or '0'}"
    qr = QrCodeWidget(uri)
    bounds = qr.getBounds()
    size = 31 * mm
    drawing = Drawing(size, size, transform=[size / (bounds[2] - bounds[0]), 0, 0, size / (bounds[3] - bounds[1]), 0, 0])
    drawing.add(qr)
    renderPDF.draw(drawing, pdf, width - 35 * mm, 4 * mm)
    pdf.showPage()
    pdf.save()


def _write_preview(pdf_path: Path, path: Path) -> None:
    with fitz.open(pdf_path) as document:
        pixmap = document[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        atomic_write(path, pixmap.tobytes("png"))


def _write_plate_dxf(part: Part, path: Path) -> bool:
    revision = dict(part.workbench.get("current_revision") or {})
    if revision.get("part_form") != "plate":
        return False
    import ezdxf

    document = ezdxf.new("R2010", setup=True)
    document.header["$INSUNITS"] = 4  # millimetres
    model = document.modelspace()
    for contour in list(revision.get("contours") or []):
        layer = "CWS_INNER" if contour.get("role") == "inner" else "CWS_OUTER"
        for segment in list(contour.get("segments") or []):
            if segment.get("kind") != "line":
                return False
            model.add_line(tuple(segment["start"]), tuple(segment["end"]), dxfattribs={"layer": layer})
    for feature in list(revision.get("features") or []):
        if feature.get("kind") != "hole":
            continue
        parameters = dict(feature.get("parameters") or {})
        model.add_circle(
            (float(parameters["x_mm"]), float(parameters["y_mm"])),
            float(parameters["diameter_mm"]) / 2.0,
            dxfattribs={"layer": "CWS_HOLES"},
        )
    document.saveas(path)
    return True


def _shape_segments(shape: cq.Shape, tolerance: float = 1.0) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    result: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
    for edge in shape.Edges():
        count = 1 if edge.geomType() == "LINE" else max(8, min(64, int(math.ceil(edge.Length() / tolerance))))
        points = [edge.positionAt(index / count) for index in range(count + 1)]
        result.extend(
            (
                (float(left.x), float(left.y), float(left.z)),
                (float(right.x), float(right.y), float(right.z)),
            )
            for left, right in zip(points, points[1:])
        )
    return result


def _draw_projected_view(
    pdf: canvas.Canvas,
    shapes: list[tuple[str, cq.Shape]],
    box: tuple[float, float, float, float],
    axes: tuple[int, int] | None,
    title: str,
) -> None:
    x, y, width, height = box
    def project(point: tuple[float, float, float]) -> tuple[float, float]:
        if axes is not None:
            return point[axes[0]], point[axes[1]]
        cosine = math.cos(math.radians(30.0))
        sine = math.sin(math.radians(30.0))
        return (point[0] - point[1]) * cosine, point[2] + (point[0] + point[1]) * sine

    segments = [(name, left, right) for name, shape in shapes for left, right in _shape_segments(shape)]
    values = [project(point) for _, left, right in segments for point in (left, right)]
    pdf.setStrokeColor(colors.HexColor("#C7D0D9"))
    pdf.rect(x, y, width, height, stroke=1, fill=0)
    pdf.setFillColor(colors.HexColor("#16324F"))
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(x + 2 * mm, y + height - 4 * mm, title)
    if not values:
        return
    min_x, max_x = min(item[0] for item in values), max(item[0] for item in values)
    min_y, max_y = min(item[1] for item in values), max(item[1] for item in values)
    span_x, span_y = max(max_x - min_x, 1.0), max(max_y - min_y, 1.0)
    scale = min((width - 8 * mm) / span_x, (height - 12 * mm) / span_y)
    origin_x = x + (width - span_x * scale) / 2 - min_x * scale
    origin_y = y + (height - span_y * scale) / 2 - min_y * scale - 2 * mm
    pdf.setStrokeColor(colors.HexColor("#263746"))
    pdf.setLineWidth(0.25)
    for _name, left, right in segments:
        projected_left = project(left)
        projected_right = project(right)
        pdf.line(
            origin_x + projected_left[0] * scale,
            origin_y + projected_left[1] * scale,
            origin_x + projected_right[0] * scale,
            origin_y + projected_right[1] * scale,
        )
    pdf.setFillColor(colors.HexColor("#1F5C8A"))
    pdf.setFont("Helvetica-Bold", 5.5)
    for name, shape in shapes:
        bounds = shape.BoundingBox()
        center = project(
            (
                (bounds.xmin + bounds.xmax) / 2.0,
                (bounds.ymin + bounds.ymax) / 2.0,
                (bounds.zmin + bounds.zmax) / 2.0,
            )
        )
        pdf.drawString(origin_x + center[0] * scale + 1.5 * mm, origin_y + center[1] * scale + 1.5 * mm, name[:20])


def _attach_manifest_to_pdf(path: Path, name: str, payload: dict[str, Any]) -> str:
    data = canonical_json_bytes(payload)
    digest = sha256_bytes(data)
    reader = PdfReader(str(path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.add_attachment(name, data)
    writer.add_metadata({"/CWSManifestSHA256": digest, "/CWSFormat": "CWS_ASSEMBLY_DRAWING_V1"})
    temp = path.with_suffix(".tmp.pdf")
    with temp.open("wb") as handle:
        writer.write(handle)
    os.replace(temp, path)
    return digest


def _write_assembly_pdf(
    project: ProjectModel,
    mark: str,
    assembly_ids: list[str],
    parts: list[Part],
    shapes: list[tuple[str, cq.Shape]],
    manifest: dict[str, Any],
    path: Path,
    assembly_quantity: int,
) -> str:
    page_width, page_height = landscape(A3)
    pdf = canvas.Canvas(str(path), pagesize=(page_width, page_height), pageCompression=1)
    pdf.setTitle(f"Assembly {mark}")
    assemblies = [project.assemblies[item] for item in assembly_ids]
    fasteners = sum(max(1, int(project.fasteners[item].quantity or 1)) for assembly in assemblies for item in assembly.fastener_ids if item in project.fasteners)
    welds = [project.welds[item] for assembly in assemblies for item in assembly.weld_ids if item in project.welds]
    total_mass = sum(float(part.mass_each_kg or 0.0) * max(1, int(part.quantity_total or 1)) for part in parts)

    def draw_header(page_label: str) -> None:
        pdf.setFillColor(colors.HexColor("#16324F"))
        pdf.rect(0, page_height - 18 * mm, page_width, 18 * mm, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(12 * mm, page_height - 11.5 * mm, f"{APP_NAME} | MERKTEKENING {mark}")
        pdf.setFont("Helvetica", 7)
        pdf.drawRightString(page_width - 32 * mm, page_height - 8.2 * mm, f"Project {project.project_name} | v{APP_VERSION}")
        pdf.drawRightString(page_width - 32 * mm, page_height - 12.2 * mm, page_label)
        uri = f"cws://project/{project.project_id}/assembly/{mark}"
        qr = QrCodeWidget(uri)
        bounds = qr.getBounds()
        size = 14 * mm
        drawing = Drawing(
            size,
            size,
            transform=[size / (bounds[2] - bounds[0]), 0, 0, size / (bounds[3] - bounds[1]), 0, 0],
        )
        drawing.add(qr)
        renderPDF.draw(drawing, pdf, page_width - 28 * mm, page_height - 16 * mm)

    draw_header("Aanzichten")
    left = 12 * mm
    top = page_height - 24 * mm
    view_width = (page_width - 30 * mm) / 2
    view_height = (top - 18 * mm) / 2
    _draw_projected_view(pdf, shapes, (left, top - view_height, view_width, view_height), (0, 1), "BOVENAANZICHT (XY)")
    _draw_projected_view(pdf, shapes, (left + view_width + 6 * mm, top - view_height, view_width, view_height), (0, 2), "VOORAANZICHT (XZ)")
    _draw_projected_view(pdf, shapes, (left, 12 * mm, view_width, view_height), (1, 2), "ZIJAANZICHT (YZ)")
    _draw_projected_view(pdf, shapes, (left + view_width + 6 * mm, 12 * mm, view_width, view_height), None, "ISOMETRISCH OVERZICHT")
    pdf.setFont("Helvetica", 5.5)
    pdf.setFillColor(colors.HexColor("#566573"))
    pdf.drawString(left, 6 * mm, "Vectorprojecties uit gevalideerde part-solids; exacte onderdeeldata en checksums staan in het ingesloten manifest.")
    pdf.showPage()

    headers = ("Pos", "Profiel", "Materiaal", "L (mm)", "Aantal", "Massa (kg)", "Rev", "Part-ID")
    widths = (0.10, 0.18, 0.13, 0.10, 0.08, 0.11, 0.07, 0.23)
    rows = [
        (
            part.part_position,
            part.normalized_profile or part.profile,
            part.normalized_material or part.material_grade or part.material,
            f"{part.length_mm:.2f}",
            str(part.quantity_total),
            f"{part.mass_each_kg * part.quantity_total:.3f}",
            part.revision or "0",
            part.internal_id,
        )
        for part in sorted(parts, key=lambda item: (item.part_position, item.internal_id))
    ]
    chunks = [rows[index:index + 32] for index in range(0, len(rows), 32)] or [[]]
    for page_index, chunk in enumerate(chunks, start=1):
        draw_header(f"Stuklijst {page_index}/{len(chunks)}")
        table_x = 12 * mm
        table_w = page_width - 24 * mm
        y = page_height - 31 * mm
        row_h = 6.3 * mm
        pdf.setFillColor(colors.HexColor("#16324F"))
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(table_x, y + 4 * mm, "STUKLIJST EN PRODUCTIE-INFORMATIE")
        pdf.setFillColor(colors.HexColor("#E7EDF2"))
        pdf.rect(table_x, y - row_h, table_w, row_h, stroke=1, fill=1)
        current = table_x
        for header, fraction in zip(headers, widths):
            pdf.setFillColor(colors.HexColor("#16324F"))
            pdf.setFont("Helvetica-Bold", 6)
            pdf.drawCentredString(current + table_w * fraction / 2, y - row_h + 2.1 * mm, header)
            current += table_w * fraction
        y -= row_h
        for row in chunk:
            y -= row_h
            pdf.setFillColor(colors.white)
            pdf.rect(table_x, y, table_w, row_h, stroke=1, fill=1)
            current = table_x
            for value, fraction in zip(row, widths):
                pdf.setFillColor(colors.black)
                pdf.setFont("Helvetica", 5.6)
                pdf.drawCentredString(current + table_w * fraction / 2, y + 2.1 * mm, str(value)[:36])
                current += table_w * fraction
        if page_index == len(chunks):
            notes = (
                f"Aantal assemblies: {assembly_quantity}",
                f"Unieke partrecords: {len(parts)}",
                f"Bouten/bevestigers: {fasteners}",
                f"Lassen: {len(welds)} | totale laslengte {sum(float(item.length_mm or 0.0) for item in welds):.1f} mm",
                f"Berekende massa: {total_mass:.3f} kg",
                f"Revisies: {', '.join(sorted({part.revision or '0' for part in parts}))}",
                f"Compositiehash: {manifest['composition_sha256']}",
            )
            note_y = max(22 * mm, y - 11 * mm)
            pdf.setFillColor(colors.HexColor("#16324F"))
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(table_x, note_y, "SAMENVATTING")
            pdf.setFillColor(colors.black)
            pdf.setFont("Helvetica", 6.5)
            for index, note in enumerate(notes):
                pdf.drawString(table_x, note_y - (5 + index * 4) * mm, note[:150])
        pdf.setFont("Helvetica", 5.5)
        pdf.setFillColor(colors.HexColor("#566573"))
        pdf.drawRightString(page_width - 12 * mm, 6 * mm, f"Assembly {mark} | manifest {manifest['manifest_sha256'][:20]}")
        pdf.showPage()
    pdf.save()
    return _attach_manifest_to_pdf(path, "cws-assembly-manifest.json", manifest)


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    output = io.StringIO(newline="")
    headers = list(rows[0]) if rows else ["status"]
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=";")
    writer.writeheader()
    if rows:
        writer.writerows({key: safe_spreadsheet_value(value) for key, value in row.items()} for row in rows)
    atomic_write(path, output.getvalue().encode("utf-8-sig"))


def _enrich_assembly_ifc(path: Path, mark: str, manifest: dict[str, Any]) -> None:
    """Add deterministic IfcElementAssembly semantics to the Part 21 file."""

    import re

    source = path.read_text(encoding="utf-8")
    element_ids = [
        int(match.group(1))
        for match in re.finditer(
            r"#(\d+)=IFC(?:BEAM|PLATE|MEMBER)\(",
            source,
            flags=re.IGNORECASE,
        )
    ]
    if not element_ids:
        raise ProjectValidationError("Assembly-IFC bevat geen onderdelen")
    max_id = max(int(value) for value in re.findall(r"#(\d+)=", source))
    assembly_id = max_id + 1
    aggregate_id = max_id + 2
    property_ids = list(range(max_id + 3, max_id + 7))
    property_set_id = max_id + 7
    defines_id = max_id + 8
    refs = ",".join(f"#{value}" for value in element_ids)
    containment_pattern = re.compile(
        r"(#\d+=IFCRELCONTAINEDINSPATIALSTRUCTURE\('[^']*',#\d+,\$,\$,\()"
        r"#[\d#,\s]+(\),#\d+\);)",
        flags=re.IGNORECASE,
    )
    source, containment_count = containment_pattern.subn(
        lambda match: f"{match.group(1)}#{assembly_id}{match.group(2)}",
        source,
        count=1,
    )
    if containment_count != 1:
        raise ProjectValidationError("Assembly-IFC mist een eenduidige ruimtelijke containmentrelatie")
    values = (
        ("AssemblyMark", mark),
        ("CompositionSHA256", str(manifest["composition_sha256"])),
        ("ManifestSHA256", str(manifest["manifest_sha256"])),
        ("PartCount", str(len(manifest["parts"]))),
    )
    lines = [
        (
            f"#{assembly_id}=IFCELEMENTASSEMBLY('{_guid22(mark + ':assembly')}',#5,"
            f"'{_escape_ifc(mark)}',$,$,#23,$,'{_escape_ifc(mark)}',.USERDEFINED.,.FACTORY.);"
        ),
        (
            f"#{aggregate_id}=IFCRELAGGREGATES('{_guid22(mark + ':parts')}',#5,"
            f"'CWS assembly composition',$,#{assembly_id},({refs}));"
        ),
    ]
    for property_id, (name, value) in zip(property_ids, values):
        lines.append(
            f"#{property_id}=IFCPROPERTYSINGLEVALUE('{name}',$,IFCTEXT('{_escape_ifc(value)}'),$);"
        )
    property_refs = ",".join(f"#{value}" for value in property_ids)
    lines.extend(
        [
            (
                f"#{property_set_id}=IFCPROPERTYSET('{_guid22(mark + ':pset')}',#5,"
                f"'Pset_CWSAssemblyPackage',$,({property_refs}));"
            ),
            (
                f"#{defines_id}=IFCRELDEFINESBYPROPERTIES('{_guid22(mark + ':defines')}',#5,"
                f"$,$,(#{assembly_id}),#{property_set_id});"
            ),
        ]
    )
    marker = "ENDSEC;\nEND-ISO-10303-21;"
    if marker not in source:
        raise ProjectValidationError("Assembly-IFC mist een geldige Part 21-afsluiting")
    source = source.replace(marker, "\n".join(lines) + "\n" + marker, 1)
    atomic_write(path, source.encode("utf-8"))


class ProjectProductionExportEngine:
    """Build an atomic package only from released, freshly revalidated parts."""

    SCHEMA_VERSION = "2.0"

    def __init__(self, *, product_version: str = APP_VERSION) -> None:
        self.product_version = product_version

    @staticmethod
    def _select_parts(project: ProjectModel, request: ExportRequest) -> list[Part]:
        result: list[Part] = []
        for part in project.parts.values():
            if part.category != EntityCategory.MAKE_PART.value:
                continue
            marks = set(_part_marks(project, part))
            if request.part_ids and part.internal_id not in request.part_ids:
                continue
            if request.assembly_marks and not marks.intersection(request.assembly_marks):
                continue
            result.append(part)
        return sorted(result, key=lambda item: (item.part_position, item.internal_id))

    @staticmethod
    def _release_blockers(part: Part) -> list[GateMessage]:
        result: list[GateMessage] = []
        revision = dict(part.workbench.get("current_revision") or {})
        if not part.workbench:
            result.append(GateMessage("CWS-REL-001", "Part Workbench ontbreekt", field="workbench"))
        if revision.get("review_status") != "released":
            result.append(GateMessage("CWS-REL-002", "Onderdeel is niet vrijgegeven", field="review_status"))
        if not roundtrip_is_current(part, revision):
            result.append(GateMessage("CWS-REL-003", "NC1/STEP/IFC/PDF-roundtripbewijs is niet actueel", field="roundtrip_validation"))
        for issue in part.blocking_issues():
            result.append(GateMessage(issue.code, issue.message, field=issue.field_path))
        return result

    def _blocked_item(
        self,
        project: ProjectModel,
        part: Part,
        root: Path,
        request: ExportRequest,
        formats: list[str],
        messages: list[GateMessage],
    ) -> ExportItemResult:
        marks = _part_marks(project, part)
        part_dir = root / safe_relative_path("parts", marks[0] if marks else "ZONDER_MERK", f"{part.part_position or 'ONBEKEND'}__{part.internal_id[:12]}")
        part_dir.mkdir(parents=True, exist_ok=True)
        artifacts = [
            ArtifactResult(
                format=fmt,
                status=ArtifactStatus.BLOCKED,
                production_artifact=fmt in CORE_FORMATS,
                object_id=part.internal_id,
                revision=part.revision,
                manufacturing_hash=part.manufacturing_hash,
                messages=list(messages),
            )
            for fmt in formats
        ]
        if request.include_blocked_review_files:
            review = part_dir / f"{safe_filename(part.part_position or part.internal_id)}_REVIEW_NIET_VRIJGEGEVEN.pdf"
            atomic_write(review, create_review_pdf(part, blocked_reasons=[item.message for item in messages], product_version=self.product_version))
            artifacts.append(_artifact(root, review, "review_pdf", part=part, source="blocked-review"))
        item = ExportItemResult(
            part_id=part.internal_id,
            part_position=part.part_position,
            assembly_marks=marks,
            classification=part.category,
            production_identity_hash=part.production_identity_hash,
            status=ExportStatus.BLOCKED,
            artifacts=artifacts,
            messages=messages,
            source_entity_id=part.source_identity.source_entity_id,
            source_file_id=part.source_identity.source_file_id,
            quantity_total=part.quantity_total,
            revision=part.revision,
            manufacturing_hash=part.manufacturing_hash,
        )
        atomic_write(part_dir / "item_manifest.json", canonical_json_bytes(item.to_dict()))
        return item

    def _export_part(
        self,
        project: ProjectModel,
        part: Part,
        root: Path,
        request: ExportRequest,
        formats: list[str],
    ) -> tuple[ExportItemResult, cq.Shape | None, CanonicalPart | None]:
        blockers = self._release_blockers(part)
        if blockers:
            return self._blocked_item(project, part, root, request, formats, blockers), None, None
        rebuild = rebuild_and_compare(part)
        stored_rebuild = dict(part.workbench.get("canonical_rebuild") or {})
        stored_report = dict(stored_rebuild.get("report") or {})
        signature = str(stored_report.get("canonical_signature") or "")
        if rebuild.shape is None or rebuild.report.get("status") != "passed" or rebuild.report.get("canonical_signature") != signature:
            message = GateMessage("CWS-REL-004", "Canonical rebuild kon niet identiek worden herhaald", field="canonical_rebuild")
            return self._blocked_item(project, part, root, request, formats, [message]), None, None

        marks = _part_marks(project, part)
        part_dir = root / safe_relative_path("parts", marks[0] if marks else "ZONDER_MERK", f"{part.part_position or 'ONBEKEND'}__{part.internal_id[:12]}")
        part_dir.mkdir(parents=True, exist_ok=True)
        base = _render_name(project, part, marks, request)
        artifacts: list[ArtifactResult] = []
        with tempfile.TemporaryDirectory(prefix=".fresh_roundtrip_", dir=root) as temp_name:
            fresh = validate_roundtrips(part, rebuild.shape, temp_name, canonical_signature=signature)
            if fresh.get("status") != "passed":
                failures = [
                    check
                    for result in dict(fresh.get("formats") or {}).values()
                    for check in list(result.get("checks") or [])
                    if check.get("status") != "passed"
                ]
                message = GateMessage(
                    "CWS-REL-005",
                    "Verse productie-roundtrip is mislukt",
                    field="roundtrip_validation",
                    evidence={"failures": failures},
                )
                return self._blocked_item(project, part, root, request, formats, [message]), None, None
            normalized_report = dict(fresh)
            normalized_formats: dict[str, Any] = {}
            core_targets: dict[str, Path] = {}
            for source_format, result in dict(fresh["formats"]).items():
                public_format = "production_pdf" if source_format == "pdf" else source_format
                suffix = ".pdf" if public_format == "production_pdf" else f".{public_format}"
                target = part_dir / f"{base}{suffix}"
                shutil.copy2(Path(result["artifact_path"]), target)
                core_targets[public_format] = target
                updated = dict(result)
                updated["artifact_path"] = target.relative_to(root).as_posix()
                normalized_formats[source_format] = updated
            normalized_report["formats"] = normalized_formats
            normalized_report.pop("report_sha256", None)
            normalized_report["release_validated_at"] = utc_now_iso()
            normalized_report["report_sha256"] = stable_hash(normalized_report)
            report_hash = normalized_report["report_sha256"]
            report_path = part_dir / "roundtrip_report.json"
            atomic_write(report_path, canonical_json_bytes(normalized_report))

            for fmt in formats:
                target: Path | None = None
                source = "canonical-release"
                if fmt in CORE_FORMATS:
                    target = core_targets[fmt]
                    source = "fresh-canonical-roundtrip"
                elif fmt == "json":
                    target = part_dir / f"{base}.json"
                    atomic_write(target, canonical_json_bytes(part.base_to_dict()))
                elif fmt == "review_pdf":
                    target = part_dir / f"{base}_REVIEW.pdf"
                    atomic_write(
                        target,
                        create_review_pdf(
                            part,
                            blocked_reasons=[],
                            product_version=self.product_version,
                        ),
                    )
                    source = "released-review"
                elif fmt == "csv":
                    target = part_dir / f"{base}.csv"
                    _write_part_csv(part, marks, target)
                elif fmt == "label_pdf":
                    target = part_dir / f"{base}_LABEL.pdf"
                    _write_label_pdf(project, part, marks, target)
                elif fmt == "preview_png":
                    target = part_dir / f"{base}_PREVIEW.png"
                    _write_preview(core_targets["production_pdf"], target)
                elif fmt == "dxf":
                    target = part_dir / f"{base}.dxf"
                    if not _write_plate_dxf(part, target):
                        artifacts.append(
                            ArtifactResult(
                                format=fmt,
                                status=ArtifactStatus.SKIPPED,
                                production_artifact=False,
                                object_id=part.internal_id,
                                revision=part.revision,
                                manufacturing_hash=part.manufacturing_hash,
                                messages=[GateMessage("CWS-REL-120", "DXF is alleen exact beschikbaar voor ondersteunde plaatcontouren", severity="warning")],
                            )
                        )
                        continue
                if target is not None:
                    artifacts.append(
                        _artifact(
                            root,
                            target,
                            fmt,
                            part=part,
                            canonical_signature=signature,
                            roundtrip_hash=report_hash,
                            source=source,
                        )
                    )
            artifacts.append(
                _artifact(
                    root,
                    report_path,
                    "roundtrip_report",
                    part=part,
                    canonical_signature=signature,
                    roundtrip_hash=report_hash,
                    source="fresh-canonical-roundtrip",
                )
            )

        canonical = canonical_part_from_workbench(part, rebuild.shape, canonical_signature=signature)
        item = ExportItemResult(
            part_id=part.internal_id,
            part_position=part.part_position,
            assembly_marks=marks,
            classification=part.category,
            production_identity_hash=part.production_identity_hash,
            status=ExportStatus.EXPORTED,
            artifacts=artifacts,
            source_entity_id=part.source_identity.source_entity_id,
            source_file_id=part.source_identity.source_file_id,
            quantity_total=part.quantity_total,
            revision=part.revision,
            manufacturing_hash=part.manufacturing_hash,
            canonical_signature=signature,
            roundtrip_report_sha256=report_hash,
        )
        atomic_write(part_dir / "item_manifest.json", canonical_json_bytes(item.to_dict()))
        return item, rebuild.shape, canonical

    @staticmethod
    def _assembly_groups(project: ProjectModel, selected: list[Part], request: ExportRequest) -> dict[str, list[Any]]:
        selected_ids = {part.internal_id for part in selected}
        groups: dict[str, list[Any]] = defaultdict(list)
        for assembly in project.assemblies.values():
            mark = assembly.assembly_mark or assembly.internal_id
            if request.assembly_marks and mark not in request.assembly_marks:
                continue
            if any(part_id in selected_ids for part_id in assembly.part_ids):
                groups[mark].append(assembly)
        return groups

    def _assembly_packages(
        self,
        project: ProjectModel,
        root: Path,
        request: ExportRequest,
        selected: list[Part],
        items: list[ExportItemResult],
        shapes: dict[str, cq.Shape],
        canonicals: dict[str, CanonicalPart],
        bom: Any,
    ) -> list[AssemblyPackageResult]:
        item_by_id = {item.part_id: item for item in items}
        results: list[AssemblyPackageResult] = []
        for mark, assemblies in sorted(self._assembly_groups(project, selected, request).items()):
            assemblies = sorted(assemblies, key=lambda item: item.internal_id)
            complete = [
                assembly
                for assembly in assemblies
                if all(part_id in item_by_id for part_id in assembly.part_ids)
            ]
            representative = complete[0] if complete else assemblies[0]
            part_ids = sorted(part_id for part_id in representative.part_ids if part_id in project.parts)
            selected_part_ids = [part_id for part_id in part_ids if part_id in item_by_id]
            missing_part_ids = sorted(set(part_ids) - set(selected_part_ids))
            parts = [project.parts[part_id] for part_id in selected_part_ids]
            messages: list[GateMessage] = []
            if missing_part_ids:
                messages.append(
                    GateMessage(
                        "CWS-REL-203",
                        "Merkselectie mist onderdelen en kan niet als compleet assemblypakket worden vrijgegeven",
                        field="part_ids",
                        evidence={"missing_part_ids": missing_part_ids},
                    )
                )
            if any(item_by_id[part_id].status != ExportStatus.EXPORTED for part_id in selected_part_ids):
                messages.append(GateMessage("CWS-REL-201", "Merk bevat een niet-vrijgegeven of mislukte part-export"))
            compositions = {
                stable_hash(_assembly_composition(project, assembly))
                for assembly in assemblies
            }
            if len(compositions) != 1:
                messages.append(GateMessage("CWS-REL-202", "Gelijk merk heeft verschillende onderdeelcomposities"))
            composition_hash = next(iter(compositions), stable_hash([]))
            assembly_dir = root / safe_relative_path("assemblies", mark)
            assembly_dir.mkdir(parents=True, exist_ok=True)
            if messages:
                payload = {
                    "assembly_mark": mark,
                    "status": "blocked",
                    "part_ids": selected_part_ids,
                    "missing_part_ids": missing_part_ids,
                    "messages": [item.to_dict() for item in messages],
                }
                manifest_path = assembly_dir / "assembly_manifest.json"
                atomic_write(manifest_path, canonical_json_bytes(payload))
                results.append(
                    AssemblyPackageResult(
                        assembly_mark=mark,
                        quantity=sum(max(1, int(item.quantity or 1)) for item in assemblies),
                        part_ids=selected_part_ids,
                        status=ExportStatus.BLOCKED,
                        relative_path=assembly_dir.relative_to(root).as_posix(),
                        sha256=sha256_file(manifest_path),
                        composition_sha256=composition_hash,
                        messages=messages,
                    )
                )
                continue

            part_ids = selected_part_ids
            transformed: list[tuple[str, cq.Shape]] = []
            for part in parts:
                matrix = cq.Matrix(part.global_placement.matrix[:3])
                transformed.append((part.part_position or part.internal_id, shapes[part.internal_id].transformGeometry(matrix)))
            compound = cq.Compound.makeCompound([shape for _name, shape in transformed])
            assembly_manifest = {
                "format": "CWS_ASSEMBLY_PACKAGE_V1",
                "project_id": project.project_id,
                "assembly_mark": mark,
                "assembly_ids": sorted(item.internal_id for item in assemblies),
                "quantity": sum(max(1, int(item.quantity or 1)) for item in assemblies),
                "composition_sha256": composition_hash,
                "parts": [item_by_id[part_id].to_dict() for part_id in part_ids],
                "fastener_ids": sorted({item for assembly in assemblies for item in assembly.fastener_ids}),
                "weld_ids": sorted({item for assembly in assemblies for item in assembly.weld_ids}),
                "purchased_item_ids": sorted({item for assembly in assemblies for item in assembly.purchased_item_ids}),
                "projection_method": "tessellated_vector_wireframe",
            }
            assembly_manifest["manifest_sha256"] = stable_hash(assembly_manifest)
            artifacts: list[ArtifactResult] = []

            nc_dir = assembly_dir / "NC"
            pdf_dir = assembly_dir / "PART_PDF"
            nc_dir.mkdir(exist_ok=True)
            pdf_dir.mkdir(exist_ok=True)
            for part_id in part_ids:
                for artifact_result in item_by_id[part_id].artifacts:
                    if artifact_result.status != ArtifactStatus.EXPORTED:
                        continue
                    if artifact_result.format == "nc1":
                        shutil.copy2(root / artifact_result.relative_path, nc_dir / Path(artifact_result.relative_path).name)
                    elif artifact_result.format == "production_pdf":
                        shutil.copy2(root / artifact_result.relative_path, pdf_dir / Path(artifact_result.relative_path).name)

            assembly_pdf = assembly_dir / f"{safe_filename(mark)}_ASSEMBLY.pdf"
            embedded_hash = _write_assembly_pdf(
                project,
                mark,
                [representative.internal_id],
                parts,
                transformed,
                assembly_manifest,
                assembly_pdf,
                assembly_manifest["quantity"],
            )
            artifacts.append(_artifact(root, assembly_pdf, "assembly_pdf", assembly_id=mark, source="canonical-assembly-drawing"))

            assembly_step = assembly_dir / f"{safe_filename(mark)}_ASSEMBLY.step"
            step_assembly = cq.Assembly(name=mark)
            for part_name, shape in transformed:
                step_assembly.add(shape, name=safe_filename(part_name, max_length=60))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                step_assembly.save(
                    str(assembly_step),
                    exportType="STEP",
                    mode="default",
                )
            synthetic = canonicals[part_ids[0]].clone()
            bounds = compound.BoundingBox()
            synthetic.part_id = f"assembly:{mark}"
            synthetic.source_format = "CWSC"
            synthetic.source_file = project.project_name
            synthetic.source_sha256 = project.manufacturing_state_sha256()
            synthetic.import_method = "canonical_assembly_release"
            synthetic.header.part_number = mark
            synthetic.header.position_number = mark
            synthetic.header.profile = "ASSEMBLY"
            synthetic.header.profile_type = "ASSEMBLY"
            synthetic.header.material = "MULTI"
            synthetic.header.quantity = assembly_manifest["quantity"]
            synthetic.header.length = max(bounds.xlen, bounds.ylen, bounds.zlen)
            synthetic.header.saw_length = synthetic.header.length
            synthetic.product.name = mark
            synthetic.product.mark = mark
            synthetic.product.profile_designation = "ASSEMBLY"
            synthetic.product.material_code = "MULTI"
            synthetic.product.main_dimensions_mm = [bounds.xlen, bounds.ylen, bounds.zlen]
            synthetic.contours = []
            synthetic.holes = []
            synthetic.attachments = {}
            synthetic.geometry = {"representation": "assembly_compound", "assembly_manifest": assembly_manifest}
            synthetic.properties = {"assembly_manifest_sha256": assembly_manifest["manifest_sha256"]}
            synthetic.validation.production_export_allowed = True
            synthetic.validation.export_status = "released"
            synthetic.recognition["production_export_allowed"] = True
            synthetic.validate()
            embed_part_in_step(assembly_step, synthetic)
            artifacts.append(_artifact(root, assembly_step, "assembly_step", assembly_id=mark, source="canonical-assembly-compound"))

            assembly_ifc = assembly_dir / f"{safe_filename(mark)}_ASSEMBLY.ifc"
            write_native_ifc(compound, assembly_ifc, name=mark, material="MULTI", canonical=synthetic)
            _enrich_assembly_ifc(assembly_ifc, mark, assembly_manifest)
            artifacts.append(_artifact(root, assembly_ifc, "assembly_ifc", assembly_id=mark, source="canonical-assembly-compound"))

            datasets = {
                "stuklijst.csv": [row.to_dict() for row in bom.part_bom if mark in row.assembly_marks],
                "inkooplijst.csv": [row.to_dict() for row in bom.purchase_bom if mark in row.assembly_marks],
                "boutenlijst.csv": [row.to_dict() for row in bom.fastener_bom if mark in row.assembly_marks],
                "laslijst.csv": [row.to_dict() for row in bom.weld_bom if mark in row.assembly_marks],
                "paklijst.csv": [
                    {
                        "part_id": part.internal_id,
                        "part_position": part.part_position,
                        "quantity": part.quantity_total,
                        "mass_total_kg": part.mass_each_kg * part.quantity_total,
                        "revision": part.revision,
                    }
                    for part in parts
                ],
            }
            for filename, rows in datasets.items():
                target = assembly_dir / filename
                _write_rows(target, rows)
                artifacts.append(_artifact(root, target, filename.removesuffix(".csv"), assembly_id=mark, source="validated-bom"))

            total_report = assembly_dir / "totaalrapport.json"
            atomic_write(
                total_report,
                canonical_json_bytes(
                    {
                        "format": "CWS_ASSEMBLY_TOTAL_REPORT_V1",
                        "project_id": project.project_id,
                        "project_name": project.project_name,
                        "assembly_mark": mark,
                        "quantity": assembly_manifest["quantity"],
                        "composition_sha256": composition_hash,
                        "part_count": len(parts),
                        "part_ids": part_ids,
                        "fastener_ids": assembly_manifest["fastener_ids"],
                        "weld_ids": assembly_manifest["weld_ids"],
                        "purchased_item_ids": assembly_manifest["purchased_item_ids"],
                        "total_mass_kg": sum(
                            float(part.mass_each_kg or 0.0) * max(1, int(part.quantity_total or 1))
                            for part in parts
                        ),
                        "artifacts": [item.to_dict() for item in artifacts],
                    }
                ),
            )
            artifacts.append(
                _artifact(root, total_report, "totaalrapport", assembly_id=mark, source="validated-assembly-summary")
            )

            assembly_manifest["drawing_manifest_sha256"] = embedded_hash
            assembly_manifest["artifacts"] = [item.to_dict() for item in artifacts]
            manifest_path = assembly_dir / "assembly_manifest.json"
            atomic_write(manifest_path, canonical_json_bytes(assembly_manifest))
            sums = [
                f"{sha256_file(path)}  {path.relative_to(assembly_dir).as_posix()}"
                for path in sorted(assembly_dir.rglob("*"))
                if path.is_file() and path.name != "SHA256SUMS.txt"
            ]
            atomic_write(assembly_dir / "SHA256SUMS.txt", ("\n".join(sums) + "\n").encode("utf-8"))
            package_path = assembly_dir.with_suffix(".zip")
            ProductionExportEngine._create_zip(assembly_dir, package_path, request.deterministic_zip)
            artifacts.append(_artifact(root, package_path, "assembly_zip", assembly_id=mark, source="assembly-package"))
            results.append(
                AssemblyPackageResult(
                    assembly_mark=mark,
                    quantity=assembly_manifest["quantity"],
                    part_ids=part_ids,
                    status=ExportStatus.EXPORTED,
                    relative_path=assembly_dir.relative_to(root).as_posix(),
                    sha256=sha256_file(manifest_path),
                    composition_sha256=composition_hash,
                    artifacts=artifacts,
                )
            )
        return results

    def export_project(self, project: ProjectModel, request: ExportRequest) -> tuple[ExportManifest, Path, Path | None]:
        formats = request.normalized_formats() or list(RELEASE_FORMATS)
        invalid = [fmt for fmt in formats if fmt not in SUPPORTED_FORMATS]
        if invalid:
            raise ValueError(f"Niet-ondersteunde formaten: {', '.join(invalid)}")
        project.validate()
        selected = self._select_parts(project, request)
        if not selected:
            raise ProjectValidationError("De exportselectie bevat geen maakdelen")
        conflicts = _filename_conflicts(selected)
        output_name = safe_filename(f"CWS_{project.project_name}_PRODUCTIE")
        final_root = Path(request.output_dir).expanduser().resolve() / output_name

        with atomic_directory(final_root) as root:
            for name in ("parts", "assemblies", "reports"):
                (root / name).mkdir(parents=True, exist_ok=True)
            bom = build_bom_snapshot(project, user="production-export", classify_if_needed=False)
            export_bom_package(bom, root / "reports" / "BOM", package_name=safe_filename(project.project_name))
            items: list[ExportItemResult] = []
            shapes: dict[str, cq.Shape] = {}
            canonicals: dict[str, CanonicalPart] = {}
            for part in selected:
                if part.internal_id in conflicts:
                    positions = ", ".join(sorted(conflicts[part.internal_id]))
                    message = GateMessage(
                        "CWS-REL-010",
                        f"Bestandsnaamconflict: positie {positions} verwijst naar verschillende geometrie",
                        field="part_position",
                    )
                    item = self._blocked_item(project, part, root, request, formats, [message])
                    shape = canonical = None
                else:
                    item, shape, canonical = self._export_part(project, part, root, request, formats)
                items.append(item)
                if shape is not None and canonical is not None:
                    shapes[part.internal_id] = shape
                    canonicals[part.internal_id] = canonical

            assemblies = self._assembly_packages(project, root, request, selected, items, shapes, canonicals, bom)
            status_counter = Counter(item.status.value for item in items)
            artifact_counter = Counter(artifact.status.value for item in items for artifact in item.artifacts)
            manifest = ExportManifest(
                schema_version=self.SCHEMA_VERSION,
                product=APP_NAME,
                product_version=self.product_version,
                export_id=str(uuid4()),
                created_at_utc=utc_now_iso(),
                project_id=project.project_id,
                project_name=project.project_name,
                project_state_hash=project.manufacturing_state_sha256(),
                requested_formats=formats,
                strict_mode=request.strict_mode,
                items=items,
                assemblies=assemblies,
                summary={
                    "selected_parts": len(items),
                    "item_statuses": dict(sorted(status_counter.items())),
                    "artifact_statuses": dict(sorted(artifact_counter.items())),
                    "production_artifacts_exported": sum(
                        1 for item in items for artifact in item.artifacts
                        if artifact.production_artifact and artifact.status == ArtifactStatus.EXPORTED
                    ),
                    "assemblies": len(assemblies),
                    "bom_snapshot_sha256": bom.snapshot_sha256,
                    "production_ready": all(item.status == ExportStatus.EXPORTED for item in items)
                    and all(item.status == ExportStatus.EXPORTED for item in assemblies),
                },
            )
            without_hash = canonical_json_bytes(manifest.to_dict(include_hash=False))
            manifest.manifest_sha256 = sha256_bytes(without_hash)
            atomic_write(root / "manifest.json", canonical_json_bytes(manifest.to_dict()))
            ProductionExportEngine._write_summary_csv(root, items)
            atomic_write(
                root / "README.txt",
                (
                    f"{APP_NAME} vrijgegeven productiepakket\n"
                    "========================================\n"
                    "Controleer manifest.json en SHA256SUMS.txt voor gebruik.\n"
                    "Alle part-productieformaten zijn tijdens deze export opnieuw gegenereerd en heringelezen.\n"
                    "Een bestand met status blocked of skipped is niet vrijgegeven voor productie.\n"
                ).encode("utf-8"),
            )
            ProductionExportEngine._write_checksums(root)

        zip_path: Path | None = None
        if request.create_zip:
            zip_path = final_root.with_suffix(".zip")
            ProductionExportEngine._create_zip(final_root, zip_path, request.deterministic_zip)
        return manifest, final_root, zip_path


__all__ = ["CORE_FORMATS", "RELEASE_FORMATS", "ProjectProductionExportEngine", "_filename_conflicts"]
