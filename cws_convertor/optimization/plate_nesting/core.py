"""Small deterministic shelf solver with independent geometry validation.

This is a planning kernel, not a CNC postprocessor. It deliberately accepts
only rectangular demand and stock and never silently scales, clips, overlaps,
or drops demand. Production release remains blocked elsewhere in the product.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from math import isfinite
from typing import Iterable


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _positive(name: str, value: float) -> float:
    result = float(value)
    if not isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be a finite positive length")
    return result


@dataclass(frozen=True)
class PlatePart:
    part_id: str
    width_mm: float
    height_mm: float
    quantity: int = 1
    allow_rotation: bool = True

    def __post_init__(self) -> None:
        if not str(self.part_id).strip():
            raise ValueError("part_id is required")
        object.__setattr__(self, "width_mm", _positive("width_mm", self.width_mm))
        object.__setattr__(self, "height_mm", _positive("height_mm", self.height_mm))
        if int(self.quantity) < 1:
            raise ValueError("quantity must be at least one")
        object.__setattr__(self, "quantity", int(self.quantity))


@dataclass(frozen=True)
class StockPlate:
    stock_id: str
    width_mm: float
    height_mm: float
    quantity: int = 1

    def __post_init__(self) -> None:
        if not str(self.stock_id).strip():
            raise ValueError("stock_id is required")
        object.__setattr__(self, "width_mm", _positive("width_mm", self.width_mm))
        object.__setattr__(self, "height_mm", _positive("height_mm", self.height_mm))
        if int(self.quantity) < 1:
            raise ValueError("quantity must be at least one")
        object.__setattr__(self, "quantity", int(self.quantity))


@dataclass(frozen=True)
class PlatePlacement:
    instance_id: str
    part_id: str
    stock_instance_id: str
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    rotated: bool = False
    rotation_deg: int = 0
    mirrored: bool = False
    geometry_sha256: str = ""
    production_identity: str = ""
    material: str = ""
    grade: str = ""
    thickness_mm: float = 0.0


@dataclass(frozen=True)
class PlateLayout:
    stock_instance_id: str
    stock_id: str
    width_mm: float
    height_mm: float
    placements: tuple[PlatePlacement, ...] = ()


@dataclass(frozen=True)
class PlateNestingPlan:
    algorithm: str
    kerf_mm: float
    margin_mm: float
    layouts: tuple[PlateLayout, ...]
    unplaced_instance_ids: tuple[str, ...]
    input_sha256: str
    plan_sha256: str

    @property
    def complete(self) -> bool:
        return not self.unplaced_instance_ids

    @property
    def placed_count(self) -> int:
        return sum(len(layout.placements) for layout in self.layouts)


@dataclass(frozen=True)
class PlateNestingValidation:
    passed: bool
    blocking_codes: tuple[str, ...] = ()
    checked_placements: int = 0
    plan_sha256: str = ""


@dataclass
class _ShelfState:
    stock: StockPlate
    instance_id: str
    x_mm: float
    y_mm: float
    row_height_mm: float = 0.0
    placements: list[PlatePlacement] = field(default_factory=list)


def _orientation_candidates(part: PlatePart) -> tuple[tuple[float, float, bool], ...]:
    candidates = [(part.width_mm, part.height_mm, False)]
    if part.allow_rotation and part.width_mm != part.height_mm:
        candidates.append((part.height_mm, part.width_mm, True))
    return tuple(candidates)


def _try_place(state: _ShelfState, part: PlatePart, instance_id: str, kerf: float, margin: float) -> bool:
    right = state.stock.width_mm - margin
    bottom = state.stock.height_mm - margin
    candidates: list[tuple[float, float, float, float, bool, bool]] = []
    for width, height, rotated in _orientation_candidates(part):
        if state.x_mm + width <= right and state.y_mm + height <= bottom:
            candidates.append((state.y_mm, state.x_mm, width, height, rotated, False))
        next_y = state.y_mm + state.row_height_mm + (kerf if state.row_height_mm else 0.0)
        if margin + width <= right and next_y + height <= bottom:
            candidates.append((next_y, margin, width, height, rotated, True))
    if not candidates:
        return False
    y, x, width, height, rotated, new_row = min(
        candidates,
        key=lambda item: (item[0], item[1], item[2] * item[3], item[4]),
    )
    if new_row:
        state.y_mm = y
        state.x_mm = margin
        state.row_height_mm = 0.0
    state.placements.append(
        PlatePlacement(instance_id, part.part_id, state.instance_id, x, y, width, height, rotated)
    )
    state.x_mm = x + width + kerf
    state.row_height_mm = max(state.row_height_mm, height)
    return True


def solve_plate_nesting(
    parts: Iterable[PlatePart],
    stock: Iterable[StockPlate],
    *,
    kerf_mm: float = 3.0,
    margin_mm: float = 10.0,
) -> PlateNestingPlan:
    kerf = float(kerf_mm)
    margin = float(margin_mm)
    if not isfinite(kerf) or kerf < 0.0:
        raise ValueError("kerf_mm must be finite and non-negative")
    if not isfinite(margin) or margin < 0.0:
        raise ValueError("margin_mm must be finite and non-negative")
    part_list = tuple(parts)
    stock_list = tuple(stock)
    demand = [
        (part, f"{part.part_id}:{number:04d}")
        for part in part_list
        for number in range(1, part.quantity + 1)
    ]
    demand.sort(key=lambda item: (-item[0].width_mm * item[0].height_mm, -max(item[0].width_mm, item[0].height_mm), item[1]))
    states = [
        _ShelfState(item, f"{item.stock_id}:{number:04d}", margin, margin)
        for item in stock_list
        for number in range(1, item.quantity + 1)
    ]
    unplaced: list[str] = []
    for part, instance_id in demand:
        if not any(_try_place(state, part, instance_id, kerf, margin) for state in states):
            unplaced.append(instance_id)
    layouts = tuple(
        PlateLayout(state.instance_id, state.stock.stock_id, state.stock.width_mm, state.stock.height_mm, tuple(state.placements))
        for state in states
        if state.placements
    )
    input_payload = {
        "parts": [asdict(item) for item in part_list],
        "stock": [asdict(item) for item in stock_list],
        "kerf_mm": kerf,
        "margin_mm": margin,
    }
    plan_payload = {
        "algorithm": "deterministic_shelf_ffd_v1",
        "input_sha256": _digest(input_payload),
        "layouts": [asdict(item) for item in layouts],
        "unplaced_instance_ids": unplaced,
    }
    return PlateNestingPlan(
        algorithm=plan_payload["algorithm"],
        kerf_mm=kerf,
        margin_mm=margin,
        layouts=layouts,
        unplaced_instance_ids=tuple(unplaced),
        input_sha256=plan_payload["input_sha256"],
        plan_sha256=_digest(plan_payload),
    )


def validate_plate_nesting(plan: PlateNestingPlan) -> PlateNestingValidation:
    codes: list[str] = []
    seen: set[str] = set()
    checked = 0
    for layout in plan.layouts:
        for placement in layout.placements:
            checked += 1
            if placement.instance_id in seen:
                codes.append("CWS.PLATE.INSTANCE_DUPLICATE")
            seen.add(placement.instance_id)
            if (
                placement.x_mm < plan.margin_mm
                or placement.y_mm < plan.margin_mm
                or placement.x_mm + placement.width_mm > layout.width_mm - plan.margin_mm
                or placement.y_mm + placement.height_mm > layout.height_mm - plan.margin_mm
            ):
                codes.append("CWS.PLATE.OUTSIDE_STOCK")
        placements = layout.placements
        for index, left in enumerate(placements):
            for right in placements[index + 1 :]:
                separated = (
                    left.x_mm + left.width_mm + plan.kerf_mm <= right.x_mm
                    or right.x_mm + right.width_mm + plan.kerf_mm <= left.x_mm
                    or left.y_mm + left.height_mm + plan.kerf_mm <= right.y_mm
                    or right.y_mm + right.height_mm + plan.kerf_mm <= left.y_mm
                )
                if not separated:
                    codes.append("CWS.PLATE.OVERLAP_OR_KERF")
    if plan.unplaced_instance_ids:
        codes.append("CWS.PLATE.UNPLACED_DEMAND")
    unique = tuple(dict.fromkeys(codes))
    return PlateNestingValidation(not unique, unique, checked, plan.plan_sha256)
