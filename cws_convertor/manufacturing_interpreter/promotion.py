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
    ) -> WorkbenchPromotionResult:
        report_hash = stable_sha256(report)
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
