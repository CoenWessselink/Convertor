"""Unified U4 product shell for the part-first CWS Convertor desktop."""
from __future__ import annotations

from pathlib import Path
import threading
from typing import Any, Iterable

from cws_convertor.product import APP_NAME, APP_VERSION
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from .context_action_service import ContextActionService
from .ui_v51_contract import apply_v51_contract
from .unified_shell import (
    CWSMainWindow as _U3MainWindow,
    U3_CONTEXT_PROPERTY,
    U3_CONTEXT_TOKEN,
)

U4_WORKFLOW_PROPERTY = "cwsUnifiedProductionWorkflow"
U4_WORKFLOW_TOKEN = "CWS-U4-PRODUCTION-WORKFLOW"
_viewer_worker_prewarm: threading.Thread | None = None


def _prewarm_viewer_workers() -> None:
    try:
        from cws_viewer.geometry.worker_pool import PersistentGeometryWorkerPool

        PersistentGeometryWorkerPool.shared(3).prewarm()
    except Exception:
        # File-open retains its normal crash-recovering lazy-start path.
        pass

_PRODUCT_QSS = """
QMainWindow, QWidget { background:#f7f9fc; color:#17243a; font-family:'Segoe UI', 'Arial'; font-size:9pt; }
QFrame#cwsProductHeader { background:#ffffff; border-bottom:1px solid #d8e0ec; }
QLabel#productName { color:#103f77; font-size:18px; font-weight:700; }
QLabel#versionBadge { color:#185aa6; background:#eaf3ff; border:1px solid #c7ddf7; border-radius:3px; padding:3px 8px; }
QLabel#safetyBadge { color:#8a5700; background:#fff7e5; border:1px solid #edcf8c; border-radius:3px; padding:3px 8px; }
QFrame#productWorkspaceHeader { background:#ffffff; border:1px solid #d9e1ec; border-radius:5px; }
QLabel#contextChip { color:#114f9d; background:#edf5ff; border:1px solid #c4daf5; border-radius:4px; padding:5px 9px; font-weight:600; }
QLabel#summaryCard { min-width:128px; color:#174b86; background:#ffffff; border:1px solid #d6e0ec; border-radius:5px; padding:7px 11px; font-weight:600; }
QLabel#safetyStatus { color:#765000; background:#fff8e8; border:1px solid #ead29b; border-radius:4px; padding:6px 9px; }
QFrame#cwsQuickWorkspaceBar { background:#ffffff; border:1px solid #d6dfeb; border-radius:4px; }
QFrame#cwsU3UnifiedContextStrip { background:#f6f9fd; border:0; border-bottom:1px solid #d7e0eb; border-radius:0; }
QFrame#cwsContextRibbon { background:#ffffff; border:0; border-bottom:1px solid #d8e0ec; }
QFrame#ribbonGroup { background:#ffffff; border:0; border-right:1px solid #dbe3ed; }
QLabel#ribbonGroupTitle { color:#74839a; font-size:8pt; padding-top:2px; }
QToolButton#ribbonButton { min-width:58px; max-width:96px; min-height:68px; background:#ffffff; color:#143252; border:1px solid transparent; border-radius:3px; padding:2px 4px; }
QToolButton#ribbonButton:hover { background:#edf5ff; border-color:#bdd5f1; }
QToolButton#ribbonButton:pressed { background:#dcecff; }
QTabBar::tab { background:#ffffff; border:0; border-bottom:2px solid transparent; padding:10px 15px; }
QTabBar::tab:selected { color:#0759c7; border:0; border-bottom:3px solid #1267d6; padding-bottom:8px; font-weight:700; }
QTabWidget::pane { border:1px solid #d4dde9; background:#ffffff; }
QTreeWidget, QTableWidget, QTableView { background:#ffffff; border:1px solid #d2dce9; gridline-color:#e4e9f0; alternate-background-color:#f8fafc; selection-background-color:#d9eaff; selection-color:#123a68; }
QHeaderView::section { background:#f1f5fa; color:#445670; border:0; border-right:1px solid #dbe3ed; border-bottom:1px solid #d4dde8; padding:6px; font-weight:600; }
QPushButton, QToolButton { min-height:24px; background:#ffffff; border:1px solid #bdc9d9; border-radius:4px; padding:4px 10px; }
QPushButton:hover, QToolButton:hover { background:#edf5ff; border-color:#6e9fdf; }
QPushButton#primaryButton { background:#075fce; color:#ffffff; border-color:#075fce; }
QPushButton#primaryButton:hover { background:#064fae; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { min-height:25px; background:#ffffff; border:1px solid #c8d3e2; border-radius:3px; padding:2px 6px; }
QSplitter::handle { background:#dfe6ef; }
QStatusBar { background:#ffffff; border-top:1px solid #d4dde8; }
"""


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()
    from .ribbon_icons import ribbon_icon
    from .product_workspaces import BomWorkspacePanel, ProductionWorkflowPanel, ScribingWorkspacePanel
    from .phase3_workspaces import ProfileNestingPanel
    from .machine_settings_panel import MachineSettingsPanel
    from .functional_workspaces import DrawingWorkspacePanel, EditWorkspacePanel

    class WorkspaceRouter(QtCore.QObject):
        """Single workspace switch path that never rebuilds project or Viewer."""

        workspace_changed = QtCore.Signal(str)

        def __init__(self, window: "CWSMainWindow") -> None:
            super().__init__(window)
            self.window = window
            self.pages: dict[str, Any] = {}
            self.names_by_page: dict[Any, str] = {}
            self.history: list[str] = []
            self.history_index = -1
            self._routing = False
            self.context_actions = ContextActionService()

        def register(
            self,
            name: str,
            page: Any,
            *,
            primary: str,
            primary_page: Any,
            host: Any | None = None,
        ) -> None:
            key = str(name).strip().lower()
            self.pages[key] = page
            self.names_by_page[page] = key
            self.names_by_page.setdefault(primary_page, primary)
            self.context_actions.register(
                key,
                primary=primary,
                page=page,
                primary_page=primary_page,
                host=host,
            )

        def open_workspace(
            self,
            workspace: str,
            *,
            preserve_project: bool = True,
            preserve_selection: bool = True,
            preserve_camera: bool = True,
            preserve_visibility: bool = True,
            record_history: bool = True,
        ) -> bool:
            if not all((preserve_project, preserve_selection, preserve_camera, preserve_visibility)):
                raise ValueError(
                    "U4 workspace switching vereist behoud van project, selectie, camera en visibility"
                )
            key = str(workspace).strip().lower()
            key = {
                "drawing": "pdf",
                "drawings": "pdf",
                "tekeningen": "pdf",
            }.get(key, key)
            binding = self.context_actions.activate(key)
            if binding is None:
                return False
            self._routing = True
            try:
                self.window.tabs.setCurrentWidget(binding.primary_page)
                self.window.application_context.set_active_surface(
                    "workbench" if key == "edit" else key
                )
            finally:
                self._routing = False
            if record_history:
                if self.history_index + 1 < len(self.history):
                    self.history = self.history[: self.history_index + 1]
                if not self.history or self.history[-1] != key:
                    self.history.append(key)
                    self.history_index = len(self.history) - 1
            self.workspace_changed.emit(key)
            return True

        def observe_current_page(self, page: Any) -> None:
            if self._routing:
                return
            key = self.names_by_page.get(page)
            if not key:
                key = self.context_actions.route_for_primary_page(page)
            if key:
                self.open_workspace(key)

        def back(self) -> None:
            if self.history_index <= 0:
                return
            self.history_index -= 1
            self.open_workspace(self.history[self.history_index], record_history=False)

        def forward(self) -> None:
            if self.history_index + 1 >= len(self.history):
                return
            self.history_index += 1
            self.open_workspace(self.history[self.history_index], record_history=False)


    _PRODUCT_QSS += """
QMainWindow, QWidget#cwsCentral, QStackedWidget {
    background: #0b1118;
    color: #dce9f3;
}
QMenuBar, QMenu, QStatusBar, QToolBar {
    background: #0d151e;
    color: #dce9f3;
    border-color: #294354;
}
QTabWidget::pane { background: #101923; border: 1px solid #294354; }
QTabBar::tab {
    background: #111c26; color: #aebfcc; border: 1px solid #294354;
    padding: 7px 18px; min-height: 22px;
}
QTabBar::tab:hover { background: #182a38; color: #ffffff; }
QTabBar::tab:selected {
    background: #153c55; color: #ffffff; border-bottom: 2px solid #22a8f0;
}
QTabWidget#cwsPrimaryTabs > QTabBar::tab {
    font: 700 10pt "Bahnschrift"; min-width: 112px; padding: 8px 22px;
}
QFrame, QGroupBox, QScrollArea, QTableView, QTreeView, QListView, QTableWidget, QTreeWidget {
    background: #111b25; color: #dce9f3; border-color: #294354;
    alternate-background-color: #14222d; gridline-color: #294354;
}
QHeaderView::section {
    background: #172531; color: #cfe0eb; border: 1px solid #294354; padding: 5px;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    background: #0b141c; color: #edf7fc; border: 1px solid #35566b;
    border-radius: 2px; padding: 4px 6px; selection-background-color: #157fc0;
}
QPushButton, QToolButton {
    background: #152532; color: #dce9f3; border: 1px solid #35566b;
    border-radius: 3px; padding: 5px 10px;
}
QPushButton:hover, QToolButton:hover { background: #1c3b4e; border-color: #22a8f0; }
QPushButton:checked, QToolButton:checked, QPushButton:default {
    background: #087fc4; color: #ffffff; border-color: #2bb4ff;
}
QPushButton:disabled, QToolButton:disabled { color: #617482; background: #121b23; }
QLabel { color: #dce9f3; }
QProgressBar { background: #0b141c; border: 1px solid #294354; color: #dce9f3; }
QProgressBar::chunk { background: #1499df; }
QSplitter::handle { background: #294354; }
QScrollBar:vertical, QScrollBar:horizontal { background: #0e1720; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #35566b; min-width: 10px; min-height: 10px;
}
"""


    class _ProductHeader(QtWidgets.QFrame):
        back_requested = QtCore.Signal()
        forward_requested = QtCore.Signal()

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsProductHeader")
            self.setFixedHeight(38)
            self.setMinimumWidth(286)
            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(9, 0, 6, 0)
            layout.setSpacing(6)
            name = QtWidgets.QLabel(APP_NAME)
            name.setObjectName("productName")
            version = QtWidgets.QLabel(APP_VERSION)
            version.setObjectName("versionBadge")
            back = QtWidgets.QToolButton()
            back.setText("<")
            back.setToolTip("Vorige werkruimte")
            back.clicked.connect(self.back_requested)
            forward = QtWidgets.QToolButton()
            forward.setText(">")
            forward.setToolTip("Volgende werkruimte")
            forward.clicked.connect(self.forward_requested)
            layout.addWidget(name)
            layout.addWidget(version)
            layout.addWidget(back)
            layout.addWidget(forward)


    class _QuickWorkspaceBar(QtWidgets.QFrame):
        action_requested = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsQuickWorkspaceBar")
            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(8, 4, 8, 4)
            layout.setSpacing(4)
            label = QtWidgets.QLabel("CONTEXTACTIES")
            label.setObjectName("mutedText")
            layout.addWidget(label)
            for title, action in (
                ("Bewerken", "edit"),
                ("Tekening", "drawings"),
                ("Machine", "settings"),
                ("Optimaliseren", "profile_nesting"),
                ("Afdrukken", "report"),
                ("Meer", "production"),
            ):
                button = QtWidgets.QToolButton()
                button.setText(title)
                button.clicked.connect(
                    lambda _checked=False, value=action: self.action_requested.emit(value)
                )
                layout.addWidget(button)
            layout.addStretch(1)


    _RIBBON_DEFINITIONS = {
        "import": (
            ("Project", (("Nieuw project", "project:new"), ("Bestand openen", "project:open"), ("Importeren", "import:files"))),
            ("Importeren vanuit", (("IFC", "import:files"), ("STEP", "import:files"), ("NC / NC1", "import:files"), ("PDF", "pdf:open"), ("Pakket (ZIP)", "import:folder"))),
            ("Doorgaan", (("Viewer", "nav:viewer"), ("Converteren", "nav:converter"))),
        ),
        "viewer": (
            ("Selectie", (("Selecteren", "viewer:select"), ("Zoeken", "viewer:search"), ("Alles selecteren", "viewer:select_all"), ("Selectie wissen", "viewer:clear"))),
            ("Weergave", (("Isoleren", "viewer:isolate"), ("Transparant", "viewer:transparent"), ("Verbergen", "viewer:hide"), ("Zichtbaar maken", "viewer:show_all"), ("Spook model", "viewer:ghost"))),
            ("Camera", (("Weergave", "viewer:fit"), ("Standaard aanzichten", "viewer:iso"))),
            ("Meten / Snijden", (("Meten", "viewer:measure"), ("Doorsnede", "viewer:tools"), ("Clip", "viewer:tools"))),
            ("Hulpmiddelen", (("Raster", "viewer:grid"), ("Snappen", "viewer:snap"), ("Assen", "viewer:axes"))),
            ("Modus", (("Bewerk modus", "nav:edit"), ("Apart venster", "viewer:detach"), ("Meer", "viewer:tools"))),
        ),
        "edit": (
            ("Bewerken", (("Toevoegen", "edit:add"), ("Verwijderen", "edit:delete"), ("Dupliceren", "edit:duplicate"))),
            ("Volgorde", (("Omhoog", "edit:move_up"), ("Omlaag", "edit:move_down"))),
            ("Data", (("Importeren", "edit:import"), ("Acties", "edit:actions"))),
            ("Controle", (("Vernieuwen", "edit:refresh"), ("Validatie", "edit:validate"), ("Berekenen", "edit:calculate"))),
            ("Wijzigingen", (("Opslaan", "edit:save"), ("Annuleren", "edit:cancel"))),
        ),
        "converter": (
            ("Acties", (("Converteren", "convert:run"), ("Batch converteren", "convert:run"), ("Validatie", "control:run"), ("Vergelijken", "nav:control"))),
            ("Import", (("Importeren", "convert:add"), ("Toevoegen", "convert:add"))),
            ("Export", (("Exporteren", "nav:export"), ("Opslaan", "project:save"))),
            ("Opties", (("Instellingen", "nav:settings"), ("Mapping", "nav:converter"), ("Materiaaltabel", "nav:bom"), ("Profielbibliotheek", "nav:profile_nesting"))),
            ("Overig", (("Log", "nav:report"), ("Geschiedenis", "nav:report"))),
        ),
        "control": (
            ("Controle", (("Validatie starten", "control:run"), ("Revisies", "control:revisions"), ("Rapportage", "nav:report"))),
            ("Context", (("Viewer", "nav:viewer"), ("Bewerken", "nav:edit"))),
        ),
        "pdf": (
            ("Tekening", (("Nieuwe tekening", "nav:drawings"), ("PDF genereren", "pdf:generate"), ("Sjabloon", "nav:drawings"), ("Formaat", "nav:drawings"), ("Schaal", "nav:drawings"), ("Maatvoering", "nav:drawings"))),
            ("Inhoud", (("Aanzichten", "viewer:iso"), ("Titelblok", "nav:drawings"), ("Stuklijst", "nav:bom"))),
            ("Hulpmiddelen", (("Detailweergave toevoegen", "nav:drawings"), ("Doorsnede toevoegen", "viewer:tools"), ("Maatvoering vernieuwen", "nav:drawings"))),
            ("Uitvoer", (("Instellingen", "nav:drawings"), ("Opslaan", "project:save"), ("Exporteren", "pdf:generate"))),
        ),
        "drawings": (
            ("Tekeningen", (("PDF / Tekening", "nav:pdf"), ("Viewer", "nav:viewer"), ("Exporteren", "nav:export"))),
        ),
        "scribing": (
            ("Tekenen / Markeren", (("Scribe", "scribing:refresh"), ("Markeringen", "scribing:refresh"), ("Boren", "scribing:refresh"), ("Gaten", "scribing:refresh"), ("Lijnen", "scribing:refresh"), ("Tekst", "scribing:refresh"))),
            ("Automatisch", (("Automatisch", "scribing:verify"), ("Herken features", "scribing:verify"), ("Op alle onderdelen", "nav:scribing"))),
            ("Beheer", (("Instellingen", "nav:scribing"), ("Template", "nav:scribing"), ("Rapport", "nav:report"))),
        ),
        "bom": (
            ("Uitvoer", (("Excel export", "bom:export"), ("CSV export", "bom:export"))),
            ("Weergave", (("Kolommen", "bom:columns"), ("Filteren", "bom:filter"), ("Groeperen", "bom:group"), ("Sorteren", "bom:sort"))),
            ("Berekenen", (("Totalen", "bom:totals"), ("Eenheden", "bom:units"))),
            ("Layout", (("Opslaan weergave", "project:save"), ("Reset layout", "bom:reset"), ("Meer", "nav:report"))),
        ),
        "profile_nesting": (
            ("Optimalisatie", (("Analyseren", "nesting:analyse"), ("Optimaliseren", "nesting:solve"))),
            ("Controle", (("Runs", "nesting:runs"), ("Rapportage", "nav:report"), ("Viewer", "nav:viewer"))),
        ),
        "report": (
            ("Rapportage", (("Vernieuwen", "report:refresh"), ("Controleren", "nav:control"))),
            ("Productie", (("BOM", "nav:bom"), ("Scribing", "nav:scribing"), ("Exporteren", "nav:export"))),
        ),
        "export": (
            ("Uitvoer", (("Exporteren", "export:run"), ("Converteren", "nav:converter"))),
            ("Gates", (("Controleren", "nav:control"), ("Rapportage", "nav:report"), ("Viewer", "nav:viewer"))),
        ),
    }


    class _ContextRibbon(QtWidgets.QFrame):
        action_requested = QtCore.Signal(str)

        def __init__(self, workspace: str, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsContextRibbon")
            self.setFixedHeight(48)
            row = QtWidgets.QHBoxLayout(self)
            row.setContentsMargins(7, 4, 7, 4)
            row.setSpacing(4)
            for group_title, actions in _RIBBON_DEFINITIONS.get(workspace, ()):
                group = QtWidgets.QFrame(self)
                group.setObjectName("ribbonGroup")
                group.setAccessibleName(group_title)
                buttons = QtWidgets.QHBoxLayout(group)
                buttons.setContentsMargins(3, 0, 3, 0)
                buttons.setSpacing(1)
                for title, action in actions:
                    button = QtWidgets.QToolButton(group)
                    button.setObjectName("ribbonButton")
                    button.setText(title)
                    button.setToolTip(title)
                    button.setAccessibleName(title)
                    button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
                    button.setIcon(self._icon_for(action, title))
                    button.setIconSize(QtCore.QSize(18, 18))
                    button.setFixedSize(32, 32)
                    button.clicked.connect(
                        lambda _checked=False, value=action: self.action_requested.emit(value)
                    )
                    buttons.addWidget(button)
                row.addWidget(group)
            row.addStretch(1)

        def _icon_for(self, action: str, title: str = "") -> Any:
            return ribbon_icon(action, title)


    class CWSMainWindow(_U3MainWindow):
        """One project, one V15 viewer and one selection across all workspaces."""

        def __init__(self, initial_paths: Iterable[str | Path] = ()) -> None:
            deferred_initial_paths = tuple(Path(path) for path in initial_paths)
            self._product_ready = False
            self._shortcuts: list[Any] = []
            self._viewer_tool_dialogs: list[Any] = []
            # Finish installing the U4 pages, router and shared context before
            # opening a project.  The base shell otherwise queues loading while
            # its temporary pages are still being replaced.
            super().__init__(())

            # The U3 compatibility shell uses a permanent split view.  The accepted
            # product shell instead owns the full window and exposes that same
            # project/viewer page as the dedicated Viewer workspace.
            legacy_central = self.centralWidget()
            placeholder = getattr(self, "viewer_page", None)
            viewer_index = self.tabs.indexOf(placeholder) if placeholder is not None else -1
            if viewer_index < 0:
                viewer_index = 1
            if placeholder is not None and self.tabs.indexOf(placeholder) >= 0:
                self.tabs.removeTab(self.tabs.indexOf(placeholder))
                placeholder.setParent(None)
                placeholder.deleteLater()
            self.project_page.setParent(None)
            self.tabs.setParent(None)
            product_shell = QtWidgets.QWidget(self)
            product_shell.setObjectName("cwsPermanentViewerWorkspaceHost")
            product_layout = QtWidgets.QVBoxLayout(product_shell)
            product_layout.setContentsMargins(0, 0, 0, 0)
            product_layout.setSpacing(0)
            product_layout.addWidget(self.tabs, 1)
            self.viewer_page = self.project_page
            self.viewer_host = product_shell
            self.tabs.insertTab(viewer_index, self.viewer_page, "Viewer")
            self.setCentralWidget(product_shell)
            if legacy_central is not None and legacy_central is not product_shell:
                legacy_central.deleteLater()
            self.setObjectName("cwsConvertorUnifiedU4MainWindow")
            self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
            application = QtWidgets.QApplication.instance()
            product_font = QtGui.QFont("Bahnschrift", 9)
            if application is not None:
                application.setFont(product_font)
            self.setFont(product_font)
            self.workspace_router = WorkspaceRouter(self)
            self._v51_binding = apply_v51_contract(self, self.workspace_router)
            self._install_product_pages()
            self.tabs.setObjectName("cwsPrimaryTabs")
            self.production_workflow_page.setProperty(
                U4_WORKFLOW_PROPERTY,
                U4_WORKFLOW_TOKEN,
            )
            self._enforcing_u4_workflow_property = False
            self.production_workflow_page.installEventFilter(self)
            self._install_product_header()
            self._install_quick_workspace_bar()
            self._install_status_indicators()
            self._register_workspaces()
            self._install_context_ribbons()
            self._install_shortcuts()
            self._restore_layout()
            self.menuBar().hide()
            if hasattr(self, "context_strip"):
                self.context_strip.hide()
            legacy_viewer_toolbar = self.project_page.findChild(
                QtWidgets.QToolBar, "cwsV9ProjectToolbar"
            )
            if legacy_viewer_toolbar is not None:
                legacy_viewer_toolbar.hide()
                actions = legacy_viewer_toolbar.actions()
                slider_action = next(
                    (
                        action
                        for action in actions
                        if isinstance(action, QtWidgets.QWidgetAction)
                        and action.defaultWidget() is self.project_page.transparency_slider
                    ),
                    None,
                )
                slider_index = actions.index(slider_action) if slider_action in actions else -1
                label_action = (
                    actions[slider_index - 1]
                    if slider_index > 0
                    and isinstance(actions[slider_index - 1], QtWidgets.QWidgetAction)
                    else None
                )
                before_action = next(
                    (action for action in actions if action.text() == "Iso"),
                    None,
                )
                if before_action is not None and slider_action is not None:
                    if label_action is not None:
                        legacy_viewer_toolbar.insertAction(before_action, label_action)
                    legacy_viewer_toolbar.insertAction(before_action, slider_action)
                    self.project_page.transparency_slider.setFixedWidth(120)
            self.tabs.currentChanged.connect(self._product_tab_changed)
            self.workspace_router.workspace_changed.connect(self._workspace_changed)
            self._product_ready = True
            self._apply_u3_snapshot(self.application_context.snapshot)
            current = self._workspace_name(self.tabs.currentWidget()) or "import"
            self.workspace_router.open_workspace(current)
            self.production_workflow_page.setProperty(
                U4_WORKFLOW_PROPERTY,
                U4_WORKFLOW_TOKEN,
            )
            if deferred_initial_paths:
                QtCore.QTimer.singleShot(
                    0,
                    lambda values=deferred_initial_paths: self.open_initial_paths(values),
                )

        def _replace_page(self, attribute: str, page: Any, title: str) -> None:
            old = getattr(self, attribute)
            index = self.tabs.indexOf(old)
            if index < 0:
                index = self.tabs.count()
            else:
                self.tabs.removeTab(index)
            old.setParent(None)
            old.deleteLater()
            setattr(self, attribute, page)
            self.tabs.insertTab(index, page, title)

        def _install_product_pages(self) -> None:
            self._u3_bom_context = None
            # PDF / Tekening is the single canonical drawing workspace.  The
            # hidden legacy page remains alive because base-class selection
            # callbacks still update its context, but it is no longer a tab.
            legacy_drawings_index = self.tabs.indexOf(self.drawings_page)
            if legacy_drawings_index >= 0:
                self.tabs.removeTab(legacy_drawings_index)
                self.drawings_page.hide()
            self._replace_page("edit_page", EditWorkspacePanel(self), "Bewerken")
            self._replace_page("pdf_page", DrawingWorkspacePanel(self), "PDF / Tekening")
            self._replace_page("scribing_page", ScribingWorkspacePanel(self), "Scribing")
            self._replace_page("bom_excel_page", BomWorkspacePanel(self), "BOM / Hoeveelheden")
            bom_layout = self.bom_excel_page.layout()
            if bom_layout is not None:
                self._u3_bom_context = QtWidgets.QLabel("Geen selectie")
                self._u3_bom_context.setObjectName("selectionContext")
                self._u3_bom_context.setWordWrap(True)
                bom_layout.insertWidget(1, self._u3_bom_context)
            # Preserve the real profile/material library as a Project screen and
            # install profile nesting as its own Productie workspace.
            self.project_profiles_page = self.profiles_page
            from cws_convertor.ui_qt.v5_workspaces import (
                ManufacturabilityPanel, PlateNestingPanel, PrintCenterPanel,
                ProjectOverviewPanel, ProjectReviewsPanel, ProjectStructurePanel,
            )
            self.project_overview_page = ProjectOverviewPanel(self)
            self.project_structure_page = ProjectStructurePanel(self)
            self.project_reviews_page = ProjectReviewsPanel(self)
            self.plate_nesting_page = PlateNestingPanel(self)
            self.print_center_page = PrintCenterPanel(self)
            self.manufacturability_page = ManufacturabilityPanel(self)
            from .manufacturing_geometry_workspace import ManufacturingGeometryWorkspace
            self.manufacturing_geometry_page = ManufacturingGeometryWorkspace(
                self.viewer_host,
                getattr(self, "project", None),
                job_manager=getattr(self, "job_manager", None),
                parent=self,
            )
            project_profiles_index = self.tabs.indexOf(self.project_profiles_page)
            if project_profiles_index >= 0:
                self.tabs.removeTab(project_profiles_index)
            self.project_profiles_page.setParent(None)
            self.profiles_page = ProfileNestingPanel(self)
            self.tabs.insertTab(project_profiles_index if project_profiles_index >= 0 else self.tabs.count(), self.profiles_page, "Optimaliseren")
            self.settings_page = MachineSettingsPanel(self)
            self.settings_page.setProperty(U3_CONTEXT_PROPERTY, U3_CONTEXT_TOKEN)
            self.settings_page.setProperty(U4_WORKFLOW_PROPERTY, U4_WORKFLOW_TOKEN)
            # The U4 ribbon complements the proven Viewer V15 toolbar; it must
            # not hide direct navigation or the model-opacity slider.
            for toolbar in self.project_page.findChildren(QtWidgets.QToolBar):
                if toolbar.objectName() == "cwsV9ProjectToolbar":
                    toolbar.setVisible(False)
            self.project_page.transparency_slider.setVisible(True)
            index = self.control_page.indexOf(self.optimization_page)
            if index >= 0:
                self.control_page.removeTab(index)
                self.optimization_page.setParent(None)
                self.optimization_page.deleteLater()
            # Keep the base-window selection contract pointed at the live U4
            # optimization surface instead of the deleted legacy tab.
            self.optimization_page = self.profiles_page
            if isinstance(self.control_page, QtWidgets.QTabWidget):
                self.control_page.addTab(self.manufacturability_page, "Maakbaarheid")
                self.control_page.addTab(self.manufacturing_geometry_page, "Manufacturing Geometry")
            self.production_workflow_page = ProductionWorkflowPanel(self)
            self.production_workflow_page.setProperty(U4_WORKFLOW_PROPERTY, U4_WORKFLOW_TOKEN)
            export_index = self.tabs.indexOf(self.export_page)
            self.tabs.insertTab(
                export_index if export_index >= 0 else self.tabs.count(),
                self.production_workflow_page,
                "Rapportage",
            )
            self.report_page = self.production_workflow_page
            for page in (
                self.edit_page,
                self.pdf_page,
                self.scribing_page,
                self.bom_excel_page,
                self.profiles_page,
                self.production_workflow_page,
            ):
                page.setProperty(U3_CONTEXT_PROPERTY, U3_CONTEXT_TOKEN)
                page.setProperty(U4_WORKFLOW_PROPERTY, U4_WORKFLOW_TOKEN)
                page.action_requested.connect(self._route_action)
            self.pdf_page.generate_pdf.connect(self._generate_pdf)
            self.bom_excel_page.show_project_requested.connect(lambda: self._route_action("viewer"))
            leaf_pages = (
                self.import_page,
                self.project_profiles_page,
                self.project_overview_page,
                self.project_structure_page,
                self.project_reviews_page,
                self.project_page,
                self.edit_page,
                self.converter_page,
                self.control_page,
                self.pdf_page,
                self.scribing_page,
                self.bom_excel_page,
                self.profiles_page,
                self.plate_nesting_page,
                self.print_center_page,
                self.manufacturability_page,
                self.settings_page,
                self.production_workflow_page,
                self.export_page,
            )
            # Remove every legacy top-level registration, including base-shell
            # aliases such as Rapport. The page widgets remain alive and are
            # immediately rehomed below one of the five primary workspaces.
            self.tabs.setObjectName("cwsPrimaryNavigation")
            self.tabs.tabBar().setObjectName("cwsPrimaryNavigationBar")
            while self.tabs.count():
                self.tabs.removeTab(0)

            def primary_host(name: str, pages: tuple[tuple[Any, str], ...]) -> Any:
                host = QtWidgets.QTabWidget(self.tabs)
                host.setObjectName(name)
                host.setDocumentMode(True)
                host.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
                for child, title in pages:
                    host.addTab(child, title)
                return host

            self.project_workspace_page = primary_host(
                "cwsPrimaryProjectWorkspace",
                ((self.import_page, "Start / Inlezen"), (self.project_overview_page, "Projectoverzicht"), (self.project_structure_page, "Projectstructuur"), (self.project_profiles_page, "Profielen & Materialen"), (self.project_reviews_page, "Projectreviews")),
            )
            self.production_workspace_page = primary_host(
                "cwsPrimaryProductionWorkspace",
                (
                    (self.bom_excel_page, "BOM & Machines"),
                    (self.settings_page, "Machine-indeling"),
                    (self.profiles_page, "Optimalisatie"),
                    (self.plate_nesting_page, "Plaatnesting"),
                    (self.edit_page, "Bewerken"),
                    (self.scribing_page, "Scribing"),
                    (self.converter_page, "Converteren"),
                    (self.pdf_page, "Tekeningen & PDF"),
                ),
            )
            self.output_workspace_page = primary_host(
                "cwsPrimaryOutputWorkspace",
                ((self.print_center_page, "Print Center"), (self.export_page, "Export Center"), (self.production_workflow_page, "Rapport & Pakket")),
            )
            self._edit_subworkspace_host = self.production_workspace_page
            self._production_subworkspace_host = self.production_workspace_page
            self.edit_workspace_page = self.production_workspace_page
            self.control_workspace_page = self.control_page
            for page, title in (
                (self.project_workspace_page, "Project"),
                (self.project_page, "Viewer"),
                (self.production_workspace_page, "Productie"),
                (self.control_workspace_page, "Controle"),
                (self.output_workspace_page, "Uitvoer"),
            ):
                self.tabs.addTab(page, QtGui.QIcon(), title)
            for index, color in enumerate(("#2E9BE8", "#27B6E8", "#55C56B", "#E9A438", "#8B6DE3")):
                self.tabs.tabBar().setTabTextColor(index, QtGui.QColor(color))
            self.tabs.tabBar().setExpanding(False)
            self.tabs.tabBar().setUsesScrollButtons(True)

        def _install_product_header(self) -> None:
            self.product_header = _ProductHeader(self.tabs)
            self.product_header.back_requested.connect(self.workspace_router.back)
            self.product_header.forward_requested.connect(self.workspace_router.forward)
            self.tabs.setCornerWidget(
                self.product_header,
                QtCore.Qt.Corner.TopLeftCorner,
            )

        def _install_quick_workspace_bar(self) -> None:
            layout = self.project_page.layout()
            if layout is None:
                return
            self.quick_workspace_bar = _QuickWorkspaceBar(self.project_page)
            self.quick_workspace_bar.action_requested.connect(self._route_action)
            layout.addWidget(self.quick_workspace_bar)

        def _install_status_indicators(self) -> None:
            self.status_project = QtWidgets.QLabel("Project: geen project")
            self.status_selection = QtWidgets.QLabel("Selectie: 0")
            self.status_workspace = QtWidgets.QLabel("Workspace: Inlezen")
            self.status_validation = QtWidgets.QLabel("Validatie: gate actief")
            for widget in (
                self.status_project,
                self.status_selection,
                self.status_workspace,
                self.status_validation,
            ):
                widget.setContentsMargins(8, 0, 8, 0)
                self.statusBar().addPermanentWidget(widget)

        def _register_workspaces(self) -> None:
            for name, page, primary, primary_page, host in (
                ("project", self.import_page, "project", self.project_workspace_page, self.project_workspace_page),
                ("import", self.import_page, "project", self.project_workspace_page, self.project_workspace_page),
                ("converter", self.converter_page, "production", self.production_workspace_page, self.production_workspace_page),
                ("control", self.control_page, "control", self.control_workspace_page, None),
                ("project_overview", self.project_overview_page, "project", self.project_workspace_page, self.project_workspace_page),
                ("project_structure", self.project_structure_page, "project", self.project_workspace_page, self.project_workspace_page),
                ("project_profiles", self.project_profiles_page, "project", self.project_workspace_page, self.project_workspace_page),
                ("project_reviews", self.project_reviews_page, "project", self.project_workspace_page, self.project_workspace_page),
                ("viewer", self.project_page, "viewer", self.project_page, None),
                ("edit", self.edit_page, "production", self.edit_workspace_page, self._edit_subworkspace_host),
                ("scribing", self.scribing_page, "production", self.edit_workspace_page, self._edit_subworkspace_host),
                ("production", self.bom_excel_page, "production", self.production_workspace_page, self._production_subworkspace_host),
                ("bom", self.bom_excel_page, "production", self.production_workspace_page, self._production_subworkspace_host),
                ("profile_nesting", self.profiles_page, "production", self.production_workspace_page, self._production_subworkspace_host),
                ("plate_nesting", self.plate_nesting_page, "production", self.production_workspace_page, self._production_subworkspace_host),
                ("settings", self.settings_page, "production", self.production_workspace_page, self._production_subworkspace_host),
                ("production_workflow", self.production_workflow_page, "production", self.production_workspace_page, self._production_subworkspace_host),
                ("report", self.production_workflow_page, "output", self.output_workspace_page, self.output_workspace_page),
                ("output", self.output_workspace_page, "output", self.output_workspace_page, self.output_workspace_page),
                ("pdf", self.pdf_page, "production", self.production_workspace_page, self.production_workspace_page),
                ("print_center", self.print_center_page, "output", self.output_workspace_page, self.output_workspace_page),
                ("manufacturability", self.manufacturability_page, "control", self.control_workspace_page, self.control_page),
                ("manufacturing_geometry", self.manufacturing_geometry_page, "control", self.control_workspace_page, self.control_page),
                ("export", self.export_page, "output", self.output_workspace_page, self.output_workspace_page),
            ):
                self.workspace_router.register(name, page, primary=primary, primary_page=primary_page, host=host)

        def _install_context_ribbons(self) -> None:
            self.context_ribbons: dict[str, Any] = {}
            installed_pages: set[Any] = set()
            for workspace, page in self.workspace_router.pages.items():
                if page in installed_pages:
                    continue
                installed_pages.add(page)
                layout = page.layout() if hasattr(page, "layout") else None
                if layout is None or not hasattr(layout, "insertWidget"):
                    continue
                ribbon = _ContextRibbon(workspace, page)
                ribbon.action_requested.connect(self._ribbon_action)
                layout.insertWidget(0, ribbon)
                self.context_ribbons[workspace] = ribbon
            self._shared_viewer_stack = self.project_page.stack

        def _ribbon_action(self, action: str) -> None:
            namespace, _, command = str(action).partition(":")
            if namespace == "nav":
                self.workspace_router.open_workspace(command)
                return
            try:
                if namespace == "viewer":
                    self._viewer_ribbon_action(command)
                elif namespace == "project" and command == "open":
                    self._choose_project()
                elif namespace == "project" and command == "new":
                    self.import_page.clear()
                    self.workspace_router.open_workspace("import")
                    self.statusBar().showMessage("Nieuwe projectcontext gereed; voeg bronbestanden toe.", 5000)
                elif namespace == "project" and command == "save":
                    if self.workspace is not None:
                        self.workspace.session.save(user="qt-gui", revision_message="Opgeslagen via product ribbon")
                        self.statusBar().showMessage("Project opgeslagen.", 4000)
                elif namespace == "import":
                    getattr(self.import_page, {"files": "_choose_files", "folder": "_choose_folder", "clear": "clear"}[command])()
                elif namespace == "convert":
                    getattr(self.converter_page, {"add": "_choose_files", "run": "_run", "clear": "_clear", "output": "_choose_output"}[command])()
                elif namespace == "control":
                    if command == "run":
                        self.validation_page._run()
                    else:
                        self._show_revisions()
                elif namespace == "pdf":
                    if command == "generate":
                        self._generate_pdf()
                    else:
                        getattr(self.pdf_page, {"open": "_choose", "analyse": "_analyse"}[command])()
                elif namespace == "scribing":
                    if command == "verify":
                        self.scribing_page._verify_authority()
                    else:
                        self.scribing_page.set_context(self.workspace, self.application_context.snapshot.selection)
                elif namespace == "bom":
                    if command == "export":
                        self._click_button_containing(self.bom_excel_page, "export")
                    elif command == "refresh":
                        self.bom_excel_page.set_context(self.workspace, self.application_context.snapshot.selection)
                    else:
                        self.bom_excel_page.handle_ribbon(command)
                elif namespace == "edit":
                    self.edit_page.handle_ribbon(command)
                elif namespace == "nesting":
                    if command == "analyse":
                        self.profiles_page._analyse()
                    elif command == "solve":
                        self.profiles_page._start_solve()
                    else:
                        self.profiles_page.tabs.setCurrentIndex(1)
                elif namespace == "report":
                    self.production_workflow_page.refresh()
                elif namespace == "export":
                    self.export_page._run()
            except Exception as exc:
                self.statusBar().showMessage(f"Actie geblokkeerd: {type(exc).__name__}: {exc}", 8000)

        def _click_button_containing(self, parent: Any, token: str) -> bool:
            for button in parent.findChildren(QtWidgets.QAbstractButton):
                if token.lower() in button.text().lower() and button.isEnabled():
                    button.click()
                    return True
            return False

        def _viewer_ribbon_action(self, command: str) -> None:
            if command == "detach":
                self.project_page.open_detached_viewer()
                return
            aliases = {
                "fit": "fit_action",
                "iso": "iso_action",
                "front": "front_action",
                "top": "top_action",
                "hide": "hide_action",
                "isolate": "isolate_action",
                "ghost": "ghost_action",
                "show_all": "show_all_action",
                "exact": "exact_action",
            }
            if command in aliases:
                action = getattr(self.project_page, aliases[command], None)
                if action is not None and action.isEnabled():
                    action.trigger()
                else:
                    self.statusBar().showMessage("Open eerst een project voor deze Viewer-actie.", 5000)
                return
            viewer = getattr(self.project_page, "viewer", None)
            workspace = getattr(self.project_page, "workspace", None)
            if viewer is None or workspace is None:
                self.statusBar().showMessage("Open eerst een project voor Viewer V15.", 5000)
                return
            if command == "search":
                query, accepted = QtWidgets.QInputDialog.getText(
                    self, "Zoeken in model", "Naam, merk of onderdeel:"
                )
                if accepted and query.strip() and hasattr(self.project_page, "tree"):
                    flags = QtCore.Qt.MatchFlag.MatchContains | QtCore.Qt.MatchFlag.MatchRecursive
                    matches = self.project_page.tree.findItems(query.strip(), flags, 0)
                    self.project_page.tree.clearSelection()
                    for item in matches:
                        item.setSelected(True)
                    if matches:
                        self.project_page.tree.scrollToItem(matches[0])
                    self.statusBar().showMessage(
                        f"{len(matches)} modelobject(en) gevonden voor '{query.strip()}'.", 5000
                    )
            elif command == "select":
                viewer.set_navigation_mode("select")
            elif command == "area":
                viewer.set_area_selection(True)
            elif command == "clear":
                workspace.interaction.select_nodes((), origin="ribbon")
            elif command == "select_all":
                scene_nodes = tuple(
                    node.node_id for node in viewer.controller.scene.nodes if node.selectable
                )
                workspace.interaction.select_nodes(scene_nodes, origin="ribbon")
            elif command == "transparent":
                node_ids = self.project_page._selected_nodes()
                controller = viewer.controller
                if node_ids:
                    controller.set_transparency(node_ids, 0.65)
            elif command in {"measure", "tools"}:
                self._show_viewer_tools()
            elif command == "snap":
                self._show_viewer_tools()
            elif command in {"grid", "axes"}:
                method_names = (("toggle_grid", "toggle_grid_visibility") if command == "grid" else ("toggle_axes", "toggle_axes_visibility"))
                invoked = False
                for target in (viewer, getattr(viewer, "controller", None)):
                    for method_name in method_names:
                        method = getattr(target, method_name, None)
                        if callable(method):
                            method(); invoked = True; break
                    if invoked:
                        break
                if not invoked:
                    self.statusBar().showMessage(
                        f"{command.title()} blijft onderdeel van de actieve Viewer V15-weergave.", 5000
                    )

        def _show_viewer_tools(self) -> None:
            workspace = getattr(self.project_page, "workspace", None)
            if workspace is None:
                return
            from .viewer_tools import IntegratedViewerToolsPanel

            dialog = QtWidgets.QDialog(self)
            dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
            dialog.setWindowTitle("Viewer V15 | Meten, doorsnede en clipbox")
            dialog.resize(980, 680)
            layout = QtWidgets.QVBoxLayout(dialog)
            panel = IntegratedViewerToolsPanel(workspace, dialog)
            layout.addWidget(panel)
            self._viewer_tool_dialogs.append(dialog)
            dialog.destroyed.connect(
                lambda _object=None, value=dialog: self._viewer_tool_dialogs.remove(value)
                if value in self._viewer_tool_dialogs else None
            )
            dialog.show()

        def _install_shortcuts(self) -> None:
            for sequence, workspace in (
                ("Ctrl+1", "viewer"),
                ("Ctrl+2", "edit"),
                ("Ctrl+3", "converter"),
                ("Ctrl+4", "scribing"),
                ("Ctrl+5", "bom"),
                ("Ctrl+6", "report"),
                ("Ctrl+7", "export"),
                ("Alt+Left", "history_back"),
                ("Alt+Right", "history_forward"),
            ):
                shortcut = QtGui.QShortcut(QtGui.QKeySequence(sequence), self)
                if workspace == "history_back":
                    shortcut.activated.connect(self.workspace_router.back)
                elif workspace == "history_forward":
                    shortcut.activated.connect(self.workspace_router.forward)
                else:
                    shortcut.activated.connect(
                        lambda value=workspace: self.workspace_router.open_workspace(value)
                    )
                self._shortcuts.append(shortcut)
            escape = QtGui.QShortcut(QtGui.QKeySequence("Esc"), self)
            escape.setContext(QtCore.Qt.ShortcutContext.ApplicationShortcut)
            escape.activated.connect(self._escape_action)
            self._shortcuts.append(escape)

        def _escape_action(self) -> None:
            cancel_load = getattr(self.project_page, "cancel_project_load", None)
            if callable(cancel_load) and cancel_load():
                return
            viewer = getattr(self.project_page, "viewer", None)
            if viewer is not None:
                viewer.controller.cancel_tool()
                if hasattr(viewer, "set_zoom_area"):
                    viewer.set_zoom_area(False)
                if hasattr(viewer, "set_area_selection"):
                    viewer.set_area_selection(False)

        def _workspace_name(self, page: Any) -> str:
            return self.workspace_router.names_by_page.get(page, "")

        def eventFilter(self, watched: Any, event: Any) -> bool:
            if (
                watched is getattr(self, "production_workflow_page", None)
                and event.type() == QtCore.QEvent.Type.DynamicPropertyChange
                and bytes(event.propertyName()).decode("utf-8") == U4_WORKFLOW_PROPERTY
                and not getattr(self, "_enforcing_u4_workflow_property", False)
                and watched.property(U4_WORKFLOW_PROPERTY) != U4_WORKFLOW_TOKEN
            ):
                self._enforcing_u4_workflow_property = True
                try:
                    watched.setProperty(U4_WORKFLOW_PROPERTY, U4_WORKFLOW_TOKEN)
                finally:
                    self._enforcing_u4_workflow_property = False
            return super().eventFilter(watched, event)

        def _product_tab_changed(self, _index: int) -> None:
            if self._product_ready:
                self.workspace_router.observe_current_page(self.tabs.currentWidget())

        def _workspace_changed(self, workspace: str) -> None:
            if not hasattr(self, "status_workspace"):
                return
            # QVTK owns a native child window and cannot safely be reparented
            # between tabs. Keep it permanently in the Viewer workspace.
            if workspace == "viewer":
                self._place_shared_viewer(workspace)
            self.production_workflow_page.setProperty(
                U4_WORKFLOW_PROPERTY,
                U4_WORKFLOW_TOKEN,
            )
            self.status_workspace.setText(f"Workspace: {workspace.replace('_', ' ').title()}")

        def _project_loaded(self, path: str) -> None:
            super()._project_loaded(path)
            self.production_workflow_page.setProperty(
                U4_WORKFLOW_PROPERTY,
                U4_WORKFLOW_TOKEN,
            )

        def _surface_for_current_tab(self) -> str:
            if hasattr(self, "workspace_router"):
                name = self._workspace_name(self.tabs.currentWidget())
                if name:
                    return "workbench" if name == "edit" else name
            return super()._surface_for_current_tab()

        def _context_snapshot_changed(self, snapshot: Any) -> None:
            super()._context_snapshot_changed(snapshot)
            self._apply_u3_snapshot(snapshot)

        def _apply_u3_snapshot(self, snapshot: Any) -> None:
            parent_apply = getattr(super(), "_apply_u3_snapshot", None)
            if callable(parent_apply):
                parent_apply(snapshot)
            if hasattr(self, "production_workflow_page"):
                self.production_workflow_page.setProperty(
                    U4_WORKFLOW_PROPERTY,
                    U4_WORKFLOW_TOKEN,
                )
            if not hasattr(self, "status_project"):
                return
            project = snapshot.project_name or snapshot.project_id or "geen project"
            self.status_project.setText(f"Project: {project}")
            self.status_selection.setText(f"Selectie: {len(snapshot.selection.entity_ids)}")
            primary = snapshot.selection.primary_entity_id
            if self._u3_bom_context is not None:
                self._u3_bom_context.setText(
                    f"Selectie: {primary}" if primary else "Geen selectie"
                )
            self.status_validation.setText(
                "Validatie: BLOCKED" if snapshot.integrity_blocking_codes else "Validatie: context OK"
            )
            selection = snapshot.selection if snapshot.project_attached else None
            workspace = self.workspace if snapshot.project_attached else None
            self.edit_page.set_context(self.workspace, snapshot.selection)
            self.pdf_page.set_context(self.workspace, snapshot.selection)
            for page in (self.project_overview_page, self.project_structure_page, self.project_profiles_page, self.project_reviews_page, self.profiles_page, self.plate_nesting_page, self.print_center_page, self.manufacturability_page):
                page.set_context(workspace, selection)
            self.bom_excel_page.set_context(workspace, selection)
            self.production_workflow_page.set_context(workspace, selection)
            settings = getattr(self, "settings_page", None)
            if settings is not None and workspace is not None:
                if hasattr(settings, "set_context"):
                    settings.set_context(workspace, selection)
                elif hasattr(settings, "set_workspace"):
                    settings.set_workspace(workspace)
                elif hasattr(settings, "set_project"):
                    settings.set_project(workspace.project)

        def _route_action(self, action: str) -> None:
            key = str(action)
            if key == "generate_pdf":
                self._generate_pdf()
                return
            if key == "save_project":
                self._ribbon_action("project:save")
                return
            mapping = {
                "properties": "viewer",
                "viewer": "viewer",
                "edit": "edit",
                "convert": "converter",
                "validate": "control",
                "pdf": "pdf",
                "profiles": "profile_nesting",
                "optimize": "profile_nesting",
                "settings": "settings",
                "drawings": "pdf",
                "scribing": "scribing",
                "quantities": "bom",
                "bom": "bom",
                "report": "production_workflow",
                "production_workflow": "production_workflow",
                "export": "export",
            }
            if key in {"open_exact", "legacy_profiles"}:
                super()._route_action(key)
                return
            target = mapping.get(key)
            if target and self.workspace_router.open_workspace(target):
                return
            super()._route_action(key)

        def _generate_pdf(self) -> None:
            drawing = self.workspace_router.pages.get("pdf") or self.workspace_router.pages.get("drawing")
            if isinstance(drawing, QtWidgets.QTabWidget):
                drawing = drawing.currentWidget()
            if drawing is not None and hasattr(drawing, "export_pdf"):
                drawing.export_pdf()
                return
            if self.workspace is None:
                QtWidgets.QMessageBox.information(
                    self, "PDF genereren", "Open eerst een project."
                )
                return
            checks = getattr(self.export_page, "format_checks", {})
            for name, control in checks.items():
                control.setChecked(name in {"production_pdf", "review_pdf"})
            self.tabs.setCurrentWidget(self.export_page)
            run = getattr(self.export_page, "_run", None)
            if callable(run):
                run()

        def _place_shared_viewer(self, workspace: str) -> None:
            viewer = getattr(self.project_page, "viewer", None)
            if viewer is None:
                return
            if not hasattr(self, "_cws_viewer_home_parent"):
                home = viewer.parentWidget()
                self._cws_viewer_home_parent = home
                self._cws_viewer_home_index = home.indexOf(viewer) if isinstance(home, QtWidgets.QSplitter) else -1
                self._cws_module_viewer_hosts = {}
            if workspace == "viewer":
                home = self._cws_viewer_home_parent
                if viewer.parentWidget() is not home:
                    if isinstance(home, QtWidgets.QSplitter):
                        home.insertWidget(max(0, self._cws_viewer_home_index), viewer)
                    elif home is not None and home.layout() is not None:
                        home.layout().addWidget(viewer)
                viewer.setMinimumHeight(320)
                viewer.show()
                return
            if workspace == "import":
                viewer.hide()
                return
            page = self.workspace_router.pages.get(workspace)
            if isinstance(page, QtWidgets.QTabWidget):
                page = page.currentWidget()
            if page is None:
                return
            layout = page.layout() if hasattr(page, "layout") else None
            if layout is None or not hasattr(layout, "insertWidget"):
                return
            host = self._cws_module_viewer_hosts.get(page)
            if host is None:
                host = QtWidgets.QFrame(page)
                host.setObjectName("module3dViewerHost")
                host.setStyleSheet("QFrame#module3dViewerHost{background:#ffffff;border:1px solid #d4dde6}")
                host_layout = QtWidgets.QVBoxLayout(host)
                host_layout.setContentsMargins(0, 0, 0, 0)
                host_layout.setSpacing(0)
                bar = QtWidgets.QHBoxLayout()
                label = QtWidgets.QLabel(f"3D MODEL - {workspace.upper()}")
                label.setStyleSheet("padding:5px 10px;color:#1f2d3d;font-weight:700")
                bar.addWidget(label)
                bar.addStretch(1)
                hint = QtWidgets.QLabel("Een model, een selectie, een Viewer")
                hint.setStyleSheet("padding-right:10px;color:#617387")
                bar.addWidget(hint)
                host_layout.addLayout(bar)
                layout.insertWidget(min(1, layout.count()), host, 3)
                self._cws_module_viewer_hosts[page] = host
            viewer.setParent(host)
            host.layout().addWidget(viewer, 1)
            viewer.setMinimumHeight(120)
            viewer.show()

        def _restore_layout(self) -> None:
            settings = QtCore.QSettings("CWS", "CWS Convertor")
            geometry = settings.value("product-ui/geometry")
            if geometry:
                self.restoreGeometry(geometry)
            workspace = str(settings.value("product-ui/last-workspace", "import") or "import")
            if workspace in self.workspace_router.pages:
                self.workspace_router.open_workspace(workspace, record_history=False)

        def closeEvent(self, event: Any) -> None:
            settings = QtCore.QSettings("CWS", "CWS Convertor")
            settings.setValue("product-ui/geometry", self.saveGeometry())
            settings.setValue(
                "product-ui/last-workspace",
                self._workspace_name(self.tabs.currentWidget()) or "import",
            )
            super().closeEvent(event)


    CwsConvertorMainWindow = CWSMainWindow

    def run_qt_application(initial_paths: Iterable[str | Path] | str | Path | None = None) -> int:
        import sys

        global _viewer_worker_prewarm

        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        application.setApplicationName(APP_NAME)
        application.setOrganizationName("CWS")
        if _viewer_worker_prewarm is None or not _viewer_worker_prewarm.is_alive():
            _viewer_worker_prewarm = threading.Thread(
                target=_prewarm_viewer_workers,
                name="CWS-Viewer-Worker-Prewarm",
                daemon=True,
            )
            _viewer_worker_prewarm.start()
        if initial_paths is None:
            paths: tuple[Path, ...] = ()
        elif isinstance(initial_paths, (str, Path)):
            paths = (Path(initial_paths),)
        else:
            paths = tuple(Path(value) for value in initial_paths)
        window = CWSMainWindow(paths)
        window.show()
        return int(application.exec())
