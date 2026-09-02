"""Canonical BOM production hub with shared selection and Viewer projection."""
from __future__ import annotations

import os
import re
import hashlib
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
from cws_convertor.bom.production_hub import (
    BOMBatchPreflight,
    BOMHubState,
    BOMScopeEngine,
    SELECTION_BASES,
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

    class _BomViewerStateBridge(QtCore.QObject):
        """Synchronise camera, visibility, clipping and colour for one project scene."""

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self._viewers: list[Any] = []
            self._subscriptions: dict[int, list[Any]] = {}
            self._syncing = False

        def register(self, viewer: Any) -> None:
            if viewer is None or viewer in self._viewers:
                return
            self._viewers.append(viewer)
            subscriptions: list[Any] = []
            try:
                from cws_viewer.contracts.events import (
                    CameraChanged, DisplayPreferencesChanged, SectionChanged,
                    StyleChanged, VisibilityChanged, WorkspaceChanged,
                )
                for event_type in (
                    CameraChanged, DisplayPreferencesChanged, SectionChanged,
                    StyleChanged, VisibilityChanged, WorkspaceChanged,
                ):
                    subscriptions.append(
                        viewer.controller.subscribe(event_type, lambda _event, source=viewer: self.publish(source))
                    )
            except Exception:
                subscriptions = []
            self._subscriptions[id(viewer)] = subscriptions
            if len(self._viewers) > 1:
                self.publish(self._viewers[0])

        def unregister(self, viewer: Any) -> None:
            if viewer in self._viewers:
                self._viewers.remove(viewer)
            for subscription in self._subscriptions.pop(id(viewer), []):
                try:
                    subscription.close()
                except Exception:
                    pass

        def publish(self, source: Any) -> None:
            if self._syncing or source not in self._viewers:
                return
            try:
                state = source.controller.export_workspace_state()
            except Exception:
                return
            self._syncing = True
            try:
                for target in tuple(self._viewers):
                    if target is source:
                        continue
                    try:
                        target.controller.restore_workspace_state(state)
                    except Exception:
                        continue
            finally:
                self._syncing = False

    class _BomViewerPane(QtWidgets.QFrame):
        """Lazy secondary renderer over the active workspace scene/cache."""

        selection_requested = QtCore.Signal(object)

        def __init__(self, parent: Any | None = None, *, state_bridge: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("bomViewerPane")
            self._workspace: Any | None = None
            self._selection: Any | None = None
            self._viewer: Any | None = None
            self._nodes_by_entity: dict[str, tuple[str, ...]] = {}
            self._state_bridge = state_bridge
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
                ("Kader", self.area_selection),
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
                if self._state_bridge is not None:
                    self._state_bridge.register(viewer)
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
                if self._state_bridge is not None:
                    self._state_bridge.unregister(viewer)
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

        def area_selection(self) -> None:
            if self._viewer is not None and hasattr(self._viewer, "set_area_selection"):
                self._viewer.set_area_selection(True)
                self._viewer.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)

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

        def apply_color_mode(
            self,
            mode: str,
            model: BOMWorkspaceReadModel | None,
            revisions: dict[str, str],
        ) -> None:
            if self._viewer is None or model is None:
                return
            from cws_viewer.contracts.enums import ColorScheme
            from cws_viewer.contracts.state import ColorAssignment
            from cws_viewer.math3d import Rgba
            from cws_viewer.core.color_schemes import ProjectColorizer
            controller = self._viewer.controller
            standard = {
                "Origineel": ColorScheme.ORIGINAL,
                "Materiaal": ColorScheme.MATERIAL,
                "Profiel": ColorScheme.PROFILE,
                "Assembly": ColorScheme.ASSEMBLY,
                "Fase": ColorScheme.PHASE,
                "Status": ColorScheme.STATUS,
            }
            controller.clear_colors()
            if mode in standard:
                scheme = standard[mode]
                if scheme != ColorScheme.ORIGINAL:
                    controller.colorize(ProjectColorizer(self._workspace.project, controller.index).assignments(scheme))
                controller.set_color_scheme(scheme)
            else:
                row_by_entity = {
                    entity_id: row
                    for family in BOM_FAMILIES
                    for row in model.family_rows(family)
                    for entity_id in row.entity_ids
                }
                def stable_colour(value: str) -> Rgba:
                    digest = hashlib.sha256(value.casefold().encode("utf-8")).digest()
                    return Rgba(0.18 + digest[0] / 510, 0.30 + digest[1] / 638, 0.28 + digest[2] / 638, 1.0)
                def state_colour(value: str, *, blocked: bool = False) -> Rgba:
                    key = str(value or "").casefold()
                    if blocked or any(token in key for token in ("block", "conflict", "error", "afkeur", "tekort")):
                        return Rgba(0.90, 0.28, 0.30, 1.0)
                    if any(token in key for token in ("ready", "gereed", "approved", "released", "vrijgegeven", "complete", "geleverd")):
                        return Rgba(0.18, 0.72, 0.42, 1.0)
                    if any(token in key for token in ("progress", "review", "pending", "wacht", "concept", "open")):
                        return Rgba(0.95, 0.63, 0.18, 1.0)
                    return Rgba(0.55, 0.59, 0.64, 1.0)
                assignments = []
                for node_id in controller.index.renderable_node_ids:
                    row = row_by_entity.get(controller.index.node(node_id).entity_id)
                    if row is None:
                        colour = Rgba(0.55, 0.59, 0.64, 1.0)
                    elif mode == "Machine":
                        colour = stable_colour(row.machine or "Geen machine")
                    elif mode == "Machinewijze":
                        key = row.machine.casefold()
                        colour = (
                            Rgba(0.45, 0.32, 0.82, 1.0) if "manual" in key or "handmatig" in key
                            else Rgba(0.16, 0.58, 0.82, 1.0) if "auto" in key
                            else Rgba(0.55, 0.59, 0.64, 1.0)
                        )
                    elif mode == "Tekening":
                        colour = state_colour(row.document_status, blocked=row.blocked)
                    elif mode == "Nesting":
                        colour = state_colour(row.nesting_status, blocked=row.blocked)
                    elif mode == "Productie":
                        colour = state_colour(row.production_status, blocked=row.blocked)
                    elif mode == "Vrijgave":
                        colour = state_colour(row.release_status, blocked=row.blocked)
                    elif mode == "Blockers":
                        colour = (
                            Rgba(0.90, 0.28, 0.30, 1.0) if row.blocked
                            else Rgba(0.18, 0.72, 0.42, 1.0)
                        )
                    else:
                        revision = revisions.get(row.group_id, "geen baseline")
                        colour = {
                            "toegevoegd": Rgba(0.18, 0.72, 0.42, 1.0),
                            "gewijzigd": Rgba(0.95, 0.55, 0.16, 1.0),
                            "ongewijzigd": Rgba(0.55, 0.59, 0.64, 1.0),
                        }.get(revision, Rgba(0.45, 0.55, 0.72, 1.0))
                    assignments.append(ColorAssignment(node_id=node_id, color=colour))
                controller.colorize(assignments)
                controller.set_color_scheme(ColorScheme.ORIGINAL)
            if self._state_bridge is not None:
                self._state_bridge.publish(self._viewer)

        def closeEvent(self, event: Any) -> None:
            self._dispose_viewer()
            super().closeEvent(event)


    class BomWorkspacePanel(QtWidgets.QWidget):
        """BOM production hub over the canonical snapshot and stable-ID bus."""

        action_requested = QtCore.Signal(str)
        show_project_requested = QtCore.Signal()
        COLUMNS = (
            "✓", "Merk / sleutel", "Omschrijving", "Profiel / maat", "Materiaal",
            "Lengte (mm)", "Aantal", "Gewicht (kg)", "Oppervlakte (m²)",
            "Machine", "Tekening", "Fase", "Levering", "Vrijgave", "Nesting",
            "Productie", "Voorraad", "Revisie", "Status",
        )

        def __init__(
            self,
            window: Any,
            parent: Any | None = None,
            *,
            allow_detach: bool = True,
            viewer_bridge: Any | None = None,
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
            self._viewer_bridge = viewer_bridge or _BomViewerStateBridge(self)
            self._hub_state: BOMHubState | None = None
            self._scope_engine: BOMScopeEngine | None = None
            self._revision_statuses: dict[str, str] = {}
            self._checked_group_ids: set[str] = set()
            self._group_header_rows: dict[int, tuple[BOMWorkspaceRow, ...]] = {}
            self._main_viewer_registered: Any | None = None
            self._preflight_partition_mode = "eligible"
            self._restored_phase = ""
            self._restored_delivery = ""

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
            self.viewer = _BomViewerPane(state_bridge=self._viewer_bridge)
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
            self.group_by.addItems((
                "Niet groeperen", "Merk", "Profiel", "Materiaal", "Machine",
                "Fase", "Levering", "Status",
            ))
            self.group_by.currentIndexChanged.connect(self.refresh)
            self.status_filter = QtWidgets.QComboBox()
            self.status_filter.addItems(("Alle statussen", "Gereed", "Review", "Geblokkeerd"))
            self.status_filter.currentIndexChanged.connect(self.refresh)
            self.phase_filter = QtWidgets.QComboBox()
            self.phase_filter.addItem("Alle fasen", "")
            self.phase_filter.currentIndexChanged.connect(self.refresh)
            self.delivery_filter = QtWidgets.QComboBox()
            self.delivery_filter.addItem("Alle leveringen", "")
            self.delivery_filter.currentIndexChanged.connect(self.refresh)
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
            layout.addWidget(self.phase_filter)
            layout.addWidget(self.delivery_filter)
            layout.addWidget(self.search, 1)
            layout.addWidget(columns)
            layout.addWidget(export)
            selection_tools = QtWidgets.QToolButton()
            selection_tools.setText("Selectie-tools")
            selection_tools.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            self.selection_tools_menu = QtWidgets.QMenu(selection_tools)
            for basis, label in (
                ("group", "Zelfde BOM-groep"), ("profile", "Zelfde profiel"),
                ("material", "Zelfde materiaal"), ("machine", "Zelfde machine"),
                ("status", "Zelfde status"), ("phase", "Zelfde fase"),
                ("delivery", "Zelfde levering"),
            ):
                self.selection_tools_menu.addAction(label, lambda _checked=False, key=basis: self._select_matching(key))
            self.selection_tools_menu.addSeparator()
            smart = self.selection_tools_menu.addMenu("Slimme selecties")
            smart.addAction("Geblokkeerde regels", lambda: self._select_smart("blocked"))
            smart.addAction("Zonder tekening", lambda: self._select_smart("drawing_missing"))
            smart.addAction("Zonder materiaal", lambda: self._select_smart("material_missing"))
            smart.addAction("Handmatige machinekeuze", lambda: self._select_smart("manual_machine"))
            smart.addAction("Nog niet vrijgegeven", lambda: self._select_smart("not_released"))
            self.selection_tools_menu.addSeparator()
            self.selection_tools_menu.addAction("Aan selectiemandje toevoegen", self._basket_add)
            self.selection_tools_menu.addAction("Selectiemandje gebruiken", self._basket_select)
            self.selection_tools_menu.addAction("Selectiemandje leegmaken", self._basket_clear)
            self.selection_tools_menu.addSeparator()
            self.selection_tools_menu.addAction("Selectieset opslaan", self._save_selection_set)
            self.saved_selection_menu = self.selection_tools_menu.addMenu("Opgeslagen selecties")
            self.selection_tools_menu.aboutToShow.connect(self._refresh_saved_selection_menu)
            selection_tools.setMenu(self.selection_tools_menu)
            layout.addWidget(selection_tools)
            self.color_mode = QtWidgets.QComboBox()
            self.color_mode.addItems((
                "Origineel", "Materiaal", "Profiel", "Assembly", "Fase",
                "Machine", "Machinewijze", "Tekening", "Nesting", "Productie",
                "Vrijgave", "Blockers", "Revisie",
            ))
            self.color_mode.currentIndexChanged.connect(self._apply_color_mode)
            layout.addWidget(self.color_mode)
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
                ("edit", "Bewerken", self._edit_selection),
                ("drawing", "Tekening", lambda: self._route_scoped_action("drawing", "drawings")),
                ("machine", "Machine", self._assign_machine),
                ("optimize", "Optimaliseren", lambda: self._route_scoped_action("optimize", "optimize")),
                ("isolate", "Isoleren", self._isolate_selection),
                ("export", "Exporteren", self._export_scope),
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
            self.more_actions["release"] = menu.addAction(
                "Vrijgeven voor productie", self._open_production_workflow
            )
            menu.addSeparator()
            menu.addAction("Selecteer alle zichtbare regels", self._select_visible)
            menu.addAction("Wis selectie", self._clear_selection)
            menu.addSeparator()
            menu.addAction("Machine-indeling resetten", self._reset_machine)
            menu.addAction("BOM-package exporteren", self._export_scope)
            menu.addAction("Productie-export (NC1 / STEP / IFC / DXF / PDF)", lambda: self._route_scoped_action("production_export", "export"))
            menu.addSeparator()
            menu.addAction("Revisiebaseline opslaan", self._save_revision_baseline)
            menu.addAction("Laatste BOM-batchactie ongedaan maken", self._undo_last_batch)
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
            self.table.itemChanged.connect(self._checkbox_changed)
            self.table.itemDoubleClicked.connect(lambda _item: self._zoom_selection())
            self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self._show_table_menu)
            layout.addWidget(self.table, 1)
            self.detail_tabs = QtWidgets.QTabWidget()
            self.detail_tabs.setObjectName("bomDetailTabs")
            self.detail_labels: dict[str, Any] = {}
            for key, label in (
                ("properties", "Eigenschappen"), ("production", "Productie"),
                ("machine", "Machine"), ("drawing", "Tekening"),
                ("traceability", "Traceability"), ("conflicts", "Conflicten"),
                ("revision", "Revisie"), ("history", "Historie"),
            ):
                page = QtWidgets.QWidget()
                page_layout = QtWidgets.QVBoxLayout(page)
                value = QtWidgets.QLabel("Selecteer een of meer BOM-regels.")
                value.setObjectName("mutedText")
                value.setWordWrap(True)
                value.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
                page_layout.addWidget(value)
                page_layout.addStretch(1)
                self.detail_labels[key] = value
                self.detail_tabs.addTab(page, label)
            self.detail = self.detail_labels["properties"]
            self.detail_tabs.setMaximumHeight(190)
            layout.addWidget(self.detail_tabs)
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
                self._hub_state = BOMHubState(workspace.project) if workspace is not None else None
                self.refresh()
            else:
                self._select_context_rows()
            self.viewer.set_context(workspace, selection)
            QtCore.QTimer.singleShot(0, self._apply_color_mode)
            main_viewer = getattr(getattr(self.window, "project_page", None), "viewer", None)
            if main_viewer is not self._main_viewer_registered:
                if self._main_viewer_registered is not None:
                    self._viewer_bridge.unregister(self._main_viewer_registered)
                self._main_viewer_registered = main_viewer
                if main_viewer is not None:
                    self._viewer_bridge.register(main_viewer)
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
            self._group_header_rows.clear()
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
                self._scope_engine = BOMScopeEngine(self._read_model)
                self._revision_statuses = self._hub_state.revision_statuses(self._read_model) if self._hub_state else {}
                self._refresh_scope_filter_values()
                for index, family in enumerate(BOM_FAMILIES):
                    label = BOM_FAMILY_LABELS[family]
                    self.family_tabs.setTabText(
                        index,
                        f"{label} ({self._read_model.family_count(family)})",
                    )
                rows = self._read_model.rows(self._scope())
                phase = str(self.phase_filter.currentData() or "")
                delivery = str(self.delivery_filter.currentData() or "")
                if phase:
                    rows = tuple(row for row in rows if row.phase == phase)
                if delivery:
                    rows = tuple(row for row in rows if row.delivery == delivery)
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
                        header_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
                        self.table.setItem(table_row, 1, header_item)
                        self.table.setItem(table_row, 6, QtWidgets.QTableWidgetItem(_number(sum(row.quantity for row in group_rows), 0)))
                        self.table.setItem(table_row, 7, QtWidgets.QTableWidgetItem(_number(sum(row.total_mass_kg for row in group_rows))))
                        self._group_header_rows[table_row] = group_rows
                        table_row += 1
                    for row in group_rows:
                        self.table.insertRow(table_row)
                        self._display_rows[table_row] = row
                        values = (
                            "",
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
                            row.phase or "-",
                            row.delivery or "-",
                            row.release_status or "-",
                            row.nesting_status or "-",
                            row.production_status or "-",
                            row.stock_status or "-",
                            self._revision_statuses.get(row.group_id, "geen baseline"),
                            "GEBLOKKEERD" if row.blocked else row.status.upper(),
                        )
                        for column, value in enumerate(values):
                            item = QtWidgets.QTableWidgetItem(str(value))
                            if column == 0:
                                item.setFlags(
                                    QtCore.Qt.ItemFlag.ItemIsEnabled
                                    | QtCore.Qt.ItemFlag.ItemIsSelectable
                                    | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                                )
                                item.setCheckState(
                                    QtCore.Qt.CheckState.Checked
                                    if row.group_id in self._checked_group_ids
                                    else QtCore.Qt.CheckState.Unchecked
                                )
                            item.setData(QtCore.Qt.ItemDataRole.UserRole, row.group_id)
                            item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, list(row.entity_ids))
                            if row.blocked:
                                item.setToolTip("\n".join(row.blocking_reasons) or "Geblokkeerd")
                            if column == 16:
                                item.setToolTip(
                                    f"Beschikbaar: {_number(row.available_stock_mm, 0)} mm\n"
                                    f"Tekort: {_number(row.shortage_mm, 0)} mm"
                                )
                                if row.shortage_mm > 0.001:
                                    item.setBackground(QtGui.QColor("#fde7e9"))
                            if column == 17:
                                revision = self._revision_statuses.get(row.group_id, "")
                                colour = {
                                    "toegevoegd": "#dff4e8", "gewijzigd": "#fff0d5",
                                    "ongewijzigd": "#eef1f4",
                                }.get(revision)
                                if colour:
                                    item.setBackground(QtGui.QColor(colour))
                            if column == 18 and row.blocked:
                                item.setBackground(QtGui.QColor("#fde7e9"))
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
                "Fase": lambda row: row.phase or "Zonder fase",
                "Levering": lambda row: row.delivery or "Zonder levering",
                "Status": lambda row: "Geblokkeerd" if row.blocked else row.status,
            }[mode]
            grouped: dict[str, list[BOMWorkspaceRow]] = defaultdict(list)
            for row in rows:
                grouped[str(getter(row))].append(row)
            return tuple(
                (label, tuple(grouped[label])) for label in sorted(grouped, key=str.casefold)
            )

        def _refresh_scope_filter_values(self) -> None:
            if self._read_model is None:
                return
            rows = self._read_model.family_rows(self._family())
            for combo, placeholder, attribute in (
                (self.phase_filter, "Alle fasen", "phase"),
                (self.delivery_filter, "Alle leveringen", "delivery"),
            ):
                restored = self._restored_phase if attribute == "phase" else self._restored_delivery
                current = str(combo.currentData() or restored or "")
                values = sorted({
                    str(getattr(row, attribute, "") or "").strip()
                    for row in rows
                    if str(getattr(row, attribute, "") or "").strip() not in {"", "-"}
                }, key=str.casefold)
                combo.blockSignals(True)
                combo.clear()
                combo.addItem(placeholder, "")
                for value in values:
                    combo.addItem(value, value)
                found = combo.findData(current)
                combo.setCurrentIndex(found if found >= 0 else 0)
                combo.blockSignals(False)
                if attribute == "phase":
                    self._restored_phase = ""
                else:
                    self._restored_delivery = ""

        def _select_rows(self, rows: Iterable[BOMWorkspaceRow]) -> None:
            requested = {row.group_id for row in rows}
            self._syncing = True
            try:
                self.table.clearSelection()
                flags = (
                    QtCore.QItemSelectionModel.SelectionFlag.Select
                    | QtCore.QItemSelectionModel.SelectionFlag.Rows
                )
                for table_row, row in self._display_rows.items():
                    if row.group_id in requested:
                        item = self.table.item(table_row, 0)
                        if item is not None:
                            self.table.selectionModel().select(self.table.indexFromItem(item), flags)
            finally:
                self._syncing = False
            self._sync_checkboxes(self._selected_rows())
            self._table_selection_changed()

        def _select_matching(self, basis: str) -> None:
            if self._scope_engine is None:
                return
            try:
                rows = self._scope_engine.matching(self._selected_rows(), basis)
            except ValueError as exc:
                QtWidgets.QMessageBox.information(self, "Slimme selectie", str(exc))
                return
            self._select_rows(rows)

        def _select_smart(self, kind: str) -> None:
            if self._read_model is None:
                return
            rows = self._read_model.family_rows(self._family())
            predicates = {
                "blocked": lambda row: row.blocked,
                "drawing_missing": lambda row: row.document_status in {"", "-", "unknown", "review_required"},
                "material_missing": lambda row: row.material in {"", "-", "unknown", "onbekend"},
                "manual_machine": lambda row: "manual" in row.machine.casefold(),
                "not_released": lambda row: row.release_status.casefold() not in {"released", "vrijgegeven", "approved"},
            }
            self._select_rows(row for row in rows if predicates[kind](row))

        def _basket_add(self) -> None:
            if self._hub_state is None:
                return
            ids = tuple(entity_id for row in self._selected_rows() for entity_id in row.entity_ids)
            if ids:
                result = self._hub_state.add_to_basket(ids)
                self._mark_project_dirty()
                self.status.setText(f"Selectiemandje bevat {len(result)} canonieke objecten")

        def _basket_select(self) -> None:
            if self._hub_state is None or self._read_model is None:
                return
            ids = set(self._hub_state.basket())
            rows = tuple(
                row for row in self._read_model.family_rows(self._family())
                if ids.intersection(row.entity_ids)
            )
            self._select_rows(rows)

        def _basket_clear(self) -> None:
            if self._hub_state is not None:
                self._hub_state.clear_basket()
                self._mark_project_dirty()
                self.status.setText("Selectiemandje is leeggemaakt")

        def _save_selection_set(self) -> None:
            if self._hub_state is None or self._workspace is None:
                return
            rows = self._selected_rows()
            if not rows:
                QtWidgets.QMessageBox.information(self, "Selectieset", "Selecteer eerst een of meer regels.")
                return
            name, accepted = QtWidgets.QInputDialog.getText(self, "Selectieset opslaan", "Naam:")
            if not accepted or not name.strip():
                return
            dynamic, accepted = QtWidgets.QInputDialog.getItem(
                self, "Selectiesettype", "Automatisch bijwerken op:",
                ("Vaste objecten", "BOM-groep", "Profiel", "Materiaal", "Machine", "Status", "Fase", "Levering"),
                0, False,
            )
            if not accepted:
                return
            basis = {
                "Vaste objecten": "", "BOM-groep": "group", "Profiel": "profile",
                "Materiaal": "material", "Machine": "machine", "Status": "status",
                "Fase": "phase", "Levering": "delivery",
            }[dynamic]
            self._hub_state.save_selection(
                name, rows, snapshot_sha256=self._workspace.bom_snapshot.snapshot_sha256,
                dynamic_basis=basis,
            )
            self._mark_project_dirty()

        def _refresh_saved_selection_menu(self) -> None:
            self.saved_selection_menu.clear()
            if self._hub_state is None or self._scope_engine is None:
                self.saved_selection_menu.setEnabled(False)
                return
            selections = self._hub_state.saved_selections()
            self.saved_selection_menu.setEnabled(bool(selections))
            for saved in selections:
                entry = self.saved_selection_menu.addMenu(saved.name)
                action = entry.addAction("Toepassen")
                action.triggered.connect(
                    lambda _checked=False, item=saved: self._select_rows(self._scope_engine.resolve_saved(item))
                )
                remove = entry.addAction("Verwijderen")
                remove.triggered.connect(
                    lambda _checked=False, item=saved: self._delete_saved_selection(item.selection_id)
                )

        def _delete_saved_selection(self, selection_id: str) -> None:
            if self._hub_state is None:
                return
            self._hub_state.delete_selection(selection_id)
            self._mark_project_dirty()

        def _selected_rows(self) -> tuple[BOMWorkspaceRow, ...]:
            rows = []
            for index in self.table.selectionModel().selectedRows() if self.table.selectionModel() else ():
                row = self._display_rows.get(index.row())
                candidates = (row,) if row is not None else self._group_header_rows.get(index.row(), ())
                for candidate in candidates:
                    if candidate is not None and candidate not in rows:
                        rows.append(candidate)
            return tuple(rows)

        def _checkbox_changed(self, item: Any) -> None:
            if self._syncing or item.column() != 0:
                return
            row = self._display_rows.get(item.row())
            if row is None:
                return
            checked = item.checkState() == QtCore.Qt.CheckState.Checked
            if checked:
                self._checked_group_ids.add(row.group_id)
            else:
                self._checked_group_ids.discard(row.group_id)
            flags = (
                QtCore.QItemSelectionModel.SelectionFlag.Select
                if checked else QtCore.QItemSelectionModel.SelectionFlag.Deselect
            ) | QtCore.QItemSelectionModel.SelectionFlag.Rows
            self.table.selectionModel().select(self.table.indexFromItem(item), flags)
            self._table_selection_changed()

        def _sync_checkboxes(self, rows: Iterable[BOMWorkspaceRow]) -> None:
            selected = {row.group_id for row in rows}
            self._checked_group_ids = selected
            self._syncing = True
            try:
                for table_row, row in self._display_rows.items():
                    item = self.table.item(table_row, 0)
                    if item is not None:
                        item.setCheckState(
                            QtCore.Qt.CheckState.Checked if row.group_id in selected
                            else QtCore.Qt.CheckState.Unchecked
                        )
            finally:
                self._syncing = False

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
            self._sync_checkboxes(rows)
            entity_ids = tuple(dict.fromkeys(
                entity_id for row in rows for entity_id in row.entity_ids
            ))
            self.window.application_context.request_selection(
                entity_ids,
                primary_entity_id=(entity_ids[0] if entity_ids else None),
                origin="bom",
            )
            update_review = getattr(self.window.application_context, "update_review_context", None)
            if callable(update_review):
                update_review(
                    active_bom_row=(rows[0].group_id if rows else ""),
                    active_bom_rows=tuple(row.group_id for row in rows),
                )
            self._update_actions()

        def _viewer_selection_requested(self, entity_ids: Iterable[str]) -> None:
            if self._workspace is not None:
                values = tuple(dict.fromkeys(str(value) for value in entity_ids if str(value)))
                values = self._resolve_viewer_scope(values)
                family = self._family_for_entities(values)
                if family and family != self._family():
                    index = BOM_FAMILIES.index(family)
                    self.family_tabs.setCurrentIndex(index)
                self.window.application_context.request_selection(
                    values, origin="bom_viewer"
                )

        def _family_for_entities(self, entity_ids: Iterable[str]) -> str:
            if self._read_model is None:
                return ""
            values = set(entity_ids)
            for family in ("parts", "assemblies", "purchase", "fasteners", "welds", "materials", "conflicts"):
                if any(values.intersection(row.entity_ids) for row in self._read_model.family_rows(family)):
                    return family
            return ""

        def _resolve_viewer_scope(self, entity_ids: tuple[str, ...]) -> tuple[str, ...]:
            if len(entity_ids) != 1 or self._read_model is None or self._workspace is None:
                return entity_ids
            entity_id = entity_ids[0]
            row = next((
                row for family in BOM_FAMILIES for row in self._read_model.family_rows(family)
                if entity_id in row.entity_ids
            ), None)
            if row is None or (len(row.entity_ids) <= 1 and entity_id not in self._workspace.project.parts):
                return entity_ids
            part = self._workspace.project.parts.get(entity_id)
            assembly_ids = tuple(getattr(part, "assembly_ids", ()) or ()) if part is not None else ()
            options = ["Alleen deze occurrence", f"Hele BOM-groep ({len(row.entity_ids)})"]
            if assembly_ids:
                options.append(f"Gehele assembly ({len(assembly_ids)})")
            if row.profile or row.material:
                options.append("Alle vergelijkbare onderdelen")
            if os.environ.get("CWS_HEADLESS_GUI_SMOKE") == "1":
                return entity_ids
            selected, accepted = QtWidgets.QInputDialog.getItem(
                self, "Selectiescope", f"{entity_id} behoort tot BOM-groep {row.group_id}.\nActie toepassen op:",
                tuple(options), 0, False,
            )
            if not accepted or selected == "Alleen deze occurrence":
                return entity_ids
            if selected.startswith("Hele BOM-groep"):
                return row.entity_ids
            if selected.startswith("Gehele assembly"):
                result = []
                for assembly_id in assembly_ids:
                    assembly = self._workspace.project.assemblies.get(assembly_id)
                    if assembly is not None:
                        result.extend(getattr(assembly, "part_ids", ()) or ())
                return tuple(dict.fromkeys(result)) or entity_ids
            similar = tuple(
                entity
                for candidate in self._read_model.family_rows(row.family)
                if candidate.profile == row.profile and candidate.material == row.material
                for entity in candidate.entity_ids
            )
            return tuple(dict.fromkeys(similar)) or entity_ids

        def _apply_color_mode(self) -> None:
            mode = self.color_mode.currentText()
            self._settings.setValue("bom/color_mode", mode)
            self.viewer.apply_color_mode(mode, self._read_model, self._revision_statuses)
            for detached in tuple(self._detached_windows):
                pane = getattr(detached, "_cws_viewer_pane", None)
                if pane is not None:
                    pane.apply_color_mode(mode, self._read_model, self._revision_statuses)

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
                for label in self.detail_labels.values():
                    label.setText("Selecteer een of meer BOM-regels.")
                return
            impact = self._scope_engine.impact(rows, visible_rows=self._visible_rows) if self._scope_engine else None
            externally_selected = set(tuple(getattr(self._selection, "entity_ids", ()) or ()))
            visible_entities = {entity_id for row in self._visible_rows for entity_id in row.entity_ids}
            hidden_count = len(externally_selected - visible_entities)
            self.selection_label.setText(
                f"{summary.group_count} regels · {summary.entity_count} occurrences · "
                f"{summary.assembly_count} assemblies · {_number(summary.quantity, 0)} stuks · "
                f"{_number(summary.total_mass_kg)} kg · {summary.blocked_count} blokkeringen"
                + (f" · {hidden_count} verborgen geselecteerd" if hidden_count else "")
            )
            blockers = tuple(dict.fromkeys(
                reason for row in rows for reason in row.blocking_reasons
            ))
            families = ", ".join(sorted({BOM_FAMILY_LABELS[row.family] for row in rows}))
            self.detail.setText(
                f"Families: {families}\n"
                f"Groepen: {', '.join(row.group_id for row in rows[:8])}"
            )
            self._update_detail_tabs(rows, blockers, impact)

        def _update_detail_tabs(
            self,
            rows: tuple[BOMWorkspaceRow, ...],
            blockers: tuple[str, ...],
            impact: Any | None,
        ) -> None:
            mixed = lambda attribute: ", ".join(dict.fromkeys(
                str(getattr(row, attribute, "") or "-") for row in rows
            ))
            self.detail_labels["properties"].setText(
                f"Profiel/maat: {mixed('profile')} · Materiaal: {mixed('material')}\n"
                f"Fase: {mixed('phase')} · Levering: {mixed('delivery')}\n"
                f"Voorraad: {_number(sum(row.available_stock_mm for row in rows), 0)} mm · "
                f"Tekort: {_number(sum(row.shortage_mm for row in rows), 0)} mm · "
                f"Leverancier: {mixed('supplier')}\n"
                f"Inkoopstatus: {mixed('purchase_status')} · Levertijd: "
                f"{max((row.lead_time_days for row in rows), default=0)} dagen · "
                f"Totale prijs: € {_number(sum(row.total_price for row in rows), 2)}"
            )
            self.detail_labels["production"].setText(
                f"Productiestatus: {mixed('production_status')}\n"
                f"Vrijgave: {mixed('release_status')}\nNesting: {mixed('nesting_status')}"
            )
            machine_lines = [
                f"{machine}: {len(ids)} occurrences"
                for machine, ids in (impact.machine_partitions if impact else ())
            ]
            self.detail_labels["machine"].setText("\n".join(machine_lines) or "Geen machine-indeling.")
            self.detail_labels["drawing"].setText(
                f"Tekeningstatus: {mixed('document_status')}\nDubbelklik een regel om in de Viewer te zoomen."
            )
            trace_count = sum(len(row.entity_ids) for row in rows)
            self.detail_labels["traceability"].setText(
                f"{trace_count} gekoppelde canonieke IDs\nSnapshot: "
                f"{self._workspace.bom_snapshot.snapshot_sha256 if self._workspace else '-'}"
            )
            self.detail_labels["conflicts"].setText(
                "\n".join(blockers) if blockers else "Geen blockers in de geselecteerde regels."
            )
            revisions = {self._revision_statuses.get(row.group_id, "geen baseline") for row in rows}
            removed = sum(1 for value in self._revision_statuses.values() if value == "verwijderd")
            self.detail_labels["revision"].setText(
                "Revisiestatus: " + ", ".join(sorted(revisions))
                + (f"\n{removed} groepen verwijderd sinds baseline" if removed else "")
            )
            events = []
            if self._workspace is not None:
                selected_ids = {entity_id for row in rows for entity_id in row.entity_ids}
                for event in reversed(tuple(getattr(self._workspace.project, "audit_log", ()) or ())):
                    if not event.entity_id or event.entity_id in selected_ids or event.action.startswith("bom."):
                        events.append(f"{event.timestamp} · {event.user} · {event.action}")
                    if len(events) >= 8:
                        break
            self.detail_labels["history"].setText("\n".join(events) or "Nog geen actiehistorie voor deze scope.")

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
            rows = self._selected_rows()
            preflight = self._confirm_preflight("release", rows)
            if preflight is None:
                return
            part_ids = self._read_model.production_part_ids(
                row for row in rows if row.group_id in set(preflight.eligible_group_ids)
            )
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
            preflight = self._confirm_preflight("machine", self._selected_rows())
            if preflight is None:
                return
            allowed_groups = set(preflight.eligible_group_ids)
            eligible_rows = tuple(row for row in self._selected_rows() if row.group_id in allowed_groups)
            part_ids = tuple(dict.fromkeys(
                entity_id for row in eligible_rows for entity_id in row.entity_ids
                if entity_id in self._workspace.project.parts
            ))
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
                    perform = lambda: service.assign_automatic(project, part_ids, user="bom-operator")
                    assigned = self._hub_state.begin_settings_transaction(
                        "machine.auto", preflight, perform, user="bom-operator"
                    ) if self._hub_state else perform()
                    blocked = sum(item.routing_status != "ready" for item in assigned)
                    message = (
                        f"{len(assigned) - blocked} onderdelen automatisch gerouteerd; "
                        f"{blocked} niet automatisch gerouteerd wegens capability-bewijs "
                        "of een handmatige vergrendeling."
                    )
                else:
                    perform = lambda: service.assign(
                        project, part_ids, machine.currentText(), user="bom-operator",
                        reason=reason.text(), manual_lock=lock.isChecked(),
                    )
                    self._hub_state.begin_settings_transaction(
                        "machine.manual", preflight, perform, user="bom-operator"
                    ) if self._hub_state else perform()
                    message = (
                        "Handmatige machinekeuze opgeslagen. Productievrijgave blijft "
                        "geblokkeerd tot capaciteit opnieuw is gevalideerd."
                    )
                session = getattr(self._workspace, "session", None)
                if session is not None and hasattr(session, "dirty"):
                    session.dirty = True
                self._rebuild_bom_snapshot()
                QtWidgets.QMessageBox.information(
                    self,
                    "Machine-indeling",
                    message,
                )
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Machine-indeling geblokkeerd", str(exc))

        def _edit_selection(self) -> None:
            if self._workspace is None or self._hub_state is None:
                return
            rows = self._selected_rows()
            preflight = self._confirm_preflight("edit", rows)
            if preflight is None:
                return
            field_label, accepted = QtWidgets.QInputDialog.getItem(
                self, "BOM-batchbewerking", "Veld:",
                (
                    "Fase", "Levering", "Revisiestatus", "Productiestatus",
                    "Classificatie", "Opmerking", "Profiel / materiaal via Part Workbench",
                ), 0, False,
            )
            if not accepted:
                return
            if field_label == "Profiel / materiaal via Part Workbench":
                self._route_scoped_action("edit", "edit")
                return
            if field_label == "Classificatie":
                value, accepted = QtWidgets.QInputDialog.getItem(
                    self, "Classificatie", "Nieuwe classificatie:",
                    ("make_part", "purchased_item", "fastener", "reference", "non_steel", "unknown"),
                    0, False,
                )
            else:
                value, accepted = QtWidgets.QInputDialog.getText(
                    self, "BOM-batchbewerking", f"Nieuwe waarde voor {field_label}:"
                )
            if not accepted or not str(value).strip():
                return
            allowed = set(preflight.eligible_group_ids)
            entity_ids = tuple(dict.fromkeys(
                entity_id for row in rows if row.group_id in allowed for entity_id in row.entity_ids
            ))
            field_name = {
                "Fase": "phase", "Levering": "delivery", "Revisiestatus": "revision_status",
                "Productiestatus": "production_status", "Classificatie": "category",
                "Opmerking": "bom_comment",
            }[field_label]

            def mutate() -> int:
                changed = 0
                for entity_id in entity_ids:
                    entity = self._workspace.project.get_entity(entity_id)
                    if entity is None:
                        continue
                    if field_name == "category" and hasattr(entity, "category"):
                        entity.category = str(value)
                    elif field_name != "bom_comment" and hasattr(entity, field_name):
                        setattr(entity, field_name, str(value))
                    else:
                        properties = getattr(entity, "properties", None)
                        if isinstance(properties, dict):
                            properties[field_name] = str(value)
                        else:
                            continue
                    if hasattr(entity, "recompute_hashes"):
                        entity.recompute_hashes()
                    changed += 1
                return changed

            try:
                changed = self._hub_state.begin_entity_transaction(
                    f"edit.{field_name}", preflight, entity_ids, mutate, user="bom-operator"
                )
                self._rebuild_bom_snapshot()
                QtWidgets.QMessageBox.information(
                    self, "BOM-batchbewerking", f"{changed} objecten gewijzigd. Undo blijft beschikbaar in deze werksessie."
                )
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "BOM-batchbewerking geblokkeerd", str(exc))

        def _rebuild_bom_snapshot(self) -> None:
            if self._workspace is None:
                return
            from cws_convertor.bom import build_bom_snapshot
            from cws_convertor.integration.selection import BomSelectionIndex
            self._workspace.bom_snapshot = build_bom_snapshot(
                self._workspace.project, user="bom-operator", classify_if_needed=False
            )
            self._workspace.bom_index = BomSelectionIndex(self._workspace.bom_snapshot)
            self._read_model = None
            self.refresh()

        def _reset_machine(self) -> None:
            if self._workspace is None:
                return
            part_ids = self._selected_part_ids()
            if not part_ids:
                return
            preflight = self._confirm_preflight("machine", self._selected_rows())
            if preflight is None:
                return
            reason, accepted = QtWidgets.QInputDialog.getText(
                self,
                "Machine-indeling resetten",
                "Reden:",
            )
            if not accepted:
                return
            try:
                perform = lambda: MachineRoutingService().reset(
                    self._workspace.project, part_ids, user="bom-operator", reason=reason,
                )
                self._hub_state.begin_settings_transaction(
                    "machine.reset", preflight, perform, user="bom-operator"
                ) if self._hub_state else perform()
                session = getattr(self._workspace, "session", None)
                if session is not None and hasattr(session, "dirty"):
                    session.dirty = True
                self._rebuild_bom_snapshot()
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Reset geblokkeerd", str(exc))

        def _export_scope(self) -> None:
            if self._workspace is None or self._read_model is None:
                return
            rows = self._selected_rows() or self._visible_rows
            if not rows:
                QtWidgets.QMessageBox.information(self, "BOM-export", "De huidige scope bevat geen regels.")
                return
            preflight = self._confirm_preflight(
                "review_export", rows, allow_blocked_review_export=True,
                expected_outputs=("XLSX", "CSV", "JSON", "PDF", "BOM-package"),
            )
            if preflight is None:
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

        def _confirm_preflight(
            self,
            action: str,
            rows: Iterable[BOMWorkspaceRow],
            *,
            allow_blocked_review_export: bool = False,
            expected_outputs: tuple[str, ...] = (),
        ) -> BOMBatchPreflight | None:
            if self._scope_engine is None or self._workspace is None:
                return None
            try:
                preflight = self._scope_engine.preflight(
                    action, rows,
                    expected_snapshot_sha256=self._workspace.bom_snapshot.snapshot_sha256,
                    visible_rows=self._visible_rows,
                    allow_blocked_review_export=allow_blocked_review_export,
                )
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(self, "BOM-preflight", str(exc))
                return None
            impact = preflight.impact
            partitions = "\n".join(
                f"• {machine}: {len(ids)} occurrences" for machine, ids in impact.machine_partitions
            )
            message = (
                f"Actie: {action}\n"
                f"{impact.group_count} BOM-regels · {impact.entity_count} occurrences · "
                f"{impact.assembly_count} assemblies · {_number(impact.total_mass_kg)} kg\n"
                f"Geschikt: {len(preflight.eligible_group_ids)} groepen · "
                f"Geblokkeerd: {len(preflight.blocked_group_ids)} groepen\n"
                + (f"Uitvoer: {', '.join(expected_outputs)}\n" if expected_outputs else "")
                + (partitions + "\n" if partitions else "")
                + f"Snapshot: {preflight.snapshot_sha256[:16]}\n"
                + f"Preflight: {preflight.preflight_sha256[:16]}"
            )
            if preflight.blocking_reasons or not preflight.eligible_group_ids:
                reasons = "\n".join(preflight.blocking_reasons) or "Geen geschikte regels voor deze actie."
                QtWidgets.QMessageBox.warning(self, "BOM-preflight geblokkeerd", message + "\n\n" + reasons)
                return None
            if os.environ.get("CWS_HEADLESS_GUI_SMOKE") == "1":
                return preflight
            if preflight.blocked_group_ids or len(impact.machine_partitions) > 1:
                dialog = QtWidgets.QMessageBox(self)
                dialog.setWindowTitle("Gemengde BOM-selectie")
                dialog.setIcon(QtWidgets.QMessageBox.Icon.Question)
                dialog.setText(message)
                eligible_button = dialog.addButton(
                    "Alleen geschikte uitvoeren", QtWidgets.QMessageBox.ButtonRole.AcceptRole
                )
                machine_button = dialog.addButton(
                    "Per machine opsplitsen", QtWidgets.QMessageBox.ButtonRole.ActionRole
                )
                blocked_button = dialog.addButton(
                    "Geblokkeerde regels openen", QtWidgets.QMessageBox.ButtonRole.HelpRole
                )
                dialog.addButton("Annuleren", QtWidgets.QMessageBox.ButtonRole.RejectRole)
                dialog.exec()
                clicked = dialog.clickedButton()
                if clicked is blocked_button:
                    blocked = set(preflight.blocked_group_ids)
                    self._select_rows(row for row in self._selected_rows() if row.group_id in blocked)
                    self.detail_tabs.setCurrentIndex(5)
                    return None
                if clicked is machine_button:
                    self._preflight_partition_mode = "machine"
                    return preflight
                if clicked is eligible_button:
                    self._preflight_partition_mode = "eligible"
                    return preflight
                return None
            answer = QtWidgets.QMessageBox.question(
                self, "BOM-preflight bevestigen", message + "\n\nActie uitvoeren op uitsluitend de geschikte regels?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            return preflight if answer == QtWidgets.QMessageBox.StandardButton.Yes else None

        def _route_scoped_action(self, action: str, route: str) -> None:
            rows = self._selected_rows()
            preflight = self._confirm_preflight(action, rows)
            if preflight is None:
                return
            allowed = set(preflight.eligible_group_ids)
            selected = tuple(row for row in rows if row.group_id in allowed)
            entity_ids = tuple(dict.fromkeys(entity_id for row in selected for entity_id in row.entity_ids))
            if entity_ids and self._workspace is not None:
                self.window.application_context.request_selection(
                    entity_ids, primary_entity_id=entity_ids[0], origin=f"bom_{action}",
                )
            if action == "production_export":
                update_export = getattr(self.window.application_context, "update_export_context", None)
                if callable(update_export):
                    update_export(
                        active_export_scope=entity_ids,
                        grouping=("machine" if self._preflight_partition_mode == "machine" else "combined"),
                        formats=("nc1", "step", "ifc", "dxf", "production_pdf"),
                        preflight_hash=preflight.preflight_sha256,
                    )
            self.action_requested.emit(route)

        def _save_revision_baseline(self) -> None:
            if self._hub_state is None or self._read_model is None:
                return
            value = self._hub_state.set_revision_baseline(self._read_model)
            self._mark_project_dirty()
            self.refresh()
            QtWidgets.QMessageBox.information(self, "Revisiebaseline", f"Baseline opgeslagen: {value[:16]}")

        def _undo_last_batch(self) -> None:
            if self._hub_state is None:
                return
            try:
                transaction_id = self._hub_state.undo_last()
                self._mark_project_dirty()
                self._rebuild_bom_snapshot()
                QtWidgets.QMessageBox.information(
                    self, "BOM-batchactie", f"Transactie {transaction_id[:8]} is ongedaan gemaakt."
                )
            except ValueError as exc:
                QtWidgets.QMessageBox.information(self, "BOM-batchactie", str(exc))

        def _mark_project_dirty(self) -> None:
            session = getattr(self._workspace, "session", None) if self._workspace is not None else None
            if session is not None and hasattr(session, "dirty"):
                session.dirty = True

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
            menu.addAction("Bewerken", lambda: self._route_scoped_action("edit", "edit"))
            menu.addAction("Tekening", lambda: self._route_scoped_action("drawing", "drawings"))
            menu.addAction("Machine toewijzen", self._assign_machine)
            menu.addAction("Waarom deze machine?", self._explain_machine)
            menu.addAction("Optimaliseren", lambda: self._route_scoped_action("optimize", "optimize"))
            menu.addAction("Scribing", lambda: self._route_scoped_action("scribing", "scribing"))
            menu.addSeparator()
            menu.addAction("Export selectie", self._export_scope)
            menu.exec(self.table.viewport().mapToGlobal(position))

        def _explain_machine(self) -> None:
            rows = self._selected_rows()
            if not rows:
                return
            lines = []
            for row in rows[:50]:
                lines.append(
                    f"{row.mark or row.group_id}: {row.machine or 'geen machine'}"
                    + (f" · {'; '.join(row.blocking_reasons)}" if row.blocking_reasons else " · capability/preflight geldig")
                )
            QtWidgets.QMessageBox.information(self, "Machineverklaring", "\n".join(lines))

        def _show_columns_menu(self) -> None:
            menu = QtWidgets.QMenu(self)
            presets = menu.addMenu("Kolompresets")
            presets.addAction("Basis", lambda: self._apply_column_preset("basis"))
            presets.addAction("Productie", lambda: self._apply_column_preset("production"))
            presets.addAction("Inkoop", lambda: self._apply_column_preset("procurement"))
            presets.addAction("Revisie", lambda: self._apply_column_preset("revision"))
            presets.addAction("Controle", lambda: self._apply_column_preset("control"))
            presets.addAction("Alles", lambda: self._apply_column_preset("all"))
            menu.addSeparator()
            menu.addAction("Werkruimte-layout opslaan…", self._save_named_layout)
            named = menu.addMenu("Opgeslagen layouts")
            self._populate_named_layouts(named)
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

        def _save_named_layout(self) -> None:
            name, accepted = QtWidgets.QInputDialog.getText(
                self, "Werkruimte-layout opslaan", "Naam:"
            )
            if not accepted or not name.strip():
                return
            key = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_") or "layout"
            root = f"bom/named_layouts/{key}"
            self._settings.setValue(f"{root}/name", name.strip())
            self._settings.setValue(f"{root}/splitter", self.splitter.saveState())
            self._settings.setValue(f"{root}/header", self.table.horizontalHeader().saveState())
            self._settings.setValue(f"{root}/family", self._family())
            self._settings.setValue(f"{root}/group", self.group_by.currentText())
            self._settings.setValue(f"{root}/status", self.status_filter.currentText())
            self._settings.setValue(f"{root}/phase", self.phase_filter.currentData() or "")
            self._settings.setValue(f"{root}/delivery", self.delivery_filter.currentData() or "")
            self._settings.setValue(f"{root}/color", self.color_mode.currentText())
            self._settings.setValue(f"{root}/detail", self.detail_tabs.currentIndex())

        def _populate_named_layouts(self, menu: Any) -> None:
            self._settings.beginGroup("bom/named_layouts")
            groups = tuple(self._settings.childGroups())
            self._settings.endGroup()
            menu.setEnabled(bool(groups))
            for key in groups:
                name = str(self._settings.value(f"bom/named_layouts/{key}/name", key))
                menu.addAction(name, lambda _checked=False, item=key: self._load_named_layout(item))

        def _load_named_layout(self, key: str) -> None:
            root = f"bom/named_layouts/{key}"
            splitter = self._settings.value(f"{root}/splitter")
            header = self._settings.value(f"{root}/header")
            if splitter:
                self.splitter.restoreState(splitter)
            if header:
                self.table.horizontalHeader().restoreState(header)
            family = str(self._settings.value(f"{root}/family", self._family()))
            if family in BOM_FAMILIES:
                self.family_tabs.setCurrentIndex(BOM_FAMILIES.index(family))
            for combo, suffix in (
                (self.group_by, "group"), (self.status_filter, "status"),
                (self.color_mode, "color"),
            ):
                value = str(self._settings.value(f"{root}/{suffix}", combo.currentText()))
                index = combo.findText(value)
                if index >= 0:
                    combo.setCurrentIndex(index)
            for combo, suffix in ((self.phase_filter, "phase"), (self.delivery_filter, "delivery")):
                index = combo.findData(str(self._settings.value(f"{root}/{suffix}", "") or ""))
                combo.setCurrentIndex(index if index >= 0 else 0)
            detail = int(self._settings.value(f"{root}/detail", 0) or 0)
            if 0 <= detail < self.detail_tabs.count():
                self.detail_tabs.setCurrentIndex(detail)
            self.refresh()

        def _apply_column_preset(self, name: str) -> None:
            visible = {
                "basis": {0, 1, 2, 3, 4, 5, 6, 7, 18},
                "production": {0, 1, 3, 4, 6, 7, 9, 10, 13, 14, 15, 18},
                "procurement": {0, 1, 2, 3, 4, 6, 7, 12, 16, 18},
                "revision": {0, 1, 2, 3, 4, 5, 6, 10, 13, 17, 18},
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
            pane = _BomViewerPane(state_bridge=self._viewer_bridge)
            pane.selection_requested.connect(self._viewer_selection_requested)
            top.setCentralWidget(pane)
            top._cws_viewer_pane = pane
            top._cws_geometry_key = "bom/detached_viewer_geometry"
            top.installEventFilter(self)
            top.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
            self._detached_windows.append(top)
            top.destroyed.connect(lambda *_: self._forget_window(top))
            pane.set_context(self._workspace, self._selection)
            geometry = self._settings.value(top._cws_geometry_key)
            if geometry:
                top.restoreGeometry(geometry)
            top.show()

        def _detach_bom(self) -> None:
            top = QtWidgets.QMainWindow(self.window)
            top.setWindowTitle("CWS Convertor · BOM / Hoeveelheden")
            top.resize(1600, 920)
            panel = BomWorkspacePanel(
                self.window, allow_detach=False, viewer_bridge=self._viewer_bridge
            )
            top.setCentralWidget(panel)
            top.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
            unsubscribe = self.window.application_context.subscribe(
                lambda snapshot: panel.set_context(
                    self.window.application_context.workspace,
                    snapshot.selection if snapshot.project_attached else None,
                )
            )
            top._cws_context_unsubscribe = unsubscribe
            top._cws_geometry_key = "bom/detached_bom_geometry"
            top.installEventFilter(self)
            self._detached_windows.append(top)
            top.destroyed.connect(lambda *_: (unsubscribe(), self._forget_window(top)))
            geometry = self._settings.value(top._cws_geometry_key)
            if geometry:
                top.restoreGeometry(geometry)
            top.show()

        def eventFilter(self, watched: Any, event: Any) -> bool:
            if event.type() == QtCore.QEvent.Type.Close:
                key = getattr(watched, "_cws_geometry_key", "")
                if key and hasattr(watched, "saveGeometry"):
                    self._settings.setValue(key, watched.saveGeometry())
            return super().eventFilter(watched, event)

        def _forget_window(self, window: Any) -> None:
            if window in self._detached_windows:
                self._detached_windows.remove(window)

        def _save_layout(self) -> None:
            self._settings.setValue("bom/splitter", self.splitter.saveState())
            self._settings.setValue("bom/header", self.table.horizontalHeader().saveState())
            self._settings.setValue("bom/family", self._family())
            self._settings.setValue("bom/scope_index", self.scope.currentIndex())
            self._settings.setValue("bom/group", self.group_by.currentText())
            self._settings.setValue("bom/status", self.status_filter.currentText())
            self._settings.setValue("bom/search", self.search.text())
            self._settings.setValue("bom/phase", self.phase_filter.currentData() or "")
            self._settings.setValue("bom/delivery", self.delivery_filter.currentData() or "")
            self._settings.setValue("bom/color_mode", self.color_mode.currentText())
            self._settings.setValue("bom/detail_tab", self.detail_tabs.currentIndex())

        def _restore_layout(self) -> None:
            mode = str(self._settings.value("bom/layout", "right") or "right")
            self._set_viewer_layout(mode if mode in {"right", "bottom", "hidden"} else "right")
            splitter = self._settings.value("bom/splitter")
            header = self._settings.value("bom/header")
            if splitter:
                self.splitter.restoreState(splitter)
            if header:
                self.table.horizontalHeader().restoreState(header)
            family = str(self._settings.value("bom/family", "parts") or "parts")
            if family in BOM_FAMILIES:
                self.family_tabs.setCurrentIndex(BOM_FAMILIES.index(family))
            self.scope.setCurrentIndex(int(self._settings.value("bom/scope_index", 0) or 0))
            self.search.setText(str(self._settings.value("bom/search", "") or ""))
            for combo, key in (
                (self.group_by, "bom/group"), (self.status_filter, "bom/status"),
                (self.color_mode, "bom/color_mode"),
            ):
                value = str(self._settings.value(key, combo.currentText()) or combo.currentText())
                index = combo.findText(value)
                if index >= 0:
                    combo.setCurrentIndex(index)
            self._restored_phase = str(self._settings.value("bom/phase", "") or "")
            self._restored_delivery = str(self._settings.value("bom/delivery", "") or "")
            detail_index = int(self._settings.value("bom/detail_tab", 0) or 0)
            if 0 <= detail_index < self.detail_tabs.count():
                self.detail_tabs.setCurrentIndex(detail_index)

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
