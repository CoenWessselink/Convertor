"""Original-input provenance checks; not fake GUI/visual acceptance."""
from pathlib import Path
import json
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.verify_original_pdf_ui_spec import SPEC_ROOT, verify_review


class OriginalInputTests(unittest.TestCase):
    def test_complete_record_and_verbatim_text_verify_with_explicit_scope(self):
        result = verify_review()
        self.assertEqual(len(result['verbatim_text_files_verified']), 3)
        self.assertEqual(result['reference_images_reviewed_before_commit'], 3)
        self.assertFalse(result['original_archive_rehashed_in_this_execution'])
        self.assertFalse(result['application_tests_proven_by_this_record'])

    def test_modified_original_prompt_is_rejected(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / 'input'; shutil.copytree(SPEC_ROOT, target)
            (target / 'CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md').write_text('replacement')
            with self.assertRaisesRegex(ValueError, 'Verbatim'):
                verify_review(target)

    def test_missing_reference_review_is_rejected(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / 'input'; shutil.copytree(SPEC_ROOT, target)
            p = target / 'INPUT_REVIEW.json'; record = json.loads(p.read_text())
            record['reference_comparison'].pop(); p.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'Three visual'):
                verify_review(target)

    def test_wrong_uploaded_archive_is_not_accepted_by_filename(self):
        with TemporaryDirectory() as folder:
            p = Path(folder) / 'CWS_CODEX_PDF_UI_INTEGRATIE_V3_2026-09-06(2).zip'
            p.write_bytes(b'not the original')
            with self.assertRaisesRegex(ValueError, 'does not match original'):
                verify_review(archive=p)


if __name__ == '__main__':
    unittest.main(verbosity=2)
