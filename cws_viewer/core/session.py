"""Mutable viewer-session state with deterministic reconciliation rules."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable

from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.contracts.state import (
    CameraState,
    ClippingBox,
    SectionPlane,
    ViewerDisplayPreferences,
)
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.math3d import Rgba
from cws_viewer.rendering.contracts import RenderState


@dataclass(slots=True)
class ViewerSession:
    """Runtime display state, separate from the immutable scene.

    Stable node IDs allow a safe subset of this state to survive a scene reload
    of the same project. Geometry or manufacturing truth is never stored here.
    """

    project_id: str = ""
    scene_hash: str = ""
    selection: tuple[str, ...] = ()
    selection_level: SelectionLevel = SelectionLevel.PART
    hidden: set[str] = field(default_factory=set)
    isolation: tuple[str, ...] = ()
    ghost_context: bool = False
    transparency: dict[str, float] = field(default_factory=dict)
    colors: dict[str, Rgba] = field(default_factory=dict)
    camera: CameraState = field(default_factory=CameraState.default)
    section_planes: dict[str, SectionPlane] = field(default_factory=dict)
    clipping_box: ClippingBox | None = None
    display_preferences: ViewerDisplayPreferences = field(default_factory=ViewerDisplayPreferences)
    accuracy_mode: bool = False

    @classmethod
    def for_scene(cls, index: SceneIndex) -> "ViewerSession":
        return cls(
            project_id=index.scene.project_id,
            scene_hash=index.scene.scene_hash,
            hidden={node.node_id for node in index.scene.nodes if not node.visible},
        )

    def reset_for_scene(self, index: SceneIndex) -> None:
        fresh = ViewerSession.for_scene(index)
        self.project_id = fresh.project_id
        self.scene_hash = fresh.scene_hash
        self.selection = fresh.selection
        self.selection_level = fresh.selection_level
        self.hidden = fresh.hidden
        self.isolation = fresh.isolation
        self.ghost_context = fresh.ghost_context
        self.transparency = fresh.transparency
        self.colors = fresh.colors
        self.camera = fresh.camera
        self.section_planes = fresh.section_planes
        self.clipping_box = fresh.clipping_box
        self.display_preferences = fresh.display_preferences
        self.accuracy_mode = fresh.accuracy_mode

    def reconcile(self, old_index: SceneIndex, new_index: SceneIndex) -> dict[str, int | bool]:
        """Preserve safe display state across a reload of the same project."""

        if old_index.scene.project_id != new_index.scene.project_id:
            self.reset_for_scene(new_index)
            return {"same_project": False, "selection_preserved": 0, "hidden_preserved": 0}

        existing = frozenset(new_index.nodes_by_id)
        base_hidden = {node.node_id for node in new_index.scene.nodes if not node.visible}
        selection = tuple(node_id for node_id in self.selection if node_id in existing)
        hidden = base_hidden | {node_id for node_id in self.hidden if node_id in existing}
        isolation = tuple(node_id for node_id in self.isolation if node_id in existing)
        transparency = {
            node_id: value for node_id, value in self.transparency.items() if node_id in existing
        }
        colors = {node_id: value for node_id, value in self.colors.items() if node_id in existing}

        self.project_id = new_index.scene.project_id
        self.scene_hash = new_index.scene.scene_hash
        self.selection = selection
        self.hidden = hidden
        self.isolation = isolation
        self.transparency = transparency
        self.colors = colors
        return {
            "same_project": True,
            "selection_preserved": len(selection),
            "hidden_preserved": len(hidden - base_hidden),
            "isolation_preserved": len(isolation),
            "style_preserved": len(transparency) + len(colors),
            "display_preferences_preserved": True,
            "accuracy_mode_preserved": self.accuracy_mode,
        }

    def set_selection(self, ids: Iterable[str]) -> None:
        self.selection = tuple(dict.fromkeys(str(value) for value in ids))

    def visible_and_ghosted(self, index: SceneIndex) -> tuple[tuple[str, ...], tuple[str, ...]]:
        renderable = set(index.renderable_node_ids)
        explicitly_hidden = (
            set(index.descendants(self.hidden, renderable_only=True)) if self.hidden else set()
        )
        renderable.difference_update(explicitly_hidden)

        if not self.isolation:
            return tuple(node_id for node_id in index.renderable_node_ids if node_id in renderable), ()

        focus = set(index.descendants(self.isolation, renderable_only=True))
        focus.intersection_update(renderable)
        if self.ghost_context:
            ghosted = renderable - focus
            visible = renderable
        else:
            ghosted = set()
            visible = focus
        return (
            tuple(node_id for node_id in index.renderable_node_ids if node_id in visible),
            tuple(node_id for node_id in index.renderable_node_ids if node_id in ghosted),
        )

    def render_state(self, index: SceneIndex) -> RenderState:
        visible, ghosted = self.visible_and_ghosted(index)
        renderable = frozenset(index.renderable_node_ids)
        selected = tuple(node_id for node_id in self.selection if node_id in renderable)
        return RenderState(
            scene_hash=index.scene.scene_hash,
            visible_node_ids=visible,
            ghosted_node_ids=ghosted,
            selected_node_ids=selected,
            transparency_by_node=tuple(sorted(self.transparency.items())),
            color_by_node=tuple(sorted(self.colors.items())),
            display_preferences=self.display_preferences,
        )

    def camera_with_projection(self, projection) -> CameraState:
        return replace(self.camera, projection=projection)


__all__ = ["ViewerSession"]
