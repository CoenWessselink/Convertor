"""Semantic viewer layers derived from the canonical scene graph.

This is a viewer presentation layer, not a second BIM/CAD layer truth. Source
layer names can be added through node tags when importers expose them; otherwise
CWS derives useful layers from canonical kind/material/profile/status tags.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable

from cws_viewer.core.scene_index import SceneIndex


@dataclass(frozen=True, slots=True)
class ViewerLayer:
    layer_id: str
    label: str
    category: str
    node_ids: tuple[str, ...]


class LayerCatalog:
    def __init__(self, layers: Iterable[ViewerLayer]) -> None:
        self.layers = tuple(layers)
        self.by_id = {layer.layer_id: layer for layer in self.layers}

    @classmethod
    def from_index(cls, index: SceneIndex) -> "LayerCatalog":
        buckets: dict[tuple[str, str], set[str]] = defaultdict(set)
        accepted_prefixes = {
            "material": "Materiaal",
            "normalized_material": "Materiaal",
            "profile": "Profiel",
            "normalized_profile": "Profiel",
            "status": "Status",
            "classification_status": "Classificatie",
            "assembly_mark": "Assembly",
            "layer": "Bronlaag",
            "source_layer": "Bronlaag",
        }
        for node in index.scene.nodes:
            if not node.selectable:
                continue
            buckets[("Type", node.kind.value)].add(node.node_id)
            for tag in node.tags:
                if ":" not in tag:
                    continue
                prefix, value = tag.split(":", 1)
                category = accepted_prefixes.get(prefix)
                if category and value:
                    buckets[(category, value)].add(node.node_id)
        layers = []
        for (category, value), ids in sorted(buckets.items(), key=lambda item: (item[0][0], item[0][1].casefold())):
            layer_id = f"{category.casefold()}::{value}".replace(" ", "_")
            layers.append(ViewerLayer(layer_id, value, category, tuple(sorted(ids))))
        return cls(layers)

    def category_names(self) -> tuple[str, ...]:
        return tuple(sorted({layer.category for layer in self.layers}))

    def layers_for_category(self, category: str) -> tuple[ViewerLayer, ...]:
        return tuple(layer for layer in self.layers if layer.category == category)


__all__ = ["ViewerLayer", "LayerCatalog"]
