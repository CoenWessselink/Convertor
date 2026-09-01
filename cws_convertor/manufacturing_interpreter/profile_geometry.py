from __future__ import annotations

import math
from typing import Any

from .contracts import CrossSectionSignature, ProfileMatchCandidate
from .profiles import profile_definitions


HOLLOW_FAMILIES = {"CHS", "RHS", "SHS"}


def _dimensions(definition: Any) -> tuple[float, float, float, float, float]:
    return (
        float(getattr(definition, "width", getattr(definition, "dim1", 0.0)) or 0.0),
        float(getattr(definition, "height", getattr(definition, "dim2", 0.0)) or 0.0),
        float(getattr(definition, "dim3", 0.0) or 0.0),
        float(getattr(definition, "dim4", 0.0) or 0.0),
        float(getattr(definition, "radius", 0.0) or 0.0),
    )


def _perimeter(family: str, width: float, height: float, thickness: float) -> float:
    family = family.upper()
    if family == "CHS":
        diameter = max(width, height)
        return math.pi * diameter + math.pi * max(0.0, diameter - 2.0 * thickness)
    if family in {"RHS", "SHS"}:
        return 2.0 * (width + height) + 2.0 * (
            max(0.0, width - 2.0 * thickness) + max(0.0, height - 2.0 * thickness)
        )
    return 2.0 * (width + height)


def match_full_profile_geometry(
    section: CrossSectionSignature,
    database: Any,
    policy: Any,
    *,
    limit: int = 12,
) -> tuple[ProfileMatchCandidate, ...]:
    recognition = getattr(policy, "recognition", policy)
    dimension_tolerance = float(getattr(recognition, "profile_dimension_mm", 0.15))
    area_relative = float(getattr(recognition, "section_area_relative", 0.001))
    candidates = []
    for definition in profile_definitions(database):
        width, height, thickness, flange, radius = _dimensions(definition)
        direct = abs(width - section.width_mm) + abs(height - section.height_mm)
        swapped = abs(height - section.width_mm) + abs(width - section.height_mm)
        dimension_residual = min(direct, swapped)
        area = float(getattr(definition, "area_mm2", 0.0) or 0.0)
        area_residual = abs(area - section.area_mm2)
        family = str(getattr(definition, "family", "")).upper()
        expected_perimeter = _perimeter(family, width, height, thickness)
        perimeter_residual = abs(expected_perimeter - section.perimeter_mm)
        expected_moment = max(area, 1.0) * (width * width + height * height) / 12.0
        observed_moment = max(section.area_mm2, 1.0) * (
            section.width_mm**2 + section.height_mm**2
        ) / 12.0
        moment_residual = abs(expected_moment - observed_moment) / max(
            expected_moment, observed_moment, 1.0
        )
        topology_match = (family in HOLLOW_FAMILIES) == (section.inner_wire_count > 0)
        radius_residual = 0.0 if radius <= 0.0 else min(
            abs(radius - min(width, height) * 0.5), abs(radius - thickness)
        )
        contour_distance = math.sqrt(
            dimension_residual**2
            + (area_residual / max(math.sqrt(max(area, 1.0)), 1.0)) ** 2
            + (perimeter_residual * 0.25) ** 2
        )
        normalized = (
            dimension_residual / max(dimension_tolerance, 1e-6)
            + area_residual / max(max(area, section.area_mm2, 1.0) * area_relative, 1e-6)
            + perimeter_residual / max(section.perimeter_mm * area_relative, dimension_tolerance, 1e-6)
            + moment_residual
            + (0.0 if topology_match else 10.0)
        )
        candidates.append(
            ProfileMatchCandidate(
                designation=str(getattr(definition, "designation", "")),
                dimension_residual_mm=dimension_residual,
                area_residual_mm2=area_residual,
                perimeter_residual_mm=perimeter_residual,
                moment_residual=moment_residual,
                radius_residual_mm=radius_residual,
                contour_distance_mm=contour_distance,
                topology_match=topology_match,
                score=1.0 / (1.0 + normalized),
            )
        )
    candidates.sort(
        key=lambda item: (
            -item.score,
            item.contour_distance_mm,
            item.dimension_residual_mm,
            item.designation,
        )
    )
    return tuple(candidates[:limit])


__all__ = ["match_full_profile_geometry"]
