"""Exact part-only BOM projections and format-specific review exports.

This is a view of the canonical BOM, not a second quantity/material authority.
A part selection does not silently acquire its entire assembly or equal marks.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import math
import tempfile
from typing import Any, Iterable
from uuid import uuid4

from .models import BOMSnapshot
from .export import export_bom_package
from cws_convertor.production_export.utils import safe_filename


def _part_snapshot(snapshot: BOMSnapshot, project: Any, part_ids: Iterable[str]) -> BOMSnapshot:
    ids = set(part_ids)
    if not ids or any(key not in project.parts for key in ids):
        raise ValueError('Lege of onbekende expliciete BOM-onderdeelselectie')
    rows = []
    for row in snapshot.part_bom:
        selected = sorted(ids.intersection(row.part_ids))
        if not selected:
            continue
        if set(selected) == set(row.part_ids):
            rows.append(replace(row, part_ids=selected))
            continue
        parts = [project.parts[key] for key in selected]
        quantities = [part.quantity_total for part in parts]
        if any(isinstance(q, bool) or not isinstance(q, (int, float)) or not math.isfinite(q) or q <= 0 or int(q) != q for q in quantities):
            raise ValueError('Gedeeltelijke BOM-groep bevat een onbekend/ongeldig aantal')
        # Do not apportion a mass by guessing a missing canonical component.
        if any(not isinstance(p.mass_each_kg, (int, float)) or not math.isfinite(p.mass_each_kg) or p.mass_each_kg <= 0 for p in parts):
            raise ValueError('Gedeeltelijke BOM-groep mist betrouwbaar individueel gewicht')
        if any(not isinstance(p.surface_area_each_m2, (int, float)) or not math.isfinite(p.surface_area_each_m2) or p.surface_area_each_m2 < 0 for p in parts):
            raise ValueError('Gedeeltelijke BOM-groep mist betrouwbaar individueel oppervlak')
        rows.append(replace(row, part_ids=selected, quantity=sum(int(q) for q in quantities),
            total_mass_kg=round(sum(p.mass_each_kg * p.quantity_total for p in parts), 6),
            total_surface_area_m2=round(sum(p.surface_area_each_m2 * p.quantity_total for p in parts), 9),
            source_entity_ids=sorted({p.source_identity.source_entity_id for p in parts if p.source_identity.source_entity_id})))
    if {key for row in rows for key in row.part_ids} != ids:
        raise ValueError('De BOM bevat niet alle gevraagde onderdeel-IDs; geen gedeeltelijke export')
    groups = {row.group_id for row in rows}
    materials = []
    for row in snapshot.material_bom:
        members = [p for p in rows if (p.category, p.material, p.profile) == (row.category, row.material, row.profile)]
        if members:
            materials.append(replace(row, quantity=sum(p.quantity for p in members),
                net_length_mm=round(sum(p.length_mm*p.quantity for p in members), 6),
                total_mass_kg=round(sum(p.total_mass_kg for p in members), 6),
                total_surface_area_m2=round(sum(p.total_surface_area_m2 for p in members), 9),
                part_group_count=len(members), blocked=any(p.blocked for p in members),
                blocking_reasons=sorted({reason for p in members for reason in p.blocking_reasons})))
    conflicts = [c for c in snapshot.conflicts if ids.intersection(c.entity_ids) or (not c.entity_ids and groups.intersection(c.group_ids))]
    trace = [dict(t) for t in snapshot.traceability if t.get('internal_id') in ids]
    summary = {**snapshot.summary, 'part_group_count': len(rows), 'assembly_group_count': 0,
        'purchase_group_count': 0, 'fastener_group_count': 0, 'weld_group_count': 0,
        'material_group_count': len(materials), 'traceability_record_count': len(trace),
        'total_part_mass_kg': round(sum(p.total_mass_kg for p in rows), 6),
        'total_part_surface_m2': round(sum(p.total_surface_area_m2 for p in rows), 9),
        'total_part_length_mm': round(sum(p.length_mm*p.quantity for p in rows), 6),
        'purchase_quantity': 0, 'fastener_quantity': 0, 'weld_object_count': 0,
        'blocking_conflict_count': sum(c.blocking for c in conflicts),
        'warning_conflict_count': sum(not c.blocking for c in conflicts),
        'full_project_bom_sha256': snapshot.snapshot_sha256,
        'scope': {'family':'parts','entity_ids':sorted(ids),'group_ids':sorted(groups),'exact_part_selection':True}}
    validation = replace(snapshot.validation,
        blocking_conflict_count=summary['blocking_conflict_count'], warning_conflict_count=summary['warning_conflict_count'],
        messages=[*snapshot.validation.messages, 'Exacte partselectie; assembly-, inkoop-, las- en boutregels niet meegeëxporteerd.']) if snapshot.validation else None
    result = replace(snapshot, part_bom=rows, assembly_bom=[], purchase_bom=[], fastener_bom=[], weld_bom=[],
                     material_bom=materials, conflicts=conflicts, traceability=trace, summary=summary, validation=validation)
    result.refresh_hash()
    return result


from copy import deepcopy
import hashlib
import json
import re
import shutil
from typing import Callable

REVIEW_EXPORT_ACTIONS = {
    "export.xlsx": ("XLSX",),
    "export.csv": ("CSV",),
    "export.json": ("JSON",),
    "export.review": ("XLSX", "CSV", "JSON", "PDF", "BOM-package"),
}


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def export_bom_review(
    snapshot: BOMSnapshot,
    output_dir: str | Path,
    *,
    action_id: str,
    source_snapshot_sha256: str = "",
    preflight_sha256: str = "",
    validate_before_publish: Callable[[], bool] | None = None,
    package_name: str | None = None,
    require_existing_directory: bool = True,
) -> dict[str, Path]:
    """Export exactly one requested review representation (or the full review kit).

    All data is frozen before writing. Returned paths are absolute and include
    the manifest/checksum files. A new, distinct directory prevents stale mixed
    formats and preserves previous exports. Any failure removes staging output.
    """
    if action_id not in REVIEW_EXPORT_ACTIONS:
        raise ValueError("Onbekende reviewexportactie: " + str(action_id))
    frozen = deepcopy(snapshot)
    original_hash = frozen.snapshot_sha256
    if not original_hash or frozen.refresh_hash() != original_hash:
        raise ValueError("BOM-snapshot is gewijzigd of heeft geen geldige hash")
    if validate_before_publish is not None and not validate_before_publish():
        raise ValueError("Reviewexport heeft verouderde brongegevens")
    json.dumps(frozen.to_dict(), allow_nan=False)  # Reject non-finite payload data.
    target = Path(output_dir).expanduser().resolve(strict=require_existing_directory)
    if not require_existing_directory:
        target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise ValueError("De review-uitvoermap bestaat niet of is geen map")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", (package_name or frozen.project_name)).strip("._-")[:64] or "CWS_BOM"
    bundle = target / f"{stem}_{action_id.split('.')[-1]}_{original_hash[:12]}_{uuid4().hex[:12]}"
    work = Path(tempfile.mkdtemp(prefix=".cws-review-", dir=target))
    try:
        formats = {"export.xlsx": ("xlsx",), "export.csv": ("csv",), "export.json": ("json",),
                   "export.review": ("xlsx", "csv", "json", "pdf")}[action_id]
        export_bom_package(frozen, work, package_name=stem, formats=formats,
                           create_zip=action_id == "export.review")
        files = sorted(path for path in work.iterdir() if path.is_file())
        if not files or any(path.stat().st_size == 0 and path.suffix != ".csv" for path in files):
            raise ValueError("Reviewexport mist een verplicht uitvoerbestand")
        payload = {
            "schema": "cws-bom-review-export-1.0", "action_id": action_id,
            "project_id": frozen.project_id, "source_snapshot_sha256": source_snapshot_sha256,
            "snapshot_sha256": original_hash, "preflight_sha256": preflight_sha256,
            "scope": dict(frozen.summary.get("scope") or {}),
            "review_only": True, "production_release_allowed": False,
            "machine_transfer_allowed": False,
            "files": {path.name: {"sha256": _digest(path), "bytes": path.stat().st_size} for path in files},
        }
        manifest = work / "REVIEW_EXPORT.json"
        manifest.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
        for name, binding in payload["files"].items():
            if _digest(work / name) != binding["sha256"]:
                raise ValueError("Reviewbestand gewijzigd voor publicatie: " + name)
        checks = work / "REVIEW_SHA256SUMS.txt"
        checks.write_text("".join(f"{_digest(path)}  {path.name}\n" for path in [*files, manifest]), encoding="utf-8")
        if validate_before_publish is not None and not validate_before_publish():
            raise ValueError("Project gewijzigd tijdens reviewexport; pakket niet gepubliceerd")
        if bundle.exists() or bundle.is_symlink():
            raise FileExistsError("Reviewexport overschrijft geen bestaande uitvoer: " + str(bundle))
        names = [path.name for path in files] + [manifest.name, checks.name]
        work.rename(bundle)
        return {name: bundle / name for name in names}
    finally:
        if work.exists():
            shutil.rmtree(work)


__all__ = ["export_bom_review", "REVIEW_EXPORT_ACTIONS"]


def _export_review(snapshot: BOMSnapshot, directory: str | Path, *, action: str, name: str,
                   source_snapshot_sha256: str = "", preflight_sha256: str = "",
                   validate_before_publish: Callable[[], bool] | None = None) -> dict[str, Path]:
    """Preserve the existing concurrent API and its format-aware BOM writers."""
    return export_bom_review(snapshot, directory, action_id=action, package_name=name,
        source_snapshot_sha256=source_snapshot_sha256, preflight_sha256=preflight_sha256,
        validate_before_publish=validate_before_publish, require_existing_directory=False)
