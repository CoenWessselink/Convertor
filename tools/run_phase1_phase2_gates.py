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
GATES = (
    ("unit_contract", "tests/core_phase0_baseline_smoke.py"),
    ("project_import", "tests/unified_project_schema_u1_smoke.py"),
    ("project_import", "tests/step_semantic_import_smoke.py"),
    ("project_import", "tests/ifc_semantic_import_smoke.py"),
    ("viewer_v15", "tests/viewer_v15_workspace_contract_smoke.py"),
    ("viewer_v15", "tests/unified_viewer_v15_u3_smoke.py"),
    ("viewer_v15", "tests/viewer_v15_selection_measurement_smoke.py"),
    ("workbench", "tests/part_workbench_smoke.py"),
    ("workbench", "tests/part_workbench_roundtrip_smoke.py"),
    ("conversion", "tests/viewer_v6_roundtrip_smoke.py"),
    ("drawing", "tests/part_drawing_standard_smoke.py"),
    ("manufacturing_m1_m18", "tests/manufacturing_face_core_smoke.py"),
    ("manufacturing_m1_m18", "tests/manufacturing_contact_core_smoke.py"),
    ("manufacturing_m1_m18", "tests/unified_manufacturing_scribing_u2_smoke.py"),
    ("profile_nesting", "tests/viewer_v15_nesting_binding_smoke.py"),
    ("production_export", "tests/production_export_smoke.py"),
    ("production_export", "tests/production_export_negative_smoke.py"),
    ("bom_reporting", "tests/project_bom_smoke.py"),
    ("bom_reporting", "tests/bom_production_hub_smoke.py"),
    ("phase1_phase2", "tests/phase1_phase2_completion_smoke.py"),
    ("qt_headless_gui", "tests/phase1_phase2_context_e2e_gui_smoke.py"),
    ("qt_headless_gui", "tests/unified_ui_shell_u3_gui_smoke.py"),
    ("qt_headless_gui", "tests/unified_u4_gui_smoke.py"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run classified CWS phase 1/2 gates")
    parser.add_argument("--output", type=Path, default=ROOT / "build/evidence/phase1_phase2_tests.json")
    args = parser.parse_args()
    environment = dict(os.environ)
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    environment.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
    results = []
    for category, relative in GATES:
        path = ROOT / relative
        if not path.is_file():
            results.append({"category": category, "test": relative, "status": "not_run", "reason": "missing"})
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
        output = completed.stdout or ""
        skipped = sum(int(value) for value in re.findall(r"skipped=(\d+)", output))
        status = "pass" if completed.returncode == 0 else "fail"
        results.append(
            {
                "category": category,
                "test": relative,
                "status": status,
                "skip_count": skipped,
                "return_code": completed.returncode,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "output_tail": output[-4000:],
            }
        )
        print(f"[{status.upper()}] {category}: {relative}")
    counts = {status: sum(item["status"] == status for item in results) for status in ("pass", "fail", "skip", "not_run")}
    payload = {
        "schema": "cws-phase1-phase2-test-evidence-1.0",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.executable,
        "counts": counts,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(args.output)
    return 1 if counts["fail"] or counts["not_run"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
