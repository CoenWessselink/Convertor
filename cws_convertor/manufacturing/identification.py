"""M4 explicit hole references and identification planning."""
from __future__ import annotations

import math
from typing import Iterable

from cws_convertor.project.model import Part, stable_sha256

from .faces_model import FaceProofStatus, FaceResolutionReport, ManufacturingFace, SurfaceType
from .identification_model import (
    HoleReferenceInput,
    HoleReferenceMark,
    IdentificationRuleSet,
    IdentificationSet,
    IdentificationStatus,
    IdentificationTextIntent,
    IdentificationTextRequest,
    ReadabilityPolicy,
)
from .marking import _distance_to_loop, _outer_and_voids, _point_in_polygon, _point_on_loop
from .marking_model import MarkSet

CWS_ID_STALE_EVIDENCE = "CWS-MARK-101"
CWS_ID_FACE_MISSING = "CWS-MARK-102"
CWS_ID_FACE_UNSUITABLE = "CWS-MARK-103"
CWS_ID_OUTSIDE_FACE = "CWS-MARK-104"
CWS_ID_EDGE_CLEARANCE = "CWS-MARK-105"
CWS_ID_TEXT_SIZE = "CWS-MARK-106"
CWS_ID_TEXT_LENGTH = "CWS-MARK-107"
CWS_ID_PART_MISMATCH = "CWS-MARK-108"


def _normalise_rotation(angle: float, policy: ReadabilityPolicy) -> float:
    value = float(angle) % 360.0
    if value > 180.0:
        value -= 360.0
    if policy == ReadabilityPolicy.KEEP_READABLE:
        if value > 90.0:
            value -= 180.0
        elif value < -90.0:
            value += 180.0
    return round(value, 9)


def _rotate(point: tuple[float, float], angle_deg: float) -> tuple[float, float]:
    radians = math.radians(angle_deg)
    c, s = math.cos(radians), math.sin(radians)
    return (point[0] * c - point[1] * s, point[0] * s + point[1] * c)


def _text_footprint(request: IdentificationTextRequest, effective_rotation_deg: float) -> tuple[tuple[float, float], ...]:
    # Geometry is an intent footprint, not a font outline. The adapter that
    # ultimately owns a proven machine font must render within this footprint.
    height = float(request.text_height_mm)
    width = max(height, height * 0.65 * len(request.text))
    half_w, half_h = width * 0.5, height * 0.5
    local = ((-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h))
    anchor = request.anchor_2d
    result = []
    for point in local:
        rotated = _rotate(point, effective_rotation_deg)
        result.append((anchor[0] + rotated[0], anchor[1] + rotated[1]))
    return tuple(result)


def _point_valid_on_face(point: tuple[float, float], face: ManufacturingFace, tolerance: float) -> bool:
    outer, voids = _outer_and_voids(face)
    if outer is None or not _point_in_polygon(point, outer, tolerance):
        return False
    for void in voids:
        if _point_in_polygon(point, void, tolerance) and not _point_on_loop(point, void, tolerance):
            return False
    return True


def _minimum_outer_clearance(points: Iterable[tuple[float, float]], face: ManufacturingFace) -> float:
    outer, _voids = _outer_and_voids(face)
    if outer is None:
        return 0.0
    return min((_distance_to_loop(point, outer) for point in points), default=0.0)


def _intent_id(prefix: str, payload: dict) -> str:
    return prefix + "-" + stable_sha256(payload)[:20].upper()


class IdentificationPlanner:
    """Validate explicit M4 intents against canonical face geometry."""

    def __init__(self, ruleset: IdentificationRuleSet | None = None) -> None:
        self.ruleset = ruleset or IdentificationRuleSet()

    @staticmethod
    def _faces(report: FaceResolutionReport) -> dict[str, ManufacturingFace]:
        return {item.face_id: item for item in report.faces}

    def _base_status(self, face: ManufacturingFace, blockers: list[str], warnings: list[str]) -> IdentificationStatus:
        if face.surface_type != SurfaceType.PLANE:
            blockers.append(CWS_ID_FACE_UNSUITABLE)
        if face.proof_status == FaceProofStatus.BLOCKED:
            blockers.append(CWS_ID_FACE_UNSUITABLE)
        elif face.proof_status == FaceProofStatus.REVIEW_REQUIRED:
            warnings.append("ManufacturingFace semantic role vereist review.")
        if blockers:
            return IdentificationStatus.BLOCKED
        if face.proof_status == FaceProofStatus.REVIEW_REQUIRED:
            return IdentificationStatus.REVIEW_REQUIRED
        return IdentificationStatus.ACCEPTED

    def _hole(self, part: Part, face: ManufacturingFace | None, request: HoleReferenceInput) -> HoleReferenceMark:
        blockers: list[str] = []
        warnings: list[str] = []
        if request.part_id != part.internal_id:
            blockers.append(CWS_ID_PART_MISMATCH)
        if face is None:
            blockers.append(CWS_ID_FACE_MISSING)
            status = IdentificationStatus.BLOCKED
        else:
            arm = float(self.ruleset.default_cross_arm_mm)
            x, y = request.center_2d
            probes = ((x - arm, y), (x + arm, y), (x, y - arm), (x, y + arm))
            if not all(_point_valid_on_face(point, face, self.ruleset.point_tolerance_mm) for point in probes):
                blockers.append(CWS_ID_OUTSIDE_FACE)
            clearance = _minimum_outer_clearance((*probes, request.center_2d), face)
            required_clearance = max(
                float(self.ruleset.edge_clearance_mm),
                float(request.diameter_mm) * 0.5 + float(self.ruleset.hole_clearance_mm),
            )
            if clearance + self.ruleset.point_tolerance_mm < required_clearance:
                blockers.append(CWS_ID_EDGE_CLEARANCE)
            status = self._base_status(face, blockers, warnings)
        arm = float(self.ruleset.default_cross_arm_mm)
        intent_id = _intent_id(
            "HOLE-REF",
            {"request": request.to_dict(), "ruleset": self.ruleset.ruleset_sha256, "arm": arm},
        )
        return HoleReferenceMark(
            intent_id=intent_id,
            input=request,
            cross_arm_mm=arm,
            status=status,
            ruleset_sha256=self.ruleset.ruleset_sha256,
            warnings=tuple(warnings),
            blocking_codes=tuple(blockers),
        )

    def _text(self, part: Part, face: ManufacturingFace | None, request: IdentificationTextRequest) -> IdentificationTextIntent:
        blockers: list[str] = []
        warnings: list[str] = []
        if request.part_id != part.internal_id:
            blockers.append(CWS_ID_PART_MISMATCH)
        if not self.ruleset.min_text_height_mm <= request.text_height_mm <= self.ruleset.max_text_height_mm:
            blockers.append(CWS_ID_TEXT_SIZE)
        if len(request.text) > self.ruleset.max_text_characters:
            blockers.append(CWS_ID_TEXT_LENGTH)

        effective = _normalise_rotation(request.rotation_deg, request.readability_policy)
        mirror_compensated = bool(part.mirrored and request.readability_policy == ReadabilityPolicy.KEEP_READABLE)
        # A readable manufacturing text intent is never geometrically mirrored.
        # A downstream adapter may rotate/place it, but may not reverse glyphs.
        mirror_text_geometry = bool(part.mirrored and request.readability_policy == ReadabilityPolicy.FIXED_ORIENTATION)
        if mirror_compensated:
            warnings.append("Mirrored part: text mirror is suppressed to preserve readability.")
        footprint = _text_footprint(request, effective)

        if face is None:
            blockers.append(CWS_ID_FACE_MISSING)
            status = IdentificationStatus.BLOCKED
        else:
            if not all(_point_valid_on_face(point, face, self.ruleset.point_tolerance_mm) for point in footprint):
                blockers.append(CWS_ID_OUTSIDE_FACE)
            clearance = _minimum_outer_clearance(footprint, face)
            if clearance + self.ruleset.point_tolerance_mm < self.ruleset.edge_clearance_mm:
                blockers.append(CWS_ID_EDGE_CLEARANCE)
            status = self._base_status(face, blockers, warnings)

        intent_id = _intent_id(
            "TEXT",
            {
                "request": request.to_dict(),
                "effective_rotation_deg": effective,
                "mirror_text_geometry": mirror_text_geometry,
                "mirror_compensated": mirror_compensated,
                "footprint": footprint,
                "ruleset": self.ruleset.ruleset_sha256,
            },
        )
        return IdentificationTextIntent(
            intent_id=intent_id,
            request=request,
            effective_rotation_deg=effective,
            mirror_text_geometry=mirror_text_geometry,
            mirror_compensated=mirror_compensated,
            footprint_2d=footprint,
            status=status,
            ruleset_sha256=self.ruleset.ruleset_sha256,
            warnings=tuple(warnings),
            blocking_codes=tuple(blockers),
        )

    def build(
        self,
        part: Part,
        face_report: FaceResolutionReport,
        *,
        mark_set: MarkSet | None = None,
        hole_references: Iterable[HoleReferenceInput] = (),
        text_requests: Iterable[IdentificationTextRequest] = (),
    ) -> IdentificationSet:
        if not part.manufacturing_hash:
            raise ValueError("M4 identification vereist manufacturing_hash")
        blockers: list[str] = []
        warnings: list[str] = []
        if face_report.part_id != part.internal_id or face_report.manufacturing_hash != part.manufacturing_hash:
            blockers.append(CWS_ID_STALE_EVIDENCE)
        if mark_set is not None and (
            mark_set.part_id != part.internal_id or mark_set.manufacturing_hash != part.manufacturing_hash
        ):
            blockers.append(CWS_ID_STALE_EVIDENCE)
        faces = self._faces(face_report)
        holes = tuple(
            self._hole(part, faces.get(request.face_id), request)
            for request in sorted(hole_references, key=lambda item: item.reference_id)
        )
        texts = tuple(
            self._text(part, faces.get(request.face_id), request)
            for request in sorted(text_requests, key=lambda item: item.request_id)
        )
        for item in holes:
            blockers.extend(item.blocking_codes)
            warnings.extend(item.warnings)
        for item in texts:
            blockers.extend(item.blocking_codes)
            warnings.extend(item.warnings)
        return IdentificationSet.create(
            part_id=part.internal_id,
            manufacturing_hash=part.manufacturing_hash,
            face_report_sha256=face_report.report_sha256,
            mark_set_sha256="" if mark_set is None else mark_set.report_sha256,
            ruleset_sha256=self.ruleset.ruleset_sha256,
            hole_references=holes,
            text_intents=texts,
            blocking_codes=tuple(dict.fromkeys(blockers)),
            warnings=tuple(dict.fromkeys(warnings)),
        )


__all__ = [
    "CWS_ID_STALE_EVIDENCE", "CWS_ID_FACE_MISSING", "CWS_ID_FACE_UNSUITABLE",
    "CWS_ID_OUTSIDE_FACE", "CWS_ID_EDGE_CLEARANCE", "CWS_ID_TEXT_SIZE",
    "CWS_ID_TEXT_LENGTH", "CWS_ID_PART_MISMATCH", "IdentificationPlanner",
]
