"""Strict JSON-native reconstruction helpers for persisted nesting records."""
from __future__ import annotations

from .models import CutTransition, ProfileNestingInputSnapshot
from .results import MaterialBalance, NestingPlan, ObjectiveBreakdown, PiecePlacement, StockBarPlan


def input_snapshot_from_dict(raw: dict) -> ProfileNestingInputSnapshot:
    return ProfileNestingInputSnapshot(**dict(raw or {}))


def plan_from_dict(raw: dict) -> NestingPlan:
    data = dict(raw or {})
    bars = []
    for raw_bar in list(data.pop("bars", []) or []):
        bar_data = dict(raw_bar or {})
        placements = [PiecePlacement(**dict(x or {})) for x in list(bar_data.pop("placements", []) or [])]
        transitions = [CutTransition(**dict(x or {})) for x in list(bar_data.pop("transitions", []) or [])]
        bars.append(StockBarPlan(placements=placements, transitions=transitions, **bar_data))
    balance_raw = data.pop("material_balance", {}) or {}
    objective_raw = data.pop("objective", None)
    balance = MaterialBalance(**dict(balance_raw))
    objective = ObjectiveBreakdown(**dict(objective_raw)) if isinstance(objective_raw, dict) else None
    return NestingPlan(bars=bars, material_balance=balance, objective=objective, **data)


__all__ = ["input_snapshot_from_dict", "plan_from_dict"]
