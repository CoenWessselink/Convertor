"""Process-local render geometry cache shared by every Viewer window.

Each render window deliberately retains its own actors, selection arrays and
OpenGL state.  Immutable VTK polydata and feature-edge resources are shared by
identity for viewers backed by the exact same :class:`MeshRepository`.  This
prevents a detached BOM Viewer from rebuilding and duplicating source geometry
while preserving independent cameras and safe renderer lifetimes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import threading
from typing import Any, Callable
from weakref import WeakKeyDictionary


@dataclass(frozen=True, slots=True)
class SharedRenderCacheStats:
    repository_identity: int
    polydata_items: int
    feature_items: int
    hits: int
    misses: int
    invalidations: int = 0
    resource_identity_sha256: str = ""

    @property
    def shared_item_count(self) -> int:
        return self.polydata_items + self.feature_items


class SharedRenderResourceCache:
    _lock = threading.RLock()
    _repositories: WeakKeyDictionary[Any, dict[str, Any]] = WeakKeyDictionary()

    @classmethod
    def _bucket(cls, repository: Any) -> dict[str, Any]:
        with cls._lock:
            bucket = cls._repositories.get(repository)
            if bucket is None:
                bucket = {
                    "polydata": {}, "features": {}, "hits": 0, "misses": 0,
                    "invalidations": 0,
                }
                cls._repositories[repository] = bucket
            return bucket

    @classmethod
    def get_or_create(
        cls,
        repository: Any,
        kind: str,
        key: str,
        builder: Callable[[], Any],
    ) -> Any:
        if kind not in {"polydata", "features"}:
            raise ValueError(f"Onbekend rendercachetype: {kind}")
        bucket = cls._bucket(repository)
        with cls._lock:
            cached = bucket[kind].get(str(key))
            if cached is not None:
                bucket["hits"] += 1
                return cached
            value = builder()
            bucket[kind][str(key)] = value
            bucket["misses"] += 1
            return value

    @classmethod
    def invalidate(
        cls,
        repository: Any,
        geometry_ids: set[str] | None = None,
    ) -> None:
        bucket = cls._bucket(repository)
        with cls._lock:
            removed = 0
            if geometry_ids is None:
                removed = len(bucket["polydata"]) + len(bucket["features"])
                bucket["polydata"].clear()
                bucket["features"].clear()
                bucket["invalidations"] += removed
                return
            requested = {str(value) for value in geometry_ids}
            for key in tuple(bucket["polydata"]):
                if any(
                    key == value or key.startswith(value + "|") or key.endswith("|" + value)
                    for value in requested
                ):
                    if bucket["polydata"].pop(key, None) is not None:
                        removed += 1
            # Edge keys start with the geometry identity used to build them.
            for key in tuple(bucket["features"]):
                if any(
                    key == value or key.startswith(value + "|") or key.endswith("|" + value)
                    for value in requested
                ):
                    if bucket["features"].pop(key, None) is not None:
                        removed += 1
            bucket["invalidations"] += removed

    @classmethod
    def evidence(cls, repository: Any) -> dict[str, Any]:
        """Machine-readable proof that windows reference identical resources."""

        bucket = cls._bucket(repository)
        with cls._lock:
            resources = [
                {
                    "kind": kind,
                    "key": key,
                    "object_identity": id(value),
                    "object_type": type(value).__name__,
                }
                for kind in ("polydata", "features")
                for key, value in sorted(bucket[kind].items())
            ]
            digest = hashlib.sha256(json.dumps(
                resources, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")).hexdigest()
            return {
                "schema": "cws-shared-render-cache-evidence-2.0",
                "repository_identity": id(repository),
                "resources": resources,
                "resource_identity_sha256": digest,
                "hits": int(bucket["hits"]),
                "builds": int(bucket["misses"]),
                "invalidations": int(bucket["invalidations"]),
            }

    @classmethod
    def stats(cls, repository: Any) -> SharedRenderCacheStats:
        bucket = cls._bucket(repository)
        with cls._lock:
            evidence = cls.evidence(repository)
            return SharedRenderCacheStats(
                repository_identity=id(repository),
                polydata_items=len(bucket["polydata"]),
                feature_items=len(bucket["features"]),
                hits=int(bucket["hits"]), misses=int(bucket["misses"]),
                invalidations=int(bucket["invalidations"]),
                resource_identity_sha256=str(evidence["resource_identity_sha256"]),
            )


__all__ = ["SharedRenderCacheStats", "SharedRenderResourceCache"]
