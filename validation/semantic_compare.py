"""Semantische vergelijking voor DSTV/NC1-productiedata."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import math

import converter as core
from conversion import build_shape


def _shape_metrics(shape) -> dict[str, Any]:
    box = shape.BoundingBox()
    return {
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_sorted_mm": sorted(
            [float(box.xlen), float(box.ylen), float(box.zlen)],
            reverse=True,
        ),
        "solids": len(shape.Solids()),
    }


def _quantize(value: float, tolerance_mm: float) -> int:
    return int(round(float(value) / tolerance_mm))


def _normalized_contour(contour: core.Contour, tolerance_mm: float) -> tuple:
    points = [
        (
            _quantize(point.x, tolerance_mm),
            _quantize(point.q, tolerance_mm),
            point.datum,
            point.notch,
            _quantize(point.radius, tolerance_mm),
        )
        for point in contour.geometry_points
    ]
    if len(points) > 1 and points[0][:2] == points[-1][:2]:
        points = points[:-1]
    if not points:
        return ()
    candidates = []
    for sequence in (points, list(reversed(points))):
        for index in range(len(sequence)):
            candidates.append(tuple(sequence[index:] + sequence[:index]))
    return min(candidates)


def nc1_summary(path: str | Path, *, tolerance_mm: float = 0.01) -> dict[str, Any]:
    source = Path(path)
    part = core.parse_nc1(source)
    header = part.header
    shape = build_shape(part).val()
    contours = sorted(
        (contour.kind, contour.face, _normalized_contour(contour, tolerance_mm))
        for contour in part.contours
    )
    holes = sorted(
        (
            hole.face,
            _quantize(hole.x, tolerance_mm),
            _quantize(hole.q, tolerance_mm),
            _quantize(hole.diameter, tolerance_mm),
            hole.operation,
            _quantize(hole.depth, tolerance_mm),
        )
        for hole in part.holes
    )
    return {
        "file": source.name,
        "header": {
            "order_number": header.order_number,
            "drawing_number": header.drawing_number,
            "part_number": header.part_number,
            "position_number": header.position_number,
            "material": header.material,
            "quantity": header.quantity,
            "profile": header.profile,
            "profile_type": header.profile_type,
            "length_mm": float(header.length),
            "saw_length_mm": float(header.saw_length),
            "dim1_mm": float(header.dim1),
            "dim2_mm": float(header.dim2),
            "dim3_mm": float(header.dim3),
            "dim4_mm": float(header.dim4),
            "radius_mm": float(header.radius),
            "weight_kg_m": float(header.weight),
            "paint_area_factor": float(header.paint_area),
        },
        "holes": holes,
        "hole_count": len(holes),
        "contours": contours,
        "contour_count": len(contours),
        "contour_point_count": sum(len(item[2]) for item in contours),
        "unsupported_blocks": sorted(set(part.unsupported_blocks)),
        "warnings": list(part.warnings),
        "metrics": _shape_metrics(shape),
    }


def _percent_delta(reference: float, candidate: float) -> float:
    return (candidate - reference) / reference * 100.0 if abs(reference) > 1e-12 else 0.0


def compare_nc1(
    source: str | Path,
    candidate: str | Path,
    *,
    tolerance_mm: float = 0.01,
) -> dict[str, Any]:
    first = nc1_summary(source, tolerance_mm=tolerance_mm)
    second = nc1_summary(candidate, tolerance_mm=tolerance_mm)
    h1, h2 = first["header"], second["header"]
    dimension_fields = [
        "length_mm",
        "saw_length_mm",
        "dim1_mm",
        "dim2_mm",
        "dim3_mm",
        "dim4_mm",
        "radius_mm",
    ]
    dimension_deltas = {
        field: float(h2[field]) - float(h1[field])
        for field in dimension_fields
    }
    metadata_fields = [
        "order_number",
        "drawing_number",
        "part_number",
        "position_number",
        "material",
        "quantity",
        "profile",
        "profile_type",
    ]
    metadata_equal = {field: h1[field] == h2[field] for field in metadata_fields}
    metrics1, metrics2 = first["metrics"], second["metrics"]
    bbox_delta = [
        float(candidate_value) - float(reference_value)
        for reference_value, candidate_value in zip(
            metrics1["bbox_sorted_mm"], metrics2["bbox_sorted_mm"]
        )
    ]
    result = {
        "source": first,
        "candidate": second,
        "byte_identical": Path(source).read_bytes() == Path(candidate).read_bytes(),
        "holes_equal": first["holes"] == second["holes"],
        "contours_equal": first["contours"] == second["contours"],
        "metadata_equal": metadata_equal,
        "all_metadata_equal": all(metadata_equal.values()),
        "dimension_delta_mm": dimension_deltas,
        "max_dimension_delta_mm": max(abs(value) for value in dimension_deltas.values()),
        "volume_delta_percent": _percent_delta(
            metrics1["volume_mm3"], metrics2["volume_mm3"]
        ),
        "area_delta_percent": _percent_delta(
            metrics1["area_mm2"], metrics2["area_mm2"]
        ),
        "bbox_delta_mm": bbox_delta,
        "max_bbox_delta_mm": max(abs(value) for value in bbox_delta),
    }
    result["passed"] = bool(
        result["holes_equal"]
        and result["contours_equal"]
        and result["all_metadata_equal"]
        and result["max_dimension_delta_mm"] <= tolerance_mm + 1e-9
        and abs(result["volume_delta_percent"]) <= 0.001
        and result["max_bbox_delta_mm"] <= tolerance_mm + 1e-9
    )
    return result
