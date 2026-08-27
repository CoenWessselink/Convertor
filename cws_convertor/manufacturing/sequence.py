"""Independent validation for the neutral manufacturing operation sequence."""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Iterable, Mapping, Sequence

from .neutral_job_model import NeutralOperation, NeutralOperationKind, NeutralOperationStatus


MARK_KINDS = {
    NeutralOperationKind.MARK,
    NeutralOperationKind.SCRIBE,
    NeutralOperationKind.POP,
    NeutralOperationKind.TEXT,
}
CUT_KINDS = {
    NeutralOperationKind.DRILL,
    NeutralOperationKind.PUNCH,
    NeutralOperationKind.CONTOUR,
    NeutralOperationKind.SAW,
    NeutralOperationKind.COMMON_CUT,
}


@dataclass(frozen=True)
class SequenceValidationResult:
    valid: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    ordered_operation_ids: tuple[str, ...] = ()


class IndependentOperationSequenceValidator:
    """Validate prerequisites without trusting the sequence producer."""

    def validate(
        self,
        operations: Sequence[NeutralOperation],
        *,
        expected_mark_ids: Iterable[str] = (),
        machine_capabilities: Mapping[str, bool] | None = None,
    ) -> SequenceValidationResult:
        blockers: list[str] = []
        warnings: list[str] = []
        by_id: dict[str, NeutralOperation] = {}
        for operation in operations:
            if operation.operation_id in by_id:
                blockers.append(f"Dubbele operation_id: {operation.operation_id}")
            by_id[operation.operation_id] = operation

        for operation in operations:
            for predecessor in operation.predecessor_ids:
                if predecessor not in by_id:
                    blockers.append(f"{operation.operation_id}: ontbrekende predecessor {predecessor}")

        visiting: set[str] = set()
        visited: set[str] = set()
        ordered: list[str] = []

        def visit(operation_id: str) -> None:
            if operation_id in visited:
                return
            if operation_id in visiting:
                blockers.append(f"Cyclus in operation-DAG bij {operation_id}")
                return
            visiting.add(operation_id)
            operation = by_id[operation_id]
            for predecessor in operation.predecessor_ids:
                if predecessor in by_id:
                    visit(predecessor)
            visiting.remove(operation_id)
            visited.add(operation_id)
            ordered.append(operation_id)

        for operation_id in tuple(by_id):
            visit(operation_id)

        position = {operation_id: index for index, operation_id in enumerate(ordered)}
        load_positions = [position[op.operation_id] for op in operations if op.operation_kind is NeutralOperationKind.LOAD]
        clamp_positions = [
            position[op.operation_id]
            for op in operations
            if op.operation_kind in {NeutralOperationKind.CLAMP, NeutralOperationKind.RECLAMP}
        ]
        sever_positions = [position[op.operation_id] for op in operations if op.operation_kind is NeutralOperationKind.SEVER]
        unload_positions = [position[op.operation_id] for op in operations if op.operation_kind is NeutralOperationKind.UNLOAD]
        production_positions = [position[op.operation_id] for op in operations if op.operation_kind in MARK_KINDS | CUT_KINDS]

        if production_positions and (not load_positions or min(load_positions) > min(production_positions)):
            blockers.append("Productieoperaties vereisen load voor bewerking")
        if production_positions and (not clamp_positions or min(clamp_positions) > min(production_positions)):
            blockers.append("Productieoperaties vereisen clamp/reclamp voor bewerking")
        if sever_positions:
            first_sever = min(sever_positions)
            for operation in operations:
                if operation.operation_kind in MARK_KINDS and position[operation.operation_id] > first_sever:
                    blockers.append(f"Markering {operation.operation_id} staat na sever")
        if unload_positions and production_positions and min(unload_positions) < max(production_positions):
            blockers.append("Unload staat voor de laatste productieoperatie")

        produced_marks = {
            str(operation.geometry_stock_mm.get("mark_id", operation.source_feature_id))
            for operation in operations
            if operation.operation_kind in MARK_KINDS
        }
        missing_marks = sorted({str(value) for value in expected_mark_ids} - produced_marks)
        if missing_marks:
            blockers.append("Markeringen verloren in sequence: " + ", ".join(missing_marks))

        capabilities = dict(machine_capabilities or {})
        for operation in operations:
            if operation.operation_kind in MARK_KINDS | CUT_KINDS:
                if operation.status is not NeutralOperationStatus.READY or not operation.ready:
                    blockers.append(f"{operation.operation_id}: operatie is niet ready")
                if operation.geometry_stock_mm.get("clamp_conflict"):
                    blockers.append(f"{operation.operation_id}: clamp conflict")
                capability_key = str(operation.geometry_stock_mm.get("capability", operation.operation_kind.value))
                if capabilities and not capabilities.get(capability_key, False):
                    blockers.append(f"{operation.operation_id}: capability {capability_key} ontbreekt")
            if operation.operation_kind is NeutralOperationKind.COMMON_CUT and not operation.geometry_stock_mm.get(
                "shared_boundary_proof"
            ):
                blockers.append(f"{operation.operation_id}: common-cut bewijs ontbreekt")

        return SequenceValidationResult(
            valid=not blockers,
            blockers=tuple(dict.fromkeys(blockers)),
            warnings=tuple(dict.fromkeys(warnings)),
            ordered_operation_ids=tuple(ordered),
        )


@dataclass(frozen=True)
class PlannedNeutralSequence:
    operations: tuple[NeutralOperation, ...]
    validation: SequenceValidationResult


class NeutralSequencePlanner:
    """Wrap proven nesting operations in deterministic handling prerequisites."""

    def build(
        self,
        operations: Sequence[NeutralOperation],
        *,
        authority_sha256: str,
        expected_mark_ids: Iterable[str] = (),
        machine_capabilities: Mapping[str, bool] | None = None,
    ) -> PlannedNeutralSequence:
        if not authority_sha256:
            raise ValueError("Sequence planning vereist frozen-authority bewijs")
        grouped: dict[str, list[NeutralOperation]] = {}
        for operation in operations:
            grouped.setdefault(operation.stock_id, []).append(operation)
        planned: list[NeutralOperation] = []
        for stock_id in sorted(grouped):
            stock_operations = sorted(grouped[stock_id], key=lambda item: item.operation_id)
            load_id = f"{stock_id}:load"
            clamp_id = f"{stock_id}:clamp"
            planned.append(self._handling_operation(load_id, NeutralOperationKind.LOAD, stock_id, (), authority_sha256))
            planned.append(
                self._handling_operation(clamp_id, NeutralOperationKind.CLAMP, stock_id, (load_id,), authority_sha256)
            )
            production_ids: list[str] = []
            for operation in stock_operations:
                kind = self._normalized_kind(operation)
                predecessors = tuple(dict.fromkeys((*operation.predecessor_ids, clamp_id)))
                normalized = replace(
                    operation,
                    operation_kind=kind,
                    predecessor_ids=predecessors,
                    operation_sha256="",
                )
                planned.append(normalized)
                production_ids.append(normalized.operation_id)
            sever_id = f"{stock_id}:sever"
            unload_id = f"{stock_id}:unload"
            planned.append(
                self._handling_operation(
                    sever_id,
                    NeutralOperationKind.SEVER,
                    stock_id,
                    tuple(production_ids) or (clamp_id,),
                    authority_sha256,
                )
            )
            planned.append(
                self._handling_operation(
                    unload_id,
                    NeutralOperationKind.UNLOAD,
                    stock_id,
                    (sever_id,),
                    authority_sha256,
                )
            )
        validation = IndependentOperationSequenceValidator().validate(
            tuple(planned),
            expected_mark_ids=expected_mark_ids,
            machine_capabilities=machine_capabilities,
        )
        return PlannedNeutralSequence(tuple(planned), validation)

    @staticmethod
    def _normalized_kind(operation: NeutralOperation) -> NeutralOperationKind:
        if operation.operation_kind is not NeutralOperationKind.MARK:
            return operation.operation_kind
        raw = str(operation.geometry_stock_mm.get("mark_kind", "mark")).lower()
        return {
            "scribe": NeutralOperationKind.SCRIBE,
            "scribe_segment": NeutralOperationKind.SCRIBE,
            "pop": NeutralOperationKind.POP,
            "hole_reference": NeutralOperationKind.POP,
            "text": NeutralOperationKind.TEXT,
            "identification_text": NeutralOperationKind.TEXT,
        }.get(raw, NeutralOperationKind.MARK)

    @staticmethod
    def _handling_operation(
        operation_id: str,
        kind: NeutralOperationKind,
        stock_id: str,
        predecessor_ids: tuple[str, ...],
        authority_sha256: str,
    ) -> NeutralOperation:
        proof = sha256(f"{authority_sha256}:{kind.value}:{stock_id}".encode("utf-8")).hexdigest()
        return NeutralOperation(
            operation_id=operation_id,
            operation_kind=kind,
            part_instance_id=f"stock:{stock_id}",
            part_id=f"stock:{stock_id}",
            stock_id=stock_id,
            target_face_id=f"stock:{stock_id}",
            source_feature_id=operation_id,
            source_evidence_sha256=authority_sha256,
            tool_id=f"handling:{kind.value}",
            capability_proof_sha256=proof,
            geometry_stock_mm={"system_operation": True, "capability": kind.value},
            predecessor_ids=predecessor_ids,
            status=NeutralOperationStatus.READY,
        )


__all__ = [
    "IndependentOperationSequenceValidator",
    "NeutralSequencePlanner",
    "PlannedNeutralSequence",
    "SequenceValidationResult",
]
