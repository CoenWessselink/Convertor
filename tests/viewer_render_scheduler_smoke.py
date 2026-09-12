from __future__ import annotations
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cws_viewer.performance.render_scheduler import DirtyFlag, RenderScheduler
from cws_viewer.performance.runtime_profiler import ViewerProfiler


class ClockQueue:
    def __init__(self):
        self.now = 0.
        self.queue = []
    def call_later(self, ms, callback):
        self.queue.append((self.now + ms / 1000, callback))
    def step(self):
        when, callback = self.queue.pop(0)
        self.now = when
        callback()


class RenderSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.queue = ClockQueue()
        self.frames = []
        self.profiler = ViewerProfiler(clock=lambda: self.queue.now)
        self.scheduler = RenderScheduler(
            lambda flags: self.frames.append((self.queue.now, flags)),
            self.queue.call_later, clock=lambda: self.queue.now, profiler=self.profiler,
        )

    def test_thousand_requests_one_frame_with_union_of_flags(self):
        for _ in range(500):
            self.scheduler.request(DirtyFlag.CAMERA)
            self.scheduler.request(DirtyFlag.SELECTION)
        self.assertEqual(1, len(self.queue.queue))
        self.assertTrue(self.scheduler.pending)
        self.queue.step()
        self.assertEqual([(0., DirtyFlag.CAMERA | DirtyFlag.SELECTION)], self.frames)
        self.assertFalse(self.scheduler.pending)
        self.assertEqual(999, self.profiler.snapshot()["counters"]["render_requests_coalesced"])

    def test_frame_rate_is_bounded_and_no_early_render(self):
        self.scheduler.request()
        self.queue.step()
        self.scheduler.request()
        self.assertGreaterEqual(self.queue.queue[0][0], 1 / 60)
        self.queue.step()
        self.assertGreaterEqual(self.frames[1][0] - self.frames[0][0], 1 / 60)

    def test_latest_state_not_a_queue_of_old_state_snapshots(self):
        state = [0]
        observed = []
        scheduler = RenderScheduler(lambda _: observed.append(state[0]), self.queue.call_later)
        for value in range(500):
            state[0] = value
            scheduler.request(DirtyFlag.CAMERA)
        self.queue.step()
        self.assertEqual([499], observed)

    def test_reentrant_request_waits_for_next_frame(self):
        def draw(flags):
            self.frames.append(flags)
            if len(self.frames) == 1:
                self.scheduler.request(DirtyFlag.VISIBILITY)
        self.scheduler._render = draw
        self.scheduler.request(DirtyFlag.CAMERA)
        self.queue.step()
        self.assertEqual([DirtyFlag.CAMERA], self.frames)
        self.assertEqual(1, len(self.queue.queue))
        self.queue.step()
        self.assertEqual([DirtyFlag.CAMERA, DirtyFlag.VISIBILITY], self.frames)

    def test_flush_invalidates_old_callback(self):
        self.scheduler.request()
        self.scheduler.flush()
        self.assertEqual(1, len(self.frames))
        self.queue.step()
        self.assertEqual(1, len(self.frames))

    def test_close_cancels_queued_and_future_work(self):
        self.scheduler.request()
        self.scheduler.close()
        self.queue.step()
        self.scheduler.request()
        self.scheduler.flush()
        self.assertEqual([], self.frames)
        self.assertEqual([], self.queue.queue)
        self.assertTrue(self.scheduler.closed)

    def test_exception_does_not_leave_scheduler_in_rendering_state(self):
        def fail(_):
            raise RuntimeError("expected")
        self.scheduler._render = fail
        self.scheduler.request()
        with self.assertRaises(RuntimeError):
            self.queue.step()
        self.scheduler._render = lambda flags: self.frames.append(flags)
        self.scheduler.request(DirtyFlag.COLOR)
        self.queue.step()
        self.assertEqual([DirtyFlag.COLOR], self.frames)

    def test_bad_frame_rate_is_rejected(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                RenderScheduler(lambda _: None, self.queue.call_later, fps=value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
