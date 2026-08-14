"""Adapters from CWS canonical read models to viewer scene contracts.

The end-to-end loader is lazy because it can instantiate native geometry
providers.  Metadata-only project browsing therefore remains lightweight.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "CwsProjectSceneAdapter",
    "SceneBuildOptions",
    "SceneBuildReport",
    "ResolvedSource",
    "ProjectSourceResolver",
    "EntityGeometryRecord",
    "GeometryCatalogReport",
    "ProjectGeometryCatalog",
    "ProjectSceneLoadResult",
    "ProjectSceneLoader",
]


def __getattr__(name: str) -> Any:
    if name in {"CwsProjectSceneAdapter", "SceneBuildOptions", "SceneBuildReport"}:
        from .project_model import CwsProjectSceneAdapter, SceneBuildOptions, SceneBuildReport

        return {
            "CwsProjectSceneAdapter": CwsProjectSceneAdapter,
            "SceneBuildOptions": SceneBuildOptions,
            "SceneBuildReport": SceneBuildReport,
        }[name]
    if name in {
        "ResolvedSource",
        "ProjectSourceResolver",
        "EntityGeometryRecord",
        "GeometryCatalogReport",
        "ProjectGeometryCatalog",
    }:
        from .source_geometry import (
            EntityGeometryRecord,
            GeometryCatalogReport,
            ProjectGeometryCatalog,
            ProjectSourceResolver,
            ResolvedSource,
        )

        return {
            "ResolvedSource": ResolvedSource,
            "ProjectSourceResolver": ProjectSourceResolver,
            "EntityGeometryRecord": EntityGeometryRecord,
            "GeometryCatalogReport": GeometryCatalogReport,
            "ProjectGeometryCatalog": ProjectGeometryCatalog,
        }[name]
    if name in {"ProjectSceneLoadResult", "ProjectSceneLoader"}:
        from .project_scene_loader import ProjectSceneLoadResult, ProjectSceneLoader

        return {
            "ProjectSceneLoadResult": ProjectSceneLoadResult,
            "ProjectSceneLoader": ProjectSceneLoader,
        }[name]
    raise AttributeError(name)
