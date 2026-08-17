from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.contracts.enums import ProjectionType
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.core.v15_navigation import V15ViewNavigationService, navigation_contract
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Vector3


class ViewerV15SelectionPivotParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MemoryRenderBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1200, height=800)
        self.controller.load_scene(build_synthetic_product_scene(30, parts_per_assembly=10))
        self.navigation = V15ViewNavigationService(self.controller)

    def tearDown(self) -> None:
        self.controller.shutdown()

    def test_contract_exposes_selection_precedence_and_active_pivot_zoom(self) -> None:
        capabilities = navigation_contract()["capabilities"]
        self.assertTrue(capabilities["selection_orbit_focus"])
        self.assertTrue(capabilities["selection_pivot_precedence"])
        self.assertTrue(capabilities["orbit_around_picked_point"])
        self.assertTrue(capabilities["active_pivot_zoom"])
        self.assertTrue(capabilities["picked_depth_pan"])

    def test_selected_part_center_wins_over_new_surface_hit_at_orbit_start(self) -> None:
        node_id = "node:item:000017"
        self.controller.set_selection((node_id,))
        expected = self.controller.orbit_pivot
        before = self.controller.get_camera()
        picked_elsewhere = expected + Vector3(3750.0, -2280.0, 940.0)

        resolved = self.navigation.begin_orbit(picked_elsewhere)

        self.assertEqual(expected, resolved)
        self.assertEqual(expected, self.controller.orbit_pivot)
        self.assertEqual(before, self.controller.get_camera())

    def test_selected_assembly_center_wins_over_new_surface_hit(self) -> None:
        assembly_id = "node:assembly:0001"
        self.controller.set_selection((assembly_id,))
        bounds = self.controller.display_bounds_for((assembly_id,), include_descendants=True)
        self.assertIsNotNone(bounds)
        assert bounds is not None
        picked_elsewhere = bounds.center + Vector3(-4200.0, 1750.0, 300.0)

        resolved = self.navigation.begin_orbit(picked_elsewhere)

        self.assertEqual(bounds.center, resolved)
        self.assertEqual(bounds.center, self.controller.orbit_pivot)

    def test_unselected_model_uses_exact_point_picked_on_orbit_mouse_down(self) -> None:
        self.controller.set_selection((), mode="replace")
        picked = Vector3(417.25, -138.5, 92.0)

        resolved = self.navigation.begin_orbit(picked)

        self.assertEqual(picked, resolved)
        self.assertEqual(picked, self.controller.orbit_pivot)

    def test_perspective_zoom_keeps_selected_part_as_visual_anchor(self) -> None:
        node_id = "node:item:000019"
        self.controller.set_selection((node_id,))
        pivot = self.controller.orbit_pivot
        before = self.controller.get_camera()
        before_eye = before.position - pivot
        before_target = before.target - pivot
        factor = 1.5

        after = self.navigation.zoom_about_active_pivot(factor)

        self.assertEqual(pivot, self.controller.orbit_pivot)
        self.assertAlmostEqual(before_eye.x / factor, (after.position - pivot).x, places=7)
        self.assertAlmostEqual(before_eye.y / factor, (after.position - pivot).y, places=7)
        self.assertAlmostEqual(before_eye.z / factor, (after.position - pivot).z, places=7)
        self.assertAlmostEqual(before_target.x / factor, (after.target - pivot).x, places=7)
        self.assertAlmostEqual(before_target.y / factor, (after.target - pivot).y, places=7)
        self.assertAlmostEqual(before_target.z / factor, (after.target - pivot).z, places=7)

    def test_orthographic_zoom_keeps_selected_part_as_visual_anchor(self) -> None:
        self.controller.set_projection(ProjectionType.ORTHOGRAPHIC)
        node_id = "node:item:000011"
        self.controller.set_selection((node_id,))
        pivot = self.controller.orbit_pivot
        before = self.controller.get_camera()
        before_target = before.target - pivot
        before_eye_from_target = before.position - before.target
        factor = 2.0

        after = self.navigation.zoom_about_active_pivot(factor)
        after_eye_from_target = after.position - after.target

        self.assertEqual(pivot, self.controller.orbit_pivot)
        self.assertAlmostEqual(before.ortho_scale / factor, after.ortho_scale, places=9)
        self.assertAlmostEqual(before_eye_from_target.x, after_eye_from_target.x, places=9)
        self.assertAlmostEqual(before_eye_from_target.y, after_eye_from_target.y, places=9)
        self.assertAlmostEqual(before_eye_from_target.z, after_eye_from_target.z, places=9)
        self.assertAlmostEqual(before_target.x / factor, (after.target - pivot).x, places=9)
        self.assertAlmostEqual(before_target.y / factor, (after.target - pivot).y, places=9)
        self.assertAlmostEqual(before_target.z / factor, (after.target - pivot).z, places=9)

    def test_runtime_widget_is_wired_to_selection_precedence_not_raw_hit_override(self) -> None:
        source = (ROOT / "cws_viewer" / "ui_qt" / "vtk_real_project_widget_v15.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("self._v15_view_navigation.begin_orbit(point)", source)
        self.assertNotIn("set_orbit_pivot(probe.world_point)", source)
        self.assertIn("zoom_about_active_pivot", source)

    def test_measurement_tool_pick_does_not_route_through_normal_selection_pick(self) -> None:
        source = (ROOT / "cws_viewer" / "ui_qt" / "vtk_real_project_widget_v15.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('getattr(self.controller, "_active_measurement_kind", None)', source)
        self.assertIn("pick = self._probe_screen(pos)", source)
        self.assertIn("probe.node_id in set(ghosted)", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
