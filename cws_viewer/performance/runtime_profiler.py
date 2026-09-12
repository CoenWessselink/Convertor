"""Bounded, honest runtime telemetry for the existing Qt/VTK viewer.

VTK EndEvent measures completion of the CPU render call, NOT physical scan-out
or GPU execution time. Those unavailable stages stay null in evidence. Stage
spans may be nested; their durations must not be added as disjoint frame costs.
"""
from __future__ import annotations

from collections import Counter, deque
from contextlib import contextmanager
import math
import threading
import time
from typing import Any, Callable, Iterator


FRAME_STAGES = (
    "input_handling", "camera_update", "culling", "selection",
    "state_synchronization", "mapper_property_updates", "render",
    "render_thread_cpu", "render_process_cpu", "qt_compose", "qt_present",
    "input_to_render_end_oldest", "input_to_render_end_latest",
)
LOAD_STAGES = (
    "source_parsing", "canonical_conversion", "tessellation", "cache_lookup",
    "scene_creation", "spatial_index", "gpu_upload", "first_usable", "exact_completion",
)


def distribution(values: list[float]) -> dict[str, float | int | None]:
    """Linear quantiles; no measurements must never look like a zero-ms PASS."""
    ordered = sorted(float(x) for x in values)
    if not ordered:
        return {"count": 0, "mean_ms": None, "p50_ms": None, "p95_ms": None,
                "p99_ms": None, "max_ms": None, "over_100_ms": None}

    def percentile(q: float) -> float:
        position = (len(ordered) - 1) * q
        left = int(position)
        right = min(left + 1, len(ordered) - 1)
        return ordered[left] + (ordered[right] - ordered[left]) * (position - left)

    return {"count": len(ordered), "mean_ms": sum(ordered) / len(ordered),
            "p50_ms": percentile(.50), "p95_ms": percentile(.95),
            "p99_ms": percentile(.99), "max_ms": ordered[-1],
            "over_100_ms": sum(x > 100.0 for x in ordered)}


class ViewerProfiler:
    """Thread-safe rolling diagnostics, independent of Qt and VTK imports.

    The overlay reads this object at low frequency. No scene traversal,
    percentile calculation or filesystem I/O takes place in record/render hooks.
    Benchmarks can attach a sample sink to retain every raw observation; normal
    interactive sessions have strictly bounded sample storage.
    """

    def __init__(self, capacity: int = 4096, *, clock: Callable[[], float] = time.perf_counter,
                 sample_sink: Callable[[str, float, float], None] | None = None) -> None:
        if capacity < 1:
            raise ValueError("Profiler capacity must be positive")
        self.capacity = int(capacity)
        self.clock = clock
        self.started_at = clock()
        self.sample_sink = sample_sink
        self._samples: dict[str, deque[float]] = {}
        self._counts: Counter[str] = Counter()
        self._counters: Counter[str] = Counter()
        self._gauges: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._render_stack: list[tuple[float, float, float, bool]] = []
        self._recent_renders: deque[float] = deque(maxlen=1024)
        self._first_input: float | None = None
        self._latest_input: float | None = None
        self._auxiliary_depth = 0
        self._observer_window: Any | None = None
        self._observer_ids: list[int] = []

    def count(self, name: str, increment: int = 1) -> None:
        with self._lock:
            self._counters[name] += int(increment)

    def gauge(self, name: str, value: Any) -> None:
        with self._lock:
            self._gauges[name] = value

    def record(self, stage: str, milliseconds: float) -> None:
        value = float(milliseconds)
        if not math.isfinite(value) or value < 0:
            self.count("invalid_samples")
            return
        with self._lock:
            self._samples.setdefault(stage, deque(maxlen=self.capacity)).append(value)
            self._counts[stage] += 1
        sink = self.sample_sink
        if sink is not None:
            sink(stage, value, self.clock())

    @contextmanager
    def span(self, stage: str) -> Iterator[None]:
        started = self.clock()
        try:
            yield
        finally:
            self.record(stage, (self.clock() - started) * 1000.0)

    @contextmanager
    def auxiliary_render(self) -> Iterator[None]:
        """Separate ID-buffer/picking passes from visible-scene frame counts."""
        self._auxiliary_depth += 1
        try:
            yield
        finally:
            self._auxiliary_depth -= 1

    def input_received(self, kind: str) -> None:
        now = self.clock()
        with self._lock:
            self._counters["input_received"] += 1
            self._counters[f"input_received.{kind}"] += 1
            if self._first_input is None:
                self._first_input = now
            self._latest_input = now

    def input_processed(self, kind: str, received_count: int = 1) -> None:
        with self._lock:
            self._counters["input_processed"] += 1
            self._counters[f"input_processed.{kind}"] += 1
            self._counters["input_coalesced"] += max(0, int(received_count) - 1)

    def render_start(self, *_: Any) -> None:
        self._render_stack.append((self.clock(), time.process_time(), time.thread_time(),
                                   bool(self._auxiliary_depth)))

    def render_end(self, *_: Any) -> None:
        if not self._render_stack:
            self.count("unpaired_render_end")
            return
        start, process_cpu, thread_cpu, auxiliary = self._render_stack.pop()
        now = self.clock()
        if auxiliary:
            self.record("selection_gpu_pass_wall", (now - start) * 1000)
            self.count("selection_gpu_passes")
            return
        self.record("render", (now - start) * 1000)
        self.record("render_thread_cpu", (time.thread_time() - thread_cpu) * 1000)
        self.record("render_process_cpu", (time.process_time() - process_cpu) * 1000)
        with self._lock:
            self._counters["actual_renders"] += 1
            self._recent_renders.append(now)
            first, latest = self._first_input, self._latest_input
            self._first_input = self._latest_input = None
        if first is not None:
            self.record("input_to_render_end_oldest", (now - first) * 1000)
        if latest is not None:
            self.record("input_to_render_end_latest", (now - latest) * 1000)

    def attach(self, render_window: Any) -> None:
        if self._observer_window is render_window:
            return
        self.detach()
        self._observer_window = render_window
        self._observer_ids = [render_window.AddObserver("StartEvent", self.render_start),
                              render_window.AddObserver("EndEvent", self.render_end)]

    def detach(self) -> None:
        if self._observer_window is not None:
            for tag in self._observer_ids:
                self._observer_window.RemoveObserver(tag)
        self._observer_window = None
        self._observer_ids.clear()
        self._render_stack.clear()

    def snapshot(self, *, include_raw: bool = False) -> dict[str, Any]:
        with self._lock:
            values = {name: list(samples) for name, samples in self._samples.items()}
            counts, counters, gauges = dict(self._counts), dict(self._counters), dict(self._gauges)
            recent = tuple(self._recent_renders)
        stages: dict[str, Any] = {}
        for name in dict.fromkeys((*FRAME_STAGES, *LOAD_STAGES, *values)):
            raw = values.get(name, [])
            stages[name] = {"status": "MEASURED" if raw else "NOT_MEASURED",
                            **distribution(raw), "total_samples": counts.get(name, 0),
                            "truncated": counts.get(name, 0) > len(raw)}
            if include_raw:
                stages[name]["raw_ms"] = raw
        now = self.clock()
        return {"schema": "cws.viewer.runtime-profiler.v1", "stages": stages,
                "counters": counters, "gauges": gauges,
                "actual_renders_last_second": sum(t >= now - 1.0 for t in recent),
                "elapsed_seconds": max(0.0, now - self.started_at),
                "sample_capacity_per_stage": self.capacity,
                "timing_boundary": "VTK render-call EndEvent, not physical display presentation",
                "gpu_execution_ms": None, "physical_present_ms": None,
                "stage_spans_may_overlap": True}
