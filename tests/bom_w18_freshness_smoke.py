"""Canonical snapshot freshness and all shipping QAction rejection boundaries."""
from __future__ import annotations
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.freshness import bom_source_content_sha256, require_current_bom_snapshot
from cws_convertor.bom.production_hub import ACTION_DEFINITIONS, BOMHubState, BOMScopeEngine
from cws_convertor.bom.workspace import BOMScope, BOMWorkspaceReadModel, scoped_bom_snapshot
from cws_convertor.project import Part, ProjectModel, PurchasedItem, Remnant, StockItem


def fixture():
    project = ProjectModel.new("Explicit synthetic stale BOM acceptance")
    for key, length in (("P1", 3000), ("P2", 2800)):
        part = Part(internal_id=key, part_position=key, name=key, length_mm=length,
            profile="HEA200", normalized_profile="HEA200", material="S355J2", normalized_material="S355J2",
            material_grade="S355J2", quantity_total=1, mass_each_kg=80, surface_area_each_m2=1.5,
            classification_status="confirmed", classification_confidence=1, profile_confidence=1, material_confidence=1)
        part.recompute_hashes()
        project.add_entity(part)
    project.add_entity(Remnant(internal_id="R1", profile="HEA200", material="S355J2", grade="S355J2",
                               remaining_length_mm=3200, status="available"))
    project.add_entity(StockItem(internal_id="S1", profile="HEA200", material="S355J2", grade="S355J2",
                                 stock_length_mm=6000, available_quantity=2, status="available"))
    return project


class FreshnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6 import QtWidgets
        cls.QtWidgets = QtWidgets
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(BomWorkspacePanel, "_restore_layout", lambda self: None))
        self.messages = []
        def modal(*args, **kwargs):
            self.messages.append(str(args[2] if len(args) > 2 else args))
            return self.QtWidgets.QMessageBox.StandardButton.Yes
        for name in ("question", "warning", "information"):
            self.stack.enter_context(patch.object(self.QtWidgets.QMessageBox, name, modal))
        self.project = fixture()
        self.snapshot = build_bom_snapshot(self.project, classify_if_needed=False)
        self.workspace = SimpleNamespace(project=self.project, bom_snapshot=self.snapshot,
            session=SimpleNamespace(project=self.project, dirty=False))
        self.selection = SimpleNamespace(entity_ids=("P1",), primary_entity_id="P1")
        self.host = self.QtWidgets.QMainWindow()
        self.host.project_page = None
        self.host.application_context = SimpleNamespace(workspace=self.workspace, selection=self.selection,
            request_selection=lambda *args, **kw: None, clear_selection=lambda **kw: None)
        self.host.workspace_router = SimpleNamespace(open_workspace=lambda route: False)
        self.panel = BomWorkspacePanel(self.host)
        self.host.setCentralWidget(self.panel)
        self.panel.set_context(self.workspace, self.selection)
        self.app.processEvents()

    def tearDown(self):
        self.host.close()
        self.host.deleteLater()
        self.app.processEvents()
        self.stack.close()

    def test_canonical_fingerprint_excludes_only_derived_and_audit_state(self):
        original = deepcopy(self.project.to_dict())
        expected = bom_source_content_sha256(self.project)
        self.assertEqual(original, self.project.to_dict(), "Fingerprint is read-only")
        state = BOMHubState(self.project)
        state.data["history"].append({"view": "changed"})
        state.data["batch_results"].append({"status": "prepared"})
        state.data["scoped_requests"] = [{"action": "inspect.hashes"}]
        state.data["basket_entity_ids"] = ["P1"]
        self.project.audit("audit-noise")
        self.project.settings["bom"]["generated_at"] = "different"
        self.assertEqual(expected, bom_source_content_sha256(self.project))
        require_current_bom_snapshot(self.snapshot, self.project)
        rebuilt = build_bom_snapshot(self.project, classify_if_needed=False)
        self.assertEqual(self.snapshot.snapshot_sha256, rebuilt.snapshot_sha256)
        for key, value in (("stock_assignments", {"P1": {"quantity": 1}}),
                           ("purchase_orders", [{"quantity": 2}]), ("external_releases", [{"release": "x"}]),
                           ("unknown_business_setting", True)):
            with self.subTest(key=key):
                previous = deepcopy(state.data.get(key))
                state.data[key] = value
                self.assertNotEqual(expected, bom_source_content_sha256(self.project))
                if previous is None: state.data.pop(key)
                else: state.data[key] = previous

    def test_existing_bom_configuration_survives_cache_refresh(self):
        self.project.settings["bom"]["user_option"] = {"precision": 3}
        snapshot = build_bom_snapshot(self.project, classify_if_needed=False)
        self.assertEqual({"precision": 3}, self.project.settings["bom"]["user_option"])
        require_current_bom_snapshot(snapshot, self.project)

    def test_exact_and_general_scoped_snapshots_inherit_original_source_authority(self):
        from cws_convertor.bom.review_export import _part_snapshot
        exact = _part_snapshot(self.snapshot, self.project, ("P1",))
        general = scoped_bom_snapshot(self.snapshot, project=self.project,
            scope=BOMScope.create(family="parts", entity_ids=("P1",)), strict_entities=True)
        for snapshot in (exact, general):
            self.assertEqual(self.snapshot.summary["source_content_sha256"], snapshot.summary["source_content_sha256"])
            require_current_bom_snapshot(snapshot, self.project)
        self.project.parts["P1"].length_mm = 5000
        self.project.parts["P1"].recompute_hashes()
        for snapshot in (self.snapshot, exact, general):
            with self.assertRaisesRegex(ValueError, "Projectinhoud"):
                require_current_bom_snapshot(snapshot, self.project)
            # Recreating a read model with an old snapshot cannot bless it.
            model = BOMWorkspaceReadModel(snapshot, self.project)
            with self.assertRaisesRegex(ValueError, "Projectinhoud"):
                BOMScopeEngine(model).preflight("inspect", model.family_rows("parts"),
                    expected_snapshot_sha256=snapshot.snapshot_sha256, allow_blocked_review_export=True)

    def test_all_87_shipping_qactions_reject_stale_missing_and_corrupt_snapshot_before_dispatch(self):
        self.panel._populate_action_matrix()
        actions = self.panel._matrix_qactions
        self.assertEqual({item.action_id for item in ACTION_DEFINITIONS}, set(actions))
        self.assertEqual(87, len(actions))
        source = self.snapshot.summary["source_content_sha256"]
        for mode in ("stale", "missing_binding", "corrupt_snapshot"):
            with self.subTest(mode=mode):
                if mode == "stale": self.project.parts["P1"].properties["new_input"] = True
                elif mode == "missing_binding": self.snapshot.summary.pop("source_content_sha256")
                else: self.snapshot.part_bom[0].length_mm += 1
                before = deepcopy(self.project.to_dict())
                with patch.object(self.panel, "_execute_matrix_action_bound", side_effect=AssertionError("Executor entered for invalid snapshot")) as executor:
                    count = len(self.messages)
                    for action in actions.values():
                        # Emulate a QAction whose enabled state was cached before
                        # a project change; no action-specific gate is bypassed
                        # to claim positive execution or production authority.
                        action.setEnabled(True)
                        action.trigger()
                    self.assertFalse(executor.called)
                    self.assertEqual(87, len(self.messages) - count)
                self.assertEqual(before, self.project.to_dict(), "No entity, settings, audit or result mutation")
                print("BOM_W18_FRESHNESS_" + mode.upper() + " = 87/87 PASS", flush=True)
                self.project.parts["P1"].properties.pop("new_input", None)
                self.snapshot.summary["source_content_sha256"] = source
                if mode == "corrupt_snapshot": self.snapshot.part_bom[0].length_mm -= 1

    def test_stale_stock_3000_to_5000_cannot_reserve_3200_remnant(self):
        self.panel._populate_action_matrix()
        action = self.panel._matrix_qactions["stock.assign"]
        self.assertTrue(action.isEnabled())
        self.assertEqual([3000], [row.length_mm for row in self.panel._action_rows()])
        self.project.parts["P1"].length_mm = 5000
        self.project.parts["P1"].recompute_hashes()
        before = deepcopy(self.project.to_dict())
        action.trigger()
        self.app.processEvents()
        self.assertEqual(before, self.project.to_dict())
        self.assertEqual({}, self.panel._hub_state.data["stock_assignments"])
        self.assertFalse(self.panel._hub_state.data["batch_results"])
        self.assertIn("Projectinhoud", self.messages[-1])
        # An explicit real rebuild restores execution against 5000 mm input.
        self.panel.refresh_button.click()
        self.app.processEvents()
        self.panel._populate_action_matrix()
        self.assertEqual([5000], [row.length_mm for row in self.panel._action_rows()])
        self.panel._matrix_qactions["stock.assign"].trigger()
        self.app.processEvents()
        assignment = next(iter(self.panel._hub_state.data["stock_assignments"].values()))
        self.assertEqual(5000, assignment["allocated_length_mm"])
        self.assertEqual("S1", assignment["source_id"])
        self.assertEqual("available", self.project.remnants["R1"].status)
        self.assertEqual("passed", self.panel._hub_state.data["batch_results"][-1]["status"])

    def test_menu_eligibility_uses_exact_occurrences_inside_an_aggregate(self):
        second = self.project.parts["P2"]
        second.length_mm = self.project.parts["P1"].length_mm
        second.recompute_hashes()
        self.project.settings["machine_capability_reports"] = {"P1": {"M1": {
            "part_id": "P1", "machine_id": "M1", "manufacturing_hash": self.project.parts["P1"].manufacturing_hash,
            "production_ready": True, "blocking_codes": [], "machine_transfer_allowed": False,
        }}}
        self.panel.refresh_button.click()
        raw = self.panel._selected_rows()
        self.assertEqual({"P1", "P2"}, {key for row in raw for key in row.entity_ids})
        exact = self.panel._action_rows()
        self.assertEqual({"P1"}, {key for row in exact for key in row.entity_ids})
        self.assertEqual("Voorstel gereed", exact[0].machine_status)
        self.panel._populate_action_matrix()
        self.assertTrue(self.panel._matrix_qactions["machine.auto_accept"].isEnabled())
        self.assertFalse(self.panel._hub_state.data["batch_results"], "Menu eligibility is not execution evidence")

    def test_mixed_external_selection_cannot_silently_drop_another_family(self):
        self.project.add_entity(PurchasedItem(internal_id="BUY1", name="BUY1", article_number="BUY1", quantity=2))
        self.panel.refresh_button.click()
        self.panel._populate_action_matrix()
        action = self.panel._matrix_qactions["edit.mark"]
        self.assertTrue(action.isEnabled())
        mixed = SimpleNamespace(entity_ids=("P1", "BUY1"), primary_entity_id="P1")
        self.host.application_context.selection = mixed
        self.panel.set_context(self.workspace, mixed)
        before = deepcopy(self.project.to_dict())
        action.trigger()  # A previously enabled native action still cannot narrow this new intent.
        self.app.processEvents()
        self.assertEqual(before, self.project.to_dict())
        self.assertTrue(any("Niet alle geselecteerde objecten" in message for message in self.messages))
        self.assertFalse(self.panel._hub_state.data["batch_results"])
        # A deliberate new exact selection remains usable.
        self.host.application_context.selection = self.selection
        self.panel.set_context(self.workspace, self.selection)
        self.assertEqual({"P1"}, {key for row in self.panel._action_rows() for key in row.entity_ids})

    def test_hidden_selected_occurrence_requires_explicit_new_scope(self):
        mixed = SimpleNamespace(entity_ids=("P1", "P2"), primary_entity_id="P1")
        self.panel.set_context(self.workspace, mixed)
        only_first = tuple(row for row in self.panel._selected_rows() if "P1" in row.entity_ids)
        with self.assertRaisesRegex(ValueError, "Niet alle geselecteerde objecten"):
            self.panel._exact_export_rows(only_first)


if __name__ == "__main__":
    unittest.main(verbosity=2)
