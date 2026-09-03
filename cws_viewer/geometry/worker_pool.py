"""Session-persistent, crash-recovering geometry worker pool."""
from __future__ import annotations

import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
import hashlib
import math
import os
from pathlib import Path
import tempfile
import threading
from typing import Callable, Iterable

from cws_viewer.contracts.geometry import (
    GeometryProvider,
    GeometryRequest,
    MeshData,
    TessellationSettings,
)
from cws_viewer.geometry.isolated import IsolatedIfcMeshProvider


_SOURCE_MIRROR_LOCK = threading.RLock()
_SOURCE_MIRROR_MAX_FILES = 32
_SOURCE_MIRROR_MAX_BYTES = 4 * 1024**3


def _source_mirror_root() -> Path:
    configured = str(os.environ.get("CWS_VIEWER_SOURCE_MIRROR_ROOT", "")).strip()
    if configured:
        return Path(configured).expanduser().resolve()
    local_data = str(os.environ.get("LOCALAPPDATA", "")).strip()
    base = Path(local_data) if local_data else Path(tempfile.gettempdir())
    return (base / "CWS Convertor" / "ViewerSourceMirrorV2").resolve()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _prune_source_mirror(root: Path, keep: Path) -> None:
    files = sorted(
        (item for item in root.iterdir() if item.is_file() and not item.name.endswith(".tmp")),
        key=lambda item: item.stat().st_mtime_ns,
        reverse=True,
    )
    total = 0
    retained = 0
    for item in files:
        size = int(item.stat().st_size)
        if item == keep or (retained < _SOURCE_MIRROR_MAX_FILES and total + size <= _SOURCE_MIRROR_MAX_BYTES):
            total += size
            retained += 1
            continue
        try:
            item.unlink()
        except OSError:
            pass


def _stage_ifc_source(source_path: str, source_sha256: str) -> Path:
    """Return an atomic, content-addressed local mirror of one IFC source."""
    source = Path(source_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"IFC-bronbestand ontbreekt: {source}")
    root = _source_mirror_root()
    suffix = source.suffix.lower() if source.suffix else ".ifc"
    target = root / f"{source_sha256.lower()}{suffix}"
    if source == target:
        return target

    with _SOURCE_MIRROR_LOCK:
        root.mkdir(parents=True, exist_ok=True)
        if target.is_file() and _sha256_file(target) == source_sha256.lower():
            os.utime(target, None)
            return target
        target.unlink(missing_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{target.stem}.", suffix=".tmp", dir=root)
        temp_path = Path(temp_name)
        digest = hashlib.sha256()
        try:
            with source.open("rb") as input_stream, os.fdopen(descriptor, "wb") as output_stream:
                while True:
                    chunk = input_stream.read(1024 * 1024)
                    if not chunk:
                        break
                    output_stream.write(chunk)
                    digest.update(chunk)
                output_stream.flush()
                os.fsync(output_stream.fileno())
            actual = digest.hexdigest()
            if actual != source_sha256.lower():
                raise RuntimeError(
                    f"IFC-source mirror hash wijkt af: verwacht {source_sha256}, ontvangen {actual}"
                )
            os.replace(temp_path, target)
        finally:
            temp_path.unlink(missing_ok=True)
        _prune_source_mirror(root, target)
        return target


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
        self.last_errors: list[str] = []
        self._last_dispatch_worker_count = 0
        self._last_source_group_count = 0
        self._last_source_shard_count = 0
        self._last_split_source_group_count = 0

    def _record_error(self, exc: BaseException) -> None:
        message = f"{type(exc).__name__}: {exc}"
        with self._lifecycle_lock:
            self.last_errors.append(message)
            del self.last_errors[:-8]

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

    def prewarm(self) -> None:
        """Start every isolated IFC process concurrently before file-open work."""
        futures = []
        for provider in self._providers:
            warm = getattr(provider, "prewarm", None)
            if callable(warm):
                futures.append(self._executor.submit(warm))
        for future in futures:
            future.result()

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
            except Exception as exc:
                self._record_error(exc)
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
                except Exception as exc:
                    self._record_error(exc)
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
            except Exception as exc:
                self._record_error(exc)
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
        mirrored_sources: dict[tuple[str, str], str] = {}
        mirrored_values: list[GeometryRequest] = []
        for request in values:
            if request.source_format.upper() != "IFC" or not Path(request.source_path).is_file():
                mirrored_values.append(request)
                continue
            source_key = (str(request.source_path), str(request.source_sha256))
            mirror = mirrored_sources.get(source_key)
            if mirror is None:
                mirror = str(_stage_ifc_source(*source_key))
                mirrored_sources[source_key] = mirror
            metadata = request.metadata_dict
            metadata["ifc_source_mirror"] = "content_hash_local_v2"
            metadata["ifc_original_source_path"] = str(request.source_path)
            mirrored_values.append(
                replace(
                    request,
                    source_path=mirror,
                    metadata=tuple(sorted(metadata.items())),
                    source_path_verified=True,
                )
            )
        values = tuple(mirrored_values)
        # Keep entities from one source together. Round-robin distribution made
        # every child parse the complete IFC independently.
        source_groups: dict[tuple[str, str, str], list[GeometryRequest]] = {}
        for request in values:
            key = (str(request.source_path), str(request.source_sha256), str(request.source_format))
            source_groups.setdefault(key, []).append(request)
        chunks: list[list[GeometryRequest]] = [[] for _ in range(self.worker_count)]
        loads = [0 for _ in range(self.worker_count)]
        shard_count = 0
        split_group_count = 0
        for group in sorted(source_groups.values(), key=lambda item: (-len(item), item[0].source_path)):
            # A single large IFC is the common production case. Keeping that
            # source as one indivisible group left five of six isolated workers
            # idle while one child tessellated every product. Split only large
            # groups; small sources still benefit from one parsed model/session.
            desired_shards = 1
            if self.worker_count > 1 and len(group) >= 384:
                desired_shards = min(
                    self.worker_count,
                    max(2, math.ceil(len(group) / 384)),
                )
            shard_size = math.ceil(len(group) / desired_shards)
            shards = [
                group[index * shard_size : min(len(group), (index + 1) * shard_size)]
                for index in range(desired_shards)
            ]
            shards = [shard for shard in shards if shard]
            shard_count += len(shards)
            if len(shards) > 1:
                split_group_count += 1
            for shard in shards:
                index = min(range(self.worker_count), key=lambda value: (loads[value], value))
                chunks[index].extend(shard)
                loads[index] += len(shard)
        self._last_source_group_count = len(source_groups)
        self._last_source_shard_count = shard_count
        self._last_split_source_group_count = split_group_count
        active_chunk_count = sum(bool(chunk) for chunk in chunks)
        dispatch_chunks = []
        for chunk in chunks:
            annotated = []
            for request in chunk:
                if request.source_format.upper() == "IFC":
                    metadata = dict(request.metadata)
                    metadata["ifc_dispatch_shards"] = str(active_chunk_count)
                    request = replace(request, metadata=tuple(sorted(metadata.items())))
                annotated.append(request)
            dispatch_chunks.append(annotated)
        futures = [
            self._executor.submit(
                self._load_many_on_worker,
                index,
                tuple(chunk),
                settings,
                cancel_check=cancel_check,
            )
            for index, chunk in enumerate(dispatch_chunks)
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
            "source_group_count": int(self._last_source_group_count),
            "source_shard_count": int(self._last_source_shard_count),
            "split_source_group_count": int(self._last_split_source_group_count),
            "active_process_count": len(process_ids),
            "active_process_ids": process_ids,
            "worker_processes": worker_processes,
            "completed_requests": self.completed_requests,
            "failed_requests": self.failed_requests,
            "restarted_workers": self.restarted_workers,
            "retry_successes": self.retry_successes,
            "last_errors": list(self.last_errors),
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
