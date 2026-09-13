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


def match_full_profile_geometry(
    section: CrossSectionSignature,
    database: Any,
    policy: Any,
    *,
    limit: int = 12,
) -> tuple[ProfileMatchCandidate, ...]:
    """Fast candidate filter; exact authority comes from native contour proof.

    Legacy implementations fabricated perimeter/moment/radius/contour errors
    from bounds. Unmeasured errors are now null, not zero and not exact matches.
    """
    recognition = getattr(policy, "recognition", policy)
    dimension_tolerance = float(getattr(recognition, "profile_dimension_mm", 0.15))
    area_relative = float(getattr(recognition, "section_area_relative", 0.001))
    if limit <= 0:
        return ()
    if not all(math.isfinite(value) and value > 0 for value in
               (dimension_tolerance, area_relative, section.width_mm, section.height_mm, section.area_mm2)):
        return ()
    candidates = []
    for definition in profile_definitions(database):
        width, height, _, _, _ = _dimensions(definition)
        area = float(getattr(definition, "area_mm2", 0.0) or 0.0)
        if not all(math.isfinite(value) and value > 0 for value in (width, height, area)):
            continue
        direct = max(abs(width - section.width_mm), abs(height - section.height_mm))
        swapped = max(abs(height - section.width_mm), abs(width - section.height_mm))
        dimension_residual = min(direct, swapped)
        area_residual = abs(area - section.area_mm2)
        family = str(getattr(definition, "family", "")).upper()
        kind = str(getattr(definition, "profile_type", "")).upper()
        topology_match = (family in HOLLOW_FAMILIES or kind in {"M", "RO"}) == (section.inner_wire_count > 0)
        normalized = (dimension_residual / dimension_tolerance
                      + area_residual / max(area, section.area_mm2) / area_relative
                      + (0.0 if topology_match else 10.0))
        candidates.append(ProfileMatchCandidate(
            designation=str(getattr(definition, "designation", "")),
            dimension_residual_mm=dimension_residual, area_residual_mm2=area_residual,
            perimeter_residual_mm=None, moment_residual=None, radius_residual_mm=None,
            contour_distance_mm=None, topology_match=topology_match,
            score=1.0 / (1.0 + normalized), proof_status="METRIC_ONLY",
            measurement_basis=("dimensions", "area", "hollow-topology-filter"),
        ))
    candidates.sort(key=lambda item: (-item.score, item.dimension_residual_mm, item.designation))
    return tuple(candidates[:limit])


__all__ = ["match_full_profile_geometry"]


def _section_xy(faces: Any, normal: Any) -> Any:
    """Normalize only an analysis copy; never publish this as source placement."""
    import cadquery as cq
    shape = cq.Compound.makeCompound(list(faces))
    n = cq.Vector(*normal).normalized()
    transverse = []
    for edge in shape.Edges():
        if str(edge.geomType()).upper() == "LINE":
            delta = edge.endPoint() - edge.startPoint()
            delta = delta - n.multiply(delta.dot(n))
            if delta.Length > 1e-8:
                transverse.append(delta)
    if transverse:
        u = max(transverse, key=lambda value: value.Length).normalized()
    else:
        helper = cq.Vector(1, 0, 0) if abs(n.x) < 0.9 else cq.Vector(0, 1, 0)
        u = n.cross(helper).normalized()
    origin = faces[0].Center()
    local = shape.copy().transformShape(cq.Plane(origin=origin, xDir=u, normal=n).fG)
    return _anchor_section(local)


def _anchor_section(shape: Any) -> Any:
    box = shape.BoundingBox()
    return shape.translate((-box.xmin, -box.ymin, -box.zmin))


def catalogue_boundary_evidence(profile: Any, source_faces: Any, axis: Any,
                                policy: Any) -> dict[str, Any]:
    """Independent catalogue reconstruction through the existing CAD builder.

    A source-extruded copy proves prism equivalence, NOT catalogue identity.
    This second comparison checks the actual inner/outer section boundaries.
    The result concerns parametrized catalogue geometry, not rolled/welded origin.
    """
    import cadquery as cq
    from cws_convertor.project.canonical_rebuild import _profile_part
    from conversion import build_shape
    from .topology import linear_tolerance, relative_tolerance

    result = {"status": "NOT_PROVEN", "method": "catalogue-parametric-two-way-section",
              "manufacturing_origin_proven": False}
    try:
        family = str(getattr(profile, "family", "")).upper()
        properties = getattr(profile, "properties", {}) or {}
        if family in {"IPN", "INP", "UNP", "UPN"} or any(
            properties.get(key) for key in ("flange_slope", "flange_slope_percent", "tapered_flange")
        ):
            # The existing builder has parallel flanges; do not certify a
            # tapered catalogue family by reconstructing a different product.
            raise ValueError("Catalogusflenshelling wordt nog niet exact gereconstrueerd")
        part = _profile_part(profile, 1.0)
        template = build_shape(part).val()
        if any("overgeslagen" in str(warning).lower() for warning in part.warnings):
            raise ValueError("Catalogusreconstructie heeft geometrie overgeslagen")
        section = template.intersect(cq.Face.makePlane(basePnt=(0.5, 0, 0), dir=(1, 0, 0)))
        target = _section_xy(tuple(section.Faces()), (1, 0, 0))
        observed = _section_xy(tuple(source_faces), axis.direction)
        linear = linear_tolerance(policy)
        area_limit = max(linear ** 2, observed.Area() * relative_tolerance(policy))
        perimeter = sum(edge.Length() for edge in observed.Edges())
        perim_limit = max(linear, perimeter * relative_tolerance(policy))
        best = None
        observed_boundary = cq.Compound.makeCompound(observed.Edges())
        observed_points = [point for edge in observed.Edges()
                           for point in edge.positions([i / 8.0 for i in range(9)])]
        for mirrored in (False, True):
            candidate = target.mirror("YZ") if mirrored else target
            for degrees in (0, 90, 180, 270):
                aligned = _anchor_section(candidate.rotate((0, 0, 0), (0, 0, 1), degrees))
                ob, cb = observed.BoundingBox(), aligned.BoundingBox()
                if max(abs(ob.xlen - cb.xlen), abs(ob.ylen - cb.ylen)) > linear:
                    continue
                missing = abs(float(observed.cut(aligned).Area()))
                extra = abs(float(aligned.cut(observed).Area()))
                delta = abs(sum(edge.Length() for edge in aligned.Edges()) - perimeter)
                # Do not spend boundary-distance work on an already failed area.
                distance = None
                if missing <= area_limit and extra <= area_limit and delta <= perim_limit:
                    boundary = cq.Compound.makeCompound(aligned.Edges())
                    checks = [boundary.distance(cq.Vertex.makeVertex(*v.toTuple())) for v in observed_points]
                    checks.extend(observed_boundary.distance(cq.Vertex.makeVertex(*v.toTuple()))
                                  for edge in aligned.Edges()
                                  for v in edge.positions([i / 8.0 for i in range(9)]))
                    distance = max(checks, default=float("inf"))
                topology_match = (len(observed.Faces()) == len(aligned.Faces())
                    and sum(len(f.innerWires()) for f in observed.Faces()) == sum(len(f.innerWires()) for f in aligned.Faces()))
                proven = bool(topology_match and distance is not None and distance <= linear
                              and aligned.isValid() and observed.isValid())
                record = {**result, "status": "PROVEN" if proven else "NOT_PROVEN",
                    "source_minus_catalogue_mm2": missing, "catalogue_minus_source_mm2": extra,
                    "perimeter_delta_mm": delta, "boundary_distance_sample_max_mm": distance,
                    "linear_tolerance_mm": linear, "area_tolerance_mm2": area_limit,
                    "topology_match": topology_match, "candidate_rotation_degrees": degrees,
                    "candidate_mirrored": mirrored,
                    "boundary_distance_method": "bidirectional 9 samples per analytic edge plus surface residuals"}
                if best is None or missing + extra < best[0]:
                    best = (missing + extra, record)
                if proven:
                    return record
        return best[1] if best else {**result, "reason": "Geen congruente doorsnedeoriëntatie"}
    except Exception as exc:
        return {**result, "reason": f"{type(exc).__name__}: {exc}"}
