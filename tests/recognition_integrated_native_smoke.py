"""Native regressions; absence of native libraries is not a passing result."""
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

class RecognitionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cws_convertor.manufacturing_interpreter.integrated_evidence import run_recognition_evidence
        cls.temp=tempfile.TemporaryDirectory(prefix='cws_native_recognition_')
        cls.report=run_recognition_evidence(cls.temp.name)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_all_native_feature_and_safety_checks(self):
        self.assertGreaterEqual(len(self.report['checks']),50)
        for row in self.report['checks']:
            with self.subTest(name=row['name']): self.assertEqual('PASS',row['status'],row.get('detail'))
    def test_no_manufacturing_authorization(self):
        self.assertIs(False,self.report['machine_transfer_allowed'])
        self.assertIs(False,self.report['full_product_release_approved'])
    def test_existing_phase2_native_regressions(self):
        import runpy
        tests=runpy.run_path(str(ROOT/'tests/test_manufacturing_interpreter_v3_phase2.py'))
        for name in sorted(tests):
            if name.startswith('test_'):
                with self.subTest(name=name): tests[name]()
    def test_precision_counts_false_positives(self):
        from tools.build_mgi_v3_acceptance_corpus import score_features
        self.assertEqual((1,1,0),score_features({'HOLE'},{'HOLE','SLOT'}))
        self.assertEqual((0,0,1),score_features({'NOTCH'},set()))
        self.assertEqual((0,1,0),score_features(set(),{'HOLE'}))
    def test_enum_names_are_normalized(self):
        from types import SimpleNamespace
        from tools.build_mgi_v3_acceptance_corpus import _semantic_names
        from cws_convertor.manufacturing_interpreter.contracts import ManufacturingSemanticType as S
        self.assertEqual({'HOLE','POSITIVE'},_semantic_names(SimpleNamespace(features=[SimpleNamespace(semantic_type=S.HOLE),SimpleNamespace(semantic_type=S.ATTACHMENT_VOLUME)])))
    def test_consumed_hole_fixture_has_no_remaining_hole(self):
        from tools.build_mgi_v3_acceptance_corpus import _notch,_hole_intersecting_cope
        base=_notch(75); result=_hole_intersecting_cope()
        self.assertAlmostEqual(base.Volume(),result.Volume(),places=6)
        self.assertLess(abs(base.cut(result).Volume()),1e-5)
        self.assertLess(abs(result.cut(base).Volume()),1e-5)

if __name__=='__main__': unittest.main(verbosity=2)
