"""Single-truth integration of CWS Project Model, Viewer, Grid, BOM and Workbench.

V9 is explicitly not a second importer or a second project database.  The
workspace opens one :class:`ProjectSession` and passes that exact in-memory
project object into the viewer scene adapter.  All downstream surfaces bind to
stable canonical entity IDs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import time
from typing import Any, Iterable

from canonical_model import write_attachment
from cws_convertor.bom import build_bom_snapshot
from cws_convertor.project.model import ProjectModel
from cws_convertor.project.service import ProjectSession
from cws_convertor.production_export.readiness import ReadinessGate
from cws_viewer.adapters.project_scene_loader import ProjectSceneLoadResult, ProjectSceneLoader
from cws_viewer.adapters.source_geometry import ProjectSourceResolver
from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.core.project_interaction import ProjectInteractionModel
from cws_viewer.exact.catalog import load_step_exact
from cws_viewer.exact.workbench import ExactPartWorkbenchService
from cws_viewer.properties import GridViewerBridge
from .selection import (
    ApplicationSelectionBus,
    BomSelectionIndex,
    PdfFeatureHighlightBridge,
)


@dataclass(frozen=True, slots=True)
class IdentityAuditReport:
    project_id: str
    canonical_entity_count: int
    scene_entity_count: int
    grid_entity_count: int
    bom_entity_count: int
    duplicate_scene_entity_ids: tuple[str, ...] = ()
    missing_in_scene: tuple[str, ...] = ()
    missing_in_grid: tuple[str, ...] = ()
    missing_in_bom: tuple[str, ...] = ()
    unexpected_scene_entities: tuple[str, ...] = ()
    project_object_identity_preserved: bool = False

    @property
    def passed(self) -> bool:
        return (
            self.project_object_identity_preserved
            and not self.duplicate_scene_entity_ids
            and not self.missing_in_scene
            and not self.missing_in_grid
            and not self.missing_in_bom
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-v9-identity-audit-1.0",
            "project_id": self.project_id,
            "passed": self.passed,
            "canonical_entity_count": self.canonical_entity_count,
            "scene_entity_count": self.scene_entity_count,
            "grid_entity_count": self.grid_entity_count,
            "bom_entity_count": self.bom_entity_count,
            "duplicate_scene_entity_ids": list(self.duplicate_scene_entity_ids),
            "missing_in_scene": list(self.missing_in_scene),
            "missing_in_grid": list(self.missing_in_grid),
            "missing_in_bom": list(self.missing_in_bom),
            "unexpected_scene_entities": list(self.unexpected_scene_entities),
            "project_object_identity_preserved": self.project_object_identity_preserved,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceLoadReport:
    project_path: Path
    project_id: str
    elapsed_seconds: float
    scene_nodes: int
    renderable_nodes: int
    grid_rows: int
    bom_traceability_rows: int
    unique_geometries: int
    proxy_geometries: int
    identity_audit: IdentityAuditReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-v9-integrated-workspace-load-1.0",
            "project_path": str(self.project_path),
            "project_id": self.project_id,
            "elapsed_seconds": self.elapsed_seconds,
            "scene_nodes": self.scene_nodes,
            "renderable_nodes": self.renderable_nodes,
            "grid_rows": self.grid_rows,
            "bom_traceability_rows": self.bom_traceability_rows,
            "unique_geometries": self.unique_geometries,
            "proxy_geometries": self.proxy_geometries,
            "identity_audit": self.identity_audit.to_dict(),
        }


@dataclass(slots=True)
class ExactPartOpenResult:
    entity_id: str
    status: str
    source_format: str
    source_path: Path | None = None
    service: ExactPartWorkbenchService | None = None
    blocking_codes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return self.service is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "status": self.status,
            "source_format": self.source_format,
            "source_path": str(self.source_path) if self.source_path else "",
            "available": self.available,
            "blocking_codes": list(self.blocking_codes),
            "notes": list(self.notes),
            "production_release_allowed": False,
        }


@dataclass(slots=True)
class IntegratedProjectWorkspace:
    """One canonical project bound to all V9 application surfaces."""

    session: ProjectSession
    load_result: ProjectSceneLoadResult
    controller: ViewerCoreController
    interaction: ProjectInteractionModel
    bridge: GridViewerBridge
    bom_snapshot: Any
    identity_audit: IdentityAuditReport
    report: WorkspaceLoadReport
    selection_bus: ApplicationSelectionBus
    bom_index: BomSelectionIndex
    pdf_bridge: PdfFeatureHighlightBridge
    _temporary_directory: tempfile.TemporaryDirectory[str] = field(repr=False)
    _interaction_unsubscribe: Any = field(repr=False, default=None)
    _owns_controller: bool = field(repr=False, default=True)

    @property
    def project(self) -> ProjectModel:
        return self.session.project

    @property
    def project_path(self) -> Path:
        assert self.session.path is not None
        return self.session.path

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        read_only: bool = False,
        cache_root: str | Path | None = None,
        source_search_roots: Iterable[str | Path] = (),
        load_all_geometry: bool = True,
        allow_proxy: bool = True,
    ) -> "IntegratedProjectWorkspace":
        started = time.perf_counter()
        project_path = Path(path).expanduser().resolve()
        session = ProjectSession.open(project_path, read_only=read_only)
        temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        controller: ViewerCoreController | None = None
        interaction: ProjectInteractionModel | None = None
        try:
            roots = list(source_search_roots)
            roots.extend(value.parent for value in session.source_paths.values())
            loader = ProjectSceneLoader(cache_root=cache_root, source_search_roots=roots)
            load_result = loader.load_project(
                session.project,
                project_path,
                load_all=load_all_geometry,
                allow_proxy=allow_proxy,
            )
            if load_result.project is not session.project:
                raise RuntimeError("Viewer heeft een tweede projectinstantie aangemaakt")

            backend = MemoryRenderBackend()
            controller = ViewerCoreController(backend)
            controller.load_scene(load_result.scene)
            interaction = ProjectInteractionModel(
                controller,
                session.project,
                mesh_repository=load_result.repository,
            )
            bridge = GridViewerBridge(interaction, interaction.grid_model)
            bridge.refresh_scope_state()
            selection_bus = ApplicationSelectionBus()
            interaction_unsubscribe = interaction.subscribe(
                lambda selection: selection_bus.publish(
                    selection.entity_ids,
                    primary_entity_id=selection.primary_entity_id,
                    origin=selection.origin,
                )
            )

            # BOM generation may classify/audit.  Run it on a detached snapshot
            # so the viewer opening a project can never mutate production state.
            bom_project = ProjectModel.from_dict(session.project.to_dict())
            bom_snapshot = build_bom_snapshot(bom_project, user="viewer-v9", classify_if_needed=True)
            cls._complete_bom_traceability(session.project, bom_snapshot)

            bom_index = BomSelectionIndex(bom_snapshot)
            pdf_bridge = PdfFeatureHighlightBridge(selection_bus)

            identity_audit = cls._audit_identity(
                session.project,
                load_result,
                interaction,
                bom_snapshot,
                project_object_identity_preserved=load_result.project is session.project,
            )
            if not identity_audit.passed:
                raise RuntimeError(f"V9 identity audit failed: {identity_audit.to_dict()}")

            temporary_directory = tempfile.TemporaryDirectory(prefix="cws-v9-exact-")
            report = WorkspaceLoadReport(
                project_path=project_path,
                project_id=session.project.project_id,
                elapsed_seconds=time.perf_counter() - started,
                scene_nodes=len(load_result.scene.nodes),
                renderable_nodes=sum(1 for node in load_result.scene.nodes if node.geometry_id),
                grid_rows=len(interaction.grid_model.rows),
                bom_traceability_rows=len(bom_snapshot.traceability),
                unique_geometries=load_result.catalog_report.unique_geometry_count,
                proxy_geometries=load_result.catalog_report.proxy_geometry_count,
                identity_audit=identity_audit,
            )
            return cls(
                session=session,
                load_result=load_result,
                controller=controller,
                interaction=interaction,
                bridge=bridge,
                bom_snapshot=bom_snapshot,
                identity_audit=identity_audit,
                report=report,
                selection_bus=selection_bus,
                bom_index=bom_index,
                pdf_bridge=pdf_bridge,
                _temporary_directory=temporary_directory,
                _interaction_unsubscribe=interaction_unsubscribe,
                _owns_controller=True,
            )
        except Exception:
            if interaction is not None:
                interaction.close()
            if controller is not None:
                controller.shutdown()
            if temporary_directory is not None:
                temporary_directory.cleanup()
            session.close()
            raise


    @staticmethod
    def _complete_bom_traceability(project: ProjectModel, snapshot: Any) -> None:
        """Ensure every canonical selectable entity has BOM traceability.

        The legacy BOM engine represents purchased parts mainly through Part
        classification.  Project Model 2.4 also has first-class PurchasedItem
        entities.  V9 adds identity-only traceability records for those items
        without inventing prices or procurement facts.
        """
        present = {str(row.get("internal_id") or "") for row in snapshot.traceability}
        for item in project.purchased_items.values():
            if item.internal_id in present:
                continue
            snapshot.traceability.append({
                "entity_type": "purchased_item",
                "internal_id": item.internal_id,
                "group_id": f"PURCHASED-{item.internal_id}",
                "name": item.name or item.description,
                "category": item.category,
                "source_file_id": item.source_identity.source_file_id,
                "source_entity_id": item.source_identity.source_entity_id,
                "global_id": item.source_identity.global_id,
                "part_position": item.source_identity.part_position or item.article_number,
                "assembly_mark": item.source_identity.assembly_mark,
                "geometry_hash": "",
                "manufacturing_hash": "",
                "production_identity_hash": "",
            })
        snapshot.traceability.sort(key=lambda row: (str(row.get("entity_type") or ""), str(row.get("internal_id") or "")))
        if hasattr(snapshot, "refresh_hash"):
            snapshot.refresh_hash()

    @staticmethod
    def _canonical_entities(project: ProjectModel) -> dict[str, str]:
        result: dict[str, str] = {}
        for kind, collection in (
            ("assembly", project.assemblies),
            ("part", project.parts),
            ("purchased_item", project.purchased_items),
            ("fastener", project.fasteners),
            ("weld", project.welds),
        ):
            for entity_id in collection:
                result[str(entity_id)] = kind
        return result

    @classmethod
    def _audit_identity(
        cls,
        project: ProjectModel,
        load_result: ProjectSceneLoadResult,
        interaction: ProjectInteractionModel,
        bom_snapshot: Any,
        *,
        project_object_identity_preserved: bool,
    ) -> IdentityAuditReport:
        canonical = cls._canonical_entities(project)
        canonical_ids = set(canonical)
        scene_ids_list = [
            str(node.entity_id)
            for node in load_result.scene.nodes
            if str(node.entity_id) in canonical_ids
        ]
        duplicate_scene = sorted(
            entity_id for entity_id in set(scene_ids_list) if scene_ids_list.count(entity_id) > 1
        )
        scene_ids = set(scene_ids_list)
        grid_ids = {str(row.entity_id) for row in interaction.grid_model.rows if str(row.entity_id) in canonical_ids}
        bom_ids = {
            str(row.get("internal_id") or "")
            for row in bom_snapshot.traceability
            if str(row.get("internal_id") or "") in canonical_ids
        }
        all_scene_entities = {str(node.entity_id) for node in load_result.scene.nodes}
        return IdentityAuditReport(
            project_id=project.project_id,
            canonical_entity_count=len(canonical_ids),
            scene_entity_count=len(scene_ids),
            grid_entity_count=len(grid_ids),
            bom_entity_count=len(bom_ids),
            duplicate_scene_entity_ids=tuple(duplicate_scene),
            missing_in_scene=tuple(sorted(canonical_ids - scene_ids)),
            missing_in_grid=tuple(sorted(canonical_ids - grid_ids)),
            missing_in_bom=tuple(sorted(canonical_ids - bom_ids)),
            unexpected_scene_entities=tuple(sorted(all_scene_entities - canonical_ids - {project.project_id})),
            project_object_identity_preserved=project_object_identity_preserved,
        )


    def bind_controller(self, controller: ViewerCoreController) -> None:
        """Bind the integrated application to one active renderer controller.

        Headless/CLI use starts with a memory backend.  The Qt shell calls this
        once after constructing its VTK widget.  The old interaction and owned
        memory controller are disposed, so only one active selection/session
        state remains in the application process.
        """
        if controller is self.controller:
            return
        previous_selection = self.interaction.selection.entity_ids
        if self._interaction_unsubscribe is not None:
            self._interaction_unsubscribe()
            self._interaction_unsubscribe = None
        self.interaction.close()
        if self._owns_controller:
            self.controller.shutdown()
        if controller.scene is None or controller.scene.scene_hash != self.load_result.scene.scene_hash:
            controller.load_scene(self.load_result.scene)
        self.controller = controller
        self.interaction = ProjectInteractionModel(
            controller,
            self.project,
            mesh_repository=self.load_result.repository,
        )
        self.bridge = GridViewerBridge(self.interaction, self.interaction.grid_model)
        self.bridge.refresh_scope_state()
        self._interaction_unsubscribe = self.interaction.subscribe(
            lambda selection: self.selection_bus.publish(
                selection.entity_ids,
                primary_entity_id=selection.primary_entity_id,
                origin=selection.origin,
            )
        )
        self._owns_controller = False
        if previous_selection:
            self.interaction.select_entities(previous_selection, origin="controller_rebind")

    def select_entities(
        self,
        entity_ids: Iterable[str],
        *,
        origin: str = "application",
        mode: str = "replace",
        feature_id: str | None = None,
        subshape_id: str | None = None,
    ) -> None:
        values = tuple(dict.fromkeys(str(value) for value in entity_ids if str(value)))
        if values:
            self.interaction.select_entities(values, origin=origin, mode=mode)
        else:
            self.controller.clear_selection()
        self.selection_bus.publish(
            values,
            primary_entity_id=(values[0] if values else None),
            feature_id=feature_id,
            subshape_id=subshape_id,
            origin=origin,
        )

    def select_bom_group(self, group_id: str, *, origin: str = "bom") -> tuple[str, ...]:
        entity_ids = self.bom_index.entities_for_group(group_id)
        if entity_ids:
            self.select_entities(entity_ids, origin=origin)
        return entity_ids

    def highlight_pdf_feature(self, entity_id: str, feature_id: str) -> None:
        self.select_entities(
            (entity_id,),
            origin="pdf",
            feature_id=feature_id,
        )

    def readiness_for_part(
        self,
        entity_id: str,
        formats: Iterable[str] = ("json", "review_pdf", "nc1", "step", "ifc", "production_pdf"),
    ) -> dict[str, Any]:
        part = self.project.parts.get(str(entity_id))
        if part is None:
            return {
                "part_id": str(entity_id),
                "production_ready": False,
                "allowed": {},
                "blocking_codes": ["CWS-V9-NOT-A-PART"],
            }
        requested = tuple(dict.fromkeys(str(value).lower() for value in formats))
        assessment = ReadinessGate().assess(part, list(requested))
        return {
            "part_id": str(entity_id),
            "production_ready": assessment.production_ready,
            "allowed": {fmt: assessment.allowed(fmt) for fmt in requested},
            "messages": {
                fmt: [message.to_dict() for message in assessment.messages_for(fmt)]
                for fmt in requested
            },
            "blocking_codes": sorted({
                message.code
                for fmt in requested
                for message in assessment.messages_for(fmt)
                if message.severity == "error"
            }),
            "viewer_can_override": False,
        }

    def open_exact_part(self, entity_id: str) -> ExactPartOpenResult:
        """Open V6 exact review only where source isolation is actually proven."""
        key = str(entity_id)
        part = self.project.parts.get(key)
        if part is None:
            return ExactPartOpenResult(
                entity_id=key,
                status="blocked",
                source_format="",
                blocking_codes=("CWS-V9-EXACT-NOT-A-PART",),
            )
        identity = part.source_identity
        source_format = str(identity.source_format or "").upper()

        # Converter-owned canonical STEP attachments are exact evidence and do
        # not require re-interpreting a multi-part source model.
        canonical = part.canonical()
        if canonical is not None and canonical.attachment_bytes("step"):
            target = Path(self._temporary_directory.name) / f"{key}.canonical.step"
            write_attachment(canonical, "step", target)
            source = load_step_exact(target, part_id=key)
            service = ExactPartWorkbenchService(source, source)
            return ExactPartOpenResult(
                entity_id=key,
                status="available_exact_canonical",
                source_format="STEP",
                source_path=target,
                service=service,
                notes=("Converter-owned canonical STEP attachment",),
            )

        if source_format != "STEP":
            code = (
                "CWS-V9-EXACT-IFC-BREP-ISOLATION-PENDING"
                if source_format == "IFC"
                else "CWS-V9-EXACT-SOURCE-FORMAT-UNSUPPORTED"
            )
            return ExactPartOpenResult(
                entity_id=key,
                status="blocked",
                source_format=source_format,
                blocking_codes=(code,),
                notes=("Projectdisplay remains available; exact production review stays blocked.",),
            )

        source_parts = [
            item for item in self.project.parts.values()
            if item.source_identity.source_file_id == identity.source_file_id
        ]
        if len(source_parts) != 1:
            return ExactPartOpenResult(
                entity_id=key,
                status="blocked",
                source_format=source_format,
                blocking_codes=("CWS-V9-EXACT-STEP-PART-ISOLATION-UNPROVEN",),
                notes=(f"Source contains {len(source_parts)} project parts; whole-file BREP is not treated as this part.",),
            )

        resolver = ProjectSourceResolver(
            self.project,
            project_package_path=self.project_path,
            search_roots=tuple(value.parent for value in self.session.source_paths.values()),
        )
        resolved = resolver.resolve(identity.source_file_id)
        source = load_step_exact(resolved.path, part_id=key)
        service = ExactPartWorkbenchService(source, None)
        return ExactPartOpenResult(
            entity_id=key,
            status="available_source_exact_canonical_required",
            source_format=source_format,
            source_path=resolved.path,
            service=service,
            blocking_codes=("CWS-EXACT-CANONICAL-MISSING",),
            notes=("Exact source BREP loaded; canonical rebuild/review is still required.",),
        )

    def save(self, path: str | Path | None = None) -> Path:
        return self.session.save(path)

    def close(self) -> None:
        if self._interaction_unsubscribe is not None:
            self._interaction_unsubscribe()
            self._interaction_unsubscribe = None
        self.interaction.close()
        # ViewerCoreController.shutdown() is idempotent.  Always dispose the
        # active controller so headless rebinds and Qt widgets cannot leak a
        # render backend after the canonical project session is closed.
        self.controller.shutdown()
        self._temporary_directory.cleanup()
        self.session.close()

    def __enter__(self) -> "IntegratedProjectWorkspace":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.close()
