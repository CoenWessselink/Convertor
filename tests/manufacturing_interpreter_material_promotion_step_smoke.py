from __future__ import annotations

import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.importers.step_project import resolve_deferred_step_recognition
from cws_convertor.manufacturing_interpreter.contracts import (
    CrossSectionSignature,
    GeometryProofStatus,
    InterpretationConfirmation,
    InterpretationReadiness,
    MaterialEvidence,
    MaterialEvidenceStatus,
)
from cws_convertor.manufacturing_interpreter.material_evidence import material_evidence_from_part
from cws_convertor.manufacturing_interpreter.project_link import (
    ProjectPartSourceLinkError,
    build_project_part_request,
)
from cws_convertor.manufacturing_interpreter.promotion import WorkbenchPromotionCoordinator
from cws_convertor.manufacturing_interpreter.profiles import recognize_profile
from cws_convertor.manufacturing_interpreter.recognition_cache import stable_sha256
from cws_convertor.project import FieldProvenance, Part, ProjectSession, SourceIdentity
from profile_database import ProfileDefinition


def _session(*, with_material_provenance: bool = True) -> ProjectSession:
    session = ProjectSession.new("MGI promotion contract", created_by="test")
    provenance = {}
    if with_material_provenance:
        provenance["material"] = FieldProvenance(
            source_file_id="source-1",
            source_entity_id="#42",
            source_path="Default.MATERIAL",
            method="ifc_semantic_exact",
            confidence=1.0,
            status="automatic",
        )
    part = Part(
        internal_id="part-1",
        name="Profiel",
        source_identity=SourceIdentity(
            source_format="STEP",
            source_file_id="source-1",
            source_sha256="a" * 64,
            source_entity_id="#42",
        ),
        profile="IPE200",
        normalized_profile="IPE200",
        profile_confidence=1.0,
        material="S355JR",
        material_grade="S355JR",
        normalized_material="S355JR",
        material_confidence=1.0,
        geometry_descriptor={"source_geometry_hash": "b" * 64},
        field_provenance=provenance,
    )
    part.recompute_hashes()
    session.project.add_entity(part, user="test")
    session.start_part_workbench(part.internal_id, user="test")
    return session


def _report(material: MaterialEvidence) -> SimpleNamespace:
    hypothesis = SimpleNamespace(hypothesis_id="hypothesis-1")
    return SimpleNamespace(
        interpretation_id="interpretation-1",
        readiness=InterpretationReadiness.READY,
        source_gate=GeometryProofStatus.PROVEN_WITHIN_POLICY,
        equivalence=SimpleNamespace(status=GeometryProofStatus.PROVEN_BREP_EQUIVALENT),
        part_id="part-1",
        source_file_id="source-1",
        source_sha256="a" * 64,
        source_geometry_hash="b" * 64,
        tolerance_policy_hash="c" * 64,
        profile_database_hash="d" * 64,
        profile=SimpleNamespace(
            status=GeometryProofStatus.PROVEN_WITHIN_POLICY,
            designation="IPE200",
            profile_type="I",
            confidence=0.99,
        ),
        material_evidence=material,
        hypotheses=(hypothesis,),
        features=(),
        manufacturing_frame=None,
        selected_axis_id="axis-1",
        axis_candidates=(SimpleNamespace(axis_id="axis-1", length_mm=1200.0),),
    )


def _confirmation(report: SimpleNamespace) -> InterpretationConfirmation:
    return InterpretationConfirmation(
        confirmation_id="confirmation-1",
        report_hash=stable_sha256(report),
        hypothesis_id="hypothesis-1",
        user="reviewer",
    )


def test_promotion_uses_supported_workbench_fields_and_preserves_mgi_pointer() -> None:
    session = _session()
    material = MaterialEvidence(
        status=MaterialEvidenceStatus.SOURCE_CONFIRMED,
        material="S355JR",
        grade="S355JR",
        confidence=1.0,
        source="ifc_semantic_exact",
        source_path="Default.MATERIAL",
    )
    report = _report(material)
    result = WorkbenchPromotionCoordinator().promote(
        report=report,
        confirmation=_confirmation(report),
        project=session.project,
        user="reviewer",
        current_source_geometry_hash=report.source_geometry_hash,
        current_tolerance_policy_hash=report.tolerance_policy_hash,
        current_profile_database_hash=report.profile_database_hash,
    )
    assert result.status == "PROMOTED", result
    revision = session.project.parts["part-1"].workbench["current_revision"]
    interpretation = revision["recognition"]["manufacturing_interpretation"]
    assert interpretation["report_hash"] == stable_sha256(report)
    assert interpretation["hypothesis_id"] == "hypothesis-1"
    assert revision["production_properties"]["material_grade"] == "S355JR"
    assert "manufacturing_interpretation" not in revision


def test_promotion_blocks_unresolved_material_and_stale_source_without_mutation() -> None:
    session = _session(with_material_provenance=False)
    report = _report(MaterialEvidence())
    before = session.project.parts["part-1"].workbench
    unresolved = WorkbenchPromotionCoordinator().promote(
        report=report,
        confirmation=_confirmation(report),
        project=session.project,
        user="reviewer",
    )
    assert unresolved.status == "BLOCKED"
    assert unresolved.blockers == ("MATERIAL_EVIDENCE_UNRESOLVED",)
    assert session.project.parts["part-1"].workbench == before

    confirmed = _report(
        MaterialEvidence(
            status=MaterialEvidenceStatus.SOURCE_CONFIRMED,
            material="S355JR",
            confidence=1.0,
        )
    )
    stale = WorkbenchPromotionCoordinator().promote(
        report=confirmed,
        confirmation=_confirmation(confirmed),
        project=session.project,
        user="reviewer",
        current_source_geometry_hash="e" * 64,
    )
    assert stale.status == "BLOCKED"
    assert stale.blockers == ("STALE_REPORT:SOURCE_GEOMETRY_HASH_CHANGED",)
    assert session.project.parts["part-1"].workbench == before


def test_project_part_link_distinguishes_source_confirmed_from_unresolved_material() -> None:
    confirmed_session = _session(with_material_provenance=True)
    confirmed_part = confirmed_session.project.parts["part-1"]
    inspection = SimpleNamespace(
        part_id="part-1",
        source_file_id="source-1",
        source_sha256="a" * 64,
        source_geometry_hash="b" * 64,
    )
    request = build_project_part_request(confirmed_part, inspection)
    assert request.material_evidence is not None
    assert request.material_evidence.status == MaterialEvidenceStatus.SOURCE_CONFIRMED
    assert dict(request.project_part_link)["project_part_id"] == "part-1"

    unresolved_part = _session(with_material_provenance=False).project.parts["part-1"]
    unresolved = material_evidence_from_part(unresolved_part)
    assert unresolved.status == MaterialEvidenceStatus.UNRESOLVED
    assert not unresolved.confirmed
    assert "geometrie" in unresolved.reason.lower()

    changed = SimpleNamespace(**vars(inspection))
    changed.source_sha256 = "f" * 64
    try:
        build_project_part_request(confirmed_part, changed)
    except ProjectPartSourceLinkError:
        pass
    else:
        raise AssertionError("Een stale bronhash moet de project-partkoppeling blokkeren")


def test_deferred_step_recognition_is_bounded_and_never_invents_material() -> None:
    with tempfile.TemporaryDirectory(prefix="cws-mgi-deferred-step-") as folder:
        source = Path(folder) / "part.step"
        source.write_bytes(b"ISO-10303-21;\nEND-ISO-10303-21;\n")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        fake_report = SimpleNamespace(
            profile=SimpleNamespace(
                status=GeometryProofStatus.PROVEN_WITHIN_POLICY,
                designation="IPE200",
                profile_type="I",
                family="IPE",
                confidence=0.98,
                reason="exact",
            ),
            equivalence=SimpleNamespace(status=GeometryProofStatus.PROVEN_BREP_EQUIVALENT),
            material_evidence=MaterialEvidence(),
            readiness=InterpretationReadiness.REVIEW_REQUIRED,
            semantic_sha256="1" * 64,
            source_geometry_hash="2" * 64,
            blockers=("MATERIAL_EVIDENCE_UNRESOLVED",),
        )
        with patch(
            "cws_convertor.manufacturing_interpreter.isolated.analyze_step_isolated",
            return_value=fake_report,
        ) as isolated:
            result = resolve_deferred_step_recognition(
                source,
                source_sha256=digest,
                timeout_seconds=3.0,
            )
        assert result["status"] == "matched"
        assert result["profile"] == "IPE200"
        assert result["material"] == ""
        assert result["material_evidence"]["status"] == "UNRESOLVED"
        assert isolated.call_args.kwargs["timeout_seconds"] == 3.0

        try:
            resolve_deferred_step_recognition(source, source_sha256="0" * 64)
        except ValueError as exc:
            assert "bronhash" in str(exc).lower()
        else:
            raise AssertionError("Een gewijzigde STEP-bron moet voor workerstart blokkeren")


def test_fragmented_standard_section_can_match_but_custom_single_contour_cannot() -> None:
    definition = ProfileDefinition(
        "IPE200-EXACT",
        "I",
        "IPE",
        200.0,
        100.0,
        8.5,
        5.6,
        area_mm2=2800.0,
    )
    database = SimpleNamespace(profiles=(definition,))
    policy = SimpleNamespace(linear_mm=0.05, relative=0.001)
    common = dict(
        section_id="section-1",
        face_id="face-1",
        area_mm2=2800.0,
        perimeter_mm=900.0,
        width_mm=200.0,
        height_mm=100.0,
        outer_edge_count=12,
        inner_wire_count=0,
        edge_type_counts=(("LINE", 12),),
        inferred_family="CUSTOM",
    )
    fragmented = CrossSectionSignature(**common, component_count=3)
    matched = recognize_profile(fragmented, database, policy)
    assert matched.status == GeometryProofStatus.RECOGNITION_INCOMPLETE
    assert matched.designation == ""

    single_custom = CrossSectionSignature(**common, component_count=1)
    blocked = recognize_profile(single_custom, database, policy)
    assert blocked.status == GeometryProofStatus.RECOGNITION_INCOMPLETE
    assert blocked.designation == ""


if __name__ == "__main__":
    test_promotion_uses_supported_workbench_fields_and_preserves_mgi_pointer()
    test_promotion_blocks_unresolved_material_and_stale_source_without_mutation()
    test_project_part_link_distinguishes_source_confirmed_from_unresolved_material()
    test_deferred_step_recognition_is_bounded_and_never_invents_material()
    test_fragmented_standard_section_can_match_but_custom_single_contour_cannot()
    print("PASS: MGI material, promotion and deferred STEP contracts")
