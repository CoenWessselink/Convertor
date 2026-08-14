from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _reexec_with_xvfb_if_needed() -> None:
    if (
        platform.system() == "Linux"
        and not os.environ.get("DISPLAY")
        and os.environ.get("CWS_VIEWER_XVFB_CHILD") != "1"
    ):
        xvfb = shutil.which("xvfb-run")
        if xvfb is None:
            return
        environment = {**os.environ, "CWS_VIEWER_XVFB_CHILD": "1", "PYTHONPATH": str(ROOT)}
        completed = subprocess.run([xvfb, "-a", sys.executable, __file__], env=environment)
        raise SystemExit(completed.returncode)


_reexec_with_xvfb_if_needed()

from cws_viewer.technology.benchmark import run_backend_case
from cws_viewer.technology.contracts import TechnologyBackendName


@unittest.skipIf(
    os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
    "GitHub Windows has no stable native OpenGL window; viewer_ci_headless_smoke covers exact topology",
)
class ViewerV1OcctTests(unittest.TestCase):
    def test_occt_renders_picks_clips_and_captures(self) -> None:
        if platform.system() == "Linux" and not os.environ.get("DISPLAY"):
            self.skipTest("X-display/xvfb ontbreekt")
        with tempfile.TemporaryDirectory(prefix="cws-occt-v1-") as temp:
            result = run_backend_case(
                TechnologyBackendName.OCCT_AIS,
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
