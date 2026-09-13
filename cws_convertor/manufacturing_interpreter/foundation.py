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
    _, _, _, direction = max(candidates, key=lambda item: item[0])
    # A groove/cope can break all longitudinal edges. The longest remaining
    # edge proves direction, not the full physical member length.
    points = [_vector(vertex.Center()) for vertex in shape.Vertices()]
    projections = [_dot(point, direction) for point in points]
    if not projections:
        return axis
    low, high = min(projections), max(projections)
    length = high-low
    anchor = _vector(axis.origin_mm)
    start = tuple(anchor[i]+direction[i]*(low-_dot(anchor, direction)) for i in range(3))
    end = tuple(start[i]+direction[i]*length for i in range(3))
    return replace(
        axis,
        direction=direction,
        origin_mm=start,
        end_mm=end,
        length_mm=length,
        signal_scores=tuple(axis.signal_scores) + (("exact_edge_direction_full_source_extent", 1.0),),
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
    if not positions:
        return [0.0, 1.0]
    return sorted(set(round(value, 6) for value in positions))


def _station_positions(shape: Any, frame: ManufacturingFrame, linear_mm: float) -> tuple[float, ...]:
    events = _event_positions(shape, frame)
    lower, upper = events[0], events[-1]
    if upper - lower <= linear_mm:
        return ((lower + upper) * 0.5,)
    epsilon = min((upper - lower) / 8.0, max(linear_mm * 2.0, (upper - lower) * 1e-5))
    candidates = [lower + epsilon, upper - epsilon, (lower + upper) * 0.5]
    for left, right in zip(events, events[1:]):
        if right - left > epsilon * 2.0:
            candidates.append((left + right) * 0.5)
    candidates = sorted(set(round(min(max(item, lower + epsilon), upper - epsilon), 6) for item in candidates))
    if len(candidates) > 33:
        step = (len(candidates) - 1) / 32.0
        candidates = [candidates[round(index * step)] for index in range(33)]
    return tuple(candidates)


def _measure_station(local_shape: Any, position_mm: float, linear_mm: float) -> tuple[SectionStation, tuple[Any, ...]]:
    """Intersect the analysis copy; never repeat a reference end-face signature.

    Moments are centroidal area moments in mm^4, measured by the CAD kernel.
    Virtual slice IDs are not claimed to be original source face identifiers.
    """
    import cadquery as cq
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from .topology import section_signature

    station_id = _stable_id("station", position_mm)
    try:
        section = local_shape.intersect(cq.Face.makePlane(basePnt=(0, 0, position_mm), dir=(0, 0, 1)))
        faces = tuple(section.Faces())
        if not faces or not all(face.isValid() and face.Area() > 0 for face in faces):
            raise ValueError("Empty or invalid section intersection")
        axis = AxisCandidate("slice-axis", (0., 0., 1.), (0., 0., 0.), (0., 0., 1.), 1., "analysis frame", 0.)
        topology = SourceTopologyEvidence("virtual-section", 0, (), (), ())
        signature = section_signature(faces, axis, topology)
        properties = GProp_GProps()
        BRepGProp.SurfaceProperties_s(section.wrapped, properties)
        centre = properties.CentreOfMass()
        inertia = properties.MatrixOfInertia()
        # The boundary key includes location, direction-independent endpoints,
        # interior samples and curve types. Equal area/bounds are not a contour.
        step = max(1e-8, linear_mm / 100.)
        def q(point: Any) -> tuple[int, int]:
            return (round(float(point.x) / step), round(float(point.y) / step))
        boundaries = []
        for face in faces:
            wires = []
            for wire in (face.outerWire(), *face.innerWires()):
                edges = []
                for edge in wire.Edges():
                    samples = tuple(sorted(q(edge.positionAt(t)) for t in (0., .25, .5, .75, 1.)))
                    edges.append((str(edge.geomType()), round(float(edge.Length()) / step), samples))
                wires.append(tuple(sorted(edges)))
            boundaries.append((wires[0], tuple(sorted(wires[1:]))))
        boundary_key = _stable_id("measured-contour", sorted(boundaries))
        station_id = _stable_id("station", (position_mm, boundary_key))
        signature = replace(signature, section_id=_stable_id("measured-section", (position_mm, boundary_key)),
                            face_id=station_id, supporting_face_ids=())
        return SectionStation(
            station_id=station_id, position_mm=position_mm, safe=True,
            signature=signature, contour_signature=boundary_key,
            loop_count=len(faces) + signature.inner_wire_count, void_count=signature.inner_wire_count,
            centroid_2d_mm=(float(centre.X()), float(centre.Y())),
            moments=(float(inertia.Value(1, 1)), float(inertia.Value(2, 2)), -float(inertia.Value(1, 2))),
            measurement_method="native-plane-intersection", status="MEASURED",
        ), faces
    except Exception as exc:
        # Unknown geometry is not a copy of a successful neighbour and is not
        # interpolated across. No invariant region may cross this station.
        signature = CrossSectionSignature(station_id, station_id, 0., 0., 0., 0., 0, 0, (), "UNKNOWN", component_count=0)
        return SectionStation(station_id, position_mm, False, signature, "", 0, 0,
                              measurement_method="native-plane-intersection", status="FAILED",
                              reason=f"{type(exc).__name__}: {exc}"), ()


def _prove_section_interval(local_shape: Any, faces: tuple[Any, ...], start: float, end: float,
                            linear_mm: float, area_relative: float) -> Any:
    """Compare a whole clipped source interval to a real section extrusion.

    Sampling alone is not proof: a small hidden notch between two equal slices
    must fail the independent, two-way local BREP residual check.
    """
    import cadquery as cq
    from types import SimpleNamespace
    from .reconstruction import prove_equivalence

    box = local_shape.BoundingBox()
    margin = max(linear_mm * 2., 1.)
    clip = cq.Solid.makeBox(box.xlen + 2*margin, box.ylen + 2*margin, end-start,
                           cq.Vector(box.xmin-margin, box.ymin-margin, start))
    source = local_shape.intersect(clip)
    pieces = [cq.Solid.extrudeLinear(f.outerWire(), list(f.innerWires()), cq.Vector(0, 0, end-start)) for f in faces]
    reconstructed = pieces[0]
    for piece in pieces[1:]:
        reconstructed = reconstructed.fuse(piece)
    return prove_equivalence(source, reconstructed, SimpleNamespace(linear_mm=linear_mm, relative=area_relative))


def build_sections_and_regions(
    shape: Any,
    frame: ManufacturingFrame,
    base_section: CrossSectionSignature,
    *,
    linear_mm: float,
    area_relative: float,
    topology: SourceTopologyEvidence,
) -> tuple[tuple[SectionStation, ...], tuple[SectionInterval, ...], tuple[ExtrusionRegionCandidate, ...]]:
    """Adaptive measured sections plus independently verified constant regions.

    ``base_section`` is retained for API compatibility, not used as a measured
    station. Finite samples can propose a region, only its full BREP test can
    certify it. A refinement budget limits cost, not acceptance tolerances.
    """
    import cadquery as cq
    from .contracts import GeometryProofStatus

    if not (math.isfinite(linear_mm) and linear_mm > 0 and math.isfinite(area_relative) and 0 < area_relative < 1):
        raise ValueError("Invalid section tolerance policy")
    # Transform a copy; preserve the source placement, geometry and handedness.
    plane = cq.Plane(origin=frame.origin_mm, xDir=frame.x_axis, normal=frame.z_axis)
    local_shape = plane.toLocalCoords(shape.copy())
    positions = _station_positions(shape, frame, linear_mm)
    measured = {position: _measure_station(local_shape, position, linear_mm) for position in positions}
    proofs: dict[tuple[float, float], Any] = {}
    accepted = {GeometryProofStatus.PROVEN_BREP_EQUIVALENT, GeometryProofStatus.PROVEN_WITHIN_POLICY}

    def interval_proof(left: float, right: float) -> Any:
        key = (left, right)
        if key not in proofs:
            first, faces = measured[left]
            last, _ = measured[right]
            if not first.safe or not last.safe or first.contour_signature != last.contour_signature:
                proofs[key] = None
            else:
                try:
                    proofs[key] = _prove_section_interval(local_shape, faces, left, right, linear_mm, area_relative)
                except Exception:
                    proofs[key] = None
        return proofs[key]

    # Refine observed changes and intervals whose equal endpoints conceal a
    # residual. Each failed or unresolved interval remains explicitly unproven.
    for _ in range(2):
        ordered = sorted(measured)
        additions = []
        for left, right in zip(ordered, ordered[1:]):
            proof = interval_proof(left, right)
            if right-left > 4*linear_mm and (proof is None or proof.status not in accepted):
                additions.append((left+right)/2.)
        for position in additions[:max(0, 65-len(measured))]:
            measured[position] = _measure_station(local_shape, position, linear_mm)
        if not additions or len(measured) >= 65:
            break

    stations = tuple(measured[position][0] for position in sorted(measured))
    intervals = []
    regions = []
    span = max(local_shape.BoundingBox().zlen, linear_mm)
    for left, right in zip(stations, stations[1:]):
        proof = interval_proof(left.position_mm, right.position_mm)
        invariant = bool(proof is not None and proof.status in accepted)
        denominator = max(abs(left.signature.area_mm2), abs(right.signature.area_mm2), 1.)
        area_change = abs(left.signature.area_mm2-right.signature.area_mm2) / denominator
        classification = "INVARIANT_EXTRUSION" if invariant else (
            "UNRESOLVED_SECTION" if not left.safe or not right.safe else
            "UNPROVEN_INTERVAL" if left.contour_signature == right.contour_signature else "SECTION_CHANGE")
        interval = SectionInterval(
            interval_id=_stable_id("interval", (left.station_id, right.station_id)),
            start_mm=left.position_mm, end_mm=right.position_mm,
            station_ids=(left.station_id, right.station_id), classification=classification,
            invariant=invariant, change_score=area_change,
            proof_status=proof.status.value if proof is not None else "NOT_PROVEN",
            reason=proof.reason if proof is not None else "Sections differ or interval proof unavailable",
        )
        intervals.append(interval)
        if invariant:
            length = right.position_mm-left.position_mm
            regions.append(ExtrusionRegionCandidate(
                region_id=_stable_id("extrusion-region", interval.interval_id), frame_id=frame.frame_id,
                start_mm=left.position_mm, end_mm=right.position_mm, length_mm=length,
                section_id=left.signature.section_id,
                supporting_face_ids=(),  # Virtual section, not all source faces.
                source_coverage=min(1., length/span),
                unexplained_positive_volume_mm3=proof.source_minus_reconstruction_mm3,
                unexplained_negative_volume_mm3=proof.reconstruction_minus_source_mm3,
                score=1.,
            ))
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
            perimeter_residual_mm=None,
            moment_residual=None,
            radius_residual_mm=None,
            contour_distance_mm=None,
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
