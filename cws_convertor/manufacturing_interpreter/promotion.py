from __future__ import annotations

from typing import Any

from .contracts import InterpretationConfirmation, InterpretationReadiness, WorkbenchPromotionResult
from .recognition_cache import stable_sha256


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
                blockers=tuple(f"STALE_REPORT:{reason}" for reason in stale),
            )
        if report.readiness != InterpretationReadiness.READY:
            return WorkbenchPromotionResult(
                status="BLOCKED",
                report_hash=report_hash,
                hypothesis_id="",
                blockers=("INTERPRETATION_NOT_READY",),
            )
        if confirmation is None or confirmation.report_hash != report_hash:
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
            state = update_part_workbench(
                project,
                report.part_id,
                {
                    "manufacturing_interpretation": {
                        "report_hash": report_hash,
                        "hypothesis_id": hypothesis.hypothesis_id,
                        "features": [feature.feature_id for feature in report.features],
                        "semantic_overrides": dict(confirmation.semantic_overrides),
                    }
                },
                user=user,
                reason="MGI V3 confirmed interpretation promotion",
            )
        except Exception as exc:
            try:
                from cws_convertor.project.workbench import undo_part_workbench

                undo_part_workbench(project, report.part_id, user=user)
            except Exception:
                pass
            return WorkbenchPromotionResult(
                status="BLOCKED",
                report_hash=report_hash,
                hypothesis_id=hypothesis.hypothesis_id,
                rolled_back=True,
                blockers=(f"WORKBENCH_REJECTED:{type(exc).__name__}",),
            )
        revision_hash = stable_sha256(state)
        return WorkbenchPromotionResult(
            status="PROMOTED",
            report_hash=report_hash,
            hypothesis_id=hypothesis.hypothesis_id,
            revision_hash=revision_hash,
        )


__all__ = ["WorkbenchPromotionCoordinator"]
