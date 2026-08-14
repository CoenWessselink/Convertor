from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.contracts.enums import ProjectionType, SelectionLevel, StandardView
from cws_viewer.contracts.events import SelectionChanged, VisibilityChanged
from cws_viewer.contracts.state import ColorAssignment, ScenePatch, ScreenshotOptions
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Rgba


class ViewerV2CoreControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MemoryRenderBackend()
        self.controller = ViewerCoreController(self.backend, width=800, height=600)
        self.scene = build_synthetic_product_scene(250, parts_per_assembly=100)
        self.controller.load_scene(self.scene)

    def tearDown(self) -> None:
        self.controller.shutdown()

    def test_selection_visibility_isolation_and_style(self) -> None:
        selection_events: list[SelectionChanged] = []
        visibility_events: list[VisibilityChanged] = []
        self.controller.subscribe(SelectionChanged, selection_events.append)
        self.controller.subscribe(VisibilityChanged, visibility_events.append)

        self.controller.set_selection(("node:item:000001",))
        self.controller.set_selection(("node:item:000002",), mode="add")
        self.assertEqual(
            ("node:item:000001", "node:item:000002"),
            self.controller.get_selection(),
        )
        self.assertTrue(selection_events)

        self.controller.hide(("node:assembly:0000",))
        assert self.backend.state is not None
        self.assertEqual(150, len(self.backend.state.visible_node_ids))
        self.controller.show(("node:assembly:0000",))
        self.assertEqual(250, len(self.backend.state.visible_node_ids))

        self.controller.isolate(("node:assembly:0001",), ghost_context=False)
        self.assertEqual(100, len(self.backend.state.visible_node_ids))
        self.controller.isolate(("node:assembly:0001",), ghost_context=True)
        self.assertEqual(250, len(self.backend.state.visible_node_ids))
        self.assertEqual(150, len(self.backend.state.ghosted_node_ids))
        self.assertTrue(visibility_events)

        self.controller.set_transparency(("node:assembly:0001",), 0.5)
        self.controller.colorize(
            (ColorAssignment("node:assembly:0001", Rgba(0.1, 0.8, 0.2, 1.0)),)
        )
        self.assertEqual(100, len(self.controller.session.transparency))
        self.assertEqual(100, len(self.controller.session.colors))
        self.controller.reset_styles(("node:assembly:0001",))
        self.assertFalse(self.controller.session.transparency)
        self.assertFalse(self.controller.session.colors)

    def test_camera_orbit_pan_zoom_fit_and_projection(self) -> None:
        before = self.controller.get_camera()
        self.controller.set_standard_view(StandardView.TOP)
        self.controller.set_projection(ProjectionType.ORTHOGRAPHIC)
        self.controller.zoom(2.0)
        self.controller.pan(0.05, -0.03)
        self.controller.orbit(15.0, 5.0)
        self.controller.fit_all()
        after = self.controller.get_camera()
        self.assertNotEqual(before, after)
        self.assertEqual(ProjectionType.ORTHOGRAPHIC, after.projection)
        self.assertGreater(after.ortho_scale, 0.0)

    def test_pick_respects_selection_level(self) -> None:
        self.backend.pick_node_id = "node:item:000123"
        self.controller.set_selection_level(SelectionLevel.ASSEMBLY)
        pick = self.controller.pick_at(10, 10)
        self.assertIsNotNone(pick)
        assert pick is not None
        self.assertEqual("node:assembly:0001", pick.node_id)
        self.assertEqual(("node:assembly:0001",), self.controller.get_selection())

    def test_stable_state_survives_same_project_reload(self) -> None:
        self.controller.set_selection(("node:item:000005", "node:item:000249"))
        self.controller.hide(("node:item:000006",))
        self.controller.isolate(("node:assembly:0000",), ghost_context=True)
        replacement = build_synthetic_product_scene(200, parts_per_assembly=100, revision_id="B")
        job = self.controller.update_scene(
            ScenePatch(
                expected_scene_hash=self.scene.scene_hash,
                replacement_scene=replacement,
                reason="V2 stable reload",
            )
        )
        self.assertEqual("succeeded", job.state.value)
        self.assertEqual(("node:item:000005",), self.controller.get_selection())
        self.assertIn("node:item:000006", self.controller.session.hidden)
        self.assertEqual(("node:assembly:0000",), self.controller.session.isolation)
        self.assertEqual(replacement.scene_hash, self.controller.session.scene_hash)

    def test_viewpoint_and_screenshot_contract(self) -> None:
        self.controller.set_selection(("node:item:000010",))
        self.controller.hide(("node:item:000011",))
        viewpoint = self.controller.save_viewpoint("Controlepunt")
        self.controller.show_all()
        self.controller.set_selection(())
        self.controller.activate_viewpoint(viewpoint)
        self.assertEqual(("node:item:000010",), self.controller.get_selection())
        self.assertIn("node:item:000011", self.controller.session.hidden)
        data = self.controller.screenshot(ScreenshotOptions(width=10, height=10))
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
