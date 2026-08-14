"""Deterministic synthetic CWS project scenes for Viewer V2."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Iterable

from cws_viewer.contracts.enums import GeometryRepresentation, NodeKind, RenderMode
from cws_viewer.contracts.scene import (
    GeometryResource,
    ProjectScene,
    SceneModel,
    SceneNode,
    StyleDefinition,
)
from cws_viewer.math3d import BoundingBox, Matrix4, Rgba, Vector3


def _sha(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _geometry_resource(name: str, size: Vector3) -> GeometryResource:
    payload = {
        "fixture": "cws-viewer-v2-display-box",
        "name": name,
        "size": size.to_tuple(),
    }
    digest = _sha(payload)
    return GeometryResource(
        geometry_id=f"geometry:v2:{name}",
        representation=GeometryRepresentation.MESH_LOD,
        content_hash=digest,
        units="mm",
        payload_ref=f"memory://viewer-v2/{name}.box.json",
        byte_length=len(json.dumps(payload, sort_keys=True).encode("utf-8")),
        metadata=(
            ("primitive", "box"),
            ("size_x", f"{size.x:.9g}"),
            ("size_y", f"{size.y:.9g}"),
            ("size_z", f"{size.z:.9g}"),
            ("display_only", "true"),
        ),
    )


def _styles() -> tuple[StyleDefinition, ...]:
    return (
        StyleDefinition("style:validated", Rgba(0.20, 0.62, 0.88, 1.0)),
        StyleDefinition("style:review", Rgba(0.96, 0.60, 0.18, 1.0)),
        StyleDefinition("style:blocked", Rgba(0.88, 0.25, 0.24, 1.0)),
        StyleDefinition("style:purchased", Rgba(0.52, 0.60, 0.68, 1.0)),
        StyleDefinition("style:fastener", Rgba(0.94, 0.78, 0.24, 1.0)),
        StyleDefinition("style:weld", Rgba(0.88, 0.36, 0.58, 1.0)),
        StyleDefinition(
            "style:reference",
            Rgba(0.42, 0.50, 0.58, 0.55),
            mode=RenderMode.SHADED_EDGES,
        ),
    )


_KIND_GEOMETRY: dict[NodeKind, tuple[str, Vector3]] = {
    NodeKind.PART: ("part", Vector3(80.0, 16.0, 12.0)),
    NodeKind.PURCHASED_ITEM: ("purchased", Vector3(34.0, 28.0, 18.0)),
    NodeKind.FASTENER: ("fastener", Vector3(8.0, 8.0, 28.0)),
    NodeKind.WELD: ("weld", Vector3(26.0, 5.0, 5.0)),
    NodeKind.REFERENCE: ("reference", Vector3(70.0, 46.0, 3.0)),
}


def _kind_for(index: int) -> NodeKind:
    bucket = index % 100
    if bucket < 80:
        return NodeKind.PART
    if bucket < 90:
        return NodeKind.PURCHASED_ITEM
    if bucket < 95:
        return NodeKind.FASTENER
    if bucket < 98:
        return NodeKind.WELD
    return NodeKind.REFERENCE


def _style_for(kind: NodeKind, index: int) -> str:
    if kind == NodeKind.PURCHASED_ITEM:
        return "style:purchased"
    if kind == NodeKind.FASTENER:
        return "style:fastener"
    if kind == NodeKind.WELD:
        return "style:weld"
    if kind == NodeKind.REFERENCE:
        return "style:reference"
    status = index % 20
    if status == 0:
        return "style:blocked"
    if status < 4:
        return "style:review"
    return "style:validated"


def build_synthetic_product_scene(
    renderable_count: int = 10_000,
    *,
    parts_per_assembly: int = 100,
    revision_id: str = "V2-A",
    name_suffix: str = "",
) -> ProjectScene:
    """Build a stable assembly/part product scene with ``renderable_count`` boxes."""

    if renderable_count <= 0:
        raise ValueError("renderable_count moet positief zijn")
    if parts_per_assembly <= 0:
        raise ValueError("parts_per_assembly moet positief zijn")

    geometry = tuple(
        _geometry_resource(name, size)
        for name, size in dict(_KIND_GEOMETRY.values()).items()
    )
    geometry_by_kind = {
        kind: (f"geometry:v2:{name}", size)
        for kind, (name, size) in _KIND_GEOMETRY.items()
    }

    root_id = "node:project:synthetic-v2"
    nodes: list[SceneNode] = [
        SceneNode(
            node_id=root_id,
            entity_id="project:synthetic-v2",
            source_entity_id=None,
            parent_node_id=None,
            kind=NodeKind.PROJECT,
            name=f"CWS Viewer V2 synthetisch project{name_suffix}",
            transform=Matrix4.identity(),
            local_bounds=BoundingBox.zero(),
            geometry_id=None,
            selectable=False,
            tags=("fixture", "viewer-v2"),
        )
    ]

    assembly_count = int(math.ceil(renderable_count / parts_per_assembly))
    for assembly_index in range(assembly_count):
        assembly_id = f"node:assembly:{assembly_index:04d}"
        nodes.append(
            SceneNode(
                node_id=assembly_id,
                entity_id=f"assembly:M{assembly_index + 1:04d}",
                source_entity_id=f"synthetic-assembly-{assembly_index:04d}",
                parent_node_id=root_id,
                kind=NodeKind.ASSEMBLY,
                name=f"M{assembly_index + 1:04d}",
                transform=Matrix4.identity(),
                local_bounds=BoundingBox.zero(),
                geometry_id=None,
                selectable=True,
                tags=("assembly", "synthetic"),
            )
        )

    spacing = Vector3(105.0, 58.0, 44.0)
    local_columns = max(1, int(math.ceil(math.sqrt(parts_per_assembly))))
    local_rows = max(1, int(math.ceil(parts_per_assembly / local_columns)))
    assembly_columns = max(1, int(math.ceil(math.sqrt(assembly_count))))
    assembly_gap = Vector3(spacing.x * 2.0, spacing.y * 2.0, spacing.z * 2.0)
    for index in range(renderable_count):
        kind = _kind_for(index)
        geometry_id, size = geometry_by_kind[kind]
        assembly_index = index // parts_per_assembly
        local_index = index % parts_per_assembly
        local_column = local_index % local_columns
        local_row = local_index // local_columns
        assembly_column = assembly_index % assembly_columns
        assembly_row = assembly_index // assembly_columns
        position = Vector3(
            assembly_column * (local_columns * spacing.x + assembly_gap.x)
            + local_column * spacing.x,
            assembly_row * (local_rows * spacing.y + assembly_gap.y)
            + local_row * spacing.y,
            0.0,
        )
        node_id = f"node:item:{index:06d}"
        status = "blocked" if index % 20 == 0 else "review" if index % 20 < 4 else "validated"
        geometry_hash = _sha({"geometry": geometry_id, "fixture_index_mod": index % 7})
        manufacturing_hash = _sha(
            {
                "geometry_hash": geometry_hash,
                "material": "S355JR" if kind == NodeKind.PART else "CATALOG",
                "kind": kind.value,
            }
        )
        half = size * 0.5
        nodes.append(
            SceneNode(
                node_id=node_id,
                entity_id=f"{kind.value}:synthetic:{index:06d}",
                source_entity_id=f"source#{index + 1}",
                parent_node_id=f"node:assembly:{assembly_index:04d}",
                kind=kind,
                name=f"{kind.value.upper()}-{index + 1:06d}{name_suffix}",
                transform=Matrix4.translation(position),
                local_bounds=BoundingBox(-half, half),
                geometry_id=geometry_id,
                selectable=True,
                clippable=True,
                visible=True,
                tags=(
                    "synthetic",
                    f"status:{status}",
                    f"assembly:M{assembly_index + 1:04d}",
                ),
                properties_ref=f"memory://viewer-v2/properties/{node_id}.json",
                geometry_hash=geometry_hash,
                manufacturing_hash=manufacturing_hash,
                style_id=_style_for(kind, index),
            )
        )

    return ProjectScene.create(
        project_id="project:synthetic-v2",
        revision_id=revision_id,
        models=(
            SceneModel(
                model_id="model:synthetic-v2",
                name="Synthetisch totaalmodel",
                source_file_id="source:synthetic-v2",
                root_node_ids=(root_id,),
                revision_id=revision_id,
                tags=("synthetic", "viewer-v2"),
            ),
        ),
        nodes=nodes,
        geometry=geometry,
        styles=_styles(),
    )


def stable_sample_node_ids(
    renderable_count: int,
    *,
    sample_count: int = 25,
) -> tuple[str, ...]:
    if renderable_count <= 0:
        raise ValueError("renderable_count moet positief zijn")
    count = max(1, min(sample_count, renderable_count))
    if count == 1:
        indices = (renderable_count // 2,)
    else:
        indices = tuple(
            sorted(
                {
                    int(round(step * (renderable_count - 1) / (count - 1)))
                    for step in range(count)
                }
            )
        )
    return tuple(f"node:item:{index:06d}" for index in indices)


__all__ = ["build_synthetic_product_scene", "stable_sample_node_ids"]
