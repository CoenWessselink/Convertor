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
    """Isolate one canonical make-part in the child process before conversion."""
    from cws_convertor.integration.exact_source import ExactSourceProjectService

    service = ExactSourceProjectService.open(project_path, read_only=True)
    part, source_path, isolation = service.isolate(entity_id, allow_heavy=True)
    if not isolation.source_shape_available or isolation.shape is None:
        evidence = "; ".join(str(value) for value in (isolation.evidence or ()))
        raise RuntimeError(
            f"Geselecteerd maakdeel {entity_id} kon niet exact uit {source_path.name} worden geisoleerd"
            + (f": {evidence}" if evidence else ".")
        )
    raw_name = str(getattr(part, "part_position", "") or entity_id)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name).strip("._") or "selected_part"
    target_format = direction.lower().replace("dstv", "nc1").replace("->", "-").split("-")[-1]
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cws-selected-part-") as temp_dir:
        isolated_step = Path(temp_dir) / f"{safe_name}.step"
        import cadquery as cq

        cq.exporters.export(isolation.shape, str(isolated_step), exportType="STEP")
        warnings = [f"{safe_name}: exact geselecteerd maakdeel uit {source_path.name} geisoleerd."]
        if target_format == "step":
            target = output / isolated_step.name
            target.write_bytes(isolated_step.read_bytes())
            return [target], warnings, []
        if target_format in {"nc1", "ifc"}:
            from conversion import convert_file

            outputs, converted_warnings, failures = convert_file(
                isolated_step,
                output,
                f"step-{target_format}",
                material=material,
                preferred_profile=str(
                    getattr(part, "normalized_profile", "") or getattr(part, "profile", "") or ""
                ),
                strict_validation=True,
            )
            return outputs, warnings + list(converted_warnings), failures
    raise ValueError(f"Doelformaat {target_format!r} ondersteunt geen selectieconversie.")


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
