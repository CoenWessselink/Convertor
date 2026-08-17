"""M8 scope-first manufacturing evidence package contracts."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from cws_convertor.production_export.utils import stable_hash

M8_PACKAGE_SCHEMA = "cws-manufacturing-evidence-package-1.0"
M8_PREFLIGHT_SCHEMA = "cws-manufacturing-export-preflight-1.0"


@dataclass(frozen=True, slots=True)
class ManufacturingPackagePreflight:
    project_id: str
    project_state_hash: str
    scope_manifest_sha256: str
    selected_part_ids: tuple[str, ...]
    selected_instance_ids: tuple[str, ...]
    neutral_job_ids: tuple[str, ...]
    evidence_sha256s: tuple[str, ...]
    blocking_codes: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()
    manifest_sha256: str = ""
    schema_version: str = M8_PREFLIGHT_SCHEMA

    def __post_init__(self) -> None:
        for name in ("selected_part_ids", "selected_instance_ids", "neutral_job_ids", "evidence_sha256s"):
            object.__setattr__(self, name, tuple(sorted(dict.fromkeys(getattr(self, name)))))
        object.__setattr__(self, "blocking_codes", tuple(sorted(dict.fromkeys(self.blocking_codes))))
        object.__setattr__(self, "messages", tuple(self.messages))
        if not self.project_id.strip() or not self.project_state_hash.strip() or not self.scope_manifest_sha256.strip():
            raise ValueError("M8 preflight mist project/scope-identiteit")
        expected = self.calculate_hash()
        if self.manifest_sha256 and self.manifest_sha256 != expected:
            raise ValueError("M8 preflight manifest hash klopt niet")

    @property
    def allowed(self) -> bool:
        return bool(self.selected_part_ids) and bool(self.selected_instance_ids) and not self.blocking_codes

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "project_state_hash": self.project_state_hash,
            "scope_manifest_sha256": self.scope_manifest_sha256,
            "selected_part_ids": list(self.selected_part_ids),
            "selected_instance_ids": list(self.selected_instance_ids),
            "neutral_job_ids": list(self.neutral_job_ids),
            "evidence_sha256s": list(self.evidence_sha256s),
            "blocking_codes": list(self.blocking_codes),
            "messages": list(self.messages),
            "allowed": self.allowed,
        }

    def calculate_hash(self) -> str:
        return stable_hash(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "ManufacturingPackagePreflight":
        # Hash the normalized immutable instance. This prevents caller set/dict
        # iteration order from influencing the evidence identity.
        result = cls(manifest_sha256="", **kwargs)
        return replace(result, manifest_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        result = self.payload_dict()
        result["manifest_sha256"] = self.manifest_sha256
        return result


@dataclass(frozen=True, slots=True)
class ManufacturingPackageArtifact:
    evidence_type: str
    subject_id: str
    relative_path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        for label, value in (
            ("evidence_type", self.evidence_type),
            ("subject_id", self.subject_id),
            ("relative_path", self.relative_path),
            ("sha256", self.sha256),
        ):
            if not str(value).strip():
                raise ValueError(f"M8 package artifact mist {label}")
        if int(self.size_bytes) < 0:
            raise ValueError("M8 package artifact size is ongeldig")

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "subject_id": self.subject_id,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": int(self.size_bytes),
        }


@dataclass(frozen=True, slots=True)
class ManufacturingPackageManifest:
    package_id: str
    project_id: str
    project_state_hash: str
    scope_manifest_sha256: str
    preflight_manifest_sha256: str
    selected_part_ids: tuple[str, ...]
    selected_instance_ids: tuple[str, ...]
    neutral_job_ids: tuple[str, ...]
    artifacts: tuple[ManufacturingPackageArtifact, ...]
    blocking_codes: tuple[str, ...] = ()
    manifest_sha256: str = ""
    schema_version: str = M8_PACKAGE_SCHEMA

    def __post_init__(self) -> None:
        for name in ("selected_part_ids", "selected_instance_ids", "neutral_job_ids"):
            object.__setattr__(self, name, tuple(sorted(dict.fromkeys(getattr(self, name)))))
        object.__setattr__(self, "artifacts", tuple(sorted(self.artifacts, key=lambda item: item.relative_path)))
        object.__setattr__(self, "blocking_codes", tuple(sorted(dict.fromkeys(self.blocking_codes))))
        for label, value in (
            ("package_id", self.package_id),
            ("project_id", self.project_id),
            ("project_state_hash", self.project_state_hash),
            ("scope_manifest_sha256", self.scope_manifest_sha256),
            ("preflight_manifest_sha256", self.preflight_manifest_sha256),
        ):
            if not str(value).strip():
                raise ValueError(f"M8 package manifest mist {label}")
        expected = self.calculate_hash()
        if self.manifest_sha256 and self.manifest_sha256 != expected:
            raise ValueError("M8 package manifest hash klopt niet")

    @property
    def production_evidence_complete(self) -> bool:
        return bool(self.artifacts) and not self.blocking_codes

    @property
    def machine_transfer_allowed(self) -> bool:
        return False

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "package_id": self.package_id,
            "project_id": self.project_id,
            "project_state_hash": self.project_state_hash,
            "scope_manifest_sha256": self.scope_manifest_sha256,
            "preflight_manifest_sha256": self.preflight_manifest_sha256,
            "selected_part_ids": list(self.selected_part_ids),
            "selected_instance_ids": list(self.selected_instance_ids),
            "neutral_job_ids": list(self.neutral_job_ids),
            "artifacts": [item.to_dict() for item in self.artifacts],
            "blocking_codes": list(self.blocking_codes),
            "production_evidence_complete": self.production_evidence_complete,
            "machine_transfer_allowed": self.machine_transfer_allowed,
        }

    def calculate_hash(self) -> str:
        return stable_hash(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "ManufacturingPackageManifest":
        result = cls(manifest_sha256="", **kwargs)
        return replace(result, manifest_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        result = self.payload_dict()
        result["manifest_sha256"] = self.manifest_sha256
        return result


__all__ = [
    "M8_PACKAGE_SCHEMA", "M8_PREFLIGHT_SCHEMA", "ManufacturingPackagePreflight",
    "ManufacturingPackageArtifact", "ManufacturingPackageManifest",
]
