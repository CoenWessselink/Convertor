"""Actual QVTK host tests; these are not physical GPU performance acceptance."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows"
else:
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb" if os.environ.get("DISPLAY") else "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets, QtTest
from cws_viewer.fixtures import build_lo4_reference_scene
from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2
from cws_viewer.core.viewer_feel_navigation import WHEEL_ZOOM_PER_NOTCH


class NativeSchedulerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        scene, repository = build_lo4_reference_scene()
        self.widget = VtkRealProjectWidgetFeelV2(repository)
        self.widget.resize(960, 640)
        self.widget.show()
        self.widget.load_scene(scene)
        self.errors = []
        self.widget.backend_failed.connect(self.errors.append)
        QtTest.QTest.qWait(200)

    def tearDown(self):
        self.widget.close()
        self.widget.deleteLater()
        self.app.processEvents()
        self.assertEqual([], self.errors)

    def wheel(self, amount=120, x=430, y=310):
        local = QtCore.QPointF(x, y)
        event = QtGui.QWheelEvent(
            local, QtCore.QPointF(self.widget.mapToGlobal(local.toPoint())),
            QtCore.QPoint(), QtCore.QPoint(0, amount), QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier, QtCore.Qt.ScrollPhase.NoScrollPhase, False,
        )
        self.app.sendEvent(self.widget, event)

    def test_thousand_backend_requests_are_one_actual_native_render(self):
        before = self.widget.backend.profiler.snapshot()["counters"]
        for _ in range(1000):
            self.widget.backend.render()
        immediate = self.widget.backend.profiler.snapshot()["counters"]
        self.assertEqual(before.get("actual_renders", 0), immediate.get("actual_renders", 0))
        QtTest.QTest.qWait(60)
        after = self.widget.backend.profiler.snapshot()["counters"]
        self.assertEqual(1000, after["render_requests"] - before["render_requests"])
        self.assertEqual(1, after["actual_renders"] - before["actual_renders"])
        self.assertEqual(1, after["scheduled_frames"] - before["scheduled_frames"])

    def test_wheel_reducer_keeps_all_detents_and_updates_camera_once(self):
        # Fixing the anchor isolates the event reducer, not the production picker.
        anchor = self.widget.controller.get_camera().target
        self.widget._wheel_anchor = lambda _: anchor
        before = self.widget.controller.get_camera()
        for _ in range(10):
            self.wheel()
        self.assertEqual(before, self.widget.controller.get_camera())
        self.assertEqual(10, self.widget._wheel_pending_events)
        QtTest.QTest.qWait(70)
        after = self.widget.controller.get_camera()
        expected_distance = (before.position - anchor).length() / (WHEEL_ZOOM_PER_NOTCH ** 10)
        self.assertAlmostEqual(expected_distance, (after.position - anchor).length(), places=6)
        self.assertEqual(0, self.widget._wheel_pending_events)
        counters = self.widget.backend.profiler.snapshot()["counters"]
        self.assertEqual(10, counters["input_received.wheel"])
        self.assertEqual(1, counters["input_processed.wheel"])
        self.assertEqual(9, counters["input_coalesced"])

    def test_opposite_wheel_events_cancel_without_false_input_backlog(self):
        before = self.widget.controller.get_camera()
        self.wheel(120)
        self.wheel(-120)
        QtTest.QTest.qWait(70)
        self.assertEqual(before, self.widget.controller.get_camera())
        self.assertEqual(0, self.widget._wheel_pending_events)
        self.assertEqual(2, self.widget.backend.profiler.snapshot()["counters"]["input_cancelled"])

    def test_capture_flushes_pending_scene_and_keeps_scheduler_attached(self):
        import tempfile
        scheduler = self.widget._render_scheduler
        self.widget.controller.set_selection((self.widget.controller.index.renderable_node_ids[0],))
        with tempfile.TemporaryDirectory() as folder:
            path = self.widget.backend.capture_png(Path(folder) / "selected.png")
            self.assertGreater(path.stat().st_size, 1000)
        self.assertIs(scheduler, self.widget.backend._render_scheduler)


if __name__ == "__main__":
    unittest.main(verbosity=2)
