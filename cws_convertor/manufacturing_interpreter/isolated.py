from __future__ import annotations

import multiprocessing as mp
import pickle
import queue
import time
from pathlib import Path
from typing import Any, Callable


def _worker(source: str, output: Any) -> None:
    try:
        from .cli import _step_inspection
        from .contracts import ManufacturingInterpretationRequest
        from .pipeline import ManufacturingGeometryInterpreter

        report = ManufacturingGeometryInterpreter().analyze(
            ManufacturingInterpretationRequest(inspection=_step_inspection(Path(source)))
        )
        output.put(("PASS", pickle.dumps(report, protocol=pickle.HIGHEST_PROTOCOL)))
    except BaseException as exc:
        output.put(("FAILED", f"{type(exc).__name__}: {exc}"))


def analyze_step_isolated(
    source: str | Path,
    *,
    timeout_seconds: float = 120.0,
    cancel_check: Callable[[], bool] | None = None,
) -> Any:
    context = mp.get_context("spawn")
    output = context.Queue(maxsize=1)
    process = context.Process(target=_worker, args=(str(Path(source).resolve()), output), daemon=False)
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
        return pickle.loads(payload)
    finally:
        if process.is_alive():
            process.terminate()
            process.join(5.0)
        output.close()


__all__ = ["analyze_step_isolated"]
