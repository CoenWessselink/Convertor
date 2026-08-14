"""Measured V1 renderer benchmark shared by local validation and Windows CI."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib
import math
from pathlib import Path
import platform
import statistics
import time
from typing import Any, Iterable

import psutil

from cws_viewer.math3d import Vector3
from cws_viewer.technology.contracts import TechnologyBackendName
from cws_viewer.technology.fixtures import (
    build_box_grid_scene,
    deterministic_pick_indices,
)
from cws_viewer.technology.host import TkNativeWindowHost
from cws_viewer.technology.metrics import BackendCaseResult, LatencySummary


def _rss_mib() -> float:
    return psutil.Process().memory_info().rss / (1024 * 1024)


def _latency(values_seconds: Iterable[float]) -> LatencySummary:
    values_ms = sorted(float(value) * 1000.0 for value in values_seconds)
    if not values_ms:
        return LatencySummary(0, 0.0, 0.0, 0.0, 0.0)
    p95_index = min(len(values_ms) - 1, max(0, math.ceil(len(values_ms) * 0.95) - 1))
    return LatencySummary(
        samples=len(values_ms),
        minimum_ms=round(values_ms[0], 6),
        median_ms=round(statistics.median(values_ms), 6),
        p95_ms=round(values_ms[p95_index], 6),
        maximum_ms=round(values_ms[-1], 6),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _import_backend(name: TechnologyBackendName) -> tuple[Any, float]:
    started = time.perf_counter()
    if name == TechnologyBackendName.VTK_MESH:
        module = importlib.import_module("cws_viewer.backends.vtk_mesh")
        backend = module.VtkMeshSpikeBackend(offscreen=True)
    elif name == TechnologyBackendName.OCCT_AIS:
        module = importlib.import_module("cws_viewer.backends.occt_ais")
        backend = module.OcctAisSpikeBackend()
    else:  # pragma: no cover - enum prevents this
        raise ValueError(name)
    return backend, time.perf_counter() - started


def run_backend_case(
    backend_name: TechnologyBackendName | str,
    node_count: int,
    *,
    output_dir: str | Path,
    width: int = 960,
    height: int = 720,
    orbit_frames: int = 20,
    pick_samples: int = 50,
) -> BackendCaseResult:
    """Run one isolated backend/count case and return machine-readable evidence."""

    name = TechnologyBackendName(backend_name)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    screenshot = output / f"{name.value}_{node_count:05d}.png"
    rss_before_import = _rss_mib()
    backend: Any | None = None
    host: TkNativeWindowHost | None = None
    stage_rss = [rss_before_import]
    try:
        backend, import_seconds = _import_backend(name)
        rss_after_import = _rss_mib()
        stage_rss.append(rss_after_import)

        native_window = None
        init_started = time.perf_counter()
        if name == TechnologyBackendName.OCCT_AIS:
            host = TkNativeWindowHost(width=width, height=height)
            native_window = host.open()
        backend.initialize(
            width=width,
            height=height,
            native_window=native_window,
        )
        if host is not None:
            host.process_events()
        initialize_seconds = time.perf_counter() - init_started
        rss_after_initialize = _rss_mib()
        stage_rss.append(rss_after_initialize)

        scene = build_box_grid_scene(node_count)
        build_started = time.perf_counter()
        backend.load_scene(scene)
        scene_build_seconds = time.perf_counter() - build_started
        rss_after_scene = _rss_mib()
        stage_rss.append(rss_after_scene)

        backend.set_isometric_view()
        backend.fit_all()
        frame_started = time.perf_counter()
        backend.render()
        if host is not None:
            host.process_events()
        first_frame_seconds = time.perf_counter() - frame_started
        stage_rss.append(_rss_mib())

        orbit_times: list[float] = []
        for _ in range(max(1, orbit_frames)):
            backend.orbit_step(1.5)
            started = time.perf_counter()
            backend.render()
            if host is not None:
                host.process_events()
            orbit_times.append(time.perf_counter() - started)

        backend.set_top_view()
        backend.fit_all()
        backend.render()
        if host is not None:
            host.process_events()
        picks: list[float] = []
        success = 0
        indices = deterministic_pick_indices(node_count, pick_samples)
        for index in indices:
            instance = scene.instances[index]
            x, y = backend.world_to_display(instance.center)
            started = time.perf_counter()
            picked = backend.pick_at(x, y)
            picks.append(time.perf_counter() - started)
            if picked == instance.node_id:
                success += 1

        clip_started = time.perf_counter()
        backend.set_clip_plane(origin=scene.bounds.center, normal=Vector3(1.0, 0.0, 0.0))
        backend.render()
        if host is not None:
            host.process_events()
        clip_seconds = time.perf_counter() - clip_started
        stage_rss.append(_rss_mib())

        backend.clear_clip_planes()
        backend.set_isometric_view()
        backend.fit_all()
        backend.render()
        if host is not None:
            host.process_events()
        path = backend.capture_png(screenshot)
        stage_rss.append(_rss_mib())
        capability = backend.capabilities()
        peak_rss = max(stage_rss)
        return BackendCaseResult(
            backend=name,
            node_count=node_count,
            status="passed",
            backend_version=capability.backend_version,
            import_ms=round(import_seconds * 1000.0, 6),
            initialize_ms=round(initialize_seconds * 1000.0, 6),
            scene_build_ms=round(scene_build_seconds * 1000.0, 6),
            first_frame_ms=round(first_frame_seconds * 1000.0, 6),
            orbit_latency=_latency(orbit_times),
            pick_latency=_latency(picks),
            pick_success_rate=round(success / len(indices), 6),
            clip_render_ms=round(clip_seconds * 1000.0, 6),
            rss_before_import_mib=round(rss_before_import, 3),
            rss_after_import_mib=round(rss_after_import, 3),
            rss_after_initialize_mib=round(rss_after_initialize, 3),
            rss_after_scene_mib=round(rss_after_scene, 3),
            peak_rss_mib=round(peak_rss, 3),
            peak_delta_mib=round(peak_rss - rss_before_import, 3),
            screenshot_path=str(path),
            screenshot_sha256=_sha256(path),
            screenshot_bytes=path.stat().st_size,
            scene_hash=scene.geometry_hash,
            notes=(
                f"host={'tk-native' if host is not None else 'offscreen-render-window'}",
                f"platform={platform.platform()}",
                f"pick_samples={len(indices)}",
                f"orbit_frames={len(orbit_times)}",
            ),
        )
    except Exception as exc:
        peak = max(stage_rss or [rss_before_import])
        return BackendCaseResult(
            backend=name,
            node_count=node_count,
            status="failed",
            backend_version="",
            import_ms=0.0,
            initialize_ms=0.0,
            scene_build_ms=0.0,
            first_frame_ms=0.0,
            orbit_latency=_latency(()),
            pick_latency=_latency(()),
            pick_success_rate=0.0,
            clip_render_ms=0.0,
            rss_before_import_mib=round(rss_before_import, 3),
            rss_after_import_mib=round(stage_rss[-1], 3),
            rss_after_initialize_mib=round(stage_rss[-1], 3),
            rss_after_scene_mib=round(stage_rss[-1], 3),
            peak_rss_mib=round(peak, 3),
            peak_delta_mib=round(peak - rss_before_import, 3),
            screenshot_path="",
            screenshot_sha256="",
            screenshot_bytes=0,
            scene_hash="",
            notes=(f"platform={platform.platform()}",),
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if backend is not None:
            try:
                backend.dispose()
            except Exception:
                pass
        if host is not None:
            host.close()


__all__ = ["run_backend_case"]
