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
from cws_viewer.core.v15_navigation import V15ViewNavigationService
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Vector3


BASE_WIDGET = ROOT / "cws_viewer" / "ui_qt" / "vtk_real_project_widget.py"
V15_WIDGET = ROOT / "cws_viewer" / "ui_qt" / "vtk_real_project_widget_v15.py"
T3_COCKPIT = ROOT / "cws_viewer" / "ui_qt" / "cockpit_t3_v15.py"


class ViewerV15TrimbleInputContractTests(unittest.TestCase):
    """Lock visible desktop interaction semantics against accidental regressions.

    The contract reproduces documented user-facing workflows with CWS code and
    CWS branding.  The deliberate CWS extension is selected-object pivot
    precedence: a selected part/assembly remains the orbit anchor; without a
    selection, orbit falls back to the exact point picked on mouse-down.
    """

    def setUp(self) -> None:
        self.backend = MemoryRenderBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1280, height=800)
        self.controller.load_scene(build_synthetic_product_scene(40, parts_per_assembly=10))
        self.navigation = V15ViewNavigationService(self.controller)

    def tearDown(self) -> None:
        self.controller.shutdown()

    def test_selected_object_is_the_stable_orbit_anchor(self) -> None:
        selected = "node:item:000023"
        self.controller.set_selection((selected,))
        expected = self.controller.display_bounds_for((selected,), include_descendants=True)
        self.assertIsNotNone(expected)
        assert expected is not None

        raw_surface_point = expected.center + Vector3(1400.0, -300.0, 250.0)
        resolved = self.navigation.begin_orbit(raw_surface_point)
        self.assertEqual(expected.center, resolved)

        before = self.controller.get_camera()
        self.controller.orbit(17.0, -9.0)
        after = self.controller.get_camera()
        self.assertAlmostEqual((before.position - resolved).length(), (after.position - resolved).length(), places=8)
        self.assertEqual(resolved, self.controller.orbit_pivot)

    def test_no_selection_uses_exact_picked_point_for_orbit(self) -> None:
        self.controller.set_selection((), mode="replace")
        point = Vector3(125.5, 87.25, -32.0)
        self.assertEqual(point, self.navigation.begin_orbit(point))
        self.assertEqual(point, self.controller.orbit_pivot)

    def test_selection_hierarchy_mode_is_persistent_and_alt_pick_can_be_temporary(self) -> None:
        hit = "node:item:000005"
        self.backend.pick_node_id = hit
        self.controller.set_selection_level(SelectionLevel.PART)
        pick = self.controller.pick_at_level(100, 100, level=SelectionLevel.ASSEMBLY)
        self.assertIsNotNone(pick)
        assert pick is not None
        self.assertEqual(SelectionLevel.PART, self.controller.session.selection_level)
        self.assertEqual("node:assembly:0000", pick.node_id)

    def test_base_mouse_selection_modifiers_match_desktop_contract(self) -> None:
        source = BASE_WIDGET.read_text(encoding="utf-8")
        self.assertIn("ControlModifier", source)
        self.assertIn('return "add"', source)
        self.assertIn("ShiftModifier", source)
        self.assertIn('return "toggle"', source)
        self.assertIn("crossing = float(end.x()) < float(start.x())", source)
        self.assertIn("self._controller.select_rectangle", source)
        self.assertIn("self._controller.fit_selection()", source)
        self.assertIn("self.context_requested.emit", source)

    def test_v15_camera_shortcuts_and_surface_orthogonal_mode_are_wired(self) -> None:
        source = V15_WIDGET.read_text(encoding="utf-8")
        for key in ("Key_U", "Key_I", "Key_O", "Key_P"):
            self.assertIn(key, source)
        for mode in ("NavigationMode.ORBIT", "NavigationMode.PAN", "NavigationMode.WALK", "NavigationMode.LOOK"):
            self.assertIn(mode, source)
        self.assertIn("Key_F11", source)
        self.assertIn("mouseDoubleClickEvent", source)
        self.assertIn("AltModifier", source)
        self.assertIn("view_from_normal", source)
        self.assertIn("Key_Backspace", source)
        self.assertIn("ShiftModifier", source)

    def test_fit_details_undo_redo_and_escape_routes_exist(self) -> None:
        base_source = BASE_WIDGET.read_text(encoding="utf-8")
        v15_source = V15_WIDGET.read_text(encoding="utf-8")
        cockpit_source = T3_COCKPIT.read_text(encoding="utf-8")
        self.assertIn("Key_Space", base_source)
        self.assertIn("fit_selection", base_source)
        self.assertIn('QKeySequence("Return")', cockpit_source)
        self.assertIn('QKeySequence("Enter")', cockpit_source)
        self.assertIn('QKeySequence("Ctrl+Z")', cockpit_source)
        self.assertIn('QKeySequence("Ctrl+Y")', cockpit_source)
        self.assertIn("controller.undo()", cockpit_source)
        self.assertIn("controller.redo()", cockpit_source)
        self.assertIn("Key_Escape", v15_source)
        self.assertIn('set_selection((), mode="replace")', v15_source)

    def test_measurement_tool_uses_probe_without_replacing_semantic_selection(self) -> None:
        source = V15_WIDGET.read_text(encoding="utf-8")
        self.assertIn('getattr(self.controller, "_active_measurement_kind", None)', source)
        self.assertIn("pick = self._probe_screen(pos)", source)
        measurement_branch = source.split('if getattr(self.controller, "_active_measurement_kind", None) is not None:', 1)[1].split("temporary = None", 1)[0]
        self.assertNotIn("pick_at(", measurement_branch)
        self.assertNotIn("set_selection", measurement_branch)

    def test_hidden_and_ghost_context_cannot_take_over_pick_focus(self) -> None:
        focus = "node:item:000006"
        ghost = "node:item:000027"
        self.controller.isolate((focus,), ghost_context=True)
        self.backend.pick_node_id = ghost
        self.assertIsNone(self.controller.pick_at(50, 50))
        self.backend.pick_node_id = focus
        self.assertIsNotNone(self.controller.pick_at(50, 50))

    def test_zoom_about_selected_pivot_preserves_anchor(self) -> None:
        selected = "node:item:000018"
        self.controller.set_selection((selected,))
        pivot = self.controller.orbit_pivot
        before = self.controller.get_camera()
        after = self.navigation.zoom_about_active_pivot(1.35)
        self.assertEqual(pivot, self.controller.orbit_pivot)
        self.assertLess((after.position - pivot).length(), (before.position - pivot).length())


if __name__ == "__main__":
    unittest.main(verbosity=2)
