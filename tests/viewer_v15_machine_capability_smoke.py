from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing.contact_model import ContactPatch, ContactRelationType, ContactResolutionReport
from cws_convertor.manufacturing.faces_model import (
    FaceLocalFrame,
    FaceProofStatus,
    FaceResolutionReport,
    ManufacturingFace,
    ManufacturingFaceRole,
    SurfaceType,
)
from cws_convertor.manufacturing.identification import IdentificationPlanner
from cws_convertor.manufacturing.identification_model import HoleReferenceInput, IdentificationTextRequest
from cws_convertor.manufacturing.machine_capability import (
    CWS_MACHINE_HEAD_CLEARANCE,
    CWS_MACHINE_HEAD_CLEARANCE_UNKNOWN,
    CWS_MACHINE_LIMIT_EXCEEDED,
    CWS_MACHINE_OPERATION_UNSUPPORTED,
    CWS_MACHINE_PART_DIMENSION,
    CWS_MACHINE_REACHABILITY_UNKNOWN,
    CWS_MACHINE_RULESET_INCOMPATIBLE,
    CWS_MACHINE_TOOL_AMBIGUOUS,
    MachineCapabilityEvaluator,
)
from cws_convertor.manufacturing.machine_capability_model import CapabilityStatus, MachineFeatureType
from cws_convertor.manufacturing.marking import ContactScribingEngine
from cws_convertor.project.model import MachineProfile, Part


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
        geometry_descriptor={"fixture": "m5", "dimensions": [100.0, 100.0, 10.0]},
    )
    part.recompute_hashes()
    return part


def _face(part: Part) -> ManufacturingFace:
    loop = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0), (0.0, 0.0))
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
        outline_loops_part_mm=(tuple((x, y, 0.0) for x, y in loop),),
        area_mm2=10000.0,
        proof_status=FaceProofStatus.VERIFIED,
        confidence=1.0,
    )


def _face_report(part: Part) -> FaceResolutionReport:
    return FaceResolutionReport.create(
        part_id=part.internal_id,
        source_geometry_hash=part.geometry_hash,
        manufacturing_hash=part.manufacturing_hash,
        profile_type=part.profile_type,
        part_form="plate",
        faces=(_face(part),),
    )


def _contact_report() -> ContactResolutionReport:
    world = (
        (20.0, 20.0, 0.0),
        (80.0, 20.0, 0.0),
        (80.0, 80.0, 0.0),
        (20.0, 80.0, 0.0),
        (20.0, 20.0, 0.0),
    )
    local = tuple((x, y) for x, y, _z in world)
    patch = ContactPatch(
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
        proof_status="verified",
    )
    return ContactResolutionReport.create(
        project_id="fixture-project",
        candidate_pairs=(("P-MAIN", "P-SECONDARY"),),
        patches=(patch,),
    )


def _machine(mark_ruleset: str, identification_ruleset: str, *, tools=None, operations=None, max_length=1000.0) -> MachineProfile:
    default_tools = [
        {
            "tool_id": "SCRIBE-1",
            "operations": ["mark"],
            "supported_mark_types": ["scribe"],
            "reachable_face_roles": ["plate_front"],
            "compatible_ruleset_sha256s": [mark_ruleset],
            "minimum_head_clearance_mm": 2.0,
            "min_segment_length_mm": 1.0,
            "max_segment_length_mm": 500.0,
        },
        {
            "tool_id": "HOLE-MARK-1",
            "operations": ["mark"],
            "supported_mark_types": ["hole_reference"],
            "reachable_face_roles": ["plate_front"],
            "compatible_ruleset_sha256s": [identification_ruleset],
            "minimum_head_clearance_mm": 2.0,
            "min_cross_arm_mm": 1.0,
            "max_cross_arm_mm": 20.0,
            "min_hole_diameter_mm": 2.0,
            "max_hole_diameter_mm": 80.0,
        },
        {
            "tool_id": "TEXT-1",
            "operations": ["mark"],
            "supported_mark_types": ["identification_text"],
            "reachable_face_roles": ["plate_front"],
            "compatible_ruleset_sha256s": [identification_ruleset],
            "minimum_head_clearance_mm": 2.0,
            "supports_text": True,
            "min_text_height_mm": 2.0,
            "max_text_height_mm": 20.0,
        },
    ]
    return MachineProfile(
        internal_id="MACHINE-PROFILE-1",
        name="Explicit test machine",
        machine_id="MACHINE-1",
        manufacturer="CWS fixture",
        machine_type="beam_line",
        controller="neutral-test-controller",
        supported_formats=["neutral_job"],
        supported_operations=list(operations if operations is not None else ["mark"]),
        min_dimensions_mm={"length_mm": 1.0},
        max_dimensions_mm={"length_mm": float(max_length)},
        tools=list(default_tools if tools is None else tools),
        postprocessor_version="unreleased-test-only",
        enabled=True,
    )


class ViewerV15MachineCapabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.part = _part()
        self.faces = _face_report(self.part)
        self.marks = ContactScribingEngine().build(self.part, self.faces, _contact_report())
        self.identification = IdentificationPlanner().build(
            self.part,
            self.faces,
            mark_set=self.marks,
            hole_references=(
                HoleReferenceInput(
                    reference_id="REF-H1",
                    part_id=self.part.internal_id,
                    face_id="FACE-MAIN",
                    center_2d=(50.0, 50.0),
                    diameter_mm=10.0,
                    source_hole_id="HOLE-1",
                ),
            ),
            text_requests=(
                IdentificationTextRequest(
                    request_id="TXT-1",
                    part_id=self.part.internal_id,
                    face_id="FACE-MAIN",
                    text="M001-P1",
                    anchor_2d=(50.0, 50.0),
                    text_height_mm=5.0,
                ),
            ),
        )

    def _machine(self, **kwargs) -> MachineProfile:
        return _machine(self.marks.ruleset_sha256, self.identification.ruleset_sha256, **kwargs)

    def _evaluate(self, machine: MachineProfile):
        return MachineCapabilityEvaluator(machine).evaluate(
            self.part,
            self.faces,
            mark_set=self.marks,
            identification_set=self.identification,
        )

    def test_explicit_machine_profile_supports_all_marking_intents(self) -> None:
        report = self._evaluate(self._machine())
        self.assertEqual(6, len(report.decisions))
        self.assertTrue(all(item.status is CapabilityStatus.SUPPORTED for item in report.decisions))
        self.assertTrue(all(item.machine_operation == "mark" for item in report.decisions))
        self.assertTrue(report.marking_reachable)
        self.assertTrue(report.ready_for_neutral_job)
        self.assertFalse(report.machine_transfer_allowed)
        self.assertEqual(
            {MachineFeatureType.SCRIBE, MachineFeatureType.HOLE_REFERENCE, MachineFeatureType.IDENTIFICATION_TEXT},
            {item.feature_type for item in report.decisions},
        )

    def test_missing_reachability_metadata_fails_closed(self) -> None:
        tools = self._machine().tools
        tools[0] = {key: value for key, value in tools[0].items() if key != "reachable_face_roles"}
        report = self._evaluate(self._machine(tools=tools))
        scribe = [item for item in report.decisions if item.feature_type is MachineFeatureType.SCRIBE]
        self.assertTrue(all(CWS_MACHINE_REACHABILITY_UNKNOWN in item.blocking_codes for item in scribe))
        self.assertFalse(report.marking_reachable)

    def test_machine_segment_limit_is_not_guessed(self) -> None:
        tools = self._machine().tools
        tools[0] = {**tools[0], "max_segment_length_mm": 50.0}
        report = self._evaluate(self._machine(tools=tools))
        scribe = [item for item in report.decisions if item.feature_type is MachineFeatureType.SCRIBE]
        self.assertTrue(any(CWS_MACHINE_LIMIT_EXCEEDED in item.blocking_codes for item in scribe))
        self.assertFalse(report.ready_for_neutral_job)

    def test_generic_mark_operation_is_required(self) -> None:
        report = self._evaluate(self._machine(operations=["saw", "drill"]))
        self.assertTrue(all(CWS_MACHINE_OPERATION_UNSUPPORTED in item.blocking_codes for item in report.decisions))
        self.assertFalse(report.marking_reachable)

    def test_text_height_limit_is_machine_profile_evidence(self) -> None:
        tools = self._machine().tools
        tools[2] = {**tools[2], "max_text_height_mm": 4.0}
        report = self._evaluate(self._machine(tools=tools))
        text = [item for item in report.decisions if item.feature_type is MachineFeatureType.IDENTIFICATION_TEXT][0]
        self.assertIn(CWS_MACHINE_LIMIT_EXCEEDED, text.blocking_codes)

    def test_part_dimension_limit_blocks_capability_report(self) -> None:
        report = self._evaluate(self._machine(max_length=50.0))
        self.assertIn(CWS_MACHINE_PART_DIMENSION, report.blocking_codes)
        self.assertFalse(report.marking_reachable)

    def test_ambiguous_tools_are_not_silently_chosen(self) -> None:
        tools = self._machine().tools
        tools.append({**tools[0], "tool_id": "SCRIBE-2"})
        report = self._evaluate(self._machine(tools=tools))
        scribe = [item for item in report.decisions if item.feature_type is MachineFeatureType.SCRIBE]
        self.assertTrue(all(CWS_MACHINE_TOOL_AMBIGUOUS in item.blocking_codes for item in scribe))
        self.assertTrue(all(not item.tool_id for item in scribe))

    def test_head_clearance_is_explicit_machine_evidence(self) -> None:
        tools = self._machine().tools
        tools[0] = {**tools[0], "minimum_head_clearance_mm": 25.0}
        report = self._evaluate(self._machine(tools=tools))
        scribe = [item for item in report.decisions if item.feature_type is MachineFeatureType.SCRIBE]
        self.assertTrue(any(CWS_MACHINE_HEAD_CLEARANCE in item.blocking_codes for item in scribe))
        tools[0] = {key: value for key, value in tools[0].items() if key != "minimum_head_clearance_mm"}
        unknown = self._evaluate(self._machine(tools=tools))
        scribe_unknown = [item for item in unknown.decisions if item.feature_type is MachineFeatureType.SCRIBE]
        self.assertTrue(any(CWS_MACHINE_HEAD_CLEARANCE_UNKNOWN in item.blocking_codes for item in scribe_unknown))

    def test_ruleset_machine_compatibility_is_hashed_and_fail_closed(self) -> None:
        tools = self._machine().tools
        tools[0] = {**tools[0], "compatible_ruleset_sha256s": ["0" * 64]}
        report = self._evaluate(self._machine(tools=tools))
        scribe = [item for item in report.decisions if item.feature_type is MachineFeatureType.SCRIBE]
        self.assertTrue(all(CWS_MACHINE_RULESET_INCOMPATIBLE in item.blocking_codes for item in scribe))

    def test_machine_capability_report_is_deterministic(self) -> None:
        machine = self._machine()
        report1 = self._evaluate(machine)
        report2 = self._evaluate(machine)
        self.assertEqual(report1.report_sha256, report2.report_sha256)
        self.assertEqual(
            [item.decision_sha256 for item in report1.decisions],
            [item.decision_sha256 for item in report2.decisions],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
