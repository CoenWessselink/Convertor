"""Deterministic serialization helpers used by viewer contracts."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping


def to_primitive(value: Any) -> Any:
    """Convert contract objects to a stable JSON-compatible representation."""

    if hasattr(value, "to_dict") and callable(value.to_dict):
        return to_primitive(value.to_dict())
    if is_dataclass(value):
        return to_primitive(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    if isinstance(value, frozenset | set):
        return sorted(to_primitive(item) for item in value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Niet-eindige numerieke waarde kan niet worden geserialiseerd")
        rounded = round(value, 12)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def stable_json_bytes(value: Any) -> bytes:
    return json.dumps(
        to_primitive(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def stable_sha256(value: Any) -> str:
    return hashlib.sha256(stable_json_bytes(value)).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def is_sha256(value: str) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in text)


def parse_semver(value: str) -> tuple[int, int, int]:
    text = str(value or "").strip()
    core = text.split("-", 1)[0].split("+", 1)[0]
    parts = core.split(".")
    if not 1 <= len(parts) <= 3 or any(not part.isdigit() for part in parts):
        raise ValueError(f"Ongeldige semver: {value!r}")
    numbers = [int(part) for part in parts]
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)  # type: ignore[return-value]


__all__ = [
    "to_primitive",
    "stable_json_bytes",
    "stable_sha256",
    "sha256_bytes",
    "is_sha256",
    "parse_semver",
]
