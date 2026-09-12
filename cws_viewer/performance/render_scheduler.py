"""One frame owner for the existing viewer; no Qt/VTK dependency here."""
from __future__ import annotations

from enum import IntFlag
import math
import time
from typing import Callable

from cws_viewer.performance.runtime_profiler import ViewerProfiler


class DirtyFlag(IntFlag):
    NONE = 0
    CAMERA = 1
    VISIBILITY = 2
    SELECTION = 4
    GEOMETRY = 8
    COLOR = 16
    SECTION = 32
    OVERLAY = 64
    QUALITY = 128
    RESIZE = 256
    ALL = CAMERA | VISIBILITY | SELECTION | GEOMETRY | COLOR | SECTION | OVERLAY | QUALITY | RESIZE


class RenderScheduler:
    """Latest-state rendering with at most one outstanding event-loop callback.

    ``call_later`` receives a nonnegative delay in milliseconds and a callback.
    UI state changes happen in their original canonical/controller paths; this
    class only combines their render requests. Reentrant requests during a
    render are retained for the next frame, never recursively rendered.
    ``flush`` is an explicit synchronous capture/teardown boundary, not a normal
    input path. Old scheduled callbacks become harmless through ticket checks.
    """

    def __init__(self, render: Callable[[DirtyFlag], None],
                 call_later: Callable[[int, Callable[[], None]], None], *,
                 fps: float = 60.0, clock: Callable[[], float] = time.perf_counter,
                 profiler: ViewerProfiler | None = None) -> None:
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("Frame rate must be finite and positive")
        self._render = render
        self._call_later = call_later
        self.clock = clock
        self.interval = 1.0 / fps
        self.profiler = profiler
        self._dirty = DirtyFlag.NONE
        self._scheduled = False
        self._rendering = False
        self._closed = False
        self._ticket = 0
        self._next_frame = 0.0

    @property
    def pending(self) -> bool:
        return bool(self._dirty)

    @property
    def closed(self) -> bool:
        return self._closed

    def request(self, dirty: DirtyFlag = DirtyFlag.OVERLAY) -> None:
        if self._closed or not dirty:
            return
        self._dirty |= DirtyFlag(dirty)
        if self.profiler:
            self.profiler.count("scheduler_requests")
        if self._scheduled or self._rendering:
            if self.profiler:
                self.profiler.count("render_requests_coalesced")
            return
        self._schedule()

    def _schedule(self) -> None:
        if self._closed or self._scheduled or not self._dirty:
            return
        self._scheduled = True
        self._ticket += 1
        ticket = self._ticket
        wait_ms = max(0, int(math.ceil((self._next_frame - self.clock()) * 1000.0)))
        self._call_later(wait_ms, lambda: self._dispatch(ticket))

    def _dispatch(self, ticket: int) -> None:
        if self._closed or ticket != self._ticket:
            return
        self._scheduled = False
        # Early timer callbacks must not defeat the maximum frame rate.
        if self.clock() + 1e-9 < self._next_frame:
            self._schedule()
            return
        self._draw()

    def _draw(self) -> None:
        if self._closed or self._rendering or not self._dirty:
            return
        dirty, self._dirty = self._dirty, DirtyFlag.NONE
        self._rendering = True
        self._next_frame = self.clock() + self.interval
        try:
            if self.profiler:
                self.profiler.count("scheduled_frames")
                self.profiler.gauge("last_frame_dirty_flags", int(dirty))
            self._render(dirty)
        finally:
            self._rendering = False
            self._schedule()

    def flush(self) -> None:
        if self._closed or self._rendering:
            return
        self._ticket += 1
        self._scheduled = False
        self._draw()

    def close(self) -> None:
        self._closed = True
        self._ticket += 1
        self._scheduled = False
        self._dirty = DirtyFlag.NONE


__all__ = ["DirtyFlag", "RenderScheduler"]
