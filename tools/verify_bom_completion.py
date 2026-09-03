"""Produce exact-SHA acceptance evidence for the complete BOM production hub."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bom_columns() -> tuple[str, ...]:
    source = (ROOT / "cws_convertor/ui_qt/bom_workspace.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in ast.walk(module):
        if not isinstance(node, ast.ClassDef) or node.name != "BomWorkspacePanel":
            continue
        for statement in node.body:
            if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "COLUMNS"
                for target in statement.targets
            ):
                return tuple(ast.literal_eval(statement.value))
    raise RuntimeError("BomWorkspacePanel.COLUMNS ontbreekt")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from cws_convertor.bom.production_hub import ACTION_DEFINITIONS
    from cws_convertor.bom.workspace import PRODUCTION_READINESS_FIELDS
    from cws_convertor.product import APP_VERSION
    from tools.capture_bom_production_hub import BOM_CAPTURE_FILENAMES

    tests = (
        "tests/bom_production_hub_complete_smoke.py",
        "tests/bom_production_hub_smoke.py",
        "tests/viewer_shared_cache_lasso_smoke.py",
        "tests/project_model_smoke.py",
    )
    records = []
    for relative in tests:
        started = time.perf_counter()
        result = subprocess.run(
            [sys.executable, str(ROOT / relative)], cwd=ROOT,
            text=True, capture_output=True, check=False,
        )
        records.append({
            "test": relative,
            "status": "passed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "duration_seconds": round(time.perf_counter() - started, 3),
            "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
            "stderr_excerpt": result.stderr[-2000:],
        })
    columns = _bom_columns()
    actions = tuple(definition.action_id for definition in ACTION_DEFINITIONS)
    hub_source = (ROOT / "cws_convertor/bom/production_hub.py").read_text(encoding="utf-8")
    ui_source = (ROOT / "cws_convertor/ui_qt/bom_workspace.py").read_text(encoding="utf-8")
    lasso_source = (ROOT / "cws_viewer/backends/vtk_project_mesh_v14.py").read_text(encoding="utf-8")
    cache_source = (ROOT / "cws_viewer/cache/render_resource_cache.py").read_text(encoding="utf-8")
    readiness_labels = tuple(label for label, _attribute in PRODUCTION_READINESS_FIELDS)
    checks = {
        "all_targeted_tests_passed": all(record["status"] == "passed" for record in records),
        "column_count_37": len(columns) == 37,
        "eleven_readiness_columns": len(readiness_labels) == 11 and set(readiness_labels) == {
            "Geometrie", "Materiaal gereed", "Tekening", "Machine gereed",
            "Nesting", "NC-export", "Scribing", "Conflictvrij", "Vrijgegeven",
            "Geproduceerd", "Geleverd",
        } and set(readiness_labels).issubset(columns),
        "action_count_at_least_87": len(actions) >= 87,
        "action_ids_unique": len(actions) == len(set(actions)),
        "selection_specific_rules_present": (
            "_selection_requirement" in hub_source
            and all(value in hub_source for value in (
                "stock.assign", "stock.release", "purchase.release",
                "machine.auto_accept", "production.withdraw", "export.nc1",
            ))
        ),
        "field_level_entity_deltas_present": (
            "class BOMFieldDelta" in hub_source
            and "entity_fields" in hub_source
            and "field_deltas" in ui_source
        ),
        "mixed_stock_and_procurement_present": all(value in hub_source for value in (
            "class BOMStockAllocationPlan", "def reserve_plan(",
            "unallocated_length_mm", "def release_assignments(", "def cancel(",
        )),
        "recursive_smart_query_present": (
            "class BOMQueryGroup" in hub_source
            and "groups=groups" in ui_source
            and "matches_group" in hub_source
        ),
        "persistent_release_bound_undo_present": all(value in hub_source for value in (
            "persistent_inverse_patch", "after_content_sha256",
            "persistent_restore", "_release_barrier",
        )),
        "true_lasso_and_colour_selection_present": (
            "_polygon_intersects_rect" in lasso_source
            and "select_same_display_color" in ui_source
        ),
        "shared_cache_identity_proof_present": all(value in cache_source for value in (
            "def evidence", "resource_identity_sha256", "invalidations",
        )),
        "eight_release_captures_unique": (
            len(BOM_CAPTURE_FILENAMES) == 8
            and len(BOM_CAPTURE_FILENAMES) == len(set(BOM_CAPTURE_FILENAMES))
        ),
    }
    requirement_checks = {
        "selection_dependent_action_matrix": (
            checks["all_targeted_tests_passed"]
            and checks["action_count_at_least_87"]
            and checks["selection_specific_rules_present"]
        ),
        "field_level_revision_and_removed_objects": (
            checks["all_targeted_tests_passed"] and checks["field_level_entity_deltas_present"]
        ),
        "separate_production_readiness_columns": (
            checks["all_targeted_tests_passed"] and checks["eleven_readiness_columns"]
        ),
        "physical_stock_remnants_and_procurement": (
            checks["all_targeted_tests_passed"] and checks["mixed_stock_and_procurement_present"]
        ),
        "compound_smart_lasso_and_colour_selection": (
            checks["all_targeted_tests_passed"]
            and checks["recursive_smart_query_present"]
            and checks["true_lasso_and_colour_selection_present"]
        ),
        "uniform_results_and_release_bound_persistent_undo": (
            checks["all_targeted_tests_passed"] and checks["persistent_release_bound_undo_present"]
        ),
        "shared_render_geometry_cache": (
            checks["all_targeted_tests_passed"] and checks["shared_cache_identity_proof_present"]
        ),
    }
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    report = {
        "schema": "cws-bom-completion-acceptance-2.0",
        "status": "passed" if all(checks.values()) and all(requirement_checks.values()) else "failed",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "version": APP_VERSION,
        "source_commit": commit,
        "checks": checks,
        "requirements": {
            key: {"status": "passed" if value else "failed", "completion_percentage": 100 if value else 0}
            for key, value in requirement_checks.items()
        },
        "completion_percentage": (
            round(100.0 * sum(requirement_checks.values()) / len(requirement_checks), 2)
            if requirement_checks else 0.0
        ),
        "column_count": len(columns),
        "columns": list(columns),
        "action_count": len(actions),
        "readiness_fields": [
            {"column": label, "attribute": attribute}
            for label, attribute in PRODUCTION_READINESS_FIELDS
        ],
        "release_capture_files": list(BOM_CAPTURE_FILENAMES),
        "action_ids_sha256": hashlib.sha256("\n".join(actions).encode("utf-8")).hexdigest(),
        "source_files": {
            relative: _sha256(ROOT / relative)
            for relative in (
                "cws_convertor/bom/production_hub.py",
                "cws_convertor/bom/workspace.py",
                "cws_convertor/ui_qt/bom_workspace.py",
                "cws_viewer/cache/render_resource_cache.py",
                "cws_viewer/geometry/loader.py",
                "cws_viewer/core/v14_controller.py",
                "cws_viewer/backends/vtk_project_mesh_v14.py",
            )
        },
        "tests": records,
        "safety_boundary": {
            "software_acceptance": True,
            "physical_machine_observed": False,
            "direct_machine_transfer_allowed": False,
        },
    }
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"], "output": str(target),
        "columns": len(columns), "actions": len(actions), "tests": len(records),
    }, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
