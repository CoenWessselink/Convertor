"""Central performance governor for interactive and progressive Viewer work.

The governor is deliberately renderer-agnostic.  Geometry scheduling, Qt/VTK
upload code and packaged evidence all consume the same state and budgets so a
large model cannot silently fall back to an unbounded, blocking load path.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
import math
import statistics
import time
from typing import Iterable


class ViewerPerformanceState(str, Enum):
    INTERACTIVE = "INTERACTIVE"
    RECOVERY = "RECOVERY"
    IDLE_HQ = "IDLE_HQ"
    BACKGROUND_LOADING = "BACKGROUND_LOADING"


@dataclass(frozen=True, slots=True)
class GeometryPrioritySignal:
    selected: bool = False
    cursor_distance_px: float | None = None
    visible: bool = True
    projected_area_px2: float = 0.0
    camera_distance: float = 1.0
    recent_interaction: bool = False
    assembly_context: bool = False
    lod_level: int = 0
    waiting_seconds: float = 0.0


class ViewerPerformanceGovernor:
    """Own dynamic priority, frame-quality and bounded upload decisions."""

    _UPLOAD_BUDGETS_MS = {
        ViewerPerformanceState.INTERACTIVE: 1.5,
        ViewerPerformanceState.RECOVERY: 3.5,
        ViewerPerformanceState.IDLE_HQ: 7.0,
        ViewerPerformanceState.BACKGROUND_LOADING: 2.5,
    }
    _MSAA_SAMPLES = {
        ViewerPerformanceState.INTERACTIVE: 0,
        ViewerPerformanceState.RECOVERY: 2,
        ViewerPerformanceState.IDLE_HQ: 8,
        ViewerPerformanceState.BACKGROUND_LOADING: 2,
    }

    def __init__(self, *, target_frame_ms: float = 16.667, history_size: int = 720) -> None:
        self.target_frame_ms = max(4.0, float(target_frame_ms))
        self.state = ViewerPerformanceState.IDLE_HQ
        self._frames: deque[float] = deque(maxlen=max(60, int(history_size)))
        self._state_since = time.perf_counter()
        self._last_interaction = 0.0
        self._loading = False

    def begin_interaction(self) -> None:
        self._last_interaction = time.perf_counter()
        self._set_state(ViewerPerformanceState.INTERACTIVE)

    def end_interaction(self) -> None:
        self._last_interaction = time.perf_counter()
        self._set_state(ViewerPerformanceState.RECOVERY)

    def set_background_loading(self, active: bool) -> None:
        self._loading = bool(active)
        if active and self.state is ViewerPerformanceState.IDLE_HQ:
            self._set_state(ViewerPerformanceState.BACKGROUND_LOADING)
        elif not active and self.state is ViewerPerformanceState.BACKGROUND_LOADING:
            self._set_state(ViewerPerformanceState.RECOVERY)

    def observe_frame(self, milliseconds: float, *, now: float | None = None) -> None:
        value = max(0.0, float(milliseconds))
        self._frames.append(value)
        current = time.perf_counter() if now is None else float(now)
        quiet_for = current - self._last_interaction
        if self.state is ViewerPerformanceState.INTERACTIVE:
            return
        if quiet_for < 0.18:
            self._set_state(ViewerPerformanceState.RECOVERY)
            return
        recent = tuple(self._frames)[-30:]
        p95 = _percentile(recent, 0.95) or 0.0
        if self._loading and p95 > self.target_frame_ms * 1.15:
            self._set_state(ViewerPerformanceState.BACKGROUND_LOADING)
        elif quiet_for >= 0.45 and p95 <= self.target_frame_ms * 1.35:
            self._set_state(ViewerPerformanceState.IDLE_HQ)
        else:
            self._set_state(ViewerPerformanceState.RECOVERY)

    @property
    def upload_budget_ms(self) -> float:
        base = self._UPLOAD_BUDGETS_MS[self.state]
        recent = tuple(self._frames)[-20:]
        p95 = _percentile(recent, 0.95)
        if p95 is None:
            return base
        if p95 > self.target_frame_ms * 1.5:
            return max(1.0, base * 0.55)
        if p95 < self.target_frame_ms * 0.75 and self.state is not ViewerPerformanceState.INTERACTIVE:
            return min(8.0, base * 1.2)
        return base

    @property
    def msaa_samples(self) -> int:
        return self._MSAA_SAMPLES[self.state]

    def priority_score(self, signal: GeometryPrioritySignal) -> float:
        """Return a stable weighted score with visibility and starvation guards."""
        score = 0.0
        score += 10_000.0 if signal.selected else 0.0
        score += 2_600.0 if signal.visible else -3_000.0
        if signal.cursor_distance_px is not None:
            score += 3_000.0 / (1.0 + max(0.0, signal.cursor_distance_px) / 48.0)
        score += min(2_000.0, math.sqrt(max(0.0, signal.projected_area_px2)) * 8.0)
        score += 1_200.0 / (1.0 + max(0.0, signal.camera_distance))
        score += 900.0 if signal.recent_interaction else 0.0
        score += 450.0 if signal.assembly_context else 0.0
        score -= max(0, int(signal.lod_level)) * 220.0
        score += min(2_500.0, max(0.0, signal.waiting_seconds) * 125.0)
        return round(score, 6)

    def snapshot(self) -> dict[str, object]:
        frames = tuple(self._frames)
        return {
            "schema": "cws-viewer-performance-governor-1.0",
            "state": self.state.value,
            "target_frame_ms": self.target_frame_ms,
            "upload_budget_ms": round(self.upload_budget_ms, 3),
            "msaa_samples": self.msaa_samples,
            "frame_samples": len(frames),
            "frame_p50_ms": _percentile(frames, 0.50),
            "frame_p95_ms": _percentile(frames, 0.95),
            "frame_p99_ms": _percentile(frames, 0.99),
            "stall_over_33ms_count": sum(value > 33.0 for value in frames),
            "stall_over_50ms_count": sum(value > 50.0 for value in frames),
            "stall_over_100ms_count": sum(value > 100.0 for value in frames),
            "background_loading": self._loading,
        }

    def _set_state(self, state: ViewerPerformanceState) -> None:
        if state is self.state:
            return
        self.state = state
        self._state_since = time.perf_counter()


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * float(percentile)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


__all__ = ["GeometryPrioritySignal", "ViewerPerformanceGovernor", "ViewerPerformanceState"]
