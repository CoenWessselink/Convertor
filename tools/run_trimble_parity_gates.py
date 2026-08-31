"""Run the reproducible CWS Viewer observable parity gate."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_trimble_parity_validation import OUTPUT, build_validation

MODULES = (
    "tests.trimble_parity_evidence_contract_smoke",
    "tests.test_trimble_observable_parity",
    "tests.viewer_v15_navigation_contract_smoke",
    "tests.viewer_v15_selection_pivot_parity_smoke",
    "tests.viewer_v15_trimble_feel_v2_smoke",
    "tests.viewer_v15_trimble_input_contract_smoke",
    "tests.viewer_v15_phase2_parity_smoke",
    "tests.viewer_v15_selection_measurement_smoke",
    "tests.viewer_v15_workspace_contract_smoke",
    "tests.viewer_v15_review_workspace_smoke",
    "tests.viewer_v15_layout_navigation_acceptance",
)


def main() -> int:
    started = time.perf_counter()
    environment = os.environ.copy()
    environment.setdefault(
        "CWS_VIEWER_ACCEPTANCE_PROJECT",
        str(Path.home() / "Documents" / "CWS Convertor Projects" / "out (11).cwscproj"),
    )
    command = [sys.executable, "-m", "unittest", "-v", *MODULES]
    module_runs = []
    for module in MODULES:
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", module],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        module_runs.append(
            {
                "module": module,
                "status": "PASS" if completed.returncode == 0 else "FAIL",
                "return_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
    return_code = 0 if all(row["status"] == "PASS" for row in module_runs) else 1
    duration = round(time.perf_counter() - started, 3)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    gate_run = {
        "schema": "cws-trimble-parity-gate-run-1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if return_code == 0 else "FAIL",
        "return_code": return_code,
        "duration_seconds": duration,
        "command": command,
        "modules": list(MODULES),
        "module_statuses": {row["module"]: row["status"] for row in module_runs},
        "module_runs": module_runs,
        "stdout": "\n".join(row["stdout"] for row in module_runs if row["stdout"]),
        "stderr": "\n".join(row["stderr"] for row in module_runs if row["stderr"]),
    }
    (OUTPUT / "TRIMBLE_PARITY_GATE_RUN.json").write_text(
        json.dumps(gate_run, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    checklist = build_validation(gate_run)
    print(json.dumps(checklist, indent=2))
    if checklist["status"] == "PASS":
        return 0
    if checklist["status"] == "BLOCKED_EXTERNAL_EVIDENCE":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
