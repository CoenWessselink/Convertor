from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from typing import Any, Iterable

from .contracts import (
    AnalyticFaceGroup,
    AxisCandidate,
    CrossSectionSignature,
    ExtrusionRegionCandidate,
    ManufacturingFrame,
    ProfileMatchCandidate,
    SectionInterval,
    SectionStation,
    SourceTopologyEvidence,
)


def _stable_id(namespace: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return f"{namespace}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _vector(value: Any) -> tuple[float, float, float]:
    if hasattr(value, "toTuple"):
        value = value.toTuple()
    return tuple(float(item) for item in value[:3])  # type: ignore[index]


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _unit(value: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(max(_dot(value, value), 1e-30))
    return tuple(item / length for item in value)  # type: ignore[return-value]


def group_analytic_faces(topology: SourceTopologyEvidence) -> SourceTopologyEvidence:
    grouped: dict[tuple[str, tuple[tuple[str, str], ...]], list[str]] = {}
    for face in topology.faces:
        key = (str(face.surface_type).upper(), tuple(sorted(face.analytic_parameters)))
        grouped.setdefault(key, []).append(face.face_id)
    groups = tuple(
        AnalyticFaceGroup(
            group_id=_stable_id("surface-group", (surface, parameters, sorted(face_ids))),
            surface_type=surface,
            member_face_ids=tuple(sorted(face_ids)),
            analytic_parameters=parameters,
            boundary_signature=_stable_id("boundary", sorted(face_ids)),
        )
        for (surface, parameters), face_ids in sorted(grouped.items(), key=lambda item: str(item[0]))
    )
    return replace(topology, analytic_groups=groups)


def select_axis(axes: tuple[AxisCandidate, ...], selected_axis_id: str = "") -> AxisCandidate | None:
    for axis in axes:
        if axis.axis_id == selected_axis_id:
            return axis
    return max(axes, key=lambda axis: (axis.score, axis.length_mm, axis.axis_id), default=None)


def build_manufacturing_frame(axis: AxisCandidate) -> ManufacturingFrame:
    z_axis = _unit(axis.direction)
    reference = min(
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        key=lambda candidate: abs(_dot(candidate, z_axis)),
    )
    x_axis = _unit(_cross(reference, z_axis))
    y_axis = _unit(_cross(z_axis, x_axis))
    origin = _vector(axis.origin_mm)
    evidence = (
        ("axis_score", float(axis.score)),
        ("orthogonality_xy", abs(_dot(x_axis, y_axis))),
        ("orthogonality_xz", abs(_dot(x_axis, z_axis))),
        ("orthogonality_yz", abs(_dot(y_axis, z_axis))),
    )
    return ManufacturingFrame(
        frame_id=_stable_id("frame", (origin, x_axis, y_axis, z_axis)),
        origin_mm=origin,
        x_axis=x_axis,
        y_axis=y_axis,
        z_axis=z_axis,
        evidence=evidence,
    )


def _projection(point: tuple[float, float, float], frame: ManufacturingFrame) -> float:
    relative = tuple(point[index] - frame.origin_mm[index] for index in range(3))
    return _dot(relative, frame.z_axis)


def _event_positions(shape: Any, frame: ManufacturingFrame) -> list[float]:
    positions: list[float] = []
    try:
        positions.extend(_projection(_vector(vertex.Center()), frame) for vertex in shape.Vertices())
    except Exception:
        pass
    if not positions:
        return [0.0, 1.0]
    return sorted(set(round(value, 6) for value in positions))


def _station_positions(shape: Any, frame: ManufacturingFrame, linear_mm: float) -> tuple[float, ...]:
    events = _event_positions(shape, frame)
    lower, upper = events[0], events[-1]
    if upper - lower <= linear_mm:
        return ((lower + upper) * 0.5,)
    epsilon = max(linear_mm * 2.0, (upper - lower) * 1e-5)
    candidates = [lower + epsilon, upper - epsilon, (lower + upper) * 0.5]
    for left, right in zip(events, events[1:]):
        if right - left > epsilon * 2.0:
            candidates.append((left + right) * 0.5)
    candidates = sorted(set(round(min(max(item, lower + epsilon), upper - epsilon), 6) for item in candidates))
    if len(candidates) > 33:
        step = (len(candidates) - 1) / 32.0
        candidates = [candidates[round(index * step)] for index in range(33)]
    return tuple(candidates)


def _station_signature(
    base: CrossSectionSignature,
    position_mm: float,
    index: int,
) -> SectionStation:
    contour_payload = (
        round(base.area_mm2, 6),
        round(base.perimeter_mm, 6),
        round(base.width_mm, 6),
        round(base.height_mm, 6),
        base.outer_edge_count,
        base.inner_wire_count,
        tuple(base.edge_type_counts),
    )
    contour_signature = _stable_id("contour", contour_payload)
    return SectionStation(
        station_id=_stable_id("station", (round(position_mm, 6), contour_signature)),
        position_mm=position_mm,
        safe=True,
        signature=replace(base, section_id=_stable_id("section", (contour_payload, index))),
        contour_signature=contour_signature,
        loop_count=max(1, 1 + base.inner_wire_count),
        void_count=base.inner_wire_count,
        moments=(base.width_mm**2 / 12.0, base.height_mm**2 / 12.0, 0.0),
    )


def build_sections_and_regions(
    shape: Any,
    frame: ManufacturingFrame,
    base_section: CrossSectionSignature,
    *,
    linear_mm: float,
    area_relative: float,
    topology: SourceTopologyEvidence,
) -> tuple[tuple[SectionStation, ...], tuple[SectionInterval, ...], tuple[ExtrusionRegionCandidate, ...]]:
    stations = tuple(
        _station_signature(base_section, position, index)
        for index, position in enumerate(_station_positions(shape, frame, linear_mm))
    )
    intervals: list[SectionInterval] = []
    regions: list[ExtrusionRegionCandidate] = []
    supporting_faces = tuple(face.face_id for face in topology.faces)
    for index, (left, right) in enumerate(zip(stations, stations[1:])):
        denominator = max(abs(left.signature.area_mm2), abs(right.signature.area_mm2), 1.0)
        area_change = abs(left.signature.area_mm2 - right.signature.area_mm2) / denominator
        same_contour = left.contour_signature == right.contour_signature
        invariant = same_contour and area_change <= area_relative
        interval = SectionInterval(
            interval_id=_stable_id("interval", (left.station_id, right.station_id)),
            start_mm=left.position_mm,
            end_mm=right.position_mm,
            station_ids=(left.station_id, right.station_id),
            classification="INVARIANT_EXTRUSION" if invariant else "SECTION_CHANGE",
            invariant=invariant,
            change_score=area_change,
        )
        intervals.append(interval)
        if invariant:
            length = max(0.0, right.position_mm - left.position_mm)
            regions.append(
                ExtrusionRegionCandidate(
                    region_id=_stable_id("extrusion-region", (interval.interval_id, left.contour_signature)),
                    frame_id=frame.frame_id,
                    start_mm=left.position_mm,
                    end_mm=right.position_mm,
                    length_mm=length,
                    section_id=left.signature.section_id,
                    supporting_face_ids=supporting_faces,
                    source_coverage=1.0,
                    unexplained_positive_volume_mm3=0.0,
                    unexplained_negative_volume_mm3=0.0,
                    score=1.0,
                )
            )
    if len(stations) == 1:
        regions.append(
            ExtrusionRegionCandidate(
                region_id=_stable_id("extrusion-region", stations[0].station_id),
                frame_id=frame.frame_id,
                start_mm=stations[0].position_mm,
                end_mm=stations[0].position_mm,
                length_mm=0.0,
                section_id=stations[0].signature.section_id,
                supporting_face_ids=supporting_faces,
                source_coverage=0.0,
                unexplained_positive_volume_mm3=0.0,
                unexplained_negative_volume_mm3=0.0,
                score=0.0,
            )
        )
    return stations, tuple(intervals), tuple(regions)


def profile_candidates(profile: Any, section: CrossSectionSignature) -> tuple[ProfileMatchCandidate, ...]:
    names: Iterable[str] = getattr(profile, "candidates", ()) or ()
    if getattr(profile, "designation", ""):
        names = (profile.designation, *tuple(names))
    unique = tuple(dict.fromkeys(str(name) for name in names if name))
    if not unique:
        return ()
    return tuple(
        ProfileMatchCandidate(
            designation=name,
            dimension_residual_mm=float(getattr(profile, "dimension_delta_mm", 0.0)),
            area_residual_mm2=float(getattr(profile, "area_delta_mm2", 0.0)),
            perimeter_residual_mm=0.0,
            moment_residual=0.0,
            radius_residual_mm=0.0,
            contour_distance_mm=0.0 if index == 0 else max(section.width_mm, section.height_mm) * 0.01,
            topology_match=True,
            score=max(0.0, float(getattr(profile, "confidence", 0.0)) - index * 0.05),
        )
        for index, name in enumerate(unique)
    )


__all__ = [
    "build_manufacturing_frame",
    "build_sections_and_regions",
    "group_analytic_faces",
    "profile_candidates",
    "select_axis",
]
