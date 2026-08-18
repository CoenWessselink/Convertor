"""U4 production workflow orchestration on top of the U3 application context.

This module deliberately does not introduce a second exporter, project model or
release authority.  It composes the existing canonical Project Model,
format-specific :class:`ReadinessGate` exposed by ``IntegratedProjectWorkspace``
and ``ProjectSession.export_production_package`` into one inspectable workflow.

Machine transfer remains out of scope and fail-closed.  A U4 workflow may build
validated files/packages on disk; it may not transmit them to a machine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .ui_context import U3_SAFETY_FLAGS, UnifiedApplicationContext


U4_WORKFLOW_SCHEMA = "cws-unified-production-workflow-1.0"
U4_RECEIPT_SCHEMA = "cws-unified-production-receipt-1.0"
U4_SAFETY_FLAGS = {
    "machine_observed_by_cws": False,
    "deployment_transport_authorized": False,
    "direct_machine_transfer": False,
    "machine_transfer_allowed": False,
}
DEFAULT_WORKFLOW_FORMATS = (
    "nc1",
    "step",
    "ifc",
    "production_pdf",
    "review_pdf",
    "json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip().lower() for value in values if str(value).strip()))


def _sha256_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ProductionPartReadiness:
    part_id: str
    part_position: str
    requested_formats: tuple[str, ...]
    allowed: dict[str, bool]
    blocking_codes: tuple[str, ...] = ()
    production_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "part_id": self.part_id,
            "part_position": self.part_position,
            "requested_formats": list(self.requested_formats),
            "allowed": dict(self.allowed),
            "blocking_codes": list(self.blocking_codes),
            "production_ready": self.production_ready,
        }


@dataclass(frozen=True, slots=True)
class ProductionWorkflowPlan:
    project_id: str
    project_schema: str
    project_state_sha256: str
    context_generation: int
    selection_only: bool
    selected_entity_ids: tuple[str, ...]
    part_ids: tuple[str, ...]
    requested_formats: tuple[str, ...]
    parts: tuple[ProductionPartReadiness, ...]
    blocking_codes: tuple[str, ...] = ()
    created_at: str = field(default_factory=_utc_now)

    @property
    def can_execute(self) -> bool:
        return bool(self.project_id and self.part_ids and self.requested_formats) and not self.blocking_codes

    @property
    def format_allowed(self) -> dict[str, bool]:
        return {
            fmt: bool(self.parts) and all(item.allowed.get(fmt, False) for item in self.parts)
            for fmt in self.requested_formats
        }

    @property
    def plan_sha256(self) -> str:
        # Exclude wall-clock/context generation so switching tabs cannot make a
        # technically identical production plan stale.  Selection, project
        # manufacturing state, readiness and requested formats are bound.
        return _sha256_json(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema": U4_WORKFLOW_SCHEMA,
            "project_id": self.project_id,
            "project_schema": self.project_schema,
            "project_state_sha256": self.project_state_sha256,
            "selection_only": self.selection_only,
            "selected_entity_ids": list(self.selected_entity_ids),
            "part_ids": list(self.part_ids),
            "requested_formats": list(self.requested_formats),
            "parts": [item.to_dict() for item in self.parts],
            "blocking_codes": list(self.blocking_codes),
            "safety": dict(U4_SAFETY_FLAGS),
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.identity_payload()
        payload.update(
            {
                "context_generation": self.context_generation,
                "created_at": self.created_at,
                "can_execute": self.can_execute,
                "format_allowed": self.format_allowed,
                "plan_sha256": self.plan_sha256,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class ProductionWorkflowReceipt:
    project_id: str
    plan_sha256: str
    export_id: str
    manifest_sha256: str
    summary: str
    output_root: str
    zip_path: str
    part_ids: tuple[str, ...]
    formats: tuple[str, ...]
    project_save_required: bool
    created_at: str = field(default_factory=_utc_now)
    receipt_sha256: str = ""

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": U4_RECEIPT_SCHEMA,
            "project_id": self.project_id,
            "plan_sha256": self.plan_sha256,
            "export_id": self.export_id,
            "manifest_sha256": self.manifest_sha256,
            "summary": self.summary,
            "output_root": self.output_root,
            "zip_path": self.zip_path,
            "part_ids": list(self.part_ids),
            "formats": list(self.formats),
            "project_save_required": self.project_save_required,
            "safety": dict(U4_SAFETY_FLAGS),
            "created_at": self.created_at,
        }

    def with_hash(self) -> "ProductionWorkflowReceipt":
        digest = _sha256_json(self._identity_payload())
        return ProductionWorkflowReceipt(
            project_id=self.project_id,
            plan_sha256=self.plan_sha256,
            export_id=self.export_id,
            manifest_sha256=self.manifest_sha256,
            summary=self.summary,
            output_root=self.output_root,
            zip_path=self.zip_path,
            part_ids=self.part_ids,
            formats=self.formats,
            project_save_required=self.project_save_required,
            created_at=self.created_at,
            receipt_sha256=digest,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = self._identity_payload()
        payload["receipt_sha256"] = self.receipt_sha256 or _sha256_json(payload)
        return payload


class ProductionWorkflowCoordinator:
    """Plan and execute production packages through the existing release engine."""

    def __init__(self, application_context: UnifiedApplicationContext) -> None:
        self.application_context = application_context
        self.latest_plan: ProductionWorkflowPlan | None = None
        self.latest_receipt: ProductionWorkflowReceipt | None = None

    @property
    def workspace(self) -> Any | None:
        return self.application_context.workspace

    @staticmethod
    def _project_state_sha256(project: Any) -> str:
        method = getattr(project, "manufacturing_state_sha256", None)
        if callable(method):
            return str(method())
        method = getattr(project, "revision_content_sha256", None)
        if callable(method):
            return str(method())
        return _sha256_json(project.to_dict())

    def build_plan(
        self,
        formats: Iterable[str] = DEFAULT_WORKFLOW_FORMATS,
        *,
        selection_only: bool = False,
    ) -> ProductionWorkflowPlan:
        requested = _unique(formats)
        snapshot = self.application_context.snapshot
        workspace = self.workspace
        blocking: list[str] = []
        selected_ids = tuple(snapshot.selection.entity_ids)

        if workspace is None:
            plan = ProductionWorkflowPlan(
                project_id="",
                project_schema="",
                project_state_sha256="",
                context_generation=snapshot.generation,
                selection_only=bool(selection_only),
                selected_entity_ids=selected_ids,
                part_ids=(),
                requested_formats=requested,
                parts=(),
                blocking_codes=("U4_NO_ACTIVE_PROJECT",),
            )
            self.latest_plan = plan
            return plan

        try:
            self.application_context.assert_consistent()
        except Exception:
            blocking.extend(self.application_context.integrity_blocking_codes())
            if not blocking:
                blocking.append("U4_CONTEXT_INCONSISTENT")

        if any(U3_SAFETY_FLAGS.values()) or any(U4_SAFETY_FLAGS.values()):
            blocking.append("U4_MACHINE_TRANSFER_BOUNDARY_OPEN")
        if bool(getattr(workspace.session, "read_only", False)):
            blocking.append("U4_PROJECT_READ_ONLY")
        if not requested:
            blocking.append("U4_NO_FORMATS_SELECTED")

        project = workspace.project
        if selection_only:
            part_ids = tuple(value for value in selected_ids if value in project.parts)
            if not selected_ids:
                blocking.append("U4_NO_SELECTION")
            elif not part_ids:
                blocking.append("U4_SELECTION_HAS_NO_PARTS")
        else:
            part_ids = tuple(sorted(str(value) for value in project.parts))
        if not part_ids:
            blocking.append("U4_NO_PARTS_IN_SCOPE")

        part_rows: list[ProductionPartReadiness] = []
        for part_id in part_ids:
            result = workspace.readiness_for_part(part_id, requested)
            part = project.parts[part_id]
            position = str(
                getattr(part, "part_position", "")
                or getattr(getattr(part, "source_identity", None), "part_position", "")
                or part_id
            )
            part_rows.append(
                ProductionPartReadiness(
                    part_id=part_id,
                    part_position=position,
                    requested_formats=requested,
                    allowed={fmt: bool(result.get("allowed", {}).get(fmt, False)) for fmt in requested},
                    blocking_codes=tuple(str(value) for value in result.get("blocking_codes", ()) if str(value)),
                    production_ready=bool(result.get("production_ready", False)),
                )
            )

        for fmt in requested:
            if part_rows and not all(row.allowed.get(fmt, False) for row in part_rows):
                blocking.append(f"U4_FORMAT_BLOCKED:{fmt}")

        plan = ProductionWorkflowPlan(
            project_id=str(project.project_id),
            project_schema=str(project.schema_version),
            project_state_sha256=self._project_state_sha256(project),
            context_generation=snapshot.generation,
            selection_only=bool(selection_only),
            selected_entity_ids=selected_ids,
            part_ids=part_ids,
            requested_formats=requested,
            parts=tuple(part_rows),
            blocking_codes=tuple(dict.fromkeys(blocking)),
        )
        self.latest_plan = plan
        return plan

    def execute_plan(
        self,
        plan: ProductionWorkflowPlan,
        output_dir: str | Path,
        *,
        create_zip: bool = True,
        user: str = "u4-workflow",
    ) -> ProductionWorkflowReceipt:
        workspace = self.workspace
        if workspace is None or str(workspace.project.project_id) != plan.project_id:
            raise RuntimeError("U4_PLAN_PROJECT_CHANGED")
        if any(U3_SAFETY_FLAGS.values()) or any(U4_SAFETY_FLAGS.values()):
            raise RuntimeError("U4_MACHINE_TRANSFER_BOUNDARY_OPEN")

        current = self.build_plan(plan.requested_formats, selection_only=plan.selection_only)
        if current.plan_sha256 != plan.plan_sha256:
            raise RuntimeError("U4_PLAN_STALE")
        if not current.can_execute:
            raise RuntimeError("U4_PLAN_BLOCKED: " + ", ".join(current.blocking_codes))

        target = Path(output_dir).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        manifest, root, zip_path = workspace.session.export_production_package(
            target,
            formats=current.requested_formats,
            part_ids=current.part_ids,
            create_zip=bool(create_zip),
            user=user or "u4-workflow",
        )
        # Do not auto-save/reload the project here. ProjectSession.save replaces
        # the in-memory ProjectModel with the verified package snapshot, which
        # would invalidate the currently bound viewer/grid identity.  The audit
        # record remains dirty in this exact session and the UI explicitly marks
        # that a normal project save is required.
        receipt = ProductionWorkflowReceipt(
            project_id=current.project_id,
            plan_sha256=current.plan_sha256,
            export_id=str(getattr(manifest, "export_id", "") or ""),
            manifest_sha256=str(getattr(manifest, "manifest_sha256", "") or ""),
            summary=str(getattr(manifest, "summary", "") or ""),
            output_root=str(Path(root)),
            zip_path=str(Path(zip_path)) if zip_path else "",
            part_ids=current.part_ids,
            formats=current.requested_formats,
            project_save_required=bool(getattr(workspace.session, "dirty", False)),
        ).with_hash()
        receipt_path = Path(root) / "CWS_U4_WORKFLOW_RECEIPT.json"
        receipt_path.write_text(
            json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.latest_receipt = receipt
        return receipt


__all__ = [
    "DEFAULT_WORKFLOW_FORMATS",
    "ProductionPartReadiness",
    "ProductionWorkflowCoordinator",
    "ProductionWorkflowPlan",
    "ProductionWorkflowReceipt",
    "U4_RECEIPT_SCHEMA",
    "U4_SAFETY_FLAGS",
    "U4_WORKFLOW_SCHEMA",
]
