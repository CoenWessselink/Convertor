"""Process-local render geometry cache shared by every Viewer window.

Each render window deliberately retains its own actors, selection arrays and
OpenGL state.  Immutable VTK polydata and feature-edge resources are shared by
identity for viewers backed by the exact same :class:`MeshRepository`.  This
prevents a detached BOM Viewer from rebuilding and duplicating source geometry
while preserving independent cameras and safe renderer lifetimes.
"""
from __future__ import annotations

from dataclasses import dataclass
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
                bucket = {"polydata": {}, "features": {}, "hits": 0, "misses": 0}
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
            if geometry_ids is None:
                bucket["polydata"].clear()
                bucket["features"].clear()
                return
            requested = {str(value) for value in geometry_ids}
            for key in tuple(bucket["polydata"]):
                if any(
                    key == value or key.startswith(value + "|") or key.endswith("|" + value)
                    for value in requested
                ):
                    bucket["polydata"].pop(key, None)
            # Edge keys start with the geometry identity used to build them.
            for key in tuple(bucket["features"]):
                if any(
                    key == value or key.startswith(value + "|") or key.endswith("|" + value)
                    for value in requested
                ):
                    bucket["features"].pop(key, None)

    @classmethod
    def stats(cls, repository: Any) -> SharedRenderCacheStats:
        bucket = cls._bucket(repository)
        with cls._lock:
            return SharedRenderCacheStats(
                repository_identity=id(repository),
                polydata_items=len(bucket["polydata"]),
                feature_items=len(bucket["features"]),
                hits=int(bucket["hits"]), misses=int(bucket["misses"]),
            )


__all__ = ["SharedRenderCacheStats", "SharedRenderResourceCache"]
