from __future__ import annotations

from pathlib import Path
import statistics
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.vtk_project import VtkProjectBackend
from cws_viewer.contracts.enums import StandardView
from cws_viewer.contracts.state import ScenePatch
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene, stable_sample_node_ids


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))]


class ViewerV2VtkCoreTests(unittest.TestCase):
    def test_10k_scene_navigation_picking_visibility_and_reload(self) -> None:
        scene = build_synthetic_product_scene(10_000)
        backend = VtkProjectBackend(offscreen=True)
        controller = ViewerCoreController(backend, width=960, height=640)
        try:
            started = time.perf_counter()
            controller.load_scene(scene)
            load_ms = (time.perf_counter() - started) * 1000.0
            controller.set_standard_view(StandardView.TOP)
            controller.fit_all()
            controller.render()

            sample_ids = stable_sample_node_ids(10_000, sample_count=25)
            latencies: list[float] = []
            correct = 0
            for node_id in sample_ids:
                x, y = backend.node_display_point(node_id)
                started = time.perf_counter()
                pick = controller.pick_at(x, y)
                latencies.append((time.perf_counter() - started) * 1000.0)
                if pick is not None and pick.node_id == node_id:
                    correct += 1
            self.assertEqual(len(sample_ids), correct)
            self.assertLess(_p95(latencies), 100.0)

            controller.hide(("node:assembly:0000",))
            self.assertEqual(9_900, len(controller.session.render_state(controller.index).visible_node_ids))
            controller.show(("node:assembly:0000",))
            controller.isolate(("node:assembly:0001",), ghost_context=False)
            self.assertEqual(100, len(controller.session.render_state(controller.index).visible_node_ids))
            controller.isolate(("node:assembly:0001",), ghost_context=True)
            self.assertEqual(9_900, len(controller.session.render_state(controller.index).ghosted_node_ids))

            controller.set_selection(("node:item:000101", "node:item:000102"))
            replacement = build_synthetic_product_scene(10_000, revision_id="V2-B", name_suffix="-B")
            controller.update_scene(
                ScenePatch(
                    expected_scene_hash=scene.scene_hash,
                    replacement_scene=replacement,
                    reason="stable reload",
                )
            )
            self.assertEqual(
                ("node:item:000101", "node:item:000102"), controller.get_selection()
            )
            self.assertNotEqual(scene.scene_hash, replacement.scene_hash)

            with tempfile.TemporaryDirectory(prefix="cws-viewer-v2-vtk-") as temp:
                path = backend.capture_png(Path(temp) / "viewer_v2_10k.png", width=1280, height=720)
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 10_000)
                self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertLess(load_ms, 10_000.0)
        finally:
            controller.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
