"""CWS Viewer core services.

Imports are kept lazy because scene contracts depend on ``core.serialization``.
"""
from __future__ import annotations

from typing import Any

__all__ = ["ViewerCoreController", "SceneIndex", "ViewerSession", "ProjectInteractionModel", "InteractionSelection", "ViewerWorkspaceStore", "ProjectColorizer", "ColorLegendItem"]


def __getattr__(name: str) -> Any:
    if name == "ViewerCoreController":
        from .controller import ViewerCoreController

        return ViewerCoreController
    if name == "SceneIndex":
        from .scene_index import SceneIndex

        return SceneIndex
    if name == "ViewerSession":
        from .session import ViewerSession

        return ViewerSession
    if name == "ViewerWorkspaceStore":
        from .workspace_store import ViewerWorkspaceStore

        return ViewerWorkspaceStore
    if name in {"ProjectColorizer", "ColorLegendItem"}:
        from .color_schemes import ColorLegendItem, ProjectColorizer

        return {"ProjectColorizer": ProjectColorizer, "ColorLegendItem": ColorLegendItem}[name]
    if name in {"ProjectInteractionModel", "InteractionSelection"}:
        from .project_interaction import InteractionSelection, ProjectInteractionModel

        return {"ProjectInteractionModel": ProjectInteractionModel, "InteractionSelection": InteractionSelection}[name]
    raise AttributeError(name)
