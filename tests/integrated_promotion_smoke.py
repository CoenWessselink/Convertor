"""The release barrier cannot turn a successful package job into global approval."""
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from tools.verify_integrated_delivery import validate_promotion


class PromotionBarrierTests(unittest.TestCase):
    def setUp(self):
        self.sha='a'*40
        self.jobs=dict(core='success',broad='success',installer='success')
        self.installer=dict(source_commit=self.sha,status='PASS',source_unchanged=True,
                            full_product_release_approved=False,direct_machine_transfer=False,
                            installed_plate_integration=dict(status='PASS',checks=24,python_on_child_path=False))
        # Match FINAL_ACCEPTANCE.json: status is top-level, counts are nested.
        self.strict=dict(status='PASS',summary=dict(required_suites=52,passed_suites=52,tests_run=1,tests_passed=1,skipped_events=0))

    def validate(self):return validate_promotion(self.jobs,self.sha,self.installer,self.strict,[{}, {}, {}, {}])
    def test_positive(self):self.assertEqual([],self.validate())
    def test_any_failure_skip_or_cancellation_blocks(self):
        for job in self.jobs:
            for state in ('failure','skipped','cancelled','in_progress'):
                before=self.jobs[job];self.jobs[job]=state
                self.assertIn('REQUIRED_JOB_NOT_SUCCESSFUL',self.validate());self.jobs[job]=before
    def test_missing_job_blocks(self):
        self.jobs.pop('broad');self.assertTrue(self.validate())
    def test_stale_installer_blocks(self):
        self.installer['source_commit']='b'*40;self.assertTrue(self.validate())
    def test_strict_skips_do_not_pass(self):
        self.strict['summary']['skipped_events']=1;self.assertTrue(self.validate())
    def test_failed_top_level_status_cannot_be_hidden_by_pass_counts(self):
        self.strict['status']='FAIL';self.assertIn('STRICT_SUITE_INCOMPLETE',self.validate())
    def test_missing_top_level_status_is_not_inferred(self):
        self.strict.pop('status');self.strict['summary']['status']='PASS'
        self.assertIn('STRICT_SUITE_INCOMPLETE',self.validate())
    def test_machine_release_and_missing_installed_controls_block(self):
        self.installer['direct_machine_transfer']=True;self.assertTrue(self.validate())
        self.installer['direct_machine_transfer']=False;self.installer.pop('installed_plate_integration');self.assertTrue(self.validate())

if __name__=='__main__':unittest.main(verbosity=2)
