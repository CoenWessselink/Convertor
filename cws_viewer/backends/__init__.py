"""Optional CWS Viewer rendering backends.

Heavy VTK/OpenCascade modules are loaded only when their concrete class is
requested.  This is required for metadata-only CLI paths and for reliable
packaged runtime diagnostics.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "HeadlessViewerController",
    "MemoryRenderBackend",
    "OcctExactPartBackend",
    "OcctAisSpikeBackend",
    "VtkMeshSpikeBackend",
    "VtkProjectBackend",
    "VtkProjectMeshBackend",
]


def __getattr__(name: str) -> Any:
    if name == "HeadlessViewerController":
        from .headless import HeadlessViewerController

        return HeadlessViewerController
    if name == "MemoryRenderBackend":
        from .memory import MemoryRenderBackend

        return MemoryRenderBackend
    if name == "OcctExactPartBackend":
        from .occt_exact import OcctExactPartBackend

        return OcctExactPartBackend
    if name == "OcctAisSpikeBackend":
        from .occt_ais import OcctAisSpikeBackend

        return OcctAisSpikeBackend
    if name == "VtkMeshSpikeBackend":
        from .vtk_mesh import VtkMeshSpikeBackend

        return VtkMeshSpikeBackend
    if name == "VtkProjectBackend":
        from .vtk_project import VtkProjectBackend

        return VtkProjectBackend
    if name == "VtkProjectMeshBackend":
        from .vtk_project_mesh import VtkProjectMeshBackend

        return VtkProjectMeshBackend
    raise AttributeError(name)
