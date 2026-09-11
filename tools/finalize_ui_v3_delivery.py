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
    'Native batch retains complete assembly document',
    'Native batch retains existing workspace and viewer',
} | {
    name + ' ' + mode
    for mode in ('part_subset', 'parts', 'assembly')
    for name in ('Native batch completed', 'Native batch exact object scope',
                 'Native batch manifest bytes bound', 'Native batch no new revision release',
                 'Native batch contains every selected drawing', 'Native combined PDF parsed',
                 'Native combined PDF has real vectors', 'Native batch left no temporary files')
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

BOM_REVIEW_ACTIONS = ("export.xlsx", "export.csv", "export.json", "export.review")
BOM_REVIEW_CHECKS = {
    *(action + " records its own completed review action" for action in BOM_REVIEW_ACTIONS),
    *(action + " review has exact A scope and no production permission" for action in BOM_REVIEW_ACTIONS),
    *(action + " produces only requested representations" for action in BOM_REVIEW_ACTIONS),
    "Cancelled review creates no files and is not passed",
    "Changed project during review dialog creates no files",
    "Empty explicit review selection does not open output or widen scope",
}


def _verify_bom_review_files(report_path: Path, report: dict) -> None:
    """Verify real installed outputs as well as assertion names; no stub pass."""
    records = report.get("review_exports", [])
    require(len(records) == 4 and {r.get("action_id") for r in records} == set(BOM_REVIEW_ACTIONS),
            "Four installed BOM review actions required")
    passed = {c.get("name") for c in report.get("checks", []) if c.get("status") == "PASS"}
    require(BOM_REVIEW_CHECKS.issubset(passed), "Installed BOM review action checks missing")
    expected = {"export.xlsx": {".xlsx"}, "export.csv": {".csv"}, "export.json": {".json"},
                "export.review": {".xlsx", ".csv", ".json", ".pdf", ".zip"}}
    for record in records:
        action = record["action_id"]
        path = evidence_path(report_path.parent / "bom-actions", record.get("manifest"))
        require(path.is_file() and digest(path) == record.get("manifest_sha256"), "BOM review manifest hash")
        manifest = load(path)
        require(manifest.get("action_id") == action and manifest.get("review_only") is True
                and manifest.get("production_release_allowed") is False
                and manifest.get("machine_transfer_allowed") is False, "BOM review intent or permissions")
        require(manifest.get("scope", {}).get("entity_ids") == ["A"], "BOM review selection widened")
        files = manifest.get("files", {})
        require(bool(files) and {Path(name).suffix for name in files if name not in {"manifest.json", "validation.json", "SHA256SUMS.txt"}} == expected[action], "BOM review format mismatch")
        for name, binding in files.items():
            artifact = evidence_path(path.parent, name)
            require(artifact.is_file() and artifact.stat().st_size == binding.get("bytes")
                    and digest(artifact) == binding.get("sha256"), "BOM review artifact hash: " + name)


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

def _verify_drawing_batches(data: dict, base: Path) -> dict:
    """Check the bytes of every batch built inside this exact native process."""
    binding = data.get('drawing_batches', {})
    require(binding.get('status') == 'PASS', 'Native drawing batch result missing')
    parts = binding.get('expected_part_ids', [])
    require(len(parts) == len(set(parts)) == 2 and all(isinstance(x, str) and x for x in parts),
            'Native drawing batch fixture scope')
    expected = {'part_subset': sorted(parts)[:1], 'parts': sorted(parts), 'assembly': ['UIV3-A1']}
    runs = binding.get('runs', [])
    require(len(runs) == 3 and {r.get('mode') for r in runs} == set(expected), 'Three native drawing batches required')
    for row in runs:
        ids = expected[row['mode']]
        require(row.get('entity_ids') == ids, 'Native drawing batch selected identity')
        path = evidence_path(base, row.get('manifest'))
        require(path.is_file() and digest(path) == row.get('manifest_sha256'), 'Drawing batch manifest hash')
        manifest = load(path)
        require(manifest.get('schema') == 'cws-drawing-review-batch-1'
                and manifest.get('status') == 'verified_review'
                and manifest.get('production_release_granted') is False, 'Drawing batch review-only authority')
        docs = manifest.get('documents', [])
        require(manifest.get('entity_ids') == ids and [d.get('entity_id') for d in docs] == ids,
                'Drawing batch exact documents')
        files = manifest.get('files', {})
        actual = {p.relative_to(path.parent).as_posix() for p in path.parent.rglob('*') if p.is_file()}
        require(actual == set(files) | {'BATCH_MANIFEST.json'}, 'Drawing batch file inventory')
        require('Tekeningen.pdf' in files and files['Tekeningen.pdf'] == row.get('pdf_sha256'),
                'Drawing batch combined file identity')
        for name, expected_hash in files.items():
            require(digest(evidence_path(path.parent, name)) == expected_hash, 'Drawing batch output hash')
        next_page = 1
        for doc in docs:
            require(doc.get('sha256') == files.get(doc.get('file')) and doc.get('first_page') == next_page
                    and isinstance(doc.get('page_count'), int) and doc['page_count'] > 0,
                    'Drawing batch missing/overlapping document pages')
            next_page += doc['page_count']
        require(manifest.get('page_count') == next_page - 1, 'Drawing batch total pages')
        if row['mode'] == 'assembly':
            require(docs[0].get('document_type') == 'assembly', 'Batch assembly substituted by part')
    return {'status': 'PASS', 'modes': sorted(expected), 'production_release_granted': False}


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
        drawing_batches = _verify_drawing_batches(data, path.parent)
        child_path = evidence_path(path.parent, data['second_process']['report']); child = load(child_path)
        require(digest(child_path) == data['second_process']['sha256'], 'Independent reopen hash: '+label)
        require(child['pid'] != data['pid'] and child['status'] == 'PASS' and child['executable_sha256'] == data['executable_sha256'], 'Independent reopen: '+label)
        images = []
        for image in data['screenshots']:
            require(digest(evidence_path(path.parent, image['file'])) == image['sha256'], 'Native screenshot hash: '+label)
            require(image['missing_glyphs'] == 0, 'Unrendered glyphs: '+label)
            images.append({'file':str(evidence_path(path.parent, image['file']).relative_to(runtime if not label.startswith('source-') else root)), 'sha256':image['sha256']})
        records[label] = {'status':'PASS','source_commit':sha,'checks':len(data['checks']),'pid':data['pid'], 'second_pid':child['pid'],
                          'executable_sha256':data['executable_sha256'],'viewer_backend':data['viewer_backend'],'screenshots':images,'drawing_batches':drawing_batches}
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
    _verify_bom_review_files(bom_path, bom)
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
