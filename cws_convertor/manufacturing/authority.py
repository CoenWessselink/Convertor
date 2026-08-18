"""Unified U2 facade for Scribing M9-M18 authorities.

Canonical M1-M8 geometry/marking/nesting/neutral-job code remains the newer
Viewer V15 implementation in :mod:`cws_convertor.manufacturing`. The frozen
M18 authority implementation is kept checksum-bound and is loaded only for
M9-M18 evidence/release/governance operations. It reads and writes the *same*
Project Model 2.25 stores through ``m18_runtime_access``.
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
from typing import Any
import zipfile

from cws_convertor.project.model import ProjectModel
from cws_convertor.project.unified_schema import m18_store_snapshot
from .m18_runtime_access import install_m18_runtime_access

M18_RUNTIME_ARCHIVE = "m18_authority_runtime.zip"
M18_RUNTIME_PAYLOAD_DIR = "m18_payload_clean"
M18_RUNTIME_SHA256 = "30bcbb5bdd0aa6bac825a31dcbd5eb69586f051dc66c01e3485d4e8a56d7a745"
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
    "M12": (
        "simulation_contracts",
        "simulation_engine",
        "simulation_validator",
        "simulation_service",
        "adapter_rehearsal",
    ),
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
    "M13": (
        "manufacturing_adapter_evidence_cases",
        "manufacturing_adapter_certificates",
        "manufacturing_adapter_certificate_revocations",
    ),
    "M14": (
        "manufacturing_adapter_sdk_manifests",
        "manufacturing_adapter_certification_batches",
        "manufacturing_adapter_certificate_supersessions",
    ),
    "M15": (
        "manufacturing_adapter_lab_matrices",
        "manufacturing_adapter_lab_campaigns",
        "manufacturing_adapter_lab_impacts",
        "manufacturing_adapter_lab_diffs",
        "manufacturing_adapter_lab_candidates",
    ),
    "M16": (
        "manufacturing_fleet_sites",
        "manufacturing_fleet_machine_bindings",
        "manufacturing_fleet_policies",
        "manufacturing_fleet_trusted_signers",
        "manufacturing_fleet_external_approvals",
        "manufacturing_fleet_recertification_queues",
        "manufacturing_fleet_deployments",
    ),
    "M17": (
        "manufacturing_deployment_stations",
        "manufacturing_deployment_control_policies",
        "manufacturing_deployment_rollout_plans",
        "manufacturing_deployment_rollback_references",
        "manufacturing_deployment_release_requests",
        "manufacturing_deployment_operator_approvals",
        "manufacturing_deployment_airgap_exports",
        "manufacturing_deployment_import_receipts",
        "manufacturing_deployment_receipts",
        "manufacturing_deployment_acknowledgements",
        "manufacturing_deployment_withdrawals",
    ),
    "M18": (
        "manufacturing_media_devices",
        "manufacturing_media_custody_policies",
        "manufacturing_media_custody_sessions",
        "manufacturing_media_custody_events",
        "manufacturing_station_reconciliations",
        "manufacturing_rollback_drills",
        "manufacturing_deployment_closures",
    ),
}

_ALLOWED_MODULES = {name for names in AUTHORITY_MODULES.values() for name in names}
_ARCHIVE_VERIFIED = False
_COMPATIBILITY_ALIASES_INSTALLED = False
_RUNTIME_IMPORT_ROOT: Path | None = None
_RUNTIME_BYTES: bytes | None = None


def runtime_archive_path() -> Path:
    return Path(__file__).resolve().with_name(M18_RUNTIME_ARCHIVE)


def runtime_payload_dir() -> Path:
    return Path(__file__).resolve().with_name(M18_RUNTIME_PAYLOAD_DIR)


def _is_valid_runtime_zip(data: bytes) -> bool:
    if not data:
        return False
    try:
        with zipfile.ZipFile(BytesIO(data), "r") as source:
            bad = source.testzip()
            names = set(source.namelist())
            return bad is None and f"{M18_RUNTIME_PACKAGE}/__init__.py" in names
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return False


def _decode_clean_payload() -> bytes:
    payload_dir = runtime_payload_dir()
    if not payload_dir.is_dir():
        raise RuntimeError(f"M18 herstelpayload ontbreekt: {payload_dir}")
    parts = sorted(payload_dir.glob("m18_authority_runtime.b64.*"))
    if not parts:
        raise RuntimeError(f"M18 herstelpayload bevat geen delen: {payload_dir}")
    encoded = b"".join(part.read_bytes() for part in parts)
    try:
        data = base64.b64decode(encoded, validate=False)
    except Exception as exc:
        raise RuntimeError(f"M18 herstelpayload kan niet worden gedecodeerd: {exc}") from exc
    return data


def _runtime_archive_bytes() -> bytes:
    global _RUNTIME_BYTES
    if _RUNTIME_BYTES is not None:
        return _RUNTIME_BYTES

    archive = runtime_archive_path()
    primary = archive.read_bytes() if archive.is_file() else b""
    candidates: list[tuple[str, bytes]] = []
    if primary:
        candidates.append((str(archive), primary))
    try:
        recovered = _decode_clean_payload()
        candidates.append((str(runtime_payload_dir()), recovered))
    except RuntimeError:
        recovered = b""

    errors: list[str] = []
    for source_name, data in candidates:
        digest = hashlib.sha256(data).hexdigest()
        if digest != M18_RUNTIME_SHA256:
            errors.append(f"{source_name}: sha256={digest}")
            continue
        if not _is_valid_runtime_zip(data):
            errors.append(f"{source_name}: checksum klopt maar payload is geen geldige runtime-ZIP")
            continue
        _RUNTIME_BYTES = data
        return data

    if not candidates:
        raise RuntimeError("Frozen M18 authority runtime en herstelpayload ontbreken")
    raise RuntimeError(
        "Geen geldige checksum-bound M18 authority runtime beschikbaar; " + "; ".join(errors)
    )


def verify_m18_runtime_archive() -> str:
    global _ARCHIVE_VERIFIED
    data = _runtime_archive_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != M18_RUNTIME_SHA256:
        raise RuntimeError(
            "Frozen M18 authority runtime SHA-256 wijkt af; "
            f"expected={M18_RUNTIME_SHA256} actual={digest}"
        )
    _ARCHIVE_VERIFIED = True
    return digest


def _validate_runtime_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = str(info.filename or "")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Onveilig M18 runtime-pad: {name!r}")
    if not path.parts or path.parts[0] != M18_RUNTIME_PACKAGE:
        raise RuntimeError("M18 runtime bevat entry buiten het geïsoleerde pakket: " + name)
    unix_mode = (int(info.external_attr) >> 16) & 0o170000
    if unix_mode == stat.S_IFLNK:
        raise RuntimeError(f"M18 runtime bevat verboden symlink-entry: {name}")
    return path


def _prepare_runtime_import_root() -> Path:
    global _RUNTIME_IMPORT_ROOT
    if _RUNTIME_IMPORT_ROOT is not None:
        return _RUNTIME_IMPORT_ROOT

    verify_m18_runtime_archive()
    runtime_bytes = _runtime_archive_bytes()
    root = Path(tempfile.mkdtemp(prefix=f"cws-m18-{M18_RUNTIME_SHA256[:12]}-"))
    resolved_root = root.resolve()
    try:
        with zipfile.ZipFile(BytesIO(runtime_bytes), "r") as source:
            infos = source.infolist()
            if not infos:
                raise RuntimeError("Frozen M18 authority runtime is leeg")
            validated = [(info, _validate_runtime_member(info)) for info in infos]
            expected_init = f"{M18_RUNTIME_PACKAGE}/__init__.py"
            if expected_init not in {info.filename for info, _ in validated}:
                observed = [info.filename for info, _ in validated[:8]]
                raise RuntimeError(
                    f"M18 runtime mist {expected_init}; eerste entries={observed!r}"
                )
            for info, relative in validated:
                target = root.joinpath(*relative.parts)
                resolved_target = target.resolve()
                if resolved_target != resolved_root and resolved_root not in resolved_target.parents:
                    raise RuntimeError(f"M18 runtime-pad ontsnapt extractieroot: {info.filename}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(info))
    except Exception:
        for candidate in sorted(root.rglob("*"), reverse=True):
            try:
                candidate.unlink() if candidate.is_file() else candidate.rmdir()
            except OSError:
                pass
        try:
            root.rmdir()
        except OSError:
            pass
        raise

    _RUNTIME_IMPORT_ROOT = root
    return root


def _install_internal_compatibility_aliases() -> None:
    global _COMPATIBILITY_ALIASES_INSTALLED
    if _COMPATIBILITY_ALIASES_INSTALLED:
        return
    module = importlib.import_module(f"{M18_RUNTIME_PACKAGE}.certification_ops")
    sys.modules.setdefault("cws_convertor.manufacturing.certification_ops", module)
    _COMPATIBILITY_ALIASES_INSTALLED = True


def _activate_runtime() -> None:
    install_m18_runtime_access()
    import_root = _prepare_runtime_import_root()
    import_root_text = str(import_root)
    if import_root_text not in sys.path:
        sys.path.insert(0, import_root_text)
    importlib.invalidate_caches()
    root = importlib.import_module(M18_RUNTIME_PACKAGE)
    if getattr(root, "M18_ORIGIN_COMMIT", "") != M18_ORIGIN_COMMIT:
        raise RuntimeError("M18 authority runtime heeft onverwachte source-commit identiteit")
    _install_internal_compatibility_aliases()


def load_authority_module(name: str):
    if name not in _ALLOWED_MODULES:
        raise KeyError(f"Module {name!r} is geen publieke U2 M9-M18 authority-module")
    _activate_runtime()
    return importlib.import_module(f"{M18_RUNTIME_PACKAGE}.{name}")


def authority_chain_status(project: ProjectModel) -> dict[str, Any]:
    _activate_runtime()
    stores = m18_store_snapshot(project)
    phases: dict[str, Any] = {}
    for phase, module_names in AUTHORITY_MODULES.items():
        loaded = []
        errors = []
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
            "store_counts": {
                key: (len(stores.get(key, {})) if isinstance(stores.get(key), dict) else stores.get(key))
                for key in phase_stores
            },
            "available": not errors,
        }

    return {
        "schema": "cws-unified-manufacturing-authority-1.0",
        "project_id": project.project_id,
        "project_schema": project.schema_version,
        "canonical_m1_m8": dict(CANONICAL_M1_M8),
        "m9_m18": phases,
        "m18_origin": {
            "version": M18_ORIGIN_VERSION,
            "commit": M18_ORIGIN_COMMIT,
            "tag": M18_ORIGIN_TAG,
            "runtime_sha256": M18_RUNTIME_SHA256,
        },
        "safety": {
            "machine_observed_by_cws": False,
            "deployment_transport_authorized": False,
            "direct_machine_transfer": False,
            "machine_transfer_allowed": False,
        },
        "all_authority_modules_available": all(item["available"] for item in phases.values()),
    }


__all__ = [
    "M18_RUNTIME_SHA256",
    "M18_ORIGIN_VERSION",
    "M18_ORIGIN_COMMIT",
    "M18_ORIGIN_TAG",
    "CANONICAL_M1_M8",
    "AUTHORITY_MODULES",
    "verify_m18_runtime_archive",
    "load_authority_module",
    "authority_chain_status",
]
