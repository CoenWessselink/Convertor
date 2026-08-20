"""Phase-6 manual planning, locks, undo/redo and partial re-optimisation.

The module never edits solver coordinates directly. Human actions modify a
compact planning layout (bar choice, sequence, orientation, common-cut policy
and locks). Every committed revision is rebuilt through the exact angle kernel
and independently validated before it can replace the current plan.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Callable
from uuid import uuid4

from cws_convertor.project.model import ProjectModel, stable_sha256, utc_now_iso

from .angle_solver import materialize_angle_layout, solve_angle_cut
from .angle_validator import validate_angle_plan
from .models import PROFILE_NESTING_SCHEMA_VERSION, NestingRunStatus
from .phase2 import prepare_phase2_context
from .results import PROFILE_NESTING_RESULT_SCHEMA_VERSION, SolverResultStatus
from .serialization import input_snapshot_from_dict, plan_from_dict

MANUAL_PLANNING_SCHEMA_VERSION = "1.0"
MAX_MANUAL_REVISIONS = 50


class ManualPlanningError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


@dataclass
class PlanLock:
    lock_id: str = field(default_factory=lambda: str(uuid4()))
    scope: str = "piece"  # piece | bar
    instance_id: str = ""
    bar_id: str = ""
    lock_assignment: bool = True
    lock_sequence: bool = False
    lock_orientation: bool = True
    lock_stock: bool = False
    reason: str = ""
    created_by: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    active: bool = True
    lock_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("lock_hash", None)
        self.lock_hash = stable_sha256(payload)
        return self.lock_hash

    def to_dict(self) -> dict[str, Any]:
        self.refresh_hash()
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PlanLock":
        lock = cls(**{k: v for k, v in dict(raw or {}).items() if k in cls.__dataclass_fields__})
        stored = str(lock.lock_hash or "")
        lock.refresh_hash()
        if stored and lock.lock_hash != stored:
            raise ManualPlanningError("CWS-NEST-028", "Handmatige lock heeft een ongeldige hash")
        return lock


@dataclass
class ManualPlanRevision:
    revision_id: str = field(default_factory=lambda: str(uuid4()))
    revision_no: int = 0
    action: str = "baseline"
    changed_by: str = ""
    changed_at: str = field(default_factory=utc_now_iso)
    before_plan_hash: str = ""
    after_plan_hash: str = ""
    validation_report_hash: str = ""
    modification: dict[str, Any] = field(default_factory=dict)
    layout: list[dict[str, Any]] = field(default_factory=list)
    locks: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] = field(default_factory=dict)
    revision_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("revision_hash", None)
        self.revision_hash = stable_sha256(payload)
        return self.revision_hash

    def to_dict(self) -> dict[str, Any]:
        self.refresh_hash()
        return asdict(self)


@dataclass
class ManualPlanningState:
    schema_version: str = MANUAL_PLANNING_SCHEMA_VERSION
    run_id: str = ""
    base_solver_plan_hash: str = ""
    best_known_plan_hash: str = ""
    current_revision_index: int = 0
    revisions: list[dict[str, Any]] = field(default_factory=list)
    locks: list[dict[str, Any]] = field(default_factory=list)
    stale: bool = False
    stale_reasons: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(default_factory=utc_now_iso)
    updated_by: str = ""
    state_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("updated_at", None)
        payload.pop("state_hash", None)
        self.state_hash = stable_sha256(payload)
        return self.state_hash

    def to_dict(self) -> dict[str, Any]:
        self.refresh_hash()
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "ManualPlanningState":
        data = dict(raw or {})
        if str(data.get("schema_version") or MANUAL_PLANNING_SCHEMA_VERSION) != MANUAL_PLANNING_SCHEMA_VERSION:
            raise ManualPlanningError("CWS-NEST-028", "Niet-ondersteund handmatig planningsschema")
        allowed = set(cls.__dataclass_fields__)
        state = cls(**{k: v for k, v in data.items() if k in allowed})
        stored = str(state.state_hash or "")
        state.refresh_hash()
        if stored and state.state_hash != stored:
            raise ManualPlanningError("CWS-NEST-028", "Handmatige planningstate heeft een ongeldige hash")
        return state


def _record(project: ProjectModel, run_id: str) -> dict[str, Any]:
    record = project.profile_nesting_runs.get(str(run_id))
    if not isinstance(record, dict):
        raise ManualPlanningError("CWS-NEST-019", f"Onbekende profielnestingrun {run_id!r}")
    if not isinstance(record.get("plan"), dict) or not isinstance(record.get("input_snapshot"), dict):
        raise ManualPlanningError("CWS-NEST-019", "Run bevat geen bewerkbaar plan/inputsnapshot")
    return record


def layout_from_plan(plan_raw: dict[str, Any]) -> list[dict[str, Any]]:
    layout: list[dict[str, Any]] = []
    for raw_bar in list(dict(plan_raw or {}).get("bars") or []):
        bar = dict(raw_bar or {})
        pieces = []
        transitions = {str(dict(x or {}).get("transition_id") or ""): dict(x or {}) for x in list(bar.get("transitions") or [])}
        for raw in sorted(list(bar.get("placements") or []), key=lambda x: int(dict(x or {}).get("sequence_index") or 0)):
            p = dict(raw or {})
            transition = transitions.get(str(p.get("transition_before_id") or ""), {})
            pieces.append({
                "instance_id": str(p.get("instance_id") or ""),
                "orientation_id": str(p.get("orientation_id") or "as_modeled"),
                "common_cut_mode": "force" if transition and bool(transition.get("common_cut")) else "auto",
                "planning_batch": "",
            })
        layout.append({
            "bar_id": str(bar.get("bar_id") or ""),
            "candidate_id": str(bar.get("candidate_id") or ""),
            "machine_profile_id": str(bar.get("machine_profile_id") or ""),
            "pieces": pieces,
        })
    return layout


def _normalised_demand_lines(lines: list[dict[str, Any]]) -> str:
    payload = []
    for raw in lines:
        line = deepcopy(dict(raw or {}))
        # eligibility messages contain only current deterministic checks. Keep
        # them, but canonicalise order for an identity comparison.
        line["eligibility_reasons"] = sorted(
            [dict(x or {}) for x in list(line.get("eligibility_reasons") or [])],
            key=lambda x: (str(x.get("code") or ""), str(x.get("message") or "")),
        )
        payload.append(line)
    payload.sort(key=lambda x: str(x.get("demand_line_id") or ""))
    return stable_sha256(payload)


def check_manual_freshness(project: ProjectModel, run_id: str) -> dict[str, Any]:
    record = _record(project, run_id)
    snapshot = dict(record.get("input_snapshot") or {})
    stock_policy = str(dict(snapshot.get("stock_snapshot") or {}).get("policy") or "stock_remnants_purchase")
    context = prepare_phase2_context(project, mode="production", stock_policy=stock_policy)
    reasons: list[dict[str, Any]] = []
    original_demand = _normalised_demand_lines([dict(x or {}) for x in list(snapshot.get("demand_lines") or [])])
    current_demand = _normalised_demand_lines([asdict(x) for x in context["demand_report"].demand_lines])
    if current_demand != original_demand:
        reasons.append({"code": "CWS-NEST-022", "kind": "demand", "message": "Onderdeelvraag/manufacturing identity wijkt af van de runsnapshot."})
    for kind, current_key, snapshot_key, code in (
        ("machine", "machine_snapshot", "machine_snapshot_hash", "CWS-NEST-023"),
        ("tool", "tool_snapshot", "tool_snapshot_hash", "CWS-NEST-023"),
        ("stock", "stock_snapshot", "stock_snapshot_hash", "CWS-NEST-024"),
    ):
        current_hash = str(dict(context[current_key]).get("snapshot_hash") or "")
        if current_hash != str(snapshot.get(snapshot_key) or ""):
            reasons.append({"code": code, "kind": kind, "message": f"{kind}configuratie wijkt af van de runsnapshot."})
    if str(context.get("reservation_version") or "") != str(snapshot.get("reservation_version") or ""):
        reasons.append({"code": "CWS-NEST-024", "kind": "reservation", "message": "Stockreserveringsversie is gewijzigd."})
    return {"fresh": not reasons, "reasons": reasons, "freshness_hash": stable_sha256(reasons)}


def initialize_manual_planning(project: ProjectModel, run_id: str, *, user: str = "gui") -> ManualPlanningState:
    record = _record(project, run_id)
    run_status = str(dict(record.get("run") or {}).get("status") or "")
    acceptance_status = str(dict(record.get("acceptance") or {}).get("status") or "")
    if run_status in {NestingRunStatus.ACCEPTED.value, NestingRunStatus.RELEASED.value} or acceptance_status == "accepted":
        raise ManualPlanningError("CWS-NEST-021", "Geaccepteerde of vrijgegeven nesting is bevroren; annuleer eerst de acceptatie voordat handmatige wijzigingen mogelijk zijn")
    existing = record.get("manual_planning")
    if isinstance(existing, dict):
        return ManualPlanningState.from_dict(existing)
    plan_raw = deepcopy(dict(record["plan"]))
    validation = dict(record.get("validation_report") or {})
    run = dict(record.get("run") or {})
    record["solver_plan"] = deepcopy(plan_raw)
    revision = ManualPlanRevision(
        revision_no=0,
        action="solver_baseline",
        changed_by=user,
        before_plan_hash=str(plan_raw.get("plan_hash") or ""),
        after_plan_hash=str(plan_raw.get("plan_hash") or ""),
        validation_report_hash=str(validation.get("report_hash") or ""),
        modification={"source": "solver", "solver_status": run.get("result_status")},
        layout=layout_from_plan(plan_raw),
        locks=[],
        plan=deepcopy(plan_raw),
    )
    state = ManualPlanningState(
        run_id=run_id,
        base_solver_plan_hash=str(plan_raw.get("plan_hash") or ""),
        best_known_plan_hash=str(plan_raw.get("plan_hash") or ""),
        current_revision_index=0,
        revisions=[revision.to_dict()],
        locks=[],
        updated_by=user,
    )
    record["manual_planning"] = state.to_dict()
    run["schema_version"] = PROFILE_NESTING_SCHEMA_VERSION
    record["run"] = run
    project.audit(
        "profile_nesting.manual_initialized", user=user, entity_id=run_id,
        before_hash=str(plan_raw.get("plan_hash") or ""), after_hash=state.state_hash,
        details={"base_solver_plan_hash": state.base_solver_plan_hash},
    )
    return state


def _current_revision(state: ManualPlanningState) -> dict[str, Any]:
    if not state.revisions:
        raise ManualPlanningError("CWS-NEST-028", "Handmatige historie is leeg")
    idx = int(state.current_revision_index)
    if idx < 0 or idx >= len(state.revisions):
        raise ManualPlanningError("CWS-NEST-028", "Handmatige historie-index is ongeldig")
    return deepcopy(dict(state.revisions[idx]))


def _find_piece(layout: list[dict[str, Any]], instance_id: str) -> tuple[int, int]:
    for bi, bar in enumerate(layout):
        for pi, piece in enumerate(list(dict(bar).get("pieces") or [])):
            if str(dict(piece).get("instance_id") or "") == str(instance_id):
                return bi, pi
    raise ManualPlanningError("CWS-NEST-019", f"Piece instance {instance_id!r} staat niet in de handmatige layout")


def _find_bar(layout: list[dict[str, Any]], bar_id: str) -> int:
    for i, raw in enumerate(layout):
        if str(dict(raw).get("bar_id") or "") == str(bar_id):
            return i
    raise ManualPlanningError("CWS-NEST-019", f"Staaf {bar_id!r} staat niet in de handmatige layout")


def _active_locks(state: ManualPlanningState) -> list[PlanLock]:
    return [PlanLock.from_dict(dict(x)) for x in state.locks if bool(dict(x).get("active", True))]


def _assert_piece_action_allowed(state: ManualPlanningState, instance_id: str, *, action: str, source_bar: str = "") -> None:
    for lock in _active_locks(state):
        if lock.scope == "bar" and lock.bar_id == source_bar:
            raise ManualPlanningError("CWS-NEST-027", f"Staaf {source_bar} is vergrendeld", details={"lock_id": lock.lock_id})
        if lock.scope != "piece" or lock.instance_id != instance_id:
            continue
        blocked = (
            action == "move" and lock.lock_assignment
            or action == "reorder" and lock.lock_sequence
            or action == "orientation" and lock.lock_orientation
        )
        if blocked:
            raise ManualPlanningError("CWS-NEST-027", f"Handmatige lock blokkeert actie {action} voor {instance_id}", details={"lock_id": lock.lock_id})


def _apply_layout_action(layout: list[dict[str, Any]], state: ManualPlanningState, action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    layout = deepcopy(layout)
    if action == "reorder":
        instance_id = str(params.get("instance_id") or "")
        bi, pi = _find_piece(layout, instance_id); bar = layout[bi]; source_bar = str(bar.get("bar_id") or "")
        _assert_piece_action_allowed(state, instance_id, action="reorder", source_bar=source_bar)
        pieces = list(bar.get("pieces") or []); piece = pieces.pop(pi)
        target = max(0, min(len(pieces), int(params.get("target_index", pi))))
        pieces.insert(target, piece); bar["pieces"] = pieces
    elif action == "move":
        instance_id = str(params.get("instance_id") or ""); target_bar_id = str(params.get("target_bar_id") or "")
        bi, pi = _find_piece(layout, instance_id); source = layout[bi]; source_bar = str(source.get("bar_id") or "")
        _assert_piece_action_allowed(state, instance_id, action="move", source_bar=source_bar)
        target_bi = _find_bar(layout, target_bar_id)
        for lock in _active_locks(state):
            if lock.scope == "bar" and lock.bar_id == target_bar_id:
                raise ManualPlanningError("CWS-NEST-027", f"Doelstaaf {target_bar_id} is vergrendeld")
        source_pieces = list(source.get("pieces") or [])
        piece = source_pieces.pop(pi); source["pieces"] = source_pieces
        target = layout[target_bi]; pieces = list(target.get("pieces") or [])
        idx = max(0, min(len(pieces), int(params.get("target_index", len(pieces)))))
        pieces.insert(idx, piece); target["pieces"] = pieces
        # remove now-empty source only when it was not explicitly added as an empty planning bar
        if not source.get("pieces") and not bool(source.get("keep_empty", False)):
            layout.pop(bi)
    elif action == "orientation":
        instance_id = str(params.get("instance_id") or ""); orientation_id = str(params.get("orientation_id") or "")
        bi, pi = _find_piece(layout, instance_id); bar_id = str(layout[bi].get("bar_id") or "")
        _assert_piece_action_allowed(state, instance_id, action="orientation", source_bar=bar_id)
        layout[bi]["pieces"][pi]["orientation_id"] = orientation_id
    elif action == "common_cut":
        instance_id = str(params.get("right_instance_id") or params.get("instance_id") or "")
        mode = str(params.get("mode") or "auto")
        if mode not in {"auto", "force", "disabled"}:
            raise ManualPlanningError("CWS-NEST-017", "Common-cutmodus moet auto, force of disabled zijn")
        bi, pi = _find_piece(layout, instance_id); bar_id = str(layout[bi].get("bar_id") or "")
        _assert_piece_action_allowed(state, instance_id, action="reorder", source_bar=bar_id)
        if pi == 0 and mode == "force":
            raise ManualPlanningError("CWS-NEST-017", "Eerste stuk op een staaf heeft geen transition vóór zich")
        layout[bi]["pieces"][pi]["common_cut_mode"] = mode
    elif action == "split_batch":
        ids=[str(x) for x in list(params.get("instance_ids") or []) if str(x)]
        if not ids and params.get("instance_id"): ids=[str(params.get("instance_id"))]
        batch_id=str(params.get("planning_batch_id") or f"manual-batch-{uuid4()}")
        if not ids: raise ManualPlanningError("CWS-NEST-028","Split batch vereist minimaal één piece instance")
        for instance_id in ids:
            bi,pi=_find_piece(layout,instance_id); bar_id=str(layout[bi].get("bar_id") or "")
            _assert_piece_action_allowed(state,instance_id,action="reorder",source_bar=bar_id)
            layout[bi]["pieces"][pi]["planning_batch"]=batch_id
    elif action == "stock":
        bar_id = str(params.get("bar_id") or ""); bi = _find_bar(layout, bar_id)
        for lock in _active_locks(state):
            if (lock.scope == "bar" and lock.bar_id == bar_id) or (lock.scope == "piece" and lock.lock_stock and any(str(x.get("instance_id") or "") == lock.instance_id for x in list(layout[bi].get("pieces") or []))):
                raise ManualPlanningError("CWS-NEST-027", f"Stockkeuze van staaf {bar_id} is vergrendeld")
        layout[bi]["candidate_id"] = str(params.get("candidate_id") or "")
        if params.get("machine_profile_id"):
            layout[bi]["machine_profile_id"] = str(params.get("machine_profile_id") or "")
    elif action == "add_empty_bar":
        bar_id = str(params.get("bar_id") or f"manual-{uuid4()}")
        if any(str(dict(x).get("bar_id") or "") == bar_id for x in layout):
            raise ManualPlanningError("CWS-NEST-019", f"Staaf-ID {bar_id} bestaat al")
        layout.append({"bar_id": bar_id, "candidate_id": str(params.get("candidate_id") or ""), "machine_profile_id": str(params.get("machine_profile_id") or ""), "pieces": [], "keep_empty": True})
    elif action == "remove_empty_bar":
        bi = _find_bar(layout, str(params.get("bar_id") or ""))
        if list(layout[bi].get("pieces") or []):
            raise ManualPlanningError("CWS-NEST-027", "Alleen een lege handmatige staaf kan worden verwijderd")
        layout.pop(bi)
    else:
        raise ManualPlanningError("CWS-NEST-028", f"Onbekende handmatige actie {action!r}")
    return layout


def _manual_modification_chain(state: ManualPlanningState, new_modification: dict[str, Any]) -> list[dict[str, Any]]:
    mods=[]
    for raw in state.revisions[1 : int(state.current_revision_index) + 1]:
        mod=dict(dict(raw).get("modification") or {})
        if mod: mods.append(mod)
    mods.append(dict(new_modification))
    return mods


def _materialize_revision(record: dict[str, Any], state: ManualPlanningState, layout: list[dict[str, Any]], *, action: str, params: dict[str, Any], user: str):
    snapshot = input_snapshot_from_dict(dict(record["input_snapshot"]))
    run = dict(record.get("run") or {})
    try:
        plan = materialize_angle_layout(
            snapshot, layout,
            scenario_family=str(run.get("scenario_family") or "waste"),
            objective_configuration=dict(run.get("objective_configuration") or snapshot.objective_configuration or {}),
            status=SolverResultStatus.MANUAL_FEASIBLE.value,
        )
    except Exception as exc:
        raise ManualPlanningError("CWS-NEST-027", f"Handmatige wijziging maakt het plan niet uitvoerbaar: {exc}") from exc
    mod = {"action": action, "parameters": deepcopy(params), "user": user, "at": utc_now_iso()}
    plan.result_schema_version = PROFILE_NESTING_RESULT_SCHEMA_VERSION
    plan.origin_plan_hash = state.base_solver_plan_hash
    plan.best_known_plan_hash = state.best_known_plan_hash
    plan.manual_revision = int(state.current_revision_index) + 1
    plan.manual_modifications = _manual_modification_chain(state, mod)
    plan.lock_snapshot_hash = stable_sha256(state.locks)
    plan.refresh_hash()
    report = validate_angle_plan(snapshot, plan)
    if not report.valid:
        raise ManualPlanningError("CWS-NEST-021", "Handmatige wijziging faalt onafhankelijke validatie", details=report.to_dict())
    return plan, report, mod


def _commit_revision(project: ProjectModel, run_id: str, record: dict[str, Any], state: ManualPlanningState, layout: list[dict[str, Any]], plan, report, modification: dict[str, Any], *, user: str) -> dict[str, Any]:
    current = _current_revision(state)
    before_hash = str(dict(record.get("plan") or {}).get("plan_hash") or "")
    # New edit after undo branches the history: redo revisions are intentionally discarded.
    state.revisions = list(state.revisions[: int(state.current_revision_index) + 1])
    revision_no = int(dict(state.revisions[-1]).get("revision_no") or 0) + 1
    rev = ManualPlanRevision(
        revision_no=revision_no,
        action=str(modification.get("action") or "manual_edit"),
        changed_by=user,
        before_plan_hash=before_hash,
        after_plan_hash=plan.plan_hash,
        validation_report_hash=report.report_hash,
        modification=deepcopy(modification),
        layout=deepcopy(layout),
        locks=deepcopy(state.locks),
        plan=plan.to_dict(),
    )
    state.revisions.append(rev.to_dict())
    if len(state.revisions) > MAX_MANUAL_REVISIONS:
        # Keep the immutable baseline plus the newest revisions.
        state.revisions = [state.revisions[0]] + state.revisions[-(MAX_MANUAL_REVISIONS-1):]
    state.current_revision_index = len(state.revisions) - 1
    state.updated_at = utc_now_iso(); state.updated_by = user; state.stale = False; state.stale_reasons = []
    record["plan"] = plan.to_dict(); record["validation_report"] = report.to_dict(); record["manual_planning"] = state.to_dict()
    run = dict(record.get("run") or {})
    run["schema_version"] = PROFILE_NESTING_SCHEMA_VERSION
    run["status"] = NestingRunStatus.REVIEW.value
    run["result_status"] = SolverResultStatus.MANUAL_FEASIBLE.value
    run["plan_hash"] = plan.plan_hash; run["validation_report_hash"] = report.report_hash; run["modified_at"] = utc_now_iso()
    audit_entry = {"action": str(modification.get("action") or "manual_edit"), "user": user, "at": utc_now_iso(), "before_plan_hash": before_hash, "after_plan_hash": plan.plan_hash, "revision_no": revision_no}
    run.setdefault("audit", []).append(audit_entry)
    record["run"] = run
    project.audit(
        "profile_nesting.manual_plan_changed", user=user, entity_id=run_id,
        before_hash=before_hash, after_hash=plan.plan_hash,
        details={"revision_no": revision_no, "modification": deepcopy(modification), "validation_report_hash": report.report_hash},
    )
    return {"plan": plan, "validation": report, "state": state, "revision": rev, "previous_revision": current}


def apply_manual_action(project: ProjectModel, run_id: str, action: str, params: dict[str, Any] | None = None, *, user: str = "gui") -> dict[str, Any]:
    freshness = check_manual_freshness(project, run_id)
    if not freshness["fresh"]:
        mark_manual_stale(project, run_id, freshness["reasons"], user=user)
        raise ManualPlanningError("CWS-NEST-022", "Plan is stale; handmatige wijziging is geblokkeerd", details=freshness)
    record = _record(project, run_id); state = initialize_manual_planning(project, run_id, user=user)
    current = _current_revision(state); layout = deepcopy(list(current.get("layout") or layout_from_plan(record["plan"])))
    layout = _apply_layout_action(layout, state, action, dict(params or {}))
    plan, report, mod = _materialize_revision(record, state, layout, action=action, params=dict(params or {}), user=user)
    return _commit_revision(project, run_id, record, state, layout, plan, report, mod, user=user)


def set_plan_lock(project: ProjectModel, run_id: str, lock: PlanLock, *, user: str = "gui") -> ManualPlanningState:
    freshness = check_manual_freshness(project, run_id)
    if not freshness["fresh"]:
        mark_manual_stale(project, run_id, freshness["reasons"], user=user)
        raise ManualPlanningError("CWS-NEST-022", "Plan is stale; lockwijziging is geblokkeerd", details=freshness)
    record=_record(project, run_id); state=initialize_manual_planning(project, run_id, user=user)
    current=_current_revision(state); layout=list(current.get("layout") or [])
    if lock.scope not in {"piece","bar"}:
        raise ManualPlanningError("CWS-NEST-027", "Lockscope moet piece of bar zijn")
    if lock.scope=="piece": _find_piece(layout, lock.instance_id)
    if lock.scope=="bar": _find_bar(layout, lock.bar_id)
    lock.created_by=user; lock.refresh_hash()
    state.locks=[x for x in state.locks if str(dict(x).get("lock_id") or "") != lock.lock_id]
    state.locks.append(lock.to_dict()); state.updated_at=utc_now_iso(); state.updated_by=user
    # Persist lock as its own revision so undo/redo and save/reopen are exact.
    snapshot=input_snapshot_from_dict(dict(record["input_snapshot"])); plan=plan_from_dict(dict(record["plan"])); plan.result_schema_version=PROFILE_NESTING_RESULT_SCHEMA_VERSION; plan.origin_plan_hash=state.base_solver_plan_hash; plan.best_known_plan_hash=state.best_known_plan_hash; plan.manual_revision=int(state.current_revision_index)+1; plan.manual_modifications=_manual_modification_chain(state,{"action":"lock","lock_id":lock.lock_id,"user":user,"at":utc_now_iso()}); plan.lock_snapshot_hash=stable_sha256(state.locks); plan.refresh_hash(); report=validate_angle_plan(snapshot,plan)
    if not report.valid: raise ManualPlanningError("CWS-NEST-021","Lock-update faalt planvalidatie",details=report.to_dict())
    _commit_revision(project,run_id,record,state,deepcopy(layout),plan,report,{"action":"lock","lock":lock.to_dict()},user=user)
    return state


def remove_plan_lock(project: ProjectModel, run_id: str, lock_id: str, *, user: str = "gui") -> ManualPlanningState:
    record=_record(project,run_id); state=initialize_manual_planning(project,run_id,user=user)
    before=len(state.locks); state.locks=[x for x in state.locks if str(dict(x).get("lock_id") or "") != str(lock_id)]
    if len(state.locks)==before: raise ManualPlanningError("CWS-NEST-027",f"Onbekende lock {lock_id!r}")
    current=_current_revision(state); layout=deepcopy(list(current.get("layout") or [])); snapshot=input_snapshot_from_dict(dict(record["input_snapshot"])); plan=plan_from_dict(dict(record["plan"])); plan.result_schema_version=PROFILE_NESTING_RESULT_SCHEMA_VERSION; plan.origin_plan_hash=state.base_solver_plan_hash; plan.best_known_plan_hash=state.best_known_plan_hash; plan.manual_revision=int(state.current_revision_index)+1; plan.manual_modifications=_manual_modification_chain(state,{"action":"unlock","lock_id":lock_id,"user":user,"at":utc_now_iso()}); plan.lock_snapshot_hash=stable_sha256(state.locks); plan.refresh_hash(); report=validate_angle_plan(snapshot,plan)
    _commit_revision(project,run_id,record,state,layout,plan,report,{"action":"unlock","lock_id":lock_id},user=user)
    return state


def _restore_revision(project: ProjectModel, run_id: str, target_index: int, *, user: str, action: str) -> dict[str, Any]:
    record=_record(project,run_id); state=initialize_manual_planning(project,run_id,user=user)
    if target_index<0 or target_index>=len(state.revisions): raise ManualPlanningError("CWS-NEST-028","Geen undo/redo-revisie beschikbaar")
    target=deepcopy(dict(state.revisions[target_index])); plan=plan_from_dict(dict(target.get("plan") or {})); snapshot=input_snapshot_from_dict(dict(record["input_snapshot"])); report=validate_angle_plan(snapshot,plan)
    if not report.valid: raise ManualPlanningError("CWS-NEST-021","Historische planrevisie faalt actuele onafhankelijke validatie",details=report.to_dict())
    before=str(dict(record.get("plan") or {}).get("plan_hash") or ""); state.current_revision_index=target_index; state.locks=deepcopy(list(target.get("locks") or [])); state.updated_at=utc_now_iso(); state.updated_by=user; record["plan"]=plan.to_dict(); record["validation_report"]=report.to_dict(); record["manual_planning"]=state.to_dict(); run=dict(record.get("run") or {}); run["status"]=NestingRunStatus.REVIEW.value if target_index else NestingRunStatus.FEASIBLE.value; run["result_status"]=SolverResultStatus.MANUAL_FEASIBLE.value if target_index else str(dict(record.get("solver_evidence") or {}).get("status") or SolverResultStatus.FEASIBLE.value); run["plan_hash"]=plan.plan_hash; run["validation_report_hash"]=report.report_hash; run["modified_at"]=utc_now_iso(); run.setdefault("audit",[]).append({"action":action,"user":user,"at":utc_now_iso(),"before_plan_hash":before,"after_plan_hash":plan.plan_hash,"target_revision":target_index}); record["run"]=run; project.audit(f"profile_nesting.{action}",user=user,entity_id=run_id,before_hash=before,after_hash=plan.plan_hash,details={"target_revision":target_index}); return {"plan":plan,"validation":report,"state":state,"revision":target}


def undo_manual_action(project: ProjectModel, run_id: str, *, user: str = "gui") -> dict[str, Any]:
    state=initialize_manual_planning(project,run_id,user=user)
    return _restore_revision(project,run_id,int(state.current_revision_index)-1,user=user,action="manual_undo")


def redo_manual_action(project: ProjectModel, run_id: str, *, user: str = "gui") -> dict[str, Any]:
    state=initialize_manual_planning(project,run_id,user=user)
    return _restore_revision(project,run_id,int(state.current_revision_index)+1,user=user,action="manual_redo")


def reset_to_solver_plan(project: ProjectModel, run_id: str, *, user: str = "gui") -> dict[str, Any]:
    record=_record(project,run_id); state=initialize_manual_planning(project,run_id,user=user)
    return _restore_revision(project,run_id,0,user=user,action="manual_reset_solver")


def _reduced_snapshot_for_instances(snapshot_raw: dict[str, Any], keep_ids: set[str]):
    raw=deepcopy(snapshot_raw); raw["piece_instances"]=[x for x in list(raw.get("piece_instances") or []) if str(dict(x).get("instance_id") or "") in keep_ids]
    used_lines={str(dict(x).get("demand_line_id") or "") for x in raw["piece_instances"]}; raw["demand_lines"]=[x for x in list(raw.get("demand_lines") or []) if str(dict(x).get("demand_line_id") or "") in used_lines]; raw["user_locks"]=[]; raw["snapshot_id"]=f"partial-{uuid4()}"; raw["created_at"]=utc_now_iso(); raw["snapshot_hash"]=""; snap=input_snapshot_from_dict(raw); snap.refresh_hash(); return snap


def partial_reoptimize(project: ProjectModel, run_id: str, *, backend: str = "auto", user: str = "gui", cancel_check: Callable[[], bool] | None = None, progress_callback: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Re-optimise only unlocked bars while keeping locked bars untouched.

    Piece locks conservatively freeze the complete bar containing that piece.
    This guarantees the lock cannot be violated by a heuristic insertion. The
    frozen-bar set and this simplification are persisted in the audit/evidence.
    """
    freshness=check_manual_freshness(project,run_id)
    if not freshness["fresh"]: mark_manual_stale(project,run_id,freshness["reasons"],user=user); raise ManualPlanningError("CWS-NEST-022","Plan is stale; heroptimalisatie is geblokkeerd",details=freshness)
    record=_record(project,run_id); state=initialize_manual_planning(project,run_id,user=user); current=_current_revision(state); layout=deepcopy(list(current.get("layout") or [])); locks=_active_locks(state)
    frozen_bars={l.bar_id for l in locks if l.scope=="bar" and l.bar_id}
    for l in locks:
        if l.scope=="piece" and l.instance_id:
            bi,_=_find_piece(layout,l.instance_id); frozen_bars.add(str(layout[bi].get("bar_id") or ""))
    frozen=[deepcopy(x) for x in layout if str(dict(x).get("bar_id") or "") in frozen_bars]
    unlocked=[deepcopy(x) for x in layout if str(dict(x).get("bar_id") or "") not in frozen_bars]
    unlocked_ids={str(dict(p).get("instance_id") or "") for b in unlocked for p in list(dict(b).get("pieces") or [])}
    if not unlocked_ids:
        raise ManualPlanningError("CWS-NEST-027","Geen unlocked remainder om te heroptimaliseren")
    reduced=_reduced_snapshot_for_instances(dict(record["input_snapshot"]),unlocked_ids)
    run=dict(record.get("run") or {})
    plan,evidence=solve_angle_cut(reduced,backend=backend,scenario_family=str(run.get("scenario_family") or "waste"),objective_configuration=dict(run.get("objective_configuration") or {}),solver_configuration={**dict(run.get("solver_configuration") or {}),"angle_exact_max_pieces":int(dict(run.get("solver_configuration") or {}).get("angle_exact_max_pieces") or 7)},cancel_check=cancel_check,progress_callback=progress_callback)
    if evidence.status==SolverResultStatus.CANCELLED.value: return {"cancelled":True,"evidence":evidence}
    if plan is None: raise ManualPlanningError("CWS-NEST-027","Unlocked remainder is niet heroptimaliseerbaar",details=evidence.to_dict())
    planning_batches={str(dict(piece).get("instance_id") or ""):str(dict(piece).get("planning_batch") or "") for bar in layout for piece in list(dict(bar).get("pieces") or []) if str(dict(piece).get("planning_batch") or "")}
    new_layout=frozen+layout_from_plan(plan.to_dict())
    for out_bar in new_layout:
        for piece in list(dict(out_bar).get("pieces") or []):
            iid=str(dict(piece).get("instance_id") or "")
            if iid in planning_batches: piece["planning_batch"]=planning_batches[iid]
    # Prevent generated bar-id collisions with frozen bars.
    frozen_ids={str(dict(x).get("bar_id") or "") for x in frozen}; counter=1
    for bar in new_layout[len(frozen):]:
        old=str(bar.get("bar_id") or ""); candidate=f"reopt-{counter:05d}"; counter+=1
        while candidate in frozen_ids: candidate=f"reopt-{counter:05d}"; counter+=1
        bar["bar_id"]=candidate; frozen_ids.add(candidate)
    manual_plan,report,mod=_materialize_revision(record,state,new_layout,action="partial_reoptimize",params={"backend":backend,"frozen_bars":sorted(frozen_bars),"unlocked_count":len(unlocked_ids),"solver_status":evidence.status,"solver_backend":evidence.backend},user=user)
    result=_commit_revision(project,run_id,record,state,new_layout,manual_plan,report,mod,user=user); result["partial_evidence"]=evidence; result["frozen_bars"]=sorted(frozen_bars); return result


def mark_manual_stale(project: ProjectModel, run_id: str, reasons: list[dict[str, Any]], *, user: str = "system") -> None:
    record=_record(project,run_id); state=initialize_manual_planning(project,run_id,user=user); before=state.state_hash; state.stale=True; state.stale_reasons=deepcopy(list(reasons or [])); state.updated_at=utc_now_iso(); state.updated_by=user; record["manual_planning"]=state.to_dict(); run=dict(record.get("run") or {}); run["status"]=NestingRunStatus.STALE.value; run["modified_at"]=utc_now_iso(); record["run"]=run; project.audit("profile_nesting.manual_stale",user=user,entity_id=run_id,before_hash=before,after_hash=state.state_hash,details={"reasons":deepcopy(reasons)})


def scenario_comparison(project: ProjectModel) -> list[dict[str, Any]]:
    rows=[]
    for run_id,record in dict(project.profile_nesting_runs or {}).items():
        run=dict(record.get("run") or {}); plan=dict(record.get("plan") or {}); obj=dict(plan.get("objective") or {}); state=dict(record.get("manual_planning") or {}); validation=dict(record.get("validation_report") or {}); solver_plan=dict(record.get("solver_plan") or {})
        current_metrics={str(k):int(v) for k,v in dict(obj.get("raw_metrics") or {}).items() if isinstance(v,(int,float))}
        best_metrics={str(k):int(v) for k,v in dict(dict(solver_plan.get("objective") or {}).get("raw_metrics") or {}).items() if isinstance(v,(int,float))} if solver_plan else dict(current_metrics)
        distance={k:int(current_metrics.get(k,0))-int(best_metrics.get(k,0)) for k in sorted(set(current_metrics)|set(best_metrics))}
        family=str(run.get("scenario_family") or "waste")
        primary_key={"waste":"waste_units","cost":"total_cost_micros","minimal_bars":"bar_count","stock_first":"purchase_bar_count","remnants_first":"remnant_source_count"}.get(family,"waste_units")
        rows.append({"run_id":run_id,"scenario":run.get("scenario_id"),"family":family,"status":run.get("result_status"),"plan_hash":plan.get("plan_hash"),"bars":len(list(plan.get("bars") or [])),"valid":bool(validation.get("valid")),"manual_revision":int(plan.get("manual_revision") or 0),"locks":len([x for x in list(state.get("locks") or []) if bool(dict(x or {}).get("active",True))]),"base_solver_plan_hash":state.get("base_solver_plan_hash",plan.get("origin_plan_hash","")),"best_known_plan_hash":state.get("best_known_plan_hash",plan.get("best_known_plan_hash","")),"objective_metrics":current_metrics,"best_known_metrics":best_metrics,"distance_to_best":distance,"primary_metric":primary_key,"primary_delta":int(distance.get(primary_key,0))})
    rows.sort(key=lambda x:(str(x.get("family") or ""),str(x.get("scenario") or ""),str(x.get("run_id") or "")))
    return rows


__all__ = [
    "MANUAL_PLANNING_SCHEMA_VERSION", "MAX_MANUAL_REVISIONS", "ManualPlanningError",
    "PlanLock", "ManualPlanRevision", "ManualPlanningState", "layout_from_plan",
    "check_manual_freshness", "initialize_manual_planning", "apply_manual_action",
    "set_plan_lock", "remove_plan_lock", "undo_manual_action", "redo_manual_action",
    "reset_to_solver_plan", "partial_reoptimize", "mark_manual_stale", "scenario_comparison",
]
