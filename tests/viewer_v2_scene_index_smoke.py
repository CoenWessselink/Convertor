from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Vector3


class ViewerV2SceneIndexTests(unittest.TestCase):
    def test_scene_hash_and_index_are_deterministic(self) -> None:
        first = build_synthetic_product_scene(10_000)
        second = build_synthetic_product_scene(10_000)
        self.assertEqual(first.scene_hash, second.scene_hash)
        self.assertEqual(first, second)
        index = SceneIndex.build(first)
        self.assertEqual(10_000, len(index.renderable_node_ids))
        self.assertEqual(10_101, len(first.nodes))
        self.assertEqual(8_000, index.counts_by_kind()["part"])

    def test_world_bounds_apply_hierarchy_transform(self) -> None:
        scene = build_synthetic_product_scene(10)
        index = SceneIndex.build(scene)
        bounds = index.world_bounds_by_node["node:item:000001"]
        self.assertTrue(bounds.center.almost_equal(Vector3(105.0, 0.0, 0.0)))
        self.assertGreater(bounds.size.x, 0.0)

    def test_assembly_descendants_and_selection_promotion(self) -> None:
        scene = build_synthetic_product_scene(250, parts_per_assembly=100)
        index = SceneIndex.build(scene)
        children = index.descendants(
            ("node:assembly:0001",), include_self=False, renderable_only=True
        )
        self.assertEqual(100, len(children))
        promoted = index.selectable_node_for_level(
            "node:item:000123", SelectionLevel.ASSEMBLY
        )
        self.assertEqual("node:assembly:0001", promoted)

    def test_revision_changes_hash_but_not_stable_ids(self) -> None:
        first = build_synthetic_product_scene(100, revision_id="A")
        second = build_synthetic_product_scene(100, revision_id="B")
        self.assertNotEqual(first.scene_hash, second.scene_hash)
        self.assertEqual(
            {node.node_id for node in first.nodes},
            {node.node_id for node in second.nodes},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
