"""Canonical plate-nesting contracts on the deterministic baseline solver."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isclose, isfinite
from typing import Any, Iterable

from .core import PlateLayout, PlateNestingPlan, PlatePlacement, PlatePart, StockPlate, solve_plate_nesting, validate_plate_nesting

Point2D = tuple[float, float]


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return sha256(raw.encode("utf-8")).hexdigest()


def _positive(name: str, value: float) -> float:
    result = float(value)
    if not isfinite(result) or result <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return result


def _signed_area(points: tuple[Point2D, ...]) -> float:
    return 0.5 * sum(points[i][0] * points[(i + 1) % len(points)][1] - points[(i + 1) % len(points)][0] * points[i][1] for i in range(len(points)))


def _contour(value: Iterable[Iterable[float]], name: str) -> tuple[Point2D, ...]:
    points = tuple((float(point[0]), float(point[1])) for point in value)
    if len(points) >= 2 and points[0] == points[-1]:
        points = points[:-1]
    if len(points) < 3 or any(not isfinite(axis) for point in points for axis in point) or abs(_signed_area(points)) <= 1e-9:
        raise ValueError(f"{name} requires at least three finite points and usable area")
    return points


def _perimeter(points: tuple[Point2D, ...]) -> float:
    return sum(((points[i][0] - points[(i + 1) % len(points)][0]) ** 2 + (points[i][1] - points[(i + 1) % len(points)][1]) ** 2) ** 0.5 for i in range(len(points)))


@dataclass(frozen=True)
class PlateGeometryRef:
    geometry_id: str
    outer_contour: tuple[Point2D, ...]
    inner_contours: tuple[tuple[Point2D, ...], ...] = ()

    def __post_init__(self) -> None:
        if not self.geometry_id:
            raise ValueError("geometry_id is required")
        outer = _contour(self.outer_contour, "outer_contour")
        holes = tuple(_contour(item, "inner_contour") for item in self.inner_contours)
        object.__setattr__(self, "outer_contour", outer)
        object.__setattr__(self, "inner_contours", holes)
        min_x, min_y, max_x, max_y = self.bounds
        if any(not (min_x <= x <= max_x and min_y <= y <= max_y) for hole in holes for x, y in hole):
            raise ValueError("inner contour lies outside the outer contour bounds")

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        xs = [point[0] for point in self.outer_contour]
        ys = [point[1] for point in self.outer_contour]
        return min(xs), min(ys), max(xs), max(ys)

    @property
    def width_mm(self) -> float:
        left, _top, right, _bottom = self.bounds
        return right - left

    @property
    def height_mm(self) -> float:
        _left, top, _right, bottom = self.bounds
        return bottom - top

    @property
    def area_mm2(self) -> float:
        return abs(_signed_area(self.outer_contour)) - sum(abs(_signed_area(item)) for item in self.inner_contours)

    @property
    def cut_length_mm(self) -> float:
        return _perimeter(self.outer_contour) + sum(_perimeter(item) for item in self.inner_contours)

    @property
    def geometry_sha256(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class PlateNestDemand:
    demand_id: str
    part_id: str
    geometry: PlateGeometryRef
    material: str
    grade: str
    thickness_mm: float
    quantity: int = 1
    allowed_rotations_deg: tuple[int, ...] = (0, 90)
    mirror_allowed: bool = False
    grain_direction_deg: float | None = None
    production_identity: str = ""

    def __post_init__(self) -> None:
        if not self.demand_id or not self.part_id or not self.material or not self.grade:
            raise ValueError("plate demand identity/material is incomplete")
        object.__setattr__(self, "thickness_mm", _positive("thickness_mm", self.thickness_mm))
        if int(self.quantity) < 1:
            raise ValueError("quantity must be at least one")
        object.__setattr__(self, "quantity", int(self.quantity))
        rotations = tuple(sorted({int(value) % 360 for value in self.allowed_rotations_deg}))
        if not rotations or any(value not in {0, 90, 180, 270} for value in rotations):
            raise ValueError("baseline plate nesting supports orthogonal rotations only")
        object.__setattr__(self, "allowed_rotations_deg", rotations)
        object.__setattr__(self, "production_identity", self.production_identity or self.part_id)


@dataclass(frozen=True)
class PlateStock:
    stock_id: str
    width_mm: float
    height_mm: float
    material: str
    grade: str
    thickness_mm: float
    quantity: int = 1
    grain_direction_deg: float | None = None

    def __post_init__(self) -> None:
        if not self.stock_id or not self.material or not self.grade:
            raise ValueError("plate stock identity/material is incomplete")
        object.__setattr__(self, "width_mm", _positive("width_mm", self.width_mm))
        object.__setattr__(self, "height_mm", _positive("height_mm", self.height_mm))
        object.__setattr__(self, "thickness_mm", _positive("thickness_mm", self.thickness_mm))
        if int(self.quantity) < 1:
            raise ValueError("stock quantity must be at least one")
        object.__setattr__(self, "quantity", int(self.quantity))


@dataclass(frozen=True)
class PlateRemnant(PlateStock):
    source_plan_sha256: str = ""
    reserved: bool = False


@dataclass(frozen=True)
class PlatePurchaseOption(PlateStock):
    supplier: str = ""
    unit_cost: float = 0.0


@dataclass(frozen=True)
class PlateOrientationVariant:
    demand_id: str
    rotation_deg: int
    mirrored: bool
    width_mm: float
    height_mm: float
    geometry_sha256: str


@dataclass(frozen=True)
class PlateSolverEvidence:
    algorithm: str
    deterministic: bool
    exact_small_supported: bool
    exact_small_proven: bool
    optimality_gap: float | None
    input_sha256: str
    solver_status: str


@dataclass(frozen=True)
class PlateValidationReport:
    passed: bool
    blocking_codes: tuple[str, ...]
    checked_placements: int
    plan_sha256: str
    validator: str = "canonical_plate_independent_v1"


@dataclass(frozen=True)
class PlateCutPlan:
    run_id: str
    algorithm: str
    kerf_mm: float
    edge_margin_mm: float
    spacing_mm: float
    layouts: tuple[PlateLayout, ...]
    unplaced_instance_ids: tuple[str, ...]
    input_sha256: str
    plan_sha256: str
    solver_evidence: PlateSolverEvidence
    utilization: float
    scrap_area_mm2: float
    cut_length_mm: float
    pierce_count: int
    predicted_remnants: tuple[PlateRemnant, ...]
    neutral_process_intent: tuple[str, ...]
    report_formats: tuple[str, ...] = ("JSON", "SVG", "PDF", "XLSX", "labels")

    @property
    def complete(self) -> bool:
        return not self.unplaced_instance_ids

    @property
    def placed_count(self) -> int:
        return sum(len(layout.placements) for layout in self.layouts)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PlateCutPlan":
        layouts = tuple(PlateLayout(str(item["stock_instance_id"]), str(item["stock_id"]), float(item["width_mm"]), float(item["height_mm"]), tuple(PlatePlacement(**dict(raw)) for raw in item.get("placements", []))) for item in value.get("layouts", []))
        return cls(
            run_id=str(value["run_id"]), algorithm=str(value["algorithm"]), kerf_mm=float(value["kerf_mm"]),
            edge_margin_mm=float(value["edge_margin_mm"]), spacing_mm=float(value["spacing_mm"]), layouts=layouts,
            unplaced_instance_ids=tuple(value.get("unplaced_instance_ids", [])), input_sha256=str(value["input_sha256"]),
            plan_sha256=str(value["plan_sha256"]), solver_evidence=PlateSolverEvidence(**dict(value["solver_evidence"])),
            utilization=float(value["utilization"]), scrap_area_mm2=float(value["scrap_area_mm2"]),
            cut_length_mm=float(value["cut_length_mm"]), pierce_count=int(value["pierce_count"]),
            predicted_remnants=tuple(PlateRemnant(**dict(item)) for item in value.get("predicted_remnants", [])),
            neutral_process_intent=tuple(value.get("neutral_process_intent", [])), report_formats=tuple(value.get("report_formats", ("JSON", "SVG", "PDF", "XLSX", "labels"))),
        )


@dataclass(frozen=True)
class PlateNestRun:
    run_id: str
    status: str
    input_sha256: str
    plan: PlateCutPlan
    validation: PlateValidationReport


def _material_key(item: PlateNestDemand | PlateStock) -> tuple[str, str, float]:
    return item.material.casefold(), item.grade.casefold(), round(float(item.thickness_mm), 6)


def _stock_sources(stock: Iterable[PlateStock], remnants: Iterable[PlateRemnant], purchases: Iterable[PlatePurchaseOption]) -> tuple[PlateStock, ...]:
    values: tuple[PlateStock, ...] = (*tuple(stock), *tuple(remnants), *tuple(purchases))
    identifiers = [item.stock_id for item in values]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("plate stock/remnant/purchase IDs must be unique")
    return tuple(item for item in values if not isinstance(item, PlateRemnant) or not item.reserved)


def solve_canonical_plate_nesting(demands: Iterable[PlateNestDemand], stock: Iterable[PlateStock], *, remnants: Iterable[PlateRemnant] = (), purchase_options: Iterable[PlatePurchaseOption] = (), kerf_mm: float = 3.0, edge_margin_mm: float = 10.0, spacing_mm: float = 0.0, run_id: str = "plate-run") -> PlateCutPlan:
    demand_list = tuple(demands)
    if not demand_list or len({item.demand_id for item in demand_list}) != len(demand_list):
        raise ValueError("canonical plate nesting requires unique, non-empty demand")
    sources = _stock_sources(stock, remnants, purchase_options)
    effective_kerf = float(kerf_mm) + float(spacing_mm)
    input_payload = {"demands": [asdict(item) for item in demand_list], "stock": [asdict(item) for item in sources], "kerf_mm": float(kerf_mm), "edge_margin_mm": float(edge_margin_mm), "spacing_mm": float(spacing_mm), "run_id": run_id}
    input_sha256 = _digest(input_payload)
    layouts: list[PlateLayout] = []
    unplaced: list[str] = []
    by_key: dict[tuple[str, str, float], list[PlateNestDemand]] = {}
    for demand in demand_list:
        by_key.setdefault(_material_key(demand), []).append(demand)
    demand_map = {item.demand_id: item for item in demand_list}
    source_map = {item.stock_id: item for item in sources}
    for key, grouped in sorted(by_key.items()):
        compatible = [item for item in sources if _material_key(item) == key]
        if not compatible:
            unplaced.extend(f"{item.demand_id}:{number:04d}" for item in grouped for number in range(1, item.quantity + 1))
            continue
        parts = tuple(PlatePart(item.demand_id, item.geometry.width_mm, item.geometry.height_mm, item.quantity, any(value in item.allowed_rotations_deg for value in (90, 270))) for item in grouped)
        legacy_stock = tuple(StockPlate(item.stock_id, item.width_mm, item.height_mm, item.quantity) for item in compatible)
        legacy = solve_plate_nesting(parts, legacy_stock, kerf_mm=effective_kerf, margin_mm=edge_margin_mm)
        unplaced.extend(legacy.unplaced_instance_ids)
        for layout in legacy.layouts:
            placements = []
            for placement in layout.placements:
                demand = demand_map[placement.part_id]
                placements.append(PlatePlacement(
                    placement.instance_id, demand.part_id, placement.stock_instance_id, placement.x_mm, placement.y_mm,
                    placement.width_mm, placement.height_mm, placement.rotated, 90 if placement.rotated else 0, False,
                    demand.geometry.geometry_sha256, demand.production_identity, demand.material, demand.grade, demand.thickness_mm,
                ))
            layouts.append(PlateLayout(layout.stock_instance_id, layout.stock_id, layout.width_mm, layout.height_mm, tuple(placements)))
    used_area = sum(demand.geometry.area_mm2 * demand.quantity for demand in demand_list) - sum(demand_map[item.rsplit(":", 1)[0]].geometry.area_mm2 for item in unplaced)
    stock_area = sum(layout.width_mm * layout.height_mm for layout in layouts)
    cut_length = sum(demand_map[item.instance_id.rsplit(":", 1)[0]].geometry.cut_length_mm for layout in layouts for item in layout.placements)
    pierces = sum(1 + len(demand_map[item.instance_id.rsplit(":", 1)[0]].geometry.inner_contours) for layout in layouts for item in layout.placements)
    predicted = []
    for layout in layouts:
        source = source_map[layout.stock_id]
        used_right = max((item.x_mm + item.width_mm for item in layout.placements), default=edge_margin_mm)
        width, height = layout.width_mm - edge_margin_mm - used_right, layout.height_mm - 2 * edge_margin_mm
        if width > max(50.0, effective_kerf) and height > 50.0:
            predicted.append(PlateRemnant(f"remnant:{layout.stock_instance_id}", width, height, source.material, source.grade, source.thickness_mm, 1, source.grain_direction_deg, input_sha256))
    exact_supported = sum(item.quantity for item in demand_list) <= 1
    complete = not unplaced
    evidence = PlateSolverEvidence("deterministic_shelf_ffd_canonical_v1", True, exact_supported, exact_supported and complete, 0.0 if exact_supported and complete else None, input_sha256, "complete" if complete else "infeasible_or_insufficient_stock")
    neutral = ("mark", "pierce", "contour", "unload")
    plan_hash = _digest({"algorithm": evidence.algorithm, "input_sha256": input_sha256, "layouts": [asdict(item) for item in layouts], "unplaced_instance_ids": sorted(unplaced), "neutral_process_intent": neutral})
    return PlateCutPlan(run_id, evidence.algorithm, float(kerf_mm), float(edge_margin_mm), float(spacing_mm), tuple(layouts), tuple(sorted(unplaced)), input_sha256, plan_hash, evidence, used_area / stock_area if stock_area else 0.0, max(0.0, stock_area - used_area), cut_length, pierces, tuple(predicted), neutral)


def validate_canonical_plate_nesting(plan: PlateCutPlan, demands: Iterable[PlateNestDemand], stock: Iterable[PlateStock], *, remnants: Iterable[PlateRemnant] = (), purchase_options: Iterable[PlatePurchaseOption] = ()) -> PlateValidationReport:
    demand_list = tuple(demands)
    demand_map = {item.demand_id: item for item in demand_list}
    sources = _stock_sources(stock, remnants, purchase_options)
    source_map = {item.stock_id: item for item in sources}
    legacy = PlateNestingPlan(plan.algorithm, plan.kerf_mm + plan.spacing_mm, plan.edge_margin_mm, plan.layouts, plan.unplaced_instance_ids, plan.input_sha256, plan.plan_sha256)
    legacy_report = validate_plate_nesting(legacy)
    codes = list(legacy_report.blocking_codes)
    expected = {f"{item.demand_id}:{number:04d}" for item in demand_list for number in range(1, item.quantity + 1)}
    actual: set[str] = set()
    stock_instances: set[str] = set()
    for layout in plan.layouts:
        if layout.stock_instance_id in stock_instances:
            codes.append("CWS.PLATE.STOCK_INSTANCE_REUSED")
        stock_instances.add(layout.stock_instance_id)
        source = source_map.get(layout.stock_id)
        if source is None:
            codes.append("CWS.PLATE.UNKNOWN_STOCK")
            continue
        for placement in layout.placements:
            actual.add(placement.instance_id)
            demand = demand_map.get(placement.instance_id.rsplit(":", 1)[0])
            if demand is None:
                codes.append("CWS.PLATE.UNKNOWN_DEMAND")
                continue
            if placement.part_id != demand.part_id or placement.production_identity != demand.production_identity:
                codes.append("CWS.PLATE.PRODUCTION_IDENTITY_CHANGED")
            if placement.geometry_sha256 != demand.geometry.geometry_sha256:
                codes.append("CWS.PLATE.GEOMETRY_OR_TOPOLOGY_CHANGED")
            if placement.rotation_deg % 360 not in demand.allowed_rotations_deg:
                codes.append("CWS.PLATE.ROTATION_FORBIDDEN")
            if placement.mirrored and not demand.mirror_allowed:
                codes.append("CWS.PLATE.MIRROR_FORBIDDEN")
            if _material_key(demand) != _material_key(source):
                codes.append("CWS.PLATE.MATERIAL_GRADE_THICKNESS_MISMATCH")
            expected_width = demand.geometry.height_mm if placement.rotation_deg % 180 == 90 else demand.geometry.width_mm
            expected_height = demand.geometry.width_mm if placement.rotation_deg % 180 == 90 else demand.geometry.height_mm
            if not isclose(placement.width_mm, expected_width, abs_tol=1e-6) or not isclose(placement.height_mm, expected_height, abs_tol=1e-6):
                codes.append("CWS.PLATE.GEOMETRY_DIMENSIONS_CHANGED")
            if demand.grain_direction_deg is not None and source.grain_direction_deg is not None:
                if not isclose((float(demand.grain_direction_deg) + placement.rotation_deg) % 180.0, float(source.grain_direction_deg) % 180.0, abs_tol=1e-6):
                    codes.append("CWS.PLATE.GRAIN_VIOLATION")
    if actual | set(plan.unplaced_instance_ids) != expected:
        codes.append("CWS.PLATE.DEMAND_IDENTITY_MISMATCH")
    unique = tuple(dict.fromkeys(codes))
    return PlateValidationReport(not unique, unique, legacy_report.checked_placements, plan.plan_sha256)


__all__ = ["PlateCutPlan", "PlateGeometryRef", "PlateNestDemand", "PlateNestRun", "PlateOrientationVariant", "PlatePurchaseOption", "PlateRemnant", "PlateSolverEvidence", "PlateStock", "PlateValidationReport", "solve_canonical_plate_nesting", "validate_canonical_plate_nesting"]
