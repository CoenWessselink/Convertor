"""Build and smoke-test a commit-bound Windows installer, without machine release."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build' / 'installer-evidence'
RELEASE = ROOT / 'release' / 'installer'
STAGING = ROOT / 'build' / 'installer-smoke-runtime'
DIST = ROOT / 'dist' / 'CWS_Convertor'


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def git(*args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main() -> int:
    if sys.platform != 'win32':
        raise RuntimeError('The installer must be built and tested on Windows')
    OUT.mkdir(parents=True, exist_ok=True)
    RELEASE.mkdir(parents=True, exist_ok=True)
    sha = git('rev-parse', 'HEAD')
    if sha != os.environ.get('GITHUB_SHA') or git('status', '--porcelain=v1', '--untracked-files=no'):
        raise RuntimeError('Expected exact, unchanged GitHub source checkout')
    sys.path.insert(0, str(ROOT))
    from cws_convertor.product import APP_VERSION
    report = {'schema': 'cws-tested-installer-1.0', 'source_commit': sha,
              'source_tree': git('rev-parse', 'HEAD^{tree}'), 'version': APP_VERSION,
              'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'RUNNING', 'steps': [], 'full_product_release_approved': False,
              'scope': 'Windows x64 beta installer; hardware and machine qualification remain separate',
              'machine_observed_by_cws': False, 'direct_machine_transfer': False}
    manifest = OUT / 'INSTALLER_ACCEPTANCE.json'
    write(manifest, report)

    def run(name: str, args: list[str], timeout: int = 900, *, env=None) -> None:
        tick = time.monotonic()
        record = {'name': name, 'command': args, 'status': 'RUNNING'}
        report['steps'].append(record)
        write(manifest, report)
        print('RUN', name, flush=True)
        try:
            with (OUT / (name + '.log')).open('w', encoding='utf-8') as stream:
                done = subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                      timeout=timeout, check=False, env=env)
            record['returncode'] = done.returncode
            if done.returncode:
                raise RuntimeError(name + ': nonzero exit code ' + str(done.returncode))
            record['status'] = 'PASS'
        except Exception as exc:
            record.update(status='FAIL', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            record['duration_seconds'] = round(time.monotonic() - tick, 3)
            write(manifest, report)
            print(record['status'], name, flush=True)

    def smoke(label: str, directory: Path) -> None:
        run(label, [sys.executable, str(ROOT / 'tests/packaged_runtime_smoke.py'),
                    '--runtime-dir', str(directory), '--label', label,
                    '--result-dir', str(OUT), '--pdf12-evidence'], 1800)
        result = json.loads((OUT / (label + '-packaged-runtime.json')).read_text(encoding='utf-8'))
        if result.get('status') != 'passed' or result.get('python_on_child_path') is not False:
            raise RuntimeError(label + ': incomplete self-contained runtime proof')

    def main_ui_proof(label: str, directory: Path) -> None:
        run(label + '_main_ui', [sys.executable, str(ROOT / 'tools/run_pdf_ui_v3_acceptance.py'),
            '--runtime-dir', str(directory), '--runtime', label,
            '--output', str(OUT / (label + '-main-ui')), '--scales', '100'], 900)
        dpi = json.loads((OUT / (label + '-main-ui/PDF_UI_V3_DPI_EVIDENCE.json')).read_text(encoding='utf-8'))
        evidence = OUT / (label + '-main-ui/dpi-100/REPORT.json')
        payload = json.loads(evidence.read_text(encoding='utf-8'))
        if (dpi.get('status') != 'PASS' or payload.get('status') != 'PASS'
                or payload.get('source_commit') != sha or payload.get('source_dirty') is not False
                or payload.get('frozen') is not True
                or payload.get('executable_sha256') != binding['runtime_files']['CWS_Convertor.exe']
                or len(payload.get('checks', [])) < 65 or len(payload.get('screenshots', [])) < 6
                or payload.get('pid') == payload.get('second_process', {}).get('pid')
                or any(c.get('status') != 'PASS' for c in payload['checks'])):
            raise RuntimeError(label + ': incomplete main-window/second-process proof')
        for image in payload['screenshots']:
            if digest(evidence.parent / image['file']) != image['sha256']:
                raise RuntimeError(label + ': main-window image hash mismatch')
        report.setdefault('main_ui_runtimes', {})[label] = {
            'status': 'PASS', 'source_commit': sha, 'executable_sha256': payload['executable_sha256'],
            'checks': len(payload['checks']), 'pid': payload['pid'],
            'second_pid': payload['second_process']['pid'], 'report': str(evidence.relative_to(OUT)),
            'report_sha256': digest(evidence), 'python_on_child_path': False}
        write(manifest, report)

    try:
        run('pyinstaller', [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', 'CWS_Convertor.spec'], 3600)
        for name in ('CWS_Convertor.exe', 'CWS_Convertor_CLI.exe'):
            if not (DIST / name).is_file():
                raise RuntimeError('Missing executable: ' + name)
        binding = {'source_commit': sha, 'source_tree': report['source_tree'], 'version': APP_VERSION,
                   'runtime_files': {p.name: digest(p) for p in DIST.glob('*.exe')},
                   'generated_at_utc': report['generated_at_utc']}
        write(DIST / 'BUILD_SOURCE.json', binding)
        smoke('dist', DIST)
        main_ui_proof('onefolder', DIST)
        portable_name = f'CWS_Convertor_Portable_{APP_VERSION}_{sha[:7]}_x64.zip'
        portable = RELEASE / portable_name
        with zipfile.ZipFile(portable, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(DIST.rglob('*')):
                if path.is_file():
                    archive.write(path, Path('CWS_Convertor') / path.relative_to(DIST))
        portable_root = ROOT / 'build' / 'fresh-portable-runtime'
        if portable_root.exists():
            raise RuntimeError('Portable acceptance requires a genuinely absent target')
        with zipfile.ZipFile(portable) as archive:
            archive.extractall(portable_root)
        portable_runtime = portable_root / 'CWS_Convertor'
        if json.loads((portable_runtime / 'BUILD_SOURCE.json').read_text()) != binding:
            raise RuntimeError('Portable source binding differs')
        if any(digest(portable_runtime / name) != expected for name, expected in binding['runtime_files'].items()):
            raise RuntimeError('Portable executable hash differs')
        smoke('portable', portable_runtime)
        main_ui_proof('portable', portable_runtime)
        report['portable'] = {'file': portable_name, 'sha256': digest(portable), 'size_bytes': portable.stat().st_size,
                              'fresh_extract_test': 'PASS', 'source_commit': sha}
        compiler = next((p for p in [
            Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Inno Setup 6/ISCC.exe',
            Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Inno Setup 6/ISCC.exe',
            Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Inno Setup 6/ISCC.exe',
        ] if p.is_file()), None)
        if compiler is None:
            raise RuntimeError('Inno Setup compiler is unavailable')
        run('inno_setup', [str(compiler), '/DCommit7=' + sha[:7], str(ROOT / 'installer/CWS_Convertor.iss')], 1800)
        name = f'CWS_Convertor_Setup_{APP_VERSION}_{sha[:7]}_x64.exe'
        installer = ROOT / 'dist_installer' / name
        if not installer.is_file():
            raise RuntimeError('Installer output is missing')
        if STAGING.exists():
            raise RuntimeError('Fresh installation test requires an absent target directory')
        run('install', [str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
                        '/CURRENTUSER', '/TASKS=fileassoc', '/DIR=' + str(STAGING),
                        '/LOG=' + str(OUT / 'install-inno.log')])
        for executable, expected in binding['runtime_files'].items():
            if digest(STAGING / executable) != expected:
                raise RuntimeError('Installed binary hash differs: ' + executable)
        if json.loads((STAGING / 'BUILD_SOURCE.json').read_text()) != binding:
            raise RuntimeError('Installed source binding differs')
        smoke('installed', STAGING)
        main_ui_proof('installed', STAGING)
        # Exercise all twelve directed NC1/STEP/IFC/PDF routes in the
        # installed executable, with no Python visible to child processes.
        matrix_path = OUT / 'installed-conversion-matrix.json'
        run('installed_conversion_matrix', [
            sys.executable, str(ROOT / 'tests/conversion_one_phase_packaged_smoke.py'),
            '--runtime-dir', str(STAGING), '--output', str(matrix_path),
            '--expected-sha', sha,
        ], 1800)
        matrix = json.loads(matrix_path.read_text(encoding='utf-8'))
        expected_routes = {f'{a}-{b}' for a in ('nc1', 'step', 'ifc', 'pdf')
                           for b in ('nc1', 'step', 'ifc', 'pdf') if a != b}
        if (matrix.get('status') != 'PASS' or matrix.get('checkout_sha') != sha
                or matrix.get('python_on_child_path') is not False
                or matrix.get('executable_sha256') != binding['runtime_files']['CWS_Convertor.exe']
                or {r.get('direction') for r in matrix.get('routes', [])} != expected_routes
                or matrix.get('route_count') != 12):
            raise RuntimeError('Installed conversion matrix lacks exact source/binary/route proof')
        # Run the actual plate controls from the installed binary, not source
        # imports or a reconstructed UI image. No external Python is on PATH.
        plate_path = OUT / 'installed-plate-integration.json'
        clean_env = os.environ.copy()
        system_root = Path(clean_env.get('SystemRoot', r'C:\Windows'))
        clean_env['PATH'] = os.pathsep.join(str(p) for p in (system_root / 'System32', system_root, system_root / 'System32/Wbem'))
        clean_env.pop('PYTHONPATH', None); clean_env.pop('PYTHONHOME', None)
        if shutil.which('python', path=clean_env['PATH']) or shutil.which('pip', path=clean_env['PATH']):
            raise RuntimeError('Installed test environment still exposes an external Python')
        run('installed_plate_integration', [str(STAGING / 'CWS_Convertor.exe'),
            '--plate-integration-evidence', '--evidence-dir', str(OUT / 'plate-integration'),
            '--report', str(plate_path)], 300, env=clean_env)
        plate = json.loads(plate_path.read_text(encoding='utf-8'))
        if (plate.get('status') != 'PASS' or plate.get('frozen') is not True
                or plate.get('source_commit') != sha
                or plate.get('executable_sha256') != binding['runtime_files']['CWS_Convertor.exe']
                or len(plate.get('checks', [])) < 20
                or any(c.get('status') != 'PASS' for c in plate['checks'])
                or plate.get('production_release_allowed') is not False):
            raise RuntimeError('Installed plate evidence lacks exact source/binary/function proof')
        report['installed_plate_integration'] = {'status': 'PASS', 'checks': len(plate['checks']),
                                               'report': plate_path.name, 'python_on_child_path': False}
        bom_path = OUT / 'installed-bom-actions.json'
        run('installed_bom_actions', [str(STAGING / 'CWS_Convertor.exe'),
            '--bom-action-evidence', '--evidence-dir', str(OUT / 'bom-actions'),
            '--report', str(bom_path)], 300, env=clean_env)
        bom = json.loads(bom_path.read_text(encoding='utf-8'))
        if (bom.get('status') != 'PASS' or bom.get('frozen') is not True
                or bom.get('source_commit') != sha or bom.get('source_dirty') is not False
                or bom.get('executable_sha256') != binding['runtime_files']['CWS_Convertor.exe']
                or len(bom.get('checks', [])) < 40 or any(c.get('status') != 'PASS' for c in bom['checks'])
                or bom.get('machine_transfer_allowed') is not False):
            raise RuntimeError('Installed BOM action proof lacks exact source/binary/selection binding')
        from tools.finalize_ui_v3_delivery import _verify_bom_exports, _verify_bom_review_files
        _verify_bom_review_files(bom_path, bom)
        grouped_bom = _verify_bom_exports(bom, OUT/'bom-actions', sha, binding['runtime_files']['CWS_Convertor.exe'])
        report['installed_bom_actions'] = {'exports': grouped_bom, 'status': 'PASS', 'checks': len(bom['checks']),
            'source_commit': sha, 'executable_sha256': bom['executable_sha256'],
            'report': bom_path.name, 'report_sha256': digest(bom_path), 'python_on_child_path': False}
        native_path = OUT / 'installed-recognition-integration.json'
        run('installed_recognition_integration', [str(STAGING / 'CWS_Convertor.exe'),
            '--recognition-integration-evidence', '--evidence-dir', str(OUT / 'recognition-integration'),
            '--report', str(native_path)], 300, env=clean_env)
        native = json.loads(native_path.read_text(encoding='utf-8'))
        if (native.get('status') != 'PASS' or native.get('frozen') is not True
                or native.get('source_commit') != sha
                or native.get('executable_sha256') != binding['runtime_files']['CWS_Convertor.exe']
                or len(native.get('checks', [])) < 50
                or any(c.get('status') != 'PASS' for c in native['checks'])
                or native.get('machine_transfer_allowed') is not False):
            raise RuntimeError('Installed recognition proof lacks exact source/binary/safety binding')
        report['installed_recognition_integration'] = {'status': 'PASS', 'checks': len(native['checks']),
            'source_commit': sha, 'executable_sha256': native['executable_sha256'],
            'report': native_path.name, 'python_on_child_path': False}
        v3_path = OUT / 'installed-pdf-v3-integration.json'
        run('installed_pdf_v3_integration', [str(STAGING / 'CWS_Convertor.exe'),
            '--pdf-v3-evidence', '--evidence-dir', str(OUT / 'pdf-v3-integration'),
            '--report', str(v3_path)], 300, env=clean_env)
        v3 = json.loads(v3_path.read_text(encoding='utf-8'))
        if (v3.get('status') != 'PASS' or v3.get('frozen') is not True
                or v3.get('source_commit') != sha or v3.get('source_dirty') is not False
                or v3.get('executable_sha256') != binding['runtime_files']['CWS_Convertor.exe']
                or len(v3.get('checks', [])) < 51 or len(v3.get('screenshots', [])) < 4
                or len(v3.get('pdf_renders', [])) < 1
                or any(c.get('status') != 'PASS' for c in v3['checks'])
                or v3.get('production_release_allowed') is not False):
            raise RuntimeError('Installed V3 proof lacks exact source/binary/interaction binding')
        for image in v3['screenshots'] + v3['pdf_renders']:
            image_path = OUT / 'pdf-v3-integration' / image['file']
            if digest(image_path) != image['sha256']:
                raise RuntimeError('Installed V3 screenshot hash mismatch')
        report['installed_pdf_v3_integration'] = {'status': 'PASS', 'checks': len(v3['checks']),
            'source_commit': sha, 'executable_sha256': v3['executable_sha256'],
            'report': v3_path.name, 'python_on_child_path': False, 'pdf_renders': len(v3['pdf_renders']),
            'external_v3_specification_verified': v3['external_v3_specification_verified']}
        report['installed_conversion_routes_passed'] = 12
        report['conversion_matrix_report'] = matrix_path.name
        run('associations', [sys.executable, str(ROOT / 'tests/windows_installer_association_smoke.py'),
                             '--runtime-dir', str(STAGING)], 180)
        user_file = STAGING / 'user-created-project-preservation.txt'
        user_file.write_text('Keep user-created files during uninstall', encoding='utf-8')
        user_digest = digest(user_file)
        # Same-version repair/reinstall is not silently counted as an upgrade
        # from every historical version or a Windows 11 acceptance test.
        run('repair_reinstall', [str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
                                '/CURRENTUSER', '/TASKS=fileassoc', '/DIR=' + str(STAGING),
                                '/LOG=' + str(OUT / 'repair-inno.log')])
        if digest(user_file) != user_digest or any(digest(STAGING / key) != value for key, value in binding['runtime_files'].items()):
            raise RuntimeError('Repair changed user data or delivered binary identities')
        smoke('reinstalled', STAGING)
        report['same_version_reinstall_test'] = 'PASS'
        run('uninstall', [str(STAGING / 'unins000.exe'), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                          '/LOG=' + str(OUT / 'uninstall-inno.log')])
        deadline = time.monotonic() + 90.0
        while True:
            leftovers = [str(p) for p in STAGING.rglob('*') if p.is_file() and p.suffix.lower() in {'.exe', '.pyd', '.dll'}]
            if not leftovers or time.monotonic() >= deadline:
                break
            time.sleep(0.25)
        if leftovers:
            raise RuntimeError('Uninstall left runtime binaries: ' + repr(leftovers[:20]))
        if not user_file.is_file() or digest(user_file) != user_digest:
            raise RuntimeError('Uninstall did not preserve the user-created file')
        run('association_cleanup', [sys.executable, str(ROOT / 'tests/windows_installer_association_smoke.py'),
                                    '--runtime-dir', str(STAGING), '--expect-absent'], 180)
        if git('status', '--porcelain=v1', '--untracked-files=no') or git('rev-parse', 'HEAD') != sha:
            raise RuntimeError('Tracked source changed during build or acceptance')
        target = RELEASE / name
        shutil.copy2(installer, target)
        report.update(status='PASS', installer=target.name, installer_size_bytes=target.stat().st_size,
                      installer_sha256=digest(target), installation_test='PASS', uninstall_test='PASS',
                      user_file_preserved=True, python_required_on_client=False,
                      source_unchanged=True, signing='not_signed')
        write(manifest, report)
        run('pdf_43_function_proof', [sys.executable, str(ROOT / 'tools/build_pdf_function_proof.py'),
            '--output', str(ROOT / 'validation/pdf_ui_v3_function_proof'), '--require-packaged-evidence',
            '--runtime-evidence-root', str(OUT)], 1200)
        proof_root = ROOT / 'validation/pdf_ui_v3_function_proof'
        matrix = json.loads((proof_root / 'PDF_FUNCTION_GAP_MATRIX.json').read_text(encoding='utf-8'))
        if matrix.get('commit') != sha or matrix.get('status') != 'PASS' or matrix['counts']['PASS'] != 43:
            raise RuntimeError('PDF 43-function acceptance did not pass')
        report['pdf_function_proof'] = {'status': 'PASS', 'source_commit': sha, 'counts': matrix['counts'],
            'matrix_sha256': digest(proof_root / 'PDF_FUNCTION_GAP_MATRIX.json')}
        write(manifest, report)
        shutil.copy2(manifest, RELEASE / manifest.name)
        for filename in ('PDF_FUNCTION_GAP_MATRIX.json', 'PDF_FUNCTION_GAP_MATRIX.md', 'TRUSTED_EXAMPLE_PROOF.json'):
            shutil.copy2(proof_root / filename, RELEASE / filename)
        with zipfile.ZipFile(RELEASE / 'PDF_FUNCTION_PROOF.zip','w',zipfile.ZIP_DEFLATED) as z:
            for path in proof_root.rglob('*'):
                if path.is_file():z.write(path,path.relative_to(proof_root))
        (RELEASE / 'SHA256SUMS.txt').write_text(digest(target) + '  ' + name + '\n' + digest(portable) + '  ' + portable.name + '\n', encoding='ascii')
        print(json.dumps(report, indent=2), flush=True)
        return 0
    except Exception as exc:
        report.update(status='FAIL', error=f'{type(exc).__name__}: {exc}')
        write(manifest, report)
        print(report['error'], file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
