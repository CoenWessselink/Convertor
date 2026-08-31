"""Thread-safe staged loading profile and evidence writer."""

from __future__ import annotations

import json
from pathlib import Path
import threading
import time
from typing import Any


class LoadProfileSession:
    def __init__(self, project_id: str = "", *, clock=time.perf_counter) -> None:
        self.project_id = str(project_id)
        self.clock = clock
        self.started_at = float(clock())
        self.finished_at: float | None = None
        self.status = "loading"
        self.stages: dict[str, float] = {}
        self.milestones: dict[str, float] = {}
        self.resources: list[dict[str, Any]] = []
        self.policy: dict[str, Any] = {}
        self._lock = threading.RLock()

    def add_duration(self, name: str, seconds: float) -> None:
        with self._lock:
            self.stages[str(name)] = self.stages.get(str(name), 0.0) + max(0.0, float(seconds))

    def mark(self, name: str) -> None:
        with self._lock:
            self.milestones.setdefault(str(name), max(0.0, self.clock() - self.started_at))

    def set_policy(self, value: dict[str, Any]) -> None:
        with self._lock:
            self.policy = dict(value)

    def record_resource(self, **value: Any) -> None:
        with self._lock:
            self.resources.append(dict(value))

    def finish(self, status: str = "complete") -> None:
        with self._lock:
            if self.finished_at is None:
                self.finished_at = float(self.clock())
            self.status = str(status)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            end = self.finished_at if self.finished_at is not None else self.clock()
            return {
                "schema": "cws-viewer-load-profile-2.0",
                "project_id": self.project_id,
                "status": self.status,
                "elapsed_seconds": max(0.0, float(end) - self.started_at),
                "stages_seconds": dict(sorted(self.stages.items())),
                "milestones_seconds": dict(sorted(self.milestones.items())),
                "policy": dict(self.policy),
                "geometry_resources": list(self.resources),
            }

    def write(self, json_path: str | Path, markdown_path: str | Path | None = None) -> Path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.to_dict()
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if markdown_path is not None:
            markdown = Path(markdown_path)
            lines = ["# CWS Viewer Load Profile", "", f"Status: `{payload['status']}`", "", "## Stages", ""]
            lines.extend(f"- `{name}`: {value:.6f} s" for name, value in payload["stages_seconds"].items())
            lines.extend(["", "## Milestones", ""])
            lines.extend(f"- `{name}`: {value:.6f} s" for name, value in payload["milestones_seconds"].items())
            markdown.parent.mkdir(parents=True, exist_ok=True)
            markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path


__all__ = ["LoadProfileSession"]
