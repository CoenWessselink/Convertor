#!/usr/bin/env python3
"""Run the complete source smoke baseline in isolated subprocesses.

The runner is intended as release evidence, not as a replacement for the
individual test scripts.  On Linux it uses xvfb-run when available so OCCT/Tk/
VTK GUI probes receive a real virtual display.  Every script gets a bounded
runtime and its complete output is persisted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKIP_PATTERN = re.compile(r"skipped\s*=\s*(\d+)", re.IGNORECASE)


def _scripts() -> tuple[Path, ...]:
    return tuple(sorted((ROOT / "tests").glob("*_smoke.py")))


def _command(script: Path, *, use_xvfb: bool) -> list[str]:
    base = [sys.executable, str(script)]
    if use_xvfb and shutil.which("xvfb-run"):
        return ["xvfb-run", "-a", *base]
    return base


def run(output: Path, *, timeout_seconds: int, use_xvfb: bool) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    logs = output / "logs"
    logs.mkdir(exist_ok=True)
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    for script in _scripts():
        command = _command(script, use_xvfb=use_xvfb)
        script_started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + f"\nTIMEOUT after {timeout_seconds}s\n"
            timed_out = True
        duration = time.perf_counter() - script_started
        combined = f"COMMAND: {' '.join(command)}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"
        log_path = logs / f"{script.stem}.log"
        log_path.write_text(combined, encoding="utf-8")
        skip_matches = [int(value) for value in SKIP_PATTERN.findall(stdout + "\n" + stderr)]
        results.append(
            {
                "script": script.name,
                "command": command,
                "status": "passed" if returncode == 0 else "failed",
                "returncode": returncode,
                "timed_out": timed_out,
                "duration_seconds": duration,
                "reported_skips": max(skip_matches, default=0),
                "log": str(log_path),
            }
        )
    failed = [item for item in results if item["status"] != "passed"]
    payload = {
        "status": "passed" if not failed else "failed",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version.replace("\n", " "),
        "test_script_count": len(results),
        "passed_script_count": len(results) - len(failed),
        "failed_script_count": len(failed),
        "reported_skip_count": sum(item["reported_skips"] for item in results),
        "elapsed_seconds": time.perf_counter() - started,
        "use_xvfb": bool(use_xvfb and shutil.which("xvfb-run")),
        "results": results,
    }
    (output / "VIEWER_V4_FULL_SMOKE_SUMMARY.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        "# CWS Viewer V4 — volledige smoke-baseline",
        "",
        f"- Status: **{payload['status']}**",
        f"- Scripts: **{payload['passed_script_count']}/{payload['test_script_count']}** geslaagd",
        f"- Mislukt: **{payload['failed_script_count']}**",
        f"- Expliciet gerapporteerde skips: **{payload['reported_skip_count']}**",
        f"- Doorlooptijd: **{payload['elapsed_seconds']:.1f} s**",
        f"- Virtueel display: **{payload['use_xvfb']}**",
        "",
        "| Script | Status | Tijd | Skips |",
        "|---|---|---:|---:|",
    ]
    for item in results:
        lines.append(
            f"| `{item['script']}` | {item['status']} | {item['duration_seconds']:.2f} s | {item['reported_skips']} |"
        )
    (output / "VIEWER_V4_FULL_SMOKE_REPORT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=360)
    parser.add_argument("--no-xvfb", action="store_true")
    args = parser.parse_args()
    result = run(
        args.output.resolve(),
        timeout_seconds=max(30, int(args.timeout)),
        use_xvfb=not args.no_xvfb,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "scripts": result["test_script_count"],
                "failed": result["failed_script_count"],
                "skips": result["reported_skip_count"],
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
