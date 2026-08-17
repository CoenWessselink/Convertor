"""M6 late binding of canonical marking intents into stock coordinates."""
from __future__ import annotations

import math
from typing import Any, Iterable

from cws_convertor.project.model import Part, stable_sha256

from .faces_model import FaceResolutionReport, ManufacturingFace
from .identification_model import IdentificationSet
from .machine_capability_model import MachineCapabilityReport, MachineFeatureDecision, MachineFeatureType
from .marking_model import MarkSet
from .nesting_binding_model import (
    CommonCutZone,
    NestedFeatureKind,
    NestedFeatureStatus,
    NestedManufacturingFeature,
    NestingMarkingReport,
    NestingPlacement,
    StockClampZone,
)

CWS_NEST_PLACEMENT_STALE = "CWS-NEST-001"
CWS_NEST_EVIDENCE_STALE = "CWS-NEST-002"
CWS_NEST_MACHINE_CAPABILITY = "CWS-NEST-003"
CWS_NEST_FACE_MISSING = "CWS-NEST-004"
CWS_NEST_CLAMP_CONFLICT = "CWS-NEST-005"
CWS_NEST_COMMON_CUT_CONFLICT = "CWS-NEST-006"
CWS_NEST_COMMON_CUT_UNVERIFIED = "CWS-NEST-007"
CWS_NEST_MACHINE_DECISION_MISSING = "CWS-NEST-008"
CWS_NEST_MACHINE_DECISION_BLOCKED = "CWS-NEST-009"


def _segment_intersects_box(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
    clearance: float,
) -> bool:
    expanded_min = tuple(float(minimum[i]) - float(clearance) for i in range(3))
    expanded_max = tuple(float(maximum[i]) + float(clearance) for i in range(3))
    direction = tuple(float(end[i]) - float(start[i]) for i in range(3))
    lower, upper = 0.0, 1.0
    for axis in range(3):
        if abs(direction[axis]) <= 1e-15:
            if start[axis] < expanded_min[axis] or start[axis] > expanded_max[axis]:
                return False
            continue
        left = (expanded_min[axis] - start[axis]) / direction[axis]
        right = (expanded_max[axis] - start[axis]) / direction[axis]
        if left > right:
            left, right = right, left
        lower = max(lower, left)
        upper = min(upper, right)
        if lower > upper:
            return False
    return True


def _polyline_segments(points: Iterable[tuple[float, float, float]], *, closed: bool = False):
    values = list(points)
    if closed and values and values[0] != values[-1]:
        values.append(values[0])
    return tuple((values[index], values[index + 1]) for index in range(max(0, len(values) - 1)))


def _geometry_segments(kind: NestedFeatureKind, geometry: dict[str, Any]):
    def point(value: Any) -> tuple[float, float, float]:
        values = tuple(float(item) for item in value)
        if len(values) != 3:
            raise ValueError("Nested featurepunt moet drie coordinaten hebben")
        return values

    if kind == NestedFeatureKind.SCRIBE_SEGMENT:
        return ((point(geometry["start_stock_mm"]), point(geometry["end_stock_mm"])),)
    if kind == NestedFeatureKind.HOLE_REFERENCE:
        return tuple(
            (point(item[0]), point(item[1]))
            for item in geometry.get("cross_segments_stock_mm", [])
        )
    footprint = tuple(point(item) for item in geometry.get("footprint_stock_mm", []))
    return _polyline_segments(footprint, closed=True)


def _rotate_face_axes(face: ManufacturingFace, angle_deg: float) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    radians = math.radians(float(angle_deg))
    c, s = math.cos(radians), math.sin(radians)
    u, v = face.local_frame.u_axis, face.local_frame.v_axis
    baseline = tuple(c * u[i] + s * v[i] for i in range(3))
    upright = tuple(-s * u[i] + c * v[i] for i in range(3))
    return baseline, upright


class NestingMarkBinder:
    """Bind M3/M4 intents to one explicit physical nesting instance."""

    def __init__(self, placement: NestingPlacement) -> None:
        self.placement = placement

    @staticmethod
    def _faces(report: FaceResolutionReport) -> dict[str, ManufacturingFace]:
        return {face.face_id: face for face in report.faces}

    @staticmethod
    def _decisions(report: MachineCapabilityReport) -> dict[str, MachineFeatureDecision]:
        return {decision.feature_id: decision for decision in report.decisions}

    def _geometry_for_scribe(self, source: Any, face: ManufacturingFace) -> dict[str, Any]:
        start_part = face.local_frame.from_local(*source.segment.start)
        end_part = face.local_frame.from_local(*source.segment.end)
        return {
            "start_stock_mm": list(self.placement.point_to_stock(start_part)),
            "end_stock_mm": list(self.placement.point_to_stock(end_part)),
            "face_u_stock": list(self.placement.vector_to_stock(face.local_frame.u_axis)),
            "face_v_stock": list(self.placement.vector_to_stock(face.local_frame.v_axis)),
            "face_normal_stock": list(self.placement.vector_to_stock(face.local_frame.normal)),
        }

    def _geometry_for_hole_reference(self, source: Any, face: ManufacturingFace) -> dict[str, Any]:
        center_part = face.local_frame.from_local(*source.input.center_2d)
        cross = []
        for start, end in source.cross_segments():
            cross.append(
                [
                    list(self.placement.point_to_stock(face.local_frame.from_local(*start))),
                    list(self.placement.point_to_stock(face.local_frame.from_local(*end))),
                ]
            )
        return {
            "center_stock_mm": list(self.placement.point_to_stock(center_part)),
            "cross_segments_stock_mm": cross,
            "source_hole_id": source.input.source_hole_id,
            "hole_diameter_mm": float(source.input.diameter_mm),
            "face_normal_stock": list(self.placement.vector_to_stock(face.local_frame.normal)),
        }

    def _geometry_for_text(self, source: Any, face: ManufacturingFace) -> dict[str, Any]:
        anchor_part = face.local_frame.from_local(*source.request.anchor_2d)
        footprint_stock = [
            list(self.placement.point_to_stock(face.local_frame.from_local(*point)))
            for point in source.footprint_2d
        ]
        baseline, upright = _rotate_face_axes(face, source.effective_rotation_deg)
        return {
            "anchor_stock_mm": list(self.placement.point_to_stock(anchor_part)),
            "footprint_stock_mm": footprint_stock,
            "baseline_axis_stock": list(self.placement.vector_to_stock(baseline)),
            "upright_axis_stock": list(self.placement.vector_to_stock(upright)),
            "face_normal_stock": list(self.placement.vector_to_stock(face.local_frame.normal)),
            "text": source.request.text,
            "text_height_mm": float(source.request.text_height_mm),
            "readability_policy": source.request.readability_policy.value,
            "mirror_text_geometry": bool(source.mirror_text_geometry),
            "mirror_compensated": bool(source.mirror_compensated),
        }

    def _interactions(
        self,
        kind: NestedFeatureKind,
        geometry: dict[str, Any],
        clamps: tuple[StockClampZone, ...],
        common_cuts: tuple[CommonCutZone, ...],
    ) -> tuple[list[str], list[str], list[str]]:
        blockers: list[str] = []
        conflicts: list[str] = []
        warnings: list[str] = []
        segments = _geometry_segments(kind, geometry)
        for zone in clamps:
            if zone.stock_id != self.placement.stock_id:
                continue
            if any(
                _segment_intersects_box(start, end, zone.minimum_stock_mm, zone.maximum_stock_mm, zone.clearance_mm)
                for start, end in segments
            ):
                blockers.append(CWS_NEST_CLAMP_CONFLICT)
                conflicts.append(zone.zone_id)
        for zone in common_cuts:
            if zone.stock_id != self.placement.stock_id:
                continue
            if self.placement.production_instance_id not in zone.member_production_instance_ids:
                continue
            if not zone.exact_geometry:
                blockers.append(CWS_NEST_COMMON_CUT_UNVERIFIED)
                conflicts.append(zone.common_cut_id)
                warnings.append("Common-cut interactie is niet exact bewezen; feature blijft geblokkeerd.")
                continue
            if any(
                _segment_intersects_box(start, end, zone.minimum_stock_mm, zone.maximum_stock_mm, zone.clearance_mm)
                for start, end in segments
            ):
                blockers.append(CWS_NEST_COMMON_CUT_CONFLICT)
                conflicts.append(zone.common_cut_id)
        return blockers, conflicts, warnings

    def _feature(
        self,
        *,
        source: Any,
        kind: NestedFeatureKind,
        face: ManufacturingFace | None,
        decision: MachineFeatureDecision | None,
        clamps: tuple[StockClampZone, ...],
        common_cuts: tuple[CommonCutZone, ...],
    ) -> NestedManufacturingFeature:
        blockers: list[str] = []
        warnings: list[str] = []
        conflicts: list[str] = []
        if face is None:
            blockers.append(CWS_NEST_FACE_MISSING)
            geometry: dict[str, Any] = {"unbound_reason": "canonical_face_missing"}
        elif kind == NestedFeatureKind.SCRIBE_SEGMENT:
            geometry = self._geometry_for_scribe(source, face)
        elif kind == NestedFeatureKind.HOLE_REFERENCE:
            geometry = self._geometry_for_hole_reference(source, face)
        else:
            geometry = self._geometry_for_text(source, face)

        if decision is None:
            blockers.append(CWS_NEST_MACHINE_DECISION_MISSING)
        elif not decision.supported:
            blockers.append(CWS_NEST_MACHINE_DECISION_BLOCKED)
            blockers.extend(decision.blocking_codes)

        if face is not None:
            interaction_blockers, interaction_conflicts, interaction_warnings = self._interactions(
                kind, geometry, clamps, common_cuts
            )
            blockers.extend(interaction_blockers)
            conflicts.extend(interaction_conflicts)
            warnings.extend(interaction_warnings)

        blockers = list(dict.fromkeys(blockers))
        status = NestedFeatureStatus.BLOCKED if blockers else NestedFeatureStatus.BOUND
        source_id = str(getattr(source, "mark_id", "") or getattr(source, "intent_id", ""))
        source_hash = str(getattr(source, "feature_sha256", "") or getattr(source, "intent_sha256", ""))
        feature_id = "NEST-" + stable_sha256(
            {
                "placement": self.placement.placement_sha256,
                "source_id": source_id,
                "source_hash": source_hash,
                "kind": kind.value,
            }
        )[:20].upper()
        return NestedManufacturingFeature(
            feature_id=feature_id,
            source_feature_id=source_id,
            source_intent_sha256=source_hash,
            feature_kind=kind,
            part_id=self.placement.part_id,
            production_instance_id=self.placement.production_instance_id,
            stock_id=self.placement.stock_id,
            face_id=str(
                getattr(source, "face_id", "")
                or getattr(getattr(source, "input", None), "face_id", "")
                or getattr(getattr(source, "request", None), "face_id", "")
            ),
            geometry_stock_mm=geometry,
            machine_decision_sha256="" if decision is None else decision.decision_sha256,
            status=status,
            conflict_zone_ids=tuple(conflicts),
            warnings=tuple(warnings),
            blocking_codes=tuple(blockers),
        )

    def build(
        self,
        part: Part,
        face_report: FaceResolutionReport,
        machine_capability: MachineCapabilityReport,
        *,
        mark_set: MarkSet | None = None,
        identification_set: IdentificationSet | None = None,
        clamp_zones: Iterable[StockClampZone] = (),
        common_cut_zones: Iterable[CommonCutZone] = (),
    ) -> NestingMarkingReport:
        blockers: list[str] = []
        warnings: list[str] = []
        clamps = tuple(clamp_zones)
        common_cuts = tuple(common_cut_zones)

        if self.placement.part_id != part.internal_id or self.placement.manufacturing_hash != part.manufacturing_hash:
            blockers.append(CWS_NEST_PLACEMENT_STALE)
        if face_report.part_id != part.internal_id or face_report.manufacturing_hash != part.manufacturing_hash:
            blockers.append(CWS_NEST_EVIDENCE_STALE)
        if mark_set is not None and (
            mark_set.part_id != part.internal_id or mark_set.manufacturing_hash != part.manufacturing_hash
        ):
            blockers.append(CWS_NEST_EVIDENCE_STALE)
        if identification_set is not None and (
            identification_set.part_id != part.internal_id
            or identification_set.manufacturing_hash != part.manufacturing_hash
        ):
            blockers.append(CWS_NEST_EVIDENCE_STALE)
        if (
            machine_capability.part_id != part.internal_id
            or machine_capability.manufacturing_hash != part.manufacturing_hash
            or not machine_capability.ready_for_neutral_job
        ):
            blockers.append(CWS_NEST_MACHINE_CAPABILITY)

        faces = self._faces(face_report)
        decisions = self._decisions(machine_capability)
        features: list[NestedManufacturingFeature] = []
        if mark_set is not None:
            for source in sorted(mark_set.features, key=lambda item: item.mark_id):
                features.append(
                    self._feature(
                        source=source,
                        kind=NestedFeatureKind.SCRIBE_SEGMENT,
                        face=faces.get(source.face_id),
                        decision=decisions.get(source.mark_id),
                        clamps=clamps,
                        common_cuts=common_cuts,
                    )
                )
        if identification_set is not None:
            for source in sorted(identification_set.hole_references, key=lambda item: item.intent_id):
                features.append(
                    self._feature(
                        source=source,
                        kind=NestedFeatureKind.HOLE_REFERENCE,
                        face=faces.get(source.input.face_id),
                        decision=decisions.get(source.intent_id),
                        clamps=clamps,
                        common_cuts=common_cuts,
                    )
                )
            for source in sorted(identification_set.text_intents, key=lambda item: item.intent_id):
                features.append(
                    self._feature(
                        source=source,
                        kind=NestedFeatureKind.IDENTIFICATION_TEXT,
                        face=faces.get(source.request.face_id),
                        decision=decisions.get(source.intent_id),
                        clamps=clamps,
                        common_cuts=common_cuts,
                    )
                )

        for feature in features:
            blockers.extend(feature.blocking_codes)
            warnings.extend(feature.warnings)
        blockers = list(dict.fromkeys(blockers))
        return NestingMarkingReport.create(
            part_id=part.internal_id,
            manufacturing_hash=part.manufacturing_hash,
            production_instance_id=self.placement.production_instance_id,
            assembly_id=self.placement.assembly_id,
            assembly_mark=self.placement.assembly_mark,
            nesting_run_id=self.placement.nesting_run_id,
            stock_id=self.placement.stock_id,
            placement_sha256=self.placement.placement_sha256,
            face_report_sha256=face_report.report_sha256,
            mark_set_sha256="" if mark_set is None else mark_set.report_sha256,
            identification_set_sha256="" if identification_set is None else identification_set.report_sha256,
            machine_capability_sha256=machine_capability.report_sha256,
            clamp_zone_sha256s=tuple(zone.zone_sha256 for zone in clamps if zone.stock_id == self.placement.stock_id),
            common_cut_zone_sha256s=tuple(zone.zone_sha256 for zone in common_cuts if zone.stock_id == self.placement.stock_id),
            features=tuple(features),
            blocking_codes=tuple(blockers),
            warnings=tuple(dict.fromkeys(warnings)),
        )


__all__ = [
    "CWS_NEST_PLACEMENT_STALE", "CWS_NEST_EVIDENCE_STALE",
    "CWS_NEST_MACHINE_CAPABILITY", "CWS_NEST_FACE_MISSING",
    "CWS_NEST_CLAMP_CONFLICT", "CWS_NEST_COMMON_CUT_CONFLICT",
    "CWS_NEST_COMMON_CUT_UNVERIFIED", "CWS_NEST_MACHINE_DECISION_MISSING",
    "CWS_NEST_MACHINE_DECISION_BLOCKED", "NestingMarkBinder",
]
