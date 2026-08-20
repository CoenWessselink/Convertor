"""PySide6 professional virtual property grid for CWS Viewer V8.

The module is import-safe when PySide6 is unavailable.  Querying, filtering,
grouping, aggregation, layouts and exports live in renderer-neutral services;
the Qt layer only presents and dispatches stable canonical entity IDs.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

from cws_viewer.properties import (
    GridColumn,
    GridGroupNode,
    GridGroupSpec,
    GridLayout,
    GridLayoutIdentity,
    GridLayoutStore,
    GridQuery,
    GridQueryResult,
    GridScope,
    GridSort,
    GridViewerBridge,
    ProjectGridModel,
    export_grid_csv,
    export_grid_xlsx,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    ROLE_ENTITY_ID = int(QtCore.Qt.ItemDataRole.UserRole) + 1
    ROLE_NODE_ID = ROLE_ENTITY_ID + 1
    ROLE_ENTRY_KIND = ROLE_ENTITY_ID + 2
    ROLE_RAW_VALUE = ROLE_ENTITY_ID + 3

    class _DisplayEntry:
        __slots__ = ("kind", "row", "group")

        def __init__(self, *, kind: str, row: Any = None, group: GridGroupNode | None = None) -> None:
            self.kind = kind
            self.row = row
            self.group = group

    def _flatten_groups(result: GridQueryResult) -> list[_DisplayEntry]:
        if not result.groups:
            return [_DisplayEntry(kind="row", row=row) for row in result.iter_rows()]
        row_by_entity = {row.entity_id: row for row in result.iter_rows()}
        output: list[_DisplayEntry] = []

        def visit(group: GridGroupNode) -> None:
            output.append(_DisplayEntry(kind="group", group=group))
            if group.children:
                for child in group.children:
                    visit(child)
            else:
                for entity_id in group.entity_ids:
                    row = row_by_entity.get(entity_id)
                    if row is not None:
                        output.append(_DisplayEntry(kind="row", row=row))

        for item in result.groups:
            visit(item)
        return output

    class VirtualProjectTableModel(QtCore.QAbstractTableModel):  # type: ignore[misc]
        """QAbstractTableModel backed by a virtual GridQueryResult."""

        def __init__(self, grid_model: ProjectGridModel, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.grid_model = grid_model
            self.columns = tuple(column for column in grid_model.columns if column.visible)
            self.result = grid_model.execute(GridQuery())
            self.entries = _flatten_groups(self.result)

        def set_columns(self, columns: Iterable[GridColumn]) -> None:
            self.beginResetModel()
            self.columns = tuple(sorted((column for column in columns if column.visible), key=lambda item: (item.order, item.key)))
            self.endResetModel()

        def set_result(self, result: GridQueryResult) -> None:
            self.beginResetModel()
            self.result = result
            self.entries = _flatten_groups(result)
            self.endResetModel()

        def rowCount(self, parent: Any = QtCore.QModelIndex()) -> int:  # noqa: N802
            return 0 if parent.isValid() else len(self.entries)

        def columnCount(self, parent: Any = QtCore.QModelIndex()) -> int:  # noqa: N802
            return 0 if parent.isValid() else len(self.columns)

        def headerData(self, section: int, orientation: Any, role: int = int(QtCore.Qt.ItemDataRole.DisplayRole)) -> Any:  # noqa: N802
            if role != int(QtCore.Qt.ItemDataRole.DisplayRole):
                return None
            if orientation == QtCore.Qt.Orientation.Horizontal and 0 <= section < len(self.columns):
                return self.columns[section].label
            if orientation == QtCore.Qt.Orientation.Vertical:
                return section + 1
            return None

        @staticmethod
        def _status_brush(value: str) -> Any | None:
            token = value.casefold()
            colours = {
                "validated": "#D9EAD3",
                "released": "#CDEBD8",
                "unchanged": "#E7EEF4",
                "moved": "#D9EAF7",
                "changed": "#FCE5CD",
                "added": "#D9EAD3",
                "removed": "#F4CCCC",
                "blocked": "#F4CCCC",
                "review_required": "#FFF2CC",
                "unclassified": "#FFF2CC",
                "ambiguous": "#EADCF8",
            }
            for key, colour in colours.items():
                if key in token:
                    return QtGui.QBrush(QtGui.QColor(colour))
            return None

        def data(self, index: Any, role: int = int(QtCore.Qt.ItemDataRole.DisplayRole)) -> Any:
            if not index.isValid() or not (0 <= index.row() < len(self.entries)):
                return None
            entry = self.entries[index.row()]
            if entry.kind == "group":
                group = entry.group
                if role == int(QtCore.Qt.ItemDataRole.DisplayRole):
                    if index.column() == 0:
                        indent = "    " * int(group.level)
                        return f"{indent}{group.value or '(leeg)'}  ({group.row_count:,})"
                    return ""
                if role == int(QtCore.Qt.ItemDataRole.FontRole):
                    font = QtGui.QFont()
                    font.setBold(True)
                    return font
                if role == int(QtCore.Qt.ItemDataRole.BackgroundRole):
                    return QtGui.QBrush(QtGui.QColor("#24384B" if group.level == 0 else "#1D2E3E"))
                if role == int(QtCore.Qt.ItemDataRole.ForegroundRole):
                    return QtGui.QBrush(QtGui.QColor("#FFFFFF"))
                if role == ROLE_ENTRY_KIND:
                    return "group"
                return None

            row = entry.row
            column = self.columns[index.column()]
            raw = row.get(column.key)
            if role == int(QtCore.Qt.ItemDataRole.DisplayRole):
                if isinstance(raw, bool):
                    return "Ja" if raw else "Nee"
                if isinstance(raw, float):
                    return f"{raw:,.3f}" if column.data_type.value == "number" else str(raw)
                return "" if raw is None else str(raw)
            if role == int(QtCore.Qt.ItemDataRole.TextAlignmentRole) and column.data_type.value in {"integer", "number"}:
                return int(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            if role == int(QtCore.Qt.ItemDataRole.BackgroundRole) and column.data_type.value == "status":
                return self._status_brush(str(raw or ""))
            if role == int(QtCore.Qt.ItemDataRole.ToolTipRole):
                unit = f" {column.unit}" if column.unit else ""
                return f"{column.label}: {raw}{unit}\nEntity: {row.entity_id}"
            if role == ROLE_ENTITY_ID:
                return row.entity_id
            if role == ROLE_NODE_ID:
                return row.node_id
            if role == ROLE_ENTRY_KIND:
                return "row"
            if role == ROLE_RAW_VALUE:
                return raw
            return None

        def flags(self, index: Any) -> Any:
            if not index.isValid():
                return QtCore.Qt.ItemFlag.NoItemFlags
            entry = self.entries[index.row()]
            if entry.kind == "group":
                return QtCore.Qt.ItemFlag.ItemIsEnabled
            return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable

        def entity_id_at(self, row_index: int) -> str | None:
            if not 0 <= row_index < len(self.entries):
                return None
            entry = self.entries[row_index]
            return None if entry.kind != "row" else str(entry.row.entity_id)

    class FieldChooserDialog(QtWidgets.QDialog):  # type: ignore[misc]
        def __init__(self, columns: Iterable[GridColumn], parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setWindowTitle("Velden kiezen en ordenen")
            self.resize(460, 620)
            layout = QtWidgets.QVBoxLayout(self)
            self.list = QtWidgets.QListWidget()
            self.list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
            self.list.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
            self.list.setAccessibleName("Beschikbare projecteigenschappen")
            for column in sorted(columns, key=lambda item: (item.order, item.key)):
                item = QtWidgets.QListWidgetItem(column.label)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, column)
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
                item.setCheckState(QtCore.Qt.CheckState.Checked if column.visible else QtCore.Qt.CheckState.Unchecked)
                self.list.addItem(item)
            layout.addWidget(self.list)
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

        def selected_columns(self) -> tuple[GridColumn, ...]:
            result = []
            for order in range(self.list.count()):
                item = self.list.item(order)
                base = item.data(QtCore.Qt.ItemDataRole.UserRole)
                result.append(
                    replace(
                        base,
                        visible=item.checkState() == QtCore.Qt.CheckState.Checked,
                        order=order,
                    )
                )
            return tuple(result)

    class ProfessionalPropertyGridPanel(QtWidgets.QWidget):  # type: ignore[misc]
        """High-density V8 project grid with stable-ID viewer integration."""

        entities_selected = QtCore.Signal(tuple)
        open_part_workbench_requested = QtCore.Signal(str)
        application_action_requested = QtCore.Signal(str)
        colorize_requested = QtCore.Signal(str)
        query_changed = QtCore.Signal(dict)

        def __init__(
            self,
            grid_model: ProjectGridModel,
            *,
            bridge: GridViewerBridge | None = None,
            layout_store: GridLayoutStore | None = None,
            layout_identity: GridLayoutIdentity | None = None,
            parent: Any | None = None,
        ) -> None:
            super().__init__(parent)
            self.grid_model = grid_model
            self.bridge = bridge
            self.layout_store = layout_store
            self.layout_identity = layout_identity or GridLayoutIdentity()
            self.current_query = GridQuery()
            self._sorts: tuple[GridSort, ...] = (GridSort("part_position"),)
            self._groups: tuple[GridGroupSpec, ...] = ()
            self._syncing_selection = False
            self.setObjectName("cwsV8ProfessionalPropertyGrid")
            self.setAccessibleName("CWS projecteigenschappen")
            self._build_ui()
            self.refresh()

        def _build_ui(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(4)

            toolbar = QtWidgets.QHBoxLayout()
            self.search = QtWidgets.QLineEdit()
            self.search.setPlaceholderText("Zoek merk, positie, profiel, materiaal, ID …")
            self.search.setClearButtonEnabled(True)
            self.search.setAccessibleName("Projectgrid zoeken")
            self.scope = QtWidgets.QComboBox()
            for label, value in (
                ("Alles", GridScope.ALL.value),
                ("Zichtbaar", GridScope.VISIBLE.value),
                ("Geselecteerd", GridScope.SELECTED.value),
                ("Gewijzigd", GridScope.CHANGED.value),
                ("Geblokkeerd", GridScope.BLOCKED.value),
            ):
                self.scope.addItem(label, value)
            self.group = QtWidgets.QComboBox()
            self.group.addItem("Niet groeperen", "")
            for column in self.grid_model.columns:
                if column.groupable:
                    self.group.addItem(column.label, column.key)
            self.colour = QtWidgets.QComboBox()
            self.colour.addItem("Geen 3D-kleur", "")
            for key in ("revision_status", "material", "profile", "classification_status", "export_status", "assembly_mark"):
                column = next((item for item in self.grid_model.columns if item.key == key), None)
                if column is not None:
                    self.colour.addItem(column.label, key)
            self.fields_button = QtWidgets.QPushButton("Velden")
            self.save_layout_button = QtWidgets.QPushButton("Layout opslaan")
            self.load_layout_button = QtWidgets.QPushButton("Layout laden")
            self.export_button = QtWidgets.QPushButton("Export")
            self.summary = QtWidgets.QLabel()
            self.summary.setAccessibleName("Grid samenvatting")

            toolbar.addWidget(self.search, 2)
            toolbar.addWidget(self.scope)
            toolbar.addWidget(self.group)
            toolbar.addWidget(self.colour)
            toolbar.addWidget(self.fields_button)
            toolbar.addWidget(self.save_layout_button)
            toolbar.addWidget(self.load_layout_button)
            toolbar.addWidget(self.export_button)
            toolbar.addStretch(1)
            toolbar.addWidget(self.summary)
            root.addLayout(toolbar)

            self.model = VirtualProjectTableModel(self.grid_model, self)
            self.table = QtWidgets.QTableView()
            self.table.setModel(self.model)
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            self.table.setAlternatingRowColors(True)
            self.table.setSortingEnabled(False)
            self.table.setWordWrap(False)
            self.table.setUniformRowHeights(True) if hasattr(self.table, "setUniformRowHeights") else None
            self.table.verticalHeader().setDefaultSectionSize(24)
            self.table.verticalHeader().setVisible(False)
            self.table.horizontalHeader().setSectionsMovable(True)
            self.table.horizontalHeader().setStretchLastSection(False)
            self.table.horizontalHeader().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.table.horizontalHeader().customContextMenuRequested.connect(self._header_menu)
            self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self._table_menu)
            self.table.setAccessibleName("Virtuele projectgrid")
            root.addWidget(self.table, 1)

            self.footer = QtWidgets.QLabel()
            self.footer.setAccessibleName("Projectgrid totalen")
            root.addWidget(self.footer)

            self.search.textChanged.connect(self.refresh)
            self.scope.currentIndexChanged.connect(self.refresh)
            self.group.currentIndexChanged.connect(self._group_changed)
            self.colour.currentIndexChanged.connect(self._colour_changed)
            self.fields_button.clicked.connect(self._choose_fields)
            self.save_layout_button.clicked.connect(self._save_layout)
            self.load_layout_button.clicked.connect(self._load_layout)
            self.export_button.clicked.connect(self._export_menu)
            self.table.selectionModel().selectionChanged.connect(self._selection_changed)
            self.table.doubleClicked.connect(self._double_clicked)
            self.table.horizontalHeader().sectionClicked.connect(self._section_clicked)

            find_action = QtGui.QAction(self)
            find_action.setShortcut(QtGui.QKeySequence.StandardKey.Find)
            find_action.triggered.connect(self.search.setFocus)
            self.addAction(find_action)

        def _build_query(self) -> GridQuery:
            group_key = str(self.group.currentData() or "")
            groups = (GridGroupSpec(group_key),) if group_key else self._groups
            return GridQuery(
                text=self.search.text(),
                sorts=self._sorts,
                groups=groups,
                scope=GridScope(str(self.scope.currentData() or GridScope.ALL.value)),
            )

        def refresh(self) -> None:
            if self.bridge is not None:
                self.bridge.refresh_scope_state()
            self.current_query = self._build_query()
            result = self.grid_model.execute(self.current_query)
            self.model.set_columns(self.grid_model.columns)
            self.model.set_result(result)
            for logical, column in enumerate(self.model.columns):
                self.table.setColumnWidth(logical, column.width)
            self.summary.setText(f"{result.row_count:,} regels · {result.elapsed_ms:.1f} ms")
            totals = []
            for aggregate in result.footer.aggregates:
                if aggregate.value is not None:
                    label = next((item.label for item in self.grid_model.columns if item.key == aggregate.key), aggregate.key)
                    totals.append(f"{label}: {aggregate.value:,.3f}")
            self.footer.setText("  |  ".join(totals[:6]))
            self.query_changed.emit(result.to_summary_dict())

        def _selection_changed(self, *_args: Any) -> None:
            if self._syncing_selection:
                return
            entity_ids = []
            for index in self.table.selectionModel().selectedRows():
                entity_id = self.model.entity_id_at(index.row())
                if entity_id:
                    entity_ids.append(entity_id)
            values = tuple(dict.fromkeys(entity_ids))
            self.entities_selected.emit(values)
            if self.bridge is not None:
                self.bridge.select_entities(values)

        def select_entities(self, entity_ids: Iterable[str]) -> None:
            wanted = set(map(str, entity_ids))
            selection = QtCore.QItemSelection()
            first_match = None
            for row_index in range(self.model.rowCount()):
                entity_id = self.model.entity_id_at(row_index)
                if entity_id in wanted:
                    left = self.model.index(row_index, 0)
                    right = self.model.index(row_index, max(0, self.model.columnCount() - 1))
                    selection.select(left, right)
                    if first_match is None:
                        first_match = left
            self._syncing_selection = True
            try:
                self.table.selectionModel().select(
                    selection,
                    QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect | QtCore.QItemSelectionModel.SelectionFlag.Rows,
                )
                if first_match is not None:
                    self.table.scrollTo(
                        first_match,
                        QtWidgets.QAbstractItemView.ScrollHint.EnsureVisible,
                    )
            finally:
                self._syncing_selection = False

        def _double_clicked(self, index: Any) -> None:
            entity_id = self.model.entity_id_at(index.row())
            if entity_id:
                self.open_part_workbench_requested.emit(entity_id)

        def _section_clicked(self, logical: int) -> None:
            if not 0 <= logical < len(self.model.columns):
                return
            key = self.model.columns[logical].key
            current = next((item for item in self._sorts if item.key == key), None)
            descending = False if current is None else not current.descending
            self._sorts = (GridSort(key, descending),)
            self.refresh()

        def _group_changed(self, _index: int) -> None:
            self.refresh()

        def _colour_changed(self, _index: int) -> None:
            key = str(self.colour.currentData() or "")
            self.colorize_requested.emit(key)
            if self.bridge is None:
                return
            if key:
                self.bridge.colourize(self.model.result, key)
            else:
                self.bridge.clear_colours()

        def _choose_fields(self) -> None:
            dialog = FieldChooserDialog(self.grid_model.columns, self)
            if dialog.exec() == int(QtWidgets.QDialog.DialogCode.Accepted):
                self.grid_model.set_columns(dialog.selected_columns())
                self.refresh()

        def current_layout(self, name: str | None = None) -> GridLayout:
            # Read actual visual order/width from the movable Qt header.
            header = self.table.horizontalHeader()
            visible_columns = list(self.model.columns)
            visual_order = sorted(range(len(visible_columns)), key=header.visualIndex)
            updated: list[GridColumn] = []
            seen: set[str] = set()
            for order, logical in enumerate(visual_order):
                base = visible_columns[logical]
                updated.append(replace(base, width=header.sectionSize(logical), visible=True, order=order))
                seen.add(base.key)
            for base in self.grid_model.columns:
                if base.key not in seen:
                    updated.append(replace(base, visible=False, order=len(updated)))
            return GridLayout(
                name=name or self.layout_identity.layout_name,
                columns=tuple(updated),
                sorts=self._sorts,
                groups=(GridGroupSpec(str(self.group.currentData())),) if self.group.currentData() else (),
                scope=GridScope(str(self.scope.currentData() or GridScope.ALL.value)),
                row_height=self.table.verticalHeader().defaultSectionSize(),
                alternating_rows=self.table.alternatingRowColors(),
            )

        def apply_layout(self, layout: GridLayout) -> None:
            self.grid_model.apply_layout(layout)
            self._sorts = layout.sorts or (GridSort("part_position"),)
            self._groups = layout.groups
            scope_index = self.scope.findData(layout.scope.value)
            if scope_index >= 0:
                self.scope.setCurrentIndex(scope_index)
            group_key = layout.groups[0].key if layout.groups else ""
            group_index = self.group.findData(group_key)
            if group_index >= 0:
                self.group.setCurrentIndex(group_index)
            self.table.verticalHeader().setDefaultSectionSize(layout.row_height)
            self.table.setAlternatingRowColors(layout.alternating_rows)
            self.refresh()

        def _save_layout(self) -> None:
            if self.layout_store is None:
                return
            name, ok = QtWidgets.QInputDialog.getText(self, "Layout opslaan", "Naam:", text=self.layout_identity.layout_name)
            if not ok or not name.strip():
                return
            identity = replace(self.layout_identity, layout_name=name.strip())
            self.layout_store.save(identity, self.current_layout(name.strip()))
            self.layout_identity = identity

        def _load_layout(self) -> None:
            if self.layout_store is None:
                return
            identities = self.layout_store.list_layouts(
                company_id=self.layout_identity.company_id,
                user_id=self.layout_identity.user_id,
                project_id=self.layout_identity.project_id,
            )
            if not identities:
                return
            names = [item.layout_name for item in identities]
            name, ok = QtWidgets.QInputDialog.getItem(self, "Layout laden", "Layout:", names, editable=False)
            if ok:
                identity = next(item for item in identities if item.layout_name == name)
                stored = self.layout_store.load(identity)
                self.layout_identity = identity
                self.apply_layout(stored.layout)

        def _export_menu(self) -> None:
            menu = QtWidgets.QMenu(self)
            menu.addAction("CSV exporteren", lambda: self._export("csv"))
            menu.addAction("Excel exporteren", lambda: self._export("xlsx"))
            menu.exec(QtGui.QCursor.pos())

        def _export(self, kind: str) -> None:
            extension = ".csv" if kind == "csv" else ".xlsx"
            path, _selected_filter = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Projectgrid exporteren",
                f"CWS_Projectgrid{extension}",
                "CSV (*.csv)" if kind == "csv" else "Excel (*.xlsx)",
            )
            if not path:
                return
            if kind == "csv":
                export_grid_csv(self.model.result, Path(path), columns=self.grid_model.columns)
            else:
                export_grid_xlsx(self.model.result, Path(path), columns=self.grid_model.columns)

        def _header_menu(self, position: Any) -> None:
            logical = self.table.horizontalHeader().logicalIndexAt(position)
            if logical < 0 or logical >= len(self.model.columns):
                return
            column = self.model.columns[logical]
            menu = QtWidgets.QMenu(self)
            menu.addAction("Oplopend sorteren", lambda: self._set_sort(column.key, False))
            menu.addAction("Aflopend sorteren", lambda: self._set_sort(column.key, True))
            if column.groupable:
                menu.addAction("Groeperen op dit veld", lambda: self._set_group(column.key))
            menu.addSeparator()
            menu.addAction("Kolom verbergen", lambda: self._hide_column(column.key))
            menu.addAction("Optimale kolombreedte", lambda: self.table.resizeColumnToContents(logical))
            menu.addAction("Velden kiezen", self._choose_fields)
            menu.exec(self.table.horizontalHeader().mapToGlobal(position))

        def _table_menu(self, position: Any) -> None:
            menu = QtWidgets.QMenu(self)
            menu.addAction("Open in Part Workbench", self._open_current)
            menu.addAction("Selecteer in 3D", self._selection_changed)
            menu.addAction("Isoleer resultaat", self._isolate_result)
            menu.addAction("Ghost resultaat", lambda: self._isolate_result(True))
            menu.addSeparator()
            for label, key in (
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
                menu.addAction(label, lambda _checked=False, value=key: self.application_action_requested.emit(value))
            menu.addSeparator()
            menu.addAction("CSV exporteren", lambda: self._export("csv"))
            menu.addAction("Excel exporteren", lambda: self._export("xlsx"))
            menu.exec(self.table.viewport().mapToGlobal(position))

        def _set_sort(self, key: str, descending: bool) -> None:
            self._sorts = (GridSort(key, descending),)
            self.refresh()

        def _set_group(self, key: str) -> None:
            index = self.group.findData(key)
            if index >= 0:
                self.group.setCurrentIndex(index)

        def _hide_column(self, key: str) -> None:
            self.grid_model.set_columns(
                replace(item, visible=False) if item.key == key else item
                for item in self.grid_model.columns
            )
            self.refresh()

        def _open_current(self) -> None:
            rows = self.table.selectionModel().selectedRows()
            if rows:
                entity_id = self.model.entity_id_at(rows[0].row())
                if entity_id:
                    self.open_part_workbench_requested.emit(entity_id)

        def _isolate_result(self, ghost: bool = False) -> None:
            if self.bridge is not None:
                self.bridge.isolate_result(self.model.result, ghost_context=ghost)

else:
    class VirtualProjectTableModel:  # pragma: no cover - headless import facade
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PySide6 is niet beschikbaar")

    class FieldChooserDialog:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PySide6 is niet beschikbaar")

    class ProfessionalPropertyGridPanel:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PySide6 is niet beschikbaar")


__all__ = [
    "FieldChooserDialog",
    "ProfessionalPropertyGridPanel",
    "VirtualProjectTableModel",
]
