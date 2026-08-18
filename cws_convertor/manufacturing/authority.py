"""Unified fail-closed facade for frozen Scribing M9-M18 authorities.

M1-M8 remain the current CWS implementation. M9-M18 are materialised only from
checksum-exact Base64 transport files, decoded in memory, validated as a safe ZIP
and imported from a process-local temporary directory. This avoids Windows Git
line-ending damage to binary ZIP blobs while retaining one Project Model 2.25
truth and the hard-closed machine-transfer boundary.
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
M18_RUNTIME_PAYLOAD_STEM = "m18_authority_runtime.b64"
M18_RUNTIME_PAYLOAD_COUNT = 7
M18_RUNTIME_SHA256 = "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1"
M18_ORIGIN_VERSION = "0.8.30-beta-dev"
M18_ORIGIN_COMMIT = "b04b1c203583295e8c5ed018d75de68b2319c839"
M18_ORIGIN_TAG = "scribing-m18-deployment-assurance-0.8.30-beta-dev"
M18_RUNTIME_PACKAGE = "cws_m18_authority"
_BASE64_DATA_BYTES = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
_BASE64_BYTES = frozenset((*_BASE64_DATA_BYTES, ord("=")))

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
_RUNTIME_BYTES: bytes | None = None
_RUNTIME_ARCHIVE_PATH: Path | None = None
_RUNTIME_IMPORT_ROOT: Path | None = None
_PAYLOAD_SHA256: str | None = None
_DECODE_STRATEGY: str | None = None
_COMPATIBILITY_ALIASES_INSTALLED = False


def runtime_payload_dir() -> Path:
    return Path(__file__).resolve().with_name(M18_RUNTIME_PAYLOAD_DIR)


def _expected_payload_names() -> tuple[str, ...]:
    return tuple(
        f"{M18_RUNTIME_PAYLOAD_STEM}.{index:03d}"
        for index in range(1, M18_RUNTIME_PAYLOAD_COUNT + 1)
    )


def _payload_files() -> tuple[Path, ...]:
    directory = runtime_payload_dir()
    if not directory.is_dir():
        raise RuntimeError(f"Frozen M18 payload-directory ontbreekt: {directory}")
    files = tuple(sorted(directory.glob(f"{M18_RUNTIME_PAYLOAD_STEM}.*")))
    names = tuple(path.name for path in files)
    expected = _expected_payload_names()
    if names != expected:
        missing = tuple(name for name in expected if name not in names)
        unexpected = tuple(name for name in names if name not in expected)
        raise RuntimeError(
            "Frozen M18 payload chunkset klopt niet; "
            f"missing={missing!r} unexpected={unexpected!r}"
        )
    return files


def _validate_runtime_member(info: zipfile.ZipInfo) -> PurePosixPath:
    name = str(info.filename or "")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Onveilig M18 runtime-pad: {name!r}")
    if not path.parts or path.parts[0] != M18_RUNTIME_PACKAGE:
        raise RuntimeError(
            "M18 runtime bevat entry buiten het geïsoleerde pakket: " + name
        )
    unix_mode = (int(info.external_attr) >> 16) & 0o170000
    if unix_mode == stat.S_IFLNK:
        raise RuntimeError(f"M18 runtime bevat verboden symlink-entry: {name}")
    return path


def _pad_base64(value: bytes) -> bytes:
    return value + b"=" * ((-len(value)) % 4)


def _decode_runtime_candidates(chunks: tuple[bytes, ...]) -> tuple[bytes, str]:
    joined = b"".join(chunks)
    candidates: list[tuple[str, bytes]] = []

    clean_joined = bytes(value for value in joined if value in _BASE64_BYTES)
    try:
        candidates.append(
            ("continuous", base64.b64decode(clean_joined, validate=True))
        )
    except Exception:
        pass

    data_only = bytes(value for value in joined if value in _BASE64_DATA_BYTES)
    try:
        candidates.append(
            (
                "continuous-repadded",
                base64.b64decode(_pad_base64(data_only), validate=True),
            )
        )
    except Exception:
        pass

    segments: list[bytes] = []
    for encoded in chunks:
        segment = bytes(value for value in encoded if value in _BASE64_DATA_BYTES)
        if not segment:
            segments = []
            break
        try:
            segments.append(base64.b64decode(_pad_base64(segment), validate=True))
        except Exception:
            segments = []
            break
    if segments:
        candidates.append(("segmented-repadded", b"".join(segments)))

    observed: list[str] = []
    for strategy, runtime in candidates:
        digest = hashlib.sha256(runtime).hexdigest()
        observed.append(f"{strategy}:{digest}")
        if digest == M18_RUNTIME_SHA256:
            return runtime, strategy
    raise RuntimeError(
        "Frozen M18 transport kon niet checksum-exact worden gereconstrueerd; "
        f"expected={M18_RUNTIME_SHA256} observed={observed!r}"
    )


def _verified_runtime_bytes() -> bytes:
    global _RUNTIME_BYTES, _PAYLOAD_SHA256, _DECODE_STRATEGY
    if _RUNTIME_BYTES is not None:
        return _RUNTIME_BYTES

    chunks: list[bytes] = []
    for path in _payload_files():
        try:
            chunks.append(b"".join(path.read_bytes().split()))
        except OSError as exc:
            raise RuntimeError(f"Frozen M18 payload chunk onleesbaar: {path}") from exc
    normalized = tuple(chunks)
    payload = b"".join(normalized)
    _PAYLOAD_SHA256 = hashlib.sha256(payload).hexdigest()

    runtime, strategy = _decode_runtime_candidates(normalized)
    if hashlib.sha256(runtime).hexdigest() != M18_RUNTIME_SHA256:
        raise RuntimeError("Frozen M18 decoded runtime SHA-256 wijkt af")

    try:
        with zipfile.ZipFile(BytesIO(runtime), "r") as source:
            bad_member = source.testzip()
            if bad_member is not None:
                raise RuntimeError(f"Frozen M18 runtime CRC-fout in {bad_member}")
            infos = source.infolist()
            if not infos:
                raise RuntimeError("Frozen M18 authority runtime is leeg")
            validated = tuple(_validate_runtime_member(info) for info in infos)
            expected_init = PurePosixPath(M18_RUNTIME_PACKAGE) / "__init__.py"
            if expected_init not in validated:
                raise RuntimeError(f"M18 runtime mist {expected_init}")
    except zipfile.BadZipFile as exc:
        raise RuntimeError("Frozen M18 decoded runtime is geen geldig ZIP-bestand") from exc

    _DECODE_STRATEGY = strategy
    _RUNTIME_BYTES = runtime
    return runtime


def runtime_archive_path() -> Path:
    global _RUNTIME_ARCHIVE_PATH
    if _RUNTIME_ARCHIVE_PATH is not None:
        return _RUNTIME_ARCHIVE_PATH
    runtime = _verified_runtime_bytes()
    root = Path(
        tempfile.mkdtemp(prefix=f"cws-m18-archive-{M18_RUNTIME_SHA256[:12]}-")
    )
    path = root / M18_RUNTIME_ARCHIVE
    path.write_bytes(runtime)
    _RUNTIME_ARCHIVE_PATH = path
    return path


def verify_m18_runtime_archive() -> str:
    _verified_runtime_bytes()
    return M18_RUNTIME_SHA256


def _prepare_runtime_import_root() -> Path:
    global _RUNTIME_IMPORT_ROOT
    if _RUNTIME_IMPORT_ROOT is not None:
        return _RUNTIME_IMPORT_ROOT

    runtime = _verified_runtime_bytes()
    root = Path(tempfile.mkdtemp(prefix=f"cws-m18-{M18_RUNTIME_SHA256[:12]}-"))
    resolved_root = root.resolve()
    try:
        with zipfile.ZipFile(BytesIO(runtime), "r") as source:
            for info in source.infolist():
                relative = _validate_runtime_member(info)
                target = root.joinpath(*relative.parts)
                resolved_target = target.resolve()
                if (
                    resolved_target != resolved_root
                    and resolved_root not in resolved_target.parents
                ):
                    raise RuntimeError(
                        f"M18 runtime-pad ontsnapt extractieroot: {info.filename}"
                    )
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
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
        raise RuntimeError(
            "M18 authority runtime heeft onverwachte source-commit identiteit"
        )
    _install_internal_compatibility_aliases()


def load_authority_module(name: str):
    if name not in _ALLOWED_MODULES:
        raise KeyError(
            f"Module {name!r} is geen publieke U2 M9-M18 authority-module"
        )
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
        phase_stores = STORE_BY_PHASE.get(phase, ())
        phases[phase] = {
            "modules": list(module_names),
            "loaded_modules": loaded,
            "errors": errors,
            "store_counts": {
                key: (
                    len(stores.get(key, {}))
                    if isinstance(stores.get(key), dict)
                    else stores.get(key)
                )
                for key in phase_stores
            },
            "available": not errors,
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
            "payload_sha256": _PAYLOAD_SHA256 or "",
            "runtime_sha256": M18_RUNTIME_SHA256,
            "decode_strategy": _DECODE_STRATEGY or "",
        },
        "safety": {
            "machine_observed_by_cws": False,
            "deployment_transport_authorized": False,
            "direct_machine_transfer": False,
            "machine_transfer_allowed": False,
        },
        "all_authority_modules_available": all(
            item["available"] for item in phases.values()
        ),
    }


__all__ = [
    "M18_RUNTIME_SHA256",
    "M18_ORIGIN_VERSION",
    "M18_ORIGIN_COMMIT",
    "M18_ORIGIN_TAG",
    "CANONICAL_M1_M8",
    "AUTHORITY_MODULES",
    "runtime_archive_path",
    "verify_m18_runtime_archive",
    "load_authority_module",
    "authority_chain_status",
]
