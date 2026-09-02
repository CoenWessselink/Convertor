from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.backends.vtk_project_mesh_v14 import VtkProjectMeshV14Backend
from cws_viewer.cache.render_resource_cache import SharedRenderResourceCache
from cws_viewer.contracts.state import ColorAssignment
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.math3d import Rgba


class PolygonMemoryBackend(MemoryRenderBackend):
    def __init__(self) -> None:
        super().__init__()
        self.received_polygon = ()

    def nodes_in_screen_polygon(self, points, _index):
        self.received_polygon = tuple(points)
        return ("node:item:000001", "node:item:000002")


class SharedCacheAndSelectionTests(unittest.TestCase):
    def test_same_repository_shares_exact_resource_and_counts_hit(self) -> None:
        repository = MeshRepository()
        calls = []
        first = SharedRenderResourceCache.get_or_create(
            repository, "polydata", "G1", lambda: calls.append("build") or object()
        )
        second = SharedRenderResourceCache.get_or_create(
            repository, "polydata", "G1", lambda: calls.append("duplicate") or object()
        )
        self.assertIs(first, second)
        self.assertEqual(["build"], calls)
        stats = SharedRenderResourceCache.stats(repository)
        self.assertEqual(1, stats.polydata_items)
        self.assertGreaterEqual(stats.hits, 1)
        self.assertEqual(id(repository), stats.repository_identity)

        other = MeshRepository()
        third = SharedRenderResourceCache.get_or_create(other, "polydata", "G1", object)
        self.assertIsNot(first, third)
        SharedRenderResourceCache.invalidate(repository, {"G1"})
        self.assertEqual(0, SharedRenderResourceCache.stats(repository).polydata_items)

    def test_freehand_lasso_runs_through_controller_selection_contract(self) -> None:
        backend = PolygonMemoryBackend()
        controller = V14ViewerCoreController(backend, width=800, height=600)
        controller.load_scene(build_synthetic_product_scene(10, parts_per_assembly=5))
        try:
            polygon = ((10, 10), (250, 20), (230, 190), (20, 170))
            selected = controller.select_polygon(polygon)
            self.assertEqual(polygon, backend.received_polygon)
            self.assertEqual(("node:item:000001", "node:item:000002"), selected)
            self.assertEqual(selected, controller.get_selection())
        finally:
            controller.shutdown()

    def test_actual_polygon_geometry_and_display_colour_selection(self) -> None:
        square = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0))
        self.assertTrue(VtkProjectMeshV14Backend._point_in_polygon((50.0, 50.0), square))
        self.assertFalse(VtkProjectMeshV14Backend._point_in_polygon((150.0, 50.0), square))

        backend = MemoryRenderBackend()
        controller = V14ViewerCoreController(backend, width=800, height=600)
        controller.load_scene(build_synthetic_product_scene(10, parts_per_assembly=5))
        try:
            same = Rgba(0.2, 0.4, 0.6, 1.0)
            controller.colorize((
                ColorAssignment("node:item:000001", same),
                ColorAssignment("node:item:000002", same),
                ColorAssignment("node:item:000003", Rgba(0.8, 0.2, 0.1, 1.0)),
            ))
            controller.set_selection(("node:item:000001",))
            selected = controller.select_same_display_color()
            self.assertEqual(("node:item:000001", "node:item:000002"), selected)
        finally:
            controller.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
