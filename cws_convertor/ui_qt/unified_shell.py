"""U3 central CWS Convertor Qt shell.

The existing V15/V9 integrated window remains the visual and functional base.
U3 adds one GUI-toolkit-independent :class:`UnifiedApplicationContext` above it
and routes all application surfaces through that context.  No project, scene,
BOM or manufacturing truth is duplicated here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from cws_convertor.integration.ui_context import (
    U3_SAFETY_FLAGS,
    UnifiedApplicationContext,
    UnifiedUiContextSnapshot,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from .main_window import CWSMainWindow as _BaseCWSMainWindow


U3_CONTEXT_PROPERTY = "cwsUnifiedApplicationContext"
U3_CONTEXT_TOKEN = "CWS-U3-SINGLE-PROJECT-SELECTION-CONTEXT"


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class UnifiedContextStrip(QtWidgets.QFrame):
        """Always-visible project/selection status shared by every tab."""

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsU3UnifiedContextStrip")
            self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
            self.setStyleSheet(
                "QFrame#cwsU3UnifiedContextStrip {"
                "background:#eef5ff;border:1px solid #b7cce8;border-radius:5px;}"
                "QLabel#u3ContextHeading {font-weight:700;color:#0b4ea2;}"
                "QLabel#u3ContextMuted {color:#5b677a;}"
                "QLabel#u3SafetyClosed {font-weight:600;color:#6f4b00;}"
            )
            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(9, 5, 9, 5)
            layout.setSpacing(12)
            heading = QtWidgets.QLabel("Projectcontext")
            heading.setObjectName("u3ContextHeading")
            self.project = QtWidgets.QLabel("Geen project")
            self.selection = QtWidgets.QLabel("Geen selectie")
            self.origin = QtWidgets.QLabel("herkomst: —")
            self.origin.setObjectName("u3ContextMuted")
            self.surface = QtWidgets.QLabel("werkvlak: start")
            self.surface.setObjectName("u3ContextMuted")
            self.safety = QtWidgets.QLabel("machine-transfer: gesloten")
            self.safety.setObjectName("u3SafetyClosed")
            layout.addWidget(heading)
            layout.addWidget(self.project, 2)
            layout.addWidget(self.selection, 2)
            layout.addWidget(self.origin, 1)
            layout.addWidget(self.surface, 1)
            layout.addStretch(1)
            layout.addWidget(self.safety)

        def apply_snapshot(self, snapshot: UnifiedUiContextSnapshot) -> None:
            if snapshot.project_attached:
                self.project.setText(
                    f"{snapshot.project_name or snapshot.project_id} · schema {snapshot.project_schema}"
                )
                self.project.setToolTip(snapshot.project_path)
            else:
                self.project.setText("Geen project")
                self.project.setToolTip("")
            selection = snapshot.selection
            if selection.primary_entity_id:
                extra = max(0, len(selection.entity_ids) - 1)
                suffix = f" +{extra}" if extra else ""
                feature = f" · {selection.feature_id}" if selection.feature_id else ""
                self.selection.setText(f"selectie: {selection.primary_entity_id}{suffix}{feature}")
            else:
                self.selection.setText("Geen selectie")
            self.origin.setText(f"herkomst: {selection.origin or '—'}")
            self.surface.setText(f"werkvlak: {snapshot.active_surface}")
            if snapshot.integrity_blocking_codes:
                self.setToolTip("\n".join(snapshot.integrity_blocking_codes))
                self.selection.setStyleSheet("color:#a33a22;font-weight:700")
            else:
                self.setToolTip("U3 canonical project/selection context: consistent")
                self.selection.setStyleSheet("")
            self.safety.setText(
                "machine-transfer: gesloten"
                if not any(U3_SAFETY_FLAGS.values())
                else "machine-transfer: BLOKKER OPEN"
            )


    class CWSMainWindow(_BaseCWSMainWindow):
        """Viewer V15 based desktop with one U3 project/selection context."""

        def __init__(self, initial_paths: Iterable[str | Path] = ()) -> None:
            self.application_context = UnifiedApplicationContext(active_surface="start")
            self._u3_ready = False
            self._u3_context_unsubscribe = None
            self._u3_bom_context: Any | None = None
            super().__init__(initial_paths)
            self._install_u3_context()
            self._u3_ready = True
            self._u3_context_unsubscribe = self.application_context.subscribe(
                self._apply_u3_snapshot,
                emit_current=True,
            )
            self._update_active_surface()

        @property
        def context_snapshot(self) -> UnifiedUiContextSnapshot:
            return self.application_context.snapshot

        def _install_u3_context(self) -> None:
            # Keep the exact existing tab widget, VTK viewer and page objects;
            # only compose an always-visible context strip above them.
            current_central = self.takeCentralWidget()
            container = QtWidgets.QWidget(self)
            container.setObjectName("cwsU3CentralViewerShell")
            layout = QtWidgets.QVBoxLayout(container)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(4)
            self.context_strip = UnifiedContextStrip(container)
            layout.addWidget(self.context_strip)
            if current_central is not None:
                current_central.setParent(container)
                layout.addWidget(current_central, 1)
            self.setCentralWidget(container)

            # BOM previously had project status but no live selection status.
            # Add a read-only context line; the BOM snapshot itself is unchanged.
            bom_layout = self.bom_excel_page.layout()
            if bom_layout is not None:
                self._u3_bom_context = QtWidgets.QLabel("Geen selectie")
                self._u3_bom_context.setObjectName("selectionContext")
                self._u3_bom_context.setWordWrap(True)
                bom_layout.insertWidget(1, self._u3_bom_context)

            # Mark all production-relevant surfaces as consumers of the exact
            # same context object.  This is metadata only, never project state.
            for page in (
                self.project_page,
                self.edit_page,
                self.scribing_page,
                self.bom_excel_page,
                self.export_page,
                self.converter_page,
                self.pdf_page,
            ):
                page.setProperty(U3_CONTEXT_PROPERTY, U3_CONTEXT_TOKEN)

            self.tabs.currentChanged.connect(lambda _index: self._update_active_surface())

            # Toolbar workbench launches bypass the main routing table in the
            # V9 base.  Rewire that one action so U3 can expose the Workbench as
            # the active surface while the modal is open.
            try:
                self.project_page.exact_action.triggered.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.project_page.exact_action.triggered.connect(self._open_exact_workbench_u3)

        def _surface_for_current_tab(self) -> str:
            page = self.tabs.currentWidget()
            mapping = {
                self.import_page: "import",
                self.project_page: "viewer",
                self.edit_page: "workbench",
                self.converter_page: "converter",
                self.control_page: "control",
                self.pdf_page: "pdf",
                self.profiles_page: "profiles",
                self.drawings_page: "drawings",
                self.scribing_page: "scribing",
                self.bom_excel_page: "bom",
                self.export_page: "export",
            }
            return mapping.get(page, "application")

        def _update_active_surface(self) -> None:
            self.application_context.set_active_surface(self._surface_for_current_tab())

        def _project_loaded(self, path: str) -> None:
            workspace = self.workspace
            if workspace is not None:
                self.application_context.attach_workspace(workspace)
            _BaseCWSMainWindow._project_loaded(self, path)
            # The base window adds a second direct interaction subscription.
            # U3 uses the application context / workspace selection bus instead.
            if self._selection_unsubscribe is not None:
                self._selection_unsubscribe()
                self._selection_unsubscribe = None
            if self.workspace is not None and self.application_context.workspace is not self.workspace:
                self.application_context.attach_workspace(self.workspace)
            current_selection = self.project_page._selected_nodes() if self.workspace is not None else None
            for page_name in ("edit_page", "pdf_page"):
                page = getattr(self, page_name, None)
                set_context = getattr(page, "set_context", None)
                if callable(set_context):
                    set_context(self.workspace, current_selection)
            self._update_active_surface()
            place_viewer = getattr(self, "_place_shared_viewer", None)
            if callable(place_viewer):
                place_viewer(self._surface_for_current_tab())

        def _project_closed(self) -> None:
            self.application_context.detach_workspace()
            _BaseCWSMainWindow._project_closed(self)

        def _selection_changed(self, selection: Any | None) -> None:
            # The base constructor calls this before U3 composition exists.
            if not getattr(self, "_u3_ready", False):
                _BaseCWSMainWindow._selection_changed(self, selection)
                return
            workspace = self.workspace
            if workspace is None:
                if self.application_context.workspace is not None:
                    self.application_context.detach_workspace()
                _BaseCWSMainWindow._selection_changed(self, None)
                return
            if self.application_context.workspace is not workspace:
                self.application_context.attach_workspace(workspace)
            self.application_context.ingest_interaction_selection(selection)
            for page_name in ("edit_page", "pdf_page"):
                page = getattr(self, page_name, None)
                set_context = getattr(page, "set_context", None)
                if callable(set_context):
                    set_context(workspace, selection)

        def _apply_u3_snapshot(self, snapshot: UnifiedUiContextSnapshot) -> None:
            self.context_strip.apply_snapshot(snapshot)
            selection = snapshot.selection if snapshot.project_attached else None
            # Reuse the proven V9 page binders, but feed them only from this
            # single U3 snapshot instead of parallel per-tab state.
            _BaseCWSMainWindow._selection_changed(self, selection)
            if self._u3_bom_context is not None:
                if snapshot.project_attached and snapshot.selection.primary_entity_id:
                    self._u3_bom_context.setText(
                        "Actieve canonical selectie: "
                        f"{snapshot.selection.primary_entity_id} · "
                        f"{len(snapshot.selection.entity_ids)} object(en) · "
                        f"herkomst {snapshot.selection.origin}"
                    )
                elif snapshot.project_attached:
                    self._u3_bom_context.setText(
                        f"Actief project: {snapshot.project_name} · geen object geselecteerd"
                    )
                else:
                    self._u3_bom_context.setText("Geen project geopend")
            if snapshot.integrity_blocking_codes:
                self.statusBar().showMessage(
                    "U3 context geblokkeerd: " + ", ".join(snapshot.integrity_blocking_codes)
                )

        def _route_action(self, action: str) -> None:
            if str(action) == "open_exact":
                self._open_exact_workbench_u3()
                return
            _BaseCWSMainWindow._route_action(self, action)
            self._update_active_surface()

        def _open_exact_workbench_u3(self) -> None:
            previous = self.application_context.active_surface
            self.application_context.set_active_surface("workbench")
            try:
                self.project_page.open_exact_workbench()
            finally:
                # Return to the visible page after the modal closes.
                self.application_context.set_active_surface(
                    self._surface_for_current_tab() or previous
                )

        def _highlight_pdf_feature(self, entity_id: str, feature_id: str) -> None:
            # Preserve the base command but use the U3 broker explicitly.  This
            # makes the PDF highlight visible in the viewer interaction model as
            # well as on the feature-aware application selection bus.
            if self.workspace is None:
                return _BaseCWSMainWindow._highlight_pdf_feature(self, entity_id, feature_id)
            try:
                self.application_context.request_selection(
                    (entity_id,),
                    primary_entity_id=entity_id,
                    feature_id=feature_id,
                    origin="pdf",
                )
            except Exception as exc:
                QtWidgets.QMessageBox.warning(
                    self,
                    "PDF-feature",
                    f"U3 selectie geblokkeerd: {type(exc).__name__}: {exc}",
                )
                return
            self.tabs.setCurrentWidget(self.project_page)

        def closeEvent(self, event: Any) -> None:
            if self._u3_context_unsubscribe is not None:
                self._u3_context_unsubscribe()
                self._u3_context_unsubscribe = None
            self.application_context.detach_workspace()
            _BaseCWSMainWindow.closeEvent(self, event)


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
    class CWSMainWindow(_BaseCWSMainWindow):  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    CwsConvertorMainWindow = CWSMainWindow

    def run_qt_application(initial_paths: Iterable[str | Path] | str | Path | None = None) -> int:  # pragma: no cover
        del initial_paths
        require_qt()
        return 2


__all__ = [
    "CWSMainWindow",
    "CwsConvertorMainWindow",
    "U3_CONTEXT_PROPERTY",
    "U3_CONTEXT_TOKEN",
    "UnifiedContextStrip",
    "run_qt_application",
]
