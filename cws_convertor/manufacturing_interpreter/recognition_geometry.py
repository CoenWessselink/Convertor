"""Native geometric evidence used by the existing interpreter; no grade inference.

Reference sections and analytic cutters remain hypotheses until the independent
bidirectional BREP validator proves the selected reconstruction.
"""
from __future__ import annotations

from typing import Any
import math


def reference_section_faces(shape: Any, axis: Any) -> tuple[Any, ...]:
    """Choose the fuller of the two transverse end planes, including seams.

    A cope at the first end is not the original profile. Looking at both ends
    avoids reconstructing that cope as material added along the whole member.
    Only end-plane faces are considered, never an interior boss end face.
    """
    from .topology import _dot, _normal, _p3, find_end_faces
    try:
        shape = shape.clean()
    except Exception:
        pass
    direction = axis.direction
    projections = [_dot(_p3(v.Center()), direction) for v in shape.Vertices()]
    if not projections:
        return find_end_faces(shape, axis)
    lower, upper = min(projections), max(projections)
    tol = max(1e-6, abs(float(axis.length_mm)) * 1e-8)
    ends: list[list[Any]] = [[], []]
    for face in shape.Faces():
        if str(face.geomType()).upper() != 'PLANE' or abs(_dot(_normal(face), direction)) < 0.999999:
            continue
        station = _dot(_p3(face.Center()), direction)
        for number, boundary in enumerate((lower, upper)):
            if abs(station - boundary) <= tol:
                ends[number].append(face)
    candidates = [group for group in ends if group]
    if not candidates:
        return find_end_faces(shape, axis)
    group = max(candidates, key=lambda faces: round(sum(float(f.Area()) for f in faces), 6))
    return tuple(sorted(group, key=lambda f: (-round(float(f.Area()), 7), _p3(f.Center()))))


def planar_halfspace(parameters: dict[str, Any]) -> Any:
    """Create the analytical outside half-space of a source-supported plane."""
    import cadquery as cq
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
    from OCP.gp import gp_Pnt
    origin = tuple(float(parameters['plane_' + c]) for c in 'xyz')
    normal = tuple(float(parameters['normal_' + c]) for c in 'xyz')
    if not all(math.isfinite(v) for v in (*origin, *normal)):
        raise ValueError('Non-finite end-cut plane')
    length = math.sqrt(sum(v * v for v in normal))
    if abs(length - 1.0) > 1e-6:
        raise ValueError('End-cut normal is not a unit vector')
    face = cq.Face.makePlane(basePnt=origin, dir=normal)
    outside = gp_Pnt(*(origin[i] + normal[i] for i in range(3)))
    return cq.Shape.cast(BRepPrimAPI_MakeHalfSpace(face.wrapped, outside).Solid())


def source_face_id(face: Any, topology: Any) -> str:
    """Topology sorts evidence by ID; its index is not a native-face index."""
    if topology is None:
        return ''
    center = face.Center().toTuple()
    matches = [item for item in topology.faces if item.surface_type == str(face.geomType()).upper()]
    if not matches:
        return ''
    return min(matches, key=lambda item: (
        abs(item.area_mm2 - float(face.Area())),
        sum((item.centroid_mm[i] - center[i]) ** 2 for i in range(3)), item.face_id,
    )).face_id


def analytical_end_cuts(shape: Any, base_shape: Any, topology: Any, residual_report: Any,
                        axis: Any, tolerance_mm: float) -> tuple[Any, ...]:
    """Recognize oblique exterior planes, but not sloped pockets/interior walls.

    Each cutter must remove a nonempty part of the base and no source material.
    The final independent reconstruction proof remains mandatory.
    """
    from .contracts import RecognizedGeometricFeature, GeometricFeatureType, ManufacturingSemanticType, GeometryProofStatus
    from .recognition_cache import stable_sha256
    if base_shape is None or axis is None:
        return ()
    residuals = [c for c in getattr(residual_report, 'components', ()) if c.direction == 'RECONSTRUCTION_MINUS_SOURCE']
    if not residuals:
        return ()
    found = []
    for face in shape.Faces():
        if str(face.geomType()).upper() != 'PLANE':
            continue
        normal = face.normalAt().toTuple()  # oriented outward, not sign-normalized
        alignment = abs(sum(normal[i] * axis.direction[i] for i in range(3)))
        if not 1e-5 < alignment < 1.0 - 1e-5:
            continue
        origin = face.Center().toTuple()
        params = {**{'plane_' + c: origin[i] for i, c in enumerate('xyz')},
                  **{'normal_' + c: normal[i] for i, c in enumerate('xyz')}}
        try:
            cutter = planar_halfspace(params)
            removed = base_shape.intersect(cutter)
            volume = abs(float(removed.Volume()))
            allowed = max(1e-6, float(tolerance_mm) ** 3)
            if volume <= allowed or abs(float(shape.intersect(cutter).Volume())) > allowed:
                continue
            # Do not claim unrelated nearby residuals as consumed by the cut.
            ids = tuple(c.component_id for c in residuals if abs(c.volume_mm3 - volume) <= max(allowed, volume * 1e-7))
            if not ids:
                continue
        except Exception:
            continue
        found.append(RecognizedGeometricFeature(
            feature_id='feature-' + stable_sha256(('end-plane', params))[:20],
            geometric_type=GeometricFeatureType.PLANAR_HALFSPACE_CUT,
            semantic_type=ManufacturingSemanticType.END_CUT,
            parameters=tuple(sorted(params.items())), source_support=(source_face_id(face, topology),),
            residual_component_ids=ids, confidence_score=0.98, proof_status=GeometryProofStatus.PLAUSIBLE,
        ))
    return tuple(found)


def source_authority_state(inspection: Any) -> tuple[Any, ...]:
    from .contracts import stable_id
    shape = getattr(inspection, 'native_shape', None)
    valid = False
    count = 0
    if shape is not None:
        try:
            valid, count = bool(shape.isValid()), len(shape.Solids())
        except Exception:
            pass
    return (bool(getattr(inspection, 'production_geometry_exact', False)),
            bool(getattr(inspection, 'selection_verified', False)),
            str(getattr(inspection, 'geometry_kind', '')).lower(),
            str(getattr(inspection, 'scope', '')), shape is not None, valid, count,
            stable_id("source-operations", (getattr(inspection, "evidence", None) or {}).get("original_nc1_operations")))


def base_coordinate_frame(base_shape: Any, axis: Any):
    """An orthonormal local frame for prism hypotheses, including rotated parts."""
    import cadquery as cq
    x = cq.Vector(*axis.direction).normalized()
    transverse = []
    for edge in base_shape.Edges():
        if str(edge.geomType()).upper() != 'LINE':
            continue
        delta = edge.endPoint() - edge.startPoint()
        if delta.Length > 1e-7 and abs(delta.normalized().dot(x)) < 1e-6:
            transverse.append(delta)
    if transverse:
        y = max(transverse, key=lambda v: v.Length).normalized()
    else:
        helper = cq.Vector(0, 1, 0) if abs(x.y) < 0.9 else cq.Vector(0, 0, 1)
        y = (helper - x.multiply(helper.dot(x))).normalized()
    return cq.Plane(origin=base_shape.Center(), xDir=x, normal=x.cross(y))
