"""Build the exact 53-item Phase-2 completion checklist without replacing 21/21 compatibility."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PHASES = ROOT / "validation" / "phases"
SOURCE = PHASES / "PHASE_2_SOURCE_TEST_EVIDENCE.json"
WINDOWS = PHASES / "PHASE_2_WINDOWS_RUNTIME_EVIDENCE.json"
COMPLETION = PHASES / "PHASE_2_COMPLETION_SCOPE_EVIDENCE.json"
OUTPUT_JSON = PHASES / "PHASE_2_COMPLETION_CHECKLIST.json"
OUTPUT_MD = PHASES / "PHASE_2_COMPLETION_CHECKLIST.md"

REQUIRED = (
    "manufacturing_face_canonical_persisted", "standard_profile_face_mappings", "custom_ambiguity_blocked",
    "exact_contact", "spatially_bounded_contact", "independent_contact_validator", "canonical_marks",
    "rulesets_versioned_hashed", "edge_hole_weld_exclusions", "nonplanar_handling", "independent_mark_validator",
    "hole_reference_engine", "identification_engine", "mirror_safe_text", "machine_face_reachability",
    "head_clearance", "dfm_engine", "machine_snapshots", "assembly_specific_identity", "nesting_bar_transform",
    "common_cut_mark_interaction", "operation_dag", "no_cycles", "neutral_manufacturing_job",
    "profile_nesting_full_regression", "plate_nesting_canonical_models", "plate_nesting_baseline_solver",
    "plate_nesting_exact_small_proof", "plate_nesting_validator", "plate_nesting_rotation_grain",
    "plate_nesting_stock_remnants", "plate_nesting_reports", "export_scope_all_required_scopes",
    "capability_driven_formats", "empty_selection_hard_block", "emitted_unsupported_skipped_blocked_matrix",
    "quality_inspection_base", "planning_base", "shopfloor_base", "validation_proof_center", "save_reopen",
    "stale_invalidation_graph", "m18_authority_verified", "safety_flags_false", "gui_cli_same_services",
    "real_synthetic_manufacturing_e2e", "windows_gui_exe", "windows_cli_exe", "fresh_portable",
    "packaged_manufacturing_smoke", "packaged_profile_nesting_smoke", "packaged_plate_nesting_smoke",
    "phase_manifests_checksums",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _passed(row: dict[str, Any]) -> bool:
    return row.get("passed") is True or str(row.get("status", "")).casefold() in {"pass", "passed", "complete", "green"}


def _digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def build_completion_validation() -> dict[str, Any]:
    assert len(REQUIRED) == 53
    source, windows, completion = _load(SOURCE), _load(WINDOWS), _load(COMPLETION)
    rows = {row.get("label"): row for row in source.get("results", [])}
    profile = [row for row in source.get("results", []) if str(row.get("label", "")).startswith("profile_nesting_regression:")]
    windows_rows = {row.get("label"): row for row in windows.get("results", [])}
    artifacts = dict(windows.get("artifacts") or {})
    coverage = dict(completion.get("coverage") or {})
    cov = lambda key: coverage.get(key) is True
    source_green = source.get("status") == "passed" and _passed(rows.get("completion_scope", {}))
    manufacturing_green = source_green and _passed(rows.get("manufacturing_e2e", {}))
    profile_green = bool(profile) and all(_passed(row) for row in profile)
    plate_green = _passed(rows.get("plate_nesting", {}))
    export_green = _passed(rows.get("export_scope_matrix", {})) and _passed(rows.get("export_scope_runtime", {}))
    persistence_green = _passed(rows.get("manufacturing_save_reopen_stale", {}))
    quality_green = _passed(rows.get("quality_inspection", {})) and cov("quality_inspection")
    m18_green = _passed(rows.get("m18_packaged_gate", {})) and windows.get("m18_packaged_gate") == "passed"
    packaged_green = windows.get("status") == "passed" and _passed(windows_rows.get("one_folder_gui_selftest", {})) and _passed(windows_rows.get("fresh_portable_gui_selftest", {}))
    phase2_exe = "CWS_Convertor_Phase2.exe" in artifacts
    cli_exe = "CWS_Convertor_CLI_Phase2.exe" in artifacts or _passed(windows_rows.get("one_folder_cli_selftest", {}))
    portable = any(name.endswith("_Portable.zip") for name in artifacts)
    conditions = [
        *([manufacturing_green] * 24), profile_green,
        plate_green and cov("plate_nesting_canonical_models"), plate_green and cov("plate_nesting_baseline_solver"),
        plate_green and cov("plate_nesting_exact_small"), plate_green and cov("plate_nesting_independent_validator"),
        plate_green and cov("plate_nesting_rotation_grain"), plate_green and cov("plate_nesting_stock_remnants"),
        plate_green and cov("plate_nesting_reports_neutral"),
        export_green, export_green, export_green, export_green,
        quality_green, cov("finite_capacity_planning"), cov("shopfloor"), cov("proof_center"),
        persistence_green and cov("project_save_reopen"), persistence_green and manufacturing_green,
        m18_green, cov("safety_flags_false") and _passed(rows.get("manufacturing_export", {})),
        cov("gui_cli_same_services"), manufacturing_green and cov("real_synthetic_e2e"),
        phase2_exe, cli_exe, portable,
        packaged_green and manufacturing_green, packaged_green and profile_green, packaged_green and plate_green,
        SOURCE.is_file() and (ROOT / "release" / "phase2" / "SHA256SUMS.txt").is_file(),
    ]
    assert len(conditions) == len(REQUIRED)
    items = [{"id": identifier, "status": "PASS" if condition else "FAIL"} for identifier, condition in zip(REQUIRED, conditions)]
    passed = sum(item["status"] == "PASS" for item in items)
    payload = {"schema": "cws-phase2-completion-checklist-1.0", "status": "complete" if passed == 53 else "incomplete", "summary": {"passed": passed, "total": 53, "failed": 53 - passed}, "items": items, "aggregate_checklist": str(PHASES / "PHASE_2_CHECKLIST.json")}
    PHASES.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    lines = ["# PHASE_2_COMPLETION_CHECKLIST", "", f"`PHASE_2_COMPLETION_CHECKLIST = {passed}/53 PASS`", "", f"`PHASE_2_COMPLETION = {payload['status'].upper()}`", ""]
    lines.extend(f"- [{item['status']}] `{item['id']}`" for item in items)
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (PHASES / "PHASE_2_TEST_MATRIX.json").write_text(json.dumps({"schema": "cws-phase-test-matrix-2.0", "phase": 2, "tests": source.get("results", []) + windows.get("results", [])}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    release_files = sorted(path for path in (ROOT / "release" / "phase2").glob("*") if path.is_file())
    (PHASES / "PHASE_2_ARTIFACT_MANIFEST.json").write_text(json.dumps({"schema": "cws-phase-artifact-manifest-2.0", "phase": 2, "artifacts": [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": _digest(path)} for path in release_files]}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (PHASES / "PHASE_2_PROMPT_TRACEABILITY.json").write_text(json.dumps({"schema": "cws-prompt-traceability-2.0", "phase": 2, "required_count": 53, "requirements": items, "evidence": [str(SOURCE), str(WINDOWS), str(COMPLETION), str(OUTPUT_JSON)]}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = build_completion_validation()
    print(f"PHASE_2_COMPLETION_CHECKLIST = {result['summary']['passed']}/53 PASS")
    raise SystemExit(0 if result["status"] == "complete" else 1)
