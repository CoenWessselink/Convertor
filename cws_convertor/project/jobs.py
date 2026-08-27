"""Cancellable background job manager used by project import/export phases."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import threading
import time
from typing import Any, Callable, Generic, TypeVar
from uuid import uuid4

from cws_convertor.errors import CWSError, ErrorCode
from .model import utc_now_iso


T = TypeVar("T")


class JobCancelled(CWSError):
    def __init__(self, message: str = "Job is geannuleerd") -> None:
        super().__init__(message, ErrorCode.JOB_CANCELLED)


class JobTimedOut(RuntimeError):
    """Raised cooperatively when the declared job timeout expires."""


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    description: str = ""
    project_id: str = ""
    scope: dict[str, Any] = field(default_factory=dict)
    cancelable: bool = True
    timeout: float | None = None
    resource_budget: dict[str, Any] = field(default_factory=dict)
    status: str = "queued"  # queued, running, completed, failed, cancelled
    progress: float = 0.0
    stage: str = "queued"
    generation: int = 0
    attempt: int = 1
    max_retries: int = 0
    elapsed_seconds: float = 0.0
    message: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    started_at: str = ""
    finished_at: str = ""
    result: Any = None
    result_hash: str = ""
    error: str = ""
    error_namespace: str = ""
    error_code: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not isinstance(data.get("result"), (dict, list, str, int, float, bool, type(None))):
            data["result"] = repr(data["result"])
        return data


class JobContext:
    def __init__(self, manager: "JobManager", job_id: str, cancel_event: threading.Event) -> None:
        self._manager = manager
        self.job_id = job_id
        self._cancel_event = cancel_event

    def update(self, progress: float, message: str = "", **metadata: Any) -> None:
        self._manager._update(self.job_id, progress=progress, message=message, metadata=metadata)
        self.check_cancelled()

    def stage(self, name: str, progress: float, message: str = "", **metadata: Any) -> None:
        self._manager._update(
            self.job_id,
            progress=progress,
            stage=str(name or "running"),
            message=message,
            metadata=metadata,
        )
        self.check_cancelled()

    def is_current_generation(self) -> bool:
        return self._manager.is_current_generation(self.job_id)

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def check_cancelled(self) -> None:
        if self._manager.is_timed_out(self.job_id):
            raise JobTimedOut("Jobtimeout verstreken")
        if self.is_cancelled():
            raise JobCancelled()


class JobManager:
    """Thread-based local job manager with explicit progress and cancellation."""

    def __init__(self, max_workers: int = 2) -> None:
        if max_workers < 1:
            raise ValueError("max_workers moet minimaal 1 zijn")
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="cws-job")
        self._lock = threading.RLock()
        self._records: dict[str, JobRecord] = {}
        self._futures: dict[str, Future[Any]] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._listeners: list[Callable[[JobRecord], None]] = []
        self._started_monotonic: dict[str, float] = {}
        self._latest_generation: dict[tuple[str, str], int] = {}
        self._specs: dict[str, tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]] = {}
        self._timed_out_jobs: set[str] = set()

    def add_listener(self, callback: Callable[[JobRecord], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def submit(
        self,
        job_type: str,
        action: Callable[..., T],
        *args: Any,
        description: str = "",
        project_id: str = "",
        scope: dict[str, Any] | None = None,
        cancelable: bool = True,
        timeout: float | None = None,
        resource_budget: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        generation: int | None = None,
        max_retries: int = 0,
        attempt: int = 1,
        **kwargs: Any,
    ) -> str:
        job_id = str(uuid4())
        key = (str(project_id), str(job_type))
        with self._lock:
            next_generation = int(generation) if generation is not None else self._latest_generation.get(key, 0) + 1
            self._latest_generation[key] = max(self._latest_generation.get(key, 0), next_generation)
        record = JobRecord(
            job_id=job_id,
            job_type=job_type,
            description=description,
            project_id=project_id,
            scope=deepcopy(dict(scope or {})),
            cancelable=bool(cancelable),
            timeout=float(timeout) if timeout is not None else None,
            resource_budget=deepcopy(dict(resource_budget or {})),
            generation=next_generation,
            attempt=max(1, int(attempt)),
            max_retries=max(0, int(max_retries)),
            metadata=dict(metadata or {}),
        )
        cancel_event = threading.Event()
        with self._lock:
            self._records[job_id] = record
            self._cancel_events[job_id] = cancel_event
            self._specs[job_id] = (action, args, dict(kwargs))
            future = self._executor.submit(
                self._run,
                job_id,
                action,
                args,
                kwargs,
                cancel_event,
            )
            self._futures[job_id] = future
        self._notify(record)
        return job_id

    def _run(
        self,
        job_id: str,
        action: Callable[..., T],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        cancel_event: threading.Event,
    ) -> T | None:
        context = JobContext(self, job_id, cancel_event)
        timer: threading.Timer | None = None
        with self._lock:
            record = self._records[job_id]
            record.status = "running"
            record.stage = "running"
            record.started_at = utc_now_iso()
            record.message = "Gestart"
            self._started_monotonic[job_id] = time.perf_counter()
        self._notify(record)
        if record.timeout is not None:
            if record.timeout <= 0.0:
                self._trigger_timeout(job_id)
            else:
                timer = threading.Timer(record.timeout, self._trigger_timeout, args=(job_id,))
                timer.daemon = True
                timer.start()
        try:
            context.check_cancelled()
            result = action(context, *args, **kwargs)
            context.check_cancelled()
            with self._lock:
                record = self._records[job_id]
                current = self.is_current_generation(job_id)
                record.status = "completed" if current else "stale_discarded"
                record.stage = "completed" if current else "stale_discarded"
                record.progress = 1.0
                record.message = "Gereed" if current else "Resultaat verworpen: verouderde generatie"
                record.finished_at = utc_now_iso()
                record.elapsed_seconds = self._elapsed(job_id)
                record.result = result if current else None
                if current:
                    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), default=repr).encode("utf-8")
                    record.result_hash = sha256(encoded).hexdigest()
            self._notify(record)
            return result
        except JobTimedOut as exc:
            with self._lock:
                record = self._records[job_id]
                record.status = "timed_out"
                record.stage = "timed_out"
                record.message = str(exc)
                record.finished_at = utc_now_iso()
                record.error = str(exc)
                record.error_namespace = "CWS.JOB.TIMEOUT"
                record.error_code = "TIMEOUT"
                record.elapsed_seconds = self._elapsed(job_id)
            self._notify(record)
            return None
        except JobCancelled as exc:
            with self._lock:
                record = self._records[job_id]
                record.status = "cancelled"
                record.stage = "cancelled"
                record.message = str(exc)
                record.finished_at = utc_now_iso()
                record.error = str(exc)
                record.error_namespace = "CWS.JOB.CANCELLED"
                record.error_code = "CANCELLED"
                record.elapsed_seconds = self._elapsed(job_id)
            self._notify(record)
            return None
        except Exception as exc:
            with self._lock:
                record = self._records[job_id]
                record.status = "failed"
                record.stage = "failed"
                record.message = "Mislukt"
                record.finished_at = utc_now_iso()
                record.error = f"{type(exc).__name__}: {exc}"
                record.error_namespace = f"CWS.JOB.{record.job_type.upper().replace('-', '_')}.{type(exc).__name__.upper()}"
                record.error_code = type(exc).__name__.upper()
                record.elapsed_seconds = self._elapsed(job_id)
            self._notify(record)
            raise
        finally:
            if timer is not None:
                timer.cancel()

    def _update(
        self,
        job_id: str,
        *,
        progress: float | None = None,
        message: str | None = None,
        stage: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._records[job_id]
            if progress is not None:
                record.progress = max(0.0, min(1.0, float(progress)))
            if message is not None:
                record.message = str(message)
            if stage is not None:
                record.stage = str(stage)
            record.elapsed_seconds = self._elapsed(job_id)
            if metadata:
                record.metadata.update(metadata)
        self._notify(record)

    def _notify(self, record: JobRecord) -> None:
        with self._lock:
            listeners = list(self._listeners)
            snapshot = JobRecord(**asdict(record))
        for callback in listeners:
            try:
                callback(snapshot)
            except Exception:
                # A UI listener may disappear while a background job is active;
                # that must never crash the actual production task.
                continue

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            event = self._cancel_events.get(job_id)
            future = self._futures.get(job_id)
            record = self._records.get(job_id)
            if event is None or record is None or record.status in {"completed", "failed", "cancelled"}:
                return False
            if not record.cancelable:
                return False
            event.set()
            if future is not None and future.cancel():
                record.status = "cancelled"
                record.stage = "cancelled"
                record.finished_at = utc_now_iso()
                record.message = "Geannuleerd vóór start"
                self._notify(record)
            return True

    def _trigger_timeout(self, job_id: str) -> None:
        with self._lock:
            record = self._records.get(job_id)
            event = self._cancel_events.get(job_id)
            if record is None or event is None or record.status in {"completed", "failed", "cancelled", "timed_out"}:
                return
            self._timed_out_jobs.add(job_id)
            event.set()

    def is_timed_out(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._timed_out_jobs

    def is_current_generation(self, job_id: str) -> bool:
        with self._lock:
            record = self._records[job_id]
            key = (record.project_id, record.job_type)
            return record.generation == self._latest_generation.get(key, record.generation)

    def retry(self, job_id: str) -> str:
        with self._lock:
            record = self._records[job_id]
            if record.status not in {"failed", "cancelled"}:
                raise ValueError("Alleen mislukte of geannuleerde jobs kunnen opnieuw worden gestart")
            if record.attempt > record.max_retries:
                raise ValueError("Retrybudget van de job is verbruikt")
            action, args, kwargs = self._specs[job_id]
            metadata = deepcopy(record.metadata)
        return self.submit(
            record.job_type,
            action,
            *args,
            description=record.description,
            project_id=record.project_id,
            scope=record.scope,
            cancelable=record.cancelable,
            timeout=record.timeout,
            resource_budget=record.resource_budget,
            metadata=metadata,
            max_retries=record.max_retries,
            attempt=record.attempt + 1,
            **kwargs,
        )

    def _elapsed(self, job_id: str) -> float:
        started = self._started_monotonic.get(job_id)
        return max(0.0, time.perf_counter() - started) if started is not None else 0.0

    def get(self, job_id: str) -> JobRecord:
        with self._lock:
            record = self._records[job_id]
            return JobRecord(**asdict(record))

    def list(self) -> list[JobRecord]:
        with self._lock:
            return [JobRecord(**asdict(item)) for item in self._records.values()]

    def wait(self, job_id: str, timeout: float | None = None) -> Any:
        with self._lock:
            future = self._futures[job_id]
        return future.result(timeout=timeout)

    def shutdown(self, *, wait: bool = True, cancel_pending: bool = False) -> None:
        if cancel_pending:
            for record in self.list():
                self.cancel(record.job_id)
        self._executor.shutdown(wait=wait, cancel_futures=cancel_pending)


__all__ = ["JobCancelled", "JobContext", "JobManager", "JobRecord", "JobTimedOut"]
