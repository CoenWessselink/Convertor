"""Unified U4 product shell for the part-first CWS Convertor desktop."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from cws_convertor.product import APP_NAME, APP_VERSION
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from .unified_shell import (
    CWSMainWindow as _U3MainWindow,
    U3_CONTEXT_PROPERTY,
    U3_CONTEXT_TOKEN,
)

U4_WORKFLOW_PROPERTY = "cwsUnifiedProductionWorkflow"
U4_WORKFLOW_TOKEN = "CWS-U4-PRODUCTION-WORKFLOW"

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
    from .product_workspaces import (
        BomWorkspacePanel,
        ProfileNestingPanel,
        ProductionWorkflowPanel,
        ScribingWorkspacePanel,
    )
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

        def register(self, name: str, page: Any) -> None:
            key = str(name).strip().lower()
            self.pages[key] = page
            self.names_by_page[page] = key

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
            page = self.pages.get(key)
            if page is None:
                return False
            self._routing = True
            try:
                self.window.tabs.setCurrentWidget(page)
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


    class _ProductHeader(QtWidgets.QFrame):
        back_requested = QtCore.Signal()
        forward_requested = QtCore.Signal()

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsProductHeader")
            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(12, 6, 12, 6)
            layout.setSpacing(9)
            name = QtWidgets.QLabel(APP_NAME)
            name.setObjectName("productName")
            version = QtWidgets.QLabel(APP_VERSION)
            version.setObjectName("versionBadge")
            safety = QtWidgets.QLabel("Productiegates actief | machine-transfer gesloten")
            safety.setObjectName("safetyBadge")
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
            layout.addStretch(1)
            layout.addWidget(safety)


    class _QuickWorkspaceBar(QtWidgets.QFrame):
        action_requested = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsQuickWorkspaceBar")
            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(8, 4, 8, 4)
            layout.setSpacing(4)
            label = QtWidgets.QLabel("Actieve part-context")
            label.setObjectName("mutedText")
            layout.addWidget(label)
            for title, action in (
                ("Bewerken", "edit"),
                ("Scribing", "scribing"),
                ("BOM", "quantities"),
                ("Rapportage", "report"),
                ("Export", "export"),
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
            ("Modus", (("Bewerk modus", "nav:edit"), ("Apart venster", "viewer:detach"), ("Exporteren", "nav:export"), ("Meer", "viewer:tools"))),
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
            ("Opties", (("Instellingen", "convert:output"), ("Mapping", "nav:converter"), ("Materiaaltabel", "nav:bom"), ("Profielbibliotheek", "nav:profile_nesting"))),
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
            self.setFixedHeight(104)
            row = QtWidgets.QHBoxLayout(self)
            row.setContentsMargins(8, 3, 8, 3)
            row.setSpacing(0)
            for group_title, actions in _RIBBON_DEFINITIONS.get(workspace, ()):
                group = QtWidgets.QFrame(self)
                group.setObjectName("ribbonGroup")
                group_layout = QtWidgets.QVBoxLayout(group)
                group_layout.setContentsMargins(5, 2, 5, 1)
                group_layout.setSpacing(1)
                buttons = QtWidgets.QHBoxLayout()
                buttons.setSpacing(1)
                for title, action in actions:
                    button = QtWidgets.QToolButton(group)
                    button.setObjectName("ribbonButton")
                    display_title = title
                    if len(title) > 12 and " " in title:
                        display_title = title.replace(" ", "\n", 1)
                    button.setText(display_title)
                    button.setToolTip(title)
                    button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                    button.setIcon(self._icon_for(action, title))
                    button.setIconSize(QtCore.QSize(26, 26))
                    button.clicked.connect(
                        lambda _checked=False, value=action: self.action_requested.emit(value)
                    )
                    buttons.addWidget(button)
                group_layout.addLayout(buttons)
                caption = QtWidgets.QLabel(group_title, group)
                caption.setObjectName("ribbonGroupTitle")
                caption.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                group_layout.addWidget(caption)
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
            self.setObjectName("cwsConvertorUnifiedU4MainWindow")
            self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
            application = QtWidgets.QApplication.instance()
            product_font = QtGui.QFont("Segoe UI", 9)
            if application is not None:
                application.setFont(product_font)
            self.setFont(product_font)
            self.setStyleSheet(self.styleSheet() + _PRODUCT_QSS)
            self.workspace_router = WorkspaceRouter(self)
            self._install_product_pages()
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
            self.tabs.currentChanged.connect(self._product_tab_changed)
            self.workspace_router.workspace_changed.connect(self._workspace_changed)
            self._product_ready = True
            self._apply_u3_snapshot(self.application_context.snapshot)
            current = self._workspace_name(self.tabs.currentWidget()) or "import"
            self.workspace_router.open_workspace(current)
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
            self._replace_page("profiles_page", ProfileNestingPanel(self), "Optimaliseren")
            index = self.control_page.indexOf(self.optimization_page)
            if index >= 0:
                self.control_page.removeTab(index)
                self.optimization_page.setParent(None)
                self.optimization_page.deleteLater()
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
            ordered_pages = (
                (self.import_page, "Inlezen"),
                (self.project_page, "Viewer"),
                (self.edit_page, "Bewerken"),
                (self.converter_page, "Converteren"),
                (self.control_page, "Controleren"),
                (self.pdf_page, "PDF / Tekening"),
                (self.scribing_page, "Scribing"),
                (self.bom_excel_page, "BOM / Hoeveelheden"),
                (self.profiles_page, "Optimaliseren"),
                (self.production_workflow_page, "Productieworkflow"),
                (self.export_page, "Exporteren"),
            )
            for page, _title in ordered_pages:
                index = self.tabs.indexOf(page)
                if index >= 0:
                    self.tabs.removeTab(index)
            for page, title in ordered_pages:
                self.tabs.addTab(page, QtGui.QIcon(), title)
            self.tabs.tabBar().setExpanding(False)
            self.tabs.tabBar().setUsesScrollButtons(True)

        def _install_product_header(self) -> None:
            central = self.centralWidget()
            layout = central.layout() if central is not None else None
            if layout is None:
                return
            self.product_header = _ProductHeader(central)
            self.product_header.back_requested.connect(self.workspace_router.back)
            self.product_header.forward_requested.connect(self.workspace_router.forward)
            layout.insertWidget(0, self.product_header)

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
            for name, page in (
                ("import", self.import_page),
                ("viewer", self.project_page),
                ("edit", self.edit_page),
                ("converter", self.converter_page),
                ("control", self.control_page),
                ("pdf", self.pdf_page),
                ("scribing", self.scribing_page),
                ("bom", self.bom_excel_page),
                ("profile_nesting", self.profiles_page),
                ("production_workflow", self.production_workflow_page),
                ("export", self.export_page),
            ):
                self.workspace_router.register(name, page)

        def _install_context_ribbons(self) -> None:
            self.context_ribbons: dict[str, Any] = {}
            for workspace, page in self.workspace_router.pages.items():
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
                elif namespace == "edit":
                    self.edit_page.handle_ribbon(command)
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

        def _workspace_name(self, page: Any) -> str:
            return self.workspace_router.names_by_page.get(page, "")

        def _product_tab_changed(self, _index: int) -> None:
            if self._product_ready:
                self.workspace_router.observe_current_page(self.tabs.currentWidget())

        def _workspace_changed(self, workspace: str) -> None:
            self.status_workspace.setText(f"Workspace: {workspace.replace('_', ' ').title()}")
            self._place_shared_viewer(workspace)

        def _surface_for_current_tab(self) -> str:
            if hasattr(self, "workspace_router"):
                name = self._workspace_name(self.tabs.currentWidget())
                if name:
                    return "workbench" if name == "edit" else name
            return super()._surface_for_current_tab()

        def _apply_u3_snapshot(self, snapshot: Any) -> None:
            super()._apply_u3_snapshot(snapshot)
            if not hasattr(self, "status_project"):
                return
            project = snapshot.project_name or snapshot.project_id or "geen project"
            self.status_project.setText(f"Project: {project}")
            self.status_selection.setText(f"Selectie: {len(snapshot.selection.entity_ids)}")
            self.status_validation.setText(
                "Validatie: BLOCKED" if snapshot.integrity_blocking_codes else "Validatie: context OK"
            )
            selection = snapshot.selection if snapshot.project_attached else None
            workspace = self.workspace if snapshot.project_attached else None
            self.edit_page.set_context(self.workspace, snapshot.selection)
            self.pdf_page.set_context(self.workspace, snapshot.selection)
            self.bom_excel_page.set_context(workspace, selection)
            self.production_workflow_page.set_context(workspace, selection)

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
            if workspace in {"viewer", "import", "pdf", "drawing"}:
                home = self._cws_viewer_home_parent
                if viewer.parentWidget() is not home:
                    if isinstance(home, QtWidgets.QSplitter):
                        home.insertWidget(max(0, self._cws_viewer_home_index), viewer)
                    elif home is not None and home.layout() is not None:
                        home.layout().addWidget(viewer)
                viewer.setMinimumHeight(320)
                viewer.show()
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
                host.setStyleSheet("QFrame#module3dViewerHost{background:#e9eff6;border:1px solid #c8d4e2}")
                host_layout = QtWidgets.QVBoxLayout(host)
                host_layout.setContentsMargins(0, 0, 0, 0)
                host_layout.setSpacing(0)
                bar = QtWidgets.QHBoxLayout()
                label = QtWidgets.QLabel(f"3D MODEL - {workspace.upper()}")
                label.setStyleSheet("padding:5px 10px;color:#153b66;font-weight:700")
                bar.addWidget(label)
                bar.addStretch(1)
                hint = QtWidgets.QLabel("Een model, een selectie, Viewer V15")
                hint.setStyleSheet("padding-right:10px;color:#66798e")
                bar.addWidget(hint)
                host_layout.addLayout(bar)
                layout.insertWidget(min(1, layout.count()), host, 3)
                self._cws_module_viewer_hosts[page] = host
            viewer.setParent(host)
            host.layout().addWidget(viewer, 1)
            viewer.setMinimumHeight(310)
            viewer.show()

        def _restore_layout(self) -> None:
            settings = QtCore.QSettings("CWS", "CWS Convertor")
            geometry = settings.value("product-ui/geometry")
            if geometry:
                self.restoreGeometry(geometry)
            workspace = str(settings.value("product-ui/last-workspace", "import") or "import")
            if workspace in self.workspace_router.pages:
                self.tabs.setCurrentWidget(self.workspace_router.pages[workspace])

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

        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        application.setApplicationName(APP_NAME)
        application.setOrganizationName("CWS")
        if initial_paths is None:
            paths: tuple[Path, ...] = ()
        elif isinstance(initial_paths, (str, Path)):
            paths = (Path(initial_paths),)
        else:
            paths = tuple(Path(value) for value in initial_paths)
        window = CWSMainWindow(paths)
        window.show()
        return int(application.exec())

else:
    class CWSMainWindow(_U3MainWindow):  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    CwsConvertorMainWindow = CWSMainWindow
    ProductionWorkflowPanel = CWSMainWindow
    WorkspaceRouter = CWSMainWindow

    def run_qt_application(initial_paths: Iterable[str | Path] | str | Path | None = None) -> int:  # pragma: no cover
        del initial_paths
        require_qt()
        return 2


__all__ = [
    "CWSMainWindow",
    "CwsConvertorMainWindow",
    "ProductionWorkflowPanel",
    "U4_WORKFLOW_PROPERTY",
    "U4_WORKFLOW_TOKEN",
    "WorkspaceRouter",
    "run_qt_application",
]

# _CWS_VISUAL_PARITY_PATCH_V1
# A single light production visual language for every workspace.
if "CWSMainWindow" in globals():
    _cws_main_window_init = CWSMainWindow.__init__
    _cws_main_window_place_shared_viewer = getattr(CWSMainWindow, "_place_shared_viewer", None)

    _CWS_PRODUCTION_QSS = r"""
    QMainWindow, QWidget { background: #f7f9fc; color: #182d47; font-family: "Segoe UI"; font-size: 9pt; }
    QTabWidget::pane { border: 1px solid #d6e0ec; background: #ffffff; }
    QTabBar::tab { background: #ffffff; border: 0; border-bottom: 2px solid transparent; padding: 9px 15px; }
    QTabBar::tab:selected { color: #075dcb; border-bottom: 2px solid #0b6ee8; font-weight: 600; }
    QFrame#ribbonGroup, QFrame#settingsPanel, QFrame#modelPreview, QFrame#drawingSheetFrame {
        background: #ffffff; border: 1px solid #d6e0ec; border-radius: 2px;
    }
    QLabel#workspaceTitle { color: #075dcb; font-size: 13pt; font-weight: 600; }
    QLabel#sectionTitle { color: #18334f; font-size: 10.5pt; font-weight: 600; }
    QLabel#mutedText { color: #657b92; }
    QLabel#liveStatus { color: #138a4b; }
    QPushButton, QToolButton { background: #ffffff; border: 1px solid #c6d3e2; border-radius: 2px; padding: 6px 10px; }
    QPushButton:hover, QToolButton:hover { background: #edf5ff; border-color: #4b91e8; }
    QPushButton#primaryButton { background: #0868d7; color: #ffffff; border-color: #0868d7; font-weight: 600; }
    QPushButton#primaryButton:hover { background: #075ab9; }
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: #ffffff; border: 1px solid #c7d4e3; padding: 5px; min-height: 20px; }
    QTableView, QTreeView, QListWidget { background: #ffffff; alternate-background-color: #f6f9fd; border: 1px solid #d5dfeb; gridline-color: #e1e8f0; }
    QHeaderView::section { background: #eef3f9; color: #4f667e; border: 0; border-right: 1px solid #d8e1eb; padding: 6px; font-weight: 600; }
    QProgressBar { background: #e5edf6; border: 0; border-radius: 3px; text-align: center; }
    QProgressBar::chunk { background: #1597e5; border-radius: 3px; }
    QSplitter::handle { background: #d9e2ec; }
    """

    def _cws_main_window_init_with_visual_parity(self, *args, **kwargs):
        _cws_main_window_init(self, *args, **kwargs)
        self.setStyleSheet(self.styleSheet() + _CWS_PRODUCTION_QSS)
        project_page = getattr(self, "project_page", None)
        host = getattr(project_page, "host", None)
        if host is not None:
            host.setMinimumHeight(360)
        if project_page is not None and hasattr(project_page, "open_detached_viewer"):
            from PySide6.QtGui import QAction, QKeySequence

            detached_action = QAction("Viewer in apart venster", self)
            detached_action.setShortcut(QKeySequence("F11"))
            detached_action.triggered.connect(project_page.open_detached_viewer)
            self.addAction(detached_action)
            self._detached_viewer_shortcut = detached_action

    def _cws_place_shared_viewer_visible(self, workspace):
        """Keep QVTK in one parent; module pages get a bounded preview."""
        project_page = getattr(self, "project_page", None)
        viewer = getattr(project_page, "viewer", None)
        if viewer is None or getattr(project_page, "workspace", None) is None:
            return
        if not hasattr(self, "_cws_viewer_home_parent"):
            home = viewer.parentWidget()
            self._cws_viewer_home_parent = home
            self._cws_viewer_home_index = home.indexOf(viewer) if isinstance(home, QtWidgets.QSplitter) else -1
            self._cws_module_viewer_hosts = {}

        home = self._cws_viewer_home_parent
        if viewer.parentWidget() is not home:
            viewer.setParent(home)
            if isinstance(home, QtWidgets.QSplitter):
                home.insertWidget(max(0, self._cws_viewer_home_index), viewer)
            elif home is not None and home.layout() is not None:
                home.layout().addWidget(viewer)
        for existing_host in self._cws_module_viewer_hosts.values():
            existing_host.hide()
        if workspace == "viewer":
            viewer.setMinimumHeight(340)
            viewer.show()
            return

        preview_workspaces = {"edit", "converter", "control", "pdf", "drawings", "scribing", "bom", "report", "export", "profile_nesting", "production"}
        page = self.workspace_router.pages.get(workspace)
        if isinstance(page, QtWidgets.QTabWidget):
            page = page.currentWidget()
        if page is None or workspace not in preview_workspaces:
            viewer.hide()
            return
        page.setMaximumHeight(16777215)
        page.setMinimumHeight(560)
        layout = page.layout() if hasattr(page, "layout") else None
        if layout is None or not hasattr(layout, "insertWidget"):
            viewer.hide()
            return

        hosts = self._cws_module_viewer_hosts
        host = hosts.get(page)
        if host is None:
            host = QtWidgets.QFrame(page)
            host.setObjectName("module3dViewerPreview")
            host.setMinimumHeight(285)
            host.setMaximumHeight(410)
            host_layout = QtWidgets.QVBoxLayout(host)
            host_layout.setContentsMargins(0, 0, 0, 0)
            host_layout.setSpacing(0)
            header = QtWidgets.QHBoxLayout()
            label = QtWidgets.QLabel(f"3D MODEL - {workspace.upper()}")
            label.setObjectName("sectionTitle")
            label.setContentsMargins(10, 4, 0, 4)
            header.addWidget(label)
            header.addStretch(1)
            hint = QtWidgets.QLabel("Stabiele preview van Viewer V15")
            hint.setObjectName("mutedText")
            header.addWidget(hint)
            open_button = QtWidgets.QPushButton("Open volledige Viewer V15")
            open_button.clicked.connect(project_page.open_detached_viewer)
            header.addWidget(open_button)
            host_layout.addLayout(header)
            preview = QtWidgets.QLabel("3D-voorvertoning wordt opgebouwd...")
            preview.setObjectName("moduleViewerPreviewImage")
            preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            preview.setMinimumHeight(245)
            # Match the native V15 render background so the bounded preview reads
            # as one continuous viewport instead of a window inside a window.
            preview.setStyleSheet("background:#fdfefe;border:0;color:#38556f;")
            host_layout.addWidget(preview, 1)
            layout.insertWidget(min(1, layout.count()), host, 3)
            hosts[page] = host

        preview = host.findChild(QtWidgets.QLabel, "moduleViewerPreviewImage")
        if preview is not None:
            try:
                import tempfile
                from pathlib import Path
                output = Path(tempfile.gettempdir()) / "CWS_Convertor" / "module-viewer-preview.png"
                output.parent.mkdir(parents=True, exist_ok=True)
                viewer.controller.fit_all()
                viewer.controller.screenshot_to_file(output)
                pixmap = QtGui.QPixmap(str(output))
                if pixmap.isNull():
                    raise RuntimeError("lege viewer-preview")
                preview.setPixmap(pixmap.scaled(1800, 340, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
            except Exception as exc:
                preview.setText("3D-preview tijdelijk niet beschikbaar. Open de volledige Viewer V15.\n" f"{type(exc).__name__}: {exc}")
        host.show()
        viewer.hide()

    CWSMainWindow.__init__ = _cws_main_window_init_with_visual_parity
    if _cws_main_window_place_shared_viewer is not None:
        # Use the real shared QVTK instance. The screenshot-preview route above
        # produced a nested window and removed live orbit/selection/measurement
        # from module workspaces. The repaired native geometry makes the
        # original single-viewer router safe again.
        CWSMainWindow._place_shared_viewer = _cws_main_window_place_shared_viewer


# Final native-viewer layout contract.  The earlier U4 router remains the
# canonical placement implementation; this wrapper only removes geometry
# constraints that can make QVTK overlap neighbouring panes and adds the
# compact V15 navigation overlay to every routed 3D workspace.
_cws_native_viewer_router_base = CWSMainWindow._place_shared_viewer


def _cws_place_shared_viewer_native(self, workspace, *args, **kwargs):
    result = _cws_native_viewer_router_base(self, workspace, *args, **kwargs)

    import shiboken6

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QSplitter, QVBoxLayout

    from cws_viewer.ui_qt.trimble_navigation_overlay import install_trimble_navigation_overlay
    from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2

    route = str(workspace or "")
    viewer = self.findChild(VtkRealProjectWidgetFeelV2, "cwsVtkRealProjectWidget")
    if viewer is None:
        return result

    viewer.setMinimumSize(0, 0)
    viewer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    page = getattr(getattr(self, "workspace_router", None), "pages", {}).get(route)
    host = page.findChild(QFrame, "module3dViewerHost") if page is not None else None
    if host is not None:
        host.setMinimumHeight(260 if route == "pdf" else 300)
        host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        host_layout = host.layout()
        if host_layout is not None:
            host_layout.setContentsMargins(0, 0, 0, 0)
            host_layout.setSpacing(0)
            host_layout.setStretch(host_layout.indexOf(viewer), 1)

    def _finish_native_layout():
        if not shiboken6.isValid(viewer):
            return
        viewer.setMinimumSize(0, 0)
        parent = viewer.parentWidget()
        if isinstance(parent, QSplitter):
            parent.setChildrenCollapsible(False)
            parent.setStretchFactor(0, 29)
            parent.setStretchFactor(1, 47)
            parent.setStretchFactor(2, 24)
            width = max(780, parent.contentsRect().width())
            if parent.count() >= 3:
                parent.widget(0).setMaximumWidth(max(280, int(width * 0.30)))
                parent.widget(2).setMaximumWidth(max(240, int(width * 0.26)))
                viewer.setMinimumWidth(min(360, max(260, int(width * 0.30))))
            parent.setSizes([max(240, int(width * 0.29)), max(360, int(width * 0.47)), max(220, int(width * 0.24))])
        viewer.updateGeometry()
        resize_renderer = getattr(viewer, "_apply_cws_pending_resize", None)
        if callable(resize_renderer):
            resize_renderer()
        render = getattr(viewer, "Render", None)
        if callable(render) and route != "import":
            render()
        overlay = install_trimble_navigation_overlay(viewer)
        overlay.reposition()

    if route != "import":
        viewer.show()
        install_trimble_navigation_overlay(viewer)
        QTimer.singleShot(0, _finish_native_layout)
        QTimer.singleShot(40, _finish_native_layout)
        QTimer.singleShot(250, _finish_native_layout)
        QTimer.singleShot(750, _finish_native_layout)
    return result


CWSMainWindow._place_shared_viewer = _cws_place_shared_viewer_native
