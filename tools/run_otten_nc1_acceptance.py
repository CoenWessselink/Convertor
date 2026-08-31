from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont

from pdf_support import canonical_from_nc1, canonical_to_nc1
from cws_convertor.optimization.plate_nesting.canonical import (
    PlateGeometryRef,
    PlateNestDemand,
    PlateStock,
    Point2D,
    solve_canonical_plate_nesting,
    validate_canonical_plate_nesting,
)
from cws_convertor.optimization.profile_nesting.models import ProfileNestingInputSnapshot
from cws_convertor.optimization.profile_nesting.straight_solver import solve_straight_cut
from cws_convertor.optimization.profile_nesting.units import LengthKernel
from cws_convertor.optimization.profile_nesting.validator import validate_straight_plan


BLUE = (17, 83, 149)
INK = (22, 36, 50)
PALETTE = ((54, 132, 205), (71, 160, 104), (230, 154, 50), (166, 105, 194), (51, 167, 167))


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    path = Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path), size=size) if path.is_file() else ImageFont.load_default()


def _digest(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str).encode("utf-8")
    return sha256(data).hexdigest()


def _save(image: Image.Image, png: Path, pdf: Path) -> None:
    png.parent.mkdir(parents=True, exist_ok=True)
    pdf.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(png, "PNG", optimize=True)
    image.convert("RGB").save(pdf, "PDF", resolution=150.0)


def _title(draw: ImageDraw.ImageDraw, title: str, subtitle: str, width: int) -> None:
    draw.rectangle((0, 0, width, 92), fill=(248, 251, 255), outline=BLUE, width=3)
    draw.rounded_rectangle((28, 20, 112, 70), radius=7, fill=BLUE)
    draw.text((42, 28), "CWS", fill="white", font=_font(26, True))
    draw.text((132, 18), title, fill=INK, font=_font(28, True))
    draw.text((132, 54), subtitle, fill=(68, 88, 108), font=_font(16))


def _dimension(draw: ImageDraw.ImageDraw, start: tuple[float, float], end: tuple[float, float], label: str, *, vertical: bool = False) -> None:
    draw.line((*start, *end), fill=BLUE, width=2)
    if vertical:
        draw.line((start[0] - 7, start[1] + 9, *start), fill=BLUE, width=2)
        draw.line((start[0] + 7, start[1] + 9, *start), fill=BLUE, width=2)
        draw.line((end[0] - 7, end[1] - 9, *end), fill=BLUE, width=2)
        draw.line((end[0] + 7, end[1] - 9, *end), fill=BLUE, width=2)
        draw.text((start[0] - 66, (start[1] + end[1]) / 2 - 10), label, fill=BLUE, font=_font(15, True))
    else:
        draw.line((start[0] + 9, start[1] - 6, *start), fill=BLUE, width=2)
        draw.line((start[0] + 9, start[1] + 6, *start), fill=BLUE, width=2)
        draw.line((end[0] - 9, end[1] - 6, *end), fill=BLUE, width=2)
        draw.line((end[0] - 9, end[1] + 6, *end), fill=BLUE, width=2)
        box = draw.textbbox((0, 0), label, font=_font(15, True))
        draw.text(((start[0] + end[0] - box[2]) / 2, start[1] - 28), label, fill=BLUE, font=_font(15, True))


def _signature(part: Any) -> dict[str, Any]:
    return {
        "part": part.part_id,
        "header": {name: getattr(part.header, name) for name in ("material", "quantity", "profile", "length", "dim1", "dim2", "dim3", "radius")},
        "contours": [
            (contour.face, [(round(point.x, 6), round(point.q, 6), tuple(round(float(value), 6) for value in point.weld)) for point in contour.points])
            for contour in part.contours
        ],
        "holes": [(hole.face, round(hole.x, 6), round(hole.q, 6), round(hole.diameter, 6)) for hole in part.holes],
    }


def _roundtrip(parts: Iterable[Any], evidence: Path) -> list[dict[str, Any]]:
    directory = evidence / "roundtrip"
    directory.mkdir(parents=True, exist_ok=True)
    results = []
    for part in parts:
        output = canonical_to_nc1(part, directory / part.source_file)
        reopened = canonical_from_nc1(output)
        before, after = _signature(part), _signature(reopened)
        results.append({
            "part_id": part.part_id,
            "passed": before == after,
            "source_signature_sha256": _digest(before),
            "result_signature_sha256": _digest(after),
            "output": str(output),
            "output_sha256": sha256(output.read_bytes()).hexdigest(),
        })
    return results


def _profile_snapshot(parts: list[Any], kernel: LengthKernel) -> ProfileNestingInputSnapshot:
    profile, material = parts[0].header.profile, parts[0].header.material
    section_hash = _digest({"profile": profile})
    lines, instances = [], []
    total = 0.0
    for part in parts:
        line_id = f"otten:{part.part_id}"
        lines.append({
            "demand_line_id": line_id, "group_key": f"{profile}|{material}",
            "part_id": part.part_id, "part_position": part.part_id,
            "manufacturing_hash": part.source_sha256, "assembly_marks": [],
            "profile_id": profile, "profile_name": profile, "section_hash": section_hash,
            "profile_type": "box", "material": material, "material_grade": material,
            "nominal_length_mm": part.header.length,
            "nominal_length_units": kernel.mm_to_units(part.header.length),
            "quantity": part.header.quantity,
            "start_cut": {"status": "exact", "primary_angle_deg": 0.0, "secondary_angle_deg": 0.0},
            "end_cut": {"status": "exact", "primary_angle_deg": 0.0, "secondary_angle_deg": 0.0},
            "candidate_machine_ids": ["CWS-SAW-01"], "eligibility_status": "eligible",
        })
        total += float(part.header.length) * int(part.header.quantity)
        for ordinal in range(1, int(part.header.quantity) + 1):
            instances.append({
                "instance_id": f"{part.part_id}:{ordinal:03d}", "demand_line_id": line_id,
                "part_id": part.part_id, "part_position": part.part_id,
                "manufacturing_hash": part.source_sha256, "quantity_ordinal": ordinal,
            })
    required_stock_length = max(
        float(part.header.length) + 23.0
        for part in parts
    )
    trade_lengths = (6000.0, 7500.0, 9000.0, 12000.0, 15000.0, 18000.0)
    stock_length = next(
        (length for length in trade_lengths if length >= required_stock_length),
        math.ceil(required_stock_length / 1000.0) * 1000.0,
    )
    stock = {"candidates": [{
        "candidate_id": f"stock:{profile}", "source_type": "purchase", "source_id": f"PURCHASE-{profile}",
        "physical": False, "profile_id": profile, "section_hash": section_hash,
        "material": material, "material_grade": material, "length_mm": stock_length,
        "length_units": kernel.mm_to_units(stock_length),
        "available_quantity": max(1, math.ceil(total / (stock_length - 25.0)) + 1),
        "minimum_reusable_mm": 500.0, "unit_price": 1.0,
    }]}
    machine = {"profiles": [{
        "profile_id": "CWS-SAW-PRODUCTION", "machine_id": "CWS-SAW-01", "enabled": True,
        "validation_status": "released", "feed_direction": "left_to_right", "kerf_mm": 3.0,
        "head_trim_mm": 10.0, "tail_trim_mm": 10.0, "minimum_end_remnant_mm": 500.0,
        "max_part_length_mm": max(12000.0, stock_length),
        "max_stock_length_mm": max(12000.0, stock_length),
        "min_part_length_mm": 20.0, "machine_tolerance_mm": 0.1,
    }]}
    payload = {"lines": lines, "instances": instances, "stock": stock, "machine": machine}
    return ProfileNestingInputSnapshot(
        snapshot_id=f"otten-{_digest(payload)[:12]}", project_id="OTTEN-26.01.07",
        project_revision_hash=_digest([part.source_sha256 for part in parts]),
        demand_snapshot_hash=_digest(lines), demand_lines=lines, piece_instances=instances,
        machine_snapshot_hash=_digest(machine), stock_snapshot_hash=_digest(stock),
        machine_snapshot=machine, stock_snapshot=stock,
        units={"unit": "mm", "resolution_mm": 0.001}, tolerances={"length_mm": 0.1},
        solver_configuration={"backend": "greedy"}, created_by="otten-acceptance",
        snapshot_hash=_digest(payload),
    )


def _profile_nesting(parts: list[Any], png: Path, pdf: Path) -> dict[str, Any]:
    kernel = LengthKernel()
    grouped: dict[tuple[str, str], list[Any]] = {}
    for part in parts:
        grouped.setdefault((part.header.profile, part.header.material), []).append(part)
    solved, runs = [], []
    for (profile, material), group in sorted(grouped.items()):
        snapshot = _profile_snapshot(group, kernel)
        plan, evidence = solve_straight_cut(snapshot, backend="greedy", scenario_family="waste")
        if plan is None:
            raise RuntimeError(f"Geen profielplan voor {profile}: {asdict(evidence)}")
        validation = validate_straight_plan(snapshot, plan)
        if not bool(getattr(validation, "valid", False)):
            raise RuntimeError(f"Ongeldig profielplan voor {profile}: {asdict(validation)}")
        solved.append((profile, plan))
        runs.append({
            "profile": profile, "material": material, "bar_count": len(plan.bars),
            "piece_count": sum(len(bar.placements) for bar in plan.bars),
            "plan_hash": getattr(plan, "plan_hash", ""),
            "evidence": asdict(evidence), "validation": asdict(validation),
        })
    height = 190 + sum(len(plan.bars) * 100 + 70 for _profile, plan in solved)
    image = Image.new("RGB", (1800, height), "white")
    draw = ImageDraw.Draw(image)
    _title(draw, "PROFIELNESTING EN OPTIMALISATIE", "Echte NC1-vraag | onafhankelijke validatie", 1800)
    y = 125
    for profile, plan in solved:
        draw.text((42, y), f"{profile} | {len(plan.bars)} handelslengte(s)", fill=INK, font=_font(22, True))
        y += 40
        for bar_index, bar in enumerate(plan.bars, 1):
            left, right, top, bottom = 160, 1650, y, y + 54
            draw.rounded_rectangle((left, top, right, bottom), radius=5, fill=(237, 242, 247), outline=INK, width=2)
            stock_mm = kernel.units_to_mm(bar.stock_length_units)
            draw.text((42, top + 14), f"B{bar_index:02d}", fill=INK, font=_font(16, True))
            for index, placement in enumerate(bar.placements):
                x0 = left + kernel.units_to_mm(placement.start_units) / stock_mm * (right - left)
                x1 = left + kernel.units_to_mm(placement.end_units) / stock_mm * (right - left)
                draw.rectangle((x0, top + 2, x1, bottom - 2), fill=PALETTE[index % len(PALETTE)], outline=INK, width=1)
                if x1 - x0 > 70:
                    draw.text((x0 + 6, top + 15), placement.part_position or placement.part_id, fill="white", font=_font(14, True))
            draw.text((right + 12, top + 14), f"{stock_mm:,.0f} mm", fill=INK, font=_font(15))
            y += 78
        y += 30
    _save(image, png, pdf)
    return {"passed": True, "runs": runs, "image": str(png), "pdf": str(pdf)}


def _plate_geometry(part: Any) -> PlateGeometryRef:
    contour = next((item for item in part.contours if item.face == "v"), part.contours[0])
    points = [(float(point.x), float(point.q)) for point in contour.points]
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    inner = []
    for hole in part.holes:
        if hole.face == contour.face:
            radius = float(hole.diameter) * 0.5
            inner.append(tuple((hole.x + math.cos(i * math.tau / 24) * radius, hole.q + math.sin(i * math.tau / 24) * radius) for i in range(24)))
    return PlateGeometryRef(f"nc1:{part.source_sha256}", tuple((x, y) for x, y in points), tuple(inner))


def _rotated_plate_point(x: float, y: float, width: float, height: float, rotation_deg: int) -> tuple[float, float]:
    rotation = int(rotation_deg) % 360
    if rotation == 90:
        return height - y, x
    if rotation == 180:
        return width - x, height - y
    if rotation == 270:
        return y, width - x
    return x, y


def _plate_nesting(parts: list[Any], png: Path, pdf: Path) -> dict[str, Any]:
    part_by_id = {part.part_id: part for part in parts}
    grouped: dict[tuple[str, float], list[Any]] = {}
    for part in parts:
        thickness = float(part.product.plate_thickness_mm or part.header.dim2)
        grouped.setdefault((part.header.material, thickness), []).append(part)
    solved, runs = [], []
    for (material, thickness), group in sorted(grouped.items()):
        demands = tuple(PlateNestDemand(
            f"otten:{part.part_id}", part.part_id, _plate_geometry(part), material, material, thickness,
            int(part.header.quantity), (0, 90, 180, 270), False, None, part.source_sha256,
        ) for part in group)
        stock = (PlateStock(f"sheet:{material}:{thickness:g}", 3000.0, 1500.0, material, material, thickness, 4),)
        plan = solve_canonical_plate_nesting(demands, stock, kerf_mm=3.0, edge_margin_mm=10.0, spacing_mm=2.0, run_id=f"otten-{material}-{thickness:g}")
        validation = validate_canonical_plate_nesting(plan, demands, stock)
        if not plan.complete or not validation.passed:
            raise RuntimeError(f"Ongeldig plaatplan {material}/{thickness:g}: {asdict(validation)}")
        solved.append((material, thickness, plan))
        runs.append({
            "material": material, "thickness_mm": thickness, "layout_count": len(plan.layouts),
            "placed_count": plan.placed_count, "utilization": plan.utilization,
            "plan_sha256": plan.plan_sha256, "validation": asdict(validation),
        })
    height = 190 + sum(len(plan.layouts) * 500 + 70 for _m, _t, plan in solved)
    image = Image.new("RGB", (1800, height), "white")
    draw = ImageDraw.Draw(image)
    _title(draw, "PLAATNESTING EN OPTIMALISATIE", "Otten 26.01.07 | contouren en gaten | kerf 3 mm | spacing 2 mm", 1800)
    y = 125
    rendered_holes = 0
    for material, thickness, plan in solved:
        draw.text((42, y), f"{material} | t={thickness:g} mm | benutting {plan.utilization * 100:.1f}% | {plan.placed_count} delen", fill=INK, font=_font(22, True))
        y += 42
        for layout in plan.layouts:
            left, top, width, sheet_height = 130, y, 1500, 430
            draw.rectangle((left, top, left + width, top + sheet_height), fill=(242, 246, 249), outline=INK, width=3)
            sx, sy = width / layout.width_mm, sheet_height / layout.height_mm
            for placement in layout.placements:
                part = part_by_id[placement.part_id]
                contour = next((item for item in part.contours if item.face == "v"), part.contours[0])
                raw_points = [(float(point.x), float(point.q)) for point in contour.points]
                min_x, max_x = min(item[0] for item in raw_points), max(item[0] for item in raw_points)
                min_y, max_y = min(item[1] for item in raw_points), max(item[1] for item in raw_points)
                part_width, part_height = max_x - min_x, max_y - min_y
                def placed_point(x: float, q: float) -> tuple[float, float]:
                    rx, ry = _rotated_plate_point(x - min_x, q - min_y, part_width, part_height, placement.rotation_deg)
                    return left + (placement.x_mm + rx) * sx, top + (placement.y_mm + ry) * sy
                polygon = [placed_point(x, q) for x, q in raw_points]
                draw.polygon(polygon, fill=(225, 239, 252), outline=BLUE)
                draw.line(polygon, fill=BLUE, width=2, joint="curve")
                for hole in part.holes:
                    if hole.face != contour.face:
                        continue
                    cx, cy = placed_point(float(hole.x), float(hole.q))
                    radius = max(1.5, float(hole.diameter) * min(sx, sy) * 0.5)
                    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill="white", outline=BLUE, width=1)
                    rendered_holes += 1
                x0, y0 = left + placement.x_mm * sx, top + placement.y_mm * sy
                if placement.width_mm * sx > 55 and placement.height_mm * sy > 24:
                    draw.text((x0 + 5, y0 + 4), placement.part_id, fill=BLUE, font=_font(13, True))
            draw.text((left + width + 16, top + 8), layout.stock_instance_id, fill=INK, font=_font(14))
            y += sheet_height + 45
        y += 30
    _save(image, png, pdf)
    return {"passed": True, "runs": runs, "rendered_hole_count": rendered_holes, "image": str(png), "pdf": str(pdf)}


def _drawing(part: Any, png: Path, pdf: Path) -> dict[str, Any]:
    image = Image.new("RGB", (1800, 1200), "white")
    draw = ImageDraw.Draw(image)
    _title(draw, f"WERKPLAATSTEKENING {part.part_id}", f"{part.header.profile} | {part.header.material} | aantal {part.header.quantity}", 1800)
    contour = next((item for item in part.contours if item.face == "v"), part.contours[0])
    points = [(float(point.x), float(point.q), point) for point in contour.points]
    min_x, max_x = min(p[0] for p in points), max(p[0] for p in points)
    min_y, max_y = min(p[1] for p in points), max(p[1] for p in points)
    span_x, span_y = max(1.0, max_x - min_x), max(1.0, max_y - min_y)
    left, right, top, bottom = 250, 1580, 250, 760
    scale = min((right - left) / span_x, (bottom - top) / span_y)
    center_y = (top + bottom) * 0.5
    def screen(x: float, y: float) -> tuple[float, float]:
        return left + (x - min_x) * scale, center_y - (y - (min_y + max_y) * 0.5) * scale
    polygon = [screen(x, y) for x, y, _point in points]
    draw.polygon(polygon, fill=(239, 246, 252), outline=INK)
    draw.line(polygon, fill=INK, width=3, joint="curve")
    holes = [hole for hole in part.holes if hole.face == contour.face]
    for hole in holes:
        cx, cy = screen(hole.x, hole.q)
        radius = max(5.0, hole.diameter * scale * 0.5)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill="white", outline=INK, width=3)
        draw.line((cx - radius - 8, cy, cx + radius + 8, cy), fill=INK, width=1)
        draw.line((cx, cy - radius - 8, cx, cy + radius + 8), fill=INK, width=1)
    model_left, model_right = screen(min_x, min_y)[0], screen(max_x, min_y)[0]
    dim_y = bottom + 80
    draw.line((model_left, center_y, model_left, dim_y), fill=BLUE, width=1)
    draw.line((model_right, center_y, model_right, dim_y), fill=BLUE, width=1)
    _dimension(draw, (model_left, dim_y), (model_right, dim_y), f"{span_x:g} mm")
    model_top, model_bottom = screen(min_x, max_y)[1], screen(min_x, min_y)[1]
    dim_x = left - 90
    draw.line((dim_x, model_top, left, model_top), fill=BLUE, width=1)
    draw.line((dim_x, model_bottom, left, model_bottom), fill=BLUE, width=1)
    _dimension(draw, (dim_x, model_top), (dim_x, model_bottom), f"{span_y:g} mm", vertical=True)
    for level, x in enumerate(sorted({round(float(hole.x), 6) for hole in holes})):
        hx = screen(x, min_y)[0]
        chain_y = bottom + 130 + level * 24
        draw.line((hx, center_y, hx, chain_y), fill=BLUE, width=1)
        _dimension(draw, (model_left, chain_y), (hx, chain_y), f"{x - min_x:g}")
    diameters: dict[float, int] = {}
    for hole in holes:
        diameters[round(float(hole.diameter), 6)] = diameters.get(round(float(hole.diameter), 6), 0) + 1
    if diameters:
        callout = " | ".join(f"{count}x \N{DIAMETER SIGN}{diameter:g}" for diameter, count in sorted(diameters.items()))
        draw.text((left, top - 55), callout, fill=BLUE, font=_font(20, True))
    angles = []
    for x, y, point in points:
        angle = next((abs(float(value)) for value in point.weld if abs(float(value)) > 0.05), None)
        if angle is None:
            continue
        angles.append(angle)
        cx, cy = screen(x, y)
        radius, radians = 45, math.radians(angle)
        draw.line((cx, cy, cx - radius, cy), fill=BLUE, width=2)
        draw.line((cx, cy, cx - math.cos(radians) * radius, cy - math.sin(radians) * radius), fill=BLUE, width=2)
        draw.arc((cx - radius, cy - radius, cx + radius, cy + radius), 180, 180 + angle, fill=BLUE, width=2)
        draw.text((cx - 92, cy - 75), f"{angle:g}\N{DEGREE SIGN}", fill=BLUE, font=_font(18, True))
    draw.rectangle((35, 1010, 1765, 1160), outline=BLUE, width=2)
    fields = (f"Project: 26.01.07 Otten", f"Onderdeel: {part.part_id}", f"Profiel: {part.header.profile}", f"Materiaal: {part.header.material}", f"Aantal: {part.header.quantity}", f"Bron: {part.source_file} / {part.source_sha256[:16]}")
    for index, text in enumerate(fields):
        draw.text((55 + index % 3 * 560, 1030 + index // 3 * 62), text, fill=INK, font=_font(17, index in {1, 2}))
    _save(image, png, pdf)
    return {"part_id": part.part_id, "horizontal": True, "holes_drawn": len(holes), "angles_drawn": angles, "image": str(png), "pdf": str(pdf)}


def run(nc_dir: Path, output_root: Path) -> dict[str, Any]:
    sources = sorted(nc_dir.glob("*.nc1"), key=lambda path: path.name.casefold())
    if not sources:
        raise FileNotFoundError(f"Geen NC1-bestanden gevonden in {nc_dir}")
    parts = [canonical_from_nc1(source) for source in sources]
    evidence, images, pdfs = output_root / "evidence" / "otten_nc1", output_root / "images", output_root / "pdf"
    roundtrip = _roundtrip(parts, evidence)
    profiles = [part for part in parts if part.header.profile_type.upper() != "B"]
    plates = [part for part in parts if part.header.profile_type.upper() == "B"]
    if not profiles or not plates:
        raise RuntimeError("Acceptatieset vereist ten minste een profiel en een plaat")
    profile_result = _profile_nesting(profiles, images / "CWS_Otten_profile_nesting.png", pdfs / "CWS_Otten_profile_nesting_report.pdf")
    plate_result = _plate_nesting(plates, images / "CWS_Otten_plate_nesting.png", pdfs / "CWS_Otten_plate_nesting_report.pdf")
    drawing_parts = sorted(
        (part for part in plates if part.holes),
        key=lambda part: (-len(part.holes), part.part_id),
    )[:2]
    if len(drawing_parts) < 2:
        raise RuntimeError("Acceptatieset vereist ten minste twee platen met gaten")
    drawings = [
        _drawing(
            part,
            images / f"CWS_Real_{part.part_id}_workshop_drawing.png",
            pdfs / f"CWS_Real_{part.part_id}_workshop_drawing.pdf",
        )
        for part in drawing_parts
    ]
    report = {
        "schema": "cws-real-nc1-acceptance-1.0", "source_directory": str(nc_dir), "source_count": len(parts),
        "source_sha256": {part.source_file: part.source_sha256 for part in parts},
        "native_parse": {
            "passed": all(bool(part.recognition.get("production_export_allowed")) and float(part.recognition.get("confidence", 0.0)) >= 1.0 for part in parts),
            "dimension_coverage_percent": {part.part_id: part.properties["dimension_graph"]["validation"]["coverage_percent"] for part in parts},
        },
        "roundtrip": {"passed": all(item["passed"] for item in roundtrip), "parts": roundtrip},
        "profile_nesting": profile_result, "plate_nesting": plate_result, "drawings": drawings,
    }
    report["passed"] = bool(report["native_parse"]["passed"] and report["roundtrip"]["passed"] and profile_result["passed"] and plate_result["passed"] and all(item["horizontal"] and item["holes_drawn"] for item in drawings))
    report["report_sha256"] = _digest(report)
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / "CWS_Otten_NC1_acceptance.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproduceerbare Otten NC1 nesting-, roundtrip- en tekeningacceptatie")
    parser.add_argument("--nc-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    report = run(args.nc_dir.resolve(), args.output_root.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
