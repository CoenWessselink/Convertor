"""Crash-isolated entry point for central conversion jobs.

One child process receives the complete batch. It preflights every source
before executing the first serializer, reports item progress atomically and
keeps item failures isolated. The Qt parent can hard-cancel the native child.
"""
from __future__ import annotations

import json
from pathlib import Path
import traceback
from typing import Any, Mapping

from cws_convertor.conversion_service import DEFAULT_CONVERSION_SERVICE


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _progress_writer(path: Path | None):
    def write(percent: int, message: str, details: dict[str, Any]) -> None:
        if path is None:
            return
        _atomic_json(
            path,
            {
                "schema": "cws.conversion.worker-progress.v1",
                "percent": max(0, min(100, int(percent))),
                "message": str(message),
                "details": dict(details),
            },
        )

    return write


def _run_job(job: Mapping[str, Any]) -> dict[str, Any]:
    output = Path(str(job["output"])).expanduser().resolve()
    direction = str(job["direction"])
    material = str(job.get("material") or "S235JR")
    project_path = str(job.get("project_path") or "")
    entity_id = str(job.get("entity_id") or "")
    progress_path = (
        Path(str(job["progress_path"])).expanduser().resolve()
        if job.get("progress_path")
        else None
    )
    progress = _progress_writer(progress_path)

    if project_path and entity_id:
        progress(5, "Projectselectie voorbereiden", {"stage": "preflight"})
        result = DEFAULT_CONVERSION_SERVICE.convert_project_selection(
            project_path,
            entity_id,
            output,
            direction,
            material=material,
        )
        progress(100, "Projectconversie afgerond", {"stage": result.get("status", "completed")})
        return result

    raw_sources = job.get("sources")
    if raw_sources is None:
        raw_sources = [job["source"]]
    sources = [str(Path(str(value)).expanduser().resolve()) for value in raw_sources]
    return DEFAULT_CONVERSION_SERVICE.convert_batch(
        sources,
        output,
        direction,
        material=material,
        progress=progress,
    )


def _convert_one(job: dict[str, Any]) -> dict[str, Any]:
    """Compatibility wrapper retained for direct worker callers."""
    payload = dict(job)
    if "sources" not in payload and "source" in payload:
        payload["sources"] = [payload["source"]]
    batch = _run_job(payload)
    results = list(batch.get("results") or [])
    return results[0] if len(results) == 1 else batch


def run_job_file(job_path: str | Path, result_path: str | Path) -> int:
    job_file = Path(job_path)
    result_file = Path(result_path)
    try:
        job = json.loads(job_file.read_text(encoding="utf-8"))
        result = _run_job(job)
        payload = {"status": "passed", "result": result}
        exit_code = 0
    except BaseException as exc:
        payload = {
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(limit=30),
        }
        exit_code = 2
    _atomic_json(result_file, payload)
    return exit_code


__all__ = ["run_job_file"]
