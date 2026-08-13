"""Small deterministic helpers for production-package export.

This module was missing from the draft v0.8 overlay.  It is intentionally
self-contained so the overlay can be imported and its smoke tests can run in
the Codex handover snapshot.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping

_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_UNDERSCORE = re.compile(r"_+")


def get_value(value: Any, *names: str, default: Any = None) -> Any:
    """Return the first present mapping key or object attribute."""
    for name in names:
        if isinstance(value, Mapping) and name in value:
            return value[name]
        if value is not None and hasattr(value, name):
            return getattr(value, name)
    return default


def iter_values(value: Any) -> list[Any]:
    """Normalize scalars, mappings and iterables to a deterministic list."""
    if value is None:
        return []
    if isinstance(value, Mapping):
        return list(value.values())
    if isinstance(value, (str, bytes, bytearray, memoryview)):
        return [value]
    try:
        return list(value)
    except TypeError:
        return [value]


def _json_default(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        # Binary data should normally be represented by an artifact path/base64
        # wrapper.  A deterministic hexadecimal representation avoids silent
        # data loss when computing state hashes.
        return {"bytes_hex": bytes(value).hex()}
    if isinstance(value, set):
        return sorted(value, key=lambda item: repr(item))
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    raise TypeError(f"Niet JSON-serialiseerbaar type: {type(value).__name__}")


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        result = value.to_dict()
        if isinstance(result, Mapping):
            return dict(result)
    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    raise TypeError(f"Object kan niet naar dict worden omgezet: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=_json_default,
    ).encode("utf-8")


def sha256_bytes(data: bytes | bytearray | memoryview) -> str:
    return hashlib.sha256(bytes(data)).hexdigest()


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_filename(value: Any, *, fallback: str = "bestand", max_length: int = 120) -> str:
    text = str(value or "").strip()
    text = _INVALID_FILENAME.sub("_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    text = _MULTI_UNDERSCORE.sub("_", text)
    if not text:
        text = fallback
    stem = text.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED:
        text = f"_{text}"
    if len(text) > max_length:
        suffix = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
        text = f"{text[:max(1, max_length - 12)].rstrip(' ._')}_{suffix}"
    return text or fallback


def safe_relative_path(*parts: Any) -> Path:
    clean: list[str] = []
    for part in parts:
        raw = str(part or "").replace("\\", "/")
        pure = PurePosixPath(raw)
        if pure.is_absolute() or ".." in pure.parts:
            # Treat untrusted visible labels as one filename component rather
            # than allowing traversal.
            clean.append(safe_filename(raw.replace("/", "_")))
            continue
        for component in pure.parts:
            if component in {"", "."}:
                continue
            clean.append(safe_filename(component))
    if not clean:
        clean = ["onbekend"]
    return Path(*clean)


def atomic_write(path: str | Path, data: bytes | bytearray | memoryview) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(bytes(data))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def atomic_directory(final_path: str | Path) -> Iterator[Path]:
    """Build a directory beside its final path and publish it atomically."""
    final = Path(final_path)
    final.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{final.name}.", suffix=".tmp", dir=final.parent))
    backup = final.with_name(f".{final.name}.backup")
    try:
        yield temp
        if backup.exists():
            shutil.rmtree(backup)
        if final.exists():
            os.replace(final, backup)
        try:
            os.replace(temp, final)
        except Exception:
            if backup.exists() and not final.exists():
                os.replace(backup, final)
            raise
        else:
            if backup.exists():
                shutil.rmtree(backup)
    except Exception:
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)
        raise


__all__ = [
    "as_dict", "atomic_directory", "atomic_write", "canonical_json_bytes",
    "finite_number", "get_value", "iter_values", "safe_filename",
    "safe_relative_path", "sha256_bytes", "sha256_file", "stable_hash",
    "utc_now_iso",
]
