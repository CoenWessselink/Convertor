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


def _export_review(snapshot: BOMSnapshot, directory: str | Path, *, action: str, name: str) -> dict[str, Path]:
    formats = {'export.xlsx': ('xlsx',), 'export.csv': ('csv',), 'export.json': ('json',),
               'export.review': ('xlsx','csv','json','pdf')}
    if action not in formats:
        raise ValueError('Geen afzonderlijke BOM-reviewexport voor ' + action)
    target = Path(directory).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    final = target / safe_filename(f'{name}_{action.split(".")[-1]}_{uuid4().hex[:10]}')
    with tempfile.TemporaryDirectory(prefix='.cws-bom-review-', dir=target) as folder:
        stage = Path(folder) / 'payload'
        outputs = export_bom_package(snapshot, stage, package_name=safe_filename(name),
            formats=formats[action], create_zip=action=='export.review')
        if any(not path.is_file() for path in outputs.values()):
            raise RuntimeError('BOM-uitvoerder mist een opgegeven uitvoerbestand')
        stage.rename(final)
    return {key: final/path.name for key,path in outputs.items()}
