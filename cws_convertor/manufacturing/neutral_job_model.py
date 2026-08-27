"""M7 versioned neutral machine-job contracts.

This is a machine-neutral planning model, not proprietary machine code. The DAG
captures only explicit dependencies. It deliberately does not assume a global
saw -> drill -> mark order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Any, Iterable

from cws_convertor.project.model import stable_sha256

NEUTRAL_JOB_SCHEMA = "cws-neutral-manufacturing-job-2.0"
NEUTRAL_OPERATION_SCHEMA = "cws-neutral-operation-2.0"
NEUTRAL_JOB_ALGORITHM = "cws-operation-dag-builder-1.0"


class NeutralOperationKind(StrEnum):
    LOAD = "load"
    CLAMP = "clamp"
    REORIENT = "reorient"
    RECLAMP = "reclamp"
    MARK = "mark"
    SCRIBE = "scribe"
    POP = "pop"
    TEXT = "text"
    DRILL = "drill"
    PUNCH = "punch"
    CONTOUR = "contour"
    SAW = "saw"
    COMMON_CUT = "common_cut"
    SEVER = "sever"
    UNLOAD = "unload"


class NeutralOperationStatus(StrEnum):
    READY = "ready"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


def _vec3(value: Iterable[float], label: str) -> tuple[float, float, float]:
    items = tuple(float(item) for item in value)
    if len(items) != 3 or not all(math.isfinite(item) for item in items):
        raise ValueError(f"{label} vereist drie eindige coordinaten")
    return items


@dataclass(frozen=True, slots=True)
class NeutralStock:
    stock_id: str
    stock_kind: str
    source_evidence_sha256: str
    length_mm: float | None = None
    profile: str = ""
    material: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata or {}))
        if not self.stock_id.strip() or not self.stock_kind.strip() or not self.source_evidence_sha256.strip():
            raise ValueError("NeutralStock mist stock-identiteit of evidence")
        if self.length_mm is not None and (
            not math.isfinite(float(self.length_mm)) or float(self.length_mm) <= 0.0
        ):
            raise ValueError("NeutralStock length_mm moet positief zijn indien opgegeven")

    @property
    def stock_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "stock_id": self.stock_id,
            "stock_kind": self.stock_kind,
            "source_evidence_sha256": self.source_evidence_sha256,
            "length_mm": None if self.length_mm is None else float(self.length_mm),
            "profile": self.profile,
            "material": self.material,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class NeutralPiece:
    part_instance_id: str
    part_id: str
    manufacturing_hash: str
    instance_variant_sha256: str
    stock_id: str
    nesting_run_id: str
    placement_sha256: str
    assembly_id: str = ""
    assembly_mark: str = ""

    def __post_init__(self) -> None:
        for label, value in (
            ("part_instance_id", self.part_instance_id),
            ("part_id", self.part_id),
            ("manufacturing_hash", self.manufacturing_hash),
            ("instance_variant_sha256", self.instance_variant_sha256),
            ("stock_id", self.stock_id),
            ("nesting_run_id", self.nesting_run_id),
            ("placement_sha256", self.placement_sha256),
        ):
            if not str(value).strip():
                raise ValueError(f"NeutralPiece mist {label}")

    @property
    def piece_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "part_instance_id": self.part_instance_id,
            "part_id": self.part_id,
            "manufacturing_hash": self.manufacturing_hash,
            "instance_variant_sha256": self.instance_variant_sha256,
            "stock_id": self.stock_id,
            "nesting_run_id": self.nesting_run_id,
            "placement_sha256": self.placement_sha256,
            "assembly_id": self.assembly_id,
            "assembly_mark": self.assembly_mark,
        }


@dataclass(frozen=True, slots=True)
class ExistingCapabilityProof:
    proof_id: str
    operation_kind: NeutralOperationKind | str
    machine_profile_sha256: str
    tool_id: str
    source_evidence_sha256: str
    supported: bool
    constraints: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_kind", NeutralOperationKind(self.operation_kind))
        object.__setattr__(self, "constraints", dict(self.constraints or {}))
        for label, value in (
            ("proof_id", self.proof_id),
            ("machine_profile_sha256", self.machine_profile_sha256),
            ("tool_id", self.tool_id),
            ("source_evidence_sha256", self.source_evidence_sha256),
        ):
            if not str(value).strip():
                raise ValueError(f"ExistingCapabilityProof mist {label}")

    @property
    def proof_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "operation_kind": self.operation_kind.value,
            "machine_profile_sha256": self.machine_profile_sha256,
            "tool_id": self.tool_id,
            "source_evidence_sha256": self.source_evidence_sha256,
            "supported": bool(self.supported),
            "constraints": dict(self.constraints),
        }


@dataclass(frozen=True, slots=True)
class ProcessOperationIntent:
    intent_id: str
    operation_kind: NeutralOperationKind | str
    part_instance_id: str
    stock_id: str
    target_face_id: str
    geometry_stock_mm: dict[str, Any]
    capability_proof: ExistingCapabilityProof
    predecessor_ids: tuple[str, ...] = ()
    estimated_duration_s: float | None = None
    source_evidence_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_kind", NeutralOperationKind(self.operation_kind))
        if self.operation_kind in {
            NeutralOperationKind.MARK,
            NeutralOperationKind.SCRIBE,
            NeutralOperationKind.POP,
            NeutralOperationKind.TEXT,
        }:
            raise ValueError("Markeeroperaties worden uitsluitend uit bewezen nesting-markeringen opgebouwd")
        object.__setattr__(self, "geometry_stock_mm", dict(self.geometry_stock_mm or {}))
        object.__setattr__(self, "predecessor_ids", tuple(dict.fromkeys(self.predecessor_ids)))
        for label, value in (
            ("intent_id", self.intent_id),
            ("part_instance_id", self.part_instance_id),
            ("stock_id", self.stock_id),
            ("target_face_id", self.target_face_id),
            ("source_evidence_sha256", self.source_evidence_sha256),
        ):
            if not str(value).strip():
                raise ValueError(f"ProcessOperationIntent mist {label}")
        if self.capability_proof.operation_kind != self.operation_kind:
            raise ValueError("ProcessOperationIntent capability proof heeft verkeerd operation_kind")
        if self.estimated_duration_s is not None and (
            not math.isfinite(float(self.estimated_duration_s)) or float(self.estimated_duration_s) < 0.0
        ):
            raise ValueError("ProcessOperationIntent duration moet niet-negatief zijn")

    @property
    def intent_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "operation_kind": self.operation_kind.value,
            "part_instance_id": self.part_instance_id,
            "stock_id": self.stock_id,
            "target_face_id": self.target_face_id,
            "geometry_stock_mm": dict(self.geometry_stock_mm),
            "capability_proof": self.capability_proof.to_dict(),
            "predecessor_ids": list(self.predecessor_ids),
            "estimated_duration_s": None if self.estimated_duration_s is None else float(self.estimated_duration_s),
            "source_evidence_sha256": self.source_evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class NeutralOperation:
    operation_id: str
    operation_kind: NeutralOperationKind | str
    part_instance_id: str
    part_id: str
    stock_id: str
    target_face_id: str
    source_feature_id: str
    source_evidence_sha256: str
    tool_id: str
    capability_proof_sha256: str
    geometry_stock_mm: dict[str, Any]
    predecessor_ids: tuple[str, ...]
    status: NeutralOperationStatus | str
    estimated_duration_s: float | None = None
    blocking_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    operation_sha256: str = ""
    schema_version: str = NEUTRAL_OPERATION_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_kind", NeutralOperationKind(self.operation_kind))
        object.__setattr__(self, "status", NeutralOperationStatus(self.status))
        object.__setattr__(self, "geometry_stock_mm", dict(self.geometry_stock_mm or {}))
        object.__setattr__(self, "predecessor_ids", tuple(dict.fromkeys(self.predecessor_ids)))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        object.__setattr__(self, "warnings", tuple(dict.fromkeys(str(item) for item in self.warnings)))
        for label, value in (
            ("operation_id", self.operation_id),
            ("part_instance_id", self.part_instance_id),
            ("part_id", self.part_id),
            ("stock_id", self.stock_id),
            ("target_face_id", self.target_face_id),
            ("source_feature_id", self.source_feature_id),
            ("source_evidence_sha256", self.source_evidence_sha256),
        ):
            if not str(value).strip():
                raise ValueError(f"NeutralOperation mist {label}")
        if self.status == NeutralOperationStatus.READY:
            if not self.tool_id.strip():
                raise ValueError("READY NeutralOperation vereist tool_id")
            if not self.capability_proof_sha256.strip():
                raise ValueError("READY NeutralOperation vereist capability proof")
        if self.estimated_duration_s is not None and (
            not math.isfinite(float(self.estimated_duration_s)) or float(self.estimated_duration_s) < 0.0
        ):
            raise ValueError("NeutralOperation duration moet niet-negatief zijn")
        expected = stable_sha256(self.identity_payload())
        if self.operation_sha256 and self.operation_sha256 != expected:
            raise ValueError("NeutralOperation operation_sha256 klopt niet")
        object.__setattr__(self, "operation_sha256", expected)

    @property
    def ready(self) -> bool:
        return (
            self.status == NeutralOperationStatus.READY
            and bool(self.tool_id.strip())
            and bool(self.capability_proof_sha256.strip())
            and not self.blocking_codes
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation_id": self.operation_id,
            "operation_kind": self.operation_kind.value,
            "part_instance_id": self.part_instance_id,
            "part_id": self.part_id,
            "stock_id": self.stock_id,
            "target_face_id": self.target_face_id,
            "source_feature_id": self.source_feature_id,
            "source_evidence_sha256": self.source_evidence_sha256,
            "tool_id": self.tool_id,
            "capability_proof_sha256": self.capability_proof_sha256,
            "geometry_stock_mm": dict(self.geometry_stock_mm),
            "predecessor_ids": list(self.predecessor_ids),
            "status": self.status.value,
            "estimated_duration_s": None if self.estimated_duration_s is None else float(self.estimated_duration_s),
            "blocking_codes": list(self.blocking_codes),
            "warnings": list(self.warnings),
        }

    def to_dict(self) -> dict[str, Any]:
        result = self.identity_payload()
        result.update({"operation_sha256": self.operation_sha256, "ready": self.ready})
        return result


@dataclass(frozen=True, slots=True)
class NeutralManufacturingJob:
    job_id: str
    project_id: str
    machine_profile_id: str
    machine_id: str
    machine_profile_sha256: str
    stocks: tuple[NeutralStock, ...]
    pieces: tuple[NeutralPiece, ...]
    operations: tuple[NeutralOperation, ...]
    execution_order: tuple[str, ...]
    blocking_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    job_sha256: str = ""
    schema_version: str = NEUTRAL_JOB_SCHEMA
    algorithm_version: str = NEUTRAL_JOB_ALGORITHM

    def __post_init__(self) -> None:
        object.__setattr__(self, "stocks", tuple(self.stocks))
        object.__setattr__(self, "pieces", tuple(self.pieces))
        object.__setattr__(self, "operations", tuple(self.operations))
        object.__setattr__(self, "execution_order", tuple(self.execution_order))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        object.__setattr__(self, "warnings", tuple(dict.fromkeys(str(item) for item in self.warnings)))
        for label, value in (
            ("job_id", self.job_id),
            ("project_id", self.project_id),
            ("machine_profile_id", self.machine_profile_id),
            ("machine_id", self.machine_id),
            ("machine_profile_sha256", self.machine_profile_sha256),
        ):
            if not str(value).strip():
                raise ValueError(f"NeutralManufacturingJob mist {label}")
        expected = self.calculate_hash()
        if self.job_sha256 and self.job_sha256 != expected:
            raise ValueError("NeutralManufacturingJob job_sha256 klopt niet")

    @property
    def ready_for_postprocessor(self) -> bool:
        return (
            bool(self.pieces)
            and not self.blocking_codes
            and all(item.ready for item in self.operations)
            and len(self.execution_order) == len(self.operations)
        )

    @property
    def machine_transfer_allowed(self) -> bool:
        # M7 produces neutral manufacturing evidence only.
        return False

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "algorithm_version": self.algorithm_version,
            "job_id": self.job_id,
            "project_id": self.project_id,
            "machine_profile_id": self.machine_profile_id,
            "machine_id": self.machine_id,
            "machine_profile_sha256": self.machine_profile_sha256,
            "stocks": [item.to_dict() for item in self.stocks],
            "pieces": [item.to_dict() for item in self.pieces],
            "operations": [item.to_dict() for item in self.operations],
            "execution_order": list(self.execution_order),
            "blocking_codes": list(self.blocking_codes),
            "warnings": list(self.warnings),
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "NeutralManufacturingJob":
        result = cls(job_sha256="", **kwargs)
        return cls(**kwargs, job_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        result = self.payload_dict()
        result.update(
            {
                "job_sha256": self.job_sha256,
                "ready_for_postprocessor": self.ready_for_postprocessor,
                "machine_transfer_allowed": self.machine_transfer_allowed,
            }
        )
        return result


__all__ = [
    "NEUTRAL_JOB_SCHEMA", "NEUTRAL_OPERATION_SCHEMA", "NEUTRAL_JOB_ALGORITHM",
    "NeutralOperationKind", "NeutralOperationStatus", "NeutralStock", "NeutralPiece",
    "ExistingCapabilityProof", "ProcessOperationIntent", "NeutralOperation",
    "NeutralManufacturingJob",
]
