"""Fail closed on the final source, native runtime and V3 evidence bindings."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import zipfile
import shutil
from tools.verify_original_pdf_ui_spec import verify_review, SPEC_ROOT

SPEC = 'f20b9597ee02eab1c45f06d85ae3d652d03eaeddb68614cc3bbcd15716a7f06e'
RELEASE_EVIDENCE_CHECKS = {
    'Release recomputes missing cached linter evidence',
    'Fresh actual geometry linter still blocks review release',
    'Blocked release writes no release audit',
    'Status line has full text access without vertical clipping',
    'Actual BOM action retains canonical part ID',
    'Actual BOM action has explicit machine.validate intent',
    'Machine advice cannot grant release or assignment',
    'Machine advice visible in existing main-window BOM',
    'Existing canonical workspace retained after BOM action',
    'Actual grouped Export Center visible in main window',
    'Main-window grouped preflight preserves exact canonical ID',
    'Grouped export cannot promote unapproved imported source',
    'Blocked grouped export starts no production job',
} | {
    f'{name} at {width} logical pixels'
    for width in (1280, 1440, 1920)
    for name in ('Primary navigation fits', 'Global actions do not obscure tabs',
                 'Primary navigation clickable', 'Context toolbar stays inside workspace',
                 'Primary navigation keyboard works', 'Workspace and viewer preserved',
                 'PDF menu remains unobscured', 'Drawing controls fit')
}

def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))

def require(condition: bool, reason: str) -> None:
    if not condition: raise RuntimeError(reason)

def evidence_path(root: Path, reference: object) -> Path:
    """Read portable artifact references without rewriting any signed evidence."""
    require(isinstance(reference, str) and bool(reference), 'Invalid evidence path')
    normalized = reference.replace('\\', '/')
    relative = PurePosixPath(normalized)
    require(not relative.is_absolute() and not PureWindowsPath(reference).drive
            and '..' not in relative.parts, 'Unsafe evidence path: ' + reference)
    candidate = root.joinpath(*relative.parts)
    require(candidate.resolve().is_relative_to(root.resolve()), 'Evidence path leaves artifact root')
    return candidate

def only(root: Path, name: str) -> Path:
    values = list(root.rglob(name))
    require(len(values) == 1, 'Expected exactly one ' + name)
    return values[0]

def _verify_bom_exports(bom: dict, base: Path, sha: str, executable_sha256: str) -> dict:
    """Require newly executed, byte-bound positive exports; not only UI navigation."""
    binding = bom.get('export_followup', {})
    path = evidence_path(base, binding.get('report'))
    require(path.is_file() and digest(path) == binding.get('sha256'), 'Grouped BOM report hash')
    report = load(path)
    require(report.get('status') == 'PASS' and report.get('source_commit') == sha
            and report.get('source_dirty') is False and report.get('frozen') is True
            and report.get('executable_sha256') == executable_sha256, 'Grouped BOM source/binary binding')
    require(len(report.get('checks', [])) >= 130 and all(c.get('status') == 'PASS' for c in report['checks'])
            and report.get('machine_transfer_allowed') is False, 'Grouped BOM controls')
    expected = {'per_part','part_mark','assembly','assembly_mark','phase','batch','machine','combined'}
    require(len(report.get('packages', [])) == 8 and {p.get('grouping') for p in report['packages']} == expected,
            'Eight real export groupings required')
    for record in report['packages']:
        package = evidence_path(path.parent, record['file'])
        require(package.is_file() and digest(package) == record['sha256'], 'Grouped BOM package hash')
        with zipfile.ZipFile(package) as archive:
            manifest = json.loads(archive.read('manifest.json'))
            require(manifest['manifest_sha256'] == record['manifest_sha256']
                    and manifest['grouping'] == record['grouping']
                    and manifest['machine_transfer_allowed'] is False, 'Grouped BOM package identity')
            require(manifest['selected_part_ids'] == ['EXPORT-A','EXPORT-B']
                    and sorted(p for g in manifest['groups'] for p in g['part_ids']) == ['EXPORT-A','EXPORT-B']
                    and set(manifest['requested_formats']) == {'step','nc1','production_pdf'}, 'Grouped BOM exact scope/formats')
            for group in manifest['groups']:
                require(hashlib.sha256(archive.read(group['file'])).hexdigest() == group['sha256'], 'Grouped BOM child package hash')
    require(len(report.get('review_exports', [])) == 3
            and {item['format'] for item in report['review_exports']} == {'xlsx','csv','json'}, 'Three review formats required')
    for review in report['review_exports']:
        require(bool(review['files']), 'Review export files missing')
        for name, expected_hash in review['files'].items():
            require(digest(evidence_path(path.parent, name)) == expected_hash, 'Review export file hash')
        manifests = [name for name in review['files'] if PurePosixPath(name).name == 'manifest.json']
        require(len(manifests) == 1, 'Review manifest missing')
        manifest = load(evidence_path(path.parent, manifests[0]))
        require(manifest['selected_formats'] == [review['format']]
                and manifest['scope']['entity_ids'] == ['EXPORT-A'], 'Review format/exact part selection')
    require(len(report.get('screenshots', {})) >= 3, 'Grouped BOM real screenshots missing')
    for image, expected_hash in report['screenshots'].items():
        require(digest(evidence_path(path.parent, image)) == expected_hash, 'Grouped BOM screenshot hash')
    return {'status':'PASS','report_sha256':digest(path),'checks':len(report['checks']),
            'real_groupings':sorted(expected),'review_formats':['csv','json','xlsx']}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--sha', required=True)
    args = parser.parse_args()
    root, runtime, sha = args.root.resolve(), args.runtime_root.resolve(), args.sha
    out = root / 'promoted'
    original_review = verify_review()
    acceptance = load(out / 'INSTALLER_ACCEPTANCE.json')
    require(acceptance['status'] == 'PASS' and acceptance['source_commit'] == sha, 'Installer binding')
    phase = load(only(root, 'PHASE_3_SOURCE_TEST_EVIDENCE.json'))
    soak = load(only(root, 'PHASE_3_SOAK_EVIDENCE.json'))
    require(phase.get('status') == 'GREEN' and len(phase['coverage']) == 12 and all(phase['coverage'].values()), 'Phase 3 incomplete')
    require(phase.get('source_revision') == sha and phase.get('source_unchanged') is True and phase.get('reused_evidence') is False, 'Phase 3 stale source')
    require(soak.get('status') == 'passed' and soak.get('elapsed_seconds', 0) >= 600 and all(soak['checks'].values()), 'Full 600-second soak missing')
    pdf12 = load(only(root, 'pdf12-source.json'))
    require(pdf12['commit'] == sha and pdf12['status'] == 'PASS' and pdf12['counts']['tests'] >= 23 and pdf12['counts']['skipped'] == pdf12['counts']['failed'] == 0, 'Mandatory PDF12 V2 tests')
    proof = load(out / 'PDF_FUNCTION_GAP_MATRIX.json')
    require(proof['commit'] == sha and proof['status'] == 'PASS', 'PDF function source')
    require({row['requirement_id'] for row in proof['items']} == {f'PDF-{i:02d}' for i in range(1,44)}, '43 requirement identities')
    require(len(proof['items']) == 43 and all(row['status'] == 'PASS' and row.get('executed_tests') for row in proof['items']), '43 function execution missing')
    require(proof['counts']['PASS'] == sum(row['status'] == 'PASS' for row in proof['items']), 'Function count inconsistent')
    require(digest(out / 'PDF_FUNCTION_GAP_MATRIX.json') == acceptance['pdf_function_proof']['matrix_sha256'], 'Function manifest hash')
    records = {}
    source_dpi_path = only(root, 'PDF_UI_V3_DPI_EVIDENCE.json')
    source_dpi = load(source_dpi_path)
    require(source_dpi['status'] == 'PASS' and source_dpi['source_commit'] == sha, 'DPI source binding')
    require({r['scale'] for r in source_dpi['runs']} == {100,125,150,175,200}, 'Five DPI scales missing')
    locations = [('source-' + str(r['scale']), evidence_path(source_dpi_path.parent, r['report']), r['sha256']) for r in source_dpi['runs']]
    for label, binding in acceptance['main_ui_runtimes'].items():
        directory = only(runtime, label + '-main-ui')
        locations.append((label, directory / 'dpi-100/REPORT.json', binding['report_sha256']))
    require(set(acceptance['main_ui_runtimes']) == {'onefolder','portable','installed'}, 'Three packaged runtimes required')
    for label, path, expected in locations:
        require(digest(path) == expected, 'Native report hash: ' + label)
        data = load(path)
        require(data['source_commit'] == sha and data['source_dirty'] is False and data['status'] == 'PASS', 'Native source: '+label)
        require(data['specification_sha256'] == SPEC and 'Headless' not in data['viewer_backend'], 'Native viewer/spec binding: '+label)
        require(len(data['checks']) >= 65 and all(c['status'] == 'PASS' for c in data['checks']), 'Native controls incomplete: '+label)
        require(RELEASE_EVIDENCE_CHECKS.issubset({c.get('name') for c in data['checks']}), 'Native release-evidence regression missing: '+label)
        child_path = evidence_path(path.parent, data['second_process']['report']); child = load(child_path)
        require(digest(child_path) == data['second_process']['sha256'], 'Independent reopen hash: '+label)
        require(child['pid'] != data['pid'] and child['status'] == 'PASS' and child['executable_sha256'] == data['executable_sha256'], 'Independent reopen: '+label)
        images = []
        for image in data['screenshots']:
            require(digest(evidence_path(path.parent, image['file'])) == image['sha256'], 'Native screenshot hash: '+label)
            require(image['missing_glyphs'] == 0, 'Unrendered glyphs: '+label)
            images.append({'file':str(evidence_path(path.parent, image['file']).relative_to(runtime if not label.startswith('source-') else root)), 'sha256':image['sha256']})
        records[label] = {'status':'PASS','source_commit':sha,'checks':len(data['checks']),'pid':data['pid'], 'second_pid':child['pid'],
                          'executable_sha256':data['executable_sha256'],'viewer_backend':data['viewer_backend'],'screenshots':images}
    require(len({records[label]['executable_sha256'] for label in ('onefolder','portable','installed')}) == 1, 'Different packaged binaries')
    for label in ('dist','portable','installed'):
        legacy = load(only(runtime, label + '-packaged-runtime.json'))
        require(legacy['status'] == 'passed' and legacy['python_on_child_path'] is False and legacy['pdf12_interactive_dimensioning']['passed'] == 35, 'PDF12 35 native controls: '+label)
    bom_path = only(runtime, 'installed-bom-actions.json')
    bom = load(bom_path)
    binding = acceptance.get('installed_bom_actions', {})
    require(digest(bom_path) == binding.get('report_sha256'), 'Installed BOM report hash')
    require(bom.get('source_commit') == sha and bom.get('source_dirty') is False and bom.get('frozen') is True
            and bom.get('status') == 'PASS' and bom.get('executable_sha256') == records['installed']['executable_sha256'], 'Installed BOM source/binary binding')
    require(len(bom.get('checks', [])) >= 40 and all(c.get('status') == 'PASS' for c in bom['checks'])
            and bom.get('machine_transfer_allowed') is False and binding.get('python_on_child_path') is False, 'Installed BOM controls')
    for image, expected in bom.get('screenshots', {}).items():
        require(digest(evidence_path(bom_path.parent / 'bom-actions', image)) == expected, 'Installed BOM screenshot hash')
    grouped_bom = _verify_bom_exports(bom, bom_path.parent/'bom-actions', sha, records['installed']['executable_sha256'])
    original_review['source_commit'] = sha
    (out / 'ORIGINAL_SPECIFICATION_REVIEW.json').write_text(json.dumps(original_review, ensure_ascii=False, indent=2), encoding='utf-8')
    for name in ('CODEX_INTEGRATIEPROMPT_PDF_UI_V3.md', 'REFERENCE_IMAGES.md'):
        shutil.copyfile(SPEC_ROOT / name, out / ('ORIGINAL_' + name))
    for name in ('PDF_UI_V3_SPEC_REVIEW_20260911.md', 'PDF_UI_V3_QUICK_GUIDE.md', 'PDF_UI_V3_NAVIGATION_REPAIR_20260911.md'):
        shutil.copyfile(SPEC_ROOT.parent / name, out / name)
    runtime_manifest = {'schema':'cws-pdf-runtime-evidence-3.0','source_commit':sha,'specification_sha256':SPEC,'status':'PASS',
                        'original_specification_file_reverified':True,
                        'original_input_verification_scope':'Archive and PNGs verified before commit; CI verifies committed original text and review record',
                        'original_archive_rehashed_in_ci':original_review['original_archive_rehashed_in_this_execution'],
                        'full_original_specification_acceptance':'SOFTWARE_BETA_WITH_RECORDED_VISUAL_REVIEW', 'runtimes':records,
                        'installed_bom_actions': {'status': 'PASS', 'checks': len(bom['checks']), 'report_sha256': digest(bom_path), 'exports':grouped_bom},
                        'pdf12_native_controls_per_packaged_runtime':35,'five_dpi_checked':[100,125,150,175,200], 'phase3_soak_seconds':soak['elapsed_seconds']}
    (out / 'PDF_RUNTIME_EVIDENCE.json').write_text(json.dumps(runtime_manifest, indent=2), encoding='utf-8')
    manifest = {'schema':'cws-native-ui-v3-release-manifest-1.0','source_commit':sha,'source_tree':acceptance['source_tree'], 'status':'PASS',
                'version':acceptance['version'],'original_specification_sha256':SPEC,'pixel_identical_reference_claimed':False,
                'original_specification_file_reverified':True,
                        'original_input_verification_scope':'Archive and PNGs verified before commit; CI verifies committed original text and review record',
                        'original_archive_rehashed_in_ci':original_review['original_archive_rehashed_in_this_execution'],
                        'full_original_specification_acceptance':'SOFTWARE_BETA_WITH_RECORDED_VISUAL_REVIEW',
                'qualification':'Tested software beta; no machine authorization, signature or target-hardware qualification',
                'files':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file() and p.name not in {'RELEASE_MANIFEST.json','SHA256SUMS.txt'}}}
    (out / 'RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=2),encoding='utf-8')
    (out / 'SHA256SUMS.txt').write_text('\n'.join(digest(p)+'  '+p.name for p in sorted(out.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.txt')+'\n',encoding='ascii')
    print(json.dumps({'status':'PASS','source_commit':sha,'native_runtime_groups':len(records),'requirements':len(proof['items'])}))
    return 0
if __name__ == '__main__':raise SystemExit(main())
