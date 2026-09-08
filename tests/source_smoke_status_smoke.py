"""Regression checks for truthful smoke accounting; no GUI is required."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from validation.run_all_smokes_v9 import classify_smoke_result

class SourceSmokeStatusTests(unittest.TestCase):
    def test_all_skipped_zero_exit_is_not_pass(self):
        self.assertEqual('skipped', classify_smoke_result(0, 'Ran 2 tests in 0.1s\nOK (skipped=2)'))
    def test_passing_assertion_script_is_pass(self):
        self.assertEqual('passed', classify_smoke_result(0, 'contract checks OK'))
    def test_passing_unittest_is_pass(self):
        self.assertEqual('passed', classify_smoke_result(0, 'Ran 2 tests in 0.1s\nOK'))
    def test_partial_skip_is_not_an_entirely_skipped_suite(self):
        self.assertEqual('passed', classify_smoke_result(0, 'Ran 3 tests in 0.1s\nOK (skipped=1)'))
    def test_explicit_no_tests_is_skip(self):
        self.assertEqual('skipped', classify_smoke_result(5, 'NO TESTS RAN skipped=2'))
    def test_error_with_skip_text_still_fails(self):
        self.assertEqual('failed', classify_smoke_result(1, 'Ran 2 tests in 0.1s\nFAILED (skipped=2)'))
    def test_timeout_always_wins(self):
        self.assertEqual('timeout', classify_smoke_result(0, 'Ran 1 test\nOK (skipped=1)', timed_out=True))
    def test_nonzero_without_explicit_skip_fails(self):
        self.assertEqual('failed', classify_smoke_result(5, 'no diagnostic output'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
