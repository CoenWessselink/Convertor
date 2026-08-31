from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


def _stable_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class InspectionCharacteristic:
    characteristic_id: str
    entity_id: str
    feature_id: str
    nominal_value: float
    lower_tolerance: float
    upper_tolerance: float
    unit: str = "mm"
    measuring_tool_type: str = "caliper"
    required: bool = True
    scope_type: str = "part"
    assembly_id: str = ""
    sample_size: int = 1
    fai_required: bool = False
    reject_on_failure: bool = True

    def __post_init__(self) -> None:
        if not self.characteristic_id or not self.entity_id or not self.feature_id:
            raise ValueError("Inspection characteristics require stable IDs")
        if self.lower_tolerance > self.upper_tolerance:
            raise ValueError("Lower tolerance cannot exceed upper tolerance")
        if self.scope_type not in {"part", "assembly"}:
            raise ValueError("Inspection scope must be part or assembly")
        if self.scope_type == "assembly" and not self.assembly_id:
            raise ValueError("Assembly inspection requires assembly_id")
        if int(self.sample_size) < 1:
            raise ValueError("Inspection sample size must be positive")

    @property
    def lower_limit(self) -> float:
        return self.nominal_value + self.lower_tolerance

    @property
    def upper_limit(self) -> float:
        return self.nominal_value + self.upper_tolerance

    def accepts(self, value: float) -> bool:
        return self.lower_limit <= float(value) <= self.upper_limit


@dataclass(frozen=True)
class InspectionPlan:
    plan_id: str
    project_id: str
    revision: str
    characteristics: tuple[InspectionCharacteristic, ...]
    source_release_hash: str
    created_by: str
    approved_by: str
    heat_certificate_required: bool = False

    def __post_init__(self) -> None:
        if not self.plan_id or not self.project_id or not self.revision:
            raise ValueError("Inspection plan identity is incomplete")
        if len(self.source_release_hash) != 64:
            raise ValueError("Inspection plan must bind a 64-character release hash")
        identifiers = [item.characteristic_id for item in self.characteristics]
        if not identifiers or len(identifiers) != len(set(identifiers)):
            raise ValueError("Inspection plan characteristics must be non-empty and unique")
        if not self.created_by or not self.approved_by:
            raise ValueError("Inspection plan requires creator and independent approver")

    @property
    def plan_sha256(self) -> str:
        return _stable_sha256(asdict(self))


@dataclass(frozen=True)
class MeasurementRecord:
    measurement_id: str
    characteristic_id: str
    measured_value: float
    measured_at: str
    operator: str
    tool_id: str
    tool_calibration_id: str
    passed: bool
    evidence_sha256: str
    entity_id: str = ""
    assembly_id: str = ""
    sample_id: str = ""
    first_article: bool = False


@dataclass
class NonConformanceRecord:
    ncr_id: str
    measurement_id: str
    characteristic_id: str
    cause: str
    disposition: str = "open"
    rework_reference: str = ""
    reinspection_measurement_id: str = ""
    closed_by: str = ""
    entity_id: str = ""
    assembly_id: str = ""

    @property
    def is_open(self) -> bool:
        return self.disposition == "open"


@dataclass(frozen=True)
class InspectionResult:
    characteristic_id: str
    measurement_ids: tuple[str, ...]
    accepted: bool
    sampled_quantity: int
    rejected_quantity: int


@dataclass(frozen=True)
class ReworkRecord:
    rework_id: str
    ncr_id: str
    operation_reference: str
    performed_by: str
    performed_at: str
    evidence_sha256: str


@dataclass(frozen=True)
class ReleaseDecision:
    decision: str
    source_release_hash: str
    approved_by: str
    approved_at: str
    blocker_codes: tuple[str, ...]
    decision_sha256: str


@dataclass
class QualityLedger:
    project_id: str
    inspection_plan: InspectionPlan
    measurements: list[MeasurementRecord] = field(default_factory=list)
    nonconformances: list[NonConformanceRecord] = field(default_factory=list)
    heat_certificates: dict[str, str] = field(default_factory=dict)
    approvals: list[dict[str, str]] = field(default_factory=list)
    inspection_results: list[InspectionResult] = field(default_factory=list)
    rework_records: list[ReworkRecord] = field(default_factory=list)
    release_decisions: list[ReleaseDecision] = field(default_factory=list)
    final_release_allowed: bool = False
    final_release_hash: str = ""

    def __post_init__(self) -> None:
        if self.project_id != self.inspection_plan.project_id:
            raise ValueError("Quality ledger and inspection plan must share project identity")

    def _characteristic(self, characteristic_id: str) -> InspectionCharacteristic:
        for item in self.inspection_plan.characteristics:
            if item.characteristic_id == characteristic_id:
                return item
        raise KeyError(f"Unknown inspection characteristic: {characteristic_id}")

    def record_measurement(self, *, measurement_id: str, characteristic_id: str, measured_value: float,
                           measured_at: str, operator: str, tool_id: str,
                           tool_calibration_id: str, entity_id: str = "", assembly_id: str = "",
                           sample_id: str = "", first_article: bool = False) -> MeasurementRecord:
        if any(item.measurement_id == measurement_id for item in self.measurements):
            raise ValueError(f"Duplicate measurement ID: {measurement_id}")
        characteristic = self._characteristic(characteristic_id)
        evidence = {
            "measurement_id": measurement_id, "characteristic_id": characteristic_id,
            "measured_value": float(measured_value), "measured_at": measured_at,
            "operator": operator, "tool_id": tool_id, "tool_calibration_id": tool_calibration_id,
            "plan_sha256": self.inspection_plan.plan_sha256,
        }
        record = MeasurementRecord(
            measurement_id=measurement_id, characteristic_id=characteristic_id,
            measured_value=float(measured_value), measured_at=measured_at, operator=operator,
            tool_id=tool_id, tool_calibration_id=tool_calibration_id,
            passed=characteristic.accepts(measured_value), evidence_sha256=_stable_sha256(evidence),
            entity_id=entity_id or characteristic.entity_id, assembly_id=assembly_id or characteristic.assembly_id,
            sample_id=sample_id, first_article=bool(first_article),
        )
        self.measurements.append(record)
        self.final_release_allowed = False
        self.final_release_hash = ""
        if not record.passed:
            self.nonconformances.append(NonConformanceRecord(
                ncr_id=f"ncr-{measurement_id}", measurement_id=measurement_id,
                characteristic_id=characteristic_id, cause="measurement_outside_tolerance",
                entity_id=record.entity_id, assembly_id=record.assembly_id,
            ))
        return record

    def inspection_result(self, characteristic_id: str) -> InspectionResult:
        characteristic = self._characteristic(characteristic_id)
        records = [item for item in self.measurements if item.characteristic_id == characteristic_id]
        accepted = len(records) >= characteristic.sample_size and all(item.passed for item in records[-characteristic.sample_size:])
        result = InspectionResult(characteristic_id, tuple(item.measurement_id for item in records), accepted, len(records), sum(not item.passed for item in records))
        self.inspection_results = [item for item in self.inspection_results if item.characteristic_id != characteristic_id]
        self.inspection_results.append(result)
        return result

    def record_rework(self, *, rework_id: str, ncr_id: str, operation_reference: str,
                      performed_by: str, performed_at: str, evidence_sha256: str) -> ReworkRecord:
        if any(item.rework_id == rework_id for item in self.rework_records):
            raise ValueError(f"Duplicate rework ID: {rework_id}")
        if not any(item.ncr_id == ncr_id for item in self.nonconformances):
            raise KeyError(f"Unknown NCR: {ncr_id}")
        if len(evidence_sha256) != 64:
            raise ValueError("Rework evidence requires SHA-256")
        record = ReworkRecord(rework_id, ncr_id, operation_reference, performed_by, performed_at, evidence_sha256)
        self.rework_records.append(record)
        return record

    def add_heat_certificate(self, heat_id: str, certificate_sha256: str) -> None:
        if not heat_id or len(certificate_sha256) != 64:
            raise ValueError("Heat certificate requires identity and SHA-256")
        self.heat_certificates[heat_id] = certificate_sha256
        self.final_release_allowed = False
        self.final_release_hash = ""

    def close_nonconformance(self, ncr_id: str, *, rework_reference: str,
                             reinspection_measurement_id: str, closed_by: str) -> None:
        record = next((item for item in self.nonconformances if item.ncr_id == ncr_id), None)
        if record is None:
            raise KeyError(f"Unknown NCR: {ncr_id}")
        reinspection = next((item for item in self.measurements if item.measurement_id == reinspection_measurement_id), None)
        if reinspection is None or not reinspection.passed:
            raise ValueError("NCR closure requires a passing reinspection measurement")
        if reinspection.characteristic_id != record.characteristic_id:
            raise ValueError("Reinspection must target the NCR characteristic")
        if not rework_reference or not closed_by:
            raise ValueError("NCR closure requires rework evidence and an approver")
        record.disposition = "closed_after_rework"
        record.rework_reference = rework_reference
        record.reinspection_measurement_id = reinspection_measurement_id
        record.closed_by = closed_by

    def _latest_measurements(self) -> dict[str, MeasurementRecord]:
        latest: dict[str, MeasurementRecord] = {}
        for item in self.measurements:
            latest[item.characteristic_id] = item
        return latest

    def release_blockers(self, source_release_hash: str) -> list[str]:
        blockers: list[str] = []
        if source_release_hash != self.inspection_plan.source_release_hash:
            blockers.append("source_release_hash_mismatch")
        latest = self._latest_measurements()
        for characteristic in self.inspection_plan.characteristics:
            if not characteristic.required:
                continue
            measurement = latest.get(characteristic.characteristic_id)
            if measurement is None:
                blockers.append(f"measurement_missing:{characteristic.characteristic_id}")
            elif not measurement.passed:
                blockers.append(f"measurement_failed:{characteristic.characteristic_id}")
        if any(item.is_open for item in self.nonconformances):
            blockers.append("open_nonconformance")
        if self.inspection_plan.heat_certificate_required and not self.heat_certificates:
            blockers.append("heat_certificate_missing")
        return blockers

    def approve_final_release(self, *, source_release_hash: str, approved_by: str, approved_at: str) -> str:
        blockers = self.release_blockers(source_release_hash)
        if blockers:
            rejected = {"decision": "rejected", "source_release_hash": source_release_hash, "approved_by": approved_by, "approved_at": approved_at, "blocker_codes": tuple(blockers)}
            self.release_decisions.append(ReleaseDecision(**rejected, decision_sha256=_stable_sha256(rejected)))
            raise ValueError("Quality release blocked: " + ", ".join(blockers))
        approval = {
            "approved_at": approved_at, "approved_by": approved_by,
            "plan_sha256": self.inspection_plan.plan_sha256,
            "source_release_hash": source_release_hash, "quality_state_sha256": self.quality_sha256,
        }
        approval["approval_sha256"] = _stable_sha256(approval)
        self.approvals.append(approval)
        self.final_release_hash = approval["approval_sha256"]
        self.final_release_allowed = True
        accepted = {"decision": "accepted", "source_release_hash": source_release_hash, "approved_by": approved_by, "approved_at": approved_at, "blocker_codes": ()}
        self.release_decisions.append(ReleaseDecision(**accepted, decision_sha256=_stable_sha256(accepted)))
        return self.final_release_hash

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "cws-quality-ledger-1.0", "project_id": self.project_id,
            "inspection_plan": asdict(self.inspection_plan),
            "measurements": [asdict(item) for item in self.measurements],
            "nonconformances": [asdict(item) for item in self.nonconformances],
            "heat_certificates": dict(sorted(self.heat_certificates.items())),
            "approvals": list(self.approvals), "final_release_allowed": self.final_release_allowed,
            "final_release_hash": self.final_release_hash,
            "inspection_results": [asdict(item) for item in self.inspection_results],
            "rework_records": [asdict(item) for item in self.rework_records],
            "release_decisions": [asdict(item) for item in self.release_decisions],
        }

    @property
    def quality_sha256(self) -> str:
        payload = self._payload()
        payload["approvals"] = []
        payload["release_decisions"] = []
        payload["final_release_allowed"] = False
        payload["final_release_hash"] = ""
        return _stable_sha256(payload)

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        payload["quality_sha256"] = self.quality_sha256
        return payload

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "QualityLedger":
        plan_data = dict(value["inspection_plan"])
        plan_data["characteristics"] = tuple(InspectionCharacteristic(**dict(item)) for item in plan_data.get("characteristics", []))
        ledger = cls(
            project_id=str(value["project_id"]), inspection_plan=InspectionPlan(**plan_data),
            measurements=[MeasurementRecord(**dict(item)) for item in value.get("measurements", [])],
            nonconformances=[NonConformanceRecord(**dict(item)) for item in value.get("nonconformances", [])],
            heat_certificates=dict(value.get("heat_certificates") or {}),
            approvals=[dict(item) for item in value.get("approvals", [])],
            inspection_results=[InspectionResult(**dict(item)) for item in value.get("inspection_results", [])],
            rework_records=[ReworkRecord(**dict(item)) for item in value.get("rework_records", [])],
            release_decisions=[ReleaseDecision(**dict(item)) for item in value.get("release_decisions", [])],
            final_release_allowed=bool(value.get("final_release_allowed", False)),
            final_release_hash=str(value.get("final_release_hash") or ""),
        )
        expected = str(value.get("quality_sha256") or "")
        if expected and expected != ledger.quality_sha256:
            raise ValueError("Quality ledger hash mismatch")
        return ledger

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "QualityLedger":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


NcrRecord = NonConformanceRecord
