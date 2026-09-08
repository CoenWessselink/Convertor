"""Pure fail-closed material/model release checks (no native CAD mocks)."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.production_export import ProjectProductionExportEngine
from cws_convertor.production_export.readiness import ReadinessGate, project_fingerprint_conflicts
from cws_convertor.project.classification import compute_production_identity
from cws_convertor.project.model import Part, ValidationIssue


def ready_part() -> Part:
    """Synthetic gate fixture; it is not CAD/roundtrip acceptance evidence."""
    part = Part(
        internal_id="gate-part", category="make_part", profile="HEA140",
        material="S355JR", material_grade="S355JR", length_mm=500,
        normalized_profile="HEA140", normalized_material="S355JR",
        classification_status="confirmed", classification_confidence=1.0,
        material_confidence=1.0, profile_confidence=1.0,
        geometry_descriptor={"type": "fixture", "length_mm": 500},
    )
    part.workbench = {
        "schema_version": "1.1",
        "current_revision": {
            "review_status": "released", "part_form": "profile",
            "production_properties": {"material": "S355JR", "material_grade": "S355JR", "profile": "HEA140"},
        },
    }
    part.recompute_hashes()
    part.production_identity_hash = compute_production_identity(part)
    part.bom_group_key = part.production_identity_hash
    formats = {name: {"status": "passed", "artifact_id": name} for name in ("nc1", "step", "ifc", "pdf")}
    part.workbench["current_revision"]["roundtrip_validation"] = {
        "status": "passed", "manufacturing_hash": part.manufacturing_hash,
        "canonical_signature": "fixture", "formats": formats,
    }
    part.workbench["canonical_rebuild"] = {"status": "current", "report": {"canonical_signature": "fixture"}}
    part.workbench["artifacts"] = {
        name: {"status": "current", "manufacturing_hash": part.manufacturing_hash} for name in formats
    }
    return part


def legacy_record() -> dict:
    return {
        "id": "transport", "classification": "make_part", "classification_status": "confirmed",
        "classification_confidence": 1.0, "material": "S355JR", "material_grade": "S355JR",
        "normalized_material": "S355JR", "profile": "HEA140", "normalized_profile": "HEA140",
        "material_confidence": 1.0, "profile_confidence": 1.0,
        "geometry_hash": "a" * 64, "production_identity_hash": "b" * 64,
        "trusted_artifacts": {"step": b"fixture"},
    }


class MaterialReleaseGateSmoke(unittest.TestCase):
    def codes(self, part: Part) -> set[str]:
        return {message.code for message in ProjectProductionExportEngine._release_blockers(part)}

    def export_codes(self, part: object) -> set[str]:
        return {message.code for message in ReadinessGate().assess(part, ["step"]).messages_for("step")}

    def test_release_module_is_native_lazy(self) -> None:
        result = subprocess.run([
            sys.executable, "-c",
            "import sys; from cws_convertor.production_export import ProjectProductionExportEngine; "
            "assert 'cadquery' not in sys.modules; assert 'OCP' not in sys.modules",
        ], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_current_fixture_passes_without_mutation(self) -> None:
        part = ready_part()
        before = deepcopy(asdict(part))
        self.assertEqual(self.codes(part), set())
        self.assertEqual(project_fingerprint_conflicts(part), [])
        self.assertEqual(project_fingerprint_conflicts(asdict(part)), [])
        self.assertEqual(asdict(part), before)

    def test_stale_identity_after_normalized_material_change(self) -> None:
        part = ready_part()
        part.normalized_material = "S235JR"
        self.assertTrue({"CWS-REL-014", "CWS-REL-015"} <= self.codes(part))
        self.assertTrue({"CWS-EXP-108", "CWS-EXP-109"} <= self.export_codes(part))

    def test_stale_geometry_and_manufacturing_hashes(self) -> None:
        for field, value in (("length_mm", 900.0), ("profile", "HEA180"), ("material", "S235JR")):
            with self.subTest(field=field):
                part = ready_part()
                setattr(part, field, value)
                self.assertIn("CWS-REL-015", self.codes(part))

    def test_valid_grade_does_not_mask_conflicting_raw_material(self) -> None:
        part = ready_part()
        part.material = "S235JR"
        self.assertIn("CWS-REL-014", self.codes(part))
        self.assertIn("CWS-EXP-108", self.export_codes(part))

    def test_stale_workbench_material_is_blocked(self) -> None:
        part = ready_part()
        part.workbench["current_revision"]["production_properties"]["material"] = "S235JR"
        self.assertIn("CWS-REL-014", self.codes(part))
        self.assertIn("CWS-EXP-108", self.export_codes(part))

    def test_nonfinite_and_out_of_range_confidences_fail_closed(self) -> None:
        for value in (float("nan"), float("inf"), -1, 1.1, None, True):
            with self.subTest(value=value):
                part = ready_part()
                part.material_confidence = value
                part.profile_confidence = value
                self.assertTrue({"CWS-REL-009", "CWS-REL-012"} <= self.codes(part))
                self.assertTrue({"CWS-EXP-105", "CWS-EXP-106"} <= self.export_codes(part))

    def test_unknown_catalog_material_cannot_be_approved_by_confidence(self) -> None:
        part = ready_part()
        part.material = part.material_grade = part.normalized_material = "UNOBTAINIUM"
        self.assertIn("CWS-REL-016", self.codes(part))
        self.assertIn("CWS-EXP-107", self.export_codes(part))

    def test_explicit_review_status_overrides_legacy_confirmation(self) -> None:
        for status in ("review_required", "blocked", "automatic", "unclassified"):
            with self.subTest(status=status):
                record = legacy_record()
                record.update(classification_status=status, classification_confirmed=True, approved=True)
                self.assertIn("CWS-EXP-022", self.export_codes(record))
        record = legacy_record()
        self.assertTrue(ReadinessGate().assess(record, ["step"]).allowed("step"))
        record.pop("classification_status")
        record["classification_confirmed"] = "false"
        self.assertIn("CWS-EXP-022", self.export_codes(record))

    def test_real_validation_issues_and_plain_blockers_are_enforced(self) -> None:
        part = ready_part()
        part.validation_issues.append(ValidationIssue("TEST-001", "Unresolved", severity="error"))
        self.assertIn("TEST-001", self.codes(part))
        self.assertIn("CWS-EXP-030", self.export_codes(part))
        part.validation_issues[0].resolved = True
        self.assertNotIn("TEST-001", self.codes(part))
        self.assertNotIn("CWS-EXP-030", self.export_codes(part))
        record = legacy_record()
        record["blockers"] = ["Materiaalconflict"]
        self.assertIn("CWS-EXP-030", self.export_codes(record))

    def test_profile_aliases_do_not_create_false_conflicts(self) -> None:
        record = legacy_record()
        record["profile"] = "HEA-140"
        self.assertNotIn("CWS-EXP-108", self.export_codes(record))


if __name__ == "__main__":
    unittest.main()
