"""Exact BREP deviation sampling for V7 compare heatmaps."""
from __future__ import annotations

import math
from statistics import mean
from typing import Iterable

from cws_viewer.exact.model import ExactPartRuntime, SubshapeKind
from cws_viewer.math3d import Vector3

from .model import DeviationField, DeviationSample


def _surface_points(runtime: ExactPartRuntime, *, max_points: int = 1200) -> tuple[tuple[Vector3, str], ...]:
    points: list[tuple[Vector3, str]] = []
    for descriptor in runtime.snapshot.subshapes:
        if descriptor.kind == SubshapeKind.VERTEX:
            points.append((descriptor.center, descriptor.stable_id))
            continue
        if descriptor.kind != SubshapeKind.EDGE:
            continue
        edge = runtime.shape_by_subshape_id.get(descriptor.stable_id)
        if edge is not None and hasattr(edge, "sample"):
            count = 24 if descriptor.geometry_type in {"CIRCLE", "ARC", "ELLIPSE"} else 5
            try:
                sampled, _parameters = edge.sample(count)
                points.extend((Vector3(float(point.x), float(point.y), float(point.z)), descriptor.stable_id) for point in sampled)
                continue
            except Exception:
                pass
        if descriptor.start is not None:
            points.append((descriptor.start, descriptor.stable_id))
        if descriptor.end is not None:
            points.append((descriptor.end, descriptor.stable_id))

    unique: dict[tuple[float, float, float], tuple[Vector3, str]] = {}
    for point, subshape_id in points:
        key = (round(point.x, 8), round(point.y, 8), round(point.z, 8))
        unique.setdefault(key, (point, subshape_id))
    ordered = tuple(unique[key] for key in sorted(unique))
    if len(ordered) <= max_points:
        return ordered
    stride = len(ordered) / max_points
    return tuple(ordered[min(int(index * stride), len(ordered) - 1)] for index in range(max_points))


def _distances(points: Iterable[tuple[Vector3, str]], target_shape, *, source_label: str) -> list[tuple[Vector3, str, str, float]]:
    import cadquery as cq

    values: list[tuple[Vector3, str, str, float]] = []
    for point, subshape_id in points:
        vertex = cq.Vertex.makeVertex(point.x, point.y, point.z)
        values.append((point, subshape_id, source_label, float(vertex.distance(target_shape))))
    return values


def build_deviation_field(
    source: ExactPartRuntime,
    target: ExactPartRuntime,
    *,
    tolerance_mm: float = 0.02,
    max_points_per_direction: int = 1200,
) -> DeviationField:
    if tolerance_mm <= 0:
        raise ValueError("Deviation tolerance moet positief zijn")
    raw = [
        *_distances(_surface_points(source, max_points=max_points_per_direction), target.shape, source_label="source"),
        *_distances(_surface_points(target, max_points=max_points_per_direction), source.shape, source_label="target"),
    ]
    if not raw:
        return DeviationField(
            source_hash=source.snapshot.exact_geometry_hash,
            target_hash=target.snapshot.exact_geometry_hash,
            tolerance_mm=tolerance_mm,
            maximum_mm=0.0,
            p95_mm=0.0,
            mean_mm=0.0,
            samples=(),
        )
    distances = sorted(item[3] for item in raw)
    maximum = distances[-1]
    p95 = distances[min(len(distances) - 1, max(0, math.ceil(len(distances) * 0.95) - 1))]
    scale = max(tolerance_mm, maximum, 1e-12)
    samples = tuple(
        DeviationSample(
            point=point,
            distance_mm=distance,
            normalized=min(1.0, distance / scale),
            source=source_label,
            subshape_id=subshape_id,
        )
        for point, subshape_id, source_label, distance in raw
    )
    return DeviationField(
        source_hash=source.snapshot.exact_geometry_hash,
        target_hash=target.snapshot.exact_geometry_hash,
        tolerance_mm=tolerance_mm,
        maximum_mm=maximum,
        p95_mm=p95,
        mean_mm=mean(distances),
        samples=samples,
    )


__all__ = ["build_deviation_field"]
