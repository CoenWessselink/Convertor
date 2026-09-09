"""Regression cases found while integrating the V3 production workspace."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from interactive_dimension_editor_v2_smoke import _build, _editor_document
from cws_convertor.drawings import (
    DimensionEditorModel, DimensionInteractionController, DimensionKind,
    DimensionStyle, DrawingRole, ProductionDrawingEngine,
    ProductionDrawingRenderer, build_snap_candidates,
)


def placed(kind="horizontal"):
    drawing = _build()
    anchors = [c.anchor for c in build_snap_candidates(drawing)
               if c.snap_type == "endpoint" and c.layer == "visible"]
    first = anchors[0]
    second = max(anchors[1:], key=lambda a: abs(a.projected_point[0] - first.projected_point[0]))
    document = _editor_document()
    controller = DimensionInteractionController()
    controller.arm(kind)
    controller.accept_anchor(first)
    controller.accept_anchor(second)
    item = controller.place((130.0, 130.0), document=document, user="v3-test")
    model = DimensionEditorModel(document)
    model.add(item, user="v3-test")
    return document, model, item


class V3DimensionRegressions(unittest.TestCase):
    def test_overlapping_components_remain_separately_selectable(self):
        drawing = _build()
        primitive = next(p for p in drawing.pages[0].primitives if p.layer == "visible")
        first, second = deepcopy(primitive), deepcopy(primitive)
        first.refs = ["entity:P1"]
        second.refs = ["entity:P2"]
        drawing.pages[0].primitives = [first, second, deepcopy(first)]
        candidates = build_snap_candidates(drawing, include_intersections=False)
        at_point = [c for c in candidates if c.point == tuple(first.points[0]) and c.snap_type == "endpoint"]
        self.assertEqual({c.anchor.entity_id for c in at_point}, {"P1", "P2"})
        self.assertEqual(len(at_point), 2)
        self.assertEqual(len(candidates), len({c.candidate_id for c in candidates}))

    def test_hover_description_identifies_entity_and_view(self):
        candidate = build_snap_candidates(_build())[0]
        self.assertIn(candidate.anchor.entity_id, candidate.label)
        self.assertIn(candidate.anchor.view_id, candidate.label)

    def test_style_undo_restores_document_style_and_object_binding(self):
        document, model, item = placed()
        original = document.style.to_dict()
        style = DimensionStyle.from_dict(original)
        style.profile_scope = "project"
        style.style_id = "v3-project"
        style.text_height_mm += 0.5
        model.update_style(style, reason="Readability", role=DrawingRole.CHECKER.value, user="reviewer")
        self.assertTrue(model.undo())
        self.assertEqual(document.style.to_dict(), original)
        self.assertEqual(document.dimensions[0].style_id, document.style.style_id)
        self.assertTrue(model.redo())
        self.assertEqual(document.style.style_id, "v3-project")
        self.assertEqual(document.dimensions[0].style_id, document.style.style_id)
        self.assertIn("style_change", next(a for a in document.audit if a["action"] == "dimension.style_changed")["details"])

    def test_release_blocks_undo_and_redo_without_mutation(self):
        document, model, item = placed()
        for anchor in item.anchors:
            anchor.proof = "canonical_projection"
        model.release(role=DrawingRole.RELEASER.value)
        before = document.to_dict()
        for action in (model.undo, model.redo):
            with self.assertRaises(PermissionError):
                action()
            self.assertEqual(document.to_dict(), before)
        model.begin_revision(reason="New revision")
        self.assertFalse(model.undo(), "History may not reach back into a released revision")
        self.assertEqual(len(document.dimensions), 1)
        self.assertEqual(len(document.extensions["released_revisions"][0]["dimensions"]), 1)

    def test_reanchor_refreshes_component_identity(self):
        document, model, item = placed()
        replacement = deepcopy(item.anchors[1])
        replacement.entity_id = "P2"
        model.reanchor(item.dimension_id, 1, replacement)
        self.assertEqual(set(item.entity_ids), {"P1", "P2"})
        self.assertEqual([a.entity_id for a in item.anchors], ["P1", "P2"])
        model.undo()
        self.assertEqual(document.dimensions[0].entity_ids, ("P1",))

    def test_nonfinite_tolerance_fails_before_transaction(self):
        document, model, _ = placed()
        before = document.to_dict()
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaises(ValueError):
                model.update_selected({"tolerance_upper_mm": value})
            self.assertEqual(document.to_dict(), before)

    def test_geometric_label_requires_explicit_override(self):
        document, model, item = placed()
        before = document.to_dict()
        with self.assertRaises(ValueError):
            model.update_selected({"label": "9999"})
        self.assertEqual(document.to_dict(), before)
        model.override_selected(display_text="9999", reason="Reference only", role=DrawingRole.DRAFTER.value)
        self.assertEqual(item.nominal_value_mm, before["dimensions"][0]["nominal_value_mm"])
        self.assertEqual(item.state, "OVERRIDDEN")

    def test_integer_precision_never_truncates_significant_zeroes(self):
        for value in (0, 10, 100, 150, 1000):
            text = ProductionDrawingEngine._interactive_label(
                {"kind": "horizontal", "nominal_value_mm": value,
                 "style": {"decimals": 0, "trailing_zeros": False}}, "mm")
            self.assertEqual(text, f"{value} mm")

    def test_angle_is_not_divided_by_ten_for_centimetre_sheet(self):
        value = {"kind": "angle", "nominal_value_mm": 90.0}
        self.assertEqual(ProductionDrawingEngine._interactive_label(value, "cm"),
                         ProductionDrawingEngine._interactive_label(value, "mm"))

    def test_signed_tolerances_do_not_produce_plus_minus_prefix(self):
        value = {"kind": "horizontal", "nominal_value_mm": 100,
                 "tolerance_upper_mm": -0.1, "tolerance_lower_mm": -0.3}
        self.assertIn("-0.1/-0.3", ProductionDrawingEngine._interactive_label(value, "mm"))

    def test_text_grip_changes_vector_output_independently_of_line(self):
        document, model, item = placed()
        def render():
            return _build(manual_dimensions=document.render_records(),
                          dimension_style=document.style.to_dict())
        before = render()
        old_lines = [asdict(p) for p in before.pages[0].primitives
                     if p.semantic_id == item.dimension_id and p.kind == "line"]
        old_text = next(p for p in before.pages[0].primitives
                        if p.semantic_id == item.dimension_id and p.kind == "text")
        model.move_selected((7.0, -3.0), text_only=True)
        after = render()
        new_lines = [asdict(p) for p in after.pages[0].primitives
                     if p.semantic_id == item.dimension_id and p.kind == "line"]
        new_text = next(p for p in after.pages[0].primitives
                        if p.semantic_id == item.dimension_id and p.kind == "text")
        self.assertEqual(old_lines, new_lines)
        self.assertAlmostEqual(new_text.points[0][0] - old_text.points[0][0], 7.0)
        self.assertAlmostEqual(new_text.points[0][1] - old_text.points[0][1], -3.0)
        import fitz
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / "before.pdf", Path(folder) / "after.pdf"]
            for drawing, path in zip((before, after), paths):
                ProductionDrawingRenderer.render(drawing, pdf_path=path)
            with fitz.open(paths[0]) as a, fitz.open(paths[1]) as b:
                self.assertNotEqual(a[0].get_pixmap().samples, b[0].get_pixmap().samples)
                self.assertGreater(len(b[0].get_drawings()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
