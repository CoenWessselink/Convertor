"""Negative acceptance tests: zero exit, partial ranges and skips are not release."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from validation.run_all_smokes_v9 import classify_smoke_outcome

class SmokeReportingTests(unittest.TestCase):
    def test_all_skipped_is_not_pass(self):
        r=classify_smoke_outcome('', 'Ran 2 tests in 0.001s\n\nOK (skipped=2)\n', 0)
        self.assertEqual(r['status'],'skipped')
        self.assertEqual(r['skipped_test_count'],2)
        self.assertFalse(r['partial_completion'])
    def test_partial_skip_is_visible(self):
        r=classify_smoke_outcome('', 'Ran 3 tests in 0.001s\n\nOK (skipped=1)\n',0)
        self.assertEqual(r['status'],'skipped')
        self.assertTrue(r['partial_completion'])
        self.assertEqual(r['reported_test_count'],3)
    def test_expected_failure_is_not_acceptance(self):
        r=classify_smoke_outcome('', 'Ran 1 test in 0.001s\n\nOK (expected failures=1)\n',0)
        self.assertEqual(r['status'],'incomplete')
    def test_no_tests_is_not_pass(self):
        for text,rc in [('Ran 0 tests in 0.0s\n\nOK',0),('NO TESTS RAN\nOK (skipped=1)',5)]:
            self.assertNotEqual(classify_smoke_outcome('',text,rc)['status'],'passed')
    def test_failure_and_timeout_have_precedence_over_skips(self):
        text='Ran 2 tests in 0.1s\nFAILED (failures=1, skipped=1)\n'
        self.assertEqual(classify_smoke_outcome('',text,1)['status'],'failed')
        self.assertEqual(classify_smoke_outcome('',text,124,timed_out=True)['status'],'timeout')
    def test_count_basis_does_not_invent_tests_for_plain_script(self):
        r=classify_smoke_outcome('assertions passed','',0)
        self.assertEqual(r['status'],'passed')
        self.assertIsNone(r['reported_test_count'])
        self.assertEqual(r['count_basis'],'script_exit_code_only')
    def test_legacy_skip(self):
        self.assertEqual(classify_smoke_outcome('SKIP: native display absent','',0)['status'],'skipped')

if __name__=='__main__': unittest.main(verbosity=2)
