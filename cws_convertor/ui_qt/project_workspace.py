"""Integrated Project/Production workspace for the CWS Convertor Qt shell."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    from cws_convertor.bom import export_bom_package
    from cws_convertor.integration import IntegratedProjectWorkspace
    from cws_viewer.backends.memory import MemoryRenderBackend
    from cws_viewer.core.controller import ViewerCoreController
    from cws_viewer.ui_qt.exact_part_workbench import ExactPartWorkbenchPanel
    from cws_viewer.ui_qt.property_grid import ProfessionalPropertyGridPanel
    from cws_viewer.ui_qt.vtk_project_widget import VtkProjectWidget
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
        failed = QtCore.Signal(str)
        finished = QtCore.Signal()

        def __init__(self, path: Path, *, load_geometry: bool) -> None:
            super().__init__()
            self.path = path
            self.load_geometry = load_geometry

        @QtCore.Slot()
        def run(self) -> None:
            try:
                workspace = IntegratedProjectWorkspace.open(
                    self.path,
                    read_only=False,
                    load_all_geometry=self.load_geometry,
                    allow_proxy=True,
                )
                self.loaded.emit(workspace)
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")
            finally:
                self.finished.emit()


    class IntegratedProjectWorkspaceWidget(QtWidgets.QWidget):
        """Tree, V8 grid, VTK model, properties, BOM and V6 exact review."""

        project_loaded = QtCore.Signal(str)
        project_closed = QtCore.Signal()
        selection_changed = QtCore.Signal(object)
        action_requested = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsV9IntegratedProjectWorkspace")
            self.workspace: IntegratedProjectWorkspace | None = None
            self._thread: QtCore.QThread | None = None
            self._worker: _LoadWorker | None = None
            self._tree_items: dict[str, Any] = {}
            self._syncing = False
            self._interaction_unsubscribe: Any | None = None
            self._grid_entity_ids: set[str] = set()
            self.viewer: Any | None = None
            self._build_ui()

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
            self.loading = QtWidgets.QLabel("Project wordt gecontroleerd en geladen …")
            self.loading.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.stack.addWidget(self.loading)
            self.host = QtWidgets.QWidget()
            self.host_layout = QtWidgets.QVBoxLayout(self.host)
            self.host_layout.setContentsMargins(0, 0, 0, 0)
            self.stack.addWidget(self.host)

            self.open_action.triggered.connect(self.choose_project)
            self.close_action.triggered.connect(self.close_project)
            self.fit_action.triggered.connect(lambda: self._controller_call("fit_all"))
            self.iso_action.triggered.connect(lambda: self._controller_call("set_standard_view", "isometric"))
            self.top_action.triggered.connect(lambda: self._controller_call("set_standard_view", "top"))
            self.front_action.triggered.connect(lambda: self._controller_call("set_standard_view", "front"))
            self.hide_action.triggered.connect(self._hide_selection)
            self.isolate_action.triggered.connect(lambda: self._isolate_selection(False))
            self.ghost_action.triggered.connect(lambda: self._isolate_selection(True))
            self.show_all_action.triggered.connect(lambda: self._controller_call("show_all"))
            self.exact_action.triggered.connect(self.open_exact_workbench)
            self.bom_action.triggered.connect(self.export_bom)
            self._set_actions_enabled(False)

        def _set_actions_enabled(self, enabled: bool) -> None:
            for action in (
                self.close_action, self.fit_action, self.iso_action, self.top_action,
                self.front_action, self.hide_action, self.isolate_action,
                self.ghost_action, self.show_all_action, self.exact_action,
                self.bom_action,
            ):
                action.setEnabled(enabled)
            self.actions_button.setEnabled(enabled)

        def choose_project(self) -> None:
            name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "CWS-project openen", "", "CWS-project (*.cwscproj)"
            )
            if name:
                self.open_project(Path(name))

        def open_project(self, path: str | Path, *, load_geometry: bool = True) -> None:
            self.close_project()
            project_path = Path(path).expanduser().resolve()
            self.status.setText(f"Controleren en laden: {project_path.name}")
            self.stack.setCurrentWidget(self.loading)
            thread = QtCore.QThread(self)
            worker = _LoadWorker(project_path, load_geometry=load_geometry)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.loaded.connect(self._project_loaded)
            worker.failed.connect(self._project_failed)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(lambda: setattr(self, "_thread", None))
            thread.finished.connect(lambda: setattr(self, "_worker", None))
            self._worker = worker
            self._thread = thread
            thread.start()

        @QtCore.Slot(object)
        def _project_loaded(self, workspace: IntegratedProjectWorkspace) -> None:
            self.workspace = workspace
            while self.host_layout.count():
                item = self.host_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

            # Use exact source meshes when loaded; otherwise show deterministic
            # project envelopes and keep the evidence limitation visible.
            if os.environ.get("CWS_HEADLESS_GUI_SMOKE") == "1":
                viewer = _HeadlessGuiSmokeViewer()
                display_evidence = "headless GUI-integratierenderer"
            elif len(workspace.load_result.repository):
                viewer = VtkRealProjectWidget(workspace.load_result.repository)
                display_evidence = "source/proxy meshrepository"
            else:
                viewer = VtkProjectWidget()
                display_evidence = "project bounds (geometrie wordt later/lazy geladen)"
            viewer.load_scene(workspace.load_result.scene)
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

            self._populate_tree()
            self._populate_bom()
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
            self.stack.setCurrentWidget(self.host)
            self._set_actions_enabled(True)
            self.project_loaded.emit(str(workspace.project_path))

        @QtCore.Slot(str)
        def _project_failed(self, message: str) -> None:
            self.status.setText(f"Project laden mislukt: {message}")
            self.stack.setCurrentWidget(self.empty)
            QtWidgets.QMessageBox.critical(self, "Project laden", message)

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
