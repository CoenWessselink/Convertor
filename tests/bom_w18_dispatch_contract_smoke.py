"""Executable dispatcher safety contracts; no navigation is positive execution."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.production_hub import BOMActionMatrix, BOMHubState, BOMScopeEngine
from cws_convertor.bom.workspace import BOMWorkspaceReadModel
from cws_convertor.project import Part, ProjectModel
from cws_convertor.ui_qt.bom_action_dispatch import _dispatch, _drawing_intent
from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel


class DispatchContracts(unittest.TestCase):
    def setUp(self):
        self.project = ProjectModel.new("W18 dispatcher contract")
        for key in ("P1", "P2"):
            part = Part(internal_id=key, part_position="B1", profile="HEA200", normalized_profile="HEA200",
                        material="S355J2", normalized_material="S355J2", material_grade="S355J2",
                        length_mm=1000, quantity_total=1, mass_each_kg=42, surface_area_each_m2=1,
                        classification_status="confirmed", classification_confidence=1,
                        profile_confidence=1, material_confidence=1, geometry_descriptor={"bbox": [1000, 200, 190]})
            part.recompute_hashes()
            self.project.add_entity(part)
        self.workspace = NS(project=self.project, bom_snapshot=build_bom_snapshot(self.project, classify_if_needed=False))
        self.selection = NS(entity_ids=("P1",), primary_entity_id="P1")
        self.context = NS(workspace=self.workspace, selection=self.selection)
        self.panel = NS(_workspace=self.workspace, _selection=self.selection,
                        window=NS(application_context=self.context), action_requested=NS(emit=Mock()))
        self.preflight = NS(snapshot_sha256=self.workspace.bom_snapshot.snapshot_sha256,
                            impact=NS(entity_ids=("P1",)))

    def test_unknown_and_unimplemented_actions_never_become_navigation(self):
        for action in ("unknown.action", "machine.assgin", "production.release", "edit.phase"):
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "Geen afzonderlijke"):
                _dispatch(self.panel, action, "edit", ("P1",), self.preflight)
        self.panel.action_requested.emit.assert_not_called()

    def test_ids_outside_preflight_block_before_any_side_effect(self):
        self.context.selection = NS(entity_ids=("P1", "P2"))
        with self.assertRaisesRegex(ValueError, "buiten de bevestigde"):
            _dispatch(self.panel, "edit", "edit", ("P1", "P2"), self.preflight)
        self.panel.action_requested.emit.assert_not_called()

    def test_changed_active_selection_blocks_before_any_side_effect(self):
        self.context.selection = NS(entity_ids=("P2",))
        with self.assertRaisesRegex(ValueError, "actieve selectie"):
            _dispatch(self.panel, "edit", "edit", ("P1",), self.preflight)
        self.panel.action_requested.emit.assert_not_called()

    def test_explicit_legacy_navigation_remains_prepared(self):
        outcome = _dispatch(self.panel, "edit", "edit", ("P1",), self.preflight)
        self.assertEqual("prepared", outcome.status)
        self.panel.action_requested.emit.assert_called_once_with("edit")

    def test_aggregated_parts_are_exact_for_all_action_handlers(self):
        rows = BOMWorkspaceReadModel(self.workspace.bom_snapshot, self.project).family_rows("parts")
        self.assertEqual(1, len(rows), "fixture must contain an aggregate of two canonical IDs")
        before = deepcopy(self.project.to_dict())
        exact = BomWorkspacePanel._exact_export_rows(self.panel, rows)
        self.assertEqual(("P1",), exact[0].entity_ids)
        self.assertEqual(1, exact[0].quantity)
        self.assertEqual(42, exact[0].total_mass_kg)
        self.assertEqual(before, self.project.to_dict())
        self.panel._selected_rows = lambda: rows
        self.panel._exact_export_rows = lambda selected: BomWorkspacePanel._exact_export_rows(self.panel, selected)
        self.assertEqual(exact, BomWorkspacePanel._action_rows(self.panel))
        self.panel._action_rows = lambda: exact
        self.assertEqual(("P1",), BomWorkspacePanel._selected_part_ids(self.panel))

    def test_group_selection_keeps_both_entities(self):
        self.panel._selection = NS(entity_ids=("P1", "P2"))
        rows = BOMWorkspaceReadModel(self.workspace.bom_snapshot, self.project).family_rows("parts")
        self.assertEqual(rows, BomWorkspacePanel._exact_export_rows(self.panel, rows))

    def test_unknown_occurrence_is_not_silently_dropped(self):
        self.panel._selection = NS(entity_ids=("P1", "deleted"))
        rows = BOMWorkspaceReadModel(self.workspace.bom_snapshot, self.project).family_rows("parts")
        with self.assertRaisesRegex(ValueError, "onbekende canonieke"):
            BomWorkspacePanel._exact_export_rows(self.panel, rows)

    def _transaction_binding(self):
        self.panel._hub_state = BOMHubState(self.project)
        binding = BomWorkspacePanel._capture_action_binding(self.panel)
        model = BOMWorkspaceReadModel(self.workspace.bom_snapshot, self.project)
        rows = BomWorkspacePanel._exact_export_rows(self.panel, model.family_rows("parts"))
        preflight = BOMScopeEngine(model).preflight("edit", rows,
            expected_snapshot_sha256=self.workspace.bom_snapshot.snapshot_sha256)
        self.panel._preflight_action_bindings = {preflight.preflight_sha256: binding}
        self.panel._validate_action_binding = lambda current: BomWorkspacePanel._validate_action_binding(self.panel, current)
        return preflight

    def test_project_edit_during_modal_blocks_transaction(self):
        preflight = self._transaction_binding()
        self.project.parts["P2"].properties["phase"] = "changed while dialog open"
        mutate = Mock()
        with self.assertRaisesRegex(ValueError, "Projectinhoud gewijzigd"):
            BomWorkspacePanel._execute_bom_transaction(self.panel, "edit.phase", preflight, mutate, entity_ids=("P1",))
        mutate.assert_not_called()
        self.assertNotIn("phase", self.project.parts["P1"].properties)

    def test_selection_edit_during_modal_blocks_transaction(self):
        preflight = self._transaction_binding()
        self.panel._selection = NS(entity_ids=("P2",))
        mutate = Mock()
        with self.assertRaisesRegex(ValueError, "Selectie gewijzigd"):
            BomWorkspacePanel._execute_bom_transaction(self.panel, "edit.phase", preflight, mutate, entity_ids=("P1",))
        mutate.assert_not_called()

    def test_unchanged_transaction_mutates_only_requested_entity(self):
        preflight = self._transaction_binding()
        before = asdict(self.project.parts["P2"])
        def mutate():
            self.project.parts["P1"].properties["phase"] = "W18"
            return 1
        execution = BomWorkspacePanel._execute_bom_transaction(self.panel, "edit.phase", preflight, mutate, entity_ids=("P1",))
        self.assertEqual("passed", execution.result.status)
        self.assertEqual(("P1",), execution.result.changed_entity_ids)
        self.assertTrue(execution.result.undo_available)
        self.assertEqual(before, asdict(self.project.parts["P2"]))

    def test_withdraw_requires_explicit_release_for_every_occurrence(self):
        def availability():
            rows = BOMWorkspaceReadModel(self.workspace.bom_snapshot, self.project).family_rows("parts")
            return rows[0].release_status, next(enabled for item, enabled, _reason in
                BOMActionMatrix().available(rows, production_ready=True) if item.action_id == "production.withdraw")
        self.project.parts["P1"].properties["release_status"] = "released"
        self.assertEqual(("Review", False), availability(), "an unreleased sibling must not disappear")
        self.project.parts["P2"].properties["review_status"] = "approved"
        self.assertEqual(("Review", False), availability(), "review approval is not production release")
        self.project.parts["P2"].properties["release_status"] = "released"
        self.assertEqual(("Vrijgegeven", True), availability())
        for part in self.project.parts.values():
            part.properties["release_status"] = "withdrawn"
        self.assertEqual(("Ingetrokken", False), availability())

    def test_drawing_views_targets_the_existing_view_controls(self):
        front, format_control, scale_control = Mock(), Mock(), Mock()
        page = NS(_entity_id="P1", set_context=Mock(), view_buttons={"front": front},
                  format=format_control, scale=scale_control)
        router = NS(open_workspace=Mock(return_value=True))
        self.panel.window.pdf_page = page
        self.panel.window.workspace_router = router
        outcome = _drawing_intent(self.panel, "drawing.views", ("P1",), self.preflight)
        self.assertEqual("prepared", outcome.status)
        front.setFocus.assert_called_once()
        format_control.setFocus.assert_not_called()
        router.open_workspace.assert_called_once_with("pdf_review")


if __name__ == "__main__":
    unittest.main(verbosity=2)
