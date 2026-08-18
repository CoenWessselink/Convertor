"""U4 production workflow orchestration over one canonical project workspace.

This layer does not create geometry, release machines or bypass format gates. It
only composes existing readiness evidence into one deterministic operator-facing
workflow snapshot that can be consumed by Qt, CLI and packaged regression tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

U4_WORKFLOW_SCHEMA = "cws-unified-production-workflow-1.0"
PRODUCTION_FORMATS = ("nc1", "step", "ifc", "production_pdf")
REVIEW_FORMATS = ("json", "review_pdf")
U4_SAFETY_FLAGS = {
    "machine_observed_by_cws": False,
    "deployment_transport_authorized": False,
    "direct_machine_transfer": False,
    "machine_transfer_allowed": False,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ProductionPartStatus:
    entity_id: str
    mark: str
    production_ready: bool
    allowed_formats: tuple[str, ...]
    blocked_formats: tuple[str, ...]
    blocking_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "mark": self.mark,
            "production_ready": self.production_ready,
            "allowed_formats": list(self.allowed_formats),
            "blocked_formats": list(self.blocked_formats),
            "blocking_codes": list(self.blocking_codes),
        }


@dataclass(frozen=True, slots=True)
class ProductionWorkflowSnapshot:
    project_id: str
    project_name: str
    scope: str
    requested_entity_ids: tuple[str, ...]
    part_statuses: tuple[ProductionPartStatus, ...]
    ready_part_count: int
    blocked_part_count: int
    blocking_codes: tuple[str, ...]
    next_action: str
    export_candidate: bool
    created_at: str

    @property
    def part_count(self) -> int:
        return len(self.part_statuses)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": U4_WORKFLOW_SCHEMA,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "scope": self.scope,
            "requested_entity_ids": list(self.requested_entity_ids),
            "part_count": self.part_count,
            "ready_part_count": self.ready_part_count,
            "blocked_part_count": self.blocked_part_count,
            "blocking_codes": list(self.blocking_codes),
            "next_action": self.next_action,
            "export_candidate": self.export_candidate,
            "production_release_allowed_from_workflow": False,
            "machine_transfer_allowed": False,
            "safety": dict(U4_SAFETY_FLAGS),
            "parts": [item.to_dict() for item in self.part_statuses],
            "created_at": self.created_at,
        }


def build_production_workflow_snapshot(
    workspace: Any,
    entity_ids: Iterable[str] = (),
) -> ProductionWorkflowSnapshot:
    """Build one deterministic production-readiness view from existing gates."""
    project = workspace.project
    requested = tuple(dict.fromkeys(str(value) for value in entity_ids if str(value)))
    selected_part_ids = tuple(value for value in requested if value in project.parts)
    if requested:
        part_ids = selected_part_ids
        scope = "selection"
    else:
        part_ids = tuple(project.parts)
        scope = "project"

    statuses: list[ProductionPartStatus] = []
    blocking_codes: set[str] = set()
    all_formats = PRODUCTION_FORMATS + REVIEW_FORMATS
    for part_id in part_ids:
        part = project.parts[part_id]
        assessment = workspace.readiness_for_part(part_id, formats=all_formats)
        allowed = tuple(fmt for fmt in all_formats if assessment.get("allowed", {}).get(fmt, False))
        blocked = tuple(fmt for fmt in all_formats if not assessment.get("allowed", {}).get(fmt, False))
        codes = tuple(sorted(set(assessment.get("blocking_codes", ()))))
        blocking_codes.update(codes)
        mark = str(
            getattr(part, "part_position", "")
            or getattr(part, "mark", "")
            or getattr(part, "name", "")
            or part_id
        )
        production_ready = bool(assessment.get("production_ready", False)) and all(
            fmt in allowed for fmt in PRODUCTION_FORMATS
        )
        statuses.append(
            ProductionPartStatus(
                entity_id=part_id,
                mark=mark,
                production_ready=production_ready,
                allowed_formats=allowed,
                blocked_formats=blocked,
                blocking_codes=codes,
            )
        )

    ready_count = sum(1 for item in statuses if item.production_ready)
    blocked_count = len(statuses) - ready_count
    if not statuses:
        next_action = "select_or_import_parts"
        export_candidate = False
    elif blocked_count:
        next_action = "resolve_readiness_blockers"
        export_candidate = False
    else:
        next_action = "review_and_export_package"
        export_candidate = True

    return ProductionWorkflowSnapshot(
        project_id=str(project.project_id),
        project_name=str(project.project_name),
        scope=scope,
        requested_entity_ids=requested,
        part_statuses=tuple(statuses),
        ready_part_count=ready_count,
        blocked_part_count=blocked_count,
        blocking_codes=tuple(sorted(blocking_codes)),
        next_action=next_action,
        export_candidate=export_candidate,
        created_at=_utc_now(),
    )


__all__ = [
    "PRODUCTION_FORMATS",
    "REVIEW_FORMATS",
    "U4_SAFETY_FLAGS",
    "U4_WORKFLOW_SCHEMA",
    "ProductionPartStatus",
    "ProductionWorkflowSnapshot",
    "build_production_workflow_snapshot",
]
