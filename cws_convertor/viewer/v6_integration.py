"""Controlled host bridge for the CWS Viewer V0-V6 handover.

The bridge is deliberately one-way: the authoritative Project Model produces
immutable viewer contracts. Viewer review results never release production or
replace owner manufacturing hashes.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from cws_convertor.project.canonical_rebuild import build_canonical_shape
from cws_convertor.project.model import Part, ProjectModel
from cws_convertor.project.service import ProjectSession
from cws_convertor.project.source_geometry import (
    SourceGeometryInspection,
    inspect_part_source_geometry,
)
from cws_convertor.steel_model.adapter import build_steel_model_snapshot
from cws_convertor.steel_model.contracts import SteelEntityRecord, SteelModelSnapshot
from cws_convertor.steel_model.viewer_boundary import (
    ViewerHostSnapshot,
    build_viewer_host_snapshot,
)
from cws_convertor.viewer.mesh_resources import ViewerMeshResource
from cws_viewer.contracts.enums import GeometryRepresentation, NodeKind, RenderMode
from cws_viewer.contracts.scene import (
    GeometryResource,
    MeshLod,
    ProjectScene,
    SceneModel,
    SceneNode,
    StyleDefinition,
)
from cws_viewer.contracts.geometry import MeshData
from cws_viewer.exact.catalog import build_exact_runtime
from cws_viewer.exact.model import ExactPartRuntime
from cws_viewer.exact.workbench import ExactPartWorkbenchService
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.math3d import BoundingBox, Matrix4, Rgba, Vector3


class ViewerIntegrationBlocked(RuntimeError):
    """The owner model cannot provide the requested viewer evidence safely."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class IntegratedSceneResult:
    steel_model: SteelModelSnapshot
    viewer_host: ViewerHostSnapshot
    scene: ProjectScene
    repository: MeshRepository
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.scene.project_id,
            "scene_hash": self.scene.scene_hash,
            "steel_model_snapshot_sha256": self.steel_model.snapshot_sha256,
            "viewer_host_snapshot_sha256": self.viewer_host.snapshot_sha256,
            "node_count": len(self.scene.nodes),
            "geometry_count": len(self.scene.geometry),
            "mesh_count": len(self.repository),
            "warnings": list(self.warnings),
        }


@dataclass(slots=True)
class IntegratedExactPart:
    part: Part
    source_inspection: SourceGeometryInspection
    source: ExactPartRuntime
    canonical: ExactPartRuntime | None
    service: ExactPartWorkbenchService
    canonical_warnings: tuple[str, ...] = ()

    @property
    def owner_manufacturing_hash(self) -> str:
        return self.part.manufacturing_hash

    def validate_compare(self) -> Mapping[str, Any]:
        if self.canonical is None:
            return {
                "status": "blocked",
                "blocking_codes": ["CWS-EXACT-CANONICAL-OWNER-BREP-MISSING"],
            }
        report = self.service.validate()
        return {
            "status": report.overall.value,
            "report": report.to_dict(),
            "owner_manufacturing_hash": self.owner_manufacturing_hash,
            "production_release_allowed": False,
        }

    def owner_gates(self) -> Mapping[str, Any]:
        state = dict(self.part.workbench or {})
        revision = dict(state.get("current_revision") or {})
        rebuild = dict(state.get("canonical_rebuild") or {})
        roundtrips = dict(revision.get("roundtrip_validation") or {})
        formats = dict(roundtrips.get("formats") or {})
        return {
            "viewer_review_only": True,
            "production_release_allowed": False,
            "owner_export_status": self.part.export_status,
            "owner_manufacturing_hash": self.part.manufacturing_hash,
            "owner_geometry_hash": self.part.geometry_hash,
            "owner_review_status": revision.get("review_status", "not_started"),
            "owner_canonical_rebuild_status": rebuild.get("status", "not_run"),
            "owner_roundtrip_status": roundtrips.get("status", "not_run"),
            "format_gates": formats,
        }


_STYLES = (
    StyleDefinition("integrated-project", Rgba(0.34, 0.39, 0.43, 1.0), visible=False),
    StyleDefinition("integrated-assembly", Rgba(0.22, 0.49, 0.78, 1.0)),
    StyleDefinition("integrated-part", Rgba(0.68, 0.71, 0.69, 1.0)),
    StyleDefinition("integrated-purchased", Rgba(0.39, 0.66, 0.48, 1.0)),
    StyleDefinition("integrated-fastener", Rgba(0.88, 0.64, 0.22, 1.0)),
    StyleDefinition("integrated-weld", Rgba(0.84, 0.34, 0.30, 1.0), mode=RenderMode.WIREFRAME),
    StyleDefinition("integrated-reference", Rgba(0.48, 0.52, 0.55, 1.0)),
)


def _kind(entity_type: str) -> NodeKind:
    return {
        "assembly": NodeKind.ASSEMBLY,
        "part": NodeKind.PART,
        "purchased_item": NodeKind.PURCHASED_ITEM,
        "fastener": NodeKind.FASTENER,
        "weld": NodeKind.WELD,
    }.get(entity_type, NodeKind.REFERENCE)


def _style_id(kind: NodeKind) -> str:
    return f"integrated-{kind.value.replace('_item', '')}"


def _bounds_from_properties(entity: SteelEntityRecord) -> BoundingBox:
    properties = dict(entity.display_properties)
    for key in ("bbox_mm", "bbox_sorted_mm", "dimensions_mm"):
        value = properties.get(key)
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            values = tuple(max(0.0, float(item or 0.0)) for item in value[:3])
            return BoundingBox.from_dimensions(*values)
    length = max(0.0, float(properties.get("length_mm") or 0.0))
    diameter = max(0.0, float(properties.get("diameter_mm") or 0.0))
    if length and diameter:
        return BoundingBox.from_dimensions(length, diameter, diameter)
    return BoundingBox.zero()


def _tags(entity: SteelEntityRecord) -> tuple[str, ...]:
    properties = dict(entity.display_properties)
    values = {
        entity.entity_type,
        f"status:{entity.status}",
        f"accuracy:{entity.accuracy_status.value}",
    }
    for key in (
        "assembly_mark",
        "part_position",
        "profile",
        "normalized_profile",
        "material",
        "normalized_material",
        "classification_status",
        "export_status",
        "phase",
    ):
        value = str(properties.get(key) or "").strip()
        if value:
            values.add(f"{key}:{value}")
    if entity.source.global_id:
        values.add(f"global_id:{entity.source.global_id}")
    return tuple(sorted(values))


def _mesh_contract(
    resource: ViewerMeshResource,
) -> tuple[GeometryResource, MeshData]:
    vertices = np.asarray(resource.vertices_mm, dtype=np.float64)
    triangles = np.asarray(resource.triangles, dtype=np.int32)
    source_hash = resource.source_geometry_hash or resource.geometry_content_sha256
    mesh = MeshData(
        vertices=vertices,
        triangles=triangles,
        source_geometry_hash=source_hash,
        provider="cws-convertor-owner-mesh-v1",
        exactness=resource.accuracy_status,
        metadata={
            "geometry_basis": resource.geometry_basis,
            "steel_model_id": resource.steel_model_id,
            "source_file_id": resource.source_file_id,
            "source_entity_id": resource.source_entity_id,
        },
    )
    geometry = GeometryResource(
        geometry_id=resource.viewer_geometry_id,
        representation=GeometryRepresentation.MESH_LOD,
        content_hash=resource.geometry_content_sha256,
        units="mm",
        payload_ref=f"memory://steel-model/{resource.viewer_geometry_id}",
        lods=(
            MeshLod(
                level=0,
                content_hash=mesh.mesh_hash,
                payload_ref=f"memory://mesh/{resource.viewer_geometry_id}",
                vertex_count=mesh.vertex_count,
                triangle_count=mesh.triangle_count,
                byte_length=mesh.byte_length,
                max_error_mm=None,
            ),
        ),
        byte_length=mesh.byte_length,
        metadata=(
            ("evidence", resource.accuracy_status),
            ("geometry_basis", resource.geometry_basis),
            ("owner_contract", resource.contract_version),
        ),
    )
    return geometry, mesh


def build_integrated_project_scene(
    project: ProjectModel,
    *,
    mesh_resources: Iterable[ViewerMeshResource] = (),
) -> IntegratedSceneResult:
    """Build a V0 scene solely from the authoritative SteelModel boundary."""

    steel_model = build_steel_model_snapshot(project)
    viewer_host = build_viewer_host_snapshot(steel_model)
    entities = {item.steel_model_id: item for item in steel_model.entities}
    bindings = {item.steel_model_id: item for item in viewer_host.bindings}
    warnings: list[str] = []

    parent_by_entity: dict[str, str] = {}
    for relation in steel_model.relations:
        if relation.relation_type.startswith("assembly."):
            previous = parent_by_entity.setdefault(relation.target_id, relation.source_id)
            if previous != relation.source_id:
                warnings.append(
                    f"{relation.target_id}: multiple assembly parents; {previous} retained"
                )

    geometry_by_id: dict[str, GeometryResource] = {}
    repository = MeshRepository()
    mesh_by_entity: dict[str, ViewerMeshResource] = {}
    for resource in mesh_resources:
        binding = bindings.get(resource.steel_model_id)
        if binding is None:
            raise ValueError(f"Mesh references unknown SteelModel entity {resource.steel_model_id}")
        if binding.viewer_geometry_id != resource.viewer_geometry_id:
            raise ValueError("Mesh geometry ID does not match the owner viewer binding")
        geometry, mesh = _mesh_contract(resource)
        geometry_by_id[geometry.geometry_id] = geometry
        repository.put(geometry.geometry_id, mesh)
        mesh_by_entity[resource.steel_model_id] = resource

    root_id = f"project:{steel_model.project_id}"
    nodes: list[SceneNode] = [
        SceneNode(
            node_id=root_id,
            entity_id=steel_model.project_id,
            source_entity_id=None,
            parent_node_id=None,
            kind=NodeKind.PROJECT,
            name=steel_model.project_name,
            transform=Matrix4.identity(),
            local_bounds=BoundingBox.zero(),
            geometry_id=None,
            selectable=False,
            clippable=False,
            tags=("steel-model", f"project-model:{steel_model.project_model_schema}"),
            style_id="integrated-project",
        )
    ]
    for entity_id in sorted(entities):
        entity = entities[entity_id]
        binding = bindings[entity_id]
        parent_id = parent_by_entity.get(entity_id)
        parent_node = bindings[parent_id].viewer_node_id if parent_id in bindings else root_id
        transform = entity.local_transform if parent_id in entities else entity.global_transform
        mesh_resource = mesh_by_entity.get(entity_id)
        geometry_id = mesh_resource.viewer_geometry_id if mesh_resource is not None else None
        bounds = (
            repository.get(geometry_id).bounds
            if geometry_id is not None and repository.get(geometry_id) is not None
            else _bounds_from_properties(entity)
        )
        assert bounds is not None
        if binding.canonical_geometry_hash != entity.geometry_hash:
            raise ValueError("Viewer binding geometry hash drifted from SteelModel")
        if binding.manufacturing_hash != entity.manufacturing_hash:
            raise ValueError("Viewer binding manufacturing hash drifted from SteelModel")
        nodes.append(
            SceneNode(
                node_id=binding.viewer_node_id,
                entity_id=entity.steel_model_id,
                source_entity_id=entity.source.source_entity_id or None,
                parent_node_id=parent_node,
                kind=_kind(entity.entity_type),
                name=entity.name or entity.steel_model_id,
                transform=Matrix4(tuple(transform)),
                local_bounds=bounds,
                geometry_id=geometry_id,
                selectable=True,
                clippable=entity.entity_type != "weld",
                tags=_tags(entity),
                properties_ref=f"steel-model://properties/{entity.steel_model_id}",
                geometry_hash=entity.geometry_hash or None,
                manufacturing_hash=entity.manufacturing_hash or None,
                style_id=_style_id(_kind(entity.entity_type)),
            )
        )

    scene = ProjectScene.create(
        project_id=steel_model.project_id,
        revision_id=steel_model.project_semantic_sha256,
        models=(
            SceneModel(
                model_id=f"steel-model:{steel_model.project_id}",
                name=steel_model.project_name,
                source_file_id=None,
                root_node_ids=(root_id,),
                revision_id=steel_model.project_semantic_sha256,
                tags=("authoritative-steel-model",),
            ),
        ),
        nodes=nodes,
        geometry=geometry_by_id.values(),
        styles=_STYLES,
    )
    return IntegratedSceneResult(
        steel_model=steel_model,
        viewer_host=viewer_host,
        scene=scene,
        repository=repository,
        warnings=tuple(warnings),
    )


def _source_runtime(
    part: Part,
    inspection: SourceGeometryInspection,
    source_sha256: str,
) -> ExactPartRuntime:
    if inspection.geometry_kind != "native_brep" or inspection.native_shape is None:
        raise ViewerIntegrationBlocked(
            "Exact Part Workbench requires a verified part-scoped source BREP",
            code="CWS-EXACT-SOURCE-BREP-UNAVAILABLE",
        )
    runtime = build_exact_runtime(
        inspection.native_shape,
        part_id=part.internal_id,
        source_name=f"owner-source:{part.source_identity.source_entity_id}",
    )
    runtime.snapshot = replace(runtime.snapshot, source_sha256=source_sha256)
    return runtime


def build_integrated_exact_part(
    session: ProjectSession,
    part_id: str,
) -> IntegratedExactPart:
    """Build exact review runtimes from owner source resolution and rebuild."""

    part = session.project.parts.get(part_id)
    if part is None:
        raise KeyError(part_id)
    source_id = part.source_identity.source_file_id
    source = session.project.sources.get(source_id)
    if source is None:
        raise ViewerIntegrationBlocked(
            "Part source record is missing",
            code="CWS-EXACT-SOURCE-RECORD-MISSING",
        )
    source_path = session.resolve_source_path(source_id)
    inspection = inspect_part_source_geometry(part, source, source_path)
    source_runtime = _source_runtime(part, inspection, source.sha256)

    canonical_runtime: ExactPartRuntime | None = None
    canonical_warnings: tuple[str, ...] = ()
    try:
        canonical_shape, warnings, _payload = build_canonical_shape(part)
        canonical_runtime = build_exact_runtime(
            canonical_shape,
            part_id=part.internal_id,
            source_name="owner-canonical-rebuild",
        )
        canonical_warnings = tuple(warnings)
    except Exception as exc:
        canonical_warnings = (f"{type(exc).__name__}: {exc}",)

    service = ExactPartWorkbenchService(
        source_runtime,
        canonical_runtime,
        owner_manufacturing_hash=part.manufacturing_hash,
    )
    return IntegratedExactPart(
        part=part,
        source_inspection=inspection,
        source=source_runtime,
        canonical=canonical_runtime,
        service=service,
        canonical_warnings=canonical_warnings,
    )


__all__ = [
    "IntegratedExactPart",
    "IntegratedSceneResult",
    "ViewerIntegrationBlocked",
    "build_integrated_exact_part",
    "build_integrated_project_scene",
]
