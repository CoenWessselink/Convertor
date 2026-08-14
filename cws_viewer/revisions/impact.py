"""Revision impact planning and controlled invalidation.

The service never deletes source geometry.  It invalidates only derived evidence
that may no longer correspond to the current manufacturing identity.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable

from cws_convertor.project.model import ProjectModel, ValidationIssue, stable_sha256, utc_now_iso

from .model import (
    ArtifactAction,
    ArtifactInvalidationRecord,
    ChangeKind,
    ProjectRevisionCompareReport,
    RevisionImpactPlan,
)

_CORE_PART_ARTIFACT_TYPES = (
    "nc1",
    "step",
    "ifc",
)

_PLANNING_SENSITIVE_ARTIFACT_TYPES = (
    "production_pdf",
    "trusted_pdf",
    "review_pdf",
    "pdf",
    "drawing",
    "optimization",
    "nesting",
    "machine_job",
)

_PRODUCTION_ARTIFACT_TYPES = _CORE_PART_ARTIFACT_TYPES + _PLANNING_SENSITIVE_ARTIFACT_TYPES


def _artifact_digest(value: Any) -> str:
    if isinstance(value, bytes):
        return hashlib.sha256(value).hexdigest()
    if isinstance(value, str):
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
    return stable_sha256(value)


def build_revision_impact_plan(
    old_project: ProjectModel,
    new_project: ProjectModel,
    report: ProjectRevisionCompareReport,
) -> RevisionImpactPlan:
    if old_project.project_id != new_project.project_id or report.project_id != new_project.project_id:
        raise ValueError("Impactplan hoort niet bij dit project")
    changed: set[str] = set()
    planning_changed: set[str] = set()
    assembly_relation_changed: set[str] = set()
    placement_only: set[str] = set()
    records: list[ArtifactInvalidationRecord] = []
    affected_assemblies: set[str] = set()

    for change in report.changes:
        current_id = change.new_entity_id or change.old_entity_id or ""
        if change.production_reuse_allowed:
            if change.placement_only and current_id:
                placement_only.add(current_id)
            if change.planning_changed and current_id:
                planning_changed.add(current_id)
                if any(item.value == "assembly_relation" for item in change.impacts):
                    assembly_relation_changed.add(current_id)
            if current_id:
                if change.planning_changed:
                    for artifact_type in _CORE_PART_ARTIFACT_TYPES:
                        records.append(ArtifactInvalidationRecord(
                            entity_id=current_id,
                            artifact_type=artifact_type,
                            action=ArtifactAction.KEEP,
                            reason_codes=("CWS-V7-PLANNING-ONLY-PART-ARTIFACT-REUSABLE",),
                            previous_hash=change.old_manufacturing_hash,
                            new_hash=change.new_manufacturing_hash,
                        ))
                    for artifact_type in _PLANNING_SENSITIVE_ARTIFACT_TYPES:
                        records.append(ArtifactInvalidationRecord(
                            entity_id=current_id,
                            artifact_type=artifact_type,
                            action=ArtifactAction.REVIEW,
                            reason_codes=("CWS-V7-PLANNING-EVIDENCE-REVIEW-REQUIRED",),
                            previous_hash=change.old_manufacturing_hash,
                            new_hash=change.new_manufacturing_hash,
                        ))
                else:
                    records.append(ArtifactInvalidationRecord(
                        entity_id=current_id,
                        artifact_type="all_production_artifacts",
                        action=ArtifactAction.KEEP,
                        reason_codes=("CWS-V7-PLACEMENT-ONLY" if change.placement_only else "CWS-V7-UNCHANGED",),
                        previous_hash=change.old_manufacturing_hash,
                        new_hash=change.new_manufacturing_hash,
                    ))

            # Quantity or assembly-membership changes leave the individual
            # manufacturing definition intact, but dependent assembly/BOM
            # evidence must be recalculated.
            if change.planning_changed:
                for project, entity_id in ((old_project, change.old_entity_id), (new_project, change.new_entity_id)):
                    if entity_id and entity_id in project.parts:
                        affected_assemblies.update(project.parts[entity_id].assembly_ids)
            continue

        if change.kind == ChangeKind.ADDED:
            if current_id:
                changed.add(current_id)
            records.append(ArtifactInvalidationRecord(
                entity_id=current_id,
                artifact_type="all_production_artifacts",
                action=ArtifactAction.REVIEW,
                reason_codes=("CWS-V7-NEW-PART-REQUIRES-VALIDATION",),
                new_hash=change.new_manufacturing_hash,
            ))
        elif change.kind in {ChangeKind.CHANGED, ChangeKind.REMOVED, ChangeKind.AMBIGUOUS} or change.manufacturing_changed:
            if current_id:
                changed.add(current_id)
            reason_codes = tuple(change.blocking_codes or ("CWS-V7-MANUFACTURING-CHANGE",))
            for artifact_type in _PRODUCTION_ARTIFACT_TYPES:
                records.append(ArtifactInvalidationRecord(
                    entity_id=current_id,
                    artifact_type=artifact_type,
                    action=ArtifactAction.INVALIDATE,
                    reason_codes=reason_codes,
                    previous_hash=change.old_manufacturing_hash,
                    new_hash=change.new_manufacturing_hash,
                ))
        for project, entity_id in ((old_project, change.old_entity_id), (new_project, change.new_entity_id)):
            if entity_id and entity_id in project.parts:
                affected_assemblies.update(project.parts[entity_id].assembly_ids)

    blocked_jobs = sorted(
        job_id
        for job_id, job in new_project.machine_jobs.items()
        if set(job.part_ids) & changed
    )
    review_jobs = sorted(
        job_id
        for job_id, job in new_project.machine_jobs.items()
        if not (set(job.part_ids) & changed) and set(job.part_ids) & planning_changed
    )

    downstream_changed = changed | planning_changed

    optimization_results = dict(new_project.settings.get("optimization_results", {}) or {})
    invalidated_optimizations = sorted(
        str(result_id)
        for result_id, value in optimization_results.items()
        if isinstance(value, dict) and set(str(item) for item in value.get("part_ids", ())) & downstream_changed
    )
    for result_id in invalidated_optimizations:
        records.append(ArtifactInvalidationRecord(
            entity_id=result_id,
            artifact_type="optimization_result",
            action=ArtifactAction.INVALIDATE,
            reason_codes=("CWS-V7-OPTIMIZATION-INPUT-CHANGED",),
        ))

    scribing_reviews = dict(new_project.settings.get("scribing_reviews", {}) or {})
    invalidated_scribing = sorted(
        str(review_id)
        for review_id, value in scribing_reviews.items()
        if isinstance(value, dict)
        and {str(value.get("target_part_id", "")), str(value.get("partner_part_id", ""))}
        & (changed | assembly_relation_changed)
    )
    for review_id in invalidated_scribing:
        records.append(ArtifactInvalidationRecord(
            entity_id=review_id,
            artifact_type="scribing_review",
            action=ArtifactAction.REVIEW,
            reason_codes=("CWS-V7-SCRIBING-REVALIDATION-REQUIRED",),
        ))

    invalidated_orders = sorted(
        str(order_id)
        for order_id, order in new_project.production_orders.items()
        if isinstance(order, dict) and set(str(item) for item in order.get("part_ids", ())) & downstream_changed
    )
    for order_id in invalidated_orders:
        records.append(ArtifactInvalidationRecord(
            entity_id=order_id,
            artifact_type="production_order",
            action=ArtifactAction.INVALIDATE,
            reason_codes=("CWS-V7-PRODUCTION-ORDER-INPUT-CHANGED",),
        ))

    return RevisionImpactPlan(
        project_id=new_project.project_id,
        old_revision_id=report.old_revision_id,
        new_revision_id=report.new_revision_id,
        records=tuple(records),
        changed_part_ids=tuple(sorted(changed)),
        planning_changed_part_ids=tuple(sorted(planning_changed)),
        placement_only_part_ids=tuple(sorted(placement_only)),
        blocked_machine_job_ids=tuple(blocked_jobs),
        review_machine_job_ids=tuple(review_jobs),
        invalidated_assembly_ids=tuple(sorted(affected_assemblies)),
        invalidated_optimization_ids=tuple(invalidated_optimizations),
        invalidated_scribing_review_ids=tuple(invalidated_scribing),
        invalidated_production_order_ids=tuple(invalidated_orders),
    )


def _artifact_key_matches(value: str, artifact_types: set[str]) -> bool:
    key = str(value).strip().lower().replace("-", "_")
    aliases = {
        "dstv": "nc1",
        "nc": "nc1",
        "stp": "step",
        "pdf": "pdf",
        "production_drawing": "drawing",
    }
    key = aliases.get(key, key)
    return key in artifact_types


def _invalidate_embedded_artifacts(
    part: Any,
    reason_codes: Iterable[str],
    *,
    artifact_types: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    selected = None if artifact_types is None else {str(item).strip().lower() for item in artifact_types}
    for key in ("trusted_artifacts", "artifacts", "attachments", "export_artifacts"):
        value = part.properties.get(key)
        if not value:
            continue
        if isinstance(value, dict):
            kept: dict[Any, Any] = {}
            for fmt, artifact in sorted(value.items(), key=lambda item: str(item[0])):
                if selected is not None and not _artifact_key_matches(str(fmt), selected):
                    kept[fmt] = artifact
                    continue
                summaries.append({
                    "container": key,
                    "format": str(fmt),
                    "sha256": _artifact_digest(artifact),
                    "reason_codes": list(dict.fromkeys(reason_codes)),
                })
            if kept:
                part.properties[key] = kept
            else:
                part.properties.pop(key, None)
        else:
            # A non-mapping container has no format-level provenance.  It can
            # only be removed for a full manufacturing invalidation.
            if selected is not None:
                continue
            part.properties.pop(key, None)
            summaries.append({
                "container": key,
                "format": "unknown",
                "sha256": _artifact_digest(value),
                "reason_codes": list(dict.fromkeys(reason_codes)),
            })
    if summaries:
        part.properties.setdefault("invalidated_artifacts", []).extend(summaries)
    return summaries


def apply_revision_impact(
    project: ProjectModel,
    plan: RevisionImpactPlan,
    *,
    user: str = "system",
) -> dict[str, Any]:
    if project.project_id != plan.project_id:
        raise ValueError("Impactplan hoort niet bij dit project")
    invalidated_artifacts = 0
    for part_id in plan.changed_part_ids:
        part = project.parts.get(part_id)
        if part is None:
            continue
        before = part.manufacturing_hash
        reason_codes = tuple(
            code
            for record in plan.records
            if record.entity_id == part_id and record.action == ArtifactAction.INVALIDATE
            for code in record.reason_codes
        ) or ("CWS-V7-MANUFACTURING-CHANGE",)
        summaries = _invalidate_embedded_artifacts(part, reason_codes)
        invalidated_artifacts += len(summaries)
        part.nc1_eligible = False
        part.export_status = "blocked"
        part.status = "review_required"
        part.properties["revision_validation_required"] = True
        part.properties["revision_invalidation_codes"] = list(dict.fromkeys(reason_codes))
        issue = ValidationIssue(
            code="CWS-V7-REVISION-ARTIFACTS-INVALIDATED",
            message="Productieartefacten zijn ongeldig geworden door een relevante revisiewijziging",
            severity="error",
            blocking=True,
            entity_id=part_id,
            field_path="parts.production_artifacts",
            source="cws_viewer.revisions",
        )
        project.upsert_validation_issue(issue, user=user)
        project.audit(
            "revision.part_artifacts_invalidated",
            user=user,
            entity_id=part_id,
            before_hash=before,
            after_hash=part.manufacturing_hash,
            details={"reason_codes": list(dict.fromkeys(reason_codes)), "artifact_count": len(summaries)},
        )

    planning_artifacts_reviewed = 0
    for part_id in plan.planning_changed_part_ids:
        part = project.parts.get(part_id)
        if part is None:
            continue
        reason_codes = ("CWS-V7-PLANNING-EVIDENCE-REVIEW-REQUIRED",)
        summaries = _invalidate_embedded_artifacts(
            part,
            reason_codes,
            artifact_types=_PLANNING_SENSITIVE_ARTIFACT_TYPES,
        )
        planning_artifacts_reviewed += len(summaries)
        part.properties["revision_planning_validation_required"] = True
        part.properties["revision_planning_codes"] = list(reason_codes)
        issue = ValidationIssue(
            code="CWS-V7-REVISION-PLANNING-EVIDENCE-REVIEW",
            message=(
                "Hoeveelheid of assemblyrelatie is gewijzigd. De individuele "
                "manufacturing artefacten blijven herbruikbaar; BOM-, tekening- "
                "en planningsbewijs moet opnieuw worden gecontroleerd."
            ),
            severity="warning",
            blocking=False,
            entity_id=part_id,
            field_path="parts.planning_evidence",
            source="cws_viewer.revisions",
        )
        project.upsert_validation_issue(issue, user=user)
        project.audit(
            "revision.part_planning_evidence_review",
            user=user,
            entity_id=part_id,
            details={"reason_codes": list(reason_codes), "artifact_count": len(summaries)},
        )

    for assembly_id in plan.invalidated_assembly_ids:
        assembly = project.assemblies.get(assembly_id)
        if assembly is None:
            continue
        previous_artifacts = list(assembly.artifact_ids)
        assembly.properties.setdefault("invalidated_artifact_ids", []).extend(previous_artifacts)
        assembly.artifact_ids.clear()
        assembly.production_status = "review_required"
        assembly.drawing_status = "invalidated"
        project.audit(
            "revision.assembly_invalidated",
            user=user,
            entity_id=assembly_id,
            details={"previous_artifact_ids": previous_artifacts},
        )

    for job_id in plan.blocked_machine_job_ids:
        job = project.machine_jobs.get(job_id)
        if job is None:
            continue
        previous_checksum = job.checksum
        job.release_status = "blocked"
        job.simulation_status = "invalidated"
        job.checksum = ""
        job.output_log.append(f"{utc_now_iso()} revision invalidated: manufacturing part changed")
        project.audit(
            "revision.machine_job_invalidated",
            user=user,
            entity_id=job_id,
            before_hash=previous_checksum,
            details={"part_ids": sorted(set(job.part_ids) & set(plan.changed_part_ids))},
        )

    reviewed_machine_jobs: list[str] = []
    for job_id in plan.review_machine_job_ids:
        job = project.machine_jobs.get(job_id)
        if job is None:
            continue
        previous_checksum = job.checksum
        job.release_status = "review_required"
        job.simulation_status = "review_required"
        job.checksum = ""
        job.output_log.append(f"{utc_now_iso()} revision review required: planning input changed")
        reviewed_machine_jobs.append(job_id)
        project.audit(
            "revision.machine_job_planning_review",
            user=user,
            entity_id=job_id,
            before_hash=previous_checksum,
            details={"part_ids": sorted(set(job.part_ids) & set(plan.planning_changed_part_ids))},
        )

    invalidated_orders: list[str] = []
    for order_id in plan.invalidated_production_order_ids:
        order = project.production_orders.get(order_id)
        if not isinstance(order, dict):
            continue
        order["status"] = "invalidated"
        order["revision_validation_required"] = True
        order["invalidated_at"] = utc_now_iso()
        order["revision_impact_old"] = plan.old_revision_id
        order["revision_impact_new"] = plan.new_revision_id
        invalidated_orders.append(order_id)

    invalidated_optimizations: list[str] = []
    optimization_results = project.settings.setdefault("optimization_results", {})
    for result_id in plan.invalidated_optimization_ids:
        value = optimization_results.get(result_id) if isinstance(optimization_results, dict) else None
        if not isinstance(value, dict):
            continue
        value["status"] = "invalidated"
        value["revision_validation_required"] = True
        value["invalidated_at"] = utc_now_iso()
        value["reason_codes"] = ["CWS-V7-OPTIMIZATION-INPUT-CHANGED"]
        invalidated_optimizations.append(result_id)

    invalidated_scribing: list[str] = []
    scribing_reviews = project.settings.setdefault("scribing_reviews", {})
    for review_id in plan.invalidated_scribing_review_ids:
        value = scribing_reviews.get(review_id) if isinstance(scribing_reviews, dict) else None
        if not isinstance(value, dict):
            continue
        value["status"] = "invalidated"
        value["revalidation_required"] = True
        value["invalidated_at"] = utc_now_iso()
        value["reason_codes"] = ["CWS-V7-SCRIBING-REVALIDATION-REQUIRED"]
        invalidated_scribing.append(review_id)

    project.audit(
        "revision.impact_applied",
        user=user,
        details={
            "old_revision_id": plan.old_revision_id,
            "new_revision_id": plan.new_revision_id,
            "changed_part_ids": list(plan.changed_part_ids),
            "planning_changed_part_ids": list(plan.planning_changed_part_ids),
            "placement_only_part_ids": list(plan.placement_only_part_ids),
            "blocked_machine_job_ids": list(plan.blocked_machine_job_ids),
            "review_machine_job_ids": list(plan.review_machine_job_ids),
            "invalidated_orders": invalidated_orders,
            "invalidated_optimizations": invalidated_optimizations,
            "invalidated_scribing_reviews": invalidated_scribing,
        },
    )
    project.modified_at = utc_now_iso()
    return {
        "changed_parts": len(plan.changed_part_ids),
        "planning_changed_parts": len(plan.planning_changed_part_ids),
        "placement_only_parts": len(plan.placement_only_part_ids),
        "invalidated_assemblies": len(plan.invalidated_assembly_ids),
        "blocked_machine_jobs": len(plan.blocked_machine_job_ids),
        "reviewed_machine_jobs": len(reviewed_machine_jobs),
        "invalidated_orders": len(invalidated_orders),
        "invalidated_optimizations": len(invalidated_optimizations),
        "invalidated_scribing_reviews": len(invalidated_scribing),
        "invalidated_embedded_artifacts": invalidated_artifacts,
        "planning_artifacts_reviewed": planning_artifacts_reviewed,
    }


__all__ = ["build_revision_impact_plan", "apply_revision_impact"]
