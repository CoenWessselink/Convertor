"""CWS Viewer V15 Phase 2 cockpit: viewer parity and review workflows.

Phase 2 builds on the Phase 1 viewer-first startup. Heavy review/coordination
panels remain lazy, while the actual VTK input host gains interactive markup
capture and the review layer gains full world-space markup/View Group workflows.
"""
from __future__ import annotations

from typing import Any

from cws_viewer.contracts.enums import ColorScheme, ProjectionType, RenderMode
from cws_viewer.review.phase2_service import (
    PHASE2_REVIEW_VERSION,
    Phase2ReviewWorkspaceService,
    phase2_review_contract,
)
from cws_viewer.ui_qt import cockpit_t3_v15 as _t3
from cws_viewer.ui_qt.cockpit_phase1_v15 import (
    CwsViewerV15Phase1CockpitWindow,
    PHASE1_BUILD,
    phase1_workspace_contract,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.view_navigation_phase2 import (
    V15ViewNavigationPanelPhase2,
    phase2_navigation_contract,
)
from cws_viewer.ui_qt.vtk_real_project_widget_phase2 import VtkRealProjectWidgetPhase2

PHASE2_BUILD = "phase2-viewer-parity-1"
PHASE2_LAYOUT_VERSION = 2


def phase2_workspace_contract() -> dict[str, Any]:
    contract = phase1_workspace_contract()
    capabilities = dict(contract.get("capabilities", {}))
    capabilities.update(phase2_review_contract()["capabilities"])
    capabilities.update(phase2_navigation_contract()["capabilities"])
    capabilities.update(
        {
            "reset_model_display_state": True,
            "phase1_startup_preserved": True,
            "phase2_actual_vtk_input_host": True,
            "phase2_review_panel_remains_lazy": True,
        }
    )
    contract["capabilities"] = capabilities
    contract["phase2"] = {
        "build": PHASE2_BUILD,
        "version": PHASE2_REVIEW_VERSION,
        "parent_build": PHASE1_BUILD,
        "review": phase2_review_contract(),
        "navigation": phase2_navigation_contract(),
        "runtime": {
            "interactive_markup_host": "VtkRealProjectWidgetPhase2",
            "review_panel": "V15ReviewPanelPhase2",
            "review_service": "Phase2ReviewWorkspaceService",
            "review_panel_lazy": True,
        },
    }
    return contract


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class CwsViewerV15Phase2CockpitWindow(CwsViewerV15Phase1CockpitWindow):
        """Phase 2 shell preserving Phase 1 load performance and T0-T8 safety."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            # T3 creates the actual project viewer through its module-level V15
            # host reference and subsequently type-checks against that same
            # reference. Temporarily replace it with the Phase 2 subclass for
            # this one construction, then restore the shared module baseline.
            previous = _t3.VtkRealProjectWidgetV15
            _t3.VtkRealProjectWidgetV15 = VtkRealProjectWidgetPhase2
            try:
                super().__init__(*args, **kwargs)
            finally:
                _t3.VtkRealProjectWidgetV15 = previous

            if not isinstance(self.viewer, VtkRealProjectWidgetPhase2):
                raise RuntimeError("Phase 2 VTK review-input host kon niet worden geactiveerd")
            self.setObjectName("cwsViewerV15Phase2CockpitWindow")
            self.setWindowTitle(
                f"CWS Viewer — {getattr(self.project, 'project_name', 'Project')}"
            )
            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText("V15 · Phase 2")
                    break
            self._install_phase2_commands()
            self.statusBar().showMessage(
                "Phase 2 actief · interactieve markups · review snapshots · View Groups · clipping parity",
                7000,
            )

        # ------------------------------------------------------------------
        # T3 view/clipping panel upgraded in-place during inherited construction
        def _install_t3_view_dock(self) -> None:
            self._t3_view_panel = V15ViewNavigationPanelPhase2(self.viewer, self)
            self._t3_view_panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 4500)
            )
            dock = QtWidgets.QDockWidget("Aanzicht / clipping", self)
            dock.setObjectName("cwsV15Dock_view")
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
            dock.setFeatures(
                QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            )
            dock.setWidget(self._t3_view_panel)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
            self._view_dock = dock
            self._v15_docks["view"] = dock
            try:
                self.resizeDocks(
                    [self._properties_dock, self._view_dock],
                    [390, 360],
                    QtCore.Qt.Orientation.Horizontal,
                )
            except Exception:
                pass

        # ------------------------------------------------------------------
        # T5 service/panel upgraded while keeping Phase 1 lazy startup
        def _install_t5_review_workspace(self) -> None:
            scene = self.viewer.controller.index.scene
            self._review_service = Phase2ReviewWorkspaceService(
                self.viewer.controller,
                project_id=scene.project_id,
                scene_hash=scene.scene_hash,
                store_path=self._review_store_path(),
                project_metadata=self._project_review_metadata(),
            )
            store = self._review_service.store_path
            if store is not None and store.exists():
                try:
                    self._review_service.load()
                except Exception as exc:
                    self._phase1_failures["review_sidecar"] = (
                        f"{type(exc).__name__}: {exc}"
                    )

            self._review_dock = self._make_lazy_dock(
                key="review",
                title="Review / Issues",
                area=QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
                hint=(
                    "Interactieve Markups, Saved Views, View Groups en Issues worden pas "
                    "als QWidget opgebouwd wanneer u Review opent. Reviewstate zelf is al "
                    "veilig geladen, zodat de snelle Phase-1 startup behouden blijft."
                ),
                loader=self._load_review_panel,
            )
            try:
                self.tabifyDockWidget(self._workbench_dock, self._review_dock)
                self._workbench_dock.raise_()
            except Exception:
                pass
            menu = self.menuBar().addMenu("Review")
            menu.addAction("Saved Views / Groups", lambda: self._show_lazy("review", tab_index=0))
            menu.addAction("Issues / ToDos", lambda: self._show_lazy("review", tab_index=1))
            menu.addAction("Markups", lambda: self._show_lazy("review", tab_index=2))
            menu.addSeparator()
            menu.addAction(self._review_dock.toggleViewAction())

        def _load_review_panel(self) -> Any:
            from cws_viewer.ui_qt.review_phase2 import V15ReviewPanelPhase2

            panel = V15ReviewPanelPhase2(self.viewer, self._review_service, self)
            panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 5000)
            )
            self._review_panel = panel
            panel.refresh()
            return panel

        # ------------------------------------------------------------------
        # Global Phase 2 commands
        def _install_phase2_commands(self) -> None:
            menu = self.menuBar().addMenu("Model")
            reset = QtGui.QAction("Reset Model", self)
            reset.setShortcut(QtGui.QKeySequence("Ctrl+Shift+R"))
            reset.triggered.connect(self._reset_model_display_state)
            menu.addAction(reset)
            menu.addSeparator()
            menu.addAction("Review / Markups", lambda: self._show_lazy("review", tab_index=2))
            menu.addAction("Aanzicht / clipping", self._show_phase2_view_dock)
            self._phase2_reset_action = reset

            # Keep the Phase 1 command bar visually compact; append only one
            # globally useful recovery command rather than another full ribbon.
            toolbars = self.findChildren(QtWidgets.QToolBar)
            if toolbars:
                toolbars[0].addSeparator()
                toolbars[0].addAction(reset)

        def _show_phase2_view_dock(self) -> None:
            self._view_dock.show()
            self._view_dock.raise_()
            self._t3_view_panel.refresh()

        def _reset_model_display_state(self) -> None:
            """Return transient model display state to a predictable baseline.

            Persistent review records (markups/issues/measurements/Saved Views)
            are intentionally not deleted. Reset Model only clears transient
            display/navigation state.
            """
            try:
                if hasattr(self.viewer, "cancel_markup_tool"):
                    self.viewer.cancel_markup_tool()
                self.viewer.controller.cancel_tool()
                self.viewer.controller.show_all()
                self.viewer.controller.clear_transparency()
                self.viewer.controller.reset_explode()
                self.viewer.view_navigation.clear_sections()
                self.viewer.view_navigation.clear_clip_box()
                self.viewer.controller.set_selection((), mode="replace")
                self.viewer.controller.set_projection(ProjectionType.PERSPECTIVE)
                self.viewer.controller.set_render_mode(RenderMode.SHADED_EDGES)
                self.interaction.apply_color_scheme(ColorScheme.ORIGINAL)
                self.viewer.controller.fit_all()
                try:
                    self._t3_view_panel.refresh()
                except Exception:
                    pass
                review = getattr(self, "_review_panel", None)
                if review is not None:
                    review.refresh()
                self.statusBar().showMessage(
                    "Reset Model uitgevoerd · reviewdata behouden · tijdelijke displaystate hersteld",
                    5000,
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Reset Model", f"{type(exc).__name__}: {exc}"
                )

else:

    class CwsViewerV15Phase2CockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15Phase2CockpitWindow",
    "PHASE2_BUILD",
    "PHASE2_LAYOUT_VERSION",
    "phase2_workspace_contract",
]
