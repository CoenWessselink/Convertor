"""Normalize a manually observed Trimble/CWS reference session.

This tool never drives Trimble and never invents observations. It hashes the
files and screenshots supplied by an operator and emits explicit external
evidence blockers for every missing measurement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "validation" / "trimble_parity"
DEFAULT_SESSION = DEFAULT_OUTPUT / "reference" / "REFERENCE_SESSION.json"
BLOCKED_EXTERNAL_EVIDENCE = "BLOCKED_EXTERNAL_EVIDENCE"
PASS = "PASS"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve(value: str | None, base: Path) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def _file_record(value: str | None, base: Path) -> dict[str, Any]:
    path = _resolve(value, base)
    exists = bool(path and path.is_file())
    return {"path": str(path) if path else None, "exists": exists, "size_bytes": path.stat().st_size if exists and path else None, "sha256": _sha256(path) if exists and path else None}


def _write(output: Path, name: str, payload: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / name).write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def build_reference_artifacts(session_path: Path = DEFAULT_SESSION, *, output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    session = json.loads(session_path.read_text(encoding="utf-8"))
    base = session_path.parent
    generated_at = datetime.now(timezone.utc).isoformat()
    trimble = dict(session.get("trimble") or {})
    cws = dict(session.get("cws") or {})
    pairing = dict(session.get("pairing") or {})
    host = dict(session.get("host") or {})
    trimble_executable = _file_record(trimble.get("executable"), base)
    cws_executable = _file_record(cws.get("executable"), base)
    trimble_model = _file_record(trimble.get("model_path"), base)
    capture_dir = _resolve(session.get("capture_directory"), base)
    captures: list[dict[str, Any]] = []
    if capture_dir and capture_dir.is_dir():
        for path in sorted(capture_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                captures.append({"path": str(path), "name": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)})
    trimble_captures = [row for row in captures if row["name"].lower().startswith("trimble_")]
    cws_captures = [row for row in captures if row["name"].lower().startswith("cws_")]
    same_model_verified = pairing.get("same_model_verified") is True
    environment_complete = all([trimble_executable["exists"], bool(trimble.get("file_version")), trimble_model["exists"], cws_executable["exists"], bool(cws.get("source_file_id")), bool(host.get("os")), bool(host.get("gpus")), bool(trimble_captures), bool(cws_captures), same_model_verified])
    environment = {
        "schema": "cws-trimble-reference-environment-1.0",
        "generated_at": generated_at,
        "status": PASS if environment_complete else BLOCKED_EXTERNAL_EVIDENCE,
        "blocking_reason": None if environment_complete else "Executable, version, exact model identity, host or paired capture evidence is incomplete.",
        "same_model_verified": same_model_verified,
        "verification_basis": pairing.get("verification_basis", []),
        "trimble": {**trimble, "executable_evidence": trimble_executable, "model_evidence": trimble_model},
        "cws": {**cws, "executable_evidence": cws_executable},
        "host": host,
        "captures": captures,
    }
    observed_gestures = dict((session.get("input") or {}).get("observations") or {})
    gestures: dict[str, dict[str, Any]] = {}
    for name in ("orbit", "pan", "wheel_zoom", "selection", "visibility"):
        observation = dict(observed_gestures.get(name) or {})
        verified = observation.get("trimble_observed") is True and observation.get("cws_compared") is True
        gestures[name] = {"status": PASS if verified else BLOCKED_EXTERNAL_EVIDENCE, "trimble_observed": observation.get("trimble_observed") is True, "cws_compared": observation.get("cws_compared") is True, "notes": observation.get("notes", "No paired live observation recorded.")}
    input_complete = all(row["status"] == PASS for row in gestures.values())
    input_mapping = {"schema": "cws-trimble-input-mapping-1.0", "generated_at": generated_at, "status": PASS if input_complete else BLOCKED_EXTERNAL_EVIDENCE, "blocking_reason": None if input_complete else "One or more Trimble gestures lack a paired live observation.", "device_profile": (session.get("input") or {}).get("device_profile", {}), "gestures": gestures}
    camera_verified = pairing.get("same_camera_verified") is True
    capture_integrity = bool(trimble_captures and cws_captures and all(row.get("sha256") for row in captures))
    visual_complete = same_model_verified and camera_verified and capture_integrity
    visual = {"schema": "cws-trimble-visual-reference-1.0", "generated_at": generated_at, "status": PASS if visual_complete else BLOCKED_EXTERNAL_EVIDENCE, "blocking_reason": None if visual_complete else "The model is paired, but camera-aligned Trimble/CWS captures have not been recorded.", "same_model_verified": same_model_verified, "same_camera_verified": camera_verified, "capture_integrity_verified": capture_integrity, "trimble_captures": trimble_captures, "cws_captures": cws_captures}
    metrics = dict(session.get("performance") or {})
    required_metrics = ("cold_load_ms", "first_visual_ms", "navigation_fps", "input_latency_p95_ms")
    metrics_complete = metrics.get("trimble_measured") is True and all(metrics.get(name) is not None for name in required_metrics)
    performance = {"schema": "cws-trimble-performance-reference-1.0", "generated_at": generated_at, "status": PASS if metrics_complete else BLOCKED_EXTERNAL_EVIDENCE, "blocking_reason": None if metrics_complete else "Trimble cold-load, first-visual, FPS and input-latency measurements are incomplete.", "required_metrics": list(required_metrics), "trimble": {name: metrics.get(name) for name in required_metrics}, "measurement_method": metrics.get("measurement_method")}
    _write(output_dir, "TRIMBLE_REFERENCE_ENVIRONMENT.json", environment)
    _write(output_dir, "TRIMBLE_INPUT_MAPPING.json", input_mapping)
    _write(output_dir, "TRIMBLE_VISUAL_REFERENCE.json", visual)
    _write(output_dir, "TRIMBLE_PERFORMANCE_REFERENCE.json", performance)
    return {"session": session, "environment": environment, "input_mapping": input_mapping, "visual": visual, "performance": performance}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, default=DEFAULT_SESSION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_reference_artifacts(args.session, output_dir=args.output)
    print(json.dumps({key: value["status"] for key, value in result.items() if isinstance(value, dict) and "status" in value}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
