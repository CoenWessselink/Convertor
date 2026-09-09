"""Regression checks for the real V3 workspace widgets (no acceptance stubs)."""
from __future__ import annotations
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cws_viewer.ui_qt.qt_compat import require_qt
from cws_convertor.drawings.interactive import (
    DimensionDocumentStore, DimensionEditorModel, SnapFilter, build_snap_candidates,
)
from cws_convertor.project.model import Part, ProjectModel
from tests.interactive_dimension_editor_v2_smoke import _build, _editor_document


class DrawingWorkspaceV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core, cls.gui, cls.widgets = require_qt()
        from PySide6 import QtTest
        cls.QtTest = QtTest
        cls.app = cls.widgets.QApplication.instance() or cls.widgets.QApplication([])

    def setUp(self):
        from cws_convertor.ui_qt.functional_workspaces import DrawingWorkspacePanel
        self.panel = DrawingWorkspacePanel()
        self.panel.resize(1280, 900)
        self.panel.show()
        self.app.processEvents()

    def tearDown(self):
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()

    def _workspace(self, name):
        project = ProjectModel.new(name, created_by="v3-test")
        project.parts["P1"] = Part(internal_id="P1", part_position="P1", name=name)
        return SimpleNamespace(project=project, session=SimpleNamespace(read_only=False, dirty=False, path=None))

    def test_wrapped_controls_stay_inside_at_desktop_widths(self):
        for width in (768, 960, 1280, 1920):
            with self.subTest(width=width):
                self.panel.resize(width, 1000)
                self.app.processEvents()
                self.assertEqual(self.panel.width(), width)
                for control in (*self.panel.dimension_tool_buttons.values(), *self.panel.dimension_action_buttons.values(),
                                self.panel.format, self.panel.orientation, self.panel.scale, self.panel.inspector_toggle):
                    rect = self.core.QRect(control.mapTo(self.panel, self.core.QPoint(0, 0)), control.size())
                    self.assertTrue(self.panel.rect().contains(rect), (width, control.text() if hasattr(control, "text") else control.objectName(), rect))
                    self.assertGreater(control.height(), 15)
                self.assertGreater(self.panel.preview.width(), 300)

    def test_dimension_tools_have_distinct_native_icons_and_accessible_names(self):
        import hashlib
        images = []
        self.assertEqual(len(self.panel.dimension_tool_buttons), 14)
        for name, button in self.panel.dimension_tool_buttons.items():
            image = button.icon().pixmap(32, 32).toImage()
            self.assertFalse(image.isNull(), name)
            images.append(hashlib.sha256(bytes(image.constBits())).hexdigest())
            self.assertTrue(button.toolTip(), name)
        self.assertEqual(len(set(images)), 14)
        for control in (self.panel.format, self.panel.orientation, self.panel.scale,
                        self.panel.preview):
            self.assertTrue(control.accessibleName())

    def test_inspector_toggle_is_a_real_click_and_does_not_change_document(self):
        self.assertTrue(self.panel.inspector_frame.isVisible())
        self.QtTest.QTest.mouseClick(self.panel.inspector_toggle, self.core.Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertFalse(self.panel.inspector_frame.isVisible())
        self.QtTest.QTest.mouseClick(self.panel.inspector_toggle, self.core.Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertTrue(self.panel.inspector_frame.isVisible())
        self.assertIsNone(self.panel._dimension_document)

    def test_same_entity_id_in_another_project_loads_that_project_only(self):
        first, second = self._workspace("First"), self._workspace("Second")
        self.panel.set_context(first, {"entity_id": "P1"})
        first_id = self.panel._dimension_document.drawing_id
        self.panel._dimension_document.extensions["origin"] = "first-project"
        self.assertTrue(self.panel._persist_dimension_editor("test.snapshot"))
        self.panel.set_context(second, {"entity_id": "P1"})
        self.assertNotIn("origin", self.panel._dimension_document.extensions)
        self.assertIs(self.panel._workspace.project, second.project)
        self.panel.set_context(first, {"entity_id": "P1"})
        self.assertEqual(self.panel._dimension_document.drawing_id, first_id)
        self.assertEqual(self.panel._dimension_document.extensions["origin"], "first-project")

    def test_unloaded_project_clears_old_canvas_and_editor(self):
        self.panel.set_context(self._workspace("First"), {"entity_id": "P1"})
        self.panel.set_context(None, None)
        self.assertIsNone(self.panel._dimension_document)
        self.assertIsNone(self.panel._dimension_model)
        self.assertIsNone(self.panel.preview._document)
        self.assertTrue(self.panel.preview._pixmap.isNull())

    def test_read_only_save_rejects_and_restores_the_persisted_document(self):
        workspace = self._workspace("First")
        self.panel.set_context(workspace, {"entity_id": "P1"})
        self.assertTrue(self.panel._persist_dimension_editor("test.baseline"))
        workspace.session.dirty = False
        before = workspace.project.to_dict()
        workspace.session.read_only = True
        self.panel._dimension_document.extensions["forbidden"] = True
        self.assertFalse(self.panel._persist_dimension_editor("test.forbidden"))
        self.assertNotIn("forbidden", self.panel._dimension_document.extensions)
        self.assertEqual(workspace.project.to_dict(), before)
        self.assertFalse(workspace.session.dirty)

    def test_released_keyboard_undo_cannot_silently_fork_revision(self):
        self.panel.set_context(self._workspace("First"), {"entity_id": "P1"})
        self.panel._dimension_document.status = "released"
        before = self.panel._dimension_document.to_dict()
        self.panel.preview.setFocus()
        self.QtTest.QTest.keyClick(self.panel.preview, self.core.Qt.Key.Key_Z, self.core.Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.panel._dimension_document.to_dict(), before)
        self.assertIn("vergrendeld", self.panel.status.text())

    def test_no_drawing_cannot_display_linter_pass(self):
        self.panel._update_dimension_properties()
        self.assertNotIn("geen blokkerende", self.panel.dimension_issue_summary.text())
        self.assertIn("geen gevalideerde", self.panel.dimension_issue_summary.text())

    def test_center_only_filter_does_not_fall_back_to_an_edge(self):
        document = _build()
        pixmap = self.gui.QPixmap(840, 594)
        pixmap.fill(self.core.Qt.GlobalColor.white)
        canvas = self.panel.preview
        candidates = build_snap_candidates(document, entity_id="P1")
        canvas.set_drawing(pixmap, document, candidates)
        edge = next(c for c in candidates if c.snap_type == "midpoint")
        # An edge is available under ALL. An empty centers filter must not
        # synthesize the nearest edge from the unfiltered document.
        canvas.set_candidates([edge], snap_filter=SnapFilter.ALL.value)
        point = canvas.sheet_to_widget(edge.point)
        canvas._update_hover(point)
        self.assertIsNotNone(canvas.current_candidate)
        canvas.set_candidates([], snap_filter=SnapFilter.CENTERS.value)
        canvas._update_hover(point)
        self.assertIsNone(canvas.current_candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
