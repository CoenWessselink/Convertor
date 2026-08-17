"""Independent M6 transform/evidence validator.

This module intentionally does not call NestingMarkBinder transform helpers.
It reconstructs face-local -> part -> stock coordinates from raw frame/matrix
values so a shared implementation error cannot make the M6 gate self-validating.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable

from .faces_model import FaceResolutionReport, ManufacturingFace
from .identification_model import IdentificationSet
from .machine_capability_model import MachineCapabilityReport
from .marking_model import MarkSet
from .nesting_binding_model import NestedFeatureKind, NestingMarkingReport, NestingPlacement

CWS_NEST_VALIDATION_EVIDENCE = "CWS-NEST-VAL-001"
CWS_NEST_VALIDATION_FEATURE_SET = "CWS-NEST-VAL-002"
CWS_NEST_VALIDATION_COORDINATES = "CWS-NEST-VAL-003"
CWS_NEST_VALIDATION_DECISION = "CWS-NEST-VAL-004"
CWS_NEST_VALIDATION_INSTANCE = "CWS-NEST-VAL-005"


def _point3(value: Iterable[float]) -> tuple[float, float, float]:
    items = tuple(float(item) for item in value)
    if len(items) != 3 or not all(math.isfinite(item) for item in items):
        raise ValueError("Validator verwacht drie eindige coordinaten")
    return items


def _face_to_part(face: ManufacturingFace, point2: Iterable[float]) -> tuple[float, float, float]:
    uv = tuple(float(item) for item in point2)
    if len(uv) != 2:
        raise ValueError("Validator verwacht twee face-local coordinaten")
    origin = face.local_frame.origin_mm
    u_axis = face.local_frame.u_axis
    v_axis = face.local_frame.v_axis
    return tuple(origin[i] + uv[0] * u_axis[i] + uv[1] * v_axis[i] for i in range(3))


def _part_to_stock(placement: NestingPlacement, point: Iterable[float]) -> tuple[float, float, float]:
    xyz = _point3(point)
    matrix = placement.part_to_stock.matrix
    result = []
    for row in range(3):
        result.append(
            float(matrix[row][0]) * xyz[0]
            + float(matrix[row][1]) * xyz[1]
            + float(matrix[row][2]) * xyz[2]
            + float(matrix[row][3])
        )
    return tuple(result)


def _expected_stock(face: ManufacturingFace, placement: NestingPlacement, point2: Iterable[float]):
    return _part_to_stock(placement, _face_to_part(face, point2))


def _error(actual: Iterable[float], expected: Iterable[float]) -> float:
    return math.dist(_point3(actual), _point3(expected))


@dataclass(frozen=True, slots=True)
class NestingValidationResult:
    passed: bool
    blocking_codes: tuple[str, ...]
    maximum_coordinate_error_mm: float
    checked_features: int
    checked_points: int
    details: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": bool(self.passed),
            "blocking_codes": list(self.blocking_codes),
            "maximum_coordinate_error_mm": float(self.maximum_coordinate_error_mm),
            "checked_features": int(self.checked_features),
            "checked_points": int(self.checked_points),
            "details": list(self.details),
        }


class IndependentNestingMarkValidator:
    def __init__(self, *, tolerance_mm: float = 1e-7) -> None:
        if not math.isfinite(float(tolerance_mm)) or float(tolerance_mm) <= 0.0:
            raise ValueError("Validator tolerance_mm moet positief zijn")
        self.tolerance_mm = float(tolerance_mm)

    def validate(
        self,
        report: NestingMarkingReport,
        *,
        placement: NestingPlacement,
        face_report: FaceResolutionReport,
        machine_capability: MachineCapabilityReport,
        mark_set: MarkSet | None = None,
        identification_set: IdentificationSet | None = None,
    ) -> NestingValidationResult:
        blockers: list[str] = []
        details: list[str] = []
        maximum_error = 0.0
        checked_points = 0

        if (
            report.placement_sha256 != placement.placement_sha256
            or report.face_report_sha256 != face_report.report_sha256
            or report.machine_capability_sha256 != machine_capability.report_sha256
            or report.mark_set_sha256 != ("" if mark_set is None else mark_set.report_sha256)
            or report.identification_set_sha256
            != ("" if identification_set is None else identification_set.report_sha256)
        ):
            blockers.append(CWS_NEST_VALIDATION_EVIDENCE)
        if (
            report.part_id != placement.part_id
            or report.production_instance_id != placement.production_instance_id
            or report.stock_id != placement.stock_id
            or report.nesting_run_id != placement.nesting_run_id
        ):
            blockers.append(CWS_NEST_VALIDATION_INSTANCE)

        faces = {face.face_id: face for face in face_report.faces}
        decisions = {item.feature_id: item for item in machine_capability.decisions}
        nested = {item.source_feature_id: item for item in report.features}
        expected_ids: list[str] = []
        if mark_set is not None:
            expected_ids.extend(item.mark_id for item in mark_set.features)
        if identification_set is not None:
            expected_ids.extend(item.intent_id for item in identification_set.hole_references)
            expected_ids.extend(item.intent_id for item in identification_set.text_intents)
        if set(expected_ids) != set(nested) or len(expected_ids) != len(report.features):
            blockers.append(CWS_NEST_VALIDATION_FEATURE_SET)

        def compare(source_id: str, face_id: str, kind: NestedFeatureKind, pairs: list[tuple[Any, Any]]) -> None:
            nonlocal maximum_error, checked_points
            feature = nested.get(source_id)
            face = faces.get(face_id)
            if feature is None or face is None or feature.feature_kind != kind:
                blockers.append(CWS_NEST_VALIDATION_FEATURE_SET)
                return
            decision = decisions.get(source_id)
            if decision is None:
                if feature.machine_decision_sha256:
                    blockers.append(CWS_NEST_VALIDATION_DECISION)
            elif feature.machine_decision_sha256 != decision.decision_sha256:
                blockers.append(CWS_NEST_VALIDATION_DECISION)
            for actual, expected in pairs:
                current = _error(actual, expected)
                maximum_error = max(maximum_error, current)
                checked_points += 1
                if current > self.tolerance_mm:
                    blockers.append(CWS_NEST_VALIDATION_COORDINATES)
                    details.append(f"{source_id}: coordinate error {current:.9g} mm")

        if mark_set is not None:
            for source in mark_set.features:
                face = faces.get(source.face_id)
                if face is None:
                    blockers.append(CWS_NEST_VALIDATION_FEATURE_SET)
                    continue
                feature = nested.get(source.mark_id)
                if feature is None:
                    blockers.append(CWS_NEST_VALIDATION_FEATURE_SET)
                    continue
                geometry = feature.geometry_stock_mm
                compare(
                    source.mark_id,
                    source.face_id,
                    NestedFeatureKind.SCRIBE_SEGMENT,
                    [
                        (geometry.get("start_stock_mm", (math.inf,) * 3), _expected_stock(face, placement, source.segment.start)),
                        (geometry.get("end_stock_mm", (math.inf,) * 3), _expected_stock(face, placement, source.segment.end)),
                    ],
                )

        if identification_set is not None:
            for source in identification_set.hole_references:
                face = faces.get(source.input.face_id)
                feature = nested.get(source.intent_id)
                if face is None or feature is None:
                    blockers.append(CWS_NEST_VALIDATION_FEATURE_SET)
                    continue
                geometry = feature.geometry_stock_mm
                pairs: list[tuple[Any, Any]] = [
                    (
                        geometry.get("center_stock_mm", (math.inf,) * 3),
                        _expected_stock(face, placement, source.input.center_2d),
                    )
                ]
                actual_cross = list(geometry.get("cross_segments_stock_mm", []))
                source_cross = list(source.cross_segments())
                if len(actual_cross) != len(source_cross):
                    blockers.append(CWS_NEST_VALIDATION_COORDINATES)
                else:
                    for actual_segment, source_segment in zip(actual_cross, source_cross):
                        pairs.extend(
                            [
                                (actual_segment[0], _expected_stock(face, placement, source_segment[0])),
                                (actual_segment[1], _expected_stock(face, placement, source_segment[1])),
                            ]
                        )
                compare(source.intent_id, source.input.face_id, NestedFeatureKind.HOLE_REFERENCE, pairs)

            for source in identification_set.text_intents:
                face = faces.get(source.request.face_id)
                feature = nested.get(source.intent_id)
                if face is None or feature is None:
                    blockers.append(CWS_NEST_VALIDATION_FEATURE_SET)
                    continue
                geometry = feature.geometry_stock_mm
                pairs = [
                    (
                        geometry.get("anchor_stock_mm", (math.inf,) * 3),
                        _expected_stock(face, placement, source.request.anchor_2d),
                    )
                ]
                actual_footprint = list(geometry.get("footprint_stock_mm", []))
                if len(actual_footprint) != len(source.footprint_2d):
                    blockers.append(CWS_NEST_VALIDATION_COORDINATES)
                else:
                    pairs.extend(
                        (actual, _expected_stock(face, placement, source_point))
                        for actual, source_point in zip(actual_footprint, source.footprint_2d)
                    )
                compare(source.intent_id, source.request.face_id, NestedFeatureKind.IDENTIFICATION_TEXT, pairs)

        blockers = list(dict.fromkeys(blockers))
        return NestingValidationResult(
            passed=not blockers,
            blocking_codes=tuple(blockers),
            maximum_coordinate_error_mm=maximum_error,
            checked_features=len(report.features),
            checked_points=checked_points,
            details=tuple(details),
        )


__all__ = [
    "CWS_NEST_VALIDATION_EVIDENCE", "CWS_NEST_VALIDATION_FEATURE_SET",
    "CWS_NEST_VALIDATION_COORDINATES", "CWS_NEST_VALIDATION_DECISION",
    "CWS_NEST_VALIDATION_INSTANCE", "NestingValidationResult",
    "IndependentNestingMarkValidator",
]
