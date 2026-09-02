"""Build and prove the final Phase-3 Windows distribution."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.10.21-beta-dev"


def source_revision() -> str:
    value = str(os.environ.get("GITHUB_SHA") or "").strip()
    if not value:
        value = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if len(value) != 40 or any(character not in "0123456789abcdefABCDEF" for character in value):
        raise RuntimeError("Finale Windows-release vereist een bekende 40-character Git SHA")
    return value.lower()


SOURCE_REVISION = source_revision()
REVISION_TAG = SOURCE_REVISION[:7]
RELEASE = ROOT / "release" / "phase3"
RESULTS = ROOT / "validation" / "results" / "windows-runtime-phase3"
PHASES = ROOT / "validation" / "phases"
ONEDIR = ROOT / "dist" / "CWS_Convertor"
ONEFILE = ROOT / "dist" / "CWS_Convertor.exe"
INSTALL_ROOT = ROOT / "build" / "phase3_installed_runtime"
PORTABLE_ROOT = ROOT / "build" / "phase3_portable_smoke"
STANDALONE_ROOT = ROOT / "build" / "phase3_standalone_smoke"


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def run(command: list[str], *, timeout: int = 1800,
        environment: dict[str, str] | None = None) -> dict[str, object]:
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=ROOT, env=environment, capture_output=True, text=True,
        timeout=timeout, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    result = {
        "command": command, "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "stdout": completed.stdout[-6000:], "stderr": completed.stderr[-6000:],
    }
    if completed.returncode != 0:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def reset_directory(path: Path) -> None:
    resolved = path.resolve()
    build_root = (ROOT / "build").resolve()
    if build_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset directory outside build root: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def clean_runtime_environment() -> dict[str, str]:
    environment = os.environ.copy()
    system_root = Path(environment.get("SystemRoot", r"C:\Windows"))
    environment["PATH"] = os.pathsep.join(
        str(item) for item in (system_root / "System32", system_root, system_root / "System32" / "Wbem")
    )
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    return environment


def zip_onedir(source: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, (Path("CWS_Convertor") / path.relative_to(source)).as_posix())


def source_files() -> list[Path]:
    roots = ["cws_convertor", "cws_viewer", "tests", "tools", "validation", "installer", "docs", "00_START_HERE", ".github"]
    suffixes = {".py", ".json", ".md", ".txt", ".yml", ".yaml", ".iss", ".spec", ".toml", ".b64"}
    files: list[Path] = []
    for name in roots:
        root = ROOT / name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes and "__pycache__" not in path.parts:
                files.append(path)
    for pattern in ("*.py", "*.spec", "requirements*.txt", "README.md"):
        files.extend(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(set(files), key=lambda item: item.relative_to(ROOT).as_posix())


def build_source_package(target: Path) -> str:
    tree_hash = sha256()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in source_files():
            relative = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            tree_hash.update(relative.encode("utf-8") + b"\0" + sha256(data).digest())
            archive.writestr(relative, data)
    return tree_hash.hexdigest()


def find_iscc() -> Path:
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    found = next((item for item in candidates if item.is_file()), None)
    if found is None:
        raise FileNotFoundError("Inno Setup 6 ISCC.exe was not found")
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    RELEASE.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    PHASES.mkdir(parents=True, exist_ok=True)
    commands: dict[str, object] = {}
    if not args.skip_build:
        commands["onedir_build"] = run(
            [sys.executable, "-m", "PyInstaller", "--noconfirm", "CWS_Convertor.spec"], timeout=2400
        )
    if not (ONEDIR / "CWS_Convertor.exe").is_file() or not (ONEDIR / "CWS_Convertor_CLI.exe").is_file():
        raise FileNotFoundError("Complete one-folder GUI/CLI runtime is missing")
    commands["onedir_runtime"] = run(
        [sys.executable, str(ROOT / "tests" / "packaged_runtime_smoke.py"), "--runtime-dir", str(ONEDIR),
         "--label", "phase3-dist", "--result-dir", str(RESULTS)], timeout=1200,
    )
    portable = RELEASE / f"CWS_Convertor_Final_{VERSION}_{REVISION_TAG}_Portable.zip"
    zip_onedir(ONEDIR, portable)
    reset_directory(PORTABLE_ROOT)
    with zipfile.ZipFile(portable) as archive:
        archive.extractall(PORTABLE_ROOT)
    commands["portable_runtime"] = run(
        [sys.executable, str(ROOT / "tests" / "packaged_runtime_smoke.py"),
         "--runtime-dir", str(PORTABLE_ROOT / "CWS_Convertor"), "--label", "phase3-portable",
         "--result-dir", str(RESULTS)], timeout=1200,
    )
    if not args.skip_build:
        commands["onefile_build"] = run(
            [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "CWS_Convertor_OneFile.spec"],
            timeout=3000,
        )
    elif not ONEFILE.is_file():
        raise FileNotFoundError("--skip-build requires the previously proven one-file GUI")
    standalone = RELEASE / "CWS_Convertor.exe"
    shutil.copy2(ONEFILE, standalone)
    reset_directory(STANDALONE_ROOT)
    standalone_copy = STANDALONE_ROOT / standalone.name
    shutil.copy2(standalone, standalone_copy)
    clean_env = clean_runtime_environment()
    standalone_selftest = RESULTS / "phase3-standalone-native-selftest.json"
    standalone_gui = RESULTS / "phase3-standalone-gui-smoke.json"
    commands["standalone_selftest"] = run(
        [str(standalone_copy), "--self-test", "--output", str(standalone_selftest)],
        timeout=900, environment=clean_env,
    )
    commands["standalone_gui"] = run(
        [str(standalone_copy), "--gui-smoke", "--output", str(standalone_gui)],
        timeout=900, environment=clean_env,
    )
    if (STANDALONE_ROOT / "_internal").exists():
        raise RuntimeError("Standalone Phase-3 GUI unexpectedly requires _internal")
    commands["installer_build"] = run(
        [str(find_iscc()), f"/DCommit7={REVISION_TAG}", str(ROOT / "installer" / "CWS_Convertor.iss")], timeout=1800
    )
    built_installer = ROOT / "dist_installer" / f"CWS_Convertor_Setup_{VERSION}_{REVISION_TAG}_x64.exe"
    installer = RELEASE / built_installer.name
    shutil.copy2(built_installer, installer)
    reset_directory(INSTALL_ROOT)
    install_command = [
        str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-",
        "/CURRENTUSER", "/TASKS=fileassoc", f"/DIR={INSTALL_ROOT}",
    ]
    commands["silent_install"] = run(install_command, timeout=900)
    commands["installed_runtime"] = run(
        [sys.executable, str(ROOT / "tests" / "packaged_runtime_smoke.py"), "--runtime-dir", str(INSTALL_ROOT),
         "--label", "phase3-installed", "--result-dir", str(RESULTS)], timeout=1200,
    )
    commands["installed_associations"] = run(
        [sys.executable, str(ROOT / "tests" / "windows_installer_association_smoke.py"),
         "--runtime-dir", str(INSTALL_ROOT)], timeout=120,
    )
    uninstaller = INSTALL_ROOT / "unins000.exe"
    commands["uninstall"] = run(
        [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
         f"/LOG={RESULTS / 'phase3-uninstall-attempt-1.log'}"], timeout=900,
    )

    def wait_for_critical_cleanup(timeout: float = 60.0) -> list[str]:
        cleanup_deadline = time.monotonic() + timeout
        leftovers: list[str] = []
        while True:
            leftovers = [
                str(path)
                for path in INSTALL_ROOT.rglob("*")
                if path.is_file() and path.suffix.lower() in {".exe", ".dll", ".pyd"}
            ]
            if not leftovers or time.monotonic() >= cleanup_deadline:
                return leftovers
            time.sleep(0.25)

    critical_leftovers = wait_for_critical_cleanup()
    uninstall_cleanup_attempts = [
        {
            "attempt": 1,
            "status": "PASS" if not critical_leftovers else "RETRY_REQUIRED",
            "critical_leftover_count": len(critical_leftovers),
            "critical_leftovers": critical_leftovers[:20],
        }
    ]
    if critical_leftovers:
        commands["uninstall_retry_install"] = run(install_command, timeout=900)
        retry_uninstaller = INSTALL_ROOT / "unins000.exe"
        commands["uninstall_retry"] = run(
            [str(retry_uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
             f"/LOG={RESULTS / 'phase3-uninstall-attempt-2.log'}"], timeout=900,
        )
        critical_leftovers = wait_for_critical_cleanup()
        uninstall_cleanup_attempts.append(
            {
                "attempt": 2,
                "status": "PASS" if not critical_leftovers else "FAIL",
                "critical_leftover_count": len(critical_leftovers),
                "critical_leftovers": critical_leftovers[:20],
            }
        )
    if critical_leftovers:
        raise RuntimeError(f"Critical installed runtime leftovers: {critical_leftovers[:20]}")
    commands["association_cleanup"] = run(
        [sys.executable, str(ROOT / "tests" / "windows_installer_association_smoke.py"),
         "--expect-absent"], timeout=120,
    )
    sbom = RELEASE / "CWS_Convertor_SBOM.cdx.json"
    commands["sbom"] = run([sys.executable, str(ROOT / "tools" / "generate_sbom.py"), str(sbom)], timeout=300)
    pip_check = run([sys.executable, "-m", "pip", "check"], timeout=300)
    lock_files = [ROOT / "requirements-runtime.lock.txt", ROOT / "requirements-build.lock.txt"]
    unpinned = []
    for lock in lock_files:
        for line in lock.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if text and not text.startswith(("#", "-")) and "==" not in text:
                unpinned.append(f"{lock.name}:{text}")
    security = {
        "schema": "cws-phase3-security-dependency-1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if pip_check["passed"] and not unpinned else "failed",
        "pip_check": pip_check, "lock_files": [str(path) for path in lock_files],
        "unpinned_requirements": unpinned, "sbom": str(sbom),
        "network_vulnerability_scan": "not_claimed_offline_build",
    }
    security_path = PHASES / "PHASE_3_SECURITY_DEPENDENCY_REPORT.json"
    security_path.write_text(json.dumps(security, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    shutil.copy2(security_path, RELEASE / security_path.name)
    if security["status"] != "passed":
        raise RuntimeError("Security/dependency gate failed")
    source_package = RELEASE / f"CWS_Convertor_Source_{VERSION}_{REVISION_TAG}.zip"
    source_tree_sha256 = build_source_package(source_package)
    artifacts = [portable, installer, standalone, sbom, RELEASE / security_path.name, source_package]
    artifact_records = [
        {"path": path.relative_to(ROOT).as_posix(), "name": path.name,
         "bytes": path.stat().st_size, "sha256": digest(path)} for path in artifacts
    ]
    checks = {
        "windows_one_folder_dist": True, "fresh_portable": True,
        "portable_self_test": True, "portable_gui_smoke": True,
        "standalone_gui_without_internal": True, "final_setup_exe": True,
        "silent_install": True, "installed_self_test": True, "installed_gui_smoke": True,
        "file_associations": True, "uninstall": True, "no_critical_leftovers": not critical_leftovers,
        "no_external_python": True, "quality_inspection_packaged": True,
        "machine_transfer_allowed": False,
    }
    evidence = {
        "schema": "cws-phase3-windows-runtime-1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "status": "PASS",
        "version": VERSION, "source_revision": SOURCE_REVISION, "source_tree_sha256": source_tree_sha256,
        "checks": checks, "commands": commands, "artifacts": artifact_records,
        "runtime_paths": {
            "one_folder_gui": str(ONEDIR / "CWS_Convertor.exe"),
            "one_folder_cli": str(ONEDIR / "CWS_Convertor_CLI.exe"),
            "portable": str(portable), "standalone_gui": str(standalone), "installer": str(installer),
        },
        "critical_leftovers": critical_leftovers,
        "uninstall_cleanup_attempts": uninstall_cleanup_attempts,
    }
    evidence_path = PHASES / "PHASE_3_WINDOWS_RUNTIME_EVIDENCE.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    release_manifest = {
        "schema": "cws-phase3-release-manifest-1.0", "status": "passed", "version": VERSION,
        "source_revision": SOURCE_REVISION, "source_tree_sha256": source_tree_sha256,
        "generated_at_utc": evidence["generated_at_utc"], "artifacts": artifact_records,
        "one_folder": {
            "path": ONEDIR.relative_to(ROOT).as_posix(),
            "gui_sha256": digest(ONEDIR / "CWS_Convertor.exe"),
            "cli_sha256": digest(ONEDIR / "CWS_Convertor_CLI.exe"),
            "complete_runtime_required": True,
        },
        "validation": evidence_path.relative_to(ROOT).as_posix(),
        "safety": {
            "machine_observed_by_cws": False, "deployment_transport_authorized": False,
            "direct_machine_transfer": False, "machine_transfer.allowed": False,
        },
    }
    manifest_path = RELEASE / "PHASE_3_RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(release_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksum_items = artifacts + [manifest_path]
    (RELEASE / "SHA256SUMS.txt").write_text(
        "".join(f"{digest(path)}  {path.name}\n" for path in checksum_items), encoding="ascii"
    )
    print("PHASE_3_WINDOWS_RUNTIME = PASS")
    print(evidence_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
