"""Deterministic, immutable indexes for :class:`ProjectScene`.

The renderer must not repeatedly walk the canonical scene graph.  This module
materialises stable lookups, hierarchy relationships, world transforms and
world-space bounds once per scene load.  It remains renderer-independent.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from cws_viewer.contracts.enums import NodeKind, SelectionLevel
from cws_viewer.contracts.scene import (
    GeometryResource,
    ProjectScene,
    SceneModel,
    SceneNode,
    StyleDefinition,
)
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import BoundingBox, Matrix4


_KIND_FOR_LEVEL: Mapping[SelectionLevel, frozenset[NodeKind]] = MappingProxyType(
    {
        SelectionLevel.MODEL: frozenset({NodeKind.MODEL}),
        SelectionLevel.ASSEMBLY: frozenset({NodeKind.ASSEMBLY}),
        SelectionLevel.PART: frozenset(
            {
                NodeKind.PART,
                NodeKind.PURCHASED_ITEM,
                NodeKind.FASTENER,
                NodeKind.WELD,
                NodeKind.REFERENCE,
            }
        ),
        SelectionLevel.FEATURE: frozenset({NodeKind.FEATURE}),
    }
)


@dataclass(frozen=True, slots=True)
class SceneIndex:
    """Precomputed read-only index for a validated scene."""

    scene: ProjectScene
    nodes_by_id: Mapping[str, SceneNode]
    models_by_id: Mapping[str, SceneModel]
    geometry_by_id: Mapping[str, GeometryResource]
    styles_by_id: Mapping[str, StyleDefinition]
    children_by_parent: Mapping[str | None, tuple[str, ...]]
    parent_by_node: Mapping[str, str | None]
    model_by_root: Mapping[str, SceneModel]
    world_transform_by_node: Mapping[str, Matrix4]
    world_bounds_by_node: Mapping[str, BoundingBox]
    renderable_node_ids: tuple[str, ...]

    @classmethod
    def build(cls, scene: ProjectScene) -> "SceneIndex":
        scene.validate()
        nodes = {node.node_id: node for node in scene.nodes}
        models = {model.model_id: model for model in scene.models}
        geometry = {item.geometry_id: item for item in scene.geometry}
        styles = {item.style_id: item for item in scene.styles}

        children: dict[str | None, list[str]] = {None: []}
        parent: dict[str, str | None] = {}
        for node in scene.nodes:
            parent[node.node_id] = node.parent_node_id
            children.setdefault(node.parent_node_id, []).append(node.node_id)
            children.setdefault(node.node_id, [])

        model_by_root: dict[str, SceneModel] = {}
        for model in scene.models:
            for root_id in model.root_node_ids:
                if root_id in model_by_root:
                    raise ViewerError(
                        "Een viewernode is root van meerdere modellen",
                        code=ViewerErrorCode.SCENE_DUPLICATE_ID,
                        context={"root_node_id": root_id},
                    )
                model_by_root[root_id] = model

        world_transforms: dict[str, Matrix4] = {}
        visiting: set[str] = set()

        def resolve_transform(node_id: str) -> Matrix4:
            if node_id in world_transforms:
                return world_transforms[node_id]
            if node_id in visiting:
                raise ViewerError(
                    "Cyclische scenehiërarchie bij world-transformberekening",
                    code=ViewerErrorCode.SCENE_CYCLE,
                    context={"node_id": node_id},
                )
            visiting.add(node_id)
            node = nodes[node_id]
            if node.parent_node_id is not None:
                transform = resolve_transform(node.parent_node_id) @ node.transform
            else:
                model = model_by_root.get(node_id)
                transform = (model.transform if model else Matrix4.identity()) @ node.transform
            world_transforms[node_id] = transform
            visiting.remove(node_id)
            return transform

        world_bounds: dict[str, BoundingBox] = {}
        renderable: list[str] = []
        for node in scene.nodes:
            transform = resolve_transform(node.node_id)
            world_bounds[node.node_id] = node.local_bounds.transformed(transform)
            if node.geometry_id is not None:
                renderable.append(node.node_id)

        return cls(
            scene=scene,
            nodes_by_id=MappingProxyType(nodes),
            models_by_id=MappingProxyType(models),
            geometry_by_id=MappingProxyType(geometry),
            styles_by_id=MappingProxyType(styles),
            children_by_parent=MappingProxyType(
                {key: tuple(value) for key, value in children.items()}
            ),
            parent_by_node=MappingProxyType(parent),
            model_by_root=MappingProxyType(model_by_root),
            world_transform_by_node=MappingProxyType(world_transforms),
            world_bounds_by_node=MappingProxyType(world_bounds),
            renderable_node_ids=tuple(renderable),
        )

    @property
    def root_node_ids(self) -> tuple[str, ...]:
        return self.children_by_parent.get(None, ())

    def node(self, node_id: str) -> SceneNode:
        try:
            return self.nodes_by_id[node_id]
        except KeyError as exc:
            raise ViewerError(
                "Viewernode bestaat niet",
                code=ViewerErrorCode.NODE_NOT_FOUND,
                context={"node_id": node_id},
            ) from exc

    def descendants(
        self,
        node_ids: Iterable[str],
        *,
        include_self: bool = True,
        renderable_only: bool = False,
    ) -> tuple[str, ...]:
        requested = tuple(dict.fromkeys(str(value) for value in node_ids))
        for node_id in requested:
            self.node(node_id)
        result: list[str] = []
        seen: set[str] = set()
        stack: list[str] = list(reversed(requested))
        while stack:
            node_id = stack.pop()
            if node_id in seen:
                continue
            seen.add(node_id)
            if (include_self or node_id not in requested) and (
                not renderable_only or self.nodes_by_id[node_id].geometry_id is not None
            ):
                result.append(node_id)
            stack.extend(reversed(self.children_by_parent.get(node_id, ())))
        return tuple(result)

    def ancestors(self, node_id: str, *, include_self: bool = False) -> tuple[str, ...]:
        self.node(node_id)
        result: list[str] = [node_id] if include_self else []
        current = self.parent_by_node[node_id]
        while current is not None:
            result.append(current)
            current = self.parent_by_node[current]
        return tuple(result)

    def selectable_node_for_level(self, node_id: str, level: SelectionLevel) -> str:
        """Promote a picked node to the nearest node matching ``level``.

        A model may be represented by a root group rather than an explicit
        ``NodeKind.MODEL`` node.  In that case the model root is returned.
        """

        requested = SelectionLevel(level)
        chain = (node_id, *self.ancestors(node_id))
        accepted = _KIND_FOR_LEVEL[requested]
        for candidate in chain:
            if self.nodes_by_id[candidate].kind in accepted:
                return candidate
        if requested == SelectionLevel.MODEL:
            for candidate in chain:
                if candidate in self.model_by_root:
                    return candidate
        return node_id

    def bounds_for(
        self,
        node_ids: Iterable[str],
        *,
        include_descendants: bool = True,
        renderable_only: bool = True,
    ) -> BoundingBox | None:
        ids = tuple(dict.fromkeys(str(value) for value in node_ids))
        if include_descendants:
            ids = self.descendants(ids, include_self=True, renderable_only=renderable_only)
        elif renderable_only:
            ids = tuple(
                node_id
                for node_id in ids
                if self.node(node_id).geometry_id is not None
            )
        if not ids:
            return None
        bounds = self.world_bounds_by_node[ids[0]]
        for node_id in ids[1:]:
            bounds = bounds.union(self.world_bounds_by_node[node_id])
        return bounds

    def scene_bounds(self, *, visible_node_ids: Iterable[str] | None = None) -> BoundingBox | None:
        ids = self.renderable_node_ids if visible_node_ids is None else tuple(visible_node_ids)
        return self.bounds_for(ids, include_descendants=False, renderable_only=True)

    def counts_by_kind(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.scene.nodes:
            counts[node.kind.value] = counts.get(node.kind.value, 0) + 1
        return dict(sorted(counts.items()))


__all__ = ["SceneIndex"]
