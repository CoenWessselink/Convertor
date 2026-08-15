"""Atomic checksum-protected CWS viewer review package."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Iterable

from .model import MarkupRecord, ReviewIssue

SCHEMA = "cws-viewer-review-2.0"


def _digest(data: dict[str, Any]) -> str:
    return sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


class ReviewStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(
        self,
        *,
        project_id: str,
        scene_hash: str,
        markups: Iterable[MarkupRecord] = (),
        issues: Iterable[ReviewIssue] = (),
        clash_records: Iterable[Any] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        data: dict[str, Any] = {
            "schema_version": SCHEMA,
            "project_id": str(project_id),
            "scene_hash": str(scene_hash),
            "markups": [m.to_dict() for m in markups],
            "issues": [i.to_dict() for i in issues],
            "clash_records": [r.to_dict() if hasattr(r, "to_dict") else dict(r) for r in clash_records],
            "metadata": dict(metadata or {}),
        }
        data["sha256"] = _digest(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, self.path)
        sidecar = self.path.with_suffix(self.path.suffix + ".sha256")
        sidecar.write_text(sha256(self.path.read_bytes()).hexdigest() + "\n", encoding="ascii")
        return self.path

    def load(self, *, expected_project_id: str | None = None) -> dict[str, Any]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        expected = str(data.pop("sha256", ""))
        actual = _digest(data)
        if expected != actual:
            raise ValueError("CWS review store checksum mismatch")
        if data.get("schema_version") != SCHEMA:
            raise ValueError(f"Niet-ondersteund review-schema: {data.get('schema_version')!r}")
        if expected_project_id is not None and str(data.get("project_id")) != str(expected_project_id):
            raise ValueError("Reviewpakket hoort bij een ander project")
        data["sha256"] = expected
        return data


__all__ = ["SCHEMA", "ReviewStore"]
