from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.drawings import (
    DIMENSION_EDITOR_SCHEMA,
    DimensionDocumentStore,
    DimensionEditorDocument,
    DimensionEditorModel,
    DimensionInteractionController,
    DimensionKind,
    DimensionState,
    DimensionStyle,
    DrawingRole,
    DrawingAnchor,
    DrawingBuildRequest,
    InteractionState,
    InteractiveDimension,
    ProductionDrawingEngine,
    SnapType,
    SnapFilter,
    build_snap_candidates,
    calculate_nominal_value,
    nearest_snap_candidate,
)
from cws_convertor.project.model import ProjectModel


HASH_A = "a" * 64
HASH_B = "b" * 64


def _mesh() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.asarray(
        ((0, 0, 0), (100, 0, 0), (100, 50, 0), (0, 50, 0), (0, 0, 10), (100, 0, 10), (100, 50, 10), (0, 50, 10)),
        dtype=float,
    )
    triangles = np.asarray(
        ((0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)),
        dtype=int,
    )
    return vertices, triangles


def _build(**changes):
    vertices, triangles = _mesh()
    values = dict(
        entity_id="P1",
        vertices=vertices,
        triangles=triangles,
        views=("front",),
        sheet_format="A4",
        orientation="landscape",
        dimension_mode="Productiematen",
        include_sections=False,
        include_details=False,
        geometry_basis="canonical_rebuild_brep",
        geometry_sha256=HASH_A,
        manufacturing_sha256=HASH_B,
        expected_manufacturing_sha256=HASH_B,
        canonical_rebuild_current=True,
        canonical_payload_current=True,
        roundtrip_current=True,
        source_revision="A",
        title_block={"project": "CWS", "entity": "P1", "profile": "PL100", "material": "S355", "revision": "A", "status": "released"},
    )
    values.update(changes)
    return ProductionDrawingEngine.build(DrawingBuildRequest(**values))


def _editor_document() -> DimensionEditorDocument:
    return DimensionEditorDocument(
        project_id="PROJECT",
        entity_id="P1",
        drawing_id="production",
        source_revision="A",
        drawing_revision="draft-1",
        geometry_sha256=HASH_A,
        manufacturing_sha256=HASH_B,
    )


class InteractiveDimensionEditorV2Tests(unittest.TestCase):
    def test_dimension_style_schema_profiles_and_release_approval(self) -> None:
        import json

        standard = DimensionStyle.cws_standard()
        schema = json.loads(
            (ROOT / "cws_convertor" / "drawings" / "schemas" / "dimension_style_v2.schema.json").read_text(encoding="utf-8")
        )
        standard.validate()
        self.assertTrue(set(schema["required"]) <= set(standard.to_dict()))
        document = _editor_document()
        anchors = [
            item.anchor
            for item in build_snap_candidates(_build())
            if item.snap_type == SnapType.ENDPOINT.value and item.layer == "visible"
        ][:2]
        for anchor in anchors:
            anchor.proof = "canonical_projection"
        dimension = InteractiveDimension(
            dimension_id="styled-1",
            kind=DimensionKind.HORIZONTAL.value,
            entity_ids=("P1",),
            drawing_id="production",
            view_id="sheet-1-front-1",
            sheet_id="sheet-1",
            page_number=1,
            anchors=anchors,
            nominal_value_mm=calculate_nominal_value(DimensionKind.HORIZONTAL.value, anchors),
            line_position=(12.5, 20.0),
            text_position=(12.5, 18.2),
            source_revision="A",
            drawing_revision="draft-1",
            geometry_sha256=HASH_A,
            manufacturing_sha256=HASH_B,
        )
        document.dimensions.append(dimension)
        model = DimensionEditorModel(document)
        custom = DimensionStyle.from_dict(standard.to_dict())
        custom.style_id = "project-steel"
        custom.version = "1.0"
        custom.profile_scope = "project"
        custom.text_height_mm = 3.0
        model.update_style(
            custom,
            reason="Projectafspraak",
            role=DrawingRole.CHECKER.value,
            user="controleur",
        )
        self.assertEqual(document.style.approved_by, "controleur")
        dimension.state = DimensionState.RESOLVED.value
        model.release(role=DrawingRole.RELEASER.value, user="vrijgever")
        self.assertEqual(document.status, "released")

    def test_all_snap_types_and_filters_are_available_without_screen_only_state(self) -> None:
        drawing = _build(
            features=(
                {"feature_id": "H1", "kind": "hole", "parameters": {"x_mm": 25.0, "y_mm": 20.0, "diameter_mm": 12.0}},
                {"feature_id": "P1", "kind": "pocket", "parameters": {"x_mm": 65.0, "y_mm": 25.0, "width_mm": 18.0, "height_mm": 12.0}},
            )
        )
        all_candidates = build_snap_candidates(drawing)
        snap_types = {item.snap_type for item in all_candidates}
        self.assertTrue(
            {
                SnapType.VERTEX.value,
                SnapType.ENDPOINT.value,
                SnapType.MIDPOINT.value,
                SnapType.INTERSECTION.value,
                SnapType.CENTER.value,
                SnapType.TANGENT.value,
                SnapType.DATUM.value,
                SnapType.FEATURE.value,
                SnapType.EXISTING_ANCHOR.value,
            }
            <= snap_types,
            snap_types,
        )
        endpoint = next(
            item
            for item in all_candidates
            if item.snap_type == SnapType.ENDPOINT.value and item.layer == "visible"
        )
        nearest = nearest_snap_candidate(drawing, endpoint.point, page_number=1)
        self.assertEqual(nearest.snap_type, SnapType.NEAREST.value)
        for snap_filter in SnapFilter:
            with self.subTest(snap_filter=snap_filter.value):
                self.assertTrue(build_snap_candidates(drawing, snap_filter=snap_filter.value))

    def test_snap_candidates_keep_semantic_projected_anchors(self) -> None:
        drawing = _build()
        candidates = build_snap_candidates(drawing)
        self.assertGreater(len(candidates), 6)
        endpoint = next(
            item for item in candidates
            if item.snap_type == SnapType.ENDPOINT.value and item.layer == "visible"
        )
        self.assertEqual(endpoint.anchor.entity_id, "P1")
        self.assertEqual(endpoint.anchor.geometry_sha256, HASH_A)
        self.assertEqual(endpoint.anchor.manufacturing_sha256, HASH_B)
        self.assertEqual(endpoint.anchor.proof, "review_projection")
        self.assertEqual(len(endpoint.anchor.projected_point), 2)
        self.assertTrue(endpoint.anchor.subshape_id)
        nearest = nearest_snap_candidate(drawing, endpoint.point, page_number=1)
        self.assertIsNotNone(nearest)
        self.assertEqual(nearest.snap_type, SnapType.NEAREST.value)

    def test_two_point_state_machine_calculates_geometry_not_screen_label(self) -> None:
        editor_document = _editor_document()
        drawing = _build()
        candidates = [item for item in build_snap_candidates(drawing) if item.snap_type == SnapType.ENDPOINT.value]
        first = candidates[0].anchor
        second = max(candidates[1:], key=lambda item: abs(item.anchor.projected_point[0] - first.projected_point[0])).anchor
        controller = DimensionInteractionController()
        controller.arm(DimensionKind.HORIZONTAL.value)
        self.assertEqual(controller.state, InteractionState.PICK_FIRST_ANCHOR)
        self.assertEqual(controller.state_history[-2:], [InteractionState.TOOL_ARMED, InteractionState.PICK_FIRST_ANCHOR])
        controller.accept_anchor(first)
        self.assertEqual(controller.state, InteractionState.PICK_NEXT_ANCHOR)
        controller.accept_anchor(second)
        self.assertEqual(controller.state, InteractionState.PLACE_DIMENSION_LINE)
        dimension = controller.place((120.0, 90.0), document=editor_document, label="")
        self.assertAlmostEqual(dimension.nominal_value_mm, abs(second.projected_point[0] - first.projected_point[0]))
        self.assertEqual(controller.state, InteractionState.COMMITTED)

    def test_transactions_individual_delete_hide_move_and_undo_redo(self) -> None:
        drawing = _build()
        anchors = [item.anchor for item in build_snap_candidates(drawing) if item.snap_type == SnapType.ENDPOINT.value][:2]
        controller = DimensionInteractionController()
        controller.arm(DimensionKind.ALIGNED.value)
        controller.accept_anchor(anchors[0])
        controller.accept_anchor(anchors[1])
        document = _editor_document()
        dimension = controller.place((120.0, 80.0), document=document)
        model = DimensionEditorModel(document, clock=lambda: "2026-09-03T12:00:00+00:00")
        model.add(dimension, user="tester")
        original_value = dimension.nominal_value_mm
        model.move_selected((5.0, -3.0), user="tester")
        self.assertEqual(document.dimensions[0].line_position, (125.0, 77.0))
        self.assertEqual(document.dimensions[0].nominal_value_mm, original_value)
        model.set_visibility(False, user="tester")
        self.assertFalse(document.dimensions[0].visible)
        self.assertTrue(model.undo(user="tester"))
        self.assertTrue(document.dimensions[0].visible)
        self.assertTrue(model.redo(user="tester"))
        self.assertFalse(document.dimensions[0].visible)
        self.assertEqual(model.delete_selected(user="tester"), 1)
        self.assertEqual(document.dimensions, [])
        self.assertTrue(model.undo(user="tester"))
        self.assertEqual(len(document.dimensions), 1)

    def test_project_roundtrip_is_entity_isolated_and_conflict_guarded(self) -> None:
        project = ProjectModel.new("maatvoering")
        document = _editor_document()
        first_version = DimensionDocumentStore.save(project, document, expected_lock_version=0, user="tester")
        self.assertEqual(first_version, 1)
        restored_project = ProjectModel.from_dict(project.to_dict())
        restored = DimensionDocumentStore.load(restored_project, entity_id="P1")
        self.assertEqual(restored.to_dict(), document.to_dict())
        other = DimensionDocumentStore.load(restored_project, entity_id="P2")
        self.assertEqual(other.entity_id, "P2")
        self.assertEqual(other.dimensions, [])
        stale_copy = DimensionEditorDocument.from_dict(deepcopy(document.to_dict()))
        DimensionDocumentStore.save(restored_project, restored, expected_lock_version=1, user="tester")
        with self.assertRaisesRegex(RuntimeError, "last-write-wins"):
            DimensionDocumentStore.save(restored_project, stale_copy, expected_lock_version=1, user="tester")

    def test_interactive_record_renders_and_linter_fails_closed_when_stale(self) -> None:
        base = _build()
        anchors = [item.anchor for item in build_snap_candidates(base) if item.snap_type == SnapType.ENDPOINT.value][:2]
        for anchor in anchors:
            anchor.proof = "canonical_projection"
        controller = DimensionInteractionController()
        controller.arm(DimensionKind.HORIZONTAL.value)
        controller.accept_anchor(anchors[0])
        controller.accept_anchor(anchors[1])
        editor_document = _editor_document()
        dimension = controller.place((120.0, 80.0), document=editor_document)
        editor_document.dimensions.append(dimension)
        drawing = _build(
            manual_dimensions=editor_document.render_records(),
            dimension_style=editor_document.style.to_dict(),
            dimension_audit=editor_document.audit,
            dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
            dimension_editor_status="released",
        )
        placed = {
            primitive.semantic_id
            for page in drawing.pages
            for primitive in page.primitives
            if primitive.layer == "dimensions"
        }
        self.assertIn(dimension.dimension_id, placed)
        interactive_codes = {
            item["code"]
            for item in drawing.lint["issues"]
            if item["code"].startswith("DRAWING_MANUAL_DIMENSION")
        }
        self.assertEqual(interactive_codes, set(), drawing.lint["issues"])
        stale = dimension.to_render_dict()
        stale["state"] = DimensionState.STALE.value
        blocked = _build(
            manual_dimensions=(stale,),
            dimension_style=editor_document.style.to_dict(),
            dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
            dimension_editor_status="released",
        )
        codes = {item["code"] for item in blocked.lint["issues"]}
        self.assertIn("DRAWING_MANUAL_DIMENSION_STALE", codes)
        self.assertFalse(blocked.lint["release_ready"])

    def test_legacy_numeric_dimension_remains_renderable_but_migrates_review_only(self) -> None:
        legacy = {"id": "legacy-1", "view": "front", "axis": "horizontal", "start": 0.0, "end": 25.0, "feature_id": "part-envelope", "anchor_type": "datum_offset"}
        drawing = _build(manual_dimensions=(legacy,))
        self.assertIn("legacy-1", {primitive.semantic_id for page in drawing.pages for primitive in page.primitives})
        document = _editor_document()
        self.assertEqual(DimensionDocumentStore.migrate_legacy((legacy,), document, user="tester"), 1)
        self.assertEqual(document.dimensions[0].state, DimensionState.STALE.value)
        self.assertEqual(document.dimensions[0].metadata["migrated_from"], "legacy_numeric_offset")

    def test_revalidation_detects_conflict_removed_geometry_and_preserves_moved_state(self) -> None:
        drawing = _build()
        candidates = [item.anchor for item in build_snap_candidates(drawing) if item.snap_type == SnapType.ENDPOINT.value][:2]
        controller = DimensionInteractionController()
        controller.arm(DimensionKind.ALIGNED.value)
        controller.accept_anchor(candidates[0])
        controller.accept_anchor(candidates[1])
        document = _editor_document()
        dimension = controller.place((120.0, 80.0), document=document)
        document.dimensions.append(dimension)
        model = DimensionEditorModel(document)
        model.select((dimension.dimension_id,))
        model.move_selected((2.0, 1.0), user="tester")
        model.revalidate(drawing, valid_view_ids=(item["view_id"] for item in drawing.view_contexts))
        self.assertEqual(dimension.state, DimensionState.MOVED.value)
        dimension.nominal_value_mm += 5.0
        model.revalidate(drawing, valid_view_ids=(item["view_id"] for item in drawing.view_contexts))
        self.assertEqual(dimension.state, DimensionState.CONFLICT.value)
        dimension.nominal_value_mm -= 5.0
        dimension.anchors[0].subshape_id = "deleted-edge"
        model.revalidate(drawing, valid_view_ids=(item["view_id"] for item in drawing.view_contexts))
        self.assertEqual(dimension.state, DimensionState.ORPHANED.value)

    def test_reanchor_and_direct_release_are_fail_closed_on_context_or_hash_mismatch(self) -> None:
        drawing = _build()
        anchors = [item.anchor for item in build_snap_candidates(drawing) if item.snap_type == SnapType.ENDPOINT.value][:2]
        for anchor in anchors:
            anchor.proof = "canonical_projection"
        controller = DimensionInteractionController()
        controller.arm(DimensionKind.HORIZONTAL.value)
        controller.accept_anchor(anchors[0])
        controller.accept_anchor(anchors[1])
        document = _editor_document()
        dimension = controller.place((120.0, 80.0), document=document)
        document.dimensions.append(dimension)
        model = DimensionEditorModel(document)
        model.select((dimension.dimension_id,))
        invalid_context = deepcopy(anchors[0])
        invalid_context.view_id = "sheet-2-detail-1"
        invalid_context.sheet_id = "sheet-2"
        invalid_context.page_number = 2
        with self.assertRaisesRegex(ValueError, "hetzelfde aanzicht"):
            model.reanchor(dimension.dimension_id, 0, invalid_context, user="tester")
        dimension.anchors[0].geometry_sha256 = "c" * 64
        with self.assertRaisesRegex(ValueError, "Inconsistente"):
            model.release(role=DrawingRole.RELEASER.value, user="vrijgever")

    def test_controlled_text_override_requires_reason_and_approval_for_release(self) -> None:
        drawing = _build()
        anchors = [item.anchor for item in build_snap_candidates(drawing) if item.snap_type == SnapType.ENDPOINT.value][:2]
        controller = DimensionInteractionController()
        controller.arm(DimensionKind.HORIZONTAL.value)
        controller.accept_anchor(anchors[0])
        controller.accept_anchor(anchors[1])
        document = _editor_document()
        dimension = controller.place((120.0, 80.0), document=document)
        model = DimensionEditorModel(document)
        model.add(dimension, user="maker")
        with self.assertRaises(ValueError):
            model.override_selected(display_text="100 TYP", reason="", role=DrawingRole.DRAFTER.value, user="maker")
        model.override_selected(display_text="100 TYP", reason="Klantnotatie", role=DrawingRole.DRAFTER.value, user="maker")
        self.assertEqual(dimension.state, DimensionState.OVERRIDDEN.value)
        self.assertEqual(dimension.override_approved_by, "")
        blocked = _build(
            manual_dimensions=document.render_records(),
            dimension_style=document.style.to_dict(),
            dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
            dimension_editor_status="released",
        )
        self.assertIn(
            "DRAWING_MANUAL_DIMENSION_OVERRIDE_UNAPPROVED",
            {item["code"] for item in blocked.lint["issues"]},
        )
        model.override_selected(display_text="100 TYP", reason="Klantnotatie", role=DrawingRole.CHECKER.value, user="checker")
        self.assertEqual(dimension.override_approved_by, "checker")


if __name__ == "__main__":
    unittest.main(verbosity=2)
