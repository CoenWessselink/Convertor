"""Unified U2/U4 facade for Scribing M9-M18 authorities.

M1-M8 remain the canonical Viewer V15 implementations.  M9-M18 normally load
from the checksum-bound frozen M18 runtime.  If that historical payload is not
available byte-exactly, the application must stay usable while failing closed:
no machine observation, deployment transport or direct transfer is enabled.

The fail-closed compatibility modules below are intentionally small.  They are
not presented as a recovered M18 binary and they never create external release
evidence.  ``m18_runtime_status()`` makes the distinction explicit.
"""
from __future__ import annotations

import base64
import hashlib
import importlib
from io import BytesIO
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
from types import ModuleType
from typing import Any
import zipfile

from cws_convertor.project.model import ProjectModel
from cws_convertor.project.unified_schema import m18_store_snapshot
from .m18_runtime_access import install_m18_runtime_access

M18_RUNTIME_ARCHIVE = "m18_authority_runtime.zip"
M18_RUNTIME_PAYLOAD_DIR = "m18_payload"
M18_RUNTIME_PAYLOAD_STEM = "m18_authority_runtime.b64"
M18_RUNTIME_PAYLOAD_COUNT = 11
M18_RUNTIME_PAYLOAD_SHA256 = "f05acd67c0264fa15dee06de0fcf0074aa750597e56dbf558c38e41f2ad1e401"
M18_RUNTIME_SHA256 = "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1"
M18_ORIGIN_VERSION = "0.8.30-beta-dev"
M18_ORIGIN_COMMIT = "b04b1c203583295e8c5ed018d75de68b2319c839"
M18_ORIGIN_TAG = "scribing-m18-deployment-assurance-0.8.30-beta-dev"
M18_RUNTIME_PACKAGE = "cws_m18_authority"

CANONICAL_M1_M8 = {
    "M1": "cws_convertor.manufacturing.faces",
    "M2": "cws_convertor.manufacturing.contact",
    "M3": "cws_convertor.manufacturing.marking",
    "M4": "cws_convertor.manufacturing.identification",
    "M5": "cws_convertor.manufacturing.machine_capability",
    "M6": "cws_convertor.manufacturing.nesting_binding",
    "M7": "cws_convertor.manufacturing.neutral_job",
    "M8": "cws_viewer.export_center.manufacturing_service",
}

AUTHORITY_MODULES = {
    "M9": ("dstv_marking_adapter",),
    "M10": ("reporting",),
    "M11": ("release_gate",),
    "M12": ("simulation_contracts", "simulation_engine", "simulation_validator", "simulation_service", "adapter_rehearsal"),
    "M13": ("adapter_certification",),
    "M14": ("adapter_sdk", "certification_ops"),
    "M15": ("certification_lab",),
    "M16": ("fleet_governance",),
    "M17": ("controlled_deployment",),
    "M18": ("deployment_assurance",),
}

STORE_BY_PHASE = {
    "M9": ("manufacturing_dstv_roundtrips",),
    "M11": ("manufacturing_release_records",),
    "M12": ("manufacturing_simulations", "manufacturing_adapter_rehearsals"),
    "M13": ("manufacturing_adapter_evidence_cases", "manufacturing_adapter_certificates", "manufacturing_adapter_certificate_revocations"),
    "M14": ("manufacturing_adapter_sdk_manifests", "manufacturing_adapter_certification_batches", "manufacturing_adapter_certificate_supersessions"),
    "M15": ("manufacturing_adapter_lab_matrices", "manufacturing_adapter_lab_campaigns", "manufacturing_adapter_lab_impacts", "manufacturing_adapter_lab_diffs", "manufacturing_adapter_lab_candidates"),
    "M16": ("manufacturing_fleet_sites", "manufacturing_fleet_machine_bindings", "manufacturing_fleet_policies", "manufacturing_fleet_trusted_signers", "manufacturing_fleet_external_approvals", "manufacturing_fleet_recertification_queues", "manufacturing_fleet_deployments"),
    "M17": ("manufacturing_deployment_stations", "manufacturing_deployment_control_policies", "manufacturing_deployment_rollout_plans", "manufacturing_deployment_rollback_references", "manufacturing_deployment_release_requests", "manufacturing_deployment_operator_approvals", "manufacturing_deployment_airgap_exports", "manufacturing_deployment_import_receipts", "manufacturing_deployment_receipts", "manufacturing_deployment_acknowledgements", "manufacturing_deployment_withdrawals"),
    "M18": ("manufacturing_media_devices", "manufacturing_media_custody_policies", "manufacturing_media_custody_sessions", "manufacturing_media_custody_events", "manufacturing_station_reconciliations", "manufacturing_rollback_drills", "manufacturing_deployment_closures"),
}

_ALLOWED_MODULES = {name for names in AUTHORITY_MODULES.values() for name in names}
_RUNTIME_BYTES: bytes | None = None
_RUNTIME_IMPORT_ROOT: Path | None = None
_RUNTIME_ERROR: str | None = None
_FALLBACK_MODULES: dict[str, ModuleType] = {}


def runtime_payload_dir() -> Path:
    return Path(__file__).resolve().with_name(M18_RUNTIME_PAYLOAD_DIR)


def _expected_payload_names() -> tuple[str, ...]:
    return tuple(f"{M18_RUNTIME_PAYLOAD_STEM}.{i:03d}" for i in range(1, M18_RUNTIME_PAYLOAD_COUNT + 1))


def _payload_files() -> tuple[Path, ...]:
    directory = runtime_payload_dir()
    if not directory.is_dir():
        raise RuntimeError(f"Frozen M18 payload-directory ontbreekt: {directory}")
    files = tuple(sorted(directory.glob(f"{M18_RUNTIME_PAYLOAD_STEM}.*")))
    names = tuple(path.name for path in files)
    expected = _expected_payload_names()
    if names != expected:
        raise RuntimeError(f"Frozen M18 payload chunkset klopt niet; expected={expected!r} observed={names!r}")
    return files


def _validate_runtime_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = str(info.filename or "")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Onveilig M18 runtime-pad: {name!r}")
    if not path.parts or path.parts[0] != M18_RUNTIME_PACKAGE:
        raise RuntimeError(f"M18 runtime bevat entry buiten geïsoleerd pakket: {name}")
    unix_mode = (int(info.external_attr) >> 16) & 0o170000
    if unix_mode == stat.S_IFLNK:
        raise RuntimeError(f"M18 runtime bevat verboden symlink-entry: {name}")
    return path


def _verified_runtime_bytes() -> bytes:
    global _RUNTIME_BYTES, _RUNTIME_ERROR
    if _RUNTIME_BYTES is not None:
        return _RUNTIME_BYTES
    try:
        payload = b"".join(b"".join(path.read_bytes().split()) for path in _payload_files())
        payload_sha = hashlib.sha256(payload).hexdigest()
        if payload_sha != M18_RUNTIME_PAYLOAD_SHA256:
            raise RuntimeError(f"Frozen M18 Base64 payload SHA-256 wijkt af; expected={M18_RUNTIME_PAYLOAD_SHA256} actual={payload_sha}")
        runtime = base64.b64decode(payload, validate=True)
        runtime_sha = hashlib.sha256(runtime).hexdigest()
        if runtime_sha != M18_RUNTIME_SHA256:
            raise RuntimeError(f"Frozen M18 decoded runtime SHA-256 wijkt af; expected={M18_RUNTIME_SHA256} actual={runtime_sha}")
        with zipfile.ZipFile(BytesIO(runtime), "r") as source:
            bad = source.testzip()
            if bad is not None:
                raise RuntimeError(f"Frozen M18 runtime CRC-fout in {bad}")
            validated = [_validate_runtime_member(info) for info in source.infolist()]
            if PurePosixPath(M18_RUNTIME_PACKAGE) / "__init__.py" not in validated:
                raise RuntimeError("Frozen M18 authority runtime mist package init")
        _RUNTIME_BYTES = runtime
        _RUNTIME_ERROR = None
        return runtime
    except Exception as exc:
        _RUNTIME_ERROR = f"{type(exc).__name__}: {exc}"
        raise


def m18_runtime_status() -> dict[str, Any]:
    try:
        _verified_runtime_bytes()
        verified = True
        error = None
    except Exception:
        verified = False
        error = _RUNTIME_ERROR
    return {
        "mode": "frozen_exact" if verified else "safe_fallback",
        "verified": verified,
        "runtime_sha256": M18_RUNTIME_SHA256,
        "payload_sha256": M18_RUNTIME_PAYLOAD_SHA256,
        "origin_commit": M18_ORIGIN_COMMIT,
        "error": error,
        "safety": {
            "machine_observed_by_cws": False,
            "deployment_transport_authorized": False,
            "direct_machine_transfer": False,
            "machine_transfer_allowed": False,
        },
    }


def verify_m18_runtime_archive() -> str:
    """Strictly verify the historical frozen M18 runtime or raise."""
    _verified_runtime_bytes()
    return M18_RUNTIME_SHA256


def _prepare_runtime_import_root() -> Path:
    global _RUNTIME_IMPORT_ROOT
    if _RUNTIME_IMPORT_ROOT is not None:
        return _RUNTIME_IMPORT_ROOT
    runtime = _verified_runtime_bytes()
    root = Path(tempfile.mkdtemp(prefix=f"cws-m18-{M18_RUNTIME_SHA256[:12]}-"))
    resolved_root = root.resolve()
    with zipfile.ZipFile(BytesIO(runtime), "r") as source:
        for info in source.infolist():
            relative = _validate_runtime_member(info)
            target = root.joinpath(*relative.parts)
            resolved_target = target.resolve()
            if resolved_target != resolved_root and resolved_root not in resolved_target.parents:
                raise RuntimeError(f"M18 runtime-pad ontsnapt extractieroot: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(info))
    _RUNTIME_IMPORT_ROOT = root
    return root


def _activate_runtime() -> None:
    install_m18_runtime_access()
    root = _prepare_runtime_import_root()
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    importlib.invalidate_caches()
    package = importlib.import_module(M18_RUNTIME_PACKAGE)
    if getattr(package, "M18_ORIGIN_COMMIT", "") != M18_ORIGIN_COMMIT:
        raise RuntimeError("M18 authority runtime heeft onverwachte source-commit identiteit")


def _release_current(project: ProjectModel):
    records = getattr(project, "manufacturing_release_records", {}) or {}
    if not isinstance(records, dict) or not records:
        return None
    # Fallback never invents or upgrades a release.  It only exposes an already
    # persisted record, newest by deterministic key order.
    return records[sorted(records)[-1]]


def _assurance_dashboard(project: ProjectModel) -> dict[str, Any]:
    return {
        "schema": "cws-m18-safe-fallback-1.0",
        "project_id": project.project_id,
        "authority_runtime_verified": False,
        "machine_observed_by_cws": False,
        "deployment_transport_authorized": False,
        "direct_machine_transfer": False,
        "machine_transfer_allowed": False,
        "media_devices": len(getattr(project, "manufacturing_media_devices", {}) or {}),
        "deployment_closures": len(getattr(project, "manufacturing_deployment_closures", {}) or {}),
        "status": "BLOCKED_EXTERNAL_EVIDENCE",
    }


def _fallback_module(name: str) -> ModuleType:
    existing = _FALLBACK_MODULES.get(name)
    if existing is not None:
        return existing
    module = ModuleType(f"{M18_RUNTIME_PACKAGE}.{name}")
    module.__dict__.update({
        "M18_ORIGIN_COMMIT": M18_ORIGIN_COMMIT,
        "M18_ORIGIN_VERSION": M18_ORIGIN_VERSION,
        "AUTHORITY_RUNTIME_VERIFIED": False,
        "SAFE_FALLBACK": True,
        "MACHINE_OBSERVED_BY_CWS": False,
        "DEPLOYMENT_TRANSPORT_AUTHORIZED": False,
        "DIRECT_MACHINE_TRANSFER": False,
    })
    if name == "release_gate":
        module.current_scribing_release = _release_current
    if name == "deployment_assurance":
        module.build_deployment_assurance_dashboard = _assurance_dashboard
    sys.modules[module.__name__] = module
    _FALLBACK_MODULES[name] = module
    return module


def load_authority_module(name: str):
    if name not in _ALLOWED_MODULES:
        raise KeyError(f"Module {name!r} is geen publieke U2 M9-M18 authority-module")
    try:
        _activate_runtime()
        return importlib.import_module(f"{M18_RUNTIME_PACKAGE}.{name}")
    except Exception:
        return _fallback_module(name)


def authority_chain_status(project: ProjectModel) -> dict[str, Any]:
    install_m18_runtime_access()
    runtime = m18_runtime_status()
    stores = m18_store_snapshot(project)
    phases: dict[str, Any] = {}
    for phase, module_names in AUTHORITY_MODULES.items():
        loaded: list[str] = []
        errors: list[str] = []
        for module_name in module_names:
            try:
                load_authority_module(module_name)
                loaded.append(module_name)
            except Exception as exc:
                errors.append(f"{module_name}: {type(exc).__name__}: {exc}")
        phase_stores = STORE_BY_PHASE.get(phase, ())
        phases[phase] = {
            "modules": list(module_names),
            "loaded_modules": loaded,
            "errors": errors,
            "store_counts": {key: len(stores.get(key, {})) if isinstance(stores.get(key), dict) else stores.get(key) for key in phase_stores},
            "available": not errors,
            "runtime_mode": runtime["mode"],
        }
    return {
        "schema": "cws-unified-manufacturing-authority-1.1",
        "project_id": project.project_id,
        "project_schema": project.schema_version,
        "canonical_m1_m8": dict(CANONICAL_M1_M8),
        "m9_m18": phases,
        "m18_origin": {
            "version": M18_ORIGIN_VERSION,
            "commit": M18_ORIGIN_COMMIT,
            "tag": M18_ORIGIN_TAG,
            "payload_sha256": M18_RUNTIME_PAYLOAD_SHA256,
            "runtime_sha256": M18_RUNTIME_SHA256,
            "runtime_verified": runtime["verified"],
            "runtime_mode": runtime["mode"],
            "runtime_error": runtime["error"],
        },
        "safety": dict(runtime["safety"]),
        "all_authority_modules_available": all(item["available"] for item in phases.values()),
        "external_authority_evidence_complete": bool(runtime["verified"]),
    }


__all__ = [
    "M18_RUNTIME_PAYLOAD_SHA256", "M18_RUNTIME_SHA256", "M18_ORIGIN_VERSION",
    "M18_ORIGIN_COMMIT", "M18_ORIGIN_TAG", "CANONICAL_M1_M8", "AUTHORITY_MODULES",
    "m18_runtime_status", "verify_m18_runtime_archive", "load_authority_module", "authority_chain_status",
]
