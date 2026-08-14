"""Renderer-neutral contracts used by the viewer controller."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.contracts.state import (
    CameraState,
    PickResult,
    ScreenshotOptions,
    ViewerCapabilities,
    ViewerDisplayPreferences,
)
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.math3d import Rgba


@dataclass(frozen=True, slots=True)
class RenderState:
    """Fully resolved display state supplied to a renderer.

    The state contains only stable node IDs and display-only overrides. It may
    never be interpreted as canonical manufacturing data.
    """

    scene_hash: str
    visible_node_ids: tuple[str, ...]
    ghosted_node_ids: tuple[str, ...]
    selected_node_ids: tuple[str, ...]
    transparency_by_node: tuple[tuple[str, float], ...]
    color_by_node: tuple[tuple[str, Rgba], ...]
    display_preferences: ViewerDisplayPreferences = field(
        default_factory=ViewerDisplayPreferences
    )

    @property
    def visible_set(self) -> frozenset[str]:
        return frozenset(self.visible_node_ids)

    @property
    def ghosted_set(self) -> frozenset[str]:
        return frozenset(self.ghosted_node_ids)

    @property
    def selected_set(self) -> frozenset[str]:
        return frozenset(self.selected_node_ids)

    @property
    def transparency(self) -> dict[str, float]:
        return dict(self.transparency_by_node)

    @property
    def colors(self) -> dict[str, Rgba]:
        return dict(self.color_by_node)


class CoreRenderBackend(Protocol):
    """Minimal backend required by :class:`ViewerCoreController`."""

    def capabilities(self) -> ViewerCapabilities: ...

    def initialize(self, *, width: int, height: int) -> None: ...

    def load_scene(self, scene: ProjectScene, index: SceneIndex) -> None: ...

    def apply_state(self, state: RenderState, index: SceneIndex) -> None: ...

    def set_camera(self, camera: CameraState) -> None: ...

    def render(self) -> None: ...

    def pick_at(self, x: int, y: int, index: SceneIndex) -> PickResult | None: ...

    def screenshot(self, options: ScreenshotOptions) -> bytes: ...

    def capture_png(self, output: str | Path) -> Path: ...

    def resize(self, width: int, height: int) -> None: ...

    def clear_scene(self) -> None: ...

    def shutdown(self) -> None: ...


__all__ = ["RenderState", "CoreRenderBackend"]
