"""Backend-neutral tree/grid/3D interaction bridge for Viewer V3.

The bridge contains no Qt/VTK objects.  It translates stable project entity IDs
and scene node IDs, forwards tree/grid selections to :class:`ViewerCoreController`,
and mirrors renderer selection events back to UI observers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from cws_viewer.contracts.enums import ColorScheme
from cws_viewer.contracts.events import SelectionChanged, Subscription
from cws_viewer.accuracy import AccuracyRecord, ViewerAccuracyProvider
from cws_viewer.core.color_schemes import ColorLegendItem, ProjectColorizer
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.properties import ProjectGridModel, ProjectPropertyProvider, PropertyRecord
from cws_viewer.search import SearchHit, ViewerSearchIndex


@dataclass(frozen=True, slots=True)
class InteractionSelection:
    node_ids: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    primary_node_id: str | None = None
    primary_entity_id: str | None = None
    origin: str = "viewer"


class ProjectInteractionModel:
    """Synchronise project tree, grid and 3D selection using stable IDs."""

    def __init__(
        self,
        controller: ViewerCoreController,
        project: object,
        *,
        mesh_repository: object | None = None,
    ) -> None:
        self.controller = controller
        self.project = project
        self.search_index = ViewerSearchIndex(controller.index.scene, project)
        self.property_provider = ProjectPropertyProvider(project)
        self.grid_model = ProjectGridModel(project)
        self.colorizer = ProjectColorizer(project, controller.index)
        self.accuracy_provider = ViewerAccuracyProvider(
            controller.index, project, mesh_repository
        )
        self._listeners: list[Callable[[InteractionSelection], None]] = []
        self._node_by_entity = {node.entity_id: node.node_id for node in controller.index.scene.nodes}
        self._origin = "viewer"
        self._selection = InteractionSelection()
        self._subscription: Subscription = controller.subscribe(
            SelectionChanged, self._on_selection_changed
        )

    @property
    def selection(self) -> InteractionSelection:
        return self._selection

    def subscribe(self, listener: Callable[[InteractionSelection], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    def _on_selection_changed(self, event: SelectionChanged) -> None:
        selection = event.selection
        node_ids = () if selection is None else tuple(selection.node_ids)
        entity_ids = () if selection is None else tuple(selection.entity_ids)
        primary_node = None if selection is None else selection.primary_node_id
        primary_entity = None
        if primary_node is not None:
            primary_entity = self.controller.index.node(primary_node).entity_id
        current = InteractionSelection(
            node_ids=node_ids,
            entity_ids=entity_ids,
            primary_node_id=primary_node,
            primary_entity_id=primary_entity,
            origin=self._origin,
        )
        self._selection = current
        for listener in tuple(self._listeners):
            listener(current)
        self._origin = "viewer"

    def node_for_entity(self, entity_id: str) -> str:
        hit = self._node_by_entity.get(str(entity_id))
        if hit is None:
            raise KeyError(entity_id)
        return hit

    def select_nodes(
        self, node_ids: Iterable[str], *, origin: str = "tree", mode: str = "replace"
    ) -> None:
        self._origin = str(origin or "tree")
        self.controller.set_selection(tuple(node_ids), mode=mode)

    def select_entities(
        self, entity_ids: Iterable[str], *, origin: str = "grid", mode: str = "replace"
    ) -> None:
        nodes = tuple(self.node_for_entity(entity_id) for entity_id in entity_ids)
        self.select_nodes(nodes, origin=origin, mode=mode)

    def search(self, query: str, *, limit: int = 200) -> tuple[SearchHit, ...]:
        return self.search_index.search(query, limit=limit)

    def select_search_hit(self, hit: SearchHit, *, mode: str = "replace") -> None:
        self.select_nodes((hit.node_id,), origin="search", mode=mode)

    def properties_for_primary(self) -> tuple[PropertyRecord, ...]:
        if self._selection.primary_entity_id is None:
            return ()
        try:
            return self.property_provider.records(self._selection.primary_entity_id)
        except KeyError:
            return ()


    def apply_color_scheme(self, scheme: ColorScheme) -> tuple[ColorLegendItem, ...]:
        requested = ColorScheme(scheme)
        self.controller.clear_colors()
        if requested != ColorScheme.ORIGINAL:
            self.controller.colorize(self.colorizer.assignments(requested))
        self.controller.set_color_scheme(requested)
        return self.colorizer.legend(requested)

    def accuracy_for_primary(self) -> AccuracyRecord | None:
        if self._selection.primary_node_id is None:
            return None
        return self.accuracy_provider.record(self._selection.primary_node_id)

    def close(self) -> None:
        self._subscription.close()
        self._listeners.clear()


__all__ = ["InteractionSelection", "ProjectInteractionModel"]
