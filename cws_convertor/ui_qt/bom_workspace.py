"""Canonical BOM production hub with shared selection and Viewer projection."""
from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from cws_convertor.bom.export import export_bom_package
from cws_convertor.bom.workspace import (
    BOM_FAMILIES,
    BOM_FAMILY_LABELS,
    BOMScope,
    BOMWorkspaceReadModel,
    BOMWorkspaceRow,
    scoped_bom_snapshot,
)
from cws_convertor.machine_routing import MachineRoutingService
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


def _number(value: Any, decimals: int = 1) -> str:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return "-"
    return f"{number:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class _BomViewerPane(QtWidgets.QFrame):
        """Lazy secondary renderer over the active workspace scene/cache."""

        selection_requested = QtCore.Signal(object)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("bomViewerPane")
            self._workspace: Any | None = None
            self._selection: Any | None = None
            self._viewer: Any | None = None
            self._nodes_by_entity: dict[str, tuple[str, ...]] = {}
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)
            bar = QtWidgets.QHBoxLayout()
            bar.setContentsMargins(8, 5, 8, 5)
            title = QtWidgets.QLabel("3D Viewer · gedeelde selectie")
            title.setObjectName("panelHeading")
            bar.addWidget(title)
            bar.addStretch(1)
            for label, callback in (
                ("Fit", self.fit_selection),
                ("Isoleer", self.isolate_selection),
                ("Ghost", self.ghost_selection),
                ("Alles", self.show_all),
            ):
                button = QtWidgets.QPushButton(label)
                button.clicked.connect(callback)
                bar.addWidget(button)
            root.addLayout(bar)
            self.host = QtWidgets.QStackedWidget()
            self.placeholder = QtWidgets.QLabel(
                "Open een project om de gekoppelde Viewer te laden."
            )
            self.placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.placeholder.setObjectName("mutedText")
            self.host.addWidget(self.placeholder)
            root.addWidget(self.host, 1)

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            changed = workspace is not self._workspace
            self._workspace = workspace
            self._selection = selection
            if changed:
                self._dispose_viewer()
            if workspace is not None and self.isVisible():
                self._ensure_viewer()
            self._sync_selection()

        def showEvent(self, event: Any) -> None:
            super().showEvent(event)
            if self._workspace is not None:
                self._ensure_viewer()
                self._sync_selection()

        def _ensure_viewer(self) -> None:
            if self._viewer is not None or self._workspace is None:
                return
            if os.environ.get("CWS_HEADLESS_GUI_SMOKE") == "1":
                self.placeholder.setText("3D Viewer actief · headless testprojectie")
                return
            try:
                from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import (
                    VtkRealProjectWidgetFeelV2,
                )

                viewer = VtkRealProjectWidgetFeelV2(self._workspace.load_result.repository)
                viewer.setMinimumSize(320, 260)
                viewer.load_scene(self._workspace.load_result.scene)
                by_entity: dict[str, list[str]] = defaultdict(list)
                for node in self._workspace.load_result.scene.nodes:
                    by_entity[str(node.entity_id)].append(str(node.node_id))
                self._nodes_by_entity = {
                    key: tuple(values) for key, values in by_entity.items()
                }
                if hasattr(viewer, "node_picked"):
                    viewer.node_picked.connect(self._viewer_picked)
                self._viewer = viewer
                self.host.addWidget(viewer)
                self.host.setCurrentWidget(viewer)
                QtCore.QTimer.singleShot(0, viewer.controller.fit_all)
            except Exception as exc:
                self.placeholder.setText(
                    f"Viewer-projectie niet beschikbaar\n{type(exc).__name__}: {exc}"
                )

        def _dispose_viewer(self) -> None:
            viewer = self._viewer
            self._viewer = None
            self._nodes_by_entity.clear()
            self.host.setCurrentWidget(self.placeholder)
            if viewer is not None:
                self.host.removeWidget(viewer)
                viewer.close()
                viewer.deleteLater()

        def _viewer_picked(self, _node_id: str) -> None:
            if self._viewer is None:
                return
            index = self._viewer.controller.index
            entity_ids = tuple(dict.fromkeys(
                index.node(node_id).entity_id
                for node_id in self._viewer.controller.session.selection
                if node_id in index.nodes_by_id
            ))
            self.selection_requested.emit(entity_ids)

        def _sync_selection(self) -> None:
            if self._viewer is None:
                return
            ids = tuple(getattr(self._selection, "entity_ids", ()) or ())
            nodes = tuple(
                node_id for entity_id in ids
                for node_id in self._nodes_by_entity.get(str(entity_id), ())
            )
            if tuple(self._viewer.controller.session.selection) != nodes:
                self._viewer.controller.set_selection(nodes)

        def fit_selection(self) -> None:
            if self._viewer is not None:
                if self._viewer.controller.session.selection:
                    self._viewer.controller.fit_selection()
                else:
                    self._viewer.controller.fit_all()

        def isolate_selection(self) -> None:
            if self._viewer is not None and self._viewer.controller.session.selection:
                self._viewer.controller.isolate(
                    self._viewer.controller.session.selection,
                    ghost_context=False,
                )

        def ghost_selection(self) -> None:
            if self._viewer is not None and self._viewer.controller.session.selection:
                self._viewer.controller.isolate(
                    self._viewer.controller.session.selection,
                    ghost_context=True,
                )

        def show_all(self) -> None:
            if self._viewer is not None:
                self._viewer.controller.show_all()

        def closeEvent(self, event: Any) -> None:
            self._dispose_viewer()
            super().closeEvent(event)


    class BomWorkspacePanel(QtWidgets.QWidget):
        """BOM production hub over the canonical snapshot and stable-ID bus."""

        action_requested = QtCore.Signal(str)
        show_project_requested = QtCore.Signal()
        COLUMNS = (
            "Merk / sleutel", "Omschrijving", "Profiel / maat", "Materiaal",
            "Lengte (mm)", "Aantal", "Gewicht (kg)", "Oppervlakte (m²)",
            "Machine", "Tekening", "Status",
        )

        def __init__(
            self,
            window: Any,
            parent: Any | None = None,
            *,
            allow_detach: bool = True,
        ) -> None:
            super().__init__(parent)
            self.window = window
            self._workspace: Any | None = None
            self._selection: Any | None = None
            self._read_model: BOMWorkspaceReadModel | None = None
            self._display_rows: dict[int, BOMWorkspaceRow] = {}
            self._visible_rows: tuple[BOMWorkspaceRow, ...] = ()
            self._syncing = False
            self._allow_detach = allow_detach
            self._detached_windows: list[Any] = []
            self._settings = QtCore.QSettings("CWS", "CWS Convertor")

            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(6)
            root.addWidget(self._header())
            root.addLayout(self._command_bar())

            self.family_tabs = QtWidgets.QTabBar()
            self.family_tabs.setObjectName("bomFamilyTabs")
            self.family_tabs.setExpanding(False)
            self.family_tabs.setMovable(False)
            for family in BOM_FAMILIES:
                self.family_tabs.addTab(BOM_FAMILY_LABELS[family])
                self.family_tabs.setTabData(self.family_tabs.count() - 1, family)
            self.family_tabs.currentChanged.connect(self.refresh)
            root.addWidget(self.family_tabs)

            root.addWidget(self._action_bar())

            self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            self.splitter.setObjectName("bomViewerSplitter")
            self.splitter.setChildrenCollapsible(False)
            self.splitter.addWidget(self._table_panel())
            self.viewer = _BomViewerPane()
            self.viewer.selection_requested.connect(self._viewer_selection_requested)
            self.splitter.addWidget(self.viewer)
            self.splitter.setStretchFactor(0, 3)
            self.splitter.setStretchFactor(1, 2)
            root.addWidget(self.splitter, 1)
            self._restore_layout()

        def _header(self) -> QtWidgets.QWidget:
            frame = QtWidgets.QFrame()
            frame.setObjectName("productWorkspaceHeader")
            layout = QtWidgets.QHBoxLayout(frame)
            labels = QtWidgets.QVBoxLayout()
            title = QtWidgets.QLabel("BOM / Hoeveelheden · productiehub")
            title.setObjectName("workspaceTitle")
            subtitle = QtWidgets.QLabel(
                "Canonieke BOM-snapshot · multiselectie · Viewer, machine, tekening, optimalisatie en scoped export"
            )
            subtitle.setObjectName("mutedText")
            labels.addWidget(title)
            labels.addWidget(subtitle)
            layout.addLayout(labels, 1)
            self.header_context = QtWidgets.QLabel("Geen project")
            self.header_context.setObjectName("contextChip")
            layout.addWidget(self.header_context)
            return frame

        def _command_bar(self) -> QtWidgets.QHBoxLayout:
            layout = QtWidgets.QHBoxLayout()
            self.scope = QtWidgets.QComboBox()
            self.scope.addItems(("Hele project", "Huidige selectie"))
            self.scope.currentIndexChanged.connect(self.refresh)
            self.group_by = QtWidgets.QComboBox()
            self.group_by.addItems(("Niet groeperen", "Merk", "Profiel", "Materiaal", "Machine", "Status"))
            self.group_by.currentIndexChanged.connect(self.refresh)
            self.status_filter = QtWidgets.QComboBox()
            self.status_filter.addItems(("Alle statussen", "Gereed", "Review", "Geblokkeerd"))
            self.status_filter.currentIndexChanged.connect(self.refresh)
            self.search = QtWidgets.QLineEdit()
            self.search.setPlaceholderText("Zoek merk, profiel, materiaal, ID …")
            self.search.setClearButtonEnabled(True)
            self.search.textChanged.connect(self.refresh)
            columns = QtWidgets.QPushButton("Kolommen / layouts")
            columns.clicked.connect(self._show_columns_menu)
            export = QtWidgets.QPushButton("Export selectie / filter")
            export.setObjectName("primaryButton")
            export.clicked.connect(self._export_scope)
            layout.addWidget(self.scope)
            layout.addWidget(self.group_by)
            layout.addWidget(self.status_filter)
            layout.addWidget(self.search, 1)
            layout.addWidget(columns)
            layout.addWidget(export)
            viewer_menu = QtWidgets.QToolButton()
            viewer_menu.setText("Viewer-indeling")
            viewer_menu.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QtWidgets.QMenu(viewer_menu)
            menu.addAction("Viewer rechts", lambda: self._set_viewer_layout("right"))
            menu.addAction("Viewer onder", lambda: self._set_viewer_layout("bottom"))
            menu.addAction("Alleen BOM", lambda: self._set_viewer_layout("hidden"))
            menu.addAction("Viewer los venster", self._detach_viewer)
            if self._allow_detach:
                menu.addAction("BOM los venster", self._detach_bom)
            viewer_menu.setMenu(menu)
            layout.addWidget(viewer_menu)
            return layout

        def _action_bar(self) -> QtWidgets.QWidget:
            frame = QtWidgets.QFrame()
            frame.setObjectName("selectionContext")
            layout = QtWidgets.QHBoxLayout(frame)
            layout.setContentsMargins(7, 5, 7, 5)
            self.selection_label = QtWidgets.QLabel("Geen BOM-regels geselecteerd")
            self.selection_label.setObjectName("selectionName")
            layout.addWidget(self.selection_label)
            layout.addStretch(1)
            specs = (
                ("edit", "Bewerken", lambda: self.action_requested.emit("edit")),
                ("drawing", "Tekening", lambda: self.action_requested.emit("drawings")),
                ("machine", "Machine", self._assign_machine),
                ("optimize", "Optimaliseren", lambda: self.action_requested.emit("optimize")),
                ("isolate", "Isoleren", self._isolate_selection),
                ("release", "Vrijgeven", self._open_production_workflow),
            )
            self.action_buttons: dict[str, Any] = {}
            for key, label, callback in specs:
                button = QtWidgets.QPushButton(label)
                button.clicked.connect(callback)
                button.setEnabled(False)
                self.action_buttons[key] = button
                layout.addWidget(button)
            more = QtWidgets.QToolButton()
            more.setText("Meer")
            more.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            menu = QtWidgets.QMenu(more)
            self.more_actions: dict[str, Any] = {}
            self.more_actions["scribing"] = menu.addAction(
                "Scribing", lambda: self.action_requested.emit("scribing")
            )
            self.more_actions["validate"] = menu.addAction(
                "Controleren", lambda: self.action_requested.emit("validate")
            )
            self.more_actions["report"] = menu.addAction(
                "Rapportage", lambda: self.action_requested.emit("report")
            )
            self.more_actions["print"] = menu.addAction(
                "PDF / afdrukken", lambda: self.action_requested.emit("print")
            )
            menu.addSeparator()
            menu.addAction("Selecteer alle zichtbare regels", self._select_visible)
            menu.addAction("Wis selectie", self._clear_selection)
            menu.addSeparator()
            menu.addAction("Machine-indeling resetten", self._reset_machine)
            menu.addAction("Export selectie / filter", self._export_scope)
            more.setMenu(menu)
            layout.addWidget(more)
            return frame

        def _table_panel(self) -> QtWidgets.QWidget:
            panel = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(panel)
            layout.setContentsMargins(0, 0, 0, 0)
            cards = QtWidgets.QHBoxLayout()
            self.groups_card = QtWidgets.QLabel("Groepen\n0")
            self.entities_card = QtWidgets.QLabel("Occurrences\n0")
            self.weight_card = QtWidgets.QLabel("Gewicht\n0,0 kg")
            self.area_card = QtWidgets.QLabel("Oppervlakte\n0,0 m²")
            self.blocked_card = QtWidgets.QLabel("Geblokkeerd\n0")
            for card in (
                self.groups_card, self.entities_card, self.weight_card,
                self.area_card, self.blocked_card,
            ):
                card.setObjectName("summaryCard")
                cards.addWidget(card)
            cards.addStretch(1)
            layout.addLayout(cards)
            self.table = QtWidgets.QTableWidget(0, len(self.COLUMNS))
            self.table.setHorizontalHeaderLabels(self.COLUMNS)
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.setSortingEnabled(True)
            self.table.verticalHeader().setVisible(False)
            self.table.horizontalHeader().setSectionsMovable(True)
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.itemSelectionChanged.connect(self._table_selection_changed)
            self.table.itemDoubleClicked.connect(lambda _item: self._zoom_selection())
            self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self._show_table_menu)
            layout.addWidget(self.table, 1)
            self.detail = QtWidgets.QLabel("Selecteer een of meer regels voor eigenschappen, blockers en acties.")
            self.detail.setObjectName("mutedText")
            self.detail.setWordWrap(True)
            self.detail.setMinimumHeight(38)
            layout.addWidget(self.detail)
            self.status = QtWidgets.QLabel("Open een project om de canonieke BOM-snapshot te laden.")
            self.status.setObjectName("safetyStatus")
            layout.addWidget(self.status)
            return panel

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            changed = workspace is not self._workspace
            self._workspace = workspace
            self._selection = selection
            if changed:
                self._read_model = None
                self.refresh()
            else:
                self._select_context_rows()
            self.viewer.set_context(workspace, selection)
            for detached in tuple(self._detached_windows):
                pane = getattr(detached, "_cws_viewer_pane", None)
                if pane is not None:
                    pane.set_context(workspace, selection)
            if workspace is None:
                self.header_context.setText("Geen project")
            else:
                count = len(tuple(getattr(selection, "entity_ids", ()) or ()))
                self.header_context.setText(
                    f"{workspace.project.project_name} · {count} geselecteerd"
                )

        def _family(self) -> str:
            return str(self.family_tabs.tabData(self.family_tabs.currentIndex()) or "parts")

        def _scope(self) -> BOMScope:
            entity_ids: Iterable[str] = ()
            if self.scope.currentIndex() == 1:
                entity_ids = tuple(getattr(self._selection, "entity_ids", ()) or ())
            status = ("all", "ready", "review", "blocked")[self.status_filter.currentIndex()]
            return BOMScope.create(
                family=self._family(),
                entity_ids=entity_ids,
                query=self.search.text(),
                status=status,
            )

        def refresh(self) -> None:
            if not hasattr(self, "table"):
                return
            selected_groups = {row.group_id for row in self._selected_rows()}
            self._syncing = True
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            self._display_rows.clear()
            try:
                if self._workspace is None:
                    self._read_model = None
                    self._visible_rows = ()
                    self._update_summary(())
                    self.status.setText(
                        "Open een project om de canonieke BOM-snapshot te laden."
                    )
                    self._update_actions()
                    return
                self._read_model = BOMWorkspaceReadModel(
                    self._workspace.bom_snapshot,
                    self._workspace.project,
                )
                for index, family in enumerate(BOM_FAMILIES):
                    label = BOM_FAMILY_LABELS[family]
                    self.family_tabs.setTabText(
                        index,
                        f"{label} ({self._read_model.family_count(family)})",
                    )
                rows = self._read_model.rows(self._scope())
                self._visible_rows = rows
                groups = self._group_rows(rows)
                table_row = 0
                for group_label, group_rows in groups:
                    if group_label:
                        self.table.insertRow(table_row)
                        header_item = QtWidgets.QTableWidgetItem(
                            f"▾ {group_label} · {len(group_rows)} groepen"
                        )
                        font = header_item.font()
                        font.setBold(True)
                        header_item.setFont(font)
                        header_item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
                        self.table.setItem(table_row, 0, header_item)
                        self.table.setItem(table_row, 5, QtWidgets.QTableWidgetItem(_number(sum(row.quantity for row in group_rows), 0)))
                        self.table.setItem(table_row, 6, QtWidgets.QTableWidgetItem(_number(sum(row.total_mass_kg for row in group_rows))))
                        table_row += 1
                    for row in group_rows:
                        self.table.insertRow(table_row)
                        self._display_rows[table_row] = row
                        values = (
                            row.mark or row.group_id,
                            row.description or row.group_id,
                            row.profile or "-",
                            row.material or "-",
                            _number(row.length_mm, 0),
                            _number(row.quantity, 0),
                            _number(row.total_mass_kg),
                            _number(row.total_surface_m2, 2),
                            row.machine or "-",
                            row.document_status or "-",
                            "GEBLOKKEERD" if row.blocked else row.status.upper(),
                        )
                        for column, value in enumerate(values):
                            item = QtWidgets.QTableWidgetItem(str(value))
                            item.setData(QtCore.Qt.ItemDataRole.UserRole, row.group_id)
                            item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, list(row.entity_ids))
                            if row.blocked:
                                item.setToolTip("\n".join(row.blocking_reasons) or "Geblokkeerd")
                            self.table.setItem(table_row, column, item)
                        table_row += 1
                grouped = self.group_by.currentIndex() != 0
                self.table.setSortingEnabled(not grouped)
                self._update_summary(rows)
                self.status.setText(
                    f"Canonieke BOM {self._workspace.bom_snapshot.snapshot_sha256[:16]} · "
                    f"{len(rows)} zichtbare groepen · export gebruikt exact deze selectie/filter"
                )
                self._select_context_rows(preferred_groups=selected_groups)
            finally:
                self._syncing = False
            self._update_actions()

        def _group_rows(
            self, rows: tuple[BOMWorkspaceRow, ...]
        ) -> tuple[tuple[str, tuple[BOMWorkspaceRow, ...]], ...]:
            mode = self.group_by.currentText()
            if mode == "Niet groeperen":
                return (("", rows),)
            getter = {
                "Merk": lambda row: row.mark or "Zonder merk",
                "Profiel": lambda row: row.profile or "Zonder profiel",
                "Materiaal": lambda row: row.material or "Zonder materiaal",
                "Machine": lambda row: row.machine or "Geen machine",
                "Status": lambda row: "Geblokkeerd" if row.blocked else row.status,
            }[mode]
            grouped: dict[str, list[BOMWorkspaceRow]] = defaultdict(list)
            for row in rows:
                grouped[str(getter(row))].append(row)
            return tuple(
                (label, tuple(grouped[label])) for label in sorted(grouped, key=str.casefold)
            )

        def _selected_rows(self) -> tuple[BOMWorkspaceRow, ...]:
            rows = []
            for index in self.table.selectionModel().selectedRows() if self.table.selectionModel() else ():
                row = self._display_rows.get(index.row())
                if row is not None and row not in rows:
                    rows.append(row)
            return tuple(rows)

        def _select_context_rows(
            self, *, preferred_groups: set[str] | None = None
        ) -> None:
            if self._workspace is None or not self._display_rows:
                return
            selected_ids = set(tuple(getattr(self._selection, "entity_ids", ()) or ()))
            groups = preferred_groups or set()
            self._syncing = True
            try:
                self.table.clearSelection()
                flags = (
                    QtCore.QItemSelectionModel.SelectionFlag.Select
                    | QtCore.QItemSelectionModel.SelectionFlag.Rows
                )
                for table_row, row in self._display_rows.items():
                    if row.group_id in groups or selected_ids.intersection(row.entity_ids):
                        item = self.table.item(table_row, 0)
                        if item is not None:
                            self.table.selectionModel().select(
                                self.table.indexFromItem(item), flags
                            )
            finally:
                self._syncing = False
            self._update_actions()

        def _table_selection_changed(self) -> None:
            if self._syncing or self._workspace is None:
                return
            rows = self._selected_rows()
            entity_ids = tuple(dict.fromkeys(
                entity_id for row in rows for entity_id in row.entity_ids
            ))
            self.window.application_context.request_selection(
                entity_ids,
                primary_entity_id=(entity_ids[0] if entity_ids else None),
                origin="bom",
            )
            self._update_actions()

        def _viewer_selection_requested(self, entity_ids: Iterable[str]) -> None:
            if self._workspace is not None:
                self.window.application_context.request_selection(
                    tuple(entity_ids), origin="bom_viewer"
                )

        def _update_summary(self, rows: Iterable[BOMWorkspaceRow]) -> None:
            if self._read_model is None:
                summary = None
            else:
                summary = self._read_model.summary(rows)
            self.groups_card.setText(f"Groepen\n{summary.group_count if summary else 0}")
            self.entities_card.setText(f"Occurrences\n{summary.entity_count if summary else 0}")
            self.weight_card.setText(f"Gewicht\n{_number(summary.total_mass_kg if summary else 0)} kg")
            self.area_card.setText(f"Oppervlakte\n{_number(summary.total_surface_m2 if summary else 0, 2)} m²")
            self.blocked_card.setText(f"Geblokkeerd\n{summary.blocked_count if summary else 0}")

        def _update_actions(self) -> None:
            rows = self._selected_rows()
            for button in self.action_buttons.values():
                button.setEnabled(False)
            for action in self.more_actions.values():
                action.setEnabled(False)
            if self._read_model is None:
                actions = ()
                summary = None
            else:
                actions = self._read_model.actions(rows)
                summary = self._read_model.summary(rows)
            for action in actions:
                button = self.action_buttons.get(action.action)
                if button is not None:
                    button.setEnabled(action.enabled)
                    button.setToolTip("" if action.enabled else action.reason)
                menu_action = self.more_actions.get(action.action)
                if menu_action is not None:
                    menu_action.setEnabled(action.enabled)
                    menu_action.setToolTip("" if action.enabled else action.reason)
            if self._read_model is not None:
                for key in ("validate", "report"):
                    self.more_actions[key].setEnabled(True)
            if summary is None or not rows:
                self.selection_label.setText("Geen BOM-regels geselecteerd")
                self.detail.setText("Selecteer een of meer regels voor eigenschappen, blockers en acties.")
                return
            self.selection_label.setText(
                f"{summary.group_count} regels · {summary.entity_count} occurrences · "
                f"{_number(summary.quantity, 0)} stuks · {_number(summary.total_mass_kg)} kg"
            )
            blockers = tuple(dict.fromkeys(
                reason for row in rows for reason in row.blocking_reasons
            ))
            families = ", ".join(sorted({BOM_FAMILY_LABELS[row.family] for row in rows}))
            self.detail.setText(
                f"Families: {families}. "
                + ("Blockers: " + " | ".join(blockers[:4]) if blockers else "Geen blockers in de geselecteerde regels.")
            )

        def _select_visible(self) -> None:
            self._syncing = True
            try:
                self.table.clearSelection()
                flags = (
                    QtCore.QItemSelectionModel.SelectionFlag.Select
                    | QtCore.QItemSelectionModel.SelectionFlag.Rows
                )
                for table_row in self._display_rows:
                    item = self.table.item(table_row, 0)
                    if item is not None:
                        self.table.selectionModel().select(
                            self.table.indexFromItem(item), flags
                        )
            finally:
                self._syncing = False
            self._table_selection_changed()

        def _clear_selection(self) -> None:
            if self._workspace is not None:
                self.window.application_context.clear_selection(origin="bom")

        def _zoom_selection(self) -> None:
            self.viewer.fit_selection()

        def _isolate_selection(self) -> None:
            self.viewer.isolate_selection()
            project_page = getattr(self.window, "project_page", None)
            callback = getattr(project_page, "_isolate_selection", None)
            if callable(callback):
                callback(False)

        def _selected_part_ids(self) -> tuple[str, ...]:
            project = getattr(self._workspace, "project", None)
            if project is None:
                return ()
            return tuple(dict.fromkeys(
                entity_id
                for row in self._selected_rows()
                for entity_id in row.entity_ids
                if entity_id in project.parts
            ))

        def _open_production_workflow(self) -> None:
            if self._workspace is None or self._read_model is None:
                return
            part_ids = self._read_model.production_part_ids(self._selected_rows())
            if part_ids:
                self.window.application_context.request_selection(
                    part_ids,
                    primary_entity_id=part_ids[0],
                    origin="bom_production_scope",
                )
            self.action_requested.emit("production_workflow")

        def _assign_machine(self) -> None:
            if self._workspace is None:
                return
            part_ids = self._selected_part_ids()
            if not part_ids:
                return
            project = self._workspace.project
            machines = sorted({
                str(profile.machine_id)
                for profile in project.machine_profiles.values()
                if str(profile.machine_id)
            } | {
                str(operation.machine_id)
                for operation in project.production_operations.values()
                if str(operation.machine_id)
            })
            if not machines:
                QtWidgets.QMessageBox.information(
                    self,
                    "Machine-indeling",
                    "Configureer eerst minimaal één machine in Machine-instellingen.",
                )
                self.action_requested.emit("settings")
                return
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"Machine toewijzen · {len(part_ids)} onderdelen")
            form = QtWidgets.QFormLayout(dialog)
            mode = QtWidgets.QComboBox()
            mode.addItems(("Automatisch · bewezen capaciteit", "Handmatig"))
            machine = QtWidgets.QComboBox()
            machine.addItems(machines)
            reason = QtWidgets.QLineEdit()
            reason.setPlaceholderText("Verplichte reden voor handmatige keuze")
            lock = QtWidgets.QCheckBox("Handmatige keuze vergrendelen")
            lock.setChecked(True)
            form.addRow("Methode", mode)
            form.addRow("Machine", machine)
            form.addRow("Reden", reason)
            form.addRow("", lock)
            def update_mode(index: int) -> None:
                manual = index == 1
                machine.setEnabled(manual)
                reason.setEnabled(manual)
                lock.setEnabled(manual)
            mode.currentIndexChanged.connect(update_mode)
            update_mode(mode.currentIndex())
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
                | QtWidgets.QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            form.addRow(buttons)
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return
            try:
                service = MachineRoutingService()
                if mode.currentIndex() == 0:
                    assigned = service.assign_automatic(
                        project,
                        part_ids,
                        user="bom-operator",
                    )
                    blocked = sum(item.routing_status != "ready" for item in assigned)
                    message = (
                        f"{len(assigned) - blocked} onderdelen automatisch gerouteerd; "
                        f"{blocked} niet automatisch gerouteerd wegens capability-bewijs "
                        "of een handmatige vergrendeling."
                    )
                else:
                    service.assign(
                        project,
                        part_ids,
                        machine.currentText(),
                        user="bom-operator",
                        reason=reason.text(),
                        manual_lock=lock.isChecked(),
                    )
                    message = (
                        "Handmatige machinekeuze opgeslagen. Productievrijgave blijft "
                        "geblokkeerd tot capaciteit opnieuw is gevalideerd."
                    )
                session = getattr(self._workspace, "session", None)
                if session is not None and hasattr(session, "dirty"):
                    session.dirty = True
                self.refresh()
                QtWidgets.QMessageBox.information(
                    self,
                    "Machine-indeling",
                    message,
                )
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Machine-indeling geblokkeerd", str(exc))

        def _reset_machine(self) -> None:
            if self._workspace is None:
                return
            part_ids = self._selected_part_ids()
            if not part_ids:
                return
            reason, accepted = QtWidgets.QInputDialog.getText(
                self,
                "Machine-indeling resetten",
                "Reden:",
            )
            if not accepted:
                return
            try:
                MachineRoutingService().reset(
                    self._workspace.project,
                    part_ids,
                    user="bom-operator",
                    reason=reason,
                )
                session = getattr(self._workspace, "session", None)
                if session is not None and hasattr(session, "dirty"):
                    session.dirty = True
                self.refresh()
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Reset geblokkeerd", str(exc))

        def _export_scope(self) -> None:
            if self._workspace is None or self._read_model is None:
                return
            rows = self._selected_rows() or self._visible_rows
            if not rows:
                QtWidgets.QMessageBox.information(self, "BOM-export", "De huidige scope bevat geen regels.")
                return
            directory = QtWidgets.QFileDialog.getExistingDirectory(self, "BOM-uitvoermap")
            if not directory:
                return
            entity_ids = tuple(dict.fromkeys(
                entity_id for row in rows for entity_id in row.entity_ids
            ))
            group_ids = tuple(dict.fromkeys(row.group_id for row in rows))
            base_scope = self._scope()
            scope = BOMScope.create(
                family=base_scope.family,
                entity_ids=entity_ids,
                group_ids=group_ids,
                query=base_scope.query,
                status=base_scope.status,
            )
            snapshot = scoped_bom_snapshot(
                self._workspace.bom_snapshot,
                entity_ids=entity_ids,
                group_ids=group_ids,
                scope=scope,
                project=self._workspace.project,
            )
            stem = re.sub(r"[^A-Za-z0-9._-]+", "_", snapshot.project_name).strip("_") or "CWS_BOM"
            outputs = export_bom_package(
                snapshot,
                Path(directory),
                package_name=f"{stem}_{base_scope.family}_scope",
            )
            QtWidgets.QMessageBox.information(
                self,
                "BOM-export",
                f"{len(outputs)} bestanden gemaakt voor {len(rows)} BOM-regels in:\n{directory}",
            )

        def _show_table_menu(self, position: QtCore.QPoint) -> None:
            item = self.table.itemAt(position)
            row = self._display_rows.get(item.row()) if item is not None else None
            if row is None:
                return
            if not self.table.selectionModel().isRowSelected(item.row(), QtCore.QModelIndex()):
                self.table.selectRow(item.row())
            menu = QtWidgets.QMenu(self)
            menu.addAction("Zoom naar selectie", self._zoom_selection)
            menu.addAction("Isoleren", self._isolate_selection)
            menu.addAction("Ghost context", self.viewer.ghost_selection)
            menu.addAction("Alles tonen", self.viewer.show_all)
            menu.addSeparator()
            menu.addAction("Bewerken", lambda: self.action_requested.emit("edit"))
            menu.addAction("Tekening", lambda: self.action_requested.emit("drawings"))
            menu.addAction("Machine toewijzen", self._assign_machine)
            menu.addAction("Optimaliseren", lambda: self.action_requested.emit("optimize"))
            menu.addAction("Scribing", lambda: self.action_requested.emit("scribing"))
            menu.addSeparator()
            menu.addAction("Export selectie", self._export_scope)
            menu.exec(self.table.viewport().mapToGlobal(position))

        def _show_columns_menu(self) -> None:
            menu = QtWidgets.QMenu(self)
            presets = menu.addMenu("Kolompresets")
            presets.addAction("Basis", lambda: self._apply_column_preset("basis"))
            presets.addAction("Productie", lambda: self._apply_column_preset("production"))
            presets.addAction("Controle", lambda: self._apply_column_preset("control"))
            presets.addAction("Alles", lambda: self._apply_column_preset("all"))
            menu.addSeparator()
            for index, label in enumerate(self.COLUMNS):
                action = menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(not self.table.isColumnHidden(index))
                action.toggled.connect(
                    lambda checked, column=index: self.table.setColumnHidden(column, not checked)
                )
            menu.addSeparator()
            menu.addAction("Kolommen passend", self.table.resizeColumnsToContents)
            menu.exec(QtGui.QCursor.pos())
            self._save_layout()

        def _apply_column_preset(self, name: str) -> None:
            visible = {
                "basis": {0, 1, 2, 3, 4, 5, 6, 10},
                "production": {0, 2, 3, 5, 6, 8, 9, 10},
                "control": set(range(len(self.COLUMNS))),
                "all": set(range(len(self.COLUMNS))),
            }[name]
            for column in range(len(self.COLUMNS)):
                self.table.setColumnHidden(column, column not in visible)
            self.table.resizeColumnsToContents()
            self._save_layout()

        def _set_viewer_layout(self, mode: str) -> None:
            if mode == "right":
                self.viewer.show()
                self.splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
                self.splitter.setSizes((900, 620))
            elif mode == "bottom":
                self.viewer.show()
                self.splitter.setOrientation(QtCore.Qt.Orientation.Vertical)
                self.splitter.setSizes((600, 360))
            elif mode == "hidden":
                self.viewer.hide()
            else:
                raise ValueError(mode)
            self._settings.setValue("bom/layout", mode)
            self.viewer.set_context(self._workspace, self._selection)

        def _detach_viewer(self) -> None:
            top = QtWidgets.QMainWindow(self.window)
            top.setWindowTitle("CWS BOM · gekoppelde Viewer")
            top.resize(1200, 800)
            pane = _BomViewerPane()
            pane.selection_requested.connect(self._viewer_selection_requested)
            top.setCentralWidget(pane)
            top._cws_viewer_pane = pane
            top.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
            self._detached_windows.append(top)
            top.destroyed.connect(lambda *_: self._forget_window(top))
            pane.set_context(self._workspace, self._selection)
            top.show()

        def _detach_bom(self) -> None:
            top = QtWidgets.QMainWindow(self.window)
            top.setWindowTitle("CWS Convertor · BOM / Hoeveelheden")
            top.resize(1600, 920)
            panel = BomWorkspacePanel(self.window, allow_detach=False)
            top.setCentralWidget(panel)
            top.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
            unsubscribe = self.window.application_context.subscribe(
                lambda snapshot: panel.set_context(
                    self.window.application_context.workspace,
                    snapshot.selection if snapshot.project_attached else None,
                )
            )
            top._cws_context_unsubscribe = unsubscribe
            self._detached_windows.append(top)
            top.destroyed.connect(lambda *_: (unsubscribe(), self._forget_window(top)))
            top.show()

        def _forget_window(self, window: Any) -> None:
            if window in self._detached_windows:
                self._detached_windows.remove(window)

        def _save_layout(self) -> None:
            self._settings.setValue("bom/splitter", self.splitter.saveState())
            self._settings.setValue("bom/header", self.table.horizontalHeader().saveState())

        def _restore_layout(self) -> None:
            mode = str(self._settings.value("bom/layout", "right") or "right")
            self._set_viewer_layout(mode if mode in {"right", "bottom", "hidden"} else "right")
            splitter = self._settings.value("bom/splitter")
            header = self._settings.value("bom/header")
            if splitter:
                self.splitter.restoreState(splitter)
            if header:
                self.table.horizontalHeader().restoreState(header)

        def handle_ribbon(self, command: str) -> None:
            if command == "columns":
                self._show_columns_menu()
            elif command == "filter":
                self.search.setFocus()
                self.search.selectAll()
            elif command == "group":
                self.group_by.showPopup()
            elif command == "sort":
                if self.group_by.currentIndex() == 0:
                    self.table.sortItems(0, QtCore.Qt.SortOrder.AscendingOrder)
            elif command == "reset":
                self.scope.setCurrentIndex(0)
                self.group_by.setCurrentIndex(0)
                self.status_filter.setCurrentIndex(0)
                self.search.clear()
                self._apply_column_preset("all")
            else:
                self.refresh()

        def closeEvent(self, event: Any) -> None:
            self._save_layout()
            for window in tuple(self._detached_windows):
                window.close()
            super().closeEvent(event)


else:
    class BomWorkspacePanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["BomWorkspacePanel"]
