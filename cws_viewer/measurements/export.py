"""Measurement JSON/CSV export without altering geometry or review state."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .model import MeasurementRecord


def export_json(records: Iterable[MeasurementRecord], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "cws-viewer-measurements-1.0", "measurements": [item.to_dict() for item in records]}
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output


def export_csv(records: Iterable[MeasurementRecord], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "measurement_id", "kind", "formatted_text", "value", "unit", "proof",
            "status", "production_eligible", "name", "note", "anchor_count", "invalid_reason",
        ])
        writer.writeheader()
        for item in records:
            writer.writerow({
                "measurement_id": item.measurement_id,
                "kind": item.kind,
                "formatted_text": item.formatted_text,
                "value": item.value,
                "unit": item.unit,
                "proof": item.proof.value,
                "status": item.status.value,
                "production_eligible": item.production_eligible,
                "name": item.name,
                "note": item.note,
                "anchor_count": len(item.anchors),
                "invalid_reason": item.invalid_reason,
            })
    return output


__all__ = ["export_json", "export_csv"]
