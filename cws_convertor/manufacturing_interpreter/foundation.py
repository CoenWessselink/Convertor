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


def refine_axis_from_shape(shape: Any, axis: AxisCandidate) -> AxisCandidate:
    requested = _unit(axis.direction)
    candidates = []
    try:
        edges = tuple(shape.Edges())
    except Exception:
        return axis
    for edge in edges:
        try:
            if str(edge.geomType()).upper() != "LINE":
                continue
            vertices = tuple(edge.Vertices())
            if len(vertices) != 2:
                continue
            start = _vector(vertices[0].Center())
            end = _vector(vertices[1].Center())
            delta = tuple(end[index] - start[index] for index in range(3))
            length = math.sqrt(_dot(delta, delta))
            if length <= 1e-9:
                continue
            direction = _unit(delta)
            alignment = _dot(direction, requested)
            if abs(alignment) < math.cos(math.radians(0.5)):
                continue
            if alignment < 0.0:
                start, end = end, start
                direction = tuple(-value for value in direction)
            candidates.append((length, start, end, direction))
        except Exception:
            continue
    if not candidates:
        return axis
    length, start, end, direction = max(candidates, key=lambda item: item[0])
    return replace(
        axis,
        direction=direction,
        origin_mm=start,
        end_mm=end,
        length_mm=length,
        signal_scores=tuple(axis.signal_scores) + (("exact_edge_refinement", 1.0),),
    )


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
    # Circular boundary extrema are not necessarily topological vertices.
    # Include their axial centre/extents so a narrow transverse drilling is
    # sampled even when all original prism vertices are at the two ends.
    try:
        for edge in shape.Edges():
            if str(edge.geomType()).upper() != "CIRCLE":
                continue
            circle = edge._geomAdaptor().Circle()
            center = tuple(circle.Location().Coord())
            normal = tuple(circle.Axis().Direction().Coord())
            center_z = _projection(center, frame)
            extent = abs(float(circle.Radius())) * math.sqrt(
                max(0.0, 1.0 - _dot(normal, frame.z_axis) ** 2)
            )
            positions.extend((center_z - extent, center_z, center_z + extent))
    except Exception:
        # Slice/interval proofs remain mandatory; a missing sampling hint can
        # never turn an unmeasured interval into a proven extrusion.
        pass
    if not positions:
        return []
    return sorted(set(round(value, 6) for value in positions))


def _station_positions(shape: Any, frame: ManufacturingFrame, linear_mm: float) -> tuple[float, ...]:
    events = _event_positions(shape, frame)
    if not events:
        return ()
    lower, upper = events[0], events[-1]
    if upper - lower <= linear_mm:
        return ((lower + upper) * 0.5,)
    epsilon = min((upper - lower) / 8.0, max(linear_mm * 2.0, (upper - lower) * 1e-5))
    candidates = [lower + epsilon, upper - epsilon,
                  *(lower + (upper - lower) * fraction for fraction in (0.25, 0.5, 0.75))]
    for left, right in zip(events, events[1:]):
        if right - left > epsilon * 2.0:
            candidates.extend(((left + right) * 0.5, left + epsilon, right - epsilon))
    candidates = sorted(set(round(min(max(item, lower + epsilon), upper - epsilon), 6) for item in candidates))
    if len(candidates) > 129:
        # Bounded sampling is not completeness: every returned invariant
        # interval must also pass a two-way native BREP reconstruction proof.
        step = (len(candidates) - 1) / 128.0
        candidates = [candidates[round(index * step)] for index in range(129)]
    return tuple(candidates)


def _measure_station(shape: Any, position_mm: float, linear_mm: float) -> tuple[SectionStation, Any]:
    """Intersect an analysis copy, never relabel the reference end section."""
    import cadquery as cq
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from types import SimpleNamespace
    from .topology import analyze_topology, section_signature

    plane = cq.Face.makePlane(basePnt=(0.0, 0.0, position_mm), dir=(0.0, 0.0, 1.0))
    cut = shape.intersect(plane)
    faces = tuple(cut.Faces())
    if not faces or not cut.isValid():
        raise ValueError("Geen geldige gesloten materiaaldwarsdoorsnede op deze positie")
    # Translate along the analysis axis only. A transverse offset must remain
    # visible: equal area and bounds do not prove identical swept geometry.
    flat = cut.translate((0.0, 0.0, -position_mm))
    topology, _ = analyze_topology(flat, SimpleNamespace(linear_mm=linear_mm))
    axis = AxisCandidate("section-normal", (0, 0, 1), (0, 0, 0), (0, 0, 1),
                         1.0, "measured_plane", 1.0)
    signature = section_signature(tuple(flat.Faces()), axis, topology)
    props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(flat.wrapped, props)
    center = props.CentreOfMass()
    inertia = props.MatrixOfInertia()
    # Area moments about the measured centroid in the fixed local basis, mm^4.
    moments = (float(inertia.Value(1, 1)), float(inertia.Value(2, 2)),
               -float(inertia.Value(1, 2)))
    if not all(math.isfinite(v) for v in (*moments, signature.area_mm2)) or signature.area_mm2 <= 0:
        raise ValueError("Doorsnedemeting heeft niet-eindige of niet-positieve waarden")
    def q(value: float) -> int:
        return round(float(value) / linear_mm)
    edges = []
    for edge in flat.Edges():
        start = tuple(q(v) for v in edge.startPoint().toTuple())
        end = tuple(q(v) for v in edge.endPoint().toTuple())
        edges.append((str(edge.geomType()), tuple(sorted((start, end))),
                      tuple(q(v) for v in edge.Center().toTuple()), q(edge.Length())))
    contour = _stable_id("measured-contour", sorted(edges))
    station = SectionStation(
        station_id=_stable_id("station", (round(position_mm, 6), contour)),
        position_mm=position_mm, safe=True, signature=signature,
        contour_signature=contour,
        loop_count=sum(1 + len(face.innerWires()) for face in faces),
        void_count=sum(len(face.innerWires()) for face in faces),
        centroid_2d_mm=(float(center.X()), float(center.Y())), moments=moments,
        measurement_status="MEASURED_NATIVE_BREP", moments_unit="mm4",
    )
    return station, cut


def _interval_proof(shape: Any, left_cut: Any, start: float, end: float,
                    linear_mm: float, area_relative: float) -> Any:
    """Prove the volume *between* slices, including features between samples."""
    import cadquery as cq
    from types import SimpleNamespace
    from .reconstruction import prove_equivalence

    box = shape.BoundingBox()
    margin = max(linear_mm * 4.0, 1.0)
    # The box is only an intersection tool, never substituted for source data.
    slab = cq.Solid.makeBox(box.xlen + margin * 2, box.ylen + margin * 2,
                           end - start, cq.Vector(box.xmin - margin, box.ymin - margin, start))
    source = shape.intersect(slab)
    solids = [cq.Solid.extrudeLinear(face.outerWire(), list(face.innerWires()),
                                    cq.Vector(0, 0, end - start)) for face in left_cut.Faces()]
    rebuilt = solids[0]
    for solid in solids[1:]:
        rebuilt = rebuilt.fuse(solid)
    return prove_equivalence(source, rebuilt, SimpleNamespace(linear_mm=linear_mm, relative=area_relative))


def build_sections_and_regions(
    shape: Any,
    frame: ManufacturingFrame,
    base_section: CrossSectionSignature,
    *,
    linear_mm: float,
    area_relative: float,
    topology: SourceTopologyEvidence,
) -> tuple[tuple[SectionStation, ...], tuple[SectionInterval, ...], tuple[ExtrusionRegionCandidate, ...]]:
    """Measured stations plus independently validated constant-section regions.

    Finite sampling alone never proves an invariant interval. Original native
    geometry is untouched; all transforms and Boolean tests use an analysis copy.
    Failed sections are explicit and cannot inherit a valid reference signature.
    """
    from .contracts import GeometryProofStatus
    if not math.isfinite(linear_mm) or linear_mm <= 0 or not math.isfinite(area_relative) or area_relative <= 0:
        raise ValueError("Ongeldig doorsnedetolerantiebeleid")
    if shape is None:
        return (), (), ()
    import cadquery as cq
    local = shape.copy().transformShape(cq.Plane(origin=frame.origin_mm,
                                               xDir=frame.x_axis, normal=frame.z_axis).fG)
    local_frame = ManufacturingFrame("analysis-local", (0, 0, 0), (1, 0, 0),
                                     (0, 1, 0), (0, 0, 1))
    positions = _station_positions(local, local_frame, linear_mm)
    stations: list[SectionStation] = []
    cuts: dict[str, Any] = {}
    for position in positions:
        try:
            station, cut = _measure_station(local, position, linear_mm)
            cuts[station.station_id] = cut
        except Exception as exc:
            empty = CrossSectionSignature(_stable_id("unmeasured", position), "", 0, 0, 0, 0,
                                          0, 0, (), "UNKNOWN")
            station = SectionStation(_stable_id("failed-station", position), position, False,
                                     empty, "", 0, 0, measurement_status="FAILED",
                                     measurement_error=f"{type(exc).__name__}: {exc}")
        stations.append(station)
    intervals: list[SectionInterval] = []
    regions: list[ExtrusionRegionCandidate] = []
    source_length = max(float(local.BoundingBox().zlen), linear_mm)
    supporting_faces = tuple(face.face_id for face in topology.faces)
    for left, right in zip(stations, stations[1:]):
        measured = left.safe and right.safe
        denominator = max(abs(left.signature.area_mm2), abs(right.signature.area_mm2), 1.0)
        area_change = abs(left.signature.area_mm2 - right.signature.area_mm2) / denominator
        same_contour = measured and left.contour_signature == right.contour_signature
        proof = None
        reason = "SECTION_CHANGE" if measured else "SECTION_MEASUREMENT_FAILED"
        if same_contour and area_change <= area_relative:
            try:
                proof = _interval_proof(local, cuts[left.station_id], left.position_mm,
                                        right.position_mm, linear_mm, area_relative)
                reason = "INTERVAL_RESIDUAL_NOT_PROVEN"
            except Exception:
                reason = "INTERVAL_PROOF_FAILED"
        invariant = bool(proof is not None and proof.two_way and proof.independent_reconstruction
                         and proof.status in {GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
                                              GeometryProofStatus.PROVEN_WITHIN_POLICY})
        interval = SectionInterval(
            interval_id=_stable_id("interval", (left.station_id, right.station_id)),
            start_mm=left.position_mm, end_mm=right.position_mm,
            station_ids=(left.station_id, right.station_id),
            classification="INVARIANT_EXTRUSION" if invariant else reason,
            invariant=invariant, change_score=area_change,
        )
        intervals.append(interval)
        if invariant:
            length = right.position_mm - left.position_mm
            regions.append(ExtrusionRegionCandidate(
                region_id=_stable_id("extrusion-region", (interval.interval_id, left.contour_signature)),
                frame_id=frame.frame_id, start_mm=left.position_mm, end_mm=right.position_mm,
                length_mm=length, section_id=left.signature.section_id,
                supporting_face_ids=supporting_faces, source_coverage=length / source_length,
                unexplained_positive_volume_mm3=proof.source_minus_reconstruction_mm3,
                unexplained_negative_volume_mm3=proof.reconstruction_minus_source_mm3, score=1.0,
            ))
    return tuple(stations), tuple(intervals), tuple(regions)


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
    "refine_axis_from_shape",
    "select_axis",
]
