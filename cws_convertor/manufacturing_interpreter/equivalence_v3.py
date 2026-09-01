from __future__ import annotations

import math
from typing import Any

from .contracts import ResidualComponent, ResidualGeometryReport
from .recognition_cache import stable_sha256


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value()) if callable(value) else float(value)
    except Exception:
        return default


def _bbox(shape: Any) -> tuple[float, float, float, float, float, float]:
    try:
        box = shape.BoundingBox()
        return tuple(float(item) for item in (box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax))
    except Exception:
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def _center(shape: Any) -> tuple[float, float, float]:
    try:
        value = shape.Center()
        if hasattr(value, "toTuple"):
            value = value.toTuple()
        return tuple(float(item) for item in value[:3])
    except Exception:
        return (0.0, 0.0, 0.0)


def _components(shape: Any, direction: str, sliver_mm3: float) -> tuple[ResidualComponent, ...]:
    try:
        solids = tuple(shape.Solids())
    except Exception:
        solids = (shape,) if shape is not None else ()
    result = []
    for index, solid in enumerate(solids):
        volume = abs(_number(getattr(solid, "Volume", 0.0)))
        if volume <= sliver_mm3:
            continue
        result.append(
            ResidualComponent(
                component_id=f"residual-{stable_sha256((direction, index, volume, _bbox(solid)))[:20]}",
                direction=direction,
                volume_mm3=volume,
                bbox_mm=_bbox(solid),
                centroid_mm=_center(solid),
            )
        )
    return tuple(result)


def _point_distance(shape: Any, point: tuple[float, float, float]) -> float:
    try:
        import cadquery as cq

        vertex = cq.Vertex.makeVertex(*point)
        return abs(float(shape.distance(vertex)))
    except Exception:
        return math.inf


def _sample_vertices(shape: Any, limit: int = 96) -> tuple[tuple[float, float, float], ...]:
    try:
        vertices = tuple(shape.Vertices())
    except Exception:
        return ()
    if len(vertices) > limit:
        step = (len(vertices) - 1) / float(limit - 1)
        vertices = tuple(vertices[round(index * step)] for index in range(limit))
    result = []
    for vertex in vertices:
        result.append(_center(vertex))
    return tuple(result)


def _percentile(values: list[float], fraction: float) -> float:
    finite = sorted(value for value in values if math.isfinite(value))
    if not finite:
        return math.inf
    return finite[round((len(finite) - 1) * fraction)]


def residual_geometry_report(source: Any, reconstructed: Any, policy: Any) -> ResidualGeometryReport:
    recognition = getattr(policy, "recognition", policy)
    sliver = float(getattr(recognition, "boolean_sliver_mm3", 0.01))
    positive = negative = None
    kernel_status = "PASS"
    try:
        positive = source.cut(reconstructed)
        negative = reconstructed.cut(source)
    except Exception as exc:
        kernel_status = f"FAILED:{type(exc).__name__}"
    positive_components = _components(positive, "SOURCE_MINUS_RECONSTRUCTION", sliver)
    negative_components = _components(negative, "RECONSTRUCTION_MINUS_SOURCE", sliver)
    distances = []
    for point in _sample_vertices(source):
        distances.append(_point_distance(reconstructed, point))
    for point in _sample_vertices(reconstructed):
        distances.append(_point_distance(source, point))
    components = positive_components + negative_components
    positive_volume = sum(item.volume_mm3 for item in positive_components)
    negative_volume = sum(item.volume_mm3 for item in negative_components)
    return ResidualGeometryReport(
        report_id=f"residual-report-{stable_sha256((positive_volume, negative_volume, distances))[:20]}",
        source_minus_reconstruction_status="EMPTY" if not positive_components else "NON_EMPTY",
        reconstruction_minus_source_status="EMPTY" if not negative_components else "NON_EMPTY",
        source_minus_reconstruction_mm3=positive_volume,
        reconstruction_minus_source_mm3=negative_volume,
        components=components,
        boundary_distance_p50_mm=_percentile(distances, 0.50),
        boundary_distance_p95_mm=_percentile(distances, 0.95),
        boundary_distance_max_mm=max((value for value in distances if math.isfinite(value)), default=math.inf),
        boolean_kernel_status=kernel_status,
        unmatched_source_regions=tuple(item.component_id for item in positive_components),
        overbuilt_regions=tuple(item.component_id for item in negative_components),
    )


__all__ = ["residual_geometry_report"]
