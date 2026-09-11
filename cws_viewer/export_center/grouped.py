"""Exact disjoint export partitions and all-or-nothing package publication.

Grouping describes files, never grants machine permission or changes quantities.
Ambiguous occurrence ownership is rejected instead of duplicating whole parts.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable, Iterable
from uuid import uuid4

from cws_convertor.machine_routing import MachineRoutingService
from cws_convertor.production_export import ExportRequest, ExportStatus, ProductionExportEngine
from cws_convertor.production_export.utils import canonical_json_bytes, safe_filename, sha256_file, stable_hash
from cws_convertor.production_export.verify import verify_export_directory, verify_export_zip

GROUPINGS = frozenset({'combined', 'per_part', 'object', 'part_mark', 'assembly', 'assembly_mark', 'phase', 'batch', 'machine'})


class GroupingError(ValueError):
    """Missing/ambiguous grouping or stale inputs; never broaden the selection."""


def _one(values: Iterable[str], part_id: str, kind: str) -> str:
    supplied = list(values)
    if any(v is not None and (not isinstance(v, (str, int)) or isinstance(v, bool)) for v in supplied):
        raise GroupingError(f'{kind}: ongeldig groepsveld voor {part_id}')
    unique = sorted({str(v).strip() for v in supplied if v is not None and str(v).strip()})
    if len(unique) != 1:
        raise GroupingError(f'{kind}: {part_id} vereist precies één bewezen groep; gevonden {unique}')
    return unique[0]


def _plan(project: Any, part_ids: Iterable[str], kind: str) -> tuple[dict, ...]:
    if kind not in GROUPINGS:
        raise GroupingError('Onbekende exportgroepering: ' + kind)
    ids = tuple(sorted(set(part_ids)))
    if not ids or any(key not in project.parts for key in ids):
        raise GroupingError('Lege of onbekende onderdeel-ID in exportgroepering')
    assignments = MachineRoutingService.assignments(project) if kind == 'machine' else {}
    capabilities = MachineRoutingService.project_capabilities(project, ids) if kind == 'machine' else {}
    groups: dict[str, list[str]] = {}
    for key in ids:
        part = project.parts[key]
        properties = part.properties or {}
        if kind == 'combined':
            group = 'combined'
        elif kind in {'per_part', 'object'}:
            group = key
        elif kind == 'part_mark':
            group = _one([part.part_position], key, kind)
        elif kind in {'assembly', 'assembly_mark'}:
            owners = set(part.assembly_ids) | {a.internal_id for a in project.assemblies.values() if key in a.part_ids}
            owner = _one(owners, key, kind)
            if owner not in project.assemblies or key not in project.assemblies[owner].part_ids:
                raise GroupingError(f'Assemblylidmaatschap ontbreekt/conflicteert: {key}/{owner}')
            group = owner if kind == 'assembly' else _one([project.assemblies[owner].assembly_mark], key, kind)
        elif kind == 'phase':
            group = _one([properties.get(f, '') for f in ('project_phase', 'construction_phase', 'phase', 'bouwfase')], key, kind)
        elif kind == 'batch':
            values = [properties.get(f, '') for f in ('batch', 'batch_id')]
            for batch, record in dict(project.settings.get('batches') or {}).items():
                members = record.get('part_ids', record.get('entity_ids', ())) if isinstance(record, dict) else record
                if isinstance(members, (list, tuple, set, dict)) and key in members:
                    values.append(str(batch))
            group = _one(values, key, kind)
        else:
            assignment = assignments.get(key)
            group = assignment.assigned_machine_id if assignment else ''
            report = capabilities.get(key, {}).get(group)
            if not group or not report or assignment.blocking_codes:
                raise GroupingError(f'Machinegroepering mist geldige toewijzing/capaciteit: {key}')
            service = MachineRoutingService()
            decision = service.route(key, {group: report}, preferred_machine=group)
            if not decision.eligible or service._value(report, 'manufacturing_hash', '') != part.manufacturing_hash:
                raise GroupingError(f'Machinecapaciteit ontbreekt of is verouderd: {key}/{group}')
        groups.setdefault(group, []).append(key)
    return tuple({'key': key, 'part_ids': members} for key, members in sorted(groups.items()))


def _revision(project: Any) -> str:
    # Includes workbench review state, raw fields, grouping and machine evidence,
    # unlike manufacturing_state_sha256, which intentionally hashes fewer fields.
    return project.revision_content_sha256()


def _execute(service: Any, job: Any, output_dir: str | Path, *, create_zip: bool,
             progress: Callable | None, cancelled: Callable[[], bool] | None) -> tuple[Path, str]:
    from cws_convertor.project.jobs import JobCancelled
    kind = str(job.scope.metadata.get('grouping', 'combined'))
    expected = job.preflight.source_revision_sha256

    def guard() -> None:
        if cancelled and cancelled():
            raise JobCancelled('Export geannuleerd vóór publicatie; geen deelpakket vrijgegeven')
        if (_revision(service.project) != expected or
                job.preflight.calculate_hash() != job.preflight.manifest_sha256 or
                job.preflight.resolution.calculate_hash() != job.preflight.resolution.manifest_sha256 or
                _plan(service.project, job.preflight.resolution.selected_part_ids, kind) != job.preflight.group_plan):
            raise GroupingError('Project, vrijgavebewijs, groepering of selectie gewijzigd sinds preflight')

    guard()
    frozen = deepcopy(service.project)
    guard()
    target = Path(output_dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    # Never overwrite an earlier accepted package. Failure/cancellation only
    # removes our uncommitted staging directory, not an existing user's output.
    name = safe_filename(f'CWS_{frozen.project_name}_{kind}_{job.job_id}_{uuid4().hex[:8]}')
    final = target / name
    records = []
    with tempfile.TemporaryDirectory(prefix='.cws-export-', dir=target) as temporary:
        stage = Path(temporary)
        payload = stage / 'payload'
        payload.mkdir()
        for index, group in enumerate(job.preflight.group_plan):
            guard()
            if progress:
                progress(.1 + .75 * index / len(job.preflight.group_plan), f'Groep {index+1}/{len(job.preflight.group_plan)}: {group["key"]}')
            request = ExportRequest(output_dir=stage / f'work-{index}', formats=list(job.requested_formats),
                part_ids=set(group['part_ids']), strict_mode=True, include_blocked_review_files=False,
                include_assembly_packages=kind in {'combined', 'assembly', 'assembly_mark'},
                create_zip=True, deterministic_zip=True)
            manifest, root, archive = service.exporter.export_project(frozen, request)
            guard()
            actual = [item.part_id for item in manifest.items]
            if (len(actual) != len(set(actual)) or set(actual) != set(group['part_ids']) or
                    not actual or not manifest.summary.get('production_ready') or
                    any(item.status != ExportStatus.EXPORTED for item in manifest.items)):
                raise GroupingError('Runtime exportgate blokkeert of scope wijkt af in groep ' + group['key'])
            verify_export_directory(root)
            if archive is None:
                # Useful for exporters returning only a verified directory;
                # archive creation still uses the same production package writer.
                archive = stage / f'work-{index}.zip'
                ProductionExportEngine._create_zip(root, archive, True)
            verify_export_zip(archive)
            filename = f'{index+1:03d}_{safe_filename(group["key"])[:70]}_{stable_hash(group["key"])[:12]}.zip'
            shutil.copyfile(archive, payload / filename)
            records.append({**group, 'file': filename, 'sha256': sha256_file(payload / filename),
                'manifest_sha256': manifest.manifest_sha256,
                'quantities': {key: frozen.parts[key].quantity_total for key in group['part_ids']}})
        guard()
        exported_ids = [key for group in records for key in group['part_ids']]
        if len(exported_ids) != len(set(exported_ids)) or set(exported_ids) != set(job.preflight.resolution.selected_part_ids):
            raise GroupingError('Groepering is geen exacte, disjuncte partitie van de selectie')
        manifest_data = {'schema': 'cws-grouped-production-export-1', 'project_id': frozen.project_id,
            'source_revision_sha256': expected, 'scope': job.scope.to_dict(),
            'preflight_sha256': job.preflight.manifest_sha256, 'grouping': kind,
            'requested_formats': list(job.requested_formats), 'groups': records,
            'selected_part_ids': sorted(exported_ids), 'status': 'verified',
            'machine_transfer_allowed': False, 'machine_qualification_granted': False}
        manifest_data['manifest_sha256'] = stable_hash(manifest_data)
        (payload / 'manifest.json').write_bytes(canonical_json_bytes(manifest_data))
        ProductionExportEngine._write_checksums(payload)
        verify_export_directory(payload)
        if create_zip:
            archive = stage / 'package.zip'
            ProductionExportEngine._create_zip(payload, archive, True)
            verify_export_zip(archive)
            shutil.move(str(archive), payload / 'package.zip')
        if progress:
            progress(.98, 'Alle groepen heringelezen; laatste broncontrole vóór gezamenlijke publicatie')
        guard()
        payload.rename(final)
    return (final / 'package.zip' if create_zip else final), manifest_data['manifest_sha256']
