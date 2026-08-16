"""CWS Viewer V15 dockable engineering workspace.

The mature V14 cockpit remains the functional baseline. V15 composes that
baseline into a dockable, persistent engineering desktop with a CWS-specific
workspace and Project Explorer contract. Third-party products are behavioural
benchmarks only; this module contains CWS-owned UI logic and CWS data contracts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cws_viewer.ui_qt import cockpit as _v14
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

V15_WORKSPACE_SCHEMA = "cws-viewer-workspace-15.1"
V15_WORKSPACE_STATE_VERSION = 15
V15_VERSION = "1.4.0-v15-preview.1"


@dataclass(frozen=True, slots=True)
class V15WorkspaceDockSpec:
    key: str
    title: str
    area: str
    default_size: int


V15_DOCK_SPECS: tuple[V15WorkspaceDockSpec, ...] = (
    V15WorkspaceDockSpec("project", "Project Explorer", "left", 320),
    V15WorkspaceDockSpec("properties", "Eigenschappen", "right", 390),
    V15WorkspaceDockSpec("workbench", "Project / Review", "bottom", 300),
)


def workspace_contract() -> dict[str, Any]:
    """Return the machine-readable V15 workspace contract used by self-tests."""
    return {
        "schema": V15_WORKSPACE_SCHEMA,
        "state_version": V15_WORKSPACE_STATE_VERSION,
        "version": V15_VERSION,
        "docks": [
            {
                "key": spec.key,
                "title": spec.title,
                "area": spec.area,
                "default_size": spec.default_size,
            }
            for spec in V15_DOCK_SPECS
        ],
        "capabilities": {
            "dockable_panels": True,
            "floating_panels": True,
            "persistent_layout": True,
            "focus_viewer_mode": True,
            "reset_layout": True,
            "v14_functionality_preserved": True,
            "rich_project_search": True,
            "project_tree_context_actions": True,
            "select_descendants": True,
            "select_parent": True,
            "select_assembly": True,
            "copy_canonical_ids": True,
        },
    }


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class CwsViewerV15CockpitWindow(_v14.CwsViewerCockpitWindow):
        """V15 workspace shell around the proven V14 viewer implementation."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._v15_docks_ready = False
            self._v15_focus_snapshot: dict[str, bool] | None = None
            super().__init__(*args, **kwargs)
            self.setObjectName("cwsViewerV15CockpitWindow")
            self.setWindowTitle(
                f"CWS Viewer V15 — {getattr(self.project, 'project_name', 'Project')}"
            )
            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText(V15_VERSION)
                    break
            self.setDockNestingEnabled(True)
            self.setCorner(QtCore.Qt.Corner.TopLeftCorner, QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)
            self.setCorner(QtCore.Qt.Corner.BottomLeftCorner, QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)
            self.setCorner(QtCore.Qt.Corner.TopRightCorner, QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
            self.setCorner(QtCore.Qt.Corner.BottomRightCorner, QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
            self._install_v15_docks()
            self._install_v15_workspace_menu()
            self._install_v15_project_explorer()
            self._v15_docks_ready = True
            self._restore_v15_state()
            try:
                self.statusBar().showMessage(
                    "V15 werkruimte actief · dockable panels · rijke Project Explorer · canonical selectie",
                    6500,
                )
            except Exception:
                pass

        @staticmethod
        def _panel_ancestor(widget: Any) -> Any:
            current = widget.parentWidget() if widget is not None else None
            while current is not None:
                if current.objectName() == "cwsPanel":
                    return current
                current = current.parentWidget()
            raise RuntimeError("CWS panel ancestor not found")

        @staticmethod
        def _hide_embedded_panel_title(panel: Any) -> None:
            for label in panel.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsPanelTitle":
                    label.hide()
                    break

        def _new_dock(self, spec: V15WorkspaceDockSpec, widget: Any) -> Any:
            dock = QtWidgets.QDockWidget(spec.title, self)
            dock.setObjectName(f"cwsV15Dock_{spec.key}")
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
            dock.setFeatures(
                QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            )
            widget.setParent(dock)
            dock.setWidget(widget)
            area = {
                "left": QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                "right": QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                "bottom": QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
            }[spec.area]
            self.addDockWidget(area, dock)
            return dock

        def _install_v15_docks(self) -> None:
            project_panel = self._panel_ancestor(self._tree)
            properties_panel = self._panel_ancestor(self._properties)
            self._hide_embedded_panel_title(project_panel)
            self._hide_embedded_panel_title(properties_panel)
            project_panel.setParent(None)
            properties_panel.setParent(None)
            self._tabs.setParent(None)

            spec_by_key = {spec.key: spec for spec in V15_DOCK_SPECS}
            self._project_dock = self._new_dock(spec_by_key["project"], project_panel)
            self._properties_dock = self._new_dock(spec_by_key["properties"], properties_panel)
            self._workbench_dock = self._new_dock(spec_by_key["workbench"], self._tabs)
            self._v15_docks = {
                "project": self._project_dock,
                "properties": self._properties_dock,
                "workbench": self._workbench_dock,
            }
            self._reset_v15_dock_sizes()

        def _install_v15_workspace_menu(self) -> None:
            menu = self.menuBar().addMenu("Werkruimte")
            for key in ("project", "properties", "workbench"):
                menu.addAction(self._v15_docks[key].toggleViewAction())
            menu.addSeparator()
            focus = QtGui.QAction("Alleen 3D Viewer", self)
            focus.setShortcut(QtGui.QKeySequence("F10"))
            focus.triggered.connect(self._toggle_v15_focus_mode)
            menu.addAction(focus)
            restore = QtGui.QAction("Alle panelen tonen", self)
            restore.triggered.connect(self._show_all_v15_docks)
            menu.addAction(restore)
            reset = QtGui.QAction("Standaardindeling herstellen", self)
            reset.triggered.connect(self._reset_v15_layout)
            menu.addAction(reset)

        def _install_v15_project_explorer(self) -> None:
            self._tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self._tree.customContextMenuRequested.connect(self._v15_tree_context_menu)
            self._tree.itemDoubleClicked.connect(lambda *_args: self.viewer.controller.fit_selection())
            self._tree.setToolTip(
                "Zoek op objectnaam, canonical ID, merk, profiel, materiaal of assembly. "
                "Rechtsklik voor selectie- en zichtbaarheidstools."
            )
            self._tree_filter.setPlaceholderText(
                "Zoek object, ID, merk, profiel, materiaal, assembly …"
            )

        def _item_node_id(self, item: Any) -> str:
            value = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            return str(value) if value else ""

        def _item_entity_id(self, item: Any) -> str:
            node_id = self._item_node_id(item)
            if not node_id:
                return ""
            try:
                return str(self.viewer.controller.index.node(node_id).entity_id or "")
            except Exception:
                return ""

        def _v15_search_blob(self, item: Any) -> str:
            values = [item.text(i) for i in range(item.columnCount())]
            node_id = self._item_node_id(item)
            entity_id = self._item_entity_id(item)
            values.extend((node_id, entity_id))
            part = None
            try:
                part = self.project.parts.get(entity_id)
            except Exception:
                part = None
            if part is not None:
                for name in (
                    "part_position", "profile", "profile_type", "material", "material_grade",
                    "part_type", "name", "source_id", "source_object_id",
                ):
                    value = getattr(part, name, None)
                    if value not in (None, ""):
                        values.append(str(value))
                assemblies = getattr(part, "assembly_ids", ()) or ()
                values.extend(str(value) for value in assemblies)
            return " ".join(values).casefold()

        def _filter_tree(self, text: str) -> None:
            query = str(text or "").casefold().strip()

            def visit(item: Any) -> bool:
                own = not query or query in self._v15_search_blob(item)
                child_match = False
                for index in range(item.childCount()):
                    child_match = visit(item.child(index)) or child_match
                show = own or child_match
                item.setHidden(not show)
                if child_match and query:
                    item.setExpanded(True)
                return show

            for index in range(self._tree.topLevelItemCount()):
                visit(self._tree.topLevelItem(index))

        def _selected_tree_node_ids(self) -> tuple[str, ...]:
            ids = [self._item_node_id(item) for item in self._tree.selectedItems()]
            return tuple(dict.fromkeys(value for value in ids if value))

        def _select_tree_node_ids(self, node_ids: tuple[str, ...]) -> None:
            if node_ids:
                self.interaction.select_nodes(node_ids, origin="v15_project_explorer")

        def _v15_select_descendants(self) -> None:
            collected: list[str] = []

            def add(item: Any) -> None:
                node_id = self._item_node_id(item)
                if node_id:
                    collected.append(node_id)
                for index in range(item.childCount()):
                    add(item.child(index))

            for item in self._tree.selectedItems():
                add(item)
            self._select_tree_node_ids(tuple(dict.fromkeys(collected)))

        def _v15_select_parent(self) -> None:
            parents: list[str] = []
            for item in self._tree.selectedItems():
                parent = item.parent()
                if parent is not None:
                    node_id = self._item_node_id(parent)
                    if node_id:
                        parents.append(node_id)
            self._select_tree_node_ids(tuple(dict.fromkeys(parents)))

        def _v15_select_assembly(self) -> None:
            selected_entities = [self._item_entity_id(item) for item in self._tree.selectedItems()]
            assembly_ids: set[str] = set()
            for entity_id in selected_entities:
                try:
                    part = self.project.parts.get(entity_id)
                except Exception:
                    part = None
                if part is not None:
                    assembly_ids.update(str(value) for value in (getattr(part, "assembly_ids", ()) or ()))
            if not assembly_ids:
                self.statusBar().showMessage("Geen assemblyrelatie op de huidige selectie", 3500)
                return
            target_entities: set[str] = set()
            try:
                for entity_id, part in self.project.parts.items():
                    part_assemblies = {str(value) for value in (getattr(part, "assembly_ids", ()) or ())}
                    if assembly_ids.intersection(part_assemblies):
                        target_entities.add(str(entity_id))
            except Exception:
                pass
            node_ids: list[str] = []
            index = self.viewer.controller.index
            for node_id in index.renderable_node_ids:
                try:
                    if str(index.node(node_id).entity_id) in target_entities:
                        node_ids.append(str(node_id))
                except Exception:
                    continue
            self._select_tree_node_ids(tuple(node_ids))

        def _v15_copy_ids(self) -> None:
            values: list[str] = []
            for item in self._tree.selectedItems():
                entity_id = self._item_entity_id(item)
                node_id = self._item_node_id(item)
                if entity_id:
                    values.append(entity_id)
                elif node_id:
                    values.append(node_id)
            if values:
                QtWidgets.QApplication.clipboard().setText("\n".join(dict.fromkeys(values)))
                self.statusBar().showMessage(f"{len(set(values))} canonical ID(s) gekopieerd", 2500)

        def _v15_show_selected(self) -> None:
            node_ids = self._selected_tree_node_ids()
            if node_ids:
                self.viewer.controller.show(node_ids)

        def _v15_tree_context_menu(self, position: Any) -> None:
            menu = QtWidgets.QMenu(self._tree)
            menu.addAction("Fit selectie", self.viewer.controller.fit_selection)
            menu.addAction("Isoleer selectie", self._isolate_selected)
            menu.addAction("Verberg selectie", self._hide_selected)
            menu.addAction("Toon selectie", self._v15_show_selected)
            menu.addSeparator()
            menu.addAction("Selecteer inclusief onderliggende objecten", self._v15_select_descendants)
            menu.addAction("Selecteer bovenliggend object", self._v15_select_parent)
            menu.addAction("Selecteer assembly", self._v15_select_assembly)
            menu.addSeparator()
            menu.addAction("Kopieer canonical ID", self._v15_copy_ids)
            if len(self._tree.selectedItems()) == 1:
                menu.addAction("Open Exact Part Workbench", self._open_exact_workbench)
            menu.exec(self._tree.viewport().mapToGlobal(position))

        def _reset_v15_dock_sizes(self) -> None:
            try:
                self.resizeDocks(
                    [self._project_dock, self._properties_dock],
                    [320, 390],
                    QtCore.Qt.Orientation.Horizontal,
                )
                self.resizeDocks(
                    [self._workbench_dock],
                    [300],
                    QtCore.Qt.Orientation.Vertical,
                )
            except Exception:
                pass

        def _show_all_v15_docks(self) -> None:
            self._v15_focus_snapshot = None
            for dock in self._v15_docks.values():
                dock.setFloating(False)
                dock.show()
            self._reset_v15_dock_sizes()

        def _toggle_v15_focus_mode(self) -> None:
            if self._v15_focus_snapshot is None:
                self._v15_focus_snapshot = {
                    key: bool(dock.isVisible()) for key, dock in self._v15_docks.items()
                }
                for dock in self._v15_docks.values():
                    dock.hide()
                self.statusBar().showMessage("Focusmodus: alleen 3D Viewer · F10 om te herstellen", 5000)
                return
            snapshot = self._v15_focus_snapshot
            self._v15_focus_snapshot = None
            for key, dock in self._v15_docks.items():
                dock.setVisible(bool(snapshot.get(key, True)))

        def _reset_v15_layout(self) -> None:
            for key, spec in ((spec.key, spec) for spec in V15_DOCK_SPECS):
                dock = self._v15_docks[key]
                dock.setFloating(False)
                area = {
                    "left": QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
                    "right": QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                    "bottom": QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
                }[spec.area]
                self.addDockWidget(area, dock)
                dock.show()
            self._v15_focus_snapshot = None
            self._tabs.setCurrentIndex(0)
            self._reset_v15_dock_sizes()

        def _restore_state(self) -> None:
            """Base-init hook: restore geometry safely before V15 docks exist."""
            geometry = self._settings.value("viewer/v15Geometry")
            if geometry is None:
                geometry = self._settings.value("viewer/v14Geometry")
            if geometry is not None:
                self.restoreGeometry(geometry)
            if getattr(self, "_v15_docks_ready", False):
                self._restore_v15_state()

        def _restore_v15_state(self) -> None:
            state = self._settings.value("viewer/v15DockState")
            if state is not None:
                try:
                    self.restoreState(state, V15_WORKSPACE_STATE_VERSION)
                except Exception:
                    pass
            try:
                tab = int(self._settings.value("viewer/v15BottomTab", 0))
                if 0 <= tab < self._tabs.count():
                    self._tabs.setCurrentIndex(tab)
            except Exception:
                pass
            try:
                text = str(self._settings.value("viewer/v15TreeFilter", "") or "")
                if text:
                    self._tree_filter.setText(text)
            except Exception:
                pass

        def closeEvent(self, event: Any) -> None:
            try:
                self._settings.setValue("viewer/v15Geometry", self.saveGeometry())
                self._settings.setValue(
                    "viewer/v15DockState",
                    self.saveState(V15_WORKSPACE_STATE_VERSION),
                )
                self._settings.setValue("viewer/v15BottomTab", self._tabs.currentIndex())
                self._settings.setValue("viewer/v15TreeFilter", self._tree_filter.text())
                self._settings.setValue("viewer/v15WorkspaceSchema", V15_WORKSPACE_SCHEMA)
                self._settings.sync()
            finally:
                super().closeEvent(event)


else:
    class CwsViewerV15CockpitWindow:  # pragma: no cover - Qt absent
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15CockpitWindow",
    "V15_DOCK_SPECS",
    "V15_VERSION",
    "V15_WORKSPACE_SCHEMA",
    "V15_WORKSPACE_STATE_VERSION",
    "V15WorkspaceDockSpec",
    "workspace_contract",
]
