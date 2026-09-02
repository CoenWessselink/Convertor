from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ALLOWED_STATUSES = ("PASS", "FAIL", "BLOCKED", "NOT_TESTED")


def load_master_traceability_gate(
    root: Path,
    traceability_path: Path | None = None,
) -> dict[str, Any]:
    path = traceability_path or root / "requirements" / "MASTER_REQUIREMENT_TRACEABILITY.json"
    if not path.is_file():
        return {
            "schema": "cws-master-release-gate-1.0",
            "status": "FAIL",
            "path": str(path),
            "required_total": 0,
            "counts": {status: 0 for status in ALLOWED_STATUSES},
            "reason": "Master requirement traceability is missing.",
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    requirements = list(payload.get("requirements") or [])
    counts = Counter(str(item.get("status", "NOT_TESTED")).upper() for item in requirements)
    normalized_counts = {status: int(counts.get(status, 0)) for status in ALLOWED_STATUSES}
    unknown = sorted(status for status in counts if status not in ALLOWED_STATUSES)
    required_total = int(payload.get("required_total") or len(requirements))
    complete = (
        bool(requirements)
        and required_total == len(requirements)
        and normalized_counts["PASS"] == required_total
        and not unknown
    )
    return {
        "schema": "cws-master-release-gate-1.0",
        "status": "PASS" if complete else "FAIL",
        "path": str(path),
        "required_total": required_total,
        "observed_total": len(requirements),
        "counts": normalized_counts,
        "unknown_statuses": unknown,
        "source_schema": payload.get("schema"),
        "source_authority": payload.get("source_authority"),
    }


def require_master_traceability_pass(
    root: Path,
    traceability_path: Path | None = None,
) -> dict[str, Any]:
    gate = load_master_traceability_gate(root, traceability_path)
    if gate["status"] != "PASS":
        counts = gate.get("counts", {})
        raise RuntimeError(
            "Master requirement traceability is not release-ready: "
            f"PASS={counts.get('PASS', 0)}, FAIL={counts.get('FAIL', 0)}, "
            f"BLOCKED={counts.get('BLOCKED', 0)}, NOT_TESTED={counts.get('NOT_TESTED', 0)}"
        )
    return gate
