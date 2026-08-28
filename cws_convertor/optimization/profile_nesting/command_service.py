"""Authoritative transactional command layer for Profile Nesting."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from cws_convertor.project.model import ProjectModel
from .angle_validator import validate_angle_plan
from .configuration import set_machine_profile
from .manual_planning import (
    PlanLock, apply_manual_action, check_manual_freshness,
    initialize_manual_planning, layout_from_plan,
    partial_reoptimize as domain_partial_reoptimize,
    redo_manual_action, remove_plan_lock, reset_to_solver_plan,
    scenario_comparison, set_plan_lock, undo_manual_action,
)
from .models import MachineOptimizationProfile, NestingRunStatus
from .phase7 import accept_nesting_run, cancel_acceptance, release_nesting_run
from .results import SolverResultStatus
from .serialization import input_snapshot_from_dict, plan_from_dict


class OptimizationProofStatus(str, Enum):
    PROVEN_OPTIMAL = "PROVEN_OPTIMAL"
    FEASIBLE_WITH_BOUND = "FEASIBLE_WITH_BOUND"
    FEASIBLE_UNPROVEN = "FEASIBLE_UNPROVEN"
    TIMEOUT_FEASIBLE = "TIMEOUT_FEASIBLE"
    INFEASIBLE_PROVEN = "INFEASIBLE_PROVEN"
    INFEASIBLE_DETECTED = "INFEASIBLE_DETECTED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ProfileNestingCommandError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


@dataclass(frozen=True)
class ProfileNestingCommandRequest:
    action: str
    run_id: str = ""
    expected_project_id: str = ""
    expected_project_revision_hash: str = ""
    permission: str = "edit"
    manual_mode: bool = False
    request_id: str = ""


@dataclass(frozen=True)
class ProfileNestingCommandResult:
    request_id: str
    action: str
    run_id: str
    status: str
    before_hash: str
    after_hash: str
    proof_status: str
    validation_hash: str = ""
    revision_no: int = 0
    message: str = ""
    payload: Any = None


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def proof_status_for_record(record: dict[str, Any]) -> OptimizationProofStatus:
    evidence = dict(record.get("solver_evidence") or {})
    validation = dict(record.get("validation_report") or {})
    run = dict(record.get("run") or {})
    if validation and not bool(validation.get("valid")):
        return OptimizationProofStatus.FAILED
    status = str(run.get("result_status") or evidence.get("status") or "").lower()
    if status == SolverResultStatus.OPTIMAL.value:
        exact = bool(evidence.get("exact_scope"))
        zero_gap = evidence.get("absolute_gap") in (0, 0.0, "0") or evidence.get("relative_gap") in (0, 0.0, "0")
        return OptimizationProofStatus.PROVEN_OPTIMAL if exact and zero_gap else OptimizationProofStatus.FEASIBLE_WITH_BOUND
    mapping = {
        SolverResultStatus.TIMEOUT_FEASIBLE.value: OptimizationProofStatus.TIMEOUT_FEASIBLE,
        SolverResultStatus.INFEASIBLE_PROVEN.value: OptimizationProofStatus.INFEASIBLE_PROVEN,
        SolverResultStatus.INFEASIBLE_DETECTED.value: OptimizationProofStatus.INFEASIBLE_DETECTED,
        SolverResultStatus.CANCELLED.value: OptimizationProofStatus.CANCELLED,
        SolverResultStatus.FAILED.value: OptimizationProofStatus.FAILED,
    }
    if status in mapping:
        return mapping[status]
    if status in {SolverResultStatus.FEASIBLE.value, SolverResultStatus.MANUAL_FEASIBLE.value}:
        bounded = evidence.get("lower_bound") is not None and evidence.get("upper_bound") is not None
        return OptimizationProofStatus.FEASIBLE_WITH_BOUND if bounded else OptimizationProofStatus.FEASIBLE_UNPROVEN
    return OptimizationProofStatus.UNKNOWN


class ProfileNestingCommandService:
    """Single write boundary for planning, acceptance and machine edits."""

    def __init__(self, *, user: str = "profile-nesting-command-service") -> None:
        self.user = user

    @staticmethod
    def _records(project: ProjectModel) -> dict[str, dict[str, Any]]:
        records = getattr(project, "profile_nesting_runs", None)
        if not isinstance(records, dict):
            raise ProfileNestingCommandError("CWS-NEST-CMD-001", "Project bevat geen canonieke Profile Nesting-store")
        return records

    def _record(self, project: ProjectModel, run_id: str) -> dict[str, Any]:
        record = self._records(project).get(str(run_id))
        if not isinstance(record, dict):
            raise ProfileNestingCommandError("CWS-NEST-CMD-002", f"Onbekende Profile Nesting-run {run_id!r}")
        return record

    @staticmethod
    def _restore(project: ProjectModel, snapshot: dict[str, Any]) -> None:
        restored = ProjectModel.from_dict(snapshot)
        for descriptor in fields(ProjectModel):
            setattr(project, descriptor.name, deepcopy(getattr(restored, descriptor.name)))

    @staticmethod
    def _assert_safety(project: ProjectModel) -> None:
        settings = dict(getattr(project, "settings", {}) or {})
        flags = {
            "machine_observed_by_cws": settings.get("machine_observed_by_cws", False),
            "deployment_transport_authorized": settings.get("deployment_transport_authorized", False),
            "direct_machine_transfer": settings.get("direct_machine_transfer", False),
            "machine_transfer.allowed": dict(settings.get("machine_transfer") or {}).get("allowed", False),
        }
        enabled = [name for name, value in flags.items() if bool(value)]
        if enabled:
            raise ProfileNestingCommandError("CWS-NEST-CMD-003", "Machine-transfer boundary staat onveilig open", details={"enabled": enabled})

    def _request(self, project: ProjectModel, action: str, run_id: str = "", *, manual: bool = False) -> ProfileNestingCommandRequest:
        return ProfileNestingCommandRequest(
            action=action, run_id=run_id, expected_project_id=project.project_id,
            expected_project_revision_hash=project.revision_content_sha256(),
            permission="edit", manual_mode=manual,
        )

    def _validate_request(self, project: ProjectModel, request: ProfileNestingCommandRequest, *, manual: bool) -> None:
        if request.permission not in {"edit", "admin"}:
            raise ProfileNestingCommandError("CWS-NEST-CMD-004", "Gebruiker mist edit-permissie")
        if request.expected_project_id and request.expected_project_id != project.project_id:
            raise ProfileNestingCommandError("CWS-NEST-CMD-005", "Projectcontext is gewijzigd")
        if request.expected_project_revision_hash and request.expected_project_revision_hash != project.revision_content_sha256():
            raise ProfileNestingCommandError("CWS-NEST-CMD-006", "Projectrevisie is stale")
        if manual and not request.manual_mode:
            raise ProfileNestingCommandError("CWS-NEST-CMD-007", "Handmatige mutatie vereist expliciete Manual Mode")
        self._assert_safety(project)

    def _mutate(self, project: ProjectModel, request: ProfileNestingCommandRequest, operation: Callable[[], Any], *, manual: bool = False, message: str = "") -> ProfileNestingCommandResult:
        self._validate_request(project, request, manual=manual)
        snapshot = project.to_dict()
        before_hash = project.revision_content_sha256()
        request_id = request.request_id or str(uuid4())
        try:
            payload = operation()
            self._assert_safety(project)
            record = self._record(project, request.run_id) if request.run_id else {}
            validation = dict(record.get("validation_report") or {})
            if validation and not bool(validation.get("valid")):
                raise ProfileNestingCommandError("CWS-NEST-CMD-008", "Onafhankelijke planvalidatie faalde", details=validation)
            after_hash = project.revision_content_sha256()
            project.audit("profile_nesting.command_committed", user=self.user, entity_id=request.run_id, before_hash=before_hash, after_hash=after_hash, details={"request_id": request_id, "action": request.action})
            revision = 0
            if isinstance(payload, dict):
                revision = int(getattr(payload.get("revision"), "revision_no", 0) or 0)
            return ProfileNestingCommandResult(
                request_id, request.action, request.run_id, "PASS", before_hash, after_hash,
                proof_status_for_record(record).value if record else OptimizationProofStatus.UNKNOWN.value,
                str(validation.get("report_hash") or ""), revision,
                message or f"{request.action} uitgevoerd en gevalideerd", _plain(payload),
            )
        except Exception as exc:
            self._restore(project, snapshot)
            project.audit("profile_nesting.command_rolled_back", user=self.user, entity_id=request.run_id, before_hash=before_hash, after_hash=before_hash, details={"request_id": request_id, "action": request.action, "error": f"{type(exc).__name__}: {exc}"})
            if isinstance(exc, ProfileNestingCommandError):
                raise
            raise ProfileNestingCommandError(str(getattr(exc, "code", "CWS-NEST-CMD-999")), str(exc), details=dict(getattr(exc, "details", {}) or {})) from exc

    def inspect_run(self, project: ProjectModel, run_id: str) -> dict[str, Any]:
        record = self._record(project, run_id)
        return {"record": deepcopy(record), "freshness": check_manual_freshness(project, run_id), "proof_status": proof_status_for_record(record).value}

    def compare_scenarios(self, project: ProjectModel) -> ProfileNestingCommandResult:
        state_hash = project.revision_content_sha256()
        payload = scenario_comparison(project)
        return ProfileNestingCommandResult(str(uuid4()), "compare_scenarios", "", "PASS", state_hash, state_hash, OptimizationProofStatus.UNKNOWN.value, message=f"{len(payload)} scenario's vergeleken", payload=_plain(payload))

    def validate_plan(self, project: ProjectModel, run_id: str) -> ProfileNestingCommandResult:
        record = self._record(project, run_id)
        freshness = check_manual_freshness(project, run_id)
        if not freshness.get("fresh"):
            raise ProfileNestingCommandError("CWS-NEST-CMD-009", "Plan is stale", details=freshness)
        report = validate_angle_plan(input_snapshot_from_dict(dict(record.get("input_snapshot") or {})), plan_from_dict(dict(record.get("plan") or {})))
        if not report.valid:
            raise ProfileNestingCommandError("CWS-NEST-CMD-008", "Onafhankelijke planvalidatie faalde", details=report.to_dict())
        state_hash = project.revision_content_sha256()
        return ProfileNestingCommandResult(str(uuid4()), "validate_plan", run_id, "PASS", state_hash, state_hash, proof_status_for_record(record).value, report.report_hash, message="Plan onafhankelijk gevalideerd", payload=report.to_dict())

    def lock_piece(self, project: ProjectModel, run_id: str, instance_id: str) -> ProfileNestingCommandResult:
        lock = PlanLock(scope="piece", instance_id=instance_id, lock_assignment=True, lock_sequence=True, lock_orientation=True, created_by=self.user)
        return self._mutate(project, self._request(project, "lock_piece", run_id, manual=True), lambda: set_plan_lock(project, run_id, lock, user=self.user), manual=True)

    def unlock_piece(self, project: ProjectModel, run_id: str, instance_id: str) -> ProfileNestingCommandResult:
        state = initialize_manual_planning(project, run_id, user=self.user)
        lock_id = next((str(item.get("lock_id")) for item in state.locks if item.get("active", True) and item.get("scope") == "piece" and item.get("instance_id") == instance_id), "")
        if not lock_id:
            raise ProfileNestingCommandError("CWS-NEST-CMD-010", "Piece is niet vergrendeld")
        return self._mutate(project, self._request(project, "unlock_piece", run_id, manual=True), lambda: remove_plan_lock(project, run_id, lock_id, user=self.user), manual=True)

    def lock_bar(self, project: ProjectModel, run_id: str, bar_id: str) -> ProfileNestingCommandResult:
        lock = PlanLock(scope="bar", bar_id=bar_id, lock_assignment=True, lock_sequence=True, lock_orientation=True, lock_stock=True, created_by=self.user)
        return self._mutate(project, self._request(project, "lock_bar", run_id, manual=True), lambda: set_plan_lock(project, run_id, lock, user=self.user), manual=True)

    def unlock_bar(self, project: ProjectModel, run_id: str, bar_id: str) -> ProfileNestingCommandResult:
        state = initialize_manual_planning(project, run_id, user=self.user)
        lock_id = next((str(item.get("lock_id")) for item in state.locks if item.get("active", True) and item.get("scope") == "bar" and item.get("bar_id") == bar_id), "")
        if not lock_id:
            raise ProfileNestingCommandError("CWS-NEST-CMD-010", "Staaf is niet vergrendeld")
        return self._mutate(project, self._request(project, "unlock_bar", run_id, manual=True), lambda: remove_plan_lock(project, run_id, lock_id, user=self.user), manual=True)

    def _manual(self, project: ProjectModel, run_id: str, action: str, params: dict[str, Any]) -> ProfileNestingCommandResult:
        return self._mutate(project, self._request(project, action, run_id, manual=True), lambda: apply_manual_action(project, run_id, action, params, user=self.user), manual=True)

    def move_piece(self, project: ProjectModel, run_id: str, instance_id: str, target_bar_id: str, target_index: int = 0) -> ProfileNestingCommandResult:
        return self._manual(project, run_id, "move", {"instance_id": instance_id, "target_bar_id": target_bar_id, "target_index": target_index})

    def reorder_piece(self, project: ProjectModel, run_id: str, instance_id: str, target_index: int) -> ProfileNestingCommandResult:
        return self._manual(project, run_id, "reorder", {"instance_id": instance_id, "target_index": target_index})

    def set_orientation(self, project: ProjectModel, run_id: str, instance_id: str, orientation_id: str) -> ProfileNestingCommandResult:
        return self._manual(project, run_id, "orientation", {"instance_id": instance_id, "orientation_id": orientation_id})

    def toggle_common_cut(self, project: ProjectModel, run_id: str, instance_id: str, mode: str) -> ProfileNestingCommandResult:
        return self._manual(project, run_id, "common_cut", {"instance_id": instance_id, "mode": mode})

    def add_draft_bar(self, project: ProjectModel, run_id: str, candidate_id: str, *, bar_id: str = "", machine_profile_id: str = "") -> ProfileNestingCommandResult:
        return self._manual(project, run_id, "add_empty_bar", {"bar_id": bar_id, "candidate_id": candidate_id, "machine_profile_id": machine_profile_id})

    def remove_draft_bar(self, project: ProjectModel, run_id: str, bar_id: str) -> ProfileNestingCommandResult:
        return self._manual(project, run_id, "remove_empty_bar", {"bar_id": bar_id})

    def set_stock_candidate(self, project: ProjectModel, run_id: str, bar_id: str, candidate_id: str, *, machine_profile_id: str = "") -> ProfileNestingCommandResult:
        return self._manual(project, run_id, "stock", {"bar_id": bar_id, "candidate_id": candidate_id, "machine_profile_id": machine_profile_id})

    def partial_reoptimize(self, project: ProjectModel, run_id: str, *, backend: str = "auto") -> ProfileNestingCommandResult:
        return self._mutate(project, self._request(project, "partial_reoptimize", run_id, manual=True), lambda: domain_partial_reoptimize(project, run_id, backend=backend, user=self.user), manual=True)

    def undo(self, project: ProjectModel, run_id: str) -> ProfileNestingCommandResult:
        return self._mutate(project, self._request(project, "undo", run_id, manual=True), lambda: undo_manual_action(project, run_id, user=self.user), manual=True)

    def redo(self, project: ProjectModel, run_id: str) -> ProfileNestingCommandResult:
        return self._mutate(project, self._request(project, "redo", run_id, manual=True), lambda: redo_manual_action(project, run_id, user=self.user), manual=True)

    def reset_layout(self, project: ProjectModel, run_id: str) -> ProfileNestingCommandResult:
        return self._mutate(project, self._request(project, "reset_layout", run_id, manual=True), lambda: reset_to_solver_plan(project, run_id, user=self.user), manual=True)

    def accept_plan(self, project: ProjectModel, run_id: str, *, reserve_stock: bool = False) -> ProfileNestingCommandResult:
        action = "accept_reserve" if reserve_stock else "accept_plan"
        return self._mutate(project, self._request(project, action, run_id), lambda: accept_nesting_run(project, run_id, user=self.user, reserve_stock=reserve_stock), message="Plan geaccepteerd en voorraad transactioneel verwerkt")

    def reserve_stock(self, project: ProjectModel, run_id: str) -> ProfileNestingCommandResult:
        return self.accept_plan(project, run_id, reserve_stock=True)

    def release_reservations(self, project: ProjectModel, run_id: str) -> ProfileNestingCommandResult:
        return self._mutate(project, self._request(project, "release_reservations", run_id), lambda: cancel_acceptance(project, run_id, user=self.user), message="Acceptatie en reserveringen vrijgegeven")

    def release_neutral_package(self, project: ProjectModel, run_id: str, output_dir: str | Path) -> ProfileNestingCommandResult:
        return self._mutate(project, self._request(project, "release_neutral_package", run_id), lambda: release_nesting_run(project, run_id, output_dir, user=self.user), message="Neutraal nestingpakket vrijgegeven en geverifieerd")

    def save_machine_profile(self, project: ProjectModel, profile: MachineOptimizationProfile) -> ProfileNestingCommandResult:
        def operation() -> dict[str, Any]:
            before = deepcopy(getattr(project, "profile_nesting_machine_profiles", {}).get(profile.profile_id))
            set_machine_profile(project, profile, user=self.user)
            if before != asdict(profile):
                for record in self._records(project).values():
                    run = dict(record.get("run") or {})
                    if run.get("status") not in {NestingRunStatus.RELEASED.value, NestingRunStatus.OBSOLETE.value}:
                        run["status"] = NestingRunStatus.STALE.value
                        run.setdefault("stale_reasons", []).append({"code": "machine_profile_revision_changed", "profile_id": profile.profile_id})
                        record["run"] = run
            return {"profile": asdict(profile), "previous": before}
        return self._mutate(project, self._request(project, "save_machine_profile"), operation, message="Machineprofiel gevalideerd, gereviseerd en afhankelijke plannen geinvalideerd")

    def _layout(self, project: ProjectModel, run_id: str) -> list[dict[str, Any]]:
        return layout_from_plan(dict(self._record(project, run_id).get("plan") or {}))

    def resolve_piece(self, project: ProjectModel, run_id: str, selected_ids: tuple[str, ...]) -> tuple[str, str, int, dict[str, Any]]:
        selected = set(selected_ids)
        candidates = []
        for bar in self._layout(project, run_id):
            for index, piece in enumerate(list(bar.get("pieces") or [])):
                ids = {str(piece.get("instance_id") or ""), str(piece.get("part_id") or "")}
                if not selected or selected.intersection(ids):
                    candidates.append((str(piece.get("instance_id") or ""), str(bar.get("bar_id") or ""), index, piece))
        if len(candidates) != 1:
            raise ProfileNestingCommandError("CWS-NEST-CMD-011", "Selecteer precies een nesting-piece of bijbehorend onderdeel", details={"matches": len(candidates)})
        return candidates[0]

    def toggle_selected_lock(self, project: ProjectModel, run_id: str, selected_ids: tuple[str, ...]) -> ProfileNestingCommandResult:
        instance_id, _, _, _ = self.resolve_piece(project, run_id, selected_ids)
        state = initialize_manual_planning(project, run_id, user=self.user)
        locked = any(item.get("active", True) and item.get("scope") == "piece" and item.get("instance_id") == instance_id for item in state.locks)
        return self.unlock_piece(project, run_id, instance_id) if locked else self.lock_piece(project, run_id, instance_id)

    def move_or_reorder_selected(self, project: ProjectModel, run_id: str, selected_ids: tuple[str, ...]) -> ProfileNestingCommandResult:
        instance_id, bar_id, index, _ = self.resolve_piece(project, run_id, selected_ids)
        layout = self._layout(project, run_id)
        other = next((str(bar.get("bar_id") or "") for bar in layout if str(bar.get("bar_id") or "") != bar_id), "")
        if other:
            try:
                return self.move_piece(project, run_id, instance_id, other, 0)
            except ProfileNestingCommandError:
                # Machine/angle constraints may legitimately reject a cross-bar
                # move. The failed command has already rolled back atomically;
                # keep the UI action useful by applying a valid local reorder.
                pass
        pieces = next(list(bar.get("pieces") or []) for bar in layout if str(bar.get("bar_id") or "") == bar_id)
        return self.reorder_piece(project, run_id, instance_id, 0 if index else min(1, len(pieces) - 1))

    def cycle_selected_orientation(self, project: ProjectModel, run_id: str, selected_ids: tuple[str, ...]) -> ProfileNestingCommandResult:
        instance_id, _, _, piece = self.resolve_piece(project, run_id, selected_ids)
        record = self._record(project, run_id)
        input_snapshot = dict(record.get("input_snapshot") or {})
        instance = next(
            (
                dict(item)
                for item in list(input_snapshot.get("piece_instances") or [])
                if str(dict(item).get("instance_id") or "") == instance_id
            ),
            {},
        )
        demand_id = str(piece.get("demand_line_id") or instance.get("demand_line_id") or "")
        line = next((dict(item) for item in list(input_snapshot.get("demand_lines") or []) if str(dict(item).get("demand_line_id") or "") == demand_id), {})
        current = str(piece.get("orientation_id") or "as_modeled")
        alternatives = [str(item) for item in list(line.get("allowed_orientations") or []) if str(item) and str(item) != current]
        if not alternatives:
            raise ProfileNestingCommandError("CWS-NEST-CMD-012", "Geen bewezen alternatieve orientation beschikbaar")
        return self.set_orientation(project, run_id, instance_id, alternatives[0])

    def cycle_selected_common_cut(self, project: ProjectModel, run_id: str, selected_ids: tuple[str, ...]) -> ProfileNestingCommandResult:
        instance_id, bar_id, index, piece = self.resolve_piece(project, run_id, selected_ids)
        if index == 0:
            bar = next(item for item in self._layout(project, run_id) if str(item.get("bar_id") or "") == bar_id)
            if len(list(bar.get("pieces") or [])) < 2:
                raise ProfileNestingCommandError("CWS-NEST-CMD-013", "Common cut vereist een voorafgaand piece")
            piece = list(bar.get("pieces") or [])[1]
            instance_id = str(piece.get("instance_id") or "")
        target = "disabled" if str(piece.get("common_cut_mode") or "auto") != "disabled" else "auto"
        return self.toggle_common_cut(project, run_id, instance_id, target)


__all__ = ["OptimizationProofStatus", "ProfileNestingCommandError", "ProfileNestingCommandRequest", "ProfileNestingCommandResult", "ProfileNestingCommandService", "proof_status_for_record"]
