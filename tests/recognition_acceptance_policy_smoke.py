from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from cws_convertor.manufacturing_interpreter.acceptance_policy import corpus_verdict

class RecognitionPolicyTests(unittest.TestCase):
    def summary(self):
        return dict(precision=1.0,recall=1.0,true_positive=12,false_ready=0,errors=[],deterministic_repeat_failures=0)
    def rows(self):return [dict(id=i,readiness='READY',unsafe_ready=False) for i in ('01','02')]
    def test_positive_reference_passes(self):self.assertTrue(corpus_verdict(self.summary(),rows=self.rows())['passed'])
    def test_all_rejecting_recognizer_fails(self):
        rows=[dict(r,readiness='BLOCKED') for r in self.rows()]
        self.assertFalse(corpus_verdict(self.summary(),rows=rows)['passed'])
    def test_false_ready_unconditionally_fails(self):
        value=self.summary();value['false_ready']=1
        self.assertFalse(corpus_verdict(value,rows=self.rows())['passed'])
    def test_low_recall_and_precision_fail(self):
        for key in ('precision','recall'):
            for invalid in (0.5,None,float('nan'),True,1.5):
                with self.subTest(key=key,value=invalid):
                    value=self.summary();value[key]=invalid
                    self.assertFalse(corpus_verdict(value,rows=self.rows())['passed'])
    def test_no_positives_cannot_claim_perfect_empty_accuracy(self):
        value=self.summary();value['true_positive']=0
        self.assertFalse(corpus_verdict(value,rows=self.rows())['passed'])
    def test_missing_reference_cannot_pass(self):self.assertFalse(corpus_verdict(self.summary(),rows=[])['passed'])

if __name__=='__main__':unittest.main(verbosity=2)
