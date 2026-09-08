"""Deterministic, fail-closed machine routing and assignment authority."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any, Iterable, Mapping

from cws_convertor.project.model import stable_sha256, utc_now_iso


ROUTING_SCHEMA_VERSION = "cws-machine-routing-1.0"


@dataclass(frozen=True, slots=True)
class MachineRouteDecision:
    part_id: str
    machine_id: str
    eligible: bool
    automatic: bool
    blocking_codes: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True, slots=True)
class MachineAssignment:
    part_id: str
    recommended_machine_id: str = ""
    assigned_machine_id: str = ""
    assignment_source: str = "AUTO"
    capability_status: str = "review_required"
    routing_status: str = "review_required"
    reason: str = ""
    manual_lock: bool = False
    assigned_by: str = ""
    assigned_at: str = ""
    blocking_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blocking_codes"] = list(self.blocking_codes)
        return data

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MachineAssignment":
        source = dict(payload or {})
        return cls(
            part_id=str(source.get("part_id") or ""),
            recommended_machine_id=str(source.get("recommended_machine_id") or ""),
            assigned_machine_id=str(source.get("assigned_machine_id") or ""),
            assignment_source=str(source.get("assignment_source") or "AUTO").upper(),
            capability_status=str(source.get("capability_status") or "review_required"),
            routing_status=str(source.get("routing_status") or "review_required"),
            reason=str(source.get("reason") or ""),
            manual_lock=bool(source.get("manual_lock", False)),
            assigned_by=str(source.get("assigned_by") or ""),
            assigned_at=str(source.get("assigned_at") or ""),
            blocking_codes=tuple(str(value) for value in source.get("blocking_codes", ()) if str(value)),
        )


@dataclass(slots=True)
class MachineRoutingSnapshot:
    project_id: str
    ruleset_version: str
    assignments: tuple[MachineAssignment, ...]
    generated_at: str = field(default_factory=utc_now_iso)
    snapshot_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ROUTING_SCHEMA_VERSION,
            "project_id": self.project_id,
            "ruleset_version": self.ruleset_version,
            "assignments": [item.to_dict() for item in self.assignments],
            "generated_at": self.generated_at,
            "snapshot_sha256": self.snapshot_sha256,
        }

    def refresh_hash(self) -> str:
        payload = self.to_dict()
        payload.pop("generated_at", None)
        payload["snapshot_sha256"] = ""
        self.snapshot_sha256 = stable_sha256(payload)
        return self.snapshot_sha256


class MachineRoutingService:
    @staticmethod
    def _value(report: Any, name: str, default: Any = None) -> Any:
        return report.get(name, default) if isinstance(report, Mapping) else getattr(report, name, default)

    def route(
        self,
        part_id: str,
        capabilities: Mapping[str, Any],
        *,
        preferred_machine: str = "",
    ) -> MachineRouteDecision:
        candidates = []
        for machine_id, report in capabilities.items():
            blockers = tuple(
                str(value) for value in (self._value(report, "blocking_codes", ()) or ())
            )
            explicit = self._value(report, "production_ready", None)
            if explicit is None:
                explicit = self._value(report, "ready_for_neutral_job", None)
            if explicit is None:
                explicit = self._value(report, "eligible", None)
            if explicit is None:
                explicit = self._value(report, "passed", None)
            if explicit is not True or blockers:
                continue
            decisions = self._value(report, "feature_decisions", None)
            if decisions is None:
                decisions = self._value(report, "decisions", ())
            decisions = decisions or ()
            candidates.append(
                (
                    0 if str(machine_id) == str(preferred_machine) else 1,
                    -len(decisions),
                    str(machine_id),
                    blockers,
                )
            )
        if not candidates:
            return MachineRouteDecision(
                str(part_id),
                "",
                False,
                False,
                ("CWS.ROUTING.NO_PROVEN_MACHINE",),
                "Geen machine heeft expliciet bewezen capaciteit",
            )
        _preferred, _score, machine_id, blockers = min(candidates)
        return MachineRouteDecision(
            str(part_id),
            machine_id,
            True,
            not bool(preferred_machine),
            blockers,
            "Deterministisch gerouteerd op bewezen machinecapaciteit",
        )

    def route_many(
        self,
        parts: Mapping[str, Mapping[str, Any]],
        *,
        preferred: Mapping[str, str] | None = None,
    ) -> tuple[MachineRouteDecision, ...]:
        choices = preferred or {}
        return tuple(
            self.route(part_id, capabilities, preferred_machine=choices.get(part_id, ""))
            for part_id, capabilities in sorted(parts.items())
        )

    @staticmethod
    def project_capabilities(
        project: Any,
        part_ids: Iterable[str] = (),
    ) -> dict[str, dict[str, Any]]:
        """Read proven capability reports without creating a second authority.

        The unified 2.25 bridge can carry the M18 authority store inside its
        compatibility envelope.  Newer callers may expose the same store as a
        runtime attribute or as a direct settings entry.  All shapes converge
        here into ``part -> machine -> report``.
        """
        settings = dict(getattr(project, "settings", {}) or {})
        unified = dict(settings.get("_cws_unified_schema_2_25", {}) or {})
        stores = dict(unified.get("m18_project_stores", {}) or {})
        candidates = (
            getattr(project, "manufacturing_machine_capabilities", None),
            settings.get("manufacturing_machine_capabilities"),
            stores.get("manufacturing_machine_capabilities"),
            settings.get("machine_capability_reports"),
        )
        requested = {str(value) for value in part_ids if str(value)}
        result: dict[str, dict[str, Any]] = {}

        def add(report: Any, *, fallback_part: str = "", fallback_machine: str = "") -> None:
            part_id = str(MachineRoutingService._value(report, "part_id", fallback_part) or fallback_part)
            machine_id = str(MachineRoutingService._value(report, "machine_id", fallback_machine) or fallback_machine)
            if not part_id or not machine_id or (requested and part_id not in requested):
                return
            result.setdefault(part_id, {})[machine_id] = report

        for raw in candidates:
            if not isinstance(raw, Mapping):
                continue
            payload = raw.get("reports", raw)
            if not isinstance(payload, Mapping):
                continue
            for outer_key, outer_value in payload.items():
                if isinstance(outer_value, Mapping) and (
                    "part_id" in outer_value or "machine_id" in outer_value
                ):
                    add(outer_value, fallback_part=str(outer_key))
                    continue
                if not isinstance(outer_value, Mapping):
                    add(outer_value)
                    continue
                for machine_key, report in outer_value.items():
                    add(
                        report,
                        fallback_part=str(outer_key),
                        fallback_machine=str(machine_key),
                    )
        return result

    @staticmethod
    def assignments(project: Any) -> dict[str, MachineAssignment]:
        routing = dict((getattr(project, "settings", {}) or {}).get("machine_routing", {}) or {})
        return {
            str(part_id): MachineAssignment.from_dict(value)
            for part_id, value in dict(routing.get("assignments", {}) or {}).items()
            if isinstance(value, Mapping)
        }

    def assign(
        self,
        project: Any,
        part_ids: Iterable[str],
        machine_id: str,
        *,
        user: str,
        reason: str,
        manual_lock: bool = True,
    ) -> tuple[MachineAssignment, ...]:
        ids = tuple(dict.fromkeys(str(value) for value in part_ids if str(value)))
        if not ids:
            raise ValueError("Selecteer minimaal één onderdeel")
        unknown = tuple(value for value in ids if value not in project.parts)
        if unknown:
            raise KeyError("Onbekende onderdeel-ID(s): " + ", ".join(unknown))
        machine = str(machine_id or "").strip()
        if not machine:
            raise ValueError("Kies een machine")
        explanation = str(reason or "").strip()
        if not explanation:
            raise ValueError("Een reden is verplicht voor handmatige machine-indeling")
        existing = self.assignments(project)
        now = utc_now_iso()
        changed: list[MachineAssignment] = []
        for part_id in ids:
            previous = existing.get(part_id)
            assignment = MachineAssignment(
                part_id=part_id,
                recommended_machine_id=(previous.recommended_machine_id if previous else ""),
                assigned_machine_id=machine,
                assignment_source="MANUAL",
                capability_status="review_required",
                routing_status="assigned_manual_review_required",
                reason=explanation,
                manual_lock=bool(manual_lock),
                assigned_by=str(user or "operator"),
                assigned_at=now,
                blocking_codes=("CWS.ROUTING.MANUAL_REVALIDATION_REQUIRED",),
            )
            existing[part_id] = assignment
            changed.append(assignment)
        snapshot = self._persist(project, existing)
        project.audit(
            "project.machine_assignment_changed",
            user=str(user or "operator"),
            after_hash=snapshot.snapshot_sha256,
            details={
                "part_ids": list(ids),
                "assigned_machine_id": machine,
                "assignment_source": "MANUAL",
                "manual_lock": bool(manual_lock),
                "reason": explanation,
                "routing_snapshot_sha256": snapshot.snapshot_sha256,
            },
        )
        return tuple(changed)

    def assign_automatic(
        self,
        project: Any,
        part_ids: Iterable[str],
        *,
        user: str,
    ) -> tuple[MachineAssignment, ...]:
        """Persist deterministic automatic choices from proven capability only."""
        ids = tuple(dict.fromkeys(str(value) for value in part_ids if str(value)))
        if not ids:
            raise ValueError("Selecteer minimaal één onderdeel")
        unknown = tuple(value for value in ids if value not in project.parts)
        if unknown:
            raise KeyError("Onbekende onderdeel-ID(s): " + ", ".join(unknown))
        capabilities = self.project_capabilities(project, ids)
        existing = self.assignments(project)
        now = utc_now_iso()
        changed: list[MachineAssignment] = []
        for part_id in ids:
            previous = existing.get(part_id)
            if previous is not None and previous.manual_lock:
                changed.append(previous)
                continue
            preferred = (
                previous.assigned_machine_id
                if previous is not None
                else ""
            )
            decision = self.route(
                part_id,
                capabilities.get(part_id, {}),
                preferred_machine=preferred,
            )
            assignment = MachineAssignment(
                part_id=part_id,
                recommended_machine_id=decision.machine_id,
                assigned_machine_id=decision.machine_id if decision.eligible else "",
                assignment_source="AUTO",
                capability_status="proven" if decision.eligible else "blocked",
                routing_status="ready" if decision.eligible else "blocked",
                reason=decision.reason,
                manual_lock=False,
                assigned_by=str(user or "operator"),
                assigned_at=now,
                blocking_codes=tuple(decision.blocking_codes),
            )
            existing[part_id] = assignment
            changed.append(assignment)
        snapshot = self._persist(project, existing)
        project.audit(
            "project.machine_assignment_automatic",
            user=str(user or "operator"),
            after_hash=snapshot.snapshot_sha256,
            details={
                "part_ids": list(ids),
                "ready_count": sum(item.routing_status == "ready" for item in changed),
                "blocked_count": sum(item.routing_status != "ready" for item in changed),
                "manual_lock_count": sum(item.manual_lock for item in changed),
                "routing_snapshot_sha256": snapshot.snapshot_sha256,
            },
        )
        return tuple(changed)

    def set_manual_lock(
        self,
        project: Any,
        part_ids: Iterable[str],
        *,
        locked: bool,
        user: str,
        reason: str,
    ) -> tuple[MachineAssignment, ...]:
        """Lock or unlock existing manual choices without bypassing revalidation."""
        ids = tuple(dict.fromkeys(str(value) for value in part_ids if str(value)))
        if not ids:
            raise ValueError("Selecteer minimaal één onderdeel")
        explanation = str(reason or "").strip()
        if not explanation:
            raise ValueError("Een reden is verplicht voor wijziging van de machinevergrendeling")
        existing = self.assignments(project)
        changed: list[MachineAssignment] = []
        for part_id in ids:
            assignment = existing.get(part_id)
            if assignment is None or assignment.assignment_source != "MANUAL":
                raise ValueError(f"Onderdeel {part_id} heeft geen handmatige machinekeuze")
            updated = replace(
                assignment, manual_lock=bool(locked), reason=explanation,
                assigned_by=str(user or "operator"), assigned_at=utc_now_iso(),
            )
            existing[part_id] = updated
            changed.append(updated)
        snapshot = self._persist(project, existing)
        project.audit(
            "project.machine_assignment_lock_changed", user=str(user or "operator"),
            after_hash=snapshot.snapshot_sha256,
            details={
                "part_ids": list(ids), "manual_lock": bool(locked),
                "reason": explanation,
                "routing_snapshot_sha256": snapshot.snapshot_sha256,
            },
        )
        return tuple(changed)

    def reset(
        self,
        project: Any,
        part_ids: Iterable[str],
        *,
        user: str,
        reason: str,
    ) -> MachineRoutingSnapshot:
        ids = tuple(dict.fromkeys(str(value) for value in part_ids if str(value)))
        if not ids:
            raise ValueError("Selecteer minimaal één onderdeel")
        explanation = str(reason or "").strip()
        if not explanation:
            raise ValueError("Een reden is verplicht voor het resetten van machine-indeling")
        existing = self.assignments(project)
        for part_id in ids:
            existing.pop(part_id, None)
        snapshot = self._persist(project, existing)
        project.audit(
            "project.machine_assignment_reset",
            user=str(user or "operator"),
            after_hash=snapshot.snapshot_sha256,
            details={
                "part_ids": list(ids),
                "reason": explanation,
                "routing_snapshot_sha256": snapshot.snapshot_sha256,
            },
        )
        return snapshot

    @staticmethod
    def _persist(project: Any, assignments: Mapping[str, MachineAssignment]) -> MachineRoutingSnapshot:
        current = dict((getattr(project, "settings", {}) or {}).get("machine_routing", {}) or {})
        snapshot = MachineRoutingSnapshot(
            project_id=str(project.project_id),
            ruleset_version=str(current.get("ruleset_version") or "manual-routing-1.0"),
            assignments=tuple(assignments[key] for key in sorted(assignments)),
        )
        snapshot.refresh_hash()
        project.settings["machine_routing"] = {
            "schema": ROUTING_SCHEMA_VERSION,
            "ruleset_version": snapshot.ruleset_version,
            "snapshot_sha256": snapshot.snapshot_sha256,
            "generated_at": snapshot.generated_at,
            "assignments": {
                assignment.part_id: assignment.to_dict()
                for assignment in snapshot.assignments
            },
        }
        return snapshot


__all__ = [
    "MachineAssignment",
    "MachineRouteDecision",
    "MachineRoutingService",
    "MachineRoutingSnapshot",
    "ROUTING_SCHEMA_VERSION",
]
