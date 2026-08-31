"""Machine-readable Viewer performance evidence without invented results."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
from typing import Any, Iterable


VIEWER_METRIC_SCHEMA = "cws-viewer-performance-evidence-1.0"
METRIC_FIELDS = (
    "shell_visible_ms",
    "first_tree_ms",
    "first_pixels_ms",
    "proxy_scene_ready_ms",
    "first_usable_ms",
    "geometry_ready_ms",
    "exact_25_ms",
    "exact_50_ms",
    "exact_75_ms",
    "exact_100_ms",
    "exact_ready_ms",
    "frame_p50_ms",
    "frame_p95_ms",
    "frame_p99_ms",
    "stall_33ms_count",
    "stall_50ms_count",
    "stall_100ms_count",
    "input_to_render_p50_ms",
    "input_to_render_p95_ms",
    "input_to_render_p99_ms",
    "orbit_latency_p95_ms",
    "pan_latency_p95_ms",
    "zoom_latency_p95_ms",
    "fit_latency_p95_ms",
    "pick_p50_ms",
    "pick_p95_ms",
    "pick_p99_ms",
    "selection_p95_ms",
    "whole_object_highlight_p95_ms",
    "area_select_ms",
    "freeze_over_100ms_count",
    "stall_over_33ms_count",
    "stall_over_50ms_count",
    "stall_over_100ms_count",
    "rss_peak_mb",
    "rss_drift_percent",
    "vram_peak_mb",
    "wrong_instance_picks",
    "hidden_object_false_picks",
    "geometry_queue_depth_peak",
    "upload_queue_depth_peak",
    "upload_frame_p50_ms",
    "upload_frame_p95_ms",
    "cache_memory_hits",
    "cache_disk_hits",
    "cache_misses",
    "cache_corruptions",
    "worker_count",
    "worker_utilization",
    "worker_restart_count",
    "worker_crash_count",
    "rss_start_mb",
    "rss_end_mb",
    "vram_start_mb",
    "vram_end_mb",
    "thread_count_start",
    "thread_count_end",
    "process_count_start",
    "process_count_end",
    "actor_count_start",
    "actor_count_end",
    "camera_roll_error",
)


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


@dataclass
class ViewerPerformanceEvidence:
    """Collect measured timings; absent observations remain explicit nulls."""

    started_monotonic: float = field(default_factory=time.perf_counter)
    values: dict[str, float | int | None] = field(
        default_factory=lambda: {name: None for name in METRIC_FIELDS}
    )
    samples: dict[str, list[float]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark(self, metric: str, *, at_monotonic: float | None = None) -> float:
        if metric not in {
            "shell_visible_ms", "first_tree_ms", "first_pixels_ms", "proxy_scene_ready_ms",
            "first_usable_ms", "geometry_ready_ms", "exact_25_ms", "exact_50_ms",
            "exact_75_ms", "exact_100_ms", "exact_ready_ms",
        }:
            raise KeyError(metric)
        value = ((at_monotonic or time.perf_counter()) - self.started_monotonic) * 1000.0
        self.values[metric] = round(max(0.0, value), 6)
        return value

    def set_metric(self, metric: str, value: float | int | None) -> None:
        if metric not in self.values:
            raise KeyError(metric)
        self.values[metric] = None if value is None else round(float(value), 6)

    def observe(self, family: str, milliseconds: float) -> None:
        self.samples.setdefault(str(family), []).append(max(0.0, float(milliseconds)))

    def finalize_samples(self) -> None:
        frames = self.samples.get("frame", ())
        self.values["frame_p50_ms"] = _percentile(frames, 0.50)
        self.values["frame_p95_ms"] = _percentile(frames, 0.95)
        self.values["frame_p99_ms"] = _percentile(frames, 0.99)
        self.values["input_to_render_p50_ms"] = _percentile(self.samples.get("input_to_render", ()), 0.50)
        self.values["pick_p50_ms"] = _percentile(self.samples.get("pick", ()), 0.50)
        for family, metric in (
            ("input_to_render", "input_to_render_p95_ms"),
            ("orbit", "orbit_latency_p95_ms"),
            ("pan", "pan_latency_p95_ms"),
            ("zoom", "zoom_latency_p95_ms"),
            ("fit", "fit_latency_p95_ms"),
            ("pick", "pick_p95_ms"),
            ("selection", "selection_p95_ms"),
            ("whole_object_highlight", "whole_object_highlight_p95_ms"),
            ("area_select", "area_select_ms"),
        ):
            self.values[metric] = _percentile(self.samples.get(family, ()), 0.95)
        self.values["upload_frame_p50_ms"] = _percentile(self.samples.get("upload_frame", ()), 0.50)
        self.values["upload_frame_p95_ms"] = _percentile(self.samples.get("upload_frame", ()), 0.95)
        self.values["input_to_render_p99_ms"] = _percentile(self.samples.get("input_to_render", ()), 0.99)
        self.values["pick_p99_ms"] = _percentile(self.samples.get("pick", ()), 0.99)
        interactive = tuple(self.samples.get("input_to_render", ())) + tuple(self.samples.get("frame", ()))
        stalls = tuple(self.samples.get("frame", ()))
        self.values["stall_over_33ms_count"] = sum(value > 33.0 for value in stalls)
        self.values["stall_over_50ms_count"] = sum(value > 50.0 for value in stalls)
        self.values["stall_over_100ms_count"] = sum(value > 100.0 for value in stalls)
        self.values["stall_33ms_count"] = self.values["stall_over_33ms_count"]
        self.values["stall_50ms_count"] = self.values["stall_over_50ms_count"]
        self.values["stall_100ms_count"] = self.values["stall_over_100ms_count"]
        self.values["freeze_over_100ms_count"] = sum(value > 100.0 for value in interactive)

    def to_dict(self) -> dict[str, Any]:
        self.finalize_samples()
        return {
            "schema": VIEWER_METRIC_SCHEMA,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "metrics": dict(self.values),
            "sample_counts": {key: len(value) for key, value in sorted(self.samples.items())},
            "metadata": dict(self.metadata),
            "unmeasured": [name for name in METRIC_FIELDS if self.values[name] is None],
        }

    def append_jsonl(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return target


__all__ = ["METRIC_FIELDS", "VIEWER_METRIC_SCHEMA", "ViewerPerformanceEvidence"]
