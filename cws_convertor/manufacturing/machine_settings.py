"""Machine, stock and remnant configuration for manufacturing workspaces.

The module translates vendor XML into the canonical project contracts.  UI
code only calls these functions; the optimizer keeps reading the existing
ProjectModel stores and therefore receives the same data after save/reopen.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4
import xml.etree.ElementTree as ET

from cws_convertor.optimization.profile_nesting.configuration import (
    set_machine_profile,
    set_purchase_option,
    set_tool,
)
from cws_convertor.optimization.profile_nesting.models import (
    MachineOptimizationProfile,
    PurchaseOption,
    ToolDefinition,
)
from cws_convertor.project.model import MachineProfile, ProjectModel, Remnant, StockItem


PROFILE_CODE_NAMES = {
    "B": "strip_plate",
    "C": "channel",
    "I": "i_profile",
    "L": "l_profile",
    "M": "special_profile",
    "RO": "round_bar",
    "RU": "round_tube",
    "SO": "solid_profile",
    "T": "t_profile",
    "U": "u_profile",
}
OPERATION_CODE_NAMES = {"BO": "drill", "KO": "cope", "PU": "punch", "SC": "saw", "SH": "scribe"}


def _number(value: Any, default: float = 0.0) -> float:
    text = str(value or "").strip().replace(".", "").replace(",", ".") if "," in str(value or "") else str(value or "").strip()
    try:
        return float(text)
    except (TypeError, ValueError):
        return float(default)


def _flag(value: Any) -> bool:
    return str(value or "").strip().casefold() in {"t", "true", "1", "yes", "ja"}


def _text(node: ET.Element | None, name: str, default: str = "") -> str:
    child = node.find(name) if node is not None else None
    return str(child.text or "").strip() if child is not None else default


def _safe_id(value: str) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in clean:
        clean = clean.replace("--", "-")
    return clean or uuid4().hex


def _hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ImportedMachineSettings:
    name: str
    source_path: str
    source_sha256: str
    parameters: dict[str, Any] = field(default_factory=dict)
    profile_capabilities: tuple[dict[str, Any], ...] = ()
    tools: tuple[dict[str, Any], ...] = ()
    imported_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_construsteel_machine_xml(path: str | Path) -> ImportedMachineSettings:
    source = Path(path).expanduser().resolve()
    raw = source.read_bytes()
    root = ET.fromstring(raw)
    machine = root.find(".//WVB036") or root
    name = _text(machine, "MACHINE_NAME", source.stem)
    parameter_nodes = machine.findall(".//WVB032")
    parameters: dict[str, Any] = {}
    for node in parameter_nodes:
        key = _text(node, "PARAMETER_NAME").upper()
        kind = _text(node, "PARAMETER_TYPE").upper()
        if not key:
            continue
        parameters[key] = _text(node, "PARAMETER_OPTION") if kind == "OPTION" else _number(_text(node, "PARAMETER_QUANTITY"))

    capabilities: list[dict[str, Any]] = []
    for node in machine.findall(".//WVB031"):
        code = _text(node, "DSTV_PROFILE_CODE").upper()
        operations: dict[str, dict[str, bool]] = {}
        for operation in node.findall(".//WVB039"):
            op = OPERATION_CODE_NAMES.get(_text(operation, "OPERATION_TYPE").upper(), _text(operation, "OPERATION_TYPE").lower())
            if not op:
                continue
            operations[op] = {
                "active": _flag(_text(operation, "ACTIVE_TYPE")),
                "front": _flag(_text(operation, "VIEW_V")),
                "bottom": _flag(_text(operation, "VIEW_U")),
                "top": _flag(_text(operation, "VIEW_O")),
                "rear": _flag(_text(operation, "VIEW_H")),
            }
        capabilities.append(
            {
                "code": code,
                "profile_type": PROFILE_CODE_NAMES.get(code, code.casefold()),
                "active": _flag(_text(node, "ACTIVE_CODE")),
                "min_y_mm": _number(_text(node, "MIN_Y")),
                "max_y_mm": _number(_text(node, "MAX_Y")),
                "min_z_mm": _number(_text(node, "MIN_Z")),
                "max_z_mm": _number(_text(node, "MAX_Z")),
                "operations": operations,
            }
        )

    tools: list[dict[str, Any]] = []
    for index, node in enumerate(machine.findall(".//WVB047"), 1):
        kind = _text(node, "TOOL_ID", "TOOL").upper()
        diameter = _number(_text(node, "TOOL_DIAMETER"))
        tools.append(
            {
                "tool_id": f"{_safe_id(name)}:{kind.casefold()}:{diameter:g}:{index}",
                "tool_type": kind.casefold(),
                "material": _text(node, "TOOL_TYPE"),
                "diameter_mm": diameter,
                "length_mm": _number(_text(node, "TOOL_LENGTH")),
                "extra_diameter_mm": _number(_text(node, "TOOL_EXTRA_DIAMETER")),
            }
        )
    return ImportedMachineSettings(
        name=name,
        source_path=str(source),
        source_sha256=sha256(raw).hexdigest(),
        parameters=parameters,
        profile_capabilities=tuple(capabilities),
        tools=tuple(tools),
        imported_at=datetime.now(timezone.utc).isoformat(),
    )


def apply_machine_settings(project: ProjectModel, imported: ImportedMachineSettings, *, user: str = "qt-gui") -> str:
    parameters = imported.parameters
    active = [item for item in imported.profile_capabilities if item.get("active")]
    operations = sorted({name for item in active for name, state in dict(item.get("operations") or {}).items() if state.get("active")})
    sides = sorted({side for item in active for state in dict(item.get("operations") or {}).values() for side in ("front", "bottom", "top", "rear") if state.get(side)})
    profile_id = f"machine:{_safe_id(imported.name)}"
    machine_profile = MachineOptimizationProfile(
        profile_id=profile_id,
        machine_id=_safe_id(imported.name),
        machine_group="saw_drill_line",
        controller_profile="DSTV 3.1",
        validation_status="manual_validation_required",
        supported_profile_types=sorted({str(item.get("profile_type") or "") for item in active if item.get("profile_type")}),
        supported_materials=["STEEL", "S235JR", "S275JR", "S355JR"],
        supported_operations=operations or ["saw"],
        supported_sides=sides,
        allowed_rotations_deg=[0.0, 90.0, 180.0, 270.0],
        feed_direction="left_to_right" if str(parameters.get("INPUTDIRECTION") or "LEFT").upper() == "LEFT" else "right_to_left",
        min_dimensions_mm={"y": min((float(item.get("min_y_mm") or 0.0) for item in active), default=0.0), "z": min((float(item.get("min_z_mm") or 0.0) for item in active), default=0.0)},
        max_dimensions_mm={"y": max((float(item.get("max_y_mm") or 0.0) for item in active), default=0.0), "z": max((float(item.get("max_z_mm") or 0.0) for item in active), default=0.0)},
        max_stock_length_mm=float(parameters.get("MAXSTOCKLENGTH") or 24000.0),
        kerf_mm=float(parameters.get("SAWBLADETHICKNESS") or 0.0),
        head_trim_mm=float(parameters.get("HEADCUT") or 0.0),
        tail_trim_mm=float(parameters.get("SAFETYLENGTH") or 0.0),
        extra_miter_loss_mm=float(parameters.get("EXTRA_MITRE_CUT") or 0.0),
        min_saw_angle_deg=float(parameters.get("MIN_ANGLE") or -90.0),
        max_saw_angle_deg=float(parameters.get("MAX_ANGLE") or 90.0),
        preferred_start_angle_range_deg=[float(parameters.get("PREF_START_ANGLE_MIN") or -90.0), float(parameters.get("PREF_START_ANGLE_MAX") or 90.0)],
        preferred_end_angle_range_deg=[float(parameters.get("PREF_END_ANGLE_MIN") or -90.0), float(parameters.get("PREF_END_ANGLE_MAX") or 90.0)],
        pivot_to_stop_mm=float(parameters.get("DISTANCETURNINGPOINT") or 0.0),
        blade_to_measurement_mm=float(parameters.get("DIST_TO_MEASURE_UNIT") or 0.0),
        blade_to_clamp_center_mm=float(parameters.get("DIST_BETW_SAWBL_CL") or 0.0),
        clamp_width_left_mm=float(parameters.get("CLAMPINGWIDTHLEFT") or 0.0),
        clamp_width_right_mm=float(parameters.get("CLAMPINGWIDTHRIGHT") or 0.0),
        safety_length_mm=float(parameters.get("SAFETYLENGTH") or 0.0),
        minimum_end_remnant_mm=float(parameters.get("MINGARBAGE") or 0.0),
        stock_first=_flag(parameters.get("STOCKPRIORITY")),
        compound_cut_policy="supported",
        common_cut_policy="supported" if _flag(parameters.get("USE_PART_CUT")) else "blocked",
        max_hole_diameter_mm=float(parameters.get("MAX_HOLE_DIAMETER") or 0.0),
        tool_ids=[str(item["tool_id"]) for item in imported.tools],
        provenance={"kind": "vendor_xml", "path": imported.source_path, "sha256": imported.source_sha256},
    )
    machine_profile.refresh_hash()
    set_machine_profile(project, machine_profile, user=user)
    for raw in imported.tools:
        tool = ToolDefinition(
            tool_id=str(raw["tool_id"]),
            tool_type=str(raw.get("tool_type") or "tool"),
            material=str(raw.get("material") or ""),
            diameter_mm=float(raw.get("diameter_mm") or 0.0),
            length_mm=float(raw.get("length_mm") or 0.0),
            allowed_machine_ids=[machine_profile.machine_id],
        )
        tool.refresh_hash()
        set_tool(project, tool, user=user)
    project.machine_profiles[profile_id] = MachineProfile(
        internal_id=profile_id,
        name=imported.name,
        category="unknown",
        machine_id=machine_profile.machine_id,
        manufacturer="ConstruSteel XML",
        machine_type="saw_drill_line",
        controller="DSTV 3.1",
        supported_formats=["NC1", "DSTV"],
        min_dimensions_mm=dict(machine_profile.min_dimensions_mm),
        max_dimensions_mm=dict(machine_profile.max_dimensions_mm),
        axes=list(machine_profile.supported_sides),
        supported_operations=list(machine_profile.supported_operations),
        tools=[dict(item) for item in imported.tools],
        kerf_mm=machine_profile.kerf_mm,
        clamp_zones=[{"side": "left", "width_mm": machine_profile.clamp_width_left_mm}, {"side": "right", "width_mm": machine_profile.clamp_width_right_mm}],
        enabled=True,
        properties={"vendor_xml": imported.to_dict(), "optimization_profile_id": profile_id},
    )
    project.settings.setdefault("machine_settings_v1", {})[profile_id] = imported.to_dict()
    project.audit("manufacturing.machine_settings_imported", user=user, entity_id=profile_id, after_hash=machine_profile.configuration_hash, details={"source_sha256": imported.source_sha256})
    return profile_id


def project_profile_catalog(project: ProjectModel) -> tuple[dict[str, str], ...]:
    found: dict[tuple[str, str, str], dict[str, str]] = {}
    for part in project.parts.values():
        props = dict(getattr(part, "properties", {}) or {})
        profile = str(getattr(part, "profile", "") or props.get("profile") or props.get("profile_name") or props.get("ifc_profile_name") or "").strip()
        if not profile:
            continue
        material = str(getattr(part, "material", "") or props.get("material") or "STEEL")
        grade = str(getattr(part, "material_grade", "") or props.get("material_grade") or props.get("grade") or "S355JR")
        section_hash = str(props.get("section_hash") or props.get("profile_section_hash") or _hash(profile.casefold()))
        found[(profile.casefold(), material.casefold(), grade.casefold())] = {"profile": profile, "profile_id": str(props.get("profile_id") or profile), "material": material, "grade": grade, "section_hash": section_hash}
    return tuple(found[key] for key in sorted(found))


def set_trade_lengths(project: ProjectModel, profile: str, material: str, grade: str, lengths_mm: Iterable[float], *, section_hash: str = "", supplier: str = "Handelslengte", user: str = "qt-gui") -> tuple[str, ...]:
    identifiers: list[str] = []
    profile_id = str(profile).strip()
    resolved_hash = str(section_hash or _hash(profile_id.casefold()))
    for length in sorted({float(value) for value in lengths_mm if float(value) > 0.0}):
        option_id = f"trade:{_safe_id(profile_id)}:{int(round(length))}"
        option = PurchaseOption(option_id, f"{profile_id}-{int(round(length))}", profile_id, resolved_hash, material or "STEEL", grade or "S355JR", length, None, supplier=supplier, minimum_reusable_mm=300.0, provenance={"kind": "commercial_length", "user": user})
        option.refresh_hash()
        set_purchase_option(project, option, user=user)
        identifiers.append(option_id)
    project.settings.setdefault("commercial_profile_lengths", {})[profile_id] = sorted({float(value) for value in lengths_mm if float(value) > 0.0})
    return tuple(identifiers)


def add_profile_stock(project: ProjectModel, profile: str, material: str, grade: str, length_mm: float, quantity: float, *, location: str = "Magazijn", section_hash: str = "", user: str = "qt-gui") -> str:
    identifier = f"stock:{_safe_id(profile)}:{int(round(float(length_mm)))}:{uuid4().hex[:8]}"
    project.stock_items[identifier] = StockItem(internal_id=identifier, name=f"{profile} {float(length_mm):g} mm", category="unknown", material=material or "STEEL", profile=profile, grade=grade or "S355JR", stock_length_mm=float(length_mm), available_quantity=float(quantity), location=location, properties={"profile_id": profile, "section_hash": section_hash or _hash(profile.casefold())})
    project.audit("stock.profile_added", user=user, entity_id=identifier)
    return identifier


def add_plate_stock(project: ProjectModel, material: str, grade: str, thickness_mm: float, width_mm: float, height_mm: float, quantity: float, *, location: str = "Plaatmagazijn", user: str = "qt-gui") -> str:
    identifier = f"plate:{int(round(float(thickness_mm)))}:{int(round(float(width_mm)))}x{int(round(float(height_mm)))}:{uuid4().hex[:8]}"
    project.stock_items[identifier] = StockItem(internal_id=identifier, name=f"Plaat {float(thickness_mm):g} x {float(width_mm):g} x {float(height_mm):g}", category="unknown", material=material or "STEEL", grade=grade or "S355JR", plate_size_mm=[float(width_mm), float(height_mm), float(thickness_mm)], available_quantity=float(quantity), location=location, properties={"thickness_mm": float(thickness_mm), "width_mm": float(width_mm), "height_mm": float(height_mm)})
    project.audit("stock.plate_added", user=user, entity_id=identifier)
    return identifier


def add_remnant(project: ProjectModel, profile: str, material: str, grade: str, remaining_length_mm: float, *, stock_item_id: str = "", location: str = "Reststukken", minimum_reusable_mm: float = 300.0, user: str = "qt-gui") -> str:
    identifier = f"remnant:{_safe_id(profile)}:{int(round(float(remaining_length_mm)))}:{uuid4().hex[:8]}"
    project.remnants[identifier] = Remnant(internal_id=identifier, name=f"Reststuk {profile} {float(remaining_length_mm):g} mm", category="unknown", stock_item_id=stock_item_id, material=material or "STEEL", profile=profile, grade=grade or "S355JR", remaining_length_mm=float(remaining_length_mm), minimum_reusable_mm=float(minimum_reusable_mm), location=location, measured_at=datetime.now(timezone.utc).isoformat(), status="available", properties={"profile_id": profile, "section_hash": _hash(profile.casefold())})
    project.audit("stock.remnant_added", user=user, entity_id=identifier)
    return identifier


def return_remnant_to_stock(project: ProjectModel, remnant_id: str, *, user: str = "qt-gui") -> None:
    item = project.remnants[str(remnant_id)]
    item.status = "available"
    item.measured_at = datetime.now(timezone.utc).isoformat()
    item.modified_at = item.measured_at
    project.audit("stock.remnant_returned", user=user, entity_id=item.internal_id, details={"location": item.location, "remaining_length_mm": item.remaining_length_mm})


__all__ = ["ImportedMachineSettings", "add_plate_stock", "add_profile_stock", "add_remnant", "apply_machine_settings", "parse_construsteel_machine_xml", "project_profile_catalog", "return_remnant_to_stock", "set_trade_lengths"]
