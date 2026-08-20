"""Validated postprocessor boundary for Profile Nesting phase 8.

This module deliberately does *not* ship a proprietary machine adapter.  It
provides the safety contract that a future adapter must satisfy before it can
turn a neutral profile-cut job into controller-specific output.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
import hashlib
import json
from typing import Any, Protocol

from cws_convertor.project.model import stable_sha256
from cws_convertor.production_export.utils import atomic_directory, atomic_write, canonical_json_bytes, sha256_file
from .phase7_reporting import NEUTRAL_JOB_FORMAT

POSTPROCESSOR_CONTRACT_VERSION = "1.0"
POSTPROCESSOR_PACKAGE_FORMAT = "CWS_PROFILE_NESTING_MACHINE_PACKAGE_V1"


class PostprocessorError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass(frozen=True)
class PostprocessorEvidence:
    status: str = "unvalidated"  # unvalidated | owner_validated | revoked
    approved_by: str = ""
    approved_at: str = ""
    machine_id: str = ""
    controller_id: str = ""
    adapter_version: str = ""
    straight_case_ids: tuple[str, ...] = ()
    angle_case_ids: tuple[str, ...] = ()
    golden_program_sha256: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["straight_case_ids"] = list(self.straight_case_ids)
        payload["angle_case_ids"] = list(self.angle_case_ids)
        payload["golden_program_sha256"] = list(self.golden_program_sha256)
        return payload

    @property
    def owner_validated(self) -> bool:
        return (
            self.status == "owner_validated"
            and bool(self.approved_by)
            and bool(self.approved_at)
            and bool(self.machine_id)
            and bool(self.controller_id)
            and bool(self.adapter_version)
            and bool(self.straight_case_ids)
            and bool(self.angle_case_ids)
            and bool(self.golden_program_sha256)
            and all(len(x) == 64 for x in self.golden_program_sha256)
        )


@dataclass(frozen=True)
class PostprocessorDescriptor:
    adapter_id: str
    name: str
    machine_id: str
    controller_id: str
    adapter_version: str
    output_extensions: tuple[str, ...]
    evidence: PostprocessorEvidence
    enabled: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["output_extensions"] = list(self.output_extensions)
        payload["evidence"] = self.evidence.to_dict()
        payload["production_enabled"] = self.production_enabled
        payload["descriptor_hash"] = stable_sha256({k: v for k, v in payload.items() if k != "descriptor_hash"})
        return payload

    @property
    def production_enabled(self) -> bool:
        return (
            self.enabled
            and self.evidence.owner_validated
            and self.machine_id == self.evidence.machine_id
            and self.controller_id == self.evidence.controller_id
            and self.adapter_version == self.evidence.adapter_version
        )


class PostprocessorAdapter(Protocol):
    descriptor: PostprocessorDescriptor

    def render(self, neutral_job: dict[str, Any]) -> dict[str, bytes]:
        """Return relative output path -> immutable bytes. No network I/O."""


class PostprocessorRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, PostprocessorAdapter] = {}

    def register(self, adapter: PostprocessorAdapter) -> None:
        descriptor = adapter.descriptor
        if not descriptor.adapter_id or descriptor.adapter_id in self._adapters:
            raise PostprocessorError("CWS-NEST-031", "Postprocessor-ID ontbreekt of is dubbel")
        if not descriptor.machine_id or not descriptor.controller_id or not descriptor.adapter_version:
            raise PostprocessorError("CWS-NEST-031", "Postprocessor mist machine/controller/versie-identiteit")
        self._adapters[descriptor.adapter_id] = adapter

    def descriptors(self) -> list[PostprocessorDescriptor]:
        return [self._adapters[key].descriptor for key in sorted(self._adapters)]

    def get(self, adapter_id: str) -> PostprocessorAdapter:
        try:
            return self._adapters[adapter_id]
        except KeyError as exc:
            raise PostprocessorError("CWS-NEST-032", f"Onbekende postprocessor {adapter_id!r}") from exc

    def production_enabled_descriptors(self) -> list[PostprocessorDescriptor]:
        return [d for d in self.descriptors() if d.production_enabled]


DEFAULT_POSTPROCESSOR_REGISTRY = PostprocessorRegistry()


def load_neutral_job(value: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, dict):
        payload = dict(value)
    else:
        path = Path(value)
        payload = json.loads(path.read_text(encoding="utf-8"))
    validate_neutral_job(payload)
    return payload


def validate_neutral_job(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if str(payload.get("format") or "") != NEUTRAL_JOB_FORMAT:
        errors.append("neutral job format is onbekend")
    stored = str(payload.get("manifest_hash") or "")
    calculated = stable_sha256({k: v for k, v in payload.items() if k != "manifest_hash"})
    if not stored or stored != calculated:
        errors.append("neutral job manifest_hash mismatch")
    transfer = dict(payload.get("machine_transfer") or {})
    if bool(transfer.get("allowed")):
        errors.append("neutral job mag zelf geen machineoverdracht toestaan")
    jobs = list(payload.get("jobs") or [])
    if not jobs:
        errors.append("neutral job bevat geen staven/jobs")
    seen: set[str] = set()
    for raw in jobs:
        job = dict(raw)
        bar_id = str(job.get("bar_id") or "")
        if not bar_id or bar_id in seen:
            errors.append(f"ongeldige/dubbele bar-ID {bar_id!r}")
        seen.add(bar_id)
        if not str(dict(job.get("machine") or {}).get("machine_id") or ""):
            errors.append(f"bar {bar_id!r} mist machine-ID")
        if not str(job.get("bar_hash") or ""):
            errors.append(f"bar {bar_id!r} mist bar-hash")
    result = {"valid": not errors, "errors": errors, "manifest_hash": stored, "job_count": len(jobs)}
    if errors:
        raise PostprocessorError("CWS-NEST-033", "Neutral manufacturing job is ongeldig", details=result)
    return result


def _validate_rendered_files(files: dict[str, bytes], descriptor: PostprocessorDescriptor) -> list[tuple[str, bytes]]:
    if not files:
        raise PostprocessorError("CWS-NEST-034", "Postprocessor leverde geen uitvoer")
    accepted_ext = {x.lower() if x.startswith(".") else f".{x.lower()}" for x in descriptor.output_extensions}
    seen: set[str] = set()
    normalized: list[tuple[str, bytes]] = []
    total = 0
    for raw_name, raw_bytes in sorted(files.items()):
        name = str(raw_name).replace("\\", "/")
        pure = PurePosixPath(name)
        if not name or pure.is_absolute() or ".." in pure.parts or len(name) > 512:
            raise PostprocessorError("CWS-NEST-034", f"Onveilig postprocessorpad: {raw_name!r}")
        name = pure.as_posix()
        if name in seen:
            raise PostprocessorError("CWS-NEST-034", f"Dubbel postprocessorpad: {name}")
        seen.add(name)
        data = bytes(raw_bytes)
        if len(data) > 64 * 1024 * 1024:
            raise PostprocessorError("CWS-NEST-034", f"Postprocessorbestand te groot: {name}")
        total += len(data)
        if total > 256 * 1024 * 1024:
            raise PostprocessorError("CWS-NEST-034", "Postprocessoruitvoer overschrijdt totale limiet")
        if accepted_ext and PurePosixPath(name).suffix.lower() not in accepted_ext:
            raise PostprocessorError("CWS-NEST-034", f"Niet-geregistreerde uitvoerextensie: {name}")
        normalized.append((name, data))
    return normalized


def generate_machine_package(
    neutral_job: dict[str, Any] | str | Path,
    adapter_id: str,
    output_dir: str | Path,
    *,
    registry: PostprocessorRegistry = DEFAULT_POSTPROCESSOR_REGISTRY,
) -> dict[str, Any]:
    """Generate a controller package through a *validated* adapter only.

    The function writes files atomically but never opens a network connection or
    machine queue.  Transfer remains an explicit responsibility outside this
    boundary.
    """
    payload = load_neutral_job(neutral_job)
    adapter = registry.get(adapter_id)
    descriptor = adapter.descriptor
    if not descriptor.production_enabled:
        raise PostprocessorError(
            "CWS-NEST-035",
            "Postprocessor is niet eigenaar-gevalideerd en blijft productie-geblokkeerd",
            details={"descriptor": descriptor.to_dict()},
        )
    machine_ids = {str(dict(j.get("machine") or {}).get("machine_id") or "") for j in list(payload.get("jobs") or [])}
    if machine_ids != {descriptor.machine_id}:
        raise PostprocessorError(
            "CWS-NEST-036",
            "Neutral job en postprocessor horen niet bij exact dezelfde machine-ID",
            details={"job_machine_ids": sorted(machine_ids), "adapter_machine_id": descriptor.machine_id},
        )
    files = _validate_rendered_files(adapter.render(payload), descriptor)
    # Determinism check is part of the adapter contract. A second render must be
    # byte-identical before anything is published.
    repeated = _validate_rendered_files(adapter.render(payload), descriptor)
    if [(n, hashlib.sha256(b).hexdigest()) for n, b in files] != [(n, hashlib.sha256(b).hexdigest()) for n, b in repeated]:
        raise PostprocessorError("CWS-NEST-037", "Postprocessoruitvoer is niet deterministisch")

    package_name = f"{descriptor.adapter_id}_{str(payload.get('run_id') or 'run')[:12]}"
    final_root = Path(output_dir) / package_name
    with atomic_directory(final_root) as root:
        artifacts = []
        for name, data in files:
            target = root.joinpath(*PurePosixPath(name).parts)
            atomic_write(target, data)
            artifacts.append({"relative_path": name, "sha256": sha256_file(target), "size_bytes": len(data)})
        manifest = {
            "format": POSTPROCESSOR_PACKAGE_FORMAT,
            "schema_version": POSTPROCESSOR_CONTRACT_VERSION,
            "adapter": descriptor.to_dict(),
            "neutral_job_manifest_hash": payload.get("manifest_hash"),
            "run_id": payload.get("run_id"),
            "release_id": payload.get("release_id"),
            "machine_id": descriptor.machine_id,
            "controller_id": descriptor.controller_id,
            "machine_transfer": {"allowed": False, "reason": "Validated file generation only; network/machine transfer is a separate controlled action."},
            "artifacts": artifacts,
        }
        manifest["manifest_hash"] = stable_sha256({k: v for k, v in manifest.items() if k != "manifest_hash"})
        atomic_write(root / "manifest.json", canonical_json_bytes(manifest))
    return {"root": str(final_root), "manifest": manifest}


__all__ = [
    "POSTPROCESSOR_CONTRACT_VERSION", "POSTPROCESSOR_PACKAGE_FORMAT", "PostprocessorError",
    "PostprocessorEvidence", "PostprocessorDescriptor", "PostprocessorAdapter", "PostprocessorRegistry",
    "DEFAULT_POSTPROCESSOR_REGISTRY", "load_neutral_job", "validate_neutral_job", "generate_machine_package",
]
