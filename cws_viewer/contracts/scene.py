"""Versioned immutable scene document for CWS Viewer Core.

The scene is a disposable display read model. It contains stable CWS entity
identities and references to derived geometry, never a second project model.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from cws_viewer.api.errors import ViewerContractError, ViewerErrorCode
from ._validation import finite_float, require_sha256, require_text
from .geometry import GeometryResource
from .primitives import BoundingBox, IDENTITY_MATRIX4, Matrix4, Rgba, matrix4, rgba

SCENE_SCHEMA_VERSION = "1.0"


def _validate_schema_version(version: object) -> str:
    text = str(version or "").strip()
    parts = text.split(".")
    if len(parts) != 2 or any(not part.isdigit() for part in parts):
        raise ViewerContractError(
            "Viewer scene schema heeft geen geldige semver",
            ViewerErrorCode.SCENE_SCHEMA_UNSUPPORTED,
            {"schema_version": text},
        )
    if text != SCENE_SCHEMA_VERSION:
        raise ViewerContractError(
            "Viewer scene schema wordt niet ondersteund",
            ViewerErrorCode.SCENE_SCHEMA_UNSUPPORTED,
            {"schema_version": text, "supported": SCENE_SCHEMA_VERSION},
        )
    return text


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class SceneModel:
    model_id: str
    name: str
    transform: Matrix4 = IDENTITY_MATRIX4
    source_file_id: str | None = None
    source_entity_id: str | None = None
    revision_id: str | None = None
    visible: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", require_text(self.model_id, "model_id"))
        object.__setattr__(self, "name", require_text(self.name, "model.name"))
        object.__setattr__(self, "transform", matrix4(self.transform, "model.transform"))
        for field_name in ("source_file_id", "source_entity_id", "revision_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_text(value, field_name))

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "transform": [list(row) for row in self.transform],
            "source_file_id": self.source_file_id,
            "source_entity_id": self.source_entity_id,
            "revision_id": self.revision_id,
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SceneModel":
        return cls(
            model_id=value["model_id"],
            name=value["name"],
            transform=value.get("transform", IDENTITY_MATRIX4),
            source_file_id=value.get("source_file_id"),
            source_entity_id=value.get("source_entity_id"),
            revision_id=value.get("revision_id"),
            visible=bool(value.get("visible", True)),
        )


@dataclass(frozen=True, slots=True)
class StyleDefinition:
    style_id: str
    color: Rgba
    opacity: float = 1.0
    edges_visible: bool = False

    def __post_init__(self) -> None:
        opacity = finite_float(self.opacity, "style.opacity")
        if not 0.0 <= opacity <= 1.0:
            raise ViewerContractError("style.opacity moet tussen 0 en 1 liggen")
        object.__setattr__(self, "style_id", require_text(self.style_id, "style_id"))
        object.__setattr__(self, "color", rgba(self.color, "style.color"))
        object.__setattr__(self, "opacity", opacity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "style_id": self.style_id,
            "color": list(self.color),
            "opacity": self.opacity,
            "edges_visible": self.edges_visible,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StyleDefinition":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class SceneNode:
    node_id: str
    entity_id: str
    model_id: str
    kind: str
    name: str
    local_bounds: BoundingBox
    source_entity_id: str | None = None
    parent_node_id: str | None = None
    transform: Matrix4 = IDENTITY_MATRIX4
    geometry_id: str | None = None
    selectable: bool = True
    clippable: bool = True
    visible: bool = True
    tags: tuple[str, ...] = ()
    properties_ref: str | None = None
    geometry_hash: str | None = None
    manufacturing_hash: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", require_text(self.node_id, "node_id"))
        object.__setattr__(self, "entity_id", require_text(self.entity_id, "entity_id"))
        object.__setattr__(self, "model_id", require_text(self.model_id, "model_id"))
        object.__setattr__(self, "kind", require_text(self.kind, "node.kind"))
        object.__setattr__(self, "name", require_text(self.name, "node.name"))
        object.__setattr__(self, "transform", matrix4(self.transform, "node.transform"))
        object.__setattr__(
            self,
            "tags",
            tuple(sorted({require_text(item, "node.tag") for item in self.tags})),
        )
        if self.geometry_hash is not None:
            object.__setattr__(self, "geometry_hash", require_sha256(self.geometry_hash, "geometry_hash"))
        if self.manufacturing_hash is not None:
            object.__setattr__(
                self,
                "manufacturing_hash",
                require_sha256(self.manufacturing_hash, "manufacturing_hash"),
            )
        for field_name in (
            "source_entity_id",
            "parent_node_id",
            "geometry_id",
            "properties_ref",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_text(value, field_name))

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "entity_id": self.entity_id,
            "model_id": self.model_id,
            "kind": self.kind,
            "name": self.name,
            "local_bounds": self.local_bounds.to_dict(),
            "source_entity_id": self.source_entity_id,
            "parent_node_id": self.parent_node_id,
            "transform": [list(row) for row in self.transform],
            "geometry_id": self.geometry_id,
            "selectable": self.selectable,
            "clippable": self.clippable,
            "visible": self.visible,
            "tags": list(self.tags),
            "properties_ref": self.properties_ref,
            "geometry_hash": self.geometry_hash,
            "manufacturing_hash": self.manufacturing_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SceneNode":
        return cls(
            node_id=value["node_id"],
            entity_id=value["entity_id"],
            model_id=value["model_id"],
            kind=value["kind"],
            name=value["name"],
            local_bounds=BoundingBox.from_dict(dict(value["local_bounds"])),
            source_entity_id=value.get("source_entity_id"),
            parent_node_id=value.get("parent_node_id"),
            transform=value.get("transform", IDENTITY_MATRIX4),
            geometry_id=value.get("geometry_id"),
            selectable=bool(value.get("selectable", True)),
            clippable=bool(value.get("clippable", True)),
            visible=bool(value.get("visible", True)),
            tags=tuple(value.get("tags", ())),
            properties_ref=value.get("properties_ref"),
            geometry_hash=value.get("geometry_hash"),
            manufacturing_hash=value.get("manufacturing_hash"),
        )


def _reject_duplicates(values: list[str], label: str) -> None:
    duplicates = sorted(item for item, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ViewerContractError(
            f"Viewer scene bevat dubbele {label}",
            details={"duplicates": duplicates},
        )


def _validate_parent_graph(nodes: tuple[SceneNode, ...]) -> None:
    by_id = {node.node_id: node for node in nodes}
    for node in nodes:
        if node.parent_node_id is None:
            continue
        parent = by_id.get(node.parent_node_id)
        if parent is None:
            raise ViewerContractError(
                "Scene node verwijst naar een ontbrekende parent",
                details={"node_id": node.node_id, "parent_node_id": node.parent_node_id},
            )
        if parent.model_id != node.model_id:
            raise ViewerContractError("Scene node en parent horen bij verschillende modellen")

    complete: set[str] = set()
    for node in nodes:
        chain: set[str] = set()
        current: SceneNode | None = node
        while current is not None and current.node_id not in complete:
            if current.node_id in chain:
                raise ViewerContractError("Scene hierarchy bevat een cyclus")
            chain.add(current.node_id)
            current = by_id.get(current.parent_node_id) if current.parent_node_id else None
        complete.update(chain)


@dataclass(frozen=True, slots=True)
class ProjectScene:
    schema_version: str
    project_id: str
    revision_id: str | None
    models: tuple[SceneModel, ...]
    nodes: tuple[SceneNode, ...]
    geometry: tuple[GeometryResource, ...]
    styles: tuple[StyleDefinition, ...] = ()
    scene_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _validate_schema_version(self.schema_version))
        object.__setattr__(self, "project_id", require_text(self.project_id, "project_id"))
        if self.revision_id is not None:
            object.__setattr__(self, "revision_id", require_text(self.revision_id, "revision_id"))
        models = tuple(sorted(self.models, key=lambda item: item.model_id))
        nodes = tuple(sorted(self.nodes, key=lambda item: item.node_id))
        geometry = tuple(sorted(self.geometry, key=lambda item: item.geometry_id))
        styles = tuple(sorted(self.styles, key=lambda item: item.style_id))
        _reject_duplicates([item.model_id for item in models], "model IDs")
        _reject_duplicates([item.node_id for item in nodes], "node IDs")
        _reject_duplicates([item.entity_id for item in nodes], "entity IDs")
        _reject_duplicates([item.geometry_id for item in geometry], "geometry IDs")
        _reject_duplicates([item.style_id for item in styles], "style IDs")
        model_ids = {item.model_id for item in models}
        geometry_ids = {item.geometry_id for item in geometry}
        for node in nodes:
            if node.model_id not in model_ids:
                raise ViewerContractError(
                    "Scene node verwijst naar een ontbrekend model",
                    details={"node_id": node.node_id, "model_id": node.model_id},
                )
            if node.geometry_id is not None and node.geometry_id not in geometry_ids:
                raise ViewerContractError(
                    "Scene node verwijst naar ontbrekende geometry",
                    details={"node_id": node.node_id, "geometry_id": node.geometry_id},
                )
        _validate_parent_graph(nodes)
        object.__setattr__(self, "models", models)
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "geometry", geometry)
        object.__setattr__(self, "styles", styles)
        found = hashlib.sha256(_canonical_json_bytes(self._content_dict())).hexdigest()
        if self.scene_hash:
            expected = require_sha256(self.scene_hash, "scene_hash")
            if expected != found:
                raise ViewerContractError(
                    "Viewer scene hash komt niet overeen met de inhoud",
                    ViewerErrorCode.GEOMETRY_HASH_MISMATCH,
                    {"expected": expected, "found": found},
                )
        object.__setattr__(self, "scene_hash", found)

    def _content_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "revision_id": self.revision_id,
            "models": [item.to_dict() for item in self.models],
            "nodes": [item.to_dict() for item in self.nodes],
            "geometry": [item.to_dict() for item in self.geometry],
            "styles": [item.to_dict() for item in self.styles],
        }

    def to_dict(self) -> dict[str, Any]:
        value = self._content_dict()
        value["scene_hash"] = self.scene_hash
        return value

    def to_json_bytes(self) -> bytes:
        return _canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProjectScene":
        try:
            return cls(
                schema_version=value["schema_version"],
                project_id=value["project_id"],
                revision_id=value.get("revision_id"),
                models=tuple(SceneModel.from_dict(item) for item in value.get("models", ())),
                nodes=tuple(SceneNode.from_dict(item) for item in value.get("nodes", ())),
                geometry=tuple(GeometryResource.from_dict(item) for item in value.get("geometry", ())),
                styles=tuple(StyleDefinition.from_dict(item) for item in value.get("styles", ())),
                scene_hash=value.get("scene_hash", ""),
            )
        except ViewerContractError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ViewerContractError("Viewer scene-document is onvolledig of ongeldig") from exc

    @classmethod
    def from_json_bytes(cls, payload: bytes) -> "ProjectScene":
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ViewerContractError("Viewer scene bevat ongeldige JSON") from exc
        if not isinstance(value, dict):
            raise ViewerContractError("Viewer scene root moet een object zijn")
        return cls.from_dict(value)


@dataclass(frozen=True, slots=True)
class ColorAssignment:
    entity_id: str
    color: Rgba

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", require_text(self.entity_id, "entity_id"))
        object.__setattr__(self, "color", rgba(self.color, "color"))


@dataclass(frozen=True, slots=True)
class ScenePatch:
    expected_scene_hash: str
    upsert_nodes: tuple[SceneNode, ...] = ()
    remove_node_ids: tuple[str, ...] = ()
    upsert_geometry: tuple[GeometryResource, ...] = ()
    remove_geometry_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        upsert_nodes = tuple(self.upsert_nodes)
        remove_nodes = tuple(sorted({require_text(item, "remove_node_id") for item in self.remove_node_ids}))
        upsert_geometry = tuple(self.upsert_geometry)
        remove_geometry = tuple(
            sorted({require_text(item, "remove_geometry_id") for item in self.remove_geometry_ids})
        )
        if {item.node_id for item in upsert_nodes}.intersection(remove_nodes):
            raise ViewerContractError("ScenePatch kan een node niet tegelijk bijwerken en verwijderen")
        if {item.geometry_id for item in upsert_geometry}.intersection(remove_geometry):
            raise ViewerContractError("ScenePatch kan geometry niet tegelijk bijwerken en verwijderen")
        object.__setattr__(self, "expected_scene_hash", require_sha256(self.expected_scene_hash, "expected_scene_hash"))
        object.__setattr__(self, "upsert_nodes", tuple(sorted(upsert_nodes, key=lambda item: item.node_id)))
        object.__setattr__(self, "remove_node_ids", remove_nodes)
        object.__setattr__(
            self,
            "upsert_geometry",
            tuple(sorted(upsert_geometry, key=lambda item: item.geometry_id)),
        )
        object.__setattr__(self, "remove_geometry_ids", remove_geometry)


__all__ = [
    "ColorAssignment",
    "ProjectScene",
    "SCENE_SCHEMA_VERSION",
    "SceneModel",
    "SceneNode",
    "ScenePatch",
    "StyleDefinition",
]
