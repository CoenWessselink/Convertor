"""Transactional/attribution tests; mocked rebuilds are not native CAD proof."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.model import Part, ProjectModel, SourceIdentity, ValidationIssue
from cws_convertor.project.production_normalization import (
    is_exact_simple_extrusion, prepare_exact_imported_part, prepare_project_exact_parts,
)
from cws_convertor.project.workbench import undo_part_workbench, redo_part_workbench, validate_workbench_state

TARGET = "cws_convertor.project.production_normalization"


def source_part() -> Part:
    part = Part(
        internal_id="automatic-extrusion", profile="HEA200", profile_type="IFCBEAM",
        material="S235JR", material_grade="S235JR", length_mm=500.0,
        source_identity=SourceIdentity(source_format="IFC", source_file_id="ifc-source", source_entity_id="42", source_sha256="a" * 64),
        geometry_descriptor={
            "status": "semantic_source_geometry", "source_semantics_preserved": True,
            "source_geometry_hash": "b" * 64, "item_count": 1,
            "primitive_counts": {"IFCEXTRUDEDAREASOLID": 1},
        },
        properties={"semantic_import": {
            "identity_exact": True, "placement_exact": True,
            "property_mapping_exact": True, "source_geometry_semantics_preserved": True,
        }},
    )
    part.recompute_hashes()
    return part


class ProductionNormalizationSafetySmoke(unittest.TestCase):
    def assert_blocked_proposal(self, part: Part) -> None:
        self.assertEqual(part.classification_status, "review_required")
        self.assertEqual(part.status, "review_required")
        self.assertFalse(part.nc1_eligible)
        self.assertFalse(part.properties["square_end_cuts_confirmed"])
        self.assertFalse(part.properties["production_frame_confirmed"])
        self.assertFalse(part.properties["common_cut_allowed"])
        self.assertEqual(part.workbench["current_revision"]["reviewed_by"], "")
        validate_workbench_state(part, part.workbench)
        part.validate_hashes()

    def test_every_semantic_flag_is_explicit_true(self) -> None:
        for flag in source_part().properties["semantic_import"]:
            for value in (None, False, "true", 1):
                with self.subTest(flag=flag, value=value):
                    part = source_part()
                    if value is None:
                        part.properties["semantic_import"].pop(flag)
                    else:
                        part.properties["semantic_import"][flag] = value
                    before = asdict(part)
                    self.assertFalse(prepare_exact_imported_part(part))
                    self.assertEqual(asdict(part), before)

    def test_missing_source_preservation_or_identity_is_not_exact(self) -> None:
        part = source_part()
        self.assertTrue(is_exact_simple_extrusion(part))
        part.geometry_descriptor.pop("source_semantics_preserved")
        self.assertFalse(is_exact_simple_extrusion(part))
        part = source_part()
        part.source_identity.source_sha256 = "invalid"
        self.assertFalse(is_exact_simple_extrusion(part))

    def test_conflicting_material_fields_never_mask_each_other(self) -> None:
        for field in ("material", "material_grade", "normalized_material"):
            part = source_part()
            setattr(part, field, "S355JR")
            before = asdict(part)
            self.assertFalse(prepare_exact_imported_part(part))
            self.assertEqual(asdict(part), before)
        part = source_part()
        part.validation_issues.append(ValidationIssue("MATERIAL", "conflict", severity="error", blocking=True))
        self.assertFalse(is_exact_simple_extrusion(part))

    def test_malformed_primitive_counts_and_nonfinite_lengths_are_rejected(self) -> None:
        for value in ("1", 1.1, True, -1, None):
            part = source_part()
            part.geometry_descriptor["primitive_counts"]["IFCEXTRUDEDAREASOLID"] = value
            self.assertFalse(is_exact_simple_extrusion(part))
        for value in (float("nan"), float("inf"), True, -1, "bad"):
            part = source_part()
            part.length_mm = value
            self.assertFalse(is_exact_simple_extrusion(part))

    def test_missing_native_dependency_commits_only_a_blocked_editable_proposal(self) -> None:
        part = source_part()
        identity = deepcopy(part.source_identity)
        with patch(f"{TARGET}._native_rebuild", side_effect=ModuleNotFoundError("cadquery absent")):
            self.assertTrue(prepare_exact_imported_part(part, user="requester"))
        self.assert_blocked_proposal(part)
        self.assertEqual(part.source_identity, identity)
        evidence = part.properties["automatic_production_normalization"]
        self.assertEqual(evidence["status"], "dependency_unavailable")
        self.assertEqual(evidence["requested_by"], "requester")
        self.assertFalse(part.workbench.get("canonical_rebuild"))

    def test_rebuild_failure_cannot_mutate_the_proposal_or_source_values(self) -> None:
        def fail(candidate: Part) -> None:
            candidate.material = "CORRUPTED"
            candidate.nc1_eligible = True
            raise RuntimeError("native rebuild failed")
        part = source_part()
        with patch(f"{TARGET}._native_rebuild", side_effect=fail):
            self.assertTrue(prepare_exact_imported_part(part))
        self.assertEqual(part.material, "S235JR")
        self.assert_blocked_proposal(part)
        self.assertEqual(part.properties["automatic_production_normalization"]["status"], "blocked")
        part = source_part()
        with patch(f"{TARGET}._native_rebuild", return_value=SimpleNamespace(shape=None, report={"status": "passed"})):
            self.assertTrue(prepare_exact_imported_part(part))
        self.assert_blocked_proposal(part)
        self.assertEqual(part.properties["automatic_production_normalization"]["status"], "blocked")

    def test_failed_workbench_transaction_leaves_part_and_project_unchanged(self) -> None:
        project = ProjectModel.new("rollback")
        part = source_part()
        project.parts[part.internal_id] = part
        before = asdict(part)
        with patch(f"{TARGET}.update_part_workbench", side_effect=RuntimeError("editor failure")):
            self.assertFalse(prepare_exact_imported_part(part))
            report = prepare_project_exact_parts(project)
        self.assertEqual(asdict(part), before)
        self.assertEqual(report["prepared"], 0)
        self.assertEqual(report["profile_types_updated"], 0)

    def test_machine_success_never_produces_a_human_signature(self) -> None:
        def success(candidate: Part) -> SimpleNamespace:
            return SimpleNamespace(shape=object(), report={
                "status": "passed", "part_id": candidate.internal_id,
                "source_geometry_hash": candidate.workbench["source_geometry"]["source_geometry_hash"],
                "manufacturing_hash": candidate.manufacturing_hash,
                "canonical_signature": "c" * 64,
            })
        part = source_part()
        with patch(f"{TARGET}._native_rebuild", side_effect=success):
            self.assertTrue(prepare_exact_imported_part(part, user="Joanne"))
        self.assert_blocked_proposal(part)
        self.assertEqual(part.properties["automatic_production_normalization"]["status"], "passed")
        self.assertEqual(part.workbench["canonical_rebuild"]["recorded_by"], "system:deterministic-ifc-extrusion")
        for provenance in part.field_provenance.values():
            self.assertEqual(provenance.confirmed_by, "")
            self.assertNotEqual(provenance.method, "user")
        for command in part.workbench["commands"]:
            self.assertEqual(command["action"], "automatic_prepare")
            for provenance in command["after_revision"]["field_provenance"].values():
                self.assertEqual(provenance["confirmed_by"], "")
                self.assertEqual(provenance["method"], "deterministic_ifc_extrusion")

    def test_automatic_command_history_remains_undoable_without_forged_signature(self) -> None:
        part = source_part()
        with patch(f"{TARGET}._native_rebuild", side_effect=ImportError("no CAD")):
            self.assertTrue(prepare_exact_imported_part(part))
        project = ProjectModel.new("undo")
        project.parts[part.internal_id] = part
        undo_part_workbench(project, part.internal_id, user="tester")
        redo_part_workbench(project, part.internal_id, user="tester")
        self.assert_blocked_proposal(part)
        before = asdict(part)
        self.assertFalse(prepare_exact_imported_part(part))
        self.assertEqual(asdict(part), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
