"""The release barrier cannot turn a successful package job into global approval."""
from copy import deepcopy
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
        self.strict=dict(status='PASS',summary=dict(required_suites=52,passed_suites=52,tests_run=1,tests_passed=1,skipped_events=0))
        self.installer['installed_recognition_integration'] = dict(status='PASS',checks=50,
            source_commit=self.sha,executable_sha256='b'*64,python_on_child_path=False)
        rows=[dict(id=f'{i:02d}',readiness='READY' if i<=2 else 'REVIEW_REQUIRED',
                   unsafe_ready=False,deterministic_identity=True,features_scored=True,
                   truth=['HOLE'] if i==1 else [],features=['HOLE'] if i==1 else [],
                   production_readiness='REVIEW_REQUIRED') for i in range(1,46)]
        self.corpus=dict(categories=rows,summary=dict(schema='cws-mgi-v3-acceptance-corpus-v2',
            source_commit=self.sha,source_unchanged=True,category_count=45,generated_step_count=45,
            precision=1.0,recall=1.0,true_positive=1,false_positive=0,false_negative=0,
            false_ready=0,errors=[],deterministic_repeat_failures=0,**{'pass':True}))

    def validate(self):return validate_promotion(self.jobs,self.sha,self.installer,self.strict,[{}, {}, {}, {}],self.corpus)
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
    def test_missing_corpus_and_stale_source_fail_closed(self):
        original=self.corpus
        for value in (None,{},dict(summary={})):
            self.corpus=value;self.assertTrue(self.validate())
        self.corpus=original;self.corpus['summary']['source_commit']='f'*40
        self.assertIn('RECOGNITION_CORPUS_SOURCE_MISMATCH',self.validate())
    def test_corpus_false_pass_does_not_hide_low_recall(self):
        self.corpus['summary']['recall']=0.2
        self.assertIn('RECOGNITION_USEFULNESS_NOT_ACCEPTED',self.validate())
    def test_corpus_extra_features_cannot_be_hidden_by_summary(self):
        self.corpus['categories'][1]['features']=['HOLE']
        self.assertIn('RECOGNITION_CORPUS_COUNTS_MISMATCH',self.validate())
    def test_corpus_duplicate_or_missing_cases_block(self):
        self.corpus['categories'][2]['id']='01'
        self.assertIn('RECOGNITION_CORPUS_INCOMPLETE',self.validate())
    def test_corpus_unsafe_machine_approval_blocks(self):
        self.corpus['categories'][0]['production_readiness']='READY'
        self.assertIn('RECOGNITION_CORPUS_UNSUPPORTED_MACHINE_APPROVAL',self.validate())
    def test_installed_native_evidence_required_at_same_sha(self):
        original=deepcopy(self.installer['installed_recognition_integration'])
        for key,value in [('status','FAIL'),('checks',49),('checks',True),('source_commit','c'*40),('python_on_child_path',True)]:
            self.installer['installed_recognition_integration']=dict(original,**{key:value})
            self.assertIn('INSTALLED_RECOGNITION_PROOF_MISSING_OR_STALE',self.validate())
        self.installer.pop('installed_recognition_integration');self.assertTrue(self.validate())
    def test_machine_release_and_missing_installed_controls_block(self):
        self.installer['direct_machine_transfer']=True;self.assertTrue(self.validate())
        self.installer['direct_machine_transfer']=False;self.installer.pop('installed_plate_integration');self.assertTrue(self.validate())

if __name__=='__main__':unittest.main(verbosity=2)
