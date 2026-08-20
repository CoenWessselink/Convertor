"""Sequence-dependent angle-aware profile nesting for phase 4.

The solver does not approximate miter cuts as nominal lengths.  Every placement
uses analytic/geometry-backed cut envelopes, angle-projected kerf and an exact
transition record.  ``solve_angle_exact_small`` enumerates piece order,
orientation and bar assignment inside a deliberately small scope.  Only a
completed search may report ``optimal``; larger jobs use a deterministic greedy
fallback and remain merely feasible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import math
import time
from typing import Any, Callable

from .angle_geometry import (
    AngleGeometryError,
    OrientationGeometry,
    build_orientation_variants,
    build_transition,
    cut_interval_units,
    cut_support_level,
    final_cut_consumption_units,
    start_cut_consumption_units,
    projected_kerf_mm,
)
from .objective import default_objective_configuration, evaluate_objective, objective_key, validate_objective_configuration
from .results import MaterialBalance, NestingPlan, PiecePlacement, SolverEvidence, SolverResultStatus, StockBarPlan
from .units import LengthKernel

ANGLE_SOLVER_VERSION = "cws-angle-sequence-v1"


@dataclass(frozen=True)
class _Piece:
    instance_id: str
    demand_line_id: str
    part_id: str
    manufacturing_hash: str
    part_position: str
    length_units: int
    priority: int
    due_date: str
    line: dict[str, Any]


@dataclass(frozen=True)
class _Candidate:
    candidate_id: str
    source_type: str
    source_id: str
    length_units: int
    available_quantity: int | None
    profile_id: str
    section_hash: str
    material: str
    material_grade: str
    heat: str
    certificate: str
    unit_price_micros: int
    extra_cost_micros: int
    minimum_reusable_units: int
    raw: dict[str, Any]


@dataclass(frozen=True)
class _Machine:
    profile_id: str
    machine_id: str
    raw: dict[str, Any]
    kerf_units: int
    head_trim_units: int
    tail_trim_units: int
    safety_length_units: int
    minimum_end_remnant_units: int
    max_part_length_units: int
    min_part_length_units: int
    max_stock_length_units: int
    tolerance_units: int
    setup_cost_micros: int
    handling_cost_micros: int
    forbidden_clamp_zones: tuple[tuple[int, int], ...]


@dataclass
class _Placed:
    piece: _Piece
    orientation: OrientationGeometry
    reference_start_units: int
    reference_end_units: int
    physical_min_units: int
    physical_max_units: int
    transition_before: Any | None = None


@dataclass
class _WorkBar:
    candidate: _Candidate
    machine: _Machine
    placed: list[_Placed] = field(default_factory=list)
    consumed_end_units: int = 0
    projected_kerf_units: int = 0
    transition_extra_loss_units: int = 0
    bar_id_hint: str = ""

    @property
    def usable_end_units(self) -> int:
        return self.candidate.length_units - self.machine.tail_trim_units - self.machine.safety_length_units


@dataclass
class _Problem:
    snapshot_hash: str
    pieces: list[_Piece]
    candidates: list[_Candidate]
    machines: list[_Machine]
    objective_configuration: dict[str, Any]
    kernel: LengthKernel
    issues: list[dict[str, Any]] = field(default_factory=list)
    variant_cache: dict[tuple[str, str], list[OrientationGeometry]] = field(default_factory=dict)


def _micros(value: Any) -> int:
    amount = Decimal(str(value or 0))
    if not amount.is_finite() or amount < 0:
        raise ValueError("Kosten moeten eindige niet-negatieve waarden zijn")
    return int((amount * Decimal(1_000_000)).to_integral_value(rounding=ROUND_HALF_UP))


def _kernel(snapshot) -> LengthKernel:
    units = dict(getattr(snapshot, "units", {}) or {})
    return LengthKernel(units_per_mm=int(units.get("units_per_mm") or 1000))


def _prepare(snapshot, *, scenario_family: str, objective_configuration: dict[str, Any] | None = None) -> _Problem:
    kernel = _kernel(snapshot)
    objective = validate_objective_configuration(
        objective_configuration or dict(getattr(snapshot, "objective_configuration", {}) or {}) or default_objective_configuration(scenario_family),
        family=scenario_family,
    )
    issues: list[dict[str, Any]] = []
    lines = {str(x.get("demand_line_id") or ""): dict(x) for x in list(getattr(snapshot, "demand_lines", []) or [])}
    pieces: list[_Piece] = []
    for raw in list(getattr(snapshot, "piece_instances", []) or []):
        item = dict(raw or {})
        line_id = str(item.get("demand_line_id") or "")
        line = lines.get(line_id)
        if not line:
            issues.append({"code": "CWS-NEST-019", "message": f"Piece instance verwijst naar onbekende demand line {line_id!r}."})
            continue
        if str(line.get("eligibility_status") or "") != "eligible":
            issues.append({"code": "CWS-NEST-008", "message": f"Demand line {line_id} is niet production-eligible."})
            continue
        length = int(line.get("nominal_length_units") or 0)
        if length <= 0:
            issues.append({"code": "CWS-NEST-001", "message": f"Demand line {line_id} heeft geen geldige lengte."})
            continue
        if str(dict(line.get("start_cut") or {}).get("status") or "") != "exact" or str(dict(line.get("end_cut") or {}).get("status") or "") != "exact":
            issues.append({"code": "CWS-NEST-006", "message": f"Demand line {line_id} heeft geen exact start-/eindzaagvlak."})
            continue
        pieces.append(_Piece(
            instance_id=str(item.get("instance_id") or ""), demand_line_id=line_id,
            part_id=str(item.get("part_id") or line.get("part_id") or ""),
            manufacturing_hash=str(item.get("manufacturing_hash") or line.get("manufacturing_hash") or ""),
            part_position=str(item.get("part_position") or line.get("part_position") or ""),
            length_units=length, priority=int(item.get("priority") or line.get("priority") or 0),
            due_date=str(item.get("due_date") or line.get("due_date") or ""), line=line,
        ))
    pieces.sort(key=lambda p: (-p.length_units, -p.priority, p.due_date or "9999", p.instance_id))
    if not pieces:
        issues.append({"code": "CWS-NEST-019", "message": "Inputsnapshot bevat geen bruikbare piece instances."})

    candidates: list[_Candidate] = []
    stock = dict(getattr(snapshot, "stock_snapshot", {}) or {})
    for raw in sorted(list(stock.get("candidates") or []), key=lambda x: str((x or {}).get("candidate_id") or "")):
        item = dict(raw or {})
        length = int(item.get("length_units") or 0)
        if length <= 0:
            continue
        quantity = item.get("available_quantity")
        quantity = None if quantity is None else max(0, int(quantity))
        if quantity == 0:
            continue
        candidates.append(_Candidate(
            candidate_id=str(item.get("candidate_id") or ""), source_type=str(item.get("source_type") or ""),
            source_id=str(item.get("source_id") or ""), length_units=length, available_quantity=quantity,
            profile_id=str(item.get("profile_id") or ""), section_hash=str(item.get("section_hash") or ""),
            material=str(item.get("material") or ""), material_grade=str(item.get("material_grade") or ""),
            heat=str(item.get("heat") or ""), certificate=str(item.get("certificate") or ""),
            unit_price_micros=_micros(item.get("unit_price", 0)), extra_cost_micros=_micros(item.get("extra_cost", 0)),
            minimum_reusable_units=kernel.mm_to_units(item.get("minimum_reusable_mm", 0) or 0), raw=item,
        ))
    if not candidates:
        issues.append({"code": "CWS-NEST-011", "message": "Geen bruikbare stock candidates."})

    machines: list[_Machine] = []
    machine_snapshot = dict(getattr(snapshot, "machine_snapshot", {}) or {})
    for raw in sorted(list(machine_snapshot.get("profiles") or []), key=lambda x: (str((x or {}).get("machine_id") or ""), str((x or {}).get("profile_id") or ""))):
        item = dict(raw or {})
        if not bool(item.get("enabled", True)) or str(item.get("validation_status") or "") not in {"validated", "released"}:
            continue
        if str(item.get("feed_direction") or "left_to_right") not in {"left_to_right", "bidirectional"}:
            # Right-to-left requires a separately validated stock-coordinate model.
            continue
        zones = []
        for z in list(item.get("forbidden_clamp_zones") or []):
            try:
                a = kernel.mm_to_units((z or {}).get("start_mm", 0)); b = kernel.mm_to_units((z or {}).get("end_mm", 0))
            except Exception:
                continue
            if b > a:
                zones.append((a, b))
        machines.append(_Machine(
            profile_id=str(item.get("profile_id") or ""), machine_id=str(item.get("machine_id") or ""), raw=item,
            kerf_units=kernel.mm_to_units(item.get("kerf_mm", 0) or 0), head_trim_units=kernel.mm_to_units(item.get("head_trim_mm", 0) or 0),
            tail_trim_units=kernel.mm_to_units(item.get("tail_trim_mm", 0) or 0), safety_length_units=kernel.mm_to_units(item.get("safety_length_mm", 0) or 0),
            minimum_end_remnant_units=kernel.mm_to_units(item.get("minimum_end_remnant_mm", 0) or 0),
            max_part_length_units=kernel.mm_to_units(item.get("max_part_length_mm", 0) or 0), min_part_length_units=kernel.mm_to_units(item.get("min_part_length_mm", 0) or 0),
            max_stock_length_units=kernel.mm_to_units(item.get("max_stock_length_mm", 0) or 0), tolerance_units=kernel.mm_to_units(item.get("machine_tolerance_mm", 0) or 0),
            setup_cost_micros=_micros(item.get("setup_cost", 0)), handling_cost_micros=_micros(item.get("handling_cost", 0)),
            forbidden_clamp_zones=tuple(zones),
        ))
    if not machines:
        issues.append({"code": "CWS-NEST-008", "message": "Geen gevalideerd angle-aware machineprofiel beschikbaar."})
    if list(getattr(snapshot, "user_locks", []) or []):
        issues.append({"code": "CWS-NEST-027", "message": "Fase 4 verwerkt nog geen handmatige locks; dit volgt in fase 6."})
    return _Problem(str(snapshot.snapshot_hash), pieces, candidates, machines, objective, kernel, issues)


def _base_compatible(piece: _Piece, candidate: _Candidate, machine: _Machine, *, machine_id: str = "", machine_profile_id: str = "") -> bool:
    line = piece.line
    if machine_id and machine.machine_id != machine_id:
        return False
    if machine_profile_id and machine.profile_id != machine_profile_id:
        return False
    mids = {str(v) for v in list(line.get("candidate_machine_ids") or [])}
    if mids and machine.machine_id not in mids:
        return False
    section = str(line.get("section_hash") or ""); profile = str(line.get("profile_id") or "")
    if candidate.section_hash and section and candidate.section_hash != section:
        return False
    if (not candidate.section_hash or not section) and candidate.profile_id and profile and candidate.profile_id != profile:
        return False
    if candidate.material != str(line.get("material") or "") or candidate.material_grade != str(line.get("material_grade") or ""):
        return False
    if str(line.get("heat_requirement") or "") and candidate.heat != str(line.get("heat_requirement") or ""):
        return False
    if str(line.get("certificate_requirement") or "") and candidate.certificate != str(line.get("certificate_requirement") or ""):
        return False
    if machine.max_part_length_units and piece.length_units > machine.max_part_length_units + machine.tolerance_units:
        return False
    if machine.min_part_length_units and piece.length_units + machine.tolerance_units < machine.min_part_length_units:
        return False
    if machine.max_stock_length_units and candidate.length_units > machine.max_stock_length_units + machine.tolerance_units:
        return False
    return True


def _angle_within_machine(orientation: OrientationGeometry, machine: _Machine) -> bool:
    raw = machine.raw
    lo = float(raw.get("min_saw_angle_deg", -90.0)); hi = float(raw.get("max_saw_angle_deg", 90.0))
    tol = float(raw.get("angle_tolerance_deg", 0.01) or 0.01)
    for cut in (orientation.variant.start_cut, orientation.variant.end_cut):
        p = float(cut.primary_angle_deg); s = float(cut.secondary_angle_deg)
        if p < lo - tol or p > hi + tol:
            return False
        if abs(s) > tol and str(raw.get("compound_cut_policy") or "blocked") != "supported":
            return False
    return True


def _variants(problem: _Problem, piece: _Piece, machine: _Machine) -> list[OrientationGeometry]:
    key = (piece.demand_line_id, machine.profile_id)
    if key in problem.variant_cache:
        return problem.variant_cache[key]
    try:
        variants = build_orientation_variants(piece.line, machine.raw, kernel=problem.kernel, require_exact=True)
    except AngleGeometryError:
        variants = []
    variants = [v for v in variants if v.variant.production_equivalence == "exact" and _angle_within_machine(v, machine)]
    problem.variant_cache[key] = variants
    return variants


def _candidate_machine_options(problem: _Problem, piece: _Piece, *, machine_id: str = "", machine_profile_id: str = "") -> list[tuple[_Candidate, _Machine, OrientationGeometry]]:
    family = str(problem.objective_configuration.get("family") or "waste")
    options: list[tuple[_Candidate, _Machine, OrientationGeometry]] = []
    for candidate in problem.candidates:
        for machine in problem.machines:
            if not _base_compatible(piece, candidate, machine, machine_id=machine_id, machine_profile_id=machine_profile_id):
                continue
            for orientation in _variants(problem, piece, machine):
                probe = _WorkBar(candidate, machine)
                if _append_choice(problem, probe, piece, orientation, mutate=False) is not None:
                    options.append((candidate, machine, orientation))
    def source_rank(source: str) -> int:
        if family == "stock_first": return {"full_stock": 0, "remnant": 1, "purchase_option": 2}.get(source, 3)
        if family == "remnants_first": return {"remnant": 0, "full_stock": 1, "purchase_option": 2}.get(source, 3)
        return {"remnant": 0, "full_stock": 1, "purchase_option": 2}.get(source, 3)
    def key(item):
        c, m, o = item
        cost = c.unit_price_micros + c.extra_cost_micros + m.setup_cost_micros + m.handling_cost_micros
        if family in {"cost", "minimal_cost"}:
            return (cost, c.length_units, source_rank(c.source_type), c.candidate_id, m.profile_id, o.variant.variant_id)
        return (c.length_units, source_rank(c.source_type), cost, c.candidate_id, m.profile_id, o.variant.variant_id)
    options.sort(key=key)
    return options


def _interval_conflicts(machine: _Machine, start: int, end: int) -> bool:
    a, b = min(start, end), max(start, end)
    for z0, z1 in machine.forbidden_clamp_zones:
        if a == b:
            if z0 <= a < z1: return True
        elif max(a, z0) < min(b, z1): return True
    return False


def _start_cut_interval(placed: _Placed, machine: _Machine, problem: _Problem) -> tuple[int, int]:
    kerf, extra = start_cut_consumption_units(placed.orientation, machine.raw, problem.kernel)
    # Start-face blade/allowance loss is on the stock-head side of the nominal
    # reference surface. The interval spans the actual saw operation envelope.
    return (
        placed.reference_start_units + placed.orientation.start_envelope.min_offset_units - kerf - extra,
        placed.reference_start_units + placed.orientation.start_envelope.max_offset_units,
    )


def _copy_bar(bar: _WorkBar) -> _WorkBar:
    return _WorkBar(bar.candidate, bar.machine, list(bar.placed), bar.consumed_end_units, bar.projected_kerf_units, bar.transition_extra_loss_units, bar.bar_id_hint)


def _append_choice(problem: _Problem, bar: _WorkBar, piece: _Piece, orientation: OrientationGeometry, *, mutate: bool = True, allow_common_cut: bool = True) -> _WorkBar | None:
    if not _base_compatible(piece, bar.candidate, bar.machine):
        return None
    if orientation.variant.production_equivalence != "exact" or not _angle_within_machine(orientation, bar.machine):
        return None
    target = bar if mutate else _copy_bar(bar)
    transition = None
    if not target.placed:
        start_kerf, start_extra = start_cut_consumption_units(orientation, target.machine.raw, problem.kernel)
        ref_start = target.machine.head_trim_units + start_kerf + start_extra - orientation.start_envelope.min_offset_units
    else:
        prev = target.placed[-1]
        try:
            transition_geometry = build_transition(
                prev.piece.line, piece.line,
                prev.piece.instance_id, prev.orientation,
                piece.instance_id, orientation,
                target.machine.raw, kernel=problem.kernel,
                allow_common_cut=bool(allow_common_cut), require_exact=True,
            )
        except AngleGeometryError:
            return None
        transition = transition_geometry.transition
        if transition.proof_status != "exact":
            return None
        ref_start = prev.reference_end_units + transition.required_reference_gap_units
        interval_start = prev.reference_end_units + prev.orientation.end_envelope.min_offset_units
        interval_end = ref_start + orientation.start_envelope.max_offset_units
        if _interval_conflicts(target.machine, interval_start, interval_end):
            return None
    ref_end = ref_start + piece.length_units
    physical_min = ref_start + orientation.start_envelope.min_offset_units
    physical_max = ref_end + orientation.end_envelope.max_offset_units
    final_kerf, final_extra = final_cut_consumption_units(orientation, target.machine.raw, problem.kernel)
    consumed_end = physical_max + final_kerf + final_extra
    if consumed_end > target.usable_end_units + target.machine.tolerance_units:
        return None
    final_interval = cut_interval_units(ref_end, orientation.end_envelope, final_kerf, final_extra)
    if _interval_conflicts(target.machine, *final_interval):
        return None
    placed = _Placed(piece, orientation, ref_start, ref_end, physical_min, physical_max, transition)
    if not target.placed:
        if _interval_conflicts(target.machine, *_start_cut_interval(placed, target.machine, problem)):
            return None
        start_kerf, start_extra = start_cut_consumption_units(orientation, target.machine.raw, problem.kernel)
        target.projected_kerf_units = start_kerf + final_kerf
        target.transition_extra_loss_units = start_extra + final_extra
    else:
        old_last = target.placed[-1]
        old_final_kerf, old_final_extra = final_cut_consumption_units(old_last.orientation, target.machine.raw, problem.kernel)
        target.projected_kerf_units -= old_final_kerf
        target.transition_extra_loss_units -= old_final_extra
        target.projected_kerf_units += int(transition.kerf_projection_units) + final_kerf
        target.transition_extra_loss_units += int(transition.extra_loss_units) + final_extra
    target.placed.append(placed)
    target.consumed_end_units = consumed_end
    return target


def _bar_signature(bar: _WorkBar) -> tuple[Any, ...]:
    return (
        bar.candidate.candidate_id, bar.machine.profile_id,
        tuple((p.piece.demand_line_id, p.orientation.variant.variant_id) for p in bar.placed),
        bar.consumed_end_units,
    )


def _work_to_plan(problem: _Problem, bars: list[_WorkBar], *, status: str) -> NestingPlan:
    result_bars: list[StockBarPlan] = []
    gross = net = kerf = head = tail = reusable = waste = transition_effect = 0
    purchase_count = physical_count = full_stock_count = remnant_count = total_cost = 0
    sorted_bars = sorted((b for b in bars if b.placed), key=_bar_signature)
    for index, work in enumerate(sorted_bars, start=1):
        bar_id = str(work.bar_id_hint or f"bar-{index:05d}")
        placements: list[PiecePlacement] = []
        transitions = [p.transition_before for p in work.placed if p.transition_before is not None]
        transition_by_right = {t.right_instance_id: t for t in transitions}
        transition_by_left = {t.left_instance_id: t for t in transitions}
        for seq, placed in enumerate(work.placed, start=1):
            final_kerf, _final_extra = final_cut_consumption_units(placed.orientation, work.machine.raw, problem.kernel)
            is_last = seq == len(work.placed)
            after = transition_by_left.get(placed.piece.instance_id)
            placement_kerf = int(after.kerf_projection_units) if after is not None else final_kerf
            placements.append(PiecePlacement(
                instance_id=placed.piece.instance_id, demand_line_id=placed.piece.demand_line_id,
                part_id=placed.piece.part_id, manufacturing_hash=placed.piece.manufacturing_hash,
                part_position=placed.piece.part_position, stock_bar_id=bar_id, sequence_index=seq,
                start_units=placed.reference_start_units, end_units=placed.reference_end_units,
                cut_position_units=placed.reference_end_units, length_units=placed.piece.length_units,
                kerf_units=placement_kerf, machine_id=work.machine.machine_id,
                machine_profile_id=work.machine.profile_id, orientation_id=placed.orientation.variant.variant_id,
                orientation_hash=placed.orientation.variant.variant_hash,
                reference_start_units=placed.reference_start_units, reference_end_units=placed.reference_end_units,
                physical_min_units=placed.physical_min_units, physical_max_units=placed.physical_max_units,
                start_envelope_min_units=placed.orientation.start_envelope.min_offset_units,
                start_envelope_max_units=placed.orientation.start_envelope.max_offset_units,
                end_envelope_min_units=placed.orientation.end_envelope.min_offset_units,
                end_envelope_max_units=placed.orientation.end_envelope.max_offset_units,
                start_cut_hash=placed.orientation.variant.start_cut.requirement_hash,
                end_cut_hash=placed.orientation.variant.end_cut.requirement_hash,
                transition_before_id=str(getattr(transition_by_right.get(placed.piece.instance_id), "transition_id", "")),
                transition_after_id=str(getattr(after, "transition_id", "")),
                final_cut_kerf_units=final_kerf if is_last else 0,
            ))
        raw_residual = work.candidate.length_units - work.machine.tail_trim_units - work.consumed_end_units
        if raw_residual < -work.machine.tolerance_units:
            raise RuntimeError("Interne angle plan materialisatie overschrijdt stock")
        raw_residual = max(0, raw_residual)
        threshold = max(work.candidate.minimum_reusable_units, work.machine.minimum_end_remnant_units)
        reusable_units = raw_residual if raw_residual > 0 and raw_residual >= threshold else 0
        waste_units = raw_residual if raw_residual > 0 and reusable_units == 0 else 0
        nominal_sum = sum(p.piece.length_units for p in work.placed)
        geom_transition = work.consumed_end_units - work.machine.head_trim_units - nominal_sum - work.projected_kerf_units
        source_cost = work.candidate.unit_price_micros + work.candidate.extra_cost_micros
        machine_cost = work.machine.setup_cost_micros + work.machine.handling_cost_micros
        common_count = sum(1 for t in transitions if t.common_cut)
        cut_count = 2 + sum(int(t.cut_count) for t in transitions)  # start + transitions + final
        bar = StockBarPlan(
            bar_id=bar_id, candidate_id=work.candidate.candidate_id, source_type=work.candidate.source_type,
            source_id=work.candidate.source_id, stock_length_units=work.candidate.length_units,
            machine_id=work.machine.machine_id, machine_profile_id=work.machine.profile_id,
            head_trim_units=work.machine.head_trim_units, tail_trim_units=work.machine.tail_trim_units,
            safety_length_units=work.machine.safety_length_units, kerf_units=work.machine.kerf_units,
            minimum_reusable_units=threshold, placements=placements, transitions=transitions,
            occupied_span_units=work.consumed_end_units - work.machine.head_trim_units,
            nominal_sum_units=nominal_sum, transition_effect_units=geom_transition,
            projected_kerf_units=work.projected_kerf_units, cut_count=cut_count, common_cut_count=common_count,
            raw_residual_units=raw_residual, reusable_remnant_units=reusable_units, waste_units=waste_units,
            source_cost_micros=source_cost, machine_cost_micros=machine_cost, total_cost_micros=source_cost + machine_cost,
        )
        bar.refresh_hash(); result_bars.append(bar)
        gross += work.candidate.length_units; net += nominal_sum; kerf += work.projected_kerf_units
        head += work.machine.head_trim_units; tail += work.machine.tail_trim_units
        reusable += reusable_units; waste += waste_units; transition_effect += geom_transition
        total_cost += bar.total_cost_micros
        if work.candidate.source_type == "purchase_option": purchase_count += 1
        else: physical_count += 1
        if work.candidate.source_type == "full_stock": full_stock_count += 1
        if work.candidate.source_type == "remnant": remnant_count += 1
    balance = MaterialBalance(
        gross_stock_units=gross, net_part_units=net, kerf_units=kerf,
        head_trim_units=head, tail_trim_units=tail, reusable_remnant_units=reusable,
        waste_units=waste, transition_effect_units=transition_effect,
    )
    balance.balance_delta_units = gross - (net + kerf + head + tail + reusable + waste + transition_effect)
    metrics = {
        "material_loss_units": balance.material_loss_units, "waste_units": waste,
        "reusable_remnant_units": reusable, "gross_stock_units": gross, "net_part_units": net,
        "bar_count": len(result_bars), "purchase_bar_count": purchase_count,
        "physical_bar_count": physical_count, "full_stock_bar_count": full_stock_count,
        "remnant_bar_count": remnant_count, "setup_count": len(result_bars), "cost_micros": total_cost,
    }
    plan = NestingPlan(
        input_snapshot_hash=problem.snapshot_hash, status=status, bars=result_bars,
        material_balance=balance, objective=evaluate_objective(metrics, problem.objective_configuration),
    )
    plan.refresh_hash(); return plan


def _plan_signature(plan: NestingPlan) -> tuple[Any, ...]:
    return tuple((b.candidate_id, b.machine_profile_id, tuple((p.instance_id, p.orientation_id) for p in b.placements)) for b in plan.bars)


def _better(plan: NestingPlan, incumbent: NestingPlan | None, config: dict[str, Any]) -> bool:
    if incumbent is None: return True
    return (objective_key(plan.objective.raw_metrics, config), _plan_signature(plan)) < (objective_key(incumbent.objective.raw_metrics, config), _plan_signature(incumbent))


def _primary(plan: NestingPlan | None, config: dict[str, Any]) -> tuple[str, int | None]:
    metric = str(config["components"][0]["metric"])
    if plan is None: return metric, None
    value = int(plan.objective.raw_metrics.get(metric, 0))
    return metric, value if str(config["components"][0].get("direction") or "min") == "min" else -value


def _evidence(problem: _Problem, backend: str, seed: int, *, exact: bool, reason: str) -> SolverEvidence:
    return SolverEvidence(
        input_snapshot_hash=problem.snapshot_hash, backend=backend, backend_version=ANGLE_SOLVER_VERSION,
        status=SolverResultStatus.UNKNOWN.value, deterministic_seed=int(seed), exact_scope=exact,
        exact_scope_reason=reason, objective_components=list(problem.objective_configuration["components"]),
        simplifications=["analytic_or_geometry_backed_cut_envelopes_only", "no_approximate_custom_section_as_exact", "no_manual_locks_phase4"],
    )


def solve_angle_greedy(snapshot, *, scenario_family: str = "waste", objective_configuration: dict[str, Any] | None = None, solver_configuration: dict[str, Any] | None = None, random_seed: int = 0, cancel_check: Callable[[], bool] | None = None, progress_callback: Callable[[dict[str, Any]], None] | None = None) -> tuple[NestingPlan | None, SolverEvidence]:
    started = time.monotonic(); config = dict(solver_configuration or {})
    problem = _prepare(snapshot, scenario_family=scenario_family, objective_configuration=objective_configuration)
    ev = _evidence(problem, "deterministic_angle_greedy", random_seed, exact=False, reason="Sequence-aware greedy baseline zonder optimaliteitsbewijs.")
    if problem.issues:
        ev.status = SolverResultStatus.INFEASIBLE_DETECTED.value; ev.simplifications.extend(f"precheck:{x['code']}" for x in problem.issues); ev.runtime_seconds=time.monotonic()-started; ev.refresh_hash(); return None, ev
    bars: list[_WorkBar] = []; usage: dict[str, int] = {}
    machine_id = str(config.get("machine_id") or ""); machine_profile_id = str(config.get("machine_profile_id") or "")
    total_pieces = max(1, len(problem.pieces))
    for piece_index, piece in enumerate(problem.pieces, start=1):
        if cancel_check is not None and bool(cancel_check()):
            ev.status=SolverResultStatus.CANCELLED.value; ev.limit_reached="cancelled"; ev.runtime_seconds=time.monotonic()-started; ev.refresh_hash(); return None, ev
        if progress_callback is not None:
            progress_callback({"phase":"greedy", "pieces_done":piece_index-1, "pieces_total":total_pieces, "elapsed_seconds":time.monotonic()-started, "nodes_explored":0, "status":"solving"})
        existing = []
        for i, bar in enumerate(bars):
            for orient in _variants(problem, piece, bar.machine):
                probe = _append_choice(problem, bar, piece, orient, mutate=False)
                if probe is not None:
                    residual = bar.candidate.length_units - bar.machine.tail_trim_units - probe.consumed_end_units
                    existing.append((residual, i, orient.variant.variant_id, probe))
        if existing:
            existing.sort(key=lambda x: (x[0], x[1], x[2])); bars[existing[0][1]] = existing[0][3]; continue
        options = _candidate_machine_options(problem, piece, machine_id=machine_id, machine_profile_id=machine_profile_id)
        selected = None
        for candidate, machine, orient in options:
            used = usage.get(candidate.candidate_id, 0)
            if candidate.available_quantity is not None and used >= candidate.available_quantity: continue
            bar = _append_choice(problem, _WorkBar(candidate, machine), piece, orient, mutate=False)
            if bar is not None:
                selected = (candidate, bar); break
        if selected is None:
            ev.status=SolverResultStatus.INFEASIBLE_DETECTED.value; ev.simplifications.append(f"unassigned:{piece.instance_id}"); ev.runtime_seconds=time.monotonic()-started; ev.refresh_hash(); return None, ev
        candidate, bar = selected; bars.append(bar); usage[candidate.candidate_id]=usage.get(candidate.candidate_id,0)+1
    if progress_callback is not None:
        progress_callback({"phase":"greedy", "pieces_done":total_pieces, "pieces_total":total_pieces, "elapsed_seconds":time.monotonic()-started, "nodes_explored":0, "status":"materializing"})
    plan = _work_to_plan(problem, bars, status=SolverResultStatus.FEASIBLE.value)
    metric, upper = _primary(plan, problem.objective_configuration)
    ev.status=SolverResultStatus.FEASIBLE.value; ev.upper_bound=upper; ev.gap_metric=metric; ev.plan_hash=plan.plan_hash; ev.best_solution_seconds=time.monotonic()-started; ev.runtime_seconds=ev.best_solution_seconds; ev.refresh_hash()
    return plan, ev


def _state_key(remaining: tuple[int, ...], bars: list[_WorkBar], pieces: list[_Piece]) -> tuple[Any, ...]:
    counts: dict[str, int] = {}
    for i in remaining: counts[pieces[i].demand_line_id] = counts.get(pieces[i].demand_line_id,0)+1
    return (tuple(sorted(counts.items())), tuple(sorted(_bar_signature(b) for b in bars)))


def solve_angle_exact_small(snapshot, *, scenario_family: str = "waste", objective_configuration: dict[str, Any] | None = None, solver_configuration: dict[str, Any] | None = None, random_seed: int = 0, timeout_seconds: float = 0.0, cancel_check: Callable[[], bool] | None = None, progress_callback: Callable[[dict[str, Any]], None] | None = None) -> tuple[NestingPlan | None, SolverEvidence]:
    started=time.monotonic(); config=dict(solver_configuration or {})
    problem=_prepare(snapshot, scenario_family=scenario_family, objective_configuration=objective_configuration)
    max_pieces=int(config.get("angle_exact_max_pieces") or 7); node_limit=int(config.get("node_limit") or 250000); timeout=float(timeout_seconds or config.get("timeout_seconds") or 0.0)
    ev=_evidence(problem, "exact_angle_sequence_enumeration", random_seed, exact=True, reason=f"Volledige enumeratie van stukvolgorde, oriëntatie en bar assignment; limiet {max_pieces} pieces.")
    if problem.issues:
        ev.status=SolverResultStatus.INFEASIBLE_DETECTED.value; ev.exact_scope=False; ev.exact_scope_reason="Deterministische voorcontrole faalde voor de exacte zoekruimte."; ev.simplifications.extend(f"precheck:{x['code']}" for x in problem.issues); ev.runtime_seconds=time.monotonic()-started; ev.refresh_hash(); return None, ev
    if len(problem.pieces)>max_pieces:
        ev.status=SolverResultStatus.UNKNOWN.value; ev.exact_scope=False; ev.exact_scope_reason=f"{len(problem.pieces)} pieces overschrijden angle_exact_max_pieces={max_pieces}."; ev.runtime_seconds=time.monotonic()-started; ev.refresh_hash(); return None, ev
    machine_id=str(config.get("machine_id") or ""); machine_profile_id=str(config.get("machine_profile_id") or "")
    # Geometry/machine/stock precheck deliberately ignores *absolute* clamp positions.
    # A piece that cannot be the first piece on a bar may still be feasible later in
    # the sequence, so using empty-bar feasibility here would incorrectly prune the
    # exact sequence search.
    for piece in problem.pieces:
        has_theoretical_option = False
        for candidate in problem.candidates:
            for machine in problem.machines:
                if not _base_compatible(piece, candidate, machine, machine_id=machine_id, machine_profile_id=machine_profile_id):
                    continue
                for orientation in _variants(problem, piece, machine):
                    try:
                        start_span = orientation.start_envelope.max_offset_units - orientation.start_envelope.min_offset_units
                        end_span = orientation.end_envelope.max_offset_units - orientation.end_envelope.min_offset_units
                        start_kerf, start_extra = start_cut_consumption_units(orientation, machine.raw, problem.kernel)
                        final_kerf, final_extra = final_cut_consumption_units(orientation, machine.raw, problem.kernel)
                    except AngleGeometryError:
                        continue
                    conservative_need = machine.head_trim_units + piece.length_units + max(0, start_span) + max(0, end_span) + start_kerf + start_extra + final_kerf + final_extra + machine.tail_trim_units + machine.safety_length_units
                    if conservative_need <= candidate.length_units + machine.tolerance_units:
                        has_theoretical_option = True
                        break
                if has_theoretical_option: break
            if has_theoretical_option: break
        if not has_theoretical_option:
            ev.status=SolverResultStatus.INFEASIBLE_DETECTED.value; ev.exact_scope=False; ev.exact_scope_reason="Minimaal één piece mist een exact geometry-backed variant/stock/machineoptie."; ev.simplifications.append(f"precheck:CWS-NEST-026:{piece.instance_id}"); ev.runtime_seconds=time.monotonic()-started; ev.refresh_hash(); return None, ev
    incumbent,_=solve_angle_greedy(snapshot, scenario_family=scenario_family, objective_configuration=problem.objective_configuration, solver_configuration=config, random_seed=random_seed)
    incumbent_time=time.monotonic()-started if incumbent is not None else None
    bars: list[_WorkBar]=[]; usage: dict[str,int]={}; visited=set(); stopped=False; stop_reason=""

    def limit_hit():
        nonlocal stopped, stop_reason
        if cancel_check is not None and bool(cancel_check()): stopped=True; stop_reason="cancelled"; return True
        if node_limit>0 and ev.nodes_explored>=node_limit: stopped=True; stop_reason="node_limit"; return True
        if timeout>0 and time.monotonic()-started>=timeout: stopped=True; stop_reason="timeout"; return True
        return False

    def recurse(remaining: tuple[int,...]):
        nonlocal incumbent, incumbent_time
        if stopped or limit_hit(): return
        ev.nodes_explored += 1
        if progress_callback is not None and (ev.nodes_explored == 1 or ev.nodes_explored % 50 == 0):
            metric, upper = _primary(incumbent, problem.objective_configuration)
            progress_callback({"phase":"exact", "pieces_total":len(problem.pieces), "nodes_explored":ev.nodes_explored, "states_pruned":ev.states_pruned, "incumbent_updates":ev.incumbent_updates, "upper_bound":upper, "gap_metric":metric, "elapsed_seconds":time.monotonic()-started, "status":"solving"})
        key=_state_key(remaining,bars,problem.pieces)
        if key in visited: ev.states_pruned += 1; return
        visited.add(key)
        if not remaining:
            plan=_work_to_plan(problem,bars,status=SolverResultStatus.FEASIBLE.value)
            if _better(plan,incumbent,problem.objective_configuration): incumbent=plan; incumbent_time=time.monotonic()-started; ev.incumbent_updates+=1
            return
        seen_piece_lines=set()
        for pos, piece_index in enumerate(remaining):
            piece=problem.pieces[piece_index]
            # Identical instances of one demand line are permutation-symmetric.
            if piece.demand_line_id in seen_piece_lines: ev.states_pruned += 1; continue
            seen_piece_lines.add(piece.demand_line_id)
            rest=remaining[:pos]+remaining[pos+1:]
            seen_existing=set()
            for bar_index,bar in enumerate(bars):
                for orient in _variants(problem,piece,bar.machine):
                    probe=_append_choice(problem,bar,piece,orient,mutate=False)
                    if probe is None: continue
                    sig=(bar.candidate.candidate_id,bar.machine.profile_id,_bar_signature(probe))
                    if sig in seen_existing: ev.states_pruned+=1; continue
                    seen_existing.add(sig)
                    old=bars[bar_index]; bars[bar_index]=probe; recurse(rest); bars[bar_index]=old
                    if stopped:return
            seen_new=set()
            for candidate,machine,orient in _candidate_machine_options(problem,piece,machine_id=machine_id,machine_profile_id=machine_profile_id):
                used=usage.get(candidate.candidate_id,0)
                if candidate.available_quantity is not None and used>=candidate.available_quantity: continue
                symmetry=(candidate.source_type,candidate.length_units,candidate.profile_id,candidate.section_hash,candidate.material,candidate.material_grade,candidate.heat,candidate.certificate,candidate.unit_price_micros,candidate.extra_cost_micros,machine.profile_id,orient.variant.variant_id)
                newkey=symmetry if candidate.source_type=="purchase_option" else (candidate.candidate_id,machine.profile_id,orient.variant.variant_id)
                if newkey in seen_new: ev.states_pruned+=1; continue
                seen_new.add(newkey)
                newbar=_append_choice(problem,_WorkBar(candidate,machine),piece,orient,mutate=False)
                if newbar is None: continue
                bars.append(newbar); usage[candidate.candidate_id]=used+1; recurse(rest); bars.pop()
                if used: usage[candidate.candidate_id]=used
                else: usage.pop(candidate.candidate_id,None)
                if stopped:return
    recurse(tuple(range(len(problem.pieces))))
    ev.runtime_seconds=time.monotonic()-started; ev.best_solution_seconds=incumbent_time; ev.limit_reached=stop_reason
    metric,upper=_primary(incumbent,problem.objective_configuration); ev.gap_metric=metric; ev.upper_bound=upper
    if stopped:
        if stop_reason == "cancelled":
            ev.status=SolverResultStatus.CANCELLED.value; ev.plan_hash=""; ev.refresh_hash(); return None,ev
        ev.status=SolverResultStatus.TIMEOUT_FEASIBLE.value if incumbent is not None else SolverResultStatus.UNKNOWN.value
        if incumbent is not None: incumbent.status=ev.status; incumbent.refresh_hash(); ev.plan_hash=incumbent.plan_hash
        ev.refresh_hash(); return incumbent,ev
    if incumbent is None:
        ev.status=SolverResultStatus.INFEASIBLE_PROVEN.value; ev.refresh_hash(); return None,ev
    incumbent.status=SolverResultStatus.OPTIMAL.value; incumbent.refresh_hash(); metric,upper=_primary(incumbent,problem.objective_configuration)
    ev.status=SolverResultStatus.OPTIMAL.value; ev.lower_bound=upper; ev.upper_bound=upper; ev.absolute_gap=0; ev.relative_gap=0.0; ev.gap_metric=metric; ev.plan_hash=incumbent.plan_hash; ev.refresh_hash(); return incumbent,ev


def solve_angle_cut(snapshot, *, backend: str = "auto", scenario_family: str = "waste", objective_configuration: dict[str, Any] | None = None, solver_configuration: dict[str, Any] | None = None, random_seed: int = 0, timeout_seconds: float = 0.0, cancel_check: Callable[[], bool] | None = None, progress_callback: Callable[[dict[str, Any]], None] | None = None):
    requested=str(backend or "auto").strip().lower(); config=dict(solver_configuration or {})
    if requested not in {"auto","greedy","exact"}: raise ValueError("backend moet auto, greedy of exact zijn")
    if requested=="greedy": return solve_angle_greedy(snapshot,scenario_family=scenario_family,objective_configuration=objective_configuration,solver_configuration=config,random_seed=random_seed,cancel_check=cancel_check,progress_callback=progress_callback)
    if requested=="exact": return solve_angle_exact_small(snapshot,scenario_family=scenario_family,objective_configuration=objective_configuration,solver_configuration=config,random_seed=random_seed,timeout_seconds=timeout_seconds,cancel_check=cancel_check,progress_callback=progress_callback)
    max_pieces=int(config.get("angle_exact_max_pieces") or 7); count=len(list(getattr(snapshot,"piece_instances",[]) or []))
    if count<=max_pieces:
        plan,ev=solve_angle_exact_small(snapshot,scenario_family=scenario_family,objective_configuration=objective_configuration,solver_configuration=config,random_seed=random_seed,timeout_seconds=timeout_seconds,cancel_check=cancel_check,progress_callback=progress_callback)
        if ev.status!=SolverResultStatus.UNKNOWN.value or plan is not None: return plan,ev
    plan,ev=solve_angle_greedy(snapshot,scenario_family=scenario_family,objective_configuration=objective_configuration,solver_configuration=config,random_seed=random_seed,cancel_check=cancel_check,progress_callback=progress_callback)
    ev.backend="deterministic_angle_greedy_fallback"; ev.exact_scope=False; ev.exact_scope_reason=f"Auto fallback: piece_count={count}, angle_exact_max_pieces={max_pieces}."; ev.simplifications.append("controlled_angle_greedy_fallback"); ev.refresh_hash(); return plan,ev


def materialize_angle_layout(
    snapshot,
    layout: list[dict[str, Any]],
    *,
    scenario_family: str = "waste",
    objective_configuration: dict[str, Any] | None = None,
    status: str = "manual_feasible",
) -> NestingPlan:
    """Rebuild an explicit human planning layout through the exact angle kernel.

    This is deliberately not a coordinate editor.  The caller supplies only
    bar/stock choice, sequence, orientation and common-cut preference. Exact
    placements, envelopes, kerf and transitions are recalculated by the same
    deterministic geometry kernel used by the solver and must subsequently be
    accepted by the independent validator.
    """
    problem = _prepare(snapshot, scenario_family=scenario_family, objective_configuration=objective_configuration)
    blocking = [x for x in problem.issues if str(x.get("code") or "") != "CWS-NEST-027"]
    if blocking:
        raise ValueError("; ".join(str(x.get("message") or x.get("code") or "") for x in blocking))
    pieces = {p.instance_id: p for p in problem.pieces}
    candidates = {c.candidate_id: c for c in problem.candidates}
    machines = {m.profile_id: m for m in problem.machines}
    used_instances: set[str] = set()
    candidate_usage: dict[str, int] = {}
    work_bars: list[_WorkBar] = []
    used_bar_ids: set[str] = set()
    for bar_index, raw_bar in enumerate(list(layout or []), start=1):
        bar_spec = dict(raw_bar or {})
        piece_specs = [dict(x or {}) for x in list(bar_spec.get("pieces") or [])]
        if not piece_specs:
            continue
        candidate_id = str(bar_spec.get("candidate_id") or "")
        machine_profile_id = str(bar_spec.get("machine_profile_id") or "")
        bar_id = str(bar_spec.get("bar_id") or f"manual-bar-{bar_index:05d}")
        if bar_id in used_bar_ids:
            raise ValueError(f"Dubbele handmatige bar-ID {bar_id!r}")
        used_bar_ids.add(bar_id)
        candidate = candidates.get(candidate_id)
        machine = machines.get(machine_profile_id)
        if candidate is None:
            raise ValueError(f"Onbekende stockcandidate {candidate_id!r}")
        if machine is None:
            raise ValueError(f"Onbekend/geblokkeerd machineprofiel {machine_profile_id!r}")
        count = candidate_usage.get(candidate_id, 0) + 1
        if candidate.available_quantity is not None and count > candidate.available_quantity:
            raise ValueError(f"Stockcandidate {candidate_id!r} overschrijdt beschikbare hoeveelheid")
        candidate_usage[candidate_id] = count
        work = _WorkBar(candidate, machine, bar_id_hint=bar_id)
        for item in piece_specs:
            instance_id = str(item.get("instance_id") or "")
            if instance_id in used_instances:
                raise ValueError(f"Piece instance {instance_id!r} is dubbel toegewezen")
            piece = pieces.get(instance_id)
            if piece is None:
                raise ValueError(f"Onbekende piece instance {instance_id!r}")
            orientation_id = str(item.get("orientation_id") or "as_modeled")
            variants = {v.variant.variant_id: v for v in _variants(problem, piece, machine)}
            orientation = variants.get(orientation_id)
            if orientation is None:
                raise ValueError(f"Oriëntatie {orientation_id!r} is niet productie-equivalent voor {instance_id}")
            common_mode = str(item.get("common_cut_mode") or "auto").lower()
            if common_mode not in {"auto", "force", "disabled"}:
                raise ValueError(f"Ongeldige common-cutmodus {common_mode!r}")
            probe = _append_choice(problem, work, piece, orientation, mutate=False, allow_common_cut=(common_mode != "disabled"))
            if probe is None:
                raise ValueError(f"Handmatige plaatsing van {instance_id} op {bar_id} is geometrisch/machinaal ongeldig")
            if common_mode == "force" and probe.placed and probe.placed[-1].transition_before is not None and not bool(probe.placed[-1].transition_before.common_cut):
                raise ValueError(f"Geforceerde common cut voor {instance_id} kan niet exact worden bewezen")
            work = probe
            used_instances.add(instance_id)
        work_bars.append(work)
    missing = sorted(set(pieces) - used_instances)
    extra = sorted(used_instances - set(pieces))
    if missing or extra:
        raise ValueError(f"Handmatige layout is niet compleet: missing={missing}, extra={extra}")
    plan = _work_to_plan(problem, work_bars, status=status)
    plan.status = status
    plan.refresh_hash()
    return plan


__all__=["ANGLE_SOLVER_VERSION","solve_angle_greedy","solve_angle_exact_small","solve_angle_cut","materialize_angle_layout"]
