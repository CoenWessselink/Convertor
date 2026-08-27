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

    session = ProjectSession.open(project_path, read_only=True)
    part = session.project.parts.get(entity_id)
    if part is None:
        raise RuntimeError(f"Onbekend maakdeel {entity_id}")
    if not part.workbench:
        raise RuntimeError("Conversie vereist een Part Workbench-revisie")
    rebuild = rebuild_and_compare(part)
    if rebuild.shape is None or rebuild.report.get("status") != "passed":
        raise RuntimeError("Conversie vereist een exact geslaagde canonical rebuild")
    raw_name = str(getattr(part, "part_position", "") or entity_id)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name).strip("._") or "selected_part"
    target_format = direction.lower().replace("dstv", "nc1").replace("->", "-").split("-")[-1]
    del material
    if target_format not in {"nc1", "step", "ifc", "pdf"}:
        raise ValueError(f"Doelformaat {target_format!r} ondersteunt geen canonical conversie")
    output.mkdir(parents=True, exist_ok=True)
    signature = str(rebuild.report.get("canonical_signature") or "")
    report = validate_roundtrips(
        part,
        rebuild.shape,
        output,
        canonical_signature=signature,
        formats=(target_format.upper(),),
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
