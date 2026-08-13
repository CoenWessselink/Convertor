"""Small validation helpers shared by immutable viewer contracts."""
from __future__ import annotations

from collections.abc import Mapping
import math
import re
from types import MappingProxyType
from typing import Any

from cws_viewer.api.errors import ViewerContractError

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def require_text(value: object, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ViewerContractError(f"{label} ontbreekt")
    return text


def require_sha256(value: object, label: str) -> str:
    digest = str(value or "").strip().lower()
    if not SHA256_PATTERN.fullmatch(digest):
        raise ViewerContractError(f"{label} is geen geldige SHA-256")
    return digest


def finite_float(value: object, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ViewerContractError(f"{label} is niet numeriek") from exc
    if not math.isfinite(number):
        raise ViewerContractError(f"{label} moet eindig zijn")
    return number


def freeze_json(value: Any, label: str = "waarde") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return finite_float(value, label)
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ViewerContractError(f"{label} bevat een niet-tekstuele JSON-sleutel")
            frozen_key = require_text(key, f"{label}.sleutel")
            if frozen_key in frozen:
                raise ViewerContractError(f"{label} bevat een dubbele JSON-sleutel")
            frozen[frozen_key] = freeze_json(item, f"{label}.{frozen_key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(freeze_json(item, f"{label}[]") for item in value)
    raise ViewerContractError(f"{label} is niet JSON-serialiseerbaar")


def thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): thaw_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw_json(item) for item in value]
    return value
