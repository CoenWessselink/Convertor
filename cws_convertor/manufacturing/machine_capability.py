"""M5 fail-closed machine capability and reachability evaluator.

The existing CWS capability vocabulary owns the generic machine operation
``mark``. M5 deepens that operation with explicit mark types, canonical-face
reachability, head clearance, tool limits and ruleset compatibility. It does
not invent controller operations and it never enables machine transfer.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from cws_convertor.project.model import MachineProfile, Part, stable_sha256

from .faces_model import FaceResolutionReport, ManufacturingFace
from .identification_model import IdentificationSet, IdentificationStatus
from .machine_capability_model import (
    CapabilityStatus,
    MachineCapabilityReport,
    MachineFeatureDecision,
    MachineFeatureType,
)
from .marking_model import MarkSet, MarkStatus

CWS_MACHINE_STALE_EVIDENCE = "CWS-MACHINE-001"
CWS_MACHINE_OPERATION_UNSUPPORTED = "CWS-MACHINE-002"
CWS_MACHINE_TOOL_MISSING = "CWS-MACHINE-003"
CWS_MACHINE_REACHABILITY_UNKNOWN = "CWS-MACHINE-004"
CWS_MACHINE_FACE_UNREACHABLE = "CWS-MACHINE-005"
CWS_MACHINE_LIMIT_UNKNOWN = "CWS-MACHINE-006"
CWS_MACHINE_LIMIT_EXCEEDED = "CWS-MACHINE-007"
CWS_MACHINE_TOOL_AMBIGUOUS = "CWS-MACHINE-008"
CWS_MACHINE_SOURCE_BLOCKED = "CWS-MACHINE-009"
CWS_MACHINE_PART_DIMENSION = "CWS-MACHINE-010"
CWS_MACHINE_PROFILE_IDENTITY = "CWS-MACHINE-011"
CWS_MACHINE_MARK_TYPE_UNSUPPORTED = "CWS-MACHINE-012"
CWS_MACHINE_RULESET_UNKNOWN = "CWS-MACHINE-013"
CWS_MACHINE_RULESET_INCOMPATIBLE = "CWS-MACHINE-014"
CWS_MACHINE_HEAD_CLEARANCE_UNKNOWN = "CWS-MACHINE-015"
CWS_MACHINE_HEAD_CLEARANCE = "CWS-MACHINE-016"


def _norm(value: Any) -> str:
    return "_".join(str(value or "").strip().lower().replace("-", " ").replace("/", " ").split())


def _as_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (_norm(value),) if value.strip() else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(_norm(item) for item in value if str(item or "").strip())
    return ()


def _raw_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip().lower(),) if value.strip() else ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item).strip().lower() for item in value if str(item or "").strip())
    return ()


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _tool_id(tool: dict[str, Any]) -> str:
    for key in ("tool_id", "id", "name"):
        text = str(tool.get(key) or "").strip()
        if text:
            return text
    return ""


def _tool_operations(tool: dict[str, Any]) -> tuple[str, ...]:
    return _as_strings(tool.get("operations") if "operations" in tool else tool.get("operation"))


def _machine_profile_hash(profile: MachineProfile) -> str:
    # Any machine-profile edit is new evidence and invalidates old reports.
    return stable_sha256(profile.base_to_dict())


def _dimension_limit(mapping: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key in mapping:
            return _finite(mapping[key])
    normalised = {_norm(key): value for key, value in mapping.items()}
    for key in keys:
        if _norm(key) in normalised:
            return _finite(normalised[_norm(key)])
    return None


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
    return math.dist(point, (start[0] + t * dx, start[1] + t * dy))


def _face_boundary_clearance(face: ManufacturingFace, probes: Iterable[tuple[float, float]]) -> float | None:
    edges: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for loop in face.boundary_loops_2d:
        points = list(loop)
        if len(points) < 2:
            continue
        if points[0] != points[-1]:
            points.append(points[0])
        edges.extend((points[index], points[index + 1]) for index in range(len(points) - 1))
    probe_list = list(probes)
    if not edges or not probe_list:
        return None
    return min(_point_segment_distance(point, start, end) for point in probe_list for start, end in edges)


def _source_probes(feature_type: MachineFeatureType, source: Any) -> tuple[tuple[float, float], ...]:
    if feature_type == MachineFeatureType.SCRIBE:
        return (source.segment.start, source.segment.midpoint, source.segment.end)
    if feature_type == MachineFeatureType.HOLE_REFERENCE:
        points: list[tuple[float, float]] = [source.input.center_2d]
        for start, end in source.cross_segments():
            points.extend((start, end))
        return tuple(points)
    return tuple(source.footprint_2d)


class MachineCapabilityEvaluator:
    """Prove mark feasibility from explicit machine-profile facts only."""

    MACHINE_OPERATION = "mark"

    def __init__(self, profile: MachineProfile) -> None:
        self.profile = profile
        self.profile_sha256 = _machine_profile_hash(profile)
        self.supported_operations = set(_as_strings(profile.supported_operations))
        self.tools = tuple(dict(tool) for tool in profile.tools if isinstance(tool, dict))

    @staticmethod
    def _faces(report: FaceResolutionReport) -> dict[str, ManufacturingFace]:
        return {face.face_id: face for face in report.faces}

    def _part_dimension_blockers(self, part: Part) -> tuple[str, ...]:
        blockers: list[str] = []
        minimum = dict(self.profile.min_dimensions_mm or {})
        maximum = dict(self.profile.max_dimensions_mm or {})
        min_length = _dimension_limit(minimum, "length_mm", "length", "L")
        max_length = _dimension_limit(maximum, "length_mm", "length", "L")
        if min_length is not None and float(part.length_mm) < min_length - 1e-9:
            blockers.append(CWS_MACHINE_PART_DIMENSION)
        if max_length is not None and float(part.length_mm) > max_length + 1e-9:
            blockers.append(CWS_MACHINE_PART_DIMENSION)
        return tuple(dict.fromkeys(blockers))

    @staticmethod
    def _reachability(tool: dict[str, Any], face: ManufacturingFace) -> tuple[bool | None, dict[str, Any]]:
        face_ids = _as_strings(tool.get("reachable_face_ids"))
        roles = _as_strings(tool.get("reachable_face_roles"))
        if not face_ids and not roles:
            return None, {}
        face_match = _norm(face.face_id) in set(face_ids) if face_ids else False
        role_match = _norm(face.semantic_role.value) in set(roles) if roles else False
        return bool(face_match or role_match), {
            "reachable_face_ids": list(face_ids),
            "reachable_face_roles": list(roles),
        }

    @staticmethod
    def _mark_type_supported(tool: dict[str, Any], feature_type: MachineFeatureType) -> bool | None:
        types = _as_strings(tool.get("supported_mark_types"))
        if not types:
            return None
        return _norm(feature_type.value) in set(types)

    @staticmethod
    def _ruleset_blockers(tool: dict[str, Any], source: Any) -> list[str]:
        source_hash = str(getattr(source, "ruleset_sha256", "") or "").strip().lower()
        compatible = _raw_strings(tool.get("compatible_ruleset_sha256s"))
        if not source_hash or not compatible:
            return [CWS_MACHINE_RULESET_UNKNOWN]
        if source_hash not in compatible:
            return [CWS_MACHINE_RULESET_INCOMPATIBLE]
        return []

    @staticmethod
    def _limits_for(
        feature_type: MachineFeatureType,
        source: Any,
        tool: dict[str, Any],
        face: ManufacturingFace,
    ) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        measured: dict[str, Any] = {}
        limits: dict[str, Any] = {}
        blockers: list[str] = []
        if feature_type == MachineFeatureType.SCRIBE:
            measured["segment_length_mm"] = float(source.segment.length_mm)
            minimum = _finite(tool.get("min_segment_length_mm"))
            maximum = _finite(tool.get("max_segment_length_mm"))
            if minimum is None or maximum is None:
                blockers.append(CWS_MACHINE_LIMIT_UNKNOWN)
            else:
                limits.update({"min_segment_length_mm": minimum, "max_segment_length_mm": maximum})
                if measured["segment_length_mm"] < minimum - 1e-9 or measured["segment_length_mm"] > maximum + 1e-9:
                    blockers.append(CWS_MACHINE_LIMIT_EXCEEDED)
        elif feature_type == MachineFeatureType.HOLE_REFERENCE:
            measured.update(
                {
                    "hole_diameter_mm": float(source.input.diameter_mm),
                    "cross_arm_mm": float(source.cross_arm_mm),
                }
            )
            min_arm = _finite(tool.get("min_cross_arm_mm"))
            max_arm = _finite(tool.get("max_cross_arm_mm"))
            if min_arm is None or max_arm is None:
                blockers.append(CWS_MACHINE_LIMIT_UNKNOWN)
            else:
                limits.update({"min_cross_arm_mm": min_arm, "max_cross_arm_mm": max_arm})
                if measured["cross_arm_mm"] < min_arm - 1e-9 or measured["cross_arm_mm"] > max_arm + 1e-9:
                    blockers.append(CWS_MACHINE_LIMIT_EXCEEDED)
            min_hole = _finite(tool.get("min_hole_diameter_mm"))
            max_hole = _finite(tool.get("max_hole_diameter_mm"))
            if min_hole is not None:
                limits["min_hole_diameter_mm"] = min_hole
                if measured["hole_diameter_mm"] < min_hole - 1e-9:
                    blockers.append(CWS_MACHINE_LIMIT_EXCEEDED)
            if max_hole is not None:
                limits["max_hole_diameter_mm"] = max_hole
                if measured["hole_diameter_mm"] > max_hole + 1e-9:
                    blockers.append(CWS_MACHINE_LIMIT_EXCEEDED)
        else:
            measured["text_height_mm"] = float(source.request.text_height_mm)
            if tool.get("supports_text") is not True:
                blockers.append(CWS_MACHINE_MARK_TYPE_UNSUPPORTED)
            minimum = _finite(tool.get("min_text_height_mm"))
            maximum = _finite(tool.get("max_text_height_mm"))
            if minimum is None or maximum is None:
                blockers.append(CWS_MACHINE_LIMIT_UNKNOWN)
            else:
                limits.update({"min_text_height_mm": minimum, "max_text_height_mm": maximum})
                if measured["text_height_mm"] < minimum - 1e-9 or measured["text_height_mm"] > maximum + 1e-9:
                    blockers.append(CWS_MACHINE_LIMIT_EXCEEDED)

        required_head = _finite(tool.get("minimum_head_clearance_mm"))
        actual_head = _face_boundary_clearance(face, _source_probes(feature_type, source))
        if required_head is None or actual_head is None:
            blockers.append(CWS_MACHINE_HEAD_CLEARANCE_UNKNOWN)
        else:
            measured["minimum_boundary_clearance_mm"] = float(actual_head)
            limits["minimum_head_clearance_mm"] = float(required_head)
            if actual_head + 1e-9 < required_head:
                blockers.append(CWS_MACHINE_HEAD_CLEARANCE)
        blockers.extend(MachineCapabilityEvaluator._ruleset_blockers(tool, source))
        return measured, limits, blockers

    def _decision(
        self,
        *,
        feature_type: MachineFeatureType,
        source: Any,
        source_usable: bool,
        face: ManufacturingFace | None,
        source_hash: str,
    ) -> MachineFeatureDecision:
        requested = feature_type.value
        blockers: list[str] = []
        warnings: list[str] = []
        tool_id = ""
        machine_operation = ""
        measured: dict[str, Any] = {}
        limits: dict[str, Any] = {}
        role = "" if face is None else face.semantic_role.value

        if not source_usable:
            blockers.append(CWS_MACHINE_SOURCE_BLOCKED)
        if self.MACHINE_OPERATION not in self.supported_operations:
            blockers.append(CWS_MACHINE_OPERATION_UNSUPPORTED)

        mark_tools = [tool for tool in self.tools if self.MACHINE_OPERATION in set(_tool_operations(tool))]
        if not mark_tools:
            blockers.append(CWS_MACHINE_TOOL_MISSING)
        elif face is None:
            blockers.append(CWS_MACHINE_FACE_UNREACHABLE)
        else:
            viable: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]] = []
            unknown_reach = False
            unknown_mark_type = False
            for tool in mark_tools:
                mark_type_supported = self._mark_type_supported(tool, feature_type)
                if mark_type_supported is None:
                    unknown_mark_type = True
                    continue
                if not mark_type_supported:
                    continue
                reachable, reach_evidence = self._reachability(tool, face)
                if reachable is None:
                    unknown_reach = True
                    continue
                if not reachable:
                    continue
                tool_measured, tool_limits, tool_blockers = self._limits_for(feature_type, source, tool, face)
                viable.append((tool, tool_measured, {**reach_evidence, **tool_limits}, tool_blockers))

            if not viable:
                if unknown_mark_type:
                    blockers.append(CWS_MACHINE_MARK_TYPE_UNSUPPORTED)
                elif unknown_reach:
                    blockers.append(CWS_MACHINE_REACHABILITY_UNKNOWN)
                else:
                    blockers.append(CWS_MACHINE_MARK_TYPE_UNSUPPORTED)
            else:
                fully_supported = [item for item in viable if not item[3]]
                candidates = fully_supported or viable
                if len(candidates) > 1:
                    blockers.append(CWS_MACHINE_TOOL_AMBIGUOUS)
                    warnings.append("Meerdere markeergereedschappen voldoen; expliciete toolkeuze ontbreekt.")
                else:
                    tool, measured, limits, tool_blockers = candidates[0]
                    tool_id = _tool_id(tool)
                    machine_operation = self.MACHINE_OPERATION
                    if not tool_id:
                        blockers.append(CWS_MACHINE_TOOL_MISSING)
                    blockers.extend(tool_blockers)

        blockers = list(dict.fromkeys(blockers))
        status = CapabilityStatus.BLOCKED if blockers else CapabilityStatus.SUPPORTED
        feature_id = str(
            getattr(source, "mark_id", "")
            or getattr(source, "intent_id", "")
            or getattr(source, "request_id", "")
        )
        face_id = str(
            getattr(source, "face_id", "")
            or getattr(getattr(source, "input", None), "face_id", "")
            or getattr(getattr(source, "request", None), "face_id", "")
        )
        return MachineFeatureDecision(
            feature_id=feature_id,
            feature_type=feature_type,
            face_id=face_id,
            canonical_face_role=role,
            requested_operation=requested,
            machine_operation=machine_operation,
            tool_id=tool_id,
            status=status,
            source_intent_sha256=source_hash,
            machine_profile_sha256=self.profile_sha256,
            measured=measured,
            limits=limits,
            warnings=tuple(warnings),
            blocking_codes=tuple(blockers),
        )

    def evaluate(
        self,
        part: Part,
        face_report: FaceResolutionReport,
        *,
        mark_set: MarkSet | None = None,
        identification_set: IdentificationSet | None = None,
    ) -> MachineCapabilityReport:
        blockers: list[str] = []
        warnings: list[str] = []
        if not self.profile.internal_id.strip() or not self.profile.machine_id.strip():
            blockers.append(CWS_MACHINE_PROFILE_IDENTITY)
        if face_report.part_id != part.internal_id or face_report.manufacturing_hash != part.manufacturing_hash:
            blockers.append(CWS_MACHINE_STALE_EVIDENCE)
        if mark_set is not None and (
            mark_set.part_id != part.internal_id or mark_set.manufacturing_hash != part.manufacturing_hash
        ):
            blockers.append(CWS_MACHINE_STALE_EVIDENCE)
        if identification_set is not None and (
            identification_set.part_id != part.internal_id
            or identification_set.manufacturing_hash != part.manufacturing_hash
        ):
            blockers.append(CWS_MACHINE_STALE_EVIDENCE)
        blockers.extend(self._part_dimension_blockers(part))

        faces = self._faces(face_report)
        decisions: list[MachineFeatureDecision] = []
        if mark_set is not None:
            for feature in sorted(mark_set.features, key=lambda item: item.mark_id):
                decisions.append(
                    self._decision(
                        feature_type=MachineFeatureType.SCRIBE,
                        source=feature,
                        source_usable=feature.production_usable and feature.status == MarkStatus.ACCEPTED,
                        face=faces.get(feature.face_id),
                        source_hash=feature.feature_sha256,
                    )
                )
        if identification_set is not None:
            for reference in sorted(identification_set.hole_references, key=lambda item: item.intent_id):
                decisions.append(
                    self._decision(
                        feature_type=MachineFeatureType.HOLE_REFERENCE,
                        source=reference,
                        source_usable=reference.production_usable and reference.status == IdentificationStatus.ACCEPTED,
                        face=faces.get(reference.input.face_id),
                        source_hash=reference.intent_sha256,
                    )
                )
            for intent in sorted(identification_set.text_intents, key=lambda item: item.intent_id):
                decisions.append(
                    self._decision(
                        feature_type=MachineFeatureType.IDENTIFICATION_TEXT,
                        source=intent,
                        source_usable=intent.production_usable and intent.status == IdentificationStatus.ACCEPTED,
                        face=faces.get(intent.request.face_id),
                        source_hash=intent.intent_sha256,
                    )
                )

        for decision in decisions:
            blockers.extend(decision.blocking_codes)
            warnings.extend(decision.warnings)
        blockers = list(dict.fromkeys(blockers))
        return MachineCapabilityReport.create(
            part_id=part.internal_id,
            manufacturing_hash=part.manufacturing_hash,
            machine_profile_id=self.profile.internal_id,
            machine_id=self.profile.machine_id,
            machine_profile_sha256=self.profile_sha256,
            face_report_sha256=face_report.report_sha256,
            mark_set_sha256="" if mark_set is None else mark_set.report_sha256,
            identification_set_sha256="" if identification_set is None else identification_set.report_sha256,
            decisions=tuple(decisions),
            blocking_codes=tuple(blockers),
            warnings=tuple(dict.fromkeys(warnings)),
        )


__all__ = [
    "CWS_MACHINE_STALE_EVIDENCE",
    "CWS_MACHINE_OPERATION_UNSUPPORTED",
    "CWS_MACHINE_TOOL_MISSING",
    "CWS_MACHINE_REACHABILITY_UNKNOWN",
    "CWS_MACHINE_FACE_UNREACHABLE",
    "CWS_MACHINE_LIMIT_UNKNOWN",
    "CWS_MACHINE_LIMIT_EXCEEDED",
    "CWS_MACHINE_TOOL_AMBIGUOUS",
    "CWS_MACHINE_SOURCE_BLOCKED",
    "CWS_MACHINE_PART_DIMENSION",
    "CWS_MACHINE_PROFILE_IDENTITY",
    "CWS_MACHINE_MARK_TYPE_UNSUPPORTED",
    "CWS_MACHINE_RULESET_UNKNOWN",
    "CWS_MACHINE_RULESET_INCOMPATIBLE",
    "CWS_MACHINE_HEAD_CLEARANCE_UNKNOWN",
    "CWS_MACHINE_HEAD_CLEARANCE",
    "MachineCapabilityEvaluator",
]
