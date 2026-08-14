"""Measurement JSON/CSV/PDF exports without altering geometry or review state.

Exports are deterministic review artefacts.  They never grant production
readiness.  Files are written atomically and accompanied by a SHA-256 sidecar
so they can be attached to a CWS audit package without silent corruption.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable

from .model import MeasurementRecord


def _atomic_write(path: Path, raw: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    digest = hashlib.sha256(raw).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    fd, temp_name = tempfile.mkstemp(prefix=f".{sidecar.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="ascii", newline="\n") as handle:
            handle.write(digest + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, sidecar)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return path


def export_json(records: Iterable[MeasurementRecord], path: str | Path) -> Path:
    output = Path(path)
    payload = {
        "schema": "cws-viewer-measurements-1.1",
        "production_release_allowed": False,
        "measurements": [item.to_dict() for item in records],
    }
    raw = (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    return _atomic_write(output, raw)


def export_csv(records: Iterable[MeasurementRecord], path: str | Path) -> Path:
    output = Path(path)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=[
            "measurement_id",
            "kind",
            "formatted_text",
            "value",
            "unit",
            "proof",
            "status",
            "production_eligible",
            "name",
            "note",
            "anchor_count",
            "invalid_reason",
        ],
    )
    writer.writeheader()
    for item in records:
        writer.writerow(
            {
                "measurement_id": item.measurement_id,
                "kind": item.kind,
                "formatted_text": item.formatted_text,
                "value": item.value,
                "unit": item.unit,
                "proof": item.proof.value,
                "status": item.status.value,
                "production_eligible": item.production_eligible,
                "name": item.name,
                "note": item.note,
                "anchor_count": len(item.anchors),
                "invalid_reason": item.invalid_reason,
            }
        )
    return _atomic_write(output, ("\ufeff" + stream.getvalue()).encode("utf-8"))


def export_pdf(
    records: Iterable[MeasurementRecord],
    path: str | Path,
    *,
    title: str = "CWS Convertor — meetrapport",
    project_name: str = "",
) -> Path:
    """Create a vector/searchable review PDF.

    ReportLab is intentionally loaded only when PDF export is requested so the
    headless measurement engine remains lightweight.
    """

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:  # pragma: no cover - dependency/Windows diagnostics
        raise RuntimeError("ReportLab ontbreekt; meetrapport-PDF kan niet worden gemaakt") from exc

    output = Path(path)
    values = tuple(records)
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
        author="CWS Convertor",
        subject="Viewer measurements — review evidence, not production release",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CwsTitle",
        parent=styles["Title"],
        alignment=TA_LEFT,
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=20,
        textColor=colors.HexColor("#17324D"),
        spaceAfter=6,
    )
    note_style = ParagraphStyle(
        "CwsNote",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#6B3F00"),
    )
    story = [Paragraph(title, title_style)]
    if project_name:
        story.append(Paragraph(f"Project: {project_name}", styles["Heading3"]))
    story.append(
        Paragraph(
            "Dit rapport bevat viewer-/reviewmetingen. Productievrijgave blijft "
            "format-specifiek en deterministisch geblokkeerd totdat de CWS-validatiepoort slaagt.",
            note_style,
        )
    )
    story.append(Spacer(1, 5 * mm))
    data: list[list[object]] = [[
        "ID", "Type", "Waarde", "Bewijs", "Status", "Productie-evidence", "Naam / opmerking"
    ]]
    for item in values:
        note = " — ".join(value for value in (item.name, item.note, item.invalid_reason) if value)
        data.append(
            [
                item.measurement_id,
                item.kind,
                item.formatted_text or f"{item.value} {item.unit}",
                item.proof.value,
                item.status.value,
                "JA" if item.production_eligible else "NEE",
                note,
            ]
        )
    if len(data) == 1:
        data.append(["—", "Geen metingen", "", "", "", "NEE", ""])
    table = Table(data, repeatRows=1, colWidths=[38*mm, 27*mm, 31*mm, 30*mm, 23*mm, 28*mm, 85*mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("LEADING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9AA8B5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF3F7")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    document.build(story)
    return _atomic_write(output, buffer.getvalue())


__all__ = ["export_json", "export_csv", "export_pdf"]
