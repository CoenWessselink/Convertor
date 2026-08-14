"""Exact STEP/BREP loading and deterministic subshape cataloguing."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

from cws_viewer.math3d import BoundingBox, Vector3

from .model import (
    ExactPartRuntime,
    ExactPartSnapshot,
    ExactShapeProperties,
    ExactnessLevel,
    FeatureDescriptor,
    ProductionFrame,
    ReferenceFace,
    SubshapeDescriptor,
    SubshapeKind,
    WorkbenchStatus,
)

_ROUND_DIGITS = 7


def _cq():
    try:
        import cadquery as cq
        return cq
    except Exception as exc:  # pragma: no cover - packaged runtime gate
        raise RuntimeError(f"CadQuery/OCP exact geometry runtime ontbreekt: {exc}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _round(value: float) -> float:
    result = round(float(value), _ROUND_DIGITS)
    return 0.0 if abs(result) < 10 ** (-_ROUND_DIGITS) else result


def _vec(value: Any) -> Vector3:
    return Vector3(float(value.x), float(value.y), float(value.z))


def _vec_key(value: Vector3 | None):
    return None if value is None else (_round(value.x), _round(value.y), _round(value.z))


def _bbox(shape: Any) -> BoundingBox:
    box = shape.BoundingBox()
    return BoundingBox(
        Vector3(float(box.xmin), float(box.ymin), float(box.zmin)),
        Vector3(float(box.xmax), float(box.ymax), float(box.zmax)),
    )


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _positive_axis(vector: Vector3) -> Vector3:
    unit = vector.normalized()
    components = (unit.x, unit.y, unit.z)
    index = max(range(3), key=lambda i: abs(components[i]))
    return -unit if components[index] < 0 else unit


def _surface_details(face: Any) -> tuple[str, Vector3 | None, float | None, Vector3 | None, Vector3 | None]:
    """Return geom type, normal, radius, axis origin and axis direction."""
    geom_type = str(face.geomType()).upper()
    normal: Vector3 | None = None
    radius: float | None = None
    axis_origin: Vector3 | None = None
    axis_direction: Vector3 | None = None
    try:
        normal = _vec(face.normalAt())
    except Exception:
        pass
    try:
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Plane

        adaptor = BRepAdaptor_Surface(face.wrapped, True)
        surface_type = adaptor.GetType()
        if surface_type == GeomAbs_Cylinder:
            cylinder = adaptor.Cylinder()
            geom_type = "CYLINDER"
            radius = float(cylinder.Radius())
            point = cylinder.Location()
            direction = cylinder.Axis().Direction()
            axis_origin = Vector3(point.X(), point.Y(), point.Z())
            axis_direction = Vector3(direction.X(), direction.Y(), direction.Z()).normalized()
        elif surface_type == GeomAbs_Plane:
            geom_type = "PLANE"
            plane = adaptor.Plane()
            direction = plane.Axis().Direction()
            axis_origin = Vector3(plane.Location().X(), plane.Location().Y(), plane.Location().Z())
            axis_direction = Vector3(direction.X(), direction.Y(), direction.Z()).normalized()
        elif surface_type == GeomAbs_Cone:
            cone = adaptor.Cone()
            geom_type = "CONE"
            radius = float(cone.RefRadius())
            point = cone.Location()
            direction = cone.Axis().Direction()
            axis_origin = Vector3(point.X(), point.Y(), point.Z())
            axis_direction = Vector3(direction.X(), direction.Y(), direction.Z()).normalized()
    except Exception:
        pass
    return geom_type, normal, radius, axis_origin, axis_direction


def _curve_details(edge: Any) -> tuple[str, Vector3 | None, Vector3 | None, Vector3 | None, float | None, Vector3 | None, Vector3 | None]:
    geom_type = str(edge.geomType()).upper()
    start: Vector3 | None = None
    end: Vector3 | None = None
    direction: Vector3 | None = None
    radius: float | None = None
    center: Vector3 | None = None
    axis_direction: Vector3 | None = None
    try:
        start = _vec(edge.startPoint())
        end = _vec(edge.endPoint())
    except Exception:
        pass
    if geom_type == "LINE" and start is not None and end is not None:
        delta = end - start
        if delta.length() > 1e-12:
            direction = _positive_axis(delta)
    if geom_type in {"CIRCLE", "ARC"}:
        try:
            radius = float(edge.radius())
            center = _vec(edge.arcCenter())
        except Exception:
            pass
        try:
            from OCP.BRepAdaptor import BRepAdaptor_Curve
            from OCP.GeomAbs import GeomAbs_Circle
            adaptor = BRepAdaptor_Curve(edge.wrapped)
            if adaptor.GetType() == GeomAbs_Circle:
                axis = adaptor.Circle().Axis().Direction()
                axis_direction = Vector3(axis.X(), axis.Y(), axis.Z()).normalized()
        except Exception:
            pass
    return geom_type, start, end, direction, radius, center, axis_direction


def _vertex_signature(vertex: Any) -> tuple[dict[str, Any], Vector3, BoundingBox]:
    point = _vec(vertex.Center())
    bounds = _bbox(vertex)
    payload = {"kind": "vertex", "point": _vec_key(point)}
    return payload, point, bounds


def _edge_signature(edge: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    geom_type, start, end, direction, radius, center, axis_direction = _curve_details(edge)
    if geom_type == "CIRCLE" and radius is not None:
        circumference = 2.0 * math.pi * radius
        if float(edge.Length()) < circumference - max(1e-7, circumference * 1e-7):
            geom_type = "ARC"
    bounds = _bbox(edge)
    if start is not None and end is not None and _vec_key(start) > _vec_key(end):
        start, end = end, start
    payload = {
        "kind": "edge",
        "geometry_type": geom_type,
        "length": _round(edge.Length()),
        "center": _vec_key(_vec(edge.Center())),
        "bounds_min": _vec_key(bounds.minimum),
        "bounds_max": _vec_key(bounds.maximum),
        "start": _vec_key(start),
        "end": _vec_key(end),
        "radius": None if radius is None else _round(radius),
        "arc_center": _vec_key(center),
        "axis_direction": _vec_key(axis_direction),
    }
    extra = {
        "geom_type": geom_type,
        "start": start,
        "end": end,
        "direction": direction,
        "radius": radius,
        "arc_center": center,
        "axis_direction": axis_direction,
        "bounds": bounds,
    }
    return payload, extra


def _face_signature(face: Any, edge_signature_hashes: Iterable[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    geom_type, normal, radius, axis_origin, axis_direction = _surface_details(face)
    center = _vec(face.Center())
    bounds = _bbox(face)
    payload = {
        "kind": "face",
        "geometry_type": geom_type,
        "area": _round(face.Area()),
        "center": _vec_key(center),
        "bounds_min": _vec_key(bounds.minimum),
        "bounds_max": _vec_key(bounds.maximum),
        "normal": _vec_key(normal),
        "radius": None if radius is None else _round(radius),
        "axis_origin": _vec_key(axis_origin),
        "axis_direction": _vec_key(axis_direction),
        "edge_signatures": sorted(edge_signature_hashes),
    }
    extra = {
        "geom_type": geom_type,
        "normal": normal,
        "radius": radius,
        "axis_origin": axis_origin,
        "axis_direction": axis_direction,
        "center": center,
        "bounds": bounds,
    }
    return payload, extra


def _assign_ids(kind: SubshapeKind, entries: list[dict[str, Any]]) -> None:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        groups[entry["signature_hash"]].append(entry)
    for signature in sorted(groups):
        group = groups[signature]
        group.sort(key=lambda item: item["sort_key"])
        for ordinal, entry in enumerate(group, start=1):
            suffix = "" if len(group) == 1 else f"-{ordinal:02d}"
            entry["stable_id"] = f"{kind.value}-{signature[:16]}{suffix}"
            entry["ordinal"] = ordinal


def shape_properties(shape: Any) -> ExactShapeProperties:
    bounds = _bbox(shape)
    return ExactShapeProperties(
        volume_mm3=float(shape.Volume()),
        surface_area_mm2=float(shape.Area()),
        center_of_mass=_vec(shape.Center()),
        bounds=bounds,
        solid_count=len(shape.Solids()),
        face_count=len(shape.Faces()),
        edge_count=len(shape.Edges()),
        vertex_count=len(shape.Vertices()),
        valid=bool(shape.isValid()),
    )


def build_subshape_catalog(shape: Any) -> tuple[tuple[SubshapeDescriptor, ...], dict[str, Any], str]:
    vertices_raw: list[dict[str, Any]] = []
    for vertex in shape.Vertices():
        payload, center, bounds = _vertex_signature(vertex)
        signature = _stable_hash(payload)
        vertices_raw.append({
            "shape": vertex,
            "signature_hash": signature,
            "sort_key": (payload["point"], signature),
            "center": center,
            "bounds": bounds,
            "payload": payload,
        })
    _assign_ids(SubshapeKind.VERTEX, vertices_raw)

    edges_raw: list[dict[str, Any]] = []
    for edge in shape.Edges():
        payload, extra = _edge_signature(edge)
        signature = _stable_hash(payload)
        edges_raw.append({
            "shape": edge,
            "signature_hash": signature,
            "sort_key": (payload["center"], payload["length"], signature),
            "payload": payload,
            **extra,
        })
    _assign_ids(SubshapeKind.EDGE, edges_raw)

    def matching_ids(children: Iterable[Any], entries: list[dict[str, Any]]) -> tuple[str, ...]:
        result: list[str] = []
        for child in children:
            for entry in entries:
                try:
                    if child.isSame(entry["shape"]):
                        result.append(entry["stable_id"])
                        break
                except Exception:
                    continue
        return tuple(sorted(dict.fromkeys(result)))

    faces_raw: list[dict[str, Any]] = []
    for face in shape.Faces():
        edge_ids = matching_ids(face.Edges(), edges_raw)
        try:
            outer_edge_ids = matching_ids(face.outerWire().Edges(), edges_raw)
            inner_wires = tuple(face.innerWires())
            inner_edge_ids = tuple(matching_ids(wire.Edges(), edges_raw) for wire in inner_wires)
        except Exception:
            outer_edge_ids = edge_ids
            inner_edge_ids = ()
        edge_hashes = [entry["signature_hash"] for entry in edges_raw if entry["stable_id"] in edge_ids]
        payload, extra = _face_signature(face, edge_hashes)
        signature = _stable_hash(payload)
        faces_raw.append({
            "shape": face,
            "signature_hash": signature,
            "sort_key": (payload["center"], payload["area"], signature),
            "payload": payload,
            "edge_ids": edge_ids,
            "outer_edge_ids": outer_edge_ids,
            "inner_edge_ids": inner_edge_ids,
            **extra,
        })
    _assign_ids(SubshapeKind.FACE, faces_raw)

    descriptors: list[SubshapeDescriptor] = []
    shape_map: dict[str, Any] = {}

    for entry in vertices_raw:
        descriptor = SubshapeDescriptor(
            stable_id=entry["stable_id"], kind=SubshapeKind.VERTEX,
            geometry_type="POINT", signature_hash=entry["signature_hash"],
            center=entry["center"], bounds=entry["bounds"], measure=0.0,
            ordinal=entry["ordinal"],
        )
        descriptors.append(descriptor); shape_map[descriptor.stable_id] = entry["shape"]

    for entry in edges_raw:
        descriptor = SubshapeDescriptor(
            stable_id=entry["stable_id"], kind=SubshapeKind.EDGE,
            geometry_type=entry["geom_type"], signature_hash=entry["signature_hash"],
            center=_vec(entry["shape"].Center()), bounds=entry["bounds"],
            measure=float(entry["shape"].Length()), ordinal=entry["ordinal"],
            direction=entry["direction"], start=entry["start"], end=entry["end"],
            radius=entry["radius"], axis_origin=entry["arc_center"],
            axis_direction=entry["axis_direction"], parent_ids=(),
        )
        descriptors.append(descriptor); shape_map[descriptor.stable_id] = entry["shape"]

    for entry in faces_raw:
        descriptor = SubshapeDescriptor(
            stable_id=entry["stable_id"], kind=SubshapeKind.FACE,
            geometry_type=entry["geom_type"], signature_hash=entry["signature_hash"],
            center=entry["center"], bounds=entry["bounds"],
            measure=float(entry["shape"].Area()), ordinal=entry["ordinal"],
            normal=entry["normal"], radius=entry["radius"],
            axis_origin=entry["axis_origin"], axis_direction=entry["axis_direction"],
            parent_ids=entry["edge_ids"],
            metadata=(
                ("outer_edge_ids", ";".join(entry.get("outer_edge_ids", ()))),
                ("inner_wire_count", str(len(entry.get("inner_edge_ids", ())))),
            ),
        )
        descriptors.append(descriptor); shape_map[descriptor.stable_id] = entry["shape"]

    descriptors.sort(key=lambda item: (item.kind.value, item.stable_id))
    geometry_hash = _stable_hash({
        "schema": "cws-exact-geometry-v1",
        "properties": shape_properties(shape).to_dict(),
        "subshape_signatures": sorted(item.signature_hash for item in descriptors),
    })
    return tuple(descriptors), shape_map, geometry_hash


def _bbox_projection(bounds: BoundingBox, direction: Vector3) -> float:
    values = [corner.dot(direction) for corner in bounds.corners()]
    return max(values) - min(values)


def derive_production_frame(properties: ExactShapeProperties, subshapes: Iterable[SubshapeDescriptor]) -> ProductionFrame:
    descriptors = tuple(subshapes)
    faces = [item for item in descriptors if item.kind == SubshapeKind.FACE and item.geometry_type == "PLANE" and item.normal]
    edges = [item for item in descriptors if item.kind == SubshapeKind.EDGE and item.geometry_type == "LINE" and item.direction]
    cylinders = [item for item in descriptors if item.kind == SubshapeKind.FACE and item.geometry_type == "CYLINDER" and item.axis_direction]

    size = properties.bounds.size
    global_axes = ((size.x, Vector3(1, 0, 0)), (size.y, Vector3(0, 1, 0)), (size.z, Vector3(0, 0, 1)))
    longest_dimension = max(value for value, _ in global_axes)

    # Manufacturing X follows the member/plate length. Prefer a truly long
    # analytical line, then an outer cylinder axis, then the longest bbox axis.
    long_edges = [item for item in edges if item.measure >= longest_dimension * 0.75]
    if long_edges:
        x_axis = _positive_axis(max(long_edges, key=lambda item: (item.measure, item.stable_id)).direction or Vector3(1, 0, 0))
    else:
        outer_cylinders = [
            item for item in cylinders
            if item.axis_direction and _bbox_projection(item.bounds, item.axis_direction) >= longest_dimension * 0.75
        ]
        if outer_cylinders:
            x_axis = _positive_axis(max(outer_cylinders, key=lambda item: item.measure).axis_direction or Vector3(1, 0, 0))
        else:
            x_axis = _positive_axis(max(global_axes, key=lambda item: item[0])[1])

    # Z is the most informative planar normal orthogonal to length. For round
    # parts, fall back to the global axis with the strongest +Z preference.
    z_candidates = [item for item in faces if item.normal and abs(item.normal.dot(x_axis)) < 0.2]
    if z_candidates:
        z_axis = _positive_axis(max(z_candidates, key=lambda item: (item.measure, abs((item.normal or Vector3.zero()).z), item.stable_id)).normal or Vector3(0, 0, 1))
    else:
        orthogonal_globals = [axis for _, axis in global_axes if abs(axis.dot(x_axis)) < 0.2]
        z_axis = max(orthogonal_globals, key=lambda axis: (abs(axis.z), abs(axis.y), abs(axis.x)))
        z_axis = _positive_axis(z_axis)

    y_axis = z_axis.cross(x_axis).normalized()
    z_axis = x_axis.cross(y_axis).normalized()
    return ProductionFrame(
        origin=properties.bounds.minimum,
        x_axis=x_axis,
        y_axis=y_axis,
        z_axis=z_axis,
        source="automatic_brep",
        confirmed=False,
    )


def derive_reference_faces(frame: ProductionFrame, subshapes: Iterable[SubshapeDescriptor]) -> tuple[ReferenceFace, ...]:
    faces = [item for item in subshapes if item.kind == SubshapeKind.FACE and item.geometry_type == "PLANE" and item.normal]
    roles = {
        "top": frame.z_axis,
        "bottom": -frame.z_axis,
        "end": frame.x_axis,
        "start": -frame.x_axis,
        "right": frame.y_axis,
        "left": -frame.y_axis,
    }
    result: list[ReferenceFace] = []
    used: set[str] = set()
    for role, direction in roles.items():
        candidates = [item for item in faces if item.stable_id not in used]
        if not candidates:
            break
        best = max(candidates, key=lambda item: ((item.normal or Vector3.zero()).dot(direction), item.measure))
        if (best.normal or Vector3.zero()).dot(direction) < 0.7:
            continue
        used.add(best.stable_id)
        result.append(ReferenceFace(role=role, face_id=best.stable_id, normal=best.normal or direction))
    return tuple(result)


def recognize_features(
    properties: ExactShapeProperties,
    frame: ProductionFrame,
    subshapes: Iterable[SubshapeDescriptor],
) -> tuple[FeatureDescriptor, ...]:
    descriptors = tuple(subshapes)
    faces = [item for item in descriptors if item.kind == SubshapeKind.FACE]
    edges = [item for item in descriptors if item.kind == SubshapeKind.EDGE]
    features: list[FeatureDescriptor] = []
    size = properties.bounds.size
    dims = sorted((size.x, size.y, size.z))
    smallest, middle, largest = dims

    cylinders = [
        item for item in faces
        if item.geometry_type == "CYLINDER" and item.radius and item.axis_direction
    ]

    # A through slot in an extruded plate is represented by two half-cylinder
    # faces plus two planar side faces.  Their cylindrical face areas each
    # correspond to half the full cylinder area.  Group those exact analytical
    # faces into one slot feature instead of misreporting two blind pockets.
    used_cylinders: set[str] = set()
    half_cylinders: list[tuple[SubshapeDescriptor, float]] = []
    for face in cylinders:
        assert face.radius is not None
        equivalent_depth = face.measure / (2.0 * math.pi * face.radius)
        if abs(equivalent_depth - smallest * 0.5) <= max(0.05, smallest * 0.02):
            half_cylinders.append((face, equivalent_depth))
    for index, (first, _) in enumerate(half_cylinders):
        if first.stable_id in used_cylinders or first.axis_origin is None:
            continue
        for second, _ in half_cylinders[index + 1:]:
            if second.stable_id in used_cylinders or second.axis_origin is None:
                continue
            if first.radius is None or second.radius is None:
                continue
            if abs(first.radius - second.radius) > max(0.01, first.radius * 1e-4):
                continue
            first_axis = (first.axis_direction or frame.z_axis).normalized()
            second_axis = (second.axis_direction or frame.z_axis).normalized()
            if abs(abs(first_axis.dot(second_axis)) - 1.0) > 1e-5:
                continue
            center_distance = (first.axis_origin - second.axis_origin).length()
            if center_distance <= 1e-6:
                continue
            center = (first.axis_origin + second.axis_origin) * 0.5
            total_length = center_distance + 2.0 * first.radius
            feature_hash = _stable_hash({
                "kind": "through_slot",
                "faces": sorted((first.signature_hash, second.signature_hash)),
                "length": _round(total_length),
                "width": _round(first.radius * 2.0),
                "depth": _round(smallest),
            })
            features.append(FeatureDescriptor(
                feature_id=f"feature-through-slot-{feature_hash[:16]}",
                feature_type="through_slot",
                subshape_ids=tuple(sorted((first.stable_id, second.stable_id))),
                center=center,
                evidence=ExactnessLevel.ANALYTICAL_FEATURE,
                axis=_positive_axis(first_axis),
                radius=first.radius,
                diameter=first.radius * 2.0,
                depth=smallest,
                confidence=1.0,
                metadata=(
                    ("slot_length_mm", str(_round(total_length))),
                    ("slot_width_mm", str(_round(first.radius * 2.0))),
                    ("end_center_distance_mm", str(_round(center_distance))),
                ),
            ))
            used_cylinders.update((first.stable_id, second.stable_id))
            break

    for face in cylinders:
        if face.stable_id in used_cylinders:
            continue
        assert face.radius is not None and face.axis_direction is not None
        # Cylinder face area is 2*pi*r*depth and remains reliable for rotated
        # holes, unlike projecting an axis-aligned bounding box.
        depth = face.measure / (2.0 * math.pi * face.radius)
        # Quarter-cylinder surfaces are convex contour fillets/radii, not
        # internal pockets. Their analytical radius is already represented by
        # the top/bottom contour edges below.
        if depth < smallest * 0.45:
            continue
        outer_profile = (
            abs(face.radius * 2.0 - smallest) <= max(0.05, smallest * 0.01)
            and abs(face.radius * 2.0 - middle) <= max(0.05, middle * 0.01)
            and depth >= largest * 0.95
        )
        if outer_profile:
            feature_type = "round_profile"
        else:
            feature_type = "through_hole" if depth >= smallest * 0.8 else "cylindrical_pocket"
        features.append(FeatureDescriptor(
            feature_id=f"feature-{feature_type}-{face.signature_hash[:16]}",
            feature_type=feature_type,
            subshape_ids=(face.stable_id,),
            center=face.center,
            evidence=ExactnessLevel.ANALYTICAL_FEATURE,
            axis=_positive_axis(face.axis_direction),
            radius=face.radius,
            diameter=face.radius * 2.0,
            depth=depth,
            confidence=1.0,
        ))

    planar_faces = [item for item in faces if item.geometry_type == "PLANE"]
    if planar_faces:
        top = max(planar_faces, key=lambda item: (item.measure, item.stable_id))
        outer_ids = {
            value for value in top.metadata_dict.get("outer_edge_ids", "").split(";") if value
        } or set(top.parent_ids)
        contour_edges = [
            edge for edge in edges
            if edge.stable_id in outer_ids and edge.geometry_type in {"LINE", "CIRCLE", "ARC"}
        ]
        if contour_edges:
            circular_count = sum(item.geometry_type in {"CIRCLE", "ARC"} for item in contour_edges)
            features.append(FeatureDescriptor(
                feature_id=f"feature-outer-contour-{top.signature_hash[:16]}",
                feature_type="outer_contour",
                subshape_ids=tuple(sorted(item.stable_id for item in contour_edges if item.geometry_type != "CIRCLE")),
                center=top.center,
                evidence=ExactnessLevel.SOURCE_BREP,
                axis=frame.z_axis,
                confidence=1.0,
                metadata=(
                    ("reference_face", top.stable_id),
                    ("analytical_curve_count", str(circular_count)),
                ),
            ))
            if circular_count:
                features.append(FeatureDescriptor(
                    feature_id=f"feature-contour-radii-{top.signature_hash[:16]}",
                    feature_type="contour_radii",
                    subshape_ids=tuple(sorted(item.stable_id for item in contour_edges if item.geometry_type in {"CIRCLE", "ARC"})),
                    center=top.center,
                    evidence=ExactnessLevel.ANALYTICAL_FEATURE,
                    axis=frame.z_axis,
                    confidence=1.0,
                    metadata=(("curve_count", str(circular_count)),),
                ))
    features.sort(key=lambda item: item.feature_id)
    return tuple(features)


def load_step_exact(path: str | Path, *, part_id: str | None = None) -> ExactPartRuntime:
    source = Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    cq = _cq()
    workplane = cq.importers.importStep(str(source))
    values = workplane.vals()
    if len(values) != 1:
        raise ValueError(f"Exact Part Workbench verwacht één STEP-shape, gevonden: {len(values)}")
    shape = values[0]
    if shape.ShapeType() not in {"Solid", "Compound", "CompSolid"}:
        raise ValueError(f"Niet-ondersteund STEP-shapetype: {shape.ShapeType()}")
    properties = shape_properties(shape)
    subshapes, shape_map, geometry_hash = build_subshape_catalog(shape)
    frame = derive_production_frame(properties, subshapes)
    references = derive_reference_faces(frame, subshapes)
    features = recognize_features(properties, frame, subshapes)
    questions: list[str] = []
    if not properties.valid:
        questions.append("Bron-BREP is niet geldig volgens OCCT")
    if properties.solid_count != 1:
        questions.append(
            f"Bron bevat {properties.solid_count} solids; opsplitsen/samenvoegen moet expliciet worden beoordeeld"
        )
    if not references:
        questions.append("Referentiezijden konden niet automatisch worden bepaald")
    status = (
        WorkbenchStatus.GEOMETRY_VALIDATED
        if properties.valid and properties.solid_count == 1 and references
        else WorkbenchStatus.REVIEW_REQUIRED
    )
    snapshot = ExactPartSnapshot(
        part_id=part_id or source.stem,
        source_name=source.name,
        source_sha256=_sha256_file(source),
        exact_geometry_hash=geometry_hash,
        properties=properties,
        subshapes=subshapes,
        features=features,
        production_frame=frame,
        reference_faces=references,
        unresolved_questions=tuple(questions),
        status=status,
    )
    return ExactPartRuntime(snapshot=snapshot, shape=shape, shape_by_subshape_id=shape_map)


def build_exact_runtime(shape: Any, *, part_id: str, source_name: str = "generated") -> ExactPartRuntime:
    properties = shape_properties(shape)
    subshapes, shape_map, geometry_hash = build_subshape_catalog(shape)
    frame = derive_production_frame(properties, subshapes)
    references = derive_reference_faces(frame, subshapes)
    features = recognize_features(properties, frame, subshapes)
    source_sha = _stable_hash({"source_name": source_name, "geometry_hash": geometry_hash})
    questions = () if properties.solid_count == 1 else (
        f"Bron bevat {properties.solid_count} solids; handmatige productgrensbevestiging vereist",
    )
    snapshot = ExactPartSnapshot(
        part_id=part_id,
        source_name=source_name,
        source_sha256=source_sha,
        exact_geometry_hash=geometry_hash,
        properties=properties,
        subshapes=subshapes,
        features=features,
        production_frame=frame,
        reference_faces=references,
        unresolved_questions=questions,
        status=(
            WorkbenchStatus.GEOMETRY_VALIDATED
            if properties.valid and properties.solid_count == 1
            else WorkbenchStatus.REVIEW_REQUIRED
        ),
    )
    return ExactPartRuntime(snapshot=snapshot, shape=shape, shape_by_subshape_id=shape_map)


__all__ = [
    "shape_properties",
    "build_subshape_catalog",
    "derive_production_frame",
    "derive_reference_faces",
    "recognize_features",
    "load_step_exact",
    "build_exact_runtime",
]
