"""Pure MGI authority/transaction contracts; native CAD is not exercised here."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.importers.step_project import apply_deferred_step_recognition
from cws_convertor.manufacturing_interpreter.material_evidence import (
    material_evidence_from_part, material_evidence_from_request, normalise_material_evidence,
)
from cws_convertor.manufacturing_interpreter.promotion import WorkbenchPromotionCoordinator
from cws_convertor.manufacturing_interpreter.recognition_cache import RecognitionCacheV3
from cws_convertor.project import SourceFileRecord
from tests.manufacturing_interpreter_material_promotion_step_smoke import _session, _report, _confirmation


def _source_evidence(**overrides):
    return normalise_material_evidence({
        "status": "SOURCE_CONFIRMED", "material": "S355JR", "grade": "S355JR",
        "confidence": 1.0, "source": "ifc_semantic_exact", "source_path": "Default.MATERIAL",
        **overrides,
    })


class MaterialAuthorityTests(unittest.TestCase):
    def test_geometry_and_unknown_methods_never_confirm(self):
        for method in ("brep", "geometry", "density_guess", "shape_heuristic", "", "made_up"):
            with self.subTest(method=method):
                self.assertFalse(_source_evidence(source=method).confirmed)

    def test_missing_location_or_user_identity_does_not_confirm(self):
        self.assertFalse(_source_evidence(source_path="").confirmed)
        self.assertFalse(_source_evidence(status="USER_CONFIRMED", source="manual").confirmed)
        self.assertTrue(_source_evidence(status="USER_CONFIRMED", source="manual",
            evidence={"confirmed_by": "reviewer"}).confirmed)

    def test_low_invalid_and_missing_confidence_do_not_confirm(self):
        for confidence in (0.0, 0.94, -1, 1.1, float("nan"), float("inf"), None):
            with self.subTest(confidence=confidence):
                self.assertFalse(_source_evidence(confidence=confidence).confirmed)
        self.assertFalse(normalise_material_evidence({"status": "SOURCE_CONFIRMED", "material": "S355JR",
            "source": "ifc_semantic_exact", "source_path": "material"}).confirmed)

    def test_conflicting_grade_blocks_but_catalog_alias_is_equivalent(self):
        self.assertEqual(_source_evidence(grade="S235JR").status.value, "CONFLICT")
        self.assertTrue(_source_evidence(material="S355 JR").confirmed)

    def test_conflicting_part_fields_block(self):
        part = _session().project.parts["part-1"]
        part.material_grade = "S235JR"
        self.assertEqual(material_evidence_from_part(part).status.value, "CONFLICT")

    def test_stale_and_foreign_provenance_block(self):
        for name, value in (("source_file_id", "other"), ("status", "stale")):
            part = _session().project.parts["part-1"]
            setattr(part.field_provenance["material"], name, value)
            self.assertEqual(material_evidence_from_part(part).status.value, "CONFLICT")

    def test_ifc_material_and_type_entities_may_differ_from_product(self):
        for method in ("ifc_material_association_exact", "ifc_type_material_inheritance", "ifc_property_exact"):
            part = _session().project.parts["part-1"]
            provenance = part.field_provenance["material"]
            provenance.method = method
            provenance.source_entity_id = "#900"
            provenance.confidence = .95
            self.assertTrue(material_evidence_from_part(part).confirmed)

    def test_descriptor_conflict_cannot_be_hidden_by_source_field(self):
        part = _session().project.parts["part-1"]
        part.geometry_descriptor["material_recognition"] = {"status": "CONFLICT"}
        self.assertEqual(material_evidence_from_part(part).status.value, "CONFLICT")

    def test_request_rejects_foreign_material_source_hash(self):
        evidence = _source_evidence(evidence={"source_sha256": "old"})
        request = SimpleNamespace(inspection=SimpleNamespace(source_sha256="new"), material_evidence=evidence)
        self.assertEqual(material_evidence_from_request(request).status.value, "CONFLICT")

    def test_promotion_automatically_checks_current_geometry(self):
        session = _session()
        report = _report(_source_evidence())
        session.project.parts["part-1"].geometry_descriptor["source_geometry_hash"] = "e" * 64
        result = WorkbenchPromotionCoordinator().promote(report=report, confirmation=_confirmation(report),
            project=session.project, user="reviewer")
        self.assertIn("STALE_REPORT:SOURCE_GEOMETRY_HASH_CHANGED", result.blockers)

    def test_ready_label_cannot_replace_geometry_proof(self):
        session = _session()
        report = _report(_source_evidence())
        report.profile.confidence = float("nan")
        result = WorkbenchPromotionCoordinator().promote(report=report, confirmation=_confirmation(report),
            project=session.project, user="reviewer")
        self.assertIn("GEOMETRY_OR_PROFILE_PROOF_INCOMPLETE", result.blockers)

    def test_promotion_rejects_stale_material_and_preserves_workbench(self):
        session = _session()
        report = _report(_source_evidence())
        part = session.project.parts["part-1"]
        part.material = part.material_grade = part.normalized_material = "S235JR"
        before = deepcopy(session.project.to_dict())
        result = WorkbenchPromotionCoordinator().promote(report=report, confirmation=_confirmation(report),
            project=session.project, user="reviewer")
        self.assertIn("STALE_REPORT:MATERIAL_CHANGED_OR_CONFLICTING", result.blockers)
        self.assertEqual(session.project.to_dict(), before)

    def test_rejected_promotion_never_undoes_an_existing_user_edit(self):
        session = _session()
        report = _report(_source_evidence())
        before = deepcopy(session.project.to_dict())
        with patch("cws_convertor.project.workbench.update_part_workbench", side_effect=ValueError("rejected")), \
             patch("cws_convertor.project.workbench.undo_part_workbench") as undo:
            result = WorkbenchPromotionCoordinator().promote(report=report, confirmation=_confirmation(report),
                project=session.project, user="reviewer")
        self.assertEqual(result.status, "BLOCKED")
        undo.assert_not_called()
        self.assertEqual(session.project.to_dict(), before)

    def test_cache_is_bound_to_part_and_material(self):
        base = dict(source_sha256="s", source_geometry_hash="g", engine_version="v",
            algorithm_versions=(), tolerance_policy_hash="t", profile_database_hash="d",
            preferred_profile="", requested_outputs=("STEP",))
        key = RecognitionCacheV3.key(**base, part_id="first", material_evidence=_source_evidence())
        self.assertNotEqual(key, RecognitionCacheV3.key(**base, part_id="second", material_evidence=_source_evidence()))
        self.assertNotEqual(key, RecognitionCacheV3.key(**base, part_id="first", material_evidence=None))


class DeferredStepTransactionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="cws-deferred-contract-")
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "part.step"
        self.path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
        self.session = _session()
        self.project = self.session.project
        self.part = self.project.parts["part-1"]
        self.part.workbench = {}
        self.part.profile = self.part.normalized_profile = ""
        self.source = SourceFileRecord.from_path(self.project.project_id, self.path)
        self.project.sources[self.source.source_id] = self.source
        self.part.source_identity.source_file_id = self.source.source_id
        self.part.source_identity.source_sha256 = self.source.sha256
        self.part.field_provenance["material"].source_file_id = self.source.source_id
        self.result = {"status": "matched", "profile": "IPE200", "confidence": .99,
            "report_hash": "c" * 64, "source_sha256": self.source.sha256,
            "source_geometry_hash": "b" * 64, "readiness": "REVIEW_REQUIRED", "blockers": []}

    def run_deferred(self, **kwargs):
        return apply_deferred_step_recognition(self.project, self.source, self.path, **kwargs)

    def test_applies_source_bound_profile_without_changing_material(self):
        with patch("cws_convertor.importers.step_project.resolve_deferred_step_recognition", return_value=self.result):
            report = self.run_deferred()
        self.assertEqual(report["applied_part_ids"], ["part-1"])
        self.assertEqual(self.part.profile, "IPE200")
        self.assertEqual(self.part.material, "S355JR")
        self.assertEqual(self.part.geometry_descriptor["profile_recognition"]["report_hash"], "c" * 64)

    def test_preserves_confirmed_and_workbench_parts(self):
        for state in ("confirmed", "workbench"):
            self.part.classification_status = "confirmed" if state == "confirmed" else "review_required"
            self.part.workbench = {"current_revision": {}} if state == "workbench" else {}
            before = deepcopy(self.project.to_dict())
            with patch("cws_convertor.importers.step_project.resolve_deferred_step_recognition") as worker:
                report = self.run_deferred()
            worker.assert_not_called()
            self.assertEqual(report["skipped_part_ids"], ["part-1"])
            self.assertEqual(self.project.to_dict(), before)

    def test_multi_part_source_is_blocked_not_guessed(self):
        other = deepcopy(self.part)
        other.internal_id = "part-2"
        self.project.parts[other.internal_id] = other
        with patch("cws_convertor.importers.step_project.resolve_deferred_step_recognition") as worker:
            report = self.run_deferred(part_ids=["part-1"])
        worker.assert_not_called()
        self.assertEqual(report["results"][0]["reason"], "PROJECT_PART_SOURCE_ISOLATION_REQUIRED")
        self.assertEqual(report["applied_part_ids"], [])

    def test_source_change_blocks_before_worker(self):
        self.path.write_text("changed", encoding="utf-8")
        with patch("cws_convertor.importers.step_project.resolve_deferred_step_recognition") as worker:
            with self.assertRaisesRegex(ValueError, "bronhash"):
                self.run_deferred()
        worker.assert_not_called()

    def test_part_changed_during_analysis_rejects_result(self):
        def mutate(*args, **kwargs):
            self.part.name = "Concurrent user edit"
            return self.result
        with patch("cws_convertor.importers.step_project.resolve_deferred_step_recognition", side_effect=mutate):
            with self.assertRaisesRegex(ValueError, "Onderdeel is gewijzigd"):
                self.run_deferred()
        self.assertEqual(self.part.profile, "")
        self.assertEqual(self.part.name, "Concurrent user edit")

    def test_foreign_result_and_foreign_selection_rejected(self):
        with self.assertRaisesRegex(ValueError, "bronvreemde"):
            self.run_deferred(part_ids=["unknown-part"])
        with patch("cws_convertor.importers.step_project.resolve_deferred_step_recognition",
            return_value={**self.result, "source_sha256": "x" * 64}):
            with self.assertRaisesRegex(ValueError, "Herkenningsresultaat"):
                self.run_deferred()
        self.assertEqual(self.part.profile, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
