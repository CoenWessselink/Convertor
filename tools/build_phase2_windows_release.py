from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

from cws_convertor.project.model import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist" / "CWS_Convertor"
ONEFILE_SPEC = ROOT / "CWS_Convertor_OneFile.spec"
ONEFILE_DIST = ROOT / "dist" / "CWS_Convertor.exe"
RELEASE = ROOT / "release" / "phase2"
ONE_FOLDER = RELEASE / "CWS_Convertor_Phase2"
PORTABLE = RELEASE / "CWS_Convertor_Phase2_Portable.zip"
FRESH_ROOT = ROOT / "build" / "phase2_fresh_portable"
STANDALONE_ROOT = ROOT / "build" / "phase2_standalone_smoke"
EVIDENCE = ROOT / "validation" / "phases" / "PHASE_2_WINDOWS_RUNTIME_EVIDENCE.json"
RESULTS = ROOT / "validation" / "results" / "windows-runtime-phase2"


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _reset(path: Path) -> None:
    resolved = path.resolve()
    if ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset path outside workspace: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _runtime_env(runtime: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(part for part in env.get("PATH", "").split(os.pathsep) if "python" not in part.casefold())
    env["CWS_PHASE2_RUNTIME_DIR"] = str(runtime)
    return env


def _run(label: str, command: list[str], env: dict[str, str] | None = None) -> dict:
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=900)
    result = {"label": label, "status": "passed" if completed.returncode == 0 else "failed", "returncode": completed.returncode, "duration_seconds": round(time.perf_counter() - started, 6), "command": command, "stdout_tail": completed.stdout[-8000:], "stderr_tail": completed.stderr[-8000:]}
    if completed.returncode:
        raise RuntimeError(f"{label} failed ({completed.returncode})\n{completed.stdout}\n{completed.stderr}")
    return result


def _zip_tree(source: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(str(Path(source.name) / path.relative_to(source)).replace("\\", "/"))
                info.date_time = (2026, 1, 1, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())


def _clean_revision() -> str:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    expected = str(os.environ.get("GITHUB_SHA") or "").strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=ROOT,
        text=True,
    ).strip()
    if len(revision) != 40 or (expected and expected.casefold() != revision.casefold()) or dirty:
        details = dirty or f"HEAD={revision}; expected={expected or revision}"
        raise RuntimeError(
            "Phase-2 release requires one exact Git commit with an unchanged tracked source tree: "
            f"{details}"
        )
    return revision


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and prove the dedicated Phase-2 Windows runtime")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    revision = _clean_revision()
    results: list[dict] = []
    if not args.skip_build:
        results.append(_run("windows_build", [str(ROOT / "build_windows_exe.bat")]))
    gui = DIST / "CWS_Convertor.exe"
    cli = DIST / "CWS_Convertor_CLI.exe"
    if not gui.is_file() or not cli.is_file():
        raise FileNotFoundError("dist/CWS_Convertor is not a complete Windows one-folder runtime")
    results.append(
        _run(
            "standalone_build",
            [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(ONEFILE_SPEC)],
        )
    )
    if not ONEFILE_DIST.is_file():
        raise FileNotFoundError("CWS_Convertor_OneFile.spec produced no standalone executable")
    _reset(RELEASE)
    shutil.copytree(DIST, ONE_FOLDER)
    standalone_release = RELEASE / "CWS_Convertor_Phase2.exe"
    shutil.copy2(ONEFILE_DIST, standalone_release)
    cli_release = RELEASE / "CWS_Convertor_CLI_Phase2.exe"
    shutil.copy2(cli, cli_release)
    RESULTS.mkdir(parents=True, exist_ok=True)
    env = _runtime_env(ONE_FOLDER)
    results.append(_run("one_folder_gui_selftest", [str(ONE_FOLDER / gui.name), "--quick-self-test", "--report", str(RESULTS / "one-folder-gui.json")], env))
    results.append(_run("one_folder_cli_selftest", [str(ONE_FOLDER / cli.name), "--quick-self-test", "--report", str(RESULTS / "one-folder-cli.json")], env))
    results.append(_run("one_folder_packaged_m18", [sys.executable, "tests/phase2_m18_packaged_gate_smoke.py"], env))
    results.append(_run("one_folder_packaged_runtime", [sys.executable, "tests/packaged_runtime_smoke.py", "--runtime-dir", str(ONE_FOLDER), "--label", "phase2-one-folder", "--result-dir", str(RESULTS)], env))
    _zip_tree(ONE_FOLDER, PORTABLE)
    versioned_portable = RELEASE / f"CWS_Convertor_Phase2_{APP_VERSION}_{revision[:7]}_Portable.zip"
    shutil.copy2(PORTABLE, versioned_portable)
    _reset(FRESH_ROOT)
    with zipfile.ZipFile(PORTABLE, "r") as archive:
        archive.extractall(FRESH_ROOT)
    fresh = FRESH_ROOT / ONE_FOLDER.name
    fresh_env = _runtime_env(fresh)
    results.append(_run("fresh_portable_gui_selftest", [str(fresh / gui.name), "--quick-self-test", "--report", str(RESULTS / "fresh-gui.json")], fresh_env))
    results.append(_run("fresh_portable_cli_selftest", [str(fresh / cli.name), "--quick-self-test", "--report", str(RESULTS / "fresh-cli.json")], fresh_env))
    results.append(_run("fresh_portable_packaged_m18", [sys.executable, "tests/phase2_m18_packaged_gate_smoke.py"], fresh_env))
    results.append(_run("fresh_portable_packaged_runtime", [sys.executable, "tests/packaged_runtime_smoke.py", "--runtime-dir", str(fresh), "--label", "phase2-fresh-portable", "--result-dir", str(RESULTS)], fresh_env))

    _reset(STANDALONE_ROOT)
    standalone = STANDALONE_ROOT / standalone_release.name
    shutil.copy2(standalone_release, standalone)
    standalone_env = _runtime_env(STANDALONE_ROOT)
    standalone_project = STANDALONE_ROOT / "phase2-standalone-smoke.cwscproj"
    results.append(_run("standalone_gui_selftest", [str(standalone), "--quick-self-test", "--report", str(RESULTS / "standalone-gui.json")], standalone_env))
    results.append(_run("standalone_create_project", [str(standalone), "--create-smoke-project", str(standalone_project), "--report", str(RESULTS / "standalone-create-project.json")], standalone_env))
    results.append(_run("standalone_gui_smoke", [str(standalone), "--gui-smoke", "--project", str(standalone_project), "--report", str(RESULTS / "standalone-gui-smoke.json")], standalone_env))
    internal_present = (STANDALONE_ROOT / "_internal").exists()
    if internal_present:
        raise RuntimeError("Standalone smoke directory unexpectedly contains _internal")
    artifacts = {}
    for path in (standalone_release, cli_release, PORTABLE, versioned_portable):
        artifacts[path.name] = {"path": str(path), "bytes": path.stat().st_size, "sha256": _sha(path)}
    release_manifest = RELEASE / "PHASE_2_RELEASE_MANIFEST.json"
    release_manifest.write_text(json.dumps({"schema": "cws-phase2-release-manifest-2.0", "status": "passed", "version": APP_VERSION, "source_revision": revision, "artifacts": artifacts, "machine_transfer_allowed": False, "direct_machine_control_allowed": False}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    artifacts[release_manifest.name] = {"path": str(release_manifest), "bytes": release_manifest.stat().st_size, "sha256": _sha(release_manifest)}
    checksums = RELEASE / "SHA256SUMS.txt"
    checksums.write_text("".join(f"{value['sha256']}  {name}\n" for name, value in artifacts.items()), encoding="ascii")
    payload = {
        "schema": "cws-phase2-windows-runtime-evidence-1.0",
        "status": "passed",
        "source_revision": revision,
        "python_removed_from_runtime_path": True,
        "one_folder": str(ONE_FOLDER),
        "fresh_portable": str(fresh),
        "standalone": {
            "path": str(standalone_release),
            "isolated_test_root": str(STANDALONE_ROOT),
            "internal_directory_present": internal_present,
            "status": "passed",
        },
        "artifacts": artifacts,
        "results": results,
        "m18_packaged_gate": "passed",
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print("PHASE_2_WINDOWS_RUNTIME = PASS")
    print(EVIDENCE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
