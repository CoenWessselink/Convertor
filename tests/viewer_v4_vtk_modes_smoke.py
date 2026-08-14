from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.vtk_project import VtkProjectBackend
from cws_viewer.contracts.enums import BackgroundTheme, RenderMode, StandardView
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene


@unittest.skipIf(
    os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
    "GitHub Windows has no stable native OpenGL window; viewer_ci_headless_smoke covers the native pipeline",
)
class ViewerV4VtkModesTests(unittest.TestCase):
    def test_professional_render_modes_and_backgrounds_are_visual(self) -> None:
        scene = build_synthetic_product_scene(120, parts_per_assembly=30)
        backend = VtkProjectBackend(offscreen=True)
        controller = ViewerCoreController(backend, width=900, height=600)
        try:
            controller.load_scene(scene)
            controller.set_standard_view(StandardView.ISOMETRIC)
            controller.fit_all()
            with tempfile.TemporaryDirectory(prefix="cws-v4-modes-") as temp:
                output = Path(temp)
                files: list[Path] = []
                cases = (
                    ("dark_edges", RenderMode.SHADED_EDGES, BackgroundTheme.DARK),
                    ("slate_shaded", RenderMode.SHADED, BackgroundTheme.SLATE),
                    ("light_wire", RenderMode.WIREFRAME, BackgroundTheme.LIGHT),
                )
                for name, mode, theme in cases:
                    controller.set_render_mode(mode)
                    controller.set_background_theme(theme)
                    controller.render()
                    path = backend.capture_png(output / f"{name}.png", width=900, height=600)
                    self.assertTrue(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                    self.assertGreater(path.stat().st_size, 8_000)
                    files.append(path)
                hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
                self.assertEqual(len(files), len(hashes))
        finally:
            controller.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
