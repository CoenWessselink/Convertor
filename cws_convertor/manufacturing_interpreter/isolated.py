from __future__ import annotations

import multiprocessing as mp
import pickle
import queue
import time
from pathlib import Path
from typing import Any, Callable


def _worker(source: str, options: dict[str, Any], output: Any) -> None:
    try:
        from .cli import _step_inspection
        from .contracts import ManufacturingInterpretationRequest
        from .pipeline import ManufacturingGeometryInterpreter

        inspection = _step_inspection(Path(source))
        expected_sha = str(options.get("source_sha256") or "")
        if expected_sha and inspection.source_sha256 != expected_sha:
            raise ValueError("STEP-bronhash wijkt af van de projectkoppeling")
        for name in (
            "part_id",
            "source_file_id",
            "source_geometry_hash",
        ):
            value = options.get(name)
            if value:
                setattr(inspection, name, str(value))
        report = ManufacturingGeometryInterpreter().analyze(
            ManufacturingInterpretationRequest(
                inspection=inspection,
                preferred_profile=str(options.get("preferred_profile") or ""),
                requested_outputs=tuple(options.get("requested_outputs") or ("STEP", "IFC", "NC1")),
                material_evidence=options.get("material_evidence"),
                project_part_link=tuple(options.get("project_part_link") or ()),
            )
        )
        output.put(("PASS", pickle.dumps(report, protocol=pickle.HIGHEST_PROTOCOL)))
    except BaseException as exc:
        output.put(("FAILED", f"{type(exc).__name__}: {exc}"))


def analyze_step_isolated(
    source: str | Path,
    *,
    timeout_seconds: float = 120.0,
    cancel_check: Callable[[], bool | None] | None = None,
    part_id: str = "",
    source_file_id: str = "",
    source_sha256: str = "",
    source_geometry_hash: str = "",
    preferred_profile: str = "",
    requested_outputs: tuple[str, ...] = ("STEP", "IFC", "NC1"),
    material_evidence: Any = None,
    project_part_link: tuple[tuple[str, str], ...] = (),
) -> Any:
    from .cli import _sha256

    path = Path(source).resolve()
    actual_sha256 = _sha256(path)
    if source_sha256 and source_sha256.lower() != actual_sha256:
        raise ValueError("STEP-bronhash wijkt af van de projectkoppeling")
    source_sha256 = actual_sha256
    timeout_seconds = float(timeout_seconds)
    if not 0.0 < timeout_seconds <= 3600.0:
        raise ValueError("timeout_seconds moet groter dan 0 en maximaal 3600 zijn")
    context = mp.get_context("spawn")
    output = context.Queue(maxsize=1)
    options = {
        "part_id": part_id,
        "source_file_id": source_file_id,
        "source_sha256": source_sha256,
        "source_geometry_hash": source_geometry_hash,
        "preferred_profile": preferred_profile,
        "requested_outputs": tuple(requested_outputs),
        "material_evidence": material_evidence,
        "project_part_link": tuple(project_part_link),
    }
    process = context.Process(
        target=_worker,
        args=(str(Path(source).resolve()), options, output),
        daemon=False,
    )
    process.start()
    deadline = time.monotonic() + timeout_seconds
    message = None
    try:
        while process.is_alive():
            try:
                message = output.get_nowait()
                break
            except queue.Empty:
                pass
            if cancel_check is not None and cancel_check():
                process.terminate()
                process.join(5.0)
                raise RuntimeError("MGI native worker cancelled")
            if time.monotonic() >= deadline:
                process.terminate()
                process.join(5.0)
                raise TimeoutError(f"MGI native worker exceeded {timeout_seconds:.1f} seconds")
            time.sleep(0.025)
        process.join(5.0)
        if message is None:
            try:
                message = output.get(timeout=2.0)
            except queue.Empty as exc:
                raise RuntimeError(f"MGI native worker crashed with exit code {process.exitcode}") from exc
        status, payload = message
        if status != "PASS":
            raise RuntimeError(str(payload))
        if _sha256(path) != actual_sha256:
            raise ValueError("STEP-bron is gewijzigd tijdens de herkenning")
        return pickle.loads(payload)
    finally:
        if process.is_alive():
            process.terminate()
            process.join(5.0)
        output.close()


__all__ = ["analyze_step_isolated"]
