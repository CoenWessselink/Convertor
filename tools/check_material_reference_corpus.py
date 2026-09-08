"""Read-only reference-corpus audit of fresh semantic material/model imports.

This is a measurement, not a claim that every imported part is producible. It
keeps source-value presence, catalogue recognition, review and export separate.
Embedded sources are extracted through ProjectSession into temporary storage;
the reference package is never saved or migrated by this tool.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.production_export.readiness import ReadinessGate
from cws_convertor.project import ProjectSession
from cws_convertor.project.classification import _catalog_profile
from material_database import MaterialDatabase


DEFAULT_PROJECT = ROOT / "validation/master_completion/hvpc_project/HVPC te Hengelo fasen totaal.cwscproj"
FORMATS = ("nc1", "step", "ifc", "production_pdf")
CORE_PATHS = (
    "material_database.py", "materials.json", "profile_database.py", "profiles.json",
    "cws_convertor/material_resolution.py", "cws_convertor/project/classification.py",
    "cws_convertor/project/service.py", "cws_convertor/project/model.py",
    "cws_convertor/importers/ifc_project.py", "cws_convertor/importers/step_project.py",
    "cws_convertor/production_export/readiness.py",
    "tools/check_material_reference_corpus.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_fingerprint() -> dict[str, Any]:
    paths = set(CORE_PATHS)
    for directory in ("cws_convertor/importers", "cws_convertor/manufacturing_interpreter", "cws_convertor/production_export", "cws_convertor/project"):
        paths.update(str(path.relative_to(ROOT)) for path in (ROOT / directory).glob("*.py"))
    files = {name: sha256(ROOT / name) for name in sorted(paths) if (ROOT / name).is_file()}
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    result = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True,
        capture_output=True, check=False,
    )
    return {"git_head": result.stdout.strip(), "audited_code_sha256": digest, "files": files}


def percent(count: int, total: int) -> float | None:
    return round(count * 100.0 / total, 2) if total else None


def counts(values: Any) -> dict[str, int]:
    return dict(sorted(Counter(str(value or "<empty>") for value in values).items()))


def runtime_dependencies() -> dict[str, Any]:
    available = {}
    for name in ("cadquery", "OCP", "ifcopenshell", "PySide6"):
        try:
            available[name] = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            available[name] = False
    return {"python": platform.python_version(), "platform": platform.platform(), "native_module_available": available}


def measure_source(path: Path, corpus_kind: str, origin: str) -> dict[str, Any]:
    """Register and import a source in its own new, disposable project."""
    start = time.perf_counter()
    digest_before = sha256(path)
    db = MaterialDatabase()
    with ProjectSession.new("Read-only reference audit") as session:
        registration = session.register_sources(
            [path], include_step_geometry=False, user="reference-corpus-audit",
        )[0]
        registered = time.perf_counter()
        result = session.semantic_import_source(registration.source.source_id, user="reference-corpus-audit")
        imported = time.perf_counter()
        parts = list(session.project.parts.values())
        resolutions = [db.resolve(part.material or part.material_grade) for part in parts]
        profile_matches = [_catalog_profile(part.profile) for part in parts]
        gate = ReadinessGate()
        assessments = [gate.assess(part, list(FORMATS)) for part in parts]
        unresolved_indexes = [index for index, resolution in enumerate(resolutions) if not resolution.resolved]
        unresolved_blocked = sum(
            not any(assessments[index].allowed(fmt) for fmt in FORMATS)
            for index in unresolved_indexes
        )
        recognized = sum(item.resolved for item in resolutions)
        present = sum(bool((part.material or part.material_grade).strip()) for part in parts)
        classification_handled = sum(
            part.classification_status not in {"", "unclassified"} for part in parts
        )
        fasteners = list(session.project.fasteners.values())
        fastener_resolutions = [db.resolve(fastener.grade) for fastener in fasteners]
        blockers = Counter(
            message.code for assessment in assessments
            for message in assessment.messages_for("nc1") if message.severity == "error"
        )
        payload = {
            "file_name": path.name,
            "origin": origin,
            "corpus_kind": corpus_kind,
            "source_sha256": digest_before,
            "source_bytes": path.stat().st_size,
            "status": "measured",
            "strategy": result.strategy,
            "profile_recognition_evidence": result.evidence.get("profile_recognition", {}),
            "semantic_blocking_reasons": result.blocking_reasons,
            "source_class_counts": result.source_class_counts,
            "entity_counts": session.project.entity_counts(),
            "parts": {
                "total": len(parts),
                "material_source_value_present": present,
                "material_source_value_present_percent": percent(present, len(parts)),
                "material_catalog_resolved": recognized,
                "material_catalog_resolved_percent": percent(recognized, len(parts)),
                "material_catalog_status_counts": counts(item.status for item in resolutions),
                "material_unresolved_raw_values": counts(
                    parts[index].material or parts[index].material_grade for index in unresolved_indexes
                ),
                "material_raw_value_counts": counts(part.material or part.material_grade for part in parts),
                "material_normalized_value_counts": counts(part.normalized_material for part in parts),
                "ifc_material_evidence_status_counts": counts(
                    part.properties["ifc_material_resolution"].get("status")
                    for part in parts if "ifc_material_resolution" in part.properties
                ),
                "profile_source_value_present": sum(bool(part.profile.strip()) for part in parts),
                "profile_catalog_resolved": sum(bool(value) for value in profile_matches),
                "profile_catalog_resolved_percent": percent(sum(bool(value) for value in profile_matches), len(parts)),
                "profile_unresolved_raw_values": counts(
                    part.profile for part, match in zip(parts, profile_matches) if not match
                ),
                "classification_status_counts": counts(part.classification_status for part in parts),
                "classification_category_counts": counts(part.category for part in parts),
                "classification_handled": classification_handled,
                "classification_handled_percent": percent(classification_handled, len(parts)),
                "material_unresolved_blocked_for_all_production_formats": unresolved_blocked,
                "material_unresolved_blocked_percent": percent(unresolved_blocked, len(unresolved_indexes)),
                "production_export_allowed_counts": {
                    fmt: sum(assessment.allowed(fmt) for assessment in assessments) for fmt in FORMATS
                },
                "nc1_blocker_occurrences": dict(sorted(blockers.items())),
            },
            "fasteners": {
                "total": len(fasteners),
                "grade_present": sum(bool(fastener.grade.strip()) for fastener in fasteners),
                "grade_catalog_resolved": sum(item.resolved for item in fastener_resolutions),
                "grade_catalog_resolved_percent": percent(sum(item.resolved for item in fastener_resolutions), len(fasteners)),
                "grade_raw_value_counts": counts(fastener.grade for fastener in fasteners),
                "grade_catalog_status_counts": counts(item.status for item in fastener_resolutions),
            },
            "semantic_import_production_export_allowed": result.production_export_allowed,
            "project_production_export_allowed": session.project.production_gate()["allowed"],
            "warnings": result.warnings,
            "seconds": {
                "registration": round(registered - start, 3),
                "semantic_import_and_classification": round(imported - registered, 3),
                "total_with_audit": round(time.perf_counter() - start, 3),
            },
            "limitations": [
                "Semantic/profile-catalog audit; no exact BREP reconstruction or native geometry fidelity benchmark.",
                "Material-source evidence is not a certificate or physical material test.",
                "Catalogue hit percentage is not recognition accuracy: no independently labeled material truth set is supplied.",
                "Production-export counts require all current readiness rules, not merely material recognition.",
            ],
        }
    payload["source_unchanged"] = digest_before == sha256(path)
    payload["safety_passed"] = (
        payload["source_unchanged"]
        and classification_handled == len(parts)
        and unresolved_blocked == len(unresolved_indexes)
    )
    return payload


def audit_source(path: Path, corpus_kind: str, origin: str) -> dict[str, Any]:
    print(f"Audit: {path.name}", flush=True)
    try:
        result = measure_source(path, corpus_kind, origin)
        part = result["parts"]
        print(
            f"  {part['total']} parts; material {part['material_catalog_resolved_percent']}%; "
            f"profile {part['profile_catalog_resolved_percent']}%; "
            f"{result['seconds']['total_with_audit']} s", flush=True,
        )
        return result
    except Exception as exc:
        return {
            "file_name": path.name, "origin": origin, "corpus_kind": corpus_kind,
            "status": "error", "error_type": type(exc).__name__, "error": str(exc),
            "traceback": traceback.format_exc(),
            "safety_passed": False,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--skip-project", action="store_true")
    parser.add_argument("--step", type=Path, action="append", default=[])
    parser.add_argument("--include-regression-steps", action="store_true", help="Include tracked generated/synthetic STEP files, explicitly labelled as such.")
    parser.add_argument("--output", type=Path, default=ROOT / "validation/material_model_recognition/reference/corpus.json")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    fingerprint_before = code_fingerprint()
    rows: list[dict[str, Any]] = []
    package_checks: list[dict[str, Any]] = []
    if not args.skip_project:
        if not args.project.is_file():
            rows.append({"file_name": args.project.name, "status": "missing", "safety_passed": False})
        else:
            before = sha256(args.project)
            try:
                with ProjectSession.open(args.project, read_only=True) as reference:
                    for source_id, source in sorted(reference.project.sources.items()):
                        if source.source_format.upper() not in {"IFC", "STEP", "STP"}:
                            continue
                        path = reference.source_paths.get(source_id)
                        origin = f"{args.project.name}::embedded/{source.file_name}"
                        if path is None or not path.is_file():
                            rows.append({"file_name": source.file_name, "origin": origin, "status": "missing", "safety_passed": False})
                        else:
                            rows.append(audit_source(path, "real_embedded_project_source", origin))
            except Exception as exc:
                rows.append({
                    "file_name": args.project.name, "status": "error", "stage": "open_reference_package",
                    "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(),
                    "safety_passed": False,
                })
            package_checks.append({"file_name": args.project.name, "sha256": before, "unchanged": before == sha256(args.project)})
    explicit_steps = [(path.resolve(), "explicit_step_reference") for path in args.step]
    if args.include_regression_steps:
        explicit_steps.extend((path, "generated_nc1_to_step_regression") for path in sorted((ROOT / "validation/v0.2_generated_step").glob("*.step")))
        explicit_steps.extend((path, "synthetic_profile_regression") for path in sorted((ROOT / "validation/v0.2_synthetic_profiles").glob("*.step")))
    for path, kind in explicit_steps:
        rows.append(audit_source(path, kind, str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)))
    fingerprint_after = code_fingerprint()
    measured = [row for row in rows if row["status"] == "measured"]
    failed = [row for row in rows if not row.get("safety_passed")]
    stable = fingerprint_before == fingerprint_after
    report = {
        "schema": "cws-material-reference-corpus-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": runtime_dependencies(),
        "code": fingerprint_before,
        "audited_code_unchanged_during_run": stable,
        "package_checks": package_checks,
        "summary": {
            "sources_requested": len(rows), "sources_measured": len(measured),
            "sources_failed_or_missing": len(failed),
            "total_parts": sum(row["parts"]["total"] for row in measured),
            "total_seconds": round(time.perf_counter() - started, 3),
            "safety_passed": bool(rows) and not failed and stable and all(item["unchanged"] for item in package_checks),
        },
        "interpretation": {
            "percentage_denominator": "All fresh imported parts per source; fasteners reported separately.",
            "source_material_value": "Effective single Part.material or material_grade after semantic evidence reconciliation; ambiguous associations may carry evidence but no selected material.",
            "handling_is_not_recognition": True,
            "blank_percentage": "null means no applicable objects, not 100%.",
            "recognition_accuracy": "Not measured without independently labeled ground truth.",
            "visual_evidence": "Not captured; this runner is a headless semantic audit.",
        },
        "sources": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)
    print(f"Report: {args.output}", flush=True)
    return 0 if report["summary"]["safety_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
