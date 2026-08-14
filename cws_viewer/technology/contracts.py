"""Contracts used by the V1 renderer technology spike.

These contracts are deliberately smaller than the public ViewerController API.
They let two render backends receive the *same* synthetic scene and expose the
same measurable operations without leaking VTK or OCCT objects into the
application layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol, Sequence

from cws_viewer.math3d import BoundingBox, Vector3


class TechnologyBackendName(StrEnum):
    OCCT_AIS = "occt_ais"
    VTK_MESH = "vtk_mesh"


@dataclass(frozen=True, slots=True)
class TechnologyInstance:
    """One stable scene instance used by both V1 backends."""

    node_id: str
    center: Vector3

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("TechnologyInstance.node_id mag niet leeg zijn")


@dataclass(frozen=True, slots=True)
class TechnologyScene:
    """Immutable synthetic scene with one shared box resource and N instances."""

    scene_id: str
    box_size: Vector3
    instances: tuple[TechnologyInstance, ...]
    bounds: BoundingBox
    geometry_hash: str
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.scene_id:
            raise ValueError("TechnologyScene.scene_id mag niet leeg zijn")
        if not self.instances:
            raise ValueError("TechnologyScene vereist minimaal één instance")
        if min(self.box_size.x, self.box_size.y, self.box_size.z) <= 0:
            raise ValueError("TechnologyScene.box_size moet positief zijn")
        node_ids = [instance.node_id for instance in self.instances]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("TechnologyScene bevat dubbele node_id's")

    @property
    def node_count(self) -> int:
        return len(self.instances)

    def center_for(self, node_id: str) -> Vector3:
        for instance in self.instances:
            if instance.node_id == node_id:
                return instance.center
        raise KeyError(node_id)


@dataclass(frozen=True, slots=True)
class TechnologyBackendCapabilities:
    backend: TechnologyBackendName
    backend_version: str
    exact_brep: bool
    mesh_instancing: bool
    stable_node_picking: bool
    clipping_plane: bool
    offscreen_capture: bool
    native_window_required: bool
    qt_host_available: bool
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NativeWindow:
    """Platform-neutral native window descriptor for OCCT or Qt hosts."""

    handle: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.handle <= 0:
            raise ValueError("NativeWindow.handle moet positief zijn")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("NativeWindow-afmetingen moeten positief zijn")


class TechnologyBackend(Protocol):
    """Minimal measurable renderer interface for the V1 decision spike."""

    @property
    def name(self) -> TechnologyBackendName: ...

    def capabilities(self) -> TechnologyBackendCapabilities: ...

    def initialize(
        self,
        *,
        width: int,
        height: int,
        native_window: NativeWindow | None = None,
    ) -> None: ...

    def load_scene(self, scene: TechnologyScene) -> None: ...

    def clear_scene(self) -> None: ...

    def fit_all(self) -> None: ...

    def set_top_view(self) -> None: ...

    def set_isometric_view(self) -> None: ...

    def orbit_step(self, angle_degrees: float) -> None: ...

    def render(self) -> None: ...

    def world_to_display(self, point: Vector3) -> tuple[int, int]: ...

    def pick_at(self, x: int, y: int) -> str | None: ...

    def set_clip_plane(self, *, origin: Vector3, normal: Vector3) -> None: ...

    def clear_clip_planes(self) -> None: ...

    def capture_png(self, output: str | Path) -> Path: ...

    def resize(self, width: int, height: int) -> None: ...

    def dispose(self) -> None: ...


__all__ = [
    "TechnologyBackendName",
    "TechnologyInstance",
    "TechnologyScene",
    "TechnologyBackendCapabilities",
    "NativeWindow",
    "TechnologyBackend",
]
