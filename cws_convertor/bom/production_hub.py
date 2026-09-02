"""Stateful, deterministic services for the BOM production hub.

The GUI is deliberately a thin client of this module.  Selections use
canonical entity/group IDs, saved sets are bound to a project, batch actions
are bound to one immutable BOM snapshot and settings mutations retain an undo
record plus the normal project audit trail.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4

from cws_convertor.project.model import stable_sha256

from .workspace import BOMScope, BOMWorkspaceReadModel, BOMWorkspaceRow


HUB_SETTINGS_KEY = "bom_production_hub"
SELECTION_BASES = (
    "group", "profile", "material", "machine", "status", "phase", "delivery",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _row_value(row: BOMWorkspaceRow, basis: str) -> str:
    if basis == "group":
        return row.group_id
    value = getattr(row, basis, "")
    return str(value or "").strip()


def _row_fingerprint(row: BOMWorkspaceRow, project: Any) -> str:
    entity_evidence = []
    for entity_id in row.entity_ids:
        entity = project.get_entity(entity_id) if hasattr(project, "get_entity") else None
        entity_evidence.append({
            "entity_id": entity_id,
            "geometry_hash": str(getattr(entity, "geometry_hash", "") or ""),
            "manufacturing_hash": str(getattr(entity, "manufacturing_hash", "") or ""),
            "quantity": getattr(entity, "quantity_total", getattr(entity, "quantity", 0)),
        })
    return stable_sha256({
        "mark": row.mark, "description": row.description, "profile": row.profile,
        "material": row.material, "length_mm": row.length_mm, "quantity": row.quantity,
        "mass": row.total_mass_kg, "surface": row.total_surface_m2,
        "machine": row.machine, "document": row.document_status, "status": row.status,
        "phase": row.phase, "delivery": row.delivery,
        "release": row.release_status, "nesting": row.nesting_status,
        "production": row.production_status, "stock": row.stock_status,
        "supplier": row.supplier, "entity_evidence": entity_evidence,
    })


@dataclass(frozen=True, slots=True)
class BOMSavedSelection:
    selection_id: str
    name: str
    family: str
    entity_ids: tuple[str, ...]
    group_ids: tuple[str, ...]
    snapshot_sha256: str
    dynamic_basis: str = ""
    dynamic_values: tuple[str, ...] = ()
    created_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-bom-saved-selection-1.0",
            "selection_id": self.selection_id,
            "name": self.name,
            "family": self.family,
            "entity_ids": list(self.entity_ids),
            "group_ids": list(self.group_ids),
            "snapshot_sha256": self.snapshot_sha256,
            "dynamic_basis": self.dynamic_basis,
            "dynamic_values": list(self.dynamic_values),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BOMSavedSelection":
        source = dict(value or {})
        return cls(
            selection_id=str(source.get("selection_id") or uuid4()),
            name=str(source.get("name") or "Selectieset"),
            family=str(source.get("family") or "parts"),
            entity_ids=_unique(source.get("entity_ids") or ()),
            group_ids=_unique(source.get("group_ids") or ()),
            snapshot_sha256=str(source.get("snapshot_sha256") or ""),
            dynamic_basis=str(source.get("dynamic_basis") or ""),
            dynamic_values=_unique(source.get("dynamic_values") or ()),
            created_at=str(source.get("created_at") or _utc_now()),
        )


@dataclass(frozen=True, slots=True)
class BOMSelectionImpact:
    family: str
    group_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    quantity: float
    total_mass_kg: float
    assembly_count: int
    blocked_group_ids: tuple[str, ...]
    hidden_entity_ids: tuple[str, ...] = ()
    machine_partitions: tuple[tuple[str, tuple[str, ...]], ...] = ()

    @property
    def group_count(self) -> int:
        return len(self.group_ids)

    @property
    def entity_count(self) -> int:
        return len(self.entity_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-bom-selection-impact-1.0",
            "family": self.family,
            "group_ids": list(self.group_ids),
            "entity_ids": list(self.entity_ids),
            "group_count": self.group_count,
            "entity_count": self.entity_count,
            "quantity": self.quantity,
            "total_mass_kg": self.total_mass_kg,
            "assembly_count": self.assembly_count,
            "blocked_group_ids": list(self.blocked_group_ids),
            "hidden_entity_ids": list(self.hidden_entity_ids),
            "machine_partitions": [
                {"machine": key, "entity_ids": list(ids)}
                for key, ids in self.machine_partitions
            ],
        }


@dataclass(frozen=True, slots=True)
class BOMBatchPreflight:
    action: str
    snapshot_sha256: str
    impact: BOMSelectionImpact
    eligible_group_ids: tuple[str, ...]
    blocked_group_ids: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    preflight_sha256: str = ""

    @property
    def allowed(self) -> bool:
        return bool(self.eligible_group_ids) and not self.blocking_reasons

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        result = {
            "schema": "cws-bom-batch-preflight-1.0",
            "action": self.action,
            "snapshot_sha256": self.snapshot_sha256,
            "impact": self.impact.to_dict(),
            "eligible_group_ids": list(self.eligible_group_ids),
            "blocked_group_ids": list(self.blocked_group_ids),
            "blocking_reasons": list(self.blocking_reasons),
            "allowed": self.allowed,
        }
        if include_hash:
            result["preflight_sha256"] = self.preflight_sha256
        return result


class BOMScopeEngine:
    """Build exact scopes and impacts without widening hidden selections."""

    def __init__(self, model: BOMWorkspaceReadModel) -> None:
        self.model = model

    def matching(self, seed: Iterable[BOMWorkspaceRow], basis: str) -> tuple[BOMWorkspaceRow, ...]:
        if basis not in SELECTION_BASES:
            raise ValueError(f"Onbekende selectiebasis: {basis}")
        selected = tuple(seed)
        if not selected:
            return ()
        families = {row.family for row in selected}
        if len(families) != 1:
            raise ValueError("Slimme selectie vereist één objectfamilie")
        values = {_row_value(row, basis) for row in selected if _row_value(row, basis)}
        if not values:
            return ()
        return tuple(
            row for row in self.model.family_rows(selected[0].family)
            if _row_value(row, basis) in values
        )

    def resolve_saved(self, saved: BOMSavedSelection) -> tuple[BOMWorkspaceRow, ...]:
        rows = self.model.family_rows(saved.family)
        if saved.dynamic_basis and saved.dynamic_values:
            return tuple(
                row for row in rows
                if _row_value(row, saved.dynamic_basis) in set(saved.dynamic_values)
            )
        entities, groups = set(saved.entity_ids), set(saved.group_ids)
        return tuple(
            row for row in rows
            if row.group_id in groups or bool(entities.intersection(row.entity_ids))
        )

    def impact(
        self,
        rows: Iterable[BOMWorkspaceRow],
        *,
        visible_rows: Iterable[BOMWorkspaceRow] = (),
    ) -> BOMSelectionImpact:
        selected = tuple(dict.fromkeys(rows))
        visible_entities = {
            entity_id for row in visible_rows for entity_id in row.entity_ids
        }
        entity_ids = _unique(entity_id for row in selected for entity_id in row.entity_ids)
        machine_groups: dict[str, list[str]] = {}
        for row in selected:
            machine_groups.setdefault(row.machine or "Geen machine", []).extend(row.entity_ids)
        summary = self.model.summary(selected)
        return BOMSelectionImpact(
            family=selected[0].family if selected else "",
            group_ids=_unique(row.group_id for row in selected),
            entity_ids=entity_ids,
            quantity=summary.quantity,
            total_mass_kg=summary.total_mass_kg,
            assembly_count=summary.assembly_count,
            blocked_group_ids=_unique(row.group_id for row in selected if row.blocked),
            hidden_entity_ids=tuple(value for value in entity_ids if value not in visible_entities),
            machine_partitions=tuple(
                (key, _unique(machine_groups[key])) for key in sorted(machine_groups, key=str.casefold)
            ),
        )

    def preflight(
        self,
        action: str,
        rows: Iterable[BOMWorkspaceRow],
        *,
        expected_snapshot_sha256: str,
        visible_rows: Iterable[BOMWorkspaceRow] = (),
        allow_blocked_review_export: bool = False,
    ) -> BOMBatchPreflight:
        if expected_snapshot_sha256 != self.model.snapshot.snapshot_sha256:
            raise ValueError("BOM-snapshot is gewijzigd; vernieuw de selectie en voer preflight opnieuw uit")
        selected = tuple(dict.fromkeys(rows))
        impact = self.impact(selected, visible_rows=visible_rows)
        blockers: list[str] = []
        if not selected:
            blockers.append("Selectie is leeg")
        blocked = tuple(row.group_id for row in selected if row.blocked)
        strict = action not in {"review_export", "inspect", "report"}
        # Row blockers form an explicit rejected partition; they do not make
        # otherwise eligible rows disappear.  Global incompatibilities below
        # still block the complete action.
        if action == "machine" and any(row.family != "parts" for row in selected):
            blockers.append("Machine-indeling accepteert uitsluitend onderdeelregels")
        if action in {"drawing", "release"} and any(
            row.family not in {"parts", "assemblies"} for row in selected
        ):
            blockers.append("Deze actie accepteert uitsluitend onderdelen of assemblies")
        if action == "release" and not bool(
            self.model.snapshot.validation and self.model.snapshot.validation.production_ready
        ):
            blockers.append("De volledige BOM is niet productiegereed")
        eligible = tuple(
            row.group_id for row in selected
            if not (strict and row.blocked)
        )
        draft = BOMBatchPreflight(
            action=str(action),
            snapshot_sha256=expected_snapshot_sha256,
            impact=impact,
            eligible_group_ids=_unique(eligible),
            blocked_group_ids=_unique(blocked),
            blocking_reasons=_unique(blockers),
        )
        return BOMBatchPreflight(
            action=draft.action,
            snapshot_sha256=draft.snapshot_sha256,
            impact=draft.impact,
            eligible_group_ids=draft.eligible_group_ids,
            blocked_group_ids=draft.blocked_group_ids,
            blocking_reasons=draft.blocking_reasons,
            preflight_sha256=stable_sha256(draft.to_dict(include_hash=False)),
        )


class BOMHubState:
    """Persistent project-owned selection sets, basket, revision baseline and undo."""

    def __init__(self, project: Any) -> None:
        self.project = project
        self._runtime_entity_undo: dict[str, dict[str, Any]] = {}
        self._runtime_settings_undo: dict[str, dict[str, Any]] = {}

    @property
    def data(self) -> dict[str, Any]:
        settings = self.project.settings.setdefault(HUB_SETTINGS_KEY, {})
        settings.setdefault("saved_selections", [])
        settings.setdefault("basket_entity_ids", [])
        settings.setdefault("history", [])
        settings.setdefault("undo", [])
        settings.setdefault("revision_baseline", {})
        return settings

    def basket(self) -> tuple[str, ...]:
        return _unique(self.data.get("basket_entity_ids") or ())

    def add_to_basket(self, entity_ids: Iterable[str], *, user: str = "bom-operator") -> tuple[str, ...]:
        before = self.basket()
        after = _unique((*before, *entity_ids))
        self.data["basket_entity_ids"] = list(after)
        self._history("basket.added", user, {"before": list(before), "after": list(after)})
        return after

    def remove_from_basket(self, entity_ids: Iterable[str], *, user: str = "bom-operator") -> tuple[str, ...]:
        removed = set(_unique(entity_ids))
        before = self.basket()
        after = tuple(value for value in before if value not in removed)
        self.data["basket_entity_ids"] = list(after)
        self._history("basket.removed", user, {"before": list(before), "after": list(after)})
        return after

    def clear_basket(self, *, user: str = "bom-operator") -> None:
        before = self.basket()
        self.data["basket_entity_ids"] = []
        self._history("basket.cleared", user, {"before": list(before)})

    def saved_selections(self) -> tuple[BOMSavedSelection, ...]:
        return tuple(BOMSavedSelection.from_dict(value) for value in self.data["saved_selections"])

    def save_selection(
        self,
        name: str,
        rows: Iterable[BOMWorkspaceRow],
        *,
        snapshot_sha256: str,
        dynamic_basis: str = "",
        user: str = "bom-operator",
    ) -> BOMSavedSelection:
        selected = tuple(rows)
        if not name.strip() or not selected:
            raise ValueError("Naam en selectie zijn verplicht")
        if dynamic_basis and dynamic_basis not in SELECTION_BASES:
            raise ValueError(f"Onbekende dynamische selectiebasis: {dynamic_basis}")
        saved = BOMSavedSelection(
            selection_id=str(uuid4()),
            name=name.strip(),
            family=selected[0].family,
            entity_ids=_unique(entity_id for row in selected for entity_id in row.entity_ids),
            group_ids=_unique(row.group_id for row in selected),
            snapshot_sha256=snapshot_sha256,
            dynamic_basis=dynamic_basis,
            dynamic_values=_unique(_row_value(row, dynamic_basis) for row in selected) if dynamic_basis else (),
        )
        self.data["saved_selections"].append(saved.to_dict())
        self._history("selection.saved", user, saved.to_dict())
        return saved

    def delete_selection(self, selection_id: str, *, user: str = "bom-operator") -> None:
        before = list(self.data["saved_selections"])
        self.data["saved_selections"] = [
            value for value in before if str(value.get("selection_id")) != str(selection_id)
        ]
        if len(before) == len(self.data["saved_selections"]):
            raise KeyError(selection_id)
        self._history("selection.deleted", user, {"selection_id": str(selection_id)})

    def set_revision_baseline(self, model: BOMWorkspaceReadModel, *, user: str = "bom-operator") -> str:
        payload = {
            row.group_id: {
                "family": row.family,
                "entity_ids": list(row.entity_ids),
                "fingerprint": _row_fingerprint(row, self.project),
            }
            for family in model._rows
            for row in model.family_rows(family)
        }
        baseline = {
            "snapshot_sha256": model.snapshot.snapshot_sha256,
            "created_at": _utc_now(),
            "groups": payload,
        }
        baseline["baseline_sha256"] = stable_sha256(baseline)
        self.data["revision_baseline"] = baseline
        self._history("revision.baseline_saved", user, {
            "snapshot_sha256": model.snapshot.snapshot_sha256,
            "baseline_sha256": baseline["baseline_sha256"],
        })
        return str(baseline["baseline_sha256"])

    def revision_statuses(self, model: BOMWorkspaceReadModel) -> dict[str, str]:
        baseline = dict(self.data.get("revision_baseline") or {})
        old = dict(baseline.get("groups") or {})
        if not old:
            return {row.group_id: "geen baseline" for family in model._rows for row in model.family_rows(family)}
        result: dict[str, str] = {}
        for family in model._rows:
            for row in model.family_rows(family):
                fingerprint = _row_fingerprint(row, self.project)
                previous = old.get(row.group_id)
                result[row.group_id] = (
                    "toegevoegd" if previous is None
                    else "ongewijzigd" if previous.get("fingerprint") == fingerprint
                    else "gewijzigd"
                )
        for group_id in set(old) - set(result):
            result[group_id] = "verwijderd"
        return result

    def begin_settings_transaction(
        self,
        action: str,
        preflight: BOMBatchPreflight,
        mutator: Callable[[], Any],
        *,
        user: str = "bom-operator",
    ) -> Any:
        if not preflight.snapshot_sha256 or not preflight.preflight_sha256:
            raise ValueError("Batchactie vereist een hashgebonden BOM-preflight")
        if not preflight.allowed:
            raise ValueError("Batchactie is door preflight geblokkeerd")
        before = deepcopy(self.project.settings)
        before_hash = stable_sha256(before)
        try:
            result = mutator()
        except Exception:
            self.project.settings = before
            raise
        after_hash = stable_sha256(self.project.settings)
        transaction_id = str(uuid4())
        self._runtime_settings_undo[transaction_id] = before
        undo = {
            "transaction_id": transaction_id,
            "action": str(action),
            "snapshot_sha256": preflight.snapshot_sha256,
            "preflight_sha256": preflight.preflight_sha256,
            "before_hash": before_hash,
            "after_hash": after_hash,
            "created_at": _utc_now(),
            "user": user,
        }
        self.data["undo"].append(undo)
        self.data["undo"] = self.data["undo"][-20:]
        self._history("batch.executed", user, {
            key: value for key, value in undo.items()
        })
        self.project.audit(
            f"bom.batch.{action}", user=user, before_hash=before_hash, after_hash=after_hash,
            details={"preflight_sha256": preflight.preflight_sha256,
                     "entity_ids": list(preflight.impact.entity_ids)},
        )
        return result

    def begin_entity_transaction(
        self,
        action: str,
        preflight: BOMBatchPreflight,
        entity_ids: Iterable[str],
        mutator: Callable[[], Any],
        *,
        user: str = "bom-operator",
    ) -> Any:
        if not preflight.allowed or not preflight.preflight_sha256:
            raise ValueError("Batchactie is door preflight geblokkeerd")
        locations: dict[str, tuple[str, Any]] = {}
        for entity_id in _unique(entity_ids):
            for collection_name in (
                "parts", "assemblies", "purchased_items", "fasteners", "welds",
            ):
                collection = getattr(self.project, collection_name, {})
                if entity_id in collection:
                    locations[entity_id] = (collection_name, deepcopy(collection[entity_id]))
                    break
        before_settings = deepcopy(self.project.settings)
        before_hash = stable_sha256(self.project.to_dict())
        try:
            result = mutator()
            self.project.validate()
        except Exception:
            self.project.settings = before_settings
            for entity_id, (collection_name, entity) in locations.items():
                getattr(self.project, collection_name)[entity_id] = entity
            raise
        transaction_id = str(uuid4())
        after_hash = stable_sha256(self.project.to_dict())
        record = {
            "transaction_id": transaction_id, "action": str(action),
            "snapshot_sha256": preflight.snapshot_sha256,
            "preflight_sha256": preflight.preflight_sha256,
            "before_hash": before_hash,
            "after_hash": after_hash, "created_at": _utc_now(), "user": user,
            "entity_ids": list(locations), "runtime_entity_restore": True,
        }
        self._runtime_entity_undo[transaction_id] = locations
        self._runtime_settings_undo[transaction_id] = before_settings
        self.data["undo"].append(record)
        self.data["undo"] = self.data["undo"][-20:]
        self._history("batch.executed", user, {
            key: value for key, value in record.items()
        })
        self.project.audit(
            f"bom.batch.{action}", user=user, before_hash=before_hash, after_hash=after_hash,
            details={"preflight_sha256": preflight.preflight_sha256, "entity_ids": list(locations)},
        )
        return result

    def undo_last(self, *, user: str = "bom-operator") -> str:
        stack = self.data["undo"]
        if not stack:
            raise ValueError("Geen BOM-batchactie beschikbaar om ongedaan te maken")
        record = deepcopy(stack[-1])
        transaction_id = str(record["transaction_id"])
        if transaction_id not in self._runtime_settings_undo:
            raise ValueError("Deze batchactie kan alleen in de oorspronkelijke werksessie worden teruggedraaid")
        current_hash = stable_sha256(self.project.settings)
        self.project.settings = deepcopy(self._runtime_settings_undo.pop(transaction_id))
        for entity_id, (collection_name, entity) in self._runtime_entity_undo.pop(
            transaction_id, {}
        ).items():
            getattr(self.project, collection_name)[entity_id] = entity
        restored_hash = stable_sha256(self.project.settings)
        self.project.audit(
            "bom.batch.undo", user=user, before_hash=current_hash, after_hash=restored_hash,
            details={"transaction_id": record["transaction_id"], "action": record["action"]},
        )
        return transaction_id

    def _history(self, action: str, user: str, details: Mapping[str, Any]) -> None:
        event = {
            "event_id": str(uuid4()), "timestamp": _utc_now(), "user": user,
            "action": action, "details": deepcopy(dict(details)),
        }
        self.data["history"].append(event)
        self.data["history"] = self.data["history"][-500:]
        self.project.audit(f"bom.{action}", user=user, details=dict(details))


__all__ = [
    "BOMBatchPreflight", "BOMHubState", "BOMSavedSelection",
    "BOMScopeEngine", "BOMSelectionImpact", "HUB_SETTINGS_KEY",
    "SELECTION_BASES",
]
