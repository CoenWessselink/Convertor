from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "validation" / "run_viewer_v2_validation.py"


class ViewerV2ValidationTests(unittest.TestCase):
    def test_validation_runner_emits_machine_readable_green_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-viewer-v2-validation-") as temp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--nodes",
                    "1000",
                    "--pick-samples",
                    "20",
                    "--output",
                    temp,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=180,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            output = Path(temp)
            payload = json.loads(
                (output / "VIEWER_V2_VALIDATION_RESULTS.json").read_text(encoding="utf-8")
            )
            self.assertEqual("passed", payload["status"])
            self.assertTrue(all(payload["acceptance"].values()))
            self.assertTrue((output / "VIEWER_V2_VALIDATION_REPORT.md").exists())
            self.assertTrue((output / "CWS_Viewer_V2_Core_Contactsheet.png").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
