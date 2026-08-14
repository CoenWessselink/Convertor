"""Renderer-independent viewer integration boundary."""

from .mesh_resources import (
    VIEWER_MESH_CONTRACT_VERSION,
    ViewerMeshResource,
    ViewerTessellationPolicy,
    build_canonical_viewer_mesh_resource,
    build_viewer_mesh_resource,
)
from .progressive_loader import (
    PROGRESSIVE_MESH_LOAD_VERSION,
    ProgressiveMeshLoadCancelled,
    ProgressiveMeshLoadPlan,
)
from .workspace import (
    AccuracySummary,
    ViewerTreeNode,
    ViewerWorkspaceState,
)

__all__ = [
    "AccuracySummary",
    "PROGRESSIVE_MESH_LOAD_VERSION",
    "ProgressiveMeshLoadCancelled",
    "ProgressiveMeshLoadPlan",
    "VIEWER_MESH_CONTRACT_VERSION",
    "ViewerMeshResource",
    "ViewerTessellationPolicy",
    "ViewerTreeNode",
    "ViewerWorkspaceState",
    "build_canonical_viewer_mesh_resource",
    "build_viewer_mesh_resource",
]
