"""Assemble already exact closed IFC faces; never manufacture missing surfaces."""
from __future__ import annotations
from typing import Any


def closed_faces_to_solid(shape: Any, tolerance_mm: float = 1e-6) -> tuple[Any, dict]:
    import cadquery as cq
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.BRepLib import BRepLib
    faces = shape.Faces()
    if shape.Solids() or not faces:
        raise ValueError('Alleen losse exacte bronvlakken zijn toegestaan')
    sewing = BRepBuilderAPI_Sewing(tolerance_mm)
    sewing.SetMaxTolerance(tolerance_mm)
    for face in faces:
        sewing.Add(face.wrapped)
    sewing.Perform()
    if sewing.NbFreeEdges() or sewing.NbMultipleEdges() or sewing.NbDeletedFaces():
        raise ValueError('Bronvlakken vormen geen gesloten manifold zonder weggelaten vlakken')
    sewn = cq.Shape.cast(sewing.SewedShape())
    shells = sewn.Shells()
    if len(shells) != 1 or len(sewn.Faces()) != len(faces):
        raise ValueError('Niet precies één gesloten shell met alle bronvlakken')
    original_area = float(shape.Area())
    solid = cq.Shape.cast(BRepBuilderAPI_MakeSolid(shells[0].wrapped).Solid())
    if not BRepLib.OrientClosedSolid_s(solid.wrapped) or not solid.isValid() or float(solid.Volume()) <= 0:
        raise ValueError('Geassembleerde bronvlakken zijn geen geldig eindig solid')
    if abs(float(solid.Area())-original_area) > max(tolerance_mm*tolerance_mm, abs(original_area)*1e-10):
        raise ValueError('Bronoppervlak is gewijzigd tijdens topologische samenvoeging')
    return solid, {'method':'exact_closed_source_faces', 'tolerance_mm':tolerance_mm,
                   'source_face_count':len(faces), 'result_face_count':len(solid.Faces()),
                   'free_edges':0,'multiple_edges':0,'deleted_faces':0,'geometry_added':False,
                   'source_surface_area_mm2':original_area,'result_surface_area_mm2':float(solid.Area())}


def native_body_occurrences(shape: Any, path: tuple[int, ...] = ()) -> tuple[tuple[tuple[int, ...], Any], ...]:
    """Walk direct children, not TopExp's deduplicated solid map.

    Two occurrences may reference the very same TopoDS handle. Bodies in a
    product are geometric occurrences, NOT yet independently orderable parts.
    Shells within a Solid are its boundary, not additional bodies.
    """
    if str(shape.ShapeType()).upper() not in {'COMPOUND', 'COMPSOLID'}:
        return ((path, shape),)
    return tuple(item for index, child in enumerate(shape)
                 for item in native_body_occurrences(child, (*path, index)))


def inventory_source_bodies(shape: Any, *, source_scope: str,
                            tolerance_mm: float = 1e-6, pair_budget: int = 256) -> dict[str, Any]:
    """Read-only native inventory; never split canonical entities or infer welds.

    Pair checks and union measurements are explicitly budgeted. Unknown or
    invalid bodies have null volume, not zero. Sum and geometric union are
    distinct quantities; neither establishes material mass or physical count.
    """
    import hashlib
    import io
    import math
    import json
    if not source_scope or not math.isfinite(tolerance_mm) or tolerance_mm <= 0 or pair_budget < 0:
        raise ValueError('An explicit source scope, positive tolerance and nonnegative budget are required')
    occurrences = native_body_occurrences(shape)
    bodies = []
    for path, body in occurrences:
        kind = str(body.ShapeType()).upper()
        valid = bool(body.isValid())
        volume = float(body.Volume()) if valid and kind == 'SOLID' else None
        exact = volume is not None and math.isfinite(volume) and volume > 0
        stream = io.BytesIO()
        body.exportBrep(stream)
        geometry_hash = hashlib.sha256(stream.getvalue()).hexdigest()
        key = json.dumps((source_scope, path), separators=(',', ':'))
        box = body.BoundingBox()
        bodies.append({
            'body_occurrence_id': 'body:' + hashlib.sha256(key.encode()).hexdigest()[:24],
            'source_scope': source_scope, 'container_path': list(path),
            'geometry_sha256': geometry_hash, 'representation': 'native_brep',
            'topology_kind': kind, 'valid': valid, 'exact_solid': exact,
            'volume_mm3': volume if exact else None, 'area_mm2': float(body.Area()) if valid else None,
            'bounds_mm': [box.xmin, box.ymin, box.zmin, box.xmax, box.ymax, box.zmax],
            'face_count': len(body.Faces()), 'shell_count': len(body.Shells()),
            'physical_part_proven': False, 'quantitative_bom_node': False,
            'status': 'GEOMETRY_AVAILABLE' if exact else 'REVIEW_NON_SOLID_OR_INVALID',
        })
    all_exact = bool(bodies) and all(row['exact_solid'] for row in bodies)
    pair_count = len(bodies) * (len(bodies) - 1) // 2
    interfaces = []
    for i, (_, left) in enumerate(occurrences):
        for j in range(i + 1, len(occurrences)):
            if len(interfaces) >= pair_budget:
                break
            row = {'left': bodies[i]['body_occurrence_id'], 'right': bodies[j]['body_occurrence_id'],
                   'relation': 'NOT_EVALUATED', 'overlap_volume_mm3': None,
                   'minimum_distance_mm': None, 'weld_proven': False}
            if bodies[i]['exact_solid'] and bodies[j]['exact_solid']:
                try:
                    right = occurrences[j][1]
                    common = left.intersect(right)
                    overlap = sum(float(s.Volume()) for s in common.Solids())
                    distance = float(left.distance(right))
                    row.update(overlap_volume_mm3=overlap, minimum_distance_mm=distance,
                               relation='OVERLAPPING' if overlap > tolerance_mm ** 3 else
                               'TOUCHING' if distance <= tolerance_mm else 'SEPARATED')
                except Exception as exc:
                    row.update(relation='REVIEW_KERNEL_ERROR', error=type(exc).__name__)
            interfaces.append(row)
    union_volume = None
    union_status = 'NOT_EVALUATED'
    if all_exact and pair_count <= pair_budget:
        try:
            union = occurrences[0][1].copy()
            for _, body in occurrences[1:]:
                union = union.fuse(body)
            if not union.isValid():
                raise ValueError('Invalid union')
            union_volume = sum(float(s.Volume()) for s in union.Solids())
            union_status = 'MEASURED_NATIVE_UNION'
        except Exception as exc:
            union_status = 'REVIEW_KERNEL_ERROR:' + type(exc).__name__
    return {
        'algorithm': 'source-body-occurrences-v1', 'body_occurrence_count': len(bodies),
        'unique_native_solid_map_count': len(shape.Solids()), 'bodies': bodies,
        'all_bodies_exact_solids': all_exact, 'interfaces': interfaces,
        'pair_checks_required': pair_count, 'pair_checks_run': len(interfaces),
        'pair_analysis_complete': len(interfaces) == pair_count and all(x['relation'] not in
            {'NOT_EVALUATED', 'REVIEW_KERNEL_ERROR'} for x in interfaces),
        'tolerance_mm': tolerance_mm, 'pair_budget': pair_budget,
        'sum_body_volumes_mm3': sum(x['volume_mm3'] for x in bodies) if all_exact else None,
        'union_volume_mm3': union_volume, 'union_status': union_status,
        'physical_part_count': None, 'bom_decomposition_authorized': False,
        'fabrication_origin_proven': False, 'source_modified': False,
    }
