"""Deterministic regressions: derived BOM cache is not a business edit."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.production_hub import BOMHubState, BOMScopeEngine, _transaction_payload
from cws_convertor.bom.workspace import BOMScope, BOMWorkspaceReadModel
from cws_convertor.project import Part, ProjectModel
from cws_convertor.project.model import stable_sha256


class BomUndoRefreshTests(unittest.TestCase):
    def setUp(self):
        self.project = ProjectModel.new("Undo cache regression")
        part = Part(internal_id="P1", name="B1", part_position="B1", category="make_part",
                    profile="HEA200", normalized_profile="HEA200", material="S355J2",
                    material_grade="S355J2", normalized_material="S355J2",
                    length_mm=3000.0, quantity_total=1, mass_each_kg=100.0,
                    material_confidence=1.0, profile_confidence=1.0,
                    classification_status="confirmed", classification_confidence=1.0,
                    geometry_descriptor={"bbox": [3000.0, 200.0, 190.0]},
                    properties={"phase": "F1"})
        part.recompute_hashes()
        self.project.add_entity(part)
        self.state = BOMHubState(self.project)
        self.snapshot = self.refresh("2026-09-08T00:00:01+00:00")

    def refresh(self, timestamp):
        with patch("cws_convertor.bom.engine.utc_now_iso", return_value=timestamp):
            return build_bom_snapshot(self.project, user="test", classify_if_needed=False)

    def edit(self, phase="F9"):
        model = BOMWorkspaceReadModel(self.snapshot, self.project)
        rows = model.rows(BOMScope.create(family="parts"))
        preflight = BOMScopeEngine(model).preflight(
            "edit", rows, expected_snapshot_sha256=self.snapshot.snapshot_sha256, visible_rows=rows)
        self.state.begin_entity_transaction(
            "edit.phase", preflight, ("P1",),
            lambda: self.project.parts["P1"].properties.update({"phase": phase}), user="test")

    def test_undo_after_refresh_at_a_different_second(self):
        self.edit()
        self.refresh("2026-09-08T00:00:02+00:00")
        self.state.undo_last(user="test")
        self.assertEqual("F1", self.project.parts["P1"].properties["phase"])
        self.assertNotIn("bom", self.project.settings)

    def test_undo_survives_refresh_and_persistent_reload(self):
        self.edit()
        self.refresh("2026-09-08T00:00:03+00:00")
        restored = ProjectModel.from_dict(json.loads(json.dumps(self.project.to_dict())))
        BOMHubState(restored).undo_last(user="test")
        self.assertEqual("F1", restored.parts["P1"].properties["phase"])

    def test_later_business_edit_still_blocks_undo(self):
        self.edit()
        self.refresh("2026-09-08T00:00:04+00:00")
        self.project.parts["P1"].properties["delivery"] = "real-later-edit"
        before = self.project.to_dict()
        with self.assertRaisesRegex(ValueError, "projectinhoud"):
            self.state.undo_last(user="test")
        self.assertEqual(before, self.project.to_dict())

    def test_unknown_bom_setting_is_not_hidden_by_cache_exclusion(self):
        self.edit()
        self.project.settings["bom"]["operator_setting"] = "real-setting"
        with self.assertRaisesRegex(ValueError, "projectinhoud"):
            self.state.undo_last(user="test")

    def test_external_release_still_blocks_undo(self):
        self.edit()
        self.refresh("2026-09-08T00:00:05+00:00")
        self.state.record_external_release("synthetic-release", ("P1",), source="test", user="test")
        with self.assertRaisesRegex(ValueError, "externe vrijgave"):
            self.state.undo_last(user="test")

    def test_repeated_undo_after_refresh_does_not_restore_stale_cache(self):
        self.edit("F2")
        self.snapshot = self.refresh("2026-09-08T00:00:06+00:00")
        self.edit("F3")
        self.refresh("2026-09-08T00:00:07+00:00")
        self.state.undo_last(user="test")
        self.assertEqual("F2", self.project.parts["P1"].properties["phase"])
        self.refresh("2026-09-08T00:00:08+00:00")
        self.state.undo_last(user="test")
        self.assertEqual("F1", self.project.parts["P1"].properties["phase"])

    def test_legacy_undo_record_retains_its_original_strict_hash(self):
        self.edit()
        record = self.state.data["undo"][-1]
        record["undo_schema"] = "cws-bom-persistent-undo-2.0"
        record["after_content_sha256"] = stable_sha256(
            _transaction_payload(self.project, include_bom_cache=True))
        self.state.undo_last(user="test")
        self.assertEqual("F1", self.project.parts["P1"].properties["phase"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
