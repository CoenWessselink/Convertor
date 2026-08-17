from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing.contact_model import (
    ContactPatch,
    ContactRelationType,
    ContactResolutionReport,
)
from cws_convertor.manufacturing.faces_model import (
    FaceLocalFrame,
    FaceProofStatus,
    FaceResolutionReport,
    ManufacturingFace,
    ManufacturingFaceRole,
    SurfaceType,
)
from cws_convertor.manufacturing.marking import (
    CWS_MARK_CONTACT_NOT_VERIFIED,
    CWS_MARK_EXCLUSION,
    CWS_MARK_LENGTH,
    CWS_MARK_STALE_FACE_REPORT,
    ContactScribingEngine,
    MarkSetValidator,
)
from cws_convertor.manufacturing.marking_model import (
    ExclusionKind,
    MarkExclusionZone,
    MarkStatus,
    MarkingRuleSet,
)
from cws_convertor.project.model import Part


def _part() -> Part:
    part = Part(
        internal_id="P-MAIN",
        name="Main",
        part_position="P1",
        profile="PL100x10",
        profile_type="PL",
        material="S355",
        material_grade="S355J2",
        length_mm=100.0,
        geometry_descriptor={"fixture": "m3", "dimensions": [100.0, 100.0, 10.0]},
    )
    part.recompute_hashes()
    return part


def _face(part: Part, *, proof_status: FaceProofStatus = FaceProofStatus.VERIFIED) -> ManufacturingFace:
    loop = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0), (0.0, 0.0))
    xyz = tuple((x, y, 0.0) for x, y in loop)
    return ManufacturingFace(
        face_id="FACE-MAIN",
        part_id=part.internal_id,
        semantic_role=ManufacturingFaceRole.PLATE_FRONT,
        canonical_kind="plate_front",
        source_geometry_ref="fixture:face:1",
        local_frame=FaceLocalFrame(
            origin_mm=(0.0, 0.0, 0.0),
            u_axis=(1.0, 0.0, 0.0),
            v_axis=(0.0, 1.0, 0.0),
            normal=(0.0, 0.0, 1.0),
        ),
        surface_type=SurfaceType.PLANE,
        boundary_loops_2d=(loop,),
        outline_loops_part_mm=(xyz,),
        area_mm2=10000.0,
        confidence=1.0,
        proof_status=proof_status,
    )


def _face_report(part: Part, *, proof_status: FaceProofStatus = FaceProofStatus.VERIFIED, manufacturing_hash: str | None = None) -> FaceResolutionReport:
    return FaceResolutionReport.create(
        part_id=part.internal_id,
        source_geometry_hash=part.geometry_hash,
        manufacturing_hash=manufacturing_hash or part.manufacturing_hash,
        profile_type=part.profile_type,
        part_form="plate",
        faces=(_face(part, proof_status=proof_status),),
    )


def _patch(*, proof_status: str = "verified") -> ContactPatch:
    world = (
        (20.0, 20.0, 0.0),
        (80.0, 20.0, 0.0),
        (80.0, 80.0, 0.0),
        (20.0, 80.0, 0.0),
        (20.0, 20.0, 0.0),
    )
    local = tuple((x, y) for x, y, _z in world)
    return ContactPatch(
        contact_id="CONTACT-1",
        assembly_id="A1",
        main_part_id="P-MAIN",
        secondary_part_id="P-SECONDARY",
        main_face_id="FACE-MAIN",
        secondary_face_id="FACE-SECONDARY",
        source_relation=("assembly_main_secondary",),
        relation_type=ContactRelationType.GEOMETRIC_TOUCH,
        exact_boundary_world_mm=(world,),
        projected_boundary_main_2d=(local,),
        projected_boundary_secondary_2d=(local,),
        area_mm2=3600.0,
        gap_mm=0.0,
        penetration_mm3=0.0,
        proof_status=proof_status,
    )


def _contact_report(*, proof_status: str = "verified") -> ContactResolutionReport:
    return ContactResolutionReport.create(
        project_id="fixture-project",
        candidate_pairs=(("P-MAIN", "P-SECONDARY"),),
        patches=(_patch(proof_status=proof_status),),
    )


class ViewerV15MarkingContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.part = _part()
        self.faces = _face_report(self.part)
        self.contacts = _contact_report()

    def test_exact_contact_boundary_yields_deterministic_accepted_scribing(self) -> None:
        engine = ContactScribingEngine()
        result1 = engine.build(self.part, self.faces, self.contacts)
        result2 = engine.build(self.part, self.faces, self.contacts)
        self.assertEqual(result1.report_sha256, result2.report_sha256)
        self.assertEqual(4, len(result1.features))
        self.assertTrue(all(item.status is MarkStatus.ACCEPTED for item in result1.features))
        self.assertTrue(all(item.production_usable for item in result1.features))
        self.assertTrue(result1.production_usable)

    def test_hole_exclusion_blocks_crossing_feature_without_silent_drop(self) -> None:
        zone = MarkExclusionZone(
            zone_id="HOLE-1",
            face_id="FACE-MAIN",
            kind=ExclusionKind.HOLE,
            center_2d=(50.0, 20.0),
            radius_mm=4.0,
            source_id="H1",
        )
        result = ContactScribingEngine().build(self.part, self.faces, self.contacts, exclusions=(zone,))
        self.assertEqual(4, len(result.features))
        blocked = [item for item in result.features if CWS_MARK_EXCLUSION in item.blocking_codes]
        self.assertTrue(blocked)
        self.assertFalse(result.production_usable)
        self.assertIn(CWS_MARK_EXCLUSION, result.blocking_codes)

    def test_non_verified_contact_never_upgrades_to_production_mark(self) -> None:
        contacts = _contact_report(proof_status="review_required")
        result = ContactScribingEngine().build(self.part, self.faces, contacts)
        self.assertEqual(4, len(result.features))
        self.assertTrue(all(CWS_MARK_CONTACT_NOT_VERIFIED in item.blocking_codes for item in result.features))
        self.assertFalse(result.production_usable)

    def test_rule_length_violation_is_audited_as_blocked_feature(self) -> None:
        rules = MarkingRuleSet(max_segment_length_mm=50.0)
        result = ContactScribingEngine(rules).build(self.part, self.faces, self.contacts)
        self.assertEqual(4, len(result.features))
        self.assertTrue(all(CWS_MARK_LENGTH in item.blocking_codes for item in result.features))
        self.assertIn(CWS_MARK_LENGTH, result.blocking_codes)

    def test_stale_face_report_fails_closed(self) -> None:
        stale = _face_report(self.part, manufacturing_hash="0" * 64)
        result = ContactScribingEngine().build(self.part, stale, self.contacts)
        self.assertIn(CWS_MARK_STALE_FACE_REPORT, result.blocking_codes)
        self.assertFalse(result.production_usable)

    def test_validator_detects_ruleset_or_evidence_drift(self) -> None:
        rules = MarkingRuleSet()
        result = ContactScribingEngine(rules).build(self.part, self.faces, self.contacts)
        changed_rules = MarkingRuleSet(edge_clearance_mm=1.0)
        blockers = MarkSetValidator.validate(
            result,
            part=self.part,
            face_report=self.faces,
            contact_report=self.contacts,
            ruleset=changed_rules,
        )
        self.assertIn(CWS_MARK_STALE_FACE_REPORT, blockers)

    def test_mark_generation_does_not_mutate_face_or_contact_evidence(self) -> None:
        face_before = self.faces.to_dict()
        contact_before = self.contacts.to_dict()
        ContactScribingEngine().build(self.part, self.faces, self.contacts)
        self.assertEqual(face_before, self.faces.to_dict())
        self.assertEqual(contact_before, self.contacts.to_dict())


if __name__ == "__main__":
    unittest.main(verbosity=2)
