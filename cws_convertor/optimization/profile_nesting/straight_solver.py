"""Pure-Python straight-cut solvers for profile nesting phase 3.

This module deliberately supports *square/straight* cuts only. Miter envelopes,
sequence-dependent transitions and common-cut proof belong to phase 4. The
module contains a deterministic greedy fallback and an exact exhaustive-enumeration
backend with symmetry/state pruning for small sets. Every produced plan must still pass validator.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import math
import time
from typing import Any, Iterable

from .objective import (
    default_objective_configuration,
    evaluate_objective,
    objective_key,
    validate_objective_configuration,
)
from .results import (
    MaterialBalance,
    NestingPlan,
    PiecePlacement,
    SolverEvidence,
    SolverResultStatus,
    StockBarPlan,
)
from .units import LengthKernel

SOLVER_VERSION = "cws-straight-cut-v1"


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
    kerf_units: int
    head_trim_units: int
    tail_trim_units: int
    safety_length_units: int
    minimum_end_remnant_units: int
    max_part_length_units: int
    max_stock_length_units: int
    min_part_length_units: int
    tolerance_units: int
    setup_cost_micros: int
    handling_cost_micros: int
    forbidden_clamp_zones: tuple[tuple[int, int], ...]
    feed_direction: str
    raw: dict[str, Any]


@dataclass
class _WorkBar:
    candidate: _Candidate
    machine: _Machine
    pieces: list[_Piece] = field(default_factory=list)
    cursor_units: int = 0

    @property
    def usable_end_units(self) -> int:
        return self.candidate.length_units - self.machine.tail_trim_units - self.machine.safety_length_units

    @property
    def remaining_capacity_units(self) -> int:
        return self.usable_end_units - self.cursor_units


@dataclass
class _PreparedProblem:
    snapshot_hash: str
    pieces: list[_Piece]
    candidates: list[_Candidate]
    machines: list[_Machine]
    objective_configuration: dict[str, Any]
    kernel: LengthKernel
    issues: list[dict[str, Any]] = field(default_factory=list)


def _micros(value: Any) -> int:
    amount = Decimal(str(value or 0))
    if not amount.is_finite() or amount < 0:
        raise ValueError("Kosten moeten eindige niet-negatieve waarden zijn")
    return int((amount * Decimal(1_000_000)).to_integral_value(rounding=ROUND_HALF_UP))


def _kernel_from_snapshot(snapshot) -> LengthKernel:
    units = dict(getattr(snapshot, "units", {}) or {})
    return LengthKernel(units_per_mm=int(units.get("units_per_mm") or 1000))


def _line_is_straight_exact(line: dict[str, Any], tolerance_deg: float = 1e-9) -> bool:
    for name in ("start_cut", "end_cut"):
        cut = dict(line.get(name) or {})
        if str(cut.get("status") or "") != "exact":
            return False
        try:
            primary = float(cut.get("primary_angle_deg") or 0)
            secondary = float(cut.get("secondary_angle_deg") or 0)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(primary) or not math.isfinite(secondary):
            return False
        if abs(primary) > tolerance_deg or abs(secondary) > tolerance_deg:
            return False
    return True


def _prepare_problem(snapshot, *, scenario_family: str = "waste", objective_configuration: dict[str, Any] | None = None) -> _PreparedProblem:
    kernel = _kernel_from_snapshot(snapshot)
    objective = validate_objective_configuration(
        objective_configuration or dict(getattr(snapshot, "objective_configuration", {}) or {}) or default_objective_configuration(scenario_family),
        family=scenario_family,
    )
    line_by_id = {str(item.get("demand_line_id") or ""): dict(item) for item in list(snapshot.demand_lines or [])}
    issues: list[dict[str, Any]] = []
    pieces: list[_Piece] = []
    raw_instances = list(getattr(snapshot, "piece_instances", []) or [])
    if not raw_instances:
        issues.append({"code": "CWS-NEST-019", "message": "Inputsnapshot bevat geen stabiele piece instances."})
    for raw in raw_instances:
        item = dict(raw or {})
        line_id = str(item.get("demand_line_id") or "")
        line = line_by_id.get(line_id)
        if not line:
            issues.append({"code": "CWS-NEST-019", "message": f"Piece instance verwijst naar onbekende demand line {line_id!r}."})
            continue
        if str(line.get("eligibility_status") or "") != "eligible":
            issues.append({"code": "CWS-NEST-008", "message": f"Demand line {line_id} is niet production-eligible."})
            continue
        if not _line_is_straight_exact(line):
            issues.append({"code": "CWS-NEST-026", "message": f"Demand line {line_id} valt buiten de rechte-cut scope van fase 3."})
            continue
        length_units = int(line.get("nominal_length_units") or 0)
        if length_units <= 0:
            issues.append({"code": "CWS-NEST-001", "message": f"Demand line {line_id} heeft geen geldige solverlengte."})
            continue
        pieces.append(_Piece(
            instance_id=str(item.get("instance_id") or ""),
            demand_line_id=line_id,
            part_id=str(item.get("part_id") or line.get("part_id") or ""),
            manufacturing_hash=str(item.get("manufacturing_hash") or line.get("manufacturing_hash") or ""),
            part_position=str(item.get("part_position") or line.get("part_position") or ""),
            length_units=length_units,
            priority=int(item.get("priority") or line.get("priority") or 0),
            due_date=str(item.get("due_date") or line.get("due_date") or ""),
            line=line,
        ))
    pieces.sort(key=lambda p: (-p.length_units, -p.priority, p.due_date or "9999", p.instance_id))

    candidates: list[_Candidate] = []
    stock_snapshot = dict(getattr(snapshot, "stock_snapshot", {}) or {})
    for raw in sorted(list(stock_snapshot.get("candidates") or []), key=lambda r: str((r or {}).get("candidate_id") or "")):
        item = dict(raw or {})
        length_units = int(item.get("length_units") or 0)
        if length_units <= 0:
            continue
        quantity = item.get("available_quantity")
        if quantity is not None:
            quantity = max(0, int(quantity))
            if quantity <= 0:
                continue
        candidates.append(_Candidate(
            candidate_id=str(item.get("candidate_id") or ""),
            source_type=str(item.get("source_type") or ""),
            source_id=str(item.get("source_id") or ""),
            length_units=length_units,
            available_quantity=quantity,
            profile_id=str(item.get("profile_id") or ""),
            section_hash=str(item.get("section_hash") or ""),
            material=str(item.get("material") or ""),
            material_grade=str(item.get("material_grade") or ""),
            heat=str(item.get("heat") or ""),
            certificate=str(item.get("certificate") or ""),
            unit_price_micros=_micros(item.get("unit_price", 0)),
            extra_cost_micros=_micros(item.get("extra_cost", 0)),
            minimum_reusable_units=kernel.mm_to_units(item.get("minimum_reusable_mm", 0) or 0),
            raw=item,
        ))
    if not candidates:
        issues.append({"code": "CWS-NEST-011", "message": "Inputsnapshot bevat geen bruikbare stock candidates."})

    machines: list[_Machine] = []
    machine_snapshot = dict(getattr(snapshot, "machine_snapshot", {}) or {})
    for raw in sorted(list(machine_snapshot.get("profiles") or []), key=lambda r: (str((r or {}).get("machine_id") or ""), str((r or {}).get("profile_id") or ""))):
        item = dict(raw or {})
        if not bool(item.get("enabled", True)) or str(item.get("validation_status") or "") not in {"validated", "released"}:
            continue
        zones: list[tuple[int, int]] = []
        for zone in list(item.get("forbidden_clamp_zones") or []):
            try:
                start = kernel.mm_to_units((zone or {}).get("start_mm", 0))
                end = kernel.mm_to_units((zone or {}).get("end_mm", 0))
            except Exception:
                continue
            if end > start:
                zones.append((start, end))
        machines.append(_Machine(
            profile_id=str(item.get("profile_id") or ""),
            machine_id=str(item.get("machine_id") or ""),
            kerf_units=kernel.mm_to_units(item.get("kerf_mm", 0) or 0),
            head_trim_units=kernel.mm_to_units(item.get("head_trim_mm", 0) or 0),
            tail_trim_units=kernel.mm_to_units(item.get("tail_trim_mm", 0) or 0),
            safety_length_units=kernel.mm_to_units(item.get("safety_length_mm", 0) or 0),
            minimum_end_remnant_units=kernel.mm_to_units(item.get("minimum_end_remnant_mm", 0) or 0),
            max_part_length_units=kernel.mm_to_units(item.get("max_part_length_mm", 0) or 0),
            max_stock_length_units=kernel.mm_to_units(item.get("max_stock_length_mm", 0) or 0),
            min_part_length_units=kernel.mm_to_units(item.get("min_part_length_mm", 0) or 0),
            tolerance_units=kernel.mm_to_units(item.get("machine_tolerance_mm", 0) or 0),
            setup_cost_micros=_micros(item.get("setup_cost", 0)),
            handling_cost_micros=_micros(item.get("handling_cost", 0)),
            forbidden_clamp_zones=tuple(zones),
            feed_direction=str(item.get("feed_direction") or "left_to_right"),
            raw=item,
        ))
    if not machines:
        issues.append({"code": "CWS-NEST-008", "message": "Inputsnapshot bevat geen gevalideerd machineprofiel."})
    if list(getattr(snapshot, "user_locks", []) or []):
        issues.append({"code": "CWS-NEST-027", "message": "Fase 3 verwerkt nog geen handmatige locks/pinned placements; solverstart is veilig geblokkeerd."})
    return _PreparedProblem(
        snapshot_hash=str(snapshot.snapshot_hash), pieces=pieces, candidates=candidates,
        machines=machines, objective_configuration=objective, kernel=kernel, issues=issues,
    )


def _base_compatible(piece: _Piece, candidate: _Candidate, machine: _Machine, *, machine_id_filter: str = "", profile_id_filter: str = "") -> bool:
    line = piece.line
    if machine_id_filter and machine.machine_id != machine_id_filter:
        return False
    if machine.feed_direction not in {"left_to_right", "bidirectional"}:
        return False
    if profile_id_filter and machine.profile_id != profile_id_filter:
        return False
    candidate_machine_ids = {str(v) for v in list(line.get("candidate_machine_ids") or [])}
    if candidate_machine_ids and machine.machine_id not in candidate_machine_ids:
        return False
    section = str(line.get("section_hash") or "")
    profile = str(line.get("profile_id") or "")
    if candidate.section_hash and section and candidate.section_hash != section:
        return False
    if (not candidate.section_hash or not section) and candidate.profile_id and profile and candidate.profile_id != profile:
        return False
    if candidate.material != str(line.get("material") or ""):
        return False
    if candidate.material_grade != str(line.get("material_grade") or ""):
        return False
    heat = str(line.get("heat_requirement") or "")
    cert = str(line.get("certificate_requirement") or "")
    if heat and candidate.heat != heat:
        return False
    if cert and candidate.certificate != cert:
        return False
    if machine.max_part_length_units and piece.length_units > machine.max_part_length_units + machine.tolerance_units:
        return False
    if machine.min_part_length_units and piece.length_units + machine.tolerance_units < machine.min_part_length_units:
        return False
    if machine.max_stock_length_units and candidate.length_units > machine.max_stock_length_units + machine.tolerance_units:
        return False
    minimum = machine.head_trim_units + piece.length_units + machine.kerf_units + machine.tail_trim_units + machine.safety_length_units
    return candidate.length_units + machine.tolerance_units >= minimum


def _cut_conflicts_with_clamp(machine: _Machine, cut_start: int, cut_end: int) -> bool:
    for start, end in machine.forbidden_clamp_zones:
        if cut_end == cut_start:
            if start <= cut_start < end:
                return True
        elif max(start, cut_start) < min(end, cut_end):
            return True
    return False


def _can_append(bar: _WorkBar, piece: _Piece) -> bool:
    if not _base_compatible(piece, bar.candidate, bar.machine):
        return False
    start = bar.cursor_units
    end = start + piece.length_units
    cut_end = end + bar.machine.kerf_units
    if cut_end > bar.usable_end_units + bar.machine.tolerance_units:
        return False
    if _cut_conflicts_with_clamp(bar.machine, end, cut_end):
        return False
    return True


def _new_bar(candidate: _Candidate, machine: _Machine) -> _WorkBar:
    return _WorkBar(candidate=candidate, machine=machine, cursor_units=machine.head_trim_units)


def _append(bar: _WorkBar, piece: _Piece) -> tuple[int, int]:
    old_cursor = bar.cursor_units
    old_count = len(bar.pieces)
    end = bar.cursor_units + piece.length_units
    bar.cursor_units = end + bar.machine.kerf_units
    bar.pieces.append(piece)
    return old_cursor, old_count


def _restore(bar: _WorkBar, state: tuple[int, int]) -> None:
    cursor, count = state
    del bar.pieces[count:]
    bar.cursor_units = cursor


def _source_rank(source_type: str, family: str) -> int:
    family = str(family or "").lower()
    if family == "remnants_first":
        return {"remnant": 0, "full_stock": 1, "purchase_option": 2}.get(source_type, 3)
    if family == "stock_first":
        return {"full_stock": 0, "remnant": 1, "purchase_option": 2}.get(source_type, 3)
    return {"remnant": 0, "full_stock": 1, "purchase_option": 2}.get(source_type, 3)


def _candidate_machine_options(problem: _PreparedProblem, piece: _Piece, *, machine_id: str = "", machine_profile_id: str = "") -> list[tuple[_Candidate, _Machine]]:
    options: list[tuple[_Candidate, _Machine]] = []
    family = str(problem.objective_configuration.get("family") or "waste")
    for candidate in problem.candidates:
        for machine in problem.machines:
            if _base_compatible(piece, candidate, machine, machine_id_filter=machine_id, profile_id_filter=machine_profile_id):
                bar = _new_bar(candidate, machine)
                if _can_append(bar, piece):
                    options.append((candidate, machine))
    def key(item: tuple[_Candidate, _Machine]):
        candidate, machine = item
        cost = candidate.unit_price_micros + candidate.extra_cost_micros + machine.setup_cost_micros + machine.handling_cost_micros
        if family in {"cost", "minimal_cost"}:
            return (cost, candidate.length_units, _source_rank(candidate.source_type, family), candidate.candidate_id, machine.machine_id, machine.profile_id)
        if family in {"stock_first", "remnants_first"}:
            return (_source_rank(candidate.source_type, family), candidate.length_units, cost, candidate.candidate_id, machine.machine_id, machine.profile_id)
        return (candidate.length_units, _source_rank(candidate.source_type, family), cost, candidate.candidate_id, machine.machine_id, machine.profile_id)
    options.sort(key=key)
    return options


def _materialize_plan(problem: _PreparedProblem, bars: Iterable[_WorkBar], *, status: str) -> NestingPlan:
    result_bars: list[StockBarPlan] = []
    gross = net = kerf = head = tail = reusable = waste = 0
    purchase_count = physical_count = full_stock_count = remnant_count = 0
    total_cost = 0
    for index, work in enumerate(bars, start=1):
        if not work.pieces:
            continue
        machine = work.machine
        candidate = work.candidate
        bar_id = f"bar-{index:05d}"
        cursor = machine.head_trim_units
        placements: list[PiecePlacement] = []
        for seq, piece in enumerate(work.pieces, start=1):
            start = cursor
            end = start + piece.length_units
            placements.append(PiecePlacement(
                instance_id=piece.instance_id,
                demand_line_id=piece.demand_line_id,
                part_id=piece.part_id,
                manufacturing_hash=piece.manufacturing_hash,
                part_position=piece.part_position,
                stock_bar_id=bar_id,
                sequence_index=seq,
                start_units=start,
                end_units=end,
                cut_position_units=end,
                length_units=piece.length_units,
                kerf_units=machine.kerf_units,
                machine_id=machine.machine_id,
                machine_profile_id=machine.profile_id,
            ))
            cursor = end + machine.kerf_units
        raw_residual = candidate.length_units - machine.tail_trim_units - cursor
        threshold = max(candidate.minimum_reusable_units, machine.minimum_end_remnant_units)
        reusable_units = raw_residual if raw_residual > 0 and raw_residual >= threshold else 0
        waste_units = raw_residual if raw_residual > 0 and reusable_units == 0 else 0
        source_cost = candidate.unit_price_micros + candidate.extra_cost_micros
        machine_cost = machine.setup_cost_micros + machine.handling_cost_micros
        bar = StockBarPlan(
            bar_id=bar_id, candidate_id=candidate.candidate_id, source_type=candidate.source_type,
            source_id=candidate.source_id, stock_length_units=candidate.length_units,
            machine_id=machine.machine_id, machine_profile_id=machine.profile_id,
            head_trim_units=machine.head_trim_units, tail_trim_units=machine.tail_trim_units,
            safety_length_units=machine.safety_length_units, kerf_units=machine.kerf_units,
            minimum_reusable_units=threshold, placements=placements, raw_residual_units=raw_residual,
            reusable_remnant_units=reusable_units, waste_units=waste_units,
            source_cost_micros=source_cost, machine_cost_micros=machine_cost,
            total_cost_micros=source_cost + machine_cost,
        )
        bar.refresh_hash(); result_bars.append(bar)
        gross += candidate.length_units
        net += sum(p.length_units for p in placements)
        kerf += len(placements) * machine.kerf_units
        head += machine.head_trim_units
        tail += machine.tail_trim_units
        reusable += reusable_units
        waste += waste_units
        total_cost += bar.total_cost_micros
        if candidate.source_type == "purchase_option": purchase_count += 1
        else: physical_count += 1
        if candidate.source_type == "full_stock": full_stock_count += 1
        if candidate.source_type == "remnant": remnant_count += 1
    balance = MaterialBalance(
        gross_stock_units=gross, net_part_units=net, kerf_units=kerf,
        head_trim_units=head, tail_trim_units=tail,
        reusable_remnant_units=reusable, waste_units=waste,
    )
    balance.balance_delta_units = gross - (net + kerf + head + tail + reusable + waste)
    metrics = {
        "material_loss_units": balance.material_loss_units,
        "waste_units": waste,
        "reusable_remnant_units": reusable,
        "gross_stock_units": gross,
        "net_part_units": net,
        "bar_count": len(result_bars),
        "purchase_bar_count": purchase_count,
        "physical_bar_count": physical_count,
        "full_stock_bar_count": full_stock_count,
        "remnant_bar_count": remnant_count,
        "setup_count": len(result_bars),
        "cost_micros": total_cost,
    }
    objective = evaluate_objective(metrics, problem.objective_configuration)
    plan = NestingPlan(
        input_snapshot_hash=problem.snapshot_hash, status=status, bars=result_bars,
        material_balance=balance, objective=objective,
    )
    plan.refresh_hash()
    return plan


def _plan_tie_signature(plan: NestingPlan) -> tuple[Any, ...]:
    return tuple(
        (bar.candidate_id, bar.machine_profile_id, tuple(p.instance_id for p in bar.placements))
        for bar in plan.bars
    )


def _is_better(plan: NestingPlan, incumbent: NestingPlan | None, objective_config: dict[str, Any]) -> bool:
    if incumbent is None:
        return True
    left = objective_key(plan.objective.raw_metrics if plan.objective else {}, objective_config)
    right = objective_key(incumbent.objective.raw_metrics if incumbent.objective else {}, objective_config)
    return (left, _plan_tie_signature(plan)) < (right, _plan_tie_signature(incumbent))


def _primary_metric(plan: NestingPlan | None, objective_config: dict[str, Any]) -> tuple[str, int | None]:
    metric = str(objective_config["components"][0]["metric"])
    if plan is None or plan.objective is None:
        return metric, None
    value = int(plan.objective.raw_metrics.get(metric, 0))
    direction = str(objective_config["components"][0].get("direction") or "min")
    return metric, value if direction == "min" else -value


def _lower_bound_primary(problem: _PreparedProblem, *, metric: str) -> int | None:
    if not problem.pieces:
        return 0
    if metric == "bar_count":
        capacities = []
        for c in problem.candidates:
            for m in problem.machines:
                cap = c.length_units - m.head_trim_units - m.tail_trim_units - m.safety_length_units
                if cap > 0:
                    capacities.append(cap)
        if not capacities:
            return None
        total = sum(p.length_units for p in problem.pieces)
        return (total + max(capacities) - 1) // max(capacities)
    if metric in {"material_loss_units", "waste_units", "purchase_bar_count", "cost_micros"}:
        return 0
    if metric == "gross_stock_units":
        return sum(p.length_units for p in problem.pieces)
    return None


def solve_greedy(snapshot, *, scenario_family: str = "waste", objective_configuration: dict[str, Any] | None = None, solver_configuration: dict[str, Any] | None = None, random_seed: int = 0) -> tuple[NestingPlan | None, SolverEvidence]:
    started = time.monotonic()
    problem = _prepare_problem(snapshot, scenario_family=scenario_family, objective_configuration=objective_configuration)
    config = dict(solver_configuration or {})
    machine_id = str(config.get("machine_id") or "")
    machine_profile_id = str(config.get("machine_profile_id") or "")
    evidence = SolverEvidence(
        input_snapshot_hash=problem.snapshot_hash, backend="deterministic_greedy_bfd",
        backend_version=SOLVER_VERSION, status=SolverResultStatus.UNKNOWN.value,
        deterministic_seed=int(random_seed), exact_scope=False,
        exact_scope_reason="Greedy baseline geeft een geldige bovenlimiet maar geen optimaliteitsbewijs.",
        objective_components=list(problem.objective_configuration["components"]),
        simplifications=["straight_square_cuts_only", "one_kerf_per_piece", "no_common_cut", "reported_gap_applies_to_primary_objective_component"],
    )
    if problem.issues:
        evidence.status = SolverResultStatus.INFEASIBLE_DETECTED.value
        evidence.runtime_seconds = time.monotonic() - started
        evidence.simplifications.extend(f"precheck:{item['code']}" for item in problem.issues)
        evidence.refresh_hash(); return None, evidence
    bars: list[_WorkBar] = []
    usage: dict[str, int] = {}
    for piece in problem.pieces:
        existing_options: list[tuple[int, int, str, str, int]] = []
        for index, bar in enumerate(bars):
            if _can_append(bar, piece):
                projected = bar.remaining_capacity_units - piece.length_units - bar.machine.kerf_units
                existing_options.append((projected, index, bar.candidate.candidate_id, bar.machine.profile_id, len(bar.pieces)))
        if existing_options:
            existing_options.sort()
            bar = bars[existing_options[0][1]]
            _append(bar, piece)
            continue
        selected = None
        for candidate, machine in _candidate_machine_options(problem, piece, machine_id=machine_id, machine_profile_id=machine_profile_id):
            used = usage.get(candidate.candidate_id, 0)
            if candidate.available_quantity is not None and used >= candidate.available_quantity:
                continue
            selected = (candidate, machine)
            break
        if selected is None:
            evidence.status = SolverResultStatus.INFEASIBLE_DETECTED.value
            evidence.runtime_seconds = time.monotonic() - started
            evidence.simplifications.append(f"unassigned:{piece.instance_id}")
            evidence.refresh_hash(); return None, evidence
        candidate, machine = selected
        bar = _new_bar(candidate, machine)
        if not _can_append(bar, piece):
            evidence.status = SolverResultStatus.FAILED.value
            evidence.runtime_seconds = time.monotonic() - started
            evidence.refresh_hash(); return None, evidence
        _append(bar, piece)
        bars.append(bar)
        usage[candidate.candidate_id] = usage.get(candidate.candidate_id, 0) + 1
    plan = _materialize_plan(problem, bars, status=SolverResultStatus.FEASIBLE.value)
    metric, upper = _primary_metric(plan, problem.objective_configuration)
    lower = _lower_bound_primary(problem, metric=metric)
    evidence.status = SolverResultStatus.FEASIBLE.value
    evidence.lower_bound = lower
    evidence.upper_bound = upper
    evidence.gap_metric = metric
    if lower is not None and upper is not None and upper >= lower:
        evidence.absolute_gap = upper - lower
        evidence.relative_gap = 0.0 if upper == 0 else float(Decimal(upper - lower) / Decimal(abs(upper)))
    evidence.plan_hash = plan.plan_hash
    evidence.best_solution_seconds = time.monotonic() - started
    evidence.runtime_seconds = evidence.best_solution_seconds
    evidence.refresh_hash()
    return plan, evidence


def _state_key(index: int, bars: list[_WorkBar], usage: dict[str, int]) -> tuple[Any, ...]:
    bar_state = tuple(sorted(
        (b.candidate.candidate_id, b.machine.profile_id, b.cursor_units, len(b.pieces))
        for b in bars
    ))
    usage_state = tuple(sorted((k, v) for k, v in usage.items() if v))
    return (index, bar_state, usage_state)


def solve_exact_small(snapshot, *, scenario_family: str = "waste", objective_configuration: dict[str, Any] | None = None, solver_configuration: dict[str, Any] | None = None, random_seed: int = 0, timeout_seconds: float = 0.0) -> tuple[NestingPlan | None, SolverEvidence]:
    started = time.monotonic()
    problem = _prepare_problem(snapshot, scenario_family=scenario_family, objective_configuration=objective_configuration)
    config = dict(solver_configuration or {})
    max_pieces = int(config.get("exact_max_pieces") or 14)
    node_limit = int(config.get("node_limit") or 250_000)
    machine_id = str(config.get("machine_id") or "")
    machine_profile_id = str(config.get("machine_profile_id") or "")
    effective_timeout = float(timeout_seconds or config.get("timeout_seconds") or 0.0)
    evidence = SolverEvidence(
        input_snapshot_hash=problem.snapshot_hash, backend="exact_enumeration",
        backend_version=SOLVER_VERSION, status=SolverResultStatus.UNKNOWN.value,
        deterministic_seed=int(random_seed), exact_scope=True,
        exact_scope_reason=f"Pure-Python volledige enumeratie met symmetriepruning; limiet {max_pieces} pieces.",
        objective_components=list(problem.objective_configuration["components"]),
        simplifications=["straight_square_cuts_only", "one_kerf_per_piece", "no_common_cut", "reported_gap_applies_to_primary_objective_component"],
    )
    if problem.issues:
        evidence.status = SolverResultStatus.INFEASIBLE_DETECTED.value
        evidence.exact_scope = False
        evidence.exact_scope_reason = "Deterministische voorcontrole faalde voordat de exacte zoekruimte bestond."
        evidence.simplifications.extend(f"precheck:{item['code']}" for item in problem.issues)
        evidence.runtime_seconds = time.monotonic() - started
        evidence.refresh_hash(); return None, evidence
    if any(machine.forbidden_clamp_zones for machine in problem.machines):
        evidence.status = SolverResultStatus.UNKNOWN.value
        evidence.exact_scope = False
        evidence.exact_scope_reason = (
            "Verboden axiale klemzones maken de volgorde relevant; fase-3 exact search "
            "enumerereert nog geen alle sequence-permutaties en claimt daarom geen optimum."
        )
        evidence.simplifications.append("sequence_dependent_clamp_zones_require_controlled_fallback")
        evidence.runtime_seconds = time.monotonic() - started
        evidence.refresh_hash(); return None, evidence
    if len(problem.pieces) > max_pieces:
        evidence.status = SolverResultStatus.UNKNOWN.value
        evidence.exact_scope = False
        evidence.exact_scope_reason = f"{len(problem.pieces)} pieces overschrijden exact_max_pieces={max_pieces}."
        evidence.runtime_seconds = time.monotonic() - started
        evidence.refresh_hash(); return None, evidence

    # Greedy gives a deterministic incumbent/upper bound before exact search.
    incumbent, _ = solve_greedy(
        snapshot, scenario_family=scenario_family,
        objective_configuration=problem.objective_configuration,
        solver_configuration=config, random_seed=random_seed,
    )
    incumbent_time = time.monotonic() - started if incumbent is not None else None
    bars: list[_WorkBar] = []
    usage: dict[str, int] = {}
    visited: set[tuple[Any, ...]] = set()
    stopped = False
    stop_reason = ""

    def limits_hit() -> bool:
        nonlocal stopped, stop_reason
        if node_limit > 0 and evidence.nodes_explored >= node_limit:
            stopped = True; stop_reason = "node_limit"; return True
        if effective_timeout > 0 and time.monotonic() - started >= effective_timeout:
            stopped = True; stop_reason = "timeout"; return True
        return False

    def recurse(index: int) -> None:
        nonlocal incumbent, incumbent_time
        if stopped or limits_hit():
            return
        evidence.nodes_explored += 1
        key = _state_key(index, bars, usage)
        if key in visited:
            evidence.states_pruned += 1
            return
        visited.add(key)
        if index >= len(problem.pieces):
            plan = _materialize_plan(problem, bars, status=SolverResultStatus.FEASIBLE.value)
            if _is_better(plan, incumbent, problem.objective_configuration):
                incumbent = plan
                incumbent_time = time.monotonic() - started
                evidence.incumbent_updates += 1
            return
        piece = problem.pieces[index]
        # Existing bars first: stable best-fit order improves incumbent quickly.
        existing: list[tuple[int, int]] = []
        seen_bar_signatures: set[tuple[Any, ...]] = set()
        for bar_index, bar in enumerate(bars):
            if not _can_append(bar, piece):
                continue
            sig = (bar.candidate.candidate_id, bar.machine.profile_id, bar.cursor_units)
            if sig in seen_bar_signatures:
                evidence.states_pruned += 1
                continue
            seen_bar_signatures.add(sig)
            residual = bar.remaining_capacity_units - piece.length_units - bar.machine.kerf_units
            existing.append((residual, bar_index))
        existing.sort()
        for _, bar_index in existing:
            state = _append(bars[bar_index], piece)
            recurse(index + 1)
            _restore(bars[bar_index], state)
            if stopped:
                return
        # Open a new bar for every distinct candidate/machine option whose
        # quantity is still available. Identical option signatures are pruned.
        seen_new: set[tuple[Any, ...]] = set()
        for candidate, machine in _candidate_machine_options(problem, piece, machine_id=machine_id, machine_profile_id=machine_profile_id):
            used = usage.get(candidate.candidate_id, 0)
            if candidate.available_quantity is not None and used >= candidate.available_quantity:
                continue
            sig = (
                candidate.source_type, candidate.length_units, candidate.profile_id,
                candidate.section_hash, candidate.material, candidate.material_grade,
                candidate.heat, candidate.certificate,
                candidate.unit_price_micros, candidate.extra_cost_micros,
                machine.profile_id,
            )
            # For purchase options with identical economics/capability, one
            # representative suffices. Physical source IDs are intentionally
            # kept distinct so limited stock remains traceable.
            symmetry_key = sig if candidate.source_type == "purchase_option" else (candidate.candidate_id, machine.profile_id)
            if symmetry_key in seen_new:
                evidence.states_pruned += 1
                continue
            seen_new.add(symmetry_key)
            bar = _new_bar(candidate, machine)
            if not _can_append(bar, piece):
                continue
            _append(bar, piece)
            bars.append(bar)
            usage[candidate.candidate_id] = used + 1
            recurse(index + 1)
            usage[candidate.candidate_id] = used
            if not used:
                usage.pop(candidate.candidate_id, None)
            bars.pop()
            if stopped:
                return

    recurse(0)
    runtime = time.monotonic() - started
    evidence.runtime_seconds = runtime
    evidence.best_solution_seconds = incumbent_time
    evidence.limit_reached = stop_reason
    metric, upper = _primary_metric(incumbent, problem.objective_configuration)
    evidence.gap_metric = metric
    evidence.upper_bound = upper
    lower = _lower_bound_primary(problem, metric=metric)
    if stopped:
        evidence.status = SolverResultStatus.TIMEOUT_FEASIBLE.value if incumbent is not None else SolverResultStatus.UNKNOWN.value
        evidence.lower_bound = lower
        if lower is not None and upper is not None and upper >= lower:
            evidence.absolute_gap = upper - lower
            evidence.relative_gap = 0.0 if upper == 0 else float(Decimal(upper - lower) / Decimal(abs(upper)))
        if incumbent is not None:
            incumbent.status = SolverResultStatus.TIMEOUT_FEASIBLE.value
            incumbent.refresh_hash()
            evidence.plan_hash = incumbent.plan_hash
        evidence.refresh_hash(); return incumbent, evidence
    if incumbent is None:
        evidence.status = SolverResultStatus.INFEASIBLE_PROVEN.value
        evidence.lower_bound = None
        evidence.upper_bound = None
        evidence.relative_gap = None
        evidence.refresh_hash(); return None, evidence
    # Complete search proves the incumbent optimal for the configured exact
    # scope. The proven bound equals the incumbent on the primary component.
    incumbent.status = SolverResultStatus.OPTIMAL.value
    incumbent.refresh_hash()
    metric, upper = _primary_metric(incumbent, problem.objective_configuration)
    evidence.status = SolverResultStatus.OPTIMAL.value
    evidence.lower_bound = upper
    evidence.upper_bound = upper
    evidence.absolute_gap = 0
    evidence.relative_gap = 0.0
    evidence.gap_metric = metric
    evidence.plan_hash = incumbent.plan_hash
    evidence.refresh_hash()
    return incumbent, evidence


def solve_straight_cut(snapshot, *, backend: str = "auto", scenario_family: str = "waste", objective_configuration: dict[str, Any] | None = None, solver_configuration: dict[str, Any] | None = None, random_seed: int = 0, timeout_seconds: float = 0.0) -> tuple[NestingPlan | None, SolverEvidence]:
    """Solve a phase-3 straight-cut snapshot without trusting the result.

    ``auto`` uses the exact backend only within its explicitly configured small
    scope and otherwise falls back to deterministic greedy. Independent
    validation is intentionally not performed in this module.
    """
    requested = str(backend or "auto").strip().lower()
    if requested not in {"auto", "greedy", "exact"}:
        raise ValueError("backend moet auto, greedy of exact zijn")
    config = dict(solver_configuration or {})
    if requested == "greedy":
        return solve_greedy(snapshot, scenario_family=scenario_family, objective_configuration=objective_configuration, solver_configuration=config, random_seed=random_seed)
    if requested == "exact":
        return solve_exact_small(snapshot, scenario_family=scenario_family, objective_configuration=objective_configuration, solver_configuration=config, random_seed=random_seed, timeout_seconds=timeout_seconds)
    max_pieces = int(config.get("exact_max_pieces") or 14)
    piece_count = len(list(getattr(snapshot, "piece_instances", []) or []))
    if piece_count <= max_pieces:
        plan, evidence = solve_exact_small(snapshot, scenario_family=scenario_family, objective_configuration=objective_configuration, solver_configuration=config, random_seed=random_seed, timeout_seconds=timeout_seconds)
        if evidence.status != SolverResultStatus.UNKNOWN.value or plan is not None:
            return plan, evidence
    plan, evidence = solve_greedy(snapshot, scenario_family=scenario_family, objective_configuration=objective_configuration, solver_configuration=config, random_seed=random_seed)
    evidence.backend = "deterministic_greedy_medium_fallback"
    evidence.exact_scope = False
    evidence.exact_scope_reason = f"Auto fallback: piece_count={piece_count}, exact_max_pieces={max_pieces}."
    evidence.simplifications.append("medium_large_controlled_greedy_fallback")
    evidence.refresh_hash()
    return plan, evidence
