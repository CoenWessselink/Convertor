"""Unified U2 facade for Scribing M9-M18 authorities.

Canonical M1-M8 geometry/marking/nesting/neutral-job code remains the newer
Viewer V15 implementation in :mod:`cws_convertor.manufacturing`.  The frozen
M18 authority implementation is kept in a checksum-bound runtime archive and is
loaded only for M9-M18 evidence/release/governance operations.  It reads and
writes the *same* Project Model 2.25 stores through ``m18_runtime_access``.
"""
from __future__ import annotations

import hashlib
import importlib
from pathlib import Path
import sys
from typing import Any

from cws_convertor.project.model import ProjectModel
from cws_convertor.project.unified_schema import m18_store_snapshot
from .m18_runtime_access import install_m18_runtime_access

M18_RUNTIME_ARCHIVE = "m18_authority_runtime.zip"
M18_RUNTIME_SHA256 = "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1"
M18_ORIGIN_VERSION = "0.8.30-beta-dev"
M18_ORIGIN_COMMIT = "b04b1c203583295e8c5ed018d75de68b2319c839"
M18_ORIGIN_TAG = "scribing-m18-deployment-assurance-0.8.30-beta-dev"

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
_ARCHIVE_VERIFIED = False
_COMPATIBILITY_ALIASES_INSTALLED = False


def runtime_archive_path() -> Path:
    return Path(__file__).resolve().with_name(M18_RUNTIME_ARCHIVE)


def verify_m18_runtime_archive() -> str:
    global _ARCHIVE_VERIFIED
    archive = runtime_archive_path()
    if not archive.is_file():
        raise RuntimeError(f"Frozen M18 authority runtime ontbreekt: {archive}")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != M18_RUNTIME_SHA256:
        raise RuntimeError(
            "Frozen M18 authority runtime SHA-256 wijkt af; "
            f"expected={M18_RUNTIME_SHA256} actual={digest}"
        )
    _ARCHIVE_VERIFIED = True
    return digest


def _install_internal_compatibility_aliases() -> None:
    """Keep one frozen M18 internal absolute import inside the isolated runtime.

    Frozen M18 ``adapter_certification`` contains a lazy absolute import of
    ``cws_convertor.manufacturing.certification_ops``.  Point that exact legacy
    name at the checksum-verified M18 module rather than creating/copying a
    second current implementation.  This alias exists only for M18's own
    certification call path; the normal public U2 API remains this facade.
    """
    global _COMPATIBILITY_ALIASES_INSTALLED
    if _COMPATIBILITY_ALIASES_INSTALLED:
        return
    module = importlib.import_module("cws_m18_authority.certification_ops")
    sys.modules.setdefault("cws_convertor.manufacturing.certification_ops", module)
    _COMPATIBILITY_ALIASES_INSTALLED = True


def _activate_runtime() -> None:
    install_m18_runtime_access()
    archive = runtime_archive_path()
    if not _ARCHIVE_VERIFIED:
        verify_m18_runtime_archive()
    archive_text = str(archive)
    if archive_text not in sys.path:
        sys.path.insert(0, archive_text)
    root = importlib.import_module("cws_m18_authority")
    if getattr(root, "M18_ORIGIN_COMMIT", "") != M18_ORIGIN_COMMIT:
        raise RuntimeError("M18 authority runtime heeft onverwachte source-commit identiteit")
    _install_internal_compatibility_aliases()


def load_authority_module(name: str):
    """Load one frozen M9-M18 module after checksum and ProjectModel bridge validation."""
    if name not in _ALLOWED_MODULES:
        raise KeyError(f"Module {name!r} is geen publieke U2 M9-M18 authority-module")
    _activate_runtime()
    return importlib.import_module(f"cws_m18_authority.{name}")


def authority_chain_status(project: ProjectModel) -> dict[str, Any]:
    """Return a deterministic M1-M18 integration/status snapshot."""
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
