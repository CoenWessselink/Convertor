from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Vector3


class ViewerV15InteractionFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MemoryRenderBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1200, height=800)
        self.controller.load_scene(build_synthetic_product_scene(30, parts_per_assembly=10))

    def tearDown(self) -> None:
        self.controller.shutdown()

    def test_assembly_selection_highlights_all_renderable_descendants(self) -> None:
        assembly = "node:assembly:0000"
        expected = self.controller.index.descendants(
            (assembly,), include_self=True, renderable_only=True
        )
        self.assertGreater(len(expected), 1)

        self.controller.set_selection((assembly,))
        state = self.controller.session.render_state(self.controller.index)

        self.assertEqual((assembly,), self.controller.get_selection())
        self.assertEqual(expected, state.selected_node_ids)
        bounds = self.controller.display_bounds_for((assembly,), include_descendants=True)
        self.assertIsNotNone(bounds)
        assert bounds is not None
        self.assertEqual(bounds.center, self.controller.orbit_pivot)

    def test_temporary_assembly_pick_highlights_assembly_not_only_hit_part(self) -> None:
        hit = "node:item:000005"
        self.backend.pick_node_id = hit
        self.controller.set_selection_level(SelectionLevel.PART)

        pick = self.controller.pick_at_level(
            320, 240, level=SelectionLevel.ASSEMBLY, mode="replace"
        )

        self.assertIsNotNone(pick)
        assert pick is not None
        self.assertEqual("node:assembly:0000", pick.node_id)
        self.assertEqual(SelectionLevel.PART, self.controller.session.selection_level)
        state = self.controller.session.render_state(self.controller.index)
        expected = self.controller.index.descendants(
            (pick.node_id,), include_self=True, renderable_only=True
        )
        self.assertEqual(expected, state.selected_node_ids)
        self.assertIn(hit, state.selected_node_ids)

    def test_ghost_context_geometry_cannot_steal_selection(self) -> None:
        focus = "node:item:000003"
        ghost = "node:item:000025"
        self.controller.isolate((focus,), ghost_context=True)
        visible, ghosted = self.controller.session.visible_and_ghosted(self.controller.index)
        self.assertIn(focus, visible)
        self.assertIn(ghost, visible)
        self.assertIn(ghost, ghosted)
        self.assertNotIn(focus, ghosted)

        self.backend.pick_node_id = ghost
        pick = self.controller.pick_at(100, 100)
        self.assertIsNone(pick)
        self.assertEqual((), self.controller.get_selection())

        self.backend.pick_node_id = focus
        pick = self.controller.pick_at(100, 100)
        self.assertIsNotNone(pick)
        self.assertEqual((focus,), self.controller.get_selection())

    def test_hidden_geometry_cannot_be_selected_even_if_renderer_returns_hit(self) -> None:
        hidden = "node:item:000006"
        self.controller.hide((hidden,))
        self.backend.pick_node_id = hidden

        pick = self.controller.pick_at(50, 50)

        self.assertIsNone(pick)
        self.assertEqual((), self.controller.get_selection())

    def test_real_explode_operation_moves_selected_orbit_focus_to_display_position(self) -> None:
        node_id = "node:item:000012"
        canonical = self.controller.index.world_bounds_by_node[node_id]
        self.controller.set_selection((node_id,))
        self.assertEqual(canonical.center, self.controller.orbit_pivot)

        affected = self.controller.explode((node_id,), distance_mm=500.0)

        self.assertEqual((node_id,), affected)
        expected = canonical.center + Vector3(500.0, 0.0, 0.0)
        self.assertEqual(expected, self.controller.orbit_pivot)
        self.controller.fit_selection()
        self.assertEqual(expected, self.controller.get_camera().target)

        reset = self.controller.reset_explode((node_id,))
        self.assertEqual((node_id,), reset)
        self.assertEqual(canonical.center, self.controller.orbit_pivot)

    def test_fit_all_uses_current_isolated_display_scope(self) -> None:
        node_id = "node:item:000021"
        self.controller.isolate((node_id,), ghost_context=False)
        expected = self.controller.display_bounds_for(
            (node_id,), include_descendants=True
        )
        self.assertIsNotNone(expected)
        assert expected is not None

        self.controller.fit_all()

        self.assertEqual(expected.center, self.controller.get_camera().target)
        self.assertEqual(expected.center, self.controller.orbit_pivot)

    def test_group_selection_is_semantic_but_render_selection_is_geometry_only(self) -> None:
        assembly = "node:assembly:0001"
        self.controller.set_selection((assembly,))
        render_state = self.controller.session.render_state(self.controller.index)
        self.assertEqual((assembly,), self.controller.get_selection())
        self.assertNotIn(assembly, render_state.selected_node_ids)
        self.assertTrue(render_state.selected_node_ids)
        for node_id in render_state.selected_node_ids:
            self.assertIn(node_id, self.controller.index.renderable_node_ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
