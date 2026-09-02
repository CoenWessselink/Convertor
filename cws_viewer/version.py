"""Version and compatibility constants for CWS Viewer Core.

The viewer package has its own API and persisted-state versions.  These are
intentionally independent from the CWS Convertor application and Canonical
Project Model versions so each contract can evolve explicitly.
"""
from __future__ import annotations

VIEWER_PACKAGE_VERSION = "1.4.0-v15-preview.2"
VIEWER_PREVIEW_VERSION = VIEWER_PACKAGE_VERSION
VIEWER_API_VERSION = "0.7.0"
SCENE_SCHEMA_VERSION = "1.0"
VIEWER_STATE_SCHEMA_VERSION = "1.1"

# Unified U1 keeps the historical Viewer/Convertor 2.5 line readable, accepts
# frozen Scribing M18 2.24 through the migration bridge, and validates 2.25 as
# the canonical integrated persistence schema.
SUPPORTED_PROJECT_SCHEMA_MAJORS = frozenset({2})
VALIDATED_PROJECT_SCHEMA_VERSIONS = frozenset({"2.3", "2.4", "2.5", "2.24", "2.25"})

PRODUCT_NAME = "CWS Viewer Core"
PRODUCT_ID = "nl.cws.convertor.viewer"


def display_version() -> str:
    return f"{PRODUCT_NAME} {VIEWER_PACKAGE_VERSION}"


__all__ = [
    "VIEWER_PACKAGE_VERSION",
    "VIEWER_PREVIEW_VERSION",
    "VIEWER_API_VERSION",
    "SCENE_SCHEMA_VERSION",
    "VIEWER_STATE_SCHEMA_VERSION",
    "SUPPORTED_PROJECT_SCHEMA_MAJORS",
    "VALIDATED_PROJECT_SCHEMA_VERSIONS",
    "PRODUCT_NAME",
    "PRODUCT_ID",
    "display_version",
]
