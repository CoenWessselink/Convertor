from __future__ import annotations

from collections import Counter, defaultdict
import math
from typing import Any, Iterable

from .contracts import (
    AxisCandidate,
    CrossSectionSignature,
    EdgeEvidence,
    FaceEvidence,
    SourceTopologyEvidence,
    stable_id,
)


def _policy_value(policy: Any, names: tuple[str, ...], default: float) -> float:
    for name in names:
        value = getattr(policy, name, None)
        if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
            return float(value)
    return default


def linear_tolerance(policy: Any) -> float:
    return _policy_value(policy, ("linear_mm", "length_mm", "linear_tolerance_mm"), 0.05)


def relative_tolerance(policy: Any) -> float:
    return _policy_value(policy, ("relative", "relative_fraction", "relative_tolerance"), 0.001)


def angle_tolerance_degrees(policy: Any) -> float:
    return _policy_value(policy, ("angle_degrees", "angular_degrees", "angle_tolerance_deg"), 0.01)


def _p3(value: Any) -> tuple[float, float, float]:
    return (float(value.x), float(value.y), float(value.z))


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _mul(a: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return (a[0] * factor, a[1] * factor, a[2] * factor)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(a: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: tuple[float, float, float]) -> tuple[float, float, float]:
    length = _norm(a)
    if length <= 1e-15:
        return (0.0, 0.0, 0.0)
    result = (a[0] / length, a[1] / length, a[2] / length)
    for item in result:
        if abs(item) > 1e-12:
            if item < 0:
                result = (-result[0], -result[1], -result[2])
            break
    return result


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return _norm(_sub(a, b))


def _quantized(values: Iterable[float], step: float) -> tuple[float, ...]:
    return tuple(round(round(float(value) / step) * step, 9) for value in values)


def _normal(face: Any) -> tuple[float, float, float]:
    try:
        value = face.normalAt()
        if isinstance(value, tuple):
            value = value[0]
        return _unit(_p3(value))
    except Exception:
        return (0.0, 0.0, 0.0)


def _edge_payload(edge: Any, step: float) -> dict[str, Any]:
    start = _p3(edge.startPoint())
    end = _p3(edge.endPoint())
    if end < start:
        start, end = end, start
    try:
        tangent = _unit(_p3(edge.tangentAt()))
    except Exception:
        tangent = _unit(_sub(end, start))
    return {
        "curve_type": str(edge.geomType()).upper(),
        "length_mm": round(float(edge.Length()), 9),
        "start_mm": _quantized(start, step),
        "end_mm": _quantized(end, step),
        "tangent": _quantized(tangent, max(step / 1000.0, 1e-9)),
    }


def analyze_topology(shape: Any, policy: Any) -> tuple[SourceTopologyEvidence, tuple[AxisCandidate, ...]]:
    step = linear_tolerance(policy)
    edge_by_id: dict[str, EdgeEvidence] = {}
    edge_occurrences: dict[str, list[str]] = defaultdict(list)
    faces: list[FaceEvidence] = []
    all_points: list[tuple[float, float, float]] = []

    for face in shape.Faces():
        boundary_ids: list[str] = []
        for edge in face.Edges():
            payload = _edge_payload(edge, step)
            edge_id = stable_id("edge", payload)
            boundary_ids.append(edge_id)
            if edge_id not in edge_by_id:
                edge_by_id[edge_id] = EdgeEvidence(edge_id=edge_id, **payload)
                all_points.extend((payload["start_mm"], payload["end_mm"]))
        face_payload = {
            "surface_type": str(face.geomType()).upper(),
            "area_mm2": round(float(face.Area()), 9),
            "centroid_mm": _quantized(_p3(face.Center()), step),
            "normal": _quantized(_normal(face), max(step / 1000.0, 1e-9)),
            "boundary_edge_ids": tuple(sorted(boundary_ids)),
            "inner_wire_count": len(face.innerWires()),
        }
        face_id = stable_id("face", face_payload)
        evidence = FaceEvidence(face_id=face_id, **face_payload)
        faces.append(evidence)
        for edge_id in set(boundary_ids):
            edge_occurrences[edge_id].append(face_id)

    adjacency: list[tuple[str, str, str]] = []
    for edge_id, face_ids in edge_occurrences.items():
        unique = sorted(set(face_ids))
        for index, left in enumerate(unique):
            for right in unique[index + 1 :]:
                adjacency.append((left, right, edge_id))

    ordered_edges = tuple(sorted(edge_by_id.values(), key=lambda item: item.edge_id))
    ordered_faces = tuple(sorted(faces, key=lambda item: item.face_id))
    topology_payload = {
        "solid_count": len(shape.Solids()),
        "face_ids": [item.face_id for item in ordered_faces],
        "edge_ids": [item.edge_id for item in ordered_edges],
        "adjacency": sorted(adjacency),
    }
    topology = SourceTopologyEvidence(
        topology_id=stable_id("topology", topology_payload),
        solid_count=len(shape.Solids()),
        faces=ordered_faces,
        edges=ordered_edges,
        face_adjacency=tuple(sorted(adjacency)),
    )
    return topology, detect_axes(shape, topology, all_points, policy)


def detect_axes(
    shape: Any,
    topology: SourceTopologyEvidence,
    points: list[tuple[float, float, float]],
    policy: Any,
) -> tuple[AxisCandidate, ...]:
    direction_support: dict[tuple[float, float, float], float] = defaultdict(float)
    for edge in topology.edges:
        if edge.curve_type == "LINE":
            direction = _unit(_sub(edge.end_mm, edge.start_mm))
            if _norm(direction) > 0:
                key = _quantized(direction, 1e-6)
                direction_support[key] += edge.length_mm

    candidates: list[AxisCandidate] = []
    unique_points = sorted(set(points))
    for direction, support_length in direction_support.items():
        projections = [_dot(point, direction) for point in unique_points]
        if not projections:
            continue
        low = min(projections)
        high = max(projections)
        span = high - low
        if span <= linear_tolerance(policy):
            continue
        origin = min(unique_points, key=lambda point: (_dot(point, direction), point))
        end = _add(origin, _mul(direction, span))
        payload = {
            "direction": direction,
            "origin_mm": _quantized(origin, linear_tolerance(policy)),
            "end_mm": _quantized(end, linear_tolerance(policy)),
            "length_mm": round(span, 9),
            "support": "linear_edges",
        }
        candidates.append(
            AxisCandidate(
                axis_id=stable_id("axis", payload),
                score=round(span + support_length, 9),
                **payload,
            )
        )

    if not candidates:
        planar = [face for face in topology.faces if face.surface_type == "PLANE"]
        for index, left in enumerate(planar):
            for right in planar[index + 1 :]:
                if abs(_dot(left.normal, right.normal)) < 0.999999:
                    continue
                delta = _sub(right.centroid_mm, left.centroid_mm)
                length = _norm(delta)
                if length <= linear_tolerance(policy):
                    continue
                direction = _unit(delta)
                origin, end = left.centroid_mm, right.centroid_mm
                if _dot(_sub(end, origin), direction) < 0:
                    origin, end = end, origin
                payload = {
                    "direction": direction,
                    "origin_mm": origin,
                    "end_mm": end,
                    "length_mm": round(length, 9),
                    "support": "opposed_planar_faces",
                }
                candidates.append(
                    AxisCandidate(
                        axis_id=stable_id("axis", payload),
                        score=round(length, 9),
                        **payload,
                    )
                )

    candidates.sort(key=lambda item: (-item.length_mm, -item.score, item.axis_id))
    return tuple(candidates)


def find_end_faces(shape: Any, axis: AxisCandidate) -> tuple[Any, ...]:
    """Return every coplanar face forming the low end of an extrusion.

    STEP exporters commonly fragment an I/U/L section into multiple coplanar
    faces.  Selecting one face turns a whole profile into a flange or web and
    caused false FLAT/L classifications.  Selection remains conservative: only
    planar faces normal to the proven axis and on the same end plane qualify.
    """

    direction = axis.direction
    possible: list[tuple[float, Any]] = []
    for face in shape.Faces():
        if str(face.geomType()).upper() != "PLANE":
            continue
        normal = _normal(face)
        if abs(_dot(normal, direction)) >= 0.999999:
            possible.append((_dot(_p3(face.Center()), direction), face))
    if not possible:
        raise ValueError("Geen planair eindvlak loodrecht op de kandidaat-as gevonden")
    low = min(item[0] for item in possible)
    plane_tolerance = max(1e-7, min(0.05, abs(float(axis.length_mm)) * 1e-8))
    faces = [face for projection, face in possible if abs(projection - low) <= plane_tolerance]
    faces.sort(
        key=lambda face: (
            -round(float(face.Area()), 9),
            _quantized(_p3(face.Center()), plane_tolerance),
        )
    )
    return tuple(faces)


def find_end_face(shape: Any, axis: AxisCandidate) -> Any:
    """Backward-compatible primary end face; aggregate users use find_end_faces."""

    return find_end_faces(shape, axis)[0]


def _edge_identity(edge: Any, step: float) -> tuple[Any, ...]:
    start = _quantized(_p3(edge.startPoint()), step)
    end = _quantized(_p3(edge.endPoint()), step)
    if end < start:
        start, end = end, start
    # Opposed circular arcs may share endpoints and length, but are not seams.
    # Their geometric centres distinguish them while remaining independent of
    # the edge's orientation along the wire.
    centre = _quantized(_p3(edge.Center()), step)
    return (
        str(edge.geomType()).upper(),
        start,
        end,
        centre,
        round(float(edge.Length()), 7),
    )


def section_signature(face: Any, axis: AxisCandidate, topology: SourceTopologyEvidence) -> CrossSectionSignature:
    faces = tuple(face) if isinstance(face, (list, tuple)) else (face,)
    if not faces:
        raise ValueError("Doorsnede bevat geen eindvlakken")
    step = max(1e-7, min(0.01, abs(float(axis.length_mm)) * 1e-9))
    outer_occurrences: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
    inner_edges: list[Any] = []
    inner_count = 0
    for item in faces:
        for edge in item.outerWire().Edges():
            outer_occurrences[_edge_identity(edge, step)].append(edge)
        wires = list(item.innerWires())
        inner_count += len(wires)
        for wire in wires:
            inner_edges.extend(wire.Edges())

    # Shared seams occur twice and are not part of the material boundary.
    outer_edges = [
        values[0]
        for _, values in sorted(outer_occurrences.items(), key=lambda item: repr(item[0]))
        if len(values) % 2 == 1
    ]
    if not outer_edges:
        outer_edges = [values[0] for values in outer_occurrences.values()]
    edge_types = Counter(str(edge.geomType()).upper() for edge in (*outer_edges, *inner_edges))

    linear_vectors: list[tuple[float, tuple[float, float, float]]] = []
    points: list[tuple[float, float, float]] = []
    for edge in (*outer_edges, *inner_edges):
        start, end = _p3(edge.startPoint()), _p3(edge.endPoint())
        points.extend((start, end))
        vector = _sub(end, start)
        if str(edge.geomType()).upper() == "LINE" and _norm(vector) > 1e-9:
            linear_vectors.append((_norm(vector), _unit(vector)))

    normal = axis.direction
    if linear_vectors:
        u = max(linear_vectors, key=lambda item: item[0])[1]
        u = _unit(_sub(u, _mul(normal, _dot(u, normal))))
    else:
        helper = (1.0, 0.0, 0.0) if abs(normal[0]) < 0.9 else (0.0, 1.0, 0.0)
        u = _unit(_cross(normal, helper))
    v = _unit(_cross(normal, u))
    circle_radii = [
        abs(float(edge.radius()))
        for edge in outer_edges
        if str(edge.geomType()).upper() == "CIRCLE" and hasattr(edge, "radius")
    ]
    if len(outer_edges) == 1 and circle_radii:
        width = height = 2.0 * max(circle_radii)
    elif points:
        pu = [_dot(point, u) for point in points]
        pv = [_dot(point, v) for point in points]
        width = max(pu) - min(pu)
        height = max(pv) - min(pv)
    else:
        projected: list[tuple[float, float]] = []
        for item in faces:
            box = item.BoundingBox()
            for x in (float(box.xmin), float(box.xmax)):
                for y in (float(box.ymin), float(box.ymax)):
                    for z in (float(box.zmin), float(box.zmax)):
                        point = (x, y, z)
                        projected.append((_dot(point, u), _dot(point, v)))
        width = max(value[0] for value in projected) - min(value[0] for value in projected)
        height = max(value[1] for value in projected) - min(value[1] for value in projected)

    outer_types = Counter(str(edge.geomType()).upper() for edge in outer_edges)
    outer_is_circle = bool(
        len(outer_edges) == 1
        and outer_types.get("CIRCLE", 0) == 1
    )
    line_directions = []
    for edge in outer_edges:
        if str(edge.geomType()).upper() != "LINE":
            continue
        direction = _unit(_sub(_p3(edge.endPoint()), _p3(edge.startPoint())))
        line_directions.append((abs(_dot(direction, u)), abs(_dot(direction, v))))
    orthogonal = bool(line_directions) and all(max(first, second) >= 0.99999 for first, second in line_directions)
    if outer_is_circle and inner_count:
        family = "RO"
    elif outer_is_circle:
        family = "RU"
    elif inner_count:
        family = "M"
    elif len(outer_edges) == 4 and orthogonal:
        family = "B"
    elif len(outer_edges) == 6 and orthogonal:
        family = "L"
    elif len(outer_edges) == 8 and orthogonal:
        family = "U"
    elif len(outer_edges) == 12 and orthogonal:
        family = "I"
    else:
        family = "CUSTOM"

    matching_ids = tuple(
        sorted(
            {
                min(
                    topology.faces,
                    key=lambda evidence: _distance(
                        evidence.centroid_mm, _p3(item.Center())
                    ),
                ).face_id
                for item in faces
            }
        )
    )
    payload = {
        "face_id": matching_ids[0] if len(matching_ids) == 1 else stable_id("section-face", matching_ids),
        "area_mm2": round(sum(float(item.Area()) for item in faces), 9),
        "perimeter_mm": round(sum(float(edge.Length()) for edge in (*outer_edges, *inner_edges)), 9),
        "width_mm": round(max(width, height), 9),
        "height_mm": round(min(width, height), 9),
        "outer_edge_count": len(outer_edges),
        "inner_wire_count": inner_count,
        "edge_type_counts": tuple(sorted(edge_types.items())),
        "inferred_family": family,
        "supporting_face_ids": matching_ids,
        "component_count": len(faces),
    }
    return CrossSectionSignature(section_id=stable_id("section", payload), **payload)
