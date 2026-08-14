"""Deterministic scheduling for progressive viewer mesh loading."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
import time


PROGRESSIVE_MESH_LOAD_VERSION = "1.0"


class ProgressiveMeshLoadCancelled(RuntimeError):
    """Raised by geometry providers when a mesh request is cancelled."""


@dataclass(slots=True)
class ProgressiveMeshLoadPlan:
    """Bounded work queue with explicit priority, failure and cancel states."""

    entity_ids: Iterable[str]
    max_in_flight: int = 2
    patch_batch_size: int = 4
    mode: str = "project"
    clock: Callable[[], float] = time.monotonic
    _all_ids: tuple[str, ...] = field(init=False, repr=False)
    _queue: deque[str] = field(init=False, repr=False)
    _pending: set[str] = field(default_factory=set, init=False, repr=False)
    _loaded: set[str] = field(default_factory=set, init=False, repr=False)
    _failed: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _cancelled: set[str] = field(default_factory=set, init=False, repr=False)
    _started_at: float = field(init=False, repr=False)
    _finished_at: float | None = field(default=None, init=False, repr=False)
    _selected_priority: str | None = field(default=None, init=False, repr=False)
    _cancel_requested: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        unique_ids = tuple(dict.fromkeys(str(item) for item in self.entity_ids))
        if any(not item for item in unique_ids):
            raise ValueError("Progressive mesh entity ids must not be empty")
        if self.max_in_flight < 1:
            raise ValueError("max_in_flight must be at least 1")
        if self.patch_batch_size < 1:
            raise ValueError("patch_batch_size must be at least 1")
        if self.mode not in {"project", "selection_only"}:
            raise ValueError(f"Unsupported progressive mesh load mode: {self.mode}")
        self._all_ids = unique_ids
        self._queue = deque(unique_ids)
        self._started_at = self.clock()
        if not unique_ids:
            self._finished_at = self._started_at

    @property
    def total(self) -> int:
        return len(self._all_ids)

    @property
    def loaded_ids(self) -> frozenset[str]:
        return frozenset(self._loaded)

    @property
    def failed(self) -> dict[str, str]:
        return dict(self._failed)

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested

    @property
    def is_finished(self) -> bool:
        return not self._queue and not self._pending

    def prioritize(self, entity_id: str, *, retry_failed: bool = True) -> bool:
        """Move an entity to the front without exceeding the concurrency limit."""

        if entity_id not in self._all_ids:
            return False
        self._selected_priority = entity_id
        if entity_id in self._loaded or entity_id in self._pending:
            return False
        if entity_id in self._failed:
            if not retry_failed:
                return False
            del self._failed[entity_id]
            self._finished_at = None
        if entity_id in self._cancelled:
            if self._cancel_requested:
                return False
            self._cancelled.remove(entity_id)
        try:
            self._queue.remove(entity_id)
        except ValueError:
            pass
        self._queue.appendleft(entity_id)
        return True

    def claim(self) -> tuple[str, ...]:
        """Claim only the work that can run immediately."""

        if self._cancel_requested:
            return ()
        available = self.max_in_flight - len(self._pending)
        claimed: list[str] = []
        while available > 0 and self._queue:
            entity_id = self._queue.popleft()
            self._pending.add(entity_id)
            claimed.append(entity_id)
            available -= 1
        return tuple(claimed)

    def mark_loaded(self, entity_id: str) -> bool:
        if entity_id not in self._pending:
            return False
        self._pending.remove(entity_id)
        if self._cancel_requested:
            self._cancelled.add(entity_id)
            self._finish_if_idle()
            return False
        self._loaded.add(entity_id)
        self._finish_if_idle()
        return True

    def mark_failed(self, entity_id: str, error: BaseException | str) -> bool:
        if entity_id not in self._pending:
            return False
        self._pending.remove(entity_id)
        if self._cancel_requested:
            self._cancelled.add(entity_id)
            self._finish_if_idle()
            return False
        message = str(error).strip() or type(error).__name__
        self._failed[entity_id] = message
        self._finish_if_idle()
        return True

    def cancel(self) -> None:
        if self._cancel_requested:
            return
        self._cancel_requested = True
        self._cancelled.update(self._queue)
        self._cancelled.update(self._pending)
        self._queue.clear()
        self._pending.clear()
        self._finished_at = self.clock()

    def manifest(self, *, include_runtime: bool = False) -> dict[str, object]:
        status = "loading"
        if self._cancel_requested:
            status = "cancelled"
        elif self.is_finished and self._failed:
            status = "completed_with_errors"
        elif self.is_finished:
            status = "completed"
        elif not self._pending:
            status = "queued"

        completed = len(self._loaded) + len(self._failed) + len(self._cancelled)
        result: dict[str, object] = {
            "contract_version": PROGRESSIVE_MESH_LOAD_VERSION,
            "mode": self.mode,
            "status": status,
            "total": self.total,
            "queued": len(self._queue),
            "pending": len(self._pending),
            "loaded": len(self._loaded),
            "failed": len(self._failed),
            "cancelled": len(self._cancelled),
            "completed": completed,
            "progress_ratio": (completed / self.total) if self.total else 1.0,
            "max_in_flight": self.max_in_flight,
            "patch_batch_size": self.patch_batch_size,
            "selected_priority": self._selected_priority,
            "failures": dict(sorted(self._failed.items())),
        }
        if include_runtime:
            end = self._finished_at if self._finished_at is not None else self.clock()
            result["elapsed_ms"] = max(0, round((end - self._started_at) * 1000))
        return result

    def _finish_if_idle(self) -> None:
        if self.is_finished and self._finished_at is None:
            self._finished_at = self.clock()
