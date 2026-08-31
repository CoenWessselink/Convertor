from __future__ import annotations

import math
import unittest

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.core.viewer_feel_navigation import WHEEL_ZOOM_PER_NOTCH
from cws_viewer.core.viewer_feel_navigation_v2 import (
    ViewerFeelNavigationV2Service,
    WORLD_UP,
)
from cws_viewer.core.viewer_interaction_profile import (
    TRIMBLE_STYLE_INTERACTION_PROFILE,
)
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Vector3


class TrimbleObservableParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MemoryRenderBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1600, height=900)
        self.controller.load_scene(build_synthetic_product_scene(60, parts_per_assembly=10))
        self.navigation = ViewerFeelNavigationV2Service(self.controller)

    def tearDown(self) -> None:
        self.controller.shutdown()

    def test_interaction_profile_is_valid_and_is_the_zoom_source_of_truth(self) -> None:
        profile = TRIMBLE_STYLE_INTERACTION_PROFILE
        profile.validate()
        self.assertEqual(profile.wheel_zoom_factor_per_notch, WHEEL_ZOOM_PER_NOTCH)
        self.assertEqual("replace", profile.selection_mode(control=False, shift=False))
        self.assertEqual("toggle", profile.selection_mode(control=True, shift=False))
        self.assertEqual("add", profile.selection_mode(control=False, shift=True))
        self.assertEqual("toggle", profile.selection_mode(control=True, shift=True))

    def test_upright_orbit_golden_preserves_pivot_radius_and_zero_roll(self) -> None:
        pivot = Vector3(1250.0, -440.0, 275.0)
        self.controller.set_orbit_pivot(pivot)
        before = self.controller.get_camera()
        eye_radius = (before.position - pivot).length()
        target_radius = (before.target - pivot).length()
        after = self.navigation.orbit_upright(37.5, 14.25)
        view = (after.target - after.position).normalized()
        expected_up = view.cross(WORLD_UP).normalized().cross(view).normalized()
        self.assertAlmostEqual(eye_radius, (after.position - pivot).length(), places=7)
        self.assertAlmostEqual(target_radius, (after.target - pivot).length(), places=7)
        self.assertAlmostEqual(1.0, after.up.dot(expected_up), places=7)
        self.assertAlmostEqual(0.0, after.up.dot(view), places=7)

    def test_repeated_orbit_golden_never_crosses_pole_or_accumulates_roll(self) -> None:
        self.controller.set_orbit_pivot(self.controller.get_camera().target)
        for _ in range(40):
            camera = self.navigation.orbit_upright(11.0, 7.0)
            view = (camera.target - camera.position).normalized()
            elevation = math.degrees(math.asin(max(-1.0, min(1.0, view.dot(WORLD_UP)))))
            self.assertLessEqual(abs(elevation), TRIMBLE_STYLE_INTERACTION_PROFILE.maximum_elevation_deg + 1e-7)
            self.assertAlmostEqual(0.0, camera.up.dot(view), places=7)

    def test_zoom_golden_is_cursor_anchored_and_preserves_semantic_pivot(self) -> None:
        semantic_pivot = Vector3(500.0, 250.0, 125.0)
        cursor_anchor = Vector3(-125.0, 375.0, 80.0)
        self.controller.set_orbit_pivot(semantic_pivot)
        before = self.controller.get_camera()
        before_radius = (before.position - cursor_anchor).length()
        after = self.navigation.zoom_about_point(WHEEL_ZOOM_PER_NOTCH, cursor_anchor)
        after_radius = (after.position - cursor_anchor).length()
        self.assertAlmostEqual(before_radius / WHEEL_ZOOM_PER_NOTCH, after_radius, places=7)
        self.assertEqual(semantic_pivot, self.controller.orbit_pivot)

    def test_contract_exposes_complete_observable_input_matrix(self) -> None:
        contract = TRIMBLE_STYLE_INTERACTION_PROFILE.contract()
        expected = {
            "left_click",
            "control_left_click",
            "shift_left_click",
            "left_drag_orbit_mode",
            "left_drag_pan_mode",
            "middle_drag",
            "wheel",
            "empty_space_orbit",
        }
        self.assertEqual(expected, set(contract["input_matrix"]))
        self.assertEqual("CWS Viewer Observable Trimble-Style Parity", contract["target"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
