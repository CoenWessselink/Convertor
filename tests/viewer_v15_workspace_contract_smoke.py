from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.cache.mesh_cache import MeshCache
from cws_viewer.contracts.geometry import MeshData, TessellationSettings
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.ui_qt.cockpit_phase1_v15 import (
    PHASE1_BUILD,
    PHASE1_LAYOUT_VERSION,
    phase1_workspace_contract,
)
from cws_viewer.ui_qt.cockpit_phase2_v15 import (
    PHASE2_BUILD,
    phase2_workspace_contract,
)
from cws_viewer.ui_qt.cockpit_v15 import (
    V15_DOCK_SPECS,
    V15_VERSION,
    V15_WORKSPACE_SCHEMA,
    V15_WORKSPACE_STATE_VERSION,
    workspace_contract,
)


class ViewerV15WorkspaceContractTests(unittest.TestCase):
    def test_contract_is_versioned_and_complete(self) -> None:
        contract = workspace_contract()
        self.assertEqual("cws-viewer-workspace-15.1", V15_WORKSPACE_SCHEMA)
        self.assertEqual(15, V15_WORKSPACE_STATE_VERSION)
        self.assertEqual(V15_WORKSPACE_SCHEMA, contract["schema"])
        self.assertEqual(V15_VERSION, contract["version"])
        self.assertEqual(["project", "properties", "workbench"], [d["key"] for d in contract["docks"]])

    def test_all_panels_are_dockable_and_persistent(self) -> None:
        caps = workspace_contract()["capabilities"]
        self.assertTrue(caps["dockable_panels"])
        self.assertTrue(caps["floating_panels"])
        self.assertTrue(caps["persistent_layout"])
        self.assertTrue(caps["focus_viewer_mode"])
        self.assertTrue(caps["reset_layout"])
        self.assertTrue(caps["v14_functionality_preserved"])
        self.assertEqual({"left", "right", "bottom"}, {spec.area for spec in V15_DOCK_SPECS})

    def test_project_explorer_startup_hierarchy_api_is_backward_compatible(self) -> None:
        scene = build_synthetic_product_scene(25, parts_per_assembly=10)
        index = SceneIndex.build(scene)
        self.assertIs(index.children_by_node, index.children_by_parent)
        self.assertTrue(index.root_node_ids)
        for root_id in index.root_node_ids:
            self.assertEqual(
                index.children_by_parent.get(root_id, ()),
                index.children_by_node.get(root_id, ()),
            )

    def test_phase1_contract_keeps_t8_and_adds_viewer_first_startup(self) -> None:
        contract = phase1_workspace_contract()
        caps = contract["capabilities"]
        self.assertEqual("cws-viewer-workspace-15.2", contract["schema"])
        self.assertEqual(V15_VERSION, contract["version"])
        self.assertEqual(PHASE1_BUILD, contract["phase1"]["build"])
        self.assertEqual(PHASE1_LAYOUT_VERSION, contract["phase1"]["layout_version"])
        self.assertEqual(
            ["review", "coordination", "export_center", "manufacturing_faces"],
            contract["phase1"]["lazy_panels"],
        )
        for name in (
            "startup_geometry_cache_prefetch",
            "lazy_review_coordination_export_manufacturing",
            "fail_isolated_optional_panels",
            "clean_viewer_first_layout",
            "phase1_professional_shell",
            "startup_metrics",
            "canonical_manufacturing_faces",
        ):
            self.assertTrue(caps[name], name)

    def test_phase2_contract_is_built_on_phase1_without_reopening_heavy_panels(self) -> None:
        contract = phase2_workspace_contract()
        caps = contract["capabilities"]
        self.assertEqual("cws-viewer-workspace-15.2", contract["schema"])
        self.assertEqual(V15_VERSION, contract["version"])
        self.assertEqual(PHASE2_BUILD, contract["phase2"]["build"])
        self.assertEqual(PHASE1_BUILD, contract["phase2"]["parent_build"])
        self.assertTrue(contract["phase2"]["runtime"]["review_panel_lazy"])
        for name in (
            "phase1_startup_preserved",
            "phase2_actual_vtk_input_host",
            "phase2_review_panel_remains_lazy",
            "interactive_markup_line",
            "interactive_markup_freehand",
            "saved_view_review_snapshot",
            "view_groups",
            "view_slideshow",
            "section_plane_offset_control",
            "reset_model_display_state",
        ):
            self.assertTrue(caps[name], name)

    def test_mesh_cache_prefetch_warms_verified_entries_for_fast_reopen(self) -> None:
        vertices = np.array(
            [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [0.0, 100.0, 0.0]],
            dtype=np.float64,
        )
        triangles = np.array([[0, 1, 2]], dtype=np.int32)
        mesh = MeshData(
            vertices,
            triangles,
            "a" * 64,
            "phase1-test",
        )
        settings = TessellationSettings()
        key = "b" * 64
        with TemporaryDirectory() as tmp:
            writer = MeshCache(tmp, max_memory_items=2)
            writer.put(
                key,
                mesh,
                provider_version="phase1-test-v1",
                settings=settings,
            )
            cache = MeshCache(tmp, max_memory_items=4)
            self.assertEqual(1, cache.prefetch((key,), max_workers=2))
            before = cache.stats.memory_hits
            loaded = cache.get(key)
            self.assertIsNotNone(loaded)
            self.assertEqual(before + 1, cache.stats.memory_hits)
            assert loaded is not None
            self.assertEqual(mesh.mesh_hash, loaded.mesh_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
