"""Uniform local logging and crash-report support.

No customer geometry is written automatically. Callers decide which structured
fields are safe to include in a log record.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import traceback
import uuid
from typing import Any

from .product import APP_NAME, APP_SLUG, APP_VERSION


SESSION_ID = uuid.uuid4().hex


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "app": APP_NAME,
            "version": APP_VERSION,
            "session_id": SESSION_ID,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("error_code", "job_id", "project_id", "entity_id", "operation"):
            value = getattr(record, key, None)
            if value not in (None, ""):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def default_log_directory() -> Path:
    base = Path.home() / ".cws-convertor" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def configure_logging(*, log_directory: str | Path | None = None, verbose: bool = False) -> logging.Logger:
    directory = Path(log_directory) if log_directory else default_log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("cws_convertor")
    if root.handlers:
        return root
    root.setLevel(logging.DEBUG if verbose else logging.INFO)

    file_handler = RotatingFileHandler(
        directory / f"{APP_SLUG}.jsonl",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)
    return root


@dataclass
class CrashReporter:
    directory: Path

    @classmethod
    def install(cls, directory: str | Path | None = None) -> "CrashReporter":
        target = Path(directory) if directory else default_log_directory() / "crashes"
        target.mkdir(parents=True, exist_ok=True)
        reporter = cls(target)
        sys.excepthook = reporter._hook
        return reporter

    def _hook(self, exc_type, exc_value, exc_traceback) -> None:  # type: ignore[no-untyped-def]
        report = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "session_id": SESSION_ID,
            "exception_type": getattr(exc_type, "__name__", str(exc_type)),
            "message": str(exc_value),
            "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        }
        path = self.directory / f"crash_{SESSION_ID}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logging.getLogger("cws_convertor").critical("Onverwerkte fout", exc_info=(exc_type, exc_value, exc_traceback))
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
