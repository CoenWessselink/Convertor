"""U4 production-workflow shell layered on the U3 central application context."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from cws_convertor.integration.production_workflow import build_production_workflow_snapshot
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from .unified_shell import CWSMainWindow as _U3MainWindow

U4_WORKFLOW_PROPERTY = "cwsUnifiedProductionWorkflow"
U4_WORKFLOW_TOKEN = "CWS-U4-PRODUCTION-WORKFLOW"


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class ProductionWorkflowPanel(QtWidgets.QWidget):
        action_requested = QtCore.Signal(str)

        def __init__(self, window: "CWSMainWindow", parent: Any | None = None) -> None:
            super().__init__(parent)
            self.window = window
            self._last_snapshot = None
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(8)

            title = QtWidgets.QLabel("Productieworkflow")
            title.setObjectName("workspaceTitle")
            root.addWidget(title)

            safety = QtWidgets.QLabel(
                "U4 combineert bestaande readiness-, scribing-, BOM- en exportgates. "
                "Deze werklaag kan geen machine-transfer of productievrijgave forceren."
            )
            safety.setObjectName("cwsSafety")
            safety.setWordWrap(True)
            root.addWidget(safety)

            self.context = QtWidgets.QLabel("Geen project geopend")
            self.context.setObjectName("selectionContext")
            self.context.setWordWrap(True)
            root.addWidget(self.context)

            actions = QtWidgets.QHBoxLayout()
            refresh = QtWidgets.QPushButton("Readiness vernieuwen")
            refresh.clicked.connect(self.refresh)
            viewer = QtWidgets.QPushButton("Naar Viewer")
            viewer.clicked.connect(lambda: self.action_requested.emit("viewer"))
            scribing = QtWidgets.QPushButton("Naar Scribing")
            scribing.clicked.connect(lambda: self.action_requested.emit("scribing"))
            bom = QtWidgets.QPushButton("Naar BOM / Excel")
            bom.clicked.connect(lambda: self.action_requested.emit("quantities"))
            export = QtWidgets.QPushButton("Naar Exporteren")
            export.setObjectName("primaryButton")
            export.clicked.connect(lambda: self.action_requested.emit("export"))
            for widget in (refresh, viewer, scribing, bom, export):
                actions.addWidget(widget)
            actions.addStretch(1)
            root.addLayout(actions)

            self.summary = QtWidgets.QTreeWidget()
            self.summary.setHeaderLabels(["Onderdeel", "Status", "Toegestaan", "Geblokkeerd", "Blocking codes"])
            self.summary.setRootIsDecorated(False)
            self.summary.setAlternatingRowColors(True)
            self.summary.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.summary.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.summary.header().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.summary.header().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.summary.header().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
            root.addWidget(self.summary, 1)

            self.status = QtWidgets.QLabel("Wacht op projectcontext")
            self.status.setWordWrap(True)
            root.addWidget(self.status)

        def refresh(self) -> None:
            workspace = self.window.workspace
            snapshot = self.window.application_context.snapshot
            self.summary.clear()
            if workspace is None:
                self.context.setText("Geen project geopend")
                self.status.setText("Open eerst een CWS-project.")
                self._last_snapshot = None
                return
            entity_ids = tuple(snapshot.selection.entity_ids) if snapshot.selection.entity_ids else ()
            report = build_production_workflow_snapshot(workspace, entity_ids)
            self._last_snapshot = report
            scope_text = "huidige selectie" if report.scope == "selection" else "heel project"
            self.context.setText(
                f"Project: {report.project_name} · scope: {scope_text} · "
                f"{report.part_count} onderdeel(en)"
            )
            for item in report.part_statuses:
                row = QtWidgets.QTreeWidgetItem(self.summary)
                row.setText(0, item.mark)
                row.setToolTip(0, item.entity_id)
                row.setText(1, "READY" if item.production_ready else "BLOCKED")
                row.setText(2, ", ".join(item.allowed_formats) or "—")
                row.setText(3, ", ".join(item.blocked_formats) or "—")
                row.setText(4, ", ".join(item.blocking_codes) or "—")
            self.status.setText(
                f"Ready: {report.ready_part_count} · blocked: {report.blocked_part_count} · "
                f"volgende stap: {report.next_action} · machine-transfer: gesloten"
            )


    class CWSMainWindow(_U3MainWindow):
        """U3 central UI plus U4 production workflow surface."""

        def __init__(self, initial_paths: Iterable[str | Path] = ()) -> None:
            super().__init__(initial_paths)
            self.setObjectName("cwsConvertorUnifiedU4MainWindow")
            self.production_workflow_page = ProductionWorkflowPanel(self)
            self.production_workflow_page.setProperty(U4_WORKFLOW_PROPERTY, U4_WORKFLOW_TOKEN)
            insert_at = self.tabs.indexOf(self.export_page)
            icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton)
            self.tabs.insertTab(insert_at if insert_at >= 0 else self.tabs.count(), self.production_workflow_page, icon, "Productieworkflow")
            self.production_workflow_page.action_requested.connect(self._route_action)
            self.project_page.project_loaded.connect(lambda _path: self.production_workflow_page.refresh())
            self.project_page.project_closed.connect(self.production_workflow_page.refresh)
            self.application_context.subscribe(lambda _snapshot: self.production_workflow_page.refresh())
            self.tabs.currentChanged.connect(lambda _index: self._u4_tab_changed())
            self.menuBar().addAction("Productieworkflow", lambda: self.tabs.setCurrentWidget(self.production_workflow_page))
            self.production_workflow_page.refresh()

        def _u4_tab_changed(self) -> None:
            if self.tabs.currentWidget() is self.production_workflow_page:
                self.application_context.set_active_surface("production_workflow")
                self.production_workflow_page.refresh()

        def _surface_for_current_tab(self) -> str:
            if hasattr(self, "production_workflow_page") and self.tabs.currentWidget() is self.production_workflow_page:
                return "production_workflow"
            return super()._surface_for_current_tab()


    CwsConvertorMainWindow = CWSMainWindow

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
    class CWSMainWindow(_U3MainWindow):  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    CwsConvertorMainWindow = CWSMainWindow
    ProductionWorkflowPanel = CWSMainWindow

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
    "run_qt_application",
]
