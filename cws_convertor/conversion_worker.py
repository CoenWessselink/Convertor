"""Crash-isolated conversion job used by the Qt converter workspace.

Native IFC/OpenCascade operations run in a child CWS process. A malformed or
exceptionally expensive model can therefore be terminated without freezing the
interactive application.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
import tempfile
import traceback
from typing import Any


def _convert_exact_native_step(
    part: Any,
    shape: Any,
    output: Path,
    safe_name: str,
    signature: str,
) -> tuple[list[Path], list[str], list[str]]:
    """Export an exact selected source BREP to STEP without a Workbench revision.

    A Workbench revision is required when manufacturing semantics must be
    reconstructed. It is not required for a lossless IFC/STEP BREP transfer.
    The generated STEP is therefore accepted only after a physical re-import
    and comparison against the isolated source shape.
    """
    import cadquery as cq

    from cws_convertor.project.canonical_rebuild import canonical_shape_metrics
    from cws_convertor.project.model import stable_sha256

    expected = canonical_shape_metrics(shape)
    output.mkdir(parents=True, exist_ok=True)
    manufacturing_hash = str(getattr(part, "manufacturing_hash", "") or "")[:12]
    suffix = f"_{manufacturing_hash}" if manufacturing_hash else ""
    artifact = output / f"{safe_name}{suffix}.step"
    with tempfile.TemporaryDirectory(prefix=".cws_exact_step_", dir=str(output)) as folder:
        temporary = Path(folder) / artifact.name
        cq.exporters.export(shape, str(temporary), exportType="STEP")
        restored = cq.importers.importStep(str(temporary)).val()
        actual = canonical_shape_metrics(restored)

        checks: list[dict[str, Any]] = []

        def exact_check(name: str, expected_value: Any, actual_value: Any) -> None:
            checks.append(
                {
                    "property": name,
                    "expected": expected_value,
                    "found": actual_value,
                    "tolerance": 0.0,
                    "status": "passed" if expected_value == actual_value else "failed",
                }
            )

        def numeric_check(name: str, expected_value: float, actual_value: float, tolerance: float) -> None:
            delta = abs(float(actual_value) - float(expected_value))
            checks.append(
                {
                    "property": name,
                    "expected": float(expected_value),
                    "found": float(actual_value),
                    "delta": delta,
                    "tolerance": float(tolerance),
                    "status": "passed" if delta <= tolerance else "failed",
                }
            )

        exact_check("valid", True, bool(actual.get("valid")))
        exact_check("solid_count", int(expected["solid_count"]), int(actual["solid_count"]))
        numeric_check(
            "volume_mm3",
            float(expected["volume_mm3"]),
            float(actual["volume_mm3"]),
            max(0.001, abs(float(expected["volume_mm3"])) * 1.0e-8),
        )
        numeric_check(
            "area_mm2",
            float(expected["area_mm2"]),
            float(actual["area_mm2"]),
            max(0.001, abs(float(expected["area_mm2"])) * 1.0e-8),
        )
        for index, (expected_value, actual_value) in enumerate(
            zip(expected["bbox_mm"], actual["bbox_mm"], strict=True),
            start=1,
        ):
            numeric_check(
                f"bbox_mm_{index}",
                float(expected_value),
                float(actual_value),
                max(0.001, abs(float(expected_value)) * 1.0e-8),
            )
        if not all(item["status"] == "passed" for item in checks):
            failed = ", ".join(item["property"] for item in checks if item["status"] != "passed")
            raise RuntimeError(f"STEP herimport wijkt af van de exacte brongeometrie: {failed}")
        temporary.replace(artifact)

    report = {
        "schema": "cws.exact-native-step-selection.v1",
        "status": "passed",
        "part_id": str(getattr(part, "internal_id", "") or ""),
        "source_signature": signature,
        "artifact_path": str(artifact.resolve()),
        "artifact_sha256": __import__("hashlib").sha256(artifact.read_bytes()).hexdigest(),
        "source_metrics": expected,
        "reimport_metrics": actual,
        "checks": checks,
        "workbench_revision_required": False,
        "authority": "exact_isolated_native_brep",
    }
    report_path = output / f"{safe_name}_step_compare.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return (
        [report_path, artifact],
        [
            f"{safe_name}: exacte bron-BREP fysiek naar STEP geschreven en opnieuw geimporteerd.",
            f"Geometrische vergelijking geslaagd: {report_path.name}",
        ],
        [],
    )


def _convert_project_selection(
    project_path: Path,
    entity_id: str,
    output: Path,
    direction: str,
    material: str,
) -> tuple[list[Path], list[str], list[str]]:
    """Convert the selected canonical Workbench part and re-import the artifact."""
    from cws_convertor.project import ProjectSession
    from cws_convertor.project.canonical_rebuild import rebuild_and_compare
    from cws_convertor.project.roundtrip import validate_roundtrips
    from cws_convertor.project.model import stable_sha256

    session = ProjectSession.open(project_path, read_only=True)
    part = session.project.parts.get(entity_id)
    if part is None:
        raise RuntimeError(f"Onbekend maakdeel {entity_id}")
    raw_name = str(getattr(part, "part_position", "") or entity_id)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name).strip("._") or "selected_part"
    target_format = direction.lower().replace("dstv", "nc1").replace("->", "-").split("-")[-1]
    if target_format not in {"nc1", "step", "ifc", "pdf"}:
        raise ValueError(f"Doelformaat {target_format!r} ondersteunt geen canonical conversie")
    # The active UI may have prepared an exact imported part in memory while the
    # source package deliberately remains untouched. Reconstruct that same
    # deterministic production context for this one selection in the isolated
    # worker instead of migrating the complete project or relying on stale data.
    if not part.workbench:
        from cws_convertor.project.production_normalization import prepare_exact_imported_part

        prepare_exact_imported_part(part)
    inspection = session.inspect_part_source_geometry(entity_id, persist=False)
    if (
        inspection.native_shape is not None
        and inspection.selection_verified
        and inspection.production_geometry_exact
        and inspection.status == "resolved_exact"
    ):
        conversion_shape = inspection.native_shape
        signature = stable_sha256(
            {
                "source_sha256": inspection.source_sha256,
                "source_geometry_hash": inspection.source_geometry_hash,
                "metrics": inspection.metrics,
            }
        )
        if not part.workbench:
            if target_format == "step":
                return _convert_exact_native_step(
                    part,
                    conversion_shape,
                    output,
                    safe_name,
                    signature,
                )
            raise RuntimeError(
                f"{target_format.upper()}-productie-uitvoer vereist bevestigde maakgegevens; "
                "STEP-export van deze exacte brongeometrie is wel direct beschikbaar"
            )
    else:
        if not part.workbench:
            raise RuntimeError(
                "Conversie vereist een exact geisoleerde bron-BREP of bevestigde maakgegevens"
            )
        rebuild = rebuild_and_compare(part)
        if rebuild.shape is None or rebuild.report.get("status") != "passed":
            blockers = "; ".join(inspection.blocking_reasons)
            raise RuntimeError(
                "Conversie vereist een exact geisoleerde IFC/STEP-BREP of een "
                "geslaagde canonical rebuild"
                + (f": {blockers}" if blockers else "")
            )
        conversion_shape = rebuild.shape
        signature = str(rebuild.report.get("canonical_signature") or "")
    del material
    output.mkdir(parents=True, exist_ok=True)
    report = validate_roundtrips(
        part,
        conversion_shape,
        output,
        canonical_signature=signature,
        formats=("NC1", "STEP", "IFC", "PDF"),
    )
    format_result = dict(report.get("formats", {}).get(target_format) or {})
    if format_result.get("status") != "passed":
        blockers = "; ".join(format_result.get("messages") or ())
        raise RuntimeError(
            f"{target_format.upper()} re-import/compare is niet geslaagd"
            + (f": {blockers}" if blockers else "")
        )
    report_path = output / f"{safe_name}_{target_format}_compare.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifact = Path(str(format_result.get("artifact_path") or ""))
    warnings = [
        f"{safe_name}: canonical rebuild, fysieke {target_format.upper()} en re-importcompare geslaagd.",
        f"Comparemanifest: {report_path.name}",
    ]
    return [report_path, artifact], warnings, []


def _convert_one(job: dict[str, Any]) -> dict[str, Any]:
    source = Path(str(job["source"])).expanduser().resolve()
    output = Path(str(job["output"])).expanduser().resolve()
    direction = str(job["direction"])
    material = str(job.get("material") or "S235JR")
    output.mkdir(parents=True, exist_ok=True)

    project_path = Path(str(job.get("project_path") or "")) if job.get("project_path") else None
    entity_id = str(job.get("entity_id") or "")
    if project_path is not None and entity_id:
        outputs, warnings, failures = _convert_project_selection(
            project_path,
            entity_id,
            output,
            direction,
            material,
        )

    elif source.suffix.lower() == ".pdf":
        from pdf_support import pdf_to_ifc, pdf_to_nc1, pdf_to_step

        target_suffix = {
            "pdf-nc1": ".nc1",
            "pdf-step": ".step",
            "pdf-ifc": ".ifc",
        }.get(direction)
        if target_suffix is None:
            raise ValueError("Kies voor een PDF-bron PDF naar NC1, STEP of IFC")
        target = output / f"{source.stem}{target_suffix}"
        if direction == "pdf-nc1":
            result = pdf_to_nc1(source, target)
        elif direction == "pdf-step":
            result = pdf_to_step(source, target)
        else:
            result = pdf_to_ifc(source, target, material=material)
        outputs = list(result.outputs)
        warnings = list(result.warnings)
        failures: list[str] = []
    else:
        from conversion import convert_file

        outputs, warnings, failures = convert_file(
            source,
            output,
            direction,
            material=material,
            strict_validation=True,
        )
    if failures:
        raise RuntimeError("; ".join(str(value) for value in failures))
    return {
        "source": str(source),
        "outputs": [str(path) for path in outputs],
        "warnings": [str(value) for value in warnings],
        "failures": [str(value) for value in failures],
    }


def run_job_file(job_path: str | Path, result_path: str | Path) -> int:
    job_file = Path(job_path)
    result_file = Path(result_path)
    try:
        job = json.loads(job_file.read_text(encoding="utf-8"))
        payload = {"status": "passed", "result": _convert_one(job)}
        exit_code = 0
    except BaseException as exc:
        payload = {
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(limit=30),
        }
        exit_code = 2
    result_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = result_file.with_suffix(result_file.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(result_file)
    return exit_code


__all__ = ["run_job_file"]
