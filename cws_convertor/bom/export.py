"""Professional, injection-safe BOM package export."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
from typing import Any, Iterable

from cws_convertor.product import APP_NAME, APP_VERSION
from .models import BOMSnapshot

_DANGEROUS_PREFIXES = ("=", "+", "-", "@")


def safe_spreadsheet_value(value: Any) -> Any:
    """Prevent CSV/XLSX formula injection while preserving numbers."""
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple, set)):
        value = ", ".join(str(item) for item in value)
    elif isinstance(value, dict):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = str(value)
    if text.lstrip().startswith(_DANGEROUS_PREFIXES):
        return "'" + text
    return text


def _flatten_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in rows:
        raw = item.to_dict() if hasattr(item, "to_dict") else dict(item)
        result.append({key: safe_spreadsheet_value(value) for key, value in raw.items()})
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
        if headers:
            writer.writeheader()
            writer.writerows(rows)


def _sheet_title(name: str) -> str:
    return re.sub(r"[\[\]:*?/\\]", "_", name)[:31]


def _write_xlsx(path: Path, snapshot: BOMSnapshot) -> None:
    import xlsxwriter

    workbook = xlsxwriter.Workbook(
        str(path),
        {"strings_to_formulas": False, "strings_to_urls": False},
    )
    workbook.set_properties({
        "title": f"{snapshot.project_name} — BOM",
        "subject": f"{APP_NAME} classificatie, BOM en herkomst",
        "author": APP_NAME,
        "company": "CWS",
        "comments": f"Gegenereerd met {APP_NAME} {APP_VERSION}",
    })
    navy = "#17365D"
    blue = "#2F75B5"
    pale_blue = "#D9EAF7"
    pale_green = "#E2F0D9"
    pale_orange = "#FCE4D6"
    pale_red = "#F4CCCC"
    grey = "#E7E6E6"
    white = "#FFFFFF"
    title_fmt = workbook.add_format({
        "bold": True, "font_size": 20, "font_color": white, "bg_color": navy,
        "align": "left", "valign": "vcenter",
    })
    subtitle_fmt = workbook.add_format({
        "font_size": 10, "font_color": "#44546A", "bg_color": pale_blue,
        "align": "left", "valign": "vcenter",
    })
    header_fmt = workbook.add_format({
        "bold": True, "font_color": white, "bg_color": blue, "border": 1,
        "align": "center", "valign": "vcenter", "text_wrap": True,
    })
    cell_fmt = workbook.add_format({"border": 1, "border_color": "#D9E1F2", "valign": "top"})
    wrap_fmt = workbook.add_format({"border": 1, "border_color": "#D9E1F2", "valign": "top", "text_wrap": True})
    int_fmt = workbook.add_format({"border": 1, "border_color": "#D9E1F2", "num_format": "0"})
    num_fmt = workbook.add_format({"border": 1, "border_color": "#D9E1F2", "num_format": "0.000"})
    mass_fmt = workbook.add_format({"border": 1, "border_color": "#D9E1F2", "num_format": "0.00"})
    money_fmt = workbook.add_format({"border": 1, "border_color": "#D9E1F2", "num_format": "€ #,##0.00"})
    kpi_label = workbook.add_format({"bold": True, "font_color": white, "bg_color": blue, "border": 1})
    kpi_value = workbook.add_format({"bold": True, "font_size": 14, "bg_color": pale_blue, "border": 1})
    ok_fmt = workbook.add_format({"bold": True, "font_color": "#006100", "bg_color": pale_green, "border": 1})
    warn_fmt = workbook.add_format({"bold": True, "font_color": "#9C5700", "bg_color": pale_orange, "border": 1})
    block_fmt = workbook.add_format({"bold": True, "font_color": "#9C0006", "bg_color": pale_red, "border": 1})

    dash = workbook.add_worksheet("Dashboard")
    dash.hide_gridlines(2)
    dash.set_tab_color(navy)
    dash.set_row(0, 32)
    dash.merge_range("A1:H1", f"{APP_NAME} — Classificatie & BOM", title_fmt)
    dash.merge_range("A2:H2", f"Project: {snapshot.project_name}  |  Snapshot: {snapshot.snapshot_sha256[:16]}", subtitle_fmt)
    dash.set_column("A:A", 28)
    dash.set_column("B:B", 18)
    dash.set_column("C:H", 16)
    kpis = [
        ("Unieke maak-/materiaalregels", snapshot.summary.get("part_group_count", 0)),
        ("Assemblymerken", snapshot.summary.get("assembly_group_count", 0)),
        ("Inkoopgroepen", snapshot.summary.get("purchase_group_count", 0)),
        ("Bevestigergroepen", snapshot.summary.get("fastener_group_count", 0)),
        ("Lasgroepen", snapshot.summary.get("weld_group_count", 0)),
        ("Materiaalgroepen", snapshot.summary.get("material_group_count", 0)),
        ("Totale massa (kg)", snapshot.summary.get("total_part_mass_kg", 0)),
        ("Herkomstregels", snapshot.summary.get("traceability_record_count", 0)),
    ]
    for index, (label, value) in enumerate(kpis):
        row = 3 + index // 2 * 2
        col = (index % 2) * 3
        dash.merge_range(row, col, row, col + 1, label, kpi_label)
        dash.merge_range(row + 1, col, row + 1, col + 1, value, kpi_value)
    status_row = 13
    validation = snapshot.validation
    status = "PRODUCTIEGEREED" if validation and validation.production_ready else "GEBLOKKEERD / REVIEW"
    dash.write(status_row, 0, "Productiestatus", kpi_label)
    dash.merge_range(status_row, 1, status_row, 3, status, ok_fmt if status.startswith("PRODUCTIE") else block_fmt)
    dash.write(status_row + 1, 0, "Blokkerende conflicten", kpi_label)
    dash.write(status_row + 1, 1, snapshot.summary.get("blocking_conflict_count", 0), block_fmt)
    dash.write(status_row + 2, 0, "Waarschuwingen", kpi_label)
    dash.write(status_row + 2, 1, snapshot.summary.get("warning_conflict_count", 0), warn_fmt)
    dash.write(status_row + 4, 0, "Belangrijk", kpi_label)
    dash.merge_range(
        status_row + 4, 1, status_row + 6, 7,
        "BOM-validatie controleert dekking en materiaalbalans. Externe IFC/STEP-productie-export blijft geblokkeerd totdat profiel, features, referentiezijden en roundtrip per onderdeel zijn gevalideerd.",
        wrap_fmt,
    )

    datasets = [
        ("Part BOM", snapshot.part_bom),
        ("Assembly BOM", snapshot.assembly_bom),
        ("Inkoop", snapshot.purchase_bom),
        ("Bevestigers", snapshot.fastener_bom),
        ("Lassen", snapshot.weld_bom),
        ("Materialen", snapshot.material_bom),
        ("Conflicten", snapshot.conflicts),
        ("Herkomst", snapshot.traceability),
    ]
    for sheet_name, source_rows in datasets:
        rows = _flatten_rows(source_rows)
        ws = workbook.add_worksheet(_sheet_title(sheet_name))
        ws.hide_gridlines(2)
        ws.freeze_panes(1, 0)
        ws.set_tab_color(blue if sheet_name not in {"Conflicten"} else "#C00000")
        if not rows:
            ws.write(0, 0, "Geen gegevens", header_fmt)
            continue
        headers = list(rows[0])
        for col, header in enumerate(headers):
            ws.write(0, col, header, header_fmt)
        for row_index, row in enumerate(rows, start=1):
            for col, header in enumerate(headers):
                value = row.get(header, "")
                fmt = cell_fmt
                if isinstance(value, bool):
                    fmt = cell_fmt
                elif isinstance(value, int):
                    fmt = int_fmt
                elif isinstance(value, float):
                    fmt = money_fmt if "price" in header or "cost" in header else (mass_fmt if "mass" in header else num_fmt)
                elif len(str(value)) > 50:
                    fmt = wrap_fmt
                ws.write(row_index, col, value, fmt)
        ws.set_row(0, 30)
        for col, header in enumerate(headers):
            max_len = max([len(str(header))] + [len(str(row.get(header, ""))) for row in rows[:1000]])
            width = min(40, max(10, max_len + 2))
            if header.endswith("_hash") or header.endswith("_ids") or header in {"blocking_reasons", "warnings", "message", "evidence"}:
                width = min(40, max(24, width))
            ws.set_column(col, col, width)
        if "blocked" in headers:
            col = headers.index("blocked")
            ws.conditional_format(1, col, len(rows), col, {
                "type": "cell", "criteria": "equal to", "value": True,
                "format": block_fmt,
            })
        if sheet_name == "Conflicten" and "blocking" in headers:
            col = headers.index("blocking")
            ws.conditional_format(1, col, len(rows), col, {
                "type": "cell", "criteria": "equal to", "value": True,
                "format": block_fmt,
            })
        table_name = re.sub(r"[^A-Za-z0-9]", "", sheet_name) + "Table"
        ws.add_table(0, 0, len(rows), len(headers) - 1, {
            "name": table_name,
            "style": "Table Style Medium 2",
            "columns": [{"header": header} for header in headers],
        })

    validation_ws = workbook.add_worksheet("Validatie")
    validation_ws.hide_gridlines(2)
    validation_ws.set_column("A:A", 34)
    validation_ws.set_column("B:B", 18)
    validation_ws.set_column("C:C", 80)
    validation_ws.write_row(0, 0, ["Controle", "Resultaat", "Toelichting"], header_fmt)
    checks = snapshot.validation.checks if snapshot.validation else {}
    row = 1
    for name, passed in sorted(checks.items()):
        validation_ws.write(row, 0, name, cell_fmt)
        validation_ws.write(row, 1, "GESLAAGD" if passed else "MISLUKT", ok_fmt if passed else block_fmt)
        validation_ws.write(row, 2, "Deterministische dekking-/balanscontrole", wrap_fmt)
        row += 1
    if snapshot.validation:
        for message in snapshot.validation.messages:
            validation_ws.write(row, 0, "Melding", warn_fmt)
            validation_ws.merge_range(row, 1, row, 2, safe_spreadsheet_value(message), wrap_fmt)
            row += 1
    workbook.close()


def _scan_xlsx_formula_errors(path: Path) -> None:
    from xml.etree import ElementTree

    errors: list[str] = []
    tokens = ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#NUM!", "#N/A")
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.startswith("xl/worksheets/") or not name.endswith(".xml"):
                continue
            raw = archive.read(name)
            upper = raw.upper()
            if not any(token.encode("ascii") in upper for token in tokens) and b't="e"' not in raw:
                continue
            root = ElementTree.fromstring(raw)
            for cell in root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                value = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                text = str(value.text or "") if value is not None else ""
                if cell.get("t") == "e" or text.upper().startswith(tokens):
                    errors.append(f"{name}!{cell.get('r', '?')}={text or 'formula error'}")
    if errors:
        raise ValueError("BOM-XLSX bevat formulefouten: " + "; ".join(errors[:20]))


def _write_pdf(path: Path, snapshot: BOMSnapshot) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    story: list[Any] = [
        Paragraph(f"{APP_NAME} - Project BOM", styles["Title"]),
        Paragraph(f"Project: {snapshot.project_name}", styles["Heading2"]),
        Paragraph(f"Snapshot SHA-256: {snapshot.snapshot_sha256}", styles["Code"]),
        Spacer(1, 5 * mm),
    ]
    summary_rows = [["Kenmerk", "Waarde"]] + [
        [str(key), str(value)] for key, value in sorted(snapshot.summary.items())
    ]
    story.append(Table(summary_rows, repeatRows=1, colWidths=(95 * mm, 155 * mm)))
    datasets = (
        ("Part BOM", snapshot.part_bom),
        ("Assembly BOM", snapshot.assembly_bom),
        ("Inkoop", snapshot.purchase_bom),
        ("Bevestigers", snapshot.fastener_bom),
        ("Lassen", snapshot.weld_bom),
        ("Materialen", snapshot.material_bom),
    )
    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C4D4")),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])
    for title, source_rows in datasets:
        rows = _flatten_rows(source_rows)
        story.extend((PageBreak(), Paragraph(title, styles["Heading1"])))
        if not rows:
            story.append(Paragraph("Geen gegevens", styles["BodyText"]))
            continue
        headers = list(rows[0])
        values = [headers] + [[str(row.get(header, "")) for header in headers] for row in rows]
        table = Table(values, repeatRows=1, hAlign="LEFT")
        table.setStyle(table_style)
        story.append(table)
    document = SimpleDocTemplate(
        str(path), pagesize=landscape(A4),
        leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=10 * mm,
        title=f"{snapshot.project_name} BOM", author=APP_NAME,
    )
    document.build(story)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_bom_package(
    snapshot: BOMSnapshot,
    output_dir: str | Path,
    *,
    package_name: str | None = None,
) -> dict[str, Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    stem = package_name or re.sub(r"[^A-Za-z0-9._-]+", "_", snapshot.project_name).strip("_") or "CWS_BOM"
    work = Path(tempfile.mkdtemp(prefix="cws-bom-", dir=str(target)))
    try:
        json_path = work / f"{stem}_BOM.json"
        json_path.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        xlsx_path = work / f"{stem}_BOM.xlsx"
        _write_xlsx(xlsx_path, snapshot)
        _scan_xlsx_formula_errors(xlsx_path)
        _write_pdf(work / f"{stem}_BOM.pdf", snapshot)
        datasets = {
            "part_bom": snapshot.part_bom,
            "assembly_bom": snapshot.assembly_bom,
            "purchase_bom": snapshot.purchase_bom,
            "fastener_bom": snapshot.fastener_bom,
            "weld_bom": snapshot.weld_bom,
            "material_bom": snapshot.material_bom,
            "conflicts": snapshot.conflicts,
            "traceability": snapshot.traceability,
        }
        for name, rows in datasets.items():
            _write_csv(work / f"{name}.csv", _flatten_rows(rows))
        validation_path = work / "validation.json"
        validation_path.write_text(
            json.dumps(snapshot.validation.to_dict() if snapshot.validation else {}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        manifest = {
            "format": "CWS_BOM_PACKAGE_V1",
            "app": APP_NAME,
            "app_version": APP_VERSION,
            "project_id": snapshot.project_id,
            "snapshot_sha256": snapshot.snapshot_sha256,
            "files": {},
        }
        for path in sorted(work.iterdir()):
            if path.is_file() and path.name not in {"manifest.json", "SHA256SUMS.txt"}:
                manifest["files"][path.name] = {"sha256": _sha256(path), "size": path.stat().st_size}
        manifest_path = work / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        checksums = [f"{_sha256(path)}  {path.name}" for path in sorted(work.iterdir()) if path.is_file()]
        sums_path = work / "SHA256SUMS.txt"
        sums_path.write_text("\n".join(checksums) + "\n", encoding="utf-8")

        outputs: dict[str, Path] = {}
        for path in sorted(work.iterdir()):
            final = target / path.name
            shutil.copy2(path, final)
            outputs[path.name] = final
        zip_path = target / f"{stem}_BOM_PACKAGE.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(work.iterdir()):
                archive.write(path, arcname=path.name)
        outputs[zip_path.name] = zip_path
        return outputs
    finally:
        shutil.rmtree(work, ignore_errors=True)


__all__ = ["safe_spreadsheet_value", "export_bom_package"]
