"""Manifest/path unit tests, NOT native GUI or original-specification evidence."""
from __future__ import annotations
import contextlib
import io
import json
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
            'source_commit': SHA, 'source_dirty': False, 'status': 'PASS',
            'specification_sha256': delivery.SPEC, 'viewer_backend': 'VtkUnitFixture',
            'checks': [{'status': 'PASS'} for _ in range(65)],
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
    write_json(promoted / 'INSTALLER_ACCEPTANCE.json', {
        'status': 'PASS', 'source_commit': SHA, 'source_tree': 'b' * 40,
        'version': 'unit-fixture-not-a-release', 'main_ui_runtimes': bindings,
        'pdf_function_proof': {'matrix_sha256': delivery.digest(promoted / 'PDF_FUNCTION_GAP_MATRIX.json')}})
    return root, runtime


class DeliveryPathTests(unittest.TestCase):
    def run_finalizer(self, root, runtime):
        with patch.object(sys, 'argv', ['finalize', '--root', str(root),
                                       '--runtime-root', str(runtime), '--sha', SHA]), contextlib.redirect_stdout(io.StringIO()):
            return delivery.main()

    def test_windows_manifest_paths_are_read_without_rewriting_signed_inputs(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            before = {p: delivery.digest(p) for p in Path(folder).rglob('*') if p.is_file()}
            self.assertEqual(self.run_finalizer(root, runtime), 0)
            for p, expected in before.items():
                self.assertEqual(delivery.digest(p), expected, str(p))
            payload = delivery.load(root / 'promoted' / 'PDF_RUNTIME_EVIDENCE.json')
            self.assertEqual(len(payload['runtimes']), 8)
            self.assertFalse(payload['original_specification_file_reverified'])
            release = delivery.load(root / 'promoted' / 'RELEASE_MANIFEST.json')
            self.assertEqual(release['full_original_specification_acceptance'], 'UNVERIFIED')

    def test_hash_tampering_still_blocks_promotion(self):
        with TemporaryDirectory() as folder:
            root, runtime = fixture(Path(folder))
            (root / 'dpi' / 'dpi-100' / 'images' / 'unit-fixture.bin').write_bytes(b'tampered')
            with self.assertRaisesRegex(RuntimeError, 'screenshot hash'):
                self.run_finalizer(root, runtime)

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
