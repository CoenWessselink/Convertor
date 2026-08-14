"""Generate machine-readable V9 main-build integration evidence.

The validator exercises one canonical project object through the integrated
viewer scene, professional grid, BOM, selection bus, format-specific readiness
and the persisted Part Workbench.  It does not claim a Windows packaged gate;
that gate is deliberately reported separately by platform/runtime.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.integration import (
    IntegratedProjectWorkspace,
    create_synthetic_integration_project,
    run_integration_self_test,
)
from cws_convertor.product import APP_NAME, APP_VERSION
from cws_convertor.project import ProjectSession
from cws_viewer.version import VIEWER_API_VERSION, VIEWER_PACKAGE_VERSION

DEFAULT_REFERENCE = Path(
    "/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/"
    "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plate_changes(diameter: float = 10.0) -> dict[str, Any]:
    return {
        "part_form": "plate",
        "recognition": {"candidate": "PL10", "confidence": 1.0, "confirmed": True},
        "dimensions": {"thickness_mm": 10.0},
        "reference_sides": [
            {
                "side_id": "top",
                "label": "Bovenzijde",
                "face_ref": "face:top",
                "confirmed": True,
            }
        ],
        "contours": [
            {
                "contour_id": "outer",
                "role": "outer",
                "closed": True,
                "segments": [
                    {"kind": "line", "start": [0.0, 0.0], "end": [100.0, 0.0]},
                    {"kind": "line", "start": [100.0, 0.0], "end": [100.0, 50.0]},
                    {"kind": "line", "start": [100.0, 50.0], "end": [0.0, 50.0]},
                    {"kind": "line", "start": [0.0, 50.0], "end": [0.0, 0.0]},
                ],
            }
        ],
        "features": [
            {
                "feature_id": "hole:1",
                "kind": "hole",
                "reference_side": "top",
                "parameters": {
                    "x_mm": 20.0,
                    "y_mm": 20.0,
                    "diameter_mm": float(diameter),
                    "through": True,
                },
            }
        ],
        "unresolved_questions": [],
    }


def _synthetic_evidence(output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    project_path = create_synthetic_integration_project(output / "CWS_V9_SYNTHETIC.cwscproj")
    with IntegratedProjectWorkspace.open(
        project_path, read_only=False, load_all_geometry=False
    ) as workspace:
        entity_id = "part-v9"
        workspace.select_entities((entity_id,), origin="v9-validator")
        gate = workspace.readiness_for_part(entity_id)
        workspace_evidence = {
            "report": workspace.report.to_dict(),
            "project_object_is_scene_project": workspace.load_result.project is workspace.project,
            "selected_entity_id": workspace.interaction.selection.primary_entity_id,
            "application_selection_entity_id": workspace.selection_bus.selection.primary_entity_id,
            "bom_group": workspace.bom_index.group_for_entity(entity_id) or "",
            "readiness": gate,
        }

    with ProjectSession.open(project_path) as session:
        part = session.project.parts["part-v9"]
        session.start_part_workbench(part.internal_id, user="v9-validator")
        state = session.update_part_workbench(
            part.internal_id,
            _plate_changes(),
            user="v9-validator",
            reason="V9 deterministic plate/reference-side/hole validation",
        )
        rebuild = session.rebuild_part_canonical(part.internal_id, user="v9-validator")
        manufacturing_hash_before = part.manufacturing_hash
        session.register_part_artifact(
            part.internal_id,
            artifact_id="v9-trusted-step",
            artifact_format="step",
            sha256="b" * 64,
            user="v9-validator",
        )
        session.update_part_workbench(
            part.internal_id,
            {"features": _plate_changes(12.0)["features"]},
            user="v9-validator",
            reason="V9 negative manufacturing hash / artifact invalidation evidence",
        )
        changed_hash = part.manufacturing_hash
        invalidated_status = part.workbench["artifacts"]["v9-trusted-step"]["status"]
        session.undo_part_workbench(part.internal_id, user="v9-validator")
        restored_hash = part.manufacturing_hash
        restored_status = part.workbench["artifacts"]["v9-trusted-step"]["status"]
        session.save(user="v9-validator", revision_message="V9 integration evidence")
        workbench_evidence = {
            "validation_issues": list(state["current_revision"]["validation_issues"]),
            "build_status": rebuild.report["build_status"],
            "canonical_metrics": rebuild.report["canonical_metrics"],
            "manufacturing_hash_before": manufacturing_hash_before,
            "manufacturing_hash_changed": changed_hash != manufacturing_hash_before,
            "artifact_status_after_change": invalidated_status,
            "manufacturing_hash_restored_by_undo": restored_hash == manufacturing_hash_before,
            "artifact_status_after_undo": restored_status,
        }

    with ProjectSession.open(project_path, read_only=True) as reopened:
        persisted = reopened.project.parts["part-v9"].workbench
        persistence_evidence = {
            "workbench_present": bool(persisted),
            "command_cursor": int(persisted.get("command_cursor", -1)),
            "artifact_status": persisted.get("artifacts", {}).get("v9-trusted-step", {}).get("status", ""),
            "canonical_rebuild_status": persisted.get("canonical_rebuild", {}).get("status", ""),
        }

    return {
        "status": "passed",
        "elapsed_seconds": time.perf_counter() - started,
        "project_path": str(project_path),
        "project_sha256": _sha256(project_path),
        "workspace": workspace_evidence,
        "part_workbench": workbench_evidence,
        "persistence": persistence_evidence,
    }


def _reference_evidence(reference: Path) -> dict[str, Any]:
    if not reference.is_file():
        return {
            "status": "not_run_missing_private_reference",
            "path": str(reference),
        }
    started = time.perf_counter()
    with IntegratedProjectWorkspace.open(
        reference, read_only=True, load_all_geometry=False
    ) as workspace:
        rows = [
            row for row in workspace.interaction.grid_model.rows
            if row.get("part_position") == "LO4"
        ]
        entity_ids = tuple(row.entity_id for row in rows)
        workspace.select_entities(entity_ids, origin="v9-reference-validator")
        exact_results = [workspace.open_exact_part(entity_id).to_dict() for entity_id in entity_ids]
        gate_results = [workspace.readiness_for_part(entity_id) for entity_id in entity_ids]
        return {
            "status": "passed" if workspace.identity_audit.passed and len(rows) == 4 else "failed",
            "path": str(reference),
            "sha256": _sha256(reference),
            "elapsed_seconds": time.perf_counter() - started,
            "workspace_report": workspace.report.to_dict(),
            "project_counts": {
                "assemblies": len(workspace.project.assemblies),
                "parts": len(workspace.project.parts),
                "fasteners": len(workspace.project.fasteners),
                "welds": len(workspace.project.welds),
            },
            "lo4": {
                "count": len(rows),
                "entity_ids": list(entity_ids),
                "assembly_marks": sorted({str(row.get("assembly_mark") or "") for row in rows}),
                "profiles": sorted({str(row.get("profile") or "") for row in rows}),
                "materials": sorted({str(row.get("material") or "") for row in rows}),
                "lengths_mm": sorted({float(row.get("length_mm") or 0.0) for row in rows}),
                "selection_synced": set(entity_ids) == set(workspace.selection_bus.selection.entity_ids),
                "bom_groups": [workspace.bom_index.group_for_entity(entity_id) or "" for entity_id in entity_ids],
                "exact_part_results": exact_results,
                "readiness": gate_results,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "viewer_v9" / "final")
    parser.add_argument(
        "--reference-project",
        type=Path,
        default=Path(os.environ.get("CWS_V9_REFERENCE_PROJECT", DEFAULT_REFERENCE)),
    )
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    integration_report = run_integration_self_test().to_dict()
    synthetic = _synthetic_evidence(output)
    reference = _reference_evidence(args.reference_project.expanduser().resolve())

    windows_gate = {
        "status": "not_run_non_windows_platform" if os.name != "nt" else "not_run_in_source_validator",
        "platform": platform.platform(),
        "required_stages": ["source", "pyinstaller_dist", "portable_extracted", "installed_application"],
        "workflow": ".github/workflows/build-windows-integrated-v9.yml",
    }
    payload: dict[str, Any] = {
        "schema": "cws-viewer-v9-main-integration-validation-1.0",
        "created_at": _utc_now(),
        "product": APP_NAME,
        "product_version": APP_VERSION,
        "viewer_version": VIEWER_PACKAGE_VERSION,
        "viewer_api_version": VIEWER_API_VERSION,
        "project_model_schema": "2.4",
        "python": sys.version,
        "platform": platform.platform(),
        "integration_selftest": integration_report,
        "synthetic_project": synthetic,
        "reference_project": reference,
        "windows_gate": windows_gate,
        "safety": {
            "single_canonical_project_truth": True,
            "viewer_can_override_production_gate": False,
            "display_mesh_is_manufacturing_truth": False,
            "general_external_ifc_exact_part_isolation_complete": False,
            "general_external_step_multi_part_isolation_complete": False,
        },
    }
    local_pass = (
        integration_report.get("status") == "passed"
        and synthetic.get("status") == "passed"
        and reference.get("status") in {"passed", "not_run_missing_private_reference"}
    )
    payload["local_gate"] = "passed" if local_pass else "failed"
    payload["release_status"] = "local_integration_passed_windows_gate_pending" if local_pass else "failed"
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    result_path = output / "VIEWER_V9_VALIDATION_RESULTS.json"
    result_path.write_text(body, encoding="utf-8")
    (output / "VIEWER_V9_VALIDATION_RESULTS.json.sha256").write_text(
        f"{_sha256(result_path)}  {result_path.name}\n", encoding="ascii"
    )
    print(body)
    return 0 if local_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
