#!/usr/bin/env python3
"""Read the existing authoritative SteelModel snapshot; emit review-only handover.

No geometry synthesis, material fallback, database lookup or authority promotion.
Requires the source repository's existing SteelModel schema verifier.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys


def import_snapshot(source: Path) -> dict:
    from cws_convertor.steel_model.contracts import SteelModelSnapshot
    payload = source.read_bytes()
    snapshot = SteelModelSnapshot.from_json_bytes(payload)
    if snapshot.units != "mm":
        raise ValueError("Only explicit millimetre snapshots are supported; no implicit unit conversion")
    source_id = snapshot.project_id
    revision = snapshot.project_semantic_sha256
    parts = []
    for entity in snapshot.entities:
        if entity.entity_type != "part":
            continue
        properties = dict(entity.display_properties)
        material_raw = properties.get("material")
        material_grade = properties.get("material_grade")
        material = material_grade or material_raw or None
        material_conflict = bool(material_raw and material_grade and material_raw != material_grade)
        # Display fields and source accuracy labels are provenance, not verified
        # engineering intent. The snapshot contains no complete native payload.
        part = {
            "CanonicalId": entity.steel_model_id,
            "SourceId": source_id,
            "SourceRevision": revision,
            "PhysicalRole": "PRIMARY",
            "Kind": "UNKNOWN",
            "Profile": properties.get("profile") or None,
            "MaterialRaw": material_raw,
            "Material": material,
            "MaterialAuthority": None,
            "ProfileAuthority": None,
            "GeometryAuthority": None,
            "GeometryHash": None,
            "ManufacturingHash": None,
            "Points": [],
            "Phase": properties.get("phase") or None,
            "Mark": properties.get("part_position") or None,
            "Udas": {
                "SOURCE_TRACE_JSON": json.dumps(entity.source.to_dict(), ensure_ascii=False, sort_keys=True),
                "SOURCE_GEOMETRY_HASH": entity.geometry_hash,
                "SOURCE_MANUFACTURING_HASH": entity.manufacturing_hash,
                "SOURCE_ACCURACY_LABEL": entity.accuracy_status.value,
                "SOURCE_MATERIAL_JSON": json.dumps({"material": material_raw, "material_grade": material_grade}, ensure_ascii=False, sort_keys=True),
                "SOURCE_TRANSFORM_JSON": json.dumps(list(entity.global_transform)),
                "SOURCE_LOCAL_TRANSFORM_JSON": json.dumps(list(entity.local_transform)),
                "SOURCE_UNITS": snapshot.units,
                "SOURCE_COORDINATE_SYSTEM_JSON": json.dumps(dict(snapshot.coordinate_system), ensure_ascii=False, sort_keys=True),
                "SOURCE_DISPLAY_PROPERTIES_JSON": json.dumps(properties, ensure_ascii=False, sort_keys=True),
                "HANDOVER_STATUS": "REVIEW_REQUIRED_MATERIAL_CONFLICT" if material_conflict else "REVIEW_REQUIRED_GEOMETRY_PAYLOAD_MISSING",
            },
            "Managed": False,
            "ManualDownstream": False,
            "NativeId": None,
        }
        parts.append(part)
    return {"SchemaVersion": "1.0", "SourceId": source_id,
            "SourceRevision": revision, "SourceSha256": hashlib.sha256(payload).hexdigest(),
            "Parts": parts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo))
    result = import_snapshot(args.snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(f"{len(result['Parts'])} canonical occurrences; REVIEW_REQUIRED; no geometry/production authority")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
