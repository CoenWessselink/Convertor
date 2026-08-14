from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "viewer_harness" / "run_v1_technology_spike.py"


class ViewerV1DecisionTests(unittest.TestCase):
    def test_quick_spike_produces_hybrid_decision_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-viewer-v1-decision-") as temp:
            command = [
                sys.executable,
                str(SCRIPT),
                "--counts",
                "100",
                "--output",
                temp,
                "--orbit-frames",
                "3",
                "--pick-samples",
                "10",
                "--timeout",
                "180",
            ]
            if platform.system() == "Linux" and os.environ.get("DISPLAY"):
                command.extend(["--xvfb", "never"])
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                text=True,
                capture_output=True,
                timeout=240,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            payload = json.loads(
                (Path(temp) / "VIEWER_V1_TECHNOLOGY_RESULTS.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual("vtk_mesh", payload["decision"]["project_renderer"])
            self.assertEqual("occt_ais", payload["decision"]["exact_part_renderer"])
            self.assertEqual(2, len(payload["cases"]))
            self.assertTrue((Path(temp) / "VIEWER_V1_TECHNOLOGY_DECISION.md").exists())
            self.assertTrue((Path(temp) / "VIEWER_V1_TECHNOLOGY_RESULTS.csv").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
