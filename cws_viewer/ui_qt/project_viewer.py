"""Professional Qt shell for the CWS Viewer V4 project workspace.

The window keeps the 3D model central while exposing compact, deterministic
controls for camera, render mode, colour schemes, visibility sets, viewpoints,
workspace persistence and Accuracy/Debug information.  It is a display and
review surface only: no method in this module can release production output or
mutate canonical manufacturing geometry.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from cws_viewer.adapters.project_scene_loader import ProjectSceneLoadResult, ProjectSceneLoader
from cws_viewer.contracts.enums import (
    BackgroundTheme,
    ColorScheme,
    ProjectionType,
    RenderMode,
    StandardView,
)
from cws_viewer.contracts.state import ScreenshotOptions
from cws_viewer.core.project_interaction import InteractionSelection, ProjectInteractionModel
from cws_viewer.errors import ViewerError
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_real_project_widget import VtkRealProjectWidget

_QSS = """
QMainWindow { background: #101720; color: #e7eef5; }
QToolBar { background: #182332; border-bottom: 1px solid #2b3d50; spacing: 4px; padding: 4px; }
QToolButton, QPushButton { background: #23364a; color: #edf4f9; border: 1px solid #34516b; border-radius: 4px; padding: 5px 9px; }
QToolButton:hover, QPushButton:hover { background: #2e4b67; }
QToolButton:checked, QPushButton:checked { background: #176896; border-color: #40a5d8; }
QLineEdit, QComboBox, QDoubleSpinBox { background: #121d28; color: #e9f1f7; border: 1px solid #31465a; border-radius: 4px; padding: 5px; }
QTreeWidget, QTableWidget, QListWidget { background: #141e29; alternate-background-color: #182431; color: #dfe9f2; border: 1px solid #2a3a4a; gridline-color: #263747; }
QTreeWidget::item:selected, QTableWidget::item:selected, QListWidget::item:selected { background: #1b6798; color: white; }
QHeaderView::section { background: #223447; color: #eef5fa; border: 0; border-right: 1px solid #31475b; padding: 6px; }
QDockWidget::title { background: #1d2a39; color: #f1f6fa; padding: 7px; }
QTabWidget::pane { border: 1px solid #2a3a4a; background: #141e29; }
QTabBar::tab { background: #1c2a39; color: #cbd8e3; padding: 7px 10px; border: 1px solid #2b3d50; }
QTabBar::tab:selected { background: #24516f; color: #ffffff; }
QStatusBar { background: #0c131b; color: #b4c3d0; }
QLabel#statusPill { border-radius: 8px; padding: 4px 9px; background: #225b45; color: #ddfff1; }
QLabel#warningPill { border-radius: 8px; padding: 4px 9px; background: #6c4e18; color: #fff2cf; }
QLabel#accuracyPass { color: #66d79b; font-weight: 600; }
QLabel#accuracyWarning { color: #ffbf54; font-weight: 600; }
QLabel#accuracyFail { color: #ff7479; font-weight: 600; }
"""


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class RealProjectViewerWindow(QtWidgets.QMainWindow):
        """CWS Viewer V4 professional project-viewing workspace."""

        def __init__(self, load_result: ProjectSceneLoadResult) -> None:
            super().__init__()
            self.load_result = load_result
            self.setObjectName("cwsViewerV4ProfessionalWindow")
            self.setWindowTitle("CWS Viewer V4 — professioneel projectmodel")
            self.resize(1680, 980)
            self.setStyleSheet(_QSS)
            self._syncing = False
            self._syncing_controls = False
            self._tree_items: dict[str, Any] = {}
            self._grid_row_by_entity: dict[str, int] = {}
            self._workspace_path = load_result.project_path.with_suffix(
                load_result.project_path.suffix + ".cwsview.json"
            )
            self._qt_settings = QtCore.QSettings("CWS", "CWS Viewer V4")

            self.viewer = VtkRealProjectWidget(load_result.repository, self)
            self.setCentralWidget(self.viewer)
            self.viewer.load_scene(load_result.scene)
            self.interaction = ProjectInteractionModel(
                self.viewer.controller,
                load_result.project,
                mesh_repository=load_result.repository,
            )
            self._unsubscribe = self.interaction.subscribe(self._on_interaction_selection)

            self._tree = self._create_tree_dock()
            self._grid = self._create_grid_dock()
            self._properties = self._create_properties_dock()
            self._workspace_tabs = self._create_workspace_dock()
            self._search = self._create_search_toolbar()
            self._create_view_toolbar()
            self._create_workspace_toolbar()

            self._status = QtWidgets.QLabel()
            self._status.setObjectName("statusPill")
            self._limitations = QtWidgets.QLabel()
            self._limitations.setObjectName("warningPill")
            self.statusBar().addPermanentWidget(self._limitations)
            self.statusBar().addPermanentWidget(self._status)

            self._populate_tree()
            self._populate_grid()
            self._update_status()
            self._refresh_workspace_lists()
            self._restore_qt_layout()
            self._restore_workspace_if_available()

            self._tree.itemSelectionChanged.connect(self._on_tree_selection)
            self._grid.itemSelectionChanged.connect(self._on_grid_selection)
            self._search.textChanged.connect(self._apply_search)
            self.viewer.node_picked.connect(
                lambda node_id: self.statusBar().showMessage(
                    f"3D-selectie: {node_id}", 3000
                )
            )

        # ------------------------------------------------------------------
        # Shell construction
        # ------------------------------------------------------------------
        def _dock(self, title: str, name: str, widget: Any, area: Any, width: int) -> Any:
            dock = QtWidgets.QDockWidget(title, self)
            dock.setObjectName(name)
            dock.setWidget(widget)
            dock.setMinimumWidth(width)
            self.addDockWidget(area, dock)
            return widget

        def _create_tree_dock(self):
            tree = QtWidgets.QTreeWidget()
            tree.setHeaderLabels(["Projectobject", "Type", "Status"])
            tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            tree.setUniformRowHeights(True)
            tree.setAlternatingRowColors(True)
            tree.header().setSectionsMovable(True)
            return self._dock(
                "Projectstructuur",
                "cwsV4ProjectTreeDock",
                tree,
                QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                365,
            )

        def _create_grid_dock(self):
            grid = QtWidgets.QTableWidget()
            columns = self.interaction.grid_model.columns
            grid.setColumnCount(len(columns))
            grid.setHorizontalHeaderLabels([column.label for column in columns])
            grid.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            grid.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            grid.setSortingEnabled(True)
            grid.setAlternatingRowColors(True)
            grid.verticalHeader().hide()
            grid.horizontalHeader().setSectionsMovable(True)
            grid.horizontalHeader().setStretchLastSection(False)
            grid.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            grid.customContextMenuRequested.connect(self._grid_context_menu)
            dock = QtWidgets.QDockWidget("Onderdelen en merken", self)
            dock.setObjectName("cwsV4ProjectGridDock")
            dock.setWidget(grid)
            dock.setMinimumHeight(260)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, dock)
            return grid

        def _create_properties_dock(self):
            tree = QtWidgets.QTreeWidget()
            tree.setHeaderLabels(["Eigenschap", "Waarde", "Herkomst", "Confidence"])
            tree.setAlternatingRowColors(True)
            tree.setUniformRowHeights(True)
            tree.header().setSectionsMovable(True)
            return self._dock(
                "Eigenschappen en herkomst",
                "cwsV4PropertiesDock",
                tree,
                QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                430,
            )

        def _button_row(self, *buttons: tuple[str, Callable[[], None]]) -> Any:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)
            layout.setSpacing(5)
            for text, handler in buttons:
                button = QtWidgets.QPushButton(text)
                button.clicked.connect(handler)
                layout.addWidget(button)
            layout.addStretch(1)
            return widget

        def _create_workspace_dock(self):
            tabs = QtWidgets.QTabWidget()
            tabs.setObjectName("cwsV4WorkspaceTabs")

            viewpoints_page = QtWidgets.QWidget()
            viewpoints_layout = QtWidgets.QVBoxLayout(viewpoints_page)
            viewpoints_layout.setContentsMargins(4, 4, 4, 4)
            self._viewpoint_list = QtWidgets.QListWidget()
            self._viewpoint_list.itemDoubleClicked.connect(
                lambda _item: self._activate_selected_viewpoint()
            )
            viewpoints_layout.addWidget(self._viewpoint_list)
            viewpoints_layout.addWidget(
                self._button_row(
                    ("Opslaan", self._save_viewpoint_dialog),
                    ("Activeren", self._activate_selected_viewpoint),
                    ("Verwijderen", self._delete_selected_viewpoint),
                )
            )
            tabs.addTab(viewpoints_page, "Viewpoints")

            visibility_page = QtWidgets.QWidget()
            visibility_layout = QtWidgets.QVBoxLayout(visibility_page)
            visibility_layout.setContentsMargins(4, 4, 4, 4)
            self._visibility_list = QtWidgets.QListWidget()
            self._visibility_list.itemDoubleClicked.connect(
                lambda _item: self._activate_selected_visibility_set()
            )
            visibility_layout.addWidget(self._visibility_list)
            visibility_layout.addWidget(
                self._button_row(
                    ("Opslaan", self._save_visibility_dialog),
                    ("Activeren", self._activate_selected_visibility_set),
                    ("Verwijderen", self._delete_selected_visibility_set),
                )
            )
            tabs.addTab(visibility_page, "Visibility")

            self._legend_tree = QtWidgets.QTreeWidget()
            self._legend_tree.setHeaderLabels(["Kleurregeling", "Aantal"])
            self._legend_tree.setAlternatingRowColors(True)
            tabs.addTab(self._legend_tree, "Legenda")

            accuracy_page = QtWidgets.QWidget()
            accuracy_layout = QtWidgets.QVBoxLayout(accuracy_page)
            accuracy_layout.setContentsMargins(4, 4, 4, 4)
            self._accuracy_status = QtWidgets.QLabel(
                "Selecteer een onderdeel voor Accuracy/Debug-informatie"
            )
            self._accuracy_tree = QtWidgets.QTreeWidget()
            self._accuracy_tree.setHeaderLabels(["Controle", "Waarde", "Status"])
            self._accuracy_tree.setAlternatingRowColors(True)
            accuracy_layout.addWidget(self._accuracy_status)
            accuracy_layout.addWidget(self._accuracy_tree)
            tabs.addTab(accuracy_page, "Accuracy")

            return self._dock(
                "Werkruimte",
                "cwsV4WorkspaceDock",
                tabs,
                QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                430,
            )

        def _create_search_toolbar(self):
            toolbar = self.addToolBar("Zoeken")
            toolbar.setObjectName("cwsV4SearchToolbar")
            toolbar.setMovable(False)
            toolbar.addWidget(QtWidgets.QLabel("Zoeken  "))
            search = QtWidgets.QLineEdit()
            search.setPlaceholderText("Merk, positie, profiel, materiaal, ID …")
            search.setClearButtonEnabled(True)
            search.setMinimumWidth(350)
            toolbar.addWidget(search)
            return search

        def _action(
            self,
            toolbar: Any,
            text: str,
            slot: Any,
            shortcut: str | None = None,
            *,
            checkable: bool = False,
        ):
            action = QtGui.QAction(text, self)
            action.setCheckable(checkable)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(slot)
            toolbar.addAction(action)
            return action

        def _combo(
            self,
            toolbar: Any,
            label: str,
            values: tuple[tuple[str, str], ...],
            handler: Callable[[int], None],
            *,
            width: int = 125,
        ) -> Any:
            toolbar.addWidget(QtWidgets.QLabel(label))
            combo = QtWidgets.QComboBox()
            combo.setMinimumWidth(width)
            for display, value in values:
                combo.addItem(display, value)
            combo.currentIndexChanged.connect(handler)
            toolbar.addWidget(combo)
            return combo

        def _create_view_toolbar(self) -> None:
            toolbar = self.addToolBar("Viewer")
            toolbar.setObjectName("cwsV4ViewerToolbar")
            toolbar.setMovable(False)
            controller = self.viewer.controller
            self._action(toolbar, "Fit", controller.fit_all, "F")
            self._action(toolbar, "Fit selectie", controller.fit_selection, "Shift+F")

            self._view_combo = self._combo(
                toolbar,
                "Aanzicht ",
                (
                    ("Isometrisch", StandardView.ISOMETRIC.value),
                    ("Voor", StandardView.FRONT.value),
                    ("Achter", StandardView.BACK.value),
                    ("Links", StandardView.LEFT.value),
                    ("Rechts", StandardView.RIGHT.value),
                    ("Boven", StandardView.TOP.value),
                    ("Onder", StandardView.BOTTOM.value),
                ),
                self._on_standard_view_changed,
                width=112,
            )
            self._projection_combo = self._combo(
                toolbar,
                "Projectie ",
                (
                    ("Perspectief", ProjectionType.PERSPECTIVE.value),
                    ("Orthografisch", ProjectionType.ORTHOGRAPHIC.value),
                ),
                self._on_projection_changed,
                width=118,
            )
            self._render_combo = self._combo(
                toolbar,
                "Weergave ",
                (
                    ("Origineel", ""),
                    ("Shaded", RenderMode.SHADED.value),
                    ("Shaded + randen", RenderMode.SHADED_EDGES.value),
                    ("Wireframe", RenderMode.WIREFRAME.value),
                ),
                self._on_render_mode_changed,
                width=135,
            )
            self._background_combo = self._combo(
                toolbar,
                "Achtergrond ",
                (
                    ("Donker", BackgroundTheme.DARK.value),
                    ("Slate", BackgroundTheme.SLATE.value),
                    ("Licht", BackgroundTheme.LIGHT.value),
                ),
                self._on_background_changed,
                width=90,
            )

            toolbar.addSeparator()
            self._action(toolbar, "Verberg", self._hide_selected, "H")
            self._action(toolbar, "Isoleer", self._isolate_selected, "I")
            self._action(toolbar, "Ghost", self._ghost_selected, "G")
            self._action(toolbar, "Alles tonen", controller.show_all, "A")

            toolbar.addWidget(QtWidgets.QLabel("Transparantie "))
            self._transparency = QtWidgets.QDoubleSpinBox()
            self._transparency.setRange(0.0, 95.0)
            self._transparency.setDecimals(0)
            self._transparency.setSingleStep(5.0)
            self._transparency.setSuffix(" %")
            self._transparency.setValue(50.0)
            self._transparency.setMaximumWidth(85)
            toolbar.addWidget(self._transparency)
            self._action(toolbar, "Toepassen", self._apply_transparency_to_selection)
            self._action(toolbar, "Reset", controller.reset_styles)

        def _create_workspace_toolbar(self) -> None:
            toolbar = self.addToolBar("Werkruimte")
            toolbar.setObjectName("cwsV4WorkspaceToolbar")
            toolbar.setMovable(False)

            self._color_combo = self._combo(
                toolbar,
                "Kleuren ",
                (
                    ("Origineel", ColorScheme.ORIGINAL.value),
                    ("Categorie", ColorScheme.CATEGORY.value),
                    ("Materiaal", ColorScheme.MATERIAL.value),
                    ("Profiel", ColorScheme.PROFILE.value),
                    ("Status", ColorScheme.STATUS.value),
                    ("Fase", ColorScheme.PHASE.value),
                    ("Bronmodel", ColorScheme.SOURCE_MODEL.value),
                    ("Assembly", ColorScheme.ASSEMBLY.value),
                    ("Monochroom", ColorScheme.MONOCHROME.value),
                ),
                self._on_color_scheme_changed,
                width=118,
            )
            self._accuracy_action = self._action(
                toolbar,
                "Accuracy/Debug",
                self._toggle_accuracy_mode,
                "Ctrl+D",
                checkable=True,
            )
            toolbar.addSeparator()
            self._action(toolbar, "Viewpoint", self._save_viewpoint_dialog, "Ctrl+B")
            self._action(toolbar, "Visibility set", self._save_visibility_dialog)
            self._action(toolbar, "Screenshot", self._save_screenshot_dialog, "Ctrl+Shift+S")
            self._action(toolbar, "Werkruimte opslaan", self._save_workspace_now, "Ctrl+S")

        # ------------------------------------------------------------------
        # Data population and selection synchronisation
        # ------------------------------------------------------------------
        def _node_display_status(self, node: Any) -> str:
            if not node.geometry_id:
                return "groep"
            mesh = self.load_result.repository.get(node.geometry_id)
            if mesh is None:
                return "deferred"
            exactness = str(getattr(mesh, "exactness", "") or "")
            return {
                "source_tessellation": "bronmesh",
                "display_approximation": "benadering",
                "display_proxy": "proxy",
            }.get(exactness, exactness or "geladen")

        def _populate_tree(self) -> None:
            index = self.viewer.controller.index
            self._tree.clear()
            self._tree_items.clear()

            def add(node_id: str, parent: Any | None) -> None:
                node = index.node(node_id)
                item = QtWidgets.QTreeWidgetItem(
                    [node.name, node.kind.value, self._node_display_status(node)]
                )
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node_id)
                if parent is None:
                    self._tree.addTopLevelItem(item)
                else:
                    parent.addChild(item)
                self._tree_items[node_id] = item
                for child in index.children_by_parent.get(node_id, ()):
                    add(child, item)

            for root in index.root_node_ids:
                add(root, None)
            self._tree.expandToDepth(1)
            self._tree.resizeColumnToContents(0)

        def _populate_grid(self, rows: tuple[Any, ...] | None = None) -> None:
            rows = rows if rows is not None else self.interaction.grid_model.rows
            columns = self.interaction.grid_model.columns
            self._grid.setSortingEnabled(False)
            self._grid.setRowCount(len(rows))
            self._grid_row_by_entity.clear()
            for row_index, row in enumerate(rows):
                self._grid_row_by_entity[row.entity_id] = row_index
                for column_index, column in enumerate(columns):
                    value = row.get(column.key, "")
                    item = QtWidgets.QTableWidgetItem(str(value))
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, row.entity_id)
                    self._grid.setItem(row_index, column_index, item)
            self._grid.setSortingEnabled(True)
            self._grid.resizeColumnsToContents()

        def _grid_context_menu(self, position: Any) -> None:
            menu = QtWidgets.QMenu(self)
            menu.addAction("Optimale kolombreedte", self._grid.resizeColumnsToContents)
            menu.addAction("Alle kolommen tonen", self._show_all_grid_columns)
            submenu = menu.addMenu("Velden")
            for column_index, column in enumerate(self.interaction.grid_model.columns):
                action = submenu.addAction(column.label)
                action.setCheckable(True)
                action.setChecked(not self._grid.isColumnHidden(column_index))
                action.toggled.connect(
                    lambda visible, index=column_index: self._grid.setColumnHidden(
                        index, not visible
                    )
                )
            menu.exec(self._grid.viewport().mapToGlobal(position))

        def _show_all_grid_columns(self) -> None:
            for column in range(self._grid.columnCount()):
                self._grid.setColumnHidden(column, False)

        def _apply_search(self, text: str) -> None:
            rows = self.interaction.grid_model.query(text, sort_by="part_position")
            self._populate_grid(rows)
            hits = self.interaction.search(text, limit=500) if text.strip() else ()
            visible_nodes = {hit.node_id for hit in hits}
            keep_nodes = set(visible_nodes)
            index = self.viewer.controller.index
            for node_id in tuple(visible_nodes):
                keep_nodes.update(index.ancestors(node_id))
            for node_id, item in self._tree_items.items():
                item.setHidden(bool(text.strip()) and node_id not in keep_nodes)
            self.statusBar().showMessage(
                f"Zoekresultaten: {len(hits):,} · gridregels: {len(rows):,}"
            )

        def _selected_tree_nodes(self) -> tuple[str, ...]:
            return tuple(
                dict.fromkeys(
                    str(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
                    for item in self._tree.selectedItems()
                    if item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                )
            )

        def _selected_grid_entities(self) -> tuple[str, ...]:
            values: list[str] = []
            for item in self._grid.selectedItems():
                entity_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
                if entity_id:
                    values.append(str(entity_id))
            return tuple(dict.fromkeys(values))

        def _on_tree_selection(self) -> None:
            if self._syncing:
                return
            self.interaction.select_nodes(self._selected_tree_nodes(), origin="tree")

        def _on_grid_selection(self) -> None:
            if self._syncing:
                return
            entities = self._selected_grid_entities()
            if entities:
                self.interaction.select_entities(entities, origin="grid")

        def _on_interaction_selection(self, selection: InteractionSelection) -> None:
            self._syncing = True
            try:
                self._tree.clearSelection()
                for node_id in selection.node_ids:
                    item = self._tree_items.get(node_id)
                    if item is not None:
                        item.setSelected(True)
                        self._tree.scrollToItem(item)
                self._grid.clearSelection()
                for entity_id in selection.entity_ids:
                    row = self._grid_row_by_entity.get(entity_id)
                    if row is not None:
                        self._grid.selectRow(row)
                self._show_properties()
                self._show_accuracy()
            finally:
                self._syncing = False

        def _show_properties(self) -> None:
            records = self.interaction.properties_for_primary()
            self._properties.clear()
            groups: dict[str, Any] = {}
            for record in records:
                parent = groups.get(record.group)
                if parent is None:
                    parent = QtWidgets.QTreeWidgetItem([record.group, "", "", ""])
                    parent.setExpanded(True)
                    self._properties.addTopLevelItem(parent)
                    groups[record.group] = parent
                confidence = "" if record.confidence is None else f"{record.confidence:.0%}"
                parent.addChild(
                    QtWidgets.QTreeWidgetItem(
                        [
                            record.label,
                            f"{record.value} {record.unit}".strip(),
                            record.provenance,
                            confidence,
                        ]
                    )
                )
            self._properties.resizeColumnToContents(0)

        def _show_accuracy(self) -> None:
            self._accuracy_tree.clear()
            record = self.interaction.accuracy_for_primary()
            if record is None:
                self._accuracy_status.setText(
                    "Selecteer een onderdeel voor Accuracy/Debug-informatie"
                )
                self._accuracy_status.setObjectName("")
                return
            status_name = record.status.value.upper()
            self._accuracy_status.setText(
                f"{status_name} · {record.entity_id} · {record.mesh_exactness or 'geen meshstatus'}"
            )
            self._accuracy_status.setObjectName(
                {
                    "pass": "accuracyPass",
                    "warning": "accuracyWarning",
                    "fail": "accuracyFail",
                }.get(record.status.value, "accuracyWarning")
            )
            self._accuracy_status.style().unpolish(self._accuracy_status)
            self._accuracy_status.style().polish(self._accuracy_status)
            fields = (
                ("Source ID", record.source_entity_id, "info"),
                ("Internal ID", record.entity_id, "info"),
                ("Viewer node", record.node_id, "info"),
                ("Geometry ID", record.geometry_id, "info"),
                ("Units", record.scene_units, "info"),
                ("Geometry hash", record.geometry_hash, "info"),
                ("Manufacturing hash", record.manufacturing_hash, "info"),
                ("Mesh hash", record.mesh_hash, "info"),
                ("Mesh provider", record.mesh_provider, "info"),
                ("Mesh exactness", record.mesh_exactness, record.status.value),
                ("Vertices", f"{record.vertex_count:,}", "info"),
                ("Triangles", f"{record.triangle_count:,}", "info"),
                ("Transform determinant", f"{record.transform_determinant:.9g}", "pass" if record.right_handed else "fail"),
                ("Right-handed", str(record.right_handed), "pass" if record.right_handed else "fail"),
                ("Bounding box", " × ".join(f"{value:.3f}" for value in record.world_bounds_size), "info"),
                ("Profile", record.profile or "onbekend", "pass" if record.profile else "warning"),
                ("Material", record.material or "onbekend", "pass" if record.material else "warning"),
                ("Recognition", record.recognition_status or "onbekend", "info"),
            )
            for label, value, status in fields:
                self._accuracy_tree.addTopLevelItem(
                    QtWidgets.QTreeWidgetItem([label, str(value), status.upper()])
                )
            if record.issues:
                issue_root = QtWidgets.QTreeWidgetItem(["Meldingen", "", record.status.value.upper()])
                issue_root.setExpanded(True)
                for issue in record.issues:
                    issue_root.addChild(
                        QtWidgets.QTreeWidgetItem(
                            [issue.code, issue.message, issue.status.value.upper()]
                        )
                    )
                self._accuracy_tree.addTopLevelItem(issue_root)
            self._accuracy_tree.resizeColumnToContents(0)

        # ------------------------------------------------------------------
        # Viewer controls
        # ------------------------------------------------------------------
        def _combo_value(self, combo: Any) -> str:
            return str(combo.currentData() or "")

        def _on_standard_view_changed(self, _index: int) -> None:
            if self._syncing_controls:
                return
            value = self._combo_value(self._view_combo)
            if value:
                self.viewer.controller.set_standard_view(StandardView(value))
                self.viewer.controller.fit_all()

        def _on_projection_changed(self, _index: int) -> None:
            if self._syncing_controls:
                return
            value = self._combo_value(self._projection_combo)
            if value:
                self.viewer.controller.set_projection(ProjectionType(value))

        def _on_render_mode_changed(self, _index: int) -> None:
            if self._syncing_controls:
                return
            value = self._combo_value(self._render_combo)
            self.viewer.controller.set_render_mode(None if not value else RenderMode(value))

        def _on_background_changed(self, _index: int) -> None:
            if self._syncing_controls:
                return
            value = self._combo_value(self._background_combo)
            if value:
                self.viewer.controller.set_background_theme(BackgroundTheme(value))

        def _on_color_scheme_changed(self, _index: int) -> None:
            if self._syncing_controls:
                return
            scheme = ColorScheme(self._combo_value(self._color_combo) or ColorScheme.ORIGINAL.value)
            legend = self.interaction.apply_color_scheme(scheme)
            self._populate_legend(legend)
            self.statusBar().showMessage(
                f"Kleurregeling: {scheme.value} · {len(legend)} legendaregels", 3000
            )

        def _toggle_accuracy_mode(self, checked: bool) -> None:
            self.viewer.controller.set_accuracy_mode(bool(checked))
            self._show_accuracy()
            if checked:
                self._workspace_tabs.setCurrentIndex(3)

        def _apply_transparency_to_selection(self) -> None:
            ids = self.viewer.controller.get_selection()
            if not ids:
                self.statusBar().showMessage("Selecteer eerst een object", 2500)
                return
            self.viewer.controller.set_transparency(ids, self._transparency.value() / 100.0)

        def _hide_selected(self) -> None:
            ids = self.viewer.controller.get_selection()
            if ids:
                self.viewer.controller.hide(ids)

        def _isolate_selected(self) -> None:
            ids = self.viewer.controller.get_selection()
            if ids:
                self.viewer.controller.isolate(ids)
                self.viewer.controller.fit_all()

        def _ghost_selected(self) -> None:
            ids = self.viewer.controller.get_selection()
            if ids:
                self.viewer.controller.isolate(ids, ghost_context=True)
                self.viewer.controller.fit_all()

        # ------------------------------------------------------------------
        # Viewpoints / visibility / workspace
        # ------------------------------------------------------------------
        def _populate_legend(self, legend: tuple[Any, ...]) -> None:
            self._legend_tree.clear()
            for entry in legend:
                item = QtWidgets.QTreeWidgetItem([entry.label, f"{entry.count:,}"])
                pixmap = QtGui.QPixmap(16, 16)
                pixmap.fill(
                    QtGui.QColor.fromRgbF(
                        entry.color.red,
                        entry.color.green,
                        entry.color.blue,
                        entry.color.alpha,
                    )
                )
                item.setIcon(0, QtGui.QIcon(pixmap))
                self._legend_tree.addTopLevelItem(item)
            self._legend_tree.resizeColumnToContents(0)

        def _refresh_workspace_lists(self) -> None:
            self._viewpoint_list.clear()
            for viewpoint in self.viewer.controller.list_viewpoints():
                item = QtWidgets.QListWidgetItem(viewpoint.name)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, viewpoint.viewpoint_id)
                item.setToolTip(
                    f"{viewpoint.created_at}\nScene: {viewpoint.scene_hash[:16]}…"
                )
                self._viewpoint_list.addItem(item)
            self._visibility_list.clear()
            for visibility in self.viewer.controller.list_visibility_sets():
                item = QtWidgets.QListWidgetItem(visibility.name)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, visibility.visibility_set_id)
                item.setToolTip(
                    f"Hidden: {len(visibility.hidden_node_ids)} · isolate: {len(visibility.isolation_node_ids)}"
                )
                self._visibility_list.addItem(item)
            scheme = self.viewer.controller.get_display_preferences().color_scheme
            self._populate_legend(self.interaction.colorizer.legend(scheme))
            self._sync_controls_from_state()

        def _selected_list_id(self, widget: Any) -> str | None:
            item = widget.currentItem()
            if item is None:
                return None
            value = item.data(QtCore.Qt.ItemDataRole.UserRole)
            return None if value is None else str(value)

        def _save_viewpoint(self, name: str) -> None:
            self.viewer.controller.save_viewpoint(name)
            self._refresh_workspace_lists()
            self._save_workspace_now(silent=True)

        def _save_viewpoint_dialog(self) -> None:
            name, ok = QtWidgets.QInputDialog.getText(
                self, "Viewpoint opslaan", "Naam:"
            )
            if ok and name.strip():
                self._save_viewpoint(name.strip())

        def _activate_selected_viewpoint(self) -> None:
            viewpoint_id = self._selected_list_id(self._viewpoint_list)
            if not viewpoint_id:
                return
            viewpoint = next(
                (
                    item
                    for item in self.viewer.controller.list_viewpoints()
                    if item.viewpoint_id == viewpoint_id
                ),
                None,
            )
            if viewpoint is not None:
                self.viewer.controller.activate_viewpoint(viewpoint)
                self._sync_controls_from_state()

        def _delete_selected_viewpoint(self) -> None:
            viewpoint_id = self._selected_list_id(self._viewpoint_list)
            if viewpoint_id:
                self.viewer.controller.delete_viewpoint(viewpoint_id)
                self._refresh_workspace_lists()
                self._save_workspace_now(silent=True)

        def _save_visibility_set(self, name: str) -> None:
            self.viewer.controller.save_visibility_set(name)
            self._refresh_workspace_lists()
            self._save_workspace_now(silent=True)

        def _save_visibility_dialog(self) -> None:
            name, ok = QtWidgets.QInputDialog.getText(
                self, "Visibility set opslaan", "Naam:"
            )
            if ok and name.strip():
                self._save_visibility_set(name.strip())

        def _activate_selected_visibility_set(self) -> None:
            visibility_id = self._selected_list_id(self._visibility_list)
            if not visibility_id:
                return
            visibility = next(
                (
                    item
                    for item in self.viewer.controller.list_visibility_sets()
                    if item.visibility_set_id == visibility_id
                ),
                None,
            )
            if visibility is not None:
                self.viewer.controller.activate_visibility_set(visibility)
                self._sync_controls_from_state()

        def _delete_selected_visibility_set(self) -> None:
            visibility_id = self._selected_list_id(self._visibility_list)
            if visibility_id:
                self.viewer.controller.delete_visibility_set(visibility_id)
                self._refresh_workspace_lists()
                self._save_workspace_now(silent=True)

        def _set_combo_data(self, combo: Any, value: str) -> None:
            index = combo.findData(value)
            if index >= 0:
                combo.setCurrentIndex(index)

        def _sync_controls_from_state(self) -> None:
            self._syncing_controls = True
            try:
                preferences = self.viewer.controller.get_display_preferences()
                self._set_combo_data(
                    self._render_combo,
                    "" if preferences.render_mode is None else preferences.render_mode.value,
                )
                self._set_combo_data(
                    self._color_combo, preferences.color_scheme.value
                )
                self._set_combo_data(
                    self._background_combo, preferences.background_theme.value
                )
                self._set_combo_data(
                    self._projection_combo,
                    self.viewer.controller.get_camera().projection.value,
                )
                self._accuracy_action.setChecked(
                    bool(self.viewer.controller.session.accuracy_mode)
                )
            finally:
                self._syncing_controls = False

        def _save_workspace_now(self, _checked: bool = False, *, silent: bool = False) -> None:
            try:
                target = self.viewer.controller.save_workspace(self._workspace_path)
                if not silent:
                    self.statusBar().showMessage(
                        f"Werkruimte opgeslagen: {target.name}", 3500
                    )
            except Exception as exc:
                if silent:
                    return
                QtWidgets.QMessageBox.critical(
                    self,
                    "Werkruimte opslaan mislukt",
                    f"{type(exc).__name__}: {exc}",
                )

        def _restore_workspace_if_available(self) -> None:
            if not self._workspace_path.is_file():
                return
            try:
                report = self.viewer.controller.load_workspace(
                    self._workspace_path, allow_scene_mismatch=True
                )
                self._refresh_workspace_lists()
                self.statusBar().showMessage(
                    "Werkruimte hersteld"
                    + (
                        f" · {len(report.dropped_node_ids)} ontbrekende stable ID's overgeslagen"
                        if report.dropped_node_ids
                        else " · exact"
                    ),
                    5000,
                )
            except Exception as exc:
                self.statusBar().showMessage(
                    f"Werkruimte niet hersteld: {type(exc).__name__}: {exc}", 7000
                )

        def _save_screenshot_dialog(self) -> None:
            default = self.load_result.project_path.with_name(
                self.load_result.project_path.stem + "_viewer.png"
            )
            filename, _filter = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Viewer screenshot opslaan",
                str(default),
                "PNG (*.png)",
            )
            if filename:
                self.viewer.controller.screenshot_to_file(
                    filename,
                    ScreenshotOptions(
                        width=max(800, self.viewer.width()),
                        height=max(600, self.viewer.height()),
                        format="png",
                    ),
                )
                self.statusBar().showMessage(
                    f"Screenshot opgeslagen: {Path(filename).name}", 3500
                )

        # ------------------------------------------------------------------
        # Qt layout persistence
        # ------------------------------------------------------------------
        def _restore_qt_layout(self) -> None:
            geometry = self._qt_settings.value("windowGeometry")
            dock_state = self._qt_settings.value("windowState")
            grid_header = self._qt_settings.value("gridHeader")
            if geometry is not None:
                self.restoreGeometry(geometry)
            if dock_state is not None:
                self.restoreState(dock_state)
            if grid_header is not None:
                self._grid.horizontalHeader().restoreState(grid_header)

        def _save_qt_layout(self) -> None:
            self._qt_settings.setValue("windowGeometry", self.saveGeometry())
            self._qt_settings.setValue("windowState", self.saveState())
            self._qt_settings.setValue(
                "gridHeader", self._grid.horizontalHeader().saveState()
            )
            self._qt_settings.sync()

        def _update_status(self) -> None:
            report = self.load_result.scene_report
            self._status.setText(
                f"{report.selectable_count:,} objecten · {report.loaded_geometry_count:,} meshes"
            )
            self._limitations.setText(
                f"{report.proxy_geometry_count} proxies · productie blijft geblokkeerd"
            )

        def closeEvent(self, event: Any) -> None:
            self._save_workspace_now(silent=True)
            self._save_qt_layout()
            self._unsubscribe()
            self.interaction.close()
            self.viewer.controller.shutdown()
            super().closeEvent(event)


    def run_real_project_viewer(
        project_path: str | Path,
        *,
        cache_root: str | Path,
        source_search_roots: tuple[str | Path, ...] = (),
        ci_smoke: bool = False,
        report_path: str | Path | None = None,
        screenshot_path: str | Path | None = None,
    ) -> int:
        result = ProjectSceneLoader(
            cache_root=cache_root,
            source_search_roots=source_search_roots,
        ).load(project_path)
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setApplicationName("CWS Viewer V4")
        app.setOrganizationName("CWS")
        window = RealProjectViewerWindow(result)
        window.show()
        if ci_smoke:
            report = Path(report_path) if report_path else None
            screenshot = Path(screenshot_path) if screenshot_path else None

            def execute() -> None:
                payload: dict[str, Any] = {"status": "failed"}
                try:
                    hits = window.interaction.search("LO4", limit=20)
                    if not hits:
                        raise RuntimeError("LO4 ontbreekt in V4 projectviewer")
                    window.interaction.select_search_hit(hits[0])
                    window.viewer.controller.isolate(
                        (hits[0].node_id,), ghost_context=True
                    )
                    window.viewer.controller.fit_selection()
                    window.viewer.controller.set_render_mode(RenderMode.SHADED_EDGES)
                    legend = window.interaction.apply_color_scheme(ColorScheme.STATUS)
                    window.viewer.controller.set_background_theme(BackgroundTheme.SLATE)
                    viewpoint = window.viewer.controller.save_viewpoint("CI LO4 status")
                    visibility = window.viewer.controller.save_visibility_set("CI LO4 ghost")
                    workspace = window.viewer.controller.export_workspace_state()
                    window.viewer.controller.save_workspace(window._workspace_path)
                    window.viewer.controller.show_all()
                    restore = window.viewer.controller.load_workspace(window._workspace_path)
                    if screenshot:
                        screenshot.parent.mkdir(parents=True, exist_ok=True)
                        window.grab().save(str(screenshot), "PNG")
                    payload.update(
                        {
                            "status": "passed",
                            "scene_hash": result.scene.scene_hash,
                            "node_count": len(result.scene.nodes),
                            "geometry_count": len(result.repository),
                            "selection": list(
                                window.viewer.controller.get_selection()
                            ),
                            "qt_version": QtCore.qVersion(),
                            "workspace_path": str(window._workspace_path),
                            "workspace_state_hash": workspace.state_hash,
                            "workspace_restore": restore.to_dict(),
                            "viewpoint_id": viewpoint.viewpoint_id,
                            "visibility_set_id": visibility.visibility_set_id,
                            "legend_count": len(legend),
                            "render_mode": window.viewer.controller.get_display_preferences().render_mode.value,
                            "color_scheme": window.viewer.controller.get_display_preferences().color_scheme.value,
                        }
                    )
                except Exception as exc:  # pragma: no cover - Windows evidence
                    payload["error"] = f"{type(exc).__name__}: {exc}"
                finally:
                    if report:
                        report.parent.mkdir(parents=True, exist_ok=True)
                        report.write_text(
                            json.dumps(payload, indent=2), encoding="utf-8"
                        )
                    window.close()
                    app.quit()

            QtCore.QTimer.singleShot(1800, execute)
        return int(app.exec())

else:

    class RealProjectViewerWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    def run_real_project_viewer(*_: Any, **__: Any) -> int:  # pragma: no cover
        require_qt()
        return 2


__all__ = ["RealProjectViewerWindow", "run_real_project_viewer"]
