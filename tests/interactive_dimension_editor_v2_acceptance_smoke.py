from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
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
    DrawingAnchor,
    DrawingBuildRequest,
    DrawingRole,
    InteractiveDimension,
    ProductionDrawingEngine,
    ProductionDrawingRenderer,
    SnapType,
    build_snap_candidates,
)
from cws_convertor.project.service import ProjectSession


HASH_A = "a" * 64
HASH_B = "b" * 64


def _mesh() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.asarray(
        ((0, 0, 0), (200, 0, 0), (200, 80, 0), (0, 80, 0), (0, 0, 20), (200, 0, 20), (200, 80, 20), (0, 80, 20)),
        dtype=float,
    )
    triangles = np.asarray(
        ((0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)),
        dtype=int,
    )
    return vertices, triangles


def _request(**changes) -> DrawingBuildRequest:
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
        title_block={"project": "CWS", "entity": "P1", "profile": "PL200", "material": "S355", "revision": "A", "status": "released"},
    )
    values.update(changes)
    return DrawingBuildRequest(**values)


def _editor() -> DimensionEditorDocument:
    return DimensionEditorDocument(
        project_id="PROJECT",
        entity_id="P1",
        drawing_id="production",
        source_revision="A",
        drawing_revision="draft-1",
        geometry_sha256=HASH_A,
        manufacturing_sha256=HASH_B,
    )


def _anchor(x: float, y: float, *, index: int = 1, view_id: str = "sheet-1-front-1") -> DrawingAnchor:
    return DrawingAnchor(
        entity_id="P1",
        feature_id="part-envelope",
        subshape_id=f"edge-{index}",
        view_id=view_id,
        sheet_id="sheet-1",
        page_number=1,
        anchor_type=SnapType.ENDPOINT.value,
        projected_point=(x, y),
        sheet_point=(x, y),
        source_revision="A",
        geometry_sha256=HASH_A,
        manufacturing_sha256=HASH_B,
        proof="canonical_projection",
    )


def _dimension(index: int, kind: str = DimensionKind.HORIZONTAL.value) -> InteractiveDimension:
    anchors = [_anchor(0.0, float(index % 10), index=index), _anchor(20.0 + index % 50, float(index % 10), index=index + 1)]
    if kind == DimensionKind.ANGLE.value:
        anchors.append(_anchor(20.0, 20.0, index=index + 2))
    if kind in {DimensionKind.RADIUS.value, DimensionKind.DIAMETER.value}:
        anchors = [_anchor(10.0, 10.0, index=index)]
        anchors[0].curve_parameter = 9.0
        value = 18.0 if kind == DimensionKind.DIAMETER.value else 9.0
    else:
        value = 20.0 + index % 50
    return InteractiveDimension(
        dimension_id=f"dimension-{index:04d}",
        kind=kind,
        entity_ids=("P1",),
        drawing_id="production",
        view_id="sheet-1-front-1",
        sheet_id="sheet-1",
        page_number=1,
        anchors=anchors,
        nominal_value_mm=value,
        line_position=(80.0 + index % 20, 70.0 + index % 30),
        text_position=(80.0 + index % 20, 68.2 + index % 30),
        source_revision="A",
        drawing_revision="draft-1",
        geometry_sha256=HASH_A,
        manufacturing_sha256=HASH_B,
        created_by="tester",
        modified_by="tester",
    )


class InteractiveDimensionV2AcceptanceTests(unittest.TestCase):
    def test_bulk_layout_clipboard_leader_and_angle_operations_are_transactional(self) -> None:
        editor = _editor()
        editor.dimensions = [_dimension(1), _dimension(2), _dimension(3)]
        model = DimensionEditorModel(editor)
        model.select(item.dimension_id for item in editor.dimensions)
        clipboard = model.copy_selected()
        self.assertEqual(len(clipboard), 3)
        self.assertEqual(model.align_selected("horizontal", user="tester"), 3)
        self.assertEqual(len({item.line_position[1] for item in editor.dimensions}), 1)
        editor.dimensions[0].line_position = (10.0, editor.dimensions[0].line_position[1])
        editor.dimensions[1].line_position = (40.0, editor.dimensions[1].line_position[1])
        editor.dimensions[2].line_position = (100.0, editor.dimensions[2].line_position[1])
        self.assertEqual(model.distribute_selected("horizontal", user="tester"), 3)
        self.assertAlmostEqual(editor.dimensions[1].line_position[0], 55.0)
        nominal = [item.nominal_value_mm for item in editor.dimensions]
        self.assertEqual(model.mirror_selected(user="tester"), 3)
        self.assertEqual([item.nominal_value_mm for item in editor.dimensions], nominal)
        self.assertEqual(model.change_cluster_order(1, user="tester"), 3)
        self.assertTrue(all(item.metadata["cluster_order"] == 1 for item in editor.dimensions))
        self.assertEqual(model.paste(clipboard, user="tester"), 3)
        self.assertEqual(len(editor.dimensions), 6)
        self.assertEqual(len({item.dimension_id for item in editor.dimensions}), 6)

        leader = _dimension(20, DimensionKind.LEADER.value)
        editor.dimensions.append(leader)
        model.select((leader.dimension_id,))
        self.assertEqual(model.set_leader_bend((33.0, 44.0), user="tester"), 1)
        self.assertEqual(leader.metadata["leader_bend_points"], [[33.0, 44.0]])

        angle = _dimension(21, DimensionKind.ANGLE.value)
        editor.dimensions.append(angle)
        model.select((angle.dimension_id,))
        self.assertEqual(model.set_angle_mode("outside", user="tester"), 1)
        outside = angle.nominal_value_mm
        self.assertGreater(outside, 180.0)
        self.assertEqual(model.set_angle_mode("supplementary", user="tester"), 1)
        self.assertLessEqual(angle.nominal_value_mm, 180.0)
        self.assertTrue(model.undo(user="tester"))
        self.assertAlmostEqual(editor.dimensions[-1].nominal_value_mm, outside)

    def test_every_required_dimension_kind_reaches_vector_document(self) -> None:
        editor = _editor()
        kinds = [item.value for item in DimensionKind]
        editor.dimensions = [_dimension(index + 1, kind) for index, kind in enumerate(kinds)]
        editor.status = "released"
        document = ProductionDrawingEngine.build(
            _request(
                manual_dimensions=editor.render_records(),
                dimension_style=editor.style.to_dict(),
                dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
                dimension_editor_status="released",
            )
        )
        placed = {primitive.semantic_id for page in document.pages for primitive in page.primitives if primitive.layer == "dimensions"}
        self.assertEqual({item.dimension_id for item in editor.dimensions} - placed, set())
        self.assertEqual(document.dimension_editor_schema, DIMENSION_EDITOR_SCHEMA)
        self.assertEqual(document.dimension_style["style_id"], "cws-standard")

    def test_sheet_orientation_scale_view_and_unit_pairwise_coverage(self) -> None:
        cases = []
        formats = ("A0", "A1", "A2", "A3", "A4")
        scales = (1, 2, 5, 10, 20, 25, 50, 100, 200)
        views = ("front", "top", "side", "end", "iso", "3d")
        for index, scale in enumerate(scales):
            cases.append((formats[index % len(formats)], "portrait" if index % 2 else "landscape", scale, views[index % len(views)], "cm" if index % 2 else "mm"))
        seen = {"formats": set(), "orientations": set(), "scales": set(), "views": set(), "units": set()}
        for sheet, orientation, scale, view, unit in cases:
            with self.subTest(sheet=sheet, orientation=orientation, scale=scale, view=view, unit=unit):
                document = ProductionDrawingEngine.build(
                    _request(sheet_format=sheet, orientation=orientation, scale_denominator=scale, views=(view,), unit=unit)
                )
                self.assertEqual(document.sheet_format, sheet)
                self.assertEqual(document.orientation, orientation)
                self.assertGreaterEqual(document.scale_denominator, scale)
                self.assertEqual(document.unit, unit)
                seen["formats"].add(sheet)
                seen["orientations"].add(orientation)
                seen["scales"].add(scale)
                seen["views"].add(view)
                seen["units"].add(unit)
        self.assertEqual(seen["formats"], set(formats))
        self.assertEqual(seen["orientations"], {"portrait", "landscape"})
        self.assertEqual(seen["scales"], set(scales))
        self.assertEqual(seen["views"], set(views))
        self.assertEqual(seen["units"], {"mm", "cm"})

    def test_section_and_detail_dimensions_render_on_their_own_sheet(self) -> None:
        features = (
            {"feature_id": "H1", "kind": "hole", "parameters": {"x_mm": 40.0, "y_mm": 20.0, "diameter_mm": 18.0}},
            {"feature_id": "S1", "kind": "slot", "parameters": {"x_mm": 120.0, "y_mm": 30.0, "width_mm": 14.0, "length_mm": 30.0}},
        )
        source = ProductionDrawingEngine.build(
            _request(features=features, include_sections=True, include_details=True)
        )
        contexts = [item for item in source.view_contexts if int(item["page_number"]) > 1]
        self.assertTrue(any(item["view"] == "section" for item in contexts))
        self.assertTrue(any(bool(item.get("detail")) for item in contexts))
        candidates = build_snap_candidates(source)
        editor = _editor()
        for index, context in enumerate(contexts[:2], start=1):
            values = [item.anchor for item in candidates if item.anchor.view_id == context["view_id"]]
            self.assertGreaterEqual(len(values), 2)
            rectangle = context["rectangle"]
            editor.dimensions.append(
                InteractiveDimension(
                    dimension_id=f"page-dimension-{index}",
                    kind=DimensionKind.ALIGNED.value,
                    entity_ids=("P1",),
                    drawing_id="production",
                    view_id=context["view_id"],
                    sheet_id=context["sheet_id"],
                    page_number=int(context["page_number"]),
                    anchors=values[:2],
                    nominal_value_mm=20.0,
                    line_position=((rectangle[0] + rectangle[2]) * 0.5, rectangle[3] - 5.0),
                    text_position=((rectangle[0] + rectangle[2]) * 0.5, rectangle[3] - 6.8),
                    source_revision="A",
                    geometry_sha256=HASH_A,
                    manufacturing_sha256=HASH_B,
                )
            )
        editor.status = "released"
        rendered = ProductionDrawingEngine.build(
            _request(
                features=features,
                include_sections=True,
                include_details=True,
                manual_dimensions=editor.render_records(),
                dimension_style=editor.style.to_dict(),
                dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
                dimension_editor_status="released",
            )
        )
        for item in editor.dimensions:
            placed = {
                primitive.semantic_id
                for primitive in rendered.pages[item.page_number - 1].primitives
                if primitive.layer == "dimensions"
            }
            self.assertIn(item.dimension_id, placed)

    def test_assembly_component_snaps_preserve_child_entity_identity(self) -> None:
        first_vertices, first_triangles = _mesh()
        second_vertices = first_vertices + np.asarray((260.0, 0.0, 0.0))
        combined_vertices = np.concatenate((first_vertices, second_vertices), axis=0)
        combined_triangles = np.concatenate((first_triangles, first_triangles + len(first_vertices)), axis=0)
        document = ProductionDrawingEngine.build(
            _request(
                entity_id="A1",
                document_type="assembly",
                vertices=combined_vertices,
                triangles=combined_triangles,
                assembly_components=(
                    {"entity_id": "P1", "vertices": first_vertices, "triangles": first_triangles},
                    {"entity_id": "P2", "vertices": second_vertices, "triangles": first_triangles},
                ),
            )
        )
        candidates = build_snap_candidates(document)
        by_entity = {
            entity_id: [item for item in candidates if item.anchor.entity_id == entity_id and item.snap_type == SnapType.ENDPOINT.value]
            for entity_id in ("P1", "P2")
        }
        self.assertTrue(by_entity["P1"])
        self.assertTrue(by_entity["P2"])
        controller = DimensionInteractionController()
        controller.arm(DimensionKind.CENTER_DISTANCE.value)
        controller.accept_anchor(by_entity["P1"][0].anchor)
        controller.accept_anchor(by_entity["P2"][0].anchor)
        editor = DimensionEditorDocument(
            project_id="PROJECT",
            entity_id="A1",
            drawing_id="production",
            source_revision="A",
            drawing_revision="draft-1",
            geometry_sha256=HASH_A,
            manufacturing_sha256=HASH_B,
        )
        dimension = controller.place((150.0, 70.0), document=editor, user="tester")
        self.assertEqual(set(dimension.entity_ids), {"P1", "P2"})
        self.assertGreater(dimension.nominal_value_mm, 0.0)

    def test_release_roles_revision_fork_and_immutable_released_snapshot(self) -> None:
        document = _editor()
        document.dimensions = [_dimension(1)]
        model = DimensionEditorModel(document, clock=lambda: "2026-09-03T12:00:00+00:00")
        with self.assertRaises(PermissionError):
            model.release(role=DrawingRole.DRAFTER.value, user="maker")
        model.release(role=DrawingRole.RELEASER.value, user="approver")
        self.assertEqual(document.status, "released")
        model.select(("dimension-0001",))
        with self.assertRaises(PermissionError):
            model.delete_selected(user="maker")
        with self.assertRaises(ValueError):
            model.begin_revision(reason="", user="maker")
        new_revision = model.begin_revision(reason="Profielwijziging", user="maker")
        self.assertEqual(new_revision, "draft-2")
        released = document.extensions["released_revisions"][0]
        model.delete_selected(user="maker")
        self.assertEqual(len(released["dimensions"]), 1)
        self.assertEqual(document.dimensions, [])

    def test_project_save_reopen_and_autosave_keep_dimensions(self) -> None:
        with TemporaryDirectory(prefix="cws-pdf12-roundtrip-") as folder:
            path = Path(folder) / "dimension-project.cwscproj"
            session = ProjectSession.new("Dimension persistence", created_by="tester")
            document = _editor()
            document.project_id = session.project.project_id
            document.dimensions = [_dimension(1), _dimension(2, DimensionKind.VERTICAL.value)]
            DimensionDocumentStore.save(session.project, document, expected_lock_version=0, user="tester")
            session.save(path, user="tester", revision_message="Store interactive dimensions")
            autosave = session.autosave()
            self.assertTrue(autosave.is_file())
            session.close()
            restored_session = ProjectSession.open(path)
            try:
                restored = DimensionDocumentStore.load(restored_session.project, entity_id="P1")
                self.assertEqual([item.dimension_id for item in restored.dimensions], ["dimension-0001", "dimension-0002"])
                self.assertEqual(restored.dimensions[1].kind, DimensionKind.VERTICAL.value)
            finally:
                restored_session.close()

    def test_hash_is_deterministic_and_changes_after_visible_layout_edit(self) -> None:
        editor = _editor()
        editor.dimensions = [_dimension(1)]
        editor.status = "released"
        request = _request(
            manual_dimensions=editor.render_records(),
            dimension_style=editor.style.to_dict(),
            dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
            dimension_editor_status="released",
        )
        first = ProductionDrawingEngine.build(request)
        second = ProductionDrawingEngine.build(request)
        with TemporaryDirectory(prefix="cws-pdf12-hash-") as folder:
            ProductionDrawingRenderer.render_pdf(first, Path(folder) / "first.pdf")
            ProductionDrawingRenderer.render_pdf(second, Path(folder) / "second.pdf")
        self.assertEqual(first.document_sha256, second.document_sha256)
        self.assertEqual(first.visible_content_sha256, second.visible_content_sha256)
        editor.dimensions[0].line_position = (110.0, 95.0)
        changed = ProductionDrawingEngine.build(
            _request(
                manual_dimensions=editor.render_records(),
                dimension_style=editor.style.to_dict(),
                dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
                dimension_editor_status="released",
            )
        )
        with TemporaryDirectory(prefix="cws-pdf12-hash-change-") as folder:
            ProductionDrawingRenderer.render_pdf(changed, Path(folder) / "changed.pdf")
        self.assertNotEqual(first.document_sha256, changed.document_sha256)
        self.assertNotEqual(first.visible_content_sha256, changed.visible_content_sha256)

    def test_500_object_stress_document_and_editor_actions(self) -> None:
        editor = _editor()
        editor.dimensions = [_dimension(index) for index in range(1, 501)]
        editor.status = "released"
        started = time.perf_counter()
        document = ProductionDrawingEngine.build(
            _request(
                views=("front", "top", "side", "iso"),
                manual_dimensions=editor.render_records(),
                dimension_style=editor.style.to_dict(),
                dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
                dimension_editor_status="released",
            )
        )
        elapsed = time.perf_counter() - started
        self.assertGreaterEqual(len(document.pages), 5)
        self.assertEqual(len(document.manual_dimensions), 500)
        self.assertLess(elapsed, 8.0)
        editor.status = "draft"
        model = DimensionEditorModel(editor)
        model.select((item.dimension_id for item in editor.dimensions))
        started = time.perf_counter()
        self.assertEqual(model.move_selected((1.0, 1.0), user="stress"), 500)
        self.assertTrue(model.undo(user="stress"))
        self.assertLess(time.perf_counter() - started, 0.25)

    def test_snap_feedback_generation_stays_within_50_ms_p95(self) -> None:
        drawing = ProductionDrawingEngine.build(_request(views=("front", "top", "side")))
        durations = []
        for _index in range(20):
            started = time.perf_counter()
            candidates = build_snap_candidates(drawing)
            durations.append(time.perf_counter() - started)
        durations.sort()
        p95 = durations[int(len(durations) * 0.95) - 1]
        self.assertGreater(len(candidates), 10)
        self.assertLess(p95, 0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)
