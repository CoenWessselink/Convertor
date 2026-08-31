"""Integrated Project/Production workspace for the CWS Convertor Qt shell."""
from __future__ import annotations

import os
from pathlib import Path
import threading
from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    from cws_convertor.bom import export_bom_package
    from cws_convertor.integration import IntegratedProjectWorkspace
    from cws_viewer.adapters.source_geometry import ProjectSourceResolver
    from cws_viewer.backends.memory import MemoryRenderBackend
    from cws_viewer.cache import MeshCache
    from cws_viewer.contracts.geometry import GeometryLoadStatus, TessellationSettings
    from cws_viewer.core.controller import ViewerCoreController
    from cws_viewer.geometry import IsolatedIfcMeshProvider, StepMeshProvider
    from cws_viewer.geometry.worker_pool import PersistentGeometryWorkerPool
    from cws_viewer.geometry.loader import (
        CancellationToken,
        GeometryLoadCancelled,
        GeometryLoadCoordinator,
    )
    from cws_viewer.performance import GeometryPriorityScheduler
    from cws_viewer.ui_qt.exact_part_workbench import ExactPartWorkbenchPanel
    from cws_viewer.performance.policy import LoadingPerformancePolicy
    from cws_viewer.ui_qt.property_grid import ProfessionalPropertyGridPanel
    from cws_viewer.ui_qt.vtk_project_widget import VtkProjectWidget
    from cws_viewer.ui_qt.vtk_real_project_widget import NavigationMode
    try:
        from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import (
            VtkRealProjectWidgetFeelV2 as VtkRealProjectWidget,
        )
    except Exception:
        from cws_viewer.ui_qt.vtk_real_project_widget import VtkRealProjectWidget
    from cws_viewer.properties import GridLayoutIdentity, GridLayoutStore
    from .viewer_tools import IntegratedViewerToolsPanel

    class _HeadlessGuiSmokeViewer(QtWidgets.QFrame):
        """QWidget host for GUI integration tests that cannot create OpenGL windows."""

        is_headless_gui_smoke = True

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsHeadlessGuiSmokeViewer")
            self.controller = ViewerCoreController(
                MemoryRenderBackend(),
                width=1280,
                height=720,
            )
            layout = QtWidgets.QVBoxLayout(self)
            label = QtWidgets.QLabel("Headless GUI smoke viewer")
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

        def load_scene(self, scene: Any) -> None:
            self.controller.load_scene(scene)

        def closeEvent(self, event: Any) -> None:
            self.controller.shutdown()
            super().closeEvent(event)

    class _LoadWorker(QtCore.QObject):
        loaded = QtCore.Signal(object)
        preview_ready = QtCore.Signal(object)
        progress = QtCore.Signal(int, str)
        failed = QtCore.Signal(str)
        cancelled = QtCore.Signal()
        finished = QtCore.Signal()

        def __init__(self, path: Path, *, load_geometry: bool) -> None:
            super().__init__()
            self.path = path
            self.load_geometry = load_geometry
            self.token = CancellationToken()
            self._preview_ack = threading.Event()

        def request_cancel(self) -> None:
            self.token.cancel()
            self._preview_ack.set()

        def acknowledge_preview(self) -> None:
            self._preview_ack.set()

        def _publish_preview(self, load_result: Any) -> None:
            self._preview_ack.clear()
            self.preview_ready.emit(load_result)
            while not self._preview_ack.wait(0.05):
                self.token.check()

        @QtCore.Slot()
        def run(self, context: Any | None = None) -> None:
            try:
                self.token.check()
                self.progress.emit(5, "Projectbestand en schema controleren")
                self.progress.emit(18, "Projectmodel, bronnen en geometrie openen")
                # Product mode renders authoritative source geometry. Display
                # proxies are diagnostic only: silently presenting boxes as a
                # completed model is never acceptable.
                allow_proxy = os.environ.get("CWS_ALLOW_DISPLAY_PROXIES", "0") == "1"
                progressive = os.environ.get("CWS_PROGRESSIVE_PROJECT_LOAD", "0") == "1"
                prefer_proxy = bool(self.load_geometry and allow_proxy and progressive)

                def report(percent: int, message: str) -> None:
                    self.token.check()
                    if context is not None:
                        context.update(max(0.0, min(1.0, float(percent) / 100.0)), message)
                    self.progress.emit(percent, message)

                workspace = IntegratedProjectWorkspace.open(
                    self.path,
                    read_only=False,
                    load_all_geometry=self.load_geometry,
                    allow_proxy=allow_proxy,
                    prefer_proxy=prefer_proxy,
                    progress_callback=report,
                    cancellation_token=self.token,
                    preview_callback=self._publish_preview,
                )
                if workspace.load_result.geometry_report.proxy_count:
                    self.progress.emit(
                        70,
                        f"Responsieve 3D-weergave gereed · {workspace.load_result.geometry_report.proxy_count:,} geometrieën",
                    )
                self.progress.emit(80, "Viewer-scene en selectiecontext voorbereiden")
                self.loaded.emit(workspace)
            except GeometryLoadCancelled:
                self.cancelled.emit()
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")
            finally:
                self.finished.emit()


    class _ExactGeometryWorker(QtCore.QObject):
        batch_ready = QtCore.Signal(object)
        progress = QtCore.Signal(int, str)
        completed = QtCore.Signal(object)
        cancelled = QtCore.Signal()
        failed = QtCore.Signal(str)
        finished = QtCore.Signal()

        def __init__(
            self,
            workspace: IntegratedProjectWorkspace,
            scheduler: GeometryPriorityScheduler | None = None,
        ) -> None:
            super().__init__()
            self.workspace = workspace
            self.scheduler = scheduler or GeometryPriorityScheduler()
            self.token = CancellationToken()

        def request_cancel(self) -> None:
            self.token.cancel()

        def run(self, context: Any | None = None) -> None:
            coordinator = None
            ifc_provider = None
            try:
                workspace = self.workspace
                roots = tuple(Path(value).parent for value in workspace.session.source_paths.values())
                resolver = ProjectSourceResolver(
                    workspace.project,
                    project_package_path=workspace.project_path,
                    search_roots=roots,
                )
                requests = workspace.load_result.catalog.unique_requests(resolver)
                self.scheduler.update_context(
                    visible=(request.geometry_id for request in requests),
                )
                requests = self.scheduler.order(requests)
                cache = MeshCache(
                    Path.home() / ".cws_convertor" / "viewer_mesh_cache",
                    max_memory_items=max(128, min(len(requests), 2048)),
                )
                settings = TessellationSettings()
                performance_policy = LoadingPerformancePolicy.detect(len(requests))
                ifc_provider = PersistentGeometryWorkerPool(performance_policy.worker_count)
                ifc_provider_version = getattr(
                    ifc_provider, "provider_version", "persistent-ifc-worker-pool-v1"
                )
                coordinator = GeometryLoadCoordinator(
                    (StepMeshProvider(),),
                    cache=cache,
                    repository=workspace.load_result.repository,
                    settings=settings,
                    max_workers=performance_policy.worker_count,
                    scheduler=self.scheduler,
                )
                upgraded: list[str] = []
                failures: list[str] = []
                batch: list[str] = []
                total = len(requests)
                completed = 0
                ifc_misses = []

                def publish(request: Any, mesh: Any, *, persist: bool = True) -> None:
                    nonlocal completed
                    workspace.load_result.repository.put(request.geometry_id, mesh)
                    if persist:
                        cache.put_async(
                            request.cache_key(settings, ifc_provider_version),
                            mesh,
                            provider_version=ifc_provider_version,
                            settings=settings,
                        )
                    upgraded.append(request.geometry_id)
                    batch.append(request.geometry_id)
                    completed += 1
                    if len(batch) >= performance_policy.scene_upload_batch_limit:
                        self.batch_ready.emit(tuple(batch))
                        batch.clear()
                    message = f"Exacte brongeometrie {completed:,}/{total:,}"
                    if completed == total or completed % 16 == 0:
                        self.progress.emit(int(round(completed * 100 / max(total, 1))), message)

                request_by_id = {request.geometry_id: request for request in requests}
                ifc_keys = {
                    request.geometry_id: request.cache_key(settings, ifc_provider_version)
                    for request in requests
                    if request.source_format.upper() == "IFC"
                }
                cached_ifc = cache.get_many(ifc_keys.values(), max_workers=12)
                for request in requests:
                    self.token.check()
                    if context is not None:
                        context.check_cancelled()
                    provider = ifc_provider if request.source_format.upper() == "IFC" else coordinator._provider(request)
                    provider_version = (
                        ifc_provider_version
                        if request.source_format.upper() == "IFC"
                        else (provider.provider_version if provider is not None else "")
                    )
                    key = request.cache_key(settings, provider_version) if provider_version else ""
                    cached = (
                        cached_ifc.get(key)
                        if request.source_format.upper() == "IFC"
                        else (cache.get(key) if key else None)
                    )
                    if cached is not None:
                        publish(request, cached, persist=False)
                        continue
                    if request.source_format.upper() == "IFC":
                        ifc_misses.append(request)
                        continue
                    result = coordinator.load_one(request, token=self.token, allow_proxy=False)
                    mesh = result.mesh
                    if (
                        mesh is not None
                        and result.status in {GeometryLoadStatus.READY, GeometryLoadStatus.PARTIAL}
                        and mesh.exactness != "display_proxy"
                    ):
                        upgraded.append(request.geometry_id)
                        batch.append(request.geometry_id)
                        completed += 1
                    else:
                        failures.append(
                            f"{request.geometry_id}: {result.error or result.status.value}"
                        )
                    if batch and len(batch) >= performance_policy.scene_upload_batch_limit:
                        self.batch_ready.emit(tuple(batch))
                        batch.clear()
                    percent = int(round(completed * 100 / max(total, 1)))
                    message = f"Exacte brongeometrie {completed:,}/{total:,}"
                    self.progress.emit(percent, message)
                    if context is not None:
                        context.update(percent / 100.0, message)

                if ifc_misses:
                    returned = ifc_provider.load_many(
                        tuple(ifc_misses),
                        settings,
                        cancel_check=self.token.check,
                    )
                    cache.put_many_async(
                        (
                            request_by_id[geometry_id].cache_key(settings, ifc_provider_version),
                            mesh,
                            ifc_provider_version,
                            settings,
                        )
                        for geometry_id, mesh in returned.items()
                    )
                    for geometry_id, mesh in returned.items():
                        publish(request_by_id[geometry_id], mesh, persist=False)
                    missing_ids = {request.geometry_id for request in ifc_misses} - set(returned)
                    for geometry_id in sorted(missing_ids):
                        request = request_by_id[geometry_id]
                        try:
                            mesh = IsolatedIfcMeshProvider().load(
                                request,
                                settings,
                                cancel_check=self.token.check,
                            )
                        except Exception as exc:
                            failures.append(
                                f"{geometry_id}: IFC-batch en geisoleerde retry faalden: "
                                f"{type(exc).__name__}: {exc}"
                            )
                            continue
                        if mesh.exactness == "display_proxy":
                            failures.append(
                                f"{geometry_id}: geisoleerde retry leverde alleen een displayproxy"
                            )
                            continue
                        publish(request, mesh)
                source_appearance_scene = None
                source_appearance_report = None
                if any(request.source_format.upper() == "IFC" for request in requests):
                    # The responsive first frame deliberately avoids parsing
                    # the full IFC presentation graph.  Exact geometry is now
                    # available, so restore source-owned colours on this worker
                    # thread and publish one immutable replacement scene.
                    from cws_convertor.importers.p21 import P21Document
                    from cws_viewer.adapters.project_model import SceneBuildOptions
                    from cws_viewer.adapters.source_style_scene import (
                        SourceAppearanceProjectSceneAdapter,
                    )

                    catalog = workspace.load_result.catalog
                    source_ids = sorted(
                        {
                            str(getattr(record, "source_file_id", "") or "")
                            for record in catalog.records_by_entity.values()
                            if str(getattr(record, "source_format", "") or "").upper() == "IFC"
                        }
                        - {""}
                    )
                    for source_file_id in source_ids:
                        self.token.check()
                        if source_file_id not in catalog._documents:
                            source = resolver.resolve(source_file_id)
                            catalog._documents[source_file_id] = P21Document.load(source.path)
                    appearance_adapter = SourceAppearanceProjectSceneAdapter()
                    source_appearance_scene = appearance_adapter.build_scene(
                        workspace.project,
                        SceneBuildOptions(),
                        geometry_catalog=catalog,
                        mesh_repository=workspace.load_result.repository,
                        enrich_source_appearance=True,
                    )
                    source_appearance_report = appearance_adapter.last_report
                if batch:
                    self.batch_ready.emit(tuple(batch))
                self.completed.emit(
                    {
                        "requested": total,
                        "upgraded": len(upgraded),
                        "failed": tuple(failures),
                        "source_appearance_scene": source_appearance_scene,
                        "source_appearance_report": source_appearance_report,
                    }
                )
            except GeometryLoadCancelled:
                self.cancelled.emit()
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")
            finally:
                if coordinator is not None:
                    coordinator.close()
                if ifc_provider is not None:
                    ifc_provider.close()
                self.finished.emit()


    class IntegratedProjectWorkspaceWidget(QtWidgets.QWidget):
        """Tree, V8 grid, VTK model, properties, BOM and V6 exact review."""

        project_loaded = QtCore.Signal(str)
        load_progress = QtCore.Signal(int, str)
        project_closed = QtCore.Signal()
        selection_changed = QtCore.Signal(object)
        action_requested = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsV9IntegratedProjectWorkspace")
            self.workspace: IntegratedProjectWorkspace | None = None
            self._thread: QtCore.QThread | None = None
            self._job_manager: Any | None = None
            self._load_job_id: str | None = None
            self._load_generation = 0
            self._worker: _LoadWorker | None = None
            self._exact_worker: _ExactGeometryWorker | None = None
            self._exact_job_id: str | None = None
            self._preview_result: Any | None = None
            self._load_elapsed = QtCore.QElapsedTimer()
            self._load_heartbeat = QtCore.QTimer(self)
            self._load_heartbeat.setInterval(1000)
            self._load_heartbeat.timeout.connect(self._loading_tick)
            self._tree_items: dict[str, Any] = {}
            self._syncing = False
            self._interaction_unsubscribe: Any | None = None
            self._grid_entity_ids: set[str] = set()
            self.viewer: Any | None = None
            self._build_ui()

        def set_job_manager(self, manager: Any) -> None:
            self._job_manager = manager

        def _build_ui(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(6, 6, 6, 6)
            root.setSpacing(5)

            toolbar = QtWidgets.QToolBar()
            toolbar.setObjectName("cwsV9ProjectToolbar")
            self.open_action = toolbar.addAction("Project openen")
            self.close_action = toolbar.addAction("Sluiten")
            toolbar.addSeparator()
            self.fit_action = toolbar.addAction("Fit")
            self.select_action = toolbar.addAction("Selecteren")
            self.orbit_action = toolbar.addAction("Draaien")
            self.pan_action = toolbar.addAction("Slepen")
            self.zoom_area_action = toolbar.addAction("Zoomvenster")
            self.iso_action = toolbar.addAction("Iso")
            self.top_action = toolbar.addAction("Boven")
            self.front_action = toolbar.addAction("Voor")
            toolbar.addSeparator()
            self.hide_action = toolbar.addAction("Verbergen")
            self.isolate_action = toolbar.addAction("Isoleren")
            self.ghost_action = toolbar.addAction("Ghost")
            self.show_all_action = toolbar.addAction("Alles tonen")
            toolbar.addSeparator()
            self.actions_button = QtWidgets.QToolButton()
            self.actions_button.setText("Acties")
            self.actions_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            self.actions_button.setMenu(self._build_application_menu())
            toolbar.addWidget(self.actions_button)
            self.exact_action = toolbar.addAction("Exact Part Workbench")
            self.bom_action = toolbar.addAction("BOM exporteren")
            toolbar.addSeparator()
            transparency_label = QtWidgets.QLabel("Doorzichtigheid")
            toolbar.addWidget(transparency_label)
            self.transparency_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            self.transparency_slider.setObjectName("cwsModelTransparencySlider")
            self.transparency_slider.setRange(0, 90)
            self.transparency_slider.setValue(0)
            self.transparency_slider.setFixedWidth(120)
            self.transparency_slider.setToolTip("Regel de doorzichtigheid van het volledige model")
            toolbar.addWidget(self.transparency_slider)
            root.addWidget(toolbar)

            self.status = QtWidgets.QLabel("Open een .cwscproj-project")
            self.status.setObjectName("cwsV9ProjectStatus")
            root.addWidget(self.status)

            self.stack = QtWidgets.QStackedWidget()
            root.addWidget(self.stack, 1)
            self.empty = QtWidgets.QLabel(
                "CWS Convertor Project / Productie\n\n"
                "Eén Canonical Project Model · één viewer scene · één property grid · één BOM."
            )
            self.empty.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.stack.addWidget(self.empty)
            self.loading = QtWidgets.QFrame()
            loading_layout = QtWidgets.QVBoxLayout(self.loading)
            loading_layout.setContentsMargins(80, 80, 80, 80)
            loading_layout.addStretch(1)
            self.loading_title = QtWidgets.QLabel("Project wordt geladen in Viewer V15")
            self.loading_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.loading_title.setStyleSheet("font-size:18px; font-weight:600; color:#103f77;")
            self.loading_detail = QtWidgets.QLabel("Projectbestand controleren")
            self.loading_detail.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.loading_detail.setStyleSheet("color:#52647c;")
            self.loading_progress = QtWidgets.QProgressBar()
            self.loading_progress.setRange(0, 100)
            self.loading_progress.setValue(0)
            self.loading_progress.setFormat("%p%")
            self.loading_progress.setMinimumHeight(20)
            self.loading_elapsed = QtWidgets.QLabel("Verstreken tijd: 0 s")
            self.loading_elapsed.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.loading_elapsed.setStyleSheet("color:#52647c;")
            loading_layout.addWidget(self.loading_title)
            loading_layout.addSpacing(8)
            loading_layout.addWidget(self.loading_detail)
            loading_layout.addSpacing(10)
            loading_layout.addWidget(self.loading_progress)
            loading_layout.addWidget(self.loading_elapsed)
            loading_layout.addStretch(1)
            self.stack.addWidget(self.loading)
            self.host = QtWidgets.QWidget()
            self.host_layout = QtWidgets.QVBoxLayout(self.host)
            self.host_layout.setContentsMargins(0, 0, 0, 0)
            self.stack.addWidget(self.host)

            self.open_action.triggered.connect(self.choose_project)
            self.close_action.triggered.connect(self.close_project)
            self.fit_action.triggered.connect(lambda: self._controller_call("fit_all"))
            self.select_action.triggered.connect(lambda: self._set_navigation_mode(NavigationMode.SELECT, "Selecteren"))
            self.orbit_action.triggered.connect(lambda: self._set_navigation_mode(NavigationMode.ORBIT, "Draaien rond muispositie"))
            self.pan_action.triggered.connect(lambda: self._set_navigation_mode(NavigationMode.PAN, "Slepen"))
            self.zoom_area_action.triggered.connect(self._activate_zoom_area)
            self.iso_action.triggered.connect(lambda: self._controller_call("set_standard_view", "isometric"))
            self.top_action.triggered.connect(lambda: self._controller_call("set_standard_view", "top"))
            self.front_action.triggered.connect(lambda: self._controller_call("set_standard_view", "front"))
            self.hide_action.triggered.connect(self._hide_selection)
            self.isolate_action.triggered.connect(lambda: self._isolate_selection(False))
            self.ghost_action.triggered.connect(lambda: self._isolate_selection(True))
            self.show_all_action.triggered.connect(lambda: self._controller_call("show_all"))
            self.exact_action.triggered.connect(self.open_exact_workbench)
            self.bom_action.triggered.connect(self.export_bom)
            self.transparency_slider.valueChanged.connect(self._set_model_transparency)
            self._set_actions_enabled(False)

        def _set_actions_enabled(self, enabled: bool) -> None:
            for action in (
                self.close_action, self.fit_action, self.select_action, self.orbit_action,
                self.pan_action, self.zoom_area_action, self.iso_action, self.top_action,
                self.front_action, self.hide_action, self.isolate_action,
                self.ghost_action, self.show_all_action, self.exact_action,
                self.bom_action,
            ):
                action.setEnabled(enabled)
            self.actions_button.setEnabled(enabled)
            self.transparency_slider.setEnabled(enabled)

        def choose_project(self) -> None:
            name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "CWS-project openen", "", "CWS-project (*.cwscproj)"
            )
            if name:
                self.open_project(Path(name))

        def open_project(self, path: str | Path, *, load_geometry: bool = True) -> None:
            self.close_project()
            self._load_generation += 1
            generation = self._load_generation
            project_path = Path(path).expanduser().resolve()
            self.status.setText(f"Controleren en laden: {project_path.name}")
            self.stack.setCurrentWidget(self.loading)
            worker = _LoadWorker(project_path, load_geometry=load_geometry)
            worker.progress.connect(
                lambda percent, message, value=generation: self._load_progress_guarded(
                    value, percent, message
                )
            )
            worker.preview_ready.connect(
                lambda result, value=generation: self._project_preview_guarded(value, result)
            )
            worker.loaded.connect(
                lambda workspace, value=generation: self._project_loaded_guarded(value, workspace)
            )
            worker.failed.connect(
                lambda message, value=generation: self._project_failed_guarded(value, message)
            )
            worker.cancelled.connect(
                lambda value=generation: self._project_cancelled_guarded(value)
            )
            worker.finished.connect(worker.deleteLater)
            worker.finished.connect(
                lambda value=generation, target=worker: self._load_finished(value, target)
            )
            self._worker = worker
            self._load_elapsed.start()
            self._load_heartbeat.start()
            if self._job_manager is None:
                raise RuntimeError("Project openen vereist de applicatiebrede JobManager")
            self._load_job_id = self._job_manager.submit(
                "project_open_import",
                lambda context: (
                    context.stage("project_open", 0.01, "Projectcontainer openen"),
                    worker.run(context),
                )[-1],
                description=f"Project openen: {project_path.name}",
                project_id=str(project_path),
                metadata={"generation_guard": True, "progressive": True},
                max_retries=1,
            )

        def _load_finished(self, generation: int, worker: Any) -> None:
            if self._worker is not worker:
                return
            self._worker = None
            self._thread = None
            if generation == self._load_generation:
                self._load_job_id = None

        def _load_progress_guarded(self, generation: int, percent: int, message: str) -> None:
            if generation == self._load_generation:
                self._load_progress_changed(percent, message)

        def _project_failed_guarded(self, generation: int, message: str) -> None:
            if generation == self._load_generation:
                self._project_failed(message)

        def _project_cancelled_guarded(self, generation: int) -> None:
            if generation != self._load_generation:
                return
            self._load_heartbeat.stop()
            self.stack.setCurrentWidget(self.empty)
            self.status.setText("Projectladen geannuleerd")
            self.load_progress.emit(0, "Projectladen geannuleerd")

        def _project_loaded_guarded(
            self,
            generation: int,
            workspace: IntegratedProjectWorkspace,
        ) -> None:
            if generation != self._load_generation:
                workspace.close()
                return
            self._project_loaded(workspace)

        def _project_preview_guarded(self, generation: int, load_result: Any) -> None:
            worker = self._worker
            try:
                if generation != self._load_generation:
                    return
                while self.host_layout.count():
                    item = self.host_layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()
                if os.environ.get("CWS_HEADLESS_GUI_SMOKE") == "1":
                    viewer = _HeadlessGuiSmokeViewer()
                else:
                    viewer = VtkRealProjectWidget(load_result.repository)
                viewer.load_scene(load_result.scene)
                self.viewer = viewer
                self._preview_result = load_result
                self.host_layout.addWidget(viewer)
                self.stack.setCurrentWidget(self.host)
                viewer.update()
                QtWidgets.QApplication.processEvents(
                    QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
                )
                self._load_progress_changed(66, "Eerste interactieve modelweergave gereed")
                QtCore.QTimer.singleShot(0, self._complete_preview_geometry)
            finally:
                if worker is not None:
                    worker.acknowledge_preview()

        def _complete_preview_geometry(self) -> None:
            viewer = self.viewer
            if viewer is None:
                return
            backend = getattr(viewer, "backend", None)
            set_filter = getattr(backend, "set_geometry_filter", None)
            if callable(set_filter):
                render_window = getattr(backend, "_render_window", None)
                if render_window is not None:
                    render_window.SetMultiSamples(
                        int(getattr(backend, "MIN_IDLE_MULTISAMPLES", 8))
                    )
                set_filter(None)
                viewer.controller.refresh_geometry(None)
                viewer.update()

        def _loading_tick(self) -> None:
            if self._load_job_id is None or not self._load_elapsed.isValid():
                self._load_heartbeat.stop()
                return
            seconds = max(0, self._load_elapsed.elapsed() // 1000)
            self.loading_elapsed.setText(f"Verstreken tijd: {seconds} s · verwerking draait op de achtergrond")
            value = self.loading_progress.value()
            self.loading_progress.setFormat(f"{value}% · {seconds} s")

        @QtCore.Slot(int, str)
        def _load_progress_changed(self, percent: int, message: str) -> None:
            self.loading_progress.setValue(max(0, min(100, int(percent))))
            self.loading_detail.setText(message)
            self.status.setText(message)
            self.load_progress.emit(percent, message)

        @QtCore.Slot(object)
        def _project_loaded(self, workspace: IntegratedProjectWorkspace) -> None:
            self._load_heartbeat.stop()
            self._load_progress_changed(84, "Viewer V15-renderer initialiseren")
            self.workspace = workspace
            preview_viewer = self.viewer if self._preview_result is workspace.load_result else None
            while self.host_layout.count():
                item = self.host_layout.takeAt(0)
                widget = item.widget()
                if widget is not None and widget is not preview_viewer:
                    widget.deleteLater()

            # Use exact source meshes when loaded; otherwise show deterministic
            # project envelopes and keep the evidence limitation visible.
            if preview_viewer is not None:
                viewer = preview_viewer
                display_evidence = "progressieve source/proxy meshrepository"
            elif os.environ.get("CWS_HEADLESS_GUI_SMOKE") == "1":
                viewer = _HeadlessGuiSmokeViewer()
                display_evidence = "headless GUI-integratierenderer"
            else:
                viewer = VtkRealProjectWidget(workspace.load_result.repository)
                display_evidence = (
                    "source/proxy meshrepository"
                    if len(workspace.load_result.repository)
                    else "Viewer V15 actief; geometrie wordt later/lazy geladen"
                )
            if preview_viewer is None:
                viewer.load_scene(workspace.load_result.scene)
            # Loading can complete before the native Qt/VTK surface has its
            # final size. Re-fit on the next event-loop turn so the first
            # visible frame uses the actual viewport.
            QtCore.QTimer.singleShot(
                0,
                lambda: (
                    viewer.controller.fit_all(),
                    viewer.update(),
                ) if self.workspace is workspace and self.viewer is viewer else None,
            )
            self._load_progress_changed(90, "Geometrie, camera en selectie koppelen")
            workspace.bind_controller(viewer.controller)
            self.viewer = viewer
            viewer.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            viewer.customContextMenuRequested.connect(self._viewer_context_menu)
            if hasattr(viewer, "node_picked"):
                viewer.node_picked.connect(
                    lambda node_id: workspace.interaction.select_nodes(
                        (str(node_id),), origin="viewer_pick"
                    )
                )

            splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            left = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
            self.tree = QtWidgets.QTreeWidget()
            self.tree.setHeaderLabels(["Projectobject", "Type", "Status"])
            self.tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            self.tree.setUniformRowHeights(True)
            self.tree.setAlternatingRowColors(True)
            self.tree.header().setSectionsMovable(True)
            self.tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.tree.customContextMenuRequested.connect(self._tree_context_menu)
            left.addWidget(self.tree)

            self.grid = ProfessionalPropertyGridPanel(
                workspace.interaction.grid_model,
                bridge=workspace.bridge,
                layout_store=GridLayoutStore(Path.home() / ".cws_convertor" / "grid_layouts"),
                layout_identity=GridLayoutIdentity(
                    "CWS", "default", workspace.project.project_id, "ProjectProductie"
                ),
            )
            left.addWidget(self.grid)
            left.setSizes([360, 520])
            splitter.addWidget(left)
            splitter.addWidget(viewer)

            right_tabs = QtWidgets.QTabWidget()
            self.properties = QtWidgets.QTreeWidget()
            self.properties.setHeaderLabels(["Eigenschap", "Waarde", "Herkomst", "Confidence"])
            right_tabs.addTab(self.properties, "Eigenschappen")
            self.accuracy = QtWidgets.QPlainTextEdit(); self.accuracy.setReadOnly(True)
            right_tabs.addTab(self.accuracy, "Accuracy / Debug")
            self.bom = QtWidgets.QPlainTextEdit(); self.bom.setReadOnly(True)
            right_tabs.addTab(self.bom, "BOM")
            self.viewer_tools = IntegratedViewerToolsPanel(workspace)
            self.viewer_tools.status_changed.connect(self.status.setText)
            right_tabs.addTab(self.viewer_tools, "Doorsnede / Meten")
            splitter.addWidget(right_tabs)
            splitter.setSizes([650, 1050, 430])
            self.host_layout.addWidget(splitter)

            # Publish the first interactive model frame before populating the
            # large tree/grid surfaces.  This is the explicit <=5 s contract.
            self.stack.setCurrentWidget(self.host)
            self._load_progress_changed(93, "Eerste interactieve modelweergave gereed")
            viewer.controller.fit_all()
            viewer.update()
            QtWidgets.QApplication.processEvents(
                QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            )

            self._populate_tree()
            self._populate_bom()
            self._load_progress_changed(97, "Modelstructuur, eigenschappen en BOM vullen")
            self.tree.itemSelectionChanged.connect(self._tree_selection_changed)
            self._interaction_unsubscribe = workspace.interaction.subscribe(
                self._interaction_selection_changed
            )
            self.grid.open_part_workbench_requested.connect(lambda _entity: self.open_exact_workbench())
            self.grid.application_action_requested.connect(self.action_requested)
            self.status.setText(
                f"{workspace.project.project_name} · {len(workspace.load_result.scene.nodes):,} nodes · "
                f"{len(workspace.interaction.grid_model.rows):,} gridregels · {display_evidence} · "
                f"identity audit PASS"
            )
            self._set_actions_enabled(True)
            self._load_progress_changed(100, "Project volledig geladen in Viewer V15")
            self.project_loaded.emit(str(workspace.project_path))
            self._preview_result = None
            if workspace.load_result.geometry_report.proxy_count:
                self._start_exact_geometry_upgrade(workspace)

        @QtCore.Slot(str)
        def _project_failed(self, message: str) -> None:
            self._load_heartbeat.stop()
            self.load_progress.emit(0, f"Project laden mislukt: {message}")
            self.status.setText(f"Project laden mislukt: {message}")
            self.stack.setCurrentWidget(self.empty)
            QtWidgets.QMessageBox.critical(self, "Project laden", message)

        def cancel_project_load(self) -> bool:
            active = self._load_job_id is not None or self._exact_job_id is not None
            if not active:
                return False
            self._load_generation += 1
            if self._worker is not None:
                self._worker.request_cancel()
            if self._exact_worker is not None:
                self._exact_worker.request_cancel()
            if self._job_manager is not None:
                if self._load_job_id is not None:
                    self._job_manager.cancel(self._load_job_id)
                if self._exact_job_id is not None:
                    self._job_manager.cancel(self._exact_job_id)
            self._load_job_id = None
            self._exact_job_id = None
            self._load_heartbeat.stop()
            if self.workspace is None:
                self.stack.setCurrentWidget(self.empty)
            self.status.setText("Projectladen geannuleerd")
            self.load_progress.emit(0, "Projectladen geannuleerd")
            return True

        def _start_exact_geometry_upgrade(self, workspace: IntegratedProjectWorkspace) -> None:
            if self._job_manager is None or workspace is not self.workspace:
                return
            generation = self._load_generation
            scheduler = getattr(self, "_geometry_priority_scheduler", None)
            if scheduler is None:
                scheduler = GeometryPriorityScheduler()
                self._geometry_priority_scheduler = scheduler
            worker = _ExactGeometryWorker(workspace, scheduler=scheduler)
            worker.batch_ready.connect(
                lambda values, value=generation: self._exact_geometry_batch(value, values)
            )
            worker.progress.connect(
                lambda percent, message, value=generation: self._exact_geometry_progress(value, percent, message)
            )
            worker.completed.connect(
                lambda report, value=generation: self._exact_geometry_completed(value, report)
            )
            worker.cancelled.connect(
                lambda value=generation: self._exact_geometry_cancelled(value)
            )
            worker.failed.connect(
                lambda message, value=generation: self._exact_geometry_failed(value, message)
            )
            worker.finished.connect(worker.deleteLater)
            self._exact_worker = worker
            self._exact_job_id = self._job_manager.submit(
                "project_exact_geometry_upgrade",
                lambda context: worker.run(context),
                description=f"Exacte viewergeometrie: {workspace.project_path.name}",
                project_id=str(workspace.project_path),
                metadata={"progressive": True, "replaces_proxies": True},
                max_retries=0,
            )

        def _exact_geometry_batch(self, generation: int, geometry_ids: Any) -> None:
            if generation != self._load_generation or self.viewer is None:
                return
            from cws_viewer.performance import LoadingPerformancePolicy,SceneUploadQueue
            values=tuple(geometry_ids);queue=getattr(self,'_scene_upload_queue',None)
            if queue is None:
                policy=LoadingPerformancePolicy.detect(len(values));queue=SceneUploadQueue(budget_ms=policy.scene_upload_budget_ms,batch_limit=policy.scene_upload_batch_limit)
                self._scene_upload_queue=queue;self._scene_upload_drain_scheduled=False
            queue.enqueue(generation,values)
            if not self._scene_upload_drain_scheduled:
                self._scene_upload_drain_scheduled=True;QtCore.QTimer.singleShot(0,self._drain_exact_geometry_uploads)

        def _drain_exact_geometry_uploads(self) -> None:
            import time
            self._scene_upload_drain_scheduled=False;queue=getattr(self,'_scene_upload_queue',None)
            if queue is None or self.viewer is None:return
            backend = getattr(self.viewer, "backend", None) or getattr(self.viewer, "_backend", None)
            if bool(getattr(backend, "interaction_quality_active", False)):
                self._scene_upload_drain_scheduled=True;QtCore.QTimer.singleShot(50,self._drain_exact_geometry_uploads);return
            frame_started=time.perf_counter();uploaded=0
            while (time.perf_counter()-frame_started)*1000.0<queue.budget_ms:
                geometry_ids=queue.claim(self._load_generation,max_items=1)
                if not geometry_ids:break
                started=time.perf_counter();self.viewer.controller.refresh_geometry(geometry_ids);queue.record_upload(1,(time.perf_counter()-started)*1000.0);uploaded+=1
            if uploaded:self.viewer.update()
            if queue.pending_count and not self._scene_upload_drain_scheduled:
                self._scene_upload_drain_scheduled=True;QtCore.QTimer.singleShot(0,self._drain_exact_geometry_uploads)

        def _exact_geometry_progress(self, generation: int, percent: int, message: str) -> None:
            if generation != self._load_generation:
                return
            self.status.setText(f"{message} · model blijft interactief")
            self.load_progress.emit(percent, message)

        def _exact_geometry_completed(self, generation: int, report: Any) -> None:
            if generation != self._load_generation:
                return
            failures = tuple(report.get("failed") or ())
            upgraded = int(report.get("upgraded") or 0)
            requested = int(report.get("requested") or 0)
            source_scene = report.get("source_appearance_scene")
            if source_scene is not None and self.workspace is not None and self.viewer is not None:
                from dataclasses import replace

                load_result = self.workspace.load_result
                self.workspace.load_result = replace(
                    load_result,
                    scene=source_scene,
                    scene_report=report.get("source_appearance_report") or load_result.scene_report,
                )
                self.viewer.controller.replace_scene_preserving_state(source_scene)
                self.viewer.update()
            self._exact_job_id = None
            self._exact_worker = None
            if failures:
                self.status.setText(
                    f"Brongeometrie {upgraded:,}/{requested:,} · {len(failures):,} onderdelen behouden veilige proxy"
                )
            else:
                self.status.setText(
                    f"Brongeometrie compleet · {upgraded:,}/{requested:,} exacte meshes"
                )

        def _exact_geometry_cancelled(self, generation: int) -> None:
            if generation == self._load_generation:
                self._exact_job_id = None
                self._exact_worker = None
                self.status.setText("Exacte geometrie-upgrade geannuleerd; interactief model blijft beschikbaar")

        def _exact_geometry_failed(self, generation: int, message: str) -> None:
            if generation == self._load_generation:
                self._exact_job_id = None
                self._exact_worker = None
                self.status.setText(f"Exacte geometrie-upgrade mislukt: {message}")

        def _set_navigation_mode(self, mode: Any, label: str) -> None:
            if self.viewer is None:
                return
            self.viewer.set_navigation_mode(mode)
            self.viewer.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)
            self.status.setText(label)

        def _activate_zoom_area(self) -> None:
            if self.viewer is None:
                return
            if hasattr(self.viewer, "set_zoom_area"):
                self.viewer.set_zoom_area(True)
            elif hasattr(self.viewer, "set_area_selection"):
                self.viewer.set_area_selection(True)
            self.viewer.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)
            self.status.setText("Zoomvenster: sleep een kader in de viewer")

        def _set_model_transparency(self, value: int) -> None:
            if self.viewer is None or self.viewer.controller.scene is None:
                return
            node_ids = self.viewer.controller.index.renderable_node_ids
            self.viewer.controller.set_transparency(node_ids, float(value) / 100.0)

        def _populate_tree(self) -> None:
            assert self.workspace is not None
            self.tree.clear(); self._tree_items.clear()
            self._grid_entity_ids = {
                str(row.entity_id) for row in self.workspace.interaction.grid_model.rows
            }
            pending = list(self.workspace.load_result.scene.nodes)
            created: dict[str, Any] = {}
            while pending:
                progress = False
                for node in tuple(pending):
                    parent = created.get(node.parent_node_id) if node.parent_node_id else None
                    if node.parent_node_id and parent is None:
                        continue
                    item = QtWidgets.QTreeWidgetItem(parent or self.tree)
                    item.setText(0, node.name or node.entity_id)
                    item.setText(1, node.kind.value)
                    item.setText(2, "selecteerbaar" if node.selectable else "groep")
                    item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node.entity_id)
                    item.setData(1, QtCore.Qt.ItemDataRole.UserRole, node.node_id)
                    created[node.node_id] = item
                    self._tree_items[node.entity_id] = item
                    pending.remove(node); progress = True
                if not progress:
                    # Defensive fallback for malformed parent references; scene
                    # validation should normally reject this before UI creation.
                    for node in pending:
                        item = QtWidgets.QTreeWidgetItem(self.tree)
                        item.setText(0, node.name or node.entity_id)
                        item.setText(1, node.kind.value)
                        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node.entity_id)
                        item.setData(1, QtCore.Qt.ItemDataRole.UserRole, node.node_id)
                        self._tree_items[node.entity_id] = item
                    break
            self.tree.expandToDepth(1)

        def _populate_bom(self) -> None:
            assert self.workspace is not None
            snapshot = self.workspace.bom_snapshot
            lines = [
                f"Project: {snapshot.project_name}",
                f"BOM snapshot: {snapshot.snapshot_sha256}",
                "",
            ]
            for key, value in sorted(snapshot.summary.items()):
                lines.append(f"{key}: {value}")
            lines.extend(["", f"Production ready: {bool(snapshot.validation and snapshot.validation.production_ready)}"])
            if snapshot.validation:
                lines.extend(snapshot.validation.messages)
            self.bom.setPlainText("\n".join(map(str, lines)))

        def _tree_selection_changed(self) -> None:
            if self._syncing or self.workspace is None:
                return
            entity_ids = [
                str(item.data(0, QtCore.Qt.ItemDataRole.UserRole) or "")
                for item in self.tree.selectedItems()
            ]
            entity_ids = [item for item in entity_ids if item in self._grid_entity_ids]
            if entity_ids:
                self.workspace.interaction.select_entities(entity_ids, origin="project_tree")

        def _interaction_selection_changed(self, selection: Any) -> None:
            if self.workspace is None:
                return
            self._syncing = True
            try:
                self.tree.clearSelection()
                for entity_id in selection.entity_ids:
                    item = self._tree_items.get(entity_id)
                    if item is not None:
                        item.setSelected(True)
                blocker = QtCore.QSignalBlocker(self.grid.table.selectionModel())
                self.grid.select_entities(selection.entity_ids)
                del blocker
                self._populate_properties()
                if hasattr(self, "viewer_tools"):
                    self.viewer_tools.refresh()
            finally:
                self._syncing = False
            self.selection_changed.emit(selection)

        def _build_application_menu(self) -> Any:
            menu = QtWidgets.QMenu(self)
            for label, key in (
                ("Eigenschappen", "properties"),
                ("Bewerken", "edit"),
                ("Converteren", "convert"),
                ("Controleren", "validate"),
                ("PDF / Tekening", "pdf"),
                ("Profielen", "profiles"),
                ("Tekeningen", "drawings"),
                ("Scribing", "scribing"),
                ("Hoeveelheden / Excel", "quantities"),
                ("Exporteren", "export"),
            ):
                menu.addAction(label, lambda _checked=False, value=key: self.action_requested.emit(value))
            return menu

        def _selection_context_menu(self, global_position: Any) -> None:
            if self.workspace is None:
                return
            menu = self._build_application_menu()
            selected = tuple(self.workspace.interaction.selection.entity_ids)
            if selected:
                menu.addSeparator()
                menu.addAction("Verbergen", self._hide_selection)
                menu.addAction("Isoleren", lambda: self._isolate_selection(False))
                menu.addAction("Ghost context", lambda: self._isolate_selection(True))
                menu.addAction("Selectie passend", lambda: self._controller_call("fit_selection"))
            menu.exec(global_position)

        def _tree_context_menu(self, position: Any) -> None:
            item = self.tree.itemAt(position)
            if item is not None and not item.isSelected():
                self.tree.clearSelection()
                item.setSelected(True)
            self._selection_context_menu(self.tree.viewport().mapToGlobal(position))

        def _viewer_context_menu(self, position: Any) -> None:
            if self.viewer is not None:
                self._selection_context_menu(self.viewer.mapToGlobal(position))

        def _populate_properties(self) -> None:
            assert self.workspace is not None
            self.properties.clear()
            for record in self.workspace.interaction.properties_for_primary():
                item = QtWidgets.QTreeWidgetItem(self.properties)
                item.setText(0, record.label)
                item.setText(1, str(record.value))
                item.setText(2, str(record.provenance))
                item.setText(3, f"{record.confidence:.0%}" if record.confidence is not None else "")
            primary = self.workspace.interaction.selection.primary_entity_id
            if primary:
                try:
                    accuracy = self.workspace.interaction.accuracy_for_primary()
                    if accuracy is None:
                        self.accuracy.setPlainText("Geen accuracyrecord voor de huidige selectie")
                    else:
                        self.accuracy.setPlainText(
                            "\n".join(f"{key}: {value}" for key, value in accuracy.to_dict().items())
                        )
                except Exception as exc:
                    self.accuracy.setPlainText(f"Accuracy niet beschikbaar: {exc}")
            else:
                self.accuracy.clear()

        def _controller_call(self, name: str, *args: Any) -> None:
            if self.workspace is None:
                return
            controller = self.workspace.controller
            if name == "set_standard_view" and args:
                from cws_viewer.contracts.enums import StandardView
                getattr(controller, name)(StandardView(str(args[0])))
            else:
                getattr(controller, name)(*args)

        def _selected_nodes(self) -> tuple[str, ...]:
            if self.workspace is None:
                return ()
            return self.workspace.controller.get_selection()

        def _hide_selection(self) -> None:
            nodes = self._selected_nodes()
            if nodes:
                self.workspace.controller.hide(nodes)

        def _isolate_selection(self, ghost: bool) -> None:
            nodes = self._selected_nodes()
            if nodes:
                self.workspace.controller.isolate(nodes, ghost_context=ghost)
                self.workspace.controller.fit_all()

        def open_exact_workbench(self) -> None:
            if self.workspace is None:
                return
            entity_id = self.workspace.interaction.selection.primary_entity_id
            if not entity_id:
                QtWidgets.QMessageBox.information(self, "Exact Part Workbench", "Selecteer eerst één onderdeel.")
                return
            result = self.workspace.open_exact_part(entity_id)
            if not result.available:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Exact Part Workbench geblokkeerd",
                    "\n".join([result.status, *result.blocking_codes, *result.notes]),
                )
                return
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"Experimental Exact Part Workbench — {entity_id}")
            dialog.resize(1500, 900)
            layout = QtWidgets.QVBoxLayout(dialog)
            banner = QtWidgets.QLabel(
                "EXPERIMENTEEL · productie blijft format-specifiek geblokkeerd tot canonical rebuild en roundtrip groen zijn"
            )
            banner.setStyleSheet("background:#6c4e18;color:#fff2cf;padding:7px;font-weight:600")
            layout.addWidget(banner)
            layout.addWidget(ExactPartWorkbenchPanel(result.service), 1)
            dialog.exec()

        def export_bom(self) -> None:
            if self.workspace is None:
                return
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "BOM-uitvoermap")
            if not directory:
                return
            outputs = export_bom_package(self.workspace.bom_snapshot, directory)
            QtWidgets.QMessageBox.information(
                self, "BOM export", f"{len(outputs)} bestanden gemaakt in:\n{directory}"
            )

        def close_project(self) -> None:
            if self._worker is not None:
                self._worker.request_cancel()
            if self._exact_worker is not None:
                self._exact_worker.request_cancel()
            self._load_generation += 1
            if self._load_job_id is not None and self._job_manager is not None:
                self._job_manager.cancel(self._load_job_id)
                self._load_job_id = None
            if self._exact_job_id is not None and self._job_manager is not None:
                self._job_manager.cancel(self._exact_job_id)
                self._exact_job_id = None
            self._worker = None
            self._exact_worker = None
            self._preview_result = None
            if self._interaction_unsubscribe is not None:
                self._interaction_unsubscribe()
                self._interaction_unsubscribe = None
            if self.workspace is not None:
                self.workspace.close()
                self.workspace = None
                self.project_closed.emit()
            if self.viewer is not None:
                try:
                    self.viewer.close()
                finally:
                    self.viewer = None
            self._tree_items.clear()
            self._grid_entity_ids.clear()
            self._set_actions_enabled(False)
            self.transparency_slider.blockSignals(True)
            self.transparency_slider.setValue(0)
            self.transparency_slider.blockSignals(False)
            self.stack.setCurrentWidget(self.empty)
            self.status.setText("Open een .cwscproj-project")

        def closeEvent(self, event: Any) -> None:
            self.close_project()
            super().closeEvent(event)

else:

    class IntegratedProjectWorkspaceWidget:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["IntegratedProjectWorkspaceWidget"]

# _CWS_DETACHED_VIEWER_PATCH_V1
# Keep the production viewer available as a first-class, independent review window.
if "IntegratedProjectWorkspaceWidget" in globals():
    _cws_workspace_widget_init = IntegratedProjectWorkspaceWidget.__init__

    def _cws_workspace_widget_init_with_detached_viewer(self, *args, **kwargs):
        _cws_workspace_widget_init(self, *args, **kwargs)
        self._detached_viewer_windows = []
        host = getattr(self, "host", None)
        if host is not None:
            host.setMinimumHeight(360)
            host.setSizePolicy(host.sizePolicy().horizontalPolicy(), host.sizePolicy().verticalPolicy())
        actions_button = getattr(self, "actions_button", None)
        menu = actions_button.menu() if actions_button is not None else None
        if menu is not None:
            from PySide6.QtGui import QAction, QKeySequence

            menu.addSeparator()
            detached_action = QAction("Viewer in apart venster", self)
            detached_action.setShortcut(QKeySequence("F11"))
            detached_action.triggered.connect(self.open_detached_viewer)
            menu.addAction(detached_action)
            self._detached_viewer_action = detached_action

    def _cws_open_detached_viewer(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QMessageBox
        from cws_viewer.ui_qt.cockpit_trimble_feel_v2 import (
            CwsViewerV15TrimbleFeelV2CockpitWindow,
        )

        workspace = getattr(self, "workspace", None)
        load_result = getattr(workspace, "load_result", None)
        scene = getattr(load_result, "scene", None)
        if scene is None:
            QMessageBox.information(self, "Viewer V15", "Open eerst een project met 3D-geometrie.")
            return None
        # Keep the independent review window on the same V15 renderer and
        # expose its complete selection, views, measurement and review cockpit.
        window = CwsViewerV15TrimbleFeelV2CockpitWindow(load_result)
        project_name = getattr(getattr(workspace, "document", None), "project_name", "Project")
        window.setWindowTitle(f"CWS Convertor Viewer V15 - {project_name}")
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._detached_viewer_windows.append(window)

        selection = getattr(getattr(workspace, "interaction", None), "selection", None)
        entity_ids = tuple(getattr(selection, "entity_ids", ()) or ())
        if entity_ids:
            try:
                window.interaction.select_entities(entity_ids, origin="convertor")
                window.viewer.controller.fit_selection()
            except Exception:
                pass

        def forget_window(*_):
            if window in self._detached_viewer_windows:
                self._detached_viewer_windows.remove(window)

        window.destroyed.connect(forget_window)
        window.showMaximized()
        return window

    IntegratedProjectWorkspaceWidget.open_detached_viewer = _cws_open_detached_viewer
    IntegratedProjectWorkspaceWidget.__init__ = _cws_workspace_widget_init_with_detached_viewer
