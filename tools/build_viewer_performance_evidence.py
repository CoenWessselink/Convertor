from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import platform
import tempfile
import time

import numpy as np

from cws_convertor.product import APP_VERSION
from cws_viewer.cache.mesh_cache import MeshCache
from cws_viewer.contracts.geometry import MeshData, TessellationSettings
from cws_viewer.performance import FrameTimeRecorder, LoadingPerformancePolicy


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation" / "performance"


def write(name: str, payload: dict) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def environment() -> dict:
    versions = {}
    for package in ("numpy", "vtk", "PySide6"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "NOT_INSTALLED"
    return {
        "status": "PASS",
        "branch": "BLOCKED_NO_GIT_COMMANDS_USED",
        "commit": "BLOCKED_NO_GIT_COMMANDS_USED",
        "working_tree_clean": "BLOCKED_NO_GIT_COMMANDS_USED",
        "app_version": APP_VERSION,
        "python": platform.python_version(),
        "packages": versions,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cores": os.cpu_count(),
        "performance_policy": LoadingPerformancePolicy.detect(117).to_dict(),
    }


def cache_benchmark() -> dict:
    rng = np.random.default_rng(42)
    fixtures = {"small": 3_000, "medium": 60_000, "large": 300_000}
    rows = []
    with tempfile.TemporaryDirectory(prefix="cws-cache-benchmark-") as directory:
        for fixture_index, (label, vertex_count) in enumerate(fixtures.items(), 1):
            vertices = rng.random((vertex_count, 3), dtype=np.float64)
            triangles = np.arange((vertex_count // 3) * 3, dtype=np.int32).reshape((-1, 3))
            mesh = MeshData(vertices, triangles, "a" * 64, "benchmark", "source_tessellation")
            for mode_index, mode in enumerate(("compressed", "uncompressed"), 1):
                cache = MeshCache(Path(directory) / mode, max_memory_items=0, max_memory_bytes=0, storage_mode=mode)
                key = f"{fixture_index}{mode_index}" * 32
                started = time.perf_counter()
                path = cache.put(key, mesh, provider_version="benchmark", settings=TessellationSettings())
                write_ms = (time.perf_counter() - started) * 1000.0
                started = time.perf_counter()
                loaded = cache.get(key)
                read_ms = (time.perf_counter() - started) * 1000.0
                rows.append({"fixture": label, "mode": mode, "write_ms": write_ms, "read_ms": read_ms, "bytes": path.stat().st_size, "valid": loaded is not None})
    return {"status": "PASS" if all(row["valid"] for row in rows) else "FAIL", "rows": rows}


def frame_benchmark() -> dict:
    recorder = FrameTimeRecorder()
    for value in (8.0, 10.0, 12.0, 16.0, 18.0, 25.0, 34.0):
        recorder.record(value)
    return {"status": "PASS", "synthetic_contract_only": True, **recorder.to_dict()}


def main() -> int:
    env = environment()
    cache = cache_benchmark()
    frames = frame_benchmark()
    write("ENVIRONMENT.json", env)
    write("BASELINE_LOAD.json", {"status": "BLOCKED", "fixture": "historical acceptance", "geometry_ready": 4, "geometry_total": 117, "elapsed_seconds": 102, "reason": "Must be remeasured on current packaged GUI"})
    write("BASELINE_INTERACTION.json", {"status": "NOT_TESTED", "reason": "Live baseline GUI recording required"})
    write("BASELINE_RENDER.json", {"status": "NOT_TESTED", "reason": "Same-camera baseline capture required"})
    write("OPTIMIZED_LOAD.json", {"status": "NOT_TESTED", "implemented": ["dynamic worker policy", "persistent worker pool", "priority scheduling", "MeshCache V2", "bounded upload queue"], "reason": "Packaged real-model benchmark required"})
    write("OPTIMIZED_INTERACTION.json", {"status": "NOT_TESTED", "implemented": ["coalesced 60 Hz navigation", "adaptive MSAA", "bounded frame telemetry"], "contract_benchmark": frames})
    write("OPTIMIZED_RENDER.json", {"status": "NOT_TESTED", "implemented": ["realistic preset", "idle PBR/Phong quality", "adaptive SSAO", "source colours"], "reason": "Visual packaged comparison required"})
    write("CACHE_BENCHMARK.json", cache)
    write("WORKER_BENCHMARK.json", {"status": "NOT_TESTED", "reason": "Requires real IFC runs at 1, 2, 4 and 6 workers"})
    write("MSAA_BENCHMARK.json", {"status": "NOT_TESTED", "interactive_samples": 2, "idle_samples": 8})
    write("FRAME_TIME_BENCHMARK.json", frames)
    acceptance = {"status": "FAILED", "required_fail": 0, "required_not_tested": 8, "required_blocked": 3, "source_components_implemented": True, "final_pass": False, "reason": "Real Windows GUI, one-folder, fresh portable and Trimble comparison evidence is not yet measured"}
    write("PERFORMANCE_ACCEPTANCE.json", acceptance)
    report = """# CWS Viewer Performance Optimization Report

## Current status

`FAILED` for final acceptance because required packaged and live measurements remain `NOT_TESTED` or `BLOCKED`.

## Implemented

- Hardware-aware persistent IFC worker policy.
- Priority-scheduled concurrent geometry loading.
- MeshCache V2 with bounded RAM cache, integrity and uncompressed fast-open mode.
- Generation-safe bounded scene upload queue.
- Navigation frame-time telemetry and adaptive interactive/idle MSAA.
- One-click realistic render preset using source colours.

## Evidence boundary

No Trimble parity, packaged GUI speed or final visual-quality claim is made without a real measurement.
"""
    (OUTPUT / "PERFORMANCE_COMPARISON.md").write_text(report, encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "cache_status": cache["status"], "acceptance": acceptance["status"]}, indent=2))
    return 0 if cache["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
