"""Deterministic source-versus-canonical exact geometry comparison."""
from __future__ import annotations

import math
from typing import Iterable

from cws_viewer.math3d import Vector3

from .model import (
    CompareSeverity,
    ComparisonMetric,
    ExactComparisonReport,
    ExactPartRuntime,
    FeatureDescriptor,
    SubshapeKind,
)


def _metric(name: str, source: float, target: float, tolerance: float, unit: str, *, relative_tolerance: float = 0.0) -> ComparisonMetric:
    delta = abs(float(target) - float(source))
    denominator = max(abs(float(source)), 1e-12)
    relative = delta / denominator
    allowed = max(float(tolerance), denominator * float(relative_tolerance))
    severity = CompareSeverity.PASS if delta <= allowed else CompareSeverity.FAIL
    return ComparisonMetric(
        name=name,
        source_value=float(source),
        canonical_value=float(target),
        absolute_delta=delta,
        relative_delta=relative,
        tolerance=allowed,
        severity=severity,
        unit=unit,
    )


def _sample_points(runtime: ExactPartRuntime, max_points: int = 500) -> tuple[Vector3, ...]:
    """Return deterministic points that are guaranteed to lie on the BREP.

    Descriptor centres are suitable for UI labels, but a trimmed face centre or
    an analytical arc centre does not necessarily lie on the represented
    subshape.  Sampling the actual OCCT edge avoids false source-to-self
    deviations for fillets and partially trimmed circles.
    """
    points: list[Vector3] = []
    for item in runtime.snapshot.subshapes:
        if item.kind == SubshapeKind.VERTEX:
            points.append(item.center)
            continue
        if item.kind != SubshapeKind.EDGE:
            continue

        edge = runtime.shape_by_subshape_id.get(item.stable_id)
        if edge is not None and hasattr(edge, "sample"):
            sample_count = 12 if item.geometry_type in {"CIRCLE", "ARC"} else 3
            try:
                sampled, _parameters = edge.sample(sample_count)
                points.extend(Vector3(float(p.x), float(p.y), float(p.z)) for p in sampled)
                continue
            except Exception:
                # Fall back to descriptor endpoints.  Comparison stays safe: a
                # failed sample cannot create invented interior evidence.
                pass
        if item.start is not None:
            points.append(item.start)
        if item.end is not None:
            points.append(item.end)

    unique: dict[tuple[float, float, float], Vector3] = {}
    for point in points:
        key = (round(point.x, 7), round(point.y, 7), round(point.z, 7))
        unique.setdefault(key, point)
    ordered = tuple(unique[key] for key in sorted(unique))
    if len(ordered) <= max_points:
        return ordered
    stride = len(ordered) / max_points
    return tuple(ordered[min(int(index * stride), len(ordered) - 1)] for index in range(max_points))


def _max_point_distance(points: Iterable[Vector3], target_shape) -> float:
    import cadquery as cq

    maximum = 0.0
    for point in points:
        vertex = cq.Vertex.makeVertex(point.x, point.y, point.z)
        maximum = max(maximum, float(vertex.distance(target_shape)))
    return maximum


def _feature_key(feature: FeatureDescriptor) -> tuple:
    # A single outer contour can be represented on either of the two parallel
    # reference faces. Its topology is already covered by exact BREP metrics,
    # so the semantic feature key intentionally ignores the face offset.
    if feature.feature_type == "outer_contour":
        return (feature.feature_type,)
    return (
        feature.feature_type,
        round(feature.center.x, 3),
        round(feature.center.y, 3),
        round(feature.center.z, 3),
        None if feature.radius is None else round(feature.radius, 3),
        None if feature.depth is None else round(feature.depth, 3),
    )


def compare_exact_parts(
    source: ExactPartRuntime,
    canonical: ExactPartRuntime,
    *,
    length_tolerance_mm: float = 0.01,
    deviation_tolerance_mm: float = 0.02,
    relative_volume_tolerance: float = 1e-6,
    relative_area_tolerance: float = 1e-6,
) -> ExactComparisonReport:
    sp, cp = source.snapshot.properties, canonical.snapshot.properties
    metrics: list[ComparisonMetric] = [
        _metric("volume", sp.volume_mm3, cp.volume_mm3, 1e-6, "mm3", relative_tolerance=relative_volume_tolerance),
        _metric("surface_area", sp.surface_area_mm2, cp.surface_area_mm2, 1e-6, "mm2", relative_tolerance=relative_area_tolerance),
        _metric("solid_count", sp.solid_count, cp.solid_count, 0.0, "count"),
        _metric("face_count", sp.face_count, cp.face_count, 0.0, "count"),
        _metric("edge_count", sp.edge_count, cp.edge_count, 0.0, "count"),
        _metric("vertex_count", sp.vertex_count, cp.vertex_count, 0.0, "count"),
    ]
    source_dims = sp.bounds.size
    canonical_dims = cp.bounds.size
    for label, a, b in (
        ("bbox_x", source_dims.x, canonical_dims.x),
        ("bbox_y", source_dims.y, canonical_dims.y),
        ("bbox_z", source_dims.z, canonical_dims.z),
    ):
        metrics.append(_metric(label, a, b, length_tolerance_mm, "mm"))

    source_to_canonical = _max_point_distance(_sample_points(source), canonical.shape)
    canonical_to_source = _max_point_distance(_sample_points(canonical), source.shape)
    metrics.append(_metric("source_to_canonical_max", 0.0, source_to_canonical, deviation_tolerance_mm, "mm"))
    metrics.append(_metric("canonical_to_source_max", 0.0, canonical_to_source, deviation_tolerance_mm, "mm"))

    source_features = {_feature_key(item): item for item in source.snapshot.features}
    canonical_features = {_feature_key(item): item for item in canonical.snapshot.features}
    matched = sorted(set(source_features) & set(canonical_features))
    missing = tuple(source_features[key].feature_id for key in sorted(set(source_features) - set(canonical_features)))
    added = tuple(canonical_features[key].feature_id for key in sorted(set(canonical_features) - set(source_features)))

    blocking: list[str] = []
    if any(item.severity == CompareSeverity.FAIL for item in metrics):
        blocking.append("CWS-EXACT-GEOMETRY-DELTA")
    if missing:
        blocking.append("CWS-EXACT-FEATURE-MISSING")
    if added:
        blocking.append("CWS-EXACT-FEATURE-ADDED")
    overall = CompareSeverity.FAIL if blocking else CompareSeverity.PASS
    return ExactComparisonReport(
        source_hash=source.snapshot.exact_geometry_hash,
        canonical_hash=canonical.snapshot.exact_geometry_hash,
        metrics=tuple(metrics),
        source_to_canonical_max_mm=source_to_canonical,
        canonical_to_source_max_mm=canonical_to_source,
        matched_features=len(matched),
        missing_features=missing,
        added_features=added,
        overall=overall,
        blocking_codes=tuple(blocking),
    )


__all__ = ["compare_exact_parts"]
