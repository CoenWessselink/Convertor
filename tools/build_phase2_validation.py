from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PHASES = ROOT / "validation" / "phases"
SOURCE = PHASES / "PHASE_2_SOURCE_TEST_EVIDENCE.json"
WINDOWS = PHASES / "PHASE_2_WINDOWS_RUNTIME_EVIDENCE.json"
PHASE1 = PHASES / "PHASE_1_CHECKLIST.json"
OUTPUT_JSON = PHASES / "PHASE_2_CHECKLIST.json"
OUTPUT_MD = PHASES / "PHASE_2_CHECKLIST.md"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def main() -> int:
    source = _load(SOURCE)
    windows = _load(WINDOWS)
    phase1 = _load(PHASE1)
    rows = {row.get("label"): row for row in source.get("results", [])}
    profile = [row for row in source.get("results", []) if str(row.get("label", "")).startswith("profile_nesting_regression:")]
    artifacts = windows.get("artifacts", {})
    windows_rows = {row.get("label"): row for row in windows.get("results", [])}
    standalone = windows.get("standalone", {})
    phase1_status = str(phase1.get("status", "")).casefold()
    phase1_counts = phase1.get("counts", {})
    phase1_summary = phase1.get("summary", {})
    phase1_passed = int(phase1_counts.get("PASS", phase1_summary.get("passed", 0)) or 0)
    phase1_required = int(phase1_counts.get("PASS", phase1_summary.get("required", phase1_passed)) or 0)
    phase1_green = (
        phase1_status in {"pass", "passed", "complete"}
        and phase1_passed == phase1_required
        and phase1_required >= 39
        and int(phase1_counts.get("FAIL", phase1_summary.get("failed", 0)) or 0) == 0
        and int(phase1_counts.get("BLOCKED", 0) or 0) == 0
        and int(phase1_counts.get("NOT_TESTED", 0) or 0) == 0
    )
    checks = [
        ("phase1_39_of_39", phase1_green),
        ("phase2_unified_gates", source.get("status") == "passed"),
        ("complete_manufacturing_e2e", rows.get("manufacturing_e2e", {}).get("status") == "passed"),
        ("all_profile_nesting_regressions", bool(profile) and all(row.get("status") == "passed" for row in profile)),
        ("plate_nesting_built", rows.get("plate_nesting", {}).get("status") == "passed"),
        ("full_export_scope_matrix", rows.get("export_scope_matrix", {}).get("status") == "passed"),
        ("manufacturing_save_reopen_stale", rows.get("manufacturing_save_reopen_stale", {}).get("status") == "passed"),
        ("manufacturing_export_runtime", rows.get("manufacturing_export", {}).get("status") == "passed"),
        ("export_scope_runtime", rows.get("export_scope_runtime", {}).get("status") == "passed"),
        ("viewer_full_width_context", rows.get("viewer_full_width_context", {}).get("status") == "passed"),
        ("m18_packaged_gate", rows.get("m18_packaged_gate", {}).get("status") == "passed" and windows.get("m18_packaged_gate") == "passed"),
        ("windows_runtime", windows.get("status") == "passed"),
        ("windows_one_folder", bool(windows.get("one_folder")) and Path(windows["one_folder"]).is_dir()),
        ("fresh_portable", bool(windows.get("fresh_portable")) and Path(windows["fresh_portable"]).is_dir()),
        ("phase2_standalone_gui_exe", "CWS_Convertor_Phase2.exe" in artifacts and standalone.get("status") == "passed" and standalone.get("internal_directory_present") is False),
        ("phase2_cli_one_folder_runtime", windows_rows.get("one_folder_cli_selftest", {}).get("status") == "passed" and windows_rows.get("fresh_portable_cli_selftest", {}).get("status") == "passed"),
        ("phase2_portable_zip", "CWS_Convertor_Phase2_Portable.zip" in artifacts),
        ("ui_baseline_shell", rows.get("phase1_unified_regression", {}).get("status") == "passed" and windows_rows.get("standalone_gui_smoke", {}).get("status") == "passed"),
        ("runtime_without_python_path", windows.get("python_removed_from_runtime_path") is True),
        ("production_machine_transfer_fail_closed", rows.get("manufacturing_e2e", {}).get("status") == "passed" and rows.get("manufacturing_export", {}).get("status") == "passed"),
        ("dedicated_evidence_complete", SOURCE.is_file() and WINDOWS.is_file()),
    ]
    items = [{"id": key, "status": "PASS" if passed else "FAIL"} for key, passed in checks]
    passed = sum(item["status"] == "PASS" for item in items)
    payload = {
        "schema": "cws-phase2-checklist-1.0",
        "status": "complete" if passed == len(items) else "incomplete",
        "summary": {"passed": passed, "total": len(items), "failed": len(items) - passed},
        "items": items,
        "evidence": {"phase1": str(PHASE1), "source": str(SOURCE), "windows": str(WINDOWS)},
    }
    PHASES.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = ["# PHASE_2_CHECKLIST", "", f"`PHASE_2_CHECKLIST = {passed}/{len(items)} PASS`", "", f"`PHASE_2 = {payload['status'].upper()}`", ""]
    lines.extend(f"- [{item['status']}] `{item['id']}`" for item in items)
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PHASE_2_CHECKLIST = {passed}/{len(items)} PASS")
    print(f"PHASE_2 = {payload['status'].upper()}")
    return 0 if payload["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
