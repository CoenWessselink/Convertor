"""Project persistence helpers for versioned profile-nesting configuration."""
from __future__ import annotations
from dataclasses import asdict
from typing import Iterable

from cws_convertor.project.model import ProjectModel, stable_sha256
from .formula import validate_formula
from .machine import validate_machine_profile, validate_tool
from .models import FormulaDefinition, MachineOptimizationProfile, PurchaseOption, ToolDefinition

CONFIG_SCHEMA_VERSION = "1.0"

def _audit_set(project: ProjectModel, action: str, entity_id: str, before: object, after: object, user: str) -> None:
    project.audit(action, user=user, entity_id=entity_id,
                  before_hash=stable_sha256(before) if before else "",
                  after_hash=stable_sha256(after))


def set_machine_profile(project: ProjectModel, profile: MachineOptimizationProfile, *, user: str = "system") -> None:
    validate_machine_profile(profile)
    before = project.profile_nesting_machine_profiles.get(profile.profile_id)
    project.profile_nesting_machine_profiles[profile.profile_id] = asdict(profile)
    _audit_set(project, "profile_nesting.machine_profile_set", profile.profile_id, before, asdict(profile), user)


def set_tool(project: ProjectModel, tool: ToolDefinition, *, user: str = "system") -> None:
    validate_tool(tool)
    before = project.profile_nesting_tool_library.get(tool.tool_id)
    project.profile_nesting_tool_library[tool.tool_id] = asdict(tool)
    _audit_set(project, "profile_nesting.tool_set", tool.tool_id, before, asdict(tool), user)


def set_formula(project: ProjectModel, formula: FormulaDefinition, *, user: str = "system") -> None:
    validate_formula(formula)
    before = project.profile_nesting_formula_library.get(formula.formula_id)
    project.profile_nesting_formula_library[formula.formula_id] = asdict(formula)
    _audit_set(project, "profile_nesting.formula_set", formula.formula_id, before, asdict(formula), user)


def set_purchase_option(project: ProjectModel, option: PurchaseOption, *, user: str = "system") -> None:
    if not option.purchase_option_id or not option.profile_id or not option.material or not option.material_grade or option.length_mm <= 0:
        raise ValueError("Purchase option mist verplichte profiel/material/lengtevelden")
    if option.available_quantity is not None and option.available_quantity < 0: raise ValueError("Negatieve purchase quantity")
    if option.moq < 1 or option.unit_price < 0 or option.lead_time_days < 0: raise ValueError("Ongeldige purchase option")
    option.refresh_hash()
    before = project.profile_nesting_purchase_options.get(option.purchase_option_id)
    project.profile_nesting_purchase_options[option.purchase_option_id] = asdict(option)
    _audit_set(project, "profile_nesting.purchase_option_set", option.purchase_option_id, before, asdict(option), user)


def load_machine_profiles(project: ProjectModel) -> list[MachineOptimizationProfile]:
    return [MachineOptimizationProfile(**dict(v)) for _, v in sorted(project.profile_nesting_machine_profiles.items())]

def load_tools(project: ProjectModel) -> list[ToolDefinition]:
    return [ToolDefinition(**dict(v)) for _, v in sorted(project.profile_nesting_tool_library.items())]

def load_formulas(project: ProjectModel) -> list[FormulaDefinition]:
    return [FormulaDefinition(**dict(v)) for _, v in sorted(project.profile_nesting_formula_library.items())]

def load_purchase_options(project: ProjectModel) -> list[PurchaseOption]:
    return [PurchaseOption(**dict(v)) for _, v in sorted(project.profile_nesting_purchase_options.items())]
