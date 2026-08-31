"""Session-persistent, crash-recovering geometry worker pool."""
from __future__ import annotations

import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import Callable, Iterable

from cws_viewer.contracts.geometry import (
    GeometryProvider,
    GeometryRequest,
    MeshData,
    TessellationSettings,
)
from cws_viewer.geometry.isolated import IsolatedIfcMeshProvider


class PersistentGeometryWorkerPool:
    """Bounded provider pool that survives project reopen and replaces failed workers."""

    provider_version = "ifc-isolated-pool-v1"
    _shared_lock = threading.RLock()
    _shared: dict[tuple[int, object], "PersistentGeometryWorkerPool"] = {}

    def __init__(
        self,
        worker_count: int,
        *,
        provider_factory: Callable[[], GeometryProvider] = IsolatedIfcMeshProvider,
    ) -> None:
        self.worker_count = max(1, min(8, int(worker_count)))
        self._provider_factory = provider_factory
        self._providers = [provider_factory() for _ in range(self.worker_count)]
        self._locks = [threading.Lock() for _ in range(self.worker_count)]
        self._executor = ThreadPoolExecutor(
            max_workers=self.worker_count,
            thread_name_prefix="CWS-GeometryWorker",
        )
        self._next_worker = 0
        self._selection_lock = threading.Lock()
        self._lifecycle_lock = threading.RLock()
        self._closed = False
        self._persistent_session_provider = False
        self.completed_requests = 0
        self.failed_requests = 0
        self.restarted_workers = 0
        self.retry_successes = 0
        self._last_dispatch_worker_count = 0

    @classmethod
    def shared(
        cls,
        worker_count: int,
        *,
        provider_factory: Callable[[], GeometryProvider] = IsolatedIfcMeshProvider,
    ) -> "PersistentGeometryWorkerPool":
        """Return one bounded pool for the current application session."""
        count = max(1, min(8, int(worker_count)))
        key = (count, provider_factory)
        with cls._shared_lock:
            pool = cls._shared.get(key)
            if pool is None or pool._closed:
                pool = cls(count, provider_factory=provider_factory)
                pool._persistent_session_provider = True
                cls._shared[key] = pool
            return pool

    @classmethod
    def shutdown_shared(cls) -> None:
        with cls._shared_lock:
            pools = tuple(cls._shared.values())
            cls._shared.clear()
        for pool in pools:
            pool.close(force=True)

    @property
    def persistent_session_provider(self) -> bool:
        return bool(self._persistent_session_provider)

    def supports(self, request: GeometryRequest) -> bool:
        with self._lifecycle_lock:
            if self._closed or not self._providers:
                return False
            return bool(self._providers[0].supports(request))

    def _claim_worker(self) -> int:
        with self._selection_lock:
            if self._closed:
                raise RuntimeError("Geometry-workerpool is gesloten")
            index = self._next_worker % self.worker_count
            self._next_worker += 1
            return index

    def _replace_worker(self, index: int) -> None:
        old = self._providers[index]
        close = getattr(old, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
        self._providers[index] = self._provider_factory()
        self.restarted_workers += 1

    def _load_on_worker(
        self,
        index: int,
        request: GeometryRequest,
        settings: TessellationSettings,
        *,
        cancel_check=None,
    ) -> MeshData:
        with self._locks[index]:
            if cancel_check:
                cancel_check()
            try:
                mesh = self._providers[index].load(
                    request,
                    settings,
                    cancel_check=cancel_check,
                )
            except Exception:
                self.failed_requests += 1
                self._replace_worker(index)
                if cancel_check:
                    cancel_check()
                try:
                    mesh = self._providers[index].load(
                        request,
                        settings,
                        cancel_check=cancel_check,
                    )
                except Exception:
                    self.failed_requests += 1
                    raise
                self.retry_successes += 1
            self.completed_requests += 1
            return mesh

    def _load_many_on_worker(
        self,
        index: int,
        requests: tuple[GeometryRequest, ...],
        settings: TessellationSettings,
        *,
        cancel_check=None,
    ) -> dict[str, MeshData]:
        with self._locks[index]:
            if cancel_check:
                cancel_check()
            provider = self._providers[index]
            try:
                load_many = getattr(provider, "load_many", None)
                if callable(load_many):
                    meshes = load_many(requests, settings, cancel_check=cancel_check)
                else:
                    meshes = {
                        request.geometry_id: provider.load(request, settings, cancel_check=cancel_check)
                        for request in requests
                    }
                self.completed_requests += len(meshes)
                return dict(meshes)
            except Exception:
                self.failed_requests += len(requests)
                self._replace_worker(index)
                provider = self._providers[index]
                load_many = getattr(provider, "load_many", None)
                if callable(load_many):
                    meshes = load_many(requests, settings, cancel_check=cancel_check)
                else:
                    meshes = {
                        request.geometry_id: provider.load(request, settings, cancel_check=cancel_check)
                        for request in requests
                    }
                self.retry_successes += len(meshes)
                self.completed_requests += len(meshes)
                return dict(meshes)

    def load(
        self,
        request: GeometryRequest,
        settings: TessellationSettings,
        *,
        cancel_check=None,
    ) -> MeshData:
        return self._load_on_worker(
            self._claim_worker(),
            request,
            settings,
            cancel_check=cancel_check,
        )

    def load_many(
        self,
        requests: Iterable[GeometryRequest],
        settings: TessellationSettings,
        *,
        cancel_check=None,
    ) -> dict[str, MeshData]:
        values = tuple(requests)
        if not values:
            return {}
        # Keep entities from one source together. Round-robin distribution made
        # every child parse the complete IFC independently.
        source_groups: dict[tuple[str, str, str], list[GeometryRequest]] = {}
        for request in values:
            key = (str(request.source_path), str(request.source_sha256), str(request.source_format))
            source_groups.setdefault(key, []).append(request)
        chunks: list[list[GeometryRequest]] = [[] for _ in range(self.worker_count)]
        loads = [0 for _ in range(self.worker_count)]
        for group in sorted(source_groups.values(), key=lambda item: (-len(item), item[0].source_path)):
            index = min(range(self.worker_count), key=lambda value: (loads[value], value))
            chunks[index].extend(group)
            loads[index] += len(group)
        futures = [
            self._executor.submit(
                self._load_many_on_worker,
                index,
                tuple(chunk),
                settings,
                cancel_check=cancel_check,
            )
            for index, chunk in enumerate(chunks)
            if chunk
        ]
        self._last_dispatch_worker_count = len(futures)
        result: dict[str, MeshData] = {}
        for future in as_completed(futures):
            result.update(future.result())
        return result

    def diagnostics(self) -> dict[str, object]:
        worker_processes = [
            getattr(provider, "diagnostics", lambda: {"transport_mode": "unknown"})()
            for provider in self._providers
        ]
        process_ids = sorted(
            {
                int(item["worker_pid"])
                for item in worker_processes
                if item.get("worker_pid") and item.get("worker_alive")
            }
        )
        return {
            "transport": "persistent_ifc_process_worker_pool_v3",
            "dispatcher": "bounded_thread_dispatcher",
            "worker_count": self.worker_count,
            "dispatch_worker_count": int(self._last_dispatch_worker_count),
            "active_process_count": len(process_ids),
            "active_process_ids": process_ids,
            "worker_processes": worker_processes,
            "completed_requests": self.completed_requests,
            "failed_requests": self.failed_requests,
            "restarted_workers": self.restarted_workers,
            "retry_successes": self.retry_successes,
            "session_shared": self.persistent_session_provider,
            "closed": self._closed,
        }

    def close(self, *, force: bool = False) -> None:
        if self._persistent_session_provider and not force:
            return
        with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True
            self._executor.shutdown(wait=True, cancel_futures=True)
            for provider in self._providers:
                close = getattr(provider, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass


atexit.register(PersistentGeometryWorkerPool.shutdown_shared)

__all__ = ["PersistentGeometryWorkerPool"]
