"""Version and compatibility constants for CWS Viewer Core.

The viewer package has its own API and persisted-state versions.  These are
intentionally independent from the CWS Convertor application and Canonical
Project Model versions so each contract can evolve explicitly.
"""
from __future__ import annotations

VIEWER_PACKAGE_VERSION = "1.0.0-dev0"
VIEWER_API_VERSION = "0.7.0"
SCENE_SCHEMA_VERSION = "1.0"
VIEWER_STATE_SCHEMA_VERSION = "1.1"

# V9 validates the historical handover projects and the newer Project Model
# 2.5 used by the integrated CWS Convertor build.
SUPPORTED_PROJECT_SCHEMA_MAJORS = frozenset({2})
VALIDATED_PROJECT_SCHEMA_VERSIONS = frozenset({"2.3", "2.4", "2.5"})

PRODUCT_NAME = "CWS Viewer Core"
PRODUCT_ID = "nl.cws.convertor.viewer"


def display_version() -> str:
    return f"{PRODUCT_NAME} {VIEWER_PACKAGE_VERSION}"


__all__ = [
    "VIEWER_PACKAGE_VERSION",
    "VIEWER_API_VERSION",
    "SCENE_SCHEMA_VERSION",
    "VIEWER_STATE_SCHEMA_VERSION",
    "SUPPORTED_PROJECT_SCHEMA_MAJORS",
    "VALIDATED_PROJECT_SCHEMA_VERSIONS",
    "PRODUCT_NAME",
    "PRODUCT_ID",
    "display_version",
]
