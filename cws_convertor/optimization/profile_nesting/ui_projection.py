"""Read-only view projections for the Profile Nesting desktop workspace.

Every row is derived from canonical project data or a persisted validated run.
No geometry or engineering value originates in the UI projection layer.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from .errors import NESTING_ERROR_CODES
from .units import LengthKernel


def _dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    return dict(value)


def _list(value: Any) -> list[Any]:
    return list(value or [])


def _units_per_mm(snapshot: dict[str, Any]) -> int:
    return int(dict(snapshot.get("units") or {}).get("units_per_mm") or 1000)


def _mm(units: Any, units_per_mm: int) -> float:
    try:
        return float(int(units or 0)) / float(units_per_mm)
    except Exception:
        return 0.0


def _pct(numer: float, denom: float) -> float:
    return (100.0 * numer / denom) if denom else 0.0


def sorted_run_records(project) -> list[tuple[str, dict[str, Any]]]:
    items = []
    for run_id, raw in dict(project.profile_nesting_runs or {}).items():
        record = dict(raw or {})
        run = dict(record.get("run") or {})
        items.append((str(run_id), record, str(run.get("created_at") or "")))
    items.sort(key=lambda x: (x[2], x[0]), reverse=True)
    return [(run_id, record) for run_id, record, _ in items]


def _primary_distance(record: dict[str, Any]) -> int:
    run=dict(record.get("run") or {}); plan=dict(record.get("plan") or {}); solver=dict(record.get("solver_plan") or {})
    cur=dict(dict(plan.get("objective") or {}).get("raw_metrics") or {}); best=dict(dict(solver.get("objective") or {}).get("raw_metrics") or {}) if solver else cur
    key={"waste":"waste_units","cost":"total_cost_micros","minimal_bars":"bar_count","stock_first":"purchase_bar_count","remnants_first":"remnant_source_count"}.get(str(run.get("scenario_family") or "waste"),"waste_units")
    try:return int(cur.get(key,0))-int(best.get(key,0))
    except Exception:return 0


def run_rows(project) -> list[dict[str, Any]]:
    rows = []
    for run_id, record in sorted_run_records(project):
        run = dict(record.get("run") or {})
        validation = dict(record.get("validation_report") or {})
        evidence = dict(record.get("solver_evidence") or {})
        plan = dict(record.get("plan") or {})
        rows.append({
            "run_id": run_id,
            "scenario": str(run.get("scenario_id") or "default"),
            "family": str(run.get("scenario_family") or "waste"),
            "status": str(run.get("status") or run.get("result_status") or "draft"),
            "result": str(run.get("result_status") or "not_solved"),
            "backend": str(evidence.get("backend") or run.get("solver_version") or ""),
            "bars": len(_list(plan.get("bars"))),
            "runtime_s": float(run.get("runtime_seconds") or evidence.get("runtime_seconds") or 0.0),
            "gap": run.get("gap") if run.get("gap") is not None else evidence.get("relative_gap"),
            "valid": bool(validation.get("valid", False)),
            "plan_hash": str(run.get("plan_hash") or plan.get("plan_hash") or ""),
            "manual_revision": int(plan.get("manual_revision") or 0),
            "locks": len(list(dict(record.get("manual_planning") or {}).get("locks") or [])),
            "stale": bool(dict(record.get("manual_planning") or {}).get("stale", False)),
            "distance_to_best": _primary_distance(record),
            "created_at": str(run.get("created_at") or ""),
        })
    return rows


def input_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    units_per_mm = _units_per_mm(snapshot)
    pieces_by_line: dict[str, int] = {}
    for piece in _list(snapshot.get("piece_instances")):
        p = _dict(piece)
        key = str(p.get("demand_line_id") or "")
        pieces_by_line[key] = pieces_by_line.get(key, 0) + 1
    rows = []
    for raw in _list(snapshot.get("demand_lines")):
        line = _dict(raw)
        start = _dict(line.get("start_cut")); end = _dict(line.get("end_cut"))
        reasons = [_dict(x) for x in _list(line.get("eligibility_reasons"))]
        blocking = [x for x in reasons if bool(x.get("blocking"))]
        dims = dict(line.get("profile_dimensions_mm") or {})
        rows.append({
            "demand_line_id": str(line.get("demand_line_id") or ""),
            "status": str(line.get("eligibility_status") or "blocked"),
            "quantity": int(line.get("quantity") or pieces_by_line.get(str(line.get("demand_line_id") or ""), 0) or 0),
            "profile": str(line.get("profile_name") or line.get("profile_id") or ""),
            "profile_id": str(line.get("profile_id") or ""),
            "section_hash": str(line.get("section_hash") or ""),
            "length_mm": float(line.get("nominal_length_mm") or _mm(line.get("nominal_length_units"), units_per_mm)),
            "project_phase": str(line.get("project_phase") or ""),
            "position": str(line.get("part_position") or ""),
            "assembly": ", ".join(str(x) for x in _list(line.get("assembly_marks"))),
            "material": str(line.get("material") or ""),
            "grade": str(line.get("material_grade") or ""),
            "manufacturing_hash": str(line.get("manufacturing_hash") or ""),
            "dimensions": " × ".join(f"{k}={v:g}" for k, v in sorted(dims.items())),
            "start_angle": f"{float(start.get('primary_angle_deg') or 0.0):g}° / {float(start.get('secondary_angle_deg') or 0.0):g}°",
            "end_angle": f"{float(end.get('primary_angle_deg') or 0.0):g}° / {float(end.get('secondary_angle_deg') or 0.0):g}°",
            "long_short": _long_short(start, end),
            "orientations": ", ".join(str(x) for x in _list(line.get("allowed_orientations"))),
            "compound": bool(abs(float(start.get("secondary_angle_deg") or 0.0)) > 1e-9 or abs(float(end.get("secondary_angle_deg") or 0.0)) > 1e-9),
            "features": len(_list(line.get("relevant_features"))),
            "batch": str(line.get("production_batch") or ""),
            "priority": int(line.get("priority") or 0),
            "due_date": str(line.get("due_date") or ""),
            "block_reason": "; ".join(str(x.get("code") or x.get("message") or "") for x in blocking),
        })
    return rows


def _long_short(start: dict[str, Any], end: dict[str, Any]) -> str:
    vals = []
    for label, cut in (("S", start), ("E", end)):
        lp, sp = cut.get("long_point_mm"), cut.get("short_point_mm")
        if lp is not None or sp is not None:
            vals.append(f"{label} L={lp if lp is not None else '-'} / K={sp if sp is not None else '-'}")
    return " | ".join(vals)


def bar_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    units_per_mm = _units_per_mm(snapshot)
    plan = dict(record.get("plan") or {})
    manual = dict(record.get("manual_planning") or {})
    active_locks = [dict(x or {}) for x in _list(manual.get("locks")) if bool(dict(x or {}).get("active", True))]
    locked_bars = {str(x.get("bar_id") or "") for x in active_locks if str(x.get("scope") or "") == "bar"}
    locked_pieces = {str(x.get("instance_id") or "") for x in active_locks if str(x.get("scope") or "") == "piece"}
    rows = []
    for raw in _list(plan.get("bars")):
        bar = _dict(raw)
        gross = _mm(bar.get("stock_length_units"), units_per_mm)
        nominal = _mm(bar.get("nominal_sum_units"), units_per_mm)
        physical = _mm(bar.get("occupied_span_units"), units_per_mm)
        remnant = _mm(bar.get("reusable_remnant_units"), units_per_mm)
        waste = _mm(bar.get("waste_units"), units_per_mm)
        rows.append({
            "bar_id": str(bar.get("bar_id") or ""),
            "candidate_id": str(bar.get("candidate_id") or ""),
            "source": str(bar.get("source_type") or ""),
            "source_id": str(bar.get("source_id") or ""),
            "stock_mm": gross,
            "nominal_mm": nominal,
            "physical_mm": physical,
            "transition_mm": _mm(bar.get("transition_effect_units"), units_per_mm),
            "kerf_mm": _mm(bar.get("projected_kerf_units"), units_per_mm),
            "trims_mm": _mm(int(bar.get("head_trim_units") or 0) + int(bar.get("tail_trim_units") or 0), units_per_mm),
            "remnant_mm": remnant,
            "scrap_mm": waste,
            "utilization_pct": _pct(physical, gross),
            "remnant_pct": _pct(remnant, gross),
            "pieces": len(_list(bar.get("placements"))),
            "cuts": int(bar.get("cut_count") or 0),
            "common_cuts": int(bar.get("common_cut_count") or 0),
            "machine": str(bar.get("machine_id") or ""),
            "machine_profile": str(bar.get("machine_profile_id") or ""),
            "cost": float(int(bar.get("total_cost_micros") or 0)) / 1_000_000.0,
            "lock": "bar" if str(bar.get("bar_id") or "") in locked_bars else ("piece" if any(str(dict(x or {}).get("instance_id") or "") in locked_pieces for x in _list(bar.get("placements"))) else ""),
            "bar_hash": str(bar.get("bar_hash") or ""),
        })
    return rows


def sequence_rows(record: dict[str, Any], *, bar_id: str = "") -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    units_per_mm = _units_per_mm(snapshot)
    lines = {str(_dict(x).get("demand_line_id") or ""): _dict(x) for x in _list(snapshot.get("demand_lines"))}
    manual = dict(record.get("manual_planning") or {})
    active_locks = [dict(x or {}) for x in _list(manual.get("locks")) if bool(dict(x or {}).get("active", True))]
    locked_bars = {str(x.get("bar_id") or "") for x in active_locks if str(x.get("scope") or "") == "bar"}
    locks_by_piece = {str(x.get("instance_id") or ""): x for x in active_locks if str(x.get("scope") or "") == "piece"}
    manual_batches={}
    revisions=list(manual.get("revisions") or []); idx=int(manual.get("current_revision_index") or 0)
    if revisions and 0 <= idx < len(revisions):
        for lb in list(dict(revisions[idx] or {}).get("layout") or []):
            for lp in list(dict(lb or {}).get("pieces") or []):
                iid=str(dict(lp or {}).get("instance_id") or ""); batch=str(dict(lp or {}).get("planning_batch") or "")
                if iid and batch: manual_batches[iid]=batch
    rows = []
    for raw_bar in _list(dict(record.get("plan") or {}).get("bars")):
        bar = _dict(raw_bar)
        if bar_id and str(bar.get("bar_id") or "") != bar_id:
            continue
        transitions = {str(_dict(x).get("transition_id") or ""): _dict(x) for x in _list(bar.get("transitions"))}
        for raw in _list(bar.get("placements")):
            p = _dict(raw); line = lines.get(str(p.get("demand_line_id") or ""), {})
            start = _dict(line.get("start_cut")); end = _dict(line.get("end_cut"))
            trans = transitions.get(str(p.get("transition_after_id") or ""), {})
            rows.append({
                "bar_id": str(bar.get("bar_id") or ""),
                "sequence": int(p.get("sequence_index") or 0),
                "position": str(p.get("part_position") or ""),
                "part_id": str(p.get("part_id") or ""),
                "instance_id": str(p.get("instance_id") or ""),
                "profile": str(line.get("profile_name") or line.get("profile_id") or ""),
                "length_mm": _mm(p.get("length_units"), units_per_mm),
                "reference_start_mm": _mm(p.get("reference_start_units"), units_per_mm),
                "reference_end_mm": _mm(p.get("reference_end_units"), units_per_mm),
                "physical_min_mm": _mm(p.get("physical_min_units"), units_per_mm),
                "physical_max_mm": _mm(p.get("physical_max_units"), units_per_mm),
                "orientation": str(p.get("orientation_id") or ""),
                "start_angle": f"{float(start.get('primary_angle_deg') or 0.0):g}°",
                "end_angle": f"{float(end.get('primary_angle_deg') or 0.0):g}°",
                "common_cut": bool(trans.get("common_cut", False)),
                "kerf_mm": _mm(p.get("kerf_units"), units_per_mm),
                "batch": str(line.get("production_batch") or ""),
                "planning_batch": manual_batches.get(str(p.get("instance_id") or ""),""),
                "lock": ("bar" if str(bar.get("bar_id") or "") in locked_bars else ("piece" if str(p.get("instance_id") or "") in locks_by_piece else "")),
                "lock_id": str(dict(locks_by_piece.get(str(p.get("instance_id") or ""), {}) or {}).get("lock_id") or ""),
            })
    rows.sort(key=lambda r: (r["bar_id"], r["sequence"], r["instance_id"]))
    return rows


def stock_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    units_per_mm = _units_per_mm(snapshot)
    candidates = _list(dict(snapshot.get("stock_snapshot") or {}).get("candidates"))
    rows = []
    for raw in candidates:
        item = _dict(raw)
        rows.append({
            "candidate_id": str(item.get("candidate_id") or ""),
            "source": str(item.get("source_type") or ""),
            "source_id": str(item.get("source_id") or ""),
            "profile": str(item.get("profile_id") or ""),
            "material": str(item.get("material") or ""),
            "grade": str(item.get("material_grade") or ""),
            "length_mm": float(item.get("length_mm") or _mm(item.get("length_units"), units_per_mm)),
            "quantity": item.get("available_quantity"),
            "heat": str(item.get("heat") or ""),
            "certificate": str(item.get("certificate") or ""),
            "supplier": str(item.get("supplier") or ""),
            "location": str(item.get("location") or ""),
            "price": float(item.get("unit_price") or 0.0),
            "reservation": str(item.get("reservation_status") or "available"),
            "reliability": str(item.get("measurement_reliability") or ""),
        })
    return rows


def machine_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    profiles = _list(dict(snapshot.get("machine_snapshot") or {}).get("profiles"))
    rows = []
    for raw in profiles:
        item = _dict(raw)
        rows.append({
            "profile_id": str(item.get("profile_id") or ""),
            "machine_id": str(item.get("machine_id") or ""),
            "group": str(item.get("machine_group") or ""),
            "status": str(item.get("validation_status") or ""),
            "kerf_mm": float(item.get("kerf_mm") or 0.0),
            "head_trim_mm": float(item.get("head_trim_mm") or 0.0),
            "tail_trim_mm": float(item.get("tail_trim_mm") or 0.0),
            "angle_range": f"{float(item.get('min_saw_angle_deg') or 0):g}° … {float(item.get('max_saw_angle_deg') or 0):g}°",
            "max_part_mm": float(item.get("max_part_length_mm") or 0.0),
            "max_stock_mm": float(item.get("max_stock_length_mm") or 0.0),
            "compound": str(item.get("compound_cut_policy") or "blocked"),
            "common": str(item.get("common_cut_policy") or "blocked"),
            "hash": str(item.get("configuration_hash") or ""),
        })
    return rows


def tool_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    tools = _list(dict(snapshot.get("tool_snapshot") or {}).get("tools"))
    rows = []
    for raw in tools:
        item = _dict(raw)
        rows.append({
            "tool_id": str(item.get("tool_id") or ""),
            "type": str(item.get("tool_type") or ""),
            "material": str(item.get("material") or ""),
            "diameter_mm": float(item.get("diameter_mm") or 0.0),
            "length_mm": float(item.get("length_mm") or 0.0),
            "machines": ", ".join(str(x) for x in _list(item.get("allowed_machine_ids"))),
            "status": str(item.get("status") or ""),
            "maintenance": str(item.get("maintenance_status") or ""),
            "hash": str(item.get("configuration_hash") or ""),
        })
    return rows


def error_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    snapshot = dict(record.get("input_snapshot") or {})
    for raw_line in _list(snapshot.get("demand_lines")):
        line = _dict(raw_line)
        for raw in _list(line.get("eligibility_reasons")):
            msg = _dict(raw)
            rows.append(_error_row(msg, source=f"input:{line.get('part_position') or line.get('part_id') or ''}"))
    validation = dict(record.get("validation_report") or {})
    for raw in _list(validation.get("messages")):
        rows.append(_error_row(_dict(raw), source="validator"))
    # Stable deterministic order; duplicates remain visible if sources differ.
    rows.sort(key=lambda r: (not r["blocking"], r["severity"], r["code"], r["source"], r["message"]))
    return rows


def _error_row(msg: dict[str, Any], *, source: str) -> dict[str, Any]:
    code = str(msg.get("code") or "")
    return {
        "code": code,
        "severity": str(msg.get("severity") or ("error" if msg.get("blocking") else "warning")),
        "blocking": bool(msg.get("blocking", False)),
        "message": str(msg.get("message") or NESTING_ERROR_CODES.get(code, "")),
        "source": source,
        "objects": ", ".join(str(x) for x in _list(msg.get("object_ids"))),
        "cause": str(msg.get("probable_cause") or ""),
        "action": str(msg.get("suggested_action") or ""),
        "details": dict(msg.get("technical_details") or {}),
    }


def evidence_rows(record: dict[str, Any]) -> list[tuple[str, str]]:
    evidence = dict(record.get("solver_evidence") or {})
    validation = dict(record.get("validation_report") or {})
    run = dict(record.get("run") or {})
    plan = dict(record.get("plan") or {})
    pairs: list[tuple[str, str]] = []
    for label, value in (
        ("Scenario", run.get("scenario_id")),
        ("Status", run.get("result_status")),
        ("Backend", evidence.get("backend")),
        ("Backendversie", evidence.get("backend_version")),
        ("Exacte scope", evidence.get("exact_scope")),
        ("Exacte scope reden", evidence.get("exact_scope_reason")),
        ("Runtime", evidence.get("runtime_seconds")),
        ("Nodes", evidence.get("nodes_explored")),
        ("Pruned states", evidence.get("states_pruned")),
        ("Lower bound", evidence.get("lower_bound")),
        ("Upper bound", evidence.get("upper_bound")),
        ("Relatieve gap", evidence.get("relative_gap")),
        ("Limit", evidence.get("limit_reached")),
        ("Plan hash", plan.get("plan_hash")),
        ("Evidence hash", evidence.get("evidence_hash")),
        ("Validator geldig", validation.get("valid")),
        ("Validatie hash", validation.get("report_hash")),
        ("Input snapshot", run.get("input_snapshot_hash")),
        ("Manual revision", plan.get("manual_revision")),
        ("Origin solver plan", plan.get("origin_plan_hash")),
        ("Best known plan", plan.get("best_known_plan_hash")),
        ("Lock snapshot", plan.get("lock_snapshot_hash")),
    ):
        pairs.append((label, "" if value is None else str(value)))
    simplifications = _list(evidence.get("simplifications"))
    if simplifications:
        pairs.append(("Vereenvoudigingen", "\n".join(str(x) for x in simplifications)))
    objective = dict(plan.get("objective") or {})
    if objective:
        pairs.append(("Objective", str(objective.get("mode") or "")))
        for key, value in sorted(dict(objective.get("raw_metrics") or {}).items()):
            pairs.append((f"Metric · {key}", str(value)))
    return pairs


def totals(record: dict[str, Any]) -> dict[str, float | int]:
    snapshot = dict(record.get("input_snapshot") or {})
    upm = _units_per_mm(snapshot)
    plan = dict(record.get("plan") or {})
    balance = dict(plan.get("material_balance") or {})
    gross = _mm(balance.get("gross_stock_units"), upm)
    net = _mm(balance.get("net_part_units"), upm)
    remnant = _mm(balance.get("reusable_remnant_units"), upm)
    waste = _mm(balance.get("waste_units"), upm)
    return {
        "bars": len(_list(plan.get("bars"))),
        "gross_mm": gross,
        "net_mm": net,
        "remnant_mm": remnant,
        "waste_mm": waste,
        "utilization_pct": _pct(net, gross),
        "balance_delta_mm": _mm(balance.get("balance_delta_units"), upm),
    }


__all__ = [
    "sorted_run_records", "run_rows", "input_rows", "bar_rows", "sequence_rows",
    "stock_rows", "machine_rows", "tool_rows", "error_rows", "evidence_rows", "totals",
]
