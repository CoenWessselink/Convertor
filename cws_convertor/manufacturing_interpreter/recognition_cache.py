from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def stable_sha256(value: Any) -> str:
    payload = json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RecognitionCacheV3:
    """Version-bound, atomic recognition evidence cache.

    Reports remain in the interpreter's in-memory cache. This disk layer stores
    immutable evidence and invalidation metadata, never native BREP objects.
    """

    schema_version = "mgi-cache-v3"

    def __init__(self, root: str | Path | None = None) -> None:
        configured = os.environ.get("CWS_MGI_CACHE_DIR", "").strip()
        self.root = Path(root or configured or (Path.home() / ".cws_convertor" / "mgi_cache_v3"))
        self.root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def key(
        cls,
        *,
        source_sha256: str,
        source_geometry_hash: str,
        engine_version: str,
        algorithm_versions: Any,
        tolerance_policy_hash: str,
        profile_database_hash: str,
        preferred_profile: str,
        requested_outputs: tuple[str, ...],
    ) -> str:
        return stable_sha256(
            {
                "schema": cls.schema_version,
                "source_sha256": source_sha256,
                "source_geometry_hash": source_geometry_hash,
                "engine_version": engine_version,
                "algorithm_versions": algorithm_versions,
                "tolerance_policy_hash": tolerance_policy_hash,
                "profile_database_hash": profile_database_hash,
                "preferred_profile": preferred_profile,
                "requested_outputs": sorted(requested_outputs),
            }
        )

    def load_evidence(self, key: str) -> dict[str, Any] | None:
        path = self.root / f"{key}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            return None
        if payload.get("schema_version") != self.schema_version or payload.get("cache_key") != key:
            return None
        return payload

    def store_evidence(self, key: str, report: Any) -> Path:
        payload = {
            "schema_version": self.schema_version,
            "cache_key": key,
            "report_hash": stable_sha256(report),
            "report": _json_value(report),
        }
        target = self.root / f"{key}.json"
        handle, temporary_name = tempfile.mkstemp(prefix=f".{key}.", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, target)
        finally:
            try:
                Path(temporary_name).unlink(missing_ok=True)
            except OSError:
                pass
        return target


__all__ = ["RecognitionCacheV3", "stable_sha256"]
