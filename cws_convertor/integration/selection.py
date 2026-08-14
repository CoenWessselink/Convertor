"""Application-wide stable-ID selection bridges for CWS Convertor V9.

The selection bus deliberately transports only canonical entity/feature IDs.
It never transports toolkit objects, triangles, BREP handles or mutable project
entities.  Tree, grid, BOM, PDF review and the Exact Part Workbench therefore
remain coupled to the same Canonical Project Model without becoming a second
source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


@dataclass(frozen=True, slots=True)
class ApplicationSelection:
    entity_ids: tuple[str, ...] = ()
    primary_entity_id: str | None = None
    feature_id: str | None = None
    subshape_id: str | None = None
    origin: str = "application"
    changed_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-application-selection-1.0",
            "entity_ids": list(self.entity_ids),
            "primary_entity_id": self.primary_entity_id or "",
            "feature_id": self.feature_id or "",
            "subshape_id": self.subshape_id or "",
            "origin": self.origin,
            "changed_at": self.changed_at,
        }


class ApplicationSelectionBus:
    """Re-entrancy-safe application selection bus using stable canonical IDs."""

    def __init__(self) -> None:
        self._selection = ApplicationSelection()
        self._listeners: list[Callable[[ApplicationSelection], None]] = []
        self._publishing = False

    @property
    def selection(self) -> ApplicationSelection:
        return self._selection

    def subscribe(self, listener: Callable[[ApplicationSelection], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    def publish(
        self,
        entity_ids: Iterable[str] = (),
        *,
        primary_entity_id: str | None = None,
        feature_id: str | None = None,
        subshape_id: str | None = None,
        origin: str = "application",
    ) -> ApplicationSelection:
        values = _unique(entity_ids)
        primary = str(primary_entity_id) if primary_entity_id else (values[0] if values else None)
        if primary and primary not in values:
            values = (primary, *values)
        next_selection = ApplicationSelection(
            entity_ids=values,
            primary_entity_id=primary,
            feature_id=str(feature_id) if feature_id else None,
            subshape_id=str(subshape_id) if subshape_id else None,
            origin=str(origin or "application"),
        )
        # Ignore exact echoes.  This prevents tree -> viewer -> tree feedback.
        current = self._selection
        if (
            current.entity_ids == next_selection.entity_ids
            and current.primary_entity_id == next_selection.primary_entity_id
            and current.feature_id == next_selection.feature_id
            and current.subshape_id == next_selection.subshape_id
            and current.origin == next_selection.origin
        ):
            return current
        self._selection = next_selection
        if self._publishing:
            return next_selection
        self._publishing = True
        try:
            for listener in tuple(self._listeners):
                listener(next_selection)
        finally:
            self._publishing = False
        return next_selection


@dataclass(frozen=True, slots=True)
class BomSelectionRecord:
    entity_id: str
    entity_type: str
    group_id: str
    part_position: str = ""
    assembly_mark: str = ""


class BomSelectionIndex:
    """Traceability index linking BOM groups and canonical entity IDs."""

    def __init__(self, snapshot: Any) -> None:
        records: list[BomSelectionRecord] = []
        for row in getattr(snapshot, "traceability", ()):
            records.append(
                BomSelectionRecord(
                    entity_id=str(row.get("internal_id") or ""),
                    entity_type=str(row.get("entity_type") or ""),
                    group_id=str(row.get("group_id") or ""),
                    part_position=str(row.get("part_position") or ""),
                    assembly_mark=str(row.get("assembly_mark") or ""),
                )
            )
        self.records = tuple(item for item in records if item.entity_id)
        self._by_entity = {item.entity_id: item for item in self.records}
        groups: dict[str, list[str]] = {}
        for item in self.records:
            if item.group_id:
                groups.setdefault(item.group_id, []).append(item.entity_id)
        self._entities_by_group = {
            key: tuple(dict.fromkeys(values)) for key, values in groups.items()
        }

    def record(self, entity_id: str) -> BomSelectionRecord | None:
        return self._by_entity.get(str(entity_id))

    def group_for_entity(self, entity_id: str) -> str | None:
        record = self.record(entity_id)
        return record.group_id if record and record.group_id else None

    def entities_for_group(self, group_id: str) -> tuple[str, ...]:
        return self._entities_by_group.get(str(group_id), ())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-v9-bom-selection-index-1.0",
            "record_count": len(self.records),
            "group_count": len(self._entities_by_group),
            "records": [
                {
                    "entity_id": item.entity_id,
                    "entity_type": item.entity_type,
                    "group_id": item.group_id,
                    "part_position": item.part_position,
                    "assembly_mark": item.assembly_mark,
                }
                for item in self.records
            ],
        }


class PdfFeatureHighlightBridge:
    """Stable-ID contract between PDF/drawing review and the 3D workbench.

    The bridge only publishes identity/highlight intent.  It cannot create or
    modify exact geometry and cannot change production release state.
    """

    def __init__(self, selection_bus: ApplicationSelectionBus) -> None:
        self.selection_bus = selection_bus

    def highlight_from_pdf(self, entity_id: str, feature_id: str) -> ApplicationSelection:
        return self.selection_bus.publish(
            (entity_id,),
            primary_entity_id=entity_id,
            feature_id=feature_id,
            origin="pdf",
        )

    def highlight_from_viewer(
        self,
        entity_id: str,
        *,
        feature_id: str | None = None,
        subshape_id: str | None = None,
    ) -> ApplicationSelection:
        return self.selection_bus.publish(
            (entity_id,),
            primary_entity_id=entity_id,
            feature_id=feature_id,
            subshape_id=subshape_id,
            origin="viewer",
        )


__all__ = [
    "ApplicationSelection",
    "ApplicationSelectionBus",
    "BomSelectionIndex",
    "BomSelectionRecord",
    "PdfFeatureHighlightBridge",
]
