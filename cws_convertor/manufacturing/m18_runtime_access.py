"""Runtime bridge for the frozen Scribing M18 authority stores on Project Model 2.25.

U1 preserved the M18 Project Model 2.24 stores inside the unified 2.25
compatibility envelope.  U2 exposes those stores as attributes expected by the
frozen M18 authority implementation without adding a second ProjectModel or
copying data.  Every getter resolves to the same mutable dictionary that is
serialized by :mod:`cws_convertor.project.unified_schema`.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from cws_convertor.project.model import Part, ProjectModel
from cws_convertor.project.unified_schema import (
    EXTENSION_KEY,
    PART_EXTENSION_KEY,
    M18_PART_FIELD_DEFAULTS,
    M18_PROJECT_STORE_DEFAULTS,
    UNIFIED_PROJECT_SCHEMA_VERSION,
)

_INSTALLED = False


def _project_stores(project: ProjectModel) -> dict[str, Any]:
    if project.schema_version != UNIFIED_PROJECT_SCHEMA_VERSION:
        raise RuntimeError(
            "M18 authority runtime requires unified Project Model 2.25; found "
            f"{project.schema_version!r}"
        )
    if not isinstance(project.settings, dict):
        project.settings = {}
    unified = project.settings.get(EXTENSION_KEY)
    if not isinstance(unified, dict):
        unified = {
            "source_schema": project.schema_version,
            "bridge_schema": UNIFIED_PROJECT_SCHEMA_VERSION,
        }
        project.settings[EXTENSION_KEY] = unified
    stores = unified.get("m18_project_stores")
    if not isinstance(stores, dict):
        stores = {}
        unified["m18_project_stores"] = stores
    return stores


def get_m18_project_store(project: ProjectModel, name: str) -> Any:
    if name not in M18_PROJECT_STORE_DEFAULTS:
        raise KeyError(f"Onbekende M18 project-store {name!r}")
    stores = _project_stores(project)
    if name not in stores:
        stores[name] = deepcopy(M18_PROJECT_STORE_DEFAULTS[name])
    return stores[name]


def _set_m18_project_store(project: ProjectModel, name: str, value: Any) -> None:
    if name not in M18_PROJECT_STORE_DEFAULTS:
        raise KeyError(f"Onbekende M18 project-store {name!r}")
    expected = M18_PROJECT_STORE_DEFAULTS[name]
    if isinstance(expected, dict) and not isinstance(value, dict):
        raise TypeError(f"M18 project-store {name} vereist een dict")
    if isinstance(expected, int) and not isinstance(value, int):
        raise TypeError(f"M18 project-store {name} vereist een int")
    _project_stores(project)[name] = value


def _part_bridge(part: Part) -> dict[str, Any]:
    if not isinstance(part.properties, dict):
        part.properties = {}
    unified = part.properties.get(PART_EXTENSION_KEY)
    if not isinstance(unified, dict):
        unified = {}
        part.properties[PART_EXTENSION_KEY] = unified
    payload = unified.get("m18_manufacturing")
    if not isinstance(payload, dict):
        payload = {}
        unified["m18_manufacturing"] = payload
    return payload


def get_m18_part_field(part: Part, name: str) -> Any:
    if name not in M18_PART_FIELD_DEFAULTS:
        raise KeyError(f"Onbekend M18 part-veld {name!r}")
    payload = _part_bridge(part)
    if name not in payload:
        payload[name] = deepcopy(M18_PART_FIELD_DEFAULTS[name])
    return payload[name]


def _set_m18_part_field(part: Part, name: str, value: Any) -> None:
    if name not in M18_PART_FIELD_DEFAULTS:
        raise KeyError(f"Onbekend M18 part-veld {name!r}")
    expected = M18_PART_FIELD_DEFAULTS[name]
    if isinstance(expected, list) and not isinstance(value, list):
        raise TypeError(f"M18 part-veld {name} vereist een list")
    if isinstance(expected, dict) and not isinstance(value, dict):
        raise TypeError(f"M18 part-veld {name} vereist een dict")
    _part_bridge(part)[name] = value


def install_m18_runtime_access() -> None:
    """Install non-duplicating compatibility properties exactly once."""
    global _INSTALLED
    if _INSTALLED:
        return

    for name in M18_PROJECT_STORE_DEFAULTS:
        if hasattr(ProjectModel, name):
            continue
        setattr(
            ProjectModel,
            name,
            property(
                lambda self, key=name: get_m18_project_store(self, key),
                lambda self, value, key=name: _set_m18_project_store(self, key, value),
                doc=f"Unified Project Model 2.25 bridge for frozen M18 store {name}.",
            ),
        )

    for name in M18_PART_FIELD_DEFAULTS:
        if hasattr(Part, name):
            continue
        setattr(
            Part,
            name,
            property(
                lambda self, key=name: get_m18_part_field(self, key),
                lambda self, value, key=name: _set_m18_part_field(self, key, value),
                doc=f"Unified Project Model 2.25 bridge for frozen M18 part field {name}.",
            ),
        )
    _INSTALLED = True


__all__ = [
    "install_m18_runtime_access",
    "get_m18_project_store",
    "get_m18_part_field",
]
