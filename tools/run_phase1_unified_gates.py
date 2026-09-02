"""Run the Phase-1 source acceptance matrix without Phase-2/M18 gates."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation" / "phases" / "PHASE_1_SOURCE_TEST_EVIDENCE.json"
TESTS = (
    ("architecture", "tests/core_phase0_baseline_smoke.py"),
    ("project_identity", "tests/unified_project_schema_u1_smoke.py"),
    ("project_identity", "tests/step_semantic_import_smoke.py"),
    ("project_identity", "tests/ifc_semantic_import_smoke.py"),
    ("viewer", "tests/viewer_v15_workspace_contract_smoke.py"),
    ("viewer", "tests/unified_viewer_v15_u3_smoke.py"),
    ("viewer", "tests/viewer_v15_selection_measurement_smoke.py"),
    ("workbench", "tests/part_workbench_smoke.py"),
    ("workbench", "tests/part_workbench_roundtrip_smoke.py"),
    ("conversion", "tests/viewer_v6_roundtrip_smoke.py"),
    ("drawing", "tests/part_drawing_standard_smoke.py"),
    ("drawing", "tests/production_drawing_engine_smoke.py"),
    ("export", "tests/viewer_v15_export_center_smoke.py"),
    ("export", "tests/production_export_smoke.py"),
    ("export", "tests/production_export_negative_smoke.py"),
    ("bom", "tests/project_bom_smoke.py"),
    ("context_jobs", "tests/phase1_context_job_contract_smoke.py"),
    ("profile_nesting_commands", "tests/phase1_profile_nesting_command_service_smoke.py"),
    ("phase1_e2e", "tests/phase1_phase2_completion_smoke.py"),
    ("gui", "tests/phase1_phase2_context_e2e_gui_smoke.py"),
    ("gui", "tests/unified_ui_shell_u3_gui_smoke.py"),
    ("gui", "tests/unified_u4_gui_smoke.py"),
)


def main() -> int:
    environment = dict(os.environ)
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    environment.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
    results: list[dict[str, object]] = []
    compile_started = time.perf_counter()
    compile_result = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "cws_convertor", "cws_viewer", "CWS_Convertor_App.py"],
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    results.append(
        {
            "category": "code_quality",
            "test": "python -m compileall",
            "status": "PASS" if compile_result.returncode == 0 else "FAIL",
            "return_code": compile_result.returncode,
            "duration_seconds": round(time.perf_counter() - compile_started, 3),
            "output": (compile_result.stdout or "")[-4000:],
        }
    )
    for category, relative in TESTS:
        path = ROOT / relative
        if not path.is_file():
            results.append({"category": category, "test": relative, "status": "NOT_TESTED", "reason": "missing"})
            continue
        started = time.perf_counter()
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        results.append(
            {
                "category": category,
                "test": relative,
                "status": "PASS" if completed.returncode == 0 else "FAIL",
                "return_code": completed.returncode,
                "duration_seconds": round(time.perf_counter() - started, 3),
                "output": (completed.stdout or "")[-4000:],
            }
        )
        print(f"[{results[-1]['status']}] {category}: {relative}")
    counts = {
        status: sum(result["status"] == status for result in results)
        for status in ("PASS", "FAIL", "BLOCKED", "NOT_TESTED")
    }
    payload = {
        "schema": "cws-phase1-source-gate-1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.executable,
        "status": "PASS" if counts["FAIL"] == 0 and counts["NOT_TESTED"] == 0 else "FAIL",
        "counts": counts,
        "results": results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
