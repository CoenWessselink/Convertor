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
