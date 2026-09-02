"""Primary integrated PySide6 desktop application for CWS Convertor V9.

The Qt shell is intentionally a composition layer.  It never imports IFC/STEP
sources independently and it never owns production truth.  Project, viewer,
property grid, BOM, PDF review and exact Part Workbench all bind to the same
:class:`IntegratedProjectWorkspace` and therefore to one Canonical Project
Model instance.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from cws_convertor.product import APP_VERSION
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

# Explicit integration contract used by diagnostics and packaging tests.  The
# concrete widgets are constructed by IntegratedProjectWorkspaceWidget so this
# shell remains a composition layer.
_INTEGRATED_SURFACE_CONTRACT = (
    "ProfessionalPropertyGridPanel",
    "VtkRealProjectWidget",
    "ExactPartWorkbenchPanel",
)

_QSS = """
QMainWindow, QWidget { background:#f5f7fa; color:#172033; font-family:'Segoe UI'; font-size:9pt; }
QMenuBar { background:#ffffff; border-bottom:1px solid #d8dee8; }
QMenuBar::item:selected, QMenu::item:selected { background:#e8f1ff; color:#064fb2; }
QTabWidget::pane { border:1px solid #cfd7e3; background:#ffffff; top:-1px; }
QTabBar::tab { background:#eef2f7; color:#334155; padding:8px 11px; border:1px solid #d7dee8; border-bottom:0; }
QTabBar::tab:selected { background:#ffffff; color:#0759c7; border-top:3px solid #0759c7; padding-top:6px; font-weight:600; }
QTabBar::tab:hover:!selected { background:#e3ebf5; }
QToolBar { background:#ffffff; border:1px solid #d8dee8; spacing:3px; padding:4px; }
QPushButton, QToolButton { background:#ffffff; color:#1f2937; border:1px solid #bdc8d8; border-radius:4px; padding:5px 9px; }
QPushButton:hover, QToolButton:hover { background:#edf4ff; border-color:#6c9fe2; }
QPushButton:disabled, QToolButton:disabled { color:#98a2b3; background:#f1f3f6; }
QPushButton#primaryButton { background:#0759c7; color:#ffffff; border-color:#0759c7; font-weight:600; }
QPushButton#primaryButton:hover { background:#064da9; }
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QPlainTextEdit, QListWidget, QTreeWidget, QTableView {
  background:#ffffff; color:#172033; border:1px solid #c8d1dd; selection-background-color:#cfe2ff; selection-color:#10233d;
}
QHeaderView::section { background:#e9eef5; color:#25364d; border:0; border-right:1px solid #d3dae4; border-bottom:1px solid #c8d1dd; padding:5px; font-weight:600; }
QGroupBox { border:1px solid #d5dce6; border-radius:5px; margin-top:8px; padding-top:8px; font-weight:600; }
QGroupBox::title { subcontrol-origin:margin; left:8px; padding:0 4px; }
QStatusBar { background:#ffffff; color:#475569; border-top:1px solid #d8dee8; }
QLabel#workspaceTitle { font-size:15px; font-weight:700; color:#0b4ea2; }
QLabel#selectionName { font-weight:700; color:#0b4ea2; }
QLabel#mutedText { color:#667085; }
QLabel#selectionContext, QFrame#selectionContext { background:#edf4ff; border:1px solid #b9d2f5; border-radius:4px; padding:6px; }
QFrame#warningPanel { background:#fff7e6; border:1px solid #e5b85c; border-radius:5px; }
QLabel#panelHeading { color:#8a5700; font-weight:700; }
QLabel#cwsSafety { background:#fff5d9; color:#754c00; border:1px solid #dfbf68; border-radius:4px; padding:7px; font-weight:600; }
"""


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()
    from cws_convertor.integration.ui_context import UnifiedApplicationContext
    from .converter_panel import ConverterPanel
    from .functional_workspaces import DrawingWorkspacePanel, EditWorkspacePanel
    from .pdf_panel import PDFPanel
    from .phase3_workspaces import Phase3ExportCenterPanel, ProfileNestingPanel, ScribingWorkspacePanel
    from .product_workspaces import (
        BomWorkspacePanel,
        ProductionWorkflowPanel,
    )
    from .project_workspace import IntegratedProjectWorkspaceWidget
    from .workspace_pages import (
        ContextActionPage,
        ExportPanel,
        ImportPanel,
        OptimizationPanel,
        ProfilesPanel,
    )

    class WorkspaceRouter(QtCore.QObject):
        """Single history-aware workspace route; the permanent ViewerHost is never moved."""

        workspace_changed = QtCore.Signal(str)

        def __init__(self, tabs: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.tabs = tabs
            self.pages: dict[str, Any] = {}
            self.names_by_page: dict[Any, str] = {}
            self.history: list[str] = []
            self.history_index = -1
            self._routing = False

        def register(self, name: str, page: Any) -> None:
            key = str(name).strip().lower()
            self.pages[key] = page
            self.names_by_page[page] = key

        def open_workspace(self, name: str, *, record: bool = True) -> bool:
            key = str(name).strip().lower()
            page = self.pages.get(key)
            if page is None:
                return False
            self._routing = True
            try:
                self.tabs.setCurrentWidget(page)
            finally:
                self._routing = False
            if record:
                self.history = self.history[: self.history_index + 1]
                if not self.history or self.history[-1] != key:
                    self.history.append(key)
                self.history_index = len(self.history) - 1
            self.workspace_changed.emit(key)
            return True

        def observe_current_page(self, page: Any) -> None:
            if not self._routing and page in self.names_by_page:
                self.open_workspace(self.names_by_page[page])

        def back(self) -> None:
            if self.history_index > 0:
                self.history_index -= 1
                self.open_workspace(self.history[self.history_index], record=False)

        def forward(self) -> None:
            if self.history_index + 1 < len(self.history):
                self.history_index += 1
                self.open_workspace(self.history[self.history_index], record=False)

    class _StartPage(QtWidgets.QWidget):
        open_project_requested = QtCore.Signal()
        open_models_requested = QtCore.Signal()

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(32, 32, 32, 32)
            root.setSpacing(14)
            hero = QtWidgets.QLabel("CWS Convertor")
            hero.setObjectName("cwsHero")
            root.addWidget(hero)
            sub = QtWidgets.QLabel(
                "Converteren · projectmodellen · viewer · Part Workbench · BOM · tekeningen"
            )
            sub.setObjectName("cwsSubHero")
            root.addWidget(sub)
            safety = QtWidgets.QLabel(
                "Productieveiligheid: AI en viewer adviseren en visualiseren. "
                "Exacte geometrie, roundtrips en formaatgates blijven deterministisch."
            )
            safety.setObjectName("cwsSafety")
            safety.setWordWrap(True)
            root.addWidget(safety)
            cards = QtWidgets.QHBoxLayout()
            project = QtWidgets.QPushButton(
                "Project / Productie openen\n.cwscproj + totaalmodel"
            )
            project.setMinimumHeight(110)
            project.clicked.connect(self.open_project_requested)
            converter = QtWidgets.QPushButton(
                "Losse modellen converteren\nNC1 · STEP · IFC"
            )
            converter.setMinimumHeight(110)
            converter.clicked.connect(self.open_models_requested)
            cards.addWidget(project)
            cards.addWidget(converter)
            root.addLayout(cards)
            info = QtWidgets.QPlainTextEdit()
            info.setReadOnly(True)
            info.setPlainText(
                "V9 geïntegreerde hoofdbuild\n\n"
                "• één Canonical Project Model\n"
                "• één ProjectScene-adapter\n"
                "• professionele V8-grid\n"
                "• VTK-totaalmodelviewer\n"
                "• experimentele exacte V6-Part Workbench\n"
                "• V7 revisie-/impactservices\n"
                "• bestaande conversiekern en PDF/AI-services\n\n"
                "production release vanuit viewer = NEE\n"
                "Niet-ondersteunde externe productiefeatures blijven geblokkeerd."
            )
            root.addWidget(info, 1)

    class _ValidationPage(QtWidgets.QWidget):
        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)
            title = QtWidgets.QLabel("Validatie & runtime-diagnose")
            title.setStyleSheet("font-size:20px;font-weight:700")
            root.addWidget(title)
            self.run = QtWidgets.QPushButton("Native/runtime-selftest uitvoeren")
            self.run.clicked.connect(self._run)
            root.addWidget(self.run)
            self.output = QtWidgets.QPlainTextEdit()
            self.output.setReadOnly(True)
            root.addWidget(self.output, 1)

        def _run(self) -> None:
            self.run.setEnabled(False)
            self.output.setPlainText("Selftest wordt uitgevoerd …")
            QtWidgets.QApplication.processEvents()
            try:
                from cws_viewer.selftest import run_self_test
                import json

                report = run_self_test(deep_native=True)
                self.output.setPlainText(
                    json.dumps(report.to_dict(), indent=2, ensure_ascii=False, default=str)
                )
            except Exception as exc:
                self.output.setPlainText(f"FAILED\n{type(exc).__name__}: {exc}")
            finally:
                self.run.setEnabled(True)

    class _BOMExcelPage(QtWidgets.QWidget):
        """Read-only BOM/Excel surface over the active integrated workspace."""

        show_project_requested = QtCore.Signal()

        def __init__(self, project_page: "IntegratedProjectWorkspaceWidget", parent: Any | None = None) -> None:
            super().__init__(parent)
            self.project_page = project_page
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(14, 14, 14, 14)
            title = QtWidgets.QLabel("BOM / Excel")
            title.setStyleSheet("font-size:20px;font-weight:700")
            root.addWidget(title)
            actions = QtWidgets.QHBoxLayout()
            refresh = QtWidgets.QPushButton("Actieve project-BOM vernieuwen")
            refresh.clicked.connect(self.refresh)
            export = QtWidgets.QPushButton("BOM-pakket exporteren")
            export.clicked.connect(project_page.export_bom)
            show = QtWidgets.QPushButton("Terug naar Project / Productie")
            show.clicked.connect(self.show_project_requested)
            actions.addWidget(refresh)
            actions.addWidget(export)
            actions.addWidget(show)
            actions.addStretch(1)
            root.addLayout(actions)
            self.output = QtWidgets.QPlainTextEdit()
            self.output.setReadOnly(True)
            root.addWidget(self.output, 1)
            self.refresh()

        def refresh(self) -> None:
            workspace = self.project_page.workspace
            if workspace is None:
                self.output.setPlainText(
                    "Open eerst een .cwscproj-project. De BOM gebruikt daarna exact dezelfde "
                    "Canonical Project Model-instance als tree, grid en 3D-viewer."
                )
                return
            snapshot = workspace.bom_snapshot
            lines = [
                f"Project: {snapshot.project_name}",
                f"Snapshot SHA-256: {snapshot.snapshot_sha256}",
                f"Traceability: {len(snapshot.traceability):,} entiteiten",
                "",
            ]
            lines.extend(f"{key}: {value}" for key, value in sorted(snapshot.summary.items()))
            lines.extend(["", "Productievrijgave vanuit BOM-tab: niet toegestaan."])
            self.output.setPlainText("\n".join(map(str, lines)))

    class _RevisionComparePage(QtWidgets.QWidget):
        """Functional V7 revision compare over two verified .cwscproj files."""

        show_project_requested = QtCore.Signal()

        def __init__(self, project_page: "IntegratedProjectWorkspaceWidget", parent: Any | None = None) -> None:
            super().__init__(parent)
            self.project_page = project_page
            self.report = None
            self.compare_panel = None
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(14, 14, 14, 14)
            title = QtWidgets.QLabel("Revisies / Compare")
            title.setStyleSheet("font-size:20px;font-weight:700")
            root.addWidget(title)
            safety = QtWidgets.QLabel(
                "Revisiecompare gebruikt stabiele Canonical entity-ID's, bronidentiteit en "
                "manufacturing hashes. Het resultaat is review-/impactbewijs en geen productievrijgave."
            )
            safety.setWordWrap(True)
            safety.setObjectName("cwsSafety")
            root.addWidget(safety)

            form = QtWidgets.QGridLayout()
            self.old_path = QtWidgets.QLineEdit(); self.old_path.setReadOnly(True)
            self.new_path = QtWidgets.QLineEdit(); self.new_path.setReadOnly(True)
            old_choose = QtWidgets.QPushButton("Oude revisie kiezen")
            new_choose = QtWidgets.QPushButton("Nieuwe revisie kiezen")
            active_new = QtWidgets.QPushButton("Actief project als nieuw")
            self.compare = QtWidgets.QPushButton("Vergelijken")
            self.export = QtWidgets.QPushButton("Comparemanifest exporteren")
            self.export.setEnabled(False)
            form.addWidget(QtWidgets.QLabel("Oud"), 0, 0)
            form.addWidget(self.old_path, 0, 1)
            form.addWidget(old_choose, 0, 2)
            form.addWidget(QtWidgets.QLabel("Nieuw"), 1, 0)
            form.addWidget(self.new_path, 1, 1)
            form.addWidget(new_choose, 1, 2)
            form.addWidget(active_new, 2, 1)
            form.addWidget(self.compare, 2, 2)
            form.addWidget(self.export, 2, 3)
            root.addLayout(form)

            self.status = QtWidgets.QLabel("Kies twee revisies van hetzelfde CWS-project")
            root.addWidget(self.status)
            self.host = QtWidgets.QStackedWidget()
            self.empty = QtWidgets.QPlainTextEdit(); self.empty.setReadOnly(True)
            self.host.addWidget(self.empty)
            root.addWidget(self.host, 1)

            old_choose.clicked.connect(lambda: self._choose(self.old_path, "Oude revisie"))
            new_choose.clicked.connect(lambda: self._choose(self.new_path, "Nieuwe revisie"))
            active_new.clicked.connect(self._use_active_as_new)
            self.compare.clicked.connect(self._compare)
            self.export.clicked.connect(self._export)
            self.refresh()

        def _choose(self, target: Any, title: str) -> None:
            name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, title, "", "CWS-project (*.cwscproj)"
            )
            if name:
                target.setText(str(Path(name).expanduser().resolve()))

        def _use_active_as_new(self) -> None:
            workspace = self.project_page.workspace
            if workspace is None:
                QtWidgets.QMessageBox.information(self, "Revisies", "Open eerst een actief project.")
                return
            self.new_path.setText(str(workspace.project_path))

        def refresh(self) -> None:
            workspace = self.project_page.workspace
            if workspace is not None and not self.new_path.text().strip():
                self.new_path.setText(str(workspace.project_path))
            if self.report is None:
                self.empty.setPlainText(
                    "Selecteer een oude en nieuwe .cwscproj-revisie. De vergelijking classificeert "
                    "onderdelen als unchanged, added, removed, moved, changed of ambiguous en "
                    "berekent de impact op productieartefacten.\n\n"
                    "Viewercompare kan productie nooit vrijgeven."
                )

        def _compare(self) -> None:
            old = Path(self.old_path.text()).expanduser()
            new = Path(self.new_path.text()).expanduser()
            if not old.is_file() or not new.is_file():
                QtWidgets.QMessageBox.information(self, "Revisies", "Kies twee bestaande projectbestanden.")
                return
            self.compare.setEnabled(False)
            self.status.setText("Projecten worden volledig geverifieerd en vergeleken …")
            QtWidgets.QApplication.processEvents()
            try:
                from cws_convertor.project.service import ProjectSession
                from cws_viewer.revisions.project_compare import compare_project_revisions
                from cws_viewer.ui_qt.revision_compare import RevisionComparePanel

                with ProjectSession.open(old, read_only=True) as old_session, ProjectSession.open(new, read_only=True) as new_session:
                    report = compare_project_revisions(old_session.project, new_session.project)
                self.report = report
                panel = RevisionComparePanel(report)
                panel.change_selected.connect(self._change_selected)
                self.host.addWidget(panel)
                self.host.setCurrentWidget(panel)
                if self.compare_panel is not None:
                    previous = self.compare_panel
                    self.host.removeWidget(previous)
                    previous.deleteLater()
                self.compare_panel = panel
                counts = ", ".join(f"{key}: {value}" for key, value in report.counts.items() if value)
                self.status.setText(
                    f"Compare gereed · {counts or 'geen wijzigingen'} · "
                    f"blokkades: {len(report.blocking_codes)}"
                )
                self.export.setEnabled(True)
            except Exception as exc:
                self.report = None
                self.export.setEnabled(False)
                self.status.setText(f"Vergelijking mislukt: {type(exc).__name__}: {exc}")
                QtWidgets.QMessageBox.critical(self, "Revisiecompare", f"{type(exc).__name__}: {exc}")
            finally:
                self.compare.setEnabled(True)

        def _change_selected(self, change_id: str) -> None:
            if self.report is None or self.project_page.workspace is None:
                return
            change = next((item for item in self.report.changes if item.change_id == change_id), None)
            if change is None:
                return
            candidates = tuple(
                value for value in (change.new_entity_id, change.old_entity_id) if value
            )
            active_parts = self.project_page.workspace.project.parts
            entity_id = next((value for value in candidates if value in active_parts), None)
            if entity_id:
                self.project_page.workspace.interaction.select_entities(
                    (entity_id,), origin="revision_compare"
                )
                self.show_project_requested.emit()

        def _export(self) -> None:
            if self.report is None:
                return
            name, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Comparemanifest opslaan", "CWS_Revision_Compare.json", "JSON (*.json)"
            )
            if not name:
                return
            path = Path(name)
            if path.suffix.lower() != ".json":
                path = path.with_suffix(".json")
            try:
                from cws_viewer.revisions.manifest import write_compare_manifest
                write_compare_manifest(path, self.report)
                self.status.setText(f"Comparemanifest met SHA-256 opgeslagen: {path}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Comparemanifest", f"{type(exc).__name__}: {exc}")

    class _ApplicationContextStrip(QtWidgets.QFrame):
        """Small read-only projection of the shared application context."""

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(8, 2, 8, 2)
            layout.setSpacing(12)
            self.project = QtWidgets.QLabel("Geen project")
            self.surface = QtWidgets.QLabel("Werkruimte: intake")
            self.selection = QtWidgets.QLabel("Selectie: geen")
            for label in (self.project, self.surface, self.selection):
                layout.addWidget(label)

        def apply_snapshot(self, snapshot: Any) -> None:
            project_id = snapshot.project_context.active_project_id or "geen"
            primary = snapshot.selection.primary_entity_id or "geen"
            self.project.setText(f"Project: {project_id}")
            self.surface.setText(f"Werkruimte: {snapshot.workspace_context.active_workspace}")
            self.selection.setText(f"Selectie: {primary}")


    class CWSMainWindow(QtWidgets.QMainWindow):
        """One-process CWS Convertor shell with integrated project viewer."""

        def __init__(self, initial_paths: Iterable[str | Path] = ()) -> None:
            super().__init__()
            self.setObjectName("cwsConvertorUnifiedU4MainWindow")
            self.setWindowTitle(f"CWS Convertor {APP_VERSION}")
            self.resize(1760, 1040)
            self.setMinimumSize(1280, 760)
            self.setStyleSheet(_QSS)
            self.application_context = UnifiedApplicationContext(active_surface="intake")
            self.job_manager = self.application_context.job_manager
            self._context_unsubscribe = None
            self._selection_unsubscribe = None
            self._intake_thread = None
            self._intake_job_id = None
            self._intake_worker = None
            self.tabs = QtWidgets.QTabWidget()
            self.tabs.setDocumentMode(True)
            self.tabs.setMovable(False)
            self.tabs.tabBar().setExpanding(False)

            self.import_page = ImportPanel()
            self.project_page = IntegratedProjectWorkspaceWidget()
            self.project_page.set_job_manager(self.job_manager)
            self.viewer_page = ContextActionPage(
                "Viewer",
                actions=(("Fit selectie", "properties"), ("Open Part Workbench", "open_exact")),
            )
            self.edit_page = EditWorkspacePanel()
            self.converter_page = ConverterPanel()
            self.converter_page.set_job_manager(self.job_manager)
            self.validation_page = _ValidationPage()
            self.revisions_page = _RevisionComparePage(self.project_page)
            self.optimization_page = ProfileNestingPanel(self)
            self.control_page = QtWidgets.QTabWidget()
            self.control_page.addTab(self.validation_page, "Validatie")
            self.control_page.addTab(self.revisions_page, "Revisies / Compare")
            self.control_page.addTab(self.optimization_page, "Optimalisatie")
            self.pdf_page = PDFPanel()
            self.profiles_page = ProfilesPanel()
            self.drawings_page = DrawingWorkspacePanel()
            self.scribing_page = ScribingWorkspacePanel(self)
            self.bom_excel_page = BomWorkspacePanel(self)
            self.production_workflow_page = ProductionWorkflowPanel(self)
            self.export_page = Phase3ExportCenterPanel(self.project_page, None, job_manager=self.job_manager)

            # Keep one permanent project/viewer instance beside the functional
            # workspaces. This is the established product layout: the live
            # project context stays available while editing, checking and
            # producing output, without duplicating or reparenting the VTK view.
            self.viewer_host = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            self.viewer_host.setObjectName("cwsPermanentViewerWorkspaceHost")
            self.viewer_host.setChildrenCollapsible(False)
            self.viewer_host.addWidget(self.project_page)
            self.viewer_host.addWidget(self.tabs)
            self.viewer_host.setStretchFactor(0, 3)
            self.viewer_host.setStretchFactor(1, 2)
            self.viewer_host.setSizes((1050, 710))
            self.setCentralWidget(self.viewer_host)

            style = self.style()
            tab_specs = (
                (self.import_page, "Inlezen", QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton),
                (self.viewer_page, "Viewer / Project", QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon),
                (self.edit_page, "Bewerken", QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView),
                (self.converter_page, "Converteren", QtWidgets.QStyle.StandardPixmap.SP_BrowserReload),
                (self.control_page, "Controleren", QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton),
                (self.pdf_page, "PDF review", QtWidgets.QStyle.StandardPixmap.SP_FileIcon),
                (self.profiles_page, "Profielen", QtWidgets.QStyle.StandardPixmap.SP_DirIcon),
                (self.drawings_page, "Tekeningen", QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView),
                (self.scribing_page, "Scribing", QtWidgets.QStyle.StandardPixmap.SP_CommandLink),
                (self.bom_excel_page, "Hoeveelheden / Excel", QtWidgets.QStyle.StandardPixmap.SP_FileDialogListView),
                (self.production_workflow_page, "Rapport", QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton),
                (self.export_page, "Exporteren", QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton),
            )
            for page, title, icon in tab_specs:
                self.tabs.addTab(page, style.standardIcon(icon), title)
            for page in (
                self.project_page,
                self.edit_page,
                self.converter_page,
                self.pdf_page,
                self.drawings_page,
                self.scribing_page,
                self.bom_excel_page,
                self.production_workflow_page,
                self.export_page,
            ):
                page.setProperty("cwsApplicationContext", "CWS-APPLICATION-CONTEXT-2")
            self.production_workflow_page.setProperty(
                "cwsUnifiedProductionWorkflow", "CWS-SINGLE-PRODUCT-SHELL-2"
            )
            self.workspace_router = WorkspaceRouter(self.tabs, self)
            for name, page in (
                ("intake", self.import_page), ("viewer", self.viewer_page),
                ("edit", self.edit_page), ("converter", self.converter_page),
                ("control", self.control_page), ("pdf_review", self.pdf_page),
                ("profiles", self.profiles_page),
                ("profile_nesting", self.optimization_page), ("drawing", self.drawings_page),
                ("scribing", self.scribing_page), ("bom", self.bom_excel_page),
                ("report", self.production_workflow_page), ("export", self.export_page),
            ):
                self.workspace_router.register(name, page)
            self._create_menu()
            self._create_status()
            self.context_strip = _ApplicationContextStrip(self)
            self._u3_bom_context = self.context_strip.selection
            self.statusBar().addPermanentWidget(self.context_strip, 1)
            self._context_unsubscribe = self.application_context.subscribe(
                self._context_snapshot_changed,
                emit_current=True,
            )
            self.import_page.project_requested.connect(lambda value: self._open_project(Path(value)))
            self.import_page.models_requested.connect(self._queue_models)
            self.import_page.pdf_requested.connect(self._open_pdf)
            self.project_page.project_loaded.connect(self._project_loaded)
            self.project_page.load_progress.connect(self._project_load_progress)
            self.project_page.project_closed.connect(self._project_closed)
            self.project_page.selection_changed.connect(self._selection_changed)
            self.project_page.action_requested.connect(self._route_action)
            self.viewer_page.action_requested.connect(self._route_action)
            self.edit_page.action_requested.connect(self._route_action)
            self.drawings_page.action_requested.connect(self._route_action)
            self.scribing_page.action_requested.connect(self._route_action)
            self.profiles_page.action_requested.connect(self._route_action)
            self.optimization_page.action_requested.connect(self._route_action)
            self.bom_excel_page.action_requested.connect(self._route_action)
            self.production_workflow_page.action_requested.connect(self._route_action)
            self.bom_excel_page.show_project_requested.connect(
                lambda: self.workspace_router.open_workspace("viewer")
            )
            self.revisions_page.show_project_requested.connect(
                lambda: self.workspace_router.open_workspace("viewer")
            )
            self.pdf_page.feature_highlight_requested.connect(self._highlight_pdf_feature)
            self.tabs.currentChanged.connect(
                lambda _index: self.workspace_router.observe_current_page(self.tabs.currentWidget())
            )
            self.workspace_router.workspace_changed.connect(self._workspace_changed)
            self._selection_changed(None)
            self.workspace_router.open_workspace("intake")
            initial = tuple(
                Path(value).expanduser().resolve()
                for value in initial_paths
                if str(value).strip()
            )
            if initial:
                QtCore.QTimer.singleShot(0, lambda values=initial: self.open_initial_paths(values))

        def open_initial_paths(self, paths: Iterable[str | Path]) -> None:
            """Route file-association/shell inputs into the integrated surfaces."""
            values = tuple(Path(value).expanduser().resolve() for value in paths)
            self.import_page.add_paths(values)
            project = next(
                (path for path in values if path.suffix.lower() == ".cwscproj" and path.is_file()),
                None,
            )
            models = tuple(
                path for path in values
                if path.suffix.lower() in {".nc", ".nc1", ".step", ".stp", ".ifc"}
                and path.is_file()
            )
            pdf = next(
                (path for path in values if path.suffix.lower() == ".pdf" and path.is_file()),
                None,
            )
            if project is not None:
                self._open_project(project)
            if models:
                if project is None:
                    self._queue_models(models)
                else:
                    self.converter_page.add_files(models)
            if pdf is not None and self.pdf_page.load_pdf(pdf):
                if project is None and not models:
                    self.tabs.setCurrentWidget(self.pdf_page)

        def _queue_models(self, values: Iterable[str | Path]) -> None:
            paths = [str(Path(value).resolve()) for value in values]
            self.converter_page.add_files(paths)
            if self._intake_job_id is not None:
                active = self.job_manager.get(self._intake_job_id)
                if active.status in {"queued", "running"}:
                    self.statusBar().showMessage("Er wordt al een modelproject opgebouwd.", 5000)
                    return

            from cws_convertor.ui_qt.project_intake import ModelIntakeWorker, suggest_project_path

            first = Path(paths[0])
            name_widget = getattr(self.import_page, "project_name", None)
            number_widget = getattr(self.import_page, "project_number", None)
            material_widget = getattr(self.import_page, "material", None)
            project_name = name_widget.text().strip() if name_widget is not None else first.stem
            project_name = project_name or first.stem
            project_number = number_widget.text().strip() if number_widget is not None else ""
            material = material_widget.currentText().strip() if material_widget is not None else "S355JR"
            target = suggest_project_path(project_name)

            self.tabs.setCurrentWidget(self.import_page)
            self.statusBar().showMessage("Modelbestanden worden ingelezen en voor Viewer V15 opgebouwd...")
            open_button = getattr(self.import_page, "open_button", None)
            if open_button is not None:
                open_button.setEnabled(False)

            worker = ModelIntakeWorker(
                paths,
                str(target),
                {
                    "project_name": project_name,
                    "project_number": project_number,
                    "material": material,
                },
            )
            worker.progress.connect(self.statusBar().showMessage)
            worker.progress_detail.connect(self._model_intake_progress)
            worker.completed.connect(self._model_intake_completed)
            worker.failed.connect(self._model_intake_failed)
            worker.finished.connect(self._model_intake_finished)
            worker.finished.connect(worker.deleteLater)
            self._intake_worker = worker
            self._intake_job_id = self.job_manager.submit(
                "project_open_import",
                lambda context: (context.stage("semantic_import", 0.01, "Modelinname gestart"), worker.run())[1],
                description=f"Project opbouwen uit {len(paths)} modelbestand(en)",
                project_id=project_name,
                metadata={"stage_contract": "semantic_tree_to_progressive_geometry"},
                max_retries=1,
            )

        @QtCore.Slot(str, object)
        def _model_intake_completed(self, project_path: str, payload: object) -> None:
            del payload
            self._load_progress_changed(72, "Projectcontainer gereed; Viewer V15 wordt geopend")
            self._open_project(Path(project_path), progress_floor=72)
            self.workspace_router.open_workspace("viewer")
            self.statusBar().showMessage(
                f"Projectcontainer gereed; Viewer V15 bouwt de scene: {Path(project_path).name}"
            )

        @QtCore.Slot(int, str)
        def _model_intake_progress(self, percent: int, message: str) -> None:
            scaled = min(72, max(1, int(percent * 0.72)))
            self._load_progress_changed(scaled, f"Inlezen: {message}")

        @QtCore.Slot(int, str)
        def _project_load_progress(self, percent: int, message: str) -> None:
            floor = max(0, min(95, int(getattr(self, "_project_progress_floor", 0))))
            mapped = floor + int(max(0, min(100, percent)) * (100 - floor) / 100)
            self._load_progress_changed(mapped, message)

        @QtCore.Slot(str)
        def _model_intake_failed(self, message: str) -> None:
            self._load_progress_failed(f"Modelinname mislukt: {message}")
            self.statusBar().showMessage("Modelinname mislukt", 10000)
            QtWidgets.QMessageBox.critical(self, "Model inladen mislukt", message)

        @QtCore.Slot()
        def _model_intake_finished(self) -> None:
            open_button = getattr(self.import_page, "open_button", None)
            if open_button is not None:
                open_button.setEnabled(True)
            self._intake_worker = None
            self._intake_thread = None
            self._intake_job_id = None

        def _open_pdf(self, value: str | Path) -> None:
            if self.pdf_page.load_pdf(value):
                self.tabs.setCurrentWidget(self.pdf_page)

        @property
        def workspace(self) -> Any | None:
            return self.project_page.workspace

        @property
        def context_snapshot(self) -> Any:
            return self.application_context.snapshot

        def _context_snapshot_changed(self, snapshot: Any) -> None:
            self.context_strip.apply_snapshot(snapshot)

        def _workspace_changed(self, workspace_name: str) -> None:
            canonical_name = {
                "edit": "workbench",
                "report": "production_workflow",
            }.get(str(workspace_name), str(workspace_name))
            self.application_context.set_active_surface(canonical_name)

        def _project_loaded(self, path: str) -> None:
            self.statusBar().showMessage(f"Project geopend: {path}")
            self._load_progress_changed(100, "Project, geometrie en Viewer V15 volledig gereed")
            QtCore.QTimer.singleShot(3000, self._hide_load_progress)
            from cws_viewer.ui_qt.trimble_navigation_overlay import (
                install_trimble_navigation_overlay,
            )
            from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import (
                VtkRealProjectWidgetFeelV2,
            )

            def install_navigation() -> None:
                viewer = self.project_page.findChild(
                    VtkRealProjectWidgetFeelV2,
                    "cwsVtkRealProjectWidget",
                )
                if viewer is not None:
                    navigation = install_trimble_navigation_overlay(viewer)
                    navigation.reposition()

            for delay_ms in (0, 100, 350, 1000):
                QtCore.QTimer.singleShot(delay_ms, install_navigation)
            self.bom_excel_page.refresh()
            self.revisions_page.refresh()
            if self._selection_unsubscribe is not None:
                self._selection_unsubscribe()
                self._selection_unsubscribe = None
            if self.workspace is not None:
                self.application_context.attach_workspace(self.workspace)
                self._selection_unsubscribe = self.workspace.interaction.subscribe(
                    self._selection_changed
                )
                self._selection_changed(self.workspace.interaction.selection)

        def _project_closed(self) -> None:
            if self._selection_unsubscribe is not None:
                self._selection_unsubscribe()
                self._selection_unsubscribe = None
            self.application_context.detach_workspace()
            self.bom_excel_page.refresh()
            self.revisions_page.refresh()
            self._selection_changed(None)

        def _selection_changed(self, selection: Any | None) -> None:
            workspace = self.workspace
            if workspace is not None:
                if self.application_context.workspace is not workspace:
                    self.application_context.attach_workspace(workspace)
                snapshot = self.application_context.ingest_interaction_selection(selection)
                selection = snapshot.selection
            self.converter_page.set_project_selection(workspace, selection)
            self.pdf_page.show_project_selection(selection or object())
            self.edit_page.set_context(workspace, selection)
            self.drawings_page.set_context(workspace, selection)
            self.scribing_page.set_context(workspace, selection)
            self.profiles_page.set_context(workspace, selection)
            if self.optimization_page is not self.profiles_page:
                self.optimization_page.set_context(workspace, selection)
            self.bom_excel_page.set_context(workspace, selection)
            self.production_workflow_page.set_context(workspace, selection)
            self.export_page.set_context(workspace, selection)

        def _route_action(self, action: str) -> None:
            routes = {
                "properties": "viewer", "viewer": "viewer", "edit": "edit",
                "convert": "converter", "validate": "control", "pdf": "pdf_review",
                "profiles": "profiles", "drawings": "drawing",
                "scribing": "scribing", "quantities": "bom", "bom": "bom",
                "report": "report", "export": "export", "print": "pdf_review",
            }
            if action == "open_exact":
                self.project_page.open_exact_workbench()
                return
            if action == "legacy_profiles":
                self._launch_legacy_ui()
                return
            route = routes.get(str(action))
            if route is not None:
                self.workspace_router.open_workspace(route)

        def _highlight_pdf_feature(self, entity_id: str, feature_id: str) -> None:
            if self.workspace is None:
                QtWidgets.QMessageBox.information(
                    self, "PDF-feature", "Open eerst het bijbehorende CWS-project."
                )
                return
            if entity_id not in self.workspace.project.parts:
                QtWidgets.QMessageBox.warning(
                    self, "PDF-feature", f"Onderdeel {entity_id} bestaat niet in het actieve project."
                )
                return
            self.workspace.pdf_bridge.highlight_from_pdf(entity_id, feature_id)
            self.workspace_router.open_workspace("viewer")

        def _create_menu(self) -> None:
            file_menu = self.menuBar().addMenu("Bestand")
            open_project = file_menu.addAction("Project openen …")
            open_project.setShortcut("Ctrl+O")
            open_project.triggered.connect(self._choose_project)
            file_menu.addAction("Bestanden inlezen", lambda: self.tabs.setCurrentWidget(self.import_page))
            file_menu.addSeparator()
            import os
            if os.environ.get("CWS_DIAGNOSTIC_LEGACY_UI") == "1":
                legacy = file_menu.addAction("Legacy Tk-interface starten (diagnostiek)")
                legacy.triggered.connect(self._launch_legacy_ui)
            file_menu.addSeparator()
            file_menu.addAction("Afsluiten", self.close, "Ctrl+Q")
            view = self.menuBar().addMenu("Weergave")
            for index in range(self.tabs.count()):
                page = self.tabs.widget(index)
                view.addAction(
                    self.tabs.tabText(index),
                    lambda _checked=False, target=page: self.tabs.setCurrentWidget(target),
                )
            extra = self.menuBar().addMenu("Meer")
            extra.addAction("Revisies / Compare", self._show_revisions)
            extra.addAction("Optimalisatie", self._show_optimization)
            help_menu = self.menuBar().addMenu("Help")
            help_menu.addAction("Runtime-diagnose", self._show_validation)
            help_menu.addAction(
                "Over CWS Convertor",
                lambda: QtWidgets.QMessageBox.information(
                    self,
                    "CWS Convertor",
                    f"CWS Convertor {APP_VERSION}\nV9 geïntegreerde viewerhoofdbuild",
                ),
            )

        def _create_status(self) -> None:
            self.statusBar().showMessage(
                "CWS Convertor gereed · productie-export blijft format-specifiek gevalideerd"
            )
            self.load_status_label = QtWidgets.QLabel()
            self.load_status_label.setObjectName("cwsLoadStatusLabel")
            self.load_status_progress = QtWidgets.QProgressBar()
            self.load_status_progress.setObjectName("cwsLoadStatusProgress")
            self.load_status_progress.setRange(0, 100)
            self.load_status_progress.setValue(0)
            self.load_status_progress.setFormat("%p%")
            self.load_status_progress.setFixedWidth(190)
            self.load_status_progress.setFixedHeight(17)
            self.statusBar().addPermanentWidget(self.load_status_label, 1)
            self.statusBar().addPermanentWidget(self.load_status_progress)
            self._hide_load_progress()

        @QtCore.Slot(int, str)
        def _load_progress_changed(self, percent: int, message: str) -> None:
            if not hasattr(self, "load_status_progress"):
                return
            value = max(0, min(100, int(percent)))
            self.load_status_label.setText(message)
            self.load_status_progress.setValue(value)
            self.load_status_label.show()
            self.load_status_progress.show()
            self.statusBar().showMessage(message)

        def _load_progress_failed(self, message: str) -> None:
            self._load_progress_changed(0, message)
            self.load_status_progress.setFormat("Mislukt")

        def _hide_load_progress(self) -> None:
            if not hasattr(self, "load_status_progress"):
                return
            self.load_status_progress.setFormat("%p%")
            self.load_status_label.hide()
            self.load_status_progress.hide()

        def _show_validation(self) -> None:
            self.tabs.setCurrentWidget(self.control_page)
            self.control_page.setCurrentWidget(self.validation_page)

        def _show_revisions(self) -> None:
            self.tabs.setCurrentWidget(self.control_page)
            self.control_page.setCurrentWidget(self.revisions_page)

        def _show_optimization(self) -> None:
            self.tabs.setCurrentWidget(self.control_page)
            self.control_page.setCurrentWidget(self.optimization_page)

        def _choose_project(self) -> None:
            name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "CWS-project openen", "", "CWS-project (*.cwscproj)"
            )
            if name:
                self._open_project(Path(name))

        def _open_project(self, path: Path, *, progress_floor: int = 0) -> None:
            self._project_progress_floor = max(0, min(95, int(progress_floor)))
            self._load_progress_changed(
                self._project_progress_floor,
                f"Project openen: {path.name}",
            )
            self.workspace_router.open_workspace("viewer")
            self.project_page.open_project(path)

        def _launch_legacy_ui(self) -> None:
            import os
            import sys

            if os.environ.get("CWS_DIAGNOSTIC_LEGACY_UI") != "1":
                QtWidgets.QMessageBox.warning(
                    self,
                    "Diagnostische legacy-interface",
                    "Legacy fallback is gesloten. Zet CWS_DIAGNOSTIC_LEGACY_UI=1 alleen voor expliciete diagnose.",
                )
                return

            if getattr(sys, "frozen", False):
                program = sys.executable
                arguments = ["--legacy-ui"]
            else:
                program = sys.executable
                arguments = [
                    str(Path(__file__).resolve().parents[2] / "CWS_Convertor_App.py"),
                    "--legacy-ui",
                ]
            if not QtCore.QProcess.startDetached(program, arguments):
                QtWidgets.QMessageBox.warning(
                    self,
                    "Legacy interface",
                    "De compatibility-interface kon niet starten.",
                )

        def _legacy_notice(self) -> None:
            QtWidgets.QMessageBox.information(
                self,
                "Legacy interface",
                "De primaire build gebruikt nu de geïntegreerde Qt-interface. "
                "Start de oude Tk-interface alleen expliciet met --legacy-ui voor regressie/fallback.",
            )

        def closeEvent(self, event: Any) -> None:
            self.project_page.close_project()
            if self._context_unsubscribe is not None:
                self._context_unsubscribe()
                self._context_unsubscribe = None
            self.application_context.close()
            super().closeEvent(event)

    # Public compatibility names used by the V9 package, tests and transition
    # launcher.  They intentionally resolve to the same classes.
    CwsConvertorMainWindow = CWSMainWindow
    IntegratedProjectPage = IntegratedProjectWorkspaceWidget

    def run_qt_application(initial_paths: Iterable[str | Path] | str | Path | None = None) -> int:
        import sys

        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        application.setApplicationName("CWS Convertor")
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
    class CWSMainWindow:
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    CwsConvertorMainWindow = CWSMainWindow
    IntegratedProjectPage = CWSMainWindow

    def run_qt_application(initial_paths: Iterable[str | Path] | str | Path | None = None) -> int:
        del initial_paths
        require_qt()
        return 2


__all__ = [
    "CWSMainWindow",
    "CwsConvertorMainWindow",
    "IntegratedProjectPage",
    "run_qt_application",
]
