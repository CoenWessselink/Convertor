from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.core.viewer_feel_navigation import (
    ViewerFeelNavigationService,
    WHEEL_ZOOM_PER_NOTCH,
    viewer_feel_navigation_contract,
)
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Vector3
from cws_viewer.ui_qt.cockpit_feel_fix_v15 import viewer_feel_workspace_contract
from cws_viewer.core.viewer_interaction_profile import TRIMBLE_STYLE_INTERACTION_PROFILE


class ViewerFeelFixSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scene = build_synthetic_product_scene(8, parts_per_assembly=4)
        self.backend = MemoryRenderBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1200, height=800)
        self.controller.load_scene(self.scene)
        self.navigation = ViewerFeelNavigationService(self.controller)

    def tearDown(self) -> None:
        self.controller.shutdown()

    def test_contract_exposes_requested_handling_and_rendering_repairs(self) -> None:
        contract = viewer_feel_workspace_contract()
        caps = contract["capabilities"]
        for name in (
            "zoom_to_cursor_surface_point",
            "zoom_to_cursor_reference_depth_fallback",
            "wheel_notch_incremental_zoom",
            "zoom_does_not_replace_semantic_orbit_pivot",
            "coalesced_navigation_input",
            "selection_cursor_arrow",
            "pan_cursor_hand",
            "tessellation_edges_suppressed",
            "hard_edge_normals",
            "selection_feature_edge_outline",
            "interactive_fxaa",
            "interactive_msaa_8x",
            "phase2_review_preserved",
            "phase1_fast_start_preserved",
        ):
            self.assertTrue(caps[name], name)
        self.assertAlmostEqual(1.08, WHEEL_ZOOM_PER_NOTCH)

    def test_cursor_zoom_scales_camera_about_cursor_without_stealing_orbit_pivot(self) -> None:
        selected = self.controller.index.renderable_node_ids[0]
        self.controller.set_selection((selected,), mode="replace")
        semantic_pivot = self.controller.orbit_pivot
        cursor_point = semantic_pivot + Vector3(250.0, 125.0, -50.0)
        before = self.controller.get_camera()
        factor = WHEEL_ZOOM_PER_NOTCH
        after = self.navigation.zoom_about_point(factor, cursor_point)
        expected_scale = 1.0 / factor
        self.assertAlmostEqual(
            (before.position - cursor_point).length() * expected_scale,
            (after.position - cursor_point).length(),
            places=6,
        )
        self.assertTrue(self.controller.orbit_pivot.almost_equal(semantic_pivot, tolerance=1e-9))

    def test_source_contains_no_triangle_edge_path_for_normal_shaded_display(self) -> None:
        backend_source = (ROOT / "cws_viewer" / "backends" / "vtk_project_mesh_feel.py").read_text(encoding="utf-8")
        widget_source = (ROOT / "cws_viewer" / "ui_qt" / "vtk_real_project_widget_feel.py").read_text(encoding="utf-8")
        self.assertIn("prop.EdgeVisibilityOff()", backend_source)
        self.assertIn("vtkFeatureEdges", backend_source)
        # The production renderer deliberately uses exact cell normals.  This
        # keeps 90-degree profile edges hard without duplicating/splitting the
        # complete IFC tessellation during first-frame loading.
        self.assertIn("normals.SplittingOff()", backend_source)
        self.assertIn("normals.ComputePointNormalsOff()", backend_source)
        self.assertIn("normals.ComputeCellNormalsOn()", backend_source)
        self.assertIn("UseFXAAOn", backend_source)
        self.assertIn("SetMultiSamples(4 if self._offscreen else 8)", backend_source)
        self.assertIn("ArrowCursor", widget_source)
        self.assertIn("OpenHandCursor", widget_source)
        self.assertIn("WHEEL_ZOOM_PER_NOTCH", widget_source)
        self.assertIn("world_point_at_display_depth", widget_source)
        self.assertIn("NAVIGATION_FRAME_MS = TRIMBLE_STYLE_INTERACTION_PROFILE.navigation_frame_ms", widget_source)
        self.assertLessEqual(TRIMBLE_STYLE_INTERACTION_PROFILE.navigation_frame_ms, 16)

    def test_phase2_contract_is_preserved(self) -> None:
        caps = viewer_feel_workspace_contract()["capabilities"]
        for name in (
            "interactive_markup_line",
            "saved_view_review_snapshot",
            "view_groups",
            "picked_surface_section_plane",
            "reset_model_display_state",
            "selection_pivot_precedence",
        ):
            self.assertTrue(caps[name], name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
