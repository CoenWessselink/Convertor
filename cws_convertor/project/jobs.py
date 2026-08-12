"""Cancellable background job manager used by project import/export phases."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
import threading
from typing import Any, Callable, Generic, TypeVar
from uuid import uuid4

from cws_convertor.errors import CWSError, ErrorCode
from .model import utc_now_iso


T = TypeVar("T")


class JobCancelled(CWSError):
    def __init__(self, message: str = "Job is geannuleerd") -> None:
        super().__init__(message, ErrorCode.JOB_CANCELLED)


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    description: str = ""
    project_id: str = ""
    status: str = "queued"  # queued, running, completed, failed, cancelled
    progress: float = 0.0
    message: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    started_at: str = ""
    finished_at: str = ""
    result: Any = None
    error: str = ""
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

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def check_cancelled(self) -> None:
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
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        job_id = str(uuid4())
        record = JobRecord(
            job_id=job_id,
            job_type=job_type,
            description=description,
            project_id=project_id,
            metadata=dict(metadata or {}),
        )
        cancel_event = threading.Event()
        with self._lock:
            self._records[job_id] = record
            self._cancel_events[job_id] = cancel_event
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
        with self._lock:
            record = self._records[job_id]
            record.status = "running"
            record.started_at = utc_now_iso()
            record.message = "Gestart"
        self._notify(record)
        try:
            context.check_cancelled()
            result = action(context, *args, **kwargs)
            context.check_cancelled()
            with self._lock:
                record = self._records[job_id]
                record.status = "completed"
                record.progress = 1.0
                record.message = "Gereed"
                record.finished_at = utc_now_iso()
                record.result = result
            self._notify(record)
            return result
        except JobCancelled as exc:
            with self._lock:
                record = self._records[job_id]
                record.status = "cancelled"
                record.message = str(exc)
                record.finished_at = utc_now_iso()
                record.error = str(exc)
            self._notify(record)
            return None
        except Exception as exc:
            with self._lock:
                record = self._records[job_id]
                record.status = "failed"
                record.message = "Mislukt"
                record.finished_at = utc_now_iso()
                record.error = f"{type(exc).__name__}: {exc}"
            self._notify(record)
            raise

    def _update(
        self,
        job_id: str,
        *,
        progress: float | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._records[job_id]
            if progress is not None:
                record.progress = max(0.0, min(1.0, float(progress)))
            if message is not None:
                record.message = str(message)
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
            event.set()
            if future is not None and future.cancel():
                record.status = "cancelled"
                record.finished_at = utc_now_iso()
                record.message = "Geannuleerd vóór start"
                self._notify(record)
            return True

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


__all__ = ["JobCancelled", "JobRecord", "JobContext", "JobManager"]
