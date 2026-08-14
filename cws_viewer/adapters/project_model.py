"""Read-only adapter from CWS Canonical Project Model to ProjectScene.

The adapter creates scene identities and deferred geometry handles.  It does not
parse IFC/STEP, split solids, mutate canonical data or manufacture geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from cws_viewer.contracts.enums import GeometryRepresentation, NodeKind, RenderMode
from cws_viewer.contracts.scene import (
    GeometryResource,
    MeshLod,
    ProjectScene,
    SceneModel,
    SceneNode,
    StyleDefinition,
)
from cws_viewer.core.serialization import is_sha256
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import BoundingBox, Matrix4, Rgba, Vector3
from cws_viewer.version import (
    SUPPORTED_PROJECT_SCHEMA_MAJORS,
    VALIDATED_PROJECT_SCHEMA_VERSIONS,
)


@dataclass(frozen=True, slots=True)
class SceneBuildOptions:
    include_assemblies: bool = True
    include_parts: bool = True
    include_purchased_items: bool = True
    include_fasteners: bool = True
    include_welds: bool = True
    create_deferred_geometry: bool = True
    include_zero_bounds: bool = True
    prefer_source_geometry: bool = True


@dataclass(frozen=True, slots=True)
class SceneBuildReport:
    project_schema_version: str
    validated_schema: bool
    node_count: int
    selectable_count: int
    geometry_resource_count: int
    deferred_geometry_count: int
    loaded_geometry_count: int = 0
    proxy_geometry_count: int = 0
    zero_bounds_count: int = 0
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_schema_version": self.project_schema_version,
            "validated_schema": self.validated_schema,
            "node_count": self.node_count,
            "selectable_count": self.selectable_count,
            "geometry_resource_count": self.geometry_resource_count,
            "deferred_geometry_count": self.deferred_geometry_count,
            "loaded_geometry_count": self.loaded_geometry_count,
            "proxy_geometry_count": self.proxy_geometry_count,
            "zero_bounds_count": self.zero_bounds_count,
            "warnings": list(self.warnings),
        }


_CATEGORY_STYLES = (
    StyleDefinition("style-project", Rgba(0.38, 0.44, 0.53, 1.0), tags=("project",)),
    StyleDefinition("style-assembly", Rgba(0.23, 0.48, 0.82, 1.0), tags=("assembly",)),
    StyleDefinition("style-part", Rgba(0.63, 0.68, 0.75, 1.0), tags=("part",)),
    StyleDefinition("style-purchased", Rgba(0.49, 0.64, 0.42, 1.0), tags=("purchased",)),
    StyleDefinition("style-fastener", Rgba(0.83, 0.62, 0.24, 1.0), tags=("fastener",)),
    StyleDefinition("style-weld", Rgba(0.80, 0.35, 0.32, 1.0), tags=("weld",)),
    StyleDefinition(
        "style-group",
        Rgba(0.5, 0.5, 0.5, 0.0),
        mode=RenderMode.WIREFRAME,
        visible=False,
        tags=("synthetic-group",),
    ),
)


def _project_version(project: Any) -> str:
    return str(getattr(project, "schema_version", "") or "")


def _major(version: str) -> int:
    try:
        return int(str(version).split(".", 1)[0])
    except (TypeError, ValueError):
        return -1


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_dict(entity: Any) -> dict[str, Any]:
    if hasattr(entity, "to_dict") and callable(entity.to_dict):
        return dict(entity.to_dict())
    if hasattr(entity, "__dict__"):
        return dict(vars(entity))
    return {}


def _source_entity_id(entity: Any) -> str | None:
    source_identity = getattr(entity, "source_identity", None)
    if source_identity is None:
        return None
    for field in ("source_entity_id", "global_id", "product_id", "occurrence_id"):
        value = str(getattr(source_identity, field, "") or "").strip()
        if value:
            return value
    return None


def _matrix(entity: Any) -> Matrix4:
    placement = getattr(entity, "global_placement", None)
    rows = getattr(placement, "matrix", None)
    if rows is None:
        return Matrix4.identity()
    try:
        return Matrix4.from_rows(rows)
    except ViewerError:
        raise
    except Exception as exc:
        raise ViewerError(
            "Projectentity bevat een ongeldige placementmatrix",
            code=ViewerErrorCode.TRANSFORM_INVALID,
            context={"entity_id": getattr(entity, "internal_id", ""), "error": str(exc)},
        ) from exc


def _vector(value: Any) -> Vector3 | None:
    if isinstance(value, Mapping):
        if {"x", "y", "z"}.issubset(value):
            return Vector3(float(value["x"]), float(value["y"]), float(value["z"]))
        if {"X", "Y", "Z"}.issubset(value):
            return Vector3(float(value["X"]), float(value["Y"]), float(value["Z"]))
    if isinstance(value, (tuple, list)) and len(value) >= 3:
        return Vector3(float(value[0]), float(value[1]), float(value[2]))
    return None


def _bounds_from_mapping(value: Any) -> BoundingBox | None:
    data = _mapping(value)
    minimum = _vector(data.get("minimum") or data.get("min") or data.get("lower"))
    maximum = _vector(data.get("maximum") or data.get("max") or data.get("upper"))
    if minimum is not None and maximum is not None:
        try:
            return BoundingBox(minimum, maximum)
        except ValueError:
            return None
    dimensions = data.get("dimensions") or data.get("size")
    size = _vector(dimensions)
    if size is not None and min(size.x, size.y, size.z) >= 0:
        return BoundingBox.from_dimensions(size.x, size.y, size.z)
    return None


def _entity_bounds(entity: Any) -> BoundingBox:
    descriptor = _mapping(getattr(entity, "geometry_descriptor", None))
    candidates = (
        descriptor.get("bounding_box"),
        descriptor.get("bbox"),
        descriptor.get("bounds"),
        descriptor,
    )
    canonical = _mapping(getattr(entity, "canonical_part", None))
    geometry = _mapping(canonical.get("geometry"))
    metrics = _mapping(canonical.get("metrics"))
    candidates += (
        geometry.get("bounding_box"),
        metrics.get("bounding_box"),
        canonical.get("bounding_box"),
    )
    for candidate in candidates:
        bounds = _bounds_from_mapping(candidate)
        if bounds is not None:
            return bounds
    # No geometric claim is made when the project entity lacks trustworthy
    # bounds.  A zero bound is explicit and reported by SceneBuildReport.
    return BoundingBox.zero()


def _entity_tags(entity: Any, kind: NodeKind) -> tuple[str, ...]:
    values = {kind.value, str(getattr(entity, "category", "") or "").strip()}
    for field in (
        "status",
        "profile",
        "normalized_profile",
        "material",
        "normalized_material",
        "part_position",
        "assembly_mark",
        "classification_status",
        "export_status",
    ):
        value = str(getattr(entity, field, "") or "").strip()
        if value:
            values.add(f"{field}:{value}")
    return tuple(sorted(value for value in values if value))


def _style_for(kind: NodeKind) -> str:
    return {
        NodeKind.PROJECT: "style-project",
        NodeKind.ASSEMBLY: "style-assembly",
        NodeKind.PART: "style-part",
        NodeKind.PURCHASED_ITEM: "style-purchased",
        NodeKind.FASTENER: "style-fastener",
        NodeKind.WELD: "style-weld",
        NodeKind.GROUP: "style-group",
    }.get(kind, "style-part")


def _geometry_representation(entity: Any) -> GeometryRepresentation:
    canonical = getattr(entity, "canonical_part", None)
    if canonical:
        return GeometryRepresentation.BREP
    descriptor = _mapping(getattr(entity, "geometry_descriptor", None))
    text = " ".join(str(value).lower() for value in descriptor.values() if isinstance(value, str))
    if "brep" in text or "solid" in text:
        return GeometryRepresentation.BREP
    if "analytical" in text:
        return GeometryRepresentation.ANALYTICAL
    return GeometryRepresentation.MESH_LOD


class CwsProjectSceneAdapter:
    """Build a deterministic read-only scene from a CWS ProjectModel."""

    def __init__(self) -> None:
        self.last_report: SceneBuildReport | None = None

    def build_scene(
        self,
        project: Any,
        options: SceneBuildOptions | None = None,
        *,
        geometry_catalog: Any | None = None,
        mesh_repository: Any | None = None,
    ) -> ProjectScene:
        opts = options or SceneBuildOptions()
        version = _project_version(project)
        if _major(version) not in SUPPORTED_PROJECT_SCHEMA_MAJORS:
            raise ViewerError(
                f"Project Model-schema {version!r} wordt niet ondersteund",
                code=ViewerErrorCode.PROJECT_SCHEMA_UNSUPPORTED,
                context={"supported_majors": sorted(SUPPORTED_PROJECT_SCHEMA_MAJORS)},
            )

        project_id = str(getattr(project, "project_id", "") or "").strip()
        if not project_id:
            raise ViewerError(
                "ProjectModel bevat geen project_id",
                code=ViewerErrorCode.PROJECT_SCHEMA_UNSUPPORTED,
            )
        project_name = str(getattr(project, "project_name", "") or "CWS-project")
        revision_id = str(getattr(project, "revision_content_sha256", lambda: "")() or "")
        units = str(getattr(project, "units", "mm") or "mm")

        nodes: list[SceneNode] = []
        geometry_by_hash: dict[str, GeometryResource] = {}
        warnings: list[str] = []
        zero_bounds = 0

        root_id = f"project:{project_id}"
        nodes.append(
            SceneNode(
                node_id=root_id,
                entity_id=project_id,
                source_entity_id=None,
                parent_node_id=None,
                kind=NodeKind.PROJECT,
                name=project_name,
                transform=Matrix4.identity(),
                local_bounds=BoundingBox.zero(),
                geometry_id=None,
                selectable=False,
                clippable=False,
                tags=("project", f"schema:{version}"),
                properties_ref=f"project://properties/{project_id}",
                style_id="style-project",
            )
        )

        group_ids: dict[NodeKind, str] = {}
        for kind, label in (
            (NodeKind.ASSEMBLY, "Assemblies / merken"),
            (NodeKind.PART, "Onderdelen"),
            (NodeKind.PURCHASED_ITEM, "Inkoopdelen"),
            (NodeKind.FASTENER, "Bevestigingsmiddelen"),
            (NodeKind.WELD, "Lassen"),
        ):
            node_id = f"group:{project_id}:{kind.value}"
            group_ids[kind] = node_id
            nodes.append(
                SceneNode(
                    node_id=node_id,
                    entity_id=f"viewer-group:{kind.value}",
                    source_entity_id=None,
                    parent_node_id=root_id,
                    kind=NodeKind.GROUP,
                    name=label,
                    transform=Matrix4.identity(),
                    local_bounds=BoundingBox.zero(),
                    geometry_id=None,
                    selectable=False,
                    clippable=False,
                    visible=True,
                    tags=("synthetic-group", kind.value),
                    style_id="style-group",
                )
            )

        assemblies = dict(getattr(project, "assemblies", {}) or {})
        parts = dict(getattr(project, "parts", {}) or {})
        purchased = dict(getattr(project, "purchased_items", {}) or {})
        fasteners = dict(getattr(project, "fasteners", {}) or {})
        welds = dict(getattr(project, "welds", {}) or {})

        child_parent: dict[str, str] = {}
        for assembly_id, assembly in assemblies.items():
            for child_id in getattr(assembly, "child_assembly_ids", ()) or ():
                child_parent.setdefault(str(child_id), str(assembly_id))

        loaded_geometry_ids: set[str] = set()
        proxy_geometry_ids: set[str] = set()

        def geometry_for(entity: Any) -> str | None:
            nonlocal zero_bounds
            internal_id = str(getattr(entity, "internal_id", "") or "")
            record = (
                geometry_catalog.record_for_entity(internal_id)
                if opts.prefer_source_geometry and geometry_catalog is not None
                else None
            )
            if record is not None:
                resource = geometry_by_hash.get(record.source_geometry_hash)
                if resource is None:
                    mesh = mesh_repository.get(record.geometry_id) if mesh_repository is not None else None
                    lods = ()
                    byte_length = 0
                    metadata = list(record.metadata)
                    if mesh is not None:
                        lods = (
                            MeshLod(
                                level=0,
                                content_hash=mesh.mesh_hash,
                                payload_ref=f"memory://mesh/{record.geometry_id}",
                                vertex_count=mesh.vertex_count,
                                triangle_count=mesh.triangle_count,
                                byte_length=mesh.byte_length,
                                max_error_mm=None,
                            ),
                        )
                        byte_length = mesh.byte_length
                        metadata.extend((("load_state", "ready"), ("exactness", mesh.exactness), ("provider", mesh.provider)))
                        loaded_geometry_ids.add(record.geometry_id)
                        if mesh.exactness == "display_proxy":
                            proxy_geometry_ids.add(record.geometry_id)
                    else:
                        metadata.append(("load_state", "deferred"))
                    resource = GeometryResource(
                        geometry_id=record.geometry_id,
                        representation=GeometryRepresentation.MESH_LOD,
                        content_hash=record.source_geometry_hash,
                        units=units,
                        payload_ref=f"project://source/{record.source_file_id}/{record.source_entity_id}",
                        lods=lods,
                        feature_map_ref=None,
                        byte_length=byte_length,
                        metadata=tuple(metadata),
                    )
                    geometry_by_hash[record.source_geometry_hash] = resource
                return resource.geometry_id

            digest = str(getattr(entity, "geometry_hash", "") or "").lower()
            if not opts.create_deferred_geometry or not is_sha256(digest):
                return None
            resource = geometry_by_hash.get(digest)
            if resource is None:
                resource = GeometryResource(
                    geometry_id=f"geometry:{digest}",
                    representation=_geometry_representation(entity),
                    content_hash=digest,
                    units=units,
                    payload_ref=f"project://geometry/{digest}",
                    lods=(),
                    feature_map_ref=f"project://feature-map/{getattr(entity, 'internal_id', digest)}",
                    metadata=(("load_state", "deferred"), ("source_entity_id", _source_entity_id(entity) or "")),
                )
                geometry_by_hash[digest] = resource
            return resource.geometry_id

        def append_entity(entity: Any, kind: NodeKind, parent_node_id: str, parent_global: Matrix4 | None = None) -> None:
            nonlocal zero_bounds
            internal_id = str(getattr(entity, "internal_id", "") or "").strip()
            if not internal_id:
                raise ViewerError(
                    "Projectentity zonder internal_id kan niet worden geadapteerd",
                    code=ViewerErrorCode.SCENE_REFERENCE_MISSING,
                    context={"kind": kind.value},
                )
            record = geometry_catalog.record_for_entity(internal_id) if geometry_catalog is not None else None
            mesh = mesh_repository.get(record.geometry_id) if record is not None and mesh_repository is not None else None
            bounds = mesh.bounds if mesh is not None else (record.fallback_bounds if record is not None else _entity_bounds(entity))
            assert bounds is not None
            if bounds == BoundingBox.zero():
                zero_bounds += 1
            geometry_hash = str(getattr(entity, "geometry_hash", "") or "") or None
            manufacturing_hash = str(getattr(entity, "manufacturing_hash", "") or "") or None
            if geometry_hash and not is_sha256(geometry_hash):
                warnings.append(f"{internal_id}: ongeldige geometry_hash genegeerd")
                geometry_hash = None
            if manufacturing_hash and not is_sha256(manufacturing_hash):
                warnings.append(f"{internal_id}: ongeldige manufacturing_hash genegeerd")
                manufacturing_hash = None
            global_matrix = _matrix(entity)
            transform = parent_global.inverse_rigid() @ global_matrix if parent_global is not None else global_matrix
            node = SceneNode(
                node_id=f"entity:{internal_id}",
                entity_id=internal_id,
                source_entity_id=_source_entity_id(entity),
                parent_node_id=parent_node_id,
                kind=kind,
                name=str(getattr(entity, "name", "") or internal_id),
                transform=transform,
                local_bounds=bounds,
                geometry_id=geometry_for(entity),
                selectable=True,
                clippable=kind not in {NodeKind.WELD},
                visible=True,
                tags=_entity_tags(entity, kind),
                properties_ref=f"project://properties/{internal_id}",
                geometry_hash=geometry_hash,
                manufacturing_hash=manufacturing_hash,
                style_id=_style_for(kind),
            )
            nodes.append(node)

        if opts.include_assemblies:
            for assembly_id in sorted(assemblies):
                parent_assembly_id = child_parent.get(assembly_id)
                parent_node = (
                    f"entity:{parent_assembly_id}"
                    if parent_assembly_id in assemblies
                    else group_ids[NodeKind.ASSEMBLY]
                )
                parent_global = _matrix(assemblies[parent_assembly_id]) if parent_assembly_id in assemblies else None
                append_entity(assemblies[assembly_id], NodeKind.ASSEMBLY, parent_node, parent_global)

        if opts.include_parts:
            for part_id in sorted(parts):
                part = parts[part_id]
                assembly_ids = sorted(str(value) for value in (getattr(part, "assembly_ids", ()) or ()))
                parent_node = (
                    f"entity:{assembly_ids[0]}"
                    if opts.include_assemblies and assembly_ids and assembly_ids[0] in assemblies
                    else group_ids[NodeKind.PART]
                )
                parent_global = _matrix(assemblies[assembly_ids[0]]) if opts.include_assemblies and assembly_ids and assembly_ids[0] in assemblies else None
                append_entity(part, NodeKind.PART, parent_node, parent_global)

        if opts.include_purchased_items:
            for entity_id in sorted(purchased):
                item = purchased[entity_id]
                assembly_ids = sorted(str(value) for value in (getattr(item, "assembly_ids", ()) or ()))
                parent_node = (
                    f"entity:{assembly_ids[0]}"
                    if opts.include_assemblies and assembly_ids and assembly_ids[0] in assemblies
                    else group_ids[NodeKind.PURCHASED_ITEM]
                )
                parent_global = _matrix(assemblies[assembly_ids[0]]) if opts.include_assemblies and assembly_ids and assembly_ids[0] in assemblies else None
                append_entity(item, NodeKind.PURCHASED_ITEM, parent_node, parent_global)

        if opts.include_fasteners:
            for entity_id in sorted(fasteners):
                append_entity(fasteners[entity_id], NodeKind.FASTENER, group_ids[NodeKind.FASTENER])

        if opts.include_welds:
            for entity_id in sorted(welds):
                append_entity(welds[entity_id], NodeKind.WELD, group_ids[NodeKind.WELD])

        scene = ProjectScene.create(
            project_id=project_id,
            revision_id=revision_id or None,
            models=(
                SceneModel(
                    model_id=f"model:{project_id}",
                    name=project_name,
                    source_file_id=None,
                    root_node_ids=(root_id,),
                    transform=Matrix4.identity(),
                    revision_id=revision_id or None,
                    tags=("cws-project", f"project-schema:{version}"),
                ),
            ),
            nodes=nodes,
            geometry=tuple(geometry_by_hash.values()),
            styles=_CATEGORY_STYLES,
        )
        self.last_report = SceneBuildReport(
            project_schema_version=version,
            validated_schema=version in VALIDATED_PROJECT_SCHEMA_VERSIONS,
            node_count=len(nodes),
            selectable_count=sum(1 for node in nodes if node.selectable),
            geometry_resource_count=len(geometry_by_hash),
            deferred_geometry_count=sum(1 for resource in geometry_by_hash.values() if not resource.lods),
            loaded_geometry_count=len(loaded_geometry_ids),
            proxy_geometry_count=len(proxy_geometry_ids),
            zero_bounds_count=zero_bounds,
            warnings=tuple(warnings),
        )
        return scene

    def property_snapshot(self, project: Any, entity_id: str) -> Mapping[str, Any]:
        if hasattr(project, "get_entity"):
            entity = project.get_entity(entity_id)
        else:
            entity = None
            for collection_name in ("assemblies", "parts", "purchased_items", "fasteners", "welds"):
                entity = (getattr(project, collection_name, {}) or {}).get(entity_id)
                if entity is not None:
                    break
        if entity is None:
            raise ViewerError(
                "Projectentity voor properties bestaat niet",
                code=ViewerErrorCode.NODE_NOT_FOUND,
                context={"entity_id": entity_id},
            )
        return _as_dict(entity)


__all__ = ["SceneBuildOptions", "SceneBuildReport", "CwsProjectSceneAdapter"]
