from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.production_hub import BOMHubState, BOMScopeEngine
from cws_convertor.bom.workspace import BOMScope, BOMWorkspaceReadModel
from cws_convertor.project import Part, ProjectModel


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
