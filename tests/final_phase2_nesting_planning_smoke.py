from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.optimization.plate_nesting import (
    PlateGeometryRef,
    PlateNestDemand,
    PlatePlacementOverride,
    PlateStock,
    PlateStockBoundary,
    apply_manual_plate_placement,
    reoptimize_canonical_plate_nesting,
    solve_canonical_plate_nesting,
    validate_canonical_plate_nesting,
)
from cws_convertor.production import (
    FiniteCapacityPlanner,
    MachineResource,
    MaintenanceWindow,
    MaterialAvailability,
    OperationRequirement,
    PlanningError,
    ProductionOrder,
    Shift,
)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def run() -> None:
    start = datetime(2026, 8, 31, 6, 0, tzinfo=timezone.utc)
    machine = MachineResource("saw-1", "Saw", "wc-1", ("saw",), setup_minutes=5)
    shift = Shift("shift-1", machine.resource_id, _iso(start), _iso(start + timedelta(hours=8)))
    maintenance = MaintenanceWindow("maint-1", machine.resource_id, _iso(start + timedelta(hours=1)), _iso(start + timedelta(hours=2)), "planned service")
    material = MaterialAvailability("mat-1", "S355-10", _iso(start + timedelta(minutes=45)), 2, "order-1", "saw")
    order = ProductionOrder("order-1", "assembly/plate", 2, _iso(start + timedelta(hours=7)), "a" * 64, (OperationRequirement("saw", "saw", 30, required_material_ids=("S355-10",)),))
    schedule = FiniteCapacityPlanner().schedule((order,), (machine,), (shift,), material_availability=(material,), maintenance_windows=(maintenance,))
    operation = schedule.operations[0]
    assert operation.starts_at == _iso(start + timedelta(hours=2))
    assert schedule.feasible
    try:
        FiniteCapacityPlanner().schedule((order,), (machine,), (shift,))
    except PlanningError as exc:
        assert exc.code == "CWS.PLAN.MATERIAL_UNAVAILABLE"
    else:
        raise AssertionError("missing material must fail closed")

    geometry = PlateGeometryRef("part-geometry", ((0, 0), (200, 0), (200, 100), (0, 100)))
    demands = (PlateNestDemand("demand", "part", geometry, "steel", "S355", 10, quantity=2, production_identity="assembly/part"),)
    stock = (PlateStock("stock", 600, 300, "steel", "S355", 10),)
    plan = solve_canonical_plate_nesting(demands, stock, run_id="phase2-final")
    first = plan.layouts[0].placements[0]
    manual = apply_manual_plate_placement(plan, demands, stock, PlatePlacementOverride(first.instance_id, first.stock_instance_id, 10, 180, locked=True))
    assert first.instance_id in manual.locked_instance_ids
    optimized = reoptimize_canonical_plate_nesting(manual, demands, stock, locked_instance_ids=(first.instance_id,))
    preserved = next(item for layout in optimized.layouts for item in layout.placements if item.instance_id == first.instance_id)
    assert (preserved.x_mm, preserved.y_mm) == (10.0, 180.0)
    assert validate_canonical_plate_nesting(optimized, demands, stock).passed

    stock_shape = PlateGeometryRef("stock-boundary", ((0, 0), (600, 0), (600, 300), (0, 300)), (((250, 100), (350, 100), (350, 200), (250, 200)),))
    boundary = PlateStockBoundary("stock", stock_shape)
    try:
        apply_manual_plate_placement(plan, demands, stock, PlatePlacementOverride(first.instance_id, first.stock_instance_id, 250, 100), stock_boundaries=(boundary,))
    except ValueError as exc:
        assert "OUTSIDE_STOCK_CONTOUR_OR_IN_HOLE" in str(exc) or "OVERLAP" in str(exc)
    else:
        raise AssertionError("placement in stock cutout must fail closed")


if __name__ == "__main__":
    run()
    print("FINAL_PHASE2_NESTING_PLANNING = PASS")
