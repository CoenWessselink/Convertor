from __future__ import annotations

from dataclasses import replace
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.production_hub import (
    ACTION_DEFINITIONS,
    BOMActionMatrix,
    BOMHubState,
    BOMProcurementService,
    BOMQueryClause,
    BOMScopeEngine,
    BOMSmartQuery,
    BOMStockAllocator,
)
from cws_convertor.bom.workspace import BOMScope, BOMWorkspaceReadModel
from cws_convertor.project import Part, ProjectModel, StockItem


def part(entity_id: str, mark: str, profile: str, material: str, phase: str, length: float = 3000.0) -> Part:
    value = Part(
        internal_id=entity_id,
        name=mark,
        part_position=mark,
        profile=profile,
        normalized_profile=profile,
        material=material,
        normalized_material=material,
        material_grade=material,
        length_mm=length,
        quantity_total=1,
        mass_each_kg=100.0,
        surface_area_each_m2=2.0,
        classification_status="confirmed",
        classification_confidence=1.0,
        profile_confidence=1.0,
        material_confidence=1.0,
        geometry_descriptor={"bbox": [length, 200.0, 200.0]},
        properties={"phase": phase, "delivery": "L1"},
    )
    value.recompute_hashes()
    return value


class CompleteBomHubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = ProjectModel.new("Complete BOM hub")
        self.project.add_entity(part("P1", "B1", "HEA200", "S355J2", "F1"))
        self.project.add_entity(part("P2", "B2", "HEA200", "S355J2", "F1", 3200.0))
        self.project.add_entity(part("P3", "B3", "IPE240", "S235JR", "F2"))
        self.project.validate()
        self.snapshot = build_bom_snapshot(
            self.project, user="test", classify_if_needed=False
        )
        self.model = BOMWorkspaceReadModel(self.snapshot, self.project)
        self.engine = BOMScopeEngine(self.model)
        self.rows = self.model.rows(BOMScope.create(family="parts"))

    def test_workflow_fields_and_same_attribute_selection(self) -> None:
        first = next(row for row in self.rows if row.mark == "B1")
        self.assertEqual("F1", first.phase)
        self.assertEqual("L1", first.delivery)
        same_profile = self.engine.matching((first,), "profile")
        self.assertEqual({"B1", "B2"}, {row.mark for row in same_profile})
        same_phase = self.engine.matching((first,), "phase")
        self.assertEqual({"B1", "B2"}, {row.mark for row in same_phase})

    def test_basket_static_and_dynamic_saved_selection(self) -> None:
        state = BOMHubState(self.project)
        first = next(row for row in self.rows if row.mark == "B1")
        state.add_to_basket(first.entity_ids)
        state.add_to_basket(("P2",))
        self.assertEqual(("P1", "P2"), state.basket())
        state.remove_from_basket(("P1",))
        self.assertEqual(("P2",), state.basket())
        saved = state.save_selection(
            "Alle HEA200", (first,), snapshot_sha256=self.snapshot.snapshot_sha256,
            dynamic_basis="profile",
        )
        resolved = self.engine.resolve_saved(saved)
        self.assertEqual({"P1", "P2"}, {
            entity_id for row in resolved for entity_id in row.entity_ids
        })
        self.assertTrue(any(event.action == "bom.selection.saved" for event in self.project.audit_log))

    def test_mixed_preflight_partitions_and_never_silently_skips(self) -> None:
        blocked = replace(
            self.rows[-1], blocked=True, status="blocked",
            blocking_reasons=("Ontbrekende geometrie",),
        )
        self.model._rows["parts"] = (*self.rows[:-1], blocked)
        selected = self.model.family_rows("parts")
        preflight = self.engine.preflight(
            "machine", selected,
            expected_snapshot_sha256=self.snapshot.snapshot_sha256,
            visible_rows=selected,
        )
        self.assertTrue(preflight.allowed)
        self.assertEqual(2, len(preflight.eligible_group_ids))
        self.assertEqual((blocked.group_id,), preflight.blocked_group_ids)
        self.assertTrue(preflight.preflight_sha256)
        with self.assertRaisesRegex(ValueError, "snapshot is gewijzigd"):
            self.engine.preflight(
                "machine", selected, expected_snapshot_sha256="stale"
            )

    def test_settings_transaction_is_audited_and_undoable(self) -> None:
        preflight = self.engine.preflight(
            "machine", self.rows,
            expected_snapshot_sha256=self.snapshot.snapshot_sha256,
            visible_rows=self.rows,
        )
        state = BOMHubState(self.project)
        state.begin_settings_transaction(
            "test", preflight,
            lambda: self.project.settings.update({"batch_value": "changed"}),
            user="tester",
        )
        self.assertEqual("changed", self.project.settings["batch_value"])
        state.undo_last(user="tester")
        self.assertNotIn("batch_value", self.project.settings)
        self.assertTrue(any(event.action == "bom.batch.undo" for event in self.project.audit_log))

    def test_entity_transaction_rolls_back_and_revision_compare_is_exact(self) -> None:
        state = BOMHubState(self.project)
        baseline_hash = state.set_revision_baseline(self.model, user="tester")
        self.assertTrue(baseline_hash)
        self.assertEqual(
            {"ongewijzigd"},
            {value for value in state.revision_statuses(self.model).values()},
        )
        first = next(row for row in self.rows if row.mark == "B1")
        preflight = self.engine.preflight(
            "edit", (first,), expected_snapshot_sha256=self.snapshot.snapshot_sha256,
            visible_rows=self.rows,
        )
        state.begin_entity_transaction(
            "edit.phase", preflight, ("P1",),
            lambda: self.project.parts["P1"].properties.update({"phase": "F9"}),
            user="tester",
        )
        changed_model = BOMWorkspaceReadModel(
            build_bom_snapshot(self.project, user="test", classify_if_needed=False),
            self.project,
        )
        self.assertIn("gewijzigd", state.revision_statuses(changed_model).values())
        state.undo_last(user="tester")
        self.assertEqual("F1", self.project.parts["P1"].properties["phase"])

    def test_compound_query_and_full_selection_action_matrix(self) -> None:
        query = BOMSmartQuery(
            query_id="Q1", name="HEA fase 1", family="parts", match="all",
            clauses=(
                BOMQueryClause("profile", "equals", "HEA200"),
                BOMQueryClause("phase", "equals", "F1"),
                BOMQueryClause("length_mm", "greater_than", "3100"),
            ),
        )
        self.assertEqual({"B2"}, {row.mark for row in self.engine.query(query)})
        state = BOMHubState(self.project)
        stored = state.save_smart_query(query.name, query.family, query.clauses, match=query.match)
        self.assertEqual(query.name, state.smart_queries()[0].name)
        state.delete_smart_query(stored.query_id)
        self.assertFalse(state.smart_queries())

        ids = [definition.action_id for definition in ACTION_DEFINITIONS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 75)
        first = self.rows[0]
        availability = {
            definition.action_id: (enabled, reason)
            for definition, enabled, reason in BOMActionMatrix().available(
                (first,), production_ready=False
            )
        }
        self.assertTrue(availability["stock.assign"][0])
        self.assertFalse(availability["purchase.edit"][0])
        self.assertFalse(availability["production.release"][0])

    def test_revision_compare_tracks_rekeyed_fields_and_removed_geometry(self) -> None:
        state = BOMHubState(self.project)
        state.set_revision_baseline(
            self.model,
            bounds_by_entity={
                "P3": {
                    "minimum": {"x": 1.0, "y": 2.0, "z": 3.0},
                    "maximum": {"x": 10.0, "y": 20.0, "z": 30.0},
                }
            },
            user="tester",
        )
        self.project.parts["P1"].material = "S460M"
        self.project.parts["P1"].normalized_material = "S460M"
        self.project.parts["P1"].material_grade = "S460M"
        self.project.parts["P1"].recompute_hashes()
        self.project.parts.pop("P3")
        changed_model = BOMWorkspaceReadModel(
            build_bom_snapshot(self.project, user="test", classify_if_needed=False),
            self.project,
        )
        deltas = state.revision_deltas(changed_model)
        p1 = next(delta for delta in deltas.values() if "P1" in delta.after.get("entity_ids", ()))
        self.assertEqual("gewijzigd", p1.status)
        self.assertIn("material", p1.changed_fields)
        self.assertIn("manufacturing", p1.changed_fields)
        removed = [
            delta for delta in deltas.values()
            if delta.status == "verwijderd" and delta.family == "parts"
        ]
        self.assertEqual(1, len(removed))
        self.assertEqual(["P3"], removed[0].before["entity_ids"])
        bounds = state.removed_revision_bounds(changed_model)
        self.assertEqual("P3", bounds[0]["entity_id"])
        self.assertEqual(30.0, bounds[0]["bounds"]["maximum"]["z"])

    def test_physical_stock_allocation_transaction_and_release_bound_undo(self) -> None:
        stock = StockItem(
            internal_id="STOCK-1", name="HEA voorraad", profile="HEA200",
            material="S355J2", stock_length_mm=6000.0,
            available_quantity=3.0, reserved_quantity=0.0,
        )
        self.project.add_entity(stock)
        first = next(row for row in self.rows if row.mark == "B1")
        options = BOMStockAllocator().options(self.project, (first,), kerf_mm=3.0)
        option = next(value for value in options if value.source_id == "STOCK-1")
        self.assertEqual(((3000.0,),), option.cut_plan)
        preflight = self.engine.preflight(
            "stock", (first,), expected_snapshot_sha256=self.snapshot.snapshot_sha256,
            visible_rows=self.rows,
        )
        state = BOMHubState(self.project)
        execution = state.execute_transaction(
            "stock.assign", preflight,
            lambda: BOMStockAllocator.reserve(
                self.project, state.data, (first,), option, preflight, user="tester"
            ),
            entity_ids=first.entity_ids, user="tester",
        )
        self.assertEqual("passed", execution.result.status)
        self.assertEqual(1.0, self.project.stock_items["STOCK-1"].reserved_quantity)
        assignment = state.data["stock_assignments"][first.group_id]
        self.assertEqual("STOCK-1", assignment["source_id"])
        self.assertTrue(assignment["reservation_id"])
        restored = ProjectModel.from_dict(self.project.to_dict())
        self.assertEqual(
            self.project.stock_items["STOCK-1"].reservation_ids,
            restored.stock_items["STOCK-1"].reservation_ids,
        )
        self.assertEqual(1, restored.stock_items["STOCK-1"].reservation_revision)
        state.record_external_release(
            execution.result.transaction_id, first.entity_ids,
            source="stock-release", user="tester",
        )
        with self.assertRaisesRegex(ValueError, "externe vrijgave"):
            state.undo_last(user="tester")
        stored = next(
            result for result in state.data["batch_results"]
            if result["transaction_id"] == execution.result.transaction_id
        )
        self.assertFalse(stored["undo_available"])

    def test_uniform_transaction_records_failure_and_rolls_back(self) -> None:
        first = self.rows[0]
        preflight = self.engine.preflight(
            "edit", (first,), expected_snapshot_sha256=self.snapshot.snapshot_sha256,
            visible_rows=self.rows,
        )
        state = BOMHubState(self.project)
        original = self.project.parts["P1"].properties["phase"]

        def invalid_mutation() -> None:
            self.project.parts["P1"].properties["phase"] = "BROKEN"
            raise RuntimeError("bewuste testfout")

        with self.assertRaisesRegex(RuntimeError, "bewuste testfout"):
            state.execute_transaction("edit.phase", preflight, invalid_mutation, entity_ids=("P1",))
        self.assertEqual(original, self.project.parts["P1"].properties["phase"])
        self.assertEqual("failed", state.data["batch_results"][-1]["status"])

    def test_procurement_creation_edit_and_release_are_canonical(self) -> None:
        first = next(row for row in self.rows if row.mark == "B1")
        preflight = self.engine.preflight(
            "purchase", (first,), expected_snapshot_sha256=self.snapshot.snapshot_sha256,
            visible_rows=self.rows,
        )
        state = BOMHubState(self.project)
        created = state.execute_transaction(
            "purchase.generate", preflight,
            lambda: BOMProcurementService.generate_needs(
                self.project, state.data, (first,), preflight, user="tester"
            ),
            user="tester",
        )
        purchase_id = created.value[0]
        self.assertIn(purchase_id, self.project.purchased_items)
        self.assertIn(purchase_id, created.result.changed_entity_ids)
        self.assertEqual("draft", state.data["purchase_orders"][0]["status"])

        updated_snapshot = build_bom_snapshot(
            self.project, user="test", classify_if_needed=False
        )
        updated_model = BOMWorkspaceReadModel(updated_snapshot, self.project)
        purchase_rows = updated_model.family_rows("purchase")
        purchase_preflight = BOMScopeEngine(updated_model).preflight(
            "purchase", purchase_rows,
            expected_snapshot_sha256=updated_snapshot.snapshot_sha256,
            visible_rows=purchase_rows,
        )

        def prepare_and_release() -> int:
            BOMProcurementService.edit(
                self.project, (purchase_id,), "supplier", "Staalhandel Test"
            )
            BOMProcurementService.edit(
                self.project, (purchase_id,), "alternative", "S355J2+N"
            )
            return BOMProcurementService.release(
                self.project, state.data, (purchase_id,)
            )

        released = state.execute_transaction(
            "purchase.release", purchase_preflight, prepare_and_release,
            entity_ids=(purchase_id,), user="tester",
        )
        self.assertEqual("released", self.project.purchased_items[purchase_id].purchase_status)
        self.assertEqual(["S355J2+N"], self.project.purchased_items[purchase_id].alternatives)
        self.assertEqual("released", state.data["purchase_orders"][0]["status"])
        state.record_external_release(
            released.result.transaction_id, (purchase_id,), source="purchase", user="tester"
        )
        with self.assertRaisesRegex(ValueError, "externe vrijgave"):
            state.undo_last(user="tester")

    def test_ui_source_contains_complete_production_hub_controls(self) -> None:
        source = (ROOT / "cws_convertor/ui_qt/bom_workspace.py").read_text(encoding="utf-8")
        required = (
            "Selectiemandje", "Opgeslagen selecties", "Revisiebaseline",
            "Per machine opsplitsen", "bomDetailTabs", "BOM-batchbewerking",
            "Productie-export (NC1 / STEP / IFC / DXF / PDF)",
            "detached_viewer_geometry", "export_workspace_state",
            "restore_workspace_state", "Alleen deze occurrence",
            "Machinewijze", "Tekening", "Nesting", "Productie", "Blockers",
            '("export", "Exporteren", self._export_scope)',
            '"Fase": lambda row', '"Levering": lambda row',
        )
        for value in required:
            self.assertIn(value, source)
        module = ast.parse(source)
        columns = ()
        for node in ast.walk(module):
            if isinstance(node, ast.ClassDef) and node.name == "BomWorkspacePanel":
                for statement in node.body:
                    if isinstance(statement, ast.Assign) and any(
                        isinstance(target, ast.Name) and target.id == "COLUMNS"
                        for target in statement.targets
                    ):
                        columns = ast.literal_eval(statement.value)
        self.assertEqual(37, len(columns))
        self.assertTrue({
            "Geometrie", "Materiaal gereed", "Tekening", "Machine gereed",
            "Nesting", "NC-export", "Scribing", "Conflictvrij", "Vrijgegeven",
            "Geproduceerd", "Geleverd",
        }.issubset(columns))


if __name__ == "__main__":
    unittest.main(verbosity=2)
