from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_NAME


class ViewerV9LauncherTests(unittest.TestCase):
    def test_launcher_version_and_integrated_selftest(self) -> None:
        version = subprocess.run(
            [sys.executable, str(ROOT / "CWS_Convertor_App.py"), "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        self.assertEqual(0, version.returncode, version.stderr)
        self.assertIn(APP_NAME, version.stdout)
        with tempfile.TemporaryDirectory(prefix="cws-v9-launcher-") as directory:
            project = Path(directory) / "smoke.cwscproj"
            create = subprocess.run(
                [sys.executable, str(ROOT / "CWS_Convertor_App.py"), "--create-smoke-project", str(project)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            self.assertEqual(0, create.returncode, create.stderr)
            report_path = Path(directory) / "report.json"
            result = subprocess.run(
                [sys.executable, str(ROOT / "CWS_Convertor_App.py"), "--self-test", "--project", str(project), "--report", str(report_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual("passed", payload["status"])
            self.assertEqual("passed", payload["integration"]["status"])
            self.assertIn("runtime", payload)
            self.assertIn("checks", payload)
            self.assertIn("viewer_integration", {item["name"] for item in payload["checks"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
