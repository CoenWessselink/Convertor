"""Regression proof for the joined recognition/BOM branch; synthetic fixtures."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.material_gate import part_material_blockers
from cws_convertor.bom.workspace import BOMScope, BOMWorkspaceReadModel
from cws_convertor.project import Part, ProjectModel
from cws_convertor.project.model import SourceFileRecord


def material_part() -> Part:
    part = Part(internal_id="material-1", name="B1", part_position="B1",
                category="make_part", profile="HEA140", normalized_profile="HEA140",
                material="S355JR", material_grade="S355JR", normalized_material="S355JR",
                material_confidence=1.0, profile_confidence=1.0,
                classification_status="confirmed", classification_confidence=1.0,
                length_mm=1000.0, geometry_descriptor={"bbox": [1000, 140, 133]})
    part.recompute_hashes()
    return part


class BomMaterialIntegrationTests(unittest.TestCase):
    def model(self, part: Part):
        project = ProjectModel.new("BOM material integration")
        part.recompute_hashes()
        project.add_entity(part)
        # Explicitly open the independent source gate, so it cannot hide a
        # missing per-part release/roundtrip check. This is NOT native proof.
        source = SourceFileRecord("fixture", "fixture.nc1", "DSTV", "a" * 64, 1,
                                  semantic_import_complete=True, production_export_allowed=True)
        project.sources[source.source_id] = source
        snapshot = build_bom_snapshot(project, classify_if_needed=False)
        model = BOMWorkspaceReadModel(snapshot, project)
        row, = model.rows(BOMScope.create(family="parts"))
        return snapshot, model, row

    def test_exact_material_is_ready_without_mutating_part(self):
        part = material_part()
        before = deepcopy(asdict(part))
        self.assertEqual((), part_material_blockers(part))
        self.assertEqual(before, asdict(part))
        _, _, row = self.model(part)
        self.assertEqual("Gereed", row.material_status)

    def test_unknown_material_never_turns_green_from_confidence(self):
        part = material_part()
        part.material = part.material_grade = part.normalized_material = "UNOBTAINIUM"
        snapshot, _, row = self.model(part)
        self.assertTrue(row.blocked)
        self.assertEqual("Geblokkeerd", row.material_status)
        self.assertFalse(snapshot.validation.production_ready)

    def test_missing_grade_cannot_be_masked_by_normalized_material(self):
        part = material_part()
        part.material_grade = ""
        _, _, row = self.model(part)
        self.assertTrue(row.blocked)
        self.assertEqual("Geblokkeerd", row.material_status)

    def test_family_and_conflicting_raw_grades_remain_blocked(self):
        for material in ("S355", "S235JR"):
            with self.subTest(material=material):
                part = material_part()
                part.material = material
                _, _, row = self.model(part)
                self.assertTrue(row.blocked)
                self.assertEqual("Geblokkeerd", row.material_status)

    def test_stale_workbench_material_is_not_shown_as_ready(self):
        part = material_part()
        part.workbench = {"current_revision": {"production_properties": {
            "material": "S235JR", "material_grade": "S235JR"}}}
        self.assertTrue(part_material_blockers(part))

    def test_invalid_confidence_never_means_ready(self):
        for confidence in (float("nan"), float("inf"), -1, 1.1, None, True, 0.8):
            with self.subTest(confidence=confidence):
                part = material_part()
                part.material_confidence = confidence
                self.assertTrue(part_material_blockers(part))

    def test_balanced_bom_and_approved_source_do_not_bypass_part_release(self):
        snapshot, model, row = self.model(material_part())
        self.assertTrue(snapshot.validation.passed)
        self.assertFalse(snapshot.validation.production_ready)
        release, = [a for a in model.actions((row,)) if a.action == "release"]
        self.assertFalse(release.enabled)
        self.assertTrue(any("vrijgavebewijs" in m for m in snapshot.validation.messages))


if __name__ == "__main__":
    unittest.main(verbosity=2)
