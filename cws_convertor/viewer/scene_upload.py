from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
import statistics
from typing import Any

from cws_viewer.performance.policy import LoadingPerformancePolicy


def estimate_resource_bytes(resource: Any) -> int:
    direct = getattr(resource, "byte_length", None)
    if isinstance(direct, (int, float)) and direct >= 0:
        return int(direct)

    total = 0
    for name in ("vertices", "vertices_mm", "triangles", "normals", "feature_edges", "lod_triangles"):
        value = getattr(resource, name, None)
        if value is None:
            continue
        if isinstance(value, tuple):
            total += sum(int(getattr(item, "nbytes", 0)) for item in value)
        else:
            total += int(getattr(value, "nbytes", 0))
    return total


@dataclass
class SceneUploadBudget:
    max_ms: float = 6.0
    max_resources: int = 4
    max_bytes: int = 16 * 1024**2
    adaptive_resource_limit: int = field(init=False)
    frames: int = 0
    uploaded_resources: int = 0
    uploaded_bytes: int = 0
    deferred_peak: int = 0
    frame_times_ms: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.max_ms = max(1.0, float(self.max_ms))
        self.max_resources = max(1, int(self.max_resources))
        self.max_bytes = max(1024, int(self.max_bytes))
        self.adaptive_resource_limit = self.max_resources

    @classmethod
    def for_geometry_count(cls, geometry_count: int) -> "SceneUploadBudget":
        policy = LoadingPerformancePolicy.detect(geometry_count=max(0, int(geometry_count)))
        return cls(
            max_ms=policy.scene_upload_budget_ms,
            max_resources=min(4, policy.scene_upload_batch_limit),
            max_bytes=policy.scene_upload_byte_limit,
        )

    @property
    def batch_limit(self) -> int:
        return max(1, min(self.max_resources, self.adaptive_resource_limit))

    def take(self, pending: deque[tuple[str, Any]]) -> list[tuple[str, Any]]:
        selected: list[tuple[str, Any]] = []
        consumed_bytes = 0
        while pending and len(selected) < self.batch_limit:
            candidate = pending[0]
            candidate_bytes = max(0, estimate_resource_bytes(candidate[1]))
            if selected and consumed_bytes + candidate_bytes > self.max_bytes:
                break
            pending.popleft()
            selected.append(candidate)
            consumed_bytes += candidate_bytes
            if consumed_bytes >= self.max_bytes:
                break
        self.deferred_peak = max(self.deferred_peak, len(pending))
        return selected

    def record_frame(self, resources: list[tuple[str, Any]], elapsed_ms: float) -> None:
        if not resources:
            return
        elapsed_ms = max(0.0, float(elapsed_ms))
        self.frames += 1
        self.uploaded_resources += len(resources)
        self.uploaded_bytes += sum(estimate_resource_bytes(resource) for _, resource in resources)
        self.frame_times_ms.append(elapsed_ms)
        if len(self.frame_times_ms) > 240:
            del self.frame_times_ms[:-240]

        if elapsed_ms > self.max_ms:
            self.adaptive_resource_limit = max(1, math.ceil(self.adaptive_resource_limit / 2))
        elif elapsed_ms < self.max_ms * 0.55 and self.adaptive_resource_limit < self.max_resources:
            self.adaptive_resource_limit += 1

    def telemetry(self) -> dict[str, Any]:
        ordered = sorted(self.frame_times_ms)
        p95 = 0.0
        if ordered:
            p95 = ordered[min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)]
        return {
            "schema": "cws.scene-upload-budget.v2",
            "budget_ms": self.max_ms,
            "resource_limit": self.max_resources,
            "adaptive_resource_limit": self.adaptive_resource_limit,
            "byte_limit": self.max_bytes,
            "frames": self.frames,
            "uploaded_resources": self.uploaded_resources,
            "uploaded_bytes": self.uploaded_bytes,
            "deferred_peak": self.deferred_peak,
            "frame_time_mean_ms": round(statistics.fmean(ordered), 3) if ordered else 0.0,
            "frame_time_p95_ms": round(p95, 3),
        }
