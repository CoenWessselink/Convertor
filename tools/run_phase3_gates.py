"""Run the complete unified Phase-3 source, UI, real-file and soak gates."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PHASES = ROOT / "validation" / "phases"
RESULTS = ROOT / "validation" / "results" / "phase3"
DEFAULT_OUTPUT = PHASES / "PHASE_3_SOURCE_TEST_EVIDENCE.json"

GROUPS = {
    "negative_regression": (
        "tests/production_export_negative_smoke.py",
        "tests/viewer_v15_marking_smoke.py",
        "tests/viewer_v15_machine_capability_smoke.py",
        "tests/viewer_v15_nesting_binding_smoke.py",
        "tests/viewer_v15_neutral_job_smoke.py",
        "tests/phase2_plate_nesting_smoke.py",
    ),
    "golden_e2e": (
        "tests/phase1_phase2_context_e2e_gui_smoke.py",
        "tests/phase2_manufacturing_e2e_smoke.py",
        "tests/production_release_package_smoke.py",
        "tests/phase3_quality_inspection_smoke.py",
    ),
    "acceptance": (
        "tests/viewer_v15_selection_measurement_smoke.py",
        "tests/viewer_v15_selection_pivot_parity_smoke.py",
        "tests/part_drawing_standard_smoke.py",
        "tests/phase2_manufacturing_persistence_smoke.py",
        "tests/phase2_export_scope_matrix_smoke.py",
        "tests/phase2_m18_packaged_gate_smoke.py",
        "tests/phase3_completion_smoke.py",
        "tests/phase3_workspaces_gui_smoke.py",
    ),
}


def run(command: list[str], *, timeout: int) -> dict[str, object]:
    started = time.perf_counter()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        value
        for value in (str(ROOT), str(ROOT / "src"), environment.get("PYTHONPATH", ""))
        if value
    )
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def reused_result(path: Path, *, passed: bool, label: str) -> dict[str, object]:
    return {
        "command": ["reuse-fresh-evidence", label, str(path)],
        "returncode": 0 if passed else 1,
        "passed": bool(passed),
        "duration_seconds": 0.0,
        "stdout": f"Reused fresh evidence: {path}",
        "stderr": "",
    }


def is_fresh(path: Path, *, maximum_age_seconds: float = 7200.0) -> bool:
    return path.is_file() and time.time() - path.stat().st_mtime <= maximum_age_seconds


def failure_summary(manifest: dict[str, object]) -> dict[str, object]:
    """Return compact, log-safe diagnostics for every failed Phase-3 gate."""

    coverage = dict(manifest.get("coverage") or {})
    failures: list[dict[str, object]] = []

    def add(label: str, result: object) -> None:
        if not isinstance(result, dict) or bool(result.get("passed")):
            return
        failures.append(
            {
                "label": label,
                "command": result.get("command"),
                "returncode": result.get("returncode"),
                "stdout_tail": str(result.get("stdout") or "")[-1200:],
                "stderr_tail": str(result.get("stderr") or "")[-1200:],
            }
        )

    add("full_regression", manifest.get("full_regression"))
    for group, results in dict(manifest.get("groups") or {}).items():
        for index, result in enumerate(results if isinstance(results, list) else []):
            add(f"group:{group}:{index + 1}", result)
    add("real_file", manifest.get("real_file"))
    add("ui_acceptance", manifest.get("ui_acceptance"))
    add("soak", manifest.get("soak"))
    return {
        "failed_coverage": sorted(key for key, value in coverage.items() if not value),
        "failed_commands": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--soak-seconds", type=float, default=600.0)
    parser.add_argument("--reuse-fresh-evidence", action="store_true")
    args = parser.parse_args()
    PHASES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    soak_path = PHASES / "PHASE_3_SOAK_EVIDENCE.json"
    reusable_soak_payload: dict[str, object] | None = None
    if args.reuse_fresh_evidence and is_fresh(soak_path):
        candidate = json.loads(soak_path.read_text(encoding="utf-8"))
        if (
            candidate.get("status") == "passed"
            and float(candidate.get("elapsed_seconds", 0.0)) >= float(args.soak_seconds)
            and all(bool(value) for value in candidate.get("checks", {}).values())
        ):
            reusable_soak_payload = candidate
    regression_summary_path = RESULTS / "source-smokes" / "VIEWER_V9_FULL_SMOKE_SUMMARY.json"
    if args.reuse_fresh_evidence and is_fresh(regression_summary_path):
        regression_summary = json.loads(regression_summary_path.read_text(encoding="utf-8"))
        counts = regression_summary.get("counts", {})
        regression_passed = counts.get("failed", 0) == 0 and counts.get("timeout", 0) == 0
        full_regression = reused_result(
            regression_summary_path,
            passed=regression_passed,
            label="full-regression",
        )
    else:
        full_regression = run(
            [sys.executable, str(ROOT / "validation" / "run_all_smokes_v9.py"),
             "--headless-windows", "--output", str(RESULTS / "source-smokes")],
            timeout=1800,
        )
    grouped: dict[str, list[dict[str, object]]] = {}
    for group, scripts in GROUPS.items():
        grouped[group] = [run([sys.executable, str(ROOT / script)], timeout=600) for script in scripts]
    real_file_path = PHASES / "PHASE_3_REAL_FILE_MATRIX.json"
    real_file = run([sys.executable, str(ROOT / "tests" / "phase3_real_file_matrix.py"),
                     "--output", str(real_file_path)], timeout=900)
    ui_path = PHASES / "PHASE_3_UI_ACCEPTANCE.json"
    ui = run([sys.executable, str(ROOT / "tests" / "phase3_visual_dpi_smoke.py"),
              "--output", str(ui_path)], timeout=600)
    if reusable_soak_payload is not None:
        soak_path.write_text(
            json.dumps(reusable_soak_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        soak = reused_result(soak_path, passed=True, label="phase3-soak")
    else:
        soak = run(
            [sys.executable, str(ROOT / "tests" / "phase3_soak_smoke.py"),
             "--duration-seconds", str(args.soak_seconds), "--output", str(soak_path)],
            timeout=max(1200, int(args.soak_seconds) + 300),
        )
    runtime = ROOT / "cws_convertor" / "manufacturing" / "m18_authority_runtime.zip"
    runtime_bytes = runtime.read_bytes() if runtime.is_file() else b""
    runtime_hash = sha256(runtime_bytes).hexdigest()
    m18 = {
        "path": str(runtime), "bytes": len(runtime_bytes), "sha256": runtime_hash,
        "exact": len(runtime_bytes) == 233402
        and runtime_hash == "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1",
    }
    group_status = {name: all(item["passed"] for item in items) for name, items in grouped.items()}
    coverage = {
        "full_software_regression": bool(full_regression["passed"]),
        "full_negative_regression": group_status["negative_regression"],
        "real_file_matrix": bool(real_file["passed"]),
        "golden_e2e_project": group_status["golden_e2e"],
        "save_reopen_migration": group_status["acceptance"],
        "picking_correctness": group_status["acceptance"],
        "vector_trusted_drawing": group_status["acceptance"],
        "manufacturing_nesting_sequence_export": group_status["acceptance"] and group_status["negative_regression"],
        "quality_inspection": group_status["golden_e2e"],
        "visual_dpi_keyboard": bool(ui["passed"]),
        "memory_soak_no_leaks": bool(soak["passed"]),
        "m18_authority": bool(m18["exact"]),
    }
    passed = all(coverage.values())
    manifest = {
        "schema": "cws-phase3-source-evidence-2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "GREEN" if passed else "RED",
        "coverage": coverage,
        "full_regression": full_regression,
        "groups": grouped,
        "real_file": {**real_file, "evidence": str(real_file_path)},
        "ui_acceptance": {**ui, "evidence": str(ui_path)},
        "soak": {**soak, "evidence": str(soak_path), "required_minimum_seconds": 600.0},
        "m18": m18,
        "safety": {
            "machine_observed_by_cws": False,
            "deployment_transport_authorized": False,
            "direct_machine_transfer": False,
            "machine_transfer.allowed": False,
        },
    }
    output_path = args.output / DEFAULT_OUTPUT.name if args.output.is_dir() else args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not passed:
        print("PHASE_3_FAILURE_SUMMARY=" + json.dumps(failure_summary(manifest), sort_keys=True))
    print(f"PHASE_3_SOURCE_GATES = {'PASS' if passed else 'FAIL'}")
    print(output_path)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
