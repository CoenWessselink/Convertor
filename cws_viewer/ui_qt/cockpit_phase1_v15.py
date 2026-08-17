"""CWS Viewer V15 Phase 1 shell.

Phase 1 keeps the proven T0-T8 engineering contracts, but changes how the
standalone desktop starts: the 3D viewer and the two daily-use explorer docks
are made useful first, while review/coordination/export/manufacturing panels are
materialised only when the user opens them.  Optional panel failures stay
isolated from the model viewport.

The visual layer is an original CWS engineering theme.  Third-party products
remain behavioural references only; no proprietary assets or code are used.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Callable

from cws_viewer.review import V15ReviewWorkspaceService
from cws_viewer.ui_qt.cockpit_t8_v15 import (
    CwsViewerV15T8CockpitWindow,
    V15_T8_VERSION,
    t8_workspace_contract,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

PHASE1_BUILD = "phase1-foundation-1"
PHASE1_LAYOUT_VERSION = 1


def phase1_workspace_contract() -> dict[str, Any]:
    contract = t8_workspace_contract()
    capabilities = dict(contract.get("capabilities", {}))
    capabilities.update(
        {
            "startup_geometry_cache_prefetch": True,
            "lazy_review_coordination_export_manufacturing": True,
            "fail_isolated_optional_panels": True,
            "clean_viewer_first_layout": True,
            "phase1_professional_shell": True,
            "startup_metrics": True,
        }
    )
    contract["capabilities"] = capabilities
    contract["phase1"] = {
        "build": PHASE1_BUILD,
        "layout_version": PHASE1_LAYOUT_VERSION,
        "startup_priority": [
            "3d_viewer",
            "project_explorer",
            "properties",
            "view_navigation",
            "optional_engineering_panels",
        ],
        "lazy_panels": ["review", "coordination", "export_center", "manufacturing_faces"],
        "failure_policy": "optional_panel_failure_does_not_close_viewer",
    }
    return contract


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    _PHASE1_QSS = """
QMainWindow#cwsViewerV15Phase1CockpitWindow {
    background: #eef2f6;
}
QFrame#cwsHeader {
    background: #ffffff;
    border: none;
    border-bottom: 1px solid #d7dce2;
    border-radius: 0px;
}
QFrame#cwsRibbon {
    background: #f7f9fc;
    border: none;
    border-bottom: 1px solid #d7dce2;
    border-radius: 0px;
}
QLabel#cwsProductTitle {
    color: #0747a6;
    font-size: 18pt;
    font-weight: 700;
}
QLabel#cwsSubtitle {
    color: #38506d;
    font-size: 9.5pt;
    font-weight: 600;
}
QLabel#cwsVersion {
    color: #7a8796;
    font-size: 8.5pt;
}
QToolBar#cwsPhase1CommandBar {
    background: #f7f9fc;
    border: none;
    spacing: 2px;
    padding: 2px 4px;
}
QToolBar#cwsPhase1CommandBar QToolButton {
    min-height: 24px;
    padding: 4px 8px;
    border-radius: 4px;
}
QToolBar#cwsPhase1CommandBar QToolButton:hover {
    background: #e8f1ff;
    border-color: #cad7e8;
}
QToolBar#cwsPhase1CommandBar QToolButton:checked {
    background: #0b5bd3;
    color: white;
    border-color: #0b5bd3;
}
QDockWidget::title {
    background: #f7f9fc;
    color: #26384d;
    border-bottom: 1px solid #d7dce2;
    padding: 6px 8px;
    font-weight: 650;
}
QTabBar::tab {
    min-height: 23px;
    padding: 5px 10px;
}
QTreeWidget, QTableWidget, QTableView, QPlainTextEdit, QListWidget {
    border-color: #d7dce2;
}
QHeaderView::section {
    padding: 5px 7px;
    background: #f4f6f9;
    color: #42526a;
}
QStatusBar {
    min-height: 22px;
}
QWidget#cwsPhase1LazyPanel {
    background: #ffffff;
}
QLabel#cwsPhase1LazyTitle {
    color: #26384d;
    font-size: 11pt;
    font-weight: 650;
}
QLabel#cwsPhase1LazyHint {
    color: #69798a;
}
"""

    class CwsViewerV15Phase1CockpitWindow(CwsViewerV15T8CockpitWindow):
        """Viewer-first Phase 1 shell with lazy optional engineering panels."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._phase1_constructing = True
            self._phase1_started = time.perf_counter()
            self._phase1_lazy_loaders: dict[str, Callable[[], Any]] = {}
            self._phase1_lazy_placeholders: dict[str, Any] = {}
            self._phase1_materialized: set[str] = set()
            self._phase1_loading: set[str] = set()
            self._phase1_failures: dict[str, str] = {}
            super().__init__(*args, **kwargs)
            self._phase1_constructing = False
            self.setObjectName("cwsViewerV15Phase1CockpitWindow")
            self.setWindowTitle(
                f"CWS Viewer — {getattr(self.project, 'project_name', 'Project')}"
            )
            self._apply_phase1_visual_design()
            self._apply_phase1_layout_policy()
            self._materialize_restored_visible_panels()
            self._record_phase1_startup_metrics()

        # ------------------------------------------------------------------
        # Lazy panel infrastructure
        def _make_lazy_dock(
            self,
            *,
            key: str,
            title: str,
            area: Any,
            hint: str,
            loader: Callable[[], Any],
        ) -> Any:
            dock = QtWidgets.QDockWidget(title, self)
            dock.setObjectName(f"cwsV15Dock_{key}")
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
            dock.setFeatures(
                QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            )

            placeholder = QtWidgets.QWidget(dock)
            placeholder.setObjectName("cwsPhase1LazyPanel")
            layout = QtWidgets.QVBoxLayout(placeholder)
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(8)
            heading = QtWidgets.QLabel(title)
            heading.setObjectName("cwsPhase1LazyTitle")
            note = QtWidgets.QLabel(hint)
            note.setObjectName("cwsPhase1LazyHint")
            note.setWordWrap(True)
            button = QtWidgets.QPushButton("Module openen")
            button.setObjectName("cwsPrimaryButton")
            button.setMaximumWidth(150)
            layout.addWidget(heading)
            layout.addWidget(note)
            layout.addWidget(button)
            layout.addStretch(1)
            dock.setWidget(placeholder)
            self.addDockWidget(area, dock)
            self._v15_docks[key] = dock
            self._phase1_lazy_loaders[key] = loader
            self._phase1_lazy_placeholders[key] = placeholder
            button.clicked.connect(lambda _checked=False, k=key: self._materialize_lazy_panel(k))
            dock.visibilityChanged.connect(
                lambda visible, k=key: self._on_lazy_visibility(k, bool(visible))
            )
            return dock

        def _on_lazy_visibility(self, key: str, visible: bool) -> None:
            if not visible or self._phase1_constructing:
                return
            if key in self._phase1_materialized or key in self._phase1_loading:
                return
            QtCore.QTimer.singleShot(0, lambda k=key: self._materialize_lazy_panel(k))

        def _materialize_lazy_panel(self, key: str) -> Any | None:
            if key in self._phase1_materialized:
                return self._v15_docks[key].widget()
            if key in self._phase1_loading:
                return None
            loader = self._phase1_lazy_loaders.get(key)
            dock = self._v15_docks.get(key)
            if loader is None or dock is None:
                return None
            self._phase1_loading.add(key)
            started = time.perf_counter()
            try:
                panel = loader()
                dock.setWidget(panel)
                self._phase1_materialized.add(key)
                self._phase1_failures.pop(key, None)
                elapsed = time.perf_counter() - started
                self.statusBar().showMessage(
                    f"{dock.windowTitle()} geladen in {elapsed:.2f} s", 3500
                )
                return panel
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                self._phase1_failures[key] = message
                placeholder = self._phase1_lazy_placeholders.get(key)
                if placeholder is not None:
                    labels = placeholder.findChildren(QtWidgets.QLabel)
                    if labels:
                        labels[-1].setText(
                            "Deze module kon niet worden geladen. De 3D Viewer blijft actief.\n\n"
                            + message
                        )
                self.statusBar().showMessage(
                    f"{dock.windowTitle()} niet geladen · viewer blijft actief", 6500
                )
                return None
            finally:
                self._phase1_loading.discard(key)

        def _show_lazy(self, key: str, *, tab_index: int | None = None) -> None:
            dock = self._v15_docks[key]
            dock.show()
            dock.raise_()
            panel = self._materialize_lazy_panel(key)
            if panel is not None and tab_index is not None and hasattr(panel, "tabs"):
                panel.tabs.setCurrentIndex(int(tab_index))

        # ------------------------------------------------------------------
        # T5-T8 optional panels: create the dock now, the expensive panel later
        def _install_t5_review_workspace(self) -> None:
            scene = self.viewer.controller.index.scene
            self._review_service = V15ReviewWorkspaceService(
                self.viewer.controller,
                project_id=scene.project_id,
                scene_hash=scene.scene_hash,
                store_path=self._review_store_path(),
                project_metadata=self._project_review_metadata(),
            )
            # Load the lightweight review sidecar state immediately so the
            # inherited T5 autosave can never overwrite an existing review with
            # an empty lazy panel state.  The expensive QWidget is still deferred.
            store = self._review_service.store_path
            if store is not None and store.exists():
                try:
                    self._review_service.load()
                except Exception as exc:
                    self._phase1_failures["review_sidecar"] = f"{type(exc).__name__}: {exc}"
            self._review_dock = self._make_lazy_dock(
                key="review",
                title="Review / Issues",
                area=QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
                hint=(
                    "Saved Views, markups en Issues worden pas opgebouwd wanneer u deze "
                    "werkruimte opent. Dit verkort de tijd tot de eerste bruikbare 3D-view."
                ),
                loader=self._load_review_panel,
            )
            try:
                self.tabifyDockWidget(self._workbench_dock, self._review_dock)
                self._workbench_dock.raise_()
            except Exception:
                pass
            menu = self.menuBar().addMenu("Review")
            menu.addAction("Saved Views", lambda: self._show_lazy("review", tab_index=0))
            menu.addAction("Issues / ToDos", lambda: self._show_lazy("review", tab_index=1))
            menu.addAction("Markups", lambda: self._show_lazy("review", tab_index=2))
            menu.addSeparator()
            menu.addAction(self._review_dock.toggleViewAction())

        def _load_review_panel(self) -> Any:
            from cws_viewer.ui_qt.review_v15 import V15ReviewPanel

            panel = V15ReviewPanel(self.viewer, self._review_service, self)
            panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 5000)
            )
            self._review_panel = panel
            panel.refresh()
            return panel

        def _install_t6_coordination_workspace(self) -> None:
            self._coordination_dock = self._make_lazy_dock(
                key="coordination",
                title="Assemblies / Compare / Clash / Sequence",
                area=QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
                hint=(
                    "Assemblies, modelvergelijking, clash/preflight en Sequence worden "
                    "on-demand gestart zodat het model eerst bestuurbaar is."
                ),
                loader=self._load_coordination_panel,
            )
            try:
                self.tabifyDockWidget(self._review_dock, self._coordination_dock)
            except Exception:
                pass
            menu = self.menuBar().addMenu("Coördinatie")
            menu.addAction("Assemblies", lambda: self._show_lazy("coordination", tab_index=0))
            menu.addAction("Compare", lambda: self._show_lazy("coordination", tab_index=1))
            menu.addAction("Clash / preflight", lambda: self._show_lazy("coordination", tab_index=2))
            menu.addAction("Sequence", lambda: self._show_lazy("coordination", tab_index=3))
            menu.addSeparator()
            menu.addAction(self._coordination_dock.toggleViewAction())

        def _load_coordination_panel(self) -> Any:
            from cws_viewer.coordination.review_bridge import T6ReviewServiceBridge
            from cws_viewer.ui_qt.coordination_v15 import V15CoordinationPanel

            bridge = T6ReviewServiceBridge(self._review_service)
            panel = V15CoordinationPanel(
                self.viewer,
                self.project,
                review_service=bridge,
                parent=self,
            )
            panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 5200)
            )
            self._coordination_panel = panel
            return panel

        def _install_t7_export_center(self) -> None:
            self._export_center_dock = self._make_lazy_dock(
                key="export_center",
                title="Export Center",
                area=QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                hint=(
                    "Exportpreflight en scope-opbouw worden pas geladen wanneer Export Center "
                    "wordt geopend. Productiegrenzen blijven fail-closed."
                ),
                loader=self._load_export_center_panel,
            )
            try:
                self.tabifyDockWidget(self._details_dock, self._export_center_dock)
                self._details_dock.raise_()
            except Exception:
                pass
            menu = self.menuBar().addMenu("Export")
            menu.addAction("Export Center openen", lambda: self._show_lazy("export_center"))
            menu.addAction(self._export_center_dock.toggleViewAction())

        def _load_export_center_panel(self) -> Any:
            from cws_viewer.ui_qt.export_center_v15 import V15ExportCenterPanel

            panel = V15ExportCenterPanel(
                self.viewer,
                self.project,
                default_output_dir=self._default_export_dir(),
                parent=self,
            )
            panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 6500)
            )
            self._export_center_panel = panel
            return panel

        def _install_manufacturing_faces(self) -> None:
            self._manufacturing_faces_dock = self._make_lazy_dock(
                key="manufacturing_faces",
                title="Manufacturing Faces",
                area=QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                hint=(
                    "Canonical face-analyse en overlays worden pas geactiveerd wanneer deze "
                    "module wordt geopend; de normale viewer hoeft hier niet op te wachten."
                ),
                loader=self._load_manufacturing_faces_panel,
            )
            try:
                self.tabifyDockWidget(
                    self._export_center_dock, self._manufacturing_faces_dock
                )
            except Exception:
                pass
            menu = self.menuBar().addMenu("Manufacturing")
            menu.addAction(
                "Manufacturing Faces openen",
                lambda: self._show_lazy("manufacturing_faces"),
            )
            menu.addAction(self._manufacturing_faces_dock.toggleViewAction())

        def _load_manufacturing_faces_panel(self) -> Any:
            from cws_viewer.ui_qt.manufacturing_faces_v15 import ManufacturingFacesPanel

            panel = ManufacturingFacesPanel(self.viewer, self.project, parent=self)
            panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 6500)
            )
            self._manufacturing_faces_panel = panel
            return panel

        # ------------------------------------------------------------------
        # Phase 1 visual/default workspace
        def _apply_phase1_visual_design(self) -> None:
            self.setStyleSheet(self.styleSheet() + _PHASE1_QSS)
            root = self.centralWidget()
            if root is not None and root.layout() is not None:
                root.layout().setContentsMargins(0, 0, 0, 0)
                root.layout().setSpacing(0)

            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText("V15 · Phase 1")
                    break

            rename = {
                "Vensterselectie": "Selecteer",
                "Rondkijken": "Kijk",
                "Alles tonen": "Toon alles",
                "Los scherm": "Los venster",
            }
            for toolbar in self.findChildren(QtWidgets.QToolBar):
                toolbar.setObjectName("cwsPhase1CommandBar")
                toolbar.setMovable(False)
                toolbar.setFloatable(False)
                toolbar.setIconSize(QtCore.QSize(16, 16))
                for action in toolbar.actions():
                    text = action.text().replace("&", "")
                    if text in rename:
                        action.setText(rename[text])

            theme_combo = getattr(self, "_theme_combo", None)
            if theme_combo is not None:
                theme_combo.hide()
                workspace_menu = next(
                    (
                        menu
                        for menu in self.menuBar().findChildren(QtWidgets.QMenu)
                        if menu.title().replace("&", "") == "Werkruimte"
                    ),
                    None,
                )
                if workspace_menu is not None:
                    theme_menu = workspace_menu.addMenu("Thema")
                    for index in range(theme_combo.count()):
                        title = theme_combo.itemText(index)
                        theme_menu.addAction(
                            title,
                            lambda _checked=False, i=index: theme_combo.setCurrentIndex(i),
                        )

            self.setDockOptions(
                QtWidgets.QMainWindow.DockOption.AnimatedDocks
                | QtWidgets.QMainWindow.DockOption.AllowNestedDocks
                | QtWidgets.QMainWindow.DockOption.AllowTabbedDocks
            )
            self.setTabPosition(
                QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                QtWidgets.QTabWidget.TabPosition.North,
            )
            self.setTabPosition(
                QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
                QtWidgets.QTabWidget.TabPosition.North,
            )

        def _apply_phase1_layout_policy(self) -> None:
            current = int(self._settings.value("viewer/phase1LayoutVersion", 0) or 0)
            if current != PHASE1_LAYOUT_VERSION:
                self._reset_v15_layout()
                self._settings.setValue(
                    "viewer/phase1LayoutVersion", PHASE1_LAYOUT_VERSION
                )
                self._settings.sync()

        def _reset_v15_layout(self) -> None:
            # Clean engineering default: model first, structure left, properties right.
            self._v15_focus_snapshot = None
            for dock in self._v15_docks.values():
                dock.setFloating(False)

            self.addDockWidget(
                QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self._project_dock
            )
            self.addDockWidget(
                QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self._properties_dock
            )
            self._project_dock.show()
            self._properties_dock.show()

            for key in ("view", "selection", "export_center", "manufacturing_faces"):
                dock = self._v15_docks.get(key)
                if dock is not None:
                    self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
                    try:
                        self.tabifyDockWidget(self._properties_dock, dock)
                    except Exception:
                        pass
                    dock.hide()

            for key in ("workbench", "review", "coordination"):
                dock = self._v15_docks.get(key)
                if dock is not None:
                    self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, dock)
                    dock.hide()

            try:
                self.resizeDocks(
                    [self._project_dock, self._properties_dock],
                    [300, 360],
                    QtCore.Qt.Orientation.Horizontal,
                )
            except Exception:
                pass
            self._properties_dock.raise_()
            self.statusBar().showMessage(
                "Phase 1 werkruimte · model eerst · engineeringpanelen laden op aanvraag",
                5000,
            )

        def _materialize_restored_visible_panels(self) -> None:
            for key in tuple(self._phase1_lazy_loaders):
                dock = self._v15_docks.get(key)
                if dock is not None and dock.isVisible():
                    QtCore.QTimer.singleShot(
                        0, lambda k=key: self._materialize_lazy_panel(k)
                    )

        # ------------------------------------------------------------------
        # Diagnostics/performance evidence
        def _record_phase1_startup_metrics(self) -> None:
            workspace_elapsed = time.perf_counter() - self._phase1_started
            report = getattr(self.load_result, "geometry_report", None)
            requested = int(getattr(report, "requested_count", 0) or 0)
            cache_hits = int(getattr(report, "cache_hit_count", 0) or 0)
            payload = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "phase1_build": PHASE1_BUILD,
                "viewer_version": V15_T8_VERSION,
                "project_path": str(self.load_result.project_path),
                "scene_hash": str(self.load_result.scene.scene_hash),
                "load_elapsed_seconds": round(float(self.load_result.elapsed_seconds), 6),
                "workspace_elapsed_seconds": round(workspace_elapsed, 6),
                "geometry_requested": requested,
                "geometry_cache_hits": cache_hits,
                "geometry_cache_hit_ratio": (
                    round(cache_hits / requested, 6) if requested else 0.0
                ),
                "timings": {key: round(float(value), 6) for key, value in self.load_result.timings},
                "lazy_panels": sorted(self._phase1_lazy_loaders),
            }
            try:
                target = Path.home() / ".cws_convertor" / "viewer_startup_metrics.jsonl"
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            except Exception:
                pass
            self.statusBar().showMessage(
                f"Viewer gereed · laden {self.load_result.elapsed_seconds:.1f} s · "
                f"workspace {workspace_elapsed:.1f} s · cache {cache_hits}/{requested}",
                7000,
            )

        def closeEvent(self, event: Any) -> None:
            # T8/T5 close hooks already guard absent lazy panels/services.
            super().closeEvent(event)

else:

    class CwsViewerV15Phase1CockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15Phase1CockpitWindow",
    "PHASE1_BUILD",
    "PHASE1_LAYOUT_VERSION",
    "phase1_workspace_contract",
]
