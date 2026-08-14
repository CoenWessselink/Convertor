"""Exact snapping and measurement-anchor creation for OCCT subshapes."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from cws_viewer.math3d import Vector3
from cws_viewer.measurements.model import ExactMeasurementAnchor, MeasurementProof, SnapType

from .model import ExactPartRuntime, SubshapeDescriptor, SubshapeKind


@dataclass(frozen=True, slots=True)
class SnapCandidate:
    snap_type: SnapType
    point: Vector3
    subshape_id: str
    distance: float
    feature_id: str | None = None
    direction: Vector3 | None = None
    normal: Vector3 | None = None
    analytical_data: tuple[tuple[str, float | str], ...] = ()


def _local_point(runtime: ExactPartRuntime, world: Vector3) -> Vector3:
    frame = runtime.snapshot.production_frame
    delta = world - frame.origin
    return Vector3(delta.dot(frame.x_axis), delta.dot(frame.y_axis), delta.dot(frame.z_axis))


def _feature_for_subshape(runtime: ExactPartRuntime, subshape_id: str) -> str | None:
    for feature in runtime.snapshot.features:
        if subshape_id in feature.subshape_ids:
            return feature.feature_id
    return None


def anchor_from_candidate(runtime: ExactPartRuntime, candidate: SnapCandidate) -> ExactMeasurementAnchor:
    descriptor = runtime.snapshot.subshape_by_id[candidate.subshape_id]
    return ExactMeasurementAnchor(
        node_id=f"part:{runtime.snapshot.part_id}",
        entity_id=runtime.snapshot.part_id,
        source_entity_id=runtime.snapshot.source_name,
        feature_id=candidate.feature_id or _feature_for_subshape(runtime, candidate.subshape_id),
        subshape_type=descriptor.kind.value,
        subshape_id=descriptor.stable_id,
        world_point=candidate.point,
        local_point=_local_point(runtime, candidate.point),
        geometry_hash=runtime.snapshot.exact_geometry_hash,
        snap_type=candidate.snap_type,
        proof=MeasurementProof.ANALYTICAL_BREP,
        direction=candidate.direction,
        normal=candidate.normal,
        analytical_data=candidate.analytical_data,
    )


def _nearest_on_segment(point: Vector3, start: Vector3, end: Vector3) -> Vector3:
    delta = end - start
    length2 = delta.dot(delta)
    if length2 <= 1e-20:
        return start
    t = max(0.0, min(1.0, (point - start).dot(delta) / length2))
    return start + delta * t


def _circle_nearest(point: Vector3, center: Vector3, radius: float, normal: Vector3 | None) -> Vector3:
    axis = (normal or Vector3(0, 0, 1)).normalized()
    radial = point - center
    radial = radial - axis * radial.dot(axis)
    if radial.length() <= 1e-12:
        reference = Vector3(1, 0, 0)
        if abs(reference.dot(axis)) > 0.9:
            reference = Vector3(0, 1, 0)
        radial = axis.cross(reference).normalized()
    else:
        radial = radial.normalized()
    return center + radial * radius


def candidates_for_subshape(runtime: ExactPartRuntime, subshape_id: str, query: Vector3 | None = None) -> tuple[SnapCandidate, ...]:
    descriptor = runtime.snapshot.subshape_by_id.get(subshape_id)
    if descriptor is None:
        raise KeyError(subshape_id)
    query_point = query or descriptor.center
    feature_id = _feature_for_subshape(runtime, subshape_id)
    result: list[SnapCandidate] = []

    def add(kind: SnapType, point: Vector3, *, direction=None, normal=None, analytical=()):
        result.append(SnapCandidate(
            snap_type=kind,
            point=point,
            subshape_id=subshape_id,
            distance=(point - query_point).length(),
            feature_id=feature_id,
            direction=direction,
            normal=normal,
            analytical_data=tuple(analytical),
        ))

    if descriptor.kind == SubshapeKind.VERTEX:
        add(SnapType.VERTEX, descriptor.center)
    elif descriptor.kind == SubshapeKind.EDGE:
        if descriptor.start is not None:
            add(SnapType.ENDPOINT, descriptor.start, direction=descriptor.direction)
        if descriptor.end is not None and (descriptor.start is None or not descriptor.end.almost_equal(descriptor.start)):
            add(SnapType.ENDPOINT, descriptor.end, direction=descriptor.direction)
        if descriptor.geometry_type == "LINE" and descriptor.start is not None and descriptor.end is not None:
            add(SnapType.MIDPOINT, (descriptor.start + descriptor.end) * 0.5, direction=descriptor.direction)
            nearest = _nearest_on_segment(query_point, descriptor.start, descriptor.end)
            add(SnapType.NEAREST, nearest, direction=descriptor.direction)
            add(SnapType.PERPENDICULAR, nearest, direction=descriptor.direction)
        elif descriptor.geometry_type in {"CIRCLE", "ARC"} and descriptor.axis_origin and descriptor.radius:
            analytical = (("radius", float(descriptor.radius)),)
            add(SnapType.CENTER, descriptor.axis_origin, normal=descriptor.axis_direction, analytical=analytical)
            add(
                SnapType.NEAREST,
                _circle_nearest(query_point, descriptor.axis_origin, descriptor.radius, descriptor.axis_direction),
                normal=descriptor.axis_direction,
                analytical=analytical,
            )
    elif descriptor.kind == SubshapeKind.FACE:
        analytical: list[tuple[str, float | str]] = [("area", float(descriptor.measure))]
        if descriptor.radius is not None:
            analytical.append(("radius", float(descriptor.radius)))
        add(SnapType.FACE_CENTER, descriptor.center, normal=descriptor.normal or descriptor.axis_direction, analytical=analytical)
        if descriptor.geometry_type == "CYLINDER" and descriptor.axis_origin and descriptor.radius:
            add(SnapType.CENTER, descriptor.axis_origin, direction=descriptor.axis_direction, analytical=analytical)

    result.sort(key=lambda item: (item.distance, item.snap_type.value, item.subshape_id))
    return tuple(result)


def snap(runtime: ExactPartRuntime, query: Vector3, *, allowed: Iterable[SnapType] | None = None, tolerance_mm: float = 5.0) -> SnapCandidate | None:
    allowed_set = None if allowed is None else {SnapType(item) for item in allowed}
    candidates: list[SnapCandidate] = []
    for descriptor in runtime.snapshot.subshapes:
        for candidate in candidates_for_subshape(runtime, descriptor.stable_id, query):
            if allowed_set is None or candidate.snap_type in allowed_set:
                candidates.append(candidate)
    if not candidates:
        return None
    best = min(candidates, key=lambda item: (item.distance, item.snap_type.value, item.subshape_id))
    return best if best.distance <= float(tolerance_mm) else None


def line_intersection(
    first: SubshapeDescriptor,
    second: SubshapeDescriptor,
    *,
    tolerance_mm: float = 1e-6,
) -> Vector3 | None:
    """Return the exact intersection of two finite line segments when unique."""
    if first.geometry_type != "LINE" or second.geometry_type != "LINE":
        return None
    if None in {first.start, first.end, second.start, second.end}:
        return None
    assert first.start and first.end and second.start and second.end
    p, q = first.start, second.start
    u, v = first.end - first.start, second.end - second.start
    w0 = p - q
    a, b, c = u.dot(u), u.dot(v), v.dot(v)
    d, e = u.dot(w0), v.dot(w0)
    denominator = a * c - b * b
    if abs(denominator) <= 1e-16:
        return None
    s = (b * e - c * d) / denominator
    t = (a * e - b * d) / denominator
    if not (-tolerance_mm <= s <= 1.0 + tolerance_mm and -tolerance_mm <= t <= 1.0 + tolerance_mm):
        return None
    p1, p2 = p + u * s, q + v * t
    if (p1 - p2).length() > tolerance_mm:
        return None
    return (p1 + p2) * 0.5


__all__ = [
    "SnapCandidate",
    "anchor_from_candidate",
    "candidates_for_subshape",
    "snap",
    "line_intersection",
]
