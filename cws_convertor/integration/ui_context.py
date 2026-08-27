"""U3 single application context for the integrated CWS Convertor desktop.

This module is deliberately GUI-toolkit independent.  It owns no project data,
geometry or manufacturing evidence.  Instead it binds exactly one
:class:`IntegratedProjectWorkspace` to one application-wide selection stream so
Viewer, Part Workbench, Scribing, BOM and Export observe the same canonical
Project Model instance and the same stable-ID selection state.

The context also closes a V9 integration gap: identity-only selection intents
published by PDF/BOM/application bridges are mirrored back into the active
viewer interaction model.  Feature/subshape identity remains on the application
selection bus and no surface may use this context to bypass production gates.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from .selection import ApplicationSelection


U3_CONTEXT_SCHEMA = "cws-application-context-2.0"
U3_SAFETY_FLAGS = {
    "machine_observed_by_cws": False,
    "deployment_transport_authorized": False,
    "direct_machine_transfer": False,
    "machine_transfer_allowed": False,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


@dataclass(frozen=True, slots=True)
class ProjectContext:
    active_project_id: str = ""
    active_model_id: str = ""
    active_assembly_id: str = ""
    active_part_id: str = ""
    active_feature_id: str = ""


@dataclass(frozen=True, slots=True)
class SelectionContext:
    selected_entity_ids: tuple[str, ...] = ()
    selected_part_ids: tuple[str, ...] = ()
    selected_assembly_ids: tuple[str, ...] = ()
    selected_feature_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ViewerContext:
    camera_state: dict[str, Any] = field(default_factory=dict)
    camera_target: tuple[float, float, float] | None = None
    camera_pivot: tuple[float, float, float] | None = None
    camera_projection: str = "perspective"
    camera_history: tuple[dict[str, Any], ...] = ()
    visibility_state: dict[str, str] = field(default_factory=dict)
    hidden_entities: tuple[str, ...] = ()
    ghosted_entities: tuple[str, ...] = ()
    isolated_scope: tuple[str, ...] = ()
    transparency_overrides: dict[str, float] = field(default_factory=dict)
    section_planes: tuple[dict[str, Any], ...] = ()
    clipping_state: dict[str, Any] = field(default_factory=dict)
    clip_box: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    search_state: dict[str, Any] = field(default_factory=dict)
    active_filters: tuple[str, ...] = ()
    active_workspace: str = "start"
    workspace_history: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReviewContext:
    measurement_state: dict[str, Any] = field(default_factory=dict)
    markup_state: dict[str, Any] = field(default_factory=dict)
    saved_view_state: dict[str, Any] = field(default_factory=dict)
    saved_views: tuple[dict[str, Any], ...] = ()
    active_bom_row: str = ""
    active_bom_rows: tuple[str, ...] = ()
    active_scribing_mark: str = ""


@dataclass(frozen=True, slots=True)
class ManufacturingContext:
    active_ruleset_id: str = ""
    active_machine_profile_id: str = ""
    active_production_instance_id: str = ""
    active_sequence_id: str = ""
    overlay_layers: tuple[str, ...] = ()
    output_eligibility: dict[str, bool] = field(default_factory=dict)
    active_edit_transaction: str = ""
    active_nesting_run: str = ""


@dataclass(frozen=True, slots=True)
class ExportContext:
    active_export_scope: tuple[str, ...] = ()
    active_release_scope: tuple[str, ...] = ()
    filters: dict[str, str] = field(default_factory=dict)
    grouping: str = "combined"
    formats: tuple[str, ...] = ()
    naming_template: str = "{project}_{scope}_{revision}"
    preflight_hash: str = ""
    package_manifest_hash: str = ""


def _context_from_dict(context_type: type[Any], value: Any) -> Any:
    source = dict(value or {}) if isinstance(value, dict) else {}
    tuple_fields = {
        "selected_entity_ids", "selected_part_ids", "selected_assembly_ids",
        "selected_feature_ids", "camera_history", "hidden_entities",
        "ghosted_entities", "isolated_scope", "section_planes", "active_filters",
        "workspace_history", "saved_views", "active_bom_rows", "active_export_scope",
        "active_release_scope", "overlay_layers", "formats",
    }
    for name in tuple_fields.intersection(source):
        source[name] = tuple(source[name] or ())
    if source.get("camera_target") is not None:
        source["camera_target"] = tuple(source["camera_target"])
    if source.get("camera_pivot") is not None:
        source["camera_pivot"] = tuple(source["camera_pivot"])
    allowed = set(context_type.__dataclass_fields__)
    return context_type(**{key: deepcopy(value) for key, value in source.items() if key in allowed})


def migrate_context_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy U3 snapshots without treating transient UI state as project data."""

    source = deepcopy(dict(payload or {}))
    schema = str(source.get("schema") or "cws-unified-ui-context-1.0")
    if schema == U3_CONTEXT_SCHEMA:
        return source
    selection = dict(source.get("selection") or {})
    entity_ids = tuple(selection.get("entity_ids") or ())
    feature_id = str(selection.get("feature_id") or "")
    source.update(
        {
            "schema": U3_CONTEXT_SCHEMA,
            "project_context": {
                "active_project_id": str(source.get("project_id") or ""),
                "active_feature_id": feature_id,
            },
            "selection_context": {
                "selected_entity_ids": list(entity_ids),
                "selected_feature_ids": [feature_id] if feature_id else [],
            },
            "viewer_context": {},
            "workspace_context": {
                "active_workspace": str(source.get("active_surface") or "start"),
                "workspace_history": [str(source.get("active_surface") or "start")],
            },
            "review_context": {},
            "manufacturing_context": {},
            "export_context": {},
        }
    )
    return source


@dataclass(frozen=True, slots=True)
class UnifiedUiContextSnapshot:
    """Immutable status record distributed to all U3 application surfaces."""

    generation: int
    active_surface: str
    selection: ApplicationSelection
    project_attached: bool = False
    project_id: str = ""
    project_name: str = ""
    project_path: str = ""
    project_schema: str = ""
    integrity_blocking_codes: tuple[str, ...] = ()
    project_context: ProjectContext = field(default_factory=ProjectContext)
    selection_context: SelectionContext = field(default_factory=SelectionContext)
    viewer_context: ViewerContext = field(default_factory=ViewerContext)
    workspace_context: WorkspaceContext = field(default_factory=WorkspaceContext)
    review_context: ReviewContext = field(default_factory=ReviewContext)
    manufacturing_context: ManufacturingContext = field(default_factory=ManufacturingContext)
    export_context: ExportContext = field(default_factory=ExportContext)
    changed_at: str = field(default_factory=_utc_now)

    @property
    def consistent(self) -> bool:
        return not self.integrity_blocking_codes

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": U3_CONTEXT_SCHEMA,
            "generation": self.generation,
            "active_surface": self.active_surface,
            "project_attached": self.project_attached,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_path": self.project_path,
            "project_schema": self.project_schema,
            "selection": self.selection.to_dict(),
            "integrity_blocking_codes": list(self.integrity_blocking_codes),
            "project_context": asdict(self.project_context),
            "selection_context": asdict(self.selection_context),
            "viewer_context": asdict(self.viewer_context),
            "workspace_context": asdict(self.workspace_context),
            "review_context": asdict(self.review_context),
            "manufacturing_context": asdict(self.manufacturing_context),
            "export_context": asdict(self.export_context),
            "consistent": self.consistent,
            "safety": dict(U3_SAFETY_FLAGS),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode(
            "utf-8"
        )
        payload["state_hash"] = sha256(encoded).hexdigest()
        payload["changed_at"] = self.changed_at
        return payload

    @property
    def state_hash(self) -> str:
        return str(self.to_dict()["state_hash"])

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UnifiedUiContextSnapshot":
        source = migrate_context_payload(payload)
        return cls(
            generation=int(source.get("generation") or 0),
            active_surface=str(source.get("active_surface") or "start"),
            selection=ApplicationSelection.from_dict(dict(source.get("selection") or {})),
            project_attached=bool(source.get("project_attached")),
            project_id=str(source.get("project_id") or ""),
            project_name=str(source.get("project_name") or ""),
            project_path=str(source.get("project_path") or ""),
            project_schema=str(source.get("project_schema") or ""),
            integrity_blocking_codes=tuple(source.get("integrity_blocking_codes") or ()),
            project_context=_context_from_dict(ProjectContext, source.get("project_context")),
            selection_context=_context_from_dict(SelectionContext, source.get("selection_context")),
            viewer_context=_context_from_dict(ViewerContext, source.get("viewer_context")),
            workspace_context=_context_from_dict(WorkspaceContext, source.get("workspace_context")),
            review_context=_context_from_dict(ReviewContext, source.get("review_context")),
            manufacturing_context=_context_from_dict(ManufacturingContext, source.get("manufacturing_context")),
            export_context=_context_from_dict(ExportContext, source.get("export_context")),
            changed_at=str(source.get("changed_at") or _utc_now()),
        )


class UnifiedApplicationContext:
    """Single project + selection authority for the U3 desktop composition.

    The context never clones a project.  ``workspace.project`` must be the same
    object as ``workspace.session.project`` and ``workspace.load_result.project``.
    Selection traffic contains only canonical stable IDs.  A direct application
    bridge publication (for example PDF feature highlight) is synchronized into
    the viewer interaction model while preserving feature/subshape identity on
    the application selection bus.
    """

    def __init__(self, *, active_surface: str = "start") -> None:
        from cws_convertor.project.jobs import JobManager

        self._workspace: Any | None = None
        self._workspace_unsubscribe: Callable[[], None] | None = None
        self._listeners: list[Callable[[UnifiedUiContextSnapshot], None]] = []
        self._selection = ApplicationSelection(origin="u3_context")
        self._active_surface = str(active_surface or "start")
        self.job_manager = JobManager(max_workers=2)
        self._project_context = ProjectContext()
        self._selection_context = SelectionContext()
        self._viewer_context = ViewerContext()
        self._workspace_context = WorkspaceContext(
            active_workspace=self._active_surface,
            workspace_history=(self._active_surface,),
        )
        self._review_context = ReviewContext()
        self._manufacturing_context = ManufacturingContext()
        self._export_context = ExportContext()
        self._user_preferences: dict[str, Any] = {}
        self._generation = 0
        self._syncing_interaction = False
        self._snapshot = self._build_snapshot()

    @property
    def workspace(self) -> Any | None:
        return self._workspace

    @property
    def selection(self) -> ApplicationSelection:
        return self._selection

    @property
    def active_surface(self) -> str:
        return self._active_surface

    @property
    def snapshot(self) -> UnifiedUiContextSnapshot:
        return self._snapshot

    def subscribe(
        self,
        listener: Callable[[UnifiedUiContextSnapshot], None],
        *,
        emit_current: bool = True,
    ) -> Callable[[], None]:
        self._listeners.append(listener)
        if emit_current:
            listener(self._snapshot)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    def attach_workspace(self, workspace: Any) -> UnifiedUiContextSnapshot:
        if workspace is self._workspace:
            return self._snapshot
        self.detach_workspace(emit=False)
        blocking = self._workspace_identity_blocking_codes(workspace)
        if blocking:
            raise RuntimeError(
                "U3 application context weigert niet-canonieke workspace: " + ", ".join(blocking)
            )
        self._workspace = workspace
        self._workspace_unsubscribe = workspace.selection_bus.subscribe(self._on_bus_selection)
        current = workspace.selection_bus.selection
        if not current.entity_ids:
            interaction_selection = getattr(workspace.interaction, "selection", None)
            entity_ids = tuple(getattr(interaction_selection, "entity_ids", ()) or ())
            if entity_ids:
                current = ApplicationSelection(
                    entity_ids=_unique(entity_ids),
                    primary_entity_id=str(
                        getattr(interaction_selection, "primary_entity_id", "") or entity_ids[0]
                    ),
                    origin=str(getattr(interaction_selection, "origin", "u3_attach") or "u3_attach"),
                )
        self._selection = current
        return self._publish_snapshot()

    def detach_workspace(
        self,
        *,
        expected_workspace: Any | None = None,
        emit: bool = True,
    ) -> UnifiedUiContextSnapshot:
        if expected_workspace is not None and self._workspace is not expected_workspace:
            return self._snapshot
        if self._workspace_unsubscribe is not None:
            self._workspace_unsubscribe()
            self._workspace_unsubscribe = None
        self._workspace = None
        self._selection = ApplicationSelection(origin="u3_detach")
        if emit:
            return self._publish_snapshot()
        self._snapshot = self._build_snapshot()
        return self._snapshot

    def set_active_surface(self, surface: str) -> UnifiedUiContextSnapshot:
        value = str(surface or "viewer").strip().lower().replace(" / ", "_").replace(" ", "_")
        if value == self._active_surface:
            return self._snapshot
        self._active_surface = value
        history = (*self._workspace_context.workspace_history, value)
        self._workspace_context = replace(
            self._workspace_context,
            active_workspace=value,
            workspace_history=history[-100:],
        )
        return self._publish_snapshot()

    def update_viewer_context(self, **changes: Any) -> UnifiedUiContextSnapshot:
        self._viewer_context = replace(self._viewer_context, **changes)
        return self._publish_snapshot()

    def update_workspace_context(self, **changes: Any) -> UnifiedUiContextSnapshot:
        self._workspace_context = replace(self._workspace_context, **changes)
        self._active_surface = self._workspace_context.active_workspace
        return self._publish_snapshot()

    def update_review_context(self, **changes: Any) -> UnifiedUiContextSnapshot:
        self._review_context = replace(self._review_context, **changes)
        return self._publish_snapshot()

    def update_manufacturing_context(self, **changes: Any) -> UnifiedUiContextSnapshot:
        self._manufacturing_context = replace(self._manufacturing_context, **changes)
        return self._publish_snapshot()

    def update_export_context(self, **changes: Any) -> UnifiedUiContextSnapshot:
        self._export_context = replace(self._export_context, **changes)
        return self._publish_snapshot()

    def serialize_state(self) -> dict[str, Any]:
        return {
            "schema": U3_CONTEXT_SCHEMA,
            "snapshot": self._snapshot.to_dict(),
            "user_preferences": deepcopy(self._user_preferences),
        }

    def restore_state(self, payload: dict[str, Any]) -> UnifiedUiContextSnapshot:
        source = dict(payload or {})
        snapshot = UnifiedUiContextSnapshot.from_dict(
            dict(source.get("snapshot") or source)
        )
        self._active_surface = snapshot.active_surface
        self._project_context = snapshot.project_context
        self._selection_context = snapshot.selection_context
        self._viewer_context = snapshot.viewer_context
        self._workspace_context = snapshot.workspace_context
        self._review_context = snapshot.review_context
        self._manufacturing_context = snapshot.manufacturing_context
        self._export_context = snapshot.export_context
        self._user_preferences = deepcopy(dict(source.get("user_preferences") or {}))
        return self._publish_snapshot()

    def close(self) -> None:
        self.job_manager.shutdown(wait=False, cancel_pending=True)

    def ingest_interaction_selection(self, selection: Any | None) -> UnifiedUiContextSnapshot:
        """Normalize legacy ProjectInteraction signals into the U3 selection bus."""
        if self._workspace is None:
            self._selection = ApplicationSelection(origin="u3_no_project")
            return self._publish_snapshot()
        if selection is None:
            return self.request_selection((), origin="u3_interaction_clear")
        entity_ids = _unique(getattr(selection, "entity_ids", ()) or ())
        primary = str(getattr(selection, "primary_entity_id", "") or "") or None
        origin = str(getattr(selection, "origin", "interaction") or "interaction")
        bus_selection = self._workspace.selection_bus.publish(
            entity_ids,
            primary_entity_id=primary,
            origin=origin,
        )
        # Exact echoes are intentionally not re-emitted by the bus.  Ensure the
        # context still reflects the interaction if this was the first binding.
        if self._selection.entity_ids != bus_selection.entity_ids:
            self._selection = bus_selection
            return self._publish_snapshot()
        return self._snapshot

    def request_selection(
        self,
        entity_ids: Iterable[str] = (),
        *,
        primary_entity_id: str | None = None,
        feature_id: str | None = None,
        subshape_id: str | None = None,
        origin: str = "application",
        mode: str = "replace",
    ) -> UnifiedUiContextSnapshot:
        if self._workspace is None:
            raise RuntimeError("Geen actief CWS-project in U3 application context")
        values = _unique(entity_ids)
        canonical_ids = self._canonical_entity_ids(self._workspace)
        unknown = tuple(value for value in values if value not in canonical_ids)
        if unknown:
            raise KeyError(f"Niet-canonieke selectie-ID(s): {', '.join(unknown)}")
        if primary_entity_id and str(primary_entity_id) not in canonical_ids:
            raise KeyError(f"Niet-canonieke primary selection-ID: {primary_entity_id}")
        self._workspace.select_entities(
            values,
            origin=str(origin or "application"),
            mode=mode,
            feature_id=feature_id,
            subshape_id=subshape_id,
        )
        # ``workspace.select_entities`` publishes a second, richer bus record
        # after synchronizing the interaction/controller.  Use the final bus
        # state as the application truth.
        self._selection = self._workspace.selection_bus.selection
        return self._publish_snapshot_if_changed()

    def clear_selection(self, *, origin: str = "application") -> UnifiedUiContextSnapshot:
        return self.request_selection((), origin=origin)

    def integrity_blocking_codes(self) -> tuple[str, ...]:
        workspace = self._workspace
        if workspace is None:
            return ()
        blocking = list(self._workspace_identity_blocking_codes(workspace))
        canonical_ids = self._canonical_entity_ids(workspace)
        unknown = tuple(value for value in self._selection.entity_ids if value not in canonical_ids)
        if unknown:
            blocking.append("U3_SELECTION_NON_CANONICAL")
        interaction_ids = tuple(getattr(workspace.interaction.selection, "entity_ids", ()) or ())
        if tuple(self._selection.entity_ids) != interaction_ids:
            blocking.append("U3_SELECTION_INTERACTION_DRIFT")
        if any(U3_SAFETY_FLAGS.values()):
            blocking.append("U3_MACHINE_TRANSFER_BOUNDARY_OPEN")
        return tuple(dict.fromkeys(blocking))

    def assert_consistent(self) -> None:
        blocking = self.integrity_blocking_codes()
        if blocking:
            raise RuntimeError("U3 context inconsistent: " + ", ".join(blocking))

    def _on_bus_selection(self, selection: ApplicationSelection) -> None:
        workspace = self._workspace
        if workspace is None:
            return
        canonical_ids = self._canonical_entity_ids(workspace)
        unknown = tuple(value for value in selection.entity_ids if value not in canonical_ids)
        if unknown:
            # Fail closed: never mirror a non-canonical stable ID into the
            # renderer.  Keep the invalid selection visible as an integrity
            # failure rather than silently widening/replacing it.
            self._selection = selection
            self._publish_snapshot()
            return

        interaction_ids = tuple(getattr(workspace.interaction.selection, "entity_ids", ()) or ())
        requested_ids = tuple(selection.entity_ids)
        if requested_ids != interaction_ids and not self._syncing_interaction:
            self._syncing_interaction = True
            try:
                if requested_ids:
                    workspace.interaction.select_entities(
                        requested_ids,
                        origin=f"u3_context:{selection.origin}",
                    )
                else:
                    workspace.controller.clear_selection()
                # The interaction mirror has no feature/subshape fields.  The
                # outer ApplicationSelectionBus publication is re-entrant safe,
                # so restore the richer application intent before it unwinds.
                workspace.selection_bus.publish(
                    requested_ids,
                    primary_entity_id=selection.primary_entity_id,
                    feature_id=selection.feature_id,
                    subshape_id=selection.subshape_id,
                    origin=selection.origin,
                )
            finally:
                self._syncing_interaction = False
        self._selection = selection
        self._publish_snapshot_if_changed(force=True)

    @staticmethod
    def _workspace_identity_blocking_codes(workspace: Any) -> tuple[str, ...]:
        blocking: list[str] = []
        project = getattr(workspace, "project", None)
        session = getattr(workspace, "session", None)
        load_result = getattr(workspace, "load_result", None)
        if project is None or session is None:
            blocking.append("U3_WORKSPACE_PROJECT_MISSING")
        else:
            if getattr(session, "project", None) is not project:
                blocking.append("U3_SESSION_PROJECT_IDENTITY_DRIFT")
            if load_result is None or getattr(load_result, "project", None) is not project:
                blocking.append("U3_VIEWER_PROJECT_IDENTITY_DRIFT")
        identity_audit = getattr(workspace, "identity_audit", None)
        if identity_audit is not None and not bool(getattr(identity_audit, "passed", False)):
            blocking.append("U3_IDENTITY_AUDIT_FAILED")
        return tuple(blocking)

    @staticmethod
    def _canonical_entity_ids(workspace: Any) -> set[str]:
        project = workspace.project
        result: set[str] = set()
        for collection_name in ("assemblies", "parts", "purchased_items", "fasteners", "welds"):
            collection = getattr(project, collection_name, {})
            result.update(str(value) for value in collection)
        return result

    def _build_snapshot(self) -> UnifiedUiContextSnapshot:
        workspace = self._workspace
        if workspace is None:
            return UnifiedUiContextSnapshot(
                generation=self._generation,
                active_surface=self._active_surface,
                selection=self._selection,
                project_context=self._project_context,
                selection_context=self._selection_context,
                viewer_context=self._viewer_context,
                workspace_context=self._workspace_context,
                review_context=self._review_context,
                manufacturing_context=self._manufacturing_context,
                export_context=self._export_context,
            )
        project = workspace.project
        entity_ids = tuple(self._selection.entity_ids)
        part_ids = tuple(value for value in entity_ids if value in project.parts)
        assembly_ids = tuple(value for value in entity_ids if value in project.assemblies)
        primary = self._selection.primary_entity_id
        self._project_context = replace(
            self._project_context,
            active_project_id=str(getattr(project, "project_id", "") or ""),
            active_model_id=str(getattr(project, "project_id", "") or ""),
            active_assembly_id=primary if primary in project.assemblies else (assembly_ids[0] if assembly_ids else ""),
            active_part_id=primary if primary in project.parts else (part_ids[0] if part_ids else ""),
            active_feature_id=str(self._selection.feature_id or ""),
        )
        self._selection_context = SelectionContext(
            selected_entity_ids=entity_ids,
            selected_part_ids=part_ids,
            selected_assembly_ids=assembly_ids,
            selected_feature_ids=(str(self._selection.feature_id),) if self._selection.feature_id else (),
        )
        project_path = getattr(workspace, "project_path", "")
        return UnifiedUiContextSnapshot(
            generation=self._generation,
            active_surface=self._active_surface,
            selection=self._selection,
            project_attached=True,
            project_id=str(getattr(project, "project_id", "") or ""),
            project_name=str(getattr(project, "project_name", "") or ""),
            project_path=str(Path(project_path)) if project_path else "",
            project_schema=str(getattr(project, "schema_version", "") or ""),
            integrity_blocking_codes=self.integrity_blocking_codes(),
            project_context=self._project_context,
            selection_context=self._selection_context,
            viewer_context=self._viewer_context,
            workspace_context=self._workspace_context,
            review_context=self._review_context,
            manufacturing_context=self._manufacturing_context,
            export_context=self._export_context,
        )

    def _publish_snapshot(self) -> UnifiedUiContextSnapshot:
        self._generation += 1
        self._snapshot = self._build_snapshot()
        for listener in tuple(self._listeners):
            listener(self._snapshot)
        return self._snapshot

    def _publish_snapshot_if_changed(self, *, force: bool = False) -> UnifiedUiContextSnapshot:
        previous = self._snapshot
        candidate = self._build_snapshot()
        same = (
            previous.active_surface == candidate.active_surface
            and previous.project_attached == candidate.project_attached
            and previous.project_id == candidate.project_id
            and previous.project_path == candidate.project_path
            and previous.selection.entity_ids == candidate.selection.entity_ids
            and previous.selection.primary_entity_id == candidate.selection.primary_entity_id
            and previous.selection.feature_id == candidate.selection.feature_id
            and previous.selection.subshape_id == candidate.selection.subshape_id
            and previous.selection.origin == candidate.selection.origin
            and previous.integrity_blocking_codes == candidate.integrity_blocking_codes
        )
        if same and not force:
            return previous
        return self._publish_snapshot()


__all__ = [
    "ExportContext",
    "ManufacturingContext",
    "ProjectContext",
    "ReviewContext",
    "SelectionContext",
    "U3_CONTEXT_SCHEMA",
    "U3_SAFETY_FLAGS",
    "UnifiedApplicationContext",
    "UnifiedUiContextSnapshot",
    "ViewerContext",
    "WorkspaceContext",
    "migrate_context_payload",
]
