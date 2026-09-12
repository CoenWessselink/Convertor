"""BOM preflight identity follows canonical stock without rebuild-time churn."""
from dataclasses import asdict, replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.production_hub import BOMScopeEngine, BOMStockAllocator, BOMHubState
from cws_convertor.bom.workspace import BOMWorkspaceReadModel
from cws_convertor.project import Part, ProjectModel, StockItem, Remnant


class StockSnapshotIdentityTests(unittest.TestCase):
    def setUp(self):
        self.project = ProjectModel.new("stock snapshot contract")
        part = Part(internal_id="P1", part_position="P1", profile="HEA200",
                    normalized_profile="HEA200", material="S355J2", length_mm=3000,
                    normalized_material="S355J2", material_grade="S355J2", material_confidence=1,
                    classification_status="confirmed", classification_confidence=1, profile_confidence=1,
                    quantity_total=1, mass_each_kg=100, surface_area_each_m2=2,
                    geometry_descriptor={"bbox": [3000, 200, 200]})
        part.recompute_hashes()
        self.project.add_entity(part)
        self.project.add_entity(StockItem(internal_id="S1", profile="HEA200",
                                         material="S355J2", stock_length_mm=6000,
                                         available_quantity=2))
        self.project.add_entity(Remnant(internal_id="R1", profile="HEA200",
                                       material="S355J2", remaining_length_mm=4000))

    def snapshot(self):
        return build_bom_snapshot(self.project, classify_if_needed=False)

    def plan(self):
        snapshot = self.snapshot()
        model = BOMWorkspaceReadModel(snapshot, self.project)
        rows = model.family_rows("parts")
        preflight = BOMScopeEngine(model).preflight("stock", rows,
            expected_snapshot_sha256=snapshot.snapshot_sha256, visible_rows=rows)
        return BOMStockAllocator().plan(self.project, rows), preflight

    def test_active_assignment_cannot_be_overwritten_or_partially_released(self):
        plan, preflight = self.plan()
        state = BOMHubState(self.project)
        record = BOMStockAllocator.reserve_plan(self.project, state.data, plan, preflight)
        assignment = state.data["stock_assignments"][preflight.eligible_group_ids[0]]
        self.assertEqual(["P1"], assignment["entity_ids"])
        new_plan, new_preflight = self.plan()
        before = self.project.to_dict()
        with self.assertRaisesRegex(ValueError, "al een voorraadreservering"):
            BOMStockAllocator.reserve_plan(self.project, state.data, new_plan, new_preflight)
        self.assertEqual(before, self.project.to_dict())
        with self.assertRaisesRegex(ValueError, "niet-geselecteerde"):
            BOMStockAllocator.release_assignments(self.project, state.data,
                preflight.eligible_group_ids, entity_ids=("P2",))
        self.assertEqual(before, self.project.to_dict())
        self.project = ProjectModel.from_dict(before)
        restored = BOMHubState(self.project)
        released = BOMStockAllocator.release_assignments(self.project, restored.data,
            preflight.eligible_group_ids, entity_ids=("P1",))
        self.assertEqual((record.reservation_id,), released)
        self.assertFalse(restored.data["stock_assignments"])

    def test_out_of_scope_and_blocked_preflight_cannot_reserve(self):
        plan, preflight = self.plan()
        state = BOMHubState(self.project)
        state.data
        before = self.project.to_dict()
        invalid = replace(preflight, impact=replace(preflight.impact, entity_ids=("P2",)))
        with self.assertRaisesRegex(ValueError, "buiten.*selectie"):
            BOMStockAllocator.reserve_plan(self.project, state.data, plan, invalid)
        self.assertEqual(before, self.project.to_dict())
        with self.assertRaisesRegex(ValueError, "geblokkeerd"):
            BOMStockAllocator.reserve_plan(self.project, state.data, plan,
                replace(preflight, blocking_reasons=("explicit invalid fixture",)))
        self.assertEqual(before, self.project.to_dict())

    def test_legacy_assignment_requires_the_whole_canonical_group(self):
        # Reuse canonical deserialization for nested provenance dataclasses.
        value = self.project.to_dict()
        value["parts"]["P2"] = {**value["parts"]["P1"], "internal_id": "P2"}
        self.project = ProjectModel.from_dict(value)
        plan, preflight = self.plan()
        state = BOMHubState(self.project)
        record = BOMStockAllocator.reserve_plan(self.project, state.data, plan, preflight)
        for assignment in state.data["stock_assignments"].values():
            assignment.pop("entity_ids")
        before = self.project.to_dict()
        with self.assertRaisesRegex(ValueError, "niet-geselecteerde"):
            BOMStockAllocator.release_assignments(self.project, state.data,
                preflight.eligible_group_ids, entity_ids=("P1",))
        self.assertEqual(before, self.project.to_dict())
        self.assertEqual((record.reservation_id,), BOMStockAllocator.release_assignments(
            self.project, state.data, preflight.eligible_group_ids, entity_ids=("P1", "P2")))

    def test_reserved_stock_invalidates_old_preflight_without_changing_parts(self):
        initial = self.snapshot()
        parts = {key: asdict(value) for key, value in self.project.parts.items()}
        self.project.stock_items["S1"].reserved_quantity = 1
        self.project.stock_items["S1"].reservation_revision += 1
        changed = self.snapshot()
        self.assertNotEqual(initial.snapshot_sha256, changed.snapshot_sha256)
        self.assertEqual(parts, {key: asdict(value) for key, value in self.project.parts.items()})
        model = BOMWorkspaceReadModel(changed, self.project)
        with self.assertRaisesRegex(ValueError, "BOM.*gewijzigd|snapshot"):
            BOMScopeEngine(model).preflight("stock", model.family_rows("parts"),
                expected_snapshot_sha256=initial.snapshot_sha256,
                visible_rows=model.family_rows("parts"))

    def test_selected_occurrence_reservation_does_not_make_sibling_allocated(self):
        from cws_convertor.bom.review_export import _part_snapshot
        value = self.project.to_dict()
        value["parts"]["P2"] = {**value["parts"]["P1"], "internal_id": "P2"}
        self.project = ProjectModel.from_dict(value)
        snapshot = self.snapshot()
        full = BOMWorkspaceReadModel(snapshot, self.project)
        self.assertEqual(1, len(full.family_rows("parts")))
        sliced = BOMWorkspaceReadModel(_part_snapshot(snapshot, self.project, {"P1"}), self.project)
        selected = sliced.family_rows("parts")
        self.assertEqual(("P1",), selected[0].entity_ids)
        preflight = BOMScopeEngine(full).preflight("stock", selected,
            expected_snapshot_sha256=snapshot.snapshot_sha256, visible_rows=full.family_rows("parts"))
        state = BOMHubState(self.project)
        before_parts = {key: asdict(part) for key, part in self.project.parts.items()}
        plan = BOMStockAllocator().plan(self.project, selected)
        BOMStockAllocator.reserve_plan(self.project, state.data, plan, preflight)
        changed = self.snapshot()
        self.assertEqual(before_parts, {key: asdict(part) for key, part in self.project.parts.items()})
        full = BOMWorkspaceReadModel(changed, self.project).family_rows("parts")[0]
        p1 = BOMWorkspaceReadModel(_part_snapshot(changed, self.project, {"P1"}), self.project).family_rows("parts")[0]
        p2 = BOMWorkspaceReadModel(_part_snapshot(changed, self.project, {"P2"}), self.project).family_rows("parts")[0]
        self.assertEqual("Toegewezen", p1.stock_status)
        self.assertTrue(p1.assigned_stock or p1.assigned_remnant)
        self.assertEqual("Gedeeltelijk", full.stock_status)
        self.assertGreaterEqual(full.shortage_mm, 3000)
        self.assertNotEqual("Toegewezen", p2.stock_status)
        self.assertFalse(p2.assigned_stock or p2.assigned_remnant)

    def test_remnant_and_assignment_each_change_identity(self):
        initial = self.snapshot()
        self.project.remnants["R1"].status = "reserved"
        reserved = self.snapshot()
        self.assertNotEqual(initial.snapshot_sha256, reserved.snapshot_sha256)
        self.project.settings.setdefault("bom_production_hub", {})["stock_assignments"] = {
            initial.part_bom[0].group_id: {"source_id": "R1", "source_type": "remnant", "status": "allocated"}
        }
        assigned = self.snapshot()
        self.assertNotEqual(reserved.snapshot_sha256, assigned.snapshot_sha256)

    def test_rebuild_and_canonical_reopen_keep_identity_stable(self):
        initial = self.snapshot()
        self.assertEqual(initial.snapshot_sha256, self.snapshot().snapshot_sha256)
        self.project.settings.setdefault("bom_production_hub", {})["history"] = [{"action": "view"}]
        self.assertEqual(initial.snapshot_sha256, self.snapshot().snapshot_sha256)
        self.project = ProjectModel.from_dict(self.project.to_dict())
        self.assertEqual(initial.snapshot_sha256, self.snapshot().snapshot_sha256)


if __name__ == "__main__":
    unittest.main(verbosity=2)
