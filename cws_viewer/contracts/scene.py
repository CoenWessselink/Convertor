"""Immutable scene graph contracts and deterministic scene hashing."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from typing import Any, Iterable, Mapping

from cws_viewer.core.serialization import is_sha256, parse_semver, stable_sha256
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import BoundingBox, Matrix4, Rgba, Vector3
from cws_viewer.version import SCENE_SCHEMA_VERSION, VIEWER_API_VERSION

from .enums import GeometryRepresentation, NodeKind, RenderMode


def _tuple_str(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


def _vector_from(value: Any) -> Vector3:
    if isinstance(value, Vector3):
        return value
    if isinstance(value, Mapping):
        return Vector3(float(value["x"]), float(value["y"]), float(value["z"]))
    return Vector3.from_iterable(value)


def _bbox_from(value: Any) -> BoundingBox:
    if isinstance(value, BoundingBox):
        return value
    if isinstance(value, Mapping):
        return BoundingBox(_vector_from(value["minimum"]), _vector_from(value["maximum"]))
    raise TypeError("BoundingBox verwacht een mapping")


def _matrix_from(value: Any) -> Matrix4:
    if isinstance(value, Matrix4):
        return value
    if isinstance(value, Mapping) and "values" in value:
        return Matrix4(tuple(float(v) for v in value["values"]))
    if isinstance(value, (tuple, list)) and len(value) == 4 and all(
        isinstance(row, (tuple, list)) for row in value
    ):
        return Matrix4.from_rows(value)
    return Matrix4(tuple(float(v) for v in value))


def _rgba_from(value: Any) -> Rgba:
    if isinstance(value, Rgba):
        return value
    if isinstance(value, Mapping):
        return Rgba(
            float(value["red"]),
            float(value["green"]),
            float(value["blue"]),
            float(value.get("alpha", 1.0)),
        )
    return Rgba(*value)


@dataclass(frozen=True, slots=True)
class MeshLod:
    level: int
    content_hash: str
    payload_ref: str
    vertex_count: int
    triangle_count: int
    byte_length: int = 0
    max_error_mm: float | None = None

    def __post_init__(self) -> None:
        if self.level < 0:
            raise ValueError("LOD-level mag niet negatief zijn")
        if not is_sha256(self.content_hash):
            raise ViewerError(
                "MeshLod content_hash is geen SHA-256",
                code=ViewerErrorCode.GEOMETRY_HASH_MISMATCH,
                context={"content_hash": self.content_hash},
            )
        if min(self.vertex_count, self.triangle_count, self.byte_length) < 0:
            raise ValueError("MeshLod aantallen mogen niet negatief zijn")
        if not str(self.payload_ref).strip():
            raise ValueError("MeshLod payload_ref ontbreekt")

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "content_hash": self.content_hash.lower(),
            "payload_ref": self.payload_ref,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "byte_length": self.byte_length,
            "max_error_mm": self.max_error_mm,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MeshLod":
        return cls(
            level=int(value["level"]),
            content_hash=str(value["content_hash"]),
            payload_ref=str(value["payload_ref"]),
            vertex_count=int(value.get("vertex_count", 0)),
            triangle_count=int(value.get("triangle_count", 0)),
            byte_length=int(value.get("byte_length", 0)),
            max_error_mm=(
                None
                if value.get("max_error_mm") is None
                else float(value["max_error_mm"])
            ),
        )


@dataclass(frozen=True, slots=True)
class GeometryResource:
    geometry_id: str
    representation: GeometryRepresentation
    content_hash: str
    units: str
    payload_ref: str
    lods: tuple[MeshLod, ...] = ()
    feature_map_ref: str | None = None
    byte_length: int = 0
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "representation", GeometryRepresentation(self.representation))
        object.__setattr__(self, "lods", tuple(self.lods))
        object.__setattr__(self, "metadata", tuple((str(k), str(v)) for k, v in self.metadata))
        if not self.geometry_id.strip():
            raise ValueError("geometry_id ontbreekt")
        if not is_sha256(self.content_hash):
            raise ViewerError(
                "GeometryResource content_hash is geen SHA-256",
                code=ViewerErrorCode.GEOMETRY_HASH_MISMATCH,
                context={"geometry_id": self.geometry_id, "content_hash": self.content_hash},
            )
        if not self.units.strip():
            raise ValueError("GeometryResource units ontbreken")
        if not self.payload_ref.strip():
            raise ValueError("GeometryResource payload_ref ontbreekt")
        if self.byte_length < 0:
            raise ValueError("GeometryResource byte_length mag niet negatief zijn")
        levels = [lod.level for lod in self.lods]
        if len(levels) != len(set(levels)):
            raise ViewerError(
                "GeometryResource bevat dubbele LOD-levels",
                code=ViewerErrorCode.SCENE_DUPLICATE_ID,
                context={"geometry_id": self.geometry_id, "levels": levels},
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "representation": self.representation.value,
            "content_hash": self.content_hash.lower(),
            "units": self.units,
            "payload_ref": self.payload_ref,
            "lods": [lod.to_dict() for lod in self.lods],
            "feature_map_ref": self.feature_map_ref,
            "byte_length": self.byte_length,
            "metadata": [[key, value] for key, value in self.metadata],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GeometryResource":
        return cls(
            geometry_id=str(value["geometry_id"]),
            representation=GeometryRepresentation(str(value["representation"])),
            content_hash=str(value["content_hash"]),
            units=str(value.get("units", "mm")),
            payload_ref=str(value["payload_ref"]),
            lods=tuple(MeshLod.from_dict(item) for item in value.get("lods", ())),
            feature_map_ref=(
                None if value.get("feature_map_ref") is None else str(value["feature_map_ref"])
            ),
            byte_length=int(value.get("byte_length", 0)),
            metadata=tuple((str(k), str(v)) for k, v in value.get("metadata", ())),
        )


@dataclass(frozen=True, slots=True)
class StyleDefinition:
    style_id: str
    color: Rgba
    mode: RenderMode = RenderMode.SHADED_EDGES
    line_width: float = 1.0
    visible: bool = True
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", RenderMode(self.mode))
        object.__setattr__(self, "tags", _tuple_str(self.tags))
        if not self.style_id.strip():
            raise ValueError("style_id ontbreekt")
        if self.line_width <= 0:
            raise ValueError("line_width moet positief zijn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "style_id": self.style_id,
            "color": {
                "red": self.color.red,
                "green": self.color.green,
                "blue": self.color.blue,
                "alpha": self.color.alpha,
            },
            "mode": self.mode.value,
            "line_width": self.line_width,
            "visible": self.visible,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StyleDefinition":
        return cls(
            style_id=str(value["style_id"]),
            color=_rgba_from(value["color"]),
            mode=RenderMode(str(value.get("mode", RenderMode.SHADED_EDGES.value))),
            line_width=float(value.get("line_width", 1.0)),
            visible=bool(value.get("visible", True)),
            tags=_tuple_str(value.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class SceneModel:
    model_id: str
    name: str
    source_file_id: str | None
    root_node_ids: tuple[str, ...]
    transform: Matrix4 = Matrix4.identity()
    revision_id: str | None = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "root_node_ids", _tuple_str(self.root_node_ids))
        object.__setattr__(self, "tags", _tuple_str(self.tags))
        if not self.model_id.strip():
            raise ValueError("model_id ontbreekt")
        if len(self.root_node_ids) != len(set(self.root_node_ids)):
            raise ViewerError(
                "SceneModel bevat dubbele root_node_ids",
                code=ViewerErrorCode.SCENE_DUPLICATE_ID,
                context={"model_id": self.model_id},
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "source_file_id": self.source_file_id,
            "root_node_ids": list(self.root_node_ids),
            "transform": list(self.transform.values),
            "revision_id": self.revision_id,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SceneModel":
        return cls(
            model_id=str(value["model_id"]),
            name=str(value.get("name", "")),
            source_file_id=(
                None if value.get("source_file_id") is None else str(value["source_file_id"])
            ),
            root_node_ids=_tuple_str(value.get("root_node_ids", ())),
            transform=_matrix_from(value.get("transform", Matrix4.identity().values)),
            revision_id=(
                None if value.get("revision_id") is None else str(value["revision_id"])
            ),
            tags=_tuple_str(value.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class SceneNode:
    node_id: str
    entity_id: str
    source_entity_id: str | None
    parent_node_id: str | None
    kind: NodeKind
    name: str
    transform: Matrix4
    local_bounds: BoundingBox
    geometry_id: str | None
    selectable: bool = True
    clippable: bool = True
    visible: bool = True
    tags: tuple[str, ...] = ()
    properties_ref: str | None = None
    geometry_hash: str | None = None
    manufacturing_hash: str | None = None
    style_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", NodeKind(self.kind))
        object.__setattr__(self, "tags", _tuple_str(self.tags))
        if not self.node_id.strip():
            raise ValueError("node_id ontbreekt")
        if not self.entity_id.strip():
            raise ValueError("entity_id ontbreekt")
        for label, digest in (
            ("geometry_hash", self.geometry_hash),
            ("manufacturing_hash", self.manufacturing_hash),
        ):
            if digest and not is_sha256(digest):
                raise ViewerError(
                    f"{label} is geen SHA-256",
                    code=ViewerErrorCode.GEOMETRY_HASH_MISMATCH,
                    context={"node_id": self.node_id, label: digest},
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "entity_id": self.entity_id,
            "source_entity_id": self.source_entity_id,
            "parent_node_id": self.parent_node_id,
            "kind": self.kind.value,
            "name": self.name,
            "transform": list(self.transform.values),
            "local_bounds": {
                "minimum": {
                    "x": self.local_bounds.minimum.x,
                    "y": self.local_bounds.minimum.y,
                    "z": self.local_bounds.minimum.z,
                },
                "maximum": {
                    "x": self.local_bounds.maximum.x,
                    "y": self.local_bounds.maximum.y,
                    "z": self.local_bounds.maximum.z,
                },
            },
            "geometry_id": self.geometry_id,
            "selectable": self.selectable,
            "clippable": self.clippable,
            "visible": self.visible,
            "tags": list(self.tags),
            "properties_ref": self.properties_ref,
            "geometry_hash": self.geometry_hash,
            "manufacturing_hash": self.manufacturing_hash,
            "style_id": self.style_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SceneNode":
        return cls(
            node_id=str(value["node_id"]),
            entity_id=str(value["entity_id"]),
            source_entity_id=(
                None if value.get("source_entity_id") is None else str(value["source_entity_id"])
            ),
            parent_node_id=(
                None if value.get("parent_node_id") is None else str(value["parent_node_id"])
            ),
            kind=NodeKind(str(value["kind"])),
            name=str(value.get("name", "")),
            transform=_matrix_from(value.get("transform", Matrix4.identity().values)),
            local_bounds=_bbox_from(value.get("local_bounds", {
                "minimum": {"x": 0, "y": 0, "z": 0},
                "maximum": {"x": 0, "y": 0, "z": 0},
            })),
            geometry_id=(None if value.get("geometry_id") is None else str(value["geometry_id"])),
            selectable=bool(value.get("selectable", True)),
            clippable=bool(value.get("clippable", True)),
            visible=bool(value.get("visible", True)),
            tags=_tuple_str(value.get("tags", ())),
            properties_ref=(
                None if value.get("properties_ref") is None else str(value["properties_ref"])
            ),
            geometry_hash=(
                None if value.get("geometry_hash") is None else str(value["geometry_hash"])
            ),
            manufacturing_hash=(
                None
                if value.get("manufacturing_hash") is None
                else str(value["manufacturing_hash"])
            ),
            style_id=(None if value.get("style_id") is None else str(value["style_id"])),
        )


@dataclass(frozen=True, slots=True)
class ProjectScene:
    schema_version: str
    api_version: str
    project_id: str
    revision_id: str | None
    models: tuple[SceneModel, ...]
    nodes: tuple[SceneNode, ...]
    geometry: tuple[GeometryResource, ...]
    styles: tuple[StyleDefinition, ...]
    scene_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "models", tuple(self.models))
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "geometry", tuple(self.geometry))
        object.__setattr__(self, "styles", tuple(self.styles))
        self._validate_schema()
        if not self.project_id.strip():
            raise ValueError("project_id ontbreekt")

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        revision_id: str | None,
        models: Iterable[SceneModel],
        nodes: Iterable[SceneNode],
        geometry: Iterable[GeometryResource] = (),
        styles: Iterable[StyleDefinition] = (),
    ) -> "ProjectScene":
        scene = cls(
            schema_version=SCENE_SCHEMA_VERSION,
            api_version=VIEWER_API_VERSION,
            project_id=project_id,
            revision_id=revision_id,
            models=tuple(models),
            nodes=tuple(nodes),
            geometry=tuple(geometry),
            styles=tuple(styles),
            scene_hash="",
        )
        hashed = replace(scene, scene_hash=scene.calculate_hash())
        # The digest above was calculated from this exact immutable instance.
        # Keep all structural/reference validation, but do not serialize the
        # full scene a second time on the first-frame critical path.  Scenes
        # loaded from external payloads still use the default hash verification.
        hashed.validate(verify_hash=False)
        return hashed

    def _validate_schema(self) -> None:
        current_major = parse_semver(SCENE_SCHEMA_VERSION)[0]
        scene_major = parse_semver(self.schema_version)[0]
        if scene_major != current_major:
            raise ViewerError(
                f"Niet-ondersteund sceneschema {self.schema_version!r}",
                code=ViewerErrorCode.SCENE_SCHEMA_UNSUPPORTED,
                context={"supported": SCENE_SCHEMA_VERSION},
            )
        api_major = parse_semver(self.api_version)[0]
        expected_api_major = parse_semver(VIEWER_API_VERSION)[0]
        if api_major != expected_api_major:
            raise ViewerError(
                f"Niet-ondersteunde viewer-API {self.api_version!r}",
                code=ViewerErrorCode.SCENE_SCHEMA_UNSUPPORTED,
                context={"supported_api": VIEWER_API_VERSION},
            )

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "api_version": self.api_version,
            "project_id": self.project_id,
            "revision_id": self.revision_id,
            "models": [item.to_dict() for item in self.models],
            "nodes": [item.to_dict() for item in self.nodes],
            "geometry": [item.to_dict() for item in self.geometry],
            "styles": [item.to_dict() for item in self.styles],
        }

    def calculate_hash(self) -> str:
        # ``payload_dict`` is already a primitive JSON contract.  Sending its
        # ~10 MB large-model payload through ``to_primitive`` again creates a
        # second complete object graph.  Direct canonical JSON is byte-for-byte
        # identical for scene contracts and removes that first-frame copy.
        payload = json.dumps(
            self.payload_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def validate(self, *, verify_hash: bool = True) -> None:
        self._validate_schema()
        from cws_viewer.core.validation import validate_project_scene

        validate_project_scene(self, verify_hash=verify_hash)

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_dict()
        payload["scene_hash"] = self.scene_hash
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], *, verify: bool = True) -> "ProjectScene":
        scene = cls(
            schema_version=str(value["schema_version"]),
            api_version=str(value.get("api_version", VIEWER_API_VERSION)),
            project_id=str(value["project_id"]),
            revision_id=(None if value.get("revision_id") is None else str(value["revision_id"])),
            models=tuple(SceneModel.from_dict(item) for item in value.get("models", ())),
            nodes=tuple(SceneNode.from_dict(item) for item in value.get("nodes", ())),
            geometry=tuple(
                GeometryResource.from_dict(item) for item in value.get("geometry", ())
            ),
            styles=tuple(StyleDefinition.from_dict(item) for item in value.get("styles", ())),
            scene_hash=str(value.get("scene_hash", "")),
        )
        if verify:
            scene.validate()
        return scene


__all__ = [
    "MeshLod",
    "GeometryResource",
    "StyleDefinition",
    "SceneModel",
    "SceneNode",
    "ProjectScene",
]
