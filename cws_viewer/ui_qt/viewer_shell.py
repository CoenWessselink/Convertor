"""Functional Qt V2 test shell for project tree + VTK viewer + properties."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cws_viewer.contracts.enums import ProjectionType, StandardView
from cws_viewer.contracts.events import SelectionChanged, VisibilityChanged
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_project_widget import VtkProjectWidget
from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2


_QSS = """
QMainWindow { background: #f7f9fc; color: #162a43; }
QToolBar { background: #ffffff; border-bottom: 1px solid #d8e2ee; spacing: 5px; padding: 6px; }
QToolButton { background: #ffffff; color: #0b55b5; border: 1px solid #cbd9e8; border-radius: 3px; padding: 7px 11px; }
QToolButton:hover { background: #eaf3ff; border-color: #7cacdf; }
QTreeWidget, QTableWidget { background: #ffffff; alternate-background-color: #f7faff; color: #20334a; border: 1px solid #d5e0ec; }
QHeaderView::section { background: #eff4fa; color: #50657d; border: 0; padding: 7px; }
QDockWidget::title { background: #f2f6fb; color: #173653; padding: 8px; font-weight: 600; }
QStatusBar { background: #ffffff; color: #667a91; border-top: 1px solid #d8e2ee; }
QLabel#statusPill { border-radius: 8px; padding: 4px 9px; background: #e7f7ef; color: #087a43; }
"""


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class ViewerMainWindow(QtWidgets.QMainWindow):
        def __init__(
            self,
            scene: ProjectScene | None = None,
            repository: MeshRepository | None = None,
        ) -> None:
            super().__init__()
            self.setObjectName("cwsViewerV2MainWindow")
            self.setWindowTitle("CWS Convertor · Viewer V15")
            self.resize(1480, 900)
            self.setStyleSheet(_QSS)
            self._syncing_selection = False
            self._items_by_node: dict[str, Any] = {}

            self.viewer = (
                VtkRealProjectWidgetFeelV2(repository, self)
                if repository is not None
                else VtkProjectWidget(self)
            )
            self.setCentralWidget(self.viewer)
            self._tree = self._create_tree_dock()
            self._properties = self._create_properties_dock()
            self._create_toolbar()
            self._status_pill = QtWidgets.QLabel("Gereed")
            self._status_pill.setObjectName("statusPill")
            self.statusBar().addPermanentWidget(self._status_pill)

            self.viewer.controller.subscribe(SelectionChanged, self._on_controller_selection)
            self.viewer.controller.subscribe(VisibilityChanged, self._on_visibility_changed)
            self.viewer.node_picked.connect(self._on_node_picked)
            self._tree.itemSelectionChanged.connect(self._on_tree_selection)

            self.load_scene(scene or build_synthetic_product_scene(1_000))

        def _create_tree_dock(self):
            dock = QtWidgets.QDockWidget("Projectstructuur", self)
            dock.setObjectName("cwsProjectTreeDock")
            dock.setAllowedAreas(
                QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
                | QtCore.Qt.DockWidgetArea.RightDockWidgetArea
            )
            tree = QtWidgets.QTreeWidget()
            tree.setHeaderLabels(["Object", "Type"])
            tree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            tree.setAlternatingRowColors(True)
            tree.setUniformRowHeights(True)
            dock.setWidget(tree)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, dock)
            dock.setMinimumWidth(320)
            return tree

        def _create_properties_dock(self):
            dock = QtWidgets.QDockWidget("Eigenschappen", self)
            dock.setObjectName("cwsPropertiesDock")
            table = QtWidgets.QTableWidget(0, 2)
            table.setHorizontalHeaderLabels(["Eigenschap", "Waarde"])
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().hide()
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            dock.setWidget(table)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
            dock.setMinimumWidth(340)
            return table

        def _action(self, toolbar, text: str, slot, shortcut: str | None = None):
            action = QtGui.QAction(text, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(slot)
            toolbar.addAction(action)
            return action

        def _create_toolbar(self) -> None:
            toolbar = self.addToolBar("Viewer")
            toolbar.setObjectName("cwsViewerToolbar")
            toolbar.setMovable(False)
            self._action(toolbar, "Fit", self.viewer.controller.fit_all, "F")
            self._action(toolbar, "Iso", lambda: self.viewer.controller.set_standard_view(StandardView.ISOMETRIC), "0")
            self._action(toolbar, "Boven", lambda: self.viewer.controller.set_standard_view(StandardView.TOP), "2")
            self._action(toolbar, "Voor", lambda: self.viewer.controller.set_standard_view(StandardView.FRONT), "1")
            toolbar.addSeparator()
            self._action(toolbar, "Verbergen", self._hide_selected, "H")
            self._action(toolbar, "Isoleren", self._isolate_selected, "I")
            self._action(toolbar, "Ghost", self._ghost_selected, "G")
            self._action(toolbar, "Alles tonen", self.viewer.controller.show_all, "A")
            toolbar.addSeparator()
            self._action(toolbar, "Perspectief", lambda: self.viewer.controller.set_projection(ProjectionType.PERSPECTIVE))
            self._action(toolbar, "Orthografisch", lambda: self.viewer.controller.set_projection(ProjectionType.ORTHOGRAPHIC))

        def load_scene(self, scene: ProjectScene) -> None:
            self.viewer.load_scene(scene)
            self._populate_tree()
            self._status_pill.setText(f"{len(self.viewer.controller.index.renderable_node_ids):,} objecten")

        def _populate_tree(self) -> None:
            index = self.viewer.controller.index
            self._tree.clear()
            self._items_by_node.clear()

            def add_node(node_id: str, parent_item: Any | None) -> None:
                node = index.node(node_id)
                item = QtWidgets.QTreeWidgetItem([node.name, node.kind.value])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, node_id)
                if parent_item is None:
                    self._tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)
                self._items_by_node[node_id] = item
                for child_id in index.children_by_parent.get(node_id, ()):
                    add_node(child_id, item)

            for root_id in index.root_node_ids:
                add_node(root_id, None)
            self._tree.expandToDepth(1)
            self._tree.resizeColumnToContents(0)

        def _selected_ids(self) -> tuple[str, ...]:
            values = []
            for item in self._tree.selectedItems():
                node_id = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if node_id:
                    values.append(str(node_id))
            return tuple(dict.fromkeys(values))

        def _on_tree_selection(self) -> None:
            if self._syncing_selection:
                return
            self.viewer.controller.set_selection(self._selected_ids())

        def _on_controller_selection(self, event: SelectionChanged) -> None:
            selection = () if event.selection is None else event.selection.node_ids
            self._syncing_selection = True
            try:
                self._tree.clearSelection()
                for node_id in selection:
                    item = self._items_by_node.get(node_id)
                    if item is not None:
                        item.setSelected(True)
                        self._tree.scrollToItem(item)
                self._show_properties(selection[-1] if selection else None)
            finally:
                self._syncing_selection = False

        def _on_node_picked(self, node_id: str) -> None:
            self._status_pill.setText(f"Geselecteerd: {node_id}")

        def _on_visibility_changed(self, event: VisibilityChanged) -> None:
            self.statusBar().showMessage(
                f"Zichtbaar {len(event.visible_node_ids):,} · verborgen {len(event.hidden_node_ids):,} · ghost {len(event.ghosted_node_ids):,}",
                4000,
            )

        def _show_properties(self, node_id: str | None) -> None:
            self._properties.setRowCount(0)
            if node_id is None:
                return
            node = self.viewer.controller.index.node(node_id)
            rows = (
                ("Node-ID", node.node_id),
                ("Entity-ID", node.entity_id),
                ("Type", node.kind.value),
                ("Naam", node.name),
                ("Bronentity", node.source_entity_id or ""),
                ("Geometry", node.geometry_id or ""),
                ("Geometry hash", node.geometry_hash or ""),
                ("Manufacturing hash", node.manufacturing_hash or ""),
                ("Tags", ", ".join(node.tags)),
            )
            self._properties.setRowCount(len(rows))
            for row, (name, value) in enumerate(rows):
                self._properties.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
                self._properties.setItem(row, 1, QtWidgets.QTableWidgetItem(value))
            self._properties.resizeColumnsToContents()

        def _hide_selected(self) -> None:
            ids = self.viewer.controller.get_selection()
            if ids:
                self.viewer.controller.hide(ids)

        def _isolate_selected(self) -> None:
            ids = self.viewer.controller.get_selection()
            if ids:
                self.viewer.controller.isolate(ids)

        def _ghost_selected(self) -> None:
            ids = self.viewer.controller.get_selection()
            if ids:
                self.viewer.controller.isolate(ids, ghost_context=True)

        def closeEvent(self, event: Any) -> None:
            self.viewer.controller.shutdown()
            super().closeEvent(event)


    def create_viewer_window(
        scene: ProjectScene | None = None,
        repository: MeshRepository | None = None,
    ) -> ViewerMainWindow:
        return ViewerMainWindow(scene, repository)


    def run_viewer_shell(
        *,
        node_count: int = 1_000,
        ci_smoke: bool = False,
        report_path: str | Path | None = None,
        screenshot_path: str | Path | None = None,
    ) -> int:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setApplicationName("CWS Viewer V2")
        window = ViewerMainWindow(build_synthetic_product_scene(node_count))
        window.show()

        if ci_smoke:
            report = Path(report_path) if report_path else None
            screenshot = Path(screenshot_path) if screenshot_path else None

            def execute_smoke() -> None:
                payload: dict[str, Any] = {"status": "failed", "node_count": node_count}
                try:
                    controller = window.viewer.controller
                    controller.set_selection(("node:item:000010",))
                    controller.isolate(("node:assembly:0000",), ghost_context=True)
                    controller.orbit(12.0, 4.0)
                    controller.zoom(1.15)
                    controller.fit_selection()
                    if screenshot:
                        screenshot.parent.mkdir(parents=True, exist_ok=True)
                        window.grab().save(str(screenshot), "PNG")
                    payload.update(
                        {
                            "status": "passed",
                            "scene_hash": controller.index.scene.scene_hash,
                            "selection": list(controller.get_selection()),
                            "visible_count": len(controller.session.render_state(controller.index).visible_node_ids),
                            "qt_version": QtCore.qVersion(),
                        }
                    )
                except Exception as exc:  # pragma: no cover - Windows evidence
                    payload["error"] = f"{type(exc).__name__}: {exc}"
                finally:
                    if report:
                        report.parent.mkdir(parents=True, exist_ok=True)
                        report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                    window.close()
                    app.quit()

            QtCore.QTimer.singleShot(1200, execute_smoke)
        return int(app.exec())

else:

    class ViewerMainWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    def create_viewer_window(scene: ProjectScene | None = None):  # pragma: no cover
        require_qt()

    def run_viewer_shell(**_: Any) -> int:  # pragma: no cover
        require_qt()
        return 2


__all__ = ["ViewerMainWindow", "create_viewer_window", "run_viewer_shell"]
