"""Canonical plate-nesting contracts on the deterministic baseline solver."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
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
class PlateStockBoundary:
    stock_id: str
    geometry: PlateGeometryRef


@dataclass(frozen=True)
class PlatePlacementOverride:
    instance_id: str
    stock_instance_id: str
    x_mm: float
    y_mm: float
    rotation_deg: int = 0
    mirrored: bool = False
    locked: bool = True


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
    locked_instance_ids: tuple[str, ...] = ()

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
            locked_instance_ids=tuple(value.get("locked_instance_ids", [])),
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


def _placed_polygon(placement: PlatePlacement, geometry: PlateGeometryRef):
    try:
        from shapely import affinity
        from shapely.geometry import Polygon
    except ImportError:
        return None
    polygon = Polygon(geometry.outer_contour, geometry.inner_contours)
    min_x, min_y, _max_x, _max_y = geometry.bounds
    polygon = affinity.translate(polygon, xoff=-min_x, yoff=-min_y)
    if placement.mirrored:
        polygon = affinity.scale(polygon, xfact=-1.0, yfact=1.0, origin="center")
    polygon = affinity.rotate(polygon, placement.rotation_deg, origin=(0.0, 0.0))
    min_x, min_y, _max_x, _max_y = polygon.bounds
    return affinity.translate(polygon, xoff=placement.x_mm - min_x, yoff=placement.y_mm - min_y)


def _rehash_plan(plan: PlateCutPlan, demands: tuple[PlateNestDemand, ...], layouts: tuple[PlateLayout, ...], unplaced: tuple[str, ...], locked: tuple[str, ...], *, algorithm: str) -> PlateCutPlan:
    demand_map = {item.demand_id: item for item in demands}
    used_area = sum(demand_map[item.instance_id.rsplit(":", 1)[0]].geometry.area_mm2 for layout in layouts for item in layout.placements)
    stock_area = sum(layout.width_mm * layout.height_mm for layout in layouts)
    cut_length = sum(demand_map[item.instance_id.rsplit(":", 1)[0]].geometry.cut_length_mm for layout in layouts for item in layout.placements)
    pierces = sum(1 + len(demand_map[item.instance_id.rsplit(":", 1)[0]].geometry.inner_contours) for layout in layouts for item in layout.placements)
    payload = {"algorithm": algorithm, "input_sha256": plan.input_sha256, "layouts": [asdict(item) for item in layouts], "unplaced_instance_ids": sorted(unplaced), "locked_instance_ids": sorted(locked), "neutral_process_intent": plan.neutral_process_intent}
    evidence = replace(plan.solver_evidence, algorithm=algorithm, exact_small_proven=False, optimality_gap=None, solver_status="manual_or_partial_validated")
    return replace(plan, algorithm=algorithm, layouts=layouts, unplaced_instance_ids=tuple(sorted(unplaced)), plan_sha256=_digest(payload), solver_evidence=evidence, utilization=used_area / stock_area if stock_area else 0.0, scrap_area_mm2=max(0.0, stock_area - used_area), cut_length_mm=cut_length, pierce_count=pierces, predicted_remnants=(), locked_instance_ids=tuple(sorted(locked)))


def apply_manual_plate_placement(plan: PlateCutPlan, demands: Iterable[PlateNestDemand], stock: Iterable[PlateStock], override: PlatePlacementOverride, *, remnants: Iterable[PlateRemnant] = (), purchase_options: Iterable[PlatePurchaseOption] = (), stock_boundaries: Iterable[PlateStockBoundary] = ()) -> PlateCutPlan:
    demand_list = tuple(demands)
    demand_map = {item.demand_id: item for item in demand_list}
    sources = _stock_sources(stock, remnants, purchase_options)
    source_map = {f"{item.stock_id}:{number:04d}": item for item in sources for number in range(1, item.quantity + 1)}
    demand_id = override.instance_id.rsplit(":", 1)[0]
    demand, source = demand_map.get(demand_id), source_map.get(override.stock_instance_id)
    if demand is None or source is None:
        raise ValueError("manual placement references unknown demand or stock instance")
    rotation = int(override.rotation_deg) % 360
    if rotation not in demand.allowed_rotations_deg or (override.mirrored and not demand.mirror_allowed):
        raise ValueError("manual placement violates orientation constraints")
    width = demand.geometry.height_mm if rotation % 180 == 90 else demand.geometry.width_mm
    height = demand.geometry.width_mm if rotation % 180 == 90 else demand.geometry.height_mm
    replacement = PlatePlacement(override.instance_id, demand.part_id, override.stock_instance_id, float(override.x_mm), float(override.y_mm), width, height, rotation % 180 == 90, rotation, bool(override.mirrored), demand.geometry.geometry_sha256, demand.production_identity, demand.material, demand.grade, demand.thickness_mm)
    layouts: list[PlateLayout] = []
    found = False
    target_found = False
    for layout in plan.layouts:
        retained = tuple(item for item in layout.placements if item.instance_id != override.instance_id)
        found = found or len(retained) != len(layout.placements)
        if layout.stock_instance_id == override.stock_instance_id:
            retained = (*retained, replacement)
            target_found = True
        if retained:
            layouts.append(replace(layout, placements=tuple(retained)))
    if not target_found:
        layouts.append(PlateLayout(override.stock_instance_id, source.stock_id, source.width_mm, source.height_mm, (replacement,)))
    unplaced = tuple(item for item in plan.unplaced_instance_ids if item != override.instance_id)
    if not found and override.instance_id not in plan.unplaced_instance_ids:
        raise ValueError("manual placement instance does not belong to this plan")
    locked = set(plan.locked_instance_ids)
    if override.locked:
        locked.add(override.instance_id)
    else:
        locked.discard(override.instance_id)
    candidate = _rehash_plan(plan, demand_list, tuple(layouts), unplaced, tuple(locked), algorithm="canonical_manual_layout_v1")
    report = validate_canonical_plate_nesting(candidate, demand_list, stock, remnants=remnants, purchase_options=purchase_options, stock_boundaries=stock_boundaries)
    if not report.passed:
        raise ValueError(f"manual placement rejected: {','.join(report.blocking_codes)}")
    return candidate


def reoptimize_canonical_plate_nesting(plan: PlateCutPlan, demands: Iterable[PlateNestDemand], stock: Iterable[PlateStock], *, locked_instance_ids: Iterable[str] = (), placement_overrides: Iterable[PlatePlacementOverride] = (), remnants: Iterable[PlateRemnant] = (), purchase_options: Iterable[PlatePurchaseOption] = (), stock_boundaries: Iterable[PlateStockBoundary] = (), run_id: str | None = None) -> PlateCutPlan:
    demand_list = tuple(demands)
    locked = tuple(sorted(set(locked_instance_ids) | set(plan.locked_instance_ids)))
    previous = {item.instance_id: item for layout in plan.layouts for item in layout.placements if item.instance_id in locked}
    if set(locked) - set(previous):
        raise ValueError("a locked placement is missing from the source plan")
    candidate = solve_canonical_plate_nesting(demand_list, stock, remnants=remnants, purchase_options=purchase_options, kerf_mm=plan.kerf_mm, edge_margin_mm=plan.edge_margin_mm, spacing_mm=plan.spacing_mm, run_id=run_id or plan.run_id)
    for instance_id in locked:
        item = previous[instance_id]
        candidate = apply_manual_plate_placement(candidate, demand_list, stock, PlatePlacementOverride(instance_id, item.stock_instance_id, item.x_mm, item.y_mm, item.rotation_deg, item.mirrored, True), remnants=remnants, purchase_options=purchase_options, stock_boundaries=stock_boundaries)
    for override in placement_overrides:
        candidate = apply_manual_plate_placement(candidate, demand_list, stock, override, remnants=remnants, purchase_options=purchase_options, stock_boundaries=stock_boundaries)
    return candidate


def validate_canonical_plate_nesting(plan: PlateCutPlan, demands: Iterable[PlateNestDemand], stock: Iterable[PlateStock], *, remnants: Iterable[PlateRemnant] = (), purchase_options: Iterable[PlatePurchaseOption] = (), stock_boundaries: Iterable[PlateStockBoundary] = ()) -> PlateValidationReport:
    demand_list = tuple(demands)
    demand_map = {item.demand_id: item for item in demand_list}
    sources = _stock_sources(stock, remnants, purchase_options)
    source_map = {item.stock_id: item for item in sources}
    boundary_map = {item.stock_id: item.geometry for item in stock_boundaries}
    legacy = PlateNestingPlan(plan.algorithm, plan.kerf_mm + plan.spacing_mm, plan.edge_margin_mm, plan.layouts, plan.unplaced_instance_ids, plan.input_sha256, plan.plan_sha256)
    legacy_report = validate_plate_nesting(legacy)
    codes = list(legacy_report.blocking_codes)
    expected = {f"{item.demand_id}:{number:04d}" for item in demand_list for number in range(1, item.quantity + 1)}
    actual: set[str] = set()
    exact_by_layout: dict[str, list[tuple[PlatePlacement, Any]]] = {}
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
            polygon = _placed_polygon(placement, demand.geometry)
            if polygon is None and (demand.geometry.inner_contours or layout.stock_id in boundary_map):
                codes.append("CWS.PLATE.EXACT_GEOMETRY_ENGINE_UNAVAILABLE")
            elif polygon is not None:
                exact_by_layout.setdefault(layout.stock_instance_id, []).append((placement, polygon))
                boundary = boundary_map.get(layout.stock_id)
                if boundary is not None:
                    stock_polygon = _placed_polygon(PlatePlacement("stock", "stock", layout.stock_instance_id, 0.0, 0.0, boundary.width_mm, boundary.height_mm), boundary)
                    usable = stock_polygon.buffer(-plan.edge_margin_mm) if stock_polygon is not None else None
                    if usable is None or usable.is_empty or not usable.covers(polygon):
                        codes.append("CWS.PLATE.OUTSIDE_STOCK_CONTOUR_OR_IN_HOLE")
    exact_clearance = plan.kerf_mm + plan.spacing_mm
    for values in exact_by_layout.values():
        for index, (_left_item, left) in enumerate(values):
            for _right_item, right in values[index + 1:]:
                if left.intersects(right) or left.distance(right) + 1e-7 < exact_clearance:
                    codes.append("CWS.PLATE.EXACT_CONTOUR_OVERLAP_OR_KERF")
    if actual | set(plan.unplaced_instance_ids) != expected:
        codes.append("CWS.PLATE.DEMAND_IDENTITY_MISMATCH")
    if set(plan.locked_instance_ids) - actual:
        codes.append("CWS.PLATE.LOCKED_INSTANCE_MISSING")
    unique = tuple(dict.fromkeys(codes))
    return PlateValidationReport(not unique, unique, legacy_report.checked_placements, plan.plan_sha256)


__all__ = ["PlateCutPlan", "PlateGeometryRef", "PlateNestDemand", "PlateNestRun", "PlateOrientationVariant", "PlatePlacementOverride", "PlatePurchaseOption", "PlateRemnant", "PlateSolverEvidence", "PlateStock", "PlateStockBoundary", "PlateValidationReport", "apply_manual_plate_placement", "reoptimize_canonical_plate_nesting", "solve_canonical_plate_nesting", "validate_canonical_plate_nesting"]
