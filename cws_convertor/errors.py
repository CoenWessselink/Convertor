"""Stable error codes shared by GUI, CLI, reports and future API jobs."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    UNKNOWN = "CWS-0000"
    INVALID_INPUT = "CWS-1001"
    UNSUPPORTED_FORMAT = "CWS-1002"
    VALIDATION_BLOCKED = "CWS-1101"
    GEOMETRY_MISMATCH = "CWS-1102"
    PROJECT_INVALID = "CWS-2001"
    PROJECT_CORRUPT = "CWS-2002"
    PROJECT_SCHEMA_UNSUPPORTED = "CWS-2003"
    PROJECT_WRITE_FAILED = "CWS-2004"
    PROJECT_READ_ONLY = "CWS-2005"
    JOB_CANCELLED = "CWS-2101"
    IMPORT_AMBIGUOUS = "CWS-3001"
    AI_CONSENT_REQUIRED = "CWS-4001"
    INTERNAL_ERROR = "CWS-9001"


@dataclass
class CWSError(Exception):
    """Base exception carrying a machine-readable error code."""

    message: str
    code: ErrorCode = ErrorCode.UNKNOWN
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": dict(self.details or {}),
        }
