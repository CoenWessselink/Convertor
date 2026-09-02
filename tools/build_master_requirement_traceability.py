from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS_ROOT = ROOT / "requirements"
SOURCE_ROOT = REQUIREMENTS_ROOT / "sources"
EVIDENCE_ROOT = ROOT / "validation" / "final_4_phase"
VALID_STATUSES = {
    "PASS", "FAIL", "BLOCKED", "NOT_TESTED", "NOT_APPLICABLE",
    "BLOCKED_EXTERNAL_EVIDENCE",
}

SOURCE_FILES = (
    "CODEX_SUPERPROMPT_CWS_CONVERTOR_100PCT_FINAL_4_FASEN_2026-08-31.md",
    "CODEX_SUPERPROMPT_CWS_CONVERTOR_UNIFIED_3_FASEN_2026-08-27.md",
    "CODEX_SUPERPROMPT_CWS_COMPLETION_100PCT_3_FASEN_2026-08-28.md",
    "CODEX_SUPERPROMPT_CWS_FULL_PRODUCT_ACCEPTANCE_TEST_2026-08-28.md",
    "CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md",
    "CODEX_SUPERPROMPT_CWS_UI_MASTER_V5_COMPLETE_3_FASEN_2026-08-31.md",
    "CODEX_SUPERPROMPT_CWS_UI_MASTER_V5_1_FINAL_3_FASEN_2026-08-31.md",
    "CODEX_SUPERPROMPT_CWS_UI_CONTROLS_VISUAL_FIDELITY_V5_1_2026-08-31.md",
    "CODEX_SUPERPROMPT_CWS_UI_V5_2_CONTROL_BUILD_3_FASEN_2026-08-31.md",
    "CODEX_SUPERPROMPT_CWS_GAP_CLOSURE_VIEWER_V5_3_FASEN_2026-08-31_V2_UI_CORRECTED.md",
    "CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md",
    "CODEX_SUPERPROMPT_CWS_MANUFACTURING_GEOMETRY_INTERPRETER_V2_3_FASEN_2026-08-31.md",
    "CWS_CONVERTOR_COMPLETE_GAP_ANALYSIS_2026-08-31.md",
    "CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json",
)

# One row is one independently reportable product obligation. Screen/control
# rows are appended from the canonical V5.2 manifests below.
CORE_REQUIREMENTS = (
    ("F1-001", 1, "All active requirement sources are versioned and reconciled without silent deletion", ("requirements/",), ("tests/final_master_traceability_smoke.py",)),
    ("F1-002", 1, "Canonical product authorities remain unique and no parallel Viewer/Project/BOM engines are introduced", ("docs/CURRENT_PRODUCT_AUTHORITY.md", "cws_convertor/integration/ui_context.py"), ("tests/final_gap_closure_smoke.py",)),
    ("F1-003", 1, "IFC geometry uses a bounded persistent process worker pool with recovery and clean shutdown", ("cws_viewer/geometry/worker_pool.py",), ("tests/performance_loading_v2_smoke.py",)),
    ("F1-004", 1, "Geometry priority is dynamic, viewport-aware, hysteretic and starvation-safe", ("cws_viewer/performance/priority.py",), ("tests/viewer_performance_closeout_smoke.py",)),
    ("F1-005", 1, "MeshCache V2 persists complete mesh payloads atomically and rejects corruption", ("cws_viewer/cache/mesh_cache.py",), ("tests/performance_loading_v2_smoke.py",)),
    ("F1-006", 1, "Scene uploads are generation-safe and bounded by per-frame time budgets", ("cws_viewer/performance/scene_upload.py",), ("tests/performance_loading_v2_smoke.py",)),
    ("F1-007", 1, "ViewerPerformanceGovernor controls interaction, recovery and idle rendering quality including MSAA", ("cws_viewer/performance/governor.py",), ("tests/viewer_performance_closeout_smoke.py",)),
    ("F1-008", 1, "Packaged cold, warm and same-session metrics include first usable, exact milestones, p95/p99 and memory/process counts", ("cws_viewer/core/real_performance_evidence.py",), ("tools/run_viewer_performance_closeout.py",)),
    ("F1-009", 1, "A real ten-minute OpenGL Viewer soak proves bounded actors, workers and memory", ("tools/run_viewer_performance_closeout.py",), ("tools/run_viewer_performance_closeout.py",)),
    ("F1-010", 1, "Viewer interaction, selection, visibility, section, measurement and saved-view behavior remains functional", ("cws_viewer/ui_qt/vtk_real_project_widget_feel_v2.py",), ("tests/viewer_v15_layout_navigation_acceptance.py",)),
    ("F1-011", 1, "Unified intake handles IFC, STEP, NC1, Trusted PDF, External PDF and project packages fail-closed", ("cws_convertor/ui_qt/project_intake.py", "cws_convertor/project/service.py"), ("tests/final_gap_closure_smoke.py",)),
    ("F1-012", 1, "Project state and user preferences are versioned, separated and recover safely", ("cws_convertor/project/storage.py", "cws_convertor/ui_qt/design_system/preferences.py"), ("tests/viewer_v9_workbench_persistence_smoke.py",)),
    ("F1-013", 1, "The exact primary navigation is Project, Viewer, Productie, Controle, Uitvoer", ("cws_convertor/ui_qt/u4_shell.py",), ("tests/ui_v51_binding_contract_smoke.py",)),
    ("F1-014", 1, "V5.2 design system is light-first with a dark preference smoke path and yellow whole-object selection", ("cws_convertor/ui_qt/design_system/",), ("tests/ui_v52_foundation_smoke.py",)),
    ("F1-015", 1, "Owned controls use stable ui_test_id identity and central control/icon registries", ("cws_convertor/ui_qt/design_system/", "cws_convertor/ui_qt/ui_v51_contract.py"), ("tests/ui_v51_binding_contract_smoke.py",)),
    ("F2-001", 2, "BOM is the immutable quantity truth with exact reconciliation and full traceability", ("cws_convertor/bom/",), ("tests/phase2_completion_scope_smoke.py",)),
    ("F2-002", 2, "BOM and Machines joins production state through canonical IDs", ("cws_convertor/ui_qt/product_workspaces.py",), ("tests/phase2_completion_scope_smoke.py",)),
    ("F2-003", 2, "Machine routing has one versioned AUTO/MANUAL assignment authority", ("cws_convertor/manufacturing/routing.py",), ("tests/final_gap_closure_smoke.py",)),
    ("F2-004", 2, "Invalid machine overrides remain REVIEW/BLOCKED and never authorize transfer", ("cws_convertor/manufacturing/routing.py",), ("tests/phase2_completion_scope_smoke.py",)),
    ("F2-005", 2, "Machine library validates ranges, tools, operations, priorities and active state", ("cws_convertor/manufacturing/machine_settings.py",), ("tests/test_manufacturing_workspace_completion.py",)),
    ("F2-006", 2, "Workbench remains the single transactional write path with rollback and undo/redo", ("cws_convertor/project/workbench.py",), ("tests/viewer_v9_workbench_persistence_smoke.py",)),
    ("F2-007", 2, "Canonical rebuild and roundtrip invalidate stale derivatives", ("cws_convertor/project/canonical_rebuild.py", "cws_convertor/project/roundtrip.py"), ("tests/phase2_manufacturing_persistence_smoke.py",)),
    ("F2-008", 2, "Manufacturing Geometry Interpreter V2 uses source topology, hypotheses and independent reconstruction", ("cws_convertor/manufacturing_interpreter/",), ("tests/manufacturing_interpreter_phase1_smoke.py",)),
    ("F2-009", 2, "Interpreter exact READY requires two-way BREP proof and false READY remains zero", ("cws_convertor/manufacturing_interpreter/service.py",), ("tests/manufacturing_interpreter_phase1_smoke.py",)),
    ("F2-010", 2, "Existing faces, contact, scribing, identification, capability and neutral-job chain remains authoritative", ("cws_convertor/manufacturing/",), ("tests/test_manufacturing_workspace_completion.py",)),
    ("F2-011", 2, "Profile nesting preserves machine/tool/stock/remnant constraints and deterministic proof", ("cws_convertor/optimization/profile_nesting/",), ("tests/phase2_completion_scope_smoke.py",)),
    ("F2-012", 2, "Plate nesting supports polygon geometry, holes, grain, rotations, remnants, locks and exact validation", ("cws_convertor/optimization/plate_nesting/",), ("tests/phase2_plate_nesting_smoke.py", "tests/phase2_completion_scope_smoke.py")),
    ("F2-013", 2, "Converter capability registry blocks every feature not proven by serializer and reimport comparator", ("cws_convertor/conversion_capabilities.py", "cws_convertor/conversion_worker.py"), ("tests/final_gap_closure_smoke.py",)),
    ("F2-014", 2, "Productie screens and controls operate on the same canonical project and selection", ("cws_convertor/ui_qt/u4_shell.py", "cws_convertor/ui_qt/v5_workspaces.py"), ("tests/unified_u4_gui_smoke.py",)),
    ("F2-015", 2, "Routing, nesting and production state survive save and reopen", ("cws_convertor/project/storage.py",), ("tests/phase2_manufacturing_persistence_smoke.py",)),
    ("F3-001", 3, "One production drawing engine emits vector geometry, dimensions, annotations and title blocks", ("cws_convertor/drawings/", "cws_convertor/ui_qt/engineering_drawing.py"), ("tests/production_drawing_engine_smoke.py",)),
    ("F3-002", 3, "Production drawing PDF remains sharp at 800 percent and is not a full-page raster", ("cws_convertor/drawings/renderer.py",), ("tests/production_drawing_engine_smoke.py", "tests/part_drawing_standard_smoke.py")),
    ("F3-003", 3, "Drawing linter blocks incomplete, stale, clipped or raster-only production pages", ("cws_convertor/drawings/linter.py",), ("tests/production_drawing_engine_smoke.py",)),
    ("F3-004", 3, "Trusted PDF payload and hash verification fails closed on tamper", ("pdf_support.py", "cws_convertor/drawings/renderer.py"), ("tests/production_drawing_engine_smoke.py", "tests/pdf_ai_smoke.py")),
    ("F3-005", 3, "External PDF remains evidence/confidence gated and REVIEW_REQUIRED until proven", ("pdf_support.py", "ai_support.py"), ("tests/final_gap_closure_smoke.py",)),
    ("F3-006", 3, "One DocumentOutputService owns preview, print and batch output", ("cws_convertor/ui_qt/production_printing.py",), ("tests/final_gap_closure_smoke.py",)),
    ("F3-007", 3, "Ctrl+P opens the context Print Center and printer failure is fail-closed", ("cws_convertor/ui_qt/v5_workspaces.py", "cws_convertor/ui_qt/ui_v51_contract.py"), ("tests/phase3_workspaces_gui_smoke.py",)),
    ("F3-008", 3, "Controle exposes validation, compare, manufacturability, geometry, evidence and PDF review", ("cws_convertor/ui_qt/u4_shell.py",), ("tests/phase3_workspaces_gui_smoke.py",)),
    ("F3-009", 3, "Problem Center reports blockers, errors and warnings without false green", ("cws_convertor/ui_qt/ui_v51_contract.py",), ("tests/ui_v51_binding_contract_smoke.py",)),
    ("F3-010", 3, "Quality inspection supports plans, measurements, NCR, rework, reinspection and release blocking", ("cws_convertor/quality/",), ("tests/phase3_quality_inspection_smoke.py",)),
    ("F3-011", 3, "Planning owns resources, work centers, shifts, requirements, orders and scheduled operations", ("cws_convertor/production.py",), ("tests/phase2_completion_scope_smoke.py",)),
    ("F3-012", 3, "Finite-capacity scheduling respects availability, maintenance, material, priority and due dates", ("cws_convertor/production.py",), ("tests/phase2_completion_scope_smoke.py",)),
    ("F3-013", 3, "Shopfloor transitions and quality hooks remain bounded and auditable", ("cws_convertor/production.py", "cws_convertor/quality/"), ("tests/phase3_quality_inspection_smoke.py",)),
    ("F3-014", 3, "Export uses Scope to Formats to Preflight to Generate to Verify to Package without scope broadening", ("cws_convertor/production_export/",), ("tests/final_gap_closure_smoke.py",)),
    ("F3-015", 3, "Readiness joins geometry, manufacturing, routing, nesting, drawing, quality and planning gates", ("cws_convertor/production_export/readiness.py",), ("tests/phase2_completion_scope_smoke.py",)),
    ("F3-016", 3, "All 25 reference and 6 support surfaces are functional in the real Qt runtime", ("cws_convertor/ui_qt/", "docs/ui/v5_2/"), ("tests/ui_v51_binding_contract_smoke.py",)),
    ("F4-001", 4, "Dynamic full acceptance is generated from this master traceability", ("tools/run_full_product_acceptance.py", "requirements/"), ("tests/final_master_traceability_smoke.py",)),
    ("F4-002", 4, "Runtime owned-control scan proves no missing, duplicate, dead or wrong-handler controls", ("cws_convertor/ui_qt/design_system/control_registry.py",), ("tests/ui_v51_binding_contract_smoke.py",)),
    ("F4-003", 4, "Visual acceptance covers required resolutions and DPI with light primary and dark smoke", ("cws_convertor/ui_qt/design_system/",), ("tests/phase3_visual_dpi_smoke.py",)),
    ("F4-004", 4, "Full IFC, STEP, NC1, Trusted PDF and External PDF workflows are tested end to end", ("tools/run_full_product_acceptance.py",), ("tools/run_full_product_acceptance.py",)),
    ("F4-005", 4, "Negative file, cache, worker, cancellation, stale-state and capacity paths fail closed", ("tests/",), ("tools/run_full_product_acceptance.py",)),
    ("F4-006", 4, "Stress suite proves bounded workspace, selection, camera, save, import/export and optimization behavior", ("tools/run_full_product_acceptance.py",), ("tools/run_full_product_acceptance.py",)),
    ("F4-007", 4, "Final Viewer cold/warm/same-session, interaction and resource metrics are packaged evidence", ("tools/run_viewer_performance_closeout.py",), ("tools/run_viewer_performance_closeout.py",)),
    ("F4-008", 4, "One-folder black-box runtime works without developer Python PATH", ("CWS_Convertor.spec",), ("tools/finalize_windows_release.py",)),
    ("F4-009", 4, "Fresh portable black-box runtime works without developer Python PATH", ("tools/finalize_windows_release.py",), ("tools/finalize_windows_release.py",)),
    ("F4-010", 4, "Fresh installer black-box runtime works and preserves file associations", ("installer/CWS_Convertor.iss",), ("tools/finalize_windows_release.py",)),
    ("F4-011", 4, "Source zip, git bundle, checksums, SBOM and manifests bind to one exact source SHA", ("tools/finalize_commit_bound_release.py",), ("tools/finalize_commit_bound_release.py",)),
    ("F4-012", 4, "Required FAIL, BLOCKED and NOT_TESTED counts are zero with false green zero", ("requirements/MASTER_REQUIREMENT_TRACEABILITY.json",), ("tools/run_full_product_acceptance.py",)),
    ("F4-013", 4, "Physical machine transfer remains blocked pending external qualification", ("cws_convertor/production.py",), ("tests/phase2_completion_scope_smoke.py",)),
    ("F4-014", 4, "Release evidence and binaries are rebuilt after every code change and name the exact SHA", ("tools/finalize_commit_bound_release.py",), ("tools/finalize_commit_bound_release.py",)),
)

SUPERSEDED = (
    {"requirement_id": "LEGACY-NAV-12", "description": "Twelve legacy top-level product tabs", "superseded_by": "F1-013"},
    {"requirement_id": "LEGACY-DARK-DEFAULT", "description": "Engineering Dark as mandatory/default product theme", "superseded_by": "F1-014"},
    {"requirement_id": "LEGACY-ACCEPTANCE-51", "description": "A fixed 51-check report as complete current acceptance", "superseded_by": "F4-001"},
    {"requirement_id": "LEGACY-RASTER-DRAWING", "description": "Full-page raster production PDF route", "superseded_by": "F3-001"},
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _phase_gate(phase: int) -> dict[str, Any]:
    path = EVIDENCE_ROOT / f"phase{phase}" / "PHASE_GATE.json"
    if not path.is_file():
        return {"status": "NOT_TESTED", "path": path}
    payload = json.loads(path.read_text(encoding="utf-8"))
    status = str(payload.get("status", "NOT_TESTED"))
    if status not in VALID_STATUSES:
        raise ValueError(f"Ongeldige status in {path}: {status}")
    payload["path"] = path
    return payload


def _screen_phase(screen_id: str) -> int:
    value = int(screen_id)
    if value <= 10 or value == 30:
        return 1
    if 11 <= value <= 18 or value == 26:
        return 2
    return 3


def _row(requirement_id: str, phase: int, description: str, implementations: tuple[str, ...], tests: tuple[str, ...], *, source: str, source_section: str) -> dict[str, Any]:
    gate = _phase_gate(phase)
    status = str(gate.get("status", "NOT_TESTED"))
    proven = status == "PASS"
    return {
        "requirement_id": requirement_id,
        "phase": phase,
        "source": source,
        "source_section": source_section,
        "description": description,
        "priority": "P0",
        "superseded_by": None,
        "implementation_paths": list(implementations),
        "test_paths": list(tests),
        "evidence_paths": [str(Path(gate["path"]).relative_to(ROOT)).replace("\\", "/")],
        "implemented": proven,
        "integrated": proven,
        "tested": proven,
        "packaged_proven": bool(proven and gate.get("packaged_proven", False)),
        "status": status,
    }


def build() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    sources = []
    for name in SOURCE_FILES:
        path = SOURCE_ROOT / name
        sources.append({
            "name": name,
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "present": path.is_file(),
            "sha256": _sha(path) if path.is_file() else None,
        })
    rows = [
        _row(req_id, phase, description, implementations, tests,
             source=SOURCE_FILES[0], source_section=f"Fase {phase}")
        for req_id, phase, description, implementations, tests in CORE_REQUIREMENTS
    ]
    screen_manifest = json.loads((ROOT / "docs/ui/v5_2/spec/SCREEN_MANIFEST.json").read_text(encoding="utf-8"))
    control_manifest = json.loads((ROOT / "docs/ui/v5_2/spec/CONTROL_INVENTORY_MASTER.json").read_text(encoding="utf-8"))
    for screen in screen_manifest["screens"]:
        screen_id = str(screen["screen_id"])
        rows.append(_row(
            f"UI-SCREEN-{screen_id}", _screen_phase(screen_id),
            f"Runtime surface {screen_id} {screen['title']} matches its active structural and functional contract",
            ("cws_convertor/ui_qt/",), ("tests/ui_v51_binding_contract_smoke.py",),
            source="SCREEN_MANIFEST.json", source_section=screen_id,
        ))
    for control in control_manifest["controls"]:
        screen_id = str(control["screen_id"])
        phase = 4 if screen_id == "GLOBAL" else _screen_phase(screen_id)
        rows.append(_row(
            f"UI-CONTROL-{control['test_id']}", phase,
            f"Control {control['test_id']} ({control.get('label', '')}) is present, uniquely owned and invokes its declared contract",
            ("cws_convertor/ui_qt/ui_v51_contract.py",), ("tests/ui_v51_binding_contract_smoke.py",),
            source="CONTROL_INVENTORY_MASTER.json", source_section=screen_id,
        ))
    if len({row["requirement_id"] for row in rows}) != len(rows):
        raise RuntimeError("Duplicate requirement_id in active traceability")
    statuses = Counter(row["status"] for row in rows)
    now = datetime.now(timezone.utc).isoformat()
    trace = {
        "schema": "cws-master-requirement-traceability-2.0",
        "generated_at": now,
        "source_authority": SOURCE_FILES[0],
        "sources": sources,
        "required_total": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "requirements": rows,
    }
    active = {
        "schema": "cws-active-requirements-1.0", "generated_at": now,
        "required_total": len(rows), "requirements": rows,
    }
    superseded = {
        "schema": "cws-superseded-requirements-1.0", "generated_at": now,
        "requirements": list(SUPERSEDED),
    }
    return trace, active, superseded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-sources", action="store_true")
    args = parser.parse_args()
    REQUIREMENTS_ROOT.mkdir(parents=True, exist_ok=True)
    trace, active, superseded = build()
    if args.check_sources:
        missing = [item["name"] for item in trace["sources"] if not item["present"]]
        if missing:
            raise SystemExit("Missing requirement sources: " + ", ".join(missing))
    for name, payload in (
        ("MASTER_REQUIREMENT_TRACEABILITY.json", trace),
        ("ACTIVE_REQUIREMENTS.json", active),
        ("SUPERSEDED_REQUIREMENTS.json", superseded),
    ):
        (REQUIREMENTS_ROOT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# CWS Convertor Master Requirement Traceability", "",
        f"Generated: `{trace['generated_at']}`", "",
        f"Active requirements: **{trace['required_total']}**", "",
        "## Status", "",
        "| Status | Count |", "|---|---:|",
    ]
    lines.extend(f"| {status} | {count} |" for status, count in trace["status_counts"].items())
    lines += ["", "## Requirement sources", ""]
    lines.extend(f"- `{item['name']}`: {'PRESENT' if item['present'] else 'MISSING'}" for item in trace["sources"])
    lines += ["", "## Core product requirements", "", "| ID | Phase | Status | Requirement |", "|---|---:|---|---|"]
    for row in trace["requirements"]:
        if not row["requirement_id"].startswith("UI-"):
            lines.append(f"| {row['requirement_id']} | {row['phase']} | {row['status']} | {row['description']} |")
    (REQUIREMENTS_ROOT / "MASTER_REQUIREMENT_TRACEABILITY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"required_total": trace["required_total"], "status_counts": trace["status_counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
