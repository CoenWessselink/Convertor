"""Machine/tool configuration and hard capability checks for profile nesting."""
from __future__ import annotations

from dataclasses import asdict
import math
from typing import Any, Iterable

from cws_convertor.project.model import stable_sha256
from .models import (
    FormulaDefinition, MachineCapabilityReport, MachineOptimizationProfile, NestingDemandLine,
    NestingMessage, ToolDefinition,
)

_PROFILE_ALIASES = {
    "hea": "i", "heb": "i", "hem": "i", "ipe": "i", "i_profile": "i",
    "upn": "u", "unp": "u", "u_profile": "u",
    "rhs": "box", "shs": "box", "koker": "box",
    "chs": "tube", "pipe": "tube", "round_tube": "tube",
    "round_bar": "round", "rod": "round",
    "strip": "flat", "bar": "flat", "vlakstaal": "flat",
    "l_profile": "l", "angle": "l", "t_profile": "t", "c_profile": "c",
}

def _norm_profile_type(value: str) -> str:
    key = str(value or "").strip().lower()
    return _PROFILE_ALIASES.get(key, key)


def _message(code: str, text: str, *, blocking: bool = True, details: dict[str, Any] | None = None) -> NestingMessage:
    return NestingMessage(code=code, severity="error" if blocking else "warning", message=text,
                          blocking=blocking, technical_details=dict(details or {}))


def validate_tool(tool: ToolDefinition) -> ToolDefinition:
    if not tool.tool_id.strip() or not tool.tool_type.strip():
        raise ValueError("Tool-ID en tooltype zijn verplicht")
    for label, value in (("diameter", tool.diameter_mm), ("lengte", tool.length_mm),
                         ("slijphoek", tool.point_angle_deg), ("toolwisseltijd", tool.tool_change_seconds),
                         ("tolerantie", tool.tolerance_mm)):
        if not math.isfinite(float(value)) or float(value) < 0:
            raise ValueError(f"Ongeldige {label} voor tool {tool.tool_id}")
    tool.refresh_hash()
    return tool


def validate_machine_profile(profile: MachineOptimizationProfile) -> MachineOptimizationProfile:
    if not profile.profile_id.strip() or not profile.machine_id.strip():
        raise ValueError("Machine optimization profile-ID en machine-ID zijn verplicht")
    if profile.feed_direction not in {"left_to_right", "right_to_left", "bidirectional"}:
        raise ValueError("Ongeldige feed direction")
    if profile.compound_cut_policy not in {"blocked", "review", "supported"}:
        raise ValueError("Ongeldig compound-cutbeleid")
    if profile.common_cut_policy not in {"blocked", "review", "supported"}:
        raise ValueError("Ongeldig common-cutbeleid")
    numeric = [
        profile.min_part_length_mm, profile.max_part_length_mm, profile.max_stock_length_mm,
        profile.kerf_mm, profile.head_trim_mm, profile.tail_trim_mm, profile.extra_miter_loss_mm,
        profile.clamp_width_left_mm, profile.clamp_width_right_mm, profile.safety_length_mm,
        profile.minimum_end_remnant_mm, profile.max_hole_diameter_mm,
        profile.machine_tolerance_mm, profile.position_tolerance_mm, profile.angle_tolerance_deg,
        profile.handling_cost, profile.setup_cost,
    ]
    if any(not math.isfinite(float(v)) or float(v) < 0 for v in numeric):
        raise ValueError(f"Machineprofiel {profile.profile_id} bevat negatieve/niet-eindige parameters")
    if not math.isfinite(profile.min_saw_angle_deg) or not math.isfinite(profile.max_saw_angle_deg):
        raise ValueError("Zaaghoekgrenzen zijn niet eindig")
    if profile.min_saw_angle_deg > profile.max_saw_angle_deg:
        raise ValueError("Minimumzaaghoek is groter dan maximumzaaghoek")
    for zone in profile.forbidden_clamp_zones:
        start, end = float(zone.get("start_mm", 0)), float(zone.get("end_mm", 0))
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            raise ValueError("Ongeldige verboden klemzone")
    profile.refresh_hash()
    return profile


def _feature_kind(feature: dict[str, Any]) -> str:
    return str(feature.get("kind") or feature.get("type") or feature.get("operation") or "").strip().lower()


def _required_operation(feature: dict[str, Any]) -> str | None:
    kind = _feature_kind(feature)
    if kind in {"hole", "drill", "bore", "tap", "tapped_hole", "countersink"}: return "drill"
    if kind in {"mark", "marking", "scribe", "code"}: return "mark"
    if kind in {"notch", "cope", "contour", "pocket"}: return "contour"
    if kind in {"punch", "punched_hole"}: return "punch"
    return None


def _hole_diameter(feature: dict[str, Any]) -> float | None:
    for key in ("diameter_mm", "diameter", "d", "hole_diameter_mm"):
        if key in feature:
            try: return float(feature[key])
            except (TypeError, ValueError): return None
    return None


def _tool_matches(tool: ToolDefinition, machine: MachineOptimizationProfile, diameter: float) -> bool:
    if tool.status != "active" or tool.maintenance_status not in {"ok", "available"}: return False
    if machine.machine_id not in tool.allowed_machine_ids and tool.allowed_machine_ids: return False
    if machine.station_id and tool.allowed_station_ids and machine.station_id not in tool.allowed_station_ids: return False
    if tool.tool_type.lower() not in {"drill", "boor", "center_drill", "centerboor", "tap_drill", "tapboor", "countersink", "verzinkboor"}: return False
    return abs(float(tool.diameter_mm) - float(diameter)) <= max(float(tool.tolerance_mm), float(machine.machine_tolerance_mm))


def evaluate_machine_capability(
    demand: NestingDemandLine,
    machine: MachineOptimizationProfile,
    tools: Iterable[ToolDefinition] = (),
    formulas: Iterable[FormulaDefinition] = (),
) -> MachineCapabilityReport:
    validate_machine_profile(machine)
    from .formula import validate_formula
    tool_list = [validate_tool(t) for t in tools]
    formula_list = list(formulas)
    for formula in formula_list: validate_formula(formula)
    tool_hashes = {t.tool_id: t.configuration_hash for t in tool_list}
    formula_hashes = {f.formula_id: f.formula_hash for f in formula_list}
    machine.refresh_hash(tool_hashes=tool_hashes, formula_hashes=formula_hashes)
    messages: list[NestingMessage] = []
    matched_tools: list[str] = []
    required_tool_ids: list[str] = []

    if not machine.enabled:
        messages.append(_message("CWS-NEST-008", "Machineprofiel is niet actief."))
    if machine.validation_status not in {"validated", "released"}:
        messages.append(_message("CWS-NEST-008", "Machineconfiguratie is nog niet gevalideerd.", blocking=True,
                                 details={"validation_status": machine.validation_status}))

    required_profile = _norm_profile_type(demand.profile_type)
    allowed_profiles = {_norm_profile_type(v) for v in machine.supported_profile_types}
    if required_profile not in allowed_profiles:
        messages.append(_message("CWS-NEST-008", f"Profieltype {demand.profile_type!r} is niet als capability geconfigureerd."))
    if machine.supported_materials and demand.material not in machine.supported_materials and demand.material_grade not in machine.supported_materials:
        messages.append(_message("CWS-NEST-013", "Materiaal/kwaliteit valt buiten machineprofiel."))

    if machine.min_part_length_mm and demand.nominal_length_mm < machine.min_part_length_mm - machine.machine_tolerance_mm:
        messages.append(_message("CWS-NEST-008", "Onderdeel is korter dan de machine-minimumlengte."))
    if machine.max_part_length_mm and demand.nominal_length_mm > machine.max_part_length_mm + machine.machine_tolerance_mm:
        messages.append(_message("CWS-NEST-008", "Onderdeel is langer dan de machine-maximumlengte."))

    dims = dict(getattr(demand, "profile_dimensions_mm", {}) or {})
    for key, minimum in machine.min_dimensions_mm.items():
        if float(minimum) <= 0: continue
        if key not in dims:
            messages.append(_message("CWS-NEST-008", f"Profielmaat {key} ontbreekt; machinefit kan niet worden bewezen."))
        elif float(dims[key]) < float(minimum) - machine.machine_tolerance_mm:
            messages.append(_message("CWS-NEST-008", f"Profielmaat {key} onder machinegrens."))
    for key, maximum in machine.max_dimensions_mm.items():
        if float(maximum) <= 0: continue
        if key not in dims:
            messages.append(_message("CWS-NEST-008", f"Profielmaat {key} ontbreekt; machinefit kan niet worden bewezen."))
        elif float(dims[key]) > float(maximum) + machine.machine_tolerance_mm:
            messages.append(_message("CWS-NEST-008", f"Profielmaat {key} boven machinegrens."))

    for label, cut in (("start", demand.start_cut), ("eind", demand.end_cut)):
        angle = float(cut.primary_angle_deg)
        if angle < machine.min_saw_angle_deg - machine.angle_tolerance_deg or angle > machine.max_saw_angle_deg + machine.angle_tolerance_deg:
            messages.append(_message("CWS-NEST-009", f"{label.capitalize()}zaaghoek {angle:g}° valt buiten machinebereik."))
        if abs(float(cut.secondary_angle_deg)) > machine.angle_tolerance_deg and machine.compound_cut_policy != "supported":
            messages.append(_message("CWS-NEST-026", "Compound cut is niet aantoonbaar ondersteund door deze machine."))

    operations = {"saw"}
    for feature in demand.relevant_features:
        op = _required_operation(feature)
        if op: operations.add(op)
        if op == "drill":
            diameter = _hole_diameter(feature)
            if diameter is None or diameter <= 0:
                messages.append(_message("CWS-NEST-010", "Gatdiameter ontbreekt of is ongeldig.")); continue
            if machine.max_hole_diameter_mm and diameter > machine.max_hole_diameter_mm + machine.machine_tolerance_mm:
                messages.append(_message("CWS-NEST-010", f"Gat Ø{diameter:g} overschrijdt machinegrens.")); continue
            matches = [t for t in tool_list if t.tool_id in machine.tool_ids and _tool_matches(t, machine, diameter)]
            required_tool_ids.append(f"drill:{diameter:g}")
            if not matches:
                messages.append(_message("CWS-NEST-010", f"Geen geldige boor voor Ø{diameter:g} op machine {machine.machine_id}."))
            else:
                matched_tools.append(matches[0].tool_id)
        side = str(feature.get("side") or feature.get("face") or "").lower()
        if side and machine.supported_sides and side not in {s.lower() for s in machine.supported_sides}:
            messages.append(_message("CWS-NEST-008", f"Featurezijde {side!r} is niet bereikbaar."))

    missing_ops = sorted(op for op in operations if op not in set(machine.supported_operations))
    if missing_ops:
        messages.append(_message("CWS-NEST-008", f"Niet-ondersteunde bewerkingen: {', '.join(missing_ops)}"))
    if not set(demand.allowed_orientations).intersection({"as_modeled"} | {f"rotate_{int(v)}" for v in machine.allowed_rotations_deg}):
        messages.append(_message("CWS-NEST-008", "Geen toegestane productieoriëntatie overlapt met machineconfiguratie."))

    report = MachineCapabilityReport(
        machine_profile_id=machine.profile_id, machine_id=machine.machine_id,
        demand_line_id=demand.demand_line_id, feasible=not any(m.blocking for m in messages),
        review_required=any(not m.blocking for m in messages), messages=messages,
        required_tool_ids=sorted(set(required_tool_ids)), matched_tool_ids=sorted(set(matched_tools)),
        effective_machine_hash=machine.configuration_hash,
    )
    report.refresh_hash(); return report


def build_machine_snapshot(profiles: Iterable[MachineOptimizationProfile], tools: Iterable[ToolDefinition], formulas: Iterable[FormulaDefinition] = ()) -> dict[str, Any]:
    from .formula import validate_formula
    tool_list = [validate_tool(t) for t in tools]
    formula_list = list(formulas)
    for formula in formula_list: validate_formula(formula)
    tool_hashes = {t.tool_id: t.configuration_hash for t in tool_list}
    formula_hashes = {f.formula_id: f.formula_hash for f in formula_list}
    profile_list = []
    for p in profiles:
        validate_machine_profile(p); p.refresh_hash(tool_hashes=tool_hashes, formula_hashes=formula_hashes); profile_list.append(p)
    payload = {
        "schema_version": "1.0",
        "profiles": [asdict(p) for p in sorted(profile_list, key=lambda x: x.profile_id)],
        "tools": [asdict(t) for t in sorted(tool_list, key=lambda x: x.tool_id)],
        "formulas": [asdict(f) for f in sorted(formula_list, key=lambda x: x.formula_id)],
    }
    payload["snapshot_hash"] = stable_sha256(payload)
    return payload


def evaluate_machine_stock_compatibility(candidate, machine: MachineOptimizationProfile) -> list[NestingMessage]:
    """Static stock-vs-machine checks independent of a bar placement/solver."""
    messages: list[NestingMessage] = []
    if machine.max_stock_length_mm and float(candidate.length_mm) > machine.max_stock_length_mm + machine.machine_tolerance_mm:
        messages.append(_message("CWS-NEST-015", "Stocklengte overschrijdt de machine-maximumlengte.",
                                 details={"stock_length_mm": candidate.length_mm, "max_stock_length_mm": machine.max_stock_length_mm}))
    minimum_handling = machine.head_trim_mm + machine.tail_trim_mm + machine.safety_length_mm
    if float(candidate.length_mm) + machine.machine_tolerance_mm < minimum_handling:
        messages.append(_message("CWS-NEST-016", "Stock is korter dan de statische trim-/veiligheidslengte van de machine."))
    return messages
