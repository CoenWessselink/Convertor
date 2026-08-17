from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
for entry in (ROOT, TESTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from viewer_v15_machine_capability_smoke import _contact_report, _face_report, _machine, _part
from viewer_v15_nesting_binding_smoke import _transform

from cws_convertor.manufacturing.identification import IdentificationPlanner
from cws_convertor.manufacturing.identification_model import HoleReferenceInput, IdentificationTextRequest
from cws_convertor.manufacturing.machine_capability import MachineCapabilityEvaluator
from cws_convertor.manufacturing.marking import ContactScribingEngine
from cws_convertor.manufacturing.nesting_binding import NestingMarkBinder
from cws_convertor.manufacturing.nesting_binding_model import NestingPlacement
from cws_convertor.manufacturing.neutral_job import (
    CWS_JOB_DEPENDENCY_CYCLE,
    CWS_JOB_MISSING_DEPENDENCY,
    CWS_JOB_OPERATION_BLOCKED,
    NeutralJobBuilder,
    OperationDagValidator,
)
from cws_convertor.manufacturing.neutral_job_model import (
    ExistingCapabilityProof,
    NeutralOperation,
    NeutralOperationKind,
    NeutralOperationStatus,
    NeutralStock,
    ProcessOperationIntent,
)


class ViewerV15NeutralJobTests(unittest.TestCase):
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
        machine = _machine(self.marks.ruleset_sha256, self.identification.ruleset_sha256)
        self.capability = MachineCapabilityEvaluator(machine).evaluate(
            self.part,
            self.faces,
            mark_set=self.marks,
            identification_set=self.identification,
        )
        self.placement = NestingPlacement(
            nesting_run_id="NEST-001",
            stock_id="BAR-001",
            stock_kind="bar",
            part_id=self.part.internal_id,
            production_instance_id="PI-001",
            manufacturing_hash=self.part.manufacturing_hash,
            part_to_stock=_transform(tx=1000.0, ty=200.0),
            assembly_id="A-001",
            assembly_mark="M001",
            provenance={"source": "explicit-test-placement"},
        )
        self.nesting = NestingMarkBinder(self.placement).build(
            self.part,
            self.faces,
            self.capability,
            mark_set=self.marks,
            identification_set=self.identification,
        )
        self.assertTrue(self.nesting.ready_for_neutral_job)
        self.stock = NeutralStock(
            stock_id="BAR-001",
            stock_kind="bar",
            source_evidence_sha256="b" * 64,
            length_mm=6000.0,
            profile="PL100x10",
            material="S355J2",
        )
        self.builder = NeutralJobBuilder()

    def proof(self, kind: NeutralOperationKind, *, supported=True, tool_id=None) -> ExistingCapabilityProof:
        return ExistingCapabilityProof(
            proof_id=f"PROOF-{kind.value.upper()}",
            operation_kind=kind,
            machine_profile_sha256=self.capability.machine_profile_sha256,
            tool_id=tool_id or f"TOOL-{kind.value.upper()}",
            source_evidence_sha256=(kind.value[0] * 64),
            supported=supported,
            constraints={"provenance": "existing-capability-layer-test"},
        )

    def saw_intent(self, *, predecessors=(), supported=True, duration=12.5) -> ProcessOperationIntent:
        return ProcessOperationIntent(
            intent_id="SAW-END-1",
            operation_kind=NeutralOperationKind.SAW,
            part_instance_id=self.placement.production_instance_id,
            stock_id=self.placement.stock_id,
            target_face_id="END-FINISH",
            geometry_stock_mm={
                "cut_plane_origin_stock_mm": [1100.0, 200.0, 0.0],
                "cut_plane_normal_stock": [1.0, 0.0, 0.0],
                "saw_angle_deg": 90.0,
            },
            capability_proof=self.proof(NeutralOperationKind.SAW, supported=supported),
            predecessor_ids=tuple(predecessors),
            estimated_duration_s=duration,
            source_evidence_sha256="1" * 64,
        )

    def drill_intent(self, *, predecessors=(), supported=True, duration=None) -> ProcessOperationIntent:
        return ProcessOperationIntent(
            intent_id="DRILL-1",
            operation_kind=NeutralOperationKind.DRILL,
            part_instance_id=self.placement.production_instance_id,
            stock_id=self.placement.stock_id,
            target_face_id="FACE-MAIN",
            geometry_stock_mm={
                "center_stock_mm": [1050.0, 250.0, 0.0],
                "axis_stock": [0.0, 0.0, 1.0],
                "diameter_mm": 14.0,
            },
            capability_proof=self.proof(NeutralOperationKind.DRILL, supported=supported),
            predecessor_ids=tuple(predecessors),
            estimated_duration_s=duration,
            source_evidence_sha256="2" * 64,
        )

    def build(self, *, process=(), mark_predecessors=None):
        return self.builder.build(
            job_id="JOB-001",
            project_id="PROJECT-001",
            nesting_reports=(self.nesting,),
            machine_capabilities={self.placement.production_instance_id: self.capability},
            stocks=(self.stock,),
            process_intents=tuple(process),
            mark_predecessors=mark_predecessors,
        )

    def test_neutral_job_integrates_saw_drill_and_mark_without_machine_code(self) -> None:
        job = self.build(process=(self.saw_intent(), self.drill_intent()))
        self.assertEqual(8, len(job.operations))
        self.assertEqual(
            {NeutralOperationKind.SAW, NeutralOperationKind.DRILL, NeutralOperationKind.MARK},
            {item.operation_kind for item in job.operations},
        )
        self.assertTrue(job.ready_for_postprocessor)
        self.assertFalse(job.machine_transfer_allowed)
        self.assertEqual(self.placement.production_instance_id, job.pieces[0].part_instance_id)
        self.assertEqual(self.nesting.instance_variant_sha256, job.pieces[0].instance_variant_sha256)

    def test_builder_does_not_invent_global_saw_drill_mark_order(self) -> None:
        job = self.build(process=(self.saw_intent(), self.drill_intent()))
        self.assertTrue(all(not item.predecessor_ids for item in job.operations))
        self.assertEqual(len(job.operations), len(job.execution_order))

    def test_explicit_dependency_policy_is_preserved_exactly(self) -> None:
        saw = self.saw_intent()
        saw_id = self.builder.process_operation_id(saw)
        drill = self.drill_intent(predecessors=(saw_id,))
        drill_id = self.builder.process_operation_id(drill)
        mark_dependencies = {feature.source_feature_id: (drill_id,) for feature in self.nesting.features}
        job = self.build(process=(saw, drill), mark_predecessors=mark_dependencies)
        by_kind = {item.operation_id: item for item in job.operations}
        self.assertEqual((saw_id,), by_kind[drill_id].predecessor_ids)
        for operation in job.operations:
            if operation.operation_kind is NeutralOperationKind.MARK:
                self.assertEqual((drill_id,), operation.predecessor_ids)
        positions = {operation_id: index for index, operation_id in enumerate(job.execution_order)}
        self.assertLess(positions[saw_id], positions[drill_id])
        self.assertTrue(all(positions[drill_id] < positions[item.operation_id] for item in job.operations if item.operation_kind is NeutralOperationKind.MARK))

    def test_cycle_is_detected_independently(self) -> None:
        common = dict(
            part_instance_id="PI-001",
            part_id="P-MAIN",
            stock_id="BAR-001",
            target_face_id="FACE-MAIN",
            source_evidence_sha256="a" * 64,
            tool_id="T1",
            capability_proof_sha256="b" * 64,
            geometry_stock_mm={},
            status=NeutralOperationStatus.READY,
        )
        a = NeutralOperation(
            operation_id="A",
            operation_kind=NeutralOperationKind.SAW,
            source_feature_id="SAW-A",
            predecessor_ids=("B",),
            **common,
        )
        b = NeutralOperation(
            operation_id="B",
            operation_kind=NeutralOperationKind.DRILL,
            source_feature_id="DRILL-B",
            predecessor_ids=("A",),
            **common,
        )
        order, blockers = OperationDagValidator.validate((a, b))
        self.assertEqual((), order)
        self.assertIn(CWS_JOB_DEPENDENCY_CYCLE, blockers)

    def test_missing_predecessor_is_not_silently_ignored(self) -> None:
        operation = NeutralOperation(
            operation_id="A",
            operation_kind=NeutralOperationKind.SAW,
            part_instance_id="PI-001",
            part_id="P-MAIN",
            stock_id="BAR-001",
            target_face_id="FACE-MAIN",
            source_feature_id="SAW-A",
            source_evidence_sha256="a" * 64,
            tool_id="T1",
            capability_proof_sha256="b" * 64,
            geometry_stock_mm={},
            predecessor_ids=("MISSING",),
            status=NeutralOperationStatus.READY,
        )
        order, blockers = OperationDagValidator.validate((operation,))
        self.assertEqual((), order)
        self.assertIn(CWS_JOB_MISSING_DEPENDENCY, blockers)

    def test_unsupported_existing_process_proof_blocks_neutral_job(self) -> None:
        job = self.build(process=(self.saw_intent(supported=False),))
        saw = next(item for item in job.operations if item.operation_kind is NeutralOperationKind.SAW)
        self.assertFalse(saw.ready)
        self.assertIn(CWS_JOB_OPERATION_BLOCKED, job.blocking_codes)
        self.assertFalse(job.ready_for_postprocessor)

    def test_duration_is_only_present_when_explicitly_supplied(self) -> None:
        job = self.build(process=(self.saw_intent(duration=12.5), self.drill_intent(duration=None)))
        saw = next(item for item in job.operations if item.operation_kind is NeutralOperationKind.SAW)
        drill = next(item for item in job.operations if item.operation_kind is NeutralOperationKind.DRILL)
        self.assertEqual(12.5, saw.estimated_duration_s)
        self.assertIsNone(drill.estimated_duration_s)
        self.assertTrue(all(item.estimated_duration_s is None for item in job.operations if item.operation_kind is NeutralOperationKind.MARK))

    def test_job_and_execution_order_are_deterministic(self) -> None:
        saw = self.saw_intent()
        saw_id = self.builder.process_operation_id(saw)
        drill = self.drill_intent(predecessors=(saw_id,))
        job1 = self.build(process=(saw, drill))
        job2 = self.build(process=(saw, drill))
        self.assertEqual(job1.job_sha256, job2.job_sha256)
        self.assertEqual(job1.execution_order, job2.execution_order)
        self.assertEqual(
            [item.operation_sha256 for item in job1.operations],
            [item.operation_sha256 for item in job2.operations],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
