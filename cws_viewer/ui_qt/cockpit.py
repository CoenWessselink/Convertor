"""CWS Viewer V14 professional light project cockpit.

This composition layer deliberately keeps the Canonical Project Model and the
V3/V14 viewer controller as the single project truth.  It exposes the mature
viewer functions in a discoverable engineering-desktop UI: professional mouse
navigation, selection, IFC grids, measurements, sections, layers, properties,
model control and exact-part review.  Third-party viewers are used only as
behavioural benchmarks; no proprietary UI assets or implementation code are
embedded.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import threading
from typing import Any

from cws_viewer.adapters.project_scene_loader import ProjectSceneLoadResult, ProjectSceneLoader
from cws_viewer.contracts.enums import (
    BackgroundTheme, ColorScheme, MeasurementKind, ProjectionType, RenderMode,
    StandardView,
)
from cws_viewer.core.layers import LayerCatalog
from cws_viewer.core.project_interaction import ProjectInteractionModel
from cws_viewer.measurements import (
    ExactMeasurementAnchor, MeasurementProof, SnapType, angle_three_points,
    distance, horizontal_distance, point as point_measurement, vertical_distance,
)
from cws_viewer.model_control import ModelControlEngine
from cws_viewer.model_control.occt_narrow import ExactOcctPairEvaluator
from cws_viewer.properties import GridLayoutIdentity, GridLayoutStore, GridViewerBridge
from cws_viewer.ui_qt.design_system import DEFAULT_THEME, THEMES, theme_qss
from cws_viewer.ui_qt.exact_part_workbench import ExactPartWorkbenchPanel
from cws_viewer.ui_qt.property_grid import ProfessionalPropertyGridPanel
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_real_project_widget import NavigationMode, VtkRealProjectWidget
from cws_viewer.exact.workbench import ExactPartWorkbenchService
from cws_convertor.integration.exact_source import ExactSourceProjectService
from cws_convertor.ui_qt.viewer_tools import IntegratedViewerToolsPanel


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class DetachedViewerWindow(QtWidgets.QMainWindow):
        attach_requested = QtCore.Signal(object)

        def __init__(self, viewer: Any, settings: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self._settings = settings
            self.setWindowTitle("CWS Viewer — losgekoppelde 3D Viewer")
            self.setCentralWidget(viewer)
            self.resize(1450, 900)
            geometry = settings.value("viewer/detachedGeometry")
            if geometry is not None:
                self.restoreGeometry(geometry)
            bar = self.addToolBar("Viewer")
            bar.setMovable(False)
            bar.addAction("Terugplaatsen", self._attach)
            bar.addAction("Volledig scherm", self._fullscreen)

        def _fullscreen(self) -> None:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()

        def _attach(self) -> None:
            widget = self.takeCentralWidget()
            if widget is not None:
                self.attach_requested.emit(widget)
            self.close()

        def closeEvent(self, event: Any) -> None:
            self._settings.setValue("viewer/detachedGeometry", self.saveGeometry())
            widget = self.takeCentralWidget()
            if widget is not None:
                self.attach_requested.emit(widget)
            super().closeEvent(event)


    class _ModelControlWorker(QtCore.QObject):
        completed = QtCore.Signal(object)
        failed = QtCore.Signal(str)
        finished = QtCore.Signal()

        def __init__(self, index: Any, project: Any, entity_ids: tuple[str, ...] | None, cancel: threading.Event) -> None:
            super().__init__()
            self.index, self.project, self.entity_ids, self.cancel = index, project, entity_ids, cancel

        @QtCore.Slot()
        def run(self) -> None:
            try:
                self.completed.emit(
                    ModelControlEngine().scan(
                        self.index, self.project,
                        entity_ids=self.entity_ids,
                        cancel_check=self.cancel.is_set,
                    )
                )
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")
            finally:
                self.finished.emit()


    class _ViewerToolsAdapter:
        def __init__(self, window: "CwsViewerCockpitWindow") -> None:
            self.controller = window.viewer.controller
            self.project = window.project
            self.project_path = window.load_result.project_path
            self.load_result = window.load_result


    class CwsViewerCockpitWindow(QtWidgets.QMainWindow):
        """Bright, discoverable CWS project viewer built on the existing engine."""

        def __init__(self, load_result: ProjectSceneLoadResult) -> None:
            super().__init__()
            self.load_result = load_result
            self.project = load_result.project
            self._settings = QtCore.QSettings("CWS", "CWS Viewer")
            self._theme_key = str(self._settings.value("ui/theme", DEFAULT_THEME))
            if self._theme_key not in THEMES:
                self._theme_key = DEFAULT_THEME
            self._syncing = False
            self._detached: DetachedViewerWindow | None = None
            self._scan_thread: Any | None = None
            self._scan_cancel = threading.Event()
            self._clash_records: tuple[Any, ...] = ()
            self._measurement_kind: MeasurementKind | None = None
            self._measurement_anchors: list[ExactMeasurementAnchor] = []
            self._grid_catalog: dict[str, Any] | None = None
            self._tree_items: dict[str, Any] = {}

            self.setObjectName("cwsViewerCockpitWindow")
            self.setWindowTitle(f"CWS Viewer — {getattr(self.project, 'project_name', 'Project')}")
            self.resize(1780, 1040)
            self.setMinimumSize(1180, 720)
            self.setStyleSheet(theme_qss(self._theme_key))

            self.viewer = VtkRealProjectWidget(load_result.repository, self)
            self.viewer.load_scene(load_result.scene)
            self.viewer.controller.set_background_theme(BackgroundTheme.LIGHT)
            self.viewer.controller.set_render_mode(RenderMode.SHADED_EDGES)
            self.interaction = ProjectInteractionModel(
                self.viewer.controller, self.project, mesh_repository=load_result.repository
            )
            self._interaction_unsubscribe = self.interaction.subscribe(self._selection_changed)
            self._layers = LayerCatalog.from_index(self.viewer.controller.index)
            self._bridge = GridViewerBridge(self.interaction, self.interaction.grid_model)

            self.viewer.pick_result.connect(self._viewer_pick)
            self.viewer.context_requested.connect(self._viewer_context_menu)
            self.viewer.tool_cancelled.connect(self._cancel_tool)
            self.viewer.interaction_message.connect(lambda text: self.statusBar().showMessage(str(text), 5000))
            self.viewer.backend_failed.connect(lambda text: self.statusBar().showMessage(f"Viewer: {text}", 7000))

            root = QtWidgets.QWidget(self)
            root.setObjectName("cwsCockpitRoot")
            self.setCentralWidget(root)
            layout = QtWidgets.QVBoxLayout(root)
            layout.setContentsMargins(5, 5, 5, 4)
            layout.setSpacing(4)
            layout.addWidget(self._build_header())
            layout.addWidget(self._build_toolbar())

            vertical = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
            vertical.setChildrenCollapsible(False)
            vertical.addWidget(self._build_main_workspace())
            vertical.addWidget(self._build_bottom_workspace())
            vertical.setSizes([720, 300])
            layout.addWidget(vertical, 1)

            self._build_status_bar()
            self._populate_tree()
            self._populate_layers()
            self._initialise_grid_catalog()
            self._refresh_properties()
            self._refresh_measurement_overlay()
            self._install_shortcuts()
            self.viewer.controller.fit_all()
            self._restore_state()

        # -----------------------------------------------------------------
        # Header / toolbar
        def _build_header(self) -> Any:
            frame = QtWidgets.QFrame(); frame.setObjectName("cwsHeader")
            row = QtWidgets.QHBoxLayout(frame); row.setContentsMargins(10, 6, 10, 6)
            title = QtWidgets.QLabel("CWS Viewer"); title.setObjectName("cwsProductTitle")
            subtitle = QtWidgets.QLabel(str(getattr(self.project, "project_name", "Project"))); subtitle.setObjectName("cwsSubtitle")
            row.addWidget(title); row.addSpacing(14); row.addWidget(subtitle); row.addStretch(1)
            self._header_selection = QtWidgets.QLabel("Geen selectie"); self._header_selection.setObjectName("statusPill")
            row.addWidget(self._header_selection)
            version = QtWidgets.QLabel("1.3.0-rc1"); version.setObjectName("cwsVersion")
            row.addSpacing(8); row.addWidget(version)
            return frame

        def _action(self, bar: Any, text: str, callback: Any, shortcut: str | None = None, *, checkable: bool = False) -> Any:
            action = QtGui.QAction(text, self); action.setCheckable(checkable)
            if shortcut: action.setShortcut(QtGui.QKeySequence(shortcut))
            action.triggered.connect(callback); bar.addAction(action); return action

        def _build_toolbar(self) -> Any:
            frame = QtWidgets.QFrame(); frame.setObjectName("cwsRibbon")
            box = QtWidgets.QVBoxLayout(frame); box.setContentsMargins(4, 2, 4, 2); box.setSpacing(1)
            bar = QtWidgets.QToolBar(); bar.setMovable(False); bar.setFloatable(False); bar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
            box.addWidget(bar)

            self._area_action = self._action(bar, "Vensterselectie", lambda checked=False: self.viewer.set_area_selection(True), "Ctrl+R")
            bar.addSeparator()
            self._nav_group = QtGui.QActionGroup(self); self._nav_group.setExclusive(True)
            self._nav_actions: dict[NavigationMode, Any] = {}
            for label, mode, shortcut in (
                ("Roteren", NavigationMode.ORBIT, "Ctrl+U"),
                ("Pan", NavigationMode.PAN, "Ctrl+I"),
                ("Lopen", NavigationMode.WALK, "Ctrl+O"),
                ("Rondkijken", NavigationMode.LOOK, "Ctrl+P"),
            ):
                action = self._action(bar, label, lambda _checked=False, m=mode: self._set_navigation(m), shortcut, checkable=True)
                self._nav_group.addAction(action); self._nav_actions[mode] = action
            self._nav_actions[NavigationMode.ORBIT].setChecked(True)
            bar.addSeparator()
            self._action(bar, "Fit", self.viewer.controller.fit_all, "F")
            self._action(bar, "Fit selectie", self.viewer.controller.fit_selection, "Space")

            view_button = QtWidgets.QToolButton(); view_button.setText("Aanzicht ▾"); view_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            view_menu = QtWidgets.QMenu(view_button)
            for label, view in (("Isometrisch", StandardView.ISOMETRIC),("Voor",StandardView.FRONT),("Achter",StandardView.BACK),("Links",StandardView.LEFT),("Rechts",StandardView.RIGHT),("Boven",StandardView.TOP),("Onder",StandardView.BOTTOM)):
                view_menu.addAction(label, lambda _checked=False, v=view: self.viewer.controller.set_standard_view(v))
            view_button.setMenu(view_menu); bar.addWidget(view_button)

            display_button = QtWidgets.QToolButton(); display_button.setText("Weergave ▾"); display_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            display_menu = QtWidgets.QMenu(display_button)
            for label, mode in (("Shaded",RenderMode.SHADED),("Shaded + randen",RenderMode.SHADED_EDGES),("Wireframe",RenderMode.WIREFRAME),("Hidden Line",RenderMode.HIDDEN_LINE)):
                display_menu.addAction(label, lambda _checked=False, m=mode: self.viewer.controller.set_render_mode(m))
            display_menu.addSeparator()
            display_menu.addAction("Perspectief", lambda: self.viewer.controller.set_projection(ProjectionType.PERSPECTIVE))
            display_menu.addAction("Orthografisch", lambda: self.viewer.controller.set_projection(ProjectionType.ORTHOGRAPHIC))
            display_button.setMenu(display_menu); bar.addWidget(display_button)

            bar.addSeparator()
            self._grid_action = self._action(bar, "Stamien", self._apply_grid_overlay, "Ctrl+G", checkable=True); self._grid_action.setChecked(True)
            self._grid_level_combo = QtWidgets.QComboBox(); self._grid_level_combo.setMinimumWidth(105); self._grid_level_combo.addItem("Auto", ""); self._grid_level_combo.currentIndexChanged.connect(self._apply_grid_overlay); bar.addWidget(self._grid_level_combo)

            measure_button = QtWidgets.QToolButton(); measure_button.setText("Meten ▾"); measure_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            measure_menu = QtWidgets.QMenu(measure_button)
            for label, kind in (("Afstand",MeasurementKind.DISTANCE),("Horizontaal",MeasurementKind.HORIZONTAL_DISTANCE),("Verticaal",MeasurementKind.VERTICAL_DISTANCE),("Puntcoördinaten",MeasurementKind.COORDINATES),("Hoek",MeasurementKind.ANGLE)):
                measure_menu.addAction(label, lambda _checked=False, k=kind: self._start_measurement(k))
            measure_menu.addSeparator(); measure_menu.addAction("Meetwerkruimte", self._focus_viewer_tools); measure_menu.addAction("Alle metingen wissen", self._clear_measurements)
            measure_button.setMenu(measure_menu); bar.addWidget(measure_button)

            section_button = QtWidgets.QToolButton(); section_button.setText("Doorsnede ▾"); section_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            section_menu = QtWidgets.QMenu(section_button); section_menu.addAction("Section/clipping werkruimte", self._focus_viewer_tools); section_menu.addAction("Clipping box", self._focus_viewer_tools)
            section_button.setMenu(section_menu); bar.addWidget(section_button)

            bar.addSeparator()
            self._action(bar, "Verberg", self._hide_selected, "Backspace")
            self._action(bar, "Isoleer", self._isolate_selected, "I")
            self._action(bar, "Ghost", self._ghost_selected)
            self._action(bar, "Alles tonen", self._show_all, "Ctrl+Shift+A")

            color_button = QtWidgets.QToolButton(); color_button.setText("Kleuren ▾"); color_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            color_menu = QtWidgets.QMenu(color_button)
            for label, scheme in (("Origineel",ColorScheme.ORIGINAL),("Categorie",ColorScheme.CATEGORY),("Materiaal",ColorScheme.MATERIAL),("Profiel",ColorScheme.PROFILE),("Status",ColorScheme.STATUS),("Fase",ColorScheme.PHASE),("Bronmodel",ColorScheme.SOURCE_MODEL),("Assembly",ColorScheme.ASSEMBLY),("Monochroom",ColorScheme.MONOCHROME)):
                color_menu.addAction(label, lambda _checked=False, s=scheme: self.interaction.apply_color_scheme(s))
            color_button.setMenu(color_menu); bar.addWidget(color_button)

            self._theme_combo = QtWidgets.QComboBox()
            for key, theme in THEMES.items(): self._theme_combo.addItem(theme.title, key)
            idx = self._theme_combo.findData(self._theme_key); self._theme_combo.setCurrentIndex(max(0, idx)); self._theme_combo.currentIndexChanged.connect(self._theme_changed); bar.addWidget(self._theme_combo)
            bar.addSeparator()
            self._action(bar, "Los scherm", self._detach_viewer)
            self._action(bar, "Volledig scherm", self._fullscreen, "F11")
            return frame

        # -----------------------------------------------------------------
        # Main workspace
        def _panel(self, title: str) -> tuple[Any, Any]:
            frame = QtWidgets.QFrame(); frame.setObjectName("cwsPanel")
            layout = QtWidgets.QVBoxLayout(frame); layout.setContentsMargins(6, 5, 6, 6); layout.setSpacing(4)
            label = QtWidgets.QLabel(title); label.setObjectName("cwsPanelTitle"); layout.addWidget(label)
            return frame, layout

        def _build_main_workspace(self) -> Any:
            splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal); splitter.setChildrenCollapsible(False)
            left, l = self._panel("Projectstructuur")
            self._tree_filter = QtWidgets.QLineEdit(); self._tree_filter.setPlaceholderText("Zoek object, merk, profiel …"); self._tree_filter.setClearButtonEnabled(True); self._tree_filter.textChanged.connect(self._filter_tree); l.addWidget(self._tree_filter)
            self._tree = QtWidgets.QTreeWidget(); self._tree.setHeaderLabels(["Object", "Type", "Status"]); self._tree.setAlternatingRowColors(True); self._tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection); self._tree.itemSelectionChanged.connect(self._tree_selection); self._tree.itemChanged.connect(self._tree_visibility); l.addWidget(self._tree, 1)
            splitter.addWidget(left)

            self._viewer_host, viewer_layout = self._panel("3D Viewer")
            self._viewer_host_layout = viewer_layout
            self._viewer_host_layout.addWidget(self.viewer, 1)
            self._viewer_placeholder = QtWidgets.QLabel("3D Viewer is losgekoppeld"); self._viewer_placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter); self._viewer_placeholder.hide(); self._viewer_host_layout.addWidget(self._viewer_placeholder)
            self._tool_status = QtWidgets.QLabel("Roteren actief · klik selecteert · middel = pan · wiel = zoom"); self._tool_status.setObjectName("cwsMuted"); self._viewer_host_layout.addWidget(self._tool_status)
            splitter.addWidget(self._viewer_host)

            right, r = self._panel("Eigenschappen en herkomst")
            self._properties = QtWidgets.QTreeWidget(); self._properties.setHeaderLabels(["Eigenschap", "Waarde", "Herkomst", "Confidence"]); self._properties.setAlternatingRowColors(True); r.addWidget(self._properties, 1)
            splitter.addWidget(right)
            splitter.setSizes([300, 1120, 360])
            return splitter

        def _build_bottom_workspace(self) -> Any:
            self._tabs = QtWidgets.QTabWidget()
            layouts = GridLayoutStore(Path.home()/".cws_convertor"/"viewer_grid_layouts")
            identity = GridLayoutIdentity("CWS", "default", str(self.project.project_id), "Project")
            self._project_grid = ProfessionalPropertyGridPanel(self.interaction.grid_model, bridge=self._bridge, layout_store=layouts, layout_identity=identity)
            self._project_grid.open_part_workbench_requested.connect(lambda _id: self._open_exact_workbench())
            self._tabs.addTab(self._project_grid, "Onderdelen en merken")

            self._viewer_tools = IntegratedViewerToolsPanel(_ViewerToolsAdapter(self))
            if hasattr(self._viewer_tools, "status_changed"):
                self._viewer_tools.status_changed.connect(lambda text: self.statusBar().showMessage(str(text), 4500))
            self._tabs.addTab(self._viewer_tools, "Meten / Sections")

            control = QtWidgets.QWidget(); c = QtWidgets.QVBoxLayout(control); c.setContentsMargins(5,5,5,5)
            controls = QtWidgets.QHBoxLayout(); self._scan_scope = QtWidgets.QComboBox(); self._scan_scope.addItems(["Hele project", "Zichtbare onderdelen", "Selectie"]); controls.addWidget(self._scan_scope)
            run = QtWidgets.QPushButton("Modelcontrole uitvoeren"); run.clicked.connect(self._run_model_control); controls.addWidget(run)
            exact = QtWidgets.QPushButton("Exact controleer geselecteerd paar"); exact.clicked.connect(self._exact_selected_clash); controls.addWidget(exact); controls.addStretch(1)
            self._clash_stats = QtWidgets.QLabel("Nog niet gecontroleerd"); controls.addWidget(self._clash_stats); c.addLayout(controls)
            self._clash_table = QtWidgets.QTableWidget(0, 7); self._clash_table.setHorizontalHeaderLabels(["ID","Categorie","Ernst","Onderdeel A","Onderdeel B","Bewijs","Status"]); self._clash_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows); self._clash_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers); self._clash_table.itemSelectionChanged.connect(self._clash_selected); c.addWidget(self._clash_table,1)
            self._tabs.addTab(control, "Model Control")

            layers_widget = QtWidgets.QWidget(); ly = QtWidgets.QVBoxLayout(layers_widget); ly.setContentsMargins(5,5,5,5)
            self._layers_tree = QtWidgets.QTreeWidget(); self._layers_tree.setHeaderLabels(["Laag", "Categorie", "Objecten"]); self._layers_tree.itemChanged.connect(self._layer_changed); ly.addWidget(self._layers_tree,1); self._tabs.addTab(layers_widget,"Lagen")
            return self._tabs

        # -----------------------------------------------------------------
        # Tree / properties / layer synchronisation
        def _populate_tree(self) -> None:
            self._syncing = True; self._tree.clear(); self._tree_items.clear()
            try:
                index = self.viewer.controller.index
                def add(node_id: str, parent: Any | None) -> None:
                    node = index.node(node_id)
                    item = QtWidgets.QTreeWidgetItem([node.name or node.entity_id, node.kind.value, ""]); item.setData(0,QtCore.Qt.ItemDataRole.UserRole,node_id); item.setFlags(item.flags()|QtCore.Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(0,QtCore.Qt.CheckState.Checked); self._tree_items[node_id]=item
                    (parent.addChild(item) if parent is not None else self._tree.addTopLevelItem(item))
                    for child in index.children_by_node.get(node_id, ()): add(child,item)
                for root in index.root_node_ids: add(root,None)
                self._tree.expandToDepth(1)
            finally: self._syncing=False

        def _filter_tree(self, text: str) -> None:
            query = text.casefold().strip()
            def visit(item: Any) -> bool:
                own = not query or query in " ".join(item.text(i) for i in range(3)).casefold(); child=False
                for i in range(item.childCount()): child = visit(item.child(i)) or child
                show=own or child; item.setHidden(not show); return show
            for i in range(self._tree.topLevelItemCount()): visit(self._tree.topLevelItem(i))

        def _tree_selection(self) -> None:
            if self._syncing: return
            ids = [str(item.data(0,QtCore.Qt.ItemDataRole.UserRole)) for item in self._tree.selectedItems() if item.data(0,QtCore.Qt.ItemDataRole.UserRole)]
            self.interaction.select_nodes(ids, origin="tree")

        def _tree_visibility(self, item: Any, _column: int) -> None:
            if self._syncing: return
            node_id=item.data(0,QtCore.Qt.ItemDataRole.UserRole)
            if not node_id:return
            if item.checkState(0)==QtCore.Qt.CheckState.Checked:self.viewer.controller.show((str(node_id),))
            else:self.viewer.controller.hide((str(node_id),))

        def _selection_changed(self, selection: Any) -> None:
            self._syncing=True
            try:
                self._tree.clearSelection()
                for node_id in selection.node_ids:
                    item=self._tree_items.get(node_id)
                    if item:item.setSelected(True);self._tree.scrollToItem(item)
                self._header_selection.setText(f"Selectie: {len(selection.entity_ids)}")
                self._refresh_properties()
                self._project_grid.refresh()
            finally:self._syncing=False

        def _refresh_properties(self) -> None:
            self._properties.clear()
            for record in self.interaction.properties_for_primary():
                confidence="" if record.confidence is None else f"{float(record.confidence):.0%}"
                self._properties.addTopLevelItem(QtWidgets.QTreeWidgetItem([record.label,str(record.value),str(record.provenance),confidence]))
            self._properties.resizeColumnToContents(0); self._properties.resizeColumnToContents(1)

        def _populate_layers(self) -> None:
            self._layers_tree.blockSignals(True); self._layers_tree.clear()
            for category in self._layers.category_names():
                parent=QtWidgets.QTreeWidgetItem([category,"",""]); parent.setFlags(parent.flags() & ~QtCore.Qt.ItemFlag.ItemIsUserCheckable); self._layers_tree.addTopLevelItem(parent)
                for layer in self._layers.layers_for_category(category):
                    item=QtWidgets.QTreeWidgetItem([layer.label,layer.category,str(len(layer.node_ids))]); item.setData(0,QtCore.Qt.ItemDataRole.UserRole,layer.layer_id); item.setFlags(item.flags()|QtCore.Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(0,QtCore.Qt.CheckState.Checked); parent.addChild(item)
            self._layers_tree.expandToDepth(0); self._layers_tree.blockSignals(False)

        def _layer_changed(self, item: Any, _column: int) -> None:
            layer_id=item.data(0,QtCore.Qt.ItemDataRole.UserRole)
            if not layer_id:return
            layer=self._layers.by_id.get(str(layer_id))
            if layer is None:return
            if item.checkState(0)==QtCore.Qt.CheckState.Checked:self.viewer.controller.show(layer.node_ids)
            else:self.viewer.controller.hide(layer.node_ids)

        # -----------------------------------------------------------------
        # Theme/navigation/display
        def _theme_changed(self, _index: int) -> None:
            key=str(self._theme_combo.currentData() or DEFAULT_THEME); self._theme_key=key; self._settings.setValue("ui/theme",key)
            app=QtWidgets.QApplication.instance(); qss=theme_qss(key)
            if app is not None: app.setStyleSheet(qss)
            self.setStyleSheet(qss)
            if key=="cws_dark": self.viewer.controller.set_background_theme(BackgroundTheme.DARK)
            else:self.viewer.controller.set_background_theme(BackgroundTheme.LIGHT)

        def _set_navigation(self, mode: NavigationMode) -> None:
            self.viewer.set_navigation_mode(mode)
            for key, action in self._nav_actions.items(): action.setChecked(key==mode)
            self._tool_status.setText({NavigationMode.ORBIT:"Roteren actief · klik selecteert · middel = pan · wiel = zoom",NavigationMode.PAN:"Pan actief · sleep links/middel",NavigationMode.WALK:"Lopen actief · WASD/QE",NavigationMode.LOOK:"Rondkijken actief · sleep links"}[mode])

        def _show_all(self) -> None:
            self.viewer.controller.show_all(); self.viewer.controller.clear_transparency(); self.viewer.controller.fit_all()
        def _hide_selected(self) -> None:
            if self.viewer.controller.session.selection:self.viewer.controller.hide(self.viewer.controller.session.selection)
        def _isolate_selected(self) -> None:
            if self.viewer.controller.session.selection:self.viewer.controller.isolate(self.viewer.controller.session.selection);self.viewer.controller.fit_all()
        def _ghost_selected(self) -> None:
            if self.viewer.controller.session.selection:self.viewer.controller.isolate(self.viewer.controller.session.selection,ghost_context=True);self.viewer.controller.fit_all()
        def _fullscreen(self) -> None:self.showNormal() if self.isFullScreen() else self.showFullScreen()

        # -----------------------------------------------------------------
        # IFC grid/stamien
        def _initialise_grid_catalog(self) -> None:
            catalogs=dict((getattr(self.project,"settings",{}) or {}).get("ifc_grid_catalogs") or {})
            if not catalogs:
                try:
                    from cws_convertor.importers.ifc_grid import extract_ifc_grid_catalog_from_document, extract_ifc_grid_catalog
                    documents=dict(getattr(self.load_result.catalog,"_documents",{}) or {})
                    for source_id, source in (getattr(self.project,"sources",{}) or {}).items():
                        if str(getattr(source,"source_format","")).upper()!="IFC":continue
                        doc=documents.get(str(source_id))
                        if doc is not None: catalogs[str(source_id)]=extract_ifc_grid_catalog_from_document(doc,source_id=str(source_id),source_file=str(getattr(source,"file_name","")))
                        else:
                            original=Path(str(getattr(source,"original_path","") or "")).expanduser()
                            if original.is_file():catalogs[str(source_id)]=extract_ifc_grid_catalog(original,source_id=str(source_id))
                except Exception as exc:self.statusBar().showMessage(f"Stamienanalyse: {type(exc).__name__}: {exc}",7000)
            grids=[];warnings=[]
            for catalog in catalogs.values():
                if not isinstance(catalog,dict):continue
                grids.extend(dict(value) for value in catalog.get("grids") or []);warnings.extend(str(v) for v in catalog.get("warnings") or [])
            self._grid_catalog={"schema":"cws-ifc-grid-catalog-merged-1.0","grids":grids,"warnings":list(dict.fromkeys(warnings))} if grids else None
            self._grid_level_combo.blockSignals(True);self._grid_level_combo.clear();self._grid_level_combo.addItem("Auto","")
            names=[]
            for grid in grids:
                name=str(grid.get("name","") or "")
                if name and name not in names:names.append(name);self._grid_level_combo.addItem(name,name)
            if len(names)>1:self._grid_level_combo.addItem("Alle niveaus","__all__")
            self._grid_level_combo.blockSignals(False);self._grid_action.setEnabled(bool(grids));self._grid_level_combo.setEnabled(bool(grids));self._apply_grid_overlay()
            if grids:self.statusBar().showMessage(f"IFC-stamien: {len(grids)} niveau(s), {sum(len(g.get('axes') or []) for g in grids)} assen",4500)

        def _apply_grid_overlay(self, *_args: Any) -> None:
            if self._grid_catalog is None:self.viewer.backend.set_grid_catalog(None,visible=False);return
            value=str(self._grid_level_combo.currentData() or "")
            levels=tuple(str(g.get("name","")) for g in self._grid_catalog.get("grids",())) if value=="__all__" else ((value,) if value else ())
            self.viewer.backend.set_grid_catalog(self._grid_catalog,visible=self._grid_action.isChecked(),levels=levels)

        # -----------------------------------------------------------------
        # Measurements
        def _measurement_proof(self, pick: Any) -> MeasurementProof:
            node=self.viewer.controller.index.node(pick.node_id);mesh=self.load_result.repository.get(node.geometry_id) if node.geometry_id else None
            return MeasurementProof.DISPLAY_PROXY if mesh is None or str(getattr(mesh,"exactness",""))=="display_proxy" else MeasurementProof.VERIFIED_MESH

        def _anchor(self, pick: Any) -> ExactMeasurementAnchor:
            node=self.viewer.controller.index.node(pick.node_id)
            return ExactMeasurementAnchor(node_id=pick.node_id,entity_id=pick.entity_id,source_entity_id=pick.source_entity_id or "",feature_id=pick.feature_id,subshape_type=pick.subshape_type,subshape_id=pick.subshape_id,world_point=pick.world_point,local_point=pick.local_point,geometry_hash=node.geometry_hash,snap_type=SnapType.NEAREST,proof=self._measurement_proof(pick),normal=pick.normal)

        def _start_measurement(self, kind: MeasurementKind) -> None:
            self._measurement_kind=MeasurementKind(kind);self._measurement_anchors=[];self.viewer.controller.begin_measurement(kind);self._focus_viewer_tools();self._tool_status.setText("Meetmodus actief · klik modelpunten · Esc beëindigt");self.viewer.setFocus()

        def _viewer_pick(self, pick: Any) -> None:
            if self._measurement_kind is None:return
            try:
                anchor=self._anchor(pick);self._measurement_anchors.append(anchor);settings=self.viewer.controller.get_measurement_settings();record=None
                if self._measurement_kind==MeasurementKind.COORDINATES:record=point_measurement(anchor,settings)
                elif self._measurement_kind==MeasurementKind.DISTANCE and len(self._measurement_anchors)>=2:record=distance(self._measurement_anchors[-2],self._measurement_anchors[-1],settings)
                elif self._measurement_kind==MeasurementKind.HORIZONTAL_DISTANCE and len(self._measurement_anchors)>=2:record=horizontal_distance(self._measurement_anchors[-2],self._measurement_anchors[-1],settings)
                elif self._measurement_kind==MeasurementKind.VERTICAL_DISTANCE and len(self._measurement_anchors)>=2:record=vertical_distance(self._measurement_anchors[-2],self._measurement_anchors[-1],settings)
                elif self._measurement_kind==MeasurementKind.ANGLE and len(self._measurement_anchors)>=3:record=angle_three_points(self._measurement_anchors[-3],self._measurement_anchors[-2],self._measurement_anchors[-1],settings)
                if record is None:self.statusBar().showMessage(f"Meetpunt {len(self._measurement_anchors)} gekozen",2500);return
                self.viewer.controller.add_measurement(record);self._measurement_anchors=[];self._refresh_measurement_overlay();self._viewer_tools.refresh();self.statusBar().showMessage(f"Meting {record.formatted_text} · {record.proof.value}",6000)
            except Exception as exc:QtWidgets.QMessageBox.warning(self,"Meten",f"{type(exc).__name__}: {exc}")

        def _clear_measurements(self) -> None:self.viewer.controller.clear_measurements();self._measurement_anchors=[];self._refresh_measurement_overlay();self._viewer_tools.refresh()
        def _refresh_measurement_overlay(self) -> None:self.viewer.backend.set_measurement_overlays(self.viewer.controller.list_measurements())
        def _cancel_tool(self) -> None:
            self._measurement_kind=None;self._measurement_anchors=[];self.viewer.controller.cancel_tool();self.viewer.set_area_selection(False);self._set_navigation(NavigationMode.ORBIT)
        def _focus_viewer_tools(self) -> None:self._tabs.setCurrentWidget(self._viewer_tools)

        # -----------------------------------------------------------------
        # Context menu / exact part / screenshots
        def _viewer_context_menu(self, global_position: Any, pick: Any) -> None:
            menu=QtWidgets.QMenu(self)
            if pick is not None:
                menu.addAction("Fit op object",self.viewer.controller.fit_selection);menu.addAction("Eigenschappen",lambda:self._properties.setFocus());menu.addSeparator();menu.addAction("Isoleer",self._isolate_selected);menu.addAction("Verberg",self._hide_selected);menu.addAction("Ghost omgeving",self._ghost_selected)
            else:menu.addAction("Fit model",self.viewer.controller.fit_all);menu.addAction("Alles tonen",self._show_all)
            menu.addSeparator();measure=menu.addMenu("Meten")
            for label,kind in (("Afstand",MeasurementKind.DISTANCE),("Horizontaal",MeasurementKind.HORIZONTAL_DISTANCE),("Verticaal",MeasurementKind.VERTICAL_DISTANCE),("Puntcoördinaten",MeasurementKind.COORDINATES),("Hoek",MeasurementKind.ANGLE)):measure.addAction(label,lambda _checked=False,k=kind:self._start_measurement(k))
            menu.addAction("Doorsnede / clipping",self._focus_viewer_tools);menu.addAction("Model Control",lambda:self._tabs.setCurrentIndex(2))
            if pick is not None:menu.addSeparator();menu.addAction("Exact Part Workbench",self._open_exact_workbench)
            menu.addSeparator();menu.addAction("Screenshot opslaan",self._screenshot);menu.exec(global_position)

        def _screenshot(self) -> None:
            path,_=QtWidgets.QFileDialog.getSaveFileName(self,"Screenshot opslaan",str(self.load_result.project_path.with_suffix(".viewer.png")),"PNG (*.png)")
            if path:self.viewer.controller.screenshot_to_file(path)

        def _open_exact_workbench(self) -> None:
            primary=self.interaction.selection.primary_entity_id
            if not primary or primary not in self.project.parts:QtWidgets.QMessageBox.information(self,"Exact Part Workbench","Selecteer eerst één maakdeel.");return
            service_project=None
            try:
                roots=tuple(Path(src.original_path).expanduser().resolve().parent for src in self.project.sources.values() if src.original_path)
                service_project=ExactSourceProjectService.open(self.load_result.project_path,read_only=True,source_search_roots=roots);_part,_path,isolation=service_project.isolate(primary)
                if isolation.runtime is None:raise RuntimeError("Geen exact source-BREP runtime beschikbaar")
                panel=ExactPartWorkbenchPanel(ExactPartWorkbenchService(isolation.runtime))
            except Exception as exc:
                if service_project is not None:service_project.close()
                QtWidgets.QMessageBox.warning(self,"Exact Part Workbench",f"{type(exc).__name__}: {exc}");return
            window=QtWidgets.QMainWindow(self);window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose,True);window.setWindowTitle("Exact Part Workbench");window.setCentralWidget(panel);window.resize(1450,900);window.destroyed.connect(lambda *_args,svc=service_project:svc.close());window.show();self._workbench_window=window

        # -----------------------------------------------------------------
        # Model control
        def _scan_ids(self) -> tuple[str, ...] | None:
            scope=self._scan_scope.currentText()
            if scope=="Selectie":return tuple(self.interaction.selection.entity_ids)
            if scope=="Zichtbare onderdelen":
                visible,_=self.viewer.controller.session.visible_and_ghosted(self.viewer.controller.index);return tuple(self.viewer.controller.index.node(node).entity_id for node in visible if self.viewer.controller.index.node(node).entity_id in self.project.parts)
            return None

        def _run_model_control(self) -> None:
            if self._scan_thread is not None:return
            self._scan_cancel.clear();thread=QtCore.QThread(self);worker=_ModelControlWorker(self.viewer.controller.index,self.project,self._scan_ids(),self._scan_cancel);worker.moveToThread(thread);thread.started.connect(worker.run);worker.completed.connect(self._model_control_done);worker.failed.connect(lambda text:QtWidgets.QMessageBox.warning(self,"Model Control",text));worker.finished.connect(thread.quit);worker.finished.connect(worker.deleteLater);thread.finished.connect(lambda:self._set_scan_thread(None));thread.finished.connect(thread.deleteLater);self._scan_thread=thread;self._clash_stats.setText("Controleren …");thread.start()
        def _set_scan_thread(self, value: Any) -> None:self._scan_thread=value

        def _model_control_done(self, result: Any) -> None:
            self._clash_records=tuple(result.records);self._clash_stats.setText(f"{result.stats.results} resultaten · {result.stats.broad_phase_candidates} kandidaten");self._clash_table.setRowCount(len(self._clash_records))
            for row,record in enumerate(self._clash_records):
                values=(record.clash_id,record.category,record.severity,record.part_a_id,record.part_b_id,record.geometry_confidence,record.status)
                for col,value in enumerate(values):self._clash_table.setItem(row,col,QtWidgets.QTableWidgetItem(str(value)))

        def _clash_selected(self) -> None:
            row=self._clash_table.currentRow()
            if 0<=row<len(self._clash_records):
                record=self._clash_records[row]
                try:self.interaction.select_entities((record.part_a_id,record.part_b_id),origin="model_control");self.viewer.controller.fit_selection()
                except Exception:pass

        def _exact_selected_clash(self) -> None:
            row=self._clash_table.currentRow()
            if row<0 or row>=len(self._clash_records):QtWidgets.QMessageBox.information(self,"Model Control","Selecteer eerst een resultaat.");return
            record=self._clash_records[row]
            try:
                roots=tuple(Path(src.original_path).expanduser().resolve().parent for src in self.project.sources.values() if src.original_path)
                with ExactOcctPairEvaluator.open(self.load_result.project_path,source_search_roots=roots) as evaluator:
                    result=ModelControlEngine().scan(self.viewer.controller.index,self.project,entity_ids=(record.part_a_id,record.part_b_id),exact_pair_evaluator=evaluator)
                if result.records:
                    self._clash_records=self._clash_records[:row]+(result.records[0],)+self._clash_records[row+1:];self._model_control_done(type("R",(),{"records":self._clash_records,"stats":type("S",(),{"results":len(self._clash_records),"broad_phase_candidates":0})()})())
                    self._clash_table.selectRow(row)
                else:QtWidgets.QMessageBox.information(self,"Exact Model Control","Exacte BREP-check bevestigt geen clash/clearance issue voor dit paar.")
            except Exception as exc:QtWidgets.QMessageBox.warning(self,"Exact Model Control",f"{type(exc).__name__}: {exc}")

        # -----------------------------------------------------------------
        # Detached viewer / shortcuts / status / lifecycle
        def _detach_viewer(self) -> None:
            if self._detached is not None:self._detached.raise_();return
            self._viewer_host_layout.removeWidget(self.viewer);self.viewer.setParent(None);self._viewer_placeholder.show();detached=DetachedViewerWindow(self.viewer,self._settings,self);detached.attach_requested.connect(self._attach_viewer);self._detached=detached;detached.show()
        def _attach_viewer(self, viewer: Any) -> None:
            self._viewer_placeholder.hide();viewer.setParent(self._viewer_host);self._viewer_host_layout.insertWidget(1,viewer);self._detached=None;viewer.show()

        def _install_shortcuts(self) -> None:
            for sequence,callback in (("Ctrl+Z",self.viewer.controller.undo),("Ctrl+Y",self.viewer.controller.redo),("Esc",self._cancel_tool),("1",lambda:self.viewer.controller.set_standard_view(StandardView.FRONT)),("2",lambda:self.viewer.controller.set_standard_view(StandardView.RIGHT)),("3",lambda:self.viewer.controller.set_standard_view(StandardView.TOP)),("0",lambda:self.viewer.controller.set_standard_view(StandardView.ISOMETRIC))):
                shortcut=QtGui.QShortcut(QtGui.QKeySequence(sequence),self);shortcut.activated.connect(callback)

        def _build_status_bar(self) -> None:
            status=QtWidgets.QStatusBar();self.setStatusBar(status)
            report=self.load_result.geometry_report
            self._status_project=QtWidgets.QLabel(f"{getattr(self.project,'project_name','Project')} · {len(self.viewer.controller.index.renderable_node_ids):,} objecten · {len(self.load_result.repository):,} unieke meshes")
            status.addPermanentWidget(self._status_project,1)
            problems=int(report.failed_count)+int(report.partial_count)+int(report.proxy_count)
            problem=QtWidgets.QLabel(f"Geometrie: {report.ready_count} gereed · {report.partial_count} gedeeltelijk · {report.failed_count} fout · {report.proxy_count} proxy")
            problem.setObjectName("warningPill" if problems else "statusPill");status.addPermanentWidget(problem)
            problem.setToolTip("Objectaantal en uniek-meshaantal hoeven niet gelijk te zijn: identieke geometrieën worden bewust één keer geladen en instanced weergegeven.")

        def _restore_state(self) -> None:
            geometry=self._settings.value("viewer/v14Geometry")
            if geometry is not None:self.restoreGeometry(geometry)

        def closeEvent(self, event: Any) -> None:
            self._settings.setValue("viewer/v14Geometry",self.saveGeometry());self._scan_cancel.set()
            try:self._interaction_unsubscribe()
            except Exception:pass
            try:self.interaction.close()
            except Exception:pass
            super().closeEvent(event)


    def run_cws_viewer_cockpit(
        project_path: str | Path,
        *,
        cache_root: str | Path | None = None,
        source_search_roots: tuple[str | Path, ...] = (),
        ci_smoke: bool = False,
        screenshot_path: str | Path | None = None,
    ) -> int:
        """Open the professional V14 cockpit around the stable real scene loader."""
        app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([]);app.setApplicationName("CWS Viewer");app.setOrganizationName("CWS");app.setStyleSheet(theme_qss(DEFAULT_THEME))
        result=ProjectSceneLoader(cache_root=cache_root,source_search_roots=source_search_roots).load(project_path)
        window=CwsViewerCockpitWindow(result);window.show()
        if ci_smoke:
            def verify() -> None:
                try:
                    if screenshot_path:Path(screenshot_path).parent.mkdir(parents=True,exist_ok=True);window.grab().save(str(screenshot_path),"PNG")
                finally:window.close()
            QtCore.QTimer.singleShot(450,verify)
        return int(app.exec())

else:
    class CwsViewerCockpitWindow:  # pragma: no cover
        def __init__(self,*_:Any,**__:Any)->None:require_qt()
    def run_cws_viewer_cockpit(*_:Any,**__:Any)->int:require_qt();return 2


__all__=["CwsViewerCockpitWindow","DetachedViewerWindow","run_cws_viewer_cockpit"]
