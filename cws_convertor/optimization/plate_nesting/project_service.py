"""One project-to-plate planning route with optimistic stock transactions.

Plans are planning evidence, never CNC or material-certificate authorization.
Stock is read from the same ProjectModel lots/reservation ledger as the BOM.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
from math import isclose, isfinite
import re
from typing import Any, Iterable
from uuid import uuid4

from material_database import MaterialDatabase
from cws_convertor.bom.material_gate import part_material_blockers
from cws_convertor.optimization.profile_nesting.models import ReservationRequest
from cws_convertor.optimization.profile_nesting.reservation import (
    _LOCK, reserve_physical_stock, release_reservation,
)
from .canonical import (
    PlateCutPlan, PlateGeometryRef, PlateNestDemand, PlateStock, PlateStockBoundary,
    _digest, solve_canonical_plate_nesting, validate_canonical_plate_nesting,
)


def _integer(value, label):
    if isinstance(value, bool) or not isfinite(float(value)) or float(value) != int(value) or int(value) < 0:
        raise ValueError(label + ' moet een geheel niet-negatief aantal zijn')
    return int(value)


def _number(value, label):
    if isinstance(value, bool) or not isfinite(float(value)) or float(value) <= 0:
        raise ValueError(label + ' moet een positief eindig getal zijn')
    return float(value)


def _grade(material, grade, catalog):
    resolved = catalog.resolve(grade)
    if not resolved.resolved:
        raise ValueError('Exacte materiaalkwaliteit ontbreekt: ' + str(grade))
    raw = catalog.resolve(material)
    # A material family may accompany a grade, but a conflicting exact grade may not.
    family_name = str(material).strip().casefold()
    category = resolved.definition.category.casefold()
    family = ((family_name in {'steel', 'staal'} and 'staal' in category) or
              (family_name in {'stainless', 'rvs'} and category == 'roestvast staal') or
              (family_name in {'aluminium', 'aluminum'} and category == 'aluminium'))
    if not family and (not raw.resolved or raw.definition.code != resolved.definition.code):
        raise ValueError('Materiaal en kwaliteit spreken elkaar tegen')
    return resolved.definition.code


def is_plate(part):
    profile = str(part.normalized_profile or part.profile).upper().strip()
    return str(part.part_type).casefold() in {'plate', 'strip'} or bool(re.match(r'^(?:PL|PLAAT|STRIP|FL|BL)\s*\d', profile))


def demand_from_part(part: Any, catalog: MaterialDatabase | None = None) -> tuple[PlateNestDemand, str]:
    if not is_plate(part):
        raise ValueError('Geen canoniek plaatdeel')
    catalog = catalog or MaterialDatabase()
    blockers = part_material_blockers(part, catalog)
    if blockers:
        raise ValueError('; '.join(blockers))
    grade = _grade(part.material, part.material_grade, catalog)
    quantity = _integer(part.quantity_total, 'Aantal')
    if not quantity:
        raise ValueError('Een plaatdeel moet ten minste één gevraagd exemplaar hebben')
    data = dict(part.geometry_descriptor or {})
    explicit = data.get('plate_geometry') or data
    thickness = explicit.get('thickness_mm')
    dimensions = explicit.get('bbox_mm', explicit.get('bbox'))
    profile_numbers = re.findall(r'\d+(?:[.,]\d+)?', str(part.normalized_profile or part.profile))
    profile_t = float(profile_numbers[0].replace(',', '.')) if profile_numbers else None
    if thickness is None and isinstance(dimensions, (list, tuple)) and len(dimensions) == 3:
        thickness = dimensions[2]
        if profile_t is not None and not isclose(float(thickness), profile_t, rel_tol=0, abs_tol=1e-6):
            raise ValueError('Lokale plaatdikte/boundingbox en profiel spreken elkaar tegen')
    if thickness is None:
        thickness = profile_t
    thickness = _number(thickness, 'Plaatdikte')
    outer, holes = explicit.get('outer_contour'), explicit.get('inner_contours', ())
    basis = 'exacte expliciete vlakke contour'
    if outer is None:
        # A conservative rectangular envelope is usable for stock planning only.
        # It never claims to reconstruct missing holes/curves or production cuts.
        length = _number(part.length_mm, 'Lengte')
        width = explicit.get('width_mm')
        if isinstance(dimensions, (list, tuple)) and len(dimensions) == 3:
            if not isclose(float(dimensions[0]), length, rel_tol=0, abs_tol=1e-6):
                raise ValueError('Boundingbox is niet aantoonbaar het lokale plaatassenstelsel')
            width = dimensions[1]
        if width is None and len(profile_numbers) >= 2:
            width = float(profile_numbers[1].replace(',', '.'))
        width = _number(width, 'Bewezen plaatbreedte')
        outer = ((0, 0), (length, 0), (length, width), (0, width))
        holes = ()
        basis = 'conservatieve rechthoekige omhulling; geen snijcontourvrijgave'
    geometry = PlateGeometryRef(str(part.internal_id), tuple(outer), tuple(holes))
    identity = _digest({'part': _part_payload(part)})  # recomputed, never trust stale model hashes
    return PlateNestDemand(str(part.internal_id), str(part.internal_id), geometry, grade, grade,
                           thickness, quantity, tuple(explicit.get('allowed_rotations_deg', (0, 90))),
                           False, explicit.get('grain_direction_deg'), identity), basis


@dataclass(frozen=True)
class PlateProjectInput:
    project_id: str
    scope: str
    entity_ids: tuple[str, ...]
    demands: tuple[PlateNestDemand, ...]
    stock: tuple[PlateStock, ...]
    boundaries: tuple[PlateStockBoundary, ...]
    sources: tuple[dict, ...]
    exclusions: tuple[dict, ...]
    geometry_basis: tuple[dict, ...]
    project_binding: str
    include_remnants: bool = True

    @property
    def blockers(self):
        return tuple(r for r in self.exclusions if r['blocking'])

    @property
    def requested_count(self):
        return sum(d.quantity for d in self.demands)


def _part_payload(part):
    payload = asdict(part)
    properties = payload.get('properties', {})
    migrated = properties.get('_cws_unified_schema_2_25', {})
    # Canonical deserialization adds this empty default. Only that exact,
    # content-free default is neutral; real face evidence stays hash-bound.
    if migrated.get('m18_manufacturing') == {'manufacturing_faces': [], 'manufacturing_faces_state': {}}:
        migrated.pop('m18_manufacturing')
        if not migrated:
            properties.pop('_cws_unified_schema_2_25', None)
    return payload


def project_binding(project, ids):
    return _digest({'project_id': project.project_id,
                    'parts': {i: _part_payload(project.parts[i]) if i in project.parts else None for i in sorted(ids)},
                    'sources': {i: asdict(s) for i, s in project.sources.items()},
                    'stock': {i: asdict(s) for i, s in project.stock_items.items()},
                    'remnants': {i: asdict(s) for i, s in project.remnants.items()}})


def collect_project_input(project, *, scope='project', entity_ids: Iterable[str] = (), include_remnants: bool = True) -> PlateProjectInput:
    if scope not in {'project', 'selection'}:
        raise ValueError('Scope moet project of selectie zijn')
    ids = tuple(sorted(project.parts if scope == 'project' else set(entity_ids)))
    demands, stock, boundaries, sources, exclusions, basis = [], [], [], [], [], []
    catalog = MaterialDatabase()
    with _LOCK:
        for identifier in ids:
            part = project.parts.get(identifier)
            if part is None:
                exclusions.append({'id': identifier, 'reason': 'Selectie bevat geen bestaand onderdeel', 'blocking': True})
                continue
            if not is_plate(part):
                exclusions.append({'id': identifier, 'reason': 'Geen plaatdeel; niet in plaatvraag', 'blocking': False})
                continue
            try:
                demand, note = demand_from_part(part, catalog)
                demands.append(demand); basis.append({'id': identifier, 'basis': note})
            except (ValueError, TypeError, KeyError) as exc:
                exclusions.append({'id': identifier, 'reason': str(exc), 'blocking': True})
        for identifier, item in sorted(project.stock_items.items()):
            if not item.plate_size_mm:
                continue
            try:
                if len(item.plate_size_mm) != 3:
                    raise ValueError('Voorraadplaat vereist [breedte, hoogte, dikte] in mm')
                count = _integer(item.available_quantity, 'Voorraad') - _integer(item.reserved_quantity, 'Gereserveerd')
                if count < 0:
                    raise ValueError('Voorraad is overgereserveerd')
                if count == 0 or item.status not in {'available', 'reserved'}:
                    continue
                grade = _grade(item.material, item.grade, catalog)
                stock.append(PlateStock(identifier, *item.plate_size_mm[:2], grade, grade, item.plate_size_mm[2], count, item.properties.get('plate_grain_direction_deg')))
                sources.append({'id': identifier, 'type': 'full_stock', 'revision': item.reservation_revision})
            except (ValueError, TypeError) as exc:
                exclusions.append({'id': identifier, 'reason': 'Voorraad: ' + str(exc), 'blocking': True})
        for identifier, item in sorted(project.remnants.items()) if include_remnants else ():
            if identifier in project.stock_items:
                exclusions.append({'id': identifier, 'reason': 'Dubbele voorraad-/reststuk-ID', 'blocking': True})
                continue
            if not item.remaining_contour or item.status != 'available' or item.reservation_ids:
                continue
            try:
                contour = item.remaining_contour
                geometry = PlateGeometryRef(identifier, tuple(contour['outer_contour']), tuple(contour.get('inner_contours', ())))
                grade = _grade(item.material, item.grade, catalog)
                stock.append(PlateStock(identifier, geometry.width_mm, geometry.height_mm, grade, grade,
                                        _number(contour['thickness_mm'], 'Reststukdikte'), 1, contour.get('grain_direction_deg')))
                boundaries.append(PlateStockBoundary(identifier, geometry))
                sources.append({'id': identifier, 'type': 'remnant', 'revision': item.reservation_revision})
            except (ValueError, TypeError, KeyError) as exc:
                exclusions.append({'id': identifier, 'reason': 'Reststuk: ' + str(exc), 'blocking': True})
        return PlateProjectInput(project.project_id, scope, ids, tuple(demands), tuple(stock), tuple(boundaries),
                                 tuple(sources), tuple(exclusions), tuple(basis), project_binding(project, ids), bool(include_remnants))


def plan_project_input(inputs: PlateProjectInput, *, kerf_mm=3.0, edge_margin_mm=10.0, run_id=None, check_cancelled=None):
    if inputs.blockers:
        raise ValueError('Plaatvraag/voorraad onvolledig: ' + '; '.join(r['id'] + ': ' + r['reason'] for r in inputs.blockers))
    if not inputs.demands:
        raise ValueError('Geen geldige plaatvraag in deze scope')
    return solve_canonical_plate_nesting(inputs.demands, inputs.stock, kerf_mm=kerf_mm, edge_margin_mm=edge_margin_mm,
                                         run_id=run_id or str(uuid4()), stock_boundaries=inputs.boundaries,
                                         check_cancelled=check_cancelled)


def _record_digest(record):
    return _digest({k: v for k, v in record.items() if k != 'record_sha256'})


def accept_project_plan(project, inputs: PlateProjectInput, plan: PlateCutPlan, *, user='plate-operator'):
    """Reserve and persist only a current complete plan, all-or-nothing.

    Shared reservation lock/service prevents BOM/profile/plate double booking.
    No stock, quantity, grade, or release property is fabricated.
    """
    with _LOCK:
        if inputs.project_id != project.project_id or project_binding(project, inputs.entity_ids) != inputs.project_binding:
            raise ValueError('Project, onderdeel of voorraad gewijzigd; opnieuw optimaliseren')
        report = validate_canonical_plate_nesting(plan, inputs.demands, inputs.stock, stock_boundaries=inputs.boundaries)
        if inputs.blockers or not report.passed:
            raise ValueError('Plan niet reserveerbaar: ' + ', '.join(report.blocking_codes))
        runs = project.settings.get('plate_nesting_runs', {})
        if plan.run_id in runs:
            raise ValueError('Run-ID bestaat al; geen dubbele reservering')
        source_map = {s['id']: s for s in inputs.sources}
        quantities = Counter(layout.stock_id for layout in plan.layouts)
        requests = [ReservationRequest(source_map[key]['type'], key, count, source_map[key]['revision']) for key, count in sorted(quantities.items())]
        names = ('settings', 'stock_items', 'remnants', 'profile_nesting_reservations',
                 'profile_nesting_reservation_revision', 'audit_log', 'modified_at')
        backup = {key: deepcopy(getattr(project, key)) for key in names}
        try:
            reservation = reserve_physical_stock(project, requests, run_id=plan.run_id, user=user)
            record = {'schema': 'cws-project-plate-run-2', 'project_id': project.project_id,
                      'plan': plan.to_dict(), 'validation': asdict(report), 'inputs': asdict(inputs),
                      'reservation_id': reservation.reservation_id, 'status': 'reserved_planning',
                      'machine_release_allowed': False,
                      'accepted_binding': project_binding(project, inputs.entity_ids)}
            record['record_sha256'] = _record_digest(record)
            project.settings.setdefault('plate_nesting_runs', {})[plan.run_id] = record
            project.audit('plate_nesting.plan_reserved', user=user, entity_id=plan.run_id,
                          after_hash=plan.plan_sha256, details={'quantity': inputs.requested_count, 'part_ids': list(inputs.entity_ids), 'reservation_id': reservation.reservation_id})
            return deepcopy(record)
        except Exception:
            for key, value in backup.items():
                setattr(project, key, value)
            raise


def verify_saved_plan(project, record):
    if record.get('schema') != 'cws-project-plate-run-2' or record.get('record_sha256') != _record_digest(record):
        raise ValueError('Oud of beschadigd plan; opnieuw plannen')
    if record['project_id'] != project.project_id or record.get('status') != 'reserved_planning':
        raise ValueError('Plan is niet actief in dit project')
    if project_binding(project, record['inputs']['entity_ids']) != record['accepted_binding']:
        raise ValueError('Opgeslagen plan is verouderd door gewijzigde onderdelen/voorraad')
    reservation = project.profile_nesting_reservations.get(record['reservation_id'], {})
    if reservation.get('status') != 'reserved' or reservation.get('run_id') != record['plan']['run_id']:
        raise ValueError('Voorraadreservering ontbreekt of is ingetrokken')
    plan = PlateCutPlan.from_dict(record['plan'])
    raw = record['inputs']
    demands = tuple(PlateNestDemand(**{**r, 'geometry': PlateGeometryRef(**r['geometry'])}) for r in raw['demands'])
    stock = tuple(PlateStock(**s) for s in raw['stock'])
    boundaries = tuple(PlateStockBoundary(r['stock_id'], PlateGeometryRef(**r['geometry'])) for r in raw['boundaries'])
    report = validate_canonical_plate_nesting(plan, demands, stock, stock_boundaries=boundaries)
    if not report.passed:
        raise ValueError('Opgeslagen plan ongeldig: ' + ', '.join(report.blocking_codes))
    return plan


def cancel_project_plan(project, run_id, *, user='plate-operator'):
    with _LOCK:
        record = project.settings.get('plate_nesting_runs', {}).get(run_id)
        if not record or record.get('record_sha256') != _record_digest(record):
            raise ValueError('Onbekend of beschadigd nestplan')
        if record.get('machine_release_allowed') or record.get('status') != 'reserved_planning':
            raise ValueError('Alleen een niet-vrijgegeven planningsreservering kan worden ingetrokken')
        release_reservation(project, record['reservation_id'], user=user)
        record['status'] = 'cancelled'
        record['record_sha256'] = _record_digest(record)
        project.audit('plate_nesting.plan_cancelled', user=user, entity_id=run_id)
