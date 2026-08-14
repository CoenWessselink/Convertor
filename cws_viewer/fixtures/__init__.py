"""Deterministic viewer fixtures."""
from __future__ import annotations

from typing import Any

from .synthetic_product import build_synthetic_product_scene, stable_sample_node_ids

__all__ = [
    "build_synthetic_product_scene",
    "stable_sample_node_ids",
    "load_lo4_reference_mesh",
    "build_lo4_reference_scene",
]


def __getattr__(name: str) -> Any:
    if name in {"load_lo4_reference_mesh", "build_lo4_reference_scene"}:
        from .real_reference import build_lo4_reference_scene, load_lo4_reference_mesh
        return {
            "load_lo4_reference_mesh": load_lo4_reference_mesh,
            "build_lo4_reference_scene": build_lo4_reference_scene,
        }[name]
    raise AttributeError(name)
