#!/usr/bin/env python3
"""Run the complete CWS Viewer V1 local validation and write auditable evidence.

The runner keeps every smoke script in a separate process, records stdout,
stderr, duration and exit code, then executes the measured OCCT/AIS versus VTK
technology benchmark.  It deliberately does not convert a skipped real fixture
into a pass and does not claim the Windows/Qt packaging gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SMOKE_FILES = tuple(sorted((ROOT / "tests").glob("*_smoke.py")))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str], *, log_dir: Path, name: str, timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    stdout_path = log_dir / f"{name}.stdout.txt"
    stderr_path = log_dir / f"{name}.stderr.txt"
    print(f"[V1 validation] START {name}", flush=True)
    timed_out = False
    return_code = -1
    with stdout_path.open("w", encoding="utf-8") as stdout_stream, stderr_path.open("w", encoding="utf-8") as stderr_stream:
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                text=True,
                stdin=subprocess.DEVNULL,
                stdout=stdout_stream,
                stderr=stderr_stream,
                timeout=timeout,
                check=False,
            )
            return_code = completed.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            return_code = 124
            stderr_stream.write(f"\nTIMEOUT after {timeout} seconds\n")
    duration = time.perf_counter() - started
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    combined = f"{stdout_text}\n{stderr_text}"
    skipped = sum(int(value) for value in re.findall(r"skipped[= ](\d+)", combined, flags=re.I))
    status = "passed" if return_code == 0 else "failed"
    print(f"[V1 validation] END {name}: {status} ({duration:.3f}s)", flush=True)
    return {
        "name": name,
        "command": command,
        "exit_code": return_code,
        "status": status,
        "timed_out": timed_out,
        "duration_seconds": round(duration, 6),
        "skipped_reported": skipped,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "stdout_sha256": sha256(stdout_path),
        "stderr_sha256": sha256(stderr_path),
    }


def write_markdown(report: dict[str, Any], output: Path) -> None:
    lines = [
        "# CWS Viewer V1 — lokaal validatierapport",
        "",
        f"**Status:** `{report['status']}`  ",
        f"**Gegenereerd:** `{report['generated_at']}`  ",
        f"**Platform:** `{report['platform']}`  ",
        f"**Python:** `{report['python']}`  ",
        f"**Commit:** `{report['git_commit']}`",
        "",
        "## Smoke scripts",
        "",
        "| Script | Status | Exit | Duur (s) | Expliciete skips |",
        "|---|---|---:|---:|---:|",
    ]
    for row in report["smokes"]:
        lines.append(
            f"| `{row['name']}` | {row['status']} | {row['exit_code']} | "
            f"{row['duration_seconds']:.3f} | {row['skipped_reported']} |"
        )
    benchmark = report["benchmark"]
    lines.extend([
        "",
        "## Technologiebenchmark",
        "",
        f"- Status: **{benchmark['status']}**",
        f"- Cases: **{benchmark['case_count']}**",
        f"- Projectrenderer: **{benchmark['decision']['project_renderer']}**",
        f"- Exact Part Workbench-renderer: **{benchmark['decision']['exact_part_renderer']}**",
        f"- Besluitstatus: **{benchmark['decision']['decision_status']}**",
        "",
        "## Harde begrenzing",
        "",
        "De lokale V1-poort bewijst de renderercontracten, synthetische 100/1.000/10.000-node scènes, picking, clipping, captures en regressie-integriteit. De PySide6-host, afzonderlijke PyInstaller-onedirimpact, portable/installed Windows-runtimes, echte Tekla-projectscene en het complexe 11881-part blijven open Windows/real-modelpoorten.",
        "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="validation/viewer_v1_final")
    parser.add_argument("--counts", default="100,1000,10000")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    logs = output / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    compile_result = run_command(
        [sys.executable, "-m", "compileall", "-q", "cws_viewer", "viewer_harness", "tests", "validation/run_viewer_v1_validation.py"],
        log_dir=logs,
        name="compileall",
        timeout=args.timeout,
    )
    smokes: list[dict[str, Any]] = []
    for smoke in SMOKE_FILES:
        smokes.append(
            run_command(
                [sys.executable, str(smoke.relative_to(ROOT))],
                log_dir=logs,
                name=smoke.stem,
                timeout=args.timeout,
            )
        )

    benchmark_dir = output / "technology_benchmark"
    benchmark_command = [
        sys.executable,
        "viewer_harness/run_v1_technology_spike.py",
        "--counts",
        args.counts,
        "--output",
        str(benchmark_dir),
        "--xvfb",
        "never",
        "--timeout",
        str(args.timeout),
        "--orbit-frames",
        "30",
        "--pick-samples",
        "75",
    ]
    benchmark_process = run_command(
        benchmark_command,
        log_dir=logs,
        name="viewer_v1_technology_benchmark",
        timeout=max(args.timeout, 900),
    )
    benchmark_summary_path = benchmark_dir / "summary.json"
    if benchmark_summary_path.exists():
        benchmark_summary = json.loads(benchmark_summary_path.read_text(encoding="utf-8"))
    else:
        benchmark_summary = {
            "status": "failed",
            "case_count": 0,
            "failures": ["summary.json ontbreekt"],
            "decision": {},
            "report_hash": "",
        }

    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        commit = "unknown"
    status = "passed" if (
        compile_result["status"] == "passed"
        and all(row["status"] == "passed" for row in smokes)
        and benchmark_process["status"] == "passed"
        and benchmark_summary.get("status") == "passed"
    ) else "failed"
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "status": status,
        "platform": platform.platform(),
        "python": sys.version.replace("\n", " "),
        "git_commit": commit,
        "compile": compile_result,
        "smoke_count": len(smokes),
        "smoke_passed": sum(row["status"] == "passed" for row in smokes),
        "smoke_failed": sum(row["status"] != "passed" for row in smokes),
        "explicit_skips_reported": sum(row["skipped_reported"] for row in smokes),
        "smokes": smokes,
        "benchmark_process": benchmark_process,
        "benchmark": benchmark_summary,
    }
    json_path = output / "VIEWER_V1_VALIDATION_SUMMARY.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, output / "VIEWER_V1_VALIDATION_REPORT.md")
    print(json.dumps({
        "status": status,
        "smokes": f"{report['smoke_passed']}/{report['smoke_count']}",
        "explicit_skips_reported": report["explicit_skips_reported"],
        "benchmark": benchmark_summary,
        "summary": str(json_path),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if status == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
