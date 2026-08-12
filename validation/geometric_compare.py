"""Geometrische en featuregerichte STEP-vergelijking."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cadquery as cq

import converter as core
import conversion
from profile_database import ProfileDatabase


def _percent_delta(reference: float, candidate: float) -> float:
    return (candidate - reference) / reference * 100.0 if abs(reference) > 1e-12 else 0.0


def shape_metrics(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    shape = cq.importers.importStep(str(source)).val()
    box = shape.BoundingBox()
    return {
        "file": source.name,
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_sorted_mm": sorted(
            [float(box.xlen), float(box.ylen), float(box.zlen)],
            reverse=True,
        ),
        "solids": len(shape.Solids()),
    }


def _round_holes(holes) -> list[tuple]:
    return sorted(tuple(round(float(value), 3) if isinstance(value, (int, float)) else value for value in hole) for hole in holes)




def _holes_equal(first: list[tuple], second: list[tuple], tolerance_mm: float = 0.011) -> bool:
    if len(first) != len(second):
        return False
    for left, right in zip(sorted(first), sorted(second)):
        if len(left) != len(right):
            return False
        for left_value, right_value in zip(left, right):
            if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
                if abs(float(left_value) - float(right_value)) > tolerance_mm:
                    return False
            elif left_value != right_value:
                return False
    return True

def step_feature_summary(
    path: str | Path,
    *,
    profile_database: ProfileDatabase | None = None,
) -> dict[str, Any]:
    source = Path(path)
    database = profile_database or ProfileDatabase(writable_copy=False)
    try:
        plate = core.analyze_step_plate(source)
        return {
            "kind": "plate",
            "part_number": plate.part_number,
            "quantity": plate.quantity,
            "profile": f"PL{core._fmt_number(plate.thickness)}*{core._fmt_number(plate.width)}",
            "profile_type": "B",
            "length_mm": float(plate.length),
            "width_mm": float(plate.width),
            "thickness_mm": float(plate.thickness),
            "dimensions_mm": [float(plate.length), float(plate.width), float(plate.thickness)],
            "holes": _round_holes(plate.holes),
            "hole_count": len(plate.holes),
            "contour_point_count": len(plate.contour),
            "recognition_confidence": 1.0,
            "recognition_method": "analytic plate",
        }
    except Exception as plate_error:
        profile = conversion.analyze_step_profile(
            source,
            profile_database=database,
            tolerance_mm=1.0,
        )
        definition = profile.profile
        return {
            "kind": "profile",
            "part_number": profile.part_number,
            "quantity": profile.quantity,
            "profile": definition.designation,
            "profile_type": definition.profile_type,
            "length_mm": float(profile.frame.length),
            "dimensions_mm": [
                float(profile.frame.length),
                float(definition.dim1),
                float(definition.dim2),
                float(definition.dim3),
                float(definition.dim4),
                float(definition.radius),
            ],
            "dim1_mm": float(definition.dim1),
            "dim2_mm": float(definition.dim2),
            "dim3_mm": float(definition.dim3),
            "dim4_mm": float(definition.dim4),
            "radius_mm": float(definition.radius),
            "holes": _round_holes(profile.holes),
            "hole_count": len(profile.holes),
            "contour_point_count": sum(len(points) for points in profile.contours.values()),
            "recognition_confidence": float(profile.match.confidence),
            "recognition_method": profile.match.matched_by,
            "plate_error": str(plate_error),
            "warnings": list(profile.warnings),
        }


def compare_step(
    source: str | Path,
    candidate: str | Path,
    *,
    profile_database: ProfileDatabase | None = None,
) -> dict[str, Any]:
    database = profile_database or ProfileDatabase(writable_copy=False)
    first_metrics = shape_metrics(source)
    second_metrics = shape_metrics(candidate)
    first_features = step_feature_summary(source, profile_database=database)
    second_features = step_feature_summary(candidate, profile_database=database)
    bbox_delta = [
        float(candidate_value) - float(reference_value)
        for reference_value, candidate_value in zip(
            first_metrics["bbox_sorted_mm"], second_metrics["bbox_sorted_mm"]
        )
    ]
    first_dimensions = first_features["dimensions_mm"]
    second_dimensions = second_features["dimensions_mm"]
    dimension_delta = [
        float(candidate_value) - float(reference_value)
        for reference_value, candidate_value in zip(first_dimensions, second_dimensions)
    ]
    result = {
        "source_metrics": first_metrics,
        "candidate_metrics": second_metrics,
        "source_features": first_features,
        "candidate_features": second_features,
        "byte_identical": Path(source).read_bytes() == Path(candidate).read_bytes(),
        "volume_delta_percent": _percent_delta(
            first_metrics["volume_mm3"], second_metrics["volume_mm3"]
        ),
        "area_delta_percent": _percent_delta(
            first_metrics["area_mm2"], second_metrics["area_mm2"]
        ),
        "bbox_delta_mm": bbox_delta,
        "max_raw_bbox_delta_mm": max(abs(value) for value in bbox_delta),
        "aligned_dimension_delta_mm": dimension_delta,
        "max_aligned_dimension_delta_mm": max(abs(value) for value in dimension_delta),
        "profile_equal": first_features["profile"] == second_features["profile"],
        "profile_type_equal": first_features["profile_type"] == second_features["profile_type"],
        "holes_equal": _holes_equal(first_features["holes"], second_features["holes"]),
        "contour_compact": second_features["contour_point_count"] <= max(
            100,
            first_features["contour_point_count"] * 4 + 20,
        ),
    }
    result["passed"] = bool(
        result["profile_equal"]
        and result["profile_type_equal"]
        and result["holes_equal"]
        and result["contour_compact"]
        and abs(result["volume_delta_percent"]) <= 0.001
        and result["max_aligned_dimension_delta_mm"] <= 0.01 + 1e-9
    )
    return result
