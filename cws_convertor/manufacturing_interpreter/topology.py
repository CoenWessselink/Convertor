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
        if isinstance(value, (int, float)) and value > 0:
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


def find_end_face(shape: Any, axis: AxisCandidate) -> Any:
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
    return min(possible, key=lambda item: item[0])[1]


def section_signature(face: Any, axis: AxisCandidate, topology: SourceTopologyEvidence) -> CrossSectionSignature:
    outer_edges = list(face.outerWire().Edges())
    edge_types = Counter(str(edge.geomType()).upper() for edge in outer_edges)
    for wire in face.innerWires():
        edge_types.update(str(edge.geomType()).upper() for edge in wire.Edges())

    linear_vectors: list[tuple[float, tuple[float, float, float]]] = []
    points: list[tuple[float, float, float]] = []
    for edge in outer_edges:
        start, end = _p3(edge.startPoint()), _p3(edge.endPoint())
        points.extend((start, end))
        vector = _sub(end, start)
        if _norm(vector) > 1e-9:
            linear_vectors.append((_norm(vector), _unit(vector)))

    normal = axis.direction
    if linear_vectors:
        u = max(linear_vectors, key=lambda item: item[0])[1]
        u = _unit(_sub(u, _mul(normal, _dot(u, normal))))
    else:
        helper = (1.0, 0.0, 0.0) if abs(normal[0]) < 0.9 else (0.0, 1.0, 0.0)
        u = _unit(_cross(normal, helper))
    v = _unit(_cross(normal, u))
    if points:
        pu = [_dot(point, u) for point in points]
        pv = [_dot(point, v) for point in points]
        width = max(pu) - min(pu)
        height = max(pv) - min(pv)
    else:
        box = face.BoundingBox()
        dimensions = sorted((float(box.xlen), float(box.ylen), float(box.zlen)), reverse=True)
        width, height = dimensions[:2]

    circular = edge_types.get("CIRCLE", 0) + edge_types.get("ELLIPSE", 0)
    inner_count = len(face.innerWires())
    if circular and inner_count:
        family = "RO"
    elif circular:
        family = "RU"
    elif inner_count:
        family = "M"
    elif len(outer_edges) <= 4:
        family = "B"
    elif len(outer_edges) == 6:
        family = "L"
    elif len(outer_edges) <= 9:
        family = "U"
    elif len(outer_edges) >= 10:
        family = "I"
    else:
        family = "CUSTOM"

    face_center = _p3(face.Center())
    matching = min(
        topology.faces,
        key=lambda item: _distance(item.centroid_mm, face_center),
    )
    payload = {
        "face_id": matching.face_id,
        "area_mm2": round(float(face.Area()), 9),
        "perimeter_mm": round(sum(float(edge.Length()) for edge in outer_edges), 9),
        "width_mm": round(max(width, height), 9),
        "height_mm": round(min(width, height), 9),
        "outer_edge_count": len(outer_edges),
        "inner_wire_count": inner_count,
        "edge_type_counts": tuple(sorted(edge_types.items())),
        "inferred_family": family,
    }
    return CrossSectionSignature(section_id=stable_id("section", payload), **payload)

