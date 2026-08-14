from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.technology.fixtures import build_box_grid_scene, deterministic_pick_indices


class ViewerV1FixtureTests(unittest.TestCase):
    def test_scene_is_deterministic_and_has_unique_ids(self) -> None:
        first = build_box_grid_scene(10_000)
        second = build_box_grid_scene(10_000)
        self.assertEqual(first, second)
        self.assertEqual(first.geometry_hash, second.geometry_hash)
        self.assertEqual(10_000, len({item.node_id for item in first.instances}))
        self.assertGreater(first.bounds.maximum.x, 0)
        self.assertGreater(first.bounds.maximum.y, 0)

    def test_pick_samples_cover_scene(self) -> None:
        indices = deterministic_pick_indices(10_000, 50)
        self.assertEqual(0, indices[0])
        self.assertEqual(9_999, indices[-1])
        self.assertEqual(50, len(indices))

    def test_invalid_node_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_box_grid_scene(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
