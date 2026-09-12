"""Reproducible block-1 source regression evidence; never installer acceptance.

Every script runs in an isolated process using the existing smoke infrastructure.
The report binds the actual Python source tree, interpreter and dependency versions.
An exit code of zero from a skipped test is not accepted as a passing test.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cws_convertor.product import APP_VERSION
from validation.run_all_smokes_v9 import _result_status


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def encoded(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def source_manifest() -> dict[str, str]:
    paths = list(ROOT.glob("*.py")) + list(ROOT.glob("requirements*.txt"))
    for directory in ("cws_convertor", "cws_project", "cws_viewer", "tests", "tools", "validation"):
        paths.extend((ROOT / directory).rglob("*.py"))
    return {path.relative_to(ROOT).as_posix(): digest(path.read_bytes())
            for path in sorted(paths) if "__pycache__" not in path.parts}


def environment() -> dict:
    packages = {}
    for name in ("PySide6", "vtk", "cadquery", "cadquery-ocp", "ifcopenshell", "shapely", "ezdxf"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"os": platform.platform(), "python": sys.version,
            "executable": sys.executable, "packages": packages,
            "qt_platform": os.environ.get("QT_QPA_PLATFORM", "offscreen"),
            "acceptance_scope": "source and Qt component tests; synthetic fixtures unless test states otherwise",
            "installed_commit": None, "native_gpu_acceptance": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--test", action="append", dest="tests", help="Repository-relative smoke script; repeatable")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scripts = args.tests or sorted({
        *(str(path.relative_to(ROOT).as_posix()) for path in (ROOT / "tests").glob("bom_*_smoke.py")),
        "tests/project_bom_smoke.py", "tests/project_model_smoke.py", "tests/project_storage_smoke.py",
        "tests/material_release_gate_smoke.py", "tests/master_requirements_v2_smoke.py",
        "tests/production_export_negative_smoke.py", "tests/unified_production_workflow_u4_smoke.py",
    })
    for script in scripts:
        path = (ROOT / script).resolve()
        if not path.is_relative_to(ROOT / "tests") or not path.is_file():
            parser.error(f"Expected an existing test script inside tests/: {script}")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True)
    before = source_manifest()
    tree_hash = digest(encoded(before))
    env = dict(os.environ, QT_QPA_PLATFORM=os.environ.get("QT_QPA_PLATFORM", "offscreen"),
               CWS_HEADLESS_GUI_SMOKE="1", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    identity = {"commit": commit, "app_version": APP_VERSION, "environment": environment(),
                "source_tree_sha256": tree_hash, "tracked_dirty": bool(dirty),
                "created_at": datetime.now(timezone.utc).isoformat()}
    records = []
    for script in scripts:
        started = time.perf_counter()
        timed_out = False
        try:
            result = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, env=env,
                                    capture_output=True, timeout=args.timeout)
            returncode, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode, stdout, stderr = -1, exc.stdout or b"", exc.stderr or b""
        combined = (stdout + b"\n" + stderr).decode("utf-8", errors="replace")
        status = _result_status(returncode, timed_out, combined).upper()
        status = {"PASSED": "PASS", "FAILED": "FAIL", "SKIPPED": "PARTIAL", "TIMEOUT": "FAIL"}[status]
        if status == "PASS" and not combined.strip():
            status = "PARTIAL"  # Importing an execution helper is not a test run.
        log_name = Path(script).stem + ".txt"
        log_bytes = stdout + b"\n--- stderr ---\n" + stderr
        (output / log_name).write_bytes(log_bytes)
        record = {**identity, "scenario": script, "result": status,
                  "input_hash": digest(encoded({"source_tree_sha256": tree_hash, "script": script,
                                                "script_sha256": before[script]})),
                  "output_hash": digest(log_bytes), "log": log_name,
                  "returncode": returncode, "timed_out": timed_out,
                  "duration_seconds": round(time.perf_counter() - started, 3)}
        records.append(record)
        print(f"{status}: {script} ({record['duration_seconds']}s)", flush=True)
    after = source_manifest()
    unchanged = before == after
    summary = {status: sum(row["result"] == status for row in records) for status in ("PASS", "FAIL", "PARTIAL")}
    report = {"schema": "cws-product-block1-source-evidence-1", **identity,
              "scenario": "block_1_source_regression", "input_hash": tree_hash,
              "output_hash": digest(encoded(records)), "source_files": before,
              "source_unchanged_during_run": unchanged,
              "changed_during_run": sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key)),
              "result": "PASS" if records and unchanged and summary["PASS"] == len(records) else "FAIL",
              "summary": summary, "tests": records,
              "limitations": ["Passing source tests do not close all W18 action scenarios.",
                              "No installed executable, physical printer, machine or GPU acceptance is implied."]}
    (output / "SOURCE_REGRESSION.json").write_bytes(encoded(report) + b"\n")
    print(json.dumps({"result": report["result"], "summary": summary,
                      "source_unchanged_during_run": unchanged, "output": str(output)}, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
