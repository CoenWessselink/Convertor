from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.contracts.enums import ProjectionType, SelectionLevel, StandardView
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.core.v15_navigation import (
    V15_T3_SCHEMA,
    V15_T3_VERSION,
    V15ViewNavigationService,
    navigation_contract,
)
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Vector3
from cws_viewer.ui_qt.cockpit_t3_v15 import (
    V15_T3_WORKSPACE_SCHEMA,
    t3_workspace_contract,
)


class RectMemoryBackend(MemoryRenderBackend):
    def nodes_in_screen_rect(self, x0, y0, x1, y1, index, *, crossing=True):
        del x0, y0, x1, y1, crossing
        return ("node:item:000010", "node:item:000011")


class ViewerV15NavigationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = RectMemoryBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1200, height=800)
        self.scene = build_synthetic_product_scene(30, parts_per_assembly=10)
        self.controller.load_scene(self.scene)
        self.service = V15ViewNavigationService(self.controller)

    def tearDown(self) -> None:
        self.controller.shutdown()

    def test_contract_claims_only_t3_view_capabilities(self) -> None:
        contract = navigation_contract()
        self.assertEqual("cws-viewer-navigation-15.3", V15_T3_SCHEMA)
        self.assertEqual("1.4.0-v15-preview.2", V15_T3_VERSION)
        self.assertEqual(V15_T3_SCHEMA, contract["schema"])
        for name in (
            "orbit_around_picked_point",
            "selection_orbit_focus",
            "zoom_area",
            "camera_history",
            "view_from_face_normal",
            "orthogonal_surface_double_click",
            "camera_positioning",
            "trimble_camera_shortcuts",
            "section_plane_enable_disable",
            "clipping_box",
            "saved_view_contract",
            "deterministic_view_state",
        ):
            self.assertTrue(contract["capabilities"][name])

    def test_t3_workspace_extends_t0_t2_without_removing_docks(self) -> None:
        contract = t3_workspace_contract()
        self.assertEqual("cws-viewer-workspace-15.1", V15_T3_WORKSPACE_SCHEMA)
        self.assertEqual(V15_T3_WORKSPACE_SCHEMA, contract["schema"])
        self.assertEqual(V15_T3_VERSION, contract["version"])
        self.assertEqual(
            ["project", "properties", "workbench", "view"],
            [item["key"] for item in contract["docks"]],
        )
        self.assertTrue(contract["capabilities"]["v14_functionality_preserved"])

    def test_selection_sets_orbit_pivot_without_moving_camera(self) -> None:
        node_id = "node:item:000017"
        before = self.controller.get_camera()
        bounds = self.controller.index.bounds_for((node_id,), include_descendants=True)
        self.assertIsNotNone(bounds)
        assert bounds is not None
        self.controller.set_selection((node_id,))
        self.assertEqual(before, self.controller.get_camera())
        self.assertEqual(bounds.center, self.controller.orbit_pivot)

    def test_multi_selection_uses_combined_bounds_center_and_clear_retains_focus(self) -> None:
        nodes = ("node:item:000010", "node:item:000021")
        bounds = self.controller.index.bounds_for(nodes, include_descendants=True)
        self.assertIsNotNone(bounds)
        assert bounds is not None
        self.controller.set_selection(nodes)
        pivot = self.controller.orbit_pivot
        self.assertEqual(bounds.center, pivot)
        self.controller.set_selection(())
        self.assertEqual(pivot, self.controller.orbit_pivot)

    def test_temporary_assembly_pick_preserves_persistent_part_mode_and_focus(self) -> None:
        self.backend.pick_node_id = "node:item:000005"
        self.controller.set_selection_level(SelectionLevel.PART)
        pick = self.controller.pick_at_level(
            10, 20, level=SelectionLevel.ASSEMBLY, mode="replace"
        )
        self.assertIsNotNone(pick)
        assert pick is not None
        self.assertEqual("node:assembly:0000", pick.node_id)
        self.assertEqual(SelectionLevel.PART, self.controller.session.selection_level)
        self.assertEqual(("node:assembly:0000",), self.controller.get_selection())
        bounds = self.controller.index.bounds_for(
            ("node:assembly:0000",), include_descendants=True
        )
        self.assertIsNotNone(bounds)
        assert bounds is not None
        self.assertEqual(bounds.center, self.controller.orbit_pivot)

    def test_temporary_part_pick_preserves_persistent_assembly_mode(self) -> None:
        self.backend.pick_node_id = "node:item:000015"
        self.controller.set_selection_level(SelectionLevel.ASSEMBLY)
        pick = self.controller.pick_at_level(
            10, 20, level=SelectionLevel.PART, mode="replace"
        )
        self.assertIsNotNone(pick)
        assert pick is not None
        self.assertEqual("node:item:000015", pick.node_id)
        self.assertEqual(SelectionLevel.ASSEMBLY, self.controller.session.selection_level)
        self.assertEqual(("node:item:000015",), self.controller.get_selection())

    def test_explicit_picked_pivot_does_not_reframe_until_orbit(self) -> None:
        before = self.controller.get_camera()
        picked = Vector3(417.25, -138.5, 92.0)
        self.service.set_orbit_pivot(picked)
        self.assertEqual(before, self.controller.get_camera())
        self.assertEqual(picked, self.controller.orbit_pivot)

    def test_orbit_rigidly_rotates_camera_around_selected_part(self) -> None:
        node_id = "node:item:000019"
        self.controller.set_selection((node_id,))
        pivot = self.controller.orbit_pivot
        before = self.controller.get_camera()
        eye_radius = (before.position - pivot).length()
        target_radius = (before.target - pivot).length()
        self.controller.orbit(31.0, -9.0)
        after = self.controller.get_camera()
        self.assertEqual(pivot, self.controller.orbit_pivot)
        self.assertAlmostEqual(eye_radius, (after.position - pivot).length(), places=7)
        self.assertAlmostEqual(target_radius, (after.target - pivot).length(), places=7)
        self.assertNotEqual(before.position, after.position)
        if target_radius > 1e-9:
            self.assertNotEqual(before.target, after.target)

    def test_fit_selection_centers_camera_and_keeps_same_selection_pivot(self) -> None:
        node_id = "node:item:000013"
        self.controller.set_selection((node_id,))
        expected = self.controller.orbit_pivot
        self.controller.fit_selection()
        camera = self.controller.get_camera()
        self.assertEqual(expected, camera.target)
        self.assertEqual(expected, self.controller.orbit_pivot)

    def test_camera_history_is_gesture_checkpointed_and_reversible(self) -> None:
        before = self.controller.get_camera()
        self.service.camera_checkpoint()
        self.controller.orbit(24.0, -8.0)
        after = self.controller.get_camera()
        self.assertNotEqual(before, after)
        self.assertTrue(self.service.camera_back())
        self.assertEqual(before, self.controller.get_camera())
        self.assertTrue(self.service.camera_forward())
        self.assertEqual(after, self.controller.get_camera())

    def test_standard_view_projection_and_position_are_deterministic(self) -> None:
        self.service.set_standard_view(StandardView.TOP)
        top = self.controller.get_camera()
        self.assertGreater((top.position - top.target).z, 0.0)
        self.service.set_projection(ProjectionType.ORTHOGRAPHIC)
        self.assertEqual(ProjectionType.ORTHOGRAPHIC, self.controller.get_camera().projection)
        positioned = self.service.set_camera_position(
            Vector3(1200.0, -800.0, 600.0), target=Vector3(10.0, 20.0, 30.0)
        )
        self.assertEqual(Vector3(1200.0, -800.0, 600.0), positioned.position)
        self.assertEqual(Vector3(10.0, 20.0, 30.0), positioned.target)

    def test_view_from_face_normal_keeps_valid_up_vector(self) -> None:
        camera = self.service.view_from_normal(Vector3(0.0, 0.0, 1.0), fit=False)
        direction = (camera.position - camera.target).normalized()
        self.assertAlmostEqual(1.0, direction.z, places=9)
        self.assertAlmostEqual(0.0, camera.up.dot(direction), places=9)

    def test_view_from_face_normal_without_target_uses_selected_orbit_focus(self) -> None:
        node_id = "node:item:000014"
        self.controller.set_selection((node_id,))
        expected = self.controller.orbit_pivot
        camera = self.service.view_from_normal(Vector3(0.0, 1.0, 0.0))
        self.assertEqual(expected, camera.target)
        self.assertEqual(expected, self.controller.orbit_pivot)
        direction = (camera.position - camera.target).normalized()
        self.assertAlmostEqual(1.0, direction.y, places=9)

    def test_view_from_face_normal_can_target_exact_picked_surface_point(self) -> None:
        picked = Vector3(125.0, 250.0, 375.0)
        camera = self.service.view_from_normal(
            Vector3(1.0, 0.0, 0.0), target=picked, fit=False
        )
        self.assertEqual(picked, camera.target)
        self.assertEqual(picked, self.controller.orbit_pivot)
        direction = (camera.position - camera.target).normalized()
        self.assertAlmostEqual(1.0, direction.x, places=9)

    def test_zoom_area_fits_bounds_without_changing_selection(self) -> None:
        self.controller.set_selection(("node:item:000001",))
        selected_before = self.controller.get_selection()
        nodes = self.service.zoom_area_screen_rect(10, 10, 800, 600)
        self.assertEqual(("node:item:000010", "node:item:000011"), nodes)
        self.assertEqual(selected_before, self.controller.get_selection())
        bounds = self.controller.index.bounds_for(nodes, include_descendants=True)
        self.assertIsNotNone(bounds)
        assert bounds is not None
        target = self.controller.get_camera().target
        self.assertAlmostEqual(bounds.center.x, target.x, places=6)
        self.assertAlmostEqual(bounds.center.y, target.y, places=6)
        self.assertAlmostEqual(bounds.center.z, target.z, places=6)
        self.assertEqual(target, self.controller.orbit_pivot)

    def test_workspace_restore_rebinds_orbit_focus_to_restored_selection(self) -> None:
        restored_node = "node:item:000006"
        other_node = "node:item:000026"
        self.controller.set_selection((restored_node,))
        expected = self.controller.orbit_pivot
        state = self.controller.export_workspace_state()
        self.controller.set_selection((other_node,))
        self.controller.set_orbit_pivot(Vector3(9000.0, -8000.0, 7000.0))
        self.controller.restore_workspace_state(state)
        self.assertEqual((restored_node,), self.controller.get_selection())
        self.assertEqual(expected, self.controller.orbit_pivot)

    def test_section_and_clipping_state_roundtrip_through_workspace_contract(self) -> None:
        plane_id = self.service.add_section(Vector3(0.0, 0.0, 1.0))
        self.service.set_section_enabled(plane_id, False)
        self.service.flip_section(plane_id)
        box = self.service.set_clip_box_fraction(0.8)
        state = self.controller.export_workspace_state()
        self.assertEqual(1, len(state.section_planes))
        self.assertFalse(state.section_planes[0].enabled)
        self.assertTrue(state.section_planes[0].flipped)
        self.assertIsNotNone(state.clipping_box)
        self.assertEqual(box, state.clipping_box)
        self.service.set_section_enabled(plane_id, True)
        self.service.clear_clip_box()
        self.controller.restore_workspace_state(state)
        restored = self.controller.session.section_planes[plane_id]
        self.assertFalse(restored.enabled)
        self.assertTrue(restored.flipped)
        self.assertEqual(box, self.controller.session.clipping_box)

    def test_saved_view_activation_rebinds_orbit_focus_to_saved_selection(self) -> None:
        saved_node = "node:item:000009"
        other_node = "node:item:000029"
        self.controller.set_selection((saved_node,))
        expected = self.controller.orbit_pivot
        viewpoint = self.service.save_named_view("Selectie-focus")
        self.controller.set_selection((other_node,))
        self.controller.set_orbit_pivot(Vector3(-1000.0, 2000.0, 3000.0))
        self.controller.activate_viewpoint(viewpoint)
        self.assertEqual((saved_node,), self.controller.get_selection())
        self.assertEqual(expected, self.controller.orbit_pivot)

    def test_saved_view_captures_camera_sections_and_clipping(self) -> None:
        self.service.set_standard_view(StandardView.RIGHT)
        self.service.add_section(Vector3(1.0, 0.0, 0.0))
        self.service.set_clip_box_fraction(0.8)
        viewpoint = self.service.save_named_view("T3 rechteraanzicht")
        self.assertEqual(self.controller.get_camera(), viewpoint.camera)
        self.assertEqual(1, len(viewpoint.section_planes))
        self.assertIsNotNone(viewpoint.clipping_box)
        self.assertEqual(viewpoint.viewpoint_id, self.controller.list_viewpoints()[0].viewpoint_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
