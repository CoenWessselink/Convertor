"""Exact progressive IFC preview for the canonical CWS desktop intake path."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import time
from typing import Callable

from cws_viewer.cache import MeshCache
from cws_viewer.contracts.geometry import TessellationSettings
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.core.real_performance_evidence import build_requests, _scene
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.geometry.worker_pool import PersistentGeometryWorkerPool
from cws_viewer.performance import LoadingPerformancePolicy


@dataclass(frozen=True, slots=True)
class RawIfcPreviewResult:
    source_path: Path
    scene: ProjectScene
    repository: MeshRepository
    request_count: int
    physical_object_count: int
    exact_mesh_count: int
    cache_hit_count: int
    elapsed_seconds: float


_CACHE_LOCK = threading.RLock()
_SESSION_CACHES: dict[str, MeshCache] = {}


def _session_cache(root: Path, request_count: int, cache_bytes: int) -> MeshCache:
    identity = str(root).casefold()
    with _CACHE_LOCK:
        cache = _SESSION_CACHES.get(identity)
        if cache is None:
            cache = MeshCache(
                root,
                max_memory_items=max(128, min(request_count * 2, 4096)),
                max_memory_bytes=cache_bytes,
            )
            _SESSION_CACHES[identity] = cache
        return cache


def load_exact_ifc_preview(
    source_path: str | Path,
    *,
    cache_root: str | Path | None = None,
    progress: Callable[[int, str], None] | None = None,
    cancel_check: Callable[[], None] | None = None,
) -> RawIfcPreviewResult:
    """Load every physical IFC object exactly, before semantic import completes."""

    started = time.perf_counter()
    source = Path(source_path).expanduser().resolve(strict=True)
    emit = progress or (lambda _percent, _message: None)
    check = cancel_check or (lambda: None)
    check()
    emit(4, "IFC-objecten, plaatsingen en geometrie-identiteiten lezen")
    requests = build_requests(source, 2_147_483_647)
    check()
    policy = LoadingPerformancePolicy.detect(len(requests), source_format="IFC")
    settings = TessellationSettings()
    pool = PersistentGeometryWorkerPool.shared(policy.worker_count)
    pool.prewarm()
    version = pool.provider_version
    root = Path(cache_root or Path.home() / ".cws_convertor" / "viewer_mesh_cache").expanduser().resolve()
    cache = _session_cache(root, len(requests), policy.cache_memory_bytes)
    keys = {request.geometry_id: request.cache_key(settings, version) for request in requests}
    emit(22, f"MeshCache V2 controleren voor {len(requests):,} unieke geometrieen")
    cached = cache.get_many(keys.values(), max_workers=policy.cache_prefetch_workers)
    meshes = {
        request.geometry_id: cached[keys[request.geometry_id]]
        for request in requests
        if keys[request.geometry_id] in cached
    }
    misses = tuple(request for request in requests if request.geometry_id not in meshes)
    check()
    if misses:
        emit(34, f"Exacte IFC-geometrie laden: {len(misses):,} cache-misses")
        meshes.update(pool.load_many(misses, settings, cancel_check=check))
    if len(meshes) != len(requests):
        missing = len(requests) - len(meshes)
        raise RuntimeError(f"Exacte IFC-preview mist {missing:,} geometrieen")
    invalid = tuple(
        geometry_id
        for geometry_id, mesh in meshes.items()
        if str(getattr(mesh, "exactness", "")) == "display_proxy"
    )
    if invalid:
        raise RuntimeError(f"Exacte IFC-preview bevat {len(invalid):,} display-proxies")
    if misses:
        cache.put_many_async(
            (
                keys[request.geometry_id],
                meshes[request.geometry_id],
                version,
                settings,
            )
            for request in misses
        )
    check()
    emit(82, "Alle exacte meshes binden aan fysieke IFC-objecten")
    scene, repository, metrics = _scene(requests, meshes)
    physical_count = sum(
        int(request.metadata_dict.get("physical_instance_count", "1") or 1)
        for request in requests
    )
    if len(scene.nodes) != physical_count:
        raise RuntimeError(
            f"IFC-previewbinding onvolledig: {len(scene.nodes):,}/{physical_count:,} objecten"
        )
    if int(metrics.get("node_count", 0)) != physical_count:
        raise RuntimeError("IFC-previewmeting en scene-objecttelling verschillen")
    emit(100, f"Exacte bronpreview gereed: {physical_count:,} objecten")
    return RawIfcPreviewResult(
        source_path=source,
        scene=scene,
        repository=repository,
        request_count=len(requests),
        physical_object_count=physical_count,
        exact_mesh_count=len(meshes),
        cache_hit_count=len(requests) - len(misses),
        elapsed_seconds=time.perf_counter() - started,
    )


__all__ = ["RawIfcPreviewResult", "load_exact_ifc_preview"]
