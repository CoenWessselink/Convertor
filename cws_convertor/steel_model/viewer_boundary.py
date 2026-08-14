"""Host-side contract for one controlled SteelConverter viewer handover."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping
from uuid import UUID, uuid5

from ._canonical import canonical_json_bytes, canonical_sha256
from .contracts import STEEL_MODEL_SCHEMA_VERSION, SteelModelSnapshot


VIEWER_HOST_CONTRACT_VERSION = "1.0"
VIEWER_ID_NAMESPACE = UUID("64a9f924-5b06-4d9d-9f60-495804098e5f")

REQUIRED_VIEWER_CAPABILITIES: tuple[str, ...] = (
    "accuracy_debug",
    "camera.standard_views",
    "compare.models",
    "large_model.telemetry",
    "measurement.state",
    "scene.load",
    "scene.patch",
    "section.planes",
    "selection.sync",
    "visibility.isolate",
)

# A renderer may be attached for trustworthy geometry display before advanced
# measurement/section/compare modules are accepted. Those tools remain gated
# individually by the complete capability list above.
CORE_VIEWER_CAPABILITIES: tuple[str, ...] = (
    "accuracy_debug",
    "camera.standard_views",
    "large_model.telemetry",
    "scene.load",
    "scene.patch",
    "selection.sync",
)

APP_OWNED_STATE: tuple[str, ...] = (
    "audit_log",
    "canonical_rebuild",
    "production_export",
    "project_persistence",
    "source_files",
    "steel_model",
    "validation",
    "workbench_edits",
)

VIEWER_OWNED_STATE: tuple[str, ...] = (
    "camera",
    "clipping",
    "compare_view",
    "display_styles",
    "measurements",
    "selection",
    "temporary_markup",
    "visibility",
    "viewpoints",
)

FORBIDDEN_VIEWER_RESPONSIBILITIES: tuple[str, ...] = (
    "authoritative_geometry_mutation",
    "ifc_or_step_source_parsing",
    "machine_code_release",
    "production_gate_override",
    "project_file_persistence",
)


def _required_text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} is required")
    return result


def _sha256(value: Any, label: str) -> str:
    result = _required_text(value, label).lower()
    if len(result) != 64 or any(char not in "0123456789abcdef" for char in result):
        raise ValueError(f"{label} is not a SHA-256")
    return result


@dataclass(frozen=True, slots=True)
class ViewerEntityBinding:
    steel_model_id: str
    viewer_node_id: str
    source_file_id: str = ""
    source_entity_id: str = ""
    viewer_geometry_id: str = ""
    viewer_geometry_content_sha256: str = ""
    canonical_geometry_hash: str = ""
    manufacturing_hash: str = ""
    accuracy_status: str = "not_applicable"

    def __post_init__(self) -> None:
        object.__setattr__(self, "steel_model_id", _required_text(self.steel_model_id, "steel_model_id"))
        object.__setattr__(self, "viewer_node_id", _required_text(self.viewer_node_id, "viewer_node_id"))
        if self.viewer_geometry_id:
            try:
                UUID(self.viewer_geometry_id)
            except ValueError as exc:
                raise ValueError("viewer_geometry_id must be a stable UUID") from exc
        if self.viewer_geometry_content_sha256:
            object.__setattr__(
                self,
                "viewer_geometry_content_sha256",
                _sha256(
                    self.viewer_geometry_content_sha256,
                    "viewer_geometry_content_sha256",
                ),
            )
            if not self.viewer_geometry_id:
                raise ValueError("Viewer geometry content requires a geometry ID")
        if self.canonical_geometry_hash:
            object.__setattr__(
                self,
                "canonical_geometry_hash",
                _sha256(self.canonical_geometry_hash, "canonical_geometry_hash"),
            )
        if self.manufacturing_hash:
            object.__setattr__(
                self,
                "manufacturing_hash",
                _sha256(self.manufacturing_hash, "manufacturing_hash"),
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "steel_model_id": self.steel_model_id,
            "viewer_node_id": self.viewer_node_id,
            "source_file_id": self.source_file_id,
            "source_entity_id": self.source_entity_id,
            "viewer_geometry_id": self.viewer_geometry_id,
            "viewer_geometry_content_sha256": self.viewer_geometry_content_sha256,
            "canonical_geometry_hash": self.canonical_geometry_hash,
            "manufacturing_hash": self.manufacturing_hash,
            "accuracy_status": self.accuracy_status,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ViewerEntityBinding":
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class ViewerHostSnapshot:
    project_id: str
    steel_model_snapshot_sha256: str
    bindings: tuple[ViewerEntityBinding, ...]
    contract_version: str = VIEWER_HOST_CONTRACT_VERSION
    steel_model_schema_version: str = STEEL_MODEL_SCHEMA_VERSION
    required_capabilities: tuple[str, ...] = REQUIRED_VIEWER_CAPABILITIES
    snapshot_sha256: str = ""

    def __post_init__(self) -> None:
        if self.contract_version != VIEWER_HOST_CONTRACT_VERSION:
            raise ValueError(f"Unsupported viewer host contract {self.contract_version!r}")
        if self.steel_model_schema_version != STEEL_MODEL_SCHEMA_VERSION:
            raise ValueError(f"Unsupported SteelModel schema {self.steel_model_schema_version!r}")
        try:
            UUID(self.project_id)
        except ValueError as exc:
            raise ValueError("Viewer host project_id must be a UUID") from exc
        object.__setattr__(
            self,
            "steel_model_snapshot_sha256",
            _sha256(self.steel_model_snapshot_sha256, "steel_model_snapshot_sha256"),
        )
        bindings = tuple(sorted(self.bindings, key=lambda item: item.steel_model_id))
        model_ids = [item.steel_model_id for item in bindings]
        node_ids = [item.viewer_node_id for item in bindings]
        if len(model_ids) != len(set(model_ids)) or len(node_ids) != len(set(node_ids)):
            raise ValueError("Viewer host bindings contain duplicate IDs")
        capabilities = tuple(sorted({_required_text(item, "required capability") for item in self.required_capabilities}))
        object.__setattr__(self, "bindings", bindings)
        object.__setattr__(self, "required_capabilities", capabilities)
        found = canonical_sha256(self._content_dict())
        if self.snapshot_sha256 and _sha256(self.snapshot_sha256, "snapshot_sha256") != found:
            raise ValueError("Viewer host snapshot hash does not match its content")
        object.__setattr__(self, "snapshot_sha256", found)

    def _content_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "steel_model_schema_version": self.steel_model_schema_version,
            "project_id": self.project_id,
            "steel_model_snapshot_sha256": self.steel_model_snapshot_sha256,
            "required_capabilities": list(self.required_capabilities),
            "bindings": [item.to_dict() for item in self.bindings],
            "ownership": {
                "application": list(APP_OWNED_STATE),
                "viewer": list(VIEWER_OWNED_STATE),
                "viewer_forbidden": list(FORBIDDEN_VIEWER_RESPONSIBILITIES),
            },
        }

    def to_dict(self) -> dict[str, Any]:
        value = self._content_dict()
        value["snapshot_sha256"] = self.snapshot_sha256
        return value

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def binding(self, steel_model_id: str) -> ViewerEntityBinding | None:
        return next(
            (
                item
                for item in self.bindings
                if item.steel_model_id == str(steel_model_id)
            ),
            None,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ViewerHostSnapshot":
        raw = dict(value)
        supplied_ownership = raw.pop("ownership", None)
        expected_ownership = {
            "application": list(APP_OWNED_STATE),
            "viewer": list(VIEWER_OWNED_STATE),
            "viewer_forbidden": list(FORBIDDEN_VIEWER_RESPONSIBILITIES),
        }
        if supplied_ownership is not None and supplied_ownership != expected_ownership:
            raise ValueError("Viewer host ownership boundary was modified")
        raw["bindings"] = tuple(ViewerEntityBinding.from_dict(item) for item in raw.get("bindings", ()))
        raw["required_capabilities"] = tuple(raw.get("required_capabilities") or ())
        return cls(**raw)

    @classmethod
    def from_json_bytes(cls, payload: bytes) -> "ViewerHostSnapshot":
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Viewer host JSON root must be an object")
        return cls.from_dict(value)


@dataclass(frozen=True, slots=True)
class ViewerHandshake:
    component_name: str
    component_version: str
    contract_version: str
    steel_model_schema_version: str
    capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "component_name", _required_text(self.component_name, "component_name"))
        object.__setattr__(self, "component_version", _required_text(self.component_version, "component_version"))
        object.__setattr__(self, "contract_version", _required_text(self.contract_version, "contract_version"))
        object.__setattr__(
            self,
            "steel_model_schema_version",
            _required_text(self.steel_model_schema_version, "steel_model_schema_version"),
        )
        object.__setattr__(
            self,
            "capabilities",
            tuple(sorted({_required_text(item, "viewer capability") for item in self.capabilities})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_name": self.component_name,
            "component_version": self.component_version,
            "contract_version": self.contract_version,
            "steel_model_schema_version": self.steel_model_schema_version,
            "capabilities": list(self.capabilities),
        }


def validate_viewer_handshake(handshake: ViewerHandshake) -> dict[str, Any]:
    errors: list[str] = []
    if handshake.contract_version != VIEWER_HOST_CONTRACT_VERSION:
        errors.append(
            f"viewer contract {handshake.contract_version} != {VIEWER_HOST_CONTRACT_VERSION}"
        )
    if handshake.steel_model_schema_version != STEEL_MODEL_SCHEMA_VERSION:
        errors.append(
            "SteelModel schema "
            f"{handshake.steel_model_schema_version} != {STEEL_MODEL_SCHEMA_VERSION}"
        )
    missing_core = sorted(set(CORE_VIEWER_CAPABILITIES) - set(handshake.capabilities))
    missing = sorted(set(REQUIRED_VIEWER_CAPABILITIES) - set(handshake.capabilities))
    if missing_core:
        errors.append("missing core capabilities: " + ", ".join(missing_core))
    return {
        "compatible": not errors,
        "complete": not errors and not missing,
        "component_name": handshake.component_name,
        "component_version": handshake.component_version,
        "missing_core_capabilities": missing_core,
        "missing_capabilities": missing,
        "errors": errors,
    }


def build_viewer_host_snapshot(steel_model: SteelModelSnapshot) -> ViewerHostSnapshot:
    bindings: list[ViewerEntityBinding] = []
    for entity in steel_model.entities:
        node_id = str(
            uuid5(
                VIEWER_ID_NAMESPACE,
                f"{steel_model.project_id}|node|{entity.steel_model_id}",
            )
        )
        geometry_id = (
            str(
                uuid5(
                    VIEWER_ID_NAMESPACE,
                    f"{steel_model.project_id}|geometry|{entity.steel_model_id}",
                )
            )
            if entity.geometry_hash
            else ""
        )
        bindings.append(
            ViewerEntityBinding(
                steel_model_id=entity.steel_model_id,
                viewer_node_id=node_id,
                source_file_id=entity.source.source_file_id,
                source_entity_id=entity.source.source_entity_id,
                viewer_geometry_id=geometry_id,
                canonical_geometry_hash=entity.geometry_hash,
                manufacturing_hash=entity.manufacturing_hash,
                accuracy_status=entity.accuracy_status.value,
            )
        )
    return ViewerHostSnapshot(
        project_id=steel_model.project_id,
        steel_model_snapshot_sha256=steel_model.snapshot_sha256,
        bindings=tuple(bindings),
    )


__all__ = [
    "APP_OWNED_STATE",
    "CORE_VIEWER_CAPABILITIES",
    "FORBIDDEN_VIEWER_RESPONSIBILITIES",
    "REQUIRED_VIEWER_CAPABILITIES",
    "VIEWER_HOST_CONTRACT_VERSION",
    "VIEWER_OWNED_STATE",
    "ViewerEntityBinding",
    "ViewerHandshake",
    "ViewerHostSnapshot",
    "build_viewer_host_snapshot",
    "validate_viewer_handshake",
]
