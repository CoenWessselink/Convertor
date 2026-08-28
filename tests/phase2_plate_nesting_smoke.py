from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.optimization.plate_nesting import PlatePart, StockPlate, solve_plate_nesting, validate_plate_nesting


class Phase2PlateNestingTests(unittest.TestCase):
    def test_deterministic_complete_plan_with_rotation_kerf_and_margin(self) -> None:
        parts = (PlatePart("P1", 700, 400, 2), PlatePart("P2", 500, 900, 1, True))
        stock = (StockPlate("S355-10", 2000, 1000, 1),)
        first = solve_plate_nesting(parts, stock, kerf_mm=4, margin_mm=20)
        second = solve_plate_nesting(parts, stock, kerf_mm=4, margin_mm=20)
        self.assertTrue(first.complete)
        self.assertEqual(3, first.placed_count)
        self.assertEqual(first.plan_sha256, second.plan_sha256)
        self.assertEqual(first.layouts, second.layouts)
        self.assertTrue(validate_plate_nesting(first).passed)

    def test_oversize_demand_fails_closed(self) -> None:
        plan = solve_plate_nesting((PlatePart("BIG", 2000, 1000),), (StockPlate("S", 1000, 500),))
        validation = validate_plate_nesting(plan)
        self.assertFalse(plan.complete)
        self.assertIn("BIG:0001", plan.unplaced_instance_ids)
        self.assertIn("CWS.PLATE.UNPLACED_DEMAND", validation.blocking_codes)

    def test_independent_validator_detects_tampering(self) -> None:
        plan = solve_plate_nesting((PlatePart("P", 200, 100),), (StockPlate("S", 500, 300),), margin_mm=10)
        layout = plan.layouts[0]
        bad = replace(layout.placements[0], x_mm=-1)
        tampered = replace(plan, layouts=(replace(layout, placements=(bad,)),))
        self.assertIn("CWS.PLATE.OUTSIDE_STOCK", validate_plate_nesting(tampered).blocking_codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
