"""Part-first Qt workspaces over one unified CWS application context.

These panels are presentation and orchestration surfaces only. They never
open source CAD files or create a second project model. Every selection is
published through ``UnifiedApplicationContext`` and every manufacturing action
uses the existing fail-closed services.
"""
from __future__ import annotations

from typing import Any

from cws_convertor.integration.production_workflow import build_production_workflow_snapshot
from cws_convertor.project.unified_schema import m18_store_snapshot
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


def _text(value: Any, fallback: str = "-") -> str:
    result = str(value or "").strip()
    return result or fallback


def _number(value: Any, decimals: int = 1) -> str:
    try:
        number = float(value or 0.0)
    except (TypeError, ValueError):
        return "-"
    return f"{number:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _selection_ids(selection: Any | None) -> tuple[str, ...]:
    return tuple(str(value) for value in (getattr(selection, "entity_ids", ()) or ()) if str(value))


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class _WorkspaceHeader(QtWidgets.QFrame):
        def __init__(self, title: str, subtitle: str, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("productWorkspaceHeader")
            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(12, 9, 12, 9)
            labels = QtWidgets.QVBoxLayout()
            labels.setSpacing(1)
            heading = QtWidgets.QLabel(title)
            heading.setObjectName("workspaceTitle")
            detail = QtWidgets.QLabel(subtitle)
            detail.setObjectName("mutedText")
            detail.setWordWrap(True)
            labels.addWidget(heading)
            labels.addWidget(detail)
            layout.addLayout(labels, 1)
            self.context = QtWidgets.QLabel("Geen project geopend")
            self.context.setObjectName("contextChip")
            layout.addWidget(self.context)

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            if workspace is None:
                self.context.setText("Geen project")
                return
            primary = str(getattr(selection, "primary_entity_id", "") or "")
            count = len(_selection_ids(selection))
            if primary:
                self.context.setText(f"{primary} | {count} geselecteerd")
            else:
                self.context.setText(f"{workspace.project.project_name} | projectscope")


    class BomWorkspacePanel(QtWidgets.QWidget):
        """Filterable BOM with bidirectional canonical selection sync."""

        action_requested = QtCore.Signal(str)
        show_project_requested = QtCore.Signal()
        COLUMNS = (
            "Merk", "Part ID", "Profiel", "Materiaal", "Lengte (mm)",
            "Aantal", "Gewicht (kg)", "Fase", "Status",
        )

        def __init__(self, window: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.window = window
            self._workspace: Any | None = None
            self._selection: Any | None = None
            self._last_snapshot: Any | None = None
            self._syncing = False
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(7)
            self.header = _WorkspaceHeader(
                "BOM / Hoeveelheden",
                "Klik een regel om hetzelfde onderdeel in Viewer, Properties en alle werkruimten te selecteren.",
            )
            root.addWidget(self.header)

            ribbon = QtWidgets.QHBoxLayout()
            export = QtWidgets.QPushButton("Excel / BOM export")
            export.setObjectName("primaryButton")
            export.clicked.connect(window.project_page.export_bom)
            columns = QtWidgets.QPushButton("Kolommen")
            columns.clicked.connect(self._resize_columns)
            self.scope = QtWidgets.QComboBox()
            self.scope.addItems(("Project BOM", "Huidige selectie"))
            self.scope.currentIndexChanged.connect(self.refresh)
            self.group_by = QtWidgets.QComboBox()
            self.group_by.addItems(("Niet groeperen", "Merk", "Profiel", "Materiaal", "Fase", "Status"))
            self.group_by.currentTextChanged.connect(self._group_changed)
            self.status_filter = QtWidgets.QComboBox()
            self.status_filter.addItems(("Alle statussen", "OK / gereed", "Review / fout"))
            self.status_filter.currentIndexChanged.connect(self._apply_filter)
            self.search = QtWidgets.QLineEdit()
            self.search.setPlaceholderText("Zoek in BOM")
            self.search.setClearButtonEnabled(True)
            self.search.textChanged.connect(self._apply_filter)
            viewer = QtWidgets.QPushButton("Terug naar Viewer")
            viewer.clicked.connect(lambda: self.action_requested.emit("viewer"))
            ribbon.addWidget(export)
            ribbon.addWidget(columns)
            ribbon.addWidget(self.scope)
            ribbon.addWidget(self.group_by)
            ribbon.addWidget(self.status_filter)
            ribbon.addStretch(1)
            ribbon.addWidget(self.search)
            ribbon.addWidget(viewer)
            root.addLayout(ribbon)

            cards = QtWidgets.QHBoxLayout()
            self.parts_card = QtWidgets.QLabel("Onderdelen\n0")
            self.assemblies_card = QtWidgets.QLabel("Assemblies\n0")
            self.weight_card = QtWidgets.QLabel("Totaal gewicht\n0,0 kg")
            self.profiles_card = QtWidgets.QLabel("Profielen\n0")
            self.review_card = QtWidgets.QLabel("Review\n0")
            for card in (self.parts_card, self.assemblies_card, self.weight_card, self.profiles_card, self.review_card):
                card.setObjectName("summaryCard")
                cards.addWidget(card)
            cards.addStretch(1)
            root.addLayout(cards)

            self.table = QtWidgets.QTableWidget(0, len(self.COLUMNS))
            self.table.setHorizontalHeaderLabels(self.COLUMNS)
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.setSortingEnabled(True)
            self.table.verticalHeader().setVisible(False)
            self.table.itemSelectionChanged.connect(self._table_selection_changed)
            self.table.itemDoubleClicked.connect(lambda _item: self.action_requested.emit("viewer"))
            self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self._show_table_menu)
            self.table.horizontalHeader().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.table.horizontalHeader().customContextMenuRequested.connect(self._show_header_menu)
            root.addWidget(self.table, 1)
            self.status = QtWidgets.QLabel("Open een project om de canonieke BOM te laden.")
            self.status.setObjectName("mutedText")
            root.addWidget(self.status)

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            changed = workspace is not self._workspace
            self._workspace = workspace
            self._selection = selection
            self.header.set_context(workspace, selection)
            if changed:
                self.refresh()
            self._select_context_rows()

        def refresh(self) -> None:
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            if self._workspace is None:
                self.table.setSortingEnabled(True)
                return
            project = self._workspace.project
            selected = set(_selection_ids(self._selection))
            selection_scope = self.scope.currentIndex() == 1 and bool(selected)
            profiles: set[str] = set()
            marks: set[str] = set()
            total_weight = 0.0
            reviews = 0
            rows = []
            for entity_id, part in sorted(project.parts.items()):
                if selection_scope and str(entity_id) not in selected:
                    continue
                source = getattr(part, "source_identity", None)
                part_id = _text(getattr(part, "part_position", "") or getattr(source, "part_position", "") or entity_id)
                mark = _text(getattr(part, "assembly_mark", "") or getattr(source, "assembly_mark", ""))
                profile = _text(getattr(part, "normalized_profile", "") or getattr(part, "profile", ""))
                material = _text(getattr(part, "normalized_material", "") or getattr(part, "material", ""))
                length = float(getattr(part, "length_mm", 0.0) or 0.0)
                quantity = int(getattr(part, "quantity_total", 1) or 1)
                weight = float(getattr(part, "mass_each_kg", 0.0) or 0.0)
                phase = _text(getattr(part, "phase", "") or getattr(project, "project_phase", ""))
                status = _text(getattr(part, "status", ""), "review")
                profiles.add(profile)
                if mark != "-":
                    marks.add(mark)
                total_weight += weight * quantity
                reviews += int(status.lower() not in {"ok", "ready", "validated", "released"})
                rows.append((entity_id, mark, part_id, profile, material, length, quantity, weight, phase, status))
            self.table.setRowCount(len(rows))
            for row, values in enumerate(rows):
                entity_id, mark, part_id, profile, material, length, quantity, weight, phase, status = values
                display = (mark, part_id, profile, material, _number(length, 0), str(quantity), _number(weight), phase, status)
                for column, value in enumerate(display):
                    item = QtWidgets.QTableWidgetItem(str(value))
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, str(entity_id))
                    self.table.setItem(row, column, item)
            self.table.setSortingEnabled(True)
            self.parts_card.setText(f"Onderdelen\n{len(rows):,}".replace(",", "."))
            self.assemblies_card.setText(f"Assemblies\n{len(marks)}")
            self.weight_card.setText(f"Totaal gewicht\n{_number(total_weight)} kg")
            self.profiles_card.setText(f"Profielen\n{len(profiles)}")
            self.review_card.setText(f"Review\n{reviews}")
            self.status.setText(f"{len(rows)} onderdelen uit hetzelfde Canonical Project Model")
            self._apply_filter()
            self._select_context_rows()

        def _resize_columns(self) -> None:
            self.table.resizeColumnsToContents()
            self.table.horizontalHeader().setStretchLastSection(True)

        def _apply_filter(self) -> None:
            needle = self.search.text().strip().casefold()
            status_mode = self.status_filter.currentIndex()
            for row in range(self.table.rowCount()):
                row_text = " ".join(
                    self.table.item(row, column).text()
                    for column in range(self.table.columnCount())
                    if self.table.item(row, column) is not None
                ).casefold()
                status_item = self.table.item(row, 8)
                status = status_item.text().strip().casefold() if status_item is not None else ""
                ready = status in {"ok", "ready", "validated", "released", "gereed"}
                status_hidden = (status_mode == 1 and not ready) or (status_mode == 2 and ready)
                self.table.setRowHidden(row, bool((needle and needle not in row_text) or status_hidden))

        def _group_changed(self, label: str) -> None:
            columns = {"Merk": 0, "Profiel": 2, "Materiaal": 3, "Fase": 7, "Status": 8}
            column = columns.get(label)
            if column is not None:
                self.table.sortItems(column, QtCore.Qt.SortOrder.AscendingOrder)
                self.status.setText(f"BOM gegroepeerd op {label.lower()}; selectie blijft gekoppeld aan Viewer V15")

        def _show_header_menu(self, position: QtCore.QPoint) -> None:
            header = self.table.horizontalHeader()
            column = header.logicalIndexAt(position)
            menu = QtWidgets.QMenu(self)
            if column >= 0:
                menu.addAction("Oplopend sorteren", lambda: self.table.sortItems(column, QtCore.Qt.SortOrder.AscendingOrder))
                menu.addAction("Aflopend sorteren", lambda: self.table.sortItems(column, QtCore.Qt.SortOrder.DescendingOrder))
                if self.COLUMNS[column] in {"Merk", "Profiel", "Materiaal", "Fase", "Status"}:
                    menu.addAction("Op deze kolom groeperen", lambda: self.group_by.setCurrentText(self.COLUMNS[column]))
                menu.addSeparator()
                menu.addAction("Kolom verbergen", lambda: self.table.setColumnHidden(column, True))
            fields = menu.addMenu("Kolommen")
            for index, label in enumerate(self.COLUMNS):
                action = fields.addAction(label)
                action.setCheckable(True)
                action.setChecked(not self.table.isColumnHidden(index))
                action.toggled.connect(lambda checked, value=index: self.table.setColumnHidden(value, not checked))
            menu.addAction("Layout herstellen", self._reset_columns)
            menu.exec(header.mapToGlobal(position))

        def _show_table_menu(self, position: QtCore.QPoint) -> None:
            item = self.table.itemAt(position)
            if item is None:
                return
            menu = QtWidgets.QMenu(self)
            menu.addAction("Tonen in Viewer", lambda: self.action_requested.emit("viewer"))
            menu.addAction("Alleen deze regel selecteren", lambda: self._select_matching(item.column(), item.text(), exact_row=item.row()))
            if item.column() in {0, 2, 3, 7, 8}:
                menu.addAction(f"Selecteer dezelfde {self.COLUMNS[item.column()].lower()}", lambda: self._select_matching(item.column(), item.text()))
            menu.addSeparator()
            menu.addAction("Op deze kolom groeperen", lambda: self.group_by.setCurrentText(self.COLUMNS[item.column()]) if self.COLUMNS[item.column()] in {"Merk", "Profiel", "Materiaal", "Fase", "Status"} else None)
            menu.addAction("Excel / BOM export", self.window.project_page.export_bom)
            menu.exec(self.table.viewport().mapToGlobal(position))

        def _select_matching(self, column: int, value: str, *, exact_row: int | None = None) -> None:
            self._syncing = True
            try:
                self.table.clearSelection()
                flags = QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows
                for row in range(self.table.rowCount()):
                    candidate = self.table.item(row, column)
                    if candidate is None or self.table.isRowHidden(row):
                        continue
                    if (exact_row is not None and row == exact_row) or (exact_row is None and candidate.text() == value):
                        self.table.selectionModel().select(candidate.index(), flags)
            finally:
                self._syncing = False
            self._table_selection_changed()

        def _reset_columns(self) -> None:
            for column in range(self.table.columnCount()):
                self.table.setColumnHidden(column, False)
            self.group_by.setCurrentIndex(0)
            self.status_filter.setCurrentIndex(0)
            self.search.clear()
            self._resize_columns()

        def handle_ribbon(self, command: str) -> None:
            if command == "columns":
                self._show_header_menu(QtCore.QPoint(8, self.table.horizontalHeader().height() // 2))
            elif command == "filter":
                self.search.setFocus()
                self.search.selectAll()
            elif command == "group":
                self.group_by.showPopup()
            elif command == "sort":
                self.table.sortItems(1, QtCore.Qt.SortOrder.AscendingOrder)
            elif command in {"totals", "units"}:
                self.refresh()
            elif command == "reset":
                self._reset_columns()
            else:
                self.refresh()

        def _select_context_rows(self) -> None:
            selected = set(_selection_ids(self._selection))
            self._syncing = True
            try:
                self.table.clearSelection()
                for row in range(self.table.rowCount()):
                    item = self.table.item(row, 0)
                    if item is not None and str(item.data(QtCore.Qt.ItemDataRole.UserRole)) in selected:
                        self.table.selectRow(row)
            finally:
                self._syncing = False

        def _table_selection_changed(self) -> None:
            if self._syncing or self._workspace is None:
                return
            ids = []
            for item in self.table.selectedItems():
                value = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "")
                if value and value not in ids:
                    ids.append(value)
            if ids:
                self.window.application_context.request_selection(ids, origin="bom")


    class ScribingWorkspacePanel(QtWidgets.QWidget):
        """Visible M1-M18 authority and mark workspace for the active selection."""

        action_requested = QtCore.Signal(str)

        def __init__(self, window: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.window = window
            self._workspace: Any | None = None
            self._selection: Any | None = None
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(7)
            self.header = _WorkspaceHeader(
                "Scribing M18",
                "Contact-, markeer- en deployment-evidence blijft gebonden aan dezelfde part-ID en fail-closed authority.",
            )
            root.addWidget(self.header)
            actions = QtWidgets.QHBoxLayout()
            exact = QtWidgets.QPushButton("Open scribing editor")
            exact.setObjectName("primaryButton")
            exact.clicked.connect(lambda: self.action_requested.emit("open_exact"))
            verify = QtWidgets.QPushButton("Controleer M18 authority")
            verify.clicked.connect(self._verify_authority)
            viewer = QtWidgets.QPushButton("Terug naar Viewer")
            viewer.clicked.connect(lambda: self.action_requested.emit("viewer"))
            actions.addWidget(exact)
            actions.addWidget(verify)
            actions.addStretch(1)
            actions.addWidget(viewer)
            root.addLayout(actions)

            splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
            marks_box = QtWidgets.QGroupBox("Scribing / markeringen in actieve context")
            marks_layout = QtWidgets.QVBoxLayout(marks_box)
            self.marks = QtWidgets.QTreeWidget()
            self.marks.setHeaderLabels(("Mark", "Onderdeel", "Type", "Zijde", "Status", "Herkomst"))
            self.marks.setRootIsDecorated(False)
            self.marks.setAlternatingRowColors(True)
            marks_layout.addWidget(self.marks)
            splitter.addWidget(marks_box)
            authority_box = QtWidgets.QGroupBox("Frozen authority chain")
            authority_layout = QtWidgets.QVBoxLayout(authority_box)
            self.authority = QtWidgets.QTreeWidget()
            self.authority.setHeaderLabels(("Fase", "Status", "Modules", "Stores", "Blokkade"))
            self.authority.setRootIsDecorated(False)
            self.authority.setAlternatingRowColors(True)
            authority_layout.addWidget(self.authority)
            splitter.addWidget(authority_box)
            splitter.setSizes((360, 260))
            root.addWidget(splitter, 1)
            self.status = QtWidgets.QLabel("Machine-transfer blijft gesloten.")
            self.status.setObjectName("safetyStatus")
            root.addWidget(self.status)

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            changed = workspace is not self._workspace
            self._workspace = workspace
            self._selection = selection
            self.header.set_context(workspace, selection)
            self._refresh_marks()
            if changed:
                self.authority.clear()

        def _refresh_marks(self) -> None:
            self.marks.clear()
            if self._workspace is None:
                return
            selected = set(_selection_ids(self._selection))
            stores = m18_store_snapshot(self._workspace.project)
            for store_name, origin in (
                ("manufacturing_marks", "M3/M18"),
                ("manufacturing_mark_states", "M18 state"),
                ("manufacturing_contact_patches", "M2 contact"),
            ):
                records = stores.get(store_name, {})
                if not isinstance(records, dict):
                    continue
                for record_id, raw in sorted(records.items()):
                    record = raw if isinstance(raw, dict) else {}
                    part_id = _text(
                        record.get("part_id") or record.get("target_part_id")
                        or record.get("entity_id") or record.get("object_id"), ""
                    )
                    if selected and part_id and part_id not in selected:
                        continue
                    item = QtWidgets.QTreeWidgetItem(self.marks)
                    values = (
                        record_id, part_id or "project", record.get("mark_type") or record.get("type") or store_name,
                        record.get("side") or record.get("face") or "-", record.get("status") or "stored", origin,
                    )
                    for column, value in enumerate(values):
                        item.setText(column, _text(value))
            if self.marks.topLevelItemCount() == 0:
                empty = QtWidgets.QTreeWidgetItem(self.marks)
                empty.setText(0, "Geen opgeslagen marks in deze context")
                empty.setText(4, "gereed voor editor")

        def _verify_authority(self) -> None:
            self.authority.clear()
            if self._workspace is None:
                self.status.setText("Open eerst een project. Machine-transfer blijft gesloten.")
                return
            self.status.setText("M18 frozen authority wordt cryptografisch gecontroleerd...")
            QtWidgets.QApplication.processEvents()
            try:
                from cws_convertor.manufacturing.authority import authority_chain_status

                report = authority_chain_status(self._workspace.project)
                for phase, phase_report in report.get("m9_m18", {}).items():
                    errors = list(phase_report.get("errors") or [])
                    item = QtWidgets.QTreeWidgetItem(self.authority)
                    values = (
                        phase,
                        "Beschikbaar" if phase_report.get("available") else "Geblokkeerd",
                        ", ".join(phase_report.get("loaded_modules") or ()),
                        ", ".join(f"{key}: {value}" for key, value in phase_report.get("store_counts", {}).items()),
                        "; ".join(errors) or "-",
                    )
                    for column, value in enumerate(values):
                        item.setText(column, _text(value))
                origin = report.get("m18_origin", {})
                state = "PASS" if report.get("all_authority_modules_available") else "BLOCKED"
                self.status.setText(
                    f"Authority {state} | M18 {origin.get('version', '-')} | "
                    f"runtime {str(origin.get('runtime_sha256', ''))[:12]}... | machine-transfer gesloten"
                )
            except Exception as exc:
                self.status.setText(f"Authority BLOCKED: {type(exc).__name__}: {exc}")


    class _NestingSolveWorker(QtCore.QObject):
        completed = QtCore.Signal(object)
        failed = QtCore.Signal(str)
        progress = QtCore.Signal(str)
        finished = QtCore.Signal()

        def __init__(self, prepared: Any) -> None:
            super().__init__()
            self.prepared = prepared

        @QtCore.Slot()
        def run(self) -> None:
            try:
                from cws_convertor.optimization.profile_nesting import execute_phase5_solve

                outcome = execute_phase5_solve(
                    self.prepared,
                    progress_callback=lambda value: self.progress.emit(
                        str(value.get("message") or value.get("phase") or "Optimaliseren")
                    ),
                )
                self.completed.emit(outcome)
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")
            finally:
                self.finished.emit()

        def run_job(self, context: Any) -> Any:
            try:
                from cws_convertor.optimization.profile_nesting import execute_phase5_solve

                def report(value: dict[str, Any]) -> None:
                    context.check_cancelled()
                    message = str(value.get("message") or value.get("phase") or "Optimaliseren")
                    progress = float(value.get("progress", value.get("percentage", 0.0)) or 0.0)
                    if progress > 1.0:
                        progress /= 100.0
                    context.stage("nesting", progress, message)
                    self.progress.emit(message)

                outcome = execute_phase5_solve(self.prepared, progress_callback=report)
                context.check_cancelled()
                self.completed.emit(outcome)
                return outcome
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")
                raise
            finally:
                self.finished.emit()


    class ProfileNestingPanel(QtWidgets.QWidget):
        """Qt integration for frozen Profile Nesting 0.8.12."""

        action_requested = QtCore.Signal(str)

        def __init__(self, window: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.window = window
            self._workspace: Any | None = None
            self._selection: Any | None = None
            self._demand_report: Any | None = None
            self._thread: Any | None = None
            self._worker: Any | None = None
            self._job_manager = getattr(window, "job_manager", None)
            self._job_id: str | None = None
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(7)
            self.header = _WorkspaceHeader(
                "Profile Nesting / Optimalisatie 0.8.12",
                "Deterministische 1D-profieloptimalisatie op Project Model 2.25; directe machine-transfer is niet toegestaan.",
            )
            root.addWidget(self.header)
            controls = QtWidgets.QHBoxLayout()
            self.analyse = QtWidgets.QPushButton("Analyseer geschiktheid")
            self.analyse.clicked.connect(self._analyse)
            self.solve = QtWidgets.QPushButton("Optimaliseer project")
            self.solve.setObjectName("primaryButton")
            self.solve.clicked.connect(self._start_solve)
            profiles = QtWidgets.QPushButton("Profielbibliotheek")
            profiles.clicked.connect(lambda: self.action_requested.emit("legacy_profiles"))
            viewer = QtWidgets.QPushButton("Terug naar Viewer")
            viewer.clicked.connect(lambda: self.action_requested.emit("viewer"))
            self.mode = QtWidgets.QComboBox()
            self.mode.addItem("Concept / review", "concept")
            self.mode.addItem("Productie (strikte gate)", "production")
            controls.addWidget(self.analyse)
            controls.addWidget(self.solve)
            controls.addWidget(self.mode)
            controls.addWidget(profiles)
            controls.addStretch(1)
            controls.addWidget(viewer)
            root.addLayout(controls)

            self.tabs = QtWidgets.QTabWidget()
            demand_page = QtWidgets.QWidget()
            demand_layout = QtWidgets.QVBoxLayout(demand_page)
            self.demand = QtWidgets.QTreeWidget()
            self.demand.setHeaderLabels(("Onderdeel", "Profiel", "Materiaal", "Lengte", "Aantal", "Gate", "Reden"))
            self.demand.setRootIsDecorated(False)
            self.demand.setAlternatingRowColors(True)
            demand_layout.addWidget(self.demand)
            self.tabs.addTab(demand_page, "Onderdelen")
            run_page = QtWidgets.QWidget()
            run_layout = QtWidgets.QVBoxLayout(run_page)
            self.runs = QtWidgets.QTreeWidget()
            self.runs.setHeaderLabels(("Run", "Status", "Resultaat", "Solver", "Waste", "Snapshot"))
            self.runs.setRootIsDecorated(False)
            self.runs.setAlternatingRowColors(True)
            run_layout.addWidget(self.runs)
            self.tabs.addTab(run_page, "Runs")
            root.addWidget(self.tabs, 1)
            self.status = QtWidgets.QLabel("Open een project om profielonderdelen te analyseren.")
            self.status.setObjectName("safetyStatus")
            root.addWidget(self.status)

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            changed = workspace is not self._workspace
            self._workspace = workspace
            self._selection = selection
            self.header.set_context(workspace, selection)
            self.analyse.setEnabled(workspace is not None and self._job_id is None)
            self.solve.setEnabled(workspace is not None and self._job_id is None)
            if changed:
                self._demand_report = None
                self.demand.clear()
                self._refresh_runs()
                if workspace is None:
                    self.status.setText("Open een project om profielonderdelen te analyseren.")
                else:
                    self.status.setText("Project geladen; profielgeschiktheid wordt geanalyseerd.")
                    QtCore.QTimer.singleShot(0, self._analyse)

        def _analyse(self) -> None:
            self.demand.clear()
            if self._workspace is None:
                return
            try:
                from cws_convertor.optimization.profile_nesting import extract_demand

                mode = str(self.mode.currentData() or "concept")
                report = extract_demand(
                    self._workspace.project,
                    mode=mode,
                    defer_machine_compatibility=True,
                )
                self._demand_report = report
                selected = set(_selection_ids(self._selection))
                visible = 0
                for line in report.demand_lines:
                    if selected and str(line.part_id) not in selected:
                        continue
                    visible += 1
                    reasons = "; ".join(message.message for message in line.eligibility_reasons[:3])
                    item = QtWidgets.QTreeWidgetItem(self.demand)
                    values = (
                        line.part_position or line.part_id,
                        line.profile_name,
                        line.material_grade or line.material,
                        f"{_number(line.nominal_length_mm, 0)} mm",
                        line.quantity,
                        line.eligibility_status,
                        reasons or "Geschikt",
                    )
                    for column, value in enumerate(values):
                        item.setText(column, _text(value))
                eligible = sum(line.eligibility_status == "eligible" for line in report.demand_lines)
                blocked = sum(line.eligibility_status == "blocked" for line in report.demand_lines)
                scope = "huidige selectie" if selected else "project"
                self.status.setText(
                    f"Analyse gereed | scopeweergave: {scope} ({visible}) | eligible: {eligible} | "
                    f"blocked: {blocked} | snapshot {report.demand_snapshot_hash[:12]}..."
                )
            except Exception as exc:
                self.status.setText(f"Nestinganalyse geblokkeerd: {type(exc).__name__}: {exc}")

        def _start_solve(self) -> None:
            if self._workspace is None or self._job_id is not None:
                return
            try:
                from cws_convertor.optimization.profile_nesting import prepare_phase5_solve

                prepared = prepare_phase5_solve(
                    self._workspace.project,
                    mode=str(self.mode.currentData() or "concept"),
                    created_by="qt-gui",
                    scenario_id=f"ui-{str(getattr(getattr(self, 'phase3_scenario', None), 'currentData', lambda: 'waste')() or 'waste')}",
                    scenario_family=str(getattr(getattr(self, "phase3_scenario", None), "currentData", lambda: "waste")() or "waste"),
                    backend=str(getattr(getattr(self, "phase3_backend", None), "currentData", lambda: "auto")() or "auto"),
                    timeout_seconds=30.0,
                )
            except Exception as exc:
                self.status.setText(f"Optimalisatie-preflight geblokkeerd: {type(exc).__name__}: {exc}")
                return
            self.solve.setEnabled(False)
            self.analyse.setEnabled(False)
            self.status.setText("Optimalisatie draait buiten de UI-thread...")
            worker = _NestingSolveWorker(prepared)
            worker.progress.connect(self.status.setText)
            worker.completed.connect(self._solve_completed)
            worker.failed.connect(self._solve_failed)
            worker.finished.connect(self._solve_finished)
            if self._job_manager is None:
                self._solve_failed("Centrale JobManager is niet beschikbaar")
                self._solve_finished()
                return
            self._worker = worker
            self._job_id = self._job_manager.submit(
                "nesting",
                worker.run_job,
                description="Profile Nesting optimalisatie",
                project_id=str(self._workspace.project.project_id),
                max_retries=1,
            )

        def _solve_completed(self, outcome: Any) -> None:
            if self._workspace is None:
                return
            try:
                from cws_convertor.optimization.profile_nesting import commit_phase5_outcome

                state = commit_phase5_outcome(self._workspace.project, outcome, user="qt-gui")
                if state == "committed":
                    self._workspace.session.save(
                        user="qt-gui",
                        revision_message="Profile Nesting 0.8.12 run opgeslagen",
                    )
                self.status.setText(
                    f"Optimalisatie {state} | resultaat: {getattr(outcome.prepared.run, 'result_status', '-')} | "
                    "machine-transfer gesloten"
                )
                self._refresh_runs()
                self.tabs.setCurrentIndex(1)
            except Exception as exc:
                self.status.setText(f"Optimalisatieresultaat geblokkeerd: {type(exc).__name__}: {exc}")

        def _solve_failed(self, message: str) -> None:
            self.status.setText(f"Optimalisatie mislukt of geblokkeerd: {message}")

        def _solve_finished(self) -> None:
            self._thread = None
            self._job_id = None
            self._worker = None
            self.analyse.setEnabled(self._workspace is not None)
            self.solve.setEnabled(self._workspace is not None)

        def _refresh_runs(self) -> None:
            self.runs.clear()
            if self._workspace is None:
                return
            stores = m18_store_snapshot(self._workspace.project)
            records = stores.get("profile_nesting_runs", {})
            if not isinstance(records, dict):
                return
            for run_id, record in sorted(records.items(), reverse=True):
                payload = record if isinstance(record, dict) else {}
                run = payload.get("run", {}) if isinstance(payload.get("run"), dict) else payload
                plan = payload.get("plan", {}) if isinstance(payload.get("plan"), dict) else {}
                evidence = payload.get("solver_evidence", {}) if isinstance(payload.get("solver_evidence"), dict) else {}
                item = QtWidgets.QTreeWidgetItem(self.runs)
                values = (
                    run_id,
                    run.get("status") or "stored",
                    run.get("result_status") or evidence.get("status") or "-",
                    evidence.get("backend") or run.get("solver_name") or "-",
                    plan.get("total_waste_mm") or plan.get("waste_mm") or "-",
                    str(run.get("input_snapshot_hash") or "")[:12] or "-",
                )
                for column, value in enumerate(values):
                    item.setText(column, _text(value))


    class ProductionWorkflowPanel(QtWidgets.QWidget):
        """Clickable readiness/report surface over the active canonical scope."""

        action_requested = QtCore.Signal(str)

        def __init__(self, window: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.window = window
            self._workspace: Any | None = None
            self._selection: Any | None = None
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(8, 8, 8, 8)
            root.setSpacing(7)
            self.header = _WorkspaceHeader(
                "Rapportage & Productieworkflow",
                "Readiness, scribing, BOM en exportgates worden samengebracht zonder productieblokkades te omzeilen.",
            )
            root.addWidget(self.header)
            actions = QtWidgets.QHBoxLayout()
            refresh = QtWidgets.QPushButton("Rapport vernieuwen")
            refresh.clicked.connect(self.refresh)
            viewer = QtWidgets.QPushButton("Terug naar Viewer")
            viewer.clicked.connect(lambda: self.action_requested.emit("viewer"))
            export = QtWidgets.QPushButton("Naar Exporteren")
            export.setObjectName("primaryButton")
            export.clicked.connect(lambda: self.action_requested.emit("export"))
            actions.addWidget(refresh)
            actions.addStretch(1)
            actions.addWidget(viewer)
            actions.addWidget(export)
            root.addLayout(actions)
            cards = QtWidgets.QHBoxLayout()
            self.scope_card = QtWidgets.QLabel("Scope\n-")
            self.ready_card = QtWidgets.QLabel("Ready\n0")
            self.blocked_card = QtWidgets.QLabel("Blocked\n0")
            self.next_card = QtWidgets.QLabel("Volgende stap\n-")
            for card in (self.scope_card, self.ready_card, self.blocked_card, self.next_card):
                card.setObjectName("summaryCard")
                cards.addWidget(card)
            root.addLayout(cards)
            self.table = QtWidgets.QTreeWidget()
            self.table.setHeaderLabels(("Onderdeel", "Status", "Toegestaan", "Geblokkeerd", "Blocking codes"))
            self.table.setRootIsDecorated(False)
            self.table.setAlternatingRowColors(True)
            self.table.itemClicked.connect(self._item_clicked)
            root.addWidget(self.table, 1)
            self.status = QtWidgets.QLabel("Machine-transfer blijft gesloten.")
            self.status.setObjectName("safetyStatus")
            root.addWidget(self.status)

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            self._workspace = workspace
            self._selection = selection
            self.header.set_context(workspace, selection)
            self.refresh()

        def refresh(self) -> None:
            self.table.clear()
            if self._workspace is None:
                self._last_snapshot = None
                self.scope_card.setText("Scope\n-")
                return
            report = build_production_workflow_snapshot(self._workspace, _selection_ids(self._selection))
            self._last_snapshot = report
            for part in report.part_statuses:
                item = QtWidgets.QTreeWidgetItem(self.table)
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, part.entity_id)
                values = (
                    part.mark,
                    "READY" if part.production_ready else "BLOCKED",
                    ", ".join(part.allowed_formats) or "-",
                    ", ".join(part.blocked_formats) or "-",
                    ", ".join(part.blocking_codes) or "-",
                )
                for column, value in enumerate(values):
                    item.setText(column, _text(value))
            self.scope_card.setText(f"Scope\n{report.scope}")
            self.ready_card.setText(f"Ready\n{report.ready_part_count}")
            self.blocked_card.setText(f"Blocked\n{report.blocked_part_count}")
            self.next_card.setText(f"Volgende stap\n{report.next_action}")
            self.status.setText(f"{report.project_name} | {report.part_count} onderdelen | machine-transfer gesloten")

        def _item_clicked(self, item: Any, _column: int) -> None:
            entity_id = str(item.data(0, QtCore.Qt.ItemDataRole.UserRole) or "")
            if entity_id and self._workspace is not None:
                self.window.application_context.request_selection((entity_id,), origin="report")


    # The production-hub implementation supersedes the early raw-part table
    # while preserving the public import used by the unified shells.
    from .bom_workspace import BomWorkspacePanel as BomWorkspacePanel

else:
    class _Unavailable:
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    BomWorkspacePanel = ProfileNestingPanel = ProductionWorkflowPanel = ScribingWorkspacePanel = _Unavailable


__all__ = [
    "BomWorkspacePanel",
    "ProfileNestingPanel",
    "ProductionWorkflowPanel",
    "ScribingWorkspacePanel",
]
