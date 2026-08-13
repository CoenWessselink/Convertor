from __future__ import annotations

from dataclasses import asdict, dataclass, field as dataclass_field
from enum import Enum
from typing import Any


class ExportStatus(str, Enum):
    EXPORTED = "exported"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    FAILED = "failed"


class ArtifactStatus(str, Enum):
    EXPORTED = "exported"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(slots=True)
class GateMessage:
    code: str
    message: str
    severity: str = "error"
    field: str = ""
    evidence: dict[str, Any] = dataclass_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ArtifactResult:
    format: str
    status: ArtifactStatus
    relative_path: str = ""
    sha256: str = ""
    size_bytes: int = 0
    media_type: str = "application/octet-stream"
    production_artifact: bool = False
    source: str = ""
    messages: list[GateMessage] = dataclass_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(slots=True)
class ExportItemResult:
    part_id: str
    part_position: str
    assembly_marks: list[str]
    classification: str
    production_identity_hash: str
    status: ExportStatus
    artifacts: list[ArtifactResult] = dataclass_field(default_factory=list)
    messages: list[GateMessage] = dataclass_field(default_factory=list)
    source_entity_id: str = ""
    source_file_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "part_id": self.part_id,
            "part_position": self.part_position,
            "assembly_marks": list(self.assembly_marks),
            "classification": self.classification,
            "production_identity_hash": self.production_identity_hash,
            "status": self.status.value,
            "source_entity_id": self.source_entity_id,
            "source_file_id": self.source_file_id,
            "messages": [m.to_dict() for m in self.messages],
            "artifacts": [a.to_dict() for a in self.artifacts],
        }


@dataclass(slots=True)
class AssemblyPackageResult:
    assembly_mark: str
    quantity: int
    part_ids: list[str]
    status: ExportStatus
    relative_path: str = ""
    sha256: str = ""
    messages: list[GateMessage] = dataclass_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(slots=True)
class ExportManifest:
    schema_version: str
    product: str
    product_version: str
    export_id: str
    created_at_utc: str
    project_id: str
    project_name: str
    project_state_hash: str
    requested_formats: list[str]
    strict_mode: bool
    items: list[ExportItemResult] = dataclass_field(default_factory=list)
    assemblies: list[AssemblyPackageResult] = dataclass_field(default_factory=list)
    messages: list[GateMessage] = dataclass_field(default_factory=list)
    summary: dict[str, Any] = dataclass_field(default_factory=dict)
    manifest_sha256: str = ""

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "product": self.product,
            "product_version": self.product_version,
            "export_id": self.export_id,
            "created_at_utc": self.created_at_utc,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_state_hash": self.project_state_hash,
            "requested_formats": list(self.requested_formats),
            "strict_mode": self.strict_mode,
            "items": [item.to_dict() for item in self.items],
            "assemblies": [assembly.to_dict() for assembly in self.assemblies],
            "messages": [m.to_dict() for m in self.messages],
            "summary": self.summary,
        }
        if include_hash:
            data["manifest_sha256"] = self.manifest_sha256
        return data
