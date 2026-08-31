"""Generation-safe, time-budgeted queue for GUI-thread geometry uploads."""

from __future__ import annotations

from collections import deque
import threading
from typing import Iterable


class SceneUploadQueue:
    def __init__(self, *, budget_ms: float = 6.0, batch_limit: int = 16) -> None:
        self.budget_ms = max(0.5, float(budget_ms))
        self.batch_limit = max(1, int(batch_limit))
        self._queue: deque[tuple[int, str]] = deque()
        self._known: set[tuple[int, str]] = set()
        self._estimated_ms_per_item = 0.5
        self.uploaded = 0
        self.stale_rejected = 0
        self._lock = threading.RLock()

    def enqueue(self, generation: int, geometry_ids: Iterable[str]) -> int:
        added = 0
        with self._lock:
            for value in geometry_ids:
                item = (int(generation), str(value))
                if not item[1] or item in self._known:
                    continue
                self._known.add(item)
                self._queue.append(item)
                added += 1
        return added

    def claim(self, current_generation: int, *, max_items: int | None = None) -> tuple[str, ...]:
        with self._lock:
            while self._queue and self._queue[0][0] != int(current_generation):
                stale = self._queue.popleft()
                self._known.discard(stale)
                self.stale_rejected += 1
            capacity = max(1, min(self.batch_limit, int(self.budget_ms / max(self._estimated_ms_per_item, 0.05))))
            if max_items is not None:
                capacity = min(capacity, max(0, int(max_items)))
            result: list[str] = []
            while self._queue and len(result) < capacity:
                generation, geometry_id = self._queue[0]
                if generation != int(current_generation):
                    stale = self._queue.popleft()
                    self._known.discard(stale)
                    self.stale_rejected += 1
                    continue
                self._queue.popleft()
                self._known.discard((generation, geometry_id))
                result.append(geometry_id)
            return tuple(result)

    def record_upload(self, count: int, elapsed_ms: float) -> None:
        if count <= 0:
            return
        measured = max(0.01, float(elapsed_ms) / int(count))
        with self._lock:
            self._estimated_ms_per_item = self._estimated_ms_per_item * 0.75 + measured * 0.25
            self.uploaded += int(count)

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._queue)

    def diagnostics(self) -> dict[str, int | float]:
        with self._lock:
            return {"pending": len(self._queue), "uploaded": self.uploaded, "stale_rejected": self.stale_rejected, "budget_ms": self.budget_ms, "estimated_ms_per_item": self._estimated_ms_per_item}


__all__ = ["SceneUploadQueue"]
