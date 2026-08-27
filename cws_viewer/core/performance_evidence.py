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
    "geometry_ready_ms",
    "frame_p50_ms",
    "frame_p95_ms",
    "input_to_render_p95_ms",
    "pick_p95_ms",
    "selection_p95_ms",
    "area_select_ms",
    "rss_peak_mb",
    "rss_drift_percent",
    "vram_peak_mb",
    "wrong_instance_picks",
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
        if metric not in {"shell_visible_ms", "first_tree_ms", "first_pixels_ms", "geometry_ready_ms"}:
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
        for family, metric in (
            ("input_to_render", "input_to_render_p95_ms"),
            ("pick", "pick_p95_ms"),
            ("selection", "selection_p95_ms"),
            ("area_select", "area_select_ms"),
        ):
            self.values[metric] = _percentile(self.samples.get(family, ()), 0.95)

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
