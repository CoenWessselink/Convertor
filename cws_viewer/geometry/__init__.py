"""Geometry loading services for CWS Viewer.

Native CAD providers are intentionally imported lazily.  Importing lightweight
contracts, caches or project adapters must not initialize CadQuery/OpenCascade;
that keeps the GUI responsive, avoids unnecessary DLL loading and prevents
native-runtime side effects in metadata-only operations.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "IfcMeshProvider",
    "UnsupportedIfcGeometry",
    "StepMeshProvider",
    "UnsupportedStepGeometry",
    "ProxyMeshProvider",
    "CancellationToken",
    "GeometryLoadCancelled",
    "MeshRepository",
    "BatchLoadReport",
    "GeometryLoadCoordinator",
    "IsolatedIfcMeshProvider",
    "NativeGeometryWorkerError",
]


def __getattr__(name: str) -> Any:
    if name in {
        "CancellationToken",
        "GeometryLoadCancelled",
        "MeshRepository",
        "BatchLoadReport",
        "GeometryLoadCoordinator",
    }:
        from .loader import (
            BatchLoadReport,
            CancellationToken,
            GeometryLoadCancelled,
            GeometryLoadCoordinator,
            MeshRepository,
        )

        return {
            "CancellationToken": CancellationToken,
            "GeometryLoadCancelled": GeometryLoadCancelled,
            "MeshRepository": MeshRepository,
            "BatchLoadReport": BatchLoadReport,
            "GeometryLoadCoordinator": GeometryLoadCoordinator,
        }[name]
    if name in {"IfcMeshProvider", "UnsupportedIfcGeometry"}:
        from .ifc_provider import IfcMeshProvider, UnsupportedIfcGeometry

        return {
            "IfcMeshProvider": IfcMeshProvider,
            "UnsupportedIfcGeometry": UnsupportedIfcGeometry,
        }[name]
    if name in {"StepMeshProvider", "UnsupportedStepGeometry"}:
        from .step_provider import StepMeshProvider, UnsupportedStepGeometry

        return {
            "StepMeshProvider": StepMeshProvider,
            "UnsupportedStepGeometry": UnsupportedStepGeometry,
        }[name]
    if name == "ProxyMeshProvider":
        from .proxy_provider import ProxyMeshProvider

        return ProxyMeshProvider
    if name in {"IsolatedIfcMeshProvider", "NativeGeometryWorkerError"}:
        from .isolated import IsolatedIfcMeshProvider, NativeGeometryWorkerError

        return {
            "IsolatedIfcMeshProvider": IsolatedIfcMeshProvider,
            "NativeGeometryWorkerError": NativeGeometryWorkerError,
        }[name]
    raise AttributeError(name)
