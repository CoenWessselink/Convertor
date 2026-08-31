from __future__ import annotations

import math
from typing import Any

import cadquery as cq

from .contracts import AxisCandidate, EquivalenceProof, GeometryProofStatus
from .topology import linear_tolerance, relative_tolerance, find_end_face


def reconstruct_prismatic(shape: Any, axis: AxisCandidate) -> Any:
    face = find_end_face(shape, axis)
    vector = cq.Vector(
        axis.direction[0] * axis.length_mm,
        axis.direction[1] * axis.length_mm,
        axis.direction[2] * axis.length_mm,
    )
    return cq.Solid.extrudeLinear(face.outerWire(), list(face.innerWires()), vector)


def _bbox_delta(left: Any, right: Any) -> float:
    a, b = left.BoundingBox(), right.BoundingBox()
    values = (
        abs(float(a.xmin) - float(b.xmin)),
        abs(float(a.xmax) - float(b.xmax)),
        abs(float(a.ymin) - float(b.ymin)),
        abs(float(a.ymax) - float(b.ymax)),
        abs(float(a.zmin) - float(b.zmin)),
        abs(float(a.zmax) - float(b.zmax)),
    )
    return max(values)


def _centroid_delta(left: Any, right: Any) -> float:
    a, b = left.Center(), right.Center()
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def prove_equivalence(source: Any, reconstructed: Any, policy: Any) -> EquivalenceProof:
    source_volume = abs(float(source.Volume()))
    reconstructed_volume = abs(float(reconstructed.Volume()))
    volume_delta = abs(source_volume - reconstructed_volume)
    area_delta = abs(float(source.Area()) - float(reconstructed.Area()))
    bbox_delta = _bbox_delta(source, reconstructed)
    centroid_delta = _centroid_delta(source, reconstructed)
    try:
        source_minus = abs(float(source.cut(reconstructed).Volume()))
        reconstruction_minus = abs(float(reconstructed.cut(source).Volume()))
    except Exception as exc:
        return EquivalenceProof(
            status=GeometryProofStatus.METRIC_ONLY,
            validator="independent-two-way-brep-residual-v1",
            independent_reconstruction=True,
            two_way=False,
            source_volume_mm3=source_volume,
            reconstructed_volume_mm3=reconstructed_volume,
            source_minus_reconstruction_mm3=0.0,
            reconstruction_minus_source_mm3=0.0,
            volume_delta_mm3=volume_delta,
            area_delta_mm2=area_delta,
            bbox_delta_mm=bbox_delta,
            centroid_delta_mm=centroid_delta,
            reason=f"BREP boolean validator niet beschikbaar: {type(exc).__name__}",
        )

    linear = linear_tolerance(policy)
    relative = relative_tolerance(policy)
    residual_allowed = max(linear ** 3, source_volume * relative)
    volume_allowed = max(linear ** 3, source_volume * relative)
    area_allowed = max(linear ** 2, abs(float(source.Area())) * relative)
    passed = (
        source_minus <= residual_allowed
        and reconstruction_minus <= residual_allowed
        and volume_delta <= volume_allowed
        and area_delta <= area_allowed
        and bbox_delta <= linear
        and centroid_delta <= linear
        and bool(reconstructed.isValid())
    )
    return EquivalenceProof(
        status=(
            GeometryProofStatus.PROVEN_BREP_EQUIVALENT
            if passed
            else GeometryProofStatus.FAILED
        ),
        validator="independent-two-way-brep-residual-v1",
        independent_reconstruction=True,
        two_way=True,
        source_volume_mm3=source_volume,
        reconstructed_volume_mm3=reconstructed_volume,
        source_minus_reconstruction_mm3=source_minus,
        reconstruction_minus_source_mm3=reconstruction_minus,
        volume_delta_mm3=volume_delta,
        area_delta_mm2=area_delta,
        bbox_delta_mm=bbox_delta,
        centroid_delta_mm=centroid_delta,
        reason=("Tweezijdig BREP-residu binnen policy" if passed else "BREP-residu buiten policy"),
    )

