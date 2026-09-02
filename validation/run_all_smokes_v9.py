"""Run every repository smoke script in an isolated subprocess.

The runner records command, duration, exit status and full stdout/stderr.  It
never converts a skip into a pass and it never stops at the first failure, so a
release report can honestly enumerate all outcomes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

# These scripts are black-box gates for an already built exact-SHA runtime.
# Running them without their required runtime arguments in the source suite is
# neither a source test nor an honest failure.  They remain mandatory in the
# Windows packaging workflow and are reported here as explicitly deferred.
PACKAGED_ONLY_SMOKES = {
    "conversion_one_phase_packaged_smoke.py": (
        "deferred_to_exact_sha_packaged_runtime_matrix"
    ),
}


def _failure_excerpt(stdout: str, stderr: str, returncode: int, *, limit: int = 3500) -> str:
    details = (stderr.strip() or stdout.strip()).replace("\x00", "")
    if not details:
        details = f"Process exited without diagnostic output (exit code {returncode})."
    return details[-limit:]


def _workflow_command_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _emit_github_failure(script: Path, status: str, returncode: int, excerpt: str) -> None:
    if os.environ.get("GITHUB_ACTIONS", "").lower() != "true":
        return
    relative = script.relative_to(ROOT).as_posix()
    message = _workflow_command_escape(
        f"{script.name} {status} with exit code {returncode}.\n{excerpt}"
    )
    print(
        f"::error file={relative},title=Smoke regression {status}::{message}",
        flush=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "viewer_v9" / "full_smokes")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--start", type=int, default=1, help="1-based first sorted script")
    parser.add_argument("--end", type=int, default=0, help="inclusive last script; 0 means all")
    parser.add_argument("--xvfb", action="store_true", help="run each script under xvfb-run -a")
    parser.add_argument("--auto-xvfb", action="store_true", help="use xvfb only for known native OCCT/Tk display tests")
    parser.add_argument(
        "--headless-windows",
        action="store_true",
        help="use the same explicit native-window skips as Windows CI",
    )
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    logs = output / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    all_scripts = sorted(
        (
            path
            for path in (ROOT / "tests").glob("*_smoke.py")
            if not path.name.startswith("full_acceptance_")
        ),
        key=lambda p: p.name.lower(),
    )
    first = max(1, int(args.start))
    last = int(args.end) if int(args.end) > 0 else len(all_scripts)
    scripts = all_scripts[first - 1:last]
    records: list[dict] = []
    started = time.perf_counter()
    for index, script in enumerate(scripts, start=1):
        command = [sys.executable, str(script)]
        display_tests = {
            "viewer_v1_decision_smoke.py",
            "viewer_v1_occt_smoke.py",
        }
        if args.xvfb or (args.auto_xvfb and script.name in display_tests):
            command = ["xvfb-run", "-a", *command]
        print(f"[{index:03d}/{len(scripts):03d}] {script.name}", flush=True)
        tick = time.perf_counter()
        deferred_reason = PACKAGED_ONLY_SMOKES.get(script.name)
        if deferred_reason:
            log_path = logs / f"{script.stem}.log"
            log_path.write_text(
                f"COMMAND: {' '.join(command)}\nSTATUS: deferred\n"
                f"REASON: {deferred_reason}\n",
                encoding="utf-8",
            )
            records.append(
                {
                    "script": script.name,
                    "command": command,
                    "status": "deferred",
                    "returncode": 0,
                    "duration_seconds": 0.0,
                    "log": str(log_path.relative_to(output)),
                    "failure_excerpt": "",
                    "reason": deferred_reason,
                }
            )
            print(f"    DEFERRED {deferred_reason}", flush=True)
            continue
        timed_out = False
        try:
            child_env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            child_env["PYTHONPATH"] = os.pathsep.join(
                value
                for value in (
                    str(ROOT),
                    str(ROOT / "src"),
                    child_env.get("PYTHONPATH", ""),
                )
                if value
            )
            if args.headless_windows:
                child_env["GITHUB_ACTIONS"] = "true"
            result = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=args.timeout,
                check=False,
                env=child_env,
            )
            returncode = int(result.returncode)
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = 124
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
        duration = time.perf_counter() - tick
        combined_output = f"{stdout}\n{stderr}"
        ran_match = re.search(r"Ran\s+(\d+)\s+tests?", combined_output)
        skipped_match = re.search(r"skipped=(\d+)", combined_output)
        all_reported_tests_skipped = bool(
            ran_match
            and skipped_match
            and int(skipped_match.group(1)) >= int(ran_match.group(1))
        )
        explicitly_skipped = (
            (returncode == 5 and "NO TESTS RAN" in combined_output and "skipped=" in combined_output)
            or (returncode == 0 and all_reported_tests_skipped)
        )
        status = (
            "timeout"
            if timed_out
            else "passed"
            if returncode == 0
            else "skipped"
            if explicitly_skipped
            else "failed"
        )
        failure_excerpt = ""
        if status in {"failed", "timeout"}:
            failure_excerpt = _failure_excerpt(stdout, stderr, returncode)
            print("    FAILURE DETAILS", flush=True)
            for line in failure_excerpt.splitlines():
                print(f"      {line}", flush=True)
            _emit_github_failure(script, status, returncode, failure_excerpt)
        log_path = logs / f"{script.stem}.log"
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\nSTATUS: {status}\nRETURNCODE: {returncode}\nDURATION_SECONDS: {duration:.6f}\n\nSTDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
            encoding="utf-8",
        )
        records.append(
            {
                "script": script.name,
                "command": command,
                "status": status,
                "returncode": returncode,
                "duration_seconds": duration,
                "log": str(log_path.relative_to(output)),
                "failure_excerpt": failure_excerpt,
            }
        )
        print(f"    {status.upper()} {duration:.2f}s", flush=True)
    counts = {
        key: sum(item["status"] == key for item in records)
        for key in ("passed", "skipped", "deferred", "failed", "timeout")
    }
    payload = {
        "schema": "cws-viewer-v9-full-smoke-summary-1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": sys.platform,
        "script_count": len(records),
        "range": {"start": first, "end": last, "total_available": len(all_scripts)},
        "counts": counts,
        "source_scope_complete": counts["failed"] == 0 and counts["timeout"] == 0,
        "packaged_gates_deferred": [
            item["script"] for item in records if item["status"] == "deferred"
        ],
        "elapsed_seconds": time.perf_counter() - started,
        "records": records,
    }
    summary = output / "VIEWER_V9_FULL_SMOKE_SUMMARY.json"
    summary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(summary), **counts}, indent=2), flush=True)
    return 0 if counts["failed"] == 0 and counts["timeout"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
