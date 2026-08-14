"""Deterministic synthetic fixtures shared by both V1 render backends."""
from __future__ import annotations

import hashlib
import json
import math

from cws_viewer.math3d import BoundingBox, Vector3
from cws_viewer.technology.contracts import TechnologyInstance, TechnologyScene


def build_box_grid_scene(
    node_count: int,
    *,
    box_size: Vector3 = Vector3(10.0, 6.0, 4.0),
    spacing: Vector3 = Vector3(14.0, 10.0, 8.0),
    layers: int = 1,
) -> TechnologyScene:
    """Build a stable grid scene with one shared geometry and N instances.

    V1 intentionally uses the same simple box resource for both backends.  The
    goal is to measure renderer/scene overhead, picking and clipping, not CAD
    tessellation quality. Exact BREP fixtures enter in V6.
    """

    if node_count <= 0:
        raise ValueError("node_count moet groter dan nul zijn")
    if layers <= 0:
        raise ValueError("layers moet groter dan nul zijn")

    per_layer = int(math.ceil(node_count / layers))
    columns = int(math.ceil(math.sqrt(per_layer)))
    rows = int(math.ceil(per_layer / columns))
    instances: list[TechnologyInstance] = []
    for index in range(node_count):
        layer = index // per_layer
        local_index = index % per_layer
        column = local_index % columns
        row = local_index // columns
        center = Vector3(
            column * spacing.x + box_size.x * 0.5,
            row * spacing.y + box_size.y * 0.5,
            layer * spacing.z + box_size.z * 0.5,
        )
        instances.append(
            TechnologyInstance(node_id=f"node:synthetic:{index:06d}", center=center)
        )

    max_center = Vector3(
        max(instance.center.x for instance in instances),
        max(instance.center.y for instance in instances),
        max(instance.center.z for instance in instances),
    )
    minimum = Vector3(0.0, 0.0, 0.0)
    maximum = Vector3(
        max_center.x + box_size.x * 0.5,
        max_center.y + box_size.y * 0.5,
        max_center.z + box_size.z * 0.5,
    )
    payload = {
        "fixture": "cws-viewer-v1-box-grid",
        "node_count": node_count,
        "box_size": [box_size.x, box_size.y, box_size.z],
        "spacing": [spacing.x, spacing.y, spacing.z],
        "layers": layers,
        "instances": [
            [instance.node_id, instance.center.x, instance.center.y, instance.center.z]
            for instance in instances
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return TechnologyScene(
        scene_id=f"scene:v1:grid:{node_count}",
        box_size=box_size,
        instances=tuple(instances),
        bounds=BoundingBox(minimum, maximum),
        geometry_hash=digest,
        metadata=(
            ("fixture", "cws-viewer-v1-box-grid"),
            ("node_count", str(node_count)),
            ("layers", str(layers)),
        ),
    )


def deterministic_pick_indices(node_count: int, sample_count: int) -> tuple[int, ...]:
    if node_count <= 0:
        raise ValueError("node_count moet positief zijn")
    requested = max(1, min(sample_count, node_count))
    if requested == 1:
        return (node_count // 2,)
    values = {
        int(round(step * (node_count - 1) / (requested - 1)))
        for step in range(requested)
    }
    return tuple(sorted(values))


__all__ = ["build_box_grid_scene", "deterministic_pick_indices"]
