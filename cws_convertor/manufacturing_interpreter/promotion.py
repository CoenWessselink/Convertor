from __future__ import annotations

from copy import deepcopy
import math
from typing import Any, Mapping

from .contracts import GeometryProofStatus, InterpretationConfirmation, InterpretationReadiness, WorkbenchPromotionResult
from .material_evidence import material_evidence_from_part, normalise_material_evidence, _material_key
from .recognition_cache import stable_sha256


def _current_revision(project: Any, part_id: str) -> dict[str, Any]:
    parts = getattr(project, "parts", None)
    part = parts.get(part_id) if isinstance(parts, Mapping) else None
    workbench = getattr(part, "workbench", None)
    if isinstance(workbench, Mapping):
        return deepcopy(dict(workbench.get("current_revision") or {}))
    return {}


def _frame_payload(frame: Any) -> dict[str, Any] | None:
    if frame is None:
        return None
    try:
        x_axis = tuple(float(value) for value in frame.x_axis)
        y_axis = tuple(float(value) for value in frame.y_axis)
        z_axis = tuple(float(value) for value in frame.z_axis)
        origin = tuple(float(value) for value in frame.origin_mm)
        if not all(len(value) == 3 for value in (x_axis, y_axis, z_axis, origin)):
            return None
        return {
            "matrix": [
                [x_axis[0], y_axis[0], z_axis[0], origin[0]],
                [x_axis[1], y_axis[1], z_axis[1], origin[1]],
                [x_axis[2], y_axis[2], z_axis[2], origin[2]],
                [0.0, 0.0, 0.0, 1.0],
            ]
        }
    except (AttributeError, TypeError, ValueError):
        return None


def _promotion_changes(
    report: Any,
    confirmation: InterpretationConfirmation,
    report_hash: str,
    hypothesis: Any,
    current: Mapping[str, Any],
) -> dict[str, Any]:
    """Map immutable MGI evidence onto fields accepted by Part Workbench.

    ``manufacturing_interpretation`` used to be sent as an unsupported
    top-level edit field, which made every real promotion fail.  The complete
    provenance pointer now lives inside the existing ``recognition`` field;
    only Workbench-owned production fields are edited.
    """

    profile = getattr(report, "profile", None)
    designation = str(getattr(profile, "designation", "") or "").strip()
    confidence = float(getattr(profile, "confidence", 0.0) or 0.0)
    material = normalise_material_evidence(getattr(report, "material_evidence", None))
    recognition = deepcopy(dict(current.get("recognition") or {}))
    recognition.update(
        {
            "candidate": designation or str(recognition.get("candidate") or ""),
            "confidence": max(0.0, min(1.0, confidence)),
            "confirmed": bool(designation),
            "manufacturing_interpretation": {
                "schema": "cws-mgi-workbench-promotion-v1",
                "interpretation_id": str(getattr(report, "interpretation_id", "") or ""),
                "report_hash": report_hash,
                "hypothesis_id": str(getattr(hypothesis, "hypothesis_id", "") or ""),
                "feature_ids": [
                    str(getattr(feature, "feature_id", "") or "")
                    for feature in tuple(getattr(report, "features", ()) or ())
                    if str(getattr(feature, "feature_id", "") or "")
                ],
                "semantic_overrides": dict(confirmation.semantic_overrides),
                "source_geometry_hash": str(getattr(report, "source_geometry_hash", "") or ""),
                "tolerance_policy_hash": str(getattr(report, "tolerance_policy_hash", "") or ""),
                "profile_database_hash": str(getattr(report, "profile_database_hash", "") or ""),
                "material_evidence": {
                    "status": material.status.value,
                    "material": material.material,
                    "grade": material.grade,
                    "confidence": material.confidence,
                    "source": material.source,
                    "source_path": material.source_path,
                    "source_entity_id": material.source_entity_id,
                    "reason": material.reason,
                    "evidence": [list(item) for item in material.evidence],
                },
            },
        }
    )
    changes: dict[str, Any] = {"recognition": recognition}

    properties = deepcopy(dict(current.get("production_properties") or {}))
    if designation:
        properties["profile"] = designation
    physical_material = material.material or material.grade
    if material.confirmed and physical_material:
        properties["material"] = physical_material
        properties["material_grade"] = material.grade or physical_material
    if properties:
        changes["production_properties"] = properties

    frame = _frame_payload(getattr(report, "manufacturing_frame", None))
    if frame is not None:
        changes["production_frame"] = frame
    axis_id = str(getattr(report, "selected_axis_id", "") or "")
    axes = tuple(getattr(report, "axis_candidates", ()) or ())
    selected_axis = next(
        (item for item in axes if str(getattr(item, "axis_id", "") or "") == axis_id),
        None,
    )
    length = float(getattr(selected_axis, "length_mm", 0.0) or 0.0)
    if length > 0.0:
        dimensions = deepcopy(dict(current.get("dimensions") or {}))
        dimensions["length_mm"] = length
        changes["dimensions"] = dimensions
    profile_type = str(getattr(profile, "profile_type", "") or "").upper()
    if str(current.get("part_form") or "unknown") == "unknown" and designation:
        changes["part_form"] = "round_bar" if profile_type == "RU" else "profile"
    return changes


class WorkbenchPromotionCoordinator:
    def promote(
        self,
        *,
        report: Any,
        confirmation: InterpretationConfirmation | None,
        project: Any,
        user: str,
        current_source_geometry_hash: str | None = None,
        current_tolerance_policy_hash: str | None = None,
        current_profile_database_hash: str | None = None,
    ) -> WorkbenchPromotionResult:
        report_hash = stable_sha256(report)
        stale = []
        parts = getattr(project, "parts", {})
        part = parts.get(str(getattr(report, "part_id", "")))
        if part is None:
            return WorkbenchPromotionResult(status="BLOCKED", report_hash=report_hash,
                hypothesis_id="", blockers=("PROJECT_PART_NOT_FOUND",))
        identity = getattr(part, "source_identity", None)
        descriptor = getattr(part, "geometry_descriptor", {})
        for name, current in (
            ("source_file_id", getattr(identity, "source_file_id", "")),
            ("source_sha256", getattr(identity, "source_sha256", "")),
            ("source_geometry_hash", descriptor.get("source_geometry_hash", "")),
        ):
            reported = str(getattr(report, name, "") or "")
            if not reported or not current or reported != str(current):
                stale.append(name.upper() + "_CHANGED")
        if current_source_geometry_hash is not None and current_source_geometry_hash != report.source_geometry_hash:
            stale.append("SOURCE_GEOMETRY_HASH_CHANGED")
        if current_tolerance_policy_hash is not None and current_tolerance_policy_hash != report.tolerance_policy_hash:
            stale.append("TOLERANCE_POLICY_HASH_CHANGED")
        if current_profile_database_hash is not None and current_profile_database_hash != report.profile_database_hash:
            stale.append("PROFILE_DATABASE_HASH_CHANGED")
        if stale:
            return WorkbenchPromotionResult(
                status="BLOCKED",
                report_hash=report_hash,
                hypothesis_id=getattr(confirmation, "hypothesis_id", "") if confirmation else "",
                blockers=tuple(dict.fromkeys(f"STALE_REPORT:{reason}" for reason in stale)),
            )
        if report.readiness != InterpretationReadiness.READY:
            return WorkbenchPromotionResult(
                status="BLOCKED",
                report_hash=report_hash,
                hypothesis_id="",
                blockers=("INTERPRETATION_NOT_READY",),
            )
        profile = getattr(report, "profile", None)
        try:
            profile_confidence = float(getattr(profile, "confidence", 0.0))
        except (TypeError, ValueError):
            profile_confidence = 0.0
        if (
            getattr(report, "source_gate", None) != GeometryProofStatus.PROVEN_WITHIN_POLICY
            or getattr(profile, "status", None) != GeometryProofStatus.PROVEN_WITHIN_POLICY
            or not str(getattr(profile, "designation", "") or "").strip()
            or not math.isfinite(profile_confidence) or not 0.95 <= profile_confidence <= 1.0
            or getattr(getattr(report, "equivalence", None), "status", None) not in {
                GeometryProofStatus.PROVEN_BREP_EQUIVALENT, GeometryProofStatus.PROVEN_WITHIN_POLICY,
            }
            or tuple(getattr(report, "blockers", ()) or ())
        ):
            return WorkbenchPromotionResult(status="BLOCKED", report_hash=report_hash,
                hypothesis_id="", blockers=("GEOMETRY_OR_PROFILE_PROOF_INCOMPLETE",))
        material_evidence = normalise_material_evidence(
            getattr(report, "material_evidence", None)
        )
        if not material_evidence.confirmed:
            return WorkbenchPromotionResult(
                status="BLOCKED",
                report_hash=report_hash,
                hypothesis_id=getattr(confirmation, "hypothesis_id", "") if confirmation else "",
                blockers=(
                    "MATERIAL_EVIDENCE_CONFLICT"
                    if material_evidence.status.value == "CONFLICT"
                    else "MATERIAL_EVIDENCE_UNRESOLVED",
                ),
            )
        current_material = material_evidence_from_part(part)
        if current_material.status.value == "CONFLICT" or (
            (current_material.material or current_material.grade)
            and _material_key(current_material.material or current_material.grade)
            != _material_key(material_evidence.material or material_evidence.grade)
        ):
            return WorkbenchPromotionResult(status="BLOCKED", report_hash=report_hash,
                hypothesis_id="", blockers=("STALE_REPORT:MATERIAL_CHANGED_OR_CONFLICTING",))
        if material_evidence.status.value == "SOURCE_CONFIRMED" and not current_material.confirmed:
            return WorkbenchPromotionResult(status="BLOCKED", report_hash=report_hash,
                hypothesis_id="", blockers=("STALE_REPORT:MATERIAL_SOURCE_NOT_CONFIRMED",))
        for key, expected in (("source_file_id", getattr(identity, "source_file_id", "")),
                              ("source_sha256", getattr(identity, "source_sha256", ""))):
            reported = dict(material_evidence.evidence).get(key)
            if reported and reported != expected:
                return WorkbenchPromotionResult(status="BLOCKED", report_hash=report_hash,
                    hypothesis_id="", blockers=("STALE_REPORT:MATERIAL_SOURCE_CHANGED",))
        if confirmation is None or confirmation.report_hash != report_hash or not confirmation.user.strip() or not user.strip():
            return WorkbenchPromotionResult(
                status="BLOCKED",
                report_hash=report_hash,
                hypothesis_id="",
                blockers=("EXPLICIT_CONFIRMATION_REQUIRED",),
            )
        hypothesis = next(
            (item for item in report.hypotheses if item.hypothesis_id == confirmation.hypothesis_id),
            None,
        )
        if hypothesis is None:
            return WorkbenchPromotionResult(
                status="BLOCKED",
                report_hash=report_hash,
                hypothesis_id=confirmation.hypothesis_id,
                blockers=("CONFIRMED_HYPOTHESIS_NOT_FOUND",),
            )
        from cws_convertor.project.workbench import update_part_workbench

        try:
            working = deepcopy(project)
            current = _current_revision(working, report.part_id)
            state = update_part_workbench(
                working,
                report.part_id,
                _promotion_changes(
                    report,
                    confirmation,
                    report_hash,
                    hypothesis,
                    current,
                ),
                user=user,
                reason="MGI V3 confirmed interpretation promotion",
            )
        except Exception as exc:
            return WorkbenchPromotionResult(
                status="BLOCKED",
                report_hash=report_hash,
                hypothesis_id=hypothesis.hypothesis_id,
                rolled_back=True,
                blockers=(f"WORKBENCH_REJECTED:{type(exc).__name__}",),
            )
        project.__dict__.update(working.__dict__)
        revision_hash = stable_sha256(state)
        return WorkbenchPromotionResult(
            status="PROMOTED",
            report_hash=report_hash,
            hypothesis_id=hypothesis.hypothesis_id,
            revision_hash=revision_hash,
        )


__all__ = ["WorkbenchPromotionCoordinator"]
