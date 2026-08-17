from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.measurements import ExactMeasurementAnchor, MeasurementProof, SnapType, distance
from cws_viewer.review import MarkupKind
from cws_viewer.review.phase2_service import (
    Phase2ReviewWorkspaceService,
    phase2_review_contract,
)
from cws_viewer.ui_qt.cockpit_phase2_v15 import phase2_workspace_contract
from cws_viewer.ui_qt.view_navigation_phase2 import phase2_navigation_contract


class ViewerV15Phase2ParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scene = build_synthetic_product_scene(40, parts_per_assembly=10)
        self.backend = MemoryRenderBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1280, height=800)
        self.controller.load_scene(self.scene)
        self.service = Phase2ReviewWorkspaceService(
            self.controller,
            project_id=self.scene.project_id,
            scene_hash=self.scene.scene_hash,
            store_path=self.root / "phase2.cwsreview.json",
            project_metadata={"project_name": "Phase 2 fixture", "revision_id": "R2"},
        )

    def tearDown(self) -> None:
        self.controller.shutdown()
        self.temp.cleanup()

    def _pick(self, index: int):
        node_id = self.controller.index.renderable_node_ids[index]
        self.backend.pick_node_id = node_id
        pick = self.controller.pick_at(20 + index, 30 + index)
        self.assertIsNotNone(pick)
        return pick

    def _anchor(self, pick):
        node = self.controller.index.node(pick.node_id)
        return ExactMeasurementAnchor(
            node_id=pick.node_id,
            entity_id=str(pick.entity_id),
            source_entity_id=str(pick.source_entity_id or ""),
            world_point=pick.world_point,
            local_point=pick.local_point,
            geometry_hash=node.geometry_hash,
            snap_type=SnapType.NEAREST,
            proof=MeasurementProof.VERIFIED_MESH,
            normal=pick.normal,
        )

    def test_phase2_contract_preserves_phase1_and_adds_real_review_workflows(self) -> None:
        contract = phase2_workspace_contract()
        caps = contract["capabilities"]
        for name in (
            "startup_geometry_cache_prefetch",
            "lazy_review_coordination_export_manufacturing",
            "interactive_markup_text",
            "interactive_markup_line",
            "interactive_markup_arrow",
            "interactive_markup_cloud",
            "interactive_markup_freehand",
            "markup_live_preview",
            "markup_world_space_overlay",
            "markup_preserves_semantic_selection",
            "saved_view_review_snapshot",
            "saved_view_markup_visibility",
            "saved_view_measurement_visibility",
            "view_groups",
            "view_group_reorder",
            "view_slideshow",
            "picked_surface_section_plane",
            "section_plane_offset_control",
            "variable_clip_box_fraction",
            "reset_model_display_state",
            "phase2_actual_vtk_input_host",
        ):
            self.assertTrue(caps[name], name)
        self.assertFalse(
            contract["phase2"]["review"]["safety"]["review_mutates_canonical_geometry"]
        )
        self.assertFalse(
            contract["phase2"]["navigation"]["safety"]["clipping_mutates_canonical_geometry"]
        )
        self.assertTrue(phase2_review_contract()["capabilities"]["interactive_markup_line"])
        self.assertTrue(
            phase2_navigation_contract()["capabilities"]["section_plane_offset_control"]
        )

    def test_line_cloud_and_freehand_are_true_multi_point_review_geometry(self) -> None:
        before_hash = self.controller.index.scene.scene_hash
        first, second, third = self._pick(0), self._pick(1), self._pick(2)
        line = self.service.create_markup_from_gesture(
            {
                "kind": "line",
                "text": "Lijn",
                "picks": (first, second),
                "world_points_mm": (
                    first.world_point.to_tuple(),
                    second.world_point.to_tuple(),
                ),
            },
            created_by="tester",
        )
        cloud = self.service.create_markup_from_gesture(
            {
                "kind": "cloud",
                "picks": (first, second, third),
                "world_points_mm": (
                    first.world_point.to_tuple(),
                    second.world_point.to_tuple(),
                    third.world_point.to_tuple(),
                ),
            }
        )
        freehand = self.service.create_markup_from_gesture(
            {
                "kind": "freehand",
                "picks": (first, first, second, second, third),
                "world_points_mm": (
                    first.world_point.to_tuple(),
                    (first.world_point.x + 1.0, first.world_point.y, first.world_point.z),
                    second.world_point.to_tuple(),
                    (second.world_point.x + 1.0, second.world_point.y, second.world_point.z),
                    third.world_point.to_tuple(),
                ),
            }
        )
        self.assertEqual(MarkupKind.LINE.value, line.kind)
        self.assertEqual(2, len(line.world_points_mm))
        self.assertEqual(3, len(cloud.world_points_mm))
        self.assertEqual(5, len(freehand.world_points_mm))
        self.assertLessEqual(len(freehand.anchors), len(freehand.world_points_mm))
        self.assertEqual(before_hash, self.controller.index.scene.scene_hash)

    def test_markup_drawing_contract_does_not_need_semantic_selection_mutation(self) -> None:
        source = (
            ROOT / "cws_viewer" / "ui_qt" / "vtk_real_project_widget_phase2.py"
        ).read_text(encoding="utf-8")
        self.assertIn("_probe_screen", source)
        self.assertNotIn("self._pick(", source)
        self.assertNotIn("set_selection(", source)
        self.assertIn("markup_gesture_completed", source)
        self.assertIn("cancel_markup_tool", source)

    def test_saved_view_restores_markup_and_measurement_visibility(self) -> None:
        first, second = self._pick(0), self._pick(1)
        markup = self.service.create_markup_from_gesture(
            {
                "kind": "arrow",
                "picks": (first, second),
                "world_points_mm": (
                    first.world_point.to_tuple(),
                    second.world_point.to_tuple(),
                ),
            }
        )
        markup.visible = False
        record = distance(
            self._anchor(first),
            self._anchor(second),
            self.controller.get_measurement_settings(),
        )
        self.controller.add_measurement(record)
        view = self.service.capture_view("Review snapshot", owner="tester")
        snapshot = self.service.view_snapshots[view.viewpoint_id]
        self.assertEqual(False, dict(snapshot.markup_visibility)[markup.markup_id])
        self.assertEqual(True, dict(snapshot.measurement_visibility)[record.measurement_id])

        markup.visible = True
        self.controller._measurements.records[record.measurement_id] = replace(
            record, visible=False
        )
        self.service.activate_saved_view(view.viewpoint_id)
        self.assertFalse(markup.visible)
        restored = {
            item.measurement_id: item for item in self.controller.list_measurements()
        }
        self.assertTrue(restored[record.measurement_id].visible)

    def test_view_group_order_is_persistent_and_deterministic(self) -> None:
        first = self.service.capture_view("A", owner="tester")
        second = self.service.capture_view("B", owner="tester")
        third = self.service.capture_view("C", owner="tester")
        group = self.service.create_view_group("Montage", created_by="tester")
        for view in (first, second, third):
            self.service.add_view_to_group(group.group_id, view.viewpoint_id)
        self.service.move_view_in_group(group.group_id, third.viewpoint_id, -2)
        expected = (third.viewpoint_id, first.viewpoint_id, second.viewpoint_id)
        self.assertEqual(expected, self.service.view_groups[group.group_id].viewpoint_ids)
        self.service.set_view_group_interval(group.group_id, 2.25)
        self.service.save()

        backend2 = MemoryRenderBackend()
        controller2 = V14ViewerCoreController(backend2, width=1280, height=800)
        controller2.load_scene(self.scene)
        try:
            restored = Phase2ReviewWorkspaceService(
                controller2,
                project_id=self.scene.project_id,
                scene_hash=self.scene.scene_hash,
                store_path=self.service.store_path,
            )
            report = restored.load()
            self.assertEqual(1, report["view_groups"])
            loaded = restored.view_groups[group.group_id]
            self.assertEqual(expected, loaded.viewpoint_ids)
            self.assertEqual(2.25, loaded.interval_seconds)
        finally:
            controller2.shutdown()

    def test_line_markup_survives_store_and_portable_package(self) -> None:
        first, second = self._pick(0), self._pick(1)
        line = self.service.create_markup_from_gesture(
            {
                "kind": MarkupKind.LINE.value,
                "text": "Phase 2 line",
                "picks": (first, second),
                "world_points_mm": (
                    first.world_point.to_tuple(),
                    second.world_point.to_tuple(),
                ),
            }
        )
        self.service.save()
        package = self.service.export_package(self.root / "phase2.cwsreview")
        self.assertTrue(package.is_file())

        backend2 = MemoryRenderBackend()
        controller2 = V14ViewerCoreController(backend2, width=1280, height=800)
        controller2.load_scene(self.scene)
        try:
            restored = Phase2ReviewWorkspaceService(
                controller2,
                project_id=self.scene.project_id,
                scene_hash=self.scene.scene_hash,
                store_path=self.service.store_path,
            )
            restored.load()
            self.assertEqual(MarkupKind.LINE.value, restored.markups[line.markup_id].kind)
            self.assertEqual(2, len(restored.markups[line.markup_id].world_points_mm))
        finally:
            controller2.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
