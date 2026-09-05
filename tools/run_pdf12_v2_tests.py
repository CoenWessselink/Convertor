"""Run the dedicated PDF-12 V2 source suite and write machine-readable totals."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TESTS = (
    "tests/interactive_dimension_editor_v2_smoke.py",
    "tests/interactive_dimension_editor_v2_acceptance_smoke.py",
    "tests/interactive_dimension_editor_v2_gui_smoke.py",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "validation" / "pdf12_interactive_dimension_v2" / "PDF12_INTERACTIVE_DIMENSION_V2_TEST_RESULTS.json",
    )
    args = parser.parse_args(argv)
    rows = []
    total = failed = skipped = 0
    for relative in TESTS:
        completed = subprocess.run(
            [sys.executable, str(ROOT / relative)],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=900,
        )
        combined = completed.stdout + "\n" + completed.stderr
        match = re.search(r"Ran\s+(\d+)\s+tests?", combined)
        count = int(match.group(1)) if match else 0
        skipped_match = re.search(r"skipped=(\d+)", combined)
        skip_count = int(skipped_match.group(1)) if skipped_match else 0
        failure_count = len(re.findall(r"^(?:FAIL|ERROR):", combined, flags=re.MULTILINE))
        passed = completed.returncode == 0 and count > 0 and skip_count == 0 and failure_count == 0
        total += count
        skipped += skip_count
        failed += failure_count + (0 if passed or failure_count else 1)
        rows.append(
            {
                "script": relative,
                "status": "PASS" if passed else "FAIL",
                "tests": count,
                "failed": failure_count,
                "skipped": skip_count,
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-8000:],
            }
        )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip().lower()
    passed = all(row["status"] == "PASS" for row in rows) and total >= 23 and failed == 0 and skipped == 0
    payload = {
        "schema": "cws-pdf12-v2-test-results-2.0",
        "status": "PASS" if passed else "FAIL",
        "commit": commit,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": {"tests": total, "passed": total - failed - skipped, "failed": failed, "skipped": skipped},
        "suites": rows,
    }
    target = args.output.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PDF12_V2_TESTS = {payload['status']} ({total} tests, {failed} failed, {skipped} skipped)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
