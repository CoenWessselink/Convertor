from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cws_viewer.performance.runtime_profiler import ViewerProfiler, distribution


class RuntimeProfilerTests(unittest.TestCase):
    def test_no_samples_are_not_zero_ms_pass(self):
        values = ViewerProfiler().snapshot()
        self.assertIsNone(values["stages"]["qt_present"]["p95_ms"])
        self.assertEqual("NOT_MEASURED", values["stages"]["gpu_upload"]["status"])
        self.assertIsNone(values["physical_present_ms"])

    def test_bounded_samples_keep_total_and_explicit_truncation(self):
        profiler = ViewerProfiler(capacity=3)
        for value in range(10):
            profiler.record("selection", value)
        stage = profiler.snapshot(include_raw=True)["stages"]["selection"]
        self.assertEqual([7., 8., 9.], stage["raw_ms"])
        self.assertEqual(10, stage["total_samples"])
        self.assertTrue(stage["truncated"])
        self.assertAlmostEqual(8.9, stage["p95_ms"])

    def test_input_latency_tracks_oldest_and_latest_without_hiding_backlog(self):
        now = [0.]
        profiler = ViewerProfiler(clock=lambda: now[0])
        profiler.input_received("move")
        now[0] = .010
        profiler.input_received("move")
        profiler.input_processed("move", 2)
        profiler.render_start()
        now[0] = .030
        profiler.render_end()
        evidence = profiler.snapshot()
        self.assertAlmostEqual(30., evidence["stages"]["input_to_render_end_oldest"]["p95_ms"])
        self.assertAlmostEqual(20., evidence["stages"]["input_to_render_end_latest"]["p95_ms"])
        self.assertEqual(1, evidence["counters"]["input_coalesced"])
        self.assertEqual(2, evidence["counters"]["input_received"])

    def test_picking_passes_are_not_visible_frames(self):
        profiler = ViewerProfiler()
        profiler.input_received("click")
        with profiler.auxiliary_render():
            profiler.render_start()
            profiler.render_end()
        evidence = profiler.snapshot()
        self.assertEqual(0, evidence["counters"].get("actual_renders", 0))
        self.assertEqual(1, evidence["counters"]["selection_gpu_passes"])
        self.assertIsNone(evidence["stages"]["input_to_render_end_latest"]["p95_ms"])
        profiler.render_start()
        profiler.render_end()
        self.assertEqual(1, profiler.snapshot()["counters"]["actual_renders"])

    def test_invalid_samples_are_rejected_and_reported(self):
        profiler = ViewerProfiler()
        for value in (-1, float("nan"), float("inf")):
            profiler.record("render", value)
        self.assertEqual(3, profiler.snapshot()["counters"]["invalid_samples"])
        self.assertEqual(0, profiler.snapshot()["stages"]["render"]["count"])

    def test_raw_sink_sees_every_sample_when_rolling_buffer_overflows(self):
        sink = []
        profiler = ViewerProfiler(capacity=2, sample_sink=lambda *args: sink.append(args))
        for value in range(7):
            profiler.record("render", value)
        self.assertEqual(7, len(sink))
        self.assertEqual(2, profiler.snapshot()["stages"]["render"]["count"])

    def test_span_records_even_when_work_raises(self):
        now = [0.]
        profiler = ViewerProfiler(clock=lambda: now[0])
        with self.assertRaises(ValueError):
            with profiler.span("selection"):
                now[0] = .007
                raise ValueError("expected")
        self.assertAlmostEqual(7., profiler.snapshot()["stages"]["selection"]["p99_ms"])

    def test_distribution_uses_strict_freeze_boundary(self):
        self.assertEqual(1, distribution([1., 100., 100.001])["over_100_ms"])
        self.assertIsNone(distribution([])["over_100_ms"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
