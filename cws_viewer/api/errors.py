"""Stable error codes for the framework-independent viewer boundary."""
from __future__ import annotations

from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class ViewerErrorCode(str, Enum):
    SCENE_SCHEMA_UNSUPPORTED = "CWS-VIEWER-SCENE-SCHEMA-UNSUPPORTED"
    SCENE_INVALID = "CWS-VIEWER-SCENE-INVALID"
    GEOMETRY_HASH_MISMATCH = "CWS-VIEWER-GEOMETRY-HASH-MISMATCH"
    RENDERER_INIT_FAILED = "CWS-VIEWER-RENDERER-INIT-FAILED"
    PICK_MAP_MISSING = "CWS-VIEWER-PICK-MAP-MISSING"
    MEASUREMENT_ANCHOR_INVALID = "CWS-VIEWER-MEASUREMENT-ANCHOR-INVALID"
    COMPARE_INPUT_MISMATCH = "CWS-VIEWER-COMPARE-INPUT-MISMATCH"
    CACHE_CORRUPT = "CWS-VIEWER-CACHE-CORRUPT"
    DEVICE_LOST = "CWS-VIEWER-DEVICE-LOST"


class ViewerContractError(ValueError):
    """Raised when data crosses the viewer boundary in an invalid form."""

    def __init__(
        self,
        message: str,
        code: ViewerErrorCode = ViewerErrorCode.SCENE_INVALID,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = MappingProxyType(dict(details or {}))


__all__ = ["ViewerContractError", "ViewerErrorCode"]
