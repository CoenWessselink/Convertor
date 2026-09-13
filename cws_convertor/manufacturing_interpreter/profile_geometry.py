from __future__ import annotations

import math
from typing import Any

from .contracts import CrossSectionSignature, ProfileMatchCandidate
from .profiles import profile_definitions


HOLLOW_FAMILIES = {"CHS", "RHS", "SHS"}


def _dimensions(definition: Any) -> tuple[float, float, float, float, float]:
    return (
        float(getattr(definition, "width", getattr(definition, "dim1", 0.0)) or 0.0),
        float(getattr(definition, "height", getattr(definition, "dim2", 0.0)) or 0.0),
        float(getattr(definition, "dim3", 0.0) or 0.0),
        float(getattr(definition, "dim4", 0.0) or 0.0),
        float(getattr(definition, "radius", 0.0) or 0.0),
    )


def _perimeter(family: str, width: float, height: float, thickness: float) -> float:
    family = family.upper()
    if family == "CHS":
        diameter = max(width, height)
        return math.pi * diameter + math.pi * max(0.0, diameter - 2.0 * thickness)
    if family in {"RHS", "SHS"}:
        return 2.0 * (width + height) + 2.0 * (
            max(0.0, width - 2.0 * thickness) + max(0.0, height - 2.0 * thickness)
        )
    return 2.0 * (width + height)


def match_full_profile_geometry(
    section: CrossSectionSignature,
    database: Any,
    policy: Any,
    *,
    limit: int = 12,
) -> tuple[ProfileMatchCandidate, ...]:
    recognition = getattr(policy, "recognition", policy)
    dimension_tolerance = float(getattr(recognition, "profile_dimension_mm", 0.15))
    area_relative = float(getattr(recognition, "section_area_relative", 0.001))
    candidates = []
    for definition in profile_definitions(database):
        width, height, thickness, flange, radius = _dimensions(definition)
        direct = abs(width - section.width_mm) + abs(height - section.height_mm)
        swapped = abs(height - section.width_mm) + abs(width - section.height_mm)
        dimension_residual = min(direct, swapped)
        area = float(getattr(definition, "area_mm2", 0.0) or 0.0)
        area_residual = abs(area - section.area_mm2)
        family = str(getattr(definition, "family", "")).upper()
        expected_perimeter = _perimeter(family, width, height, thickness)
        perimeter_residual = abs(expected_perimeter - section.perimeter_mm)
        expected_moment = max(area, 1.0) * (width * width + height * height) / 12.0
        observed_moment = max(section.area_mm2, 1.0) * (
            section.width_mm**2 + section.height_mm**2
        ) / 12.0
        moment_residual = abs(expected_moment - observed_moment) / max(
            expected_moment, observed_moment, 1.0
        )
        topology_match = (family in HOLLOW_FAMILIES) == (section.inner_wire_count > 0)
        radius_residual = 0.0 if radius <= 0.0 else min(
            abs(radius - min(width, height) * 0.5), abs(radius - thickness)
        )
        contour_distance = math.sqrt(
            dimension_residual**2
            + (area_residual / max(math.sqrt(max(area, 1.0)), 1.0)) ** 2
            + (perimeter_residual * 0.25) ** 2
        )
        normalized = (
            dimension_residual / max(dimension_tolerance, 1e-6)
            + area_residual / max(max(area, section.area_mm2, 1.0) * area_relative, 1e-6)
            + perimeter_residual / max(section.perimeter_mm * area_relative, dimension_tolerance, 1e-6)
            + moment_residual
            + (0.0 if topology_match else 10.0)
        )
        candidates.append(
            ProfileMatchCandidate(
                designation=str(getattr(definition, "designation", "")),
                dimension_residual_mm=dimension_residual,
                area_residual_mm2=area_residual,
                perimeter_residual_mm=perimeter_residual,
                moment_residual=moment_residual,
                radius_residual_mm=radius_residual,
                contour_distance_mm=contour_distance,
                topology_match=topology_match,
                score=1.0 / (1.0 + normalized),
            )
        )
    candidates.sort(
        key=lambda item: (
            -item.score,
            item.contour_distance_mm,
            item.dimension_residual_mm,
            item.designation,
        )
    )
    return tuple(candidates[:limit])


__all__ = ["match_full_profile_geometry"]


def _catalogue_section(definition: Any) -> Any:
    """Reuse the production profile builder; no second catalogue or guessed grade."""
    import cadquery as cq
    from pathlib import Path
    from converter import Header, NC1Part
    from conversion import build_shape

    kind = str(getattr(definition, 'profile_type', '')).upper()
    header = Header(order_number='', drawing_number='', part_number='', position_number='',
                    material='', quantity=1, profile=str(definition.designation), profile_type=kind,
                    length=10., saw_length=10., dim1=float(definition.dim1), dim2=float(definition.dim2),
                    dim3=float(definition.dim3), dim4=float(definition.dim4), radius=float(definition.radius),
                    weight=0., paint_area=0., web_miter_front=0., web_miter_rear=0.,
                    flange_miter_front=0., flange_miter_rear=0.)
    part = NC1Part(Path('catalogue-geometry-only'), header, [], [])
    solid = build_shape(part).val()
    if not solid.isValid() or len(solid.Solids()) != 1:
        raise ValueError('Catalogue builder did not yield one valid solid')
    if any('overgeslagen' in w.lower() for w in part.warnings):
        raise ValueError('Catalogue builder omitted geometry')
    section = solid.intersect(cq.Face.makePlane(basePnt=(5., 0., 0.), dir=(1., 0., 0.)))
    return cq.Plane(origin=(5., 0., 0.), xDir=(0., 1., 0.), normal=(1., 0., 0.)).toLocalCoords(section)


def native_section_comparison(source_faces: tuple[Any, ...], axis: Any, definition: Any, policy: Any) -> dict[str, Any]:
    """Measure bidirectional planar residuals, not bbox/area coincidence.

    Rotations/reflections align a catalogue *cross-section* only. Source solids,
    occurrence placements and feature/manufacturing handedness are untouched.
    This proves shape similarity, never rolled versus welded manufacture.
    """
    import cadquery as cq
    from .topology import linear_tolerance, relative_tolerance

    try:
        normal = source_faces[0].normalAt().normalized()
        if normal.dot(cq.Vector(*axis.direction)) < 0:
            normal = -normal
        lines = [e for f in source_faces for e in f.Edges() if str(e.geomType()).upper() == 'LINE']
        if lines:
            edge = max(lines, key=lambda e: e.Length())
            transverse = (edge.endPoint()-edge.startPoint()).normalized()
        else:
            helper = cq.Vector(1, 0, 0) if abs(normal.x) < .9 else cq.Vector(0, 1, 0)
            transverse = normal.cross(helper).normalized()
        plane = cq.Plane(origin=source_faces[0].Center(), xDir=transverse, normal=normal)
        source = plane.toLocalCoords(cq.Compound.makeCompound(list(source_faces))).clean()
        reference = _catalogue_section(definition).clean()
        def centred(shape: Any) -> Any:
            faces = shape.Faces()
            area = sum(float(f.Area()) for f in faces)
            centre = sum((f.Center().multiply(float(f.Area())) for f in faces), cq.Vector()).multiply(1./area)
            return shape.translate(-centre)
        source, reference = centred(source), centred(reference)
        linear = linear_tolerance(policy)
        area_limit = max(linear**2, reference.Area()*relative_tolerance(policy))
        best = None
        for mirrored in (False, True):
            candidate = reference.mirror('YZ') if mirrored else reference
            for angle in (0., 90., 180., 270.):
                oriented = candidate.rotate((0,0,0),(0,0,1),angle)
                missing, extra = source.cut(oriented), oriented.cut(source)
                missing_area, extra_area = float(missing.Area()), float(extra.Area())
                # Maximum tested boundary separation supplements two-way area
                # and local-residual thickness. It is not a Hausdorff certificate.
                boundary_distance = max(
                    (cq.Vertex.makeVertex(*edge.positionAt(t).toTuple()).distance(other)
                     for current, other in ((source, oriented), (oriented, source))
                     for edge in current.Edges() for t in (0., .25, .5, .75, 1.)), default=float('inf'))
                local_ok = all(
                    f.Area() <= linear**2 or
                    2*f.Area()/max(sum(e.Length() for e in f.Edges()), 1e-12) <= linear
                    for residual in (missing, extra) for f in residual.Faces())
                passed = missing_area <= area_limit and extra_area <= area_limit and boundary_distance <= linear and local_ok
                observation = {'status': 'PROVEN' if passed else 'FAILED',
                    'source_minus_catalogue_mm2': missing_area, 'catalogue_minus_source_mm2': extra_area,
                    'boundary_sample_max_mm': boundary_distance, 'linear_tolerance_mm': linear,
                    'area_tolerance_mm2': area_limit, 'rotation_degrees': angle,
                    'section_reflected_for_comparison': mirrored,
                    'method': 'native-two-way-planar-residual-and-local-thickness',
                    'catalogue_source': str(getattr(definition, 'source', '')),
                    'catalogue_standard': str(getattr(definition, 'standard', '')),
                    'fabrication_origin_proven': False}
                if best is None or missing_area+extra_area < best['source_minus_catalogue_mm2']+best['catalogue_minus_source_mm2']:
                    best = observation
                if passed:
                    return observation
        return best or {'status':'UNAVAILABLE', 'reason':'No orientation tested'}
    except Exception as exc:
        return {'status':'UNAVAILABLE', 'reason':f'{type(exc).__name__}: {exc}'}
