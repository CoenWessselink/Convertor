from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np

from cws_convertor.viewer.progressive_loader import ProgressiveMeshLoadPlan, VIEWPORT_PRIORITY_NAMES
from cws_convertor.viewer.scene_upload import SceneUploadBudget
from cws_viewer.cache.mesh_cache import MeshCache
from cws_viewer.contracts.geometry import GeometryRequest, MeshData, TessellationSettings
from cws_viewer.geometry.worker_pool import PersistentGeometryWorkerPool
from cws_viewer.performance.policy import LoadingPerformancePolicy


class _SyntheticProvider:
    def __init__(self, delay_s: float = 0.02) -> None:
        self.delay_s = delay_s

    def load(
        self,
        request: GeometryRequest,
        settings: TessellationSettings,
        *,
        cancel_check=None,
    ) -> MeshData:
        if cancel_check is not None:
            cancel_check()
        time.sleep(self.delay_s)
        vertices = np.asarray(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            dtype=np.float64,
        )
        triangles = np.asarray([[0, 1, 2]], dtype=np.int32)
        return MeshData(
            vertices=vertices,
            triangles=triangles,
            source_geometry_hash=request.source_geometry_hash,
            provider="loader-v2-synthetic",
            metadata={"geometry_id": request.geometry_id, "settings": settings.to_dict()},
        )


@dataclass(frozen=True)
class _UploadResource:
    byte_length: int


def _measure_pool(worker_count: int, request_count: int = 8) -> tuple[float, dict[str, Any]]:
    requests = [
        GeometryRequest(
            geometry_id=f"part-{index:02d}",
            source_geometry_hash=f"{index + 1:064x}",
            source_format="IFC",
            source_file_id=f"synthetic-loader-v2-{index:02d}",
            source_path=f"synthetic-{index:02d}.ifc",
            source_sha256=f"{index + 100:064x}",
            source_entity_id=f"part-{index:02d}",
            source_path_verified=True,
        )
        for index in range(request_count)
    ]
    pool = PersistentGeometryWorkerPool(worker_count, provider_factory=_SyntheticProvider)
    started = time.perf_counter()
    results = pool.load_many(requests, TessellationSettings())
    elapsed = time.perf_counter() - started
    diagnostics = pool.diagnostics()
    pool.close()
    if len(results) != request_count:
        raise RuntimeError("persistent worker pool returned an incomplete result set")
    return elapsed, diagnostics


def _priority_probe() -> tuple[bool, list[str], dict[str, int]]:
    ids = tuple(f"part-{index}" for index in range(7))
    plan = ProgressiveMeshLoadPlan(ids, patch_batch_size=1, max_in_flight=1)
    plan.update_viewport_context(
        selected=(ids[0],),
        under_cursor=(ids[1],),
        visible=(ids[2],),
        near_camera=(ids[3],),
        large_silhouette=(ids[4],),
        current_assembly=(ids[5],),
        camera_distances={ids[2]: 20.0, ids[3]: 5.0, ids[4]: 10.0, ids[5]: 15.0},
    )
    observed: list[str] = []
    while not plan.is_finished:
        batch = plan.claim()
        if not batch:
            break
        observed.extend(batch)
        for entity_id in batch:
            plan.mark_loaded(entity_id)
    expected = list(ids)
    manifest = plan.manifest()
    return observed == expected, observed, dict(manifest.get("priority_counts", {}))


def _is_mmap_backed(value: np.ndarray) -> bool:
    current: Any = value
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        if isinstance(current, np.memmap):
            return True
        seen.add(id(current))
        current = getattr(current, "base", None)
    return False


def _cache_probe(root: Path) -> dict[str, Any]:
    triangle_count = 10_000
    vertices = np.zeros((triangle_count * 3, 3), dtype=np.float64)
    base = np.arange(triangle_count, dtype=np.float64)
    vertices[0::3, 0] = base
    vertices[1::3, 0] = base + 0.75
    vertices[2::3, 0] = base
    vertices[2::3, 1] = 0.75
    triangles = np.arange(triangle_count * 3, dtype=np.int32).reshape((-1, 3))
    mesh = MeshData(
        vertices=vertices,
        triangles=triangles,
        source_geometry_hash="2" * 64,
        provider="loader-v2-cache-probe",
        metadata={"probe": True},
    )
    cache = MeshCache(root, storage_mode="mmap")
    key = "3" * 64
    started = time.perf_counter()
    cache.put(
        key,
        mesh,
        provider_version="loader-v2-probe-1",
        settings=TessellationSettings(),
    )
    write_ms = (time.perf_counter() - started) * 1000.0
    cache.clear_memory()
    started = time.perf_counter()
    restored = cache.get(key)
    cold_read_ms = (time.perf_counter() - started) * 1000.0
    started = time.perf_counter()
    warm = cache.get(key)
    warm_read_ms = (time.perf_counter() - started) * 1000.0
    if restored is None or warm is None:
        raise RuntimeError("memory-mapped Cache V2 probe missed")
    return {
        "storage_mode": cache.storage_mode,
        "write_ms": round(write_ms, 3),
        "cold_read_ms": round(cold_read_ms, 3),
        "warm_read_ms": round(warm_read_ms, 3),
        "vertices_mmap": _is_mmap_backed(restored.vertices),
        "triangles_mmap": _is_mmap_backed(restored.triangles),
        "normal_count": int(restored.normals.shape[0]) if restored.normals is not None else 0,
        "feature_edge_count": int(restored.feature_edges.shape[0]) if restored.feature_edges is not None else 0,
        "lod_levels": len(restored.lod_triangles),
        "bounds": restored.bounds is not None,
    }


def _upload_probe() -> dict[str, Any]:
    queue = deque((f"resource-{index}", _UploadResource(2 * 1024**2)) for index in range(10))
    budget = SceneUploadBudget(max_ms=6.0, max_resources=4, max_bytes=5 * 1024**2)
    first = budget.take(queue)
    budget.record_frame(first, 8.5)
    second = budget.take(queue)
    budget.record_frame(second, 2.0)
    return {
        "first_frame_resources": len(first),
        "second_frame_resources": len(second),
        "remaining": len(queue),
        "telemetry": budget.telemetry(),
    }


def run_probe(output_path: Path | str, *, require_frozen: bool = True) -> dict[str, Any]:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frozen = bool(getattr(sys, "frozen", False))
    policy = LoadingPerformancePolicy.detect(geometry_count=400, source_format="ifc")
    workers = max(2, min(4, policy.worker_count))

    serial_s, serial_diagnostics = _measure_pool(1)
    parallel_s, parallel_diagnostics = _measure_pool(workers)
    speedup = serial_s / max(parallel_s, 1e-9)
    priority_ok, observed_priority, priority_counts = _priority_probe()
    with tempfile.TemporaryDirectory(prefix="cws-loader-v2-") as temporary:
        cache = _cache_probe(Path(temporary))
    upload = _upload_probe()

    gates = {
        "packaged_execution": (not require_frozen) or frozen,
        "hardware_adaptive_policy": policy.worker_count >= 2 and policy.cache_memory_bytes > 0,
        "persistent_worker_pool": parallel_diagnostics.get("completed_requests", 0) == 8,
        "parallel_speedup": speedup >= 1.20,
        "viewport_priority_order": priority_ok and tuple(VIEWPORT_PRIORITY_NAMES) == (
            "selected",
            "under_cursor",
            "visible",
            "near_camera",
            "large_silhouette",
            "current_assembly",
            "rest",
        ),
        "cache_v2_mmap": cache["storage_mode"] == "mmap" and cache["vertices_mmap"] and cache["triangles_mmap"],
        "cache_v2_render_resources": cache["normal_count"] > 0 and cache["feature_edge_count"] > 0 and cache["lod_levels"] >= 2 and bool(cache["bounds"]),
        "bounded_scene_upload": upload["first_frame_resources"] == 2 and upload["remaining"] > 0,
    }
    passed = sum(bool(value) for value in gates.values())
    result = {
        "schema": "cws.loader-engine-v2.performance-evidence.v1",
        "status": "PASS" if passed == len(gates) else "FAIL",
        "packaged": frozen,
        "executable": sys.executable,
        "policy": policy.to_dict(),
        "worker_pool": {
            "workers": workers,
            "requests": 8,
            "serial_ms": round(serial_s * 1000.0, 3),
            "parallel_ms": round(parallel_s * 1000.0, 3),
            "speedup": round(speedup, 3),
            "serial_diagnostics": serial_diagnostics,
            "parallel_diagnostics": parallel_diagnostics,
        },
        "viewport_priority": {
            "bands": list(VIEWPORT_PRIORITY_NAMES),
            "observed_order": observed_priority,
            "counts": priority_counts,
        },
        "cache_v2": cache,
        "scene_upload": upload,
        "gates": gates,
        "summary": {"passed": passed, "total": len(gates)},
    }
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    return result
