"""Display-only explode calculations; canonical placements remain immutable."""
from __future__ import annotations

from typing import Mapping

from cws_viewer.math3d import BoundingBox, Vector3


def radial_explode(bounds_by_node: Mapping[str, BoundingBox], distance_mm: float) -> dict[str, Vector3]:
    if distance_mm < 0:
        raise ValueError("Explodeafstand mag niet negatief zijn")
    if not bounds_by_node:
        return {}
    center = Vector3(
        sum(box.center.x for box in bounds_by_node.values()) / len(bounds_by_node),
        sum(box.center.y for box in bounds_by_node.values()) / len(bounds_by_node),
        sum(box.center.z for box in bounds_by_node.values()) / len(bounds_by_node),
    )
    result: dict[str, Vector3] = {}
    for node_id, box in bounds_by_node.items():
        direction = box.center - center
        if direction.length() <= 1e-9:
            direction = Vector3(1, 0, 0)
        result[node_id] = direction.normalized() * float(distance_mm)
    return result


__all__ = ["radial_explode"]
