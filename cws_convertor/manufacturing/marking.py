"""M3 contact-derived scribing with fail-closed geometric validation."""
from __future__ import annotations

import math
from typing import Iterable, Mapping

from cws_convertor.project.model import Part, stable_sha256

from .contact_model import ContactPatch, ContactResolutionReport
from .faces_model import FaceProofStatus, FaceResolutionReport, ManufacturingFace, SurfaceType
from .marking_model import (
    ExclusionKind,
    MarkExclusionZone,
    MarkFeature,
    MarkKind,
    MarkSegment2D,
    MarkSet,
    MarkStatus,
    MarkingRuleSet,
)

CWS_MARK_STALE_FACE_REPORT = "CWS-MARK-006"
CWS_MARK_CONTACT_NOT_VERIFIED = "CWS-MARK-007"
CWS_MARK_FACE_UNSUITABLE = "CWS-MARK-008"
CWS_MARK_OUTSIDE_FACE = "CWS-MARK-009"
CWS_MARK_EDGE_CLEARANCE = "CWS-MARK-010"
CWS_MARK_EXCLUSION = "CWS-MARK-011"
CWS_MARK_LENGTH = "CWS-MARK-012"
CWS_MARK_ZERO_LENGTH = "CWS-MARK-013"
CWS_MARK_CONTACT_AREA = "CWS-MARK-014"
CWS_MARK_CONTACT_WRONG_PART = "CWS-MARK-015"


def _polygon_area(loop: Iterable[tuple[float, float]]) -> float:
    points = list(loop)
    if len(points) < 3:
        return 0.0
    if points[0] != points[-1]:
        points.append(points[0])
    return 0.5 * sum(
        points[index][0] * points[index + 1][1] - points[index + 1][0] * points[index][1]
        for index in range(len(points) - 1)
    )


def _point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    denominator = dx * dx + dy * dy
    if denominator <= 1e-24:
        return math.dist(point, start)
    t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / denominator
    t = max(0.0, min(1.0, t))
    closest = (start[0] + t * dx, start[1] + t * dy)
    return math.dist(point, closest)


def _loop_edges(loop: Iterable[tuple[float, float]]) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
    points = list(loop)
    if len(points) < 2:
        return ()
    if points[0] != points[-1]:
        points.append(points[0])
    return tuple((points[index], points[index + 1]) for index in range(len(points) - 1))


def _point_on_loop(point: tuple[float, float], loop: Iterable[tuple[float, float]], tolerance: float) -> bool:
    return any(_point_segment_distance(point, start, end) <= tolerance for start, end in _loop_edges(loop))


def _point_in_polygon(point: tuple[float, float], loop: Iterable[tuple[float, float]], tolerance: float) -> bool:
    points = list(loop)
    if len(points) < 3:
        return False
    if _point_on_loop(point, points, tolerance):
        return True
    if points[0] == points[-1]:
        points = points[:-1]
    inside = False
    x, y = point
    j = len(points) - 1
    for i, current in enumerate(points):
        previous = points[j]
        yi, yj = current[1], previous[1]
        if (yi > y) != (yj > y):
            denominator = yj - yi
            if abs(denominator) > 1e-18:
                crossing_x = (previous[0] - current[0]) * (y - yi) / denominator + current[0]
                if x < crossing_x:
                    inside = not inside
        j = i
    return inside


def _distance_to_loop(point: tuple[float, float], loop: Iterable[tuple[float, float]]) -> float:
    edges = _loop_edges(loop)
    if not edges:
        return math.inf
    return min(_point_segment_distance(point, start, end) for start, end in edges)


def _outer_and_voids(face: ManufacturingFace) -> tuple[
    tuple[tuple[float, float], ...] | None,
    tuple[tuple[tuple[float, float], ...], ...],
]:
    loops = [loop for loop in face.boundary_loops_2d if len(loop) >= 3]
    if not loops:
        return None, ()
    outer = max(loops, key=lambda loop: abs(_polygon_area(loop)))
    voids = tuple(loop for loop in loops if loop is not outer)
    return outer, voids


def _segment_within_face(segment: MarkSegment2D, face: ManufacturingFace, rules: MarkingRuleSet) -> tuple[bool, float]:
    outer, voids = _outer_and_voids(face)
    if outer is None:
        return False, 0.0
    probes = (segment.start, segment.midpoint, segment.end)
    for point in probes:
        if not _point_in_polygon(point, outer, rules.point_tolerance_mm):
            return False, 0.0
        if any(
            _point_in_polygon(point, void, rules.point_tolerance_mm)
            and not _point_on_loop(point, void, rules.point_tolerance_mm)
            for void in voids
        ):
            return False, 0.0
    clearance = min(_distance_to_loop(point, outer) for point in probes)
    return True, clearance


def _zone_clearance(rules: MarkingRuleSet, zone: MarkExclusionZone) -> float:
    if zone.kind == ExclusionKind.HOLE:
        base = rules.hole_clearance_mm
    elif zone.kind == ExclusionKind.WELD:
        base = rules.weld_clearance_mm
    elif zone.kind == ExclusionKind.CLAMP:
        base = rules.clamp_clearance_mm
    else:
        base = 0.0
    return max(float(base), float(zone.clearance_mm))


def _feature_id(
    part_id: str,
    face_id: str,
    contact_id: str,
    loop_index: int,
    segment_index: int,
    segment: MarkSegment2D,
    ruleset_sha256: str,
) -> str:
    digest = stable_sha256(
        {
            "part_id": part_id,
            "face_id": face_id,
            "contact_id": contact_id,
            "loop_index": loop_index,
            "segment_index": segment_index,
            "segment": segment.to_dict(),
            "ruleset_sha256": ruleset_sha256,
        }
    )
    return "MARK-" + digest[:20].upper()


class ContactScribingEngine:
    """Build auditable face-local marks from exact contact-patch boundaries."""

    def __init__(self, ruleset: MarkingRuleSet | None = None) -> None:
        self.ruleset = ruleset or MarkingRuleSet()

    @staticmethod
    def _face_map(report: FaceResolutionReport) -> dict[str, ManufacturingFace]:
        return {face.face_id: face for face in report.faces}

    def _mark_for_segment(
        self,
        *,
        part: Part,
        face: ManufacturingFace,
        patch: ContactPatch,
        loop_index: int,
        segment_index: int,
        segment: MarkSegment2D,
        exclusions: tuple[MarkExclusionZone, ...],
    ) -> MarkFeature:
        blockers: list[str] = []
        warnings: list[str] = []
        exact = bool(patch.production_usable)
        confidence = min(float(face.confidence), 1.0 if exact else 0.0)

        if self.ruleset.require_verified_contact and not patch.production_usable:
            blockers.append(CWS_MARK_CONTACT_NOT_VERIFIED)
        if self.ruleset.require_planar_face and face.surface_type != SurfaceType.PLANE:
            blockers.append(CWS_MARK_FACE_UNSUITABLE)
        if face.proof_status == FaceProofStatus.BLOCKED:
            blockers.append(CWS_MARK_FACE_UNSUITABLE)
        elif face.proof_status == FaceProofStatus.REVIEW_REQUIRED:
            warnings.append("ManufacturingFace semantic role vereist review; mark blijft review-required.")

        if segment.length_mm <= self.ruleset.point_tolerance_mm:
            blockers.append(CWS_MARK_ZERO_LENGTH)
        elif not self.ruleset.min_segment_length_mm <= segment.length_mm <= self.ruleset.max_segment_length_mm:
            blockers.append(CWS_MARK_LENGTH)

        within, edge_distance = _segment_within_face(segment, face, self.ruleset)
        if not within:
            blockers.append(CWS_MARK_OUTSIDE_FACE)
        elif edge_distance + self.ruleset.point_tolerance_mm < self.ruleset.edge_clearance_mm:
            blockers.append(CWS_MARK_EDGE_CLEARANCE)

        hit_zones: list[str] = []
        for zone in exclusions:
            if zone.face_id != face.face_id:
                continue
            required = float(zone.radius_mm) + _zone_clearance(self.ruleset, zone)
            if _point_segment_distance(zone.center_2d, segment.start, segment.end) + self.ruleset.point_tolerance_mm < required:
                hit_zones.append(zone.zone_id)
        if hit_zones:
            blockers.append(CWS_MARK_EXCLUSION)
            warnings.append("Mark kruist exclusion zone(s): " + ", ".join(sorted(hit_zones)))

        if blockers:
            status = MarkStatus.BLOCKED
        elif face.proof_status == FaceProofStatus.REVIEW_REQUIRED:
            status = MarkStatus.REVIEW_REQUIRED
        else:
            status = MarkStatus.ACCEPTED

        mark_id = _feature_id(
            part.internal_id,
            face.face_id,
            patch.contact_id,
            loop_index,
            segment_index,
            segment,
            self.ruleset.ruleset_sha256,
        )
        return MarkFeature(
            mark_id=mark_id,
            part_id=part.internal_id,
            face_id=face.face_id,
            kind=MarkKind.SCRIBE_SEGMENT,
            status=status,
            segment=segment,
            source_contact_id=patch.contact_id,
            source_secondary_part_id=patch.secondary_part_id,
            ruleset_sha256=self.ruleset.ruleset_sha256,
            source_geometry_hash=patch.geometry_hash,
            exact_geometry=exact,
            confidence=confidence,
            provenance={
                "derivation": "contact_patch.projected_boundary_main_2d",
                "contact_relation_type": patch.relation_type.value,
                "source_relation": list(patch.source_relation),
                "loop_index": loop_index,
                "segment_index": segment_index,
                "edge_distance_mm": edge_distance,
                "exclusion_zone_ids": sorted(hit_zones),
            },
            warnings=tuple(warnings),
            blocking_codes=tuple(blockers),
        )

    def build(
        self,
        part: Part,
        face_report: FaceResolutionReport,
        contact_report: ContactResolutionReport,
        *,
        exclusions: Iterable[MarkExclusionZone] = (),
    ) -> MarkSet:
        if not part.manufacturing_hash:
            raise ValueError("M3 scribing vereist een manufacturing_hash")
        exclusion_tuple = tuple(exclusions)
        blockers: list[str] = []
        warnings: list[str] = []

        if face_report.part_id != part.internal_id or face_report.manufacturing_hash != part.manufacturing_hash:
            blockers.append(CWS_MARK_STALE_FACE_REPORT)
        if not face_report.passed:
            blockers.extend(face_report.blocking_codes)
        faces = self._face_map(face_report)

        patches = [patch for patch in contact_report.patches if patch.main_part_id == part.internal_id]
        foreign = [
            patch.contact_id
            for patch in contact_report.patches
            if patch.secondary_part_id == part.internal_id and patch.main_part_id != part.internal_id
        ]
        if foreign:
            warnings.append(
                "Onderdeel is secondary in contact(en) " + ", ".join(sorted(foreign)) +
                "; M3 schrijft alleen partnercontouren op het canonical main part."
            )

        features: list[MarkFeature] = []
        for patch in sorted(patches, key=lambda item: item.contact_id):
            if patch.area_mm2 < self.ruleset.minimum_contact_area_mm2:
                blockers.append(CWS_MARK_CONTACT_AREA)
            if patch.main_part_id != part.internal_id:
                blockers.append(CWS_MARK_CONTACT_WRONG_PART)
                continue
            face = faces.get(patch.main_face_id)
            if face is None:
                blockers.append(CWS_MARK_FACE_UNSUITABLE)
                warnings.append(f"Contact {patch.contact_id} verwijst naar ontbrekende face {patch.main_face_id}.")
                continue
            for loop_index, loop in enumerate(patch.projected_boundary_main_2d):
                points = list(loop)
                if len(points) < 2:
                    blockers.append(CWS_MARK_ZERO_LENGTH)
                    continue
                if math.dist(points[0], points[-1]) > self.ruleset.point_tolerance_mm:
                    points.append(points[0])
                for segment_index in range(len(points) - 1):
                    segment = MarkSegment2D(points[segment_index], points[segment_index + 1])
                    features.append(
                        self._mark_for_segment(
                            part=part,
                            face=face,
                            patch=patch,
                            loop_index=loop_index,
                            segment_index=segment_index,
                            segment=segment,
                            exclusions=exclusion_tuple,
                        )
                    )

        for feature in features:
            blockers.extend(feature.blocking_codes)
        blockers = list(dict.fromkeys(blockers))
        return MarkSet.create(
            part_id=part.internal_id,
            manufacturing_hash=part.manufacturing_hash,
            face_report_sha256=face_report.report_sha256,
            contact_report_sha256=contact_report.report_sha256,
            ruleset_sha256=self.ruleset.ruleset_sha256,
            features=tuple(features),
            exclusions=exclusion_tuple,
            blocking_codes=tuple(blockers),
            warnings=tuple(warnings),
        )


class MarkSetValidator:
    """Revalidate identity bindings without upgrading confidence."""

    @staticmethod
    def validate(
        mark_set: MarkSet,
        *,
        part: Part,
        face_report: FaceResolutionReport,
        contact_report: ContactResolutionReport,
        ruleset: MarkingRuleSet,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if mark_set.part_id != part.internal_id or mark_set.manufacturing_hash != part.manufacturing_hash:
            blockers.append(CWS_MARK_STALE_FACE_REPORT)
        if mark_set.face_report_sha256 != face_report.report_sha256:
            blockers.append(CWS_MARK_STALE_FACE_REPORT)
        if mark_set.contact_report_sha256 != contact_report.report_sha256:
            blockers.append(CWS_MARK_CONTACT_NOT_VERIFIED)
        if mark_set.ruleset_sha256 != ruleset.ruleset_sha256:
            blockers.append(CWS_MARK_STALE_FACE_REPORT)
        return tuple(dict.fromkeys(blockers))


__all__ = [
    "CWS_MARK_STALE_FACE_REPORT", "CWS_MARK_CONTACT_NOT_VERIFIED",
    "CWS_MARK_FACE_UNSUITABLE", "CWS_MARK_OUTSIDE_FACE",
    "CWS_MARK_EDGE_CLEARANCE", "CWS_MARK_EXCLUSION", "CWS_MARK_LENGTH",
    "CWS_MARK_ZERO_LENGTH", "CWS_MARK_CONTACT_AREA", "CWS_MARK_CONTACT_WRONG_PART",
    "ContactScribingEngine", "MarkSetValidator",
]
