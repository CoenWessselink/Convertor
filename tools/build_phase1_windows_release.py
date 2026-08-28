"""Build and prove the Phase-1 Windows one-folder and fresh portable runtime."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DIST = ROOT / "dist" / "CWS_Convertor"
RELEASE = ROOT / "release" / "phase1"
VALIDATION = ROOT / "validation" / "phases"
STAGING = ROOT / "build" / "phase1_fresh_portable"


def _safe_reset(path: Path) -> None:
    resolved = path.resolve()
    if resolved == ROOT.resolve() or ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"Onveilige staging path geweigerd: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def _run(label: str, command: list[str], *, cwd: Path, environment: dict[str, str], timeout: float) -> dict[str, object]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return {
            "label": label,
            "command": command,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "return_code": completed.returncode,
            "duration_seconds": round(time.perf_counter() - started, 3),
            "output": (completed.stdout or "")[-8000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "label": label,
            "command": command,
            "status": "FAIL",
            "return_code": -1,
            "duration_seconds": round(time.perf_counter() - started, 3),
            "output": f"TIMEOUT: {exc}",
        }


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and prove the Phase-1 Windows runtime")
    parser.add_argument("--skip-build", action="store_true", help="Gebruik uitsluitend een reeds succesvol gebouwde dist")
    args = parser.parse_args(argv)
    RELEASE.mkdir(parents=True, exist_ok=True)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    source_environment = dict(os.environ)
    source_environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    source_environment.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
    records: list[dict[str, object]] = []
    if args.skip_build:
        records.append({"label": "prebuilt_one_folder", "status": "PASS", "output": "Actuele dist uit voorgaande succesvolle buildstap"})
    else:
        records.append(
            _run(
                "pyinstaller_one_folder",
                [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "CWS_Convertor.spec"],
                cwd=ROOT,
                environment=source_environment,
                timeout=1800,
            )
        )
        if records[-1]["status"] != "PASS":
            return _finish(records, ())
    gui = DIST / "CWS_Convertor.exe"
    cli = DIST / "CWS_Convertor_CLI.exe"
    if not gui.is_file() or not cli.is_file():
        records.append({"label": "dist_binaries", "status": "FAIL", "output": "GUI of CLI EXE ontbreekt"})
        return _finish(records, ())

    runtime_environment = dict(source_environment)
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    runtime_environment["PATH"] = os.pathsep.join((str(windows / "System32"), str(windows)))
    reports = ROOT / "build" / "evidence" / "phase1_windows"
    reports.mkdir(parents=True, exist_ok=True)
    smoke_project = reports / "phase1_smoke.cwscproj"
    commands = (
        ("dist_gui_quick_self_test", [str(gui), "--quick-self-test", "--report", str(reports / "dist_gui_selftest.json")], 300.0),
        ("dist_cli_quick_self_test", [str(cli), "--quick-self-test", "--report", str(reports / "dist_cli_selftest.json")], 300.0),
        ("dist_create_smoke_project", [str(gui), "--create-smoke-project", str(smoke_project), "--report", str(reports / "create_project.json")], 180.0),
        ("dist_gui_smoke", [str(gui), "--gui-smoke", "--project", str(smoke_project), "--report", str(reports / "dist_gui_smoke.json")], 300.0),
    )
    for label, command, timeout in commands:
        records.append(_run(label, command, cwd=DIST, environment=runtime_environment, timeout=timeout))
        if records[-1]["status"] != "PASS":
            return _finish(records, ())

    from cws_convertor.product import APP_VERSION

    commit = str(os.environ.get("GITHUB_SHA") or "").strip()
    if not commit:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if len(commit) != 40 or any(character not in "0123456789abcdefABCDEF" for character in commit):
        raise RuntimeError("Phase-1 release vereist een bekende 40-character Git SHA")
    commit7 = commit[:7]
    portable_name = f"CWS_Convertor_Phase1_{APP_VERSION}_{commit7}_Portable.zip"
    portable = RELEASE / portable_name
    if portable.exists():
        portable.unlink()
    with ZipFile(portable, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(DIST.rglob("*")):
            if path.is_file():
                archive.write(path, Path("CWS_Convertor") / path.relative_to(DIST))
    _safe_reset(STAGING)
    with ZipFile(portable) as archive:
        archive.extractall(STAGING)
    fresh = STAGING / "CWS_Convertor"
    fresh_gui = fresh / "CWS_Convertor.exe"
    fresh_cli = fresh / "CWS_Convertor_CLI.exe"
    fresh_commands = (
        ("fresh_portable_gui_quick_self_test", [str(fresh_gui), "--quick-self-test", "--report", str(reports / "fresh_gui_selftest.json")], 300.0),
        ("fresh_portable_cli_quick_self_test", [str(fresh_cli), "--quick-self-test", "--report", str(reports / "fresh_cli_selftest.json")], 300.0),
        ("fresh_portable_gui_smoke", [str(fresh_gui), "--gui-smoke", "--project", str(smoke_project), "--report", str(reports / "fresh_gui_smoke.json")], 300.0),
    )
    for label, command, timeout in fresh_commands:
        records.append(_run(label, command, cwd=fresh, environment=runtime_environment, timeout=timeout))

    phase_gui = RELEASE / "CWS_Convertor_Phase1.exe"
    phase_cli = RELEASE / "CWS_Convertor_CLI_Phase1.exe"
    shutil.copy2(gui, phase_gui)
    shutil.copy2(cli, phase_cli)
    artifacts = (portable, phase_gui, phase_cli)
    sums = "".join(f"{_sha(path)} *{path.name}\n" for path in artifacts)
    (RELEASE / "SHA256SUMS.txt").write_text(sums, encoding="ascii")
    manifest = {
        "schema": "cws-phase1-windows-manifest-1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": APP_VERSION,
        "commit": commit7,
        "one_folder_required": True,
        "python_removed_from_path": True,
        "artifacts": [
            {"path": str(path.relative_to(ROOT)), "size": path.stat().st_size, "sha256": _sha(path)}
            for path in artifacts
        ],
        "checks": records,
        "status": "PASS" if all(record["status"] == "PASS" for record in records) else "FAIL",
    }
    (RELEASE / "PHASE_1_WINDOWS_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return _finish(records, artifacts, manifest=manifest)


def _finish(
    records: list[dict[str, object]],
    artifacts: tuple[Path, ...],
    *,
    manifest: dict[str, object] | None = None,
) -> int:
    payload = manifest or {
        "schema": "cws-phase1-windows-manifest-1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "FAIL",
        "checks": records,
        "artifacts": [str(path) for path in artifacts],
    }
    evidence = VALIDATION / "PHASE_1_WINDOWS_RUNTIME_EVIDENCE.json"
    evidence.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "checks": len(records)}, sort_keys=True))
    print(evidence)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
