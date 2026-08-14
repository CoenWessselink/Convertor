"""Validated read state shared by the project UI and a future renderer."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping

from cws_convertor.steel_model.contracts import (
    AccuracyStatus,
    SteelEntityRecord,
    SteelModelSnapshot,
    SteelValidationRecord,
)
from cws_convertor.steel_model.viewer_boundary import (
    ViewerEntityBinding,
    ViewerHandshake,
    ViewerHostSnapshot,
    validate_viewer_handshake,
)
from .mesh_resources import ViewerMeshResource


ACCURACY_LABELS: Mapping[AccuracyStatus, str] = {
    AccuracyStatus.EXACT: "Exact",
    AccuracyStatus.TOLERANCE_VERIFIED: "Binnen tolerantie",
    AccuracyStatus.APPROXIMATE: "Benadering",
    AccuracyStatus.MANUAL_VALIDATION_REQUIRED: "Handmatige validatie vereist",
    AccuracyStatus.NOT_APPLICABLE: "Niet van toepassing",
}


@dataclass(frozen=True, slots=True)
class AccuracySummary:
    exact: int
    tolerance_verified: int
    approximate: int
    manual_validation_required: int
    not_applicable: int

    @property
    def geometry_total(self) -> int:
        return self.exact + self.tolerance_verified + self.approximate + self.manual_validation_required

    @property
    def review_count(self) -> int:
        return self.approximate + self.manual_validation_required

    def to_dict(self) -> dict[str, int]:
        return {
            "exact": self.exact,
            "tolerance_verified": self.tolerance_verified,
            "approximate": self.approximate,
            "manual_validation_required": self.manual_validation_required,
            "not_applicable": self.not_applicable,
            "geometry_total": self.geometry_total,
            "review_count": self.review_count,
        }


@dataclass(frozen=True, slots=True)
class ViewerTreeNode:
    node_id: str
    label: str
    steel_model_id: str = ""
    entity_type: str = ""
    accuracy_status: str = "not_applicable"
    children: tuple["ViewerTreeNode", ...] = ()


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value


class ViewerWorkspaceState:
    """One verified source/model/viewer projection with synchronized selection."""

    def __init__(
        self,
        steel_model: SteelModelSnapshot,
        viewer_host: ViewerHostSnapshot,
    ) -> None:
        if steel_model.project_id != viewer_host.project_id:
            raise ValueError("Viewer host belongs to another project")
        if steel_model.snapshot_sha256 != viewer_host.steel_model_snapshot_sha256:
            raise ValueError("Viewer host does not reference the loaded SteelModel snapshot")

        self.steel_model = steel_model
        self.viewer_host = viewer_host
        self._entities = {item.steel_model_id: item for item in steel_model.entities}
        self._sources = {item.source_id: item for item in steel_model.sources}
        self._bindings = {item.steel_model_id: item for item in viewer_host.bindings}
        self._model_id_by_node = {
            item.viewer_node_id: item.steel_model_id for item in viewer_host.bindings
        }
        if set(self._entities) != set(self._bindings):
            missing = sorted(set(self._entities) - set(self._bindings))
            unexpected = sorted(set(self._bindings) - set(self._entities))
            raise ValueError(
                "Viewer bindings do not cover SteelModel entities: "
                f"missing={missing[:5]!r}, unexpected={unexpected[:5]!r}"
            )
        for steel_model_id, binding in self._bindings.items():
            entity = self._entities[steel_model_id]
            if binding.accuracy_status != entity.accuracy_status.value:
                raise ValueError(f"Viewer accuracy status mismatch for {steel_model_id}")
            if binding.source_file_id != entity.source.source_file_id:
                raise ValueError(f"Viewer source binding mismatch for {steel_model_id}")
            if binding.source_entity_id != entity.source.source_entity_id:
                raise ValueError(f"Viewer source entity mismatch for {steel_model_id}")
            if binding.canonical_geometry_hash != entity.geometry_hash:
                raise ValueError(f"Viewer geometry hash mismatch for {steel_model_id}")

        self._selected_id = ""
        self._mesh_resources: dict[str, ViewerMeshResource] = {}
        self._handshake: ViewerHandshake | None = None
        self._handshake_report: dict[str, Any] = {
            "compatible": False,
            "component_name": "",
            "component_version": "",
            "complete": False,
            "missing_core_capabilities": list(viewer_host.required_capabilities),
            "missing_capabilities": list(viewer_host.required_capabilities),
            "errors": ["viewer component not attached"],
        }

    @property
    def selected_id(self) -> str:
        return self._selected_id

    @property
    def selected_entity(self) -> SteelEntityRecord | None:
        return self._entities.get(self._selected_id)

    @property
    def selected_binding(self) -> ViewerEntityBinding | None:
        return self._bindings.get(self._selected_id)

    @property
    def renderer_compatible(self) -> bool:
        return bool(self._handshake_report.get("compatible"))

    @property
    def handshake_report(self) -> dict[str, Any]:
        return _plain_json(self._handshake_report)

    def register_handshake(self, handshake: ViewerHandshake) -> dict[str, Any]:
        report = validate_viewer_handshake(handshake)
        self._handshake = handshake
        self._handshake_report = report
        return self.handshake_report

    def capability_available(self, capability: str) -> bool:
        return bool(
            self.renderer_compatible
            and self._handshake is not None
            and capability in self._handshake.capabilities
        )

    def select(self, steel_model_id: str) -> dict[str, Any]:
        if steel_model_id and steel_model_id not in self._entities:
            raise KeyError(f"Unknown SteelModel entity {steel_model_id!r}")
        self._selected_id = steel_model_id
        return self.selection_payload()

    def select_viewer_node(self, viewer_node_id: str) -> dict[str, Any]:
        try:
            steel_model_id = self._model_id_by_node[viewer_node_id]
        except KeyError as exc:
            raise KeyError(f"Unknown viewer node {viewer_node_id!r}") from exc
        return self.select(steel_model_id)

    def entity(self, steel_model_id: str) -> SteelEntityRecord | None:
        return self._entities.get(steel_model_id)

    def binding(self, steel_model_id: str) -> ViewerEntityBinding | None:
        return self._bindings.get(steel_model_id)

    def mesh_resource(self, steel_model_id: str) -> ViewerMeshResource | None:
        return self._mesh_resources.get(steel_model_id)

    def attach_mesh_resource(self, resource: ViewerMeshResource) -> dict[str, Any]:
        """Validate and bind one lazily resolved mesh to the active host."""

        return self.attach_mesh_resources((resource,))

    def attach_mesh_resources(
        self,
        resources: Iterable[ViewerMeshResource],
    ) -> dict[str, Any]:
        """Atomically bind one or more independently verified mesh resources."""

        values = tuple(resources)
        if not values:
            raise ValueError("Viewer mesh patch contains no resources")
        if len({item.steel_model_id for item in values}) != len(values):
            raise ValueError("Viewer mesh patch contains duplicate SteelModel IDs")
        for resource in values:
            self._validate_mesh_resource(resource)

        previous_host_sha256 = self.viewer_host.snapshot_sha256
        replacements = {
            resource.steel_model_id: replace(
                self._bindings[resource.steel_model_id],
                viewer_geometry_content_sha256=resource.geometry_content_sha256,
            )
            for resource in values
        }
        bindings = tuple(
            replacements.get(item.steel_model_id, item)
            for item in self.viewer_host.bindings
        )
        self.viewer_host = ViewerHostSnapshot(
            project_id=self.viewer_host.project_id,
            steel_model_snapshot_sha256=self.viewer_host.steel_model_snapshot_sha256,
            bindings=bindings,
            contract_version=self.viewer_host.contract_version,
            steel_model_schema_version=self.viewer_host.steel_model_schema_version,
            required_capabilities=self.viewer_host.required_capabilities,
        )
        self._bindings.update(replacements)
        self._mesh_resources.update(
            {resource.steel_model_id: resource for resource in values}
        )
        return {
            "contract_version": self.viewer_host.contract_version,
            "project_id": self.steel_model.project_id,
            "steel_model_snapshot_sha256": self.steel_model.snapshot_sha256,
            "previous_viewer_host_snapshot_sha256": previous_host_sha256,
            "viewer_host_snapshot_sha256": self.viewer_host.snapshot_sha256,
            "viewer_host": self.viewer_host.to_dict(),
            "entities": [
                self._entities[resource.steel_model_id].to_dict()
                for resource in values
            ],
            "resources": [resource.to_dict() for resource in values],
        }

    def _validate_mesh_resource(self, resource: ViewerMeshResource) -> None:
        if resource.project_id != self.steel_model.project_id:
            raise ValueError("Viewer mesh belongs to another project")
        entity = self._entities.get(resource.steel_model_id)
        binding = self._bindings.get(resource.steel_model_id)
        if entity is None or binding is None:
            raise ValueError("Viewer mesh refers to an unknown SteelModel entity")
        if resource.viewer_geometry_id != binding.viewer_geometry_id:
            raise ValueError("Viewer mesh geometry ID does not match its binding")
        if resource.source_file_id != binding.source_file_id:
            raise ValueError("Viewer mesh source file does not match its binding")
        if resource.source_entity_id != binding.source_entity_id:
            raise ValueError("Viewer mesh source entity does not match its binding")
        if resource.source_sha256 != entity.source.source_sha256:
            raise ValueError("Viewer mesh source hash does not match SteelModel trace")
        if resource.accuracy_status != entity.accuracy_status.value:
            raise ValueError("Viewer mesh accuracy does not match SteelModel state")

    def accuracy_summary(self) -> AccuracySummary:
        counts = Counter(item.accuracy_status for item in self._entities.values())
        return AccuracySummary(
            exact=counts[AccuracyStatus.EXACT],
            tolerance_verified=counts[AccuracyStatus.TOLERANCE_VERIFIED],
            approximate=counts[AccuracyStatus.APPROXIMATE],
            manual_validation_required=counts[AccuracyStatus.MANUAL_VALIDATION_REQUIRED],
            not_applicable=counts[AccuracyStatus.NOT_APPLICABLE],
        )

    def issues(
        self,
        *,
        steel_model_id: str | None = None,
        unresolved_only: bool = True,
    ) -> tuple[SteelValidationRecord, ...]:
        target = self._selected_id if steel_model_id is None else steel_model_id
        values = self.steel_model.validation
        if target:
            entity = self._entities.get(target)
            source_id = entity.source.source_file_id if entity else ""
            values = tuple(
                item
                for item in values
                if item.steel_model_id in {"", target, source_id}
            )
        if unresolved_only:
            values = tuple(item for item in values if not item.resolved)
        return tuple(values)

    def selection_payload(self) -> dict[str, Any]:
        entity = self.selected_entity
        binding = self.selected_binding
        if entity is None or binding is None:
            return {}
        source = self._sources.get(entity.source.source_file_id)
        return {
            "steel_model_id": entity.steel_model_id,
            "viewer_node_id": binding.viewer_node_id,
            "viewer_geometry_id": binding.viewer_geometry_id,
            "viewer_geometry_content_sha256": binding.viewer_geometry_content_sha256,
            "entity_type": entity.entity_type,
            "name": entity.name,
            "category": entity.category,
            "status": entity.status,
            "accuracy_status": entity.accuracy_status.value,
            "accuracy_label": ACCURACY_LABELS[entity.accuracy_status],
            "geometry_kind": entity.geometry_kind,
            "geometry_hash": entity.geometry_hash,
            "manufacturing_hash": entity.manufacturing_hash,
            "source_file_id": entity.source.source_file_id,
            "source_file_name": source.file_name if source else "",
            "source_format": entity.source.source_format,
            "source_sha256": entity.source.source_sha256,
            "source_entity_id": entity.source.source_entity_id,
            "global_id": entity.source.global_id,
            "local_transform": list(entity.local_transform),
            "global_transform": list(entity.global_transform),
            "display_properties": _plain_json(entity.display_properties),
            "validation_issue_codes": list(entity.validation_issue_codes),
        }

    def scene_payload(self) -> dict[str, Any]:
        """Return the exact versioned snapshots a renderer must consume."""

        return {
            "contract_version": self.viewer_host.contract_version,
            "project_id": self.steel_model.project_id,
            "steel_model_snapshot_sha256": self.steel_model.snapshot_sha256,
            "viewer_host_snapshot_sha256": self.viewer_host.snapshot_sha256,
            "steel_model": self.steel_model.to_dict(),
            "viewer_host": self.viewer_host.to_dict(),
            "mesh_resources": [
                self._mesh_resources[item].to_dict()
                for item in sorted(self._mesh_resources)
            ],
        }

    def search(self, query: str = "", *, entity_type: str = "") -> tuple[SteelEntityRecord, ...]:
        needle = query.strip().casefold()
        values: list[SteelEntityRecord] = []
        for entity in self.steel_model.entities:
            if entity_type and entity.entity_type != entity_type:
                continue
            searchable = " ".join(
                (
                    entity.steel_model_id,
                    entity.entity_type,
                    entity.name,
                    entity.category,
                    entity.source.source_entity_id,
                    str(entity.display_properties.get("part_position") or ""),
                    str(entity.display_properties.get("assembly_mark") or ""),
                    str(entity.display_properties.get("profile") or ""),
                    str(entity.display_properties.get("material") or ""),
                )
            ).casefold()
            if not needle or needle in searchable:
                values.append(entity)
        return tuple(values)

    def tree(self, query: str = "") -> tuple[ViewerTreeNode, ...]:
        visible = {item.steel_model_id for item in self.search(query)}
        if query:
            parent_by_child: dict[str, set[str]] = defaultdict(set)
            for relation in self.steel_model.relations:
                if relation.relation_type.startswith("assembly."):
                    parent_by_child[relation.target_id].add(relation.source_id)
            pending = list(visible)
            while pending:
                child_id = pending.pop()
                for parent_id in parent_by_child.get(child_id, ()):
                    if parent_id not in visible:
                        visible.add(parent_id)
                        pending.append(parent_id)
        by_source: dict[str, set[str]] = defaultdict(set)
        for entity in self.steel_model.entities:
            if entity.steel_model_id in visible:
                by_source[entity.source.source_file_id].add(entity.steel_model_id)

        nodes: list[ViewerTreeNode] = []
        for source in self.steel_model.sources:
            members = by_source.pop(source.source_id, set())
            if query and not members and query.casefold() not in source.file_name.casefold():
                continue
            children = self._entity_tree(members)
            nodes.append(
                ViewerTreeNode(
                    node_id=f"source:{source.source_id}",
                    label=f"{source.file_name} [{source.source_format}]",
                    children=children,
                )
            )
        internal = by_source.pop("", set())
        for members in by_source.values():
            internal.update(members)
        if internal:
            nodes.append(
                ViewerTreeNode(
                    node_id="source:internal",
                    label="Interne projectobjecten",
                    children=self._entity_tree(internal),
                )
            )
        return tuple(nodes)

    def visual_manifest(self) -> dict[str, Any]:
        summary = self.accuracy_summary()
        return {
            "project_id": self.steel_model.project_id,
            "steel_model_snapshot_sha256": self.steel_model.snapshot_sha256,
            "viewer_host_snapshot_sha256": self.viewer_host.snapshot_sha256,
            "source_count": len(self.steel_model.sources),
            "entity_count": len(self.steel_model.entities),
            "binding_count": len(self.viewer_host.bindings),
            "mesh_resource_count": len(self._mesh_resources),
            "mesh_vertex_count": sum(
                len(item.vertices_mm) for item in self._mesh_resources.values()
            ),
            "mesh_triangle_count": sum(
                len(item.triangles) for item in self._mesh_resources.values()
            ),
            "accuracy": summary.to_dict(),
            "selected": self.selection_payload(),
            "renderer": self.handshake_report,
        }

    def _entity_tree(self, member_ids: set[str]) -> tuple[ViewerTreeNode, ...]:
        children_by_parent: dict[str, list[str]] = defaultdict(list)
        child_ids: set[str] = set()
        for relation in self.steel_model.relations:
            if not relation.relation_type.startswith("assembly."):
                continue
            if relation.source_id in member_ids and relation.target_id in member_ids:
                children_by_parent[relation.source_id].append(relation.target_id)
                child_ids.add(relation.target_id)

        roots = sorted(
            member_ids - child_ids,
            key=lambda item: self._entity_sort_key(self._entities[item]),
        )
        seen: set[str] = set()

        def build(steel_model_id: str, ancestors: frozenset[str]) -> ViewerTreeNode:
            entity = self._entities[steel_model_id]
            if steel_model_id in ancestors:
                return self._tree_node(entity, ())
            descendants = tuple(
                build(child_id, ancestors | {steel_model_id})
                for child_id in sorted(
                    children_by_parent.get(steel_model_id, ()),
                    key=lambda item: self._entity_sort_key(self._entities[item]),
                )
                if child_id not in seen
            )
            seen.add(steel_model_id)
            return self._tree_node(entity, descendants)

        result = [build(item, frozenset()) for item in roots if item not in seen]
        for steel_model_id in sorted(member_ids - seen):
            result.append(build(steel_model_id, frozenset()))
        return tuple(result)

    @staticmethod
    def _entity_sort_key(entity: SteelEntityRecord) -> tuple[str, str, str]:
        properties = entity.display_properties
        mark = str(
            properties.get("assembly_mark")
            or properties.get("part_position")
            or entity.name
            or entity.steel_model_id
        )
        return (entity.entity_type, mark.casefold(), entity.steel_model_id)

    @staticmethod
    def _tree_node(
        entity: SteelEntityRecord,
        children: Iterable[ViewerTreeNode],
    ) -> ViewerTreeNode:
        properties = entity.display_properties
        identifier = str(
            properties.get("assembly_mark")
            or properties.get("part_position")
            or entity.name
            or entity.steel_model_id
        )
        profile = str(properties.get("profile") or "")
        label = f"{identifier} - {profile}" if profile and profile not in identifier else identifier
        return ViewerTreeNode(
            node_id=f"entity:{entity.steel_model_id}",
            label=label,
            steel_model_id=entity.steel_model_id,
            entity_type=entity.entity_type,
            accuracy_status=entity.accuracy_status.value,
            children=tuple(children),
        )


__all__ = [
    "ACCURACY_LABELS",
    "AccuracySummary",
    "ViewerTreeNode",
    "ViewerWorkspaceState",
]
