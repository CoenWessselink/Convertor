from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing.faces_model import (
    FaceLocalFrame,
    FaceProofStatus,
    FaceResolutionReport,
    ManufacturingFace,
    ManufacturingFaceRole,
    SurfaceType,
)
from cws_convertor.manufacturing.identification import (
    CWS_ID_FACE_MISSING,
    CWS_ID_OUTSIDE_FACE,
    IdentificationPlanner,
)
from cws_convertor.manufacturing.identification_model import (
    HoleReferenceInput,
    IdentificationStatus,
    IdentificationTextRequest,
    ReadabilityPolicy,
)
from cws_convertor.project.model import Part


def _part(*, mirrored: bool = False) -> Part:
    part = Part(
        internal_id="P-MAIN",
        name="Main",
        part_position="P1",
        profile="PL100x10",
        profile_type="PL",
        material="S355",
        material_grade="S355J2",
        length_mm=100.0,
        mirrored=mirrored,
        geometry_descriptor={"fixture": "m4", "dimensions": [100.0, 100.0, 10.0]},
    )
    part.recompute_hashes()
    return part


def _face(part: Part, *, proof: FaceProofStatus = FaceProofStatus.VERIFIED) -> ManufacturingFace:
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
        proof_status=proof,
        confidence=1.0,
    )


def _report(part: Part, *, proof: FaceProofStatus = FaceProofStatus.VERIFIED) -> FaceResolutionReport:
    return FaceResolutionReport.create(
        part_id=part.internal_id,
        source_geometry_hash=part.geometry_hash,
        manufacturing_hash=part.manufacturing_hash,
        profile_type=part.profile_type,
        part_form="plate",
        faces=(_face(part, proof=proof),),
    )


class ViewerV15IdentificationContractTests(unittest.TestCase):
    def test_explicit_per_face_hole_reference_is_accepted(self) -> None:
        part = _part()
        request = HoleReferenceInput(
            reference_id="REF-H1",
            part_id=part.internal_id,
            face_id="FACE-MAIN",
            center_2d=(50.0, 50.0),
            diameter_mm=10.0,
            source_hole_id="HOLE-1",
            source_partner_part_id="P-SECONDARY",
        )
        result = IdentificationPlanner().build(part, _report(part), hole_references=(request,))
        self.assertEqual(1, len(result.hole_references))
        self.assertEqual(IdentificationStatus.ACCEPTED, result.hole_references[0].status)
        self.assertTrue(result.hole_references[0].production_usable)
        self.assertTrue(result.production_usable)
        self.assertEqual(2, len(result.hole_references[0].cross_segments()))

    def test_missing_face_binding_is_retained_as_blocked_reference(self) -> None:
        part = _part()
        request = HoleReferenceInput(
            reference_id="REF-MISSING",
            part_id=part.internal_id,
            face_id="FACE-UNKNOWN",
            center_2d=(50.0, 50.0),
            diameter_mm=10.0,
            source_hole_id="HOLE-2",
        )
        result = IdentificationPlanner().build(part, _report(part), hole_references=(request,))
        self.assertEqual(1, len(result.hole_references))
        self.assertIn(CWS_ID_FACE_MISSING, result.hole_references[0].blocking_codes)
        self.assertIn(CWS_ID_FACE_MISSING, result.blocking_codes)
        self.assertFalse(result.production_usable)

    def test_mirrored_part_keeps_structured_text_readable_without_reversing_glyphs(self) -> None:
        part = _part(mirrored=True)
        request = IdentificationTextRequest(
            request_id="TXT-1",
            part_id=part.internal_id,
            face_id="FACE-MAIN",
            text="M001-P1",
            anchor_2d=(50.0, 50.0),
            text_height_mm=5.0,
            rotation_deg=180.0,
            readability_policy=ReadabilityPolicy.KEEP_READABLE,
            source_partner_part_id="P-SECONDARY",
        )
        result = IdentificationPlanner().build(part, _report(part), text_requests=(request,))
        intent = result.text_intents[0]
        self.assertEqual("M001-P1", intent.request.text)
        self.assertEqual(0.0, intent.effective_rotation_deg)
        self.assertTrue(intent.mirror_compensated)
        self.assertFalse(intent.mirror_text_geometry)
        self.assertEqual(IdentificationStatus.ACCEPTED, intent.status)
        self.assertTrue(intent.production_usable)

    def test_text_footprint_outside_face_fails_closed(self) -> None:
        part = _part()
        request = IdentificationTextRequest(
            request_id="TXT-OUT",
            part_id=part.internal_id,
            face_id="FACE-MAIN",
            text="LONG IDENTIFICATION",
            anchor_2d=(2.0, 2.0),
            text_height_mm=8.0,
        )
        result = IdentificationPlanner().build(part, _report(part), text_requests=(request,))
        self.assertIn(CWS_ID_OUTSIDE_FACE, result.text_intents[0].blocking_codes)
        self.assertFalse(result.production_usable)

    def test_review_required_face_never_becomes_production_identification(self) -> None:
        part = _part()
        request = IdentificationTextRequest(
            request_id="TXT-REVIEW",
            part_id=part.internal_id,
            face_id="FACE-MAIN",
            text="P1",
            anchor_2d=(50.0, 50.0),
            text_height_mm=5.0,
        )
        result = IdentificationPlanner().build(
            part,
            _report(part, proof=FaceProofStatus.REVIEW_REQUIRED),
            text_requests=(request,),
        )
        self.assertEqual(IdentificationStatus.REVIEW_REQUIRED, result.text_intents[0].status)
        self.assertFalse(result.production_usable)

    def test_identification_hash_is_deterministic_and_inputs_are_not_mutated(self) -> None:
        part = _part()
        report = _report(part)
        request = IdentificationTextRequest(
            request_id="TXT-DET",
            part_id=part.internal_id,
            face_id="FACE-MAIN",
            text="P1",
            anchor_2d=(50.0, 50.0),
            text_height_mm=5.0,
        )
        before = report.to_dict()
        result1 = IdentificationPlanner().build(part, report, text_requests=(request,))
        result2 = IdentificationPlanner().build(part, report, text_requests=(request,))
        self.assertEqual(result1.report_sha256, result2.report_sha256)
        self.assertEqual(before, report.to_dict())

    def test_empty_identification_request_is_valid_noop_not_invented_data(self) -> None:
        part = _part()
        result = IdentificationPlanner().build(part, _report(part))
        self.assertEqual((), result.hole_references)
        self.assertEqual((), result.text_intents)
        self.assertTrue(result.production_usable)


if __name__ == "__main__":
    unittest.main(verbosity=2)
