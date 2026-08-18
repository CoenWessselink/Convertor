"""Fail-closed facade for the frozen CWS Scribing M9-M18 authority.

The canonical runtime is SHA-256 bound. A historical Windows checkout treated
the binary ZIP as text and expanded LF bytes to CRLF. Recovery is permitted only
when the checked-out transport hash matches its known fingerprint and reversing
that conversion produces the exact canonical runtime hash. ZIP members are then
path, CRC and completeness checked before import. Project data remains solely in
canonical Project Model 2.25.
"""
from __future__ import annotations

import binascii
import hashlib
import importlib
from io import BytesIO
from pathlib import Path, PurePosixPath
import stat
import struct
import sys
import tempfile
from typing import Any
import zipfile
import zlib

from cws_convertor.project.model import ProjectModel
from cws_convertor.project.unified_schema import m18_store_snapshot
from .m18_runtime_access import install_m18_runtime_access

M18_RUNTIME_ARCHIVE = "m18_authority_runtime.zip"
# Canonical frozen ZIP bytes before the historic Windows line-ending expansion.
M18_RUNTIME_SHA256 = "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1"
# Exact expanded checkout bytes observed and pinned by Windows CI.
M18_WINDOWS_TRANSPORT_SHA256 = "30bcbb5bdd0aa6bac825a31dcbd5eb69586f051dc66c01e3485d4e8a56d7a745"
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
        "simulation_contracts", "simulation_engine", "simulation_validator",
        "simulation_service", "adapter_rehearsal",
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
        "manufacturing_adapter_evidence_cases", "manufacturing_adapter_certificates",
        "manufacturing_adapter_certificate_revocations",
    ),
    "M14": (
        "manufacturing_adapter_sdk_manifests", "manufacturing_adapter_certification_batches",
        "manufacturing_adapter_certificate_supersessions",
    ),
    "M15": (
        "manufacturing_adapter_lab_matrices", "manufacturing_adapter_lab_campaigns",
        "manufacturing_adapter_lab_impacts", "manufacturing_adapter_lab_diffs",
        "manufacturing_adapter_lab_candidates",
    ),
    "M16": (
        "manufacturing_fleet_sites", "manufacturing_fleet_machine_bindings",
        "manufacturing_fleet_policies", "manufacturing_fleet_trusted_signers",
        "manufacturing_fleet_external_approvals", "manufacturing_fleet_recertification_queues",
        "manufacturing_fleet_deployments",
    ),
    "M17": (
        "manufacturing_deployment_stations", "manufacturing_deployment_control_policies",
        "manufacturing_deployment_rollout_plans", "manufacturing_deployment_rollback_references",
        "manufacturing_deployment_release_requests", "manufacturing_deployment_operator_approvals",
        "manufacturing_deployment_airgap_exports", "manufacturing_deployment_import_receipts",
        "manufacturing_deployment_receipts", "manufacturing_deployment_acknowledgements",
        "manufacturing_deployment_withdrawals",
    ),
    "M18": (
        "manufacturing_media_devices", "manufacturing_media_custody_policies",
        "manufacturing_media_custody_sessions", "manufacturing_media_custody_events",
        "manufacturing_station_reconciliations", "manufacturing_rollback_drills",
        "manufacturing_deployment_closures",
    ),
}
_ALLOWED_MODULES = {name for values in AUTHORITY_MODULES.values() for name in values}
_REQUIRED_FILES = {
    f"{M18_RUNTIME_PACKAGE}/__init__.py",
    *(f"{M18_RUNTIME_PACKAGE}/{name}.py" for name in _ALLOWED_MODULES),
}
_LOCAL_FILE = 0x04034B50
_CENTRAL_FILE = 0x02014B50
_END_CENTRAL = 0x06054B50
_RUNTIME_ENTRIES: dict[str, bytes] | None = None
_RUNTIME_IMPORT_ROOT: Path | None = None
_COMPATIBILITY_ALIASES_INSTALLED = False
_RECOVERY_MODE = ""
_TRANSPORT_SHA256 = ""


def runtime_archive_path() -> Path:
    return Path(__file__).resolve().with_name(M18_RUNTIME_ARCHIVE)


def _safe_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Onveilig M18 runtime-pad: {name!r}")
    if not path.parts or path.parts[0] != M18_RUNTIME_PACKAGE:
        raise RuntimeError(f"M18 entry buiten authority package: {name}")
    return path


def _canonical_runtime_bytes(raw: bytes) -> tuple[bytes, str, str]:
    transport_sha = hashlib.sha256(raw).hexdigest()
    if transport_sha == M18_RUNTIME_SHA256:
        return raw, "canonical-binary", transport_sha
    if transport_sha != M18_WINDOWS_TRANSPORT_SHA256:
        raise RuntimeError(
            "Frozen M18 transport SHA-256 wijkt af; "
            f"canonical={M18_RUNTIME_SHA256} windows={M18_WINDOWS_TRANSPORT_SHA256} "
            f"actual={transport_sha}"
        )
    canonical = raw.replace(b"\r\n", b"\n")
    canonical_sha = hashlib.sha256(canonical).hexdigest()
    if canonical_sha != M18_RUNTIME_SHA256:
        raise RuntimeError(
            "Windows M18 CRLF-recovery levert niet de canonical frozen runtime; "
            f"expected={M18_RUNTIME_SHA256} actual={canonical_sha}"
        )
    return canonical, "windows-crlf-recovered", transport_sha


def _normal_entries(raw: bytes) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    with zipfile.ZipFile(BytesIO(raw), "r") as source:
        bad = source.testzip()
        if bad is not None:
            raise RuntimeError(f"M18 CRC-fout in {bad}")
        for info in source.infolist():
            name = str(info.filename or "")
            _safe_path(name)
            mode = (int(info.external_attr) >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise RuntimeError(f"Verboden symlink in M18 runtime: {name}")
            if not info.is_dir():
                result[name] = source.read(info)
    return result


def _local_entries(raw: bytes) -> dict[str, bytes]:
    """CRC-checked fallback if only the canonical local ZIP records survive."""
    result: dict[str, bytes] = {}
    header = struct.Struct("<IHHHHHIIIHH")
    offset = 0
    while offset + 4 <= len(raw):
        signature = struct.unpack_from("<I", raw, offset)[0]
        if signature in {_CENTRAL_FILE, _END_CENTRAL}:
            break
        if signature != _LOCAL_FILE:
            if not raw[offset:] or all(byte == 0 for byte in raw[offset:]):
                break
            raise RuntimeError(
                f"Ongeldige M18 ZIP-signature op byte {offset}: 0x{signature:08x}"
            )
        if offset + header.size > len(raw):
            raise RuntimeError("Afgekapt lokaal M18 ZIP-header")
        (
            _sig, _version, flags, method, _mtime, _mdate, crc32,
            compressed_size, uncompressed_size, name_length, extra_length,
        ) = header.unpack_from(raw, offset)
        if flags & 0x0001:
            raise RuntimeError("Versleutelde M18 ZIP-entry is verboden")
        if flags & 0x0008:
            raise RuntimeError("M18 recovery weigert losse data descriptors")
        name_start = offset + header.size
        name_end = name_start + name_length
        data_start = name_end + extra_length
        data_end = data_start + compressed_size
        if data_end > len(raw):
            raise RuntimeError("Afgekapt M18 ZIP-payload")
        encoding = "utf-8" if flags & 0x0800 else "cp437"
        name = raw[name_start:name_end].decode(encoding)
        _safe_path(name)
        compressed = raw[data_start:data_end]
        if method == 0:
            payload = compressed
        elif method == 8:
            payload = zlib.decompress(compressed, -15)
        else:
            raise RuntimeError(f"Niet-ondersteunde M18 ZIP-compressie {method}: {name}")
        if len(payload) != uncompressed_size:
            raise RuntimeError(f"M18 entrygrootte wijkt af: {name}")
        if (binascii.crc32(payload) & 0xFFFFFFFF) != crc32:
            raise RuntimeError(f"M18 entry-CRC wijkt af: {name}")
        if not name.endswith("/"):
            result[name] = payload
        offset = data_end
    return result


def _verified_entries() -> dict[str, bytes]:
    global _RUNTIME_ENTRIES, _RECOVERY_MODE, _TRANSPORT_SHA256
    if _RUNTIME_ENTRIES is not None:
        return _RUNTIME_ENTRIES
    archive = runtime_archive_path()
    if not archive.is_file():
        raise RuntimeError(f"Frozen M18 authority runtime ontbreekt: {archive}")
    canonical, transport_mode, transport_sha = _canonical_runtime_bytes(archive.read_bytes())
    try:
        entries = _normal_entries(canonical)
        zip_mode = "central-directory"
    except (zipfile.BadZipFile, RuntimeError):
        entries = _local_entries(canonical)
        zip_mode = "validated-local-record-recovery"
    missing = sorted(_REQUIRED_FILES - set(entries))
    if missing:
        raise RuntimeError(f"Frozen M18 runtime mist verplichte modules: {missing}")
    init_text = entries[f"{M18_RUNTIME_PACKAGE}/__init__.py"].decode("utf-8")
    if M18_ORIGIN_COMMIT not in init_text:
        raise RuntimeError("M18 runtime mist frozen source-commit identiteit")
    _RECOVERY_MODE = f"{transport_mode}+{zip_mode}"
    _TRANSPORT_SHA256 = transport_sha
    _RUNTIME_ENTRIES = entries
    return entries


def verify_m18_runtime_archive() -> str:
    _verified_entries()
    return M18_RUNTIME_SHA256


def _prepare_runtime_import_root() -> Path:
    global _RUNTIME_IMPORT_ROOT
    if _RUNTIME_IMPORT_ROOT is not None:
        return _RUNTIME_IMPORT_ROOT
    root = Path(tempfile.mkdtemp(prefix=f"cws-m18-{M18_RUNTIME_SHA256[:12]}-"))
    resolved_root = root.resolve()
    try:
        for name, payload in _verified_entries().items():
            relative = _safe_path(name)
            target = root.joinpath(*relative.parts)
            resolved_target = target.resolve()
            if resolved_target != resolved_root and resolved_root not in resolved_target.parents:
                raise RuntimeError(f"M18 path ontsnapt extractieroot: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
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


def _activate_runtime() -> None:
    global _COMPATIBILITY_ALIASES_INSTALLED
    install_m18_runtime_access()
    root = _prepare_runtime_import_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    importlib.invalidate_caches()
    package = importlib.import_module(M18_RUNTIME_PACKAGE)
    if getattr(package, "M18_ORIGIN_COMMIT", "") != M18_ORIGIN_COMMIT:
        raise RuntimeError("M18 authority heeft onverwachte source-commit identiteit")
    if not _COMPATIBILITY_ALIASES_INSTALLED:
        module = importlib.import_module(f"{M18_RUNTIME_PACKAGE}.certification_ops")
        sys.modules.setdefault("cws_convertor.manufacturing.certification_ops", module)
        _COMPATIBILITY_ALIASES_INSTALLED = True


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
        loaded: list[str] = []
        errors: list[str] = []
        for module_name in module_names:
            try:
                load_authority_module(module_name)
                loaded.append(module_name)
            except Exception as exc:
                errors.append(f"{module_name}: {type(exc).__name__}: {exc}")
        phases[phase] = {
            "modules": list(module_names),
            "loaded_modules": loaded,
            "errors": errors,
            "store_counts": {
                key: len(stores.get(key, {})) if isinstance(stores.get(key), dict) else stores.get(key)
                for key in STORE_BY_PHASE.get(phase, ())
            },
            "available": not errors,
        }
    return {
        "schema": "cws-unified-manufacturing-authority-1.2",
        "project_id": project.project_id,
        "project_schema": project.schema_version,
        "canonical_m1_m8": dict(CANONICAL_M1_M8),
        "m9_m18": phases,
        "m18_origin": {
            "version": M18_ORIGIN_VERSION,
            "commit": M18_ORIGIN_COMMIT,
            "tag": M18_ORIGIN_TAG,
            "transport_sha256": _TRANSPORT_SHA256,
            "runtime_sha256": M18_RUNTIME_SHA256,
            "recovery_mode": _RECOVERY_MODE,
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
    "M18_RUNTIME_SHA256", "M18_WINDOWS_TRANSPORT_SHA256", "M18_ORIGIN_VERSION",
    "M18_ORIGIN_COMMIT", "M18_ORIGIN_TAG", "CANONICAL_M1_M8",
    "AUTHORITY_MODULES", "verify_m18_runtime_archive", "load_authority_module",
    "authority_chain_status",
]
