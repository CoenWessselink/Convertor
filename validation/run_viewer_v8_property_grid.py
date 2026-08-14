#!/usr/bin/env python3
"""Run the CWS Viewer V8 professional property-grid acceptance gate.

The V8 gate validates one renderer-neutral grid datasource across:
- a deterministic 20k-row synthetic workload;
- the real private CWS `.cwscproj` reference when available;
- V7 revision scopes and impacts;
- tenant-aware, atomic layout persistence;
- formula-safe CSV/XLSX exports;
- stable-ID viewer-selection bridging contracts (covered by smoke tests);
- machine-readable, checksum-verifiable evidence.

The generated image is renderer-independent evidence created from real query
results. It is deliberately labelled as *not* a dynamic Qt screenshot. The
Windows workflow separately gates the actual PySide6/VTK interface.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.storage import ProjectStore
from cws_viewer.properties import (
    FilterOperator,
    GridFilter,
    GridGroupSpec,
    GridLayout,
    GridLayoutIdentity,
    GridLayoutStore,
    GridQuery,
    GridScope,
    GridSort,
    ProjectGridModel,
    export_grid_csv,
    export_grid_xlsx,
)
from cws_viewer.version import VIEWER_API_VERSION, VIEWER_PACKAGE_VERSION

REFERENCE_PROJECT_NAME = "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
COMPARE_RELATIVE = Path("validation/viewer_v7/REAL_PROJECT_COMPARE_MANIFEST.json")


def _default_project() -> Path:
    candidates: list[Path] = []
    for variable in ("CWS_V8_REFERENCE_PROJECT", "CWS_REFERENCE_PROJECT"):
        explicit = os.environ.get(variable, "").strip()
        if explicit:
            candidates.append(Path(explicit).expanduser())
    reference_root = os.environ.get("CWS_REFERENCE_ROOT", "").strip()
    if reference_root:
        candidates.append(Path(reference_root).expanduser() / REFERENCE_PROJECT_NAME)
    candidates.extend(
        [
            ROOT / "reference_inputs" / REFERENCE_PROJECT_NAME,
            ROOT.parent / "reference_inputs" / REFERENCE_PROJECT_NAME,
            Path("/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL")
            / REFERENCE_PROJECT_NAME,
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return (ROOT / "reference_inputs" / REFERENCE_PROJECT_NAME).resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return path


def _write_csv(path: Path, headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(headers)
        writer.writerows(rows)
    os.replace(temporary, path)
    return path


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _part(index: int) -> SimpleNamespace:
    blocked = index % 17 == 0
    material = "S355JR" if index % 3 else "S235JR"
    profile = ("HEA140", "HEA160", "STRIP5*120", "D20")[index % 4]
    assembly = f"M{index // 100:04d}"
    name = f"Onderdeel {index:06d}"
    # Dedicated formula-injection rows make the export gate observable.
    if index == 7:
        name = "=HYPERLINK(\"https://invalid.example\",\"test\")"
    elif index == 8:
        name = "+SUM(1,1)"
    return SimpleNamespace(
        internal_id=f"part-{index:06d}",
        status="blocked" if blocked else "validated",
        category="make_part",
        part_position=f"P{index:06d}",
        assembly_ids=[assembly],
        name=name,
        profile=profile,
        normalized_profile=profile,
        material=material,
        normalized_material=material,
        length_mm=float(500 + index % 7500),
        quantity_total=1 + index % 4,
        mass_each_kg=float((index % 250) / 10.0),
        surface_area_each_m2=float((index % 100) / 100.0),
        classification_status="confirmed" if not blocked else "review_required",
        export_status="blocked" if blocked else "ready",
        nc1_eligible=not blocked,
        validation_issues=(
            ()
            if not blocked
            else (SimpleNamespace(code="CWS-V8-TEST-BLOCK", message="Controle vereist"),)
        ),
        source_identity=SimpleNamespace(
            source_entity_id=str(index + 1),
            source_format="IFC",
            assembly_mark=assembly,
            part_position=f"P{index:06d}",
        ),
        confidence=1.0,
        geometry_hash=(f"{index % 16:x}" * 64),
        manufacturing_hash=(f"{(index + 1) % 16:x}" * 64),
    )


def _synthetic_project(count: int) -> SimpleNamespace:
    return SimpleNamespace(
        project_id="v8-synthetic-project",
        project_name="CWS Viewer V8 20k Grid Validation",
        project_phase="Productie",
        parts={f"part-{index:06d}": _part(index) for index in range(count)},
        assemblies={},
        purchased_items={},
        fasteners={},
        welds={},
    )


def _revision_report(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    report = payload.get("report")
    return report if isinstance(report, Mapping) else None


def _column(model: ProjectGridModel, key: str):
    return next(column for column in model.columns if column.key == key)


def _build_layout(model: ProjectGridModel) -> GridLayout:
    visible_keys = {
        "status",
        "entity_type",
        "assembly_mark",
        "part_position",
        "name",
        "profile",
        "material",
        "length_mm",
        "quantity_total",
        "total_mass_kg",
        "classification_status",
        "revision_status",
        "revision_impacts",
        "blocked",
        "warnings",
    }
    ordered_keys = [
        "status",
        "revision_status",
        "assembly_mark",
        "part_position",
        "name",
        "entity_type",
        "profile",
        "material",
        "length_mm",
        "quantity_total",
        "total_mass_kg",
        "classification_status",
        "revision_impacts",
        "blocked",
        "warnings",
    ]
    order_by_key = {key: index for index, key in enumerate(ordered_keys)}
    columns = []
    for column in model.columns:
        order = order_by_key.get(column.key, len(ordered_keys) + column.order)
        width = column.width
        if column.key in {"name", "warnings", "revision_impacts"}:
            width = max(width, 220)
        columns.append(
            replace(
                column,
                visible=column.key in visible_keys,
                order=order,
                width=width,
                frozen=column.key in {"status", "revision_status", "assembly_mark", "part_position"},
            )
        )
    return GridLayout(
        name="CWS V8 Productiecontrole",
        columns=tuple(columns),
        sorts=(GridSort("revision_status"), GridSort("assembly_mark"), GridSort("part_position")),
        filters=(),
        groups=(GridGroupSpec("revision_status"), GridGroupSpec("assembly_mark")),
        scope=GridScope.ALL,
        row_height=25,
        alternating_rows=True,
    )


def _row_values(result, limit: int = 12) -> list[dict[str, Any]]:
    return [row.as_dict() for row in result.rows_page(0, limit)]


def _draw_kpi(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, title: str, value: str, colour: tuple[int, int, int]) -> None:
    draw.rounded_rectangle((x, y, x + w, y + 86), radius=12, fill=(28, 42, 56), outline=(63, 82, 99), width=1)
    draw.text((x + 14, y + 12), title, fill=(163, 181, 197), font=_font(16))
    draw.text((x + 14, y + 40), value, fill=colour, font=_font(27, bold=True))


_HEADER_LABELS = {
    "assembly_mark": "Merk",
    "part_position": "Pos.",
    "profile": "Profiel",
    "material": "Materiaal",
    "length_mm": "Lengte",
    "revision_status": "Revisie",
    "blocked": "Blok.",
    "revision_impacts": "Impact",
    "production_reuse": "Hergebruik",
    "entity_type": "Type",
    "name": "Naam",
    "classification_status": "Classificatie",
    "blockers": "Blokkadereden",
}


def _draw_table(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    w: int,
    title: str,
    columns: Sequence[tuple[str, int]],
    rows: Sequence[Mapping[str, Any]],
    row_height: int = 28,
) -> int:
    title_font = _font(18, bold=True)
    header_font = _font(13, bold=True)
    text_font = _font(12)
    draw.rounded_rectangle((x, y, x + w, y + 38 + row_height * (len(rows) + 1) + 12), radius=10, fill=(19, 31, 43), outline=(56, 75, 91), width=1)
    draw.text((x + 12, y + 9), title, fill=(234, 242, 248), font=title_font)
    y0 = y + 38
    draw.rectangle((x + 1, y0, x + w - 1, y0 + row_height), fill=(37, 56, 72))
    cx = x + 8
    for key, width in columns:
        draw.text((cx, y0 + 6), _HEADER_LABELS.get(key, key), fill=(217, 229, 238), font=header_font)
        cx += width
        draw.line((cx - 5, y0 + 4, cx - 5, y0 + row_height - 4), fill=(73, 96, 114), width=1)
    for row_index, row in enumerate(rows):
        ry = y0 + row_height * (row_index + 1)
        fill = (24, 38, 51) if row_index % 2 == 0 else (20, 34, 47)
        draw.rectangle((x + 1, ry, x + w - 1, ry + row_height), fill=fill)
        cx = x + 8
        for key, width in columns:
            raw = row.get(key, "")
            text = str(raw if raw is not None else "")
            max_chars = max(4, int(width / 7.2))
            if len(text) > max_chars:
                text = text[: max(1, max_chars - 1)] + "…"
            colour = (225, 232, 237)
            if key in {"status", "revision_status", "blocked"}:
                token = text.casefold()
                if any(item in token for item in ("blocked", "removed", "true", "changed")):
                    colour = (255, 154, 154)
                elif "moved" in token:
                    colour = (125, 202, 255)
                elif any(item in token for item in ("validated", "unchanged", "false")):
                    colour = (143, 221, 167)
            draw.text((cx, ry + 6), text, fill=colour, font=text_font)
            cx += width
    return y + 38 + row_height * (len(rows) + 1) + 12


def _render_evidence(
    path: Path,
    *,
    synthetic: Mapping[str, Any],
    real: Mapping[str, Any] | None,
    lo4_rows: Sequence[Mapping[str, Any]],
    changed_rows: Sequence[Mapping[str, Any]],
    blocked_rows: Sequence[Mapping[str, Any]],
) -> Path:
    canvas = Image.new("RGB", (1800, 1260), (10, 18, 28))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1800, 78), fill=(19, 45, 66))
    draw.text((32, 18), "CWS Viewer V8 — Professional Property Grid", fill=(242, 248, 252), font=_font(30, bold=True))
    draw.text((33, 54), "Renderer-independent validation evidence — not a dynamic Qt screenshot", fill=(154, 188, 211), font=_font(15))

    _draw_kpi(draw, 30, 100, 265, "Synthetic rows", f"{synthetic['rows']:,}", (105, 205, 255))
    _draw_kpi(draw, 315, 100, 265, "Build time", f"{synthetic['build_ms']:.1f} ms", (141, 226, 160))
    _draw_kpi(draw, 600, 100, 265, "Complex query", f"{synthetic['query_ms']:.1f} ms", (255, 201, 112))
    _draw_kpi(draw, 885, 100, 265, "Blocked rows", f"{synthetic['blocked_rows']:,}", (255, 141, 141))
    _draw_kpi(draw, 1170, 100, 265, "Real project", "LOADED" if real else "NOT AVAILABLE", (141, 226, 160) if real else (255, 201, 112))
    _draw_kpi(draw, 1455, 100, 315, "Viewer / API", f"{VIEWER_PACKAGE_VERSION} / {VIEWER_API_VERSION}", (185, 158, 255))

    y = 210
    if real:
        draw.text((32, y), "Real .cwscproj overview", fill=(239, 245, 249), font=_font(22, bold=True))
        draw.text(
            (32, y + 32),
            f"Assemblies {real['counts'].get('assembly', 0):,}   Parts {real['counts'].get('part', 0):,}   Fasteners {real['counts'].get('fastener', 0):,}   Welds {real['counts'].get('weld', 0):,}   Changed {real['changed_rows']:,}   Blocked {real['blocked_rows']:,}",
            fill=(165, 187, 203),
            font=_font(16),
        )
        y += 74
    else:
        draw.text((32, y), "Private reference model not available in this runtime; synthetic gate is explicit.", fill=(255, 201, 112), font=_font(18, bold=True))
        y += 50

    left_w = 855
    right_x = 915
    lo4_cols = (("assembly_mark", 110), ("part_position", 100), ("profile", 140), ("material", 110), ("length_mm", 100), ("revision_status", 120), ("blocked", 80))
    changed_cols = (("revision_status", 110), ("part_position", 110), ("profile", 130), ("material", 110), ("revision_impacts", 220), ("production_reuse", 110))
    blocked_cols = (("entity_type", 110), ("part_position", 120), ("name", 260), ("classification_status", 180), ("blockers", 900))

    _draw_table(draw, x=30, y=y, w=left_w, title="LO4 / MLO4 — stable canonical IDs", columns=lo4_cols, rows=lo4_rows[:6])
    _draw_table(draw, x=right_x, y=y, w=855, title="V7 revision scope — changed / moved / removed", columns=changed_cols, rows=changed_rows[:8])
    y2 = y + 350
    _draw_table(draw, x=30, y=y2, w=1740, title="Blocked scope — reasons remain visible and exportable", columns=blocked_cols, rows=blocked_rows[:12])

    footer_y = 1195
    draw.line((30, footer_y, 1770, footer_y), fill=(58, 79, 95), width=1)
    draw.text((32, footer_y + 14), "Evidence source: deterministic ProjectGridModel queries and actual exported rows. Qt/VTK GUI gate remains Windows-only.", fill=(132, 156, 174), font=_font(14))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=_default_project())
    parser.add_argument("--compare", type=Path, default=ROOT / COMPARE_RELATIVE)
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "viewer_v8")
    parser.add_argument("--synthetic-rows", type=int, default=20_000)
    parser.add_argument("--allow-missing-project", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    gates: list[dict[str, Any]] = []

    def gate(code: str, passed: bool, actual: Any, expected: Any, note: str = "") -> None:
        gates.append({"code": code, "passed": bool(passed), "actual": actual, "expected": expected, "note": note})

    # ------------------------------------------------------------------
    # Synthetic 20k virtualisation/performance gate
    # ------------------------------------------------------------------
    synthetic_project = _synthetic_project(max(1, int(args.synthetic_rows)))
    t0 = time.perf_counter()
    synthetic_model = ProjectGridModel(synthetic_project)
    build_ms = (time.perf_counter() - t0) * 1000.0
    synthetic_query = GridQuery(
        text="HEA",
        filters=(
            GridFilter("material", FilterOperator.EQ, "S355JR"),
            GridFilter("length_mm", FilterOperator.BETWEEN, 1000, 5000),
        ),
        sorts=(GridSort("length_mm", descending=True), GridSort("part_position")),
        groups=(GridGroupSpec("profile"), GridGroupSpec("assembly_mark")),
    )
    synthetic_result = synthetic_model.execute(synthetic_query)
    blocked_result = synthetic_model.execute(GridQuery(scope=GridScope.BLOCKED, sorts=(GridSort("part_position"),)))
    selected_ids = [f"part-{index:06d}" for index in range(0, min(500, args.synthetic_rows), 11)]
    visible_ids = [f"part-{index:06d}" for index in range(min(5000, args.synthetic_rows))]
    synthetic_model.set_scope_state(selected_entity_ids=selected_ids, visible_entity_ids=visible_ids)
    selected_result = synthetic_model.execute(GridQuery(scope=GridScope.SELECTED))
    visible_result = synthetic_model.execute(GridQuery(scope=GridScope.VISIBLE))

    synthetic_summary = {
        "rows": len(synthetic_model.rows),
        "build_ms": build_ms,
        "query_rows": synthetic_result.row_count,
        "query_ms": synthetic_result.elapsed_ms,
        "group_count": len(synthetic_result.groups),
        "blocked_rows": blocked_result.row_count,
        "selected_rows": selected_result.row_count,
        "visible_rows": visible_result.row_count,
        "first_page_size": len(synthetic_result.rows_page(0, 50)),
    }
    gate("V8-SYNTHETIC-ROW-COUNT", len(synthetic_model.rows) == args.synthetic_rows, len(synthetic_model.rows), args.synthetic_rows)
    gate("V8-SYNTHETIC-BUILD-PERFORMANCE", build_ms < 5000.0, round(build_ms, 3), "<5000 ms", "Development guardrail; not an end-user SLA")
    gate("V8-SYNTHETIC-QUERY-PERFORMANCE", synthetic_result.elapsed_ms < 1500.0, round(synthetic_result.elapsed_ms, 3), "<1500 ms", "Multi-filter, multi-sort and two-level grouping")
    gate("V8-VIRTUAL-PAGE", len(synthetic_result.rows_page(0, 50)) == min(50, synthetic_result.row_count), len(synthetic_result.rows_page(0, 50)), min(50, synthetic_result.row_count))
    gate("V8-SCOPE-SELECTED", selected_result.row_count == len(selected_ids), selected_result.row_count, len(selected_ids))
    gate("V8-SCOPE-VISIBLE", visible_result.row_count == len(visible_ids), visible_result.row_count, len(visible_ids))
    gate("V8-SCOPE-BLOCKED", blocked_result.row_count > 0 and all(bool(row.get("blocked")) for row in blocked_result.iter_rows()), blocked_result.row_count, ">0; all blocked")

    # Formula-safe synthetic export includes intentionally dangerous strings.
    synthetic_export_query = synthetic_model.execute(GridQuery(filters=(GridFilter("part_position", FilterOperator.IN, ("P000007", "P000008")),)))
    synthetic_csv = output / "CWS_Viewer_V8_Formula_Safety.csv"
    synthetic_xlsx = output / "CWS_Viewer_V8_Formula_Safety.xlsx"
    synthetic_csv_evidence = export_grid_csv(synthetic_export_query, synthetic_csv)
    synthetic_xlsx_evidence = export_grid_xlsx(synthetic_export_query, synthetic_xlsx)
    csv_text = synthetic_csv.read_text(encoding="utf-8-sig")
    formula_safe_pass = "'=HYPERLINK" in csv_text and "'+SUM" in csv_text
    gate("V8-FORMULA-SAFE-CSV", formula_safe_pass, formula_safe_pass, True)

    # Layout persistence.
    layout = _build_layout(synthetic_model)
    layout_store = GridLayoutStore(output / "layouts")
    identity = GridLayoutIdentity(
        company_id="CWS",
        user_id="validation-user",
        project_id="global",
        layout_name="Productiecontrole",
    )
    stored = layout_store.save(identity, layout)
    loaded = layout_store.load(identity)
    layout_pass = loaded.layout.to_dict() == layout.to_dict()
    gate("V8-LAYOUT-ATOMIC-ROUNDTRIP", layout_pass, loaded.payload_sha256, stored.payload_sha256)
    layout_copy = output / "CWS_Viewer_V8_Productiecontrole.cwsgrid.json"
    layout_copy.write_bytes(stored.path.read_bytes())
    layout_copy.with_suffix(layout_copy.suffix + ".sha256").write_text(_sha256(layout_copy) + "\n", encoding="ascii")

    # ------------------------------------------------------------------
    # Real project and V7 revision gate
    # ------------------------------------------------------------------
    real_summary: dict[str, Any] | None = None
    lo4_rows: list[dict[str, Any]] = []
    changed_rows: list[dict[str, Any]] = []
    real_blocked_rows: list[dict[str, Any]] = []
    project_path = args.project.expanduser().resolve()
    compare_path = args.compare.expanduser().resolve()
    if project_path.is_file():
        t1 = time.perf_counter()
        opened = ProjectStore().open(project_path, read_only=True)
        project_open_ms = (time.perf_counter() - t1) * 1000.0
        report = _revision_report(compare_path)
        t2 = time.perf_counter()
        real_model = ProjectGridModel(opened.project, revision_report=report)
        grid_build_ms = (time.perf_counter() - t2) * 1000.0
        counts: dict[str, int] = {}
        for row in real_model.rows:
            counts[row.entity_type] = counts.get(row.entity_type, 0) + 1

        lo4 = real_model.execute(
            GridQuery(
                filters=(GridFilter("part_position", FilterOperator.EQ, "LO4"),),
                sorts=(GridSort("entity_id"),),
            )
        )
        changed = real_model.execute(
            GridQuery(
                scope=GridScope.CHANGED,
                groups=(GridGroupSpec("revision_status"), GridGroupSpec("revision_impacts")),
                sorts=(GridSort("revision_status"), GridSort("part_position")),
            )
        )
        blocked = real_model.execute(
            GridQuery(scope=GridScope.BLOCKED, sorts=(GridSort("entity_type"), GridSort("part_position")))
        )
        lo4_rows = _row_values(lo4, 10)
        changed_rows = _row_values(changed, 20)
        real_blocked_rows = _row_values(blocked, 30)
        changed_statuses = sorted({str(row.get("revision_status")) for row in changed.iter_rows()})

        lo4_ids = [row.entity_id for row in lo4.iter_rows()]
        real_model.set_scope_state(selected_entity_ids=lo4_ids)
        selected_lo4 = real_model.execute(GridQuery(scope=GridScope.SELECTED, sorts=(GridSort("entity_id"),)))

        # Professional exports use the same layout/columns as the UI.
        real_layout = _build_layout(real_model)
        real_model.apply_layout(real_layout)
        lo4_csv_evidence = export_grid_csv(selected_lo4, output / "CWS_Viewer_V8_LO4_Selected.csv", columns=real_model.columns)
        lo4_xlsx_evidence = export_grid_xlsx(selected_lo4, output / "CWS_Viewer_V8_LO4_Selected.xlsx", columns=real_model.columns)
        changed_csv_evidence = export_grid_csv(changed, output / "CWS_Viewer_V8_Changed.csv", columns=real_model.columns)
        changed_xlsx_evidence = export_grid_xlsx(changed, output / "CWS_Viewer_V8_Changed.xlsx", columns=real_model.columns)
        blocked_csv_evidence = export_grid_csv(blocked, output / "CWS_Viewer_V8_Blocked.csv", columns=real_model.columns)
        blocked_xlsx_evidence = export_grid_xlsx(blocked, output / "CWS_Viewer_V8_Blocked.xlsx", columns=real_model.columns)

        # Compact complete inventory: only stable, operational fields.
        inventory_headers = [
            "entity_id",
            "entity_type",
            "assembly_mark",
            "part_position",
            "name",
            "profile",
            "material",
            "length_mm",
            "quantity_total",
            "total_mass_kg",
            "classification_status",
            "export_status",
            "revision_status",
            "revision_impacts",
            "blocked",
            "blockers",
            "source_entity_id",
            "geometry_hash",
            "manufacturing_hash",
        ]
        _write_csv(
            output / "VIEWER_V8_REAL_PROJECT_GRID_INVENTORY.csv",
            inventory_headers,
            ([row.get(key, "") for key in inventory_headers] for row in real_model.rows),
        )

        real_summary = {
            "project_path": str(project_path),
            "project_sha256": _sha256(project_path),
            "project_open_ms": project_open_ms,
            "grid_build_ms": grid_build_ms,
            "rows_including_removed_revision": len(real_model.rows),
            "counts": counts,
            "lo4_rows": lo4.row_count,
            "changed_rows": changed.row_count,
            "changed_statuses": changed_statuses,
            "blocked_rows": blocked.row_count,
            "revision_report_available": report is not None,
            "revision_compare_path": str(compare_path) if compare_path.is_file() else "",
            "exports": {
                "lo4_csv": lo4_csv_evidence,
                "lo4_xlsx": lo4_xlsx_evidence,
                "changed_csv": changed_csv_evidence,
                "changed_xlsx": changed_xlsx_evidence,
                "blocked_csv": blocked_csv_evidence,
                "blocked_xlsx": blocked_xlsx_evidence,
            },
        }
        gate("V8-REAL-ASSEMBLY-COUNT", counts.get("assembly") == 353, counts.get("assembly"), 353)
        gate("V8-REAL-PART-COUNT", counts.get("part") == 2432, counts.get("part"), 2432)
        gate("V8-REAL-FASTENER-COUNT", counts.get("fastener") == 723, counts.get("fastener"), 723)
        gate("V8-REAL-WELD-COUNT", counts.get("weld") == 2654, counts.get("weld"), 2654)
        gate("V8-REAL-LO4-COUNT", lo4.row_count == 4, lo4.row_count, 4)
        gate("V8-REAL-LO4-PROFILE", all(row.get("profile") == "STRIP5*120" for row in lo4.iter_rows()), sorted({row.get("profile") for row in lo4.iter_rows()}), ["STRIP5*120"])
        gate("V8-REAL-LO4-MATERIAL", all(row.get("material") == "S235JR" for row in lo4.iter_rows()), sorted({row.get("material") for row in lo4.iter_rows()}), ["S235JR"])
        gate("V8-REAL-REVISION-SCOPE", {"moved", "changed", "removed"}.issubset(set(changed_statuses)), changed_statuses, "contains moved, changed, removed")
        gate("V8-REAL-SELECTED-SCOPE", selected_lo4.row_count == 4, selected_lo4.row_count, 4)
        gate("V8-REAL-BLOCKED-SCOPE", blocked.row_count > 0 and all(bool(row.get("blocked")) for row in blocked.iter_rows()), blocked.row_count, ">0; all blocked")
    else:
        gate(
            "V8-REAL-PROJECT-AVAILABLE",
            bool(args.allow_missing_project),
            str(project_path),
            "present or --allow-missing-project",
            "Private reference missing; no real-project success is claimed",
        )
        if not args.allow_missing_project:
            raise FileNotFoundError(f"V8 referentieproject ontbreekt: {project_path}")

    if not lo4_rows:
        lo4_rows = _row_values(synthetic_model.execute(GridQuery(filters=(GridFilter("profile", FilterOperator.EQ, "STRIP5*120"),))), 6)
    if not changed_rows:
        changed_rows = [{"revision_status": "not_run", "part_position": "", "profile": "", "material": "", "revision_impacts": "private reference missing", "production_reuse": False}]
    if not real_blocked_rows:
        real_blocked_rows = _row_values(blocked_result, 12)

    evidence_image = _render_evidence(
        output / "CWS_Viewer_V8_Professional_Property_Grid_Evidence.png",
        synthetic=synthetic_summary,
        real=real_summary,
        lo4_rows=lo4_rows,
        changed_rows=changed_rows,
        blocked_rows=real_blocked_rows,
    )

    acceptance_csv = output / "VIEWER_V8_ACCEPTANCE_MATRIX.csv"
    _write_csv(
        acceptance_csv,
        ("code", "passed", "actual", "expected", "note"),
        (
            (item["code"], "PASS" if item["passed"] else "FAIL", json.dumps(item["actual"], ensure_ascii=False), json.dumps(item["expected"], ensure_ascii=False), item["note"])
            for item in gates
        ),
    )

    generated_files = sorted(
        path for path in output.rglob("*")
        if path.is_file() and path.name != "VIEWER_V8_VALIDATION_RESULTS.json"
    )
    artifacts = [
        {
            "path": str(path.relative_to(output)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in generated_files
    ]
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    result = {
        "schema": "cws-viewer-v8-validation-1.0",
        "viewer_package_version": VIEWER_PACKAGE_VERSION,
        "viewer_api_version": VIEWER_API_VERSION,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "status": "passed" if all(item["passed"] for item in gates) else "failed",
        "elapsed_ms": elapsed_ms,
        "synthetic": synthetic_summary,
        "real_project": real_summary,
        "formula_safe_exports": {
            "csv": synthetic_csv_evidence,
            "xlsx": synthetic_xlsx_evidence,
        },
        "layout": {
            "path": str(layout_copy),
            "payload_sha256": loaded.payload_sha256,
            "visible_columns": [column.key for column in loaded.layout.columns if column.visible],
            "group_keys": [group.key for group in loaded.layout.groups],
            "sort_keys": [sort.key for sort in loaded.layout.sorts],
        },
        "evidence_image": str(evidence_image),
        "gates": gates,
        "gate_counts": {
            "total": len(gates),
            "passed": sum(1 for item in gates if item["passed"]),
            "failed": sum(1 for item in gates if not item["passed"]),
        },
        "artifacts": artifacts,
        "windows_qt_gate": "not_run_in_local_linux_runtime",
        "claims": {
            "qt_dynamic_screenshot": False,
            "real_project_gate": real_summary is not None,
            "production_geometry_modified": False,
            "canonical_edit_service_used": False,
        },
    }
    result_path = _write_json(output / "VIEWER_V8_VALIDATION_RESULTS.json", result)
    print(json.dumps({
        "status": result["status"],
        "results": str(result_path),
        "gates": result["gate_counts"],
        "synthetic": synthetic_summary,
        "real_project": None if real_summary is None else {
            "counts": real_summary["counts"],
            "lo4_rows": real_summary["lo4_rows"],
            "changed_rows": real_summary["changed_rows"],
            "blocked_rows": real_summary["blocked_rows"],
        },
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
