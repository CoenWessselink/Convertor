"""M7 neutral operation DAG builder and validator."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

from cws_convertor.project.model import stable_sha256

from .machine_capability_model import MachineCapabilityReport
from .nesting_binding_model import NestingMarkingReport
from .neutral_job_model import (
    ExistingCapabilityProof,
    NeutralManufacturingJob,
    NeutralOperation,
    NeutralOperationKind,
    NeutralOperationStatus,
    NeutralPiece,
    NeutralStock,
    ProcessOperationIntent,
)

CWS_JOB_NESTING_NOT_READY = "CWS-JOB-001"
CWS_JOB_PROCESS_PROOF_BLOCKED = "CWS-JOB-002"
CWS_JOB_STOCK_MISMATCH = "CWS-JOB-003"
CWS_JOB_INSTANCE_MISMATCH = "CWS-JOB-004"
CWS_JOB_DUPLICATE_OPERATION = "CWS-JOB-005"
CWS_JOB_MISSING_DEPENDENCY = "CWS-JOB-006"
CWS_JOB_DEPENDENCY_CYCLE = "CWS-JOB-007"
CWS_JOB_MARK_PROOF_MISMATCH = "CWS-JOB-008"
CWS_JOB_OPERATION_BLOCKED = "CWS-JOB-009"
CWS_JOB_STOCK_MISSING = "CWS-JOB-010"
CWS_JOB_MACHINE_PROFILE_MISMATCH = "CWS-JOB-011"
CWS_JOB_PROCESS_INTENT_MISMATCH = "CWS-JOB-012"


def _mark_operation_id(nested_feature_id: str) -> str:
    return "OP-MARK-" + stable_sha256({"nested_feature_id": nested_feature_id})[:20].upper()


def _process_operation_id(intent: ProcessOperationIntent) -> str:
    return "OP-" + intent.operation_kind.value.upper() + "-" + stable_sha256(
        {"intent_id": intent.intent_id, "intent_sha256": intent.intent_sha256}
    )[:20].upper()


class OperationDagValidator:
    """Validate exact predecessor references and produce deterministic topo order."""

    @staticmethod
    def validate(operations: Iterable[NeutralOperation]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        items = tuple(operations)
        by_id: dict[str, NeutralOperation] = {}
        blockers: list[str] = []
        for operation in items:
            if operation.operation_id in by_id:
                blockers.append(CWS_JOB_DUPLICATE_OPERATION)
            by_id[operation.operation_id] = operation
        if len(by_id) != len(items):
            return (), tuple(dict.fromkeys(blockers))

        indegree = {operation_id: 0 for operation_id in by_id}
        outgoing: dict[str, list[str]] = defaultdict(list)
        for operation in items:
            for predecessor in operation.predecessor_ids:
                if predecessor not in by_id or predecessor == operation.operation_id:
                    blockers.append(CWS_JOB_MISSING_DEPENDENCY)
                    continue
                outgoing[predecessor].append(operation.operation_id)
                indegree[operation.operation_id] += 1

        if CWS_JOB_MISSING_DEPENDENCY in blockers:
            return (), tuple(dict.fromkeys(blockers))

        ready = sorted(operation_id for operation_id, degree in indegree.items() if degree == 0)
        order: list[str] = []
        while ready:
            current = ready.pop(0)
            order.append(current)
            for target in sorted(outgoing.get(current, [])):
                indegree[target] -= 1
                if indegree[target] == 0:
                    ready.append(target)
                    ready.sort()
        if len(order) != len(items):
            blockers.append(CWS_JOB_DEPENDENCY_CYCLE)
            return (), tuple(dict.fromkeys(blockers))
        return tuple(order), tuple(dict.fromkeys(blockers))


class NeutralJobBuilder:
    """Create one deterministic neutral job without generating machine code."""

    @staticmethod
    def mark_operation_id(nested_feature_id: str) -> str:
        return _mark_operation_id(nested_feature_id)

    @staticmethod
    def process_operation_id(intent: ProcessOperationIntent) -> str:
        return _process_operation_id(intent)

    @staticmethod
    def _piece(report: NestingMarkingReport) -> NeutralPiece:
        return NeutralPiece(
            part_instance_id=report.production_instance_id,
            part_id=report.part_id,
            manufacturing_hash=report.manufacturing_hash,
            instance_variant_sha256=report.instance_variant_sha256,
            stock_id=report.stock_id,
            nesting_run_id=report.nesting_run_id,
            placement_sha256=report.placement_sha256,
            assembly_id=report.assembly_id,
            assembly_mark=report.assembly_mark,
        )

    @staticmethod
    def _mark_operations(
        report: NestingMarkingReport,
        capability: MachineCapabilityReport,
        predecessors_by_source_feature: Mapping[str, Iterable[str]],
    ) -> tuple[list[NeutralOperation], list[str]]:
        operations: list[NeutralOperation] = []
        blockers: list[str] = []
        decisions = {item.feature_id: item for item in capability.decisions}
        for feature in sorted(report.features, key=lambda item: item.feature_id):
            decision = decisions.get(feature.source_feature_id)
            operation_blockers: list[str] = []
            if not report.ready_for_neutral_job or not feature.production_usable:
                operation_blockers.append(CWS_JOB_NESTING_NOT_READY)
            if decision is None or feature.machine_decision_sha256 != decision.decision_sha256:
                operation_blockers.append(CWS_JOB_MARK_PROOF_MISMATCH)
            elif not decision.supported:
                operation_blockers.append(CWS_JOB_MARK_PROOF_MISMATCH)
            operation_blockers = list(dict.fromkeys(operation_blockers))
            blockers.extend(operation_blockers)
            status = NeutralOperationStatus.BLOCKED if operation_blockers else NeutralOperationStatus.READY
            operation_id = _mark_operation_id(feature.feature_id)
            operations.append(
                NeutralOperation(
                    operation_id=operation_id,
                    operation_kind=NeutralOperationKind.MARK,
                    part_instance_id=report.production_instance_id,
                    part_id=report.part_id,
                    stock_id=report.stock_id,
                    target_face_id=feature.face_id,
                    source_feature_id=feature.source_feature_id,
                    source_evidence_sha256=feature.feature_sha256,
                    tool_id="" if decision is None else decision.tool_id,
                    capability_proof_sha256="" if decision is None else decision.decision_sha256,
                    geometry_stock_mm=feature.geometry_stock_mm,
                    predecessor_ids=tuple(predecessors_by_source_feature.get(feature.source_feature_id, ())),
                    status=status,
                    blocking_codes=tuple(operation_blockers),
                )
            )
        return operations, blockers

    @staticmethod
    def _process_operation(
        intent: ProcessOperationIntent,
        *,
        piece: NeutralPiece,
        machine_profile_sha256: str,
    ) -> tuple[NeutralOperation, list[str]]:
        blockers: list[str] = []
        proof: ExistingCapabilityProof = intent.capability_proof
        if intent.part_instance_id != piece.part_instance_id or intent.stock_id != piece.stock_id:
            blockers.append(CWS_JOB_PROCESS_INTENT_MISMATCH)
        if proof.machine_profile_sha256 != machine_profile_sha256:
            blockers.append(CWS_JOB_MACHINE_PROFILE_MISMATCH)
        if not proof.supported:
            blockers.append(CWS_JOB_PROCESS_PROOF_BLOCKED)
        blockers = list(dict.fromkeys(blockers))
        status = NeutralOperationStatus.BLOCKED if blockers else NeutralOperationStatus.READY
        return (
            NeutralOperation(
                operation_id=_process_operation_id(intent),
                operation_kind=intent.operation_kind,
                part_instance_id=intent.part_instance_id,
                part_id=piece.part_id,
                stock_id=intent.stock_id,
                target_face_id=intent.target_face_id,
                source_feature_id=intent.intent_id,
                source_evidence_sha256=intent.source_evidence_sha256,
                tool_id=proof.tool_id,
                capability_proof_sha256=proof.proof_sha256,
                geometry_stock_mm=intent.geometry_stock_mm,
                predecessor_ids=intent.predecessor_ids,
                status=status,
                estimated_duration_s=intent.estimated_duration_s,
                blocking_codes=tuple(blockers),
            ),
            blockers,
        )

    def build(
        self,
        *,
        job_id: str,
        project_id: str,
        nesting_reports: Iterable[NestingMarkingReport],
        machine_capabilities: Mapping[str, MachineCapabilityReport],
        stocks: Iterable[NeutralStock],
        process_intents: Iterable[ProcessOperationIntent] = (),
        mark_predecessors: Mapping[str, Iterable[str]] | None = None,
    ) -> NeutralManufacturingJob:
        reports = tuple(sorted(nesting_reports, key=lambda item: item.production_instance_id))
        stock_items = tuple(sorted(stocks, key=lambda item: item.stock_id))
        stock_by_id = {item.stock_id: item for item in stock_items}
        pieces = tuple(self._piece(report) for report in reports)
        piece_by_id = {item.part_instance_id: item for item in pieces}
        blockers: list[str] = []
        warnings: list[str] = []
        operations: list[NeutralOperation] = []
        mark_predecessors = dict(mark_predecessors or {})

        machine_profiles = {
            (capability.machine_profile_id, capability.machine_id, capability.machine_profile_sha256)
            for capability in machine_capabilities.values()
        }
        if len(machine_profiles) != 1:
            blockers.append(CWS_JOB_MACHINE_PROFILE_MISMATCH)
            machine_profile_id = "UNRESOLVED"
            machine_id = "UNRESOLVED"
            machine_profile_sha256 = stable_sha256({"machine_profiles": sorted(machine_profiles)})
        else:
            machine_profile_id, machine_id, machine_profile_sha256 = next(iter(machine_profiles))

        for report in reports:
            if report.stock_id not in stock_by_id:
                blockers.append(CWS_JOB_STOCK_MISSING)
            capability = machine_capabilities.get(report.production_instance_id)
            if capability is None:
                blockers.append(CWS_JOB_MARK_PROOF_MISMATCH)
                continue
            if capability.machine_profile_sha256 != machine_profile_sha256:
                blockers.append(CWS_JOB_MACHINE_PROFILE_MISMATCH)
            mark_ops, mark_blockers = self._mark_operations(report, capability, mark_predecessors)
            operations.extend(mark_ops)
            blockers.extend(mark_blockers)

        for intent in sorted(process_intents, key=lambda item: item.intent_id):
            piece = piece_by_id.get(intent.part_instance_id)
            if piece is None:
                blockers.append(CWS_JOB_INSTANCE_MISMATCH)
                continue
            if intent.stock_id not in stock_by_id:
                blockers.append(CWS_JOB_STOCK_MISSING)
            operation, operation_blockers = self._process_operation(
                intent,
                piece=piece,
                machine_profile_sha256=machine_profile_sha256,
            )
            operations.append(operation)
            blockers.extend(operation_blockers)

        operation_ids = [item.operation_id for item in operations]
        if len(set(operation_ids)) != len(operation_ids):
            blockers.append(CWS_JOB_DUPLICATE_OPERATION)
        order, dag_blockers = OperationDagValidator.validate(operations)
        blockers.extend(dag_blockers)
        if any(not operation.ready for operation in operations):
            blockers.append(CWS_JOB_OPERATION_BLOCKED)

        blockers = list(dict.fromkeys(blockers))
        return NeutralManufacturingJob.create(
            job_id=job_id,
            project_id=project_id,
            machine_profile_id=machine_profile_id,
            machine_id=machine_id,
            machine_profile_sha256=machine_profile_sha256,
            stocks=stock_items,
            pieces=pieces,
            operations=tuple(sorted(operations, key=lambda item: item.operation_id)),
            execution_order=order,
            blocking_codes=tuple(blockers),
            warnings=tuple(warnings),
        )


__all__ = [
    "CWS_JOB_NESTING_NOT_READY", "CWS_JOB_PROCESS_PROOF_BLOCKED",
    "CWS_JOB_STOCK_MISMATCH", "CWS_JOB_INSTANCE_MISMATCH",
    "CWS_JOB_DUPLICATE_OPERATION", "CWS_JOB_MISSING_DEPENDENCY",
    "CWS_JOB_DEPENDENCY_CYCLE", "CWS_JOB_MARK_PROOF_MISMATCH",
    "CWS_JOB_OPERATION_BLOCKED", "CWS_JOB_STOCK_MISSING",
    "CWS_JOB_MACHINE_PROFILE_MISMATCH", "CWS_JOB_PROCESS_INTENT_MISMATCH",
    "OperationDagValidator", "NeutralJobBuilder",
]
