"""Create the required initial Phase-1 checklist and manifest set."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_VERSION, CANONICAL_PART_SCHEMA_VERSION, PROJECT_SCHEMA_VERSION


OUT = ROOT / "validation" / "phases"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def item(item_id: str, status: str, evidence: str, command: str = "") -> dict[str, str]:
    return {"id": item_id, "status": status, "command": command, "evidence": evidence}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    gui = ROOT / "dist" / "CWS_Convertor" / "CWS_Convertor.exe"
    cli = ROOT / "dist" / "CWS_Convertor" / "CWS_Convertor_CLI.exe"
    source_evidence_path = OUT / "PHASE_1_SOURCE_TEST_EVIDENCE.json"
    windows_evidence_path = OUT / "PHASE_1_WINDOWS_RUNTIME_EVIDENCE.json"
    repository_evidence_path = OUT / "PHASE_1_REPOSITORY_CI_EVIDENCE.json"
    source_evidence = load_json(source_evidence_path)
    windows_evidence = load_json(windows_evidence_path)
    repository_evidence = load_json(repository_evidence_path)
    progressive_evidence_path = OUT / "PHASE_1_PROGRESSIVE_PERFORMANCE.json"
    large_model_evidence_path = OUT / "PHASE_1_LARGE_MODEL_PERFORMANCE.json"
    exact_workbench_evidence_path = ROOT / "validation" / "viewer_v6" / "VIEWER_V6_VALIDATION_RESULTS.json"
    progressive_evidence = load_json(progressive_evidence_path)
    large_model_evidence = load_json(large_model_evidence_path)
    exact_workbench_evidence = load_json(exact_workbench_evidence_path)
    source_green = source_evidence.get("status") == "PASS"
    windows_green = windows_evidence.get("status") == "PASS"
    performance_green = (
        progressive_evidence.get("status") == "passed"
        and large_model_evidence.get("status") == "passed"
    )
    real_roundtrip_green = (
        large_model_evidence.get("status") == "passed"
        and exact_workbench_evidence.get("status") == "passed"
    )
    portable_candidates = sorted((ROOT / "release" / "phase1").glob("CWS_Convertor_Phase1_*_Portable.zip"))
    portable = portable_candidates[-1] if portable_candidates else ROOT / "release" / "phase1" / "MISSING.zip"
    sums = ROOT / "release" / "phase1" / "SHA256SUMS.txt"
    windows_manifest = ROOT / "release" / "phase1" / "PHASE_1_WINDOWS_MANIFEST.json"
    source_status = "PASS" if source_green else "NOT_TESTED"
    windows_status = "PASS" if windows_green else "NOT_TESTED"
    checks = [
        item(
            "current_branch_head_recorded",
            "PASS" if repository_evidence.get("branch_head_recorded") else "NOT_TESTED",
            str(repository_evidence_path),
        ),
        item(
            "required_ci_actually_runs",
            "PASS" if repository_evidence.get("required_ci_green") else "FAIL",
            str(repository_evidence_path),
        ),
        item(
            "no_uncommitted_production_code",
            "PASS" if repository_evidence.get("working_tree_clean") else "FAIL",
            str(repository_evidence_path),
        ),
        item("current_authority", "PASS", "docs/CURRENT_PRODUCT_AUTHORITY.md"),
        item("one_explicit_shell", source_status, str(source_evidence_path)),
        item("one_permanent_viewer_host", source_status, str(source_evidence_path)),
        item("no_production_import_time_viewer_monkeypatch", source_status, str(source_evidence_path)),
        item("full_application_context", source_status, str(source_evidence_path)),
        item("one_job_manager_contract", source_status, str(source_evidence_path)),
        item("project_identity_e2e", source_status, str(source_evidence_path)),
        item("selection_e2e", source_status, str(source_evidence_path)),
        item("camera_visibility_section_e2e", source_status, str(source_evidence_path)),
        item("progressive_large_model_path", source_status, str(source_evidence_path)),
        item(
            "viewer_performance_metrics",
            "PASS" if performance_green else "NOT_TESTED",
            f"{progressive_evidence_path}; {large_model_evidence_path}",
        ),
        item("bounded_picking", source_status, str(source_evidence_path)),
        item("one_workbench_write_path", source_status, str(source_evidence_path)),
        item("canonical_rebuild", source_status, str(source_evidence_path)),
        item("independent_geometry_validator", source_status, str(source_evidence_path)),
        item("transaction_rollback", source_status, str(source_evidence_path)),
        item("exact_scene_refresh", source_status, str(source_evidence_path)),
        item("converter_capability_registry", source_status, str(source_evidence_path)),
        item("reimport_roundtrip", source_status, str(source_evidence_path)),
        item(
            "real_source_result_difference",
            "PASS" if real_roundtrip_green else "NOT_TESTED",
            f"{large_model_evidence_path}; {exact_workbench_evidence_path}",
        ),
        item("vector_canonical_drawing", source_status, str(source_evidence_path)),
        item("geometry_anchored_dimensions", source_status, str(source_evidence_path)),
        item("drawing_linter", source_status, str(source_evidence_path)),
        item("trusted_pdf", source_status, str(source_evidence_path)),
        item("bom_reconciliation", source_status, str(source_evidence_path)),
        item("export_scope_empty_selection_block", source_status, str(source_evidence_path)),
        item("save_reopen", source_status, str(source_evidence_path)),
        item("safety_flags_false", source_status, str(source_evidence_path)),
        item("full_relevant_regressions", source_status, str(source_evidence_path)),
        item("source_gui_smoke", source_status, str(source_evidence_path)),
        item("windows_gui_exe", "PASS" if windows_green and gui.is_file() else "FAIL", str(gui)),
        item("windows_cli_exe", "PASS" if windows_green and cli.is_file() else "FAIL", str(cli)),
        item("fresh_portable_zip", "PASS" if windows_green and portable.is_file() else "FAIL", str(portable)),
        item("exe_quick_self_test", windows_status, str(windows_evidence_path)),
        item("exe_gui_smoke", windows_status, str(windows_evidence_path)),
        item("phase1_manifest_checksums", "PASS" if windows_green and sums.is_file() and windows_manifest.is_file() else "FAIL", str(windows_manifest)),
    ]
    fail_count = sum(check["status"] == "FAIL" for check in checks)
    not_tested_count = sum(check["status"] == "NOT_TESTED" for check in checks)
    phase_status = "COMPLETE" if not fail_count and not not_tested_count else ("FAILED" if fail_count else "PARTIAL")
    payload = {
        "schema": "cws-phase-checklist-1.0",
        "phase": 1,
        "status": phase_status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "product": "CWS Convertor",
        "version": APP_VERSION,
        "project_model": PROJECT_SCHEMA_VERSION,
        "canonical_part": CANONICAL_PART_SCHEMA_VERSION,
        "checks": checks,
        "counts": {status: sum(check["status"] == status for check in checks) for status in ("PASS", "FAIL", "BLOCKED", "NOT_TESTED")},
    }
    (OUT / "PHASE_1_CHECKLIST.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Phase 1 checklist", "", f"Status: `{payload['status']}`", ""]
    lines.extend(f"- [{check['status']}] `{check['id']}` - {check['evidence']}" for check in checks)
    (OUT / "PHASE_1_CHECKLIST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    matrix = {
        "schema": "cws-phase-test-matrix-1.0",
        "phase": 1,
        "tests": [check for check in checks if "test" in check["id"] or "regression" in check["id"] or "smoke" in check["id"]],
    }
    (OUT / "PHASE_1_TEST_MATRIX.json").write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts = {
        "schema": "cws-phase-artifact-manifest-1.0",
        "phase": 1,
        "artifacts": [
            {"path": str(path.relative_to(ROOT)), "exists": path.is_file(), "sha256": digest(path), "size": path.stat().st_size if path.is_file() else 0}
            for path in (gui, cli, portable, sums, windows_manifest)
        ],
    }
    (OUT / "PHASE_1_ARTIFACT_MANIFEST.json").write_text(json.dumps(artifacts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    changes = {
        "schema": "cws-phase-change-manifest-1.0",
        "phase": 1,
        "changes": [
            "Complete ApplicationContext state fields and deterministic state hash",
            "Complete central JobManager contract with scope, timeout, resource budget, result hash and error code",
            "Freeze current product authority and classify old handover as historical",
            "Create conservative Phase-1 checklist/test/artifact/change manifests",
        ],
    }
    (OUT / "PHASE_1_CHANGE_MANIFEST.json").write_text(json.dumps(changes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
