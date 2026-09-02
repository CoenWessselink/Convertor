"""Fail-closed export-scope and job contracts for CWS Viewer V15 T7."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from cws_convertor.production_export.utils import stable_hash
from cws_viewer.version import VIEWER_PREVIEW_VERSION

V15_T7_SCHEMA = "cws-viewer-export-center-1.0"
V15_T7_VERSION = VIEWER_PREVIEW_VERSION


class ExportScopeKind(StrEnum):
    FULL_PROJECT = "full_project"
    CURRENT_SELECTION = "current_selection"
    ENTITY_IDS = "entity_ids"
    PART_POSITIONS = "part_positions"
    ASSEMBLY_MARKS = "assembly_marks"
    PROJECT_PHASE = "project_phase"
    REVISION_DELTA = "revision_delta"
    BATCH = "batch"
    NESTING_RUN = "nesting_run"
    NESTING_BAR = "nesting_bar"


class ExportJobStatus(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    BLOCKED = "blocked"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ExportScope:
    kind: ExportScopeKind | str
    values: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    recursive: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", ExportScopeKind(self.kind))
        object.__setattr__(
            self,
            "values",
            tuple(dict.fromkeys(str(value).strip() for value in self.values if str(value).strip())),
        )
        object.__setattr__(
            self,
            "entity_ids",
            tuple(dict.fromkeys(str(value).strip() for value in self.entity_ids if str(value).strip())),
        )
        object.__setattr__(self, "metadata", dict(self.metadata or {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "values": list(self.values),
            "entity_ids": list(self.entity_ids),
            "recursive": bool(self.recursive),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ScopeResolution:
    scope: ExportScope
    selected_part_ids: tuple[str, ...]
    blocking_codes: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()
    project_state_hash: str = ""
    schema_version: str = V15_T7_SCHEMA
    manifest_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "selected_part_ids", tuple(sorted(dict.fromkeys(self.selected_part_ids))))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(self.blocking_codes)))
        object.__setattr__(self, "messages", tuple(self.messages))
        if self.manifest_sha256:
            expected = self.calculate_hash()
            if expected != self.manifest_sha256:
                raise ValueError("Export-scope manifest hash klopt niet")

    @property
    def allowed(self) -> bool:
        return bool(self.selected_part_ids) and not self.blocking_codes

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scope": self.scope.to_dict(),
            "selected_part_ids": list(self.selected_part_ids),
            "blocking_codes": list(self.blocking_codes),
            "messages": list(self.messages),
            "project_state_hash": self.project_state_hash,
            "allowed": self.allowed,
        }

    def calculate_hash(self) -> str:
        return stable_hash(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "ScopeResolution":
        result = cls(manifest_sha256="", **kwargs)
        return cls(**kwargs, manifest_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_dict()
        payload["manifest_sha256"] = self.manifest_sha256
        return payload


@dataclass(frozen=True, slots=True)
class ExportPreflightItem:
    part_id: str
    part_position: str
    blocking_codes: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.blocking_codes

    def to_dict(self) -> dict[str, Any]:
        return {
            "part_id": self.part_id,
            "part_position": self.part_position,
            "blocking_codes": list(self.blocking_codes),
            "messages": list(self.messages),
            "ready": self.ready,
        }


@dataclass(frozen=True, slots=True)
class ExportPreflight:
    resolution: ScopeResolution
    requested_formats: tuple[str, ...]
    items: tuple[ExportPreflightItem, ...]
    blocking_codes: tuple[str, ...] = ()
    schema_version: str = V15_T7_SCHEMA
    manifest_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested_formats", tuple(dict.fromkeys(self.requested_formats)))
        object.__setattr__(self, "items", tuple(self.items))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(self.blocking_codes)))
        if self.manifest_sha256 and self.calculate_hash() != self.manifest_sha256:
            raise ValueError("Export-preflight manifest hash klopt niet")

    @property
    def allowed(self) -> bool:
        return self.resolution.allowed and not self.blocking_codes and all(item.ready for item in self.items)

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "scope_manifest_sha256": self.resolution.manifest_sha256,
            "requested_formats": list(self.requested_formats),
            "items": [item.to_dict() for item in self.items],
            "blocking_codes": list(self.blocking_codes),
            "allowed": self.allowed,
        }

    def calculate_hash(self) -> str:
        return stable_hash(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "ExportPreflight":
        result = cls(manifest_sha256="", **kwargs)
        return cls(**kwargs, manifest_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_dict()
        payload["manifest_sha256"] = self.manifest_sha256
        payload["resolution"] = self.resolution.to_dict()
        return payload


@dataclass(slots=True)
class ExportJob:
    job_id: str
    scope: ExportScope
    requested_formats: tuple[str, ...]
    preflight: ExportPreflight
    status: ExportJobStatus = ExportJobStatus.PLANNED
    progress: float = 0.0
    output_dir: str = ""
    package_path: str = ""
    export_manifest_sha256: str = ""
    error: str = ""

    def __post_init__(self) -> None:
        self.status = ExportJobStatus(self.status)
        self.requested_formats = tuple(dict.fromkeys(self.requested_formats))
        self.progress = max(0.0, min(1.0, float(self.progress)))

    @property
    def releasable(self) -> bool:
        return self.status == ExportJobStatus.READY and self.preflight.allowed

    def evidence_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "scope": self.scope.to_dict(),
            "requested_formats": list(self.requested_formats),
            "preflight_manifest_sha256": self.preflight.manifest_sha256,
            "status": self.status.value,
            "progress": self.progress,
            "output_dir": self.output_dir,
            "package_path": self.package_path,
            "export_manifest_sha256": self.export_manifest_sha256,
            "error": self.error,
        }


def export_center_contract() -> dict[str, Any]:
    return {
        "schema": V15_T7_SCHEMA,
        "version": V15_T7_VERSION,
        "capabilities": {
            "scope_first_export": True,
            "full_project_scope": True,
            "current_selection_scope": True,
            "explicit_entity_scope": True,
            "part_position_scope": True,
            "assembly_mark_scope": True,
            "project_phase_scope": True,
            "revision_delta_scope": True,
            "batch_scope": True,
            "nesting_run_scope": True,
            "nesting_bar_scope": True,
            "deterministic_scope_manifest": True,
            "release_preflight": True,
            "production_export_engine_reuse": True,
            "job_lifecycle": True,
            "job_cancel_before_write": True,
            "checksum_manifest": True,
        },
        "safety": {
            "silent_scope_broadening": False,
            "missing_scope_metadata_falls_back_to_project": False,
            "blocked_artifact_counts_as_released": False,
            "approximate_geometry_promoted_to_production": False,
            "machine_transfer_enabled": False,
        },
    }


__all__ = [
    "V15_T7_SCHEMA",
    "V15_T7_VERSION",
    "ExportScopeKind",
    "ExportJobStatus",
    "ExportScope",
    "ScopeResolution",
    "ExportPreflightItem",
    "ExportPreflight",
    "ExportJob",
    "export_center_contract",
]
