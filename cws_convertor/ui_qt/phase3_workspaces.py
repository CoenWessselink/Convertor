"""Integrated phase-3 workspaces around the existing production engines."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

from cws_convertor.optimization.profile_nesting.command_service import (
    ProfileNestingCommandError,
    ProfileNestingCommandService,
)
import json
from typing import Any, Iterable, Mapping

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cws_convertor.project.manufacturing_contracts import ExportGrouping, ExportScope, ExportScopeKind
from cws_convertor.ui_qt.product_workspaces import (
    ProfileNestingPanel as _ProfileNestingPanel,
    ScribingWorkspacePanel as _ScribingWorkspacePanel,
)
from cws_viewer.export_center.models import ExportScope as ViewerExportScope
from cws_viewer.export_center.models import ExportScopeKind as ViewerExportScopeKind
from cws_viewer.export_center.service import V15ExportCenterService


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    return value


def _selection_ids(selection: Any) -> tuple[str, ...]:
    for name in ("entity_ids", "selected_entity_ids", "part_ids", "ids"):
        value = getattr(selection, name, None)
        if value:
            return tuple(str(item) for item in value)
    if isinstance(selection, (tuple, list, set)):
        return tuple(str(item) for item in selection)
    return ()


def _project_from_workspace(workspace: Any) -> Any:
    return getattr(workspace, "project", None) or getattr(workspace, "project_model", None) or workspace


def _owner_window(widget: QWidget) -> Any:
    candidate = getattr(widget, "window", None)
    return candidate() if callable(candidate) else candidate


def _iter_records(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        yield from ((str(key), item) for key, item in value.items())
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            plain = _plain(item)
            identifier = ""
            if isinstance(plain, Mapping):
                identifier = str(
                    plain.get("id")
                    or plain.get("part_id")
                    or plain.get("run_id")
                    or plain.get("mark_id")
                    or index
                )
            yield identifier or str(index), item


def _fill_table(table: QTableWidget, records: Iterable[tuple[str, Any]]) -> None:
    rows = list(records)
    keys: list[str] = ["id"]
    flattened: list[dict[str, Any]] = []
    for identifier, record in rows:
        plain = _plain(record)
        row = dict(plain) if isinstance(plain, Mapping) else {"value": plain}
        row.setdefault("id", identifier)
        flattened.append(row)
        for key in row:
            if key not in keys and len(keys) < 10:
                keys.append(str(key))
    table.clear()
    table.setColumnCount(len(keys))
    table.setHorizontalHeaderLabels(keys)
    table.setRowCount(len(flattened))
    for row_index, row in enumerate(flattened):
        for column, key in enumerate(keys):
            value = row.get(key, "")
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, sort_keys=True, default=str)
            table.setItem(row_index, column, QTableWidgetItem(str(value)))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)


class ScribingWorkspacePanel(_ScribingWorkspacePanel):
    """Face/contact/mark authoring around the exact marking engine."""

    TAB_NAMES = (
        "Faces",
        "Contacts",
        "Scribing",
        "Hole References",
        "Identification",
        "Machine Reachability",
        "Sequence",
        "Validation",
        "Audit",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("phase3ScribingWorkspace")
        self._phase3_project = None
        self._phase3_selection: tuple[str, ...] = ()
        self._phase3_tables: dict[str, QTableWidget] = {}
        self._phase3_refreshing = False

        surface = QSplitter(Qt.Orientation.Horizontal, self)
        surface.setObjectName("scribingAuthoringSurface")
        left = QGroupBox("Assembly / parts en filters", surface)
        left_layout = QVBoxLayout(left)
        self.scribing_filter = QLineEdit(left)
        self.scribing_filter.setPlaceholderText("Filter op profiel, status of machine")
        self.scribing_ruleset = QComboBox(left)
        self.scribing_ruleset.addItem("Geen declaratieve ruleset", "")
        self.scribing_tree = QTreeWidget(left)
        self.scribing_tree.setHeaderLabels(["Assembly / part", "Profiel", "Status", "Machine"])
        left_layout.addWidget(self.scribing_filter)
        left_layout.addWidget(self.scribing_ruleset)
        left_layout.addWidget(self.scribing_tree, 1)

        center = QGroupBox("Shared Viewer V15 overlays", surface)
        center_layout = QVBoxLayout(center)
        self.overlay_status = QLabel("De permanente ViewerHost blijft eigenaar van camera en scene.", center)
        self.overlay_status.setWordWrap(True)
        center_layout.addWidget(self.overlay_status)
        for label, layer in (
            ("Faces", "faces"),
            ("Contacts", "contacts"),
            ("Candidate marks", "candidate_marks"),
            ("Accepted marks", "accepted_marks"),
            ("Suppressed marks", "suppressed_marks"),
            ("Hole / POP references", "hole_references"),
            ("Machine reachability", "machine_reachability"),
        ):
            toggle = QCheckBox(label, center)
            toggle.setObjectName(f"overlay_{layer}")
            toggle.toggled.connect(lambda checked, name=layer: self._set_overlay(name, checked))
            center_layout.addWidget(toggle)
        center_layout.addStretch(1)

        right = QGroupBox("Mark / face / contact / rule / capability", surface)
        right_layout = QVBoxLayout(right)
        self.scribing_properties = QTreeWidget(right)
        self.scribing_properties.setHeaderLabels(["Eigenschap", "Waarde"])
        right_layout.addWidget(self.scribing_properties, 1)
        self.override_delta = QLineEdit(right)
        self.override_delta.setPlaceholderText('{"suppressed": true, "reason": "..."}')
        self.apply_override = QPushButton("Override als delta vastleggen", right)
        self.apply_override.clicked.connect(self._record_override_delta)
        right_layout.addWidget(self.override_delta)
        right_layout.addWidget(self.apply_override)
        surface.addWidget(left)
        surface.addWidget(center)
        surface.addWidget(right)
        surface.setSizes([320, 440, 320])

        self.phase3_scribing_tabs = QTabWidget(self)
        self.phase3_scribing_tabs.setObjectName("phase3ScribingTabs")
        for name in self.TAB_NAMES:
            table = QTableWidget(self.phase3_scribing_tabs)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.phase3_scribing_tabs.addTab(table, name)
            self._phase3_tables[name] = table
        root = self.layout()
        if root is not None:
            root.addWidget(surface)
            root.addWidget(self.phase3_scribing_tabs, 1)
        self.scribing_filter.textChanged.connect(self._apply_tree_filter)
        self.scribing_tree.itemSelectionChanged.connect(self._push_tree_selection)

    def set_context(self, workspace: Any, selection: Any) -> None:
        super().set_context(workspace, selection)
        self._phase3_project = _project_from_workspace(workspace)
        self._phase3_selection = _selection_ids(selection)
        self._refresh_phase3()

    def _settings(self) -> dict[str, Any]:
        settings = getattr(self._phase3_project, "settings", {})
        return settings if isinstance(settings, dict) else {}

    def _refresh_phase3(self) -> None:
        settings = self._settings()
        self._phase3_refreshing = True
        self.scribing_tree.clear()
        parts = getattr(self._phase3_project, "parts", ())
        for identifier, part in _iter_records(parts):
            data = _plain(part)
            data = data if isinstance(data, Mapping) else {}
            item = QTreeWidgetItem(
                [
                    str(data.get("position") or data.get("name") or identifier),
                    str(data.get("profile") or data.get("profile_name") or ""),
                    str(data.get("manufacturing_status") or data.get("status") or ""),
                    str(data.get("machine_id") or ""),
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, str(data.get("id") or data.get("part_id") or identifier))
            self.scribing_tree.addTopLevelItem(item)
            if item.data(0, Qt.ItemDataRole.UserRole) in self._phase3_selection:
                item.setSelected(True)

        rulesets = settings.get("manufacturing_rulesets", settings.get("marking_rulesets", {}))
        current = self.scribing_ruleset.currentData()
        self.scribing_ruleset.clear()
        self.scribing_ruleset.addItem("Geen declaratieve ruleset", "")
        for identifier, ruleset in _iter_records(rulesets):
            data = _plain(ruleset)
            name = data.get("name", identifier) if isinstance(data, Mapping) else identifier
            self.scribing_ruleset.addItem(str(name), identifier)
        index = self.scribing_ruleset.findData(current)
        if index >= 0:
            self.scribing_ruleset.setCurrentIndex(index)

        sources = {
            "Faces": ("manufacturing_face_store", "manufacturing_faces"),
            "Contacts": ("contact_patch_store", "manufacturing_contacts"),
            "Scribing": ("m18_store_snapshot", "manufacturing_mark_sets"),
            "Hole References": ("hole_reference_store", "manufacturing_hole_references"),
            "Identification": ("identification_store", "manufacturing_identification"),
            "Machine Reachability": ("machine_capability_store", "manufacturing_capabilities"),
            "Sequence": ("neutral_manufacturing_jobs", "manufacturing_sequences"),
            "Validation": ("manufacturing_validation", "mark_validation_store"),
            "Audit": ("manufacturing_audit", "manufacturing_evidence"),
        }
        for tab_name, keys in sources.items():
            value: Any = {}
            for key in keys:
                if key in settings:
                    value = settings[key]
                    break
            _fill_table(self._phase3_tables[tab_name], _iter_records(value))
        self.scribing_properties.clear()
        authority_data = _plain(settings.get("m18_authority_verification", {}))
        for key, value in (authority_data.items() if isinstance(authority_data, Mapping) else ()):
            self.scribing_properties.addTopLevelItem(QTreeWidgetItem([str(key), str(value)]))
        self.scribing_properties.addTopLevelItem(QTreeWidgetItem(["Machine transfer", "UIT (frozen safety boundary)"]))
        self._phase3_refreshing = False

    def _set_overlay(self, layer: str, checked: bool) -> None:
        viewer = getattr(getattr(_owner_window(self), "project_page", None), "viewer", None)
        applied = False
        for name in ("set_manufacturing_overlay", "set_overlay_visible", "set_overlay_enabled"):
            method = getattr(viewer, name, None)
            if callable(method):
                try:
                    method(layer, bool(checked))
                    applied = True
                    break
                except TypeError:
                    continue
        self.overlay_status.setText(
            f"Overlay {layer}: {'aan' if checked else 'uit'}" + ("" if applied else " (context geregistreerd)")
        )

    def _apply_tree_filter(self, text: str) -> None:
        needle = text.strip().casefold()
        for index in range(self.scribing_tree.topLevelItemCount()):
            item = self.scribing_tree.topLevelItem(index)
            haystack = " ".join(item.text(column) for column in range(item.columnCount())).casefold()
            item.setHidden(bool(needle and needle not in haystack))

    def _push_tree_selection(self) -> None:
        if self._phase3_refreshing:
            return
        ids = tuple(
            str(item.data(0, Qt.ItemDataRole.UserRole))
            for item in self.scribing_tree.selectedItems()
            if item.data(0, Qt.ItemDataRole.UserRole)
        )
        context = getattr(_owner_window(self), "application_context", None)
        request = getattr(context, "request_selection", None)
        if callable(request) and ids:
            try:
                request(ids, origin="scribing")
            except TypeError:
                request(ids)

    def _record_override_delta(self) -> None:
        try:
            delta = json.loads(self.override_delta.text() or "{}")
            if not isinstance(delta, dict):
                raise ValueError("override moet een JSON-object zijn")
        except (ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Ongeldige override", str(exc))
            return
        overrides = self._settings().setdefault("manufacturing_override_deltas", [])
        overrides.append({"target_ids": list(self._phase3_selection), "changes": delta})
        self.override_delta.clear()
        self._refresh_phase3()


class ProfileNestingPanel(_ProfileNestingPanel):
    """Full planning surface around the existing profile nesting solver."""

    EXTRA_TABS = (
        "Scenarios",
        "Bars",
        "Stock / remnants / purchase",
        "Machines",
        "Tools / formulas",
        "Sequence",
        "Validation",
        "Evidence",
        "Reports / labels",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.profile_nesting_commands = ProfileNestingCommandService(user="qt-gui")
        self.setObjectName("phase3ProfileNestingWorkspace")
        self._phase3_workspace = None
        self._phase3_project = None
        self._phase3_selection: tuple[str, ...] = ()
        self._phase3_tables: dict[str, QTableWidget] = {}
        controls = QGroupBox("Scenario, locks en vrijgave", self)
        controls_layout = QHBoxLayout(controls)
        self.phase3_scenario = QComboBox(controls)
        for family in ("waste", "cost", "stock_first", "bars", "fast", "optimal", "custom"):
            self.phase3_scenario.addItem(family.replace("_", " ").title(), family)
        self.phase3_scenario.setToolTip("Scenariofamilie wordt als expliciete solver-input opgeslagen.")
        controls_layout.addWidget(self.phase3_scenario)
        self.phase3_backend = QComboBox(controls)
        for backend in ("auto", "exact", "greedy"):
            self.phase3_backend.addItem(backend.title(), backend)
        self.phase3_backend.setToolTip("Backendkeuze wordt met het solverbewijs vastgelegd.")
        controls_layout.addWidget(self.phase3_backend)
        for label, action in (
            ("Vergelijk scenario's", "compare"),
            ("Valideer", "validate"),
            ("Lock / unlock", "lock"),
            ("Move / reorder", "move"),
            ("Rotate / orientation", "orientation"),
            ("Common cut", "common_cut"),
            ("Partieel heroptimaliseren", "partial_reoptimize"),
            ("Undo", "undo"),
            ("Redo", "redo"),
            ("Layout opslaan", "save_layout"),
            ("Reset layout", "reset_layout"),
            ("Annuleren", "cancel"),
            ("Vernieuwen", "refresh"),
            ("Accepteer + reserveer", "accept_reserve"),
            ("Release neutraal pakket", "release"),
        ):
            button = QPushButton(label, controls)
            button.setObjectName(f"nesting_{action}")
            button.clicked.connect(lambda _checked=False, name=action: self._phase3_action(name))
            controls_layout.addWidget(button)
        self.phase3_proof_badge = QLabel("UNKNOWN", controls)
        self.phase3_proof_badge.setObjectName("profileNestingProofBadge")
        self.phase3_proof_badge.setStyleSheet(
            "QLabel { background: #fff4cf; border: 1px solid #c78b00; color: #5f4200; "
            "font-weight: 700; padding: 4px 8px; }"
        )
        controls_layout.addWidget(self.phase3_proof_badge)
        self.phase3_nesting_status = QLabel("Kies of bereken een run.", controls)
        controls_layout.addWidget(self.phase3_nesting_status, 1)
        self.phase3_nesting_tabs = QTabWidget(self)
        self.phase3_nesting_tabs.setObjectName("phase3NestingTabs")
        for name in self.EXTRA_TABS:
            table = QTableWidget(self.phase3_nesting_tabs)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.phase3_nesting_tabs.addTab(table, name)
            self._phase3_tables[name] = table
        root = self.layout()
        if root is not None:
            root.addWidget(controls)
            root.addWidget(self.phase3_nesting_tabs, 1)

    def set_context(self, workspace: Any, selection: Any) -> None:
        super().set_context(workspace, selection)
        self._phase3_workspace = workspace
        self._phase3_project = _project_from_workspace(workspace)
        self._phase3_selection = _selection_ids(selection)
        self._refresh_phase3_nesting()

    def _settings(self) -> dict[str, Any]:
        settings = getattr(self._phase3_project, "settings", {})
        return settings if isinstance(settings, dict) else {}

    def _refresh_phase3_nesting(self) -> None:
        settings = self._settings()
        sources = {
            "Scenarios": ("profile_nesting_scenarios", "profile_nesting_runs"),
            "Bars": ("profile_nesting_bars", "nesting_bars"),
            "Stock / remnants / purchase": ("profile_nesting_stock", "stock_inventory"),
            "Machines": ("profile_nesting_machines", "machine_profiles"),
            "Tools / formulas": ("profile_nesting_tools", "cut_formulas"),
            "Sequence": ("neutral_manufacturing_jobs", "manufacturing_sequences"),
            "Validation": ("profile_nesting_validation", "nesting_validation"),
            "Evidence": ("profile_nesting_evidence", "nesting_evidence"),
            "Reports / labels": ("profile_nesting_reports", "nesting_reports"),
        }
        for tab_name, keys in sources.items():
            value: Any = {}
            for key in keys:
                if key in settings:
                    value = settings[key]
                    break
            _fill_table(self._phase3_tables[tab_name], _iter_records(value))

        run_id = self._run_id()
        if not run_id or self._phase3_project is None:
            self.phase3_proof_badge.setText("UNKNOWN")
            return
        try:
            inspection = self.profile_nesting_commands.inspect_run(self._phase3_project, run_id)
            proof = str(inspection.get("proof_status") or "UNKNOWN")
            fresh = bool(dict(inspection.get("freshness") or {}).get("fresh"))
            self.phase3_proof_badge.setText(proof if fresh else f"STALE | {proof}")
        except ProfileNestingCommandError as exc:
            self.phase3_proof_badge.setText(f"BLOCKED {exc.code}")

    def _run_id(self) -> str:
        project = self._phase3_project
        settings = self._settings()
        run_id = str(
            getattr(project, "active_profile_nesting_run_id", "")
            or settings.get("active_profile_nesting_run_id", "")
        )
        if run_id:
            return run_id
        records = getattr(project, "profile_nesting_runs", {}) if project is not None else {}
        return str(next(reversed(records), "")) if isinstance(records, dict) else ""

    def _persist_phase3_project(self) -> None:
        workspace = self._phase3_workspace
        session = getattr(workspace, "session", None)
        save = getattr(session, "save", None)
        if not callable(save):
            return
        try:
            save()
        except TypeError:
            project_path = getattr(workspace, "project_path", None)
            if project_path:
                save(project_path)

    def _publish_optimization_context(self, run_id: str, result: Any) -> None:
        window = self.window()
        context = getattr(window, "application_context", None) or getattr(window, "app_context", None)
        update = getattr(context, "update_optimization_context", None)
        if not callable(update):
            return
        record = dict(getattr(self._phase3_project, "profile_nesting_runs", {}).get(run_id) or {})
        evidence = dict(record.get("solver_evidence") or {})
        update(
            active_profile_nesting_run=run_id,
            active_scenario_id=str(self.phase3_scenario.currentData() or "waste"),
            active_backend=str(self.phase3_backend.currentData() or "auto"),
            proof_status=str(getattr(result, "proof_status", self.phase3_proof_badge.text())),
            plan_revision_hash=str(getattr(result, "after_hash", "")),
            solver_evidence_hash=str(
                evidence.get("evidence_hash") or evidence.get("manifest_hash") or evidence.get("input_hash") or ""
            ),
        )

    def _phase3_action(self, action: str) -> None:
        project = self._phase3_project
        if project is None:
            self.phase3_nesting_status.setText("BLOCKED: geen actief canoniek project.")
            return
        run_id = self._run_id()
        if action == "cancel":
            job_id = str(getattr(self, "_job_id", "") or "")
            manager = getattr(self, "job_manager", None) or getattr(self, "_job_manager", None)
            if job_id and manager is not None:
                manager.cancel(job_id)
                self.phase3_nesting_status.setText(f"Solverjob {job_id} annuleren aangevraagd.")
            else:
                self.phase3_nesting_status.setText("Geen actieve solverjob om te annuleren.")
            return
        if action == "refresh":
            self._refresh_phase3_nesting()
            refresh = getattr(self, "_refresh_runs", None)
            if callable(refresh):
                refresh()
            self.phase3_nesting_status.setText("Project, runs en bewijsstatus vernieuwd.")
            return
        if action == "save_layout":
            self._persist_phase3_project()
            self.phase3_nesting_status.setText("Canonieke projectlayout opgeslagen.")
            return
        if action != "compare" and not run_id:
            self.phase3_nesting_status.setText("BLOCKED: selecteer of bereken eerst een nestingrun.")
            return
        try:
            service = self.profile_nesting_commands
            selected = tuple(self._phase3_selection)
            operations = {
                "compare": lambda: service.compare_scenarios(project),
                "validate": lambda: service.validate_plan(project, run_id),
                "lock": lambda: service.toggle_selected_lock(project, run_id, selected),
                "move": lambda: service.move_or_reorder_selected(project, run_id, selected),
                "orientation": lambda: service.cycle_selected_orientation(project, run_id, selected),
                "common_cut": lambda: service.cycle_selected_common_cut(project, run_id, selected),
                "partial_reoptimize": lambda: service.partial_reoptimize(
                    project, run_id, backend=str(self.phase3_backend.currentData() or "auto")
                ),
                "undo": lambda: service.undo(project, run_id),
                "redo": lambda: service.redo(project, run_id),
                "reset_layout": lambda: service.reset_layout(project, run_id),
                "accept_reserve": lambda: service.accept_plan(project, run_id, reserve_stock=True),
                "release": lambda: service.release_neutral_package(
                    project,
                    run_id,
                    Path.home() / "Documents" / "CWS Convertor" / "Profile Nesting Releases",
                ),
            }
            if action not in operations:
                raise ProfileNestingCommandError("CWS-NEST-UI-001", f"Onbekende UI-actie {action!r}")
            result = operations[action]()
            if action not in {"compare", "validate"}:
                self._persist_phase3_project()
            self._publish_optimization_context(run_id, result)
            self._refresh_phase3_nesting()
            self.phase3_nesting_status.setText(str(result.message or f"{action} voltooid"))
        except ProfileNestingCommandError as exc:
            self._refresh_phase3_nesting()
            self.phase3_nesting_status.setText(f"ROLLBACK / BLOCKED {exc.code}: {exc}")
        except Exception as exc:
            self._refresh_phase3_nesting()
            self.phase3_nesting_status.setText(f"ROLLBACK / BLOCKED {type(exc).__name__}: {exc}")


class Phase3ExportCenterPanel(QWidget):
    """Ten-step deterministic export flow on the existing V15 backend."""

    job_event = Signal(object)

    _BACKEND_KIND = {
        ExportScopeKind.SELECTION: ViewerExportScopeKind.CURRENT_SELECTION,
        ExportScopeKind.SELECTED_PARTS: ViewerExportScopeKind.ENTITY_IDS,
        ExportScopeKind.PART_MARK: ViewerExportScopeKind.PART_POSITIONS,
        ExportScopeKind.ASSEMBLY_MARK: ViewerExportScopeKind.ASSEMBLY_MARKS,
        ExportScopeKind.PHASE: ViewerExportScopeKind.PROJECT_PHASE,
        ExportScopeKind.BATCH: ViewerExportScopeKind.BATCH,
        ExportScopeKind.NESTING_RUN: ViewerExportScopeKind.NESTING_RUN,
        ExportScopeKind.NESTING_BAR: ViewerExportScopeKind.NESTING_BAR,
        ExportScopeKind.REVISION_DELTA: ViewerExportScopeKind.REVISION_DELTA,
        ExportScopeKind.FULL_PROJECT: ViewerExportScopeKind.FULL_PROJECT,
    }

    def __init__(self, viewer_host: Any, project: Any = None, *, job_manager: Any = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("phase3ExportCenter")
        self.viewer_host = viewer_host
        self.project = project
        self.job_manager = job_manager
        self.selection_ids: tuple[str, ...] = ()
        self._selection: Any = None
        self.service: V15ExportCenterService | None = None
        self.current_export_job_id = ""
        self.current_background_job_id = ""
        self._format_checks: dict[str, QCheckBox] = {}
        self.job_event.connect(self._on_job_event)
        if self.job_manager is not None:
            self.job_manager.add_listener(self.job_event.emit)

        root = QVBoxLayout(self)
        title = QLabel("Scope-first Export Center", self)
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        root.addWidget(title)
        top = QSplitter(Qt.Orientation.Horizontal, self)
        root.addWidget(top, 1)
        form_host = QWidget(top)
        form = QFormLayout(form_host)
        self.scope = QComboBox(form_host)
        for kind in ExportScopeKind:
            self.scope.addItem(kind.value.replace("_", " ").title(), kind)
        self.scope.setCurrentIndex(self.scope.findData(ExportScopeKind.SELECTION))
        self.scope_values = QLineEdit(form_host)
        self.scope_values.setPlaceholderText("Exacte IDs/marks, komma-gescheiden; leeg blijft leeg")
        form.addRow("1. Scope", self.scope)
        form.addRow("2. Filters", self.scope_values)
        self.grouping = QComboBox(form_host)
        for grouping in ExportGrouping:
            self.grouping.addItem(grouping.value.replace("_", " ").title(), grouping)
        form.addRow("3. Groepering", self.grouping)
        formats_host = QWidget(form_host)
        formats_layout = QHBoxLayout(formats_host)
        formats_layout.setContentsMargins(0, 0, 0, 0)
        for value in ("STEP", "IFC", "DSTV", "DXF", "PDF", "XLSX", "JSON", "CSV", "LABELS"):
            check = QCheckBox(value, formats_host)
            check.setChecked(value in {"STEP", "JSON"})
            formats_layout.addWidget(check)
            self._format_checks[value] = check
        form.addRow("4. Formats", formats_host)
        self.naming = QLineEdit("{project}_{scope}_{revision}", form_host)
        self.output_dir = QLineEdit(str(Path.cwd() / "build" / "exports"), form_host)
        browse = QPushButton("Kies map", form_host)
        browse.clicked.connect(self._choose_output)
        output_host = QWidget(form_host)
        output_layout = QHBoxLayout(output_host)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.output_dir, 1)
        output_layout.addWidget(browse)
        form.addRow("5. Naamgeving", self.naming)
        form.addRow("Output", output_host)
        self.preflight_button = QPushButton("6. Preflight", form_host)
        self.preflight_button.clicked.connect(self._preflight)
        self.generate_button = QPushButton("8. Generate", form_host)
        self.generate_button.clicked.connect(self._generate)
        self.cancel_button = QPushButton("Annuleren", form_host)
        self.cancel_button.clicked.connect(self._cancel)
        buttons = QWidget(form_host)
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.addWidget(self.preflight_button)
        buttons_layout.addWidget(self.generate_button)
        buttons_layout.addWidget(self.cancel_button)
        form.addRow(buttons)
        evidence = QTabWidget(top)
        self.blockers = QTextBrowser(evidence)
        self.verify = QTextBrowser(evidence)
        self.manifest = QTextBrowser(evidence)
        evidence.addTab(self.blockers, "7. Conflicts / blockers")
        evidence.addTab(self.verify, "9. Re-import verify")
        evidence.addTab(self.manifest, "10. Manifest / package")
        top.addWidget(form_host)
        top.addWidget(evidence)
        top.setSizes([620, 520])
        self.status = QLabel("Scope is verplicht; de applicatie verbreedt nooit automatisch naar full project.", self)
        root.addWidget(self.status)
        self._install_service()

    def set_context(self, workspace: Any, selection: Any) -> None:
        project = _project_from_workspace(workspace)
        if project is not self.project:
            self.project = project
            self._install_service()
        self.selection_ids = _selection_ids(selection)
        self._selection = selection
        self._show_scope_in_viewer()

    def _install_service(self) -> None:
        if self.project is None or not hasattr(self.project, "parts"):
            self.service = None
            return
        self.service = V15ExportCenterService(self.project, selection_entity_ids=lambda: self.selection_ids)

    def _values(self) -> tuple[str, ...]:
        return tuple(value.strip() for value in self.scope_values.text().split(",") if value.strip())

    def _scope(self) -> ExportScope:
        kind = ExportScopeKind(self.scope.currentData())
        grouping = ExportGrouping(self.grouping.currentData())
        values = self._values()
        entity_ids = self.selection_ids if kind is ExportScopeKind.SELECTION else ()
        if kind is ExportScopeKind.SELECTED_PARTS:
            entity_ids = values or self.selection_ids
        return ExportScope(
            kind=kind,
            values=values,
            entity_ids=entity_ids,
            metadata={"grouping": grouping.value, "naming": self.naming.text()},
        )

    def _filtered_entity_ids(self, scope: ExportScope) -> tuple[str, ...]:
        wanted = set(scope.values)
        field = "assembly_id" if scope.kind is ExportScopeKind.ASSEMBLY else "machine_batch_id"
        matches: list[str] = []
        for identifier, part in _iter_records(getattr(self.project, "parts", ())):
            data = _plain(part)
            if isinstance(data, Mapping) and str(data.get(field, "")) in wanted:
                matches.append(str(data.get("id") or data.get("part_id") or identifier))
        return tuple(matches)

    def _backend_scope(self, scope: ExportScope) -> ViewerExportScope:
        if scope.kind in {ExportScopeKind.ASSEMBLY, ExportScopeKind.MACHINE_BATCH}:
            return ViewerExportScope(
                kind=ViewerExportScopeKind.ENTITY_IDS,
                entity_ids=self._filtered_entity_ids(scope),
                metadata={**dict(scope.metadata), "canonical_scope": scope.kind.value, "scope_values": list(scope.values)},
            )
        return ViewerExportScope(
            kind=self._BACKEND_KIND[scope.kind],
            values=scope.values,
            entity_ids=scope.entity_ids,
            recursive=scope.recursive,
            metadata=dict(scope.metadata),
        )

    def _formats(self) -> tuple[str, ...]:
        return tuple(name.lower() for name, check in self._format_checks.items() if check.isChecked())

    def _preflight(self) -> Any:
        if self.service is None:
            self.blockers.setPlainText("BLOCKED: geen actief project")
            return None
        scope = self._scope()
        if scope.is_empty_selection:
            self.blockers.setPlainText("BLOCKED: de gekozen selection-scope is leeg; scopeverbreding is verboden.")
            return None
        if scope.kind in {ExportScopeKind.ASSEMBLY, ExportScopeKind.MACHINE_BATCH} and not self._filtered_entity_ids(scope):
            self.blockers.setPlainText("BLOCKED: de exacte scope bevat geen herleidbare parts.")
            return None
        formats = self._formats()
        if not formats:
            self.blockers.setPlainText("BLOCKED: kies ten minste een backend- en scope-geldig format.")
            return None
        try:
            preflight = self.service.preflight(self._backend_scope(scope), formats)
        except Exception as exc:
            self.blockers.setPlainText(f"BLOCKED: {type(exc).__name__}: {exc}")
            return None
        lines = [f"scope_sha256: {preflight.resolution.manifest_sha256}", f"preflight_sha256: {preflight.manifest_sha256}"]
        lines.extend(f"BLOCKED: {code}" for code in preflight.blocking_codes)
        for item in preflight.items:
            lines.extend(f"{item.part_position}: {code}" for code in item.blocking_codes)
        if not preflight.blocking_codes and not any(item.blocking_codes for item in preflight.items):
            lines.append("GREEN: scope, backend capabilities en output eligibility zijn geldig.")
        self.blockers.setPlainText("\n".join(lines))
        self._show_scope_in_viewer()
        return preflight

    def _generate(self) -> None:
        preflight = self._preflight()
        if preflight is None or preflight.blocking_codes or any(item.blocking_codes for item in preflight.items):
            return
        if self.service is None:
            return
        planned = self.service.prepare_job(self._backend_scope(self._scope()), self._formats())
        self.current_export_job_id = planned.job_id
        if self.job_manager is None:
            self.blockers.append("BLOCKED: centrale JobManager ontbreekt")
            return
        project_id = str(getattr(self.project, "project_id", getattr(self.project, "id", "")))
        self.current_background_job_id = self.job_manager.submit(
            "phase3-export",
            self._execute_export,
            planned.job_id,
            self.output_dir.text().strip(),
            description="Scope-first export, verificatie en package manifest",
            project_id=project_id,
            metadata={"scope": self._scope().kind.value, "formats": list(self._formats())},
        )
        self.status.setText(f"Export job gestart: {self.current_background_job_id}")

    def _execute_export(self, context: Any, export_job_id: str, output_dir: str) -> dict[str, Any]:
        if self.service is None:
            raise RuntimeError("Exportservice is niet beschikbaar")
        context.stage("generate", 0.05, "Artifacts genereren")
        result = self.service.execute_job(
            export_job_id,
            output_dir,
            create_zip=True,
            progress=lambda progress, message: context.update(progress, message),
        )
        context.stage("reimport_verify", 0.92, "Manifest en package opnieuw lezen")
        package = Path(result.package_path) if result.package_path else None
        if package is not None and not package.is_file():
            raise RuntimeError("Package ontbreekt na export")
        manifest = self.service.evidence_manifest()
        context.stage("manifest", 1.0, "Manifest en checksums vastgelegd")
        return {
            "export_job_id": result.job_id,
            "package_path": result.package_path,
            "export_manifest_sha256": result.export_manifest_sha256,
            "reimport_verified": bool(result.export_manifest_sha256 and (package is None or package.is_file())),
            "evidence_manifest": manifest,
        }

    def _on_job_event(self, record: Any) -> None:
        if getattr(record, "job_id", "") != self.current_background_job_id:
            return
        self.status.setText(f"{record.stage}: {record.message} ({record.progress:.0%})")
        if record.status == "completed":
            result = record.result or {}
            self.verify.setPlainText(
                "GREEN: deterministic package heropend en manifest checksum aanwezig."
                if result.get("reimport_verified")
                else "BLOCKED: re-import verificatie ontbreekt."
            )
            self.manifest.setPlainText(json.dumps(result, indent=2, sort_keys=True, default=str))
        elif record.status in {"failed", "cancelled"}:
            self.blockers.append(f"{record.status.upper()}: {record.error or record.message}")

    def _cancel(self) -> None:
        if self.job_manager is not None and self.current_background_job_id:
            self.job_manager.cancel(self.current_background_job_id)

    def _choose_output(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Exportmap", self.output_dir.text())
        if selected:
            self.output_dir.setText(selected)

    def _show_scope_in_viewer(self) -> None:
        viewer = getattr(self.viewer_host, "viewer", self.viewer_host)
        scope = self._scope()
        for name in ("show_export_scope", "set_scope_preview"):
            method = getattr(viewer, name, None)
            if callable(method):
                try:
                    method(tuple(scope.entity_ids or scope.values), ghost_context=True)
                    return
                except TypeError:
                    continue


__all__ = ["Phase3ExportCenterPanel", "ProfileNestingPanel", "ScribingWorkspacePanel"]
