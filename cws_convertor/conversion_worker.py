"""Crash-isolated conversion job used by the Qt converter workspace.

Native IFC/OpenCascade operations run in a child CWS process. A malformed or
exceptionally expensive model can therefore be terminated without freezing the
interactive application.
"""
from __future__ import annotations

import json
from pathlib import Path
import traceback
from typing import Any


def _convert_one(job: dict[str, Any]) -> dict[str, Any]:
    source = Path(str(job["source"])).expanduser().resolve()
    output = Path(str(job["output"])).expanduser().resolve()
    direction = str(job["direction"])
    material = str(job.get("material") or "S235JR")
    output.mkdir(parents=True, exist_ok=True)

    if source.suffix.lower() == ".pdf":
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
