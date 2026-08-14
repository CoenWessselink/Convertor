"""In-memory V2 render backend for deterministic controller tests."""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from cws_viewer.contracts.enums import MeasurementKind
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.contracts.state import (
    CameraState,
    PickResult,
    ScreenshotOptions,
    ViewerCapabilities,
)
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.math3d import Vector3
from cws_viewer.rendering.contracts import RenderState
from cws_viewer.version import VIEWER_PACKAGE_VERSION

# Valid deterministic 1×1 transparent PNG.
_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAF/gL+QOBdnwAAAABJRU5ErkJggg=="
)


class MemoryRenderBackend:
    """Records renderer calls without claiming graphical capabilities."""

    def __init__(self) -> None:
        self.initialized = False
        self.width = 0
        self.height = 0
        self.scene: ProjectScene | None = None
        self.index: SceneIndex | None = None
        self.state: RenderState | None = None
        self.camera = CameraState.default()
        self.render_count = 0
        self.shutdown_called = False
        self.pick_node_id: str | None = None

    def capabilities(self) -> ViewerCapabilities:
        return ViewerCapabilities(
            renderer_backend="memory-v2",
            backend_version=VIEWER_PACKAGE_VERSION,
            supports_large_mesh_scene=False,
            supports_exact_brep=False,
            supports_subshape_picking=False,
            supports_multi_section=False,
            supports_measurements=frozenset({MeasurementKind.POINT}),
            supports_point_clouds=False,
            supports_offscreen_render=True,
            supports_hardware_acceleration=False,
            max_clip_planes=0,
            notes=("Deterministische testbackend; geen eindgebruikersrenderer.",),
        )

    def initialize(self, *, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Afmetingen moeten positief zijn")
        self.width = int(width)
        self.height = int(height)
        self.initialized = True

    def load_scene(self, scene: ProjectScene, index: SceneIndex) -> None:
        self.scene = scene
        self.index = index

    def apply_state(self, state: RenderState, index: SceneIndex) -> None:
        self.state = state
        self.index = index

    def set_camera(self, camera: CameraState) -> None:
        self.camera = camera

    def render(self) -> None:
        self.render_count += 1

    def pick_at(self, x: int, y: int, index: SceneIndex) -> PickResult | None:
        if self.pick_node_id is None:
            return None
        node = index.node(self.pick_node_id)
        bounds = index.world_bounds_by_node[node.node_id]
        return PickResult(
            node_id=node.node_id,
            entity_id=node.entity_id,
            part_id=node.entity_id if node.kind.value in {"part", "purchased_item"} else None,
            feature_id=None,
            source_entity_id=node.source_entity_id,
            subshape_type=None,
            subshape_id=None,
            world_point=bounds.center,
            local_point=node.local_bounds.center,
            normal=Vector3(0.0, 0.0, 1.0),
        )

    def screenshot(self, options: ScreenshotOptions) -> bytes:
        return _PNG_1X1

    def capture_png(self, output: str | Path) -> Path:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_PNG_1X1)
        return path

    def resize(self, width: int, height: int) -> None:
        self.width = int(width)
        self.height = int(height)

    def clear_scene(self) -> None:
        self.scene = None
        self.index = None
        self.state = None

    def shutdown(self) -> None:
        self.clear_scene()
        self.shutdown_called = True
        self.initialized = False


__all__ = ["MemoryRenderBackend"]
