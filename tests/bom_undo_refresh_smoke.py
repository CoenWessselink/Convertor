"""BOM undo must ignore derived cache refreshes, never business changes."""
from __future__ import annotations
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cws_convertor.project import Part, ProjectModel
from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.production_hub import BOMHubState, BOMScopeEngine
from cws_convertor.bom.workspace import BOMScope, BOMWorkspaceReadModel

class UndoRefreshTests(unittest.TestCase):
    def setUp(self):
        self.project = ProjectModel.new("Undo refresh regression")
        part = Part(internal_id="P1", name="P1", part_position="P1", category="make_part",
                    profile="HEA200", normalized_profile="HEA200", material="S355J2",
                    material_grade="S355J2", normalized_material="S355J2", length_mm=3000,
                    classification_status="confirmed", classification_confidence=1.0,
                    profile_confidence=1.0, material_confidence=1.0,
                    properties={"phase": "F1"}, geometry_descriptor={"bbox": [3000, 200, 190]})
        part.recompute_hashes()
        self.project.add_entity(part)
        self.refresh("2026-01-01T00:00:00Z")
        self.state = BOMHubState(self.project)
        rows = self.model.rows(BOMScope.create(family="parts"))
        self.preflight = BOMScopeEngine(self.model).preflight(
            "edit", rows, expected_snapshot_sha256=self.snapshot.snapshot_sha256,
            visible_rows=rows)

    def refresh(self, timestamp):
        with patch("cws_convertor.bom.engine.utc_now_iso", return_value=timestamp):
            self.snapshot = build_bom_snapshot(self.project, classify_if_needed=False)
        self.model = BOMWorkspaceReadModel(self.snapshot, self.project)

    def edit(self):
        self.state.begin_entity_transaction("edit.phase", self.preflight, ("P1",),
            lambda: self.project.parts["P1"].properties.update(phase="F9"), user="tester")

    def test_refresh_across_clock_boundary_does_not_block_undo(self):
        self.edit()
        self.refresh("2026-01-02T00:00:00Z")
        self.state.undo_last(user="tester")
        self.assertEqual("F1", self.project.parts["P1"].properties["phase"])
        self.assertNotIn("bom", self.project.settings)

    def test_repeated_refresh_and_reopen_preserve_undo(self):
        self.edit()
        for day in (2, 3, 4):
            self.refresh(f"2026-01-0{day}T00:00:00Z")
        self.project = ProjectModel.from_dict(self.project.to_dict())
        BOMHubState(self.project).undo_last(user="tester")
        self.assertEqual("F1", self.project.parts["P1"].properties["phase"])

    def test_real_entity_edit_still_blocks_undo(self):
        self.edit()
        self.project.parts["P1"].length_mm = 5000
        self.project.parts["P1"].recompute_hashes()
        self.refresh("2026-01-02T00:00:00Z")
        with self.assertRaisesRegex(ValueError, "projectinhoud"):
            self.state.undo_last(user="tester")
        self.assertEqual(5000, self.project.parts["P1"].length_mm)
        self.assertEqual("F9", self.project.parts["P1"].properties["phase"])

    def test_real_settings_edit_still_blocks_undo(self):
        self.edit()
        self.project.settings["important_production_setting"] = "changed"
        with self.assertRaisesRegex(ValueError, "projectinhoud"):
            self.state.undo_last(user="tester")

    def test_external_release_still_blocks_undo(self):
        self.edit()
        self.state.record_external_release("R1", ("P1",), source="test")
        with self.assertRaisesRegex(ValueError, "externe vrijgave"):
            self.state.undo_last(user="tester")

    def test_failed_transaction_restores_business_state(self):
        def fail():
            self.project.parts["P1"].properties["phase"] = "bad"
            raise ValueError("forced failure")
        with self.assertRaisesRegex(ValueError, "forced failure"):
            self.state.begin_entity_transaction("edit.phase", self.preflight, ("P1",), fail, user="tester")
        self.assertEqual("F1", self.project.parts["P1"].properties["phase"])
        self.assertFalse(self.state.data["undo"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
