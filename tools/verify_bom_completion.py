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
    checks = {
        "all_targeted_tests_passed": all(record["status"] == "passed" for record in records),
        "column_count_37": len(columns) == 37,
        "eleven_readiness_columns": {
            "Geometrie", "Materiaal gereed", "Tekening", "Machine gereed",
            "Nesting", "NC-export", "Scribing", "Conflictvrij", "Vrijgegeven",
            "Geproduceerd", "Geleverd",
        }.issubset(columns),
        "action_count_at_least_75": len(actions) >= 75,
        "action_ids_unique": len(actions) == len(set(actions)),
        "eight_release_captures_unique": (
            len(BOM_CAPTURE_FILENAMES) == 8
            and len(BOM_CAPTURE_FILENAMES) == len(set(BOM_CAPTURE_FILENAMES))
        ),
    }
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    report = {
        "schema": "cws-bom-completion-acceptance-1.0",
        "status": "passed" if all(checks.values()) else "failed",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "version": APP_VERSION,
        "source_commit": commit,
        "checks": checks,
        "column_count": len(columns),
        "columns": list(columns),
        "action_count": len(actions),
        "release_capture_files": list(BOM_CAPTURE_FILENAMES),
        "action_ids_sha256": hashlib.sha256("\n".join(actions).encode("utf-8")).hexdigest(),
        "source_files": {
            relative: _sha256(ROOT / relative)
            for relative in (
                "cws_convertor/bom/production_hub.py",
                "cws_convertor/bom/workspace.py",
                "cws_convertor/ui_qt/bom_workspace.py",
                "cws_viewer/cache/render_resource_cache.py",
                "cws_viewer/core/v14_controller.py",
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
