"""Produce exact native-BREP result evidence for one deterministic STEP source."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() not in {".step", ".stp"}:
        parser.error("--input must point to an existing STEP file")
    started = time.perf_counter()
    session = ProjectSession.new("Phase 1 exact source evidence", created_by="acceptance")
    try:
        registration = session.register_sources(
            [source], include_step_geometry=True, user="acceptance"
        )[0]
        semantic = session.semantic_import_source(
            registration.source.source_id, user="acceptance"
        )
        part = next(
            (
                candidate
                for candidate in session.project.parts.values()
                if candidate.geometry_descriptor.get("source_locator", {})
                .get("selector", {})
                .get("entity_ids")
            ),
            None,
        )
        inspection = (
            session.inspect_part_source_geometry(
                part.internal_id, persist=False, user="acceptance"
            )
            if part is not None
            else None
        )
        inspection_payload = inspection.to_dict() if inspection is not None else {}
        topology = dict(inspection_payload.get("topology") or {})
        metrics = dict(inspection_payload.get("metrics") or {})
        checks = {
            "semantic_import_completed": semantic.semantic_import_complete,
            "one_part_selected": part is not None,
            "resolved_exact": inspection_payload.get("status") == "resolved_exact",
            "native_brep": inspection_payload.get("geometry_kind") == "native_brep",
            "selection_verified": inspection_payload.get("selection_verified") is True,
            "valid_solid": metrics.get("valid") is True
            and int(topology.get("solid_count") or 0) > 0,
            "topology_non_empty": all(
                int(topology.get(key) or 0) > 0
                for key in ("face_count", "edge_count", "vertex_count")
            ),
            "source_sha_bound": inspection_payload.get("source_sha256") == digest(source),
            "production_gate_closed": session.project.production_gate().get("allowed") is False,
        }
        payload = {
            "schema": "cws-phase1-exact-source-result-1.0",
            "status": "passed" if all(checks.values()) else "failed",
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "source": {
                "path": str(source),
                "bytes": source.stat().st_size,
                "sha256": digest(source),
            },
            "inspection": inspection_payload,
            "checks": checks,
        }
        target = args.output.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"PHASE_1_EXACT_SOURCE_RESULT = {payload['status'].upper()}")
        print(target)
        return 0 if payload["status"] == "passed" else 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
