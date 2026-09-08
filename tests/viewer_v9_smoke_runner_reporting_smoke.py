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
    _result_status,
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

    def test_successful_process_with_only_skips_is_not_a_pass(self) -> None:
        self.assertEqual("skipped", _result_status(0, False, "Ran 2 tests\nOK (skipped=2)"))
        self.assertEqual("skipped", _result_status(0, False, "Ran 0 tests\nOK (skipped=1)"))

    def test_partial_skips_do_not_hide_executed_passing_tests(self) -> None:
        self.assertEqual("passed", _result_status(0, False, "Ran 3 tests\nOK (skipped=1)"))

    def test_empty_unittest_run_without_explicit_skip_is_not_relabelled(self) -> None:
        self.assertEqual("passed", _result_status(0, False, "Ran 0 tests\nOK"))

    def test_failure_and_timeout_take_precedence_over_skip_text(self) -> None:
        self.assertEqual("failed", _result_status(1, False, "Ran 3 tests\nFAILED (failures=1, skipped=2)"))
        self.assertEqual("timeout", _result_status(124, True, "Ran 2 tests\nOK (skipped=2)"))

    def test_no_tests_exit_is_only_a_skip_with_explicit_evidence(self) -> None:
        self.assertEqual("skipped", _result_status(5, False, "NO TESTS RAN; skipped=1"))
        self.assertEqual("failed", _result_status(5, False, "unexpected error"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
