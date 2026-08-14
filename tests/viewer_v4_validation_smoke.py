from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "validation" / "run_viewer_v4_professional_controls.py"


class ViewerV4ValidationTests(unittest.TestCase):
    def test_validation_runner_emits_green_machine_readable_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-viewer-v4-validation-") as temp:
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--nodes", "240", "--output", temp],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=240,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            output = Path(temp)
            payload = json.loads((output / "VIEWER_V4_VALIDATION_RESULTS.json").read_text(encoding="utf-8"))
            self.assertEqual("passed", payload["status"])
            self.assertTrue(all(payload["acceptance"].values()))
            self.assertTrue((output / "VIEWER_V4_VALIDATION_REPORT.md").is_file())
            self.assertTrue((output / "CWS_Viewer_V4_Professional_Controls_Contactsheet.png").is_file())
            self.assertTrue((output / "viewer_v4_validation.cwsview.json.sha256").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
