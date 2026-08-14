"""Formula-safe CSV/XLSX export for the CWS Viewer V8 property grid."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Sequence

from .grid import ColumnType, GridColumn, GridQueryResult

_DANGEROUS_PREFIXES = ("=", "+", "-", "@")


def formula_safe(value: Any) -> Any:
    """Return spreadsheet-safe literal data without changing numeric values."""
    if value is None or isinstance(value, (int, float, bool)):
        return value
    text = str(value)
    if text.startswith(_DANGEROUS_PREFIXES):
        return "'" + text
    return text


def _selected_columns(columns: Iterable[GridColumn]) -> tuple[GridColumn, ...]:
    return tuple(sorted((item for item in columns if item.visible), key=lambda item: (item.order, item.key)))


def _atomic_target(path: Path) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    return tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))


def _publish(temporary: str, target: Path) -> str:
    os.replace(temporary, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    sidecar = target.with_suffix(target.suffix + ".sha256")
    sidecar_tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
    sidecar_tmp.write_text(digest + "\n", encoding="ascii")
    os.replace(sidecar_tmp, sidecar)
    return digest


def export_grid_csv(
    result: GridQueryResult,
    path: str | Path,
    *,
    columns: Sequence[GridColumn] | None = None,
    delimiter: str = ";",
) -> dict[str, Any]:
    target = Path(path)
    selected = _selected_columns(columns or result.model.columns)
    fd, temporary = _atomic_target(target)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
            writer.writerow([item.label for item in selected])
            for row in result.iter_rows():
                writer.writerow([formula_safe(row.get(item.key)) for item in selected])
        digest = _publish(temporary, target)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return {
        "path": str(target),
        "format": "csv",
        "rows": result.row_count,
        "columns": len(selected),
        "sha256": digest,
        "formula_safe": True,
    }


def export_grid_xlsx(
    result: GridQueryResult,
    path: str | Path,
    *,
    columns: Sequence[GridColumn] | None = None,
    title: str = "CWS Convertor — projecteigenschappen",
) -> dict[str, Any]:
    try:
        import xlsxwriter
    except ImportError as exc:  # pragma: no cover - explicit packaging gate
        raise RuntimeError("XlsxWriter ontbreekt voor XLSX-export") from exc

    target = Path(path)
    selected = _selected_columns(columns or result.model.columns)
    fd, temporary = _atomic_target(target)
    os.close(fd)
    try:
        workbook = xlsxwriter.Workbook(
            temporary,
            {
                "constant_memory": True,
                "strings_to_formulas": False,
                "strings_to_urls": False,
                "nan_inf_to_errors": False,
            },
        )
        workbook.set_properties(
            {
                "title": title,
                "subject": "CWS Viewer V8 property-grid export",
                "author": "CWS Convertor",
                "comments": "Read-only export from the canonical project property grid.",
            }
        )
        sheet = workbook.add_worksheet("Eigenschappen")
        meta = workbook.add_worksheet("Metadata")
        meta.hide()

        title_format = workbook.add_format(
            {
                "bold": True,
                "font_size": 16,
                "font_color": "#FFFFFF",
                "bg_color": "#16324A",
                "align": "left",
                "valign": "vcenter",
            }
        )
        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "#FFFFFF",
                "bg_color": "#214E6B",
                "border": 1,
                "border_color": "#3D627B",
                "align": "left",
                "valign": "vcenter",
            }
        )
        text_format = workbook.add_format({"border": 1, "border_color": "#D7E0E7"})
        integer_format = workbook.add_format({"border": 1, "border_color": "#D7E0E7", "num_format": "0"})
        number_format = workbook.add_format({"border": 1, "border_color": "#D7E0E7", "num_format": "0.000"})
        bool_format = workbook.add_format({"border": 1, "border_color": "#D7E0E7", "align": "center"})
        numeric_formats = {"0.000": number_format, "0": integer_format}
        footer_label_format = workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": "#24455E", "border": 1}
        )
        footer_number_format = workbook.add_format(
            {"bold": True, "font_color": "#FFFFFF", "bg_color": "#24455E", "border": 1, "num_format": "0.000"}
        )

        sheet.set_row(0, 26)
        sheet.merge_range(0, 0, 0, max(0, len(selected) - 1), title, title_format)
        sheet.write_row(1, 0, [item.label for item in selected], header_format)
        sheet.freeze_panes(2, 0)
        sheet.autofilter(1, 0, max(1, result.row_count + 1), max(0, len(selected) - 1))
        sheet.set_landscape()
        sheet.fit_to_pages(1, 0)

        for column_index, column in enumerate(selected):
            width = max(8.0, min(42.0, column.width / 8.0))
            sheet.set_column(column_index, column_index, width)

        for row_index, row in enumerate(result.iter_rows(), start=2):
            for column_index, column in enumerate(selected):
                raw = row.get(column.key)
                value = formula_safe(raw)
                if column.data_type == ColumnType.INTEGER and isinstance(value, (int, float)):
                    sheet.write_number(row_index, column_index, float(value), integer_format)
                elif column.data_type == ColumnType.NUMBER and isinstance(value, (int, float)) and math.isfinite(float(value)):
                    format_code = column.number_format or "0.000"
                    fmt = numeric_formats.get(format_code)
                    if fmt is None:
                        fmt = workbook.add_format(
                            {
                                "border": 1,
                                "border_color": "#D7E0E7",
                                "num_format": format_code,
                            }
                        )
                        numeric_formats[format_code] = fmt
                    sheet.write_number(row_index, column_index, float(value), fmt)
                elif column.data_type == ColumnType.BOOLEAN:
                    sheet.write(row_index, column_index, "Ja" if bool(value) else "Nee", bool_format)
                else:
                    sheet.write(row_index, column_index, value, text_format)

        footer_row = result.row_count + 2
        aggregate_by_key = {item.key: item for item in result.footer.aggregates}
        for column_index, column in enumerate(selected):
            aggregate = aggregate_by_key.get(column.key)
            if column_index == 0:
                sheet.write(footer_row, column_index, f"Totaal: {result.row_count:,} regels", footer_label_format)
            elif aggregate is not None and aggregate.value is not None:
                sheet.write_number(footer_row, column_index, float(aggregate.value), footer_number_format)
            else:
                sheet.write_blank(footer_row, column_index, None, footer_label_format)

        # Status colouring remains visual only and never changes exported values.
        status_columns = {
            column.key: index
            for index, column in enumerate(selected)
            if column.key in {"status", "classification_status", "export_status", "revision_status"}
        }
        for _key, index in status_columns.items():
            data_start, data_end = 2, max(2, result.row_count + 1)
            for token, colour in (
                ("validated", "#D9EAD3"),
                ("released", "#D9EAD3"),
                ("unchanged", "#E7EEF4"),
                ("moved", "#D9EAF7"),
                ("review", "#FFF2CC"),
                ("changed", "#FCE5CD"),
                ("blocked", "#F4CCCC"),
                ("removed", "#F4CCCC"),
                ("ambiguous", "#EADCF8"),
            ):
                sheet.conditional_format(
                    data_start,
                    index,
                    data_end,
                    index,
                    {
                        "type": "text",
                        "criteria": "containing",
                        "value": token,
                        "format": workbook.add_format({"bg_color": colour}),
                    },
                )

        metadata = {
            "format": "CWS_VIEWER_GRID_EXPORT_V1",
            "rows": result.row_count,
            "columns": [item.to_dict() for item in selected],
            "query": result.query.to_dict(),
            "footer": result.footer.to_dict(),
            "formula_safe": True,
        }
        meta.write(0, 0, json.dumps(metadata, ensure_ascii=False, sort_keys=True))
        workbook.close()
        digest = _publish(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return {
        "path": str(target),
        "format": "xlsx",
        "rows": result.row_count,
        "columns": len(selected),
        "sha256": digest,
        "formula_safe": True,
    }


__all__ = ["export_grid_csv", "export_grid_xlsx", "formula_safe"]
