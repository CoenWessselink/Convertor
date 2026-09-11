"""Per-object artifact identity; positive CAD fixture is explicitly synthetic."""
from __future__ import annotations
import io,json,sys,tempfile,unittest,warnings,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cws_convertor.production_export.verify import verify_export_directory,verify_export_zip,ExportVerificationError
from cws_convertor.production_export.utils import canonical_json_bytes,sha256_bytes,stable_hash
from cws_convertor.production_export.engine import ProductionExportEngine


def fixture(root, *, owners=('A',), expected=b'actual', size=6, relative='part.dat'):
    """Synthetic manifest only. Not a native acceptance exporter."""
    root.mkdir(parents=True,exist_ok=True)
    (root/'part.dat').write_bytes(b'actual')
    value={'schema_version':'manifest-unit-fixture','items':[
        {'part_id':key,'artifacts':[{'status':'exported','relative_path':relative,
            'sha256':sha256_bytes(expected),'size_bytes':size}]} for key in owners]}
    value['manifest_sha256']=stable_hash(value)
    (root/'manifest.json').write_bytes(canonical_json_bytes(value))
    ProductionExportEngine._write_checksums(root)
    archive=root.with_suffix('.zip');ProductionExportEngine._create_zip(root,archive,True)
    return archive


class ArtifactIdentityTests(unittest.TestCase):
    def both_refuse(self,**kwargs):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'package';archive=fixture(root,**kwargs)
            with self.assertRaises(ExportVerificationError):verify_export_directory(root)
            with self.assertRaises(ExportVerificationError):verify_export_zip(archive)

    def test_valid_artifact_is_independently_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'package';archive=fixture(root)
            self.assertEqual(1,verify_export_directory(root)['checked_artifacts'])
            self.assertEqual(1,verify_export_zip(archive)['checked_artifacts'])

    def test_rewritten_checksums_do_not_hide_wrong_object_bytes(self):
        self.both_refuse(expected=b'overwritten')

    def test_valid_hash_does_not_hide_wrong_size(self):
        self.both_refuse(size=999)

    def test_identical_bytes_do_not_allow_two_owners_one_path(self):
        self.both_refuse(owners=('A','B'))

    def test_missing_referenced_artifact_is_not_just_unlisted(self):
        self.both_refuse(relative='missing.dat')

    def test_windows_and_traversal_artifact_paths_refused(self):
        for path in ('../part.dat','/part.dat',r'C:\part.dat',r'folder\part.dat'):
            with self.subTest(path=path):self.both_refuse(relative=path)

    def test_duplicate_zip_entry_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=fixture(Path(folder)/'package')
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                with zipfile.ZipFile(archive,'a') as z:z.writestr('part.dat',b'actual')
            with self.assertRaisesRegex(ExportVerificationError,'Dubbele'):verify_export_zip(archive)

    def test_real_grouped_same_prefix_ids_keep_both_complete_artifacts(self):
        from cws_convertor.ui_qt.bom_export_evidence import _released_project
        from cws_viewer.export_center import V15ExportCenterService,ExportScope,ExportScopeKind,ExportJobStatus
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)
            first=_released_project(out/'a',part_id='SHARED-PREFIX-A',part_position='SAME',assembly_id='A',assembly_mark='SAME')
            second=_released_project(out/'b',part_id='SHARED-PREFIX-B',part_position='SAME',assembly_id='B',assembly_mark='SAME')
            first.project.parts.update(second.project.parts);first.project.assemblies.update(second.project.assemblies)
            service=V15ExportCenterService(first.project)
            job=service.prepare_job(ExportScope(ExportScopeKind.ENTITY_IDS,entity_ids=tuple(first.project.parts),metadata={'grouping':'part_mark'}),('STEP','DSTV','PDF'))
            result=service.execute_job(job.job_id,out/'export')
            self.assertEqual(ExportJobStatus.COMPLETED,result.status,result.error)
            with zipfile.ZipFile(result.package_path) as z:
                parent=json.loads(z.read('manifest.json'));self.assertEqual(1,len(parent['groups']))
                with zipfile.ZipFile(io.BytesIO(z.read(parent['groups'][0]['file']))) as child:
                    manifest=json.loads(child.read('manifest.json'));self.assertEqual(2,len(manifest['items']))
                    owners={}
                    for item in manifest['items']:
                        for artifact in item['artifacts']:
                            data=child.read(artifact['relative_path'])
                            self.assertEqual(sha256_bytes(data),artifact['sha256'])
                            self.assertEqual(len(data),artifact['size_bytes'])
                            name=artifact['relative_path'].casefold()
                            self.assertNotIn(name,owners);owners[name]=item['part_id']
                    self.assertEqual({'SHARED-PREFIX-A','SHARED-PREFIX-B'},set(owners.values()))
                    self.assertEqual(8,len(owners))


if __name__=='__main__':unittest.main(verbosity=2)
