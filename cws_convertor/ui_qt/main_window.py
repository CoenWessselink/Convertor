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
    from .converter_panel import ConverterPanel
    from .pdf_panel import PDFPanel
    from .project_workspace import IntegratedProjectWorkspaceWidget
    from .workspace_pages import (
        ContextActionPage,
        ExportPanel,
        ImportPanel,
        OptimizationPanel,
        ProfilesPanel,
    )

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

    class CWSMainWindow(QtWidgets.QMainWindow):
        """One-process CWS Convertor shell with integrated project viewer."""

        def __init__(self, initial_paths: Iterable[str | Path] = ()) -> None:
            super().__init__()
            self.setObjectName("cwsConvertorV9MainWindow")
            self.setWindowTitle(f"CWS Convertor {APP_VERSION}")
            self.resize(1760, 1040)
            self.setMinimumSize(1280, 760)
            self.setStyleSheet(_QSS)
            self._selection_unsubscribe = None
            self.tabs = QtWidgets.QTabWidget()
            self.tabs.setDocumentMode(True)
            self.tabs.setMovable(False)
            self.tabs.tabBar().setExpanding(False)
            self.setCentralWidget(self.tabs)

            self.import_page = ImportPanel()
            self.project_page = IntegratedProjectWorkspaceWidget()
            self.edit_page = ContextActionPage(
                "Bewerken",
                actions=(("Open Part Workbench", "open_exact"), ("Terug naar Viewer", "viewer")),
            )
            self.converter_page = ConverterPanel()
            self.validation_page = _ValidationPage()
            self.revisions_page = _RevisionComparePage(self.project_page)
            self.optimization_page = OptimizationPanel()
            self.control_page = QtWidgets.QTabWidget()
            self.control_page.addTab(self.validation_page, "Validatie")
            self.control_page.addTab(self.revisions_page, "Revisies / Compare")
            self.control_page.addTab(self.optimization_page, "Optimalisatie")
            self.pdf_page = PDFPanel()
            self.profiles_page = ProfilesPanel()
            self.drawings_page = ContextActionPage(
                "Tekeningen",
                actions=(("PDF / Tekening", "pdf"), ("Open Part Workbench", "open_exact"), ("Exporteren", "export")),
            )
            self.scribing_page = ContextActionPage(
                "Scribing",
                actions=(("Open scribing in Part Workbench", "open_exact"), ("Terug naar Viewer", "viewer")),
            )
            self.bom_excel_page = _BOMExcelPage(self.project_page)
            self.export_page = ExportPanel()

            style = self.style()
            tab_specs = (
                (self.import_page, "Inlezen", QtWidgets.QStyle.StandardPixmap.SP_DialogOpenButton),
                (self.project_page, "Viewer / Project", QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon),
                (self.edit_page, "Bewerken", QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView),
                (self.converter_page, "Converteren", QtWidgets.QStyle.StandardPixmap.SP_BrowserReload),
                (self.control_page, "Controleren", QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton),
                (self.pdf_page, "PDF / Tekening", QtWidgets.QStyle.StandardPixmap.SP_FileIcon),
                (self.profiles_page, "Profielen", QtWidgets.QStyle.StandardPixmap.SP_DirIcon),
                (self.drawings_page, "Tekeningen", QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView),
                (self.scribing_page, "Scribing", QtWidgets.QStyle.StandardPixmap.SP_CommandLink),
                (self.bom_excel_page, "Hoeveelheden / Excel", QtWidgets.QStyle.StandardPixmap.SP_FileDialogListView),
                (self.export_page, "Exporteren", QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton),
            )
            for page, title, icon in tab_specs:
                self.tabs.addTab(page, style.standardIcon(icon), title)
            self._create_menu()
            self._create_status()
            self.import_page.project_requested.connect(lambda value: self._open_project(Path(value)))
            self.import_page.models_requested.connect(self._queue_models)
            self.import_page.pdf_requested.connect(self._open_pdf)
            self.project_page.project_loaded.connect(self._project_loaded)
            self.project_page.project_closed.connect(self._project_closed)
            self.project_page.selection_changed.connect(self._selection_changed)
            self.project_page.action_requested.connect(self._route_action)
            self.edit_page.action_requested.connect(self._route_action)
            self.drawings_page.action_requested.connect(self._route_action)
            self.scribing_page.action_requested.connect(self._route_action)
            self.profiles_page.action_requested.connect(self._route_action)
            self.bom_excel_page.show_project_requested.connect(
                lambda: self.tabs.setCurrentWidget(self.project_page)
            )
            self.revisions_page.show_project_requested.connect(
                lambda: self.tabs.setCurrentWidget(self.project_page)
            )
            self.pdf_page.feature_highlight_requested.connect(self._highlight_pdf_feature)
            self._selection_changed(None)
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
                self.converter_page.add_files(models)
                if project is None:
                    self.tabs.setCurrentWidget(self.converter_page)
            if pdf is not None and self.pdf_page.load_pdf(pdf):
                if project is None and not models:
                    self.tabs.setCurrentWidget(self.pdf_page)

        def _queue_models(self, values: Iterable[str | Path]) -> None:
            self.converter_page.add_files(values)
            self.tabs.setCurrentWidget(self.converter_page)

        def _open_pdf(self, value: str | Path) -> None:
            if self.pdf_page.load_pdf(value):
                self.tabs.setCurrentWidget(self.pdf_page)

        @property
        def workspace(self) -> Any | None:
            return self.project_page.workspace

        def _project_loaded(self, path: str) -> None:
            self.statusBar().showMessage(f"Project geopend: {path}")
            self.bom_excel_page.refresh()
            self.revisions_page.refresh()
            if self._selection_unsubscribe is not None:
                self._selection_unsubscribe()
                self._selection_unsubscribe = None
            if self.workspace is not None:
                self._selection_unsubscribe = self.workspace.interaction.subscribe(
                    self._selection_changed
                )
                self._selection_changed(self.workspace.interaction.selection)

        def _project_closed(self) -> None:
            if self._selection_unsubscribe is not None:
                self._selection_unsubscribe()
                self._selection_unsubscribe = None
            self.bom_excel_page.refresh()
            self.revisions_page.refresh()
            self._selection_changed(None)

        def _selection_changed(self, selection: Any | None) -> None:
            workspace = self.workspace
            self.converter_page.set_project_selection(workspace, selection)
            self.pdf_page.show_project_selection(selection or object())
            self.edit_page.set_context(workspace, selection)
            self.drawings_page.set_context(workspace, selection)
            self.scribing_page.set_context(workspace, selection)
            self.profiles_page.set_context(workspace, selection)
            self.export_page.set_context(workspace, selection)

        def _route_action(self, action: str) -> None:
            routes = {
                "properties": self.project_page,
                "viewer": self.project_page,
                "edit": self.edit_page,
                "convert": self.converter_page,
                "validate": self.control_page,
                "pdf": self.pdf_page,
                "profiles": self.profiles_page,
                "drawings": self.drawings_page,
                "scribing": self.scribing_page,
                "quantities": self.bom_excel_page,
                "export": self.export_page,
            }
            if action == "open_exact":
                self.project_page.open_exact_workbench()
                return
            if action == "legacy_profiles":
                self._launch_legacy_ui()
                return
            page = routes.get(str(action))
            if page is not None:
                self.tabs.setCurrentWidget(page)

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
            self.tabs.setCurrentWidget(self.project_page)

        def _create_menu(self) -> None:
            file_menu = self.menuBar().addMenu("Bestand")
            open_project = file_menu.addAction("Project openen …")
            open_project.setShortcut("Ctrl+O")
            open_project.triggered.connect(self._choose_project)
            file_menu.addAction("Bestanden inlezen", lambda: self.tabs.setCurrentWidget(self.import_page))
            file_menu.addSeparator()
            legacy = file_menu.addAction("Legacy Tk-interface starten")
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

        def _open_project(self, path: Path) -> None:
            self.tabs.setCurrentWidget(self.project_page)
            self.project_page.open_project(path)

        def _launch_legacy_ui(self) -> None:
            import sys

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
