from __future__ import annotations

import ast
import os
from pathlib import Path
from types import SimpleNamespace
import sys
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


class InteractiveDimensionUiContractTests(unittest.TestCase):
    def test_dimension_editor_ui_modules_compile_and_expose_required_controls(self) -> None:
        workspace_source = (ROOT / "cws_convertor" / "ui_qt" / "functional_workspaces.py").read_text(encoding="utf-8")
        canvas_source = (ROOT / "cws_convertor" / "ui_qt" / "drawing_dimension_canvas.py").read_text(encoding="utf-8")
        ast.parse(workspace_source)
        ast.parse(canvas_source)
        for token in (
            "Horizontale maat", "Verticale maat", "Uitgelijnde maat", "Kettingmaat",
            "Baseline-/nulpuntmaat", "Ordinaatmaat X", "Hoekmaat", "Radiusmaat",
            "Diametermaat", "Hart-op-hartmaat", "Leader/callout", "Tekstnotitie",
            "Selectie verwijderen", "Eigenschappen wijzigen", "Opnieuw ankeren",
        ):
            self.assertIn(token, workspace_source)
        for token in ("sheet_clicked", "pointer_moved", "dimension_dragged", "cycle_candidate", "widget_to_sheet", "sheet_to_widget"):
            self.assertIn(token, canvas_source)


@unittest.skipUnless(qt_available(), "PySide6 is niet beschikbaar")
class InteractiveDimensionQtWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        core, gui, widgets = require_qt()
        cls.QtCore, cls.QtGui, cls.QtWidgets = core, gui, widgets
        from PySide6 import QtTest

        cls.QtTest = QtTest
        cls.application = widgets.QApplication.instance() or widgets.QApplication([])

    def setUp(self) -> None:
        import numpy as np

        from cws_convertor.drawings import (
            DimensionDocumentStore,
            DimensionEditorModel,
            DimensionKind,
            DrawingBuildRequest,
            ProductionDrawingEngine,
            ProductionDrawingRenderer,
            build_snap_candidates,
        )
        from cws_convertor.project.model import ProjectModel
        from cws_convertor.ui_qt.functional_workspaces import DrawingWorkspacePanel

        self.DimensionKind = DimensionKind
        self.DrawingBuildRequest = DrawingBuildRequest
        self.ProductionDrawingEngine = ProductionDrawingEngine
        self.ProductionDrawingRenderer = ProductionDrawingRenderer
        self.build_snap_candidates = build_snap_candidates
        self.vertices = np.asarray(
            ((0, 0, 0), (100, 0, 0), (100, 50, 0), (0, 50, 0), (0, 0, 10), (100, 0, 10), (100, 50, 10), (0, 50, 10)),
            dtype=float,
        )
        self.triangles = np.asarray(
            ((0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)),
            dtype=int,
        )
        self.temporary = TemporaryDirectory(prefix="cws-pdf12-gui-")
        self.root = Path(self.temporary.name)
        project = ProjectModel.new("PDF12 GUI", created_by="tester")
        session = SimpleNamespace(path=None, read_only=False, dirty=False)
        self.workspace = SimpleNamespace(project=project, session=session)
        self.panel = DrawingWorkspacePanel()
        self.panel._workspace = self.workspace
        self.panel._entity_id = "P1"
        self.panel._dimension_document = DimensionDocumentStore.load(
            project,
            entity_id="P1",
            source_revision="A",
            geometry_sha256="a" * 64,
            manufacturing_sha256="b" * 64,
            user="tester",
        )
        self.panel._dimension_model = DimensionEditorModel(self.panel._dimension_document)
        self.panel._loaded_lock_version = 0

        def refresh() -> None:
            document = self._build_document()
            pdf = self.root / "preview.pdf"
            png = self.root / "preview.png"
            self.ProductionDrawingRenderer.render(document, pdf_path=pdf, png_path=png)
            self.panel._drawing_document = document
            self.panel._last_png = png
            pixmap = self.QtGui.QPixmap(str(png))
            candidates = self.build_snap_candidates(document, entity_id="P1")
            self.panel._snap_candidates = candidates
            self.panel.preview.set_drawing(pixmap, document, candidates)
            self.panel.preview.set_selected_ids(self.panel._dimension_model.selected_ids)

        self.panel.refresh_preview = refresh
        refresh()
        self.panel.resize(1500, 900)
        self.panel.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()
        self.temporary.cleanup()

    def _build_document(self):
        return self.ProductionDrawingEngine.build(
            self.DrawingBuildRequest(
                entity_id="P1",
                vertices=self.vertices,
                triangles=self.triangles,
                views=("front",),
                sheet_format="A4",
                orientation="landscape",
                dimension_mode="Productiematen",
                include_sections=False,
                include_details=False,
                manual_dimensions=self.panel._dimension_document.render_records(),
                dimension_style=self.panel._dimension_document.style.to_dict(),
                dimension_editor_schema=self.panel._dimension_document.schema,
                dimension_editor_status=self.panel._dimension_document.status,
                geometry_basis="canonical_rebuild_brep",
                geometry_sha256="a" * 64,
                manufacturing_sha256="b" * 64,
                expected_manufacturing_sha256="b" * 64,
                source_revision="A",
                canonical_rebuild_current=True,
                canonical_payload_current=True,
                roundtrip_current=True,
                title_block={"project": "CWS", "entity": "P1", "profile": "PL100", "material": "S355", "revision": "A", "status": "released"},
            )
        )

    def _click_sheet(self, point, *, modifiers=None) -> None:
        widget_point = self.panel.preview.sheet_to_widget(point).toPoint()
        self.QtTest.QTest.mouseMove(self.panel.preview, widget_point)
        self.application.processEvents()
        self.QtTest.QTest.mouseClick(
            self.panel.preview,
            self.QtCore.Qt.MouseButton.LeftButton,
            modifiers or self.QtCore.Qt.KeyboardModifier.NoModifier,
            widget_point,
        )
        self.application.processEvents()

    def test_real_qt_point_pick_place_select_drag_hide_delete_undo(self) -> None:
        candidates = [item for item in self.panel._snap_candidates if item.snap_type == "endpoint"]
        first = candidates[0]
        second = max(candidates[1:], key=lambda item: abs(item.anchor.projected_point[0] - first.anchor.projected_point[0]))
        self.QtTest.QTest.mouseClick(
            self.panel.dimension_tool_buttons[self.DimensionKind.HORIZONTAL.value],
            self.QtCore.Qt.MouseButton.LeftButton,
        )
        self._click_sheet(first.point)
        self.assertEqual(len(self.panel._dimension_controller.anchors), 1)
        self.QtTest.QTest.mouseMove(self.panel.preview, self.panel.preview.sheet_to_widget(first.point).toPoint())
        self.application.processEvents()
        if len(self.panel.preview._hover_candidates) > 1:
            candidate_before = self.panel.preview.current_candidate.candidate_id
            self.QtTest.QTest.keyClick(self.panel.preview, self.QtCore.Qt.Key.Key_Tab)
            self.assertNotEqual(self.panel.preview.current_candidate.candidate_id, candidate_before)
        self._click_sheet(second.point)
        self.assertEqual(self.panel._dimension_controller.state.value, "PLACE_DIMENSION_LINE")
        placement = ((first.point[0] + second.point[0]) * 0.5, max(first.point[1], second.point[1]) + 18.0)
        self._click_sheet(placement)
        self.assertEqual(len(self.panel._dimension_document.dimensions), 1)
        dimension = self.panel._dimension_document.dimensions[0]
        self.assertGreater(dimension.nominal_value_mm, 0.0)
        self.assertEqual(
            dimension.dimension_id,
            self.workspace.project.settings["drawing_dimension_editor_v2"]["documents"]["P1::production"]["dimensions"][0]["dimension_id"],
        )

        rendered = next(
            primitive
            for primitive in self.panel._drawing_document.pages[0].primitives
            if primitive.semantic_id == dimension.dimension_id
        )
        midpoint = (
            (rendered.points[0][0] + rendered.points[1][0]) * 0.5,
            (rendered.points[0][1] + rendered.points[1][1]) * 0.5,
        )
        self._click_sheet(midpoint)
        self.assertEqual(self.panel._dimension_model.selected_ids, {dimension.dimension_id})
        self.assertTrue(self.panel.edit_properties_button.isEnabled())

        start = self.panel.preview.sheet_to_widget(midpoint).toPoint()
        end = start + self.QtCore.QPoint(35, 20)
        before = dimension.line_position
        self.QtTest.QTest.mousePress(self.panel.preview, self.QtCore.Qt.MouseButton.LeftButton, pos=start)
        self.QtTest.QTest.mouseMove(self.panel.preview, end, delay=20)
        self.QtTest.QTest.mouseRelease(self.panel.preview, self.QtCore.Qt.MouseButton.LeftButton, pos=end)
        self.application.processEvents()
        self.assertNotEqual(self.panel._dimension_document.dimensions[0].line_position, before)

        hide_button = self.panel.dimension_action_buttons["Verberg/toon selectie"]
        self.QtTest.QTest.mouseClick(hide_button, self.QtCore.Qt.MouseButton.LeftButton)
        self.assertFalse(self.panel._dimension_document.dimensions[0].visible)
        self.QtTest.QTest.keyClick(self.panel.preview, self.QtCore.Qt.Key.Key_Z, self.QtCore.Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(self.panel._dimension_document.dimensions[0].visible)
        self.QtTest.QTest.keyClick(self.panel.preview, self.QtCore.Qt.Key.Key_Delete)
        self.assertEqual(self.panel._dimension_document.dimensions, [])
        self.QtTest.QTest.keyClick(self.panel.preview, self.QtCore.Qt.Key.Key_Z, self.QtCore.Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(len(self.panel._dimension_document.dimensions), 1)

        restored = self.panel._dimension_document.dimensions[0]
        restored_primitive = next(
            primitive
            for primitive in self.panel._drawing_document.pages[0].primitives
            if primitive.semantic_id == restored.dimension_id and len(primitive.points) >= 2
        )
        restored_midpoint = (
            (restored_primitive.points[0][0] + restored_primitive.points[1][0]) * 0.5,
            (restored_primitive.points[0][1] + restored_primitive.points[1][1]) * 0.5,
        )
        self._click_sheet(restored_midpoint)
        self.assertEqual(self.panel._dimension_model.selected_ids, {restored.dimension_id})
        duplicate_button = self.panel.dimension_action_buttons["Selectie dupliceren"]
        self.QtTest.QTest.mouseClick(duplicate_button, self.QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.panel._dimension_document.dimensions), 2)
        self.panel._copy_dimensions()
        copied = len(self.panel._dimension_clipboard)
        self.assertGreaterEqual(copied, 1)
        self.panel._paste_dimensions()
        self.assertEqual(len(self.panel._dimension_document.dimensions), 2 + copied)

        page = self.panel._drawing_document.pages[0]
        drag_start = self.panel.preview.sheet_to_widget((3.0, 3.0)).toPoint()
        drag_end = self.panel.preview.sheet_to_widget((page.width_mm - 3.0, page.height_mm - 38.0)).toPoint()
        self.QtTest.QTest.mousePress(self.panel.preview, self.QtCore.Qt.MouseButton.LeftButton, pos=drag_start)
        self.QtTest.QTest.mouseMove(self.panel.preview, drag_end, delay=20)
        self.QtTest.QTest.mouseRelease(self.panel.preview, self.QtCore.Qt.MouseButton.LeftButton, pos=drag_end)
        self.application.processEvents()
        self.assertGreaterEqual(len(self.panel._dimension_model.selected_ids), 2)

        pan_before = self.QtCore.QPointF(self.panel.preview._pan)
        pan_start = self.panel.preview.sheet_to_widget((page.width_mm * 0.5, page.height_mm * 0.5)).toPoint()
        pan_end = pan_start + self.QtCore.QPoint(30, 20)
        self.QtTest.QTest.mousePress(self.panel.preview, self.QtCore.Qt.MouseButton.MiddleButton, pos=pan_start)
        self.QtTest.QTest.mouseMove(self.panel.preview, pan_end, delay=20)
        self.QtTest.QTest.mouseRelease(self.panel.preview, self.QtCore.Qt.MouseButton.MiddleButton, pos=pan_end)
        self.application.processEvents()
        self.assertNotEqual(self.panel.preview._pan, pan_before)
        self.panel.preview.fit_to_view()

        self.QtTest.QTest.mouseClick(
            self.panel.dimension_tool_buttons[self.DimensionKind.VERTICAL.value],
            self.QtCore.Qt.MouseButton.LeftButton,
        )
        self.assertNotEqual(self.panel._dimension_tool, "select")
        self.QtTest.QTest.keyClick(self.panel.preview, self.QtCore.Qt.Key.Key_Escape)
        self.assertEqual(self.panel._dimension_tool, "select")

        screenshot = self.root / "PDF12-GUI-001_POINT_PICK_PASS.png"
        self.assertTrue(self.panel.grab().save(str(screenshot)))
        self.assertGreater(screenshot.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
