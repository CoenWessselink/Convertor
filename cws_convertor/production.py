"""Finite-capacity planning and fail-closed shopfloor contracts for Phase 2."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Any, Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from cws_convertor.project.model import ProjectModel


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class PlanningError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class Resource:
    resource_id: str
    name: str
    work_center_id: str
    capabilities: tuple[str, ...]
    active: bool = True


@dataclass(frozen=True)
class MachineResource(Resource):
    setup_minutes: int = 0
    direct_machine_control_allowed: bool = False

    def __post_init__(self) -> None:
        if self.direct_machine_control_allowed or int(self.setup_minutes) < 0:
            raise ValueError("machine planning must remain non-controlling with non-negative setup")


@dataclass(frozen=True)
class WorkCenter:
    work_center_id: str
    name: str
    resource_ids: tuple[str, ...]


@dataclass(frozen=True)
class Shift:
    shift_id: str
    resource_id: str
    starts_at: str
    ends_at: str

    def __post_init__(self) -> None:
        if _time(self.ends_at) <= _time(self.starts_at):
            raise ValueError("shift end must follow shift start")


@dataclass(frozen=True)
class OperationRequirement:
    operation_id: str
    capability: str
    duration_minutes: int
    setup_code: str = ""
    eligible_resource_ids: tuple[str, ...] = ()
    predecessor_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.operation_id or not self.capability or int(self.duration_minutes) <= 0:
            raise ValueError("operation requirement is incomplete")


@dataclass(frozen=True)
class ProductionOrder:
    order_id: str
    production_identity: str
    quantity: int
    due_at: str
    release_hash: str
    operations: tuple[OperationRequirement, ...]
    status: str = "released"

    def __post_init__(self) -> None:
        identifiers = [item.operation_id for item in self.operations]
        if not self.order_id or not self.production_identity or int(self.quantity) < 1 or len(self.release_hash) != 64:
            raise ValueError("production order identity/release is invalid")
        if not identifiers or len(identifiers) != len(set(identifiers)):
            raise ValueError("production operations must be non-empty and unique")


@dataclass(frozen=True)
class ScheduledOperation:
    schedule_id: str
    order_id: str
    operation_id: str
    resource_id: str
    starts_at: str
    ends_at: str
    setup_minutes: int
    predecessor_ids: tuple[str, ...]
    status: str = "scheduled"
    manually_rescheduled: bool = False
    late: bool = False


@dataclass(frozen=True)
class ProductionSchedule:
    schedule_id: str
    operations: tuple[ScheduledOperation, ...]
    input_sha256: str
    schedule_sha256: str
    blocker_codes: tuple[str, ...] = ()

    @property
    def feasible(self) -> bool:
        return not self.blocker_codes

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProductionSchedule":
        return cls(str(value["schedule_id"]), tuple(ScheduledOperation(**dict(item)) for item in value.get("operations", [])), str(value["input_sha256"]), str(value["schedule_sha256"]), tuple(value.get("blocker_codes", [])))


class FiniteCapacityPlanner:
    def schedule(self, orders: Iterable[ProductionOrder], resources: Iterable[Resource], shifts: Iterable[Shift], *, schedule_id: str = "phase2-schedule") -> ProductionSchedule:
        order_list = tuple(sorted(orders, key=lambda item: (_time(item.due_at), item.order_id)))
        resource_map = {item.resource_id: item for item in resources}
        shift_list = tuple(shifts)
        shift_map: dict[str, list[Shift]] = {}
        for shift in shift_list:
            shift_map.setdefault(shift.resource_id, []).append(shift)
        for values in shift_map.values():
            values.sort(key=lambda item: _time(item.starts_at))
        input_hash = _digest({"orders": [asdict(item) for item in order_list], "resources": [asdict(item) for item in resource_map.values()], "shifts": [asdict(item) for item in shift_list], "schedule_id": schedule_id})
        available: dict[str, datetime] = {}
        previous_setup: dict[str, str] = {}
        scheduled: list[ScheduledOperation] = []
        for order in order_list:
            remaining = {item.operation_id: item for item in order.operations}
            order_end: dict[str, datetime] = {}
            while remaining:
                ready = sorted((item for item in remaining.values() if all(key in order_end for key in item.predecessor_ids)), key=lambda item: item.operation_id)
                if not ready:
                    raise PlanningError("CWS.PLAN.PRECEDENCE_CYCLE", order.order_id)
                for requirement in ready:
                    predecessor_end = max((order_end[key] for key in requirement.predecessor_ids), default=datetime.min.replace(tzinfo=timezone.utc))
                    candidates = []
                    for resource in resource_map.values():
                        if not resource.active or requirement.capability not in resource.capabilities or (requirement.eligible_resource_ids and resource.resource_id not in requirement.eligible_resource_ids):
                            continue
                        setup = int(getattr(resource, "setup_minutes", 0)) if previous_setup.get(resource.resource_id) != requirement.setup_code else 0
                        for shift in shift_map.get(resource.resource_id, []):
                            start = max(_time(shift.starts_at), available.get(resource.resource_id, _time(shift.starts_at)), predecessor_end)
                            end = start + timedelta(minutes=setup + requirement.duration_minutes)
                            if end <= _time(shift.ends_at):
                                candidates.append((end, start, resource, setup))
                                break
                    if not candidates:
                        raise PlanningError("CWS.PLAN.NO_ELIGIBLE_CAPACITY", f"{order.order_id}/{requirement.operation_id}")
                    end, start, resource, setup = min(candidates, key=lambda item: (item[0], item[2].resource_id))
                    scheduled.append(ScheduledOperation(f"{order.order_id}:{requirement.operation_id}", order.order_id, requirement.operation_id, resource.resource_id, _iso(start), _iso(end), setup, requirement.predecessor_ids, late=end > _time(order.due_at)))
                    available[resource.resource_id], previous_setup[resource.resource_id], order_end[requirement.operation_id] = end, requirement.setup_code, end
                    remaining.pop(requirement.operation_id)
        result = ProductionSchedule(schedule_id, tuple(scheduled), input_hash, _digest([asdict(item) for item in scheduled]))
        return replace(result, blocker_codes=self.validate(result, order_list, tuple(resource_map.values()), shift_list))

    def validate(self, schedule: ProductionSchedule, orders: Iterable[ProductionOrder], resources: Iterable[Resource], shifts: Iterable[Shift]) -> tuple[str, ...]:
        resource_map = {item.resource_id: item for item in resources}
        order_map = {item.order_id: item for item in orders}
        shift_map: dict[str, list[Shift]] = {}
        for shift in shifts:
            shift_map.setdefault(shift.resource_id, []).append(shift)
        codes, by_resource = [], {}
        index = {(item.order_id, item.operation_id): item for item in schedule.operations}
        for item in schedule.operations:
            by_resource.setdefault(item.resource_id, []).append(item)
            resource, order = resource_map.get(item.resource_id), order_map.get(item.order_id)
            requirement = next((value for value in order.operations if value.operation_id == item.operation_id), None) if order else None
            if resource is None or requirement is None or requirement.capability not in resource.capabilities or (requirement.eligible_resource_ids and item.resource_id not in requirement.eligible_resource_ids):
                codes.append("CWS.PLAN.INELIGIBLE_RESOURCE")
            if not any(_time(shift.starts_at) <= _time(item.starts_at) and _time(item.ends_at) <= _time(shift.ends_at) for shift in shift_map.get(item.resource_id, [])):
                codes.append("CWS.PLAN.OUTSIDE_SHIFT")
            for predecessor in item.predecessor_ids:
                earlier = index.get((item.order_id, predecessor))
                if earlier is None or _time(earlier.ends_at) > _time(item.starts_at):
                    codes.append("CWS.PLAN.PRECEDENCE_VIOLATION")
        for values in by_resource.values():
            ordered = sorted(values, key=lambda item: _time(item.starts_at))
            if any(_time(left.ends_at) > _time(right.starts_at) for left, right in zip(ordered, ordered[1:])):
                codes.append("CWS.PLAN.CAPACITY_OVERLAP")
        return tuple(dict.fromkeys(codes))

    def manual_reschedule(self, schedule: ProductionSchedule, orders: Iterable[ProductionOrder], resources: Iterable[Resource], shifts: Iterable[Shift], *, schedule_operation_id: str, resource_id: str, starts_at: str, ends_at: str) -> ProductionSchedule:
        operations = tuple(replace(item, resource_id=resource_id, starts_at=starts_at, ends_at=ends_at, manually_rescheduled=True) if item.schedule_id == schedule_operation_id else item for item in schedule.operations)
        if operations == schedule.operations:
            raise PlanningError("CWS.PLAN.UNKNOWN_OPERATION", schedule_operation_id)
        candidate = replace(schedule, operations=operations, schedule_sha256=_digest([asdict(item) for item in operations]))
        blockers = self.validate(candidate, orders, resources, shifts)
        if blockers:
            raise PlanningError(blockers[0], "manual reschedule is not feasible")
        return replace(candidate, blocker_codes=())


@dataclass(frozen=True)
class ShopfloorIssue:
    issue_id: str
    schedule_id: str
    issue_type: str
    description: str
    ncr_id: str = ""


@dataclass
class OperationExecution:
    execution_id: str
    schedule_id: str
    order_id: str
    operation_id: str
    release_hash: str
    operator: str
    status: str = "running"
    started_at: str = ""
    completed_at: str = ""
    good_quantity: int = 0
    reject_quantity: int = 0
    measurement_ids: list[str] = field(default_factory=list)
    issue_ids: list[str] = field(default_factory=list)


@dataclass
class ShopfloorState:
    schedule: ProductionSchedule
    release_hashes: dict[str, str]
    order_quantities: dict[str, int]
    executions: dict[str, OperationExecution] = field(default_factory=dict)
    issues: dict[str, ShopfloorIssue] = field(default_factory=dict)
    remnants: dict[str, dict[str, Any]] = field(default_factory=dict)
    selected_schedule_id: str = ""
    direct_machine_control_allowed: bool = False

    @classmethod
    def from_schedule(cls, schedule: ProductionSchedule, orders: Iterable[ProductionOrder]) -> "ShopfloorState":
        values = tuple(orders)
        return cls(schedule, {item.order_id: item.release_hash for item in values}, {item.order_id: item.quantity for item in values})

    def open_released_work(self) -> tuple[ScheduledOperation, ...]:
        completed = {item.schedule_id for item in self.executions.values() if item.status == "completed"}
        return tuple(item for item in self.schedule.operations if item.schedule_id not in completed)

    def scan_select(self, identifier: str) -> ScheduledOperation:
        matches = [item for item in self.open_released_work() if identifier in {item.schedule_id, item.order_id, item.operation_id}]
        if len(matches) != 1:
            raise ValueError("scan/select identity must resolve to exactly one released operation")
        self.selected_schedule_id = matches[0].schedule_id
        return matches[0]

    def current_release(self) -> str:
        operation = next((item for item in self.schedule.operations if item.schedule_id == self.selected_schedule_id), None)
        return self.release_hashes.get(operation.order_id, "") if operation else ""

    def start_operation(self, schedule_id: str, *, release_hash: str, operator: str, started_at: str) -> OperationExecution:
        operation = next((item for item in self.schedule.operations if item.schedule_id == schedule_id), None)
        if operation is None:
            raise KeyError(f"unknown scheduled operation: {schedule_id}")
        if release_hash != self.release_hashes.get(operation.order_id):
            raise ValueError("shopfloor release hash is stale")
        for predecessor in operation.predecessor_ids:
            if not any(item.order_id == operation.order_id and item.operation_id == predecessor and item.status == "completed" for item in self.executions.values()):
                raise ValueError("shopfloor precedence is not complete")
        execution = OperationExecution(f"execution:{schedule_id}", schedule_id, operation.order_id, operation.operation_id, release_hash, operator, started_at=started_at)
        self.executions[execution.execution_id] = execution
        return execution

    def complete_operation(self, execution_id: str, *, completed_at: str, good_quantity: int, reject_quantity: int = 0, measurement_ids: Iterable[str] = (), issue_description: str = "") -> OperationExecution:
        execution = self.executions[execution_id]
        if execution.status != "running" or good_quantity < 0 or reject_quantity < 0 or good_quantity + reject_quantity > self.order_quantities[execution.order_id]:
            raise ValueError("invalid shopfloor completion state")
        measurements = list(measurement_ids)
        if reject_quantity and (not measurements or not issue_description):
            raise ValueError("reject quantity requires measurement evidence and an issue/NCR")
        execution.status, execution.completed_at = "completed", completed_at
        execution.good_quantity, execution.reject_quantity, execution.measurement_ids = int(good_quantity), int(reject_quantity), measurements
        if reject_quantity:
            issue = ShopfloorIssue(f"issue:{execution_id}", execution.schedule_id, "nonconformance", issue_description, f"ncr:{execution_id}")
            self.issues[issue.issue_id] = issue
            execution.issue_ids.append(issue.issue_id)
        return execution

    def register_remnant(self, remnant_id: str, *, source_schedule_id: str, material: str, grade: str, thickness_mm: float, width_mm: float, height_mm: float) -> None:
        if remnant_id in self.remnants or min(thickness_mm, width_mm, height_mm) <= 0:
            raise ValueError("invalid or duplicate remnant")
        self.remnants[remnant_id] = {"source_schedule_id": source_schedule_id, "material": material, "grade": grade, "thickness_mm": float(thickness_mm), "width_mm": float(width_mm), "height_mm": float(height_mm)}

    def to_dict(self) -> dict[str, Any]:
        return {"schedule": self.schedule.to_dict(), "release_hashes": self.release_hashes, "order_quantities": self.order_quantities, "executions": {key: asdict(value) for key, value in self.executions.items()}, "issues": {key: asdict(value) for key, value in self.issues.items()}, "remnants": self.remnants, "selected_schedule_id": self.selected_schedule_id, "direct_machine_control_allowed": False}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ShopfloorState":
        return cls(ProductionSchedule.from_dict(dict(value["schedule"])), dict(value.get("release_hashes") or {}), {key: int(item) for key, item in dict(value.get("order_quantities") or {}).items()}, {key: OperationExecution(**dict(item)) for key, item in dict(value.get("executions") or {}).items()}, {key: ShopfloorIssue(**dict(item)) for key, item in dict(value.get("issues") or {}).items()}, {key: dict(item) for key, item in dict(value.get("remnants") or {}).items()}, str(value.get("selected_schedule_id") or ""), False)


@dataclass
class Phase2ProductionState:
    schedule: ProductionSchedule | None = None
    shopfloor: ShopfloorState | None = None
    plate_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    quality_ledgers: dict[str, dict[str, Any]] = field(default_factory=dict)
    proof_center: dict[str, Any] = field(default_factory=dict)
    schema: str = "cws-phase2-production-state-1.0"

    def _payload(self) -> dict[str, Any]:
        return {"schema": self.schema, "schedule": self.schedule.to_dict() if self.schedule else None, "shopfloor": self.shopfloor.to_dict() if self.shopfloor else None, "plate_runs": self.plate_runs, "quality_ledgers": self.quality_ledgers, "proof_center": self.proof_center}

    @property
    def state_sha256(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "state_sha256": self.state_sha256}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Phase2ProductionState":
        state = cls(ProductionSchedule.from_dict(dict(value["schedule"])) if value.get("schedule") else None, ShopfloorState.from_dict(dict(value["shopfloor"])) if value.get("shopfloor") else None, {key: dict(item) for key, item in dict(value.get("plate_runs") or {}).items()}, {key: dict(item) for key, item in dict(value.get("quality_ledgers") or {}).items()}, dict(value.get("proof_center") or {}), str(value.get("schema") or "cws-phase2-production-state-1.0"))
        if value.get("state_sha256") and value["state_sha256"] != state.state_sha256:
            raise ValueError("phase-2 production state hash mismatch")
        return state

    def persist_to_project(self, project: "ProjectModel", *, user: str = "system") -> str:
        before = _digest(project.settings.get("phase2_production") or {})
        project.settings["phase2_production"] = self.to_dict()
        project.audit("phase2_production.persisted", user=user, before_hash=before, after_hash=self.state_sha256)
        return self.state_sha256

    @classmethod
    def from_project(cls, project: "ProjectModel") -> "Phase2ProductionState":
        value = dict(project.settings.get("phase2_production") or {})
        return cls.from_dict(value) if value else cls()


__all__ = ["FiniteCapacityPlanner", "MachineResource", "OperationExecution", "OperationRequirement", "Phase2ProductionState", "PlanningError", "ProductionOrder", "ProductionSchedule", "Resource", "ScheduledOperation", "Shift", "ShopfloorIssue", "ShopfloorState", "WorkCenter"]
