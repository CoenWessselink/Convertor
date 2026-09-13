"""Adaptive close-up tessellation integration for the production Viewer V15 host.

The patch is intentionally narrow and reversible. It keeps the canonical project,
entity IDs, scene graph, selection and manufacturing geometry untouched. Only the
cached display mesh for selected, screen-large, visibly faceted curved resources
is replaced with a stricter tessellation profile after interaction settles.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

_INSTALLED = False


def install_adaptive_closeup_refinement() -> None:
    global _INSTALLED
    # Diagnostic/evidence processes are deliberately finite-lived and must not
    # start background tessellation jobs after their UI assertions complete.
    # This does not alter normal interactive desktop runtime behaviour.
    if os.environ.get("CWS_HEADLESS_NONINTERACTIVE") == "1":
        return
    if _INSTALLED or not qt_available():
        return

    QtCore, _QtGui, _QtWidgets = require_qt()

    from cws_convertor.integration import IntegratedProjectWorkspace
    from cws_convertor.ui_qt.project_workspace import IntegratedProjectWorkspaceWidget
    from cws_viewer.adapters.source_geometry import ProjectSourceResolver
    from cws_viewer.cache import MeshCache
    from cws_viewer.contracts.geometry import TessellationSettings
    from cws_viewer.geometry import StepMeshProvider
    from cws_viewer.geometry.loader import CancellationToken, GeometryLoadCancelled, GeometryLoadCoordinator
    from cws_viewer.geometry.silhouette_quality import inspect_silhouette_quality
    from cws_viewer.geometry.worker_pool import PersistentGeometryWorkerPool
    from cws_viewer.performance import GeometryPriorityScheduler
    from cws_viewer.performance.adaptive_detail import projected_extent_pixels
    from cws_viewer.performance.policy import LoadingPerformancePolicy
    from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2

    class _CloseUpGeometryWorker(QtCore.QObject):
        batch_ready = QtCore.Signal(object)
        completed = QtCore.Signal(object)
        failed = QtCore.Signal(str)
        finished = QtCore.Signal()

        def __init__(self, workspace: IntegratedProjectWorkspace, geometry_ids: tuple[str, ...]) -> None:
            super().__init__()
            self.workspace = workspace
            self.geometry_ids = tuple(dict.fromkeys(str(v) for v in geometry_ids if str(v)))
            self.token = CancellationToken()

        def request_cancel(self) -> None:
            self.token.cancel()

        def run(self, context: Any | None = None) -> None:
            coordinator = None
            try:
                workspace = self.workspace
                roots = tuple(Path(value).parent for value in workspace.session.source_paths.values())
                resolver = ProjectSourceResolver(
                    workspace.project,
                    project_package_path=workspace.project_path,
                    search_roots=roots,
                )
                wanted = set(self.geometry_ids)
                requests = tuple(
                    request
                    for request in workspace.load_result.catalog.unique_requests(resolver)
                    if request.geometry_id in wanted
                )
                if not requests:
                    self.completed.emit({"requested": 0, "upgraded": 0, "geometry_ids": (), "failed": ()})
                    return

                settings = TessellationSettings.close_up()
                policy = LoadingPerformancePolicy.detect(len(requests))
                cache = MeshCache(
                    Path.home() / ".cws_convertor" / "viewer_mesh_cache",
                    max_memory_items=max(64, min(len(requests) * 8, 512)),
                )
                providers = (
                    PersistentGeometryWorkerPool.shared(policy.worker_count),
                    StepMeshProvider(),
                )
                scheduler = GeometryPriorityScheduler()
                scheduler.update_context(selected=self.geometry_ids, visible=self.geometry_ids)
                coordinator = GeometryLoadCoordinator(
                    providers,
                    cache=cache,
                    repository=workspace.load_result.repository,
                    settings=settings,
                    max_workers=max(1, min(policy.worker_count, 4)),
                    scheduler=scheduler,
                )
                report = coordinator.load_many(requests, token=self.token, allow_proxy=False)
                upgraded = tuple(
                    result.request.geometry_id
                    for result in report.results
                    if result.succeeded
                    and result.mesh is not None
                    and result.mesh.exactness != "display_proxy"
                )
                failed = tuple(
                    f"{result.request.geometry_id}: {result.error or result.status.value}"
                    for result in report.results
                    if not result.succeeded
                )
                if upgraded:
                    self.batch_ready.emit(upgraded)
                self.completed.emit(
                    {
                        "requested": len(requests),
                        "upgraded": len(upgraded),
                        "geometry_ids": upgraded,
                        "failed": failed,
                        "settings": settings.to_dict(),
                    }
                )
            except GeometryLoadCancelled:
                self.completed.emit(
                    {
                        "requested": len(self.geometry_ids),
                        "upgraded": 0,
                        "geometry_ids": (),
                        "cancelled": True,
                        "failed": (),
                    }
                )
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")
            finally:
                if coordinator is not None:
                    coordinator.close()
                self.finished.emit()

    def _ensure_adaptive_state(self: Any) -> None:
        if hasattr(self, "_cws_closeup_timer"):
            return
        self._cws_closeup_worker = None
        self._cws_closeup_job_id = None
        self._cws_closeup_pending_ids = set()
        self._cws_closeup_completed_ids = set()
        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(180)
        timer.timeout.connect(lambda: _start_pending_closeup(self))
        self._cws_closeup_timer = timer

    def _bind_viewer(self: Any) -> None:
        viewer = getattr(self, "viewer", None)
        if viewer is None:
            return
        viewer._cws_adaptive_detail_callback = lambda: _camera_idle(self)

    def _camera_idle(self: Any) -> None:
        workspace = getattr(self, "workspace", None)
        if workspace is not None:
            _schedule_closeup(self, workspace.interaction.selection)

    def _candidate_geometry_ids(self: Any, selection: Any) -> tuple[str, ...]:
        workspace = getattr(self, "workspace", None)
        viewer = getattr(self, "viewer", None)
        if workspace is None or viewer is None or selection is None:
            return ()
        node_ids = tuple(str(value) for value in getattr(selection, "node_ids", ()) if str(value))
        if not node_ids:
            return ()
        index = viewer.controller.index
        camera = viewer.controller.session.camera
        viewport_height = max(1.0, float(viewer.height()))
        selected_renderables = index.descendants(node_ids, include_self=True, renderable_only=True)
        candidates: list[str] = []
        for node_id in selected_renderables:
            node = index.node(node_id)
            geometry_id = str(node.geometry_id or "")
            if not geometry_id:
                continue
            mesh = workspace.load_result.repository.get(geometry_id)
            if mesh is None or mesh.exactness == "display_proxy":
                continue
            if not inspect_silhouette_quality(mesh).needs_refinement:
                continue
            bounds = index.world_bounds_by_node.get(node_id)
            if bounds is None:
                continue
            if projected_extent_pixels(bounds, camera, viewport_height) >= 90.0:
                candidates.append(geometry_id)
        return tuple(dict.fromkeys(candidates))

    def _schedule_closeup(self: Any, selection: Any) -> None:
        _ensure_adaptive_state(self)
        values = set(_candidate_geometry_ids(self, selection))
        values.difference_update(self._cws_closeup_completed_ids)
        if not values:
            return
        self._cws_closeup_pending_ids.update(values)
        self._cws_closeup_timer.start()

    def _start_pending_closeup(self: Any) -> None:
        workspace = getattr(self, "workspace", None)
        manager = getattr(self, "_job_manager", None)
        if workspace is None or manager is None:
            return
        if getattr(self, "_exact_worker", None) is not None or self._cws_closeup_worker is not None:
            self._cws_closeup_timer.start(250)
            return
        geometry_ids = tuple(
            sorted(self._cws_closeup_pending_ids - self._cws_closeup_completed_ids)
        )
        self._cws_closeup_pending_ids.difference_update(geometry_ids)
        if not geometry_ids:
            return
        generation = int(getattr(self, "_load_generation", 0))
        worker = _CloseUpGeometryWorker(workspace, geometry_ids)
        worker.batch_ready.connect(
            lambda values, value=generation: self._exact_geometry_batch(value, values)
        )
        worker.completed.connect(
            lambda report, value=generation: _closeup_completed(self, value, report)
        )
        worker.failed.connect(
            lambda message, value=generation: _closeup_failed(self, value, message)
        )
        worker.finished.connect(worker.deleteLater)
        self._cws_closeup_worker = worker
        self._cws_closeup_job_id = manager.submit(
            "project_closeup_geometry_refinement",
            lambda context: worker.run(context),
            description=f"Close-up viewergeometrie: {workspace.project_path.name}",
            project_id=str(workspace.project_path),
            metadata={"adaptive_closeup": True, "geometry_ids": geometry_ids},
            max_retries=0,
        )

    def _closeup_completed(self: Any, generation: int, report: Any) -> None:
        if generation != int(getattr(self, "_load_generation", -1)):
            return
        upgraded = tuple(report.get("geometry_ids") or ())
        self._cws_closeup_completed_ids.update(map(str, upgraded))
        self._cws_closeup_job_id = None
        self._cws_closeup_worker = None
        if upgraded and hasattr(self, "status"):
            self.status.setText(f"Close-up detail verfijnd · {len(upgraded):,} meshresource(s)")
        if self._cws_closeup_pending_ids:
            self._cws_closeup_timer.start(100)

    def _closeup_failed(self: Any, generation: int, message: str) -> None:
        if generation == int(getattr(self, "_load_generation", -1)):
            self._cws_closeup_job_id = None
            self._cws_closeup_worker = None
            if hasattr(self, "status"):
                self.status.setText(
                    f"Close-up geometrie behouden op standaardkwaliteit: {message}"
                )

    original_init = IntegratedProjectWorkspaceWidget.__init__
    def patched_init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        _ensure_adaptive_state(self)
    IntegratedProjectWorkspaceWidget.__init__ = patched_init

    original_preview = IntegratedProjectWorkspaceWidget._project_preview_guarded
    def patched_preview(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = original_preview(self, *args, **kwargs)
        _ensure_adaptive_state(self)
        _bind_viewer(self)
        return result
    IntegratedProjectWorkspaceWidget._project_preview_guarded = patched_preview

    original_loaded = IntegratedProjectWorkspaceWidget._project_loaded
    def patched_loaded(self: Any, *args: Any, **kwargs: Any) -> Any:
        result = original_loaded(self, *args, **kwargs)
        _ensure_adaptive_state(self)
        _bind_viewer(self)
        workspace = getattr(self, "workspace", None)
        if workspace is not None:
            _schedule_closeup(self, workspace.interaction.selection)
        return result
    IntegratedProjectWorkspaceWidget._project_loaded = patched_loaded

    original_flush = IntegratedProjectWorkspaceWidget._flush_interaction_selection
    def patched_flush(self: Any) -> Any:
        result = original_flush(self)
        workspace = getattr(self, "workspace", None)
        if workspace is not None:
            _schedule_closeup(self, workspace.interaction.selection)
        return result
    IntegratedProjectWorkspaceWidget._flush_interaction_selection = patched_flush

    original_exact_completed = IntegratedProjectWorkspaceWidget._exact_geometry_completed
    def patched_exact_completed(self: Any, generation: int, report: Any) -> Any:
        result = original_exact_completed(self, generation, report)
        workspace = getattr(self, "workspace", None)
        if workspace is not None:
            _schedule_closeup(self, workspace.interaction.selection)
        return result
    IntegratedProjectWorkspaceWidget._exact_geometry_completed = patched_exact_completed

    original_cancel = IntegratedProjectWorkspaceWidget.cancel_project_load
    def patched_cancel(self: Any) -> Any:
        worker = getattr(self, "_cws_closeup_worker", None)
        if worker is not None:
            worker.request_cancel()
        manager = getattr(self, "_job_manager", None)
        job_id = getattr(self, "_cws_closeup_job_id", None)
        if manager is not None and job_id is not None:
            manager.cancel(job_id)
        return original_cancel(self)
    IntegratedProjectWorkspaceWidget.cancel_project_load = patched_cancel

    original_close = IntegratedProjectWorkspaceWidget.close_project
    def patched_close(self: Any) -> Any:
        worker = getattr(self, "_cws_closeup_worker", None)
        if worker is not None:
            worker.request_cancel()
        result = original_close(self)
        if hasattr(self, "_cws_closeup_pending_ids"):
            self._cws_closeup_pending_ids.clear()
            self._cws_closeup_completed_ids.clear()
            self._cws_closeup_worker = None
            self._cws_closeup_job_id = None
        return result
    IntegratedProjectWorkspaceWidget.close_project = patched_close

    original_idle = VtkRealProjectWidgetFeelV2._restore_idle_quality
    def patched_idle(self: Any) -> Any:
        result = original_idle(self)
        callback = getattr(self, "_cws_adaptive_detail_callback", None)
        if callable(callback):
            callback()
        return result
    VtkRealProjectWidgetFeelV2._restore_idle_quality = patched_idle

    _INSTALLED = True


__all__ = ["install_adaptive_closeup_refinement"]
