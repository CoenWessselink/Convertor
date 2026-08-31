"""Bounded frame-time telemetry for navigation and rendering evidence."""

from __future__ import annotations

from collections import deque
import math


class FrameTimeRecorder:
    def __init__(self, max_samples: int = 4096) -> None:
        self._samples: deque[float] = deque(maxlen=max(32, int(max_samples)))

    def record(self, milliseconds: float) -> None:
        value = float(milliseconds)
        if math.isfinite(value) and value >= 0.0:
            self._samples.append(value)

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        position = (len(values) - 1) * percentile
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return values[lower]
        return values[lower] * (upper - position) + values[upper] * (position - lower)

    def to_dict(self) -> dict[str, int | float]:
        values = sorted(self._samples)
        mean = sum(values) / len(values) if values else 0.0
        return {
            "sample_count": len(values),
            "frame_ms_mean": mean,
            "frame_ms_p50": self._percentile(values, 0.50),
            "frame_ms_p95": self._percentile(values, 0.95),
            "frame_ms_p99": self._percentile(values, 0.99),
            "frame_ms_max": values[-1] if values else 0.0,
            "fps_mean": 1000.0 / mean if mean > 0.0 else 0.0,
            "stalls_over_33ms": sum(value > 33.0 for value in values),
            "stalls_over_50ms": sum(value > 50.0 for value in values),
            "stalls_over_100ms": sum(value > 100.0 for value in values),
        }


__all__ = ["FrameTimeRecorder"]
