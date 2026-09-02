"""Canonical BOM workspace read model, selection scope and scoped snapshots.

The Qt surface, exports and production actions use this module instead of
reconstructing quantities from ``ProjectModel.parts``.  It deliberately keeps
toolkit objects out of the contract so the same stable-ID scope is testable in
headless, CLI and packaged runtimes.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

from .models import BOMSnapshot, BOMValidation


BOM_FAMILIES = (
    "parts",
    "assemblies",
    "purchase",
    "fasteners",
    "welds",
    "materials",
    "conflicts",
)

BOM_FAMILY_LABELS = {
    "parts": "Onderdelen",
    "assemblies": "Assemblies",
    "purchase": "Inkoop",
    "fasteners": "Bouten",
    "welds": "Lassen",
    "materials": "Materialen",
    "conflicts": "Blokkeringen",
}


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _mixed(values: Iterable[str], *, empty: str = "-") -> str:
    found = tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))
    if not found:
        return empty
    if len(found) == 1:
        return found[0]
    return "Gemengd"


@dataclass(frozen=True, slots=True)
class BOMWorkspaceRow:
    family: str
    group_id: str
    entity_ids: tuple[str, ...]
    mark: str = ""
    description: str = ""
    profile: str = ""
    material: str = ""
    length_mm: float = 0.0
    quantity: float = 0.0
    total_mass_kg: float = 0.0
    total_surface_m2: float = 0.0
    machine: str = ""
    document_status: str = ""
    phase: str = ""
    delivery: str = ""
    release_status: str = ""
    nesting_status: str = ""
    production_status: str = ""
    stock_status: str = ""
    supplier: str = ""
    available_stock_mm: float = 0.0
    shortage_mm: float = 0.0
    unit_price: float = 0.0
    total_price: float = 0.0
    lead_time_days: int = 0
    expected_delivery: str = ""
    purchase_status: str = ""
    geometry_status: str = ""
    material_status: str = ""
    machine_status: str = ""
    nc_status: str = ""
    scribing_status: str = ""
    conflict_status: str = ""
    delivery_status: str = ""
    assigned_stock: str = ""
    assigned_remnant: str = ""
    alternative_material: str = ""
    purchase_release_status: str = ""
    revision_status: str = ""
    status: str = "review_required"
    blocked: bool = False
    blocking_reasons: tuple[str, ...] = ()
    raw: Any = field(default=None, compare=False, repr=False)

    @property
    def searchable_text(self) -> str:
        return " ".join(
            (
                self.family,
                self.group_id,
                self.mark,
                self.description,
                self.profile,
                self.material,
                self.machine,
                self.document_status,
                self.phase,
                self.delivery,
                self.release_status,
                self.nesting_status,
                self.production_status,
                self.stock_status,
                self.supplier,
                self.geometry_status,
                self.material_status,
                self.machine_status,
                self.nc_status,
                self.scribing_status,
                self.conflict_status,
                self.delivery_status,
                self.assigned_stock,
                self.assigned_remnant,
                self.alternative_material,
                self.purchase_release_status,
                self.revision_status,
                self.status,
                *self.blocking_reasons,
                *self.entity_ids,
            )
        ).casefold()


@dataclass(frozen=True, slots=True)
class BOMScope:
    family: str = "parts"
    entity_ids: tuple[str, ...] = ()
    group_ids: tuple[str, ...] = ()
    query: str = ""
    status: str = "all"

    @classmethod
    def create(
        cls,
        *,
        family: str = "parts",
        entity_ids: Iterable[str] = (),
        group_ids: Iterable[str] = (),
        query: str = "",
        status: str = "all",
    ) -> "BOMScope":
        if family not in BOM_FAMILIES:
            raise ValueError(f"Onbekende BOM-familie: {family}")
        if status not in {"all", "ready", "review", "blocked"}:
            raise ValueError(f"Onbekende BOM-statusfilter: {status}")
        return cls(
            family=family,
            entity_ids=_unique(entity_ids),
            group_ids=_unique(group_ids),
            query=str(query or "").strip(),
            status=status,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-bom-scope-1.0",
            "family": self.family,
            "entity_ids": list(self.entity_ids),
            "group_ids": list(self.group_ids),
            "query": self.query,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class BOMSelectionSummary:
    family: str
    group_count: int
    entity_count: int
    quantity: float
    total_mass_kg: float
    total_surface_m2: float
    assembly_count: int
    blocked_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-bom-selection-summary-1.0",
            "family": self.family,
            "group_count": self.group_count,
            "entity_count": self.entity_count,
            "quantity": self.quantity,
            "total_mass_kg": self.total_mass_kg,
            "total_surface_m2": self.total_surface_m2,
            "assembly_count": self.assembly_count,
            "blocked_count": self.blocked_count,
        }


@dataclass(frozen=True, slots=True)
class BOMActionAvailability:
    action: str
    enabled: bool
    reason: str = ""


class BOMWorkspaceReadModel:
    """Immutable workspace projection over one :class:`BOMSnapshot`."""

    def __init__(self, snapshot: BOMSnapshot, project: Any | None = None) -> None:
        self.snapshot = snapshot
        self.project = project
        self._routing = dict(
            ((getattr(project, "settings", {}) or {}).get("machine_routing", {}) or {}).get(
                "assignments", {}
            )
            if project is not None
            else {}
        )
        self._rows = {family: self._build_family(family) for family in BOM_FAMILIES}

    def family_count(self, family: str) -> int:
        return len(self._rows.get(family, ()))

    def family_rows(self, family: str) -> tuple[BOMWorkspaceRow, ...]:
        if family not in BOM_FAMILIES:
            raise ValueError(f"Onbekende BOM-familie: {family}")
        return self._rows[family]

    def rows(self, scope: BOMScope) -> tuple[BOMWorkspaceRow, ...]:
        entity_ids = set(scope.entity_ids)
        group_ids = set(scope.group_ids)
        needle = scope.query.casefold()
        result: list[BOMWorkspaceRow] = []
        for row in self.family_rows(scope.family):
            if entity_ids and not entity_ids.intersection(row.entity_ids):
                continue
            if group_ids and row.group_id not in group_ids:
                continue
            if needle and needle not in row.searchable_text:
                continue
            if scope.status == "ready" and (row.blocked or row.status not in {"ready", "released", "ok"}):
                continue
            if scope.status == "blocked" and not row.blocked:
                continue
            if scope.status == "review" and (row.blocked or row.status in {"ready", "released", "ok"}):
                continue
            result.append(row)
        return tuple(result)

    def summary(self, rows: Iterable[BOMWorkspaceRow]) -> BOMSelectionSummary:
        values = tuple(rows)
        entity_ids = {entity_id for row in values for entity_id in row.entity_ids}
        assembly_marks = {
            mark.strip()
            for row in values
            for mark in str(row.mark or "").split(",")
            if mark.strip() and row.family in {"assemblies", "parts", "purchase"}
        }
        return BOMSelectionSummary(
            family=values[0].family if values else "",
            group_count=len(values),
            entity_count=len(entity_ids),
            quantity=sum(float(row.quantity or 0.0) for row in values),
            total_mass_kg=sum(float(row.total_mass_kg or 0.0) for row in values),
            total_surface_m2=sum(float(row.total_surface_m2 or 0.0) for row in values),
            assembly_count=len(assembly_marks),
            blocked_count=sum(1 for row in values if row.blocked),
        )

    def actions(self, rows: Iterable[BOMWorkspaceRow]) -> tuple[BOMActionAvailability, ...]:
        values = tuple(rows)
        families = {row.family for row in values}
        has_selection = bool(values)
        selectable = bool({entity_id for row in values for entity_id in row.entity_ids})
        only_parts = bool(values) and families == {"parts"}
        drawing_scope = bool(values) and families.issubset({"parts", "assemblies"})
        optimizable = bool(values) and families.issubset({"parts", "materials"})
        project_ready = bool(
            self.snapshot.validation and self.snapshot.validation.production_ready
        )
        releasable = (
            drawing_scope
            and not any(row.blocked for row in values)
            and project_ready
        )
        return (
            BOMActionAvailability("edit", has_selection and families.issubset({"parts", "assemblies", "purchase"}), "Selecteer onderdelen, assemblies of inkoopregels"),
            BOMActionAvailability("drawing", drawing_scope, "Tekening is beschikbaar voor onderdelen en assemblies"),
            BOMActionAvailability("machine", only_parts, "Machine-indeling vereist uitsluitend onderdeelregels"),
            BOMActionAvailability("optimize", optimizable, "Optimalisatie vereist onderdelen of materiaalregels"),
            BOMActionAvailability("isolate", selectable, "Deze BOM-regels hebben geen selecteerbare modelobjecten"),
            BOMActionAvailability(
                "release",
                releasable,
                "Volledige project-, bron- en productievalidatie moet gereed zijn",
            ),
            BOMActionAvailability("export", has_selection, "Selecteer minimaal één BOM-regel"),
            BOMActionAvailability("scribing", only_parts, "Scribing vereist uitsluitend onderdeelregels"),
            BOMActionAvailability("print", has_selection, "Selecteer minimaal één BOM-regel"),
        )

    def production_part_ids(
        self, rows: Iterable[BOMWorkspaceRow]
    ) -> tuple[str, ...]:
        """Expand an explicit BOM scope to fabrication parts only.

        This expansion belongs to the BOM production action.  It deliberately
        does not change the global rule that an arbitrary non-part selection
        may never widen to all project parts.
        """
        selected = tuple(rows)
        result: list[str] = []
        pending_assemblies: set[str] = set()
        for row in selected:
            if row.family == "parts":
                result.extend(row.entity_ids)
            elif row.family == "assemblies":
                pending_assemblies.update(row.entity_ids)
        visited: set[str] = set()
        assembly_rows = self.family_rows("assemblies")
        while pending_assemblies:
            assembly_id = pending_assemblies.pop()
            if assembly_id in visited:
                continue
            visited.add(assembly_id)
            for row in assembly_rows:
                if assembly_id not in row.entity_ids:
                    continue
                raw = row.raw
                result.extend(getattr(raw, "part_ids", ()))
                pending_assemblies.update(getattr(raw, "child_assembly_ids", ()))
        if self.project is not None:
            result = [
                part_id for part_id in result
                if part_id in self.project.parts
                and str(getattr(self.project.parts[part_id], "category", ""))
                != "purchased_item"
            ]
        return _unique(result)

    def _machine_for(self, entity_ids: Iterable[str]) -> str:
        values = []
        for entity_id in entity_ids:
            assignment = self._routing.get(str(entity_id), {})
            if isinstance(assignment, Mapping):
                machine = str(
                    assignment.get("assigned_machine_id")
                    or assignment.get("recommended_machine_id")
                    or ""
                )
                source = str(assignment.get("assignment_source") or "").lower()
                if machine:
                    values.append(f"{machine} · {source}" if source else machine)
        return _mixed(values)

    def _drawing_for_marks(self, marks: Iterable[str]) -> str:
        if self.project is None:
            return "-"
        requested = {str(mark) for mark in marks if str(mark)}
        values = [
            str(getattr(assembly, "drawing_status", "") or "")
            for assembly in self.project.assemblies.values()
            if str(getattr(assembly, "assembly_mark", "") or "") in requested
        ]
        return _mixed(values)

    def _entity_field(self, entity_ids: Iterable[str], *names: str) -> str:
        if self.project is None:
            return "-"
        values: list[str] = []
        for entity_id in entity_ids:
            entity = self.project.get_entity(str(entity_id)) if hasattr(self.project, "get_entity") else None
            if entity is None:
                continue
            properties = getattr(entity, "properties", {}) or {}
            value = ""
            for name in names:
                value = getattr(entity, name, "") or properties.get(name) or properties.get(name.title())
                if value not in (None, ""):
                    break
            if value not in (None, ""):
                values.append(str(value))
        return _mixed(values)

    def _workflow_fields(self, entity_ids: Iterable[str]) -> dict[str, Any]:
        ids = tuple(entity_ids)
        return {
            "phase": self._entity_field(ids, "phase", "project_phase"),
            "delivery": self._entity_field(ids, "delivery", "delivery_id", "shipment"),
            "release_status": self._entity_field(ids, "release_status", "review_status", "status"),
            "nesting_status": self._entity_field(ids, "nesting_status"),
            "production_status": self._entity_field(ids, "production_status", "fabrication_status"),
            "stock_status": self._entity_field(ids, "stock_status", "procurement_status"),
            "supplier": self._entity_field(ids, "supplier"),
            "delivery_status": self._entity_field(ids, "delivery_status", "shipment_status"),
            "purchase_release_status": self._entity_field(ids, "purchase_release_status"),
        }

    def _readiness_fields(
        self,
        entity_ids: Iterable[str],
        *,
        group_id: str,
        material: str,
        document_status: str,
        machine: str,
        blocked: bool,
    ) -> dict[str, Any]:
        ids = tuple(entity_ids)
        entities = [
            self.project.get_entity(entity_id)
            for entity_id in ids
            if self.project is not None and self.project.get_entity(entity_id) is not None
        ]
        parts = [entity for entity in entities if getattr(entity, "entity_type", "") == "part"]
        material_relevant = any(
            getattr(entity, "entity_type", "") in {"part", "purchased_item", "fastener", "weld"}
            for entity in entities
        )
        geometry_ready = bool(entities) and all(
            getattr(entity, "entity_type", "") != "part"
            or bool(getattr(entity, "geometry_hash", ""))
            for entity in entities
        )
        known_material = str(material or "").strip().casefold() not in {
            "", "-", "unknown", "onbekend", "gemengd",
        }
        routing_values = [self._routing.get(str(entity_id), {}) for entity_id in ids]
        routing_states = [
            str(value.get("routing_status") or value.get("capability_status") or "")
            for value in routing_values if isinstance(value, Mapping)
        ]
        machine_ready = bool(machine and machine != "-") and bool(routing_states) and all(
            value.casefold() in {"ready", "eligible", "assigned"} for value in routing_states
        )
        nc_ready = bool(parts) and all(
            bool(getattr(part, "nc1_eligible", False))
            and str(getattr(part, "export_status", "")).casefold() in {"ready", "released", "valid", "ok"}
            for part in parts
        )
        scribing_values = []
        for part in parts:
            properties = getattr(part, "properties", {}) or {}
            explicit = str(properties.get("scribing_status") or "")
            features = tuple(getattr(part, "production_features", ()) or ())
            has_scribing = any(
                str(feature.get("type") or feature.get("operation") or "").casefold()
                in {"scribe", "scribing", "mark", "marking"}
                for feature in features if isinstance(feature, Mapping)
            )
            scribing_values.append(explicit or ("ready" if has_scribing else "not_required"))
        hub = dict(((getattr(self.project, "settings", {}) or {}).get("bom_production_hub", {}) or {}))
        assignment = dict((hub.get("stock_assignments") or {}).get(group_id) or {})
        source_type = str(assignment.get("source_type") or "")
        source_id = str(assignment.get("source_id") or "")
        return {
            "geometry_status": "Gereed" if geometry_ready else "Geblokkeerd",
            "material_status": (
                "Gereed" if known_material else "Niet van toepassing" if not material_relevant else "Geblokkeerd"
            ),
            "machine_status": "Gereed" if machine_ready else ("Niet van toepassing" if not parts else "Review"),
            "nc_status": "Gereed" if nc_ready else ("Niet van toepassing" if not parts else "Geblokkeerd"),
            "scribing_status": _mixed(scribing_values, empty="Niet van toepassing"),
            "conflict_status": "Geblokkeerd" if blocked else "Conflictvrij",
            "assigned_stock": source_id if source_type == "full_stock" else "",
            "assigned_remnant": source_id if source_type == "remnant" else "",
        }

    def _stock_fields(
        self, *, profile: str, material: str, required_length_mm: float
    ) -> dict[str, Any]:
        if self.project is None:
            return {}
        profile_key = str(profile or "").casefold()
        material_key = str(material or "").casefold()
        available = 0.0
        suppliers: list[str] = []
        prices: list[float] = []
        for stock in self.project.stock_items.values():
            if str(stock.profile or "").casefold() != profile_key:
                continue
            stock_materials = {
                str(value).casefold() for value in (stock.material, stock.grade) if str(value)
            }
            if material_key and stock_materials and material_key not in stock_materials:
                continue
            quantity = max(0.0, float(stock.available_quantity or 0.0) - float(stock.reserved_quantity or 0.0))
            available += float(stock.stock_length_mm or 0.0) * quantity
            if stock.supplier:
                suppliers.append(str(stock.supplier))
            if stock.unit_price:
                prices.append(float(stock.unit_price))
        for remnant in self.project.remnants.values():
            if str(remnant.status or "").casefold() not in {"available", "beschikbaar"}:
                continue
            remnant_materials = {
                str(value).casefold() for value in (remnant.material, remnant.grade) if str(value)
            }
            if str(remnant.profile or "").casefold() == profile_key and (
                not material_key or not remnant_materials or material_key in remnant_materials
            ):
                available += float(remnant.remaining_length_mm or 0.0)
        shortage = max(0.0, float(required_length_mm or 0.0) - available)
        return {
            "available_stock_mm": available,
            "shortage_mm": shortage,
            "stock_status": "Tekort" if shortage > 0.001 else "Beschikbaar",
            "supplier": _mixed(suppliers),
            "unit_price": min(prices) if prices else 0.0,
        }

    def _build_family(self, family: str) -> tuple[BOMWorkspaceRow, ...]:
        snapshot = self.snapshot
        rows: list[BOMWorkspaceRow] = []
        def enrich(
            workflow: dict[str, Any], entity_ids: Iterable[str], *, group_id: str,
            material: str = "", document: str = "", machine: str = "", blocked: bool = False,
        ) -> dict[str, Any]:
            workflow.update(self._readiness_fields(
                entity_ids, group_id=group_id, material=material,
                document_status=document, machine=machine, blocked=blocked,
            ))
            return workflow
        if family == "parts":
            for item in snapshot.part_bom:
                marks = tuple(item.assembly_marks)
                workflow = self._workflow_fields(item.part_ids)
                workflow.update(self._stock_fields(
                    profile=item.profile, material=item.material,
                    required_length_mm=float(item.length_mm or 0.0) * float(item.quantity or 0.0),
                ))
                machine = self._machine_for(item.part_ids)
                document = self._drawing_for_marks(marks)
                enrich(
                    workflow, item.part_ids, group_id=item.group_id,
                    material=item.material, document=document, machine=machine,
                    blocked=item.blocked,
                )
                rows.append(BOMWorkspaceRow(
                    family=family, group_id=item.group_id, entity_ids=_unique(item.part_ids),
                    mark=item.part_position or ", ".join(marks), description=item.name,
                    profile=item.profile, material=item.material, length_mm=item.length_mm,
                    quantity=item.quantity, total_mass_kg=item.total_mass_kg,
                    total_surface_m2=item.total_surface_area_m2,
                    machine=machine, document_status=document,
                    **workflow,
                    status=item.status, blocked=item.blocked,
                    blocking_reasons=tuple(item.blocking_reasons), raw=item,
                ))
        elif family == "assemblies":
            for item in snapshot.assembly_bom:
                workflow = self._workflow_fields(item.assembly_ids)
                document = self._drawing_for_marks((item.assembly_mark,))
                enrich(
                    workflow, item.assembly_ids, group_id=item.group_id,
                    document=document, blocked=item.blocked,
                )
                rows.append(BOMWorkspaceRow(
                    family=family, group_id=item.group_id, entity_ids=_unique(item.assembly_ids),
                    mark=item.assembly_mark, description=item.name, quantity=item.quantity,
                    total_mass_kg=item.total_weight_kg, total_surface_m2=item.total_surface_area_m2,
                    document_status=document,
                    **workflow,
                    status="blocked" if item.blocked else "ready", blocked=item.blocked,
                    blocking_reasons=tuple(item.blocking_reasons), raw=item,
                ))
        elif family == "purchase":
            for item in snapshot.purchase_bom:
                entity_ids = _unique((*item.part_ids, *getattr(item, "purchased_item_ids", ())))
                workflow = self._workflow_fields(entity_ids)
                purchased = [
                    self.project.purchased_items[entity_id]
                    for entity_id in entity_ids
                    if self.project is not None and entity_id in self.project.purchased_items
                ]
                if purchased:
                    workflow.update({
                        "unit_price": min(float(value.unit_price or 0.0) for value in purchased),
                        "total_price": sum(float(value.unit_price or 0.0) * float(value.quantity or 0.0) for value in purchased),
                        "lead_time_days": max(int(value.lead_time_days or 0) for value in purchased),
                        "purchase_status": _mixed(value.purchase_status for value in purchased),
                        "supplier": _mixed(value.supplier for value in purchased),
                        "expected_delivery": _mixed(
                            (getattr(value, "properties", {}) or {}).get("expected_delivery", "")
                            for value in purchased
                        ),
                        "alternative_material": _mixed(
                            alternative
                            for value in purchased
                            for alternative in (value.alternatives or ())
                        ),
                    })
                enrich(
                    workflow, entity_ids, group_id=item.group_id,
                    material=item.material_or_grade, blocked=item.blocked,
                )
                rows.append(BOMWorkspaceRow(
                    family=family, group_id=item.group_id, entity_ids=entity_ids,
                    mark=item.article_number, description=item.description,
                    profile=item.profile_or_size, material=item.material_or_grade,
                    length_mm=item.length_mm, quantity=item.quantity,
                    **workflow,
                    status="blocked" if item.blocked else "ready", blocked=item.blocked,
                    blocking_reasons=tuple(item.blocking_reasons), raw=item,
                ))
        elif family == "fasteners":
            for item in snapshot.fastener_bom:
                workflow = self._workflow_fields(item.fastener_ids)
                enrich(
                    workflow, item.fastener_ids, group_id=item.group_id,
                    material=item.grade, blocked=item.blocked,
                )
                rows.append(BOMWorkspaceRow(
                    family=family, group_id=item.group_id, entity_ids=_unique(item.fastener_ids),
                    mark=item.fastener_type, description=item.standard, profile=f"Ø{item.diameter_mm:g} × {item.length_mm:g}",
                    material=item.grade, length_mm=item.length_mm, quantity=item.quantity,
                    **workflow,
                    status="blocked" if item.blocked else "ready", blocked=item.blocked,
                    blocking_reasons=tuple(item.blocking_reasons), raw=item,
                ))
        elif family == "welds":
            for item in snapshot.weld_bom:
                workflow = self._workflow_fields(item.weld_ids)
                enrich(
                    workflow, item.weld_ids, group_id=item.group_id,
                    material=item.location, blocked=item.blocked,
                )
                rows.append(BOMWorkspaceRow(
                    family=family, group_id=item.group_id, entity_ids=_unique(item.weld_ids),
                    mark=", ".join(item.assembly_marks), description=item.weld_type,
                    profile=f"a={item.size_mm:g} · {item.process}".strip(" ·"), material=item.location,
                    length_mm=item.length_mm, quantity=item.quantity,
                    **workflow,
                    status="blocked" if item.blocked else "ready", blocked=item.blocked,
                    blocking_reasons=tuple(item.blocking_reasons), raw=item,
                ))
        elif family == "materials":
            for item in snapshot.material_bom:
                part_ids = _unique(
                    entity_id
                    for part_row in snapshot.part_bom
                    if part_row.category == item.category
                    and part_row.material == item.material
                    and part_row.profile == item.profile
                    for entity_id in part_row.part_ids
                )
                workflow = enrich(
                    self._workflow_fields(part_ids), part_ids, group_id=item.group_id,
                    material=item.material, blocked=item.blocked,
                )
                workflow.update(self._stock_fields(
                    profile=item.profile, material=item.material,
                    required_length_mm=float(item.net_length_mm or 0.0),
                ))
                rows.append(BOMWorkspaceRow(
                    family=family, group_id=item.group_id, entity_ids=part_ids,
                    mark=item.category, description=item.profile, profile=item.profile,
                    material=item.material, length_mm=item.net_length_mm,
                    quantity=item.quantity, total_mass_kg=item.total_mass_kg,
                    total_surface_m2=item.total_surface_area_m2,
                    **workflow,
                    status="blocked" if item.blocked else "ready", blocked=item.blocked,
                    blocking_reasons=tuple(item.blocking_reasons), raw=item,
                ))
        elif family == "conflicts":
            for item in snapshot.conflicts:
                workflow = enrich(
                    self._workflow_fields(item.entity_ids), item.entity_ids,
                    group_id=item.conflict_id, blocked=item.blocking,
                )
                rows.append(BOMWorkspaceRow(
                    family=family, group_id=item.conflict_id,
                    entity_ids=_unique(item.entity_ids), mark=item.key,
                    description=item.message, profile=item.conflict_type,
                    material=item.severity, quantity=len(item.entity_ids),
                    **workflow,
                    status="blocked" if item.blocking else "warning", blocked=item.blocking,
                    blocking_reasons=(item.message,), raw=item,
                ))
        return tuple(rows)


def scoped_bom_snapshot(
    snapshot: BOMSnapshot,
    *,
    entity_ids: Iterable[str] = (),
    group_ids: Iterable[str] = (),
    scope: BOMScope | None = None,
    project: Any | None = None,
) -> BOMSnapshot:
    """Return a deterministic export snapshot for an explicit BOM scope."""
    entities = set(_unique(entity_ids if scope is None else scope.entity_ids))
    groups = set(_unique(group_ids if scope is None else scope.group_ids))
    if not entities and not groups:
        return snapshot
    direct_groups = groups | {
        str(row.get("group_id") or "")
        for row in snapshot.traceability
        if str(row.get("internal_id") or "") in entities
    }

    assembly_rows = [
        row for row in snapshot.assembly_bom
        if row.group_id in direct_groups
        or bool(entities.intersection(row.assembly_ids))
        or bool(entities.intersection(getattr(row, "part_ids", ())))
        or bool(entities.intersection(getattr(row, "purchased_item_ids", ())))
        or bool(entities.intersection(getattr(row, "fastener_ids", ())))
        or bool(entities.intersection(getattr(row, "weld_ids", ())))
    ]
    known_assembly_groups = {row.group_id for row in assembly_rows}
    while True:
        child_ids = {
            child_id
            for row in assembly_rows
            for child_id in getattr(row, "child_assembly_ids", ())
        }
        discovered = [
            row for row in snapshot.assembly_bom
            if row.group_id not in known_assembly_groups
            and child_ids.intersection(row.assembly_ids)
        ]
        if not discovered:
            break
        assembly_rows.extend(discovered)
        known_assembly_groups.update(row.group_id for row in discovered)
    related_entities = {
        entity_id
        for row in assembly_rows
        for name in (
            "assembly_ids", "part_ids", "purchased_item_ids", "fastener_ids",
            "weld_ids", "child_assembly_ids",
        )
        for entity_id in getattr(row, name, ())
    }
    effective_entities = entities | related_entities
    trace_groups = {
        str(row.get("group_id") or "")
        for row in snapshot.traceability
        if str(row.get("internal_id") or "") in effective_entities
    }
    selected_groups = direct_groups | trace_groups | known_assembly_groups

    def selected(row: Any, ids_name: str) -> bool:
        row_ids = {str(value) for value in getattr(row, ids_name, ())}
        if row.group_id in selected_groups:
            return True
        return bool(effective_entities.intersection(row_ids))

    part_rows = [row for row in snapshot.part_bom if selected(row, "part_ids")]
    purchase_rows = [
        row for row in snapshot.purchase_bom
        if selected(row, "part_ids")
        or bool(effective_entities.intersection(getattr(row, "purchased_item_ids", ())))
    ]
    fastener_rows = [row for row in snapshot.fastener_bom if selected(row, "fastener_ids")]
    weld_rows = [row for row in snapshot.weld_bom if selected(row, "weld_ids")]
    assembly_scope = bool(scope is not None and scope.family == "assemblies" and project is not None)
    selected_assembly_marks = {row.assembly_mark for row in assembly_rows}
    if assembly_scope:
        exact_part_ids = related_entities.intersection(project.parts)
        exact_purchase_ids = related_entities.intersection(project.purchased_items)
        exact_fastener_ids = related_entities.intersection(project.fasteners)
        exact_weld_ids = related_entities.intersection(project.welds)
        narrowed_parts = []
        for row in part_rows:
            ids = sorted(exact_part_ids.intersection(row.part_ids))
            if not ids:
                continue
            parts = [project.parts[part_id] for part_id in ids]
            quantity = sum(max(1, int(part.quantity_total or 1)) for part in parts)
            narrowed_parts.append(replace(
                row,
                part_ids=ids,
                quantity=quantity,
                total_mass_kg=round(sum(
                    float(part.mass_each_kg or 0.0) * max(1, int(part.quantity_total or 1))
                    for part in parts
                ), 6),
                total_surface_area_m2=round(sum(
                    float(part.surface_area_each_m2 or 0.0) * max(1, int(part.quantity_total or 1))
                    for part in parts
                ), 9),
                assembly_marks=sorted(selected_assembly_marks.intersection(row.assembly_marks)),
                source_entity_ids=sorted({
                    part.source_identity.source_entity_id for part in parts
                    if part.source_identity.source_entity_id
                }),
            ))
        part_rows = narrowed_parts
        narrowed_purchase = []
        for row in purchase_rows:
            part_ids = sorted(exact_part_ids.intersection(row.part_ids))
            purchased_ids = sorted(
                exact_purchase_ids.intersection(getattr(row, "purchased_item_ids", ()))
            )
            if not part_ids and not purchased_ids:
                continue
            legacy = [project.parts[part_id] for part_id in part_ids]
            purchased = [project.purchased_items[item_id] for item_id in purchased_ids]
            quantity = sum(
                max(1, int(part.quantity_total or 1)) for part in legacy
            ) + sum(float(item.quantity or 0.0) for item in purchased)
            narrowed_purchase.append(replace(
                row,
                part_ids=part_ids,
                purchased_item_ids=purchased_ids,
                quantity=quantity,
                total_price=round(float(row.unit_price or 0.0) * quantity, 2),
                assembly_marks=sorted(selected_assembly_marks.intersection(row.assembly_marks)),
                source_entity_ids=sorted({
                    item.source_identity.source_entity_id for item in (*legacy, *purchased)
                    if item.source_identity.source_entity_id
                }),
            ))
        purchase_rows = narrowed_purchase
        narrowed_fasteners = []
        for row in fastener_rows:
            ids = sorted(exact_fastener_ids.intersection(row.fastener_ids))
            if not ids:
                continue
            narrowed_fasteners.append(replace(
                row,
                fastener_ids=ids,
                quantity=sum(max(1, int(project.fasteners[item_id].quantity or 1)) for item_id in ids),
                assembly_marks=sorted(selected_assembly_marks.intersection(row.assembly_marks)),
                source_entity_ids=sorted({
                    project.fasteners[item_id].source_identity.source_entity_id
                    for item_id in ids
                    if project.fasteners[item_id].source_identity.source_entity_id
                }),
            ))
        fastener_rows = narrowed_fasteners
        narrowed_welds = []
        for row in weld_rows:
            ids = sorted(exact_weld_ids.intersection(row.weld_ids))
            if not ids:
                continue
            weld_items = [project.welds[item_id] for item_id in ids]
            narrowed_welds.append(replace(
                row,
                weld_ids=ids,
                quantity=len(ids),
                total_length_mm=round(sum(float(item.length_mm or 0.0) for item in weld_items), 6),
                total_time_minutes=round(sum(float(item.time_minutes or 0.0) for item in weld_items), 6),
                total_cost=round(sum(float(item.cost or 0.0) for item in weld_items), 6),
                assembly_marks=sorted(selected_assembly_marks.intersection(row.assembly_marks)),
                source_entity_ids=sorted({
                    item.source_identity.source_entity_id for item in weld_items
                    if item.source_identity.source_entity_id
                }),
            ))
        weld_rows = narrowed_welds
    assembly_marks = {
        mark
        for row in (*part_rows, *purchase_rows)
        for mark in getattr(row, "assembly_marks", ())
    }
    assembly_rows = list({row.group_id: row for row in (
        *assembly_rows,
        *(
            row for row in snapshot.assembly_bom
            if selected(row, "assembly_ids") or row.assembly_mark in assembly_marks
        ),
    )}.values())
    material_rows = []
    for row in snapshot.material_bom:
        matching_parts = [
            part for part in part_rows
            if (part.category, part.material, part.profile)
            == (row.category, row.material, row.profile)
        ]
        if row.group_id not in selected_groups and not matching_parts:
            continue
        if assembly_scope:
            if not matching_parts:
                continue
            material_rows.append(replace(
                row,
                quantity=sum(part.quantity for part in matching_parts),
                net_length_mm=round(sum(part.length_mm * part.quantity for part in matching_parts), 6),
                total_mass_kg=round(sum(part.total_mass_kg for part in matching_parts), 6),
                total_surface_area_m2=round(sum(
                    part.total_surface_area_m2 for part in matching_parts
                ), 9),
                part_group_count=len(matching_parts),
                blocked=any(part.blocked for part in matching_parts),
                blocking_reasons=sorted({
                    reason for part in matching_parts for reason in part.blocking_reasons
                }),
            ))
        else:
            material_rows.append(row)
    included_groups = {
        row.group_id
        for row in (
            *part_rows, *purchase_rows, *fastener_rows, *weld_rows,
            *assembly_rows, *material_rows,
        )
    }
    included_entities = entities | {
        entity_id
        for row in (*part_rows, *purchase_rows, *fastener_rows, *weld_rows, *assembly_rows)
        for name in ("part_ids", "purchased_item_ids", "fastener_ids", "weld_ids", "assembly_ids")
        for entity_id in getattr(row, name, ())
    }
    conflicts = [
        row for row in snapshot.conflicts
        if included_entities.intersection(row.entity_ids)
        or (not assembly_scope and included_groups.intersection(row.group_ids))
        or row.conflict_id in selected_groups
    ]
    traceability = [
        dict(row) for row in snapshot.traceability
        if str(row.get("internal_id") or "") in included_entities
        or (
            not assembly_scope
            and str(row.get("group_id") or "") in included_groups
        )
    ]
    blocking = sum(1 for row in conflicts if row.blocking) + sum(
        1 for row in (*part_rows, *purchase_rows, *fastener_rows, *weld_rows, *assembly_rows) if row.blocked
    )
    summary = {
        "part_group_count": len(part_rows),
        "assembly_group_count": len(assembly_rows),
        "purchase_group_count": len(purchase_rows),
        "fastener_group_count": len(fastener_rows),
        "weld_group_count": len(weld_rows),
        "material_group_count": len(material_rows),
        "traceability_record_count": len(traceability),
        "blocking_conflict_count": sum(1 for row in conflicts if row.blocking),
        "warning_conflict_count": sum(1 for row in conflicts if not row.blocking),
        "total_part_mass_kg": round(sum(row.total_mass_kg for row in part_rows), 6),
        "total_part_surface_m2": round(sum(row.total_surface_area_m2 for row in part_rows), 9),
        "total_part_length_mm": round(sum(row.length_mm * row.quantity for row in part_rows), 6),
        "purchase_quantity": round(sum(row.quantity for row in purchase_rows), 6),
        "fastener_quantity": sum(row.quantity for row in fastener_rows),
        "weld_object_count": sum(row.quantity for row in weld_rows),
        "scope": (scope.to_dict() if scope is not None else {
            "schema": "cws-bom-scope-1.0",
            "entity_ids": sorted(entities),
            "group_ids": sorted(groups),
        }),
    }
    original_validation = snapshot.validation
    validation = BOMValidation(
        passed=bool(original_validation and original_validation.passed and not blocking),
        production_ready=bool(original_validation and original_validation.production_ready and not blocking),
        checks=dict(original_validation.checks if original_validation else {}),
        blocking_conflict_count=summary["blocking_conflict_count"],
        warning_conflict_count=summary["warning_conflict_count"],
        traceability_coverage=(
            len({str(row.get("internal_id") or "") for row in traceability}) / len(included_entities)
            if included_entities else 1.0
        ),
        messages=list(original_validation.messages if original_validation else ())
        + ["Scoped BOM-export; productie-vrijgave blijft gebonden aan de volledige projectvalidatie"],
    )
    result = BOMSnapshot(
        project_id=snapshot.project_id,
        project_name=snapshot.project_name,
        generated_at=snapshot.generated_at,
        schema_version=snapshot.schema_version,
        classification_report_sha256=snapshot.classification_report_sha256,
        part_bom=part_rows,
        assembly_bom=assembly_rows,
        purchase_bom=purchase_rows,
        fastener_bom=fastener_rows,
        weld_bom=weld_rows,
        material_bom=material_rows,
        conflicts=conflicts,
        traceability=traceability,
        summary=summary,
        validation=validation,
    )
    result.refresh_hash()
    return result


__all__ = [
    "BOMActionAvailability",
    "BOMScope",
    "BOMSelectionSummary",
    "BOMWorkspaceReadModel",
    "BOMWorkspaceRow",
    "BOM_FAMILIES",
    "BOM_FAMILY_LABELS",
    "scoped_bom_snapshot",
]
