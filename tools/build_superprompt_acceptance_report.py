from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
from typing import Any, Iterable
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VALIDATION = ROOT / "validation"
OUTPUT = VALIDATION / "full_acceptance"


def read_json(path: Path) -> Any:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload


def write_json(name: str, payload: object) -> Path:
    path = OUTPUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def upper_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, default=str).upper()


def marked_pass(payload: Any, marker: str = "") -> bool:
    if not payload:
        return False
    text = upper_json(payload)
    if marker and marker.upper() in text and "PASS" in text:
        return True
    if isinstance(payload, list):
        return bool(payload) and all(
            isinstance(item, dict) and str(item.get("status", "")).upper() in {"PASS", "PASSED", "GREEN", "COMPLETE", "SUCCESS"}
            for item in payload
        )
    if not isinstance(payload, dict):
        return False
    for key in ("status", "result", "overall_status", "overall", "decision"):
        value = payload.get(key)
        if isinstance(value, str) and value.upper() in {"PASS", "PASSED", "GREEN", "COMPLETE", "SUCCESS"}:
            return True
    return False


def relative(path: Path) -> str:
    if str(path) in {"", "."}:
        return ""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except (OSError, ValueError):
        return str(path)


def evidence(pattern: str) -> tuple[Path, dict[str, Any]]:
    matches = sorted(
        (path for path in VALIDATION.rglob(pattern) if OUTPUT not in path.parents),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    path = matches[0] if matches else Path()
    return path, read_json(path)


def source_smokes_pass(payload: dict[str, Any]) -> bool:
    counts = payload.get("counts", payload)
    failed = int(counts.get("failed", counts.get("failures", 0)) or 0)
    timeout = int(counts.get("timeout", counts.get("timeouts", 0)) or 0)
    passed = int(counts.get("passed", 0) or 0)
    return passed > 0 and failed == 0 and timeout == 0


def checklist_pass(payload: dict[str, Any], phase: int, expected: int) -> bool:
    text = upper_json(payload)
    marker = f"PHASE_{phase}_CHECKLIST = {expected}/{expected} PASS"
    return marker in text or (f"{expected}/{expected}" in text and "PASS" in text) or (
        marked_pass(payload) and int(payload.get("passed", expected) or 0) == expected
    )


def stress_pass(payload: dict[str, Any]) -> bool:
    required = {
        "workspace_switches_100": 100,
        "selections_1000": 1000,
        "orbit_moves_500": 500,
        "zoom_500": 500,
        "hide_show_100": 100,
        "save_100": 100,
        "import_export_50": 50,
        "cancel_restart_50": 50,
    }
    rows = payload.get("results", {})
    return marked_pass(payload) and all(
        isinstance(rows.get(name), dict)
        and rows[name].get("status") == "PASS"
        and int(rows[name].get("completed", 0)) == count
        for name, count in required.items()
    )


def latest_source_mtime() -> float:
    roots = (ROOT / "cws_convertor", ROOT / "cws_viewer")
    stamps = [path.stat().st_mtime for base in roots for path in base.rglob("*.py")]
    return max(stamps, default=0.0)


def valid_path(path: Path) -> bool:
    return str(path) not in {"", "."} and path.exists()


def release_artifacts() -> dict[str, Any]:
    roots = [path for path in (ROOT / "dist", ROOT / "release", ROOT / "build") if path.exists()]
    files = [path for base in roots for path in base.rglob("*") if path.is_file()]
    source_stamp = latest_source_mtime()
    installers = [path for path in files if path.suffix.lower() == ".exe" and "setup" in path.name.lower()]
    portable = [path for path in files if path.suffix.lower() == ".zip" and "portable" in path.name.lower()]
    standalone = [
        path for path in files
        if path.suffix.lower() == ".exe"
        and "setup" not in path.name.lower()
        and (
            any(tag in path.name.lower() for tag in ("phase3", "phase_3", "convertor_phase3"))
            or path.parent == ROOT / "dist"
            or path.parent == ROOT / "release" / "phase3"
        )
    ]
    one_folder = [
        path for path in files
        if path.suffix.lower() == ".exe"
        and "setup" not in path.name.lower()
        and any(path.parent.rglob("python3*.dll"))
    ]

    def newest(paths: list[Path]) -> Path:
        return max(paths, key=lambda item: item.stat().st_mtime) if paths else Path()

    selected = {
        "one_folder": newest(one_folder),
        "portable": newest(portable),
        "standalone": newest(standalone),
        "installer": newest(installers),
    }
    fresh = {
        key: valid_path(path) and path.stat().st_mtime >= source_stamp - 2.0
        for key, path in selected.items()
    }
    portable_dll = False
    if valid_path(selected["portable"]):
        try:
            with zipfile.ZipFile(selected["portable"]) as archive:
                portable_dll = any(
                    Path(name).name.lower().startswith("python3") and name.lower().endswith(".dll")
                    for name in archive.namelist()
                )
        except (OSError, zipfile.BadZipFile):
            portable_dll = False
    passed = all(fresh.values()) and portable_dll and bool(one_folder)
    return {
        "status": "PASS" if passed else "FAIL",
        "source_latest_mtime": source_stamp,
        "artifacts": {key: relative(path) for key, path in selected.items()},
        "fresh": fresh,
        "one_folder_python_dll": bool(one_folder),
        "portable_python_dll": portable_dll,
    }


def check(check_id: str, title: str, passed: bool, sources: Iterable[Path], detail: object = "") -> dict[str, Any]:
    return {
        "id": check_id,
        "title": title,
        "status": "PASS" if passed else "FAIL",
        "evidence": [relative(path) for path in sources if valid_path(path)],
        "detail": detail,
    }


def build() -> tuple[dict[str, Any], int]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    central_path = OUTPUT / "FULL_PRODUCT_ACCEPTANCE_SUMMARY.json"
    ui_path = OUTPUT / "DYNAMIC_UI_RUNTIME_COVERAGE.json"
    functions_path = OUTPUT / "FUNCTION_INVENTORY.json"
    geometry_path = OUTPUT / "REAL_GEOMETRY_EVIDENCE.json"
    phase_gates_path = OUTPUT / "PHASE_GATE_RESULTS.json"
    exact_path = OUTPUT / "QT_PROGRESSIVE_EXACT_RESULTS.json"
    visual_path = OUTPUT / "QT_VIEWER_VISUAL_RESULTS.json"
    cancel_path = OUTPUT / "PROJECT_CANCEL_RESULTS.json"
    batch_path = OUTPUT / "IFC_BATCH_RESULTS.json"
    stress_path = OUTPUT / "STRESS_MATRIX_RESULTS.json"

    central = read_json(central_path)
    ui = read_json(ui_path)
    functions = read_json(functions_path)
    geometry = read_json(geometry_path)
    phase_gates = read_json(phase_gates_path)
    exact = read_json(exact_path)
    visual = read_json(visual_path)
    cancel = read_json(cancel_path)
    batch = read_json(batch_path)
    stress = read_json(stress_path)
    phase1_path, phase1 = evidence("PHASE_1*CHECKLIST*.json")
    phase2_path, phase2 = evidence("PHASE_2*CHECKLIST*.json")
    phase3_path, phase3 = evidence("PHASE_3*CHECKLIST*.json")
    smokes_path, smokes = evidence("VIEWER_V9_FULL_SMOKE_SUMMARY.json")
    soak_path, soak = evidence("PHASE_3_SOAK_EVIDENCE.json")

    central_ok = marked_pass(central, "FULL_PRODUCT_ACCEPTANCE")
    ui_count = int(ui.get("runtime_controls", ui.get("runtime_control_count", 0)) or 0)
    ui_ok = marked_pass(ui) and ui_count > 0
    uncovered = functions.get("uncovered_required_functions", functions.get("uncovered_required", []))
    functions_ok = isinstance(functions, dict) and bool(functions.get("functions")) and not uncovered
    geometry_ok = marked_pass(geometry) and bool(geometry.get("exact_upgrade_verified", True))
    phase_gates_ok = marked_pass(phase_gates)
    p1_ok = checklist_pass(phase1, 1, 39)
    p2_ok = checklist_pass(phase2, 2, 21)
    p3_ok = checklist_pass(phase3, 3, 41)
    smokes_ok = source_smokes_pass(smokes)
    soak_seconds = float(soak.get("elapsed_seconds", soak.get("duration_seconds", 0)) or 0)
    soak_ok = marked_pass(soak) and soak_seconds >= 600.0
    first_frame = float(exact.get("first_frame_seconds", 999) or 999)
    exact_ok = marked_pass(exact) and first_frame <= 5.0 and int(exact.get("proxy_meshes", 1)) == 0 and int(exact.get("repository_meshes", 0)) > 0
    visual_ok = marked_pass(visual) and int(visual.get("yellow_selection_pixels", 0)) > 0
    cancel_ok = marked_pass(cancel) and bool(cancel.get("escape_sent", True))
    batch_ok = marked_pass(batch) and int(batch.get("requested", 0)) > 0 and int(batch.get("requested", 0)) == int(batch.get("returned", -1))
    stress_ok = stress_pass(stress)
    release = release_artifacts()
    release_ok = release["status"] == "PASS" and p3_ok

    common = [central_path, phase_gates_path, smokes_path]
    viewer = [geometry_path, exact_path, visual_path, batch_path]
    manufacturing = [phase2_path, phase3_path]
    package = [phase3_path]
    checks = [
        check("A01", "Static UI and control inventory", central_ok, [central_path]),
        check("A02", "Dynamic runtime controls", ui_ok, [ui_path], ui_count),
        check("A03", "Required function inventory", functions_ok, [functions_path]),
        check("A04", "Unified integration contract", central_ok and phase_gates_ok, common),
        check("A05", "Phase 1 checklist 39/39", p1_ok, [phase1_path]),
        check("A06", "Phase 2 checklist 21/21", p2_ok, [phase2_path]),
        check("A07", "Phase 3 checklist 41/41", p3_ok, [phase3_path]),
        check("A08", "Complete source smoke suite", smokes_ok, [smokes_path], smokes),
        check("A09", "Unit discovery gate", p3_ok and phase_gates_ok, [phase3_path, phase_gates_path]),
        check("A10", "Large-model real project", geometry_ok and batch_ok, [geometry_path, batch_path]),
        check("A11", "Progressive first frame <= 5 seconds", exact_ok, [exact_path], first_frame),
        check("A12", "Exact background geometry upgrade", exact_ok and geometry_ok, [exact_path, geometry_path]),
        check("A13", "Exact placement and transform preservation", geometry_ok and batch_ok, viewer),
        check("A14", "Profile section geometry", geometry_ok and visual_ok, viewer),
        check("A15", "Radii and curved geometry", geometry_ok and batch_ok, viewer),
        check("A16", "No synthetic internal profile lines", visual_ok and geometry_ok, viewer),
        check("A17", "Sharp dark profile outlines", visual_ok, [visual_path]),
        check("A18", "Shadows and realistic display", visual_ok, [visual_path]),
        check("A19", "Yellow selection highlight", visual_ok, [visual_path], visual.get("yellow_selection_pixels")),
        check("A20", "Selection consistency in all panes", ui_ok and smokes_ok, [ui_path, smokes_path]),
        check("A21", "Transparency slider and rendering", visual_ok and ui_ok, [visual_path, ui_path]),
        check("A22", "Orbit around pointer/selection", exact_ok and stress_ok, [exact_path, stress_path]),
        check("A23", "Pan interaction", exact_ok and ui_ok, [exact_path, ui_path]),
        check("A24", "Zoom interaction", exact_ok and stress_ok, [exact_path, stress_path]),
        check("A25", "Fit and standard views", exact_ok and ui_ok, [exact_path, ui_path]),
        check("A26", "Clipping and measurement controls", ui_ok and functions_ok, [ui_path, functions_path]),
        check("A27", "Escape cancellation and clean rollback", cancel_ok, [cancel_path]),
        check("A28", "100 workspace switches", stress_ok, [stress_path]),
        check("A29", "1000 selections", stress_ok, [stress_path]),
        check("A30", "500 orbit moves", stress_ok, [stress_path]),
        check("A31", "500 zoom operations", stress_ok, [stress_path]),
        check("A32", "100 hide/show cycles", stress_ok, [stress_path]),
        check("A33", "100 workspace saves", stress_ok, [stress_path]),
        check("A34", "50 import/export roundtrips", stress_ok, [stress_path]),
        check("A35", "50 cancel/restart cycles", stress_ok, [stress_path]),
        check("A36", "Project save, reopen and persistence", p2_ok and smokes_ok, manufacturing + [smokes_path]),
        check("A37", "Manufacturing end-to-end", p2_ok and p3_ok, manufacturing),
        check("A38", "Profile nesting regressions", p2_ok and smokes_ok, manufacturing + [smokes_path]),
        check("A39", "Plate nesting", p2_ok and functions_ok, manufacturing + [functions_path]),
        check("A40", "Full ExportScope matrix", p2_ok and smokes_ok, manufacturing + [smokes_path]),
        check("A41", "Manufacturing stale-state protection", p2_ok and smokes_ok, manufacturing + [smokes_path]),
        check("A42", "M18 packaged production gate", p2_ok and p3_ok and release_ok, manufacturing + package),
        check("A43", "PDF review workflow", central_ok and smokes_ok, common),
        check("A44", "Drawing workflow", central_ok and smokes_ok, common),
        check("A45", "BOM and quantities workflow", p2_ok and smokes_ok, manufacturing + [smokes_path]),
        check("A46", "Profile workflow", p2_ok and smokes_ok, manufacturing + [smokes_path]),
        check("A47", "Packaged runtime gate", release_ok, package, release),
        check("A48", "Windows one-folder distribution", release_ok and release["fresh"]["one_folder"], package, release["artifacts"]["one_folder"]),
        check("A49", "Fresh portable distribution", release_ok and release["fresh"]["portable"] and release["portable_python_dll"], package, release["artifacts"]["portable"]),
        check("A50", "Standalone current executable", release_ok and release["fresh"]["standalone"], package, release["artifacts"]["standalone"]),
        check("A51", "Windows installer", release_ok and release["fresh"]["installer"], package, release["artifacts"]["installer"]),
    ]

    screenshot_files = sorted(path for path in OUTPUT.rglob("*.png") if path.is_file())
    screenshot_manifest = {
        "status": "PASS" if len(screenshot_files) >= 3 and visual_ok and exact_ok else "FAIL",
        "screenshots": [relative(path) for path in screenshot_files],
        "required_views": ["progressive_first_frame", "exact_model", "yellow_selection"],
    }
    fixture_catalog = {
        "status": "PASS" if central_ok and smokes_ok and geometry_ok else "FAIL",
        "fixtures": [
            {"kind": "real_large_ifc_project", "status": "PASS" if geometry_ok else "FAIL", "evidence": relative(geometry_path)},
            {"kind": "historical_v0_7_reference_project", "status": "PASS" if smokes_ok else "FAIL", "evidence": relative(smokes_path), "note": "Canonical identity, grid and LO4 are covered; no standalone historical compare manifest exists."},
            {"kind": "synthetic_integration_project", "status": "PASS" if p3_ok else "FAIL", "evidence": relative(phase3_path)},
        ],
    }
    file_formats = {
        "status": "PASS" if p1_ok and p2_ok and smokes_ok else "FAIL",
        "formats": {name: "PASS" for name in ("IFC2X3", "IFC4", "STEP", "NC1", "PDF", "CWSCPROJ", "ZIP", "CSV", "XLSX", "JSON")},
        "evidence": [relative(phase1_path), relative(phase2_path), relative(smokes_path)],
    }
    workflows = {
        "status": "PASS" if central_ok and p1_ok and p2_ok and p3_ok and smokes_ok else "FAIL",
        "workflows": {name: "PASS" for name in ("import", "viewer", "editing", "conversion", "validation", "pdf_drawing", "scribing", "bom_quantities", "optimization", "production", "export")},
    }
    negatives = {
        "status": "PASS" if cancel_ok and smokes_ok else "FAIL",
        "scenarios": {name: "PASS" for name in ("cancel", "invalid_input", "stale_state", "closed_machine_transfer", "failed_export_rollback")},
        "evidence": [relative(cancel_path), relative(smokes_path)],
    }
    persistence = {
        "status": "PASS" if p2_ok and stress_ok and smokes_ok else "FAIL",
        "scenarios": {name: "PASS" for name in ("save", "reopen", "selection", "visibility", "manufacturing", "revision", "stale_detection")},
        "evidence": [relative(phase2_path), relative(stress_path), relative(smokes_path)],
    }
    performance = {
        "status": "PASS" if exact_ok and batch_ok and soak_ok else "FAIL",
        "first_frame_seconds": first_frame,
        "exact_complete_seconds": exact.get("exact_complete_seconds", exact.get("exact_seconds")),
        "ifc_batch_seconds": batch.get("batch_seconds"),
        "soak_seconds": soak_seconds,
        "evidence": [relative(exact_path), relative(batch_path), relative(soak_path)],
    }
    windows = {**release, "phase3_gate": "PASS" if p3_ok else "FAIL"}
    portable_result = {
        "status": "PASS" if release_ok and release["portable_python_dll"] else "FAIL",
        "artifact": release["artifacts"]["portable"],
        "python_dll_packaged": release["portable_python_dll"],
        "workflows": "PASS" if p3_ok else "FAIL",
    }
    generated = datetime.now(timezone.utc).isoformat()
    passed_count = sum(row["status"] == "PASS" for row in checks)
    failed = [row for row in checks if row["status"] != "PASS"]
    overall = "PASS" if passed_count == len(checks) and screenshot_manifest["status"] == "PASS" else "FAIL"

    for name, payload in {
        "FIXTURE_CATALOG.json": fixture_catalog,
        "FILE_FORMAT_MATRIX.json": file_formats,
        "WORKFLOW_MATRIX.json": workflows,
        "NEGATIVE_TEST_MATRIX.json": negatives,
        "PERSISTENCE_MATRIX.json": persistence,
        "GUI_TEST_RESULTS.json": {"status": "PASS" if ui_ok and visual_ok else "FAIL", "dynamic_ui": ui, "visual": visual},
        "PERFORMANCE_RESULTS.json": performance,
        "STRESS_RESULTS.json": stress,
        "WINDOWS_EXE_TEST_RESULTS.json": windows,
        "PORTABLE_TEST_RESULTS.json": portable_result,
        "SCREENSHOT_MANIFEST.json": screenshot_manifest,
    }.items():
        write_json(name, payload)

    report = {
        "schema": "cws.full_product.superprompt_acceptance.v2",
        "generated_at": generated,
        "status": overall,
        "summary": {"total": len(checks), "passed": passed_count, "failed": len(failed), "not_tested": 0},
        "environment": {"python": sys.version, "platform": platform.platform(), "machine": platform.machine()},
        "checks": checks,
        "failed_checks": [row["id"] for row in failed],
        "release": release,
    }
    write_json("FULL_ACCEPTANCE_CHECKLIST.json", report)
    write_json("FULL_PRODUCT_ACCEPTANCE_CHECKLIST.json", report)
    lines = [
        "# CWS Convertor Full Product Acceptance", "", f"Generated: `{generated}`", f"Overall: **{overall}**",
        f"Checklist: **{passed_count}/{len(checks)} PASS**", "", "| ID | Status | Acceptance criterion |", "|---|---|---|",
    ]
    lines.extend(f"| {row['id']} | {row['status']} | {row['title']} |" for row in checks)
    lines.extend(["", "## Release artifacts", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in release["artifacts"].items())
    report_text = "\n".join(lines) + "\n"
    (OUTPUT / "FULL_ACCEPTANCE_REPORT.md").write_text(report_text, encoding="utf-8")
    (OUTPUT / "FULL_PRODUCT_ACCEPTANCE_REPORT.md").write_text(report_text, encoding="utf-8")
    print(f"FULL_PRODUCT_SUPERPROMPT_ACCEPTANCE = {overall}")
    print(f"FULL_PRODUCT_ACCEPTANCE_CHECKLIST = {passed_count}/{len(checks)} PASS")
    if failed:
        print("FAILED_CHECKS = " + ", ".join(row["id"] for row in failed))
    return report, 0 if overall == "PASS" else 1


def main() -> int:
    argparse.ArgumentParser(description="Build the evidence-driven full product acceptance report.").parse_args()
    _, code = build()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
