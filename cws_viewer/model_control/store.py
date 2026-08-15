"""Atomic sidecar store for viewer model-control review issues."""
from __future__ import annotations

import json
from pathlib import Path
import os
from hashlib import sha256
from typing import Iterable

from .model import ClashRecord


def _digest(payload: dict) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class ModelControlStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, project_id: str, records: Iterable[ClashRecord]) -> Path:
        data = {
            "schema_version": "cws-model-control-review-1.0",
            "project_id": str(project_id),
            "records": [item.to_dict() for item in records],
        }
        data["sha256"] = _digest(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, self.path)
        return self.path

    def load(self) -> dict:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        expected = str(data.pop("sha256", ""))
        actual = _digest(data)
        if expected != actual:
            raise ValueError("Model Control store checksum mismatch")
        data["sha256"] = expected
        return data


__all__ = ["ModelControlStore"]
