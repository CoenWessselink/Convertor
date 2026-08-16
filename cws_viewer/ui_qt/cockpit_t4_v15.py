"""CWS Viewer V15 T4 cockpit: selection, properties, measurements and snapping."""
from __future__ import annotations

from typing import Any

from cws_viewer.core.v15_selection_measurement import (
    V15_T4_SCHEMA,
    V15_T4_VERSION,
    selection_measurement_contract,
)
from cws_viewer.ui_qt.cockpit_t3_v15 import (
    CwsViewerV15T3CockpitWindow,
    t3_workspace_contract,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.selection_measurement_v15 import V15SelectionMeasurementPanel

V15_T4_WORKSPACE_SCHEMA = "cws-viewer-workspace-15.1"
V15_T4_WORKSPACE_STATE_VERSION = 15


def t4_workspace_contract() -> dict[str, Any]:
    contract = t3_workspace_contract()
    contract["schema"] = V15_T4_WORKSPACE_SCHEMA
    contract["state_version"] = V15_T4_WORKSPACE_STATE_VERSION
    contract["version"] = V15_T4_VERSION
    contract["docks"] = [
        *contract.get("docks", []),
        {
            "key": "selection",
            "title": "Selectie / meten",
            "area": "right",
            "default_size": 350,
        },
    ]
    capabilities = dict(contract.get("capabilities", {}))
    capabilities.update(selection_measurement_contract()["capabilities"])
    contract["capabilities"] = capabilities
    contract["selection_measurement"] = selection_measurement_contract()
    return contract


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class CwsViewerV15T4CockpitWindow(CwsViewerV15T3CockpitWindow):
        """T4 interaction shell without changing canonical geometry ownership."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._t4_property_filter: Any | None = None
            super().__init__(*args, **kwargs)
            self.setObjectName("cwsViewerV15T4CockpitWindow")
            self.setWindowTitle(
                f"CWS Viewer V15 T4 — {getattr(self.project, 'project_name', 'Project')}"
            )
            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText(V15_T4_VERSION)
                    break
            self._install_t4_property_tools()
            self._install_t4_selection_dock()
            self._restore_v15_state()
            self._refresh_properties()
            self.statusBar().showMessage(
                "T4 actief · hierarchy picking · grouped properties · snap/proof feedback · geometry-based measurements",
                7000,
            )

        def _install_t4_selection_dock(self) -> None:
            panel = V15SelectionMeasurementPanel(
                self.viewer,
                mesh_repository=self.load_result.repository,
                parent=self,
            )
            panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 4500)
            )
            panel.open_measurements_requested.connect(self._focus_viewer_tools)
            panel.open_exact_workbench_requested.connect(self._open_exact_workbench)
            dock = QtWidgets.QDockWidget("Selectie / meten", self)
            dock.setObjectName("cwsV15Dock_selection")
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
            dock.setFeatures(
                QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            )
            dock.setWidget(panel)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
            self._selection_panel = panel
            self._selection_dock = dock
            self._v15_docks["selection"] = dock
            try:
                self.tabifyDockWidget(self._view_dock, self._selection_dock)
                self._view_dock.raise_()
            except Exception:
                pass
            menu = self.menuBar().addMenu("Selectie T4")
            menu.addAction(dock.toggleViewAction())
            menu.addAction("Vensterselectie", lambda: self.viewer.set_area_selection(True))
            menu.addAction("Alles zichtbaar selecteren", panel.service.select_all_visible)
            menu.addAction("Selectie omkeren", panel.service.invert_visible_selection)
            menu.addAction("Selectie wissen", panel.service.clear_selection)

        def _install_t4_property_tools(self) -> None:
            self._properties.setContextMenuPolicy(
                QtCore.Qt.ContextMenuPolicy.CustomContextMenu
            )
            self._properties.customContextMenuRequested.connect(
                self._t4_property_context_menu
            )
            parent = self._properties.parentWidget()
            layout = parent.layout() if parent is not None else None
            if layout is not None:
                self._t4_property_filter = QtWidgets.QLineEdit(parent)
                self._t4_property_filter.setPlaceholderText(
                    "Zoek eigenschap, waarde of herkomst…"
                )
                self._t4_property_filter.setClearButtonEnabled(True)
                self._t4_property_filter.textChanged.connect(
                    lambda _text: self._refresh_properties()
                )
                layout.insertWidget(1, self._t4_property_filter)

        def _t4_property_context_menu(self, position: Any) -> None:
            item = self._properties.itemAt(position)
            if item is None:
                return
            menu = QtWidgets.QMenu(self._properties)
            menu.addAction(
                "Kopieer waarde",
                lambda: QtWidgets.QApplication.clipboard().setText(item.text(1)),
            )
            menu.addAction(
                "Kopieer eigenschap + waarde",
                lambda: QtWidgets.QApplication.clipboard().setText(
                    f"{item.text(0)}: {item.text(1)}"
                ),
            )
            raw_key = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if raw_key:
                menu.addAction(
                    "Kopieer property key",
                    lambda: QtWidgets.QApplication.clipboard().setText(str(raw_key)),
                )
            menu.exec(self._properties.viewport().mapToGlobal(position))

        def _refresh_properties(self) -> None:
            if not hasattr(self, "_properties"):
                return
            self._properties.clear()
            try:
                records = tuple(self.interaction.properties_for_primary())
            except Exception:
                records = ()
            query = ""
            if self._t4_property_filter is not None:
                query = self._t4_property_filter.text().casefold().strip()
            groups: dict[str, list[Any]] = {}
            for record in records:
                haystack = " ".join(
                    (
                        str(record.group),
                        str(record.label),
                        str(record.value),
                        str(record.provenance),
                        str(record.key),
                    )
                ).casefold()
                if query and query not in haystack:
                    continue
                groups.setdefault(str(record.group or "Algemeen"), []).append(record)
            for group_name, group_records in groups.items():
                group = QtWidgets.QTreeWidgetItem([group_name, "", "", ""])
                font = group.font(0)
                font.setBold(True)
                group.setFont(0, font)
                group.setFlags(group.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
                self._properties.addTopLevelItem(group)
                for record in group_records:
                    confidence = (
                        ""
                        if record.confidence is None
                        else f"{float(record.confidence):.0%}"
                    )
                    value = str(record.value)
                    if record.unit and value:
                        value = f"{value} {record.unit}"
                    item = QtWidgets.QTreeWidgetItem(
                        [
                            str(record.label),
                            value,
                            str(record.provenance),
                            confidence,
                        ]
                    )
                    item.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(record.key))
                    group.addChild(item)
                group.setExpanded(True)
            self._properties.resizeColumnToContents(0)
            self._properties.resizeColumnToContents(1)

        def _selection_changed(self, selection: Any) -> None:
            super()._selection_changed(selection)
            panel = getattr(self, "_selection_panel", None)
            if panel is not None:
                panel.refresh()

        def _reset_v15_layout(self) -> None:
            super()._reset_v15_layout()
            if hasattr(self, "_selection_dock"):
                self._selection_dock.setFloating(False)
                self.addDockWidget(
                    QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                    self._selection_dock,
                )
                self._selection_dock.show()
                try:
                    self.tabifyDockWidget(self._view_dock, self._selection_dock)
                except Exception:
                    pass

else:

    class CwsViewerV15T4CockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15T4CockpitWindow",
    "V15_T4_SCHEMA",
    "V15_T4_VERSION",
    "V15_T4_WORKSPACE_SCHEMA",
    "V15_T4_WORKSPACE_STATE_VERSION",
    "t4_workspace_contract",
]
