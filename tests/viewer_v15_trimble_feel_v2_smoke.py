from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.importers.p21 import P21Document, P21Entity
from cws_viewer.adapters.source_appearance import IfcAppearanceResolver
from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.core.viewer_feel_navigation_v2 import ViewerFeelNavigationV2Service, WORLD_UP
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.ui_qt.trimble_feel_v2_contract import PREVIEW2_VERSION, preview2_workspace_contract


class ViewerV15TrimbleFeelV2Smoke(unittest.TestCase):
    def test_preview2_contract_contains_requested_local_viewer_features(self) -> None:
        contract = preview2_workspace_contract()
        caps = contract["capabilities"]
        self.assertEqual(PREVIEW2_VERSION, contract["version"])
        self.assertEqual(10, len(contract["docks"]))
        for name in (
            "world_up_horizontal_orbit",
            "orbit_roll_suppressed",
            "ifc_source_presentation_colours",
            "original_colour_means_imported_colour",
            "ssao_contact_shading_interactive",
            "balanced_studio_lighting",
            "selected_object_fill_highlight",
            "ctrl_click_multi_selection",
            "grid_list_to_3d_selection",
            "3d_to_grid_list_selection",
            "assembly_part_level_toolbar",
            "assembly_selection_expands_in_grid",
            "persistent_bottom_views_strip",
            "views_strip_search",
            "views_strip_groups",
            "views_strip_slideshow",
            "measurement_foreground_labels",
            "measurement_from_to_markers",
            "measurement_live_hover_preview",
            "measurement_overlay_camera_tracking",
        ):
            self.assertTrue(caps[name], name)

    def test_ifc_style_resolver_recovers_mapped_source_colour_and_transparency(self) -> None:
        entities = {
            1: P21Entity(1, "IFCCOLOURRGB", "'Tekla blue',0.12,0.56,0.81"),
            2: P21Entity(2, "IFCSURFACESTYLERENDERING", "#1,0.20,$,$,$,$,$,$,.NOTDEFINED."),
            3: P21Entity(3, "IFCSURFACESTYLE", "'Original',.BOTH.,(#2)"),
            4: P21Entity(4, "IFCSTYLEDITEM", "#101,(#3),$"),
            100: P21Entity(100, "IFCMAPPEDITEM", "#101,#102"),
            101: P21Entity(101, "IFCFACETEDBREP", "(#103)"),
            102: P21Entity(102, "IFCCARTESIANTRANSFORMATIONOPERATOR3D", "$,$,$,$,$"),
            103: P21Entity(103, "IFCCLOSEDSHELL", "()"),
        }
        by_type: dict[str, tuple[int, ...]] = {}
        for value in entities.values():
            by_type.setdefault(value.type_name, tuple())
            by_type[value.type_name] = (*by_type[value.type_name], value.entity_id)
        document = P21Document(
            path=Path("synthetic.ifc"),
            entities=entities,
            by_type=by_type,
            schema="IFC2X3",
        )
        appearance = IfcAppearanceResolver(document).color_for_items(("100",))
        self.assertIsNotNone(appearance)
        assert appearance is not None
        self.assertAlmostEqual(0.12, appearance.color.red, places=6)
        self.assertAlmostEqual(0.56, appearance.color.green, places=6)
        self.assertAlmostEqual(0.81, appearance.color.blue, places=6)
        self.assertAlmostEqual(0.80, appearance.color.alpha, places=6)
        self.assertIn("ifc:", appearance.provenance)

    def test_horizontal_orbit_remains_world_up_without_accumulating_roll(self) -> None:
        backend = MemoryRenderBackend()
        controller = V14ViewerCoreController(backend, width=1440, height=900)
        controller.load_scene(build_synthetic_product_scene(40, parts_per_assembly=10))
        try:
            controller.set_selection(("node:item:000018",))
            navigation = ViewerFeelNavigationV2Service(controller)
            navigation.orbit_upright(0.0, 31.0)
            for _ in range(8):
                navigation.orbit_upright(17.0, 0.0)
            camera = controller.get_camera()
            view = (camera.target - camera.position).normalized()
            expected_right = view.cross(WORLD_UP).normalized()
            expected_up = expected_right.cross(view).normalized()
            self.assertLess((camera.up - expected_up).length(), 1e-8)
            self.assertGreater(camera.up.dot(WORLD_UP), 0.0)
            self.assertEqual(
                controller.orbit_pivot,
                controller.display_bounds_for(
                    ("node:item:000018",), include_descendants=True
                ).center,
            )
        finally:
            controller.shutdown()

    def test_v2_runtime_sources_lock_multiselect_views_measurement_and_grid_sync(self) -> None:
        widget = (ROOT / "cws_viewer/ui_qt/vtk_real_project_widget_feel_v2.py").read_text(encoding="utf-8")
        renderer = (ROOT / "cws_viewer/backends/vtk_project_mesh_feel_v2.py").read_text(encoding="utf-8")
        cockpit = (ROOT / "cws_viewer/ui_qt/cockpit_trimble_feel_v2.py").read_text(encoding="utf-8")
        views = (ROOT / "cws_viewer/ui_qt/views_strip_feel_v2.py").read_text(encoding="utf-8")
        adapter = (ROOT / "cws_viewer/adapters/source_style_scene.py").read_text(encoding="utf-8")
        interaction = (ROOT / "cws_viewer/core/project_interaction.py").read_text(encoding="utf-8")

        self.assertIn('return "toggle"', widget)
        self.assertIn("ControlModifier", widget)
        self.assertIn("orbit_upright", widget)
        self.assertIn("set_measurement_preview", widget)
        self.assertIn("vtkSSAOPass", renderer)
        self.assertIn("vtkTextActor", renderer)
        self.assertIn('"A"', renderer)
        self.assertIn('"B"', renderer)
        self.assertIn("_sync_selection_fill", renderer)
        self.assertIn("Merk / assembly", cockpit)
        self.assertIn("_grid_entities_for_selection", cockpit)
        self.assertIn("grid.select_entities(self._grid_entities_for_selection(selection))", cockpit)
        self.assertIn("selectable_node_for_level(node_id, level)", interaction)
        self.assertIn("CwsViewsStripV2", cockpit)
        self.assertIn("Nieuwe View", views)
        self.assertIn("View Group", views)
        self.assertIn("style-source-ifc-", adapter)


if __name__ == "__main__":
    unittest.main(verbosity=2)
