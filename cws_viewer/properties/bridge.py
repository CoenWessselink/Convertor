"""Bidirectional grid/tree/3D selection and deterministic grid colour bridge."""
from __future__ import annotations

import hashlib
from typing import Iterable

from cws_viewer.contracts.state import ColorAssignment
from cws_viewer.math3d import Rgba
from .grid import GridQueryResult, ProjectGridModel


_PALETTE = (
    Rgba(0.18, 0.55, 0.82, 1.0),
    Rgba(0.20, 0.72, 0.48, 1.0),
    Rgba(0.95, 0.58, 0.18, 1.0),
    Rgba(0.73, 0.35, 0.83, 1.0),
    Rgba(0.87, 0.28, 0.32, 1.0),
    Rgba(0.16, 0.70, 0.72, 1.0),
    Rgba(0.58, 0.68, 0.20, 1.0),
    Rgba(0.83, 0.44, 0.67, 1.0),
    Rgba(0.48, 0.57, 0.68, 1.0),
    Rgba(0.93, 0.76, 0.20, 1.0),
)

_STATUS_COLOURS = {
    "validated": Rgba(0.18, 0.72, 0.42, 1.0),
    "released": Rgba(0.12, 0.64, 0.36, 1.0),
    "unchanged": Rgba(0.46, 0.53, 0.61, 1.0),
    "moved": Rgba(0.20, 0.58, 0.96, 1.0),
    "changed": Rgba(1.00, 0.56, 0.08, 1.0),
    "added": Rgba(0.17, 0.82, 0.42, 1.0),
    "removed": Rgba(0.92, 0.20, 0.22, 1.0),
    "ambiguous": Rgba(0.82, 0.20, 0.86, 1.0),
    "blocked": Rgba(0.92, 0.20, 0.22, 1.0),
    "review_required": Rgba(1.00, 0.68, 0.12, 1.0),
    "unclassified": Rgba(1.00, 0.68, 0.12, 1.0),
}


def _colour_for(value: object) -> Rgba:
    text = str(value or "").strip().casefold()
    if text in _STATUS_COLOURS:
        return _STATUS_COLOURS[text]
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return _PALETTE[digest[0] % len(_PALETTE)]


class GridViewerBridge:
    """Synchronise stable canonical entity IDs with the viewer controller."""

    def __init__(self, interaction: object, model: ProjectGridModel) -> None:
        self.interaction = interaction
        self.model = model

    @property
    def controller(self):
        return getattr(self.interaction, "controller")

    def refresh_scope_state(self) -> None:
        index = self.controller.index
        visible_node_ids, _ghosted = self.controller.session.visible_and_ghosted(index)
        visible_entity_ids = tuple(index.node(node_id).entity_id for node_id in visible_node_ids)
        selection = getattr(self.interaction, "selection")
        self.model.set_scope_state(
            visible_entity_ids=visible_entity_ids,
            selected_entity_ids=getattr(selection, "entity_ids", ()),
        )

    def select_entities(self, entity_ids: Iterable[str], *, mode: str = "replace") -> None:
        values = tuple(dict.fromkeys(map(str, entity_ids)))
        getattr(self.interaction, "select_entities")(values, origin="property_grid", mode=mode)
        self.refresh_scope_state()

    def select_result_page(
        self,
        result: GridQueryResult,
        *,
        offset: int = 0,
        limit: int = 500,
        mode: str = "replace",
    ) -> tuple[str, ...]:
        entity_ids = tuple(row.entity_id for row in result.rows_page(offset, limit) if row.node_id)
        if entity_ids:
            self.select_entities(entity_ids, mode=mode)
        return entity_ids

    def isolate_result(self, result: GridQueryResult, *, ghost_context: bool = False) -> tuple[str, ...]:
        node_ids = tuple(row.node_id for row in result.iter_rows() if row.node_id)
        if node_ids:
            self.controller.isolate(node_ids, ghost_context=ghost_context)
            self.controller.fit_all()
        self.refresh_scope_state()
        return node_ids

    def colourize(self, result: GridQueryResult, column_key: str) -> dict[str, Rgba]:
        assignments = []
        legend: dict[str, Rgba] = {}
        for row in result.iter_rows():
            if not row.node_id:
                continue
            value = str(row.get(column_key, "") or "")
            colour = legend.setdefault(value, _colour_for(value))
            assignments.append(ColorAssignment(node_id=row.node_id, color=colour))
        self.controller.clear_colors()
        if assignments:
            self.controller.colorize(assignments)
        return legend

    def clear_colours(self) -> None:
        self.controller.clear_colors()


__all__ = ["GridViewerBridge"]
