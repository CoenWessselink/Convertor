from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing.export_scope_matrix import export_scope_policy
from cws_convertor.optimization.plate_nesting import PlatePart, StockPlate, solve_plate_nesting, validate_plate_nesting
from cws_convertor.project.manufacturing_contracts import ExportScopeKind, ManufacturingHashChain


class Phase2ManufacturingE2ETests(unittest.TestCase):
    def test_demand_to_nesting_scope_and_stale_release_chain(self) -> None:
        plan = solve_plate_nesting(
            (PlatePart("PL-001", 600, 300, 2), PlatePart("PL-002", 450, 250, 1)),
            (StockPlate("S355-PL10", 2000, 1000),),
            kerf_mm=3,
            margin_mm=15,
        )
        self.assertTrue(validate_plate_nesting(plan).passed)
        chain = ManufacturingHashChain()
        chain.set("geometry_hash", {"parts": ["PL-001", "PL-002"]})
        chain.set("base_manufacturing_hash", {"material": "S355", "thickness_mm": 10})
        chain.set("manufacturing_face_hash", {"face": "top"})
        chain.set("contact_hash", {"contacts": []})
        chain.set("mark_set_hash", {"marks": []})
        chain.set("ruleset_hash", {"ruleset": "phase2"})
        chain.set("assembly_marking_variant_hash", {"variant": "normal"})
        chain.set("production_instance_hash", {"instances": plan.placed_count})
        chain.set("nesting_hash", plan.plan_sha256, already_hashed=True)
        self.assertEqual("nesting_run", export_scope_policy(ExportScopeKind.NESTING_RUN).backend_kind)
        chain.set("sequence_hash", {"sequence": [item.instance_id for layout in plan.layouts for item in layout.placements]})
        chain.set("artifact_hash", {"scope": "nesting_run", "plan": plan.plan_sha256})
        chain.set("release_hash", {"machine_transfer_allowed": False})
        chain.require_through("release_hash")
        invalidated = chain.set("base_manufacturing_hash", {"material": "S355", "thickness_mm": 12})
        self.assertIn("nesting_hash", invalidated)
        self.assertNotIn("release_hash", chain.snapshot())


if __name__ == "__main__":
    unittest.main(verbosity=2)
