"""Manifest/path unit tests, NOT native GUI or original-specification evidence."""
from __future__ import annotations
import contextlib
import io
import json
import hashlib, zipfile
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import finalize_ui_v3_delivery as delivery

SHA = 'a' * 40


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def grouped_fixture(root):
    """Deliberately synthetic manifest fixture: no CAD, installer or GUI claim."""
    root.mkdir(parents=True, exist_ok=True)
    packages = []
    for kind in ('per_part','part_mark','assembly','assembly_mark','phase','batch','machine','combined'):
        path = root / (kind + '.zip')
        payload = b'MANIFEST UNIT FIXTURE - NOT CAD OR MACHINE OUTPUT'
        manifest = {'manifest_sha256':'d'*64,'grouping':kind,'machine_transfer_allowed':False,
            'selected_part_ids':['EXPORT-A','EXPORT-B'],'requested_formats':['step','nc1','production_pdf'],
            'groups':[{'file':'unit.txt','part_ids':['EXPORT-A','EXPORT-B'],'sha256':hashlib.sha256(payload).hexdigest()}]}
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr('manifest.json',json.dumps(manifest));archive.writestr('unit.txt',payload)
        packages.append({'grouping':kind,'file':path.name,'sha256':delivery.digest(path),'manifest_sha256':'d'*64})
    reviews=[]
    for fmt in ('csv','xlsx','json'):
        path=root/fmt/'manifest.json'
        write_json(path, {'selected_formats':[fmt], 'scope':{'entity_ids':['EXPORT-A']}})
        reviews.append({'format':fmt,'files':{fmt+'/manifest.json':delivery.digest(path)}})
    images={}
    for index in range(3):
        path=root/('unit-screenshot-'+str(index)+'.bin');path.write_bytes(b'MANIFEST UNIT FIXTURE - NOT A SCREENSHOT')
        images[path.name]=delivery.digest(path)
    report=root/'BOM_EXPORT_EVIDENCE.json'
    write_json(report, {'status':'PASS','source_commit':SHA,'source_dirty':False,'frozen':True,
        'executable_sha256':'c'*64, 'checks':[{'status':'PASS'} for _ in range(130)],
        'machine_transfer_allowed':False,'screenshots':images,'packages':packages,'review_exports':reviews})
    return {'report':'exports/BOM_EXPORT_EVIDENCE.json','sha256':delivery.digest(report)}


def drawing_batch_fixture(root):
    """Hash/provenance-only fixture. Payload is NOT an actual PDF or UI evidence."""
    rows = []
    for mode, ids in (('part_subset', ['PART-A']), ('parts', ['PART-A','PART-B']), ('assembly', ['UIV3-A1'])):
        folder = root / ('drawing-batch-' + mode)
        folder.mkdir(parents=True, exist_ok=True)
        pdf = folder / 'Tekeningen.pdf'
        pdf.write_bytes(b'MANIFEST UNIT FIXTURE - NOT A PDF OR SCREENSHOT')
        files = {'Tekeningen.pdf': delivery.digest(pdf)}
        docs = []
        for index, key in enumerate(ids):
            child = folder / (key + '.pdf')
            child.write_bytes(b'MANIFEST UNIT FIXTURE - NOT A PDF')
            files[child.name] = delivery.digest(child)
            docs.append({'entity_id': key, 'first_page': index + 1, 'page_count': 1,
                         'file': child.name, 'sha256': files[child.name],
                         'document_type': 'assembly' if mode == 'assembly' else 'part'})
        manifest = folder / 'BATCH_MANIFEST.json'
        write_json(manifest, {'schema': 'cws-drawing-review-batch-1', 'status': 'verified_review',
                             'production_release_granted': False, 'entity_ids': ids,
                             'documents': docs, 'files': files, 'page_count': len(ids)})
        rows.append({'mode': mode, 'entity_ids': ids, 'manifest': manifest.relative_to(root).as_posix(),
                     'manifest_sha256': delivery.digest(manifest), 'pdf_sha256': delivery.digest(pdf)})
    return {'status': 'PASS', 'expected_part_ids': ['PART-A','PART-B'], 'runs': rows}


def fixture(base):
    """Synthetic manifest fixture; deliberately not a software acceptance run."""
    root, runtime = base / 'source', base / 'runtime'
    promoted = root / 'promoted'
    proof = {'commit': SHA, 'status': 'PASS', 'counts': {'PASS': 43}, 'items': [
        {'requirement_id': f'PDF-{i:02d}', 'status': 'PASS',
         'executed_tests': ['synthetic-manifest-unit-test']} for i in range(1, 44)]}
    write_json(promoted / 'PDF_FUNCTION_GAP_MATRIX.json', proof)
    write_json(root / 'PHASE_3_SOURCE_TEST_EVIDENCE.json', {
        'status': 'GREEN', 'coverage': {str(i): True for i in range(12)},
        'source_revision': SHA, 'source_unchanged': True, 'reused_evidence': False})
    write_json(root / 'PHASE_3_SOAK_EVIDENCE.json', {
        'status': 'passed', 'elapsed_seconds': 600.1, 'checks': {'unit-fixture': True}})
    write_json(root / 'pdf12-source.json', {'commit': SHA, 'status': 'PASS',
        'counts': {'tests': 23, 'skipped': 0, 'failed': 0}})

    def native(folder):
        image = folder / 'images' / 'unit-fixture.bin'
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b'MANIFEST UNIT FIXTURE - NOT A SCREENSHOT')
        child = folder / 'reopen' / 'REPORT.json'
        write_json(child, {'pid': 2, 'status': 'PASS', 'executable_sha256': 'c' * 64})
        report = folder / 'REPORT.json'
        write_json(report, {
            'drawing_batches': drawing_batch_fixture(folder),
            'source_commit': SHA, 'source_dirty': False, 'status': 'PASS',
            'specification_sha256': delivery.SPEC, 'viewer_backend': 'VtkUnitFixture',
            'checks': [{'status': 'PASS'} for _ in range(65)] + [{'name': name, 'status': 'PASS'} for name in sorted(delivery.RELEASE_EVIDENCE_CHECKS)],
            'pid': 1, 'executable_sha256': 'c' * 64,
            'second_process': {'report': r'reopen\REPORT.json', 'sha256': delivery.digest(child)},
            'screenshots': [{'file': r'images\unit-fixture.bin',
                             'sha256': delivery.digest(image), 'missing_glyphs': 0}]})
        return report

    runs = []
    for percent in (100, 125, 150, 175, 200):
        report = native(root / 'dpi' / f'dpi-{percent}')
        runs.append({'scale': percent, 'report': f'dpi-{percent}\\REPORT.json',
                     'sha256': delivery.digest(report)})
    write_json(root / 'dpi' / 'PDF_UI_V3_DPI_EVIDENCE.json', {
        'source_commit': SHA, 'status': 'PASS', 'runs': runs})
    bindings = {}
    for label in ('onefolder', 'portable', 'installed'):
        report = native(runtime / (label + '-main-ui') / 'dpi-100')
        bindings[label] = {'report_sha256': delivery.digest(report)}
    for label in ('dist', 'portable', 'installed'):
        write_json(runtime / (label + '-packaged-runtime.json'), {
            'status': 'passed', 'python_on_child_path': False,
            'pdf12_interactive_dimensioning': {'passed': 35}})
    grouped = grouped_fixture(runtime / 'bom-actions' / 'exports')
    bom_path = runtime / 'installed-bom-actions.json'
    review_exports = []
    for action in delivery.BOM_REVIEW_ACTIONS:
        folder = runtime / 'bom-actions' / action.replace('.', '-')
        folder.mkdir(parents=True)
        extensions = {'.xlsx'} if action == 'export.xlsx' else {'.csv'} if action == 'export.csv' else {'.json'} if action == 'export.json' else {'.xlsx', '.csv', '.json', '.pdf', '.zip'}
        files = {}
        for extension in extensions:
            artifact = folder / ('UNIT-FIXTURE-NOT-REAL-OUTPUT' + extension)
            artifact.write_bytes(b'Synthetic manifest unit fixture only')
            files[artifact.name] = {'sha256': delivery.digest(artifact), 'bytes': artifact.stat().st_size}
        manifest = folder / 'REVIEW_EXPORT.json'
        write_json(manifest, {'action_id': action, 'review_only': True,
            'production_release_allowed': False, 'machine_transfer_allowed': False,
            'scope': {'entity_ids': ['A']}, 'files': files})
        review_exports.append({'action_id': action,
            'manifest': manifest.relative_to(runtime / 'bom-actions').as_posix(),
            'manifest_sha256': delivery.digest(manifest)})
    write_json(bom_path, {'export_followup':grouped, 'status': 'PASS', 'frozen': True, 'source_dirty': False,
                         'source_commit': SHA, 'executable_sha256': 'c' * 64,
                         'checks': [{'status': 'PASS'} for _ in range(40)] + [{'name': name, 'status': 'PASS'} for name in sorted(delivery.BOM_REVIEW_CHECKS)],
                         'review_exports': review_exports,
                         'machine_transfer_allowed': False, 'screenshots': {}})
    write_json(promoted / 'INSTALLER_ACCEPTANCE.json', {
        'installed_bom_actions': {'report_sha256': delivery.digest(bom_path), 'python_on_child_path': False},
        'status': 'PASS', 'source_commit': SHA, 'source_tree': 'b' * 40,
        'version': 'unit-fixture-not-a-release', 'main_ui_runtimes': bindings,
        'pdf_function_proof': {'matrix_sha256': delivery.digest(promoted / 'PDF_FUNCTION_GAP_MATRIX.json')}})
    return root, runtime


class DeliveryPathTests(unittest.TestCase):
    def run_finalizer(self, root, runtime):
        with patch.object(sys, 'argv', ['finalize', '--root', str(root),
                                       '--runtime-root', str(runtime), '--sha', SHA]), contextlib.redirect_stdout(io.StringIO()):
            return delivery.main()

    def test_missing_component_batch_refusal_checks_blocks_promotion(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            report = runtime / 'installed-bom-actions.json'
            payload = delivery.load(report)
            payload['checks'] = [row for row in payload['checks']
                                 if row.get('name') != 'Rejected batch publishes no files or running job']
            write_json(report, payload)
            acceptance = root / 'promoted' / 'INSTALLER_ACCEPTANCE.json'
            binding = delivery.load(acceptance)
            binding['installed_bom_actions']['report_sha256'] = delivery.digest(report)
            write_json(acceptance, binding)
            with self.assertRaisesRegex(RuntimeError, 'BOM review action checks missing'):
                self.run_finalizer(root, runtime)

    def test_missing_one_review_action_blocks_promotion(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            report = runtime / 'installed-bom-actions.json'
            payload = delivery.load(report); payload['review_exports'].pop()
            write_json(report, payload)
            acceptance = root / 'promoted' / 'INSTALLER_ACCEPTANCE.json'
            binding = delivery.load(acceptance)
            binding['installed_bom_actions']['report_sha256'] = delivery.digest(report)
            write_json(acceptance, binding)
            with self.assertRaisesRegex(RuntimeError, 'Four installed BOM review actions'):
                self.run_finalizer(root, runtime)

    def test_review_artifact_tampering_blocks_promotion(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            artifact = next((runtime / 'bom-actions').rglob('*.xlsx'))
            artifact.write_bytes(b'TAMPERED')
            with self.assertRaisesRegex(RuntimeError, 'BOM review artifact hash'):
                self.run_finalizer(root, runtime)

    def test_windows_manifest_paths_are_read_without_rewriting_signed_inputs(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            before = {p: delivery.digest(p) for p in Path(folder).rglob('*') if p.is_file()}
            self.assertEqual(self.run_finalizer(root, runtime), 0)
            for p, expected in before.items():
                self.assertEqual(delivery.digest(p), expected, str(p))
            payload = delivery.load(root / 'promoted' / 'PDF_RUNTIME_EVIDENCE.json')
            self.assertEqual(len(payload['runtimes']), 8)
            self.assertTrue(payload['original_specification_file_reverified'])
            self.assertFalse(payload['original_archive_rehashed_in_ci'])
            release = delivery.load(root / 'promoted' / 'RELEASE_MANIFEST.json')
            self.assertEqual(release['full_original_specification_acceptance'], 'SOFTWARE_BETA_WITH_RECORDED_VISUAL_REVIEW')

    def test_missing_batch_proof_cannot_promote_old_green_report(self):
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, 'batch result missing'):
                delivery._verify_drawing_batches({}, Path(folder))

    def test_changed_batch_output_is_rejected_even_with_green_report(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            binding = drawing_batch_fixture(root)
            (root/'drawing-batch-parts/Tekeningen.pdf').write_bytes(b'tampered')
            with self.assertRaisesRegex(RuntimeError, 'batch output hash'):
                delivery._verify_drawing_batches({'drawing_batches': binding}, root)

    def test_batch_cannot_gain_unselected_objects_by_rebinding_manifest(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            binding = drawing_batch_fixture(root)
            path = root / binding['runs'][0]['manifest']
            payload = delivery.load(path); payload['entity_ids'].append('EXTRA')
            write_json(path, payload); binding['runs'][0]['manifest_sha256'] = delivery.digest(path)
            with self.assertRaisesRegex(RuntimeError, 'batch exact documents'):
                delivery._verify_drawing_batches({'drawing_batches': binding}, root)

    def test_hash_tampering_still_blocks_promotion(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            (root / 'dpi' / 'dpi-100' / 'images' / 'unit-fixture.bin').write_bytes(b'tampered')
            with self.assertRaisesRegex(RuntimeError, 'screenshot hash'):
                self.run_finalizer(root, runtime)

    def test_native_report_without_new_release_regression_is_rejected(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            report = root / 'dpi' / 'dpi-100' / 'REPORT.json'
            value = delivery.load(report)
            value['checks'] = [c for c in value['checks'] if c.get('name') not in delivery.RELEASE_EVIDENCE_CHECKS]
            write_json(report, value)
            index = root / 'dpi' / 'PDF_UI_V3_DPI_EVIDENCE.json'
            manifest = delivery.load(index); manifest['runs'][0]['sha256'] = delivery.digest(report)
            write_json(index, manifest)
            with self.assertRaisesRegex(RuntimeError, 'release-evidence regression missing'):
                self.run_finalizer(root, runtime)

    def test_pre_navigation_green_report_cannot_be_promoted(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            report = root / 'dpi' / 'dpi-100' / 'REPORT.json'
            value = delivery.load(report)
            value['checks'] = [c for c in value['checks']
                if c.get('name') != 'Primary navigation fits at 1280 logical pixels']
            write_json(report, value)
            index = root / 'dpi' / 'PDF_UI_V3_DPI_EVIDENCE.json'
            manifest = delivery.load(index)
            manifest['runs'][0]['sha256'] = delivery.digest(report)
            write_json(index, manifest)
            with self.assertRaisesRegex(RuntimeError, 'release-evidence regression missing'):
                self.run_finalizer(root, runtime)

    def test_missing_installed_bom_proof_cannot_promote(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            (runtime / 'installed-bom-actions.json').unlink()
            with self.assertRaisesRegex(RuntimeError, 'installed-bom-actions'):
                self.run_finalizer(root, runtime)

    def test_tampered_installed_bom_proof_cannot_promote(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            report = runtime / 'installed-bom-actions.json'
            payload = delivery.load(report); payload['source_commit'] = 'wrong'
            write_json(report, payload)
            with self.assertRaisesRegex(RuntimeError, 'BOM report hash'):
                self.run_finalizer(root, runtime)

    def test_old_bom_pass_without_grouped_exports_cannot_promote(self):
        with TemporaryDirectory() as folder:
            root,runtime=fixture(Path(folder));bom=delivery.load(runtime/'installed-bom-actions.json')
            bom.pop('export_followup')
            with self.assertRaisesRegex(RuntimeError, 'Invalid evidence path'):
                delivery._verify_bom_exports(bom,runtime/'bom-actions',SHA,'c'*64)

    def test_tampered_grouped_output_cannot_promote(self):
        with TemporaryDirectory() as folder:
            root,runtime=fixture(Path(folder));bom=delivery.load(runtime/'installed-bom-actions.json')
            (runtime/'bom-actions/exports/per_part.zip').write_bytes(b'changed')
            with self.assertRaisesRegex(RuntimeError, 'package hash'):
                delivery._verify_bom_exports(bom,runtime/'bom-actions',SHA,'c'*64)

    def test_missing_grouping_cannot_promote_with_rebound_report_hash(self):
        with TemporaryDirectory() as folder:
            root,runtime=fixture(Path(folder));bom=delivery.load(runtime/'installed-bom-actions.json')
            path=runtime/'bom-actions/exports/BOM_EXPORT_EVIDENCE.json';report=delivery.load(path)
            report['packages'].pop();write_json(path,report);bom['export_followup']['sha256']=delivery.digest(path)
            with self.assertRaisesRegex(RuntimeError, 'Eight real export groupings'):
                delivery._verify_bom_exports(bom,runtime/'bom-actions',SHA,'c'*64)

    def test_grouped_report_bound_to_other_binary_cannot_promote(self):
        with TemporaryDirectory() as folder:
            root,runtime=fixture(Path(folder));bom=delivery.load(runtime/'installed-bom-actions.json')
            with self.assertRaisesRegex(RuntimeError, 'source/binary binding'):
                delivery._verify_bom_exports(bom,runtime/'bom-actions',SHA,'wrong')

    def test_review_file_tampering_cannot_promote(self):
        with TemporaryDirectory() as folder:
            root,runtime=fixture(Path(folder));bom=delivery.load(runtime/'installed-bom-actions.json')
            (runtime/'bom-actions/exports/csv/manifest.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'Review export file hash'):
                delivery._verify_bom_exports(bom,runtime/'bom-actions',SHA,'c'*64)

    def test_relative_windows_and_posix_paths_resolve_to_same_file(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            expected = root / 'dpi-175' / 'REPORT.json'
            self.assertEqual(delivery.evidence_path(root, r'dpi-175\REPORT.json'), expected)
            self.assertEqual(delivery.evidence_path(root, 'dpi-175/REPORT.json'), expected)

    def test_absolute_drive_unc_and_traversal_paths_are_rejected(self):
        with TemporaryDirectory() as folder:
            for value in ('../escape', r'..\escape', '/absolute', r'C:\escape',
                          r'C:escape', r'\\server\share\escape', 'dpi/../../escape', ''):
                with self.subTest(value=value), self.assertRaises(RuntimeError):
                    delivery.evidence_path(Path(folder), value)

    def test_non_string_reference_is_rejected(self):
        with TemporaryDirectory() as folder:
            for value in (None, 3, ['dpi', 'REPORT.json']):
                with self.subTest(value=value), self.assertRaises(RuntimeError):
                    delivery.evidence_path(Path(folder), value)


if __name__ == '__main__':
    unittest.main(verbosity=2)
