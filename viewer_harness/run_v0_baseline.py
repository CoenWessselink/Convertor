"""Run every smoke script independently and emit an auditable JSON summary."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any


def _tail(text: str, limit: int = 12000) -> str:
    return text if len(text) <= limit else text[-limit:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=900, help="Timeout in seconds per smoke script")
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    logs = output.parent / f"{output.stem}_logs"
    logs.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    if args.reference_root is not None:
        env["CWS_REFERENCE_ROOT"] = str(args.reference_root.resolve())

    scripts = sorted((repo / "tests").glob("*_smoke.py"))
    results: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc)

    for script in scripts:
        command = [sys.executable, str(script)]
        before = time.perf_counter()
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=repo,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=args.timeout,
                check=False,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = 124
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stderr += f"\nTIMEOUT after {args.timeout} seconds\n"
        duration = time.perf_counter() - before
        log_path = logs / f"{script.stem}.log"
        log_path.write_text(
            "$ " + " ".join(command) + "\n\n=== STDOUT ===\n" + stdout + "\n=== STDERR ===\n" + stderr,
            encoding="utf-8",
        )
        result = {
            "script": script.name,
            "command": command,
            "status": "passed" if exit_code == 0 else ("timeout" if timed_out else "failed"),
            "exit_code": exit_code,
            "duration_seconds": round(duration, 3),
            "log": str(log_path.relative_to(output.parent)),
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }
        results.append(result)
        print(f"[{result['status'].upper():7}] {script.name} ({duration:.2f}s)", flush=True)

    finished = datetime.now(timezone.utc)
    passed = sum(item["status"] == "passed" for item in results)
    failed = len(results) - passed
    payload = {
        "schema_version": "1.0",
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "repo": str(repo),
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "reference_root": env.get("CWS_REFERENCE_ROOT", ""),
        "script_count": len(results),
        "passed": passed,
        "failed": failed,
        "status": "passed" if failed == 0 else "failed",
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Result: {passed}/{len(results)} passed; report={output}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
