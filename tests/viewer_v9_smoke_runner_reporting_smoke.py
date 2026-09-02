from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.run_all_smokes_v9 import (
    SOURCE_SMOKE_EXCLUSIONS,
    _failure_excerpt,
    _workflow_command_escape,
)


class ViewerV9SmokeRunnerReportingTests(unittest.TestCase):
    def test_failure_excerpt_prefers_stderr_and_is_bounded(self) -> None:
        self.assertEqual("native crash", _failure_excerpt("stdout", "native crash", 3))
        self.assertEqual("cdef", _failure_excerpt("abcdef", "", 3, limit=4))
        self.assertIn("exit code 3221225477", _failure_excerpt("", "", 3221225477))

    def test_github_command_payload_is_escaped(self) -> None:
        self.assertEqual("100%25%0D%0Afailed", _workflow_command_escape("100%\r\nfailed"))

    def test_environment_patch_does_not_leak(self) -> None:
        before = os.environ.get("GITHUB_ACTIONS")
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            self.assertEqual("true", os.environ["GITHUB_ACTIONS"])
        self.assertEqual(before, os.environ.get("GITHUB_ACTIONS"))

    def test_packaged_only_conversion_matrix_is_not_run_without_artifact_arguments(self) -> None:
        self.assertIn(
            "conversion_one_phase_packaged_smoke.py",
            SOURCE_SMOKE_EXCLUSIONS,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
