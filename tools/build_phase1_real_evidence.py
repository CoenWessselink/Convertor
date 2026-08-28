from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PHASES = ROOT / "validation" / "phases"
LARGE = PHASES / "PHASE_1_LARGE_MODEL_PERFORMANCE.json"
RESULT = ROOT / "validation" / "results" / "viewer-v6-real-11881-exact-source.json"
OUTPUT = PHASES / "PHASE_1_REAL_SOURCE_RESULT_DIFFERENCE.json"


def _strings(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, str):
        yield value


def _find_source(payload: dict[str, Any]) -> Path | None:
    for value in _strings(payload):
        candidate = Path(value)
        if candidate.suffix.lower() not in {".step", ".stp", ".ifc"}:
            continue
        if candidate.is_file():
            return candidate.resolve()
        matches = sorted((ROOT / "reference-models-local").rglob(candidate.name))
        if matches:
            return matches[0].resolve()
    return None


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    large = json.loads(LARGE.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    source = _find_source(large)
    inspection = dict(result.get("inspection") or {})
    metrics = dict(inspection.get("metrics") or {})
    topology = dict(inspection.get("topology") or {})
    actual_sha = _sha(source) if source else ""
    expected_sha = str(inspection.get("source_sha256") or "")
    checks = {
        "source_exists": bool(source),
        "source_hash_matches_result_provenance": bool(actual_sha and actual_sha == expected_sha),
        "result_passed": result.get("status") == "passed",
        "result_is_exact_native_brep": inspection.get("status") == "resolved_exact" and inspection.get("geometry_kind") == "native_brep",
        "selection_verified": inspection.get("selection_verified") is True,
        "solid_valid": metrics.get("valid") is True and int(topology.get("solid_count") or 0) > 0,
        "topology_is_non_empty": all(int(topology.get(key) or 0) > 0 for key in ("face_count", "edge_count", "vertex_count")),
        "source_and_result_are_distinct_artifacts": bool(source and source.resolve() != RESULT.resolve()),
    }
    payload = {
        "schema": "cws-phase1-real-source-result-difference-evidence-1.0",
        "status": "passed" if all(checks.values()) else "failed",
        "source": {"path": str(source) if source else "", "bytes": source.stat().st_size if source else 0, "sha256": actual_sha, "representation": source.suffix.lower().lstrip(".") if source else ""},
        "result": {"path": str(RESULT), "bytes": RESULT.stat().st_size, "sha256": _sha(RESULT), "status": inspection.get("status"), "geometry_kind": inspection.get("geometry_kind"), "source_geometry_hash": inspection.get("source_geometry_hash"), "metrics": metrics, "topology": topology},
        "difference": {
            "representation_changed": True,
            "source_representation": source.suffix.lower().lstrip(".") if source else "",
            "result_representation": "canonical exact-native-BREP inspection JSON",
            "geometry_loss_detected": False if checks["result_is_exact_native_brep"] and checks["solid_valid"] else None,
            "provenance_sha256_equal": actual_sha == expected_sha and bool(actual_sha),
            "result_bytes_minus_source_bytes": RESULT.stat().st_size - source.stat().st_size if source else None,
        },
        "checks": checks,
        "inputs": {"large_model_evidence": str(LARGE), "exact_result_evidence": str(RESULT)},
    }
    PHASES.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"PHASE_1_REAL_SOURCE_RESULT_DIFFERENCE = {payload['status'].upper()}")
    print(OUTPUT)
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
