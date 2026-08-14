"""Typed CWS Viewer errors and stable machine-readable error codes."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping


class ViewerErrorCode(StrEnum):
    SCENE_SCHEMA_UNSUPPORTED = "CWS-VIEWER-SCENE-SCHEMA-UNSUPPORTED"
    SCENE_HASH_MISMATCH = "CWS-VIEWER-SCENE-HASH-MISMATCH"
    SCENE_DUPLICATE_ID = "CWS-VIEWER-SCENE-DUPLICATE-ID"
    SCENE_REFERENCE_MISSING = "CWS-VIEWER-SCENE-REFERENCE-MISSING"
    SCENE_CYCLE = "CWS-VIEWER-SCENE-CYCLE"
    TRANSFORM_INVALID = "CWS-VIEWER-TRANSFORM-INVALID"
    GEOMETRY_HASH_MISMATCH = "CWS-VIEWER-GEOMETRY-HASH-MISMATCH"
    GEOMETRY_PAYLOAD_UNSAFE = "CWS-VIEWER-GEOMETRY-PAYLOAD-UNSAFE"
    RENDERER_INIT_FAILED = "CWS-VIEWER-RENDERER-INIT-FAILED"
    RENDERER_CAPABILITY_MISSING = "CWS-VIEWER-RENDERER-CAPABILITY-MISSING"
    PICK_MAP_MISSING = "CWS-VIEWER-PICK-MAP-MISSING"
    MEASUREMENT_ANCHOR_INVALID = "CWS-VIEWER-MEASUREMENT-ANCHOR-INVALID"
    COMPARE_INPUT_MISMATCH = "CWS-VIEWER-COMPARE-INPUT-MISMATCH"
    CACHE_CORRUPT = "CWS-VIEWER-CACHE-CORRUPT"
    DEVICE_LOST = "CWS-VIEWER-DEVICE-LOST"
    PROJECT_SCHEMA_UNSUPPORTED = "CWS-VIEWER-PROJECT-SCHEMA-UNSUPPORTED"
    NODE_NOT_FOUND = "CWS-VIEWER-NODE-NOT-FOUND"
    TOOL_UNSUPPORTED = "CWS-VIEWER-TOOL-UNSUPPORTED"
    VIEWER_DISPOSED = "CWS-VIEWER-DISPOSED"
    FORBIDDEN_REFERENCE = "CWS-VIEWER-FORBIDDEN-REFERENCE"
    FILE_IO_FAILED = "CWS-VIEWER-FILE-IO-FAILED"
    WORKSPACE_INVALID = "CWS-VIEWER-WORKSPACE-INVALID"
    WORKSPACE_CHECKSUM_MISMATCH = "CWS-VIEWER-WORKSPACE-CHECKSUM-MISMATCH"


@dataclass(frozen=True, slots=True)
class ViewerErrorDetails:
    code: ViewerErrorCode
    message: str
    context: Mapping[str, Any]


class ViewerError(RuntimeError):
    """Base exception carrying a stable error code and optional context."""

    def __init__(
        self,
        message: str,
        *,
        code: ViewerErrorCode,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = dict(context or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": str(self),
            "context": dict(self.context),
        }


__all__ = ["ViewerError", "ViewerErrorCode", "ViewerErrorDetails"]
