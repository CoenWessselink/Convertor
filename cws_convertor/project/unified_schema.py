"""Unified Project Model 2.25 compatibility bridge.

U1 deliberately does not copy the Scribing M18 implementation over the newer
Viewer/Convertor tree.  Instead it creates one lossless persistence boundary:

* the active GitHub Project Model 2.5 line migrates to 2.25;
* every historical M18 2.x schema through frozen 2.24 migrates to 2.25;
* M18 authority stores are preserved byte-for-JSON-semantics in an internal
  extension envelope until U2 promotes the winning contracts into the native
  ProjectModel fields/services;
* serialized 2.25 snapshots expose the original M18 store names again, so the
  handover remains inspectable and no authority data disappears;
* part geometry/manufacturing hashes are not changed by the 2.5/2.6-2.24
  migration itself.

The bridge is installed from :mod:`cws_convertor.project.__init__` immediately
after ``model`` is imported and before storage/service modules are imported.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from . import model as _model


UNIFIED_PROJECT_SCHEMA_VERSION = "2.25"
EXTENSION_KEY = "_cws_unified_schema_2_25"
PART_EXTENSION_KEY = "_cws_unified_schema_2_25"

# ProjectModel fields that exist in the frozen M18 2.24 authority model but not
# yet in the active GitHub 2.5 dataclass.  U2 will reconcile these contracts
# one by one.  U1's job is lossless persistence, not a duplicate implementation.
M18_PROJECT_STORE_DEFAULTS: dict[str, Any] = {
    "profile_nesting_runs": {},
    "profile_nesting_settings": {},
    "profile_nesting_machine_profiles": {},
    "profile_nesting_tool_library": {},
    "profile_nesting_formula_library": {},
    "profile_nesting_purchase_options": {},
    "profile_nesting_reservations": {},
    "profile_nesting_reservation_revision": 0,
    "manufacturing_contact_patches": {},
    "manufacturing_contact_states": {},
    "manufacturing_rulesets": {},
    "manufacturing_marks": {},
    "manufacturing_mark_states": {},
    "manufacturing_marking_tools": {},
    "manufacturing_machine_capabilities": {},
    "manufacturing_machine_mark_evaluations": {},
    "manufacturing_nesting_mark_bindings": {},
    "manufacturing_sequences": {},
    "manufacturing_export_scopes": {},
    "manufacturing_dstv_roundtrips": {},
    "manufacturing_release_records": {},
    "manufacturing_simulations": {},
    "manufacturing_adapter_rehearsals": {},
    "manufacturing_adapter_evidence_cases": {},
    "manufacturing_adapter_certificates": {},
    "manufacturing_adapter_certificate_revocations": {},
    "manufacturing_adapter_sdk_manifests": {},
    "manufacturing_adapter_certification_batches": {},
    "manufacturing_adapter_certificate_supersessions": {},
    "manufacturing_adapter_lab_matrices": {},
    "manufacturing_adapter_lab_campaigns": {},
    "manufacturing_adapter_lab_impacts": {},
    "manufacturing_adapter_lab_diffs": {},
    "manufacturing_adapter_lab_candidates": {},
    "manufacturing_fleet_sites": {},
    "manufacturing_fleet_machine_bindings": {},
    "manufacturing_fleet_policies": {},
    "manufacturing_fleet_trusted_signers": {},
    "manufacturing_fleet_external_approvals": {},
    "manufacturing_fleet_recertification_queues": {},
    "manufacturing_fleet_deployments": {},
    "manufacturing_deployment_stations": {},
    "manufacturing_deployment_control_policies": {},
    "manufacturing_deployment_rollout_plans": {},
    "manufacturing_deployment_rollback_references": {},
    "manufacturing_deployment_release_requests": {},
    "manufacturing_deployment_operator_approvals": {},
    "manufacturing_deployment_airgap_exports": {},
    "manufacturing_deployment_import_receipts": {},
    "manufacturing_deployment_receipts": {},
    "manufacturing_deployment_acknowledgements": {},
    "manufacturing_deployment_withdrawals": {},
    "manufacturing_media_devices": {},
    "manufacturing_media_custody_policies": {},
    "manufacturing_media_custody_sessions": {},
    "manufacturing_media_custody_events": {},
    "manufacturing_station_reconciliations": {},
    "manufacturing_rollback_drills": {},
    "manufacturing_deployment_closures": {},
}

M18_PART_FIELD_DEFAULTS: dict[str, Any] = {
    "manufacturing_faces": [],
    "manufacturing_faces_state": {},
}

# Explicitly accepted historical 2.x sources.  2.5 is the current GitHub
# authority.  2.6..2.24 are successive Scribing/Profile-Nesting development
# schemas ending at the frozen M18 authority.  Future 2.26+ remains rejected.
KNOWN_2X_SOURCE_SCHEMAS = frozenset(
    [f"2.{minor}" for minor in range(0, 25)]
)

_ORIGINAL_MIGRATE = _model.migrate_project_dict
_ORIGINAL_TO_DICT = _model.ProjectModel.to_dict
_INSTALLED = False


def _version_tuple(value: str) -> tuple[int, ...]:
    text = str(value or "").strip()
    parts = text.split(".") if text else []
    if not parts or any(not part.isdigit() for part in parts):
        return ()
    return tuple(int(part) for part in parts)


def _extension(settings: dict[str, Any]) -> dict[str, Any]:
    value = settings.get(EXTENSION_KEY)
    if not isinstance(value, dict):
        value = {}
        settings[EXTENSION_KEY] = value
    return value


def _part_extension(properties: dict[str, Any]) -> dict[str, Any]:
    value = properties.get(PART_EXTENSION_KEY)
    if not isinstance(value, dict):
        value = {}
        properties[PART_EXTENSION_KEY] = value
    return value


def _upgrade_pre_25_workbench(raw: dict[str, Any], source_version: str) -> None:
    """Preserve the proven 2.0-2.4 -> 2.5 Workbench migration contract.

    Those early schemas predate Workbench 1.1 hash binding.  Their old external
    roundtrip evidence must remain invalidated exactly as before; newer 2.5 and
    M18 schemas are not touched by this helper.
    """

    if source_version not in {"2.0", "2.1", "2.2", "2.3", "2.4"}:
        return
    migration_timestamp = _model.utc_now_iso()
    for part in dict(raw.get("parts") or {}).values():
        if not isinstance(part, dict):
            continue
        part.setdefault("workbench", {})
        state = part.get("workbench")
        if not isinstance(state, dict) or not state:
            continue
        state["schema_version"] = "1.1"

        def invalidate_revision(revision: Any) -> None:
            if not isinstance(revision, dict):
                return
            roundtrip = revision.get("roundtrip_validation")
            if not isinstance(roundtrip, dict):
                return
            if roundtrip.get("status") in {None, "", "not_run", "invalidated"}:
                return
            roundtrip["status"] = "invalidated"
            roundtrip["invalidated_at"] = migration_timestamp
            roundtrip["invalidated_reason"] = "workbench_hash_contract_upgraded"
            for result in dict(roundtrip.get("formats") or {}).values():
                if isinstance(result, dict):
                    result["status"] = "invalidated"
            roundtrip.pop("report_sha256", None)
            roundtrip["report_sha256"] = _model.stable_sha256(roundtrip)

        invalidate_revision(state.get("current_revision"))
        for command in list(state.get("commands") or []):
            if not isinstance(command, dict):
                continue
            invalidate_revision(command.get("before_revision"))
            invalidate_revision(command.get("after_revision"))
            command["before_sha256"] = _model.stable_sha256(
                dict(command.get("before_revision") or {})
            )
            command["after_sha256"] = _model.stable_sha256(
                dict(command.get("after_revision") or {})
            )
        for record in list(state.get("revision_history") or []):
            if not isinstance(record, dict):
                continue
            invalidate_revision(record.get("snapshot"))
            record["snapshot_sha256"] = _model.stable_sha256(
                dict(record.get("snapshot") or {})
            )
        for artifact in dict(state.get("artifacts") or {}).values():
            if isinstance(artifact, dict):
                artifact["status"] = "invalidated"
                artifact["invalidated_at"] = migration_timestamp
                artifact["invalidated_reason"] = "workbench_hash_contract_upgraded"
        rebuild = state.get("canonical_rebuild")
        if isinstance(rebuild, dict) and rebuild:
            rebuild["status"] = "invalidated"
            rebuild["invalidated_at"] = migration_timestamp
            rebuild["invalidated_reason"] = "workbench_hash_contract_upgraded"
        part["geometry_hash"] = ""
        part["manufacturing_hash"] = ""
        part["production_identity_hash"] = ""
        part["bom_group_key"] = ""
        part["nc1_eligible"] = False
        part["export_status"] = "blocked_pending_roundtrip_validation"


def _capture_m18_extensions(raw: dict[str, Any], *, source_schema: str) -> None:
    settings = raw.get("settings")
    if not isinstance(settings, dict):
        settings = {}
        raw["settings"] = settings
    unified = _extension(settings)
    # Source provenance is immutable once a legacy/M18 snapshot has crossed the
    # 2.25 bridge. Re-opening an already migrated 2.25 package must not rewrite
    # its original 2.5/2.24 origin to 2.25, otherwise its semantic package hash
    # would drift without a user or manufacturing change.
    unified.setdefault("source_schema", str(source_schema or ""))
    unified["bridge_schema"] = UNIFIED_PROJECT_SCHEMA_VERSION
    stores = unified.get("m18_project_stores")
    if not isinstance(stores, dict):
        stores = {}
        unified["m18_project_stores"] = stores

    for key, default in M18_PROJECT_STORE_DEFAULTS.items():
        if key in raw:
            stores[key] = deepcopy(raw.pop(key))
        elif key not in stores:
            stores[key] = deepcopy(default)

    for part in dict(raw.get("parts") or {}).values():
        if not isinstance(part, dict):
            continue
        properties = part.get("properties")
        if not isinstance(properties, dict):
            properties = {}
            part["properties"] = properties
        unified_part = _part_extension(properties)
        m18_part = unified_part.get("m18_manufacturing")
        if not isinstance(m18_part, dict):
            m18_part = {}
            unified_part["m18_manufacturing"] = m18_part
        for key, default in M18_PART_FIELD_DEFAULTS.items():
            if key in part:
                m18_part[key] = deepcopy(part.pop(key))
            elif key not in m18_part:
                m18_part[key] = deepcopy(default)


def _append_history(raw: dict[str, Any], source_version: str) -> None:
    history = list(raw.get("migration_history") or [])
    if any(
        str(item.get("from") or "") == source_version
        and str(item.get("to") or "") == UNIFIED_PROJECT_SCHEMA_VERSION
        for item in history
        if isinstance(item, Mapping)
    ):
        raw["migration_history"] = history
        return
    history.append(
        {
            "from": source_version,
            "to": UNIFIED_PROJECT_SCHEMA_VERSION,
            "timestamp": _model.utc_now_iso(),
            "reason": (
                "Unified U1 migration: Viewer/Convertor Project Model 2.5 and "
                "Scribing M18 Project Model 2.24 converge losslessly; M18 authority "
                "stores are retained for semantic promotion during U2 without "
                "changing current part manufacturing hashes."
            ),
        }
    )
    raw["migration_history"] = history


def migrate_project_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate known project snapshots to the unified 2.25 persistence shape."""

    if not isinstance(data, dict):
        return data
    raw = deepcopy(data)
    source_version = str(raw.get("schema_version") or "")

    # Historical 1.x canonical-project fixtures keep the existing migration
    # implementation.  Because ProjectModel now defaults to 2.25, that legacy
    # builder naturally emits the unified schema.
    if (not source_version and "canonical_parts" in raw) or source_version.startswith("1."):
        legacy = _ORIGINAL_MIGRATE(raw)
        if str(legacy.get("schema_version") or "") == UNIFIED_PROJECT_SCHEMA_VERSION:
            _capture_m18_extensions(legacy, source_schema=source_version or "1.0")
        return legacy

    parsed = _version_tuple(source_version)
    current = _version_tuple(UNIFIED_PROJECT_SCHEMA_VERSION)
    if parsed and current and parsed > current:
        # Fail closed: ProjectModel.from_dict will reject the future schema.
        return raw

    if source_version == UNIFIED_PROJECT_SCHEMA_VERSION:
        _capture_m18_extensions(raw, source_schema=source_version)
        return raw

    if source_version not in KNOWN_2X_SOURCE_SCHEMAS:
        return raw

    _upgrade_pre_25_workbench(raw, source_version)
    _capture_m18_extensions(raw, source_schema=source_version)
    raw["schema_version"] = UNIFIED_PROJECT_SCHEMA_VERSION
    _append_history(raw, source_version)
    return raw


def _clean_empty_extension_container(container: dict[str, Any], key: str) -> None:
    value = container.get(key)
    if isinstance(value, dict) and not value:
        container.pop(key, None)


def project_to_dict(project: _model.ProjectModel) -> dict[str, Any]:
    """Serialize 2.25 with native-looking M18 store keys and no duplicate copy.

    Runtime compatibility stores live inside ``settings``/part ``properties`` so
    the current 2.5 dataclasses need no duplicate authority implementation.
    The serialized project restores the original M18 names, keeping the package
    easy to audit and making U2 promotion deterministic.
    """

    data = _ORIGINAL_TO_DICT(project)
    data["schema_version"] = UNIFIED_PROJECT_SCHEMA_VERSION

    settings = data.get("settings")
    if not isinstance(settings, dict):
        settings = {}
        data["settings"] = settings
    unified = settings.get(EXTENSION_KEY)
    stores: dict[str, Any] = {}
    if isinstance(unified, dict):
        candidate = unified.get("m18_project_stores")
        if isinstance(candidate, dict):
            stores = candidate
    for key, default in M18_PROJECT_STORE_DEFAULTS.items():
        data[key] = deepcopy(stores.get(key, default))

    # Do not hash/serialize the compatibility copy twice.
    if isinstance(unified, dict):
        unified = deepcopy(unified)
        unified.pop("m18_project_stores", None)
        if unified:
            settings[EXTENSION_KEY] = unified
        else:
            settings.pop(EXTENSION_KEY, None)
    _clean_empty_extension_container(settings, EXTENSION_KEY)

    for part in dict(data.get("parts") or {}).values():
        if not isinstance(part, dict):
            continue
        properties = part.get("properties")
        if not isinstance(properties, dict):
            properties = {}
            part["properties"] = properties
        unified_part = properties.get(PART_EXTENSION_KEY)
        m18_part: dict[str, Any] = {}
        if isinstance(unified_part, dict):
            candidate = unified_part.get("m18_manufacturing")
            if isinstance(candidate, dict):
                m18_part = candidate
        for key, default in M18_PART_FIELD_DEFAULTS.items():
            part[key] = deepcopy(m18_part.get(key, default))
        if isinstance(unified_part, dict):
            unified_part = deepcopy(unified_part)
            unified_part.pop("m18_manufacturing", None)
            if unified_part:
                properties[PART_EXTENSION_KEY] = unified_part
            else:
                properties.pop(PART_EXTENSION_KEY, None)
        _clean_empty_extension_container(properties, PART_EXTENSION_KEY)
    return data


def m18_store_snapshot(project: _model.ProjectModel) -> dict[str, Any]:
    """Return a detached M18 authority-store snapshot for U2 reconciliation."""

    settings = project.settings if isinstance(project.settings, dict) else {}
    unified = settings.get(EXTENSION_KEY)
    stores = unified.get("m18_project_stores") if isinstance(unified, dict) else None
    return deepcopy(stores) if isinstance(stores, dict) else {
        key: deepcopy(default) for key, default in M18_PROJECT_STORE_DEFAULTS.items()
    }


def install_unified_project_schema() -> None:
    """Install the 2.25 migration/serialization bridge exactly once."""

    global _INSTALLED
    if _INSTALLED:
        return
    if str(_model.PROJECT_SCHEMA_VERSION) != UNIFIED_PROJECT_SCHEMA_VERSION:
        raise RuntimeError(
            "Unified project bridge requires PROJECT_SCHEMA_VERSION=2.25; found "
            f"{_model.PROJECT_SCHEMA_VERSION!r}"
        )
    _model.migrate_project_dict = migrate_project_dict
    _model.ProjectModel.to_dict = project_to_dict
    _INSTALLED = True


__all__ = [
    "UNIFIED_PROJECT_SCHEMA_VERSION",
    "M18_PROJECT_STORE_DEFAULTS",
    "M18_PART_FIELD_DEFAULTS",
    "migrate_project_dict",
    "project_to_dict",
    "m18_store_snapshot",
    "install_unified_project_schema",
]
