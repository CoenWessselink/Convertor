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

    def run(name: str, args: list[str], timeout: int = 900) -> None:
        tick = time.monotonic()
        record = {'name': name, 'command': args, 'status': 'RUNNING'}
        report['steps'].append(record)
        write(manifest, report)
        print('RUN', name, flush=True)
        try:
            with (OUT / (name + '.log')).open('w', encoding='utf-8') as stream:
                done = subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                      timeout=timeout, check=False)
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
        run('associations', [sys.executable, str(ROOT / 'tests/windows_installer_association_smoke.py'),
                             '--runtime-dir', str(STAGING)], 180)
        user_file = STAGING / 'user-created-project-preservation.txt'
        user_file.write_text('Keep user-created files during uninstall', encoding='utf-8')
        user_digest = digest(user_file)
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
        shutil.copy2(manifest, RELEASE / manifest.name)
        (RELEASE / 'SHA256SUMS.txt').write_text(digest(target) + '  ' + name + '\n', encoding='ascii')
        print(json.dumps(report, indent=2), flush=True)
        return 0
    except Exception as exc:
        report.update(status='FAIL', error=f'{type(exc).__name__}: {exc}')
        write(manifest, report)
        print(report['error'], file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
