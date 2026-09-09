"""Native input regressions: clicks/releases need not be preceded by a move."""
from __future__ import annotations
import copy
from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.interactive_dimension_editor_v2_gui_smoke import InteractiveDimensionQtWorkflowTests


class DrawingCanvasNativeEventsTests(InteractiveDimensionQtWorkflowTests):
    def test_click_resolves_actual_point_without_hover_event(self):
        canvas = self.panel.preview
        endpoints = [c for c in self.panel._snap_candidates if c.snap_type == 'endpoint']
        first = endpoints[0]
        second = max(endpoints, key=lambda c: abs(c.point[0] - first.point[0]))
        events = []
        canvas.sheet_clicked.connect(lambda point, candidate, modifiers: events.append((point, candidate)))
        for target in (first, second):
            # QTest.mouseClick intentionally does not send a preceding move.
            self.QtTest.QTest.mouseClick(canvas, self.QtCore.Qt.MouseButton.LeftButton,
                pos=canvas.sheet_to_widget(target.point).toPoint())
            self.application.processEvents()
            self.assertIsNotNone(events[-1][1])
            point = events[-1][1].point
            self.assertAlmostEqual(point[0], target.point[0], delta=0.5)
            self.assertAlmostEqual(point[1], target.point[1], delta=0.5)

    def test_tab_updates_hover_instruction_and_preserves_clicked_identity(self):
        canvas = self.panel.preview
        first = next(c for c in self.panel._snap_candidates if c.snap_type == 'endpoint')
        second = copy.deepcopy(first)
        second = replace(second, candidate_id=second.candidate_id + ':P2')
        second.anchor.entity_id = 'P2'
        canvas.set_candidates([first, second])
        changes, clicks = [], []
        canvas.pointer_moved.connect(lambda point, candidate: changes.append(candidate.candidate_id if candidate else None))
        canvas.sheet_clicked.connect(lambda point, candidate, modifiers: clicks.append(candidate))
        position = canvas.sheet_to_widget(first.point).toPoint()
        self.QtTest.QTest.mouseClick(canvas, self.QtCore.Qt.MouseButton.LeftButton, pos=position)
        before = canvas.current_candidate.candidate_id
        self.QtTest.QTest.keyClick(canvas, self.QtCore.Qt.Key.Key_Tab)
        after = canvas.current_candidate.candidate_id
        self.assertNotEqual(before, after)
        self.assertEqual(changes[-1], after)
        self.QtTest.QTest.mouseClick(canvas, self.QtCore.Qt.MouseButton.LeftButton, pos=position)
        self.assertEqual(clicks[-1].candidate_id, after)

    def test_release_position_commits_drag_when_moves_are_coalesced(self):
        endpoints = [c for c in self.panel._snap_candidates if c.snap_type == 'endpoint']
        first = endpoints[0]
        second = max(endpoints, key=lambda c: abs(c.point[0] - first.point[0]))
        self.QtTest.QTest.mouseClick(self.panel.dimension_tool_buttons['horizontal'], self.QtCore.Qt.MouseButton.LeftButton)
        self._click_sheet(first.point)
        self._click_sheet(second.point)
        self._click_sheet(((first.point[0]+second.point[0])/2, max(first.point[1],second.point[1])+18))
        dimension = self.panel._dimension_document.dimensions[-1]
        canvas = self.panel.preview
        canvas.set_selected_ids([dimension.dimension_id])
        primitive = next(p for p in self.panel._drawing_document.pages[0].primitives
                         if p.semantic_id == dimension.dimension_id and len(p.points) >= 2)
        mid = tuple((primitive.points[0][i]+primitive.points[1][i])/2 for i in (0,1))
        start = canvas.sheet_to_widget(mid).toPoint()
        end = start + self.QtCore.QPoint(32, 18)
        events = []
        canvas.dimension_dragged.connect(lambda *args: events.append(args))
        self.QtTest.QTest.mousePress(canvas, self.QtCore.Qt.MouseButton.LeftButton, pos=start)
        self.QtTest.QTest.mouseRelease(canvas, self.QtCore.Qt.MouseButton.LeftButton, pos=end)
        self.application.processEvents()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], dimension.dimension_id)
        self.assertGreater(events[0][1][0], 0)
        self.assertGreater(events[0][1][1], 0)


if __name__ == '__main__':
    # Run only this class; the original two GUI tests remain in their own suite.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DrawingCanvasNativeEventsTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
