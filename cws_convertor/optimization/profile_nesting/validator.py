"""Independent validator for profile nesting plans.

The validator reconstructs every straight-cut bar from persisted inputs and the
serialized plan. It intentionally does not call solver placement/compatibility
helpers, so a solver bug is not automatically accepted by shared code.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from cws_convertor.project.model import stable_sha256
from .models import NestingMessage
from .results import NestingPlan, PlanValidationReport
from .units import LengthKernel


def _issue(code: str, message: str, *, object_ids: list[str] | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return asdict(NestingMessage(
        code=code, severity="error", message=message, blocking=True,
        object_ids=list(object_ids or []), technical_details=dict(details or {}),
    ))


def _kernel(snapshot) -> LengthKernel:
    units = dict(getattr(snapshot, "units", {}) or {})
    return LengthKernel(units_per_mm=int(units.get("units_per_mm") or 1000))


def _plan_hash_without_mutation(plan: NestingPlan) -> tuple[str, list[dict[str, Any]]]:
    data = asdict(plan)
    data.pop("created_at", None)
    data.pop("plan_hash", None)
    bar_issues: list[dict[str, Any]] = []
    for bar in list(data.get("bars") or []):
        stored = str(bar.get("bar_hash") or "")
        payload = dict(bar); payload.pop("bar_hash", None)
        calculated = stable_sha256(payload)
        if stored != calculated:
            bar_issues.append(_issue(
                "CWS-NEST-021", "Barhash wijkt af van de inhoud.",
                object_ids=[str(bar.get("bar_id") or "")],
                details={"stored": stored, "calculated": calculated},
            ))
    return stable_sha256(data), bar_issues


def _angles_are_straight(line: dict[str, Any]) -> bool:
    for key in ("start_cut", "end_cut"):
        cut = dict(line.get(key) or {})
        if str(cut.get("status") or "") != "exact":
            return False
        try:
            if abs(float(cut.get("primary_angle_deg") or 0)) > 1e-9:
                return False
            if abs(float(cut.get("secondary_angle_deg") or 0)) > 1e-9:
                return False
        except (TypeError, ValueError):
            return False
    return True


def validate_straight_plan(snapshot, plan: NestingPlan) -> PlanValidationReport:
    kernel = _kernel(snapshot)
    messages: list[dict[str, Any]] = []
    if plan.input_snapshot_hash != str(snapshot.snapshot_hash):
        messages.append(_issue("CWS-NEST-022", "Plan is niet gebonden aan de aangeleverde inputsnapshot."))

    calculated_plan_hash, hash_issues = _plan_hash_without_mutation(plan)
    messages.extend(hash_issues)
    if plan.plan_hash != calculated_plan_hash:
        messages.append(_issue(
            "CWS-NEST-021", "Planhash wijkt af van de planinhoud.",
            details={"stored": plan.plan_hash, "calculated": calculated_plan_hash},
        ))

    lines = {str(x.get("demand_line_id") or ""): dict(x) for x in list(snapshot.demand_lines or [])}
    instances = {str(x.get("instance_id") or ""): dict(x) for x in list(getattr(snapshot, "piece_instances", []) or [])}
    candidates = {str(x.get("candidate_id") or ""): dict(x) for x in list(dict(snapshot.stock_snapshot or {}).get("candidates") or [])}
    machine_profiles = {str(x.get("profile_id") or ""): dict(x) for x in list(dict(snapshot.machine_snapshot or {}).get("profiles") or [])}

    required_ids = set(instances)
    seen_instances: dict[str, str] = {}
    candidate_usage: dict[str, int] = {}
    gross = net = kerf_total = head_total = tail_total = remnant_total = waste_total = 0
    purchase_count = physical_count = full_stock_count = remnant_source_count = 0
    total_cost_micros = 0

    for bar in plan.bars:
        candidate = candidates.get(bar.candidate_id)
        machine = machine_profiles.get(bar.machine_profile_id)
        if candidate is None:
            messages.append(_issue("CWS-NEST-011", "Plan verwijst naar onbekende stockcandidate.", object_ids=[bar.bar_id, bar.candidate_id]))
            continue
        if machine is None:
            messages.append(_issue("CWS-NEST-008", "Plan verwijst naar onbekend machineprofiel.", object_ids=[bar.bar_id, bar.machine_profile_id]))
            continue
        if str(machine.get("machine_id") or "") != bar.machine_id:
            messages.append(_issue("CWS-NEST-008", "Machine-ID en machineprofiel zijn inconsistent.", object_ids=[bar.bar_id]))
        if not bool(machine.get("enabled", True)) or str(machine.get("validation_status") or "") not in {"validated", "released"}:
            messages.append(_issue("CWS-NEST-008", "Machineprofiel is niet gevalideerd/vrijgegeven.", object_ids=[bar.bar_id]))
        if str(machine.get("feed_direction") or "left_to_right") not in {"left_to_right", "bidirectional"}:
            messages.append(_issue("CWS-NEST-008", "Fase 3 ondersteunt deze machine-feedrichting nog niet veilig.", object_ids=[bar.bar_id]))
        if str(candidate.get("source_type") or "") != bar.source_type or str(candidate.get("source_id") or "") != bar.source_id:
            messages.append(_issue("CWS-NEST-024", "Stockbronmetadata wijkt af van de inputsnapshot.", object_ids=[bar.bar_id]))
        expected_stock_length = int(candidate.get("length_units") or 0)
        if expected_stock_length != int(bar.stock_length_units):
            messages.append(_issue("CWS-NEST-024", "Stocklengte wijkt af van de inputsnapshot.", object_ids=[bar.bar_id]))
        candidate_usage[bar.candidate_id] = candidate_usage.get(bar.candidate_id, 0) + 1
        quantity = candidate.get("available_quantity")
        if quantity is not None and candidate_usage[bar.candidate_id] > int(quantity):
            messages.append(_issue("CWS-NEST-012", "Plan gebruikt meer stockbars dan beschikbaar.", object_ids=[bar.candidate_id]))

        expected_kerf = kernel.mm_to_units(machine.get("kerf_mm", 0) or 0)
        expected_head = kernel.mm_to_units(machine.get("head_trim_mm", 0) or 0)
        expected_tail = kernel.mm_to_units(machine.get("tail_trim_mm", 0) or 0)
        expected_safety = kernel.mm_to_units(machine.get("safety_length_mm", 0) or 0)
        expected_min_remnant = max(
            kernel.mm_to_units(machine.get("minimum_end_remnant_mm", 0) or 0),
            kernel.mm_to_units(candidate.get("minimum_reusable_mm", 0) or 0),
        )
        for label, actual, expected in (
            ("kerf", bar.kerf_units, expected_kerf),
            ("head trim", bar.head_trim_units, expected_head),
            ("tail trim", bar.tail_trim_units, expected_tail),
            ("safety length", bar.safety_length_units, expected_safety),
            ("minimum reusable", bar.minimum_reusable_units, expected_min_remnant),
        ):
            if int(actual) != int(expected):
                messages.append(_issue("CWS-NEST-023", f"{label} in plan wijkt af van machine/stock snapshot.", object_ids=[bar.bar_id]))
        max_stock = kernel.mm_to_units(machine.get("max_stock_length_mm", 0) or 0)
        tolerance = kernel.mm_to_units(machine.get("machine_tolerance_mm", 0) or 0)
        if max_stock and bar.stock_length_units > max_stock + tolerance:
            messages.append(_issue("CWS-NEST-015", "Stocklengte overschrijdt machinegrens.", object_ids=[bar.bar_id]))

        zones: list[tuple[int, int]] = []
        for zone in list(machine.get("forbidden_clamp_zones") or []):
            try:
                start = kernel.mm_to_units((zone or {}).get("start_mm", 0) or 0)
                end = kernel.mm_to_units((zone or {}).get("end_mm", 0) or 0)
            except Exception:
                continue
            if end > start:
                zones.append((start, end))

        cursor = expected_head
        placements = sorted(bar.placements, key=lambda p: p.sequence_index)
        if [p.sequence_index for p in placements] != list(range(1, len(placements) + 1)):
            messages.append(_issue("CWS-NEST-021", "Sequence indices op een bar zijn niet aaneengesloten.", object_ids=[bar.bar_id]))
        for placement in placements:
            instance = instances.get(placement.instance_id)
            if instance is None:
                messages.append(_issue("CWS-NEST-019", "Plan bevat een onbekende piece instance.", object_ids=[placement.instance_id, bar.bar_id]))
                continue
            if placement.instance_id in seen_instances:
                messages.append(_issue("CWS-NEST-019", "Piece instance is dubbel toegewezen.", object_ids=[placement.instance_id, seen_instances[placement.instance_id], bar.bar_id]))
            else:
                seen_instances[placement.instance_id] = bar.bar_id
            line_id = str(instance.get("demand_line_id") or "")
            line = lines.get(line_id)
            if line is None:
                messages.append(_issue("CWS-NEST-019", "Piece instance verwijst naar ontbrekende demand line.", object_ids=[placement.instance_id]))
                continue
            if placement.demand_line_id != line_id or placement.part_id != str(instance.get("part_id") or line.get("part_id") or ""):
                messages.append(_issue("CWS-NEST-019", "Placement-identiteit wijkt af van de inputsnapshot.", object_ids=[placement.instance_id]))
            if placement.manufacturing_hash != str(instance.get("manufacturing_hash") or line.get("manufacturing_hash") or ""):
                messages.append(_issue("CWS-NEST-004", "Manufacturing hash van placement is stale/mismatch.", object_ids=[placement.instance_id]))
            if str(line.get("eligibility_status") or "") != "eligible" or not _angles_are_straight(line):
                messages.append(_issue("CWS-NEST-026", "Placement valt buiten de gevalideerde rechte-cut scope.", object_ids=[placement.instance_id]))
            machine_ids = {str(x) for x in list(line.get("candidate_machine_ids") or [])}
            if machine_ids and bar.machine_id not in machine_ids:
                messages.append(_issue("CWS-NEST-008", "Placement gebruikt geen kandidaatmachine van de demand line.", object_ids=[placement.instance_id, bar.machine_id]))

            section = str(line.get("section_hash") or "")
            if str(candidate.get("section_hash") or "") and section and str(candidate.get("section_hash")) != section:
                messages.append(_issue("CWS-NEST-013", "Section identity mismatch tussen part en stock.", object_ids=[placement.instance_id, bar.candidate_id]))
            elif str(candidate.get("profile_id") or "") and str(line.get("profile_id") or "") and str(candidate.get("profile_id")) != str(line.get("profile_id")):
                messages.append(_issue("CWS-NEST-013", "Profiel mismatch tussen part en stock.", object_ids=[placement.instance_id, bar.candidate_id]))
            if str(candidate.get("material") or "") != str(line.get("material") or "") or str(candidate.get("material_grade") or "") != str(line.get("material_grade") or ""):
                messages.append(_issue("CWS-NEST-013", "Materiaal/kwaliteit mismatch tussen part en stock.", object_ids=[placement.instance_id, bar.candidate_id]))
            if str(line.get("heat_requirement") or "") and str(candidate.get("heat") or "") != str(line.get("heat_requirement") or ""):
                messages.append(_issue("CWS-NEST-013", "Heat requirement wordt niet gerespecteerd.", object_ids=[placement.instance_id]))
            if str(line.get("certificate_requirement") or "") and str(candidate.get("certificate") or "") != str(line.get("certificate_requirement") or ""):
                messages.append(_issue("CWS-NEST-013", "Certificaatrequirement wordt niet gerespecteerd.", object_ids=[placement.instance_id]))

            expected_length = int(line.get("nominal_length_units") or 0)
            if int(placement.length_units) != expected_length:
                messages.append(_issue("CWS-NEST-001", "Placementlengte wijkt af van demand line.", object_ids=[placement.instance_id]))
            if int(placement.start_units) != cursor:
                messages.append(_issue("CWS-NEST-014", "Placement start niet op de gereconstrueerde cursor; overlap/gat mogelijk.", object_ids=[placement.instance_id, bar.bar_id]))
            expected_end = cursor + expected_length
            if int(placement.end_units) != expected_end or int(placement.cut_position_units) != expected_end:
                messages.append(_issue("CWS-NEST-014", "Placement end/cutposition is geometrisch inconsistent.", object_ids=[placement.instance_id, bar.bar_id]))
            if int(placement.kerf_units) != expected_kerf:
                messages.append(_issue("CWS-NEST-023", "Placementkerf wijkt af van machine snapshot.", object_ids=[placement.instance_id]))
            cut_start, cut_end = expected_end, expected_end + expected_kerf
            for start, end in zones:
                conflict = start <= cut_start < end if cut_start == cut_end else max(start, cut_start) < min(end, cut_end)
                if conflict:
                    messages.append(_issue("CWS-NEST-016", "Zaagsnede kruist een verboden klemzone.", object_ids=[placement.instance_id, bar.bar_id]))
            cursor = expected_end + expected_kerf

        expected_residual = bar.stock_length_units - expected_tail - cursor
        if expected_residual < expected_safety - tolerance:
            messages.append(_issue("CWS-NEST-016", "Onvoldoende veiligheidslengte na laatste zaagsnede.", object_ids=[bar.bar_id]))
        if expected_residual < -tolerance:
            messages.append(_issue("CWS-NEST-015", "Bar overschrijdt de beschikbare stocklengte.", object_ids=[bar.bar_id]))
        expected_residual = max(0, expected_residual)
        expected_remnant = expected_residual if expected_residual > 0 and expected_residual >= expected_min_remnant else 0
        expected_waste = expected_residual if expected_residual > 0 and expected_remnant == 0 else 0
        if int(bar.raw_residual_units) != expected_residual or int(bar.reusable_remnant_units) != expected_remnant or int(bar.waste_units) != expected_waste:
            messages.append(_issue("CWS-NEST-018", "Rest-/afvalverdeling klopt niet met de gereconstrueerde materiaalbalans.", object_ids=[bar.bar_id]))

        gross += int(bar.stock_length_units)
        net += sum(int(p.length_units) for p in placements)
        kerf_total += len(placements) * expected_kerf
        head_total += expected_head
        tail_total += expected_tail
        remnant_total += expected_remnant
        waste_total += expected_waste
        total_cost_micros += int(bar.total_cost_micros)
        if bar.source_type == "purchase_option": purchase_count += 1
        else: physical_count += 1
        if bar.source_type == "full_stock": full_stock_count += 1
        if bar.source_type == "remnant": remnant_source_count += 1

    missing = sorted(required_ids.difference(seen_instances))
    extra = sorted(set(seen_instances).difference(required_ids))
    if missing:
        messages.append(_issue("CWS-NEST-019", "Niet alle verplichte piece instances zijn toegewezen.", object_ids=missing[:20], details={"missing_count": len(missing)}))
    if extra:
        messages.append(_issue("CWS-NEST-019", "Plan bevat niet-verplichte piece instances.", object_ids=extra[:20], details={"extra_count": len(extra)}))
    if plan.unassigned_instance_ids:
        messages.append(_issue("CWS-NEST-019", "Plan bevat expliciet unassigned instances.", object_ids=list(plan.unassigned_instance_ids)[:20]))

    delta = gross - (net + kerf_total + head_total + tail_total + remnant_total + waste_total)
    recomputed_balance = {
        "gross_stock_units": gross,
        "net_part_units": net,
        "kerf_units": kerf_total,
        "head_trim_units": head_total,
        "tail_trim_units": tail_total,
        "reusable_remnant_units": remnant_total,
        "waste_units": waste_total,
        "balance_delta_units": delta,
        "material_loss_units": kerf_total + head_total + tail_total + waste_total,
    }
    stored_balance = asdict(plan.material_balance)
    for key in ("gross_stock_units", "net_part_units", "kerf_units", "head_trim_units", "tail_trim_units", "reusable_remnant_units", "waste_units", "balance_delta_units"):
        if int(stored_balance.get(key, 0)) != int(recomputed_balance[key]):
            messages.append(_issue("CWS-NEST-018", f"Materiaalbalansveld {key} wijkt af van onafhankelijke reconstructie."))
    if delta != 0:
        messages.append(_issue("CWS-NEST-018", "Materiaalbalans sluit niet exact.", details={"delta_units": delta}))

    if plan.objective is not None:
        expected_metrics = {
            "material_loss_units": recomputed_balance["material_loss_units"],
            "waste_units": waste_total,
            "reusable_remnant_units": remnant_total,
            "gross_stock_units": gross,
            "net_part_units": net,
            "bar_count": len(plan.bars),
            "purchase_bar_count": purchase_count,
            "physical_bar_count": physical_count,
            "full_stock_bar_count": full_stock_count,
            "remnant_bar_count": remnant_source_count,
            "setup_count": len(plan.bars),
            "cost_micros": total_cost_micros,
        }
        for key, value in expected_metrics.items():
            if int(plan.objective.raw_metrics.get(key, 0)) != int(value):
                messages.append(_issue("CWS-NEST-021", f"Objective metric {key} wijkt af van onafhankelijke reconstructie."))

    valid = not messages
    if not valid and not any(m.get("code") == "CWS-NEST-021" for m in messages):
        messages.append(_issue("CWS-NEST-021", "Solverresultaat faalt onafhankelijke planvalidatie."))
    report = PlanValidationReport(
        input_snapshot_hash=str(snapshot.snapshot_hash), plan_hash=plan.plan_hash,
        valid=valid, status="passed" if valid else "blocked", messages=messages,
        material_balance=recomputed_balance, assigned_instance_count=len(seen_instances),
        required_instance_count=len(required_ids), checked_bar_count=len(plan.bars),
    )
    report.refresh_hash()
    return report
