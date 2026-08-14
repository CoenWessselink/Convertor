"""Run Viewer V6 smoke scripts as isolated subprocesses and persist evidence.

The batch range makes the runner usable in constrained CI/analysis shells while
keeping each smoke test independent.  A final aggregation call without
``--start`` or with ``--aggregate-only`` creates the machine-readable summary.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation" / "viewer_v6_full_smokes"
LOGS = OUT / "logs"


def _tests() -> list[Path]:
    return sorted((ROOT / "tests").glob("*_smoke.py"))


def _run(path: Path, timeout_seconds: int) -> dict:
    started = time.perf_counter()
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    # The analysis container can expose DISPLAY=:0 without a reachable X
    # server.  Leave display creation to the tests' explicit xvfb re-exec so
    # native OCCT/Qt tests remain deterministic instead of failing on a stale
    # inherited display variable.
    if (
        sys.platform.startswith("linux")
        and env.get("DISPLAY") == ":0"
        and path.name != "viewer_v2_vtk_core_smoke.py"
    ):
        env.pop("DISPLAY", None)
    try:
        proc = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
        exit_code = proc.returncode
        skipped_only = exit_code == 5 and "skipped" in f"{proc.stdout}\n{proc.stderr}".lower()
        status = "passed" if exit_code == 0 or skipped_only else "failed"
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        status = "timeout"
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
    elapsed = time.perf_counter() - started
    combined = f"{stdout}\n{stderr}"
    summary_skips = [int(value) for value in re.findall(r"skipped[= ](\d+)", combined, flags=re.I)]
    line_skips = sum(1 for line in combined.splitlines() if " ... skipped " in line.lower())
    explicit_skips = max([line_skips, *summary_skips], default=0)
    result = {
        "script": str(path.relative_to(ROOT)),
        "status": status,
        "exit_code": exit_code,
        "elapsed_seconds": elapsed,
        "explicit_skips": explicit_skips,
        "skipped_only": bool(exit_code == 5 and status == "passed"),
    }
    log = (
        f"$ {sys.executable} {path.relative_to(ROOT)}\n\n"
        f"STDOUT\n{stdout}\n\nSTDERR\n{stderr}\n\n"
        f"EXIT {exit_code}\nELAPSED {elapsed:.3f}s\n"
    )
    (LOGS / f"{path.stem}.log").write_text(log, encoding="utf-8")
    (LOGS / f"{path.stem}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def aggregate() -> dict:
    tests = _tests()
    results = []
    for path in tests:
        evidence = LOGS / f"{path.stem}.json"
        if evidence.is_file():
            results.append(json.loads(evidence.read_text(encoding="utf-8")))
        else:
            results.append({
                "script": str(path.relative_to(ROOT)),
                "status": "not_run",
                "exit_code": None,
                "elapsed_seconds": None,
                "explicit_skips": 0,
            })
    summary = {
        "schema": "cws-viewer-v6-full-smoke-summary-1.0",
        "python": sys.version,
        "platform": sys.platform,
        "total": len(results),
        "passed": sum(item["status"] == "passed" for item in results),
        "failed": sum(item["status"] == "failed" for item in results),
        "timeout": sum(item["status"] == "timeout" for item in results),
        "not_run": sum(item["status"] == "not_run" for item in results),
        "explicit_skips": sum(int(item.get("explicit_skips", 0)) for item in results),
        "results": results,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "VIEWER_V6_FULL_SMOKE_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=0, help="0 means all remaining tests")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--aggregate-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    tests = _tests()
    if not args.aggregate_only:
        selected = tests[args.start:] if args.count <= 0 else tests[args.start:args.start + args.count]
        for path in selected:
            result = _run(path, args.timeout)
            print(f"{result['status'].upper():8} {result['elapsed_seconds']:8.2f}s {path.name}", flush=True)
    summary = aggregate()
    print(json.dumps({key: summary[key] for key in ("total", "passed", "failed", "timeout", "not_run", "explicit_skips")}, indent=2))
    return 1 if summary["failed"] or summary["timeout"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
