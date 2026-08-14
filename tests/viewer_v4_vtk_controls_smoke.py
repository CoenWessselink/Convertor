from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageStat

from cws_viewer.backends.vtk_project import VtkProjectBackend
from cws_viewer.contracts.enums import BackgroundTheme, RenderMode, StandardView
from cws_viewer.contracts.state import ColorAssignment, ScreenshotOptions
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Rgba


class ViewerV4VtkControlsTests(unittest.TestCase):
    def test_professional_display_states_render_different_valid_images(self) -> None:
        scene = build_synthetic_product_scene(500, parts_per_assembly=100)
        backend = VtkProjectBackend(offscreen=True)
        controller = ViewerCoreController(backend, width=960, height=640)
        try:
            controller.load_scene(scene)
            controller.set_standard_view(StandardView.ISOMETRIC)
            controller.fit_all()
            images: dict[str, bytes] = {}

            images["original"] = controller.screenshot(
                ScreenshotOptions(960, 640, "png")
            )
            controller.set_render_mode(RenderMode.WIREFRAME)
            images["wireframe"] = controller.screenshot(
                ScreenshotOptions(960, 640, "png")
            )
            controller.set_render_mode(RenderMode.SHADED_EDGES)
            controller.set_background_theme(BackgroundTheme.LIGHT)
            controller.colorize(
                tuple(
                    ColorAssignment(
                        f"node:item:{index:06d}",
                        Rgba(0.90, 0.32, 0.26, 1.0)
                        if index % 2
                        else Rgba(0.16, 0.63, 0.88, 1.0),
                    )
                    for index in range(500)
                )
            )
            images["colorized"] = controller.screenshot(
                ScreenshotOptions(960, 640, "png")
            )
            controller.isolate(("node:assembly:0001",), ghost_context=True)
            controller.set_selection(("node:item:000101",))
            controller.fit_all()
            images["ghost"] = controller.screenshot(
                ScreenshotOptions(960, 640, "png")
            )

            hashes = {name: hashlib.sha256(data).hexdigest() for name, data in images.items()}
            self.assertEqual(len(images), len(set(hashes.values())))
            for name, data in images.items():
                self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"), name)
                image = Image.open(BytesIO(data)).convert("RGB")
                self.assertEqual((960, 640), image.size)
                variance = sum(ImageStat.Stat(image).var)
                self.assertGreater(variance, 25.0, name)
        finally:
            controller.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
