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
import math
import time
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4

from cws_convertor.project.model import stable_sha256

from .workspace import BOMScope, BOMWorkspaceReadModel, BOMWorkspaceRow


HUB_SETTINGS_KEY = "bom_production_hub"
SELECTION_BASES = (
    "group", "profile", "material", "machine", "status", "phase", "delivery",
)
QUERY_FIELDS = (
    "family", "mark", "description", "profile", "material", "machine",
    "status", "phase", "delivery", "release_status", "nesting_status",
    "production_status", "stock_status", "document_status", "geometry_status",
    "machine_status", "nc_status", "scribing_status", "conflict_status",
    "delivery_status", "revision_status", "shortage_mm", "quantity",
    "available_stock_mm", "assigned_stock", "assigned_remnant",
    "expected_delivery", "supplier", "purchase_status",
    "purchase_release_status", "alternative_material", "total_price",
    "total_mass_kg", "length_mm",
)
QUERY_OPERATORS = (
    "equals", "not_equals", "contains", "not_contains", "is_empty",
    "is_not_empty", "greater_than", "less_than",
)


@dataclass(frozen=True, slots=True)
class BOMQueryClause:
    field: str
    operator: str
    value: str = ""

    def __post_init__(self) -> None:
        if self.field not in QUERY_FIELDS:
            raise ValueError(f"Onbekend BOM-queryveld: {self.field}")
        if self.operator not in QUERY_OPERATORS:
            raise ValueError(f"Onbekende BOM-queryoperator: {self.operator}")

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "operator": self.operator, "value": self.value}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BOMQueryClause":
        return cls(
            field=str(value.get("field") or "status"),
            operator=str(value.get("operator") or "equals"),
            value=str(value.get("value") or ""),
        )


@dataclass(frozen=True, slots=True)
class BOMQueryGroup:
    """Recursive EN/OF expression used by compound smart selections."""

    match: str
    clauses: tuple[BOMQueryClause, ...] = ()
    groups: tuple["BOMQueryGroup", ...] = ()
    negate: bool = False

    def __post_init__(self) -> None:
        if self.match not in {"all", "any"}:
            raise ValueError("Een querygroep gebruikt 'all' of 'any'")
        if not self.clauses and not self.groups:
            raise ValueError("Een querygroep vereist minimaal één voorwaarde of subgroep")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match": self.match,
            "clauses": [clause.to_dict() for clause in self.clauses],
            "groups": [group.to_dict() for group in self.groups],
            "negate": self.negate,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BOMQueryGroup":
        return cls(
            match=str(value.get("match") or "all"),
            clauses=tuple(BOMQueryClause.from_dict(item) for item in value.get("clauses") or ()),
            groups=tuple(cls.from_dict(item) for item in value.get("groups") or ()),
            negate=bool(value.get("negate", False)),
        )


@dataclass(frozen=True, slots=True)
class BOMSmartQuery:
    query_id: str
    name: str
    family: str
    match: str
    clauses: tuple[BOMQueryClause, ...]
    groups: tuple[BOMQueryGroup, ...] = ()
    negate: bool = False
    created_at: str = field(default_factory=lambda: _utc_now())

    def __post_init__(self) -> None:
        if self.match not in {"all", "any"}:
            raise ValueError("Een slimme selectie gebruikt 'all' of 'any'")
        if not self.clauses and not self.groups:
            raise ValueError("Een slimme selectie vereist minimaal één voorwaarde")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-bom-smart-query-2.0", "query_id": self.query_id,
            "name": self.name, "family": self.family, "match": self.match,
            "clauses": [clause.to_dict() for clause in self.clauses],
            "groups": [group.to_dict() for group in self.groups],
            "negate": self.negate,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BOMSmartQuery":
        return cls(
            query_id=str(value.get("query_id") or uuid4()),
            name=str(value.get("name") or "Slimme selectie"),
            family=str(value.get("family") or "parts"),
            match=str(value.get("match") or "all"),
            clauses=tuple(BOMQueryClause.from_dict(item) for item in value.get("clauses") or ()),
            groups=tuple(BOMQueryGroup.from_dict(item) for item in value.get("groups") or ()),
            negate=bool(value.get("negate", False)),
            created_at=str(value.get("created_at") or _utc_now()),
        )


@dataclass(frozen=True, slots=True)
class BOMFieldDelta:
    """One exact changed field, optionally scoped to a canonical entity."""

    field_path: str
    before: Any = None
    after: Any = None
    entity_id: str = ""
    change: str = "changed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "entity_id": self.entity_id,
            "change": self.change,
            "before": deepcopy(self.before),
            "after": deepcopy(self.after),
        }


@dataclass(frozen=True, slots=True)
class BOMRevisionDelta:
    group_id: str
    family: str
    status: str
    changed_fields: tuple[str, ...] = ()
    field_deltas: tuple[BOMFieldDelta, ...] = ()
    before: Mapping[str, Any] = field(default_factory=dict)
    after: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id, "family": self.family,
            "status": self.status, "changed_fields": list(self.changed_fields),
            "field_deltas": [value.to_dict() for value in self.field_deltas],
            "before": deepcopy(dict(self.before)), "after": deepcopy(dict(self.after)),
        }


@dataclass(frozen=True, slots=True)
class BOMActionDefinition:
    action_id: str
    label: str
    category: str
    families: tuple[str, ...]
    route: str
    mutating: bool = False
    allow_blocked: bool = False
    requires_production_ready: bool = False


@dataclass(frozen=True, slots=True)
class BOMBatchResult:
    transaction_id: str
    action: str
    status: str
    snapshot_sha256: str
    preflight_sha256: str
    before_hash: str
    after_hash: str
    eligible_group_ids: tuple[str, ...]
    blocked_group_ids: tuple[str, ...]
    changed_entity_ids: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()
    undo_available: bool = False
    release_id: str = ""
    item_results: tuple[Mapping[str, Any], ...] = ()
    duration_ms: float = 0.0
    created_at: str = field(default_factory=lambda: _utc_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-bom-batch-result-2.0",
            "transaction_id": self.transaction_id, "action": self.action,
            "status": self.status, "snapshot_sha256": self.snapshot_sha256,
            "preflight_sha256": self.preflight_sha256,
            "before_hash": self.before_hash, "after_hash": self.after_hash,
            "eligible_group_ids": list(self.eligible_group_ids),
            "blocked_group_ids": list(self.blocked_group_ids),
            "changed_entity_ids": list(self.changed_entity_ids),
            "outputs": list(self.outputs), "messages": list(self.messages),
            "undo_available": self.undo_available, "release_id": self.release_id,
            "item_results": [deepcopy(dict(value)) for value in self.item_results],
            "duration_ms": round(float(self.duration_ms), 3),
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class BOMTransactionExecution:
    value: Any
    result: BOMBatchResult


@dataclass(frozen=True, slots=True)
class BOMStockSourceOption:
    source_type: str
    source_id: str
    source_length_mm: float
    cut_plan: tuple[tuple[float, ...], ...]
    kerf_mm: float

    @property
    def source_quantity(self) -> int:
        return len(self.cut_plan)

    @property
    def net_length_mm(self) -> float:
        return sum(sum(values) for values in self.cut_plan)


@dataclass(frozen=True, slots=True)
class BOMStockPiece:
    group_id: str
    occurrence: int
    length_mm: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "occurrence": self.occurrence,
            "length_mm": self.length_mm,
        }


@dataclass(frozen=True, slots=True)
class BOMStockAllocation:
    source_type: str
    source_id: str
    source_instance: int
    source_length_mm: float
    reservation_revision: int
    pieces: tuple[BOMStockPiece, ...]
    kerf_mm: float

    @property
    def used_length_mm(self) -> float:
        return sum(piece.length_mm for piece in self.pieces) + max(0, len(self.pieces) - 1) * self.kerf_mm

    @property
    def remaining_length_mm(self) -> float:
        return max(0.0, self.source_length_mm - self.used_length_mm)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_instance": self.source_instance,
            "source_length_mm": self.source_length_mm,
            "reservation_revision": self.reservation_revision,
            "pieces": [piece.to_dict() for piece in self.pieces],
            "kerf_mm": self.kerf_mm,
            "used_length_mm": self.used_length_mm,
            "remaining_length_mm": self.remaining_length_mm,
        }


@dataclass(frozen=True, slots=True)
class BOMStockAllocationPlan:
    allocations: tuple[BOMStockAllocation, ...]
    unallocated_pieces: tuple[BOMStockPiece, ...]
    kerf_mm: float
    stock_snapshot_sha256: str

    @property
    def complete(self) -> bool:
        return not self.unallocated_pieces

    @property
    def required_length_mm(self) -> float:
        return sum(
            piece.length_mm
            for allocation in self.allocations
            for piece in allocation.pieces
        ) + sum(piece.length_mm for piece in self.unallocated_pieces)

    @property
    def allocated_length_mm(self) -> float:
        return sum(piece.length_mm for allocation in self.allocations for piece in allocation.pieces)

    @property
    def shortage_length_mm(self) -> float:
        return sum(piece.length_mm for piece in self.unallocated_pieces)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-bom-stock-allocation-plan-2.0",
            "allocations": [value.to_dict() for value in self.allocations],
            "unallocated_pieces": [value.to_dict() for value in self.unallocated_pieces],
            "kerf_mm": self.kerf_mm,
            "stock_snapshot_sha256": self.stock_snapshot_sha256,
            "complete": self.complete,
            "required_length_mm": self.required_length_mm,
            "allocated_length_mm": self.allocated_length_mm,
            "shortage_length_mm": self.shortage_length_mm,
        }


class BOMStockAllocator:
    """Deterministic physical stock/remnant matching and reservation."""

    @staticmethod
    def cut_plan(
        lengths: Iterable[float], source_length_mm: float, kerf_mm: float
    ) -> tuple[tuple[float, ...], ...]:
        bins: list[list[float]] = []
        source_length = float(source_length_mm)
        kerf = max(0.0, float(kerf_mm))
        for length in sorted((float(value) for value in lengths), reverse=True):
            if length <= 0.0 or length > source_length:
                return ()
            placed = False
            for values in bins:
                used = sum(values) + max(0, len(values) - 1) * kerf
                if used + kerf + length <= source_length + 1e-6:
                    values.append(length)
                    placed = True
                    break
            if not placed:
                bins.append([length])
        return tuple(tuple(values) for values in bins)

    @staticmethod
    def piece_lengths(rows: Iterable[BOMWorkspaceRow]) -> tuple[float, ...]:
        return tuple(
            float(row.length_mm)
            for row in rows
            for _ in range(max(1, int(round(float(row.quantity or 1.0)))))
        )

    @staticmethod
    def pieces(rows: Iterable[BOMWorkspaceRow]) -> tuple[BOMStockPiece, ...]:
        return tuple(
            BOMStockPiece(row.group_id, occurrence, float(row.length_mm))
            for row in rows
            for occurrence in range(max(1, int(round(float(row.quantity or 1.0)))))
        )

    @staticmethod
    def _identity(rows: Iterable[BOMWorkspaceRow]) -> tuple[str, str]:
        selected = tuple(rows)
        if not selected or any(row.family != "parts" for row in selected):
            raise ValueError("Voorraadtoewijzing accepteert uitsluitend onderdeelregels")
        identities = {(row.profile.casefold(), row.material.casefold()) for row in selected}
        if len(identities) != 1:
            raise ValueError("Een reservering vereist één profiel/materiaalcombinatie")
        if any(float(row.length_mm or 0.0) <= 0.0 for row in selected):
            raise ValueError("Alle geselecteerde onderdelen moeten een positieve lengte hebben")
        return next(iter(identities))

    def plan(
        self,
        project: Any,
        rows: Iterable[BOMWorkspaceRow],
        *,
        kerf_mm: float = 3.0,
        preference: str = "remnants_first",
    ) -> BOMStockAllocationPlan:
        """Allocate occurrences across multiple physical remnants and stock bars.

        The result is deterministic and bound to the reservation revisions used
        during planning.  A partial plan remains useful: its unallocated pieces
        are the exact input for procurement instead of a misleading aggregate
        length subtraction.
        """

        from cws_convertor.manufacturing.m18_runtime_access import install_m18_runtime_access
        install_m18_runtime_access()
        selected = tuple(rows)
        profile_key, material_key = self._identity(selected)
        if preference not in {"remnants_first", "best_fit"}:
            raise ValueError(f"Onbekende voorraadvoorkeur: {preference}")
        kerf = max(0.0, float(kerf_mm))
        candidates: list[dict[str, Any]] = []

        def material_matches(material: Any, grade: Any) -> bool:
            values = {str(value).casefold() for value in (material, grade) if str(value)}
            return not material_key or not values or material_key in values

        for remnant in sorted(project.remnants.values(), key=lambda value: str(value.internal_id)):
            if (
                str(remnant.status).casefold() not in {"available", "beschikbaar"}
                or remnant.reservation_ids
                or str(remnant.profile).casefold() != profile_key
                or not material_matches(remnant.material, remnant.grade)
                or float(remnant.remaining_length_mm or 0.0) <= 0.0
            ):
                continue
            candidates.append({
                "source_type": "remnant", "source_id": str(remnant.internal_id),
                "instance": 0, "length": float(remnant.remaining_length_mm),
                "remaining": float(remnant.remaining_length_mm), "pieces": [],
                "reservation_revision": int(remnant.reservation_revision),
            })
        for stock in sorted(project.stock_items.values(), key=lambda value: str(value.internal_id)):
            free = int(math.floor(max(
                0.0, float(stock.available_quantity) - float(stock.reserved_quantity)
            ) + 1e-9))
            if (
                str(stock.status).casefold() not in {"available", "reserved", "beschikbaar"}
                or str(stock.profile).casefold() != profile_key
                or not material_matches(stock.material, stock.grade)
                or float(stock.stock_length_mm or 0.0) <= 0.0
            ):
                continue
            for instance in range(free):
                candidates.append({
                    "source_type": "full_stock", "source_id": str(stock.internal_id),
                    "instance": instance, "length": float(stock.stock_length_mm),
                    "remaining": float(stock.stock_length_mm), "pieces": [],
                    "reservation_revision": int(stock.reservation_revision),
                })

        pieces = sorted(
            self.pieces(selected),
            key=lambda value: (-value.length_mm, value.group_id, value.occurrence),
        )
        unallocated: list[BOMStockPiece] = []
        for piece in pieces:
            fitting = []
            for candidate in candidates:
                needed = piece.length_mm + (kerf if candidate["pieces"] else 0.0)
                if needed <= candidate["remaining"] + 1e-6:
                    remaining_after = candidate["remaining"] - needed
                    source_rank = 0 if candidate["source_type"] == "remnant" else 1
                    key = (
                        (source_rank, remaining_after)
                        if preference == "remnants_first"
                        else (remaining_after, source_rank)
                    )
                    fitting.append((key, candidate["source_id"], candidate["instance"], candidate, needed))
            if not fitting:
                unallocated.append(piece)
                continue
            _key, _source_id, _instance, candidate, needed = min(fitting)
            candidate["pieces"].append(piece)
            candidate["remaining"] -= needed

        used = [candidate for candidate in candidates if candidate["pieces"]]
        allocations = tuple(
            BOMStockAllocation(
                source_type=str(candidate["source_type"]),
                source_id=str(candidate["source_id"]),
                source_instance=int(candidate["instance"]),
                source_length_mm=float(candidate["length"]),
                reservation_revision=int(candidate["reservation_revision"]),
                pieces=tuple(candidate["pieces"]),
                kerf_mm=kerf,
            )
            for candidate in sorted(
                used,
                key=lambda value: (
                    0 if value["source_type"] == "remnant" else 1,
                    value["source_id"], value["instance"],
                ),
            )
        )
        stock_snapshot = stable_sha256({
            "project_id": str(project.project_id),
            "project_reservation_revision": int(project.profile_nesting_reservation_revision),
            "sources": [
                {
                    "source_type": candidate["source_type"],
                    "source_id": candidate["source_id"],
                    "source_instance": candidate["instance"],
                    "source_length_mm": candidate["length"],
                    "reservation_revision": candidate["reservation_revision"],
                }
                for candidate in candidates
            ],
            "pieces": [piece.to_dict() for piece in pieces],
            "kerf_mm": kerf,
        })
        return BOMStockAllocationPlan(
            allocations=allocations,
            unallocated_pieces=tuple(unallocated),
            kerf_mm=kerf,
            stock_snapshot_sha256=stock_snapshot,
        )

    def options(
        self,
        project: Any,
        rows: Iterable[BOMWorkspaceRow],
        *,
        kerf_mm: float = 3.0,
    ) -> tuple[BOMStockSourceOption, ...]:
        selected = tuple(rows)
        profile_key, material_key = self._identity(selected)
        pieces = self.piece_lengths(selected)
        options: list[BOMStockSourceOption] = []
        for stock in project.stock_items.values():
            free = int(max(0.0, float(stock.available_quantity) - float(stock.reserved_quantity)))
            stock_materials = {
                str(value).casefold() for value in (stock.material, stock.grade) if str(value)
            }
            if (
                str(stock.status).casefold() not in {"available", "reserved"}
                or str(stock.profile).casefold() != profile_key
                or (bool(material_key) and bool(stock_materials) and material_key not in stock_materials)
                or free < 1
            ):
                continue
            plan = self.cut_plan(pieces, float(stock.stock_length_mm), kerf_mm)
            if plan and len(plan) <= free:
                options.append(BOMStockSourceOption(
                    "full_stock", stock.internal_id, float(stock.stock_length_mm),
                    plan, float(kerf_mm),
                ))
        for remnant in project.remnants.values():
            remnant_materials = {
                str(value).casefold() for value in (remnant.material, remnant.grade) if str(value)
            }
            if (
                str(remnant.status).casefold() != "available"
                or remnant.reservation_ids
                or str(remnant.profile).casefold() != profile_key
                or (bool(material_key) and bool(remnant_materials) and material_key not in remnant_materials)
            ):
                continue
            plan = self.cut_plan(pieces, float(remnant.remaining_length_mm), kerf_mm)
            if len(plan) == 1:
                options.append(BOMStockSourceOption(
                    "remnant", remnant.internal_id, float(remnant.remaining_length_mm),
                    plan, float(kerf_mm),
                ))
        return tuple(sorted(options, key=lambda item: (
            item.source_quantity * item.source_length_mm - item.net_length_mm,
            item.source_type, item.source_id,
        )))

    @staticmethod
    def reserve_plan(
        project: Any,
        hub_data: dict[str, Any],
        plan: BOMStockAllocationPlan,
        preflight: "BOMBatchPreflight",
        *,
        user: str = "bom-operator",
    ) -> Any:
        from cws_convertor.optimization.profile_nesting.models import ReservationRequest
        from cws_convertor.optimization.profile_nesting.reservation import reserve_physical_stock

        if not plan.allocations:
            raise ValueError("Het voorraadplan bevat geen reserveerbare fysieke bron")
        planned_groups = {
            piece.group_id for allocation in plan.allocations for piece in allocation.pieces
        } | {piece.group_id for piece in plan.unallocated_pieces}
        if not planned_groups.issubset(set(preflight.eligible_group_ids)):
            raise ValueError("Voorraadplan bevat groepen buiten de bevestigde preflightscope")
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for allocation in plan.allocations:
            value = grouped.setdefault(
                (allocation.source_type, allocation.source_id),
                {"instances": set(), "reservation_revision": allocation.reservation_revision},
            )
            if int(value["reservation_revision"]) != int(allocation.reservation_revision):
                raise ValueError("Voorraadplan bevat conflicterende bronrevisies")
            value["instances"].add(allocation.source_instance)
        requests = []
        for (source_type, source_id), source_plan in sorted(grouped.items()):
            source = (
                project.stock_items.get(source_id)
                if source_type == "full_stock"
                else project.remnants.get(source_id)
            )
            if source is None:
                raise ValueError(f"Fysieke bron {source_id} bestaat niet meer")
            requests.append(ReservationRequest(
                source_type=source_type,
                source_id=source_id,
                quantity=len(source_plan["instances"]) if source_type == "full_stock" else 1,
                expected_reservation_revision=int(source_plan["reservation_revision"]),
            ))
        record = reserve_physical_stock(
            project, requests,
            run_id=f"bom-{preflight.preflight_sha256[:16]}", user=user,
        )
        assignments = hub_data.setdefault("stock_assignments", {})
        for group_id in sorted(planned_groups):
            sources = []
            allocated_pieces = []
            for allocation in plan.allocations:
                matching = tuple(piece for piece in allocation.pieces if piece.group_id == group_id)
                if not matching:
                    continue
                allocated_pieces.extend(matching)
                sources.append({
                    "source_type": allocation.source_type,
                    "source_id": allocation.source_id,
                    "source_instance": allocation.source_instance,
                    "source_length_mm": allocation.source_length_mm,
                    "reservation_revision": allocation.reservation_revision,
                    "piece_occurrences": [piece.occurrence for piece in matching],
                    "piece_lengths_mm": [piece.length_mm for piece in matching],
                })
            missing = tuple(piece for piece in plan.unallocated_pieces if piece.group_id == group_id)
            source_types = {source["source_type"] for source in sources}
            source_ids = {source["source_id"] for source in sources}
            assignments[group_id] = {
                "schema": "cws-bom-stock-assignment-2.0",
                "source_type": next(iter(source_types)) if len(source_types) == 1 else "mixed",
                "source_id": next(iter(source_ids)) if len(source_ids) == 1 else "mixed",
                "sources": sources,
                "reservation_id": record.reservation_id,
                "kerf_mm": plan.kerf_mm,
                "allocated_piece_count": len(allocated_pieces),
                "allocated_length_mm": sum(piece.length_mm for piece in allocated_pieces),
                "unallocated_piece_count": len(missing),
                "unallocated_length_mm": sum(piece.length_mm for piece in missing),
                "status": "partial" if missing else "allocated",
                "stock_snapshot_sha256": plan.stock_snapshot_sha256,
                "preflight_sha256": preflight.preflight_sha256,
            }
        return record

    @staticmethod
    def reserve(
        project: Any,
        hub_data: dict[str, Any],
        rows: Iterable[BOMWorkspaceRow],
        option: BOMStockSourceOption,
        preflight: "BOMBatchPreflight",
        *,
        user: str = "bom-operator",
    ) -> Any:
        selected = tuple(rows)
        source = (
            project.stock_items.get(option.source_id)
            if option.source_type == "full_stock"
            else project.remnants.get(option.source_id)
        )
        if source is None:
            raise ValueError(f"Fysieke bron {option.source_id} bestaat niet")
        remaining = list(BOMStockAllocator.pieces(selected))
        allocations = []
        for source_instance, lengths in enumerate(option.cut_plan):
            assigned = []
            for length in lengths:
                index = next(
                    (idx for idx, piece in enumerate(remaining) if abs(piece.length_mm - float(length)) <= 1e-6),
                    None,
                )
                if index is None:
                    raise ValueError("Legacy voorraadplan komt niet overeen met de geselecteerde occurrences")
                assigned.append(remaining.pop(index))
            allocations.append(BOMStockAllocation(
                source_type=option.source_type, source_id=option.source_id,
                source_instance=source_instance, source_length_mm=option.source_length_mm,
                reservation_revision=int(source.reservation_revision),
                pieces=tuple(assigned), kerf_mm=option.kerf_mm,
            ))
        plan = BOMStockAllocationPlan(
            allocations=tuple(allocations), unallocated_pieces=tuple(remaining),
            kerf_mm=option.kerf_mm,
            stock_snapshot_sha256=stable_sha256({
                "legacy_source": option.source_id,
                "preflight_sha256": preflight.preflight_sha256,
                "allocations": [value.to_dict() for value in allocations],
            }),
        )
        return BOMStockAllocator.reserve_plan(
            project, hub_data, plan, preflight, user=user
        )

    @staticmethod
    def release_assignments(
        project: Any,
        hub_data: dict[str, Any],
        group_ids: Iterable[str],
        *,
        user: str = "bom-operator",
    ) -> tuple[str, ...]:
        from cws_convertor.optimization.profile_nesting.reservation import release_reservation

        requested = set(_unique(group_ids))
        assignments = hub_data.setdefault("stock_assignments", {})
        reservation_ids = {
            str(assignments[group_id].get("reservation_id") or "")
            for group_id in requested if group_id in assignments
        } - {""}
        if not reservation_ids:
            raise ValueError("De selectie heeft geen actieve voorraadreservering")
        for reservation_id in reservation_ids:
            linked = {
                group_id for group_id, assignment in assignments.items()
                if str(assignment.get("reservation_id") or "") == reservation_id
            }
            if not linked.issubset(requested):
                raise ValueError(
                    "Een fysieke reservering kan alleen voor alle gekoppelde BOM-groepen tegelijk worden vrijgegeven"
                )
        for reservation_id in sorted(reservation_ids):
            release_reservation(project, reservation_id, user=user)
        for group_id in tuple(assignments):
            if group_id in requested:
                assignments.pop(group_id, None)
        return tuple(sorted(reservation_ids))


class BOMProcurementService:
    """Canonical purchase-need creation, editing and release authority."""

    @staticmethod
    def generate_needs(
        project: Any,
        hub_data: dict[str, Any],
        rows: Iterable[BOMWorkspaceRow],
        preflight: "BOMBatchPreflight",
        *,
        user: str = "bom-operator",
    ) -> tuple[str, ...]:
        from cws_convertor.project import PurchasedItem

        created: list[str] = []
        orders = hub_data.setdefault("purchase_orders", [])
        for row in rows:
            assignment = dict((hub_data.get("stock_assignments") or {}).get(row.group_id) or {})
            shortage = float(
                assignment.get("unallocated_length_mm")
                if "unallocated_length_mm" in assignment
                else row.shortage_mm or 0.0
            )
            if (
                not assignment and shortage <= 0.001
                and str(row.stock_status).casefold()
                in {"beschikbaar", "toegewezen", "available", "allocated"}
            ):
                continue
            required = (
                shortage
                if "unallocated_length_mm" in assignment
                else shortage if shortage > 0.001
                else float(row.length_mm or 0.0) * float(row.quantity or 1.0)
            )
            if required <= 0.0:
                continue
            active = [
                order for order in orders
                if order.get("source_group_id") == row.group_id
                and str(order.get("status") or "").casefold()
                not in {"cancelled", "closed", "received"}
            ]
            if active:
                raise ValueError(
                    f"BOM-groep {row.group_id} heeft al een actieve inkoopbehoefte"
                )
            entity_id = str(uuid4())
            piece_length = max(float(row.length_mm or required), 1.0)
            quantity = max(1.0, math.ceil(required / piece_length))
            supplier = row.supplier if row.supplier not in {"", "-", "Gemengd"} else ""
            item = PurchasedItem(
                internal_id=entity_id,
                name=f"Inkoopbehoefte {row.profile or row.mark or row.group_id}",
                article_number=f"AUTO-{entity_id[:8].upper()}",
                supplier=supplier,
                description=row.description or row.profile,
                material=row.material,
                grade=row.material,
                dimensions={"profile": row.profile, "required_length_mm": required},
                quantity=quantity,
                unit="piece",
                unit_price=float(row.unit_price or 0.0),
                lead_time_days=int(row.lead_time_days or 0),
                purchase_status="review_required",
                properties={
                    "source_bom_group": row.group_id,
                    "expected_delivery": row.expected_delivery,
                    "purchase_release_status": "draft",
                    "required_length_mm": required,
                    "stock_assignment_sha256": stable_sha256(assignment) if assignment else "",
                    "preflight_sha256": preflight.preflight_sha256,
                },
            )
            project.add_entity(item, user=user)
            created.append(entity_id)
            orders.append({
                "purchase_item_id": entity_id, "source_group_id": row.group_id,
                "status": "draft", "required_length_mm": required,
                "preflight_sha256": preflight.preflight_sha256,
            })
        if not created:
            raise ValueError("De selectie bevat geen berekenbare inkoopbehoefte")
        return tuple(created)

    @staticmethod
    def edit(
        project: Any,
        purchase_ids: Iterable[str],
        field_name: str,
        value: str,
    ) -> int:
        ids = _unique(purchase_ids)
        for entity_id in ids:
            item = project.purchased_items.get(entity_id)
            if item is None:
                raise KeyError(f"Onbekende inkoopregel {entity_id}")
            if field_name == "supplier":
                item.supplier = str(value).strip()
            elif field_name == "unit_price":
                item.unit_price = float(str(value).replace(",", "."))
            elif field_name == "lead_time_days":
                item.lead_time_days = int(value)
            elif field_name == "expected_delivery":
                item.properties["expected_delivery"] = str(value).strip()
            elif field_name == "alternative":
                alternative = str(value).strip()
                if alternative and alternative not in item.alternatives:
                    item.alternatives.append(alternative)
            elif field_name == "purchase_status":
                item.purchase_status = str(value).strip()
            else:
                raise ValueError(f"Onbekend inkoopveld {field_name}")
        return len(ids)

    @staticmethod
    def release(
        project: Any,
        hub_data: dict[str, Any],
        purchase_ids: Iterable[str],
    ) -> int:
        ids = _unique(purchase_ids)
        for entity_id in ids:
            item = project.purchased_items.get(entity_id)
            if item is None:
                raise KeyError(f"Onbekende inkoopregel {entity_id}")
            if not item.supplier or float(item.quantity or 0.0) <= 0.0:
                raise ValueError(f"Inkoopregel {entity_id} mist leverancier of hoeveelheid")
            item.purchase_status = "released"
            item.properties["purchase_release_status"] = "released"
            item.properties["purchase_released_at"] = _utc_now()
            for order in hub_data.setdefault("purchase_orders", []):
                if order.get("purchase_item_id") == entity_id:
                    order["status"] = "released"
                    order["released_at"] = item.properties["purchase_released_at"]
        return len(ids)

    @staticmethod
    def cancel(
        project: Any,
        hub_data: dict[str, Any],
        purchase_ids: Iterable[str],
        *,
        reason: str,
    ) -> int:
        ids = _unique(purchase_ids)
        if not str(reason).strip():
            raise ValueError("Een annuleringsreden is verplicht")
        for entity_id in ids:
            item = project.purchased_items.get(entity_id)
            if item is None:
                raise KeyError(f"Onbekende inkoopregel {entity_id}")
            if str(item.purchase_status).casefold() in {"received", "geleverd", "closed"}:
                raise ValueError(f"Inkoopregel {entity_id} is al ontvangen of afgesloten")
            item.purchase_status = "cancelled"
            item.properties["purchase_release_status"] = "cancelled"
            item.properties["purchase_cancelled_at"] = _utc_now()
            item.properties["purchase_cancel_reason"] = str(reason).strip()
            for order in hub_data.setdefault("purchase_orders", []):
                if order.get("purchase_item_id") == entity_id:
                    order["status"] = "cancelled"
                    order["cancelled_at"] = item.properties["purchase_cancelled_at"]
                    order["cancel_reason"] = str(reason).strip()
        return len(ids)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


_MISSING = object()


def _field_level_deltas(
    before: Any,
    after: Any,
    *,
    prefix: str = "",
    entity_id: str = "",
) -> tuple[BOMFieldDelta, ...]:
    """Return deterministic leaf deltas without flattening list semantics."""

    result: list[BOMFieldDelta] = []

    def visit(left: Any, right: Any, path: str) -> None:
        if left is _MISSING and isinstance(right, Mapping):
            for key in sorted(right, key=str):
                child = f"{path}.{key}" if path else str(key)
                visit(_MISSING, right[key], child)
            return
        if right is _MISSING and isinstance(left, Mapping):
            for key in sorted(left, key=str):
                child = f"{path}.{key}" if path else str(key)
                visit(left[key], _MISSING, child)
            return
        if isinstance(left, Mapping) and isinstance(right, Mapping):
            for key in sorted(set(left) | set(right), key=str):
                child = f"{path}.{key}" if path else str(key)
                visit(left.get(key, _MISSING), right.get(key, _MISSING), child)
            return
        if left is not _MISSING and right is not _MISSING and left == right:
            return
        change = "added" if left is _MISSING else "removed" if right is _MISSING else "changed"
        result.append(BOMFieldDelta(
            field_path=path or prefix or "value",
            entity_id=entity_id,
            change=change,
            before=None if left is _MISSING else deepcopy(left),
            after=None if right is _MISSING else deepcopy(right),
        ))

    visit(before, after, prefix)
    return tuple(result)


def _transaction_payload(project: Any) -> dict[str, Any]:
    """Stable business payload used for persistent, non-recursive undo."""

    payload = deepcopy(project.to_dict())
    for key in ("audit_log", "modified_at", "revisions"):
        payload.pop(key, None)
    settings = payload.get("settings")
    if isinstance(settings, dict):
        hub = settings.get(HUB_SETTINGS_KEY)
        if isinstance(hub, dict):
            for key in ("history", "undo", "batch_results"):
                hub.pop(key, None)
    return payload


def _build_inverse_patch(before: Any, after: Any) -> tuple[dict[str, Any], ...]:
    operations: list[dict[str, Any]] = []

    def visit(left: Any, right: Any, path: tuple[str, ...]) -> None:
        if isinstance(left, Mapping) and isinstance(right, Mapping):
            for key in sorted(set(left) | set(right), key=str):
                child = (*path, str(key))
                if key not in left:
                    operations.append({"op": "remove", "path": list(child)})
                elif key not in right:
                    operations.append({
                        "op": "set", "path": list(child), "value": deepcopy(left[key]),
                    })
                else:
                    visit(left[key], right[key], child)
            return
        if left != right:
            operations.append({
                "op": "set", "path": list(path), "value": deepcopy(left),
            })

    visit(before, after, ())
    return tuple(operations)


def _apply_inverse_patch(payload: dict[str, Any], operations: Iterable[Mapping[str, Any]]) -> None:
    for operation in operations:
        path = tuple(str(value) for value in operation.get("path") or ())
        if not path:
            raise ValueError("Ongeldige lege undo-patch")
        parent: dict[str, Any] = payload
        for key in path[:-1]:
            child = parent.get(key)
            if not isinstance(child, dict):
                child = {}
                parent[key] = child
            parent = child
        if operation.get("op") == "remove":
            parent.pop(path[-1], None)
        elif operation.get("op") == "set":
            parent[path[-1]] = deepcopy(operation.get("value"))
        else:
            raise ValueError(f"Onbekende undo-patchbewerking: {operation.get('op')}")


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


def _row_payload(
    row: BOMWorkspaceRow,
    project: Any,
    *,
    bounds_by_entity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    fields = {
        name: deepcopy(getattr(row, name, None))
        for name in (
            "family", "group_id", "entity_ids", "mark", "description", "profile",
            "material", "length_mm", "quantity", "total_mass_kg", "total_surface_m2",
            "machine", "document_status", "phase", "delivery", "release_status",
            "nesting_status", "production_status", "stock_status", "supplier",
            "available_stock_mm", "shortage_mm", "unit_price", "total_price",
            "lead_time_days", "expected_delivery", "purchase_status", "status",
            "blocked", "blocking_reasons", "geometry_status", "material_status",
            "machine_status", "nc_status", "scribing_status", "conflict_status",
            "delivery_status", "assigned_stock", "assigned_remnant",
            "alternative_material", "purchase_release_status",
        )
        if hasattr(row, name)
    }
    fields["entity_ids"] = list(row.entity_ids)
    fields["blocking_reasons"] = list(row.blocking_reasons)
    fields["entity_evidence"] = []
    for entity_id in row.entity_ids:
        entity = project.get_entity(entity_id) if hasattr(project, "get_entity") else None
        evidence = {
            "entity_id": entity_id,
            "entity_type": str(getattr(entity, "entity_type", "") or ""),
            "geometry_hash": str(getattr(entity, "geometry_hash", "") or ""),
            "manufacturing_hash": str(getattr(entity, "manufacturing_hash", "") or ""),
            "production_features": deepcopy(getattr(entity, "production_features", ()) or ()),
            "entity_fields": deepcopy(
                entity.base_to_dict() if entity is not None and hasattr(entity, "base_to_dict") else {}
            ),
        }
        if bounds_by_entity and entity_id in bounds_by_entity:
            evidence["world_bounds"] = deepcopy(bounds_by_entity[entity_id])
        fields["entity_evidence"].append(evidence)
    fields["fingerprint"] = stable_sha256(fields)
    return fields


_ALL_FAMILIES = ("parts", "assemblies", "purchase", "fasteners", "welds", "materials", "conflicts")
_MODEL_FAMILIES = ("parts", "assemblies", "purchase", "fasteners", "welds")
ACTION_DEFINITIONS = (
    # Bekijken en controleren
    BOMActionDefinition("viewer.zoom", "Zoom naar selectie", "Bekijken en controleren", _MODEL_FAMILIES, "viewer"),
    BOMActionDefinition("viewer.fit", "Passend in beeld", "Bekijken en controleren", _MODEL_FAMILIES, "viewer"),
    BOMActionDefinition("viewer.isolate", "Isoleren", "Bekijken en controleren", _MODEL_FAMILIES, "viewer"),
    BOMActionDefinition("viewer.ghost", "Andere objecten ghosten", "Bekijken en controleren", _MODEL_FAMILIES, "viewer"),
    BOMActionDefinition("viewer.hide", "Verbergen", "Bekijken en controleren", _MODEL_FAMILIES, "viewer"),
    BOMActionDefinition("viewer.show_all", "Alles opnieuw tonen", "Bekijken en controleren", _ALL_FAMILIES, "viewer", allow_blocked=True),
    BOMActionDefinition("viewer.section", "Doorsnede rond selectie", "Bekijken en controleren", _MODEL_FAMILIES, "viewer"),
    BOMActionDefinition("viewer.measure", "Meten", "Bekijken en controleren", _MODEL_FAMILIES, "viewer"),
    BOMActionDefinition("inspect.properties", "Eigenschappen openen", "Bekijken en controleren", _ALL_FAMILIES, "inspect", allow_blocked=True),
    BOMActionDefinition("inspect.source", "Bronobject tonen", "Bekijken en controleren", _MODEL_FAMILIES, "inspect", allow_blocked=True),
    BOMActionDefinition("inspect.assembly", "Assemblycontext tonen", "Bekijken en controleren", _MODEL_FAMILIES, "inspect", allow_blocked=True),
    BOMActionDefinition("inspect.hashes", "Geometrie/productiehash bekijken", "Bekijken en controleren", _MODEL_FAMILIES, "inspect", allow_blocked=True),
    BOMActionDefinition("inspect.blockers", "Conflicten en blockers tonen", "Bekijken en controleren", _ALL_FAMILIES, "inspect", allow_blocked=True),
    # Bewerken
    BOMActionDefinition("edit.profile", "Profiel aanpassen", "Bewerken", ("parts",), "edit", True),
    BOMActionDefinition("edit.material", "Materiaal aanpassen", "Bewerken", ("parts", "purchase"), "edit", True),
    BOMActionDefinition("edit.length", "Lengte aanpassen", "Bewerken", ("parts", "purchase"), "edit", True),
    BOMActionDefinition("edit.mark", "Merk/positie aanpassen", "Bewerken", ("parts", "assemblies"), "edit", True),
    BOMActionDefinition("edit.phase", "Fase wijzigen", "Bewerken", _MODEL_FAMILIES, "edit", True),
    BOMActionDefinition("edit.classification", "Classificatie wijzigen", "Bewerken", ("parts", "purchase"), "edit", True),
    BOMActionDefinition("edit.assembly_add", "Aan assembly toevoegen", "Bewerken", ("parts", "purchase"), "edit", True),
    BOMActionDefinition("edit.assembly_remove", "Uit assembly verwijderen", "Bewerken", ("parts", "purchase"), "edit", True),
    BOMActionDefinition("edit.orientation", "Productieoriëntatie aanpassen", "Bewerken", ("parts",), "edit", True),
    BOMActionDefinition("edit.revision", "Revisiestatus aanpassen", "Bewerken", _MODEL_FAMILIES, "edit", True),
    BOMActionDefinition("edit.comment", "Opmerking toevoegen", "Bewerken", _ALL_FAMILIES, "edit", True, True),
    # Tekening en documenten
    BOMActionDefinition("drawing.open_part", "Onderdeeltekening openen", "Tekening en documenten", ("parts",), "drawings"),
    BOMActionDefinition("drawing.generate", "Tekening genereren", "Tekening en documenten", ("parts", "assemblies"), "drawings", True),
    BOMActionDefinition("drawing.regenerate", "Tekening opnieuw genereren", "Tekening en documenten", ("parts", "assemblies"), "drawings", True),
    BOMActionDefinition("drawing.open_assembly", "Assemblytekening openen", "Tekening en documenten", ("assemblies",), "drawings"),
    BOMActionDefinition("drawing.preview", "PDF-preview", "Tekening en documenten", ("parts", "assemblies"), "drawings"),
    BOMActionDefinition("drawing.setup", "Formaat, schaal en aanzichten instellen", "Tekening en documenten", ("parts", "assemblies"), "drawings", True),
    BOMActionDefinition("drawing.format", "Formaat kiezen (A4 t/m A0)", "Tekening en documenten", ("parts", "assemblies"), "drawings", True),
    BOMActionDefinition("drawing.scale", "Schaal automatisch of handmatig", "Tekening en documenten", ("parts", "assemblies"), "drawings", True),
    BOMActionDefinition("drawing.views", "Aanzichten kiezen", "Tekening en documenten", ("parts", "assemblies"), "drawings", True),
    BOMActionDefinition("drawing.dimension_check", "Maatvoering controleren", "Tekening en documenten", ("parts", "assemblies"), "drawings"),
    BOMActionDefinition("drawing.revision", "Tekeningrevisie toevoegen", "Tekening en documenten", ("parts", "assemblies"), "drawings", True),
    BOMActionDefinition("drawing.approve", "Tekening goedkeuren", "Tekening en documenten", ("parts", "assemblies"), "drawings", True),
    BOMActionDefinition("drawing.batch_pdf", "Batch-PDF maken", "Tekening en documenten", ("parts", "assemblies"), "drawings"),
    BOMActionDefinition("drawing.print", "Printen", "Tekening en documenten", ("parts", "assemblies"), "print"),
    # Machine en productie
    BOMActionDefinition("machine.recommend", "Aanbevolen machine bekijken", "Machine en productie", ("parts",), "machine"),
    BOMActionDefinition("machine.explain", "Waarom deze machine?", "Machine en productie", ("parts",), "machine", allow_blocked=True),
    BOMActionDefinition("machine.assign", "Machine toewijzen", "Machine en productie", ("parts",), "machine", True),
    BOMActionDefinition("machine.auto_accept", "Automatische toewijzing accepteren", "Machine en productie", ("parts",), "machine", True),
    BOMActionDefinition("machine.manual_lock", "Handmatige toewijzing vergrendelen", "Machine en productie", ("parts",), "machine", True),
    BOMActionDefinition("machine.reset", "Machinekeuze resetten", "Machine en productie", ("parts",), "machine", True),
    BOMActionDefinition("machine.validate", "Geschiktheid opnieuw controleren", "Machine en productie", ("parts",), "machine"),
    BOMActionDefinition("machine.alternatives", "Alternatieve machine tonen", "Machine en productie", ("parts",), "machine"),
    BOMActionDefinition("machine.blocker", "Productieblokker bekijken", "Machine en productie", ("parts",), "inspect", allow_blocked=True),
    BOMActionDefinition("production.route", "Productieroute bekijken", "Machine en productie", ("parts", "assemblies"), "production"),
    BOMActionDefinition("production.operations", "Bewerkingen bekijken", "Machine en productie", ("parts",), "production"),
    BOMActionDefinition("production.nc_preview", "NC1/DSTV-preview", "Machine en productie", ("parts",), "export"),
    BOMActionDefinition("production.release", "Vrijgeven voor productie", "Machine en productie", ("parts", "assemblies"), "production", True, False, True),
    BOMActionDefinition("production.withdraw", "Productievrijgave intrekken", "Machine en productie", ("parts", "assemblies"), "production", True),
    # Optimalisatie en voorraad
    BOMActionDefinition("optimize.profile", "Profielnesting starten", "Optimalisatie en voorraad", ("parts", "materials"), "optimize"),
    BOMActionDefinition("optimize.plate", "Plaatnesting starten", "Optimalisatie en voorraad", ("parts", "materials"), "optimize"),
    BOMActionDefinition("optimize.trade_length", "Optimaliseren op handelslengte", "Optimalisatie en voorraad", ("parts", "materials"), "optimize"),
    BOMActionDefinition("optimize.stock", "Optimaliseren op aanwezige voorraad", "Optimalisatie en voorraad", ("parts", "materials"), "optimize"),
    BOMActionDefinition("optimize.remnants_include", "Reststukken meenemen", "Optimalisatie en voorraad", ("parts", "materials"), "optimize"),
    BOMActionDefinition("optimize.remnants_exclude", "Reststukken uitsluiten", "Optimalisatie en voorraad", ("parts", "materials"), "optimize"),
    BOMActionDefinition("optimize.kerf", "Zaagverlies instellen", "Optimalisatie en voorraad", ("parts", "materials"), "optimize"),
    BOMActionDefinition("stock.plan", "Voorraad- en reststukplan berekenen", "Optimalisatie en voorraad", ("parts",), "stock"),
    BOMActionDefinition("stock.assign", "Toewijzen aan voorraadstuk", "Optimalisatie en voorraad", ("parts",), "stock", True),
    BOMActionDefinition("stock.release", "Voorraadreservering vrijgeven", "Optimalisatie en voorraad", ("parts",), "stock", True),
    BOMActionDefinition("stock.shortage", "Materiaaltekort berekenen", "Optimalisatie en voorraad", ("parts", "materials"), "stock"),
    BOMActionDefinition("purchase.generate", "Inkoopbehoefte genereren", "Optimalisatie en voorraad", ("parts", "materials", "purchase"), "purchase", True),
    BOMActionDefinition("purchase.edit", "Inkoopgegevens bewerken", "Optimalisatie en voorraad", ("purchase",), "purchase", True),
    BOMActionDefinition("purchase.release", "Inkoop vrijgeven", "Optimalisatie en voorraad", ("purchase",), "purchase", True),
    BOMActionDefinition("purchase.cancel", "Inkoop annuleren", "Optimalisatie en voorraad", ("purchase",), "purchase", True),
    BOMActionDefinition("optimize.alternatives", "Alternatieve profielen/materialen", "Optimalisatie en voorraad", ("parts", "purchase", "materials"), "optimize"),
    BOMActionDefinition("optimize.compare", "Vergelijken met vorige optimalisatie", "Optimalisatie en voorraad", ("parts", "materials"), "optimize"),
    # Export
    BOMActionDefinition("export.production", "NC1/STEP/IFC/DXF/productie-PDF", "Export", ("parts", "assemblies"), "export", requires_production_ready=True),
    BOMActionDefinition("export.review", "XLSX/CSV/JSON/PDF/BOM-package", "Export", _ALL_FAMILIES, "review_export", allow_blocked=True),
    BOMActionDefinition("export.grouping", "Groeperen per onderdeel/merk/assembly/machine/fase/levering", "Export", _ALL_FAMILIES, "export"),
    BOMActionDefinition("export.nc1", "NC1/DSTV", "Export", ("parts",), "export", requires_production_ready=True),
    BOMActionDefinition("export.step", "STEP", "Export", ("parts", "assemblies"), "export"),
    BOMActionDefinition("export.ifc", "IFC", "Export", ("parts", "assemblies"), "export"),
    BOMActionDefinition("export.dxf", "DXF", "Export", ("parts", "assemblies"), "export"),
    BOMActionDefinition("export.pdf", "PDF", "Export", _MODEL_FAMILIES, "export"),
    BOMActionDefinition("export.xlsx", "XLSX", "Export", _ALL_FAMILIES, "review_export", allow_blocked=True),
    BOMActionDefinition("export.csv", "CSV", "Export", _ALL_FAMILIES, "review_export", allow_blocked=True),
    BOMActionDefinition("export.json", "JSON", "Export", _ALL_FAMILIES, "review_export", allow_blocked=True),
    BOMActionDefinition("export.package", "Productiepackage", "Export", ("parts", "assemblies"), "export", requires_production_ready=True),
    BOMActionDefinition("export.occurrences", "Alleen geselecteerde occurrences", "Export", _MODEL_FAMILIES, "export"),
    BOMActionDefinition("export.per_part", "Eén bestand per onderdeel", "Export", ("parts",), "export"),
    BOMActionDefinition("export.per_mark", "Eén bestand per merk", "Export", ("parts", "assemblies"), "export"),
    BOMActionDefinition("export.per_assembly", "Eén package per assembly", "Export", ("assemblies",), "export"),
    BOMActionDefinition("export.per_machine", "Eén package per machine", "Export", ("parts",), "export"),
    BOMActionDefinition("export.per_phase", "Eén package per fase of levering", "Export", _MODEL_FAMILIES, "export"),
)


class BOMActionMatrix:
    def __init__(self, definitions: Iterable[BOMActionDefinition] = ACTION_DEFINITIONS) -> None:
        self.definitions = tuple(definitions)

    def available(
        self,
        rows: Iterable[BOMWorkspaceRow],
        *,
        production_ready: bool,
    ) -> tuple[tuple[BOMActionDefinition, bool, str], ...]:
        selected = tuple(rows)
        families = {row.family for row in selected}
        result = []
        for definition in self.definitions:
            enabled = bool(selected) and families.issubset(set(definition.families))
            reason = "" if enabled else (
                "Selecteer minimaal één BOM-regel"
                if not selected else "Niet beschikbaar voor deze objectfamilie"
            )
            if enabled and any(row.blocked for row in selected) and not definition.allow_blocked:
                enabled, reason = False, "Selectie bevat geblokkeerde regels"
            if enabled and definition.requires_production_ready and not production_ready:
                enabled, reason = False, "De volledige BOM is niet productiegereed"
            if enabled:
                reason = self._selection_requirement(definition.action_id, selected)
                enabled = not reason
            result.append((definition, enabled, reason))
        return tuple(result)

    @staticmethod
    def _selection_requirement(
        action_id: str,
        rows: tuple[BOMWorkspaceRow, ...],
    ) -> str:
        entity_actions = (
            "viewer.", "inspect.source", "inspect.assembly", "inspect.hashes",
            "edit.", "drawing.", "machine.", "production.", "export.occurrences",
        )
        if action_id.startswith(entity_actions) and not any(row.entity_ids for row in rows):
            return "De selectie bevat geen gekoppelde canonieke objecten"
        if action_id in {"stock.plan", "stock.assign"}:
            identities = {
                (row.profile.casefold(), row.material.casefold()) for row in rows
            }
            if len(identities) != 1:
                return "Selecteer één profiel/materiaalcombinatie"
            if any(float(row.length_mm or 0.0) <= 0.0 for row in rows):
                return "Een of meer onderdelen hebben geen geldige lengte"
            if action_id == "stock.assign" and not any(
                float(row.available_stock_mm or 0.0) > 0.0 for row in rows
            ):
                return "Geen passende fysieke voorraad of reststukken beschikbaar"
        if action_id == "stock.release" and not any(
            row.assigned_stock or row.assigned_remnant for row in rows
        ):
            return "De selectie heeft geen actieve voorraadreservering"
        if action_id == "purchase.generate" and all(
            float(row.shortage_mm or 0.0) <= 0.0
            and str(row.stock_status).casefold() not in {"tekort", "shortage"}
            for row in rows
        ):
            return "De selectie bevat geen aantoonbare inkoopbehoefte"
        if action_id == "purchase.release":
            if any(not row.supplier or row.supplier in {"-", "Gemengd"} for row in rows):
                return "Vul voor alle inkoopregels een leverancier in"
            if any(str(row.purchase_status).casefold() in {"released", "received", "cancelled"} for row in rows):
                return "Selectie bevat al vrijgegeven, ontvangen of geannuleerde inkoopregels"
        if action_id == "purchase.cancel" and any(
            str(row.purchase_status).casefold() in {"received", "closed", "cancelled"}
            for row in rows
        ):
            return "Ontvangen, afgesloten of geannuleerde inkoopregels kunnen niet opnieuw worden geannuleerd"
        if action_id in {"machine.manual_lock", "machine.reset"} and any(
            not row.machine or row.machine == "-" for row in rows
        ):
            return "Niet alle geselecteerde onderdelen hebben een machinekeuze"
        if action_id == "machine.auto_accept" and any(
            row.machine_status.casefold() not in {"gereed", "ready", "eligible", "assigned"}
            for row in rows
        ):
            return "Niet alle automatische machinekeuzes zijn capability-gevalideerd"
        if action_id == "production.withdraw" and any(
            row.release_status.casefold() not in {"released", "vrijgegeven", "approved"}
            for row in rows
        ):
            return "De selectie bevat niet-vrijgegeven regels"
        if action_id in {"drawing.open_part", "drawing.open_assembly", "drawing.preview", "drawing.print"} and any(
            str(row.document_status).casefold() in {"", "-", "unknown", "onbekend", "review_required"}
            for row in rows
        ):
            return "Een of meer tekeningen ontbreken of vereisen review"
        if action_id == "export.nc1" and any(
            row.nc_status.casefold() not in {"gereed", "ready", "released", "ok"}
            for row in rows
        ):
            return "Niet alle geselecteerde onderdelen zijn NC-gereed"
        return ""


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

    @staticmethod
    def _matches_clause(row: BOMWorkspaceRow, clause: BOMQueryClause) -> bool:
        raw = getattr(row, clause.field, "")
        left = str(raw if raw is not None else "").strip()
        right = str(clause.value or "").strip()
        operator = clause.operator
        if operator == "is_empty":
            return left in {"", "-", "onbekend", "unknown"}
        if operator == "is_not_empty":
            return left not in {"", "-", "onbekend", "unknown"}
        if operator in {"greater_than", "less_than"}:
            try:
                lhs, rhs = float(raw or 0.0), float(right)
            except (TypeError, ValueError):
                return False
            return lhs > rhs if operator == "greater_than" else lhs < rhs
        lhs, rhs = left.casefold(), right.casefold()
        if operator == "equals":
            return lhs == rhs
        if operator == "not_equals":
            return lhs != rhs
        if operator == "contains":
            return rhs in lhs
        if operator == "not_contains":
            return rhs not in lhs
        return False

    def query(self, smart_query: BOMSmartQuery) -> tuple[BOMWorkspaceRow, ...]:
        rows = self.model.family_rows(smart_query.family)

        def matches_group(row: BOMWorkspaceRow, group: BOMQueryGroup) -> bool:
            values = [self._matches_clause(row, clause) for clause in group.clauses]
            values.extend(matches_group(row, nested) for nested in group.groups)
            predicate = all if group.match == "all" else any
            result = predicate(values)
            return not result if group.negate else result

        def matches(row: BOMWorkspaceRow) -> bool:
            values = [self._matches_clause(row, clause) for clause in smart_query.clauses]
            values.extend(matches_group(row, group) for group in smart_query.groups)
            predicate = all if smart_query.match == "all" else any
            result = predicate(values)
            return not result if smart_query.negate else result

        return tuple(row for row in rows if matches(row))

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
        strict = (
            action not in {"review_export", "inspect", "report", "comment"}
            and not allow_blocked_review_export
        )
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
        self._runtime_project_undo: dict[str, dict[str, Any]] = {}

    @property
    def data(self) -> dict[str, Any]:
        settings = self.project.settings.setdefault(HUB_SETTINGS_KEY, {})
        settings.setdefault("saved_selections", [])
        settings.setdefault("smart_queries", [])
        settings.setdefault("basket_entity_ids", [])
        settings.setdefault("history", [])
        settings.setdefault("undo", [])
        settings.setdefault("batch_results", [])
        settings.setdefault("external_releases", [])
        settings.setdefault("stock_assignments", {})
        settings.setdefault("purchase_orders", [])
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

    def smart_queries(self) -> tuple[BOMSmartQuery, ...]:
        return tuple(BOMSmartQuery.from_dict(value) for value in self.data["smart_queries"])

    def save_smart_query(
        self,
        name: str,
        family: str,
        clauses: Iterable[BOMQueryClause],
        *,
        groups: Iterable[BOMQueryGroup] = (),
        match: str = "all",
        negate: bool = False,
        user: str = "bom-operator",
    ) -> BOMSmartQuery:
        query = BOMSmartQuery(
            query_id=str(uuid4()), name=str(name).strip(), family=str(family),
            match=str(match), clauses=tuple(clauses), groups=tuple(groups),
            negate=bool(negate),
        )
        if not query.name:
            raise ValueError("Naam van slimme selectie ontbreekt")
        self.data["smart_queries"].append(query.to_dict())
        self._history("smart_query.saved", user, query.to_dict())
        return query

    def delete_smart_query(self, query_id: str, *, user: str = "bom-operator") -> None:
        before = list(self.data["smart_queries"])
        self.data["smart_queries"] = [
            value for value in before if str(value.get("query_id")) != str(query_id)
        ]
        if len(before) == len(self.data["smart_queries"]):
            raise KeyError(query_id)
        self._history("smart_query.deleted", user, {"query_id": str(query_id)})

    def set_revision_baseline(
        self,
        model: BOMWorkspaceReadModel,
        *,
        bounds_by_entity: Mapping[str, Any] | None = None,
        user: str = "bom-operator",
    ) -> str:
        payload = {
            row.group_id: _row_payload(
                row, self.project, bounds_by_entity=bounds_by_entity
            )
            for family in model._rows
            for row in model.family_rows(family)
        }
        baseline = {
            "schema": "cws-bom-revision-baseline-2.0",
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

    def revision_deltas(self, model: BOMWorkspaceReadModel) -> dict[str, BOMRevisionDelta]:
        baseline = dict(self.data.get("revision_baseline") or {})
        old = dict(baseline.get("groups") or {})
        result: dict[str, BOMRevisionDelta] = {}
        current: dict[str, dict[str, Any]] = {
            row.group_id: _row_payload(row, self.project)
            for family in model._rows
            for row in model.family_rows(family)
        }
        if not old:
            return {
                group_id: BOMRevisionDelta(
                    group_id=group_id,
                    family=str(after.get("family") or ""),
                    status="geen baseline",
                    changed_fields=(),
                    before={},
                    after=deepcopy(after),
                )
                for group_id, after in current.items()
            }
        ignored = {"fingerprint", "entity_evidence"}

        def compare_fields(
            before: Mapping[str, Any], after: Mapping[str, Any]
        ) -> tuple[tuple[str, ...], tuple[BOMFieldDelta, ...]]:
            row_before = {key: value for key, value in before.items() if key not in ignored}
            row_after = {key: value for key, value in after.items() if key not in ignored}
            deltas = list(_field_level_deltas(row_before, row_after))
            changed = tuple(sorted({delta.field_path.split(".", 1)[0] for delta in deltas}))
            old_evidence = {
                item.get("entity_id"): item for item in before.get("entity_evidence") or ()
            }
            new_evidence = {
                item.get("entity_id"): item for item in after.get("entity_evidence") or ()
            }
            for entity_id in sorted(set(old_evidence) | set(new_evidence)):
                left, right = old_evidence.get(entity_id, {}), new_evidence.get(entity_id, {})
                if left and right and left.get("geometry_hash") != right.get("geometry_hash"):
                    changed += ("geometry",)
                if left and right and left.get("manufacturing_hash") != right.get("manufacturing_hash"):
                    changed += ("manufacturing",)
                if left and right and left.get("production_features") != right.get("production_features"):
                    changed += ("production_features",)
                left_fields = left.get("entity_fields", _MISSING) if left else _MISSING
                right_fields = right.get("entity_fields", _MISSING) if right else _MISSING
                if left_fields is _MISSING and right_fields is _MISSING:
                    # Baseline 1.0 compatibility: hashes/features still provide
                    # exact manufacturing deltas even without full entity fields.
                    continue
                deltas.extend(_field_level_deltas(
                    left_fields, right_fields,
                    prefix=f"entity.{entity_id}", entity_id=str(entity_id),
                ))
            return _unique(changed), tuple(deltas)

        old_entity_sets = {
            group_id: set(_unique(payload.get("entity_ids") or ()))
            for group_id, payload in old.items()
        }
        current_entity_ids = {
            entity_id for payload in current.values()
            for entity_id in _unique(payload.get("entity_ids") or ())
        }
        for group_id, after in current.items():
            before = old.get(group_id)
            if before is None:
                after_ids = set(_unique(after.get("entity_ids") or ()))
                candidates = [
                    (len(after_ids.intersection(entity_ids)), old_group, payload)
                    for old_group, payload in old.items()
                    for entity_ids in (old_entity_sets[old_group],)
                    if after_ids.intersection(entity_ids)
                    and str(payload.get("family") or "") == str(after.get("family") or "")
                ]
                if candidates:
                    _overlap, _old_group, before = max(
                        candidates, key=lambda item: (item[0], item[1])
                    )
            if before is None:
                status = "toegevoegd"
                changed, field_deltas = compare_fields({}, after)
            elif before.get("fingerprint") == after.get("fingerprint"):
                status, changed, field_deltas = "ongewijzigd", (), ()
            else:
                status = "gewijzigd"
                changed, field_deltas = compare_fields(before, after)
            result[group_id] = BOMRevisionDelta(
                group_id=group_id, family=str(after.get("family") or ""), status=status,
                changed_fields=changed, field_deltas=field_deltas,
                before=deepcopy(before or {}), after=deepcopy(after),
            )
        for group_id in sorted(old):
            before = dict(old[group_id] or {})
            missing_ids = old_entity_sets[group_id] - current_entity_ids
            if not missing_ids:
                continue
            removed_payload = deepcopy(before)
            removed_payload["entity_ids"] = sorted(missing_ids)
            removed_payload["entity_evidence"] = [
                item for item in before.get("entity_evidence") or ()
                if str(item.get("entity_id") or "") in missing_ids
            ]
            removed_quantities = []
            for evidence in removed_payload["entity_evidence"]:
                fields = dict(evidence.get("entity_fields") or {})
                removed_quantities.append(float(
                    fields.get("quantity_total", fields.get("quantity", 1.0)) or 1.0
                ))
            removed_payload["quantity"] = (
                sum(removed_quantities) if removed_quantities else float(len(missing_ids))
            )
            if removed_payload["entity_evidence"]:
                mass = surface = 0.0
                has_mass = has_surface = False
                for evidence in removed_payload["entity_evidence"]:
                    fields = dict(evidence.get("entity_fields") or {})
                    quantity = float(fields.get("quantity_total", fields.get("quantity", 1.0)) or 1.0)
                    if "mass_each_kg" in fields:
                        mass += float(fields.get("mass_each_kg") or 0.0) * quantity
                        has_mass = True
                    if "surface_area_each_m2" in fields:
                        surface += float(fields.get("surface_area_each_m2") or 0.0) * quantity
                        has_surface = True
                if has_mass:
                    removed_payload["total_mass_kg"] = mass
                if has_surface:
                    removed_payload["total_surface_m2"] = surface
            removed_group_id = (
                group_id if group_id not in result
                else f"{group_id}::removed::{stable_sha256(sorted(missing_ids))[:10]}"
            )
            result[removed_group_id] = BOMRevisionDelta(
                group_id=removed_group_id, family=str(before.get("family") or ""),
                status="verwijderd", changed_fields=("removed",),
                field_deltas=compare_fields(removed_payload, {})[1],
                before=removed_payload, after={},
            )
        return result

    def revision_statuses(self, model: BOMWorkspaceReadModel) -> dict[str, str]:
        if not dict(self.data.get("revision_baseline") or {}).get("groups"):
            return {row.group_id: "geen baseline" for family in model._rows for row in model.family_rows(family)}
        return {key: value.status for key, value in self.revision_deltas(model).items()}

    def removed_revision_rows(self, model: BOMWorkspaceReadModel, family: str) -> tuple[BOMWorkspaceRow, ...]:
        rows = []
        for delta in self.revision_deltas(model).values():
            if delta.status != "verwijderd" or delta.family != family:
                continue
            value = dict(delta.before)
            rows.append(BOMWorkspaceRow(
                family=family, group_id=delta.group_id,
                entity_ids=_unique(value.get("entity_ids") or ()),
                mark=str(value.get("mark") or ""),
                description=str(value.get("description") or "Verwijderd sinds revisiebaseline"),
                profile=str(value.get("profile") or ""), material=str(value.get("material") or ""),
                length_mm=float(value.get("length_mm") or 0.0), quantity=float(value.get("quantity") or 0.0),
                total_mass_kg=float(value.get("total_mass_kg") or 0.0),
                total_surface_m2=float(value.get("total_surface_m2") or 0.0),
                status="removed", blocked=True,
                blocking_reasons=("Object bestaat niet meer in de actuele revisie",),
                revision_status="verwijderd",
            ))
        return tuple(rows)

    def removed_revision_bounds(self, model: BOMWorkspaceReadModel) -> tuple[dict[str, Any], ...]:
        result: dict[str, dict[str, Any]] = {}
        for delta in self.revision_deltas(model).values():
            if delta.status != "verwijderd":
                continue
            for evidence in delta.before.get("entity_evidence") or ():
                bounds = evidence.get("world_bounds")
                if bounds:
                    entity_id = str(evidence.get("entity_id") or "")
                    result.setdefault(entity_id, {
                        "entity_id": entity_id,
                        "group_id": delta.group_id, "bounds": deepcopy(bounds),
                    })
        return tuple(result[key] for key in sorted(result))

    @staticmethod
    def _result_items(
        preflight: BOMBatchPreflight,
        *,
        eligible_status: str,
        message: str = "",
    ) -> tuple[Mapping[str, Any], ...]:
        return tuple(
            {
                "group_id": group_id,
                "status": eligible_status,
                "message": message,
            }
            for group_id in preflight.eligible_group_ids
        ) + tuple(
            {
                "group_id": group_id,
                "status": "blocked",
                "message": "Regel door preflight uitgesloten; niet stilzwijgend overgeslagen",
            }
            for group_id in preflight.blocked_group_ids
        )

    def _store_result(self, result: BOMBatchResult, *, user: str) -> BOMBatchResult:
        self.data["batch_results"].append(result.to_dict())
        self.data["batch_results"] = self.data["batch_results"][-200:]
        self._history("batch.result", user, result.to_dict())
        return result

    def record_result(
        self,
        action: str,
        preflight: BOMBatchPreflight,
        *,
        outputs: Iterable[str] = (),
        messages: Iterable[str] = (),
        user: str = "bom-operator",
    ) -> BOMBatchResult:
        digest = stable_sha256(self.project.to_dict())
        return self._store_result(BOMBatchResult(
            transaction_id=str(uuid4()), action=str(action), status="passed",
            snapshot_sha256=preflight.snapshot_sha256,
            preflight_sha256=preflight.preflight_sha256,
            before_hash=digest, after_hash=digest,
            eligible_group_ids=preflight.eligible_group_ids,
            blocked_group_ids=preflight.blocked_group_ids,
            changed_entity_ids=(), outputs=_unique(outputs), messages=_unique(messages),
            undo_available=False,
            item_results=self._result_items(preflight, eligible_status="passed"),
        ), user=user)

    def execute_transaction(
        self,
        action: str,
        preflight: BOMBatchPreflight,
        mutator: Callable[[], Any],
        *,
        entity_ids: Iterable[str] = (),
        outputs: Iterable[str] = (),
        messages: Iterable[str] = (),
        user: str = "bom-operator",
    ) -> BOMTransactionExecution:
        if not preflight.allowed or not preflight.preflight_sha256:
            raise ValueError("Batchactie is door preflight geblokkeerd")
        # Materialise the persistent hub schema before hashing so result/undo
        # bookkeeping cannot look like a later business-content mutation.
        self.data
        started = time.perf_counter()
        current_entities = _unique(entity_ids or preflight.impact.entity_ids)
        before_state = deepcopy(self.project.__dict__)
        before_content = _transaction_payload(self.project)
        before_hash = stable_sha256(self.project.to_dict())
        transaction_id = str(uuid4())
        try:
            value = mutator()
            self.project.validate()
        except Exception as exc:
            self.project.__dict__.clear()
            self.project.__dict__.update(before_state)
            failure = BOMBatchResult(
                transaction_id=transaction_id, action=str(action), status="failed",
                snapshot_sha256=preflight.snapshot_sha256,
                preflight_sha256=preflight.preflight_sha256,
                before_hash=before_hash, after_hash=before_hash,
                eligible_group_ids=preflight.eligible_group_ids,
                blocked_group_ids=preflight.blocked_group_ids,
                changed_entity_ids=(), outputs=(),
                messages=(f"{type(exc).__name__}: {exc}",), undo_available=False,
                item_results=self._result_items(
                    preflight, eligible_status="failed", message=f"{type(exc).__name__}: {exc}",
                ),
                duration_ms=(time.perf_counter() - started) * 1000.0,
            )
            self._store_result(failure, user=user)
            self.project.audit(
                f"bom.batch.{action}.failed", user=user,
                before_hash=before_hash, after_hash=before_hash,
                details={"transaction_id": transaction_id,
                         "preflight_sha256": preflight.preflight_sha256},
            )
            raise
        if isinstance(value, (tuple, list)) and all(
            isinstance(item, str) for item in value
        ):
            current_entities = _unique((*current_entities, *value))
        after_hash = stable_sha256(self.project.to_dict())
        after_content = _transaction_payload(self.project)
        inverse_patch = _build_inverse_patch(before_content, after_content)
        result = BOMBatchResult(
            transaction_id=transaction_id, action=str(action), status="passed",
            snapshot_sha256=preflight.snapshot_sha256,
            preflight_sha256=preflight.preflight_sha256,
            before_hash=before_hash, after_hash=after_hash,
            eligible_group_ids=preflight.eligible_group_ids,
            blocked_group_ids=preflight.blocked_group_ids,
            changed_entity_ids=current_entities, outputs=_unique(outputs),
            messages=_unique(messages), undo_available=bool(inverse_patch),
            item_results=self._result_items(preflight, eligible_status="passed"),
            duration_ms=(time.perf_counter() - started) * 1000.0,
        )
        record = {
            "transaction_id": transaction_id, "action": str(action),
            "snapshot_sha256": preflight.snapshot_sha256,
            "preflight_sha256": preflight.preflight_sha256,
            "before_hash": before_hash, "after_hash": after_hash,
            "created_at": result.created_at, "user": user,
            "entity_ids": list(current_entities), "runtime_project_restore": True,
            "persistent_inverse_patch": list(inverse_patch),
            "after_content_sha256": stable_sha256(after_content),
            "undo_schema": "cws-bom-persistent-undo-2.0",
        }
        if inverse_patch:
            self._runtime_project_undo[transaction_id] = before_state
            self.data["undo"].append(record)
            self.data["undo"] = self.data["undo"][-20:]
        self._store_result(result, user=user)
        self.project.audit(
            f"bom.batch.{action}", user=user, before_hash=before_hash,
            after_hash=after_hash, details={
                "transaction_id": transaction_id,
                "preflight_sha256": preflight.preflight_sha256,
                "entity_ids": list(current_entities),
            },
        )
        return BOMTransactionExecution(value=value, result=result)

    def record_external_release(
        self,
        release_id: str,
        entity_ids: Iterable[str],
        *,
        source: str,
        user: str = "bom-operator",
    ) -> None:
        event = {
            "release_id": str(release_id), "source": str(source),
            "entity_ids": list(_unique(entity_ids)), "released_at": _utc_now(),
            "user": user,
        }
        self.data["external_releases"].append(event)
        for result in self.data.get("batch_results") or ():
            if str(result.get("transaction_id") or "") == str(release_id):
                result["undo_available"] = False
                result["release_id"] = str(release_id)
        self._history("external_release.recorded", user, event)

    def _release_barrier(self, entity_ids: Iterable[str]) -> str:
        requested = set(_unique(entity_ids))
        for release in self.data.get("external_releases") or ():
            released_ids = set(_unique(release.get("entity_ids") or ()))
            if not released_ids or not requested or requested.intersection(released_ids):
                return str(release.get("release_id") or "externe BOM-vrijgave")
        for job in getattr(self.project, "machine_jobs", {}).values():
            if str(getattr(job, "release_status", "")).casefold() in {"released", "vrijgegeven"}:
                if not requested or requested.intersection(getattr(job, "part_ids", ()) or ()):
                    return str(getattr(job, "internal_id", "machinejob"))
        for run_id, record in getattr(self.project, "profile_nesting_runs", {}).items():
            run = dict(record.get("run") or {}) if isinstance(record, Mapping) else {}
            if run.get("released_at") or str(run.get("status") or "").casefold() == "released":
                snapshot = dict(record.get("input_snapshot") or {}) if isinstance(record, Mapping) else {}
                released_part_ids = {
                    str(value.get("part_id") or "")
                    for value in snapshot.get("demand_lines") or ()
                    if isinstance(value, Mapping) and str(value.get("part_id") or "")
                }
                if not requested or not released_part_ids or requested.intersection(released_part_ids):
                    return str(run_id)
        return ""

    def begin_settings_transaction(
        self,
        action: str,
        preflight: BOMBatchPreflight,
        mutator: Callable[[], Any],
        *,
        user: str = "bom-operator",
    ) -> Any:
        # Compatibility entry point: settings transactions intentionally use
        # the same full-project rollback, persisted result report and
        # release-bound undo contract as every other BOM mutation.
        return self.execute_transaction(
            action, preflight, mutator,
            entity_ids=preflight.impact.entity_ids,
            user=user,
        ).value

    def begin_entity_transaction(
        self,
        action: str,
        preflight: BOMBatchPreflight,
        entity_ids: Iterable[str],
        mutator: Callable[[], Any],
        *,
        user: str = "bom-operator",
    ) -> Any:
        # Compatibility entry point kept for callers outside the workspace;
        # execution itself is centralized so failures and successful actions
        # always produce the same immutable result contract.
        return self.execute_transaction(
            action, preflight, mutator,
            entity_ids=entity_ids,
            user=user,
        ).value

    def undo_last(self, *, user: str = "bom-operator") -> str:
        stack = self.data["undo"]
        if not stack:
            raise ValueError("Geen BOM-batchactie beschikbaar om ongedaan te maken")
        record = deepcopy(stack[-1])
        transaction_id = str(record["transaction_id"])
        barrier = self._release_barrier(record.get("entity_ids") or ())
        if barrier:
            raise ValueError(
                f"Undo is geblokkeerd omdat externe vrijgave {barrier} de geselecteerde scope heeft vergrendeld"
            )
        inverse_patch = tuple(record.get("persistent_inverse_patch") or ())
        if inverse_patch:
            expected = str(record.get("after_content_sha256") or "")
            actual = stable_sha256(_transaction_payload(self.project))
            if expected and actual != expected:
                raise ValueError(
                    "Undo is geblokkeerd omdat de projectinhoud na deze transactie verder is gewijzigd"
                )
            current_hash = stable_sha256(self.project.to_dict())
            payload = self.project.to_dict()
            _apply_inverse_patch(payload, inverse_patch)
            restored = type(self.project).from_dict(payload)
            self.project.__dict__.clear()
            self.project.__dict__.update(restored.__dict__)
            hub = self.data
            hub["undo"] = [
                value for value in hub.get("undo") or ()
                if str(value.get("transaction_id") or "") != transaction_id
            ]
            for result in hub.get("batch_results") or ():
                if str(result.get("transaction_id") or "") == transaction_id:
                    result["undo_available"] = False
                    result["status"] = "undone"
                    result["undone_at"] = _utc_now()
            self._runtime_project_undo.pop(transaction_id, None)
            restored_hash = stable_sha256(self.project.to_dict())
            self.project.audit(
                "bom.batch.undo", user=user, before_hash=current_hash,
                after_hash=restored_hash, details={
                    "transaction_id": transaction_id, "action": record["action"],
                    "release_barrier_checked": True, "persistent_restore": True,
                },
            )
            return transaction_id
        if transaction_id in self._runtime_project_undo:
            current_hash = stable_sha256(self.project.to_dict())
            before_state = self._runtime_project_undo.pop(transaction_id)
            self.project.__dict__.clear()
            self.project.__dict__.update(deepcopy(before_state))
            restored_hash = stable_sha256(self.project.to_dict())
            self.project.audit(
                "bom.batch.undo", user=user, before_hash=current_hash,
                after_hash=restored_hash, details={
                    "transaction_id": transaction_id, "action": record["action"],
                    "release_barrier_checked": True,
                },
            )
            return transaction_id
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
    "ACTION_DEFINITIONS", "BOMActionDefinition", "BOMActionMatrix",
    "BOMBatchPreflight", "BOMBatchResult", "BOMFieldDelta", "BOMHubState", "BOMQueryClause",
    "BOMProcurementService", "BOMQueryGroup", "BOMRevisionDelta", "BOMSavedSelection", "BOMScopeEngine",
    "BOMSelectionImpact", "BOMSmartQuery", "BOMTransactionExecution",
    "BOMStockAllocation", "BOMStockAllocationPlan", "BOMStockAllocator",
    "BOMStockPiece", "BOMStockSourceOption", "HUB_SETTINGS_KEY",
    "QUERY_FIELDS", "QUERY_OPERATORS", "SELECTION_BASES",
]
