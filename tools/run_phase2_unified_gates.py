from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation" / "phases" / "PHASE_2_SOURCE_TEST_EVIDENCE.json"


def _run(label: str, command: list[str], *, environment: dict[str, str] | None = None) -> dict:
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=ROOT, env=environment, text=True, capture_output=True, timeout=900)
    return {
        "label": label,
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "duration_seconds": round(time.perf_counter() - started, 6),
        "command": command,
        "stdout_tail": completed.stdout[-12000:],
        "stderr_tail": completed.stderr[-12000:],
    }


def main() -> int:
    python = sys.executable
    cases: list[tuple[str, list[str], dict[str, str] | None]] = [
        ("source_compile", [python, "-m", "compileall", "-q", "cws_convertor", "cws_viewer", "tools"], None),
        ("phase1_unified_regression", [python, "tools/run_phase1_unified_gates.py"], None),
        ("manufacturing_e2e", [python, "tests/phase2_manufacturing_e2e_smoke.py"], None),
        ("plate_nesting", [python, "tests/phase2_plate_nesting_smoke.py"], None),
        ("export_scope_matrix", [python, "tests/phase2_export_scope_matrix_smoke.py"], None),
        ("manufacturing_save_reopen_stale", [python, "tests/phase2_manufacturing_persistence_smoke.py"], None),
        ("manufacturing_export", [python, "tests/viewer_v15_manufacturing_export_smoke.py"], None),
        ("export_scope_runtime", [python, "tests/viewer_v15_export_center_smoke.py"], None),
        ("viewer_full_width_context", [python, "tests/phase1_phase2_context_e2e_gui_smoke.py"], None),
    ]
    profile_tests = sorted(path for path in (ROOT / "tests").glob("*nesting*smoke.py") if "plate_nesting" not in path.name)
    for path in profile_tests:
        cases.append((f"profile_nesting_regression:{path.stem}", [python, str(path.relative_to(ROOT))], None))
    m18_env = os.environ.copy()
    runtime = ROOT / "dist" / "CWS_Convertor"
    if runtime.is_dir():
        m18_env["CWS_PHASE2_RUNTIME_DIR"] = str(runtime)
    cases.append(("m18_packaged_gate", [python, "tests/phase2_m18_packaged_gate_smoke.py"], m18_env))
    results = [_run(label, command, environment=environment) for label, command, environment in cases]
    payload = {
        "schema": "cws-phase2-source-test-evidence-1.0",
        "status": "passed" if all(item["status"] == "passed" for item in results) else "failed",
        "profile_nesting_regression_files": [str(path.relative_to(ROOT)) for path in profile_tests],
        "results": results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    passed = sum(item["status"] == "passed" for item in results)
    print(f"PHASE_2_UNIFIED_GATES = {passed}/{len(results)} PASS")
    print(OUTPUT)
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
