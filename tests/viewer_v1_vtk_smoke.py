from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HEADLESS_WINDOWS = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"

if not HEADLESS_WINDOWS:
    from cws_viewer.technology.benchmark import run_backend_case
    from cws_viewer.technology.contracts import TechnologyBackendName


@unittest.skipIf(
    HEADLESS_WINDOWS,
    "GitHub Windows has no stable native OpenGL window; viewer_ci_headless_smoke covers the native pipeline",
)
class ViewerV1VtkTests(unittest.TestCase):
    def test_vtk_renders_picks_clips_and_captures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-vtk-v1-") as temp:
            result = run_backend_case(
                TechnologyBackendName.VTK_MESH,
                100,
                output_dir=temp,
                orbit_frames=3,
                pick_samples=10,
                width=640,
                height=480,
            )
            self.assertEqual("passed", result.status, result.error)
            self.assertEqual(1.0, result.pick_success_rate)
            self.assertLess(result.pick_latency.p95_ms, 100.0)
            screenshot = Path(result.screenshot_path)
            self.assertTrue(screenshot.exists())
            self.assertTrue(screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
