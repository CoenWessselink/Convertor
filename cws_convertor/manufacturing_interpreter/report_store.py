from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .contracts import ENGINE_VERSION
from .recognition_cache import stable_sha256


REPORT_SCHEMA = "cws-manufacturing-interpretation-v3"


class ReportInvalidatedError(RuntimeError):
    pass


def save_report(report: Any, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    envelope = {
        "schema": REPORT_SCHEMA,
        "engine_version": ENGINE_VERSION,
        "source_sha256": report.source_sha256,
        "source_geometry_hash": report.source_geometry_hash,
        "tolerance_policy_hash": report.tolerance_policy_hash,
        "profile_database_hash": report.profile_database_hash,
        "algorithm_versions": list(report.algorithm_versions),
        "semantic_sha256": report.semantic_sha256,
        "payload_sha256": stable_sha256(payload),
        "report": payload,
    }
    handle, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(envelope, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, target)
    finally:
        try:
            Path(temporary_name).unlink(missing_ok=True)
        except OSError:
            pass
    return target


def load_report_envelope(
    path: str | Path,
    *,
    source_sha256: str,
    source_geometry_hash: str,
    tolerance_policy_hash: str,
    profile_database_hash: str,
) -> dict[str, Any]:
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = {
        "schema": REPORT_SCHEMA,
        "engine_version": ENGINE_VERSION,
        "source_sha256": source_sha256,
        "source_geometry_hash": source_geometry_hash,
        "tolerance_policy_hash": tolerance_policy_hash,
        "profile_database_hash": profile_database_hash,
    }
    mismatches = [key for key, value in expected.items() if str(envelope.get(key, "")) != str(value)]
    if mismatches:
        raise ReportInvalidatedError("Report invalidated by: " + ", ".join(mismatches))
    payload = envelope.get("report")
    if not isinstance(payload, dict) or stable_sha256(payload) != envelope.get("payload_sha256"):
        raise ReportInvalidatedError("Report payload hash mismatch")
    return envelope


__all__ = ["REPORT_SCHEMA", "ReportInvalidatedError", "load_report_envelope", "save_report"]
