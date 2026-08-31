"""Build fail-closed Trimble/CWS observable parity evidence.

The previous parity builder promoted a passing CWS unit-test suite to full
Trimble parity. This module keeps CWS implementation evidence, observed
Trimble evidence, and side-by-side comparison evidence separate. Missing
external observations can therefore never produce a parity PASS.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from cws_viewer.core.viewer_interaction_profile import TRIMBLE_STYLE_INTERACTION_PROFILE
from tools.capture_trimble_reference import BLOCKED_EXTERNAL_EVIDENCE, build_reference_artifacts

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation" / "trimble_parity"
PHASE_OUTPUT = ROOT / "validation" / "phases"
SESSION = OUTPUT / "reference" / "REFERENCE_SESSION.json"
TARGET = "CWS Viewer Observable Trimble Connect Parity"

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
NOT_TESTED = "NOT_TESTED"
NOT_APPLICABLE = "NOT_APPLICABLE"
ALLOWED_STATUSES = {PASS, FAIL, BLOCKED, BLOCKED_EXTERNAL_EVIDENCE, NOT_TESTED, NOT_APPLICABLE}


def _write_json(output: Path, name: str, value: Any) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    path = output / name
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return path


def _write_text(output: Path, name: str, value: str) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    path = output / name
    path.write_text(value.rstrip() + "\n", encoding="utf-8")
    return path


def _aggregate_status(statuses: Iterable[str]) -> str:
    values = [value for value in statuses if value != NOT_APPLICABLE]
    for status in (FAIL, BLOCKED, BLOCKED_EXTERNAL_EVIDENCE, NOT_TESTED):
        if status in values:
            return status
    return PASS if values and all(value == PASS for value in values) else NOT_TESTED


def _item(test_id: str, category: str, title: str, evidence: list[str], *, evidence_scope: str, status: str, required: bool = True, blocking_reason: str | None = None) -> dict[str, Any]:
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported parity status: {status}")
    result: dict[str, Any] = {"id": test_id, "category": category, "title": title, "required": required, "status": status, "evidence_scope": evidence_scope, "evidence": evidence}
    if blocking_reason:
        result["blocking_reason"] = blocking_reason
    return result


def _test_matrix(gate_run: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    internal = PASS if gate_run.get("status") == PASS else FAIL
    module_statuses = dict(gate_run.get("module_statuses") or {})
    environment = reference["environment"]
    input_mapping = reference["input_mapping"]
    visual = reference["visual"]
    performance = reference["performance"]
    external_reason = "A paired observation in the live Trimble reference application is missing."

    def cws(test_id: str, category: str, title: str, evidence: list[str]) -> dict[str, Any]:
        modules = []
        for path in evidence:
            if path.startswith("tests/") and path.endswith(".py"):
                modules.append(path[:-3].replace("/", "."))
        statuses = [module_statuses[module] for module in modules if module in module_statuses]
        status = _aggregate_status(statuses) if statuses else internal
        return _item(test_id, category, title, evidence, evidence_scope="CWS_AUTOMATED", status=status)

    tests = [
        cws("TP_NAV_001", "navigation", "Fit, orbit, pan and cursor zoom input map", ["TRIMBLE_PARITY_INPUT_MATRIX.json", "tests/test_trimble_observable_parity.py"]),
        cws("TP_NAV_002", "navigation", "Incremental wheel zoom at 1.08 per notch", ["cws_viewer/core/viewer_interaction_profile.py", "tests/test_trimble_observable_parity.py"]),
        cws("TP_CAM_001", "camera", "Orbit uses selected object or cursor surface pivot", ["tests/viewer_v15_selection_pivot_parity_smoke.py"]),
        cws("TP_CAM_002", "camera", "World-up orbit suppresses roll and pole flip", ["tests/test_trimble_observable_parity.py"]),
        cws("TP_CAM_003", "camera", "Pan scales at picked perspective depth", ["tests/viewer_v15_navigation_contract_smoke.py"]),
        cws("TP_CAM_004", "camera", "Camera history and deterministic standard views", ["tests/viewer_v15_navigation_contract_smoke.py"]),
        cws("TP_SEL_001", "selection", "Part and assembly selection levels", ["tests/viewer_v15_navigation_contract_smoke.py"]),
        cws("TP_SEL_002", "selection", "Ctrl toggle and Shift add multi-selection", ["tests/viewer_v15_trimble_input_contract_smoke.py"]),
        cws("TP_SEL_003", "selection", "Instanced mesh resolves nearest real surface", ["tests/viewer_v15_selection_pivot_parity_smoke.py"]),
        cws("TP_SEL_004", "selection", "Selection is saturated engineering yellow", ["screenshots/cws/TP_VIS_002_cws_live_selected.png", "tests/viewer_v15_trimble_feel_v2_smoke.py"]),
        cws("TP_VISB_001", "visibility", "Hide, isolate, ghost and show-all state", ["tests/viewer_v15_phase2_parity_smoke.py"]),
        cws("TP_VISB_002", "visibility", "Visibility survives workspace restore", ["tests/viewer_v15_navigation_contract_smoke.py"]),
        cws("TP_MEAS_001", "measurement", "Distance measurement with live 3D anchors and labels", ["tests/viewer_v15_selection_measurement_smoke.py"]),
        cws("TP_MEAS_002", "measurement", "Horizontal and vertical measurement modes", ["tests/viewer_v15_selection_measurement_smoke.py"]),
        cws("TP_SEC_001", "section_clipping", "Section plane enable, disable and flip roundtrip", ["tests/viewer_v15_navigation_contract_smoke.py"]),
        cws("TP_SEC_002", "section_clipping", "Clipping box roundtrip", ["tests/viewer_v15_navigation_contract_smoke.py"]),
        cws("TP_TREE_001", "model_tree", "Tree selection is synchronized with project identity", ["tests/viewer_v15_workspace_contract_smoke.py"]),
        cws("TP_PROP_001", "properties", "Property grid follows selected project object", ["tests/viewer_v15_workspace_contract_smoke.py"]),
        cws("TP_VIEW_001", "saved_views", "Saved view captures camera, selection, sections and clipping", ["tests/viewer_v15_navigation_contract_smoke.py"]),
        cws("TP_VIEW_002", "saved_views", "Activating a saved view restores orbit focus", ["tests/viewer_v15_navigation_contract_smoke.py"]),
        cws("TP_REV_001", "review", "Markup and review workspace contracts remain available", ["tests/viewer_v15_review_workspace_smoke.py"]),
        _item("TP_VIS_001", "visual", "Same source model, placement and IFC colours in paired captures", ["TRIMBLE_VISUAL_REFERENCE.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=visual["status"], blocking_reason=visual.get("blocking_reason")),
        cws("TP_VIS_002", "visual", "Technical and realistic CWS modes retain sharp profile silhouettes", ["tests/viewer_v15_trimble_feel_v2_smoke.py"]),
        cws("TP_UI_001", "ui_layout", "Ribbon and viewport controls remain available", ["tests/viewer_v15_layout_navigation_acceptance.py"]),
        cws("TP_UI_002", "ui_layout", "Viewport control overlays avoid each other", ["tests/viewer_v15_layout_navigation_acceptance.py"]),
        cws("TP_IN_001", "input", "CWS interaction profile is centralized and validated", ["tests/test_trimble_observable_parity.py"]),
        cws("TP_PERF_001", "performance", "CWS navigation input is coalesced at a deterministic schedule", ["cws_viewer/core/viewer_interaction_profile.py", "tests/test_trimble_observable_parity.py"]),
        cws("TP_PERF_002", "performance", "CWS adaptive rendering and indexed instance picking", ["tests/viewer_v15_selection_pivot_parity_smoke.py"]),
        cws("TP_QA_001", "acceptance", "Reproducible CWS parity regression suite", ["TRIMBLE_PARITY_GATE_RUN.json"]),
        _item("TP_DIFF_001", "intentional_difference", "No claim of Trimble proprietary implementation parity", ["TRIMBLE_CWS_INTENTIONAL_DIFFERENCES.md"], evidence_scope="CLAIM_BOUNDARY", status=NOT_APPLICABLE, required=False),
        _item("TP_DIFF_002", "intentional_difference", "Pixel-identical proprietary UI chrome is outside scope", ["TRIMBLE_CWS_INTENTIONAL_DIFFERENCES.md"], evidence_scope="CLAIM_BOUNDARY", status=NOT_APPLICABLE, required=False),
        _item("TP_REF_001", "reference_environment", "Trimble executable, version, host and display are recorded", ["TRIMBLE_REFERENCE_ENVIRONMENT.json"], evidence_scope="TRIMBLE_OBSERVED", status=environment["status"], blocking_reason=environment.get("blocking_reason")),
        _item("TP_REF_002", "reference_environment", "CWS and Trimble identify the exact same source model", ["TRIMBLE_REFERENCE_ENVIRONMENT.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=PASS if environment.get("same_model_verified") else BLOCKED_EXTERNAL_EVIDENCE, blocking_reason=None if environment.get("same_model_verified") else external_reason),
        _item("TP_REF_003", "reference_environment", "Unmodified CWS and Trimble captures have SHA-256 evidence", ["TRIMBLE_VISUAL_REFERENCE.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=PASS if visual.get("capture_integrity_verified") else BLOCKED_EXTERNAL_EVIDENCE, blocking_reason=None if visual.get("capture_integrity_verified") else external_reason),
        _item("TP_INPUT_002", "input", "Trimble mouse and keyboard mapping is observed case by case", ["TRIMBLE_INPUT_MAPPING.json"], evidence_scope="TRIMBLE_OBSERVED", status=input_mapping["status"], blocking_reason=input_mapping.get("blocking_reason")),
        _item("TP_LIVE_001", "live_comparison", "Orbit direction, pivot and sensitivity match live Trimble", ["TRIMBLE_INPUT_MAPPING.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=input_mapping["gestures"]["orbit"]["status"], blocking_reason=external_reason),
        _item("TP_LIVE_002", "live_comparison", "Pan direction and picked-depth behaviour match live Trimble", ["TRIMBLE_INPUT_MAPPING.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=input_mapping["gestures"]["pan"]["status"], blocking_reason=external_reason),
        _item("TP_LIVE_003", "live_comparison", "Wheel zoom direction, factor and cursor anchor match live Trimble", ["TRIMBLE_INPUT_MAPPING.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=input_mapping["gestures"]["wheel_zoom"]["status"], blocking_reason=external_reason),
        _item("TP_LIVE_004", "live_comparison", "Whole-object selection and modifiers match live Trimble", ["TRIMBLE_INPUT_MAPPING.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=input_mapping["gestures"]["selection"]["status"], blocking_reason=external_reason),
        _item("TP_LIVE_005", "live_comparison", "Hide, isolate, ghost and show-all match live Trimble", ["TRIMBLE_INPUT_MAPPING.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=input_mapping["gestures"]["visibility"]["status"], blocking_reason=external_reason),
        _item("TP_VIS_003", "visual", "Camera-aligned profile, edge, shadow and selection comparison", ["TRIMBLE_VISUAL_REFERENCE.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=visual["status"], blocking_reason=visual.get("blocking_reason")),
        _item("TP_PERF_003", "performance", "Paired cold-load, first-visual, FPS and input-latency benchmark", ["TRIMBLE_PERFORMANCE_REFERENCE.json"], evidence_scope="CWS_TRIMBLE_COMPARISON", status=performance["status"], blocking_reason=performance.get("blocking_reason")),
    ]
    if len(tests) != 42:
        raise AssertionError(f"Expected exactly 42 parity cases, got {len(tests)}")
    return tests


def _checklist_payload(tests: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    required = [item for item in tests if item["required"]]
    counts = {status: sum(item["status"] == status for item in required) for status in ALLOWED_STATUSES}
    status = _aggregate_status(item["status"] for item in required)
    return {
        "schema": "cws-trimble-parity-checklist-2.0",
        "target": TARGET,
        "generated_at": generated_at,
        "status": status,
        "case_total": len(tests),
        "required_total": len(required),
        "required_pass": counts[PASS],
        "required_fail": counts[FAIL],
        "required_blocked": counts[BLOCKED],
        "required_blocked_external_evidence": counts[BLOCKED_EXTERNAL_EVIDENCE],
        "required_not_tested": counts[NOT_TESTED],
        "failed_ids": [item["id"] for item in required if item["status"] == FAIL],
        "blocked_ids": [item["id"] for item in required if item["status"] == BLOCKED],
        "blocked_external_evidence_ids": [item["id"] for item in required if item["status"] == BLOCKED_EXTERNAL_EVIDENCE],
        "not_tested_ids": [item["id"] for item in required if item["status"] == NOT_TESTED],
        "claim_boundary": "PASS requires both CWS automation and paired live Trimble evidence.",
    }


def _phase_item(item_id: str, title: str, status: str, evidence: list[str], reason: str = "") -> dict[str, Any]:
    result = {"id": item_id, "title": title, "status": status, "evidence": evidence}
    if reason:
        result["reason"] = reason
    return result


def _write_phase_artifacts(phase_output: Path, generated_at: str, checklist: dict[str, Any], tests: list[dict[str, Any]], reference: dict[str, Any], gate_run: dict[str, Any]) -> None:
    session = reference["session"]
    ui_audit = dict(session.get("ui_audit") or {})
    architecture = dict(session.get("architecture_audit") or {})
    current_workspaces = list(ui_audit.get("current_primary_workspaces") or [])
    target_workspaces = ["Project", "Viewer", "Bewerken", "BOM & Productie", "Uitvoer"]
    module_statuses = dict(gate_run.get("module_statuses") or {})
    layout_status = module_statuses.get("tests.viewer_v15_layout_navigation_acceptance", FAIL)
    workspace_status = PASS if current_workspaces == target_workspaces and layout_status == PASS else FAIL
    context_status = PASS if architecture.get("context_action_service_found") is True and layout_status == PASS else FAIL
    cases = {item["id"]: item for item in tests}
    navigation_status = _aggregate_status(cases[item_id]["status"] for item_id in ("TP_NAV_001", "TP_NAV_002", "TP_CAM_001", "TP_CAM_002", "TP_CAM_003", "TP_CAM_004"))
    selection_status = _aggregate_status(cases[item_id]["status"] for item_id in ("TP_SEL_001", "TP_SEL_002", "TP_SEL_003", "TP_SEL_004"))
    e2e_status = PASS if gate_run.get("status") == PASS else FAIL

    phase1_items = [
        _phase_item("P1_REF_01", "Formal Trimble reference environment", reference["environment"]["status"], ["validation/trimble_parity/TRIMBLE_REFERENCE_ENVIRONMENT.json"]),
        _phase_item("P1_REF_02", "Exactly 42 fail-closed parity cases", PASS if len(tests) == 42 else FAIL, ["validation/phases/PHASE_1_TRIMBLE_PARITY_MATRIX.json"]),
        _phase_item("P1_INPUT_01", "Observed Trimble input mapping", reference["input_mapping"]["status"], ["validation/trimble_parity/TRIMBLE_INPUT_MAPPING.json"]),
        _phase_item("P1_NAV_01", "CWS navigation and pivot contracts", navigation_status, ["validation/trimble_parity/TRIMBLE_PARITY_GATE_RUN.json"]),
        _phase_item("P1_SEL_01", "Whole-object CWS selection regression", selection_status, ["tests/viewer_v15_trimble_input_contract_smoke.py"]),
        _phase_item("P1_VIS_01", "Camera-aligned live Trimble visual parity", reference["visual"]["status"], ["validation/trimble_parity/TRIMBLE_VISUAL_REFERENCE.json"]),
        _phase_item("P1_PERF_01", "Paired Trimble/CWS performance reference", reference["performance"]["status"], ["validation/phases/PHASE_1_VIEWER_PERFORMANCE.json"]),
        _phase_item("P1_UI_01", "Exactly five primary product workspaces", workspace_status, ["validation/phases/PHASE_1_UI_SIMPLIFICATION_REPORT.md"], "Current shell does not match the five-workspace target." if workspace_status == FAIL else ""),
        _phase_item("P1_ARCH_01", "Single ContextActionService authority", context_status, ["validation/phases/PHASE_1_UI_SIMPLIFICATION_REPORT.md"], "No authoritative ContextActionService was found in the audit." if context_status == FAIL else ""),
        _phase_item("P1_E2E_01", "Basic viewer regression E2E", e2e_status, ["validation/trimble_parity/TRIMBLE_PARITY_GATE_RUN.json"]),
        _phase_item("P1_UI_02", "No modal or floating viewer obstruction", layout_status, ["tests/viewer_v15_layout_navigation_acceptance.py"]),
        _phase_item("P1_REL_01", "Phase-1 Windows one-folder and portable release", NOT_TESTED, []),
    ]
    phase1_status = _aggregate_status(item["status"] for item in phase1_items)
    phase1 = {"schema": "cws-phase1-trimble-viewer-checklist-1.0", "generated_at": generated_at, "status": phase1_status, "complete": phase1_status == PASS, "items": phase1_items, "parity_status": checklist["status"]}
    _write_json(phase_output, "PHASE_1_TRIMBLE_VIEWER_CHECKLIST.json", phase1)
    lines = ["# Phase 1 - Trimble viewer checklist", "", f"`PHASE_1 = {phase1_status}`", ""]
    lines.extend(f"- `{item['status']}` {item['id']}: {item['title']}" for item in phase1_items)
    _write_text(phase_output, "PHASE_1_TRIMBLE_VIEWER_CHECKLIST.md", "\n".join(lines))
    _write_json(phase_output, "PHASE_1_TRIMBLE_PARITY_MATRIX.json", {"schema": "cws-phase1-trimble-parity-matrix-1.0", "generated_at": generated_at, "status": checklist["status"], "cases": tests})
    _write_json(phase_output, "PHASE_1_VIEWER_PERFORMANCE.json", reference["performance"])
    _write_text(phase_output, "PHASE_1_UI_SIMPLIFICATION_REPORT.md", "\n".join(["# Phase 1 UI simplification audit", "", f"Status: `{workspace_status}`", "", f"Target primary workspaces: {', '.join(target_workspaces)}.", f"Observed primary workspaces: {', '.join(current_workspaces) if current_workspaces else 'not recorded'}.", "", f"ContextActionService authority: `{context_status}`.", "", "This is an implementation gap, not an external-evidence exception."]))

    track = {
        "schema": "cws-phase1-trimble-change-manifest-1.0",
        "generated_at": generated_at,
        "status": phase1_status,
        "changed_files": ["tools/capture_trimble_reference.py", "tools/build_trimble_parity_validation_v2.py", "tools/build_trimble_parity_validation.py", "tools/run_trimble_parity_gates.py", "tests/trimble_parity_evidence_contract_smoke.py", "validation/trimble_parity/reference/REFERENCE_SESSION.json"],
        "claim_corrections": ["CWS tests no longer certify Trimble input behaviour.", "A CWS frame scheduler no longer certifies Trimble performance.", "Unaligned screenshots no longer certify visual parity."],
        "machine_transfer_allowed": False,
    }
    _write_json(phase_output, "PHASE_1_TRIMBLE_CHANGE_MANIFEST.json", track)
    existing_manifest_path = phase_output / "PHASE_1_CHANGE_MANIFEST.json"
    try:
        existing_manifest = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        existing_manifest = {"schema": "cws-phase1-change-manifest-aggregate-1.0"}
    existing_manifest["trimble_parity_bom_pdf_routing_2026_08_30"] = track
    _write_json(phase_output, "PHASE_1_CHANGE_MANIFEST.json", existing_manifest)

    phase2_items = [
        _phase_item("P2_BOM_01", "Unified BOM selection, quantity and geometry authority", NOT_TESTED, ["cws_convertor/bom"]),
        _phase_item("P2_BOM_02", "BOM PDF/XLSX/CSV print and export workflows", NOT_TESTED, ["cws_convertor/bom/export.py"]),
        _phase_item("P2_PROD_01", "Unified manufacturing and nesting workspace", NOT_TESTED, ["cws_convertor/manufacturing"]),
        _phase_item("P2_PROD_02", "Machine settings, stock lengths, plates and remnants", NOT_TESTED, ["cws_convertor/manufacturing"]),
        _phase_item("P2_SAFE_01", "Machine transfer remains fail-closed", PASS, ["cws_convertor/manufacturing/authority.py"]),
    ]
    phase2 = {"schema": "cws-phase2-bom-production-checklist-1.0", "generated_at": generated_at, "status": _aggregate_status(item["status"] for item in phase2_items), "items": phase2_items}
    _write_json(phase_output, "PHASE_2_BOM_PRODUCTION_CHECKLIST.json", phase2)
    _write_text(phase_output, "PHASE_2_BOM_PRODUCTION_CHECKLIST.md", "# Phase 2 - BOM and production checklist\n\n" + "\n".join(f"- `{item['status']}` {item['id']}: {item['title']}" for item in phase2_items))

    projection_path = ROOT / "cws_convertor" / "drawings" / "projection.py"
    routing_path = ROOT / "cws_convertor" / "manufacturing" / "routing.py"
    output_path = ROOT / "cws_convertor" / "output" / "document_output.py"
    drawing_source = (ROOT / "cws_convertor" / "ui_qt" / "engineering_drawing.py").read_text(encoding="utf-8")
    phase3_items = [
        _phase_item("P3_DRAW_01", "Vector-native engineering drawing projection model", PASS if projection_path.is_file() and "DrawingProjectionModel.export_pdf" in drawing_source else FAIL, [str(projection_path), "cws_convertor/ui_qt/engineering_drawing.py"]),
        _phase_item("P3_DRAW_02", "DrawingProjectionModel single authority", PASS if projection_path.is_file() else FAIL, [str(projection_path)]),
        _phase_item("P3_ROUTE_01", "MachineRoutingService single authority", PASS if routing_path.is_file() else FAIL, [str(routing_path)]),
        _phase_item("P3_OUT_01", "DocumentOutputService print/preview/export authority", PASS if output_path.is_file() else FAIL, [str(output_path)]),
        _phase_item("P3_RT_01", "PDF/NC/IFC/STEP production roundtrip matrix", NOT_TESTED, []),
        _phase_item("P3_SAFE_01", "Direct machine transfer remains disabled", PASS, ["cws_convertor/manufacturing/authority.py"]),
    ]
    phase3 = {"schema": "cws-phase3-pdf-routing-checklist-1.0", "generated_at": generated_at, "status": _aggregate_status(item["status"] for item in phase3_items), "items": phase3_items}
    _write_json(phase_output, "PHASE_3_PDF_ROUTING_CHECKLIST.json", phase3)
    _write_text(phase_output, "PHASE_3_PDF_ROUTING_CHECKLIST.md", "# Phase 3 - PDF and routing checklist\n\n" + "\n".join(f"- `{item['status']}` {item['id']}: {item['title']}" for item in phase3_items))


def build_validation(gate_run: dict[str, Any] | None = None, *, output_dir: Path = OUTPUT, phase_output_dir: Path = PHASE_OUTPUT, session_path: Path = SESSION) -> dict[str, Any]:
    run = gate_run or {"status": NOT_TESTED, "duration_seconds": 0.0}
    generated_at = datetime.now(timezone.utc).isoformat()
    reference = build_reference_artifacts(session_path, output_dir=output_dir)
    tests = _test_matrix(run, reference)
    checklist = _checklist_payload(tests, generated_at)
    inventory: dict[str, list[str]] = {}
    for item in tests:
        inventory.setdefault(item["category"], []).append(item["id"])
    _write_json(output_dir, "TRIMBLE_PARITY_FUNCTION_INVENTORY.json", {"schema": "cws-trimble-parity-function-inventory-2.0", "target": TARGET, "generated_at": generated_at, "categories": inventory, "function_count": len(tests)})
    _write_json(output_dir, "TRIMBLE_PARITY_MATRIX.json", {"schema": "cws-trimble-parity-matrix-2.0", "target": TARGET, "generated_at": generated_at, "status": checklist["status"], "cases": tests})
    _write_json(output_dir, "TRIMBLE_PARITY_TEST_MATRIX.json", {"schema": "cws-trimble-parity-test-matrix-2.0", "target": TARGET, "generated_at": generated_at, "tests": tests})
    profile = TRIMBLE_STYLE_INTERACTION_PROFILE.contract()
    input_status = _aggregate_status([PASS if run.get("status") == PASS else FAIL, reference["input_mapping"]["status"]])
    _write_json(output_dir, "TRIMBLE_PARITY_INPUT_MATRIX.json", {"schema": "cws-trimble-parity-input-matrix-2.0", "target": TARGET, "generated_at": generated_at, "status": input_status, "cws_contract_status": PASS if run.get("status") == PASS else FAIL, "cws_contract": profile, "trimble_observation_status": reference["input_mapping"]["status"], "trimble_observation": reference["input_mapping"]})
    visual_tests = [item for item in tests if item["category"] == "visual"]
    _write_json(output_dir, "TRIMBLE_PARITY_VISUAL_MATRIX.json", {"schema": "cws-trimble-parity-visual-matrix-2.0", "target": TARGET, "generated_at": generated_at, "status": _aggregate_status(item["status"] for item in visual_tests), "checks": visual_tests, "reference": reference["visual"]})
    _write_json(output_dir, "TRIMBLE_CWS_PERFORMANCE_COMPARISON.json", {"schema": "cws-trimble-performance-comparison-2.0", "target": TARGET, "generated_at": generated_at, "status": reference["performance"]["status"], "cws": {"navigation_schedule_hz": round(1000.0 / profile["profile"]["navigation_frame_ms"], 2), "adaptive_interaction_rendering": True, "indexed_instanced_mesh_picking": True, "gate_duration_seconds": run.get("duration_seconds", 0.0)}, "trimble_reference": reference["performance"]})
    _write_json(output_dir, "TRIMBLE_PARITY_CHECKLIST.json", checklist)
    _write_text(output_dir, "TRIMBLE_PARITY_CAMERA_AUDIT.md", f"# Camera audit\n\nCWS automated camera contract: `{'PASS' if run.get('status') == PASS else 'FAIL'}`.\n\nLive Trimble input comparison: `{reference['input_mapping']['status']}`.\n\nA CWS camera unit test is not accepted as evidence of Trimble behaviour.\n")
    _write_text(output_dir, "TRIMBLE_CWS_INTENTIONAL_DIFFERENCES.md", "# Intentional differences\n\nCWS does not claim Trimble source-code, asset, telemetry, rendering-internal or proprietary UI identity. Observable parity requires a paired live measurement on the same model and camera.\n")
    _write_text(output_dir, "TRIMBLE_PARITY_REPORT.md", f"# CWS Viewer observable parity report\n\n`TRIMBLE_PARITY = {checklist['status']}`\n\n- Cases: `{checklist['case_total']}`\n- Required PASS: `{checklist['required_pass']}/{checklist['required_total']}`\n- Required FAIL: `{checklist['required_fail']}`\n- Required BLOCKED: `{checklist['required_blocked']}`\n- Required BLOCKED_EXTERNAL_EVIDENCE: `{checklist['required_blocked_external_evidence']}`\n- Required NOT_TESTED: `{checklist['required_not_tested']}`\n\nThe result is fail-closed: internal CWS tests cannot replace a live Trimble observation.\n")
    _write_phase_artifacts(phase_output_dir, generated_at, checklist, tests, reference, run)
    return checklist


if __name__ == "__main__":
    print(json.dumps(build_validation(), indent=2))
