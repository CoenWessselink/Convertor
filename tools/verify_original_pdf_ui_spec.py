"""Verify the recorded V3 original-input review; optionally rehash its actual ZIP.

A design reference is not application test evidence. CI checks the committed
prompt and review, never claiming it rehashed PNG bytes it does not have.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

SPEC_SHA256 = 'f20b9597ee02eab1c45f06d85ae3d652d03eaeddb68614cc3bbcd15716a7f06e'
SPEC_ROOT = Path(__file__).resolve().parents[1] / 'docs/pdf_ui_v3_original'


def verify_review(root: Path = SPEC_ROOT, archive: Path | None = None) -> dict:
    root = Path(root)
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    digest = lambda data: hashlib.sha256(data).hexdigest()
    review = read(root / 'INPUT_REVIEW.json')
    original = read(root / 'MANIFEST.json')
    def require(ok: bool, message: str) -> None:
        if not ok:
            raise ValueError(message)
    require(review['archive_sha256'] == SPEC_SHA256, 'Original archive hash mismatch')
    require(review['archive_size_bytes'] == 4022148, 'Original archive size mismatch')
    require(review['full_prompt_read'] is True and review['original_images_visually_inspected'] == 3, 'Original input review incomplete')
    expected = {row['path']: row['sha256'] for row in original['files']}
    supplied = {row['path']: row['sha256'] for row in review['files']}
    require(len(expected) == len(supplied) == len(review['files']) == 6 and expected == supplied, 'Original file manifest mismatch')
    pngs = {name for name in expected if name.endswith('.png')}
    require(len(pngs) == 3 and {row['reference'] for row in review['reference_comparison']} == pngs, 'Three visual comparisons required')
    for row in review['reference_comparison']:
        require(bool(row['review']) and bool(row['intentional_differences']) and bool(row['runtime_scenes']), 'Visual comparison missing')
    text_files = []
    for row in review['files']:
        require(row['content_verified_from_uploaded_archive'] is True, 'Missing pre-commit input verification')
        if row['path'].endswith('.md'):
            p = root / row['path']
            require(digest(p.read_bytes()) == expected[row['path']], 'Verbatim prompt/reference text changed: ' + row['path'])
            text_files.append(row['path'])
    archive_checked_now = False
    if archive is not None:
        raw = Path(archive).read_bytes()
        require(digest(raw) == SPEC_SHA256, 'Supplied archive does not match original')
        with zipfile.ZipFile(archive) as z:
            for name, expected_hash in expected.items():
                require(digest(z.read('CODEX_PDF_UI_INTEGRATIE_V3/' + name)) == expected_hash, 'Original archive member mismatch: ' + name)
        archive_checked_now = True
    return {
        'schema': 'cws-v3-original-input-verification-1.0', 'archive_sha256': SPEC_SHA256,
        'archive_byte_verification': review['archive_byte_verification'],
        'original_archive_rehashed_in_this_execution': archive_checked_now,
        'verbatim_text_files_verified': text_files,
        'reference_images_reviewed_before_commit': 3,
        'review_record_sha256': digest((root / 'INPUT_REVIEW.json').read_bytes()),
        'reference_comparison': review['reference_comparison'],
        'scope': review['scope'], 'application_tests_proven_by_this_record': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify_review(archive=args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'input_review_verified': True, 'original_archive_rehashed_in_this_execution': result['original_archive_rehashed_in_this_execution']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
