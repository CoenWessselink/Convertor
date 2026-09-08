from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import FieldProvenance, Part, ProjectSession, SourceFileRecord, SourceIdentity, ValidationIssue
from cws_convertor.ui.material_review import (
    apply_material_confirmation,
    apply_step_recognition_job,
    bounded_confidence,
    build_bulk_preview,
    bulk_scope_part_ids,
    catalog_candidates,
    classification_snapshot,
    create_step_recognition_job,
    material_evidence,
    material_review_reasons,
    material_review_transaction,
    part_fingerprint,
    redo_material_confirmation,
    reject_material_confirmation,
    restore_classification_snapshot,
    selection_ids,
    undo_material_confirmation,
)


@dataclass(frozen=True)
class Material:
    code: str
    name: str
    category: str
    standard: str
    aliases: tuple[str, ...] = ()


class Catalog:
    materials = (
        Material("S235JR", "Constructiestaal S235JR", "Staal", "EN 10025-2", ("S235", "1.0038")),
        Material("S355JR", "Constructiestaal S355JR", "Staal", "EN 10025-2", ("S355", "1.0045")),
        Material("6082-T6", "Aluminium 6082-T6", "Aluminium", "EN 573", ("AL6082T6",)),
    )


def make_part(
    part_id: str,
    *,
    material: str = "S235",
    grade: str = "S235JR",
    normalized: str = "S235JR",
    material_confidence: float = 0.0,
    classification_status: str = "review_required",
    source_class: str = "IFCBEAM",
    geometry_hash: str = "a" * 64,
) -> Part:
    part = Part(
        internal_id=part_id,
        part_position=part_id.upper(),
        source_identity=SourceIdentity(source_format="IFC", source_entity_id=f"#{part_id}"),
        properties={"ifc_entity_type": source_class, "ifc_materials": [material]},
        geometry_descriptor={
            "material_recognition": {
                "status": "source_candidate",
                "confidence": material_confidence,
                "candidate": normalized,
                "reason": "IfcRelAssociatesMaterial",
            }
        },
        geometry_hash=geometry_hash,
        material=material,
        material_grade=grade,
        normalized_material=normalized,
        material_confidence=material_confidence,
        classification_status=classification_status,
        category="make_part",
    )
    part.field_provenance["material"] = FieldProvenance(
        source_entity_id=f"#{part_id}",
        source_path="IfcRelAssociatesMaterial",
        method="exact_source",
        confidence=material_confidence,
    )
    return part


class MaterialReviewLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = Catalog()

    def test_candidates_separate_catalog_match_from_source_confidence(self) -> None:
        rows = catalog_candidates(self.catalog, "S235", source_confidence=0.0)
        self.assertEqual(rows[0].code, "S235JR")
        self.assertEqual(rows[0].match_status, "alias")
        self.assertEqual(rows[0].catalog_match, 0.95)
        self.assertEqual(rows[0].source_confidence, 0.0)
        self.assertEqual(bounded_confidence("not-a-number"), 0.0)
        self.assertEqual(bounded_confidence(float("nan")), 0.0)
        self.assertEqual(bounded_confidence(float("inf")), 0.0)

    def test_generic_entity_confidence_is_never_used_as_material_evidence(self) -> None:
        part = make_part("p1", material_confidence=0.0)
        part.confidence = 1.0
        rows = material_evidence(part)
        self.assertTrue(rows)
        self.assertTrue(all(row.confidence == 0.0 for row in rows))
        self.assertTrue(any(row.method == "IfcRelAssociatesMaterial" for row in rows))

    def test_review_reasons_detect_conflicts_and_missing_confirmation(self) -> None:
        part = make_part("p1", material="S235JR", grade="S355JR", material_confidence=1.0)
        reasons = material_review_reasons(part, self.catalog)
        self.assertIn("materiaal en kwaliteit conflicteren", reasons)
        self.assertIn("classificatie niet handmatig bevestigd", reasons)

    def test_bulk_scope_is_exact_and_confirmed_parts_are_fail_closed(self) -> None:
        p1 = make_part("p1")
        p2 = make_part("p2")
        p3 = make_part("p3", material="S355", grade="S355JR", normalized="S355JR")
        p4 = make_part("p4", classification_status="confirmed", material_confidence=1.0)
        project = SimpleNamespace(parts={part.internal_id: part for part in (p1, p2, p3, p4)})
        self.assertEqual(
            bulk_scope_part_ids(project, "selection", primary_part_id="p1", selected_part_ids=("p1", "p3")),
            ("p1", "p3"),
        )
        self.assertEqual(
            set(bulk_scope_part_ids(project, "raw_material", primary_part_id="p1")),
            {"p1", "p2", "p4"},
        )
        preview = {row.part_id: row for row in build_bulk_preview(project, ("p1", "p4"), self.catalog)}
        self.assertTrue(preview["p1"].eligible)
        self.assertFalse(preview["p4"].eligible)
        self.assertIn("alleen individueel", preview["p4"].note)

    def test_classification_snapshot_restores_undo_metadata(self) -> None:
        part = make_part("p1", material_confidence=0.35)
        part.validation_issues.append(
            ValidationIssue(
                code="CWS-CLASSIFICATION-BLOCK-01",
                message="Review vereist",
                blocking=True,
            )
        )
        snapshot = classification_snapshot(part)
        part.category = "non_steel"
        part.classification_status = "confirmed"
        part.material_confidence = 1.0
        part.field_provenance.pop("category", None)
        part.validation_issues.clear()
        restore_classification_snapshot(part, snapshot)
        self.assertEqual(part.category, "make_part")
        self.assertEqual(part.classification_status, "review_required")
        self.assertEqual(part.material_confidence, 0.35)
        self.assertEqual(part.validation_issues[0].code, "CWS-CLASSIFICATION-BLOCK-01")

    def test_selection_ids_supports_snapshot_and_mapping_shapes(self) -> None:
        self.assertEqual(selection_ids({"entity_ids": ["p1", "p2"]}), ("p1", "p2"))
        snapshot = SimpleNamespace(entity_ids=("p3",), primary_entity_id="p3")
        self.assertEqual(selection_ids(snapshot), ("p3",))

    def test_real_session_confirmation_undo_redo_keeps_material_and_grade_atomic(self) -> None:
        session = ProjectSession.new("Material review controller", created_by="tester")
        part = make_part("p1")
        part.profile = "HEA300"
        part.confidence = 1.0
        part.profile_confidence = 0.0
        part.recompute_hashes()
        session.project.add_entity(part, user="tester")
        before_provenance = asdict(part.field_provenance["material"])
        result = apply_material_confirmation(
            session,
            "p1",
            candidate="S355JR",
            category="make_part",
            reason="3.1-certificaat gecontroleerd",
            user="tester",
        )
        self.assertTrue(result["command_id"])
        self.assertEqual((part.material, part.material_grade, part.normalized_material), ("S355JR",) * 3)
        self.assertEqual(part.classification_status, "confirmed")
        self.assertEqual(part.material_confidence, 1.0)
        self.assertEqual(part.profile_confidence, 0.0)

        undo_material_confirmation(session, "p1", user="tester")
        self.assertEqual((part.material, part.material_grade), ("S235", "S235JR"))
        self.assertEqual(part.classification_status, "review_required")
        self.assertEqual(part.material_confidence, 0.0)
        self.assertEqual(asdict(part.field_provenance["material"]), before_provenance)
        self.assertNotIn("normalized_material", part.field_provenance)
        redo_material_confirmation(session, "p1", user="tester")
        self.assertEqual((part.material, part.material_grade), ("S355JR", "S355JR"))
        self.assertEqual(part.classification_status, "confirmed")
        self.assertEqual(part.profile_confidence, 0.0)
        session.close()

    def test_invalid_material_cannot_partially_start_workbench(self) -> None:
        session = ProjectSession.new("Invalid material")
        part = make_part("p1")
        part.recompute_hashes()
        session.project.add_entity(part)
        before = session.project.to_dict()
        with self.assertRaisesRegex(ValueError, "cataloguscode"):
            apply_material_confirmation(
                session, "p1", candidate="IMAGINARY-STEEL", category="make_part", reason="Review"
            )
        self.assertEqual(session.project.to_dict(), before)
        self.assertIs(session.project.parts["p1"], part)
        session.close()

    def test_confirmation_failure_rolls_back_workbench_and_other_part_changes(self) -> None:
        session = ProjectSession.new("Atomic material")
        first, second = make_part("p1"), make_part("p2")
        first.recompute_hashes()
        second.recompute_hashes()
        session.project.add_entity(first)
        session.project.add_entity(second)
        before = session.project.to_dict()

        def failed_confirmation(*_args, **_kwargs):
            second.category = "non_steel"
            raise RuntimeError("injected classification failure")

        with patch.object(session, "confirm_part_classification", side_effect=failed_confirmation):
            with self.assertRaisesRegex(RuntimeError, "injected"):
                apply_material_confirmation(
                    session, "p1", candidate="S355JR", category="make_part", reason="Review"
                )
        self.assertEqual(session.project.to_dict(), before)
        self.assertIs(session.project.parts["p1"], first)
        self.assertIs(session.project.parts["p2"], second)
        session.close()

    def test_bulk_transaction_rolls_back_all_parts_on_save_failure(self) -> None:
        session = ProjectSession.new("Atomic bulk material")
        for part_id in ("p1", "p2"):
            part = make_part(part_id)
            part.profile = "HEA300"
            part.recompute_hashes()
            session.project.add_entity(part)
        before = session.project.to_dict()
        with self.assertRaisesRegex(OSError, "save failed"):
            with material_review_transaction(session):
                for part_id in ("p1", "p2"):
                    apply_material_confirmation(
                        session, part_id, candidate="S355JR", category="make_part", reason="Bulk review"
                    )
                raise OSError("save failed")
        self.assertEqual(session.project.to_dict(), before)
        session.close()

    def test_confirmation_survives_save_reopen_then_undo_redo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_material_review_") as folder:
            path = Path(folder) / "review.cwsproj"
            session = ProjectSession.new("Persistent review")
            part = make_part("p1")
            part.profile = "HEA300"
            part.recompute_hashes()
            session.project.add_entity(part)
            original_provenance = asdict(part.field_provenance["material"])
            apply_material_confirmation(
                session, "p1", candidate="S355JR", category="make_part", reason="Certificate checked"
            )
            saved_path = session.save(path, user="tester")
            session.close()
            reopened = ProjectSession.open(saved_path)
            restored = reopened.project.parts["p1"]
            self.assertEqual(restored.material, "S355JR")
            undo_material_confirmation(reopened, "p1")
            self.assertEqual((restored.material, restored.material_grade), ("S235", "S235JR"))
            self.assertEqual(asdict(restored.field_provenance["material"]), original_provenance)
            redo_material_confirmation(reopened, "p1")
            self.assertEqual(restored.material, "S355JR")
            self.assertEqual(restored.profile_confidence, 0.0)
            reopened.save(user="tester")
            reopened.close()

    def test_fingerprint_detects_non_material_evidence_changes(self) -> None:
        part = make_part("p1")
        before = part_fingerprint(part)
        part.profile_confidence = 0.9
        self.assertNotEqual(part_fingerprint(part), before)
        before = part_fingerprint(part)
        part.category = "non_steel"
        self.assertNotEqual(part_fingerprint(part), before)

    def test_step_worker_snapshot_is_scoped_detached_and_preserves_live_references(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_step_review_") as folder:
            source_path = Path(folder) / "selected.step"
            source_path.write_text("ISO-10303-21; END-ISO-10303-21;", encoding="utf-8")
            session = ProjectSession.new("STEP review job")
            source = SourceFileRecord.from_path(session.project.project_id, source_path)
            source.semantic_import_complete = True
            session.project.sources[source.source_id] = source
            part = make_part("p1")
            part.source_identity = SourceIdentity(source_format="STEP", source_file_id=source.source_id, source_sha256=source.sha256)
            part.recompute_hashes()
            session.project.add_entity(part)
            job = create_step_recognition_job(session, "p1")
            self.assertEqual((job.source_id, job.part_id), (source.source_id, "p1"))
            self.assertIsNot(job.detached_session.project, session.project)
            self.assertIsNone(job.detached_session.package)
            self.assertIsNone(job.detached_session.path)
            detached = job.detached_session.project.parts["p1"]
            detached.properties["recognition_test_result"] = "review_required"
            detached.recompute_hashes()
            self.assertNotIn("recognition_test_result", part.properties)
            apply_step_recognition_job(job)
            self.assertIs(session.project, job.original_project)
            self.assertIs(session.project.parts["p1"], part)
            self.assertEqual(part.properties["recognition_test_result"], "review_required")
            self.assertTrue(session.dirty)
            stale_job = create_step_recognition_job(session, "p1")
            session.project.audit("user.edited_elsewhere")
            with self.assertRaisesRegex(ValueError, "Project gewijzigd"):
                apply_step_recognition_job(stale_job)
            session.close()

    def test_step_worker_rejects_wrong_format_and_read_only_session(self) -> None:
        session = ProjectSession.new("STEP guard")
        part = make_part("p1")
        part.recompute_hashes()
        session.project.add_entity(part)
        with self.assertRaisesRegex(ValueError, "STEP-onderdeel"):
            create_step_recognition_job(session, "p1")
        session.read_only = True
        with self.assertRaisesRegex(ValueError, "alleen-lezen"):
            create_step_recognition_job(session, "p1")
        session.close()

    def test_real_session_rejection_persists_reason_without_overwriting_source(self) -> None:
        session = ProjectSession.new("Material rejection controller", created_by="tester")
        part = make_part("p1")
        part.profile = "HEA300"
        part.recompute_hashes()
        session.project.add_entity(part, user="tester")
        reject_material_confirmation(
            session,
            "p1",
            candidate="S355JR",
            reason="Certificaat noemt een andere grade",
            user="tester",
        )
        self.assertEqual((part.material, part.material_grade), ("S235", "S235JR"))
        revision = part.workbench["current_revision"]
        self.assertEqual(revision["recognition"]["material_review"]["status"], "rejected")
        self.assertEqual(revision["unresolved_questions"][-1]["review_kind"], "material_candidate_rejected")
        self.assertTrue(any(issue["code"] == "CWS-WB-QUESTION" for issue in revision["validation_issues"]))
        session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
