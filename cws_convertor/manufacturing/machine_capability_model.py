"""M5 machine capability and reachability evidence contracts.

A machine profile may prove that a manufacturing intent is reachable. It may
never turn an unsupported/unknown capability into an implicit permission. A
successful M5 report is only readiness evidence for a neutral machine job;
actual transfer remains disabled until a later proven adapter/release gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from cws_convertor.project.model import stable_sha256

MACHINE_CAPABILITY_SCHEMA = "cws-machine-capability-report-1.0"
MACHINE_CAPABILITY_ALGORITHM = "cws-machine-capability-evaluator-1.0"


class MachineFeatureType(StrEnum):
    SCRIBE = "scribe"
    HOLE_REFERENCE = "hole_reference"
    IDENTIFICATION_TEXT = "identification_text"


class CapabilityStatus(StrEnum):
    SUPPORTED = "supported"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class MachineFeatureDecision:
    feature_id: str
    feature_type: MachineFeatureType | str
    face_id: str
    canonical_face_role: str
    requested_operation: str
    machine_operation: str
    tool_id: str
    status: CapabilityStatus | str
    source_intent_sha256: str
    machine_profile_sha256: str
    measured: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    blocking_codes: tuple[str, ...] = ()
    decision_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_type", MachineFeatureType(self.feature_type))
        object.__setattr__(self, "status", CapabilityStatus(self.status))
        object.__setattr__(self, "measured", dict(self.measured or {}))
        object.__setattr__(self, "limits", dict(self.limits or {}))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        object.__setattr__(
            self,
            "blocking_codes",
            tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))),
        )
        if not self.feature_id.strip() or not self.face_id.strip():
            raise ValueError("MachineFeatureDecision mist feature_id of face_id")
        if not self.requested_operation.strip() or not self.source_intent_sha256.strip():
            raise ValueError("MachineFeatureDecision mist operation of source intent hash")
        if not self.machine_profile_sha256.strip():
            raise ValueError("MachineFeatureDecision mist machine profile hash")
        expected = stable_sha256(self.identity_payload())
        if self.decision_sha256 and self.decision_sha256 != expected:
            raise ValueError("MachineFeatureDecision decision_sha256 klopt niet")
        object.__setattr__(self, "decision_sha256", expected)

    @property
    def supported(self) -> bool:
        return self.status == CapabilityStatus.SUPPORTED and not self.blocking_codes

    def identity_payload(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "feature_type": self.feature_type.value,
            "face_id": self.face_id,
            "canonical_face_role": self.canonical_face_role,
            "requested_operation": self.requested_operation,
            "machine_operation": self.machine_operation,
            "tool_id": self.tool_id,
            "status": self.status.value,
            "source_intent_sha256": self.source_intent_sha256,
            "machine_profile_sha256": self.machine_profile_sha256,
            "measured": dict(self.measured),
            "limits": dict(self.limits),
            "warnings": list(self.warnings),
            "blocking_codes": list(self.blocking_codes),
        }

    def to_dict(self) -> dict[str, Any]:
        result = self.identity_payload()
        result["decision_sha256"] = self.decision_sha256
        result["supported"] = self.supported
        return result


@dataclass(frozen=True, slots=True)
class MachineCapabilityReport:
    part_id: str
    manufacturing_hash: str
    machine_profile_id: str
    machine_id: str
    machine_profile_sha256: str
    face_report_sha256: str
    mark_set_sha256: str
    identification_set_sha256: str
    decisions: tuple[MachineFeatureDecision, ...]
    blocking_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    algorithm_version: str = MACHINE_CAPABILITY_ALGORITHM
    report_sha256: str = ""
    schema_version: str = MACHINE_CAPABILITY_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "decisions", tuple(self.decisions))
        object.__setattr__(
            self,
            "blocking_codes",
            tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))),
        )
        object.__setattr__(self, "warnings", tuple(dict.fromkeys(str(item) for item in self.warnings)))
        if not self.part_id.strip() or not self.manufacturing_hash.strip():
            raise ValueError("MachineCapabilityReport mist onderdeel- of manufacturing identiteit")
        if not self.machine_profile_id.strip() or not self.machine_profile_sha256.strip():
            raise ValueError("MachineCapabilityReport mist machineprofiel-identiteit")
        expected = self.calculate_hash()
        if self.report_sha256 and self.report_sha256 != expected:
            raise ValueError("MachineCapabilityReport report_sha256 klopt niet")

    @property
    def marking_reachable(self) -> bool:
        return bool(self.decisions) and not self.blocking_codes and all(item.supported for item in self.decisions)

    @property
    def ready_for_neutral_job(self) -> bool:
        return self.marking_reachable

    @property
    def machine_transfer_allowed(self) -> bool:
        # M5 explicitly does not own postprocessor/manufacturer validation.
        return False

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "algorithm_version": self.algorithm_version,
            "part_id": self.part_id,
            "manufacturing_hash": self.manufacturing_hash,
            "machine_profile_id": self.machine_profile_id,
            "machine_id": self.machine_id,
            "machine_profile_sha256": self.machine_profile_sha256,
            "face_report_sha256": self.face_report_sha256,
            "mark_set_sha256": self.mark_set_sha256,
            "identification_set_sha256": self.identification_set_sha256,
            "decisions": [item.to_dict() for item in self.decisions],
            "blocking_codes": list(self.blocking_codes),
            "warnings": list(self.warnings),
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "MachineCapabilityReport":
        result = cls(report_sha256="", **kwargs)
        return cls(**kwargs, report_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        result = self.payload_dict()
        result.update(
            {
                "report_sha256": self.report_sha256,
                "marking_reachable": self.marking_reachable,
                "ready_for_neutral_job": self.ready_for_neutral_job,
                "machine_transfer_allowed": self.machine_transfer_allowed,
            }
        )
        return result


__all__ = [
    "MACHINE_CAPABILITY_SCHEMA",
    "MACHINE_CAPABILITY_ALGORITHM",
    "MachineFeatureType",
    "CapabilityStatus",
    "MachineFeatureDecision",
    "MachineCapabilityReport",
]
