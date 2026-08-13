"""Dependency-free canonical JSON and hashing for handover contracts."""
from __future__ import annotations

from enum import Enum
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


def _normalise(value: Any, *, precision: int = 9) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): _normalise(item, precision=precision)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalise(item, precision=precision) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Canonical JSON contains a non-finite number")
        rounded = round(value, precision)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"Unsupported canonical JSON value {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalise(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


__all__ = ["canonical_json_bytes", "canonical_sha256"]
