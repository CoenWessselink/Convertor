from __future__ import annotations
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.revisions import build_revision_impact_plan,compare_project_revisions,verify_compare_manifest,verify_compare_package,write_compare_csv,write_compare_manifest,write_compare_package
TESTS=ROOT/'tests'
if str(TESTS) not in sys.path: sys.path.insert(0,str(TESTS))
from viewer_v7_project_revision_smoke import projects

class ViewerV7ManifestTests(unittest.TestCase):
    def test_atomic_manifest_checksum_csv_and_tamper_detection(self):
        old,new=projects(); report=compare_project_revisions(old,new); plan=build_revision_impact_plan(old,new,report)
        with tempfile.TemporaryDirectory(prefix='cws-v7-manifest-') as temp:
            path=write_compare_manifest(Path(temp)/'compare.json',report,impact_plan=plan)
            info=verify_compare_manifest(path)
            self.assertEqual(len(report.changes),info['change_count'])
            self.assertTrue(path.with_suffix('.json.sha256').exists())
            csv_path=write_compare_csv(Path(temp)/'compare.csv',report)
            self.assertIn('manufacturing_changed',csv_path.read_text(encoding='utf-8-sig').splitlines()[0])
            path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'checksum'):
                verify_compare_manifest(path)

    def test_deterministic_zip_package_and_path_safety(self):
        old,new=projects(); report=compare_project_revisions(old,new); plan=build_revision_impact_plan(old,new,report)
        with tempfile.TemporaryDirectory(prefix='cws-v7-package-') as temp:
            root=Path(temp)
            evidence=root/'evidence.txt'; evidence.write_text('revision evidence',encoding='utf-8')
            first=write_compare_package(root/'package-a',report,impact_plan=plan,extra_files={'evidence/evidence.txt':evidence},zip_path=root/'a.zip')
            second=write_compare_package(root/'package-b',report,impact_plan=plan,extra_files={'evidence/evidence.txt':evidence},zip_path=root/'b.zip')
            info=verify_compare_package(first['zip'])
            self.assertGreaterEqual(info['verified_files'],5)
            self.assertEqual(first['zip'].read_bytes(),second['zip'].read_bytes())
            with self.assertRaisesRegex(ValueError,'Onveilig'):
                write_compare_package(root/'unsafe',report,extra_files={'../escape.txt':evidence})

    def test_internal_report_hash_rejects_recomputed_outer_checksum(self):
        import hashlib, json
        old,new=projects(); report=compare_project_revisions(old,new); plan=build_revision_impact_plan(old,new,report)
        with tempfile.TemporaryDirectory(prefix='cws-v7-manifest-internal-') as temp:
            path=write_compare_manifest(Path(temp)/'compare.json',report,impact_plan=plan)
            payload=json.loads(path.read_text(encoding='utf-8'))
            payload['report']['changes'][0]['confidence']=0.123456
            raw=(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
            path.write_bytes(raw)
            path.with_suffix('.json.sha256').write_text(hashlib.sha256(raw).hexdigest()+'\n',encoding='ascii')
            with self.assertRaisesRegex(ValueError,'Interne compare report hash'):
                verify_compare_manifest(path)

if __name__=='__main__': unittest.main(verbosity=2)
