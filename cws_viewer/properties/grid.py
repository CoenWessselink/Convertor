"""Professional, renderer-neutral project property grid for CWS Viewer V8.

The module deliberately contains no Qt objects.  It provides one deterministic
query/virtualisation layer shared by the Qt grid, CLI exports, BOM views and
viewer selection bridge.  Canonical entities remain the only production truth;
this grid is read-only unless an explicit audited edit service is used elsewhere.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from functools import cmp_to_key
import json
import math
from pathlib import Path
import time
from typing import Any, Iterable, Iterator, Mapping, Sequence


class ColumnType(StrEnum):
    TEXT = "text"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    STATUS = "status"
    ID = "id"


class AggregateKind(StrEnum):
    NONE = "none"
    COUNT = "count"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    AVERAGE = "average"


class FilterOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    BETWEEN = "between"
    IS_EMPTY = "is_empty"
    NOT_EMPTY = "not_empty"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


class GridScope(StrEnum):
    ALL = "all"
    VISIBLE = "visible"
    SELECTED = "selected"
    CHANGED = "changed"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class GridColumn:
    # The first five fields retain the V3/V4 positional constructor contract.
    key: str
    label: str
    width: int = 120
    visible: bool = True
    order: int = 0
    data_type: ColumnType = ColumnType.TEXT
    aggregate: AggregateKind = AggregateKind.NONE
    sortable: bool = True
    filterable: bool = True
    groupable: bool = True
    frozen: bool = False
    number_format: str = ""
    unit: str = ""
    source: str = "canonical"

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_type", ColumnType(self.data_type))
        object.__setattr__(self, "aggregate", AggregateKind(self.aggregate))
        if not self.key.strip():
            raise ValueError("GridColumn key ontbreekt")
        if self.width < 40:
            raise ValueError("GridColumn width moet minimaal 40 zijn")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["data_type"] = self.data_type.value
        data["aggregate"] = self.aggregate.value
        return data

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GridColumn":
        return cls(
            key=str(value["key"]),
            label=str(value.get("label", value["key"])),
            width=max(40, int(value.get("width", 120))),
            visible=bool(value.get("visible", True)),
            order=int(value.get("order", 0)),
            data_type=ColumnType(str(value.get("data_type", ColumnType.TEXT.value))),
            aggregate=AggregateKind(str(value.get("aggregate", AggregateKind.NONE.value))),
            sortable=bool(value.get("sortable", True)),
            filterable=bool(value.get("filterable", True)),
            groupable=bool(value.get("groupable", True)),
            frozen=bool(value.get("frozen", False)),
            number_format=str(value.get("number_format", "")),
            unit=str(value.get("unit", "")),
            source=str(value.get("source", "canonical")),
        )


@dataclass(frozen=True, slots=True)
class GridRow:
    entity_id: str
    values: tuple[tuple[str, Any], ...]
    entity_type: str = "part"
    node_id: str = ""
    search_text: str = ""
    source_index: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        # Values are short, stable tuples.  Dict conversion is still cheaper
        # than keeping a second mutable truth per row.
        return dict(self.values).get(key, default)

    def as_dict(self) -> dict[str, Any]:
        return dict(self.values)


@dataclass(frozen=True, slots=True)
class GridSort:
    key: str
    descending: bool = False
    nulls_last: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GridFilter:
    key: str
    operator: FilterOperator = FilterOperator.EQ
    value: Any = None
    value2: Any = None
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "operator", FilterOperator(self.operator))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["operator"] = self.operator.value
        return data


@dataclass(frozen=True, slots=True)
class GridGroupSpec:
    key: str
    descending: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GridScopeState:
    visible_entity_ids: frozenset[str] = frozenset()
    selected_entity_ids: frozenset[str] = frozenset()

    @classmethod
    def create(
        cls,
        *,
        visible_entity_ids: Iterable[str] = (),
        selected_entity_ids: Iterable[str] = (),
    ) -> "GridScopeState":
        return cls(
            visible_entity_ids=frozenset(map(str, visible_entity_ids)),
            selected_entity_ids=frozenset(map(str, selected_entity_ids)),
        )


@dataclass(frozen=True, slots=True)
class GridQuery:
    text: str = ""
    filters: tuple[GridFilter, ...] = ()
    sorts: tuple[GridSort, ...] = ()
    groups: tuple[GridGroupSpec, ...] = ()
    scope: GridScope = GridScope.ALL

    def __post_init__(self) -> None:
        object.__setattr__(self, "filters", tuple(self.filters))
        object.__setattr__(self, "sorts", tuple(self.sorts))
        object.__setattr__(self, "groups", tuple(self.groups))
        object.__setattr__(self, "scope", GridScope(self.scope))

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "filters": [item.to_dict() for item in self.filters],
            "sorts": [item.to_dict() for item in self.sorts],
            "groups": [item.to_dict() for item in self.groups],
            "scope": self.scope.value,
        }


@dataclass(frozen=True, slots=True)
class GridAggregate:
    key: str
    kind: AggregateKind
    value: int | float | None
    count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", AggregateKind(self.kind))

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "kind": self.kind.value, "value": self.value, "count": self.count}


@dataclass(frozen=True, slots=True)
class GridFooter:
    row_count: int
    aggregates: tuple[GridAggregate, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"row_count": self.row_count, "aggregates": [item.to_dict() for item in self.aggregates]}


@dataclass(frozen=True, slots=True)
class GridGroupNode:
    key: str
    value: str
    level: int
    row_count: int
    entity_ids: tuple[str, ...]
    aggregates: tuple[GridAggregate, ...]
    children: tuple["GridGroupNode", ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "level": self.level,
            "row_count": self.row_count,
            "entity_ids": list(self.entity_ids),
            "aggregates": [item.to_dict() for item in self.aggregates],
            "children": [item.to_dict() for item in self.children],
        }


@dataclass(frozen=True, slots=True)
class GridQueryResult:
    model: "ProjectGridModel" = field(repr=False, compare=False)
    row_indices: tuple[int, ...]
    groups: tuple[GridGroupNode, ...]
    footer: GridFooter
    query: GridQuery
    elapsed_ms: float

    @property
    def row_count(self) -> int:
        return len(self.row_indices)

    def row(self, index: int) -> GridRow:
        return self.model.row_at_source_index(self.row_indices[index])

    def rows_page(self, offset: int, limit: int) -> tuple[GridRow, ...]:
        start = max(0, int(offset))
        end = min(self.row_count, start + max(0, int(limit)))
        return tuple(self.model.row_at_source_index(item) for item in self.row_indices[start:end])

    def iter_rows(self) -> Iterator[GridRow]:
        for index in self.row_indices:
            yield self.model.row_at_source_index(index)

    @property
    def rows(self) -> tuple[GridRow, ...]:
        # Compatibility convenience; virtual clients should use rows_page().
        return tuple(self.iter_rows())

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "elapsed_ms": self.elapsed_ms,
            "query": self.query.to_dict(),
            "footer": self.footer.to_dict(),
            "groups": [item.to_dict() for item in self.groups],
        }


@dataclass(frozen=True, slots=True)
class GridLayout:
    name: str
    columns: tuple[GridColumn, ...]
    sorts: tuple[GridSort, ...] = ()
    filters: tuple[GridFilter, ...] = ()
    groups: tuple[GridGroupSpec, ...] = ()
    scope: GridScope = GridScope.ALL
    row_height: int = 24
    alternating_rows: bool = True
    schema_version: str = "cws-grid-layout-1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "columns", tuple(self.columns))
        object.__setattr__(self, "sorts", tuple(self.sorts))
        object.__setattr__(self, "filters", tuple(self.filters))
        object.__setattr__(self, "groups", tuple(self.groups))
        object.__setattr__(self, "scope", GridScope(self.scope))
        if self.row_height < 16 or self.row_height > 96:
            raise ValueError("Grid row_height buiten geldig bereik")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "columns": [item.to_dict() for item in self.columns],
            "sorts": [item.to_dict() for item in self.sorts],
            "filters": [item.to_dict() for item in self.filters],
            "groups": [item.to_dict() for item in self.groups],
            "scope": self.scope.value,
            "row_height": self.row_height,
            "alternating_rows": self.alternating_rows,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GridLayout":
        if str(value.get("schema_version", "")) != "cws-grid-layout-1.0":
            raise ValueError("Onbekend gridlayout-schema")
        return cls(
            name=str(value.get("name", "Standaard")),
            columns=tuple(GridColumn.from_dict(item) for item in value.get("columns", ())),
            sorts=tuple(GridSort(**item) for item in value.get("sorts", ())),
            filters=tuple(
                GridFilter(
                    key=str(item["key"]),
                    operator=FilterOperator(str(item.get("operator", FilterOperator.EQ.value))),
                    value=item.get("value"),
                    value2=item.get("value2"),
                    case_sensitive=bool(item.get("case_sensitive", False)),
                )
                for item in value.get("filters", ())
            ),
            groups=tuple(GridGroupSpec(**item) for item in value.get("groups", ())),
            scope=GridScope(str(value.get("scope", GridScope.ALL.value))),
            row_height=int(value.get("row_height", 24)),
            alternating_rows=bool(value.get("alternating_rows", True)),
        )


_DEFAULT_COLUMNS: tuple[GridColumn, ...] = (
    GridColumn("status", "Status", 100, True, 0, ColumnType.STATUS),
    GridColumn("entity_type", "Type", 105, True, 1, ColumnType.TEXT),
    GridColumn("assembly_mark", "Merk", 110, True, 2, ColumnType.TEXT),
    GridColumn("part_position", "Positie", 110, True, 3, ColumnType.TEXT),
    GridColumn("name", "Naam", 210, True, 4, ColumnType.TEXT),
    GridColumn("category", "Categorie", 125, True, 5, ColumnType.TEXT),
    GridColumn("profile", "Profiel", 120, True, 6, ColumnType.TEXT),
    GridColumn("material", "Materiaal", 110, True, 7, ColumnType.TEXT),
    GridColumn("length_mm", "Lengte", 95, True, 8, ColumnType.NUMBER, AggregateKind.SUM, number_format="0.00", unit="mm"),
    GridColumn("quantity_total", "Aantal", 80, True, 9, ColumnType.INTEGER, AggregateKind.SUM, number_format="0"),
    GridColumn("mass_each_kg", "Massa/stuk", 105, True, 10, ColumnType.NUMBER, AggregateKind.SUM, number_format="0.000", unit="kg"),
    GridColumn("total_mass_kg", "Totaalmassa", 110, True, 11, ColumnType.NUMBER, AggregateKind.SUM, number_format="0.000", unit="kg"),
    GridColumn("classification_status", "Classificatie", 125, True, 12, ColumnType.STATUS),
    GridColumn("export_status", "Export", 110, True, 13, ColumnType.STATUS),
    GridColumn("revision_status", "Revisie", 105, True, 14, ColumnType.STATUS, source="revision"),
    GridColumn("revision_impacts", "Impact", 170, True, 15, ColumnType.TEXT, source="revision"),
    GridColumn("production_reuse", "Hergebruik", 95, True, 16, ColumnType.BOOLEAN, source="revision"),
    GridColumn("blocked", "Geblokkeerd", 100, True, 17, ColumnType.BOOLEAN),
    GridColumn("warnings", "Waarschuwingen", 260, True, 18, ColumnType.TEXT),
    GridColumn("source_entity_id", "Bronentity", 115, False, 19, ColumnType.ID, source="source"),
    GridColumn("entity_id", "Interne ID", 260, False, 20, ColumnType.ID),
    GridColumn("source_format", "Bronformaat", 100, False, 21, ColumnType.TEXT, source="source"),
    GridColumn("phase", "Fase", 100, False, 22, ColumnType.TEXT),
    GridColumn("confidence", "Confidence", 95, False, 23, ColumnType.NUMBER, AggregateKind.AVERAGE, number_format="0.0%"),
    GridColumn("surface_area_each_m2", "Oppervlak/stuk", 120, False, 24, ColumnType.NUMBER, AggregateKind.SUM, number_format="0.000", unit="m²"),
    GridColumn("total_surface_m2", "Totaal oppervlak", 125, False, 25, ColumnType.NUMBER, AggregateKind.SUM, number_format="0.000", unit="m²"),
    GridColumn("nc1_eligible", "NC1 geschikt", 100, False, 26, ColumnType.BOOLEAN),
    GridColumn("warnings_count", "Meldingen", 85, False, 27, ColumnType.INTEGER, AggregateKind.SUM),
    GridColumn("blockers", "Blokkadecodes", 260, False, 28, ColumnType.TEXT),
    GridColumn("revision_confidence", "Revisieconfidence", 120, False, 29, ColumnType.NUMBER, AggregateKind.AVERAGE, number_format="0.0%", source="revision"),
    GridColumn("revision_blockers", "Revisieblokkades", 260, False, 30, ColumnType.TEXT, source="revision"),
    GridColumn("supplier", "Leverancier", 140, False, 31, ColumnType.TEXT),
    GridColumn("manufacturer", "Fabrikant", 140, False, 32, ColumnType.TEXT),
    GridColumn("standard", "Norm", 120, False, 33, ColumnType.TEXT),
    GridColumn("unit", "Eenheid", 80, False, 34, ColumnType.TEXT),
    GridColumn("unit_price", "Stukprijs", 95, False, 35, ColumnType.NUMBER, AggregateKind.SUM, number_format="€ 0.00"),
    GridColumn("total_price", "Totaalprijs", 100, False, 36, ColumnType.NUMBER, AggregateKind.SUM, number_format="€ 0.00"),
    GridColumn("lead_time_days", "Levertijd", 90, False, 37, ColumnType.INTEGER, AggregateKind.MAX, unit="dagen"),
    GridColumn("diameter_mm", "Diameter", 90, False, 38, ColumnType.NUMBER, AggregateKind.NONE, number_format="0.00", unit="mm"),
    GridColumn("hole_diameter_mm", "Gatdiameter", 100, False, 39, ColumnType.NUMBER, AggregateKind.NONE, number_format="0.00", unit="mm"),
    GridColumn("connected_count", "Verbonden delen", 105, False, 40, ColumnType.INTEGER, AggregateKind.SUM),
    GridColumn("size_mm", "Lasmaat", 90, False, 41, ColumnType.NUMBER, AggregateKind.NONE, number_format="0.00", unit="mm"),
    GridColumn("process", "Proces", 90, False, 42, ColumnType.TEXT),
    GridColumn("side", "Zijde", 90, False, 43, ColumnType.TEXT),
    GridColumn("location", "Locatie", 110, False, 44, ColumnType.TEXT),
    GridColumn("time_minutes", "Bewerkingstijd", 115, False, 45, ColumnType.NUMBER, AggregateKind.SUM, number_format="0.00", unit="min"),
    GridColumn("cost", "Kosten", 90, False, 46, ColumnType.NUMBER, AggregateKind.SUM, number_format="€ 0.00"),
    GridColumn("part_count", "Onderdelen", 90, False, 47, ColumnType.INTEGER, AggregateKind.SUM),
    GridColumn("fastener_count", "Bevestigers", 95, False, 48, ColumnType.INTEGER, AggregateKind.SUM),
    GridColumn("weld_count", "Lassen", 80, False, 49, ColumnType.INTEGER, AggregateKind.SUM),
    GridColumn("geometry_hash", "Geometry hash", 260, False, 50, ColumnType.ID),
    GridColumn("manufacturing_hash", "Manufacturing hash", 260, False, 51, ColumnType.ID),
)


def _enum_text(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _safe_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any) -> str:
    return str(value or "")


def _source_identity(entity: Any) -> Any:
    return getattr(entity, "source_identity", None)


def _issues(entity: Any) -> tuple[str, ...]:
    values = []
    for issue in getattr(entity, "validation_issues", ()) or ():
        code = _text(getattr(issue, "code", ""))
        message = _text(getattr(issue, "message", issue))
        values.append(f"{code}: {message}" if code else message)
    return tuple(item for item in values if item)


def _revision_map(report: Any | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if report is None:
        return result
    changes = report.get("changes", ()) if isinstance(report, Mapping) else getattr(report, "changes", ())
    for item in changes or ():
        if isinstance(item, Mapping):
            new_id = _text(item.get("new_entity_id"))
            old_id = _text(item.get("old_entity_id"))
        else:
            new_id = _text(getattr(item, "new_entity_id", ""))
            old_id = _text(getattr(item, "old_entity_id", ""))
        if new_id:
            result[new_id] = item
        elif old_id:
            result[f"removed:{old_id}"] = item
    return result


def _revision_values(change: Any | None) -> dict[str, Any]:
    if change is None:
        return {
            "revision_status": "",
            "revision_impacts": "",
            "revision_confidence": None,
            "production_reuse": True,
            "revision_blockers": "",
        }
    getter = change.get if isinstance(change, Mapping) else lambda key, default=None: getattr(change, key, default)
    impacts_raw = getter("impacts", ()) or ()
    impacts = ", ".join(_enum_text(item) for item in impacts_raw)
    blockers = "; ".join(map(str, getter("blocking_codes", ()) or ()))
    reuse = getter("production_reuse_allowed", None)
    if reuse is None and not isinstance(change, Mapping):
        reuse = getattr(change, "production_reuse_allowed", False)
    return {
        "revision_status": _enum_text(getter("kind", "")),
        "revision_impacts": impacts,
        "revision_confidence": getter("confidence", None),
        "production_reuse": bool(reuse),
        "revision_blockers": blockers,
    }


class ProjectGridModel:
    """One deterministic grid datasource for project, viewer and exports."""

    def __init__(
        self,
        project: Any,
        *,
        scene: Any | None = None,
        revision_report: Any | None = None,
        columns: Iterable[GridColumn] | None = None,
        include_removed_revision_rows: bool = True,
    ) -> None:
        self.project = project
        self.scene = scene
        self.revision_report = revision_report
        self.columns = tuple(sorted(columns or _DEFAULT_COLUMNS, key=lambda item: (item.order, item.key)))
        self._column_by_key = {item.key: item for item in self.columns}
        self._node_by_entity = {
            _text(getattr(node, "entity_id", "")): _text(getattr(node, "node_id", ""))
            for node in (getattr(scene, "nodes", ()) or ())
        }
        self._revision_by_entity = _revision_map(revision_report)
        self._scope_state = GridScopeState()
        self._rows = self._build_rows(include_removed_revision_rows=include_removed_revision_rows)
        self._row_by_entity = {row.entity_id: row for row in self._rows}

    @property
    def rows(self) -> tuple[GridRow, ...]:
        return self._rows

    def row_at_source_index(self, source_index: int) -> GridRow:
        return self._rows[source_index]

    def row_for_entity(self, entity_id: str) -> GridRow:
        return self._row_by_entity[str(entity_id)]

    def set_scope_state(
        self,
        *,
        visible_entity_ids: Iterable[str] = (),
        selected_entity_ids: Iterable[str] = (),
    ) -> GridScopeState:
        self._scope_state = GridScopeState.create(
            visible_entity_ids=visible_entity_ids,
            selected_entity_ids=selected_entity_ids,
        )
        return self._scope_state

    def _base_values(self, entity: Any, entity_type: str) -> dict[str, Any]:
        identity = _source_identity(entity)
        issue_values = _issues(entity)
        category = _enum_text(getattr(entity, "category", entity_type))
        status = _enum_text(getattr(entity, "status", ""))
        classification_status = _text(getattr(entity, "classification_status", ""))
        export_status = _text(getattr(entity, "export_status", ""))
        source_entity_id = _text(getattr(identity, "source_entity_id", ""))
        source_format = _text(getattr(identity, "source_format", ""))
        assembly_mark = _text(getattr(entity, "assembly_mark", "") or getattr(identity, "assembly_mark", ""))
        part_position = _text(getattr(entity, "part_position", "") or getattr(identity, "part_position", ""))
        quantity = _safe_float(getattr(entity, "quantity_total", getattr(entity, "quantity", 1)))
        mass_each = _safe_float(getattr(entity, "mass_each_kg", 0.0))
        length = _safe_float(getattr(entity, "length_mm", 0.0))
        blocked = bool(issue_values) or status == "blocked" or export_status == "blocked" or classification_status in {"blocked", "review_required", "unclassified"}
        values: dict[str, Any] = {
            "status": status,
            "entity_type": entity_type,
            "category": category,
            "assembly_mark": assembly_mark,
            "part_position": part_position,
            "name": _text(getattr(entity, "name", "")),
            "profile": _text(getattr(entity, "normalized_profile", "") or getattr(entity, "profile", "")),
            "material": _text(getattr(entity, "normalized_material", "") or getattr(entity, "material", "")),
            "length_mm": length,
            "quantity_total": int(quantity) if quantity.is_integer() else quantity,
            "mass_each_kg": mass_each,
            "total_mass_kg": mass_each * quantity,
            "surface_area_each_m2": _safe_float(getattr(entity, "surface_area_each_m2", 0.0)),
            "classification_status": classification_status,
            "export_status": export_status,
            "nc1_eligible": bool(getattr(entity, "nc1_eligible", False)),
            "source_entity_id": source_entity_id,
            "source_format": source_format,
            "phase": _text(getattr(entity, "phase", "") or getattr(self.project, "project_phase", "")),
            "confidence": _safe_float(getattr(entity, "confidence", getattr(entity, "classification_confidence", 0.0))),
            "warnings_count": len(issue_values),
            "warnings": "; ".join(issue_values),
            "blocked": blocked,
            "blockers": "; ".join(issue_values),
            "entity_id": _text(getattr(entity, "internal_id", "")),
            "geometry_hash": _text(getattr(entity, "geometry_hash", "")),
            "manufacturing_hash": _text(getattr(entity, "manufacturing_hash", "")),
        }
        return values

    def _entity_values(self, entity: Any, entity_type: str) -> dict[str, Any]:
        values = self._base_values(entity, entity_type)
        if entity_type == "assembly":
            quantity = _safe_int(getattr(entity, "quantity", 1), 1)
            values.update(
                assembly_mark=_text(getattr(entity, "assembly_mark", "")),
                quantity_total=quantity,
                mass_each_kg=_safe_float(getattr(entity, "total_weight_kg", 0.0)) / max(1, quantity),
                total_mass_kg=_safe_float(getattr(entity, "total_weight_kg", 0.0)),
                total_surface_m2=_safe_float(getattr(entity, "surface_area_m2", 0.0)),
                part_count=len(getattr(entity, "part_ids", ()) or ()),
                fastener_count=len(getattr(entity, "fastener_ids", ()) or ()),
                weld_count=len(getattr(entity, "weld_ids", ()) or ()),
                classification_status="assembly",
                export_status=_text(getattr(entity, "production_status", "")),
            )
        elif entity_type == "purchased_item":
            quantity = _safe_float(getattr(entity, "quantity", 1.0))
            unit_price = _safe_float(getattr(entity, "unit_price", 0.0))
            values.update(
                part_position=_text(getattr(entity, "article_number", "")),
                name=_text(getattr(entity, "description", "") or getattr(entity, "name", "")),
                material=_text(getattr(entity, "material", "")),
                quantity_total=quantity,
                supplier=_text(getattr(entity, "supplier", "")),
                manufacturer=_text(getattr(entity, "manufacturer", "")),
                standard=_text(getattr(entity, "standard", "")),
                unit=_text(getattr(entity, "unit", "piece")),
                unit_price=unit_price,
                total_price=unit_price * quantity,
                lead_time_days=_safe_int(getattr(entity, "lead_time_days", 0)),
                classification_status="purchased_item",
                export_status=_text(getattr(entity, "purchase_status", "")),
            )
        elif entity_type == "fastener":
            quantity = _safe_int(getattr(entity, "quantity", 1), 1)
            values.update(
                name=_text(getattr(entity, "fastener_type", "") or getattr(entity, "name", "")),
                profile=_text(getattr(entity, "standard", "")),
                material=_text(getattr(entity, "grade", "")),
                length_mm=_safe_float(getattr(entity, "length_mm", 0.0)),
                quantity_total=quantity,
                diameter_mm=_safe_float(getattr(entity, "diameter_mm", 0.0)),
                hole_diameter_mm=_safe_float(getattr(entity, "hole_diameter_mm", 0.0)),
                connected_count=len(getattr(entity, "connected_part_ids", ()) or ()),
                classification_status="fastener",
            )
        elif entity_type == "weld":
            values.update(
                name=_text(getattr(entity, "weld_type", "") or getattr(entity, "name", "")),
                length_mm=_safe_float(getattr(entity, "length_mm", 0.0)),
                quantity_total=1,
                size_mm=_safe_float(getattr(entity, "size_mm", 0.0)),
                process=_text(getattr(entity, "process", "")),
                side=_text(getattr(entity, "side", "")),
                location=_text(getattr(entity, "location", "")),
                time_minutes=_safe_float(getattr(entity, "time_minutes", 0.0)),
                cost=_safe_float(getattr(entity, "cost", 0.0)),
                connected_count=len(getattr(entity, "connected_part_ids", ()) or ()),
                classification_status="weld",
            )
        return values

    def _build_rows(self, *, include_removed_revision_rows: bool) -> tuple[GridRow, ...]:
        rows: list[GridRow] = []
        collections = (
            ("assembly", getattr(self.project, "assemblies", {}) or {}),
            ("part", getattr(self.project, "parts", {}) or {}),
            ("purchased_item", getattr(self.project, "purchased_items", {}) or {}),
            ("fastener", getattr(self.project, "fasteners", {}) or {}),
            ("weld", getattr(self.project, "welds", {}) or {}),
        )
        for entity_type, collection in collections:
            for entity_id, entity in sorted(collection.items(), key=lambda item: str(item[0])):
                values = self._entity_values(entity, entity_type)
                values.update(_revision_values(self._revision_by_entity.get(str(entity_id))))
                if values["revision_blockers"]:
                    values["blocked"] = True
                    values["blockers"] = "; ".join(filter(None, (values["blockers"], values["revision_blockers"])))
                values["entity_id"] = str(entity_id)
                node_id = self._node_by_entity.get(str(entity_id), "")
                search_text = " ".join(_text(value).casefold() for value in values.values())
                rows.append(
                    GridRow(
                        entity_id=str(entity_id),
                        values=tuple(values.items()),
                        entity_type=entity_type,
                        node_id=node_id,
                        search_text=search_text,
                        source_index=len(rows),
                    )
                )
        if include_removed_revision_rows:
            for key, change in sorted(self._revision_by_entity.items()):
                if not key.startswith("removed:"):
                    continue
                entity_id = key
                rev = _revision_values(change)
                getter = change.get if isinstance(change, Mapping) else lambda name, default=None: getattr(change, name, default)
                values = {
                    "status": "obsolete",
                    "entity_type": "removed",
                    "category": "removed",
                    "assembly_mark": "",
                    "part_position": _text(getter("old_part_position", "")),
                    "name": _text(getter("old_source_id", "Verwijderd onderdeel")),
                    "profile": "",
                    "material": "",
                    "length_mm": 0.0,
                    "quantity_total": 0,
                    "mass_each_kg": 0.0,
                    "total_mass_kg": 0.0,
                    "classification_status": "removed",
                    "export_status": "removed",
                    "source_entity_id": _text(getter("old_source_id", "")),
                    "phase": _text(getattr(self.project, "project_phase", "")),
                    "warnings_count": 0,
                    "warnings": "",
                    "blocked": True,
                    "blockers": "CWS-V7-REVISION-REMOVED",
                    "entity_id": entity_id,
                    **rev,
                }
                search_text = " ".join(_text(value).casefold() for value in values.values())
                rows.append(GridRow(entity_id, tuple(values.items()), "removed", "", search_text, len(rows)))
        return tuple(rows)

    @staticmethod
    def _empty(value: Any) -> bool:
        return value is None or value == "" or value == () or value == []

    @staticmethod
    def _normalised(value: Any, *, case_sensitive: bool = False) -> Any:
        if isinstance(value, str):
            return value if case_sensitive else value.casefold()
        return value

    def _matches_filter(self, row: GridRow, rule: GridFilter) -> bool:
        current = row.get(rule.key)
        operator = rule.operator
        if operator == FilterOperator.IS_EMPTY:
            return self._empty(current)
        if operator == FilterOperator.NOT_EMPTY:
            return not self._empty(current)
        if operator == FilterOperator.IS_TRUE:
            return bool(current)
        if operator == FilterOperator.IS_FALSE:
            return not bool(current)
        left = self._normalised(current, case_sensitive=rule.case_sensitive)
        right = self._normalised(rule.value, case_sensitive=rule.case_sensitive)
        right2 = self._normalised(rule.value2, case_sensitive=rule.case_sensitive)
        if operator == FilterOperator.EQ:
            return left == right
        if operator == FilterOperator.NE:
            return left != right
        if operator in {FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS, FilterOperator.STARTS_WITH, FilterOperator.ENDS_WITH}:
            haystack = _text(left)
            needle = _text(right)
            result = (
                needle in haystack if operator in {FilterOperator.CONTAINS, FilterOperator.NOT_CONTAINS}
                else haystack.startswith(needle) if operator == FilterOperator.STARTS_WITH
                else haystack.endswith(needle)
            )
            return not result if operator == FilterOperator.NOT_CONTAINS else result
        if operator in {FilterOperator.IN, FilterOperator.NOT_IN}:
            raw_options = rule.value if isinstance(rule.value, (list, tuple, set, frozenset)) else (rule.value,)
            options = tuple(
                self._normalised(item, case_sensitive=rule.case_sensitive)
                for item in raw_options
            )
            result = left in options
            return not result if operator == FilterOperator.NOT_IN else result
        try:
            left_num = float(left)
            right_num = float(right)
            right2_num = float(right2) if right2 is not None else right_num
        except (TypeError, ValueError):
            return False
        if operator == FilterOperator.GT:
            return left_num > right_num
        if operator == FilterOperator.GTE:
            return left_num >= right_num
        if operator == FilterOperator.LT:
            return left_num < right_num
        if operator == FilterOperator.LTE:
            return left_num <= right_num
        if operator == FilterOperator.BETWEEN:
            low, high = sorted((right_num, right2_num))
            return low <= left_num <= high
        return False

    def _matches_scope(self, row: GridRow, scope: GridScope) -> bool:
        if scope == GridScope.ALL:
            return True
        if scope == GridScope.VISIBLE:
            return row.entity_id in self._scope_state.visible_entity_ids
        if scope == GridScope.SELECTED:
            return row.entity_id in self._scope_state.selected_entity_ids
        if scope == GridScope.CHANGED:
            return row.get("revision_status", "") not in {"", "unchanged"}
        if scope == GridScope.BLOCKED:
            return bool(row.get("blocked", False))
        return True

    @staticmethod
    def _compare_values(left: Any, right: Any, spec: GridSort) -> int:
        left_empty = left is None or left == ""
        right_empty = right is None or right == ""
        if left_empty or right_empty:
            if left_empty and right_empty:
                return 0
            result = 1 if left_empty else -1
            return result if spec.nulls_last else -result
        if isinstance(left, bool) or isinstance(right, bool):
            lval, rval = bool(left), bool(right)
        else:
            try:
                lval, rval = float(left), float(right)
            except (TypeError, ValueError):
                lval, rval = _text(left).casefold(), _text(right).casefold()
        result = -1 if lval < rval else 1 if lval > rval else 0
        return -result if spec.descending else result

    def _sort_indices(self, indices: list[int], sorts: Sequence[GridSort]) -> None:
        if not sorts:
            sorts = (GridSort("part_position"), GridSort("name"))

        def compare(left_index: int, right_index: int) -> int:
            left, right = self._rows[left_index], self._rows[right_index]
            for spec in sorts:
                result = self._compare_values(left.get(spec.key), right.get(spec.key), spec)
                if result:
                    return result
            return -1 if left.entity_id < right.entity_id else 1 if left.entity_id > right.entity_id else 0

        indices.sort(key=cmp_to_key(compare))

    def _aggregate(self, indices: Sequence[int]) -> tuple[GridAggregate, ...]:
        aggregates: list[GridAggregate] = []
        for column in self.columns:
            if column.aggregate == AggregateKind.NONE:
                continue
            values = [self._rows[index].get(column.key) for index in indices]
            numeric = [float(value) for value in values if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))]
            if column.aggregate == AggregateKind.COUNT:
                result: int | float | None = len([value for value in values if not self._empty(value)])
            elif not numeric:
                result = None
            elif column.aggregate == AggregateKind.SUM:
                result = math.fsum(numeric)
            elif column.aggregate == AggregateKind.MIN:
                result = min(numeric)
            elif column.aggregate == AggregateKind.MAX:
                result = max(numeric)
            elif column.aggregate == AggregateKind.AVERAGE:
                result = math.fsum(numeric) / len(numeric)
            else:
                result = None
            aggregates.append(GridAggregate(column.key, column.aggregate, result, len(numeric)))
        return tuple(aggregates)

    def _build_group_nodes(
        self,
        indices: Sequence[int],
        specs: Sequence[GridGroupSpec],
        *,
        level: int = 0,
    ) -> tuple[GridGroupNode, ...]:
        if not specs:
            return ()
        spec = specs[0]
        groups: dict[str, list[int]] = {}
        for index in indices:
            value = _text(self._rows[index].get(spec.key, ""))
            groups.setdefault(value, []).append(index)
        keys = sorted(groups, key=lambda value: value.casefold(), reverse=spec.descending)
        nodes = []
        for value in keys:
            child_indices = groups[value]
            nodes.append(
                GridGroupNode(
                    key=spec.key,
                    value=value,
                    level=level,
                    row_count=len(child_indices),
                    entity_ids=tuple(self._rows[index].entity_id for index in child_indices),
                    aggregates=self._aggregate(child_indices),
                    children=self._build_group_nodes(child_indices, specs[1:], level=level + 1),
                )
            )
        return tuple(nodes)

    def execute(self, query: GridQuery | None = None) -> GridQueryResult:
        query = query or GridQuery()
        started = time.perf_counter()
        tokens = tuple(dict.fromkeys(token.casefold() for token in query.text.split() if token.strip()))
        indices: list[int] = []
        for index, row in enumerate(self._rows):
            if not self._matches_scope(row, query.scope):
                continue
            if tokens and any(token not in row.search_text for token in tokens):
                continue
            if any(not self._matches_filter(row, rule) for rule in query.filters):
                continue
            indices.append(index)
        self._sort_indices(indices, query.sorts)
        groups = self._build_group_nodes(indices, query.groups)
        footer = GridFooter(len(indices), self._aggregate(indices))
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return GridQueryResult(self, tuple(indices), groups, footer, query, elapsed_ms)

    # ------------------------------------------------------------------
    # V3/V4 compatibility helpers
    # ------------------------------------------------------------------
    def query(
        self,
        text: str = "",
        *,
        filters: dict[str, Any] | None = None,
        sort_by: str = "part_position",
        descending: bool = False,
    ) -> tuple[GridRow, ...]:
        rules = tuple(GridFilter(key, FilterOperator.EQ, value) for key, value in (filters or {}).items())
        result = self.execute(GridQuery(text=text, filters=rules, sorts=(GridSort(sort_by, descending),)))
        return result.rows

    def groups(self, key: str, rows: Iterable[GridRow] | None = None) -> dict[str, tuple[GridRow, ...]]:
        out: dict[str, list[GridRow]] = {}
        for row in rows or self._rows:
            out.setdefault(_text(row.get(key, "")), []).append(row)
        return {name: tuple(values) for name, values in sorted(out.items(), key=lambda item: item[0].casefold())}

    def layout(self, name: str = "Standaard") -> GridLayout:
        return GridLayout(name=name, columns=self.columns)

    def apply_layout(self, layout: GridLayout) -> tuple[GridColumn, ...]:
        known = self._column_by_key
        loaded: list[GridColumn] = []
        seen: set[str] = set()
        for column in layout.columns:
            if column.key not in known or column.key in seen:
                continue
            base = known[column.key]
            loaded.append(
                GridColumn(
                    key=base.key,
                    label=column.label or base.label,
                    width=max(40, column.width),
                    visible=column.visible,
                    order=column.order,
                    data_type=base.data_type,
                    aggregate=base.aggregate,
                    sortable=base.sortable,
                    filterable=base.filterable,
                    groupable=base.groupable,
                    frozen=column.frozen,
                    number_format=base.number_format,
                    unit=base.unit,
                    source=base.source,
                )
            )
            seen.add(column.key)
        for base in self.columns:
            if base.key not in seen:
                loaded.append(GridColumn.from_dict({**base.to_dict(), "order": len(loaded)}))
        self.columns = tuple(sorted(loaded, key=lambda item: (item.order, item.key)))
        self._column_by_key = {item.key: item for item in self.columns}
        return self.columns

    def save_layout(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.layout().to_dict()
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
        return path

    def load_layout(self, path: str | Path) -> tuple[GridColumn, ...]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        # Legacy V4 layout was just a column list.
        if isinstance(data, list):
            data = {
                "schema_version": "cws-grid-layout-1.0",
                "name": "Legacy",
                "columns": data,
            }
        return self.apply_layout(GridLayout.from_dict(data))

    def set_columns(self, columns: Iterable[GridColumn]) -> tuple[GridColumn, ...]:
        values = tuple(columns)
        keys = [column.key for column in values]
        if len(keys) != len(set(keys)):
            raise ValueError("Dubbele gridkolom")
        self.columns = tuple(sorted(values, key=lambda item: (item.order, item.key)))
        self._column_by_key = {item.key: item for item in self.columns}
        return self.columns


__all__ = [
    "AggregateKind",
    "ColumnType",
    "FilterOperator",
    "GridAggregate",
    "GridColumn",
    "GridFilter",
    "GridFooter",
    "GridGroupNode",
    "GridGroupSpec",
    "GridLayout",
    "GridQuery",
    "GridQueryResult",
    "GridRow",
    "GridScope",
    "GridScopeState",
    "GridSort",
    "ProjectGridModel",
]
