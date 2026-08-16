from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing import (
    DstvFaceMappingAdapter,
    FaceLocalFrame,
    FaceProofStatus,
    ManufacturingFaceResolver,
    ManufacturingFaceRole,
    ManufacturingFaceService,
    ManufacturingFaceValidator,
    SurfaceType,
)
from cws_convertor.project.model import Part, Transform3D, stable_sha256
from cws_convertor.project.workbench import create_workbench_state, evaluate_workbench_revision


def _box(length: float, width: float, height: float, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> cq.Shape:
    return cq.Solid.makeBox(length, width, height, cq.Vector(x, y, z))


def _shape_i(length=1000.0, h=100.0, b=100.0, tf=10.0, tw=8.0) -> cq.Shape:
    y0 = (b - tw) / 2.0
    return _box(length, tw, h, y=y0).fuse(_box(length, b, tf)).fuse(_box(length, b, tf, z=h - tf))


def _shape_u(length=1000.0, h=100.0, b=50.0, tf=8.0, tw=6.0) -> cq.Shape:
    return _box(length, tw, h).fuse(_box(length, b, tf)).fuse(_box(length, b, tf, z=h - tf))


def _shape_l(length=1000.0, h=70.0, b=50.0, th=6.0, tv=6.0) -> cq.Shape:
    return _box(length, tv, h).fuse(_box(length, b, th))


def _shape_rhs(length=1000.0, h=80.0, b=60.0, t=5.0) -> cq.Shape:
    outer = _box(length, b, h)
    inner = _box(length + 2.0, b - 2.0 * t, h - 2.0 * t, x=-1.0, y=t, z=t)
    return outer.cut(inner)


def _workbench_part(part_id: str, profile_type: str, *, part_form: str = "profile") -> Part:
    part = Part(
        internal_id=part_id,
        name=part_id,
        part_position=part_id,
        profile="TEST",
        profile_type=profile_type,
        material="S235",
        material_grade="S235JR",
        geometry_descriptor={"dimensions": [1000.0, 100.0, 100.0]},
    )
    part.recompute_hashes()
    state = create_workbench_state(part, user="test", source_geometry_hash=part.geometry_hash)
    revision = deepcopy(state["current_revision"])
    revision["part_form"] = part_form
    revision["recognition"] = {"candidate": "TEST", "confidence": 1.0, "confirmed": True}
    revision["production_frame"] = {"matrix": Transform3D.identity().matrix}
    revision["dimensions"] = {"length_mm": 1000.0}
    revision["production_properties"] = {
        "profile": "TEST",
        "material": "S235",
        "material_grade": "S235JR",
        "part_position": part_id,
        "assembly_position": "",
    }
    revision["reference_sides"] = [
        {"side_id": "review", "label": "review", "face_ref": "canonical", "confirmed": True}
    ]
    revision["contours"] = []
    revision["features"] = []
    revision["validation_issues"] = evaluate_workbench_revision(revision)
    assert not revision["validation_issues"], revision["validation_issues"]
    state["current_revision"] = revision
    snapshot = deepcopy(revision)
    state["revision_history"] = [
        {
            "revision_id": snapshot["revision_id"],
            "revision_number": snapshot["revision_number"],
            "timestamp": snapshot["modified_at"],
            "user": "test",
            "reason": snapshot["reason"],
            "snapshot_sha256": stable_sha256(snapshot),
            "snapshot": snapshot,
        }
    ]
    state["commands"] = []
    state["command_cursor"] = 0
    part.workbench = state
    return part


def _roles(report) -> set[ManufacturingFaceRole]:
    return {face.semantic_role for face in report.faces}


class ManufacturingFaceCoreTests(unittest.TestCase):
    def test_face_local_frame_is_right_handed_and_roundtrips(self) -> None:
        frame = FaceLocalFrame(
            origin_mm=(10.0, 20.0, 30.0),
            u_axis=(1.0, 0.0, 0.0),
            v_axis=(0.0, 1.0, 0.0),
            normal=(0.0, 0.0, 1.0),
        )
        point = frame.from_local(5.0, 7.0, 0.0)
        self.assertEqual((15.0, 27.0, 30.0), point)
        local = frame.to_local(point)
        self.assertAlmostEqual(5.0, local[0])
        self.assertAlmostEqual(7.0, local[1])
        self.assertAlmostEqual(0.0, local[2])
        self.assertEqual(frame.frame_sha256, FaceLocalFrame.from_dict(frame.to_dict()).frame_sha256)

    def test_i_profile_maps_outer_flange_web_and_ends_without_guessing_dstv_web_side(self) -> None:
        part = _workbench_part("I1", "I")
        report = ManufacturingFaceResolver().resolve(part, shape=_shape_i())
        roles = _roles(report)
        for required in (
            ManufacturingFaceRole.TOP_OUTER,
            ManufacturingFaceRole.BOTTOM_OUTER,
            ManufacturingFaceRole.WEB_LEFT,
            ManufacturingFaceRole.WEB_RIGHT,
            ManufacturingFaceRole.END_START,
            ManufacturingFaceRole.END_FINISH,
        ):
            self.assertIn(required, roles)
        web = next(face for face in report.faces if face.semantic_role == ManufacturingFaceRole.WEB_LEFT)
        self.assertEqual({"v", "h"}, set(web.dstv_side_candidates))
        self.assertEqual(FaceProofStatus.REVIEW_REQUIRED, web.proof_status)
        self.assertEqual("blocked", DstvFaceMappingAdapter().map_face(web)["status"])
        self.assertFalse(ManufacturingFaceValidator().validate(part, report))

    def test_u_profile_maps_web_and_flange_outer_faces(self) -> None:
        part = _workbench_part("U1", "U")
        report = ManufacturingFaceResolver().resolve(part, shape=_shape_u())
        roles = _roles(report)
        self.assertIn(ManufacturingFaceRole.WEB_LEFT, roles)
        self.assertIn(ManufacturingFaceRole.WEB_RIGHT, roles)
        self.assertIn(ManufacturingFaceRole.TOP_OUTER, roles)
        self.assertIn(ManufacturingFaceRole.BOTTOM_OUTER, roles)
        self.assertIn(ManufacturingFaceRole.END_START, roles)
        self.assertIn(ManufacturingFaceRole.END_FINISH, roles)

    def test_l_profile_maps_two_outer_legs(self) -> None:
        part = _workbench_part("L1", "L")
        report = ManufacturingFaceResolver().resolve(part, shape=_shape_l())
        roles = _roles(report)
        self.assertIn(ManufacturingFaceRole.LEG_A_OUTER, roles)
        self.assertIn(ManufacturingFaceRole.LEG_B_OUTER, roles)
        self.assertIn(ManufacturingFaceRole.END_START, roles)
        self.assertIn(ManufacturingFaceRole.END_FINISH, roles)

    def test_rhs_maps_four_outer_longitudinal_surfaces_and_keeps_inner_faces_custom(self) -> None:
        part = _workbench_part("R1", "M")
        report = ManufacturingFaceResolver().resolve(part, shape=_shape_rhs())
        roles = _roles(report)
        for required in (
            ManufacturingFaceRole.TOP_OUTER,
            ManufacturingFaceRole.BOTTOM_OUTER,
            ManufacturingFaceRole.LONGITUDINAL_PRIMARY,
            ManufacturingFaceRole.LONGITUDINAL_SECONDARY,
        ):
            self.assertIn(required, roles)
        inner = [face for face in report.faces if face.canonical_kind == "box_inner_wall"]
        self.assertTrue(inner)
        self.assertTrue(all(face.semantic_role == ManufacturingFaceRole.CUSTOM for face in inner))

    def test_plate_front_back_are_canonical_but_dstv_mapping_remains_blocked_until_confirmed(self) -> None:
        part = _workbench_part("B1", "B", part_form="profile")
        report = ManufacturingFaceResolver().resolve(part, shape=_box(1000.0, 300.0, 12.0))
        front = next(face for face in report.faces if face.semantic_role == ManufacturingFaceRole.PLATE_FRONT)
        back = next(face for face in report.faces if face.semantic_role == ManufacturingFaceRole.PLATE_BACK)
        self.assertEqual(SurfaceType.PLANE, front.surface_type)
        self.assertEqual(SurfaceType.PLANE, back.surface_type)
        self.assertEqual("blocked", DstvFaceMappingAdapter().map_face(front)["status"])

    def test_round_surface_requires_rotational_mapping_and_has_no_flat_dstv_candidate(self) -> None:
        part = _workbench_part("RO1", "RO", part_form="round_bar")
        shape = cq.Solid.makeCylinder(25.0, 1000.0, cq.Vector(0.0, 0.0, 0.0), cq.Vector(1.0, 0.0, 0.0))
        report = ManufacturingFaceResolver().resolve(part, shape=shape)
        round_face = next(face for face in report.faces if face.semantic_role == ManufacturingFaceRole.ROUND_SURFACE)
        self.assertEqual(SurfaceType.CYLINDER, round_face.surface_type)
        self.assertFalse(round_face.dstv_side_candidates)
        self.assertEqual("blocked", DstvFaceMappingAdapter().map_face(round_face)["status"])

    def test_custom_profile_keeps_semantic_roles_custom_instead_of_guessing(self) -> None:
        part = _workbench_part("CUST", "ZZ")
        report = ManufacturingFaceResolver().resolve(part, shape=_box(1000.0, 42.0, 37.0))
        non_end = [
            face for face in report.faces
            if face.semantic_role not in {ManufacturingFaceRole.END_START, ManufacturingFaceRole.END_FINISH}
        ]
        self.assertTrue(non_end)
        self.assertTrue(all(face.semantic_role == ManufacturingFaceRole.CUSTOM for face in non_end))
        self.assertTrue(any("geen bewezen" in item for item in report.warnings))

    def test_confirmed_reference_side_is_the_only_way_to_promote_dstv_mapping(self) -> None:
        part = _workbench_part("I2", "I")
        resolver = ManufacturingFaceResolver()
        first = resolver.resolve(part, shape=_shape_i())
        web = next(face for face in first.faces if face.semantic_role == ManufacturingFaceRole.WEB_LEFT)
        revision = deepcopy(part.workbench["current_revision"])
        revision["reference_sides"] = [
            {"side_id": "v", "label": "DSTV v", "face_ref": web.source_geometry_ref, "confirmed": True}
        ]
        revision["validation_issues"] = evaluate_workbench_revision(revision)
        self.assertFalse(revision["validation_issues"])
        part.workbench["current_revision"] = revision
        snapshot = deepcopy(revision)
        part.workbench["revision_history"] = [
            {
                "revision_id": snapshot["revision_id"],
                "revision_number": snapshot["revision_number"],
                "timestamp": snapshot["modified_at"],
                "user": "test",
                "reason": snapshot["reason"],
                "snapshot_sha256": stable_sha256(snapshot),
                "snapshot": snapshot,
            }
        ]
        second = resolver.resolve(part, shape=_shape_i())
        confirmed = next(face for face in second.faces if face.source_geometry_ref == web.source_geometry_ref)
        self.assertEqual(("v",), confirmed.dstv_side_candidates)
        self.assertEqual(FaceProofStatus.VERIFIED, confirmed.proof_status)
        mapped = DstvFaceMappingAdapter().map_face(confirmed)
        self.assertEqual("verified", mapped["status"])
        self.assertEqual("v", mapped["dstv_side"])

    def test_service_persists_hash_bound_report_without_changing_manufacturing_hash(self) -> None:
        part = _workbench_part("PERSIST", "I")
        before = part.manufacturing_hash
        service = ManufacturingFaceService()
        resolved = ManufacturingFaceResolver().resolve(part, shape=_shape_i())
        with patch.object(service.resolver, "resolve", return_value=resolved):
            report = service.build(part, persist=True)
        self.assertEqual(before, part.manufacturing_hash)
        self.assertEqual(report.report_sha256, part.workbench["manufacturing_faces"]["report_sha256"])
        restored = service.load_current(part)
        self.assertIsNotNone(restored)
        self.assertEqual(report.report_sha256, restored.report_sha256)


if __name__ == "__main__":
    unittest.main(verbosity=2)
