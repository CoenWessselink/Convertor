"""CWS Viewer preview.2 cockpit focused on local Trimble-like 3D workflows."""
from __future__ import annotations

from typing import Any

from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.core.viewer_feel_navigation_v2 import viewer_feel_navigation_v2_contract
from cws_viewer.review.feel_v2_service import FeelV2ReviewWorkspaceService
from cws_viewer.ui_qt import cockpit_feel_fix_v15 as _feel_cockpit
from cws_viewer.ui_qt.cockpit_feel_fix_v15 import (
    CwsViewerV15FeelFixCockpitWindow,
    viewer_feel_workspace_contract,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.views_strip_feel_v2 import CwsViewsStripV2
from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2

FEEL_V2_BUILD = "viewer-trimble-feel-v2"


def trimble_feel_v2_workspace_contract() -> dict[str, Any]:
    contract = viewer_feel_workspace_contract()
    caps = dict(contract.get("capabilities", {}))
    caps.update(viewer_feel_navigation_v2_contract()["capabilities"])
    caps.update(
        {
            "ifc_source_presentation_colours": True,
            "original_colour_means_imported_colour": True,
            "ssao_contact_shading_interactive": True,
            "balanced_studio_lighting": True,
            "selected_object_fill_highlight": True,
            "selection_feature_edge_outline": True,
            "ctrl_click_multi_selection": True,
            "grid_list_to_3d_selection": True,
            "3d_to_grid_list_selection": True,
            "assembly_part_level_toolbar": True,
            "persistent_bottom_views_strip": True,
            "views_strip_search": True,
            "views_strip_groups": True,
            "views_strip_slideshow": True,
            "views_strip_update_rename_delete": True,
            "measurement_foreground_labels": True,
            "measurement_from_to_markers": True,
            "measurement_live_hover_preview": True,
            "measurement_overlay_camera_tracking": True,
        }
    )
    docks = list(contract.get("docks", ()))
    if not any(item.get("key") == "views_strip" for item in docks):
        docks.append(
            {
                "key": "views_strip",
                "title": "Views",
                "area": "bottom",
                "default_size": 125,
            }
        )
    contract["docks"] = docks
    contract["capabilities"] = caps
    contract["feel_v2"] = {
        "build": FEEL_V2_BUILD,
        "navigation": viewer_feel_navigation_v2_contract(),
        "selection_policy": {
            "ctrl_click": "toggle/add multiselect",
            "shift_click": "add",
            "levels": ["assembly/merk", "part/onderdeel"],
            "tree_grid_3d_bidirectional": True,
        },
        "graphics": {
            "source_ifc_colours": True,
            "tessellation_edges": False,
            "hard_edge_normals": True,
            "fxaa": True,
            "msaa_interactive": 8,
            "ssao_contact_shading": True,
            "depth_peeling": True,
        },
        "measurements": {
            "foreground_label": True,
            "from_to_markers": True,
            "live_preview": True,
            "distance_colour": "red",
            "horizontal_vertical_colour": "blue",
        },
    }
    return contract


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    _EXTRA_QSS = """
QWidget#cwsViewsStripV2 {
    background: #f7f8fa;
    border-top: 1px solid #cdd3db;
}
QLabel#cwsViewsStripTitle {
    color: #26384d;
    font-size: 10pt;
    font-weight: 700;
}
QPushButton#cwsViewCard {
    background: #ffffff;
    border: 1px solid #cfd5dc;
    border-radius: 4px;
    padding: 7px 10px;
    text-align: left;
    color: #26384d;
}
QPushButton#cwsViewCard:hover {
    border: 1px solid #2386d8;
    background: #f1f8ff;
}
QComboBox#cwsSelectionLevelQuick {
    min-width: 118px;
    min-height: 24px;
}
"""

    class CwsViewerV15TrimbleFeelV2CockpitWindow(CwsViewerV15FeelFixCockpitWindow):
        """Single-build local viewer parity cockpit."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            previous = _feel_cockpit.VtkRealProjectWidgetFeel
            _feel_cockpit.VtkRealProjectWidgetFeel = VtkRealProjectWidgetFeelV2
            try:
                super().__init__(*args, **kwargs)
            finally:
                _feel_cockpit.VtkRealProjectWidgetFeel = previous

            if not isinstance(self.viewer, VtkRealProjectWidgetFeelV2):
                raise RuntimeError("Trimble-feel V2 input/render host kon niet worden geactiveerd")
            self.setObjectName("cwsViewerV15TrimbleFeelV2CockpitWindow")
            self.setStyleSheet(self.styleSheet() + _EXTRA_QSS)
            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText("1.4.0-v15-preview.2")
                    break
            self._install_views_strip()
            self._connect_grid_bidirectional_selection()
            self.statusBar().showMessage(
                "preview.2 · horizontaal orbit blijft waterpas · IFC-bronkleuren · contactschaduw · Views · live meten",
                8500,
            )

        # --------------------------------------------------------------
        # Lightweight level selector in the main command bar
        def _build_toolbar(self) -> Any:
            frame = super()._build_toolbar()
            bar = frame.findChild(QtWidgets.QToolBar)
            if bar is not None:
                bar.addSeparator()
                label = QtWidgets.QLabel("Selectie:")
                bar.addWidget(label)
                combo = QtWidgets.QComboBox()
                combo.setObjectName("cwsSelectionLevelQuick")
                combo.addItem("Onderdeel", SelectionLevel.PART.value)
                combo.addItem("Merk / assembly", SelectionLevel.ASSEMBLY.value)
                current = self.viewer.controller.session.selection_level.value
                index = combo.findData(current)
                combo.setCurrentIndex(max(0, index))
                combo.currentIndexChanged.connect(self._quick_selection_level_changed)
                bar.addWidget(combo)
                self._quick_selection_level = combo
            return frame

        def _quick_selection_level_changed(self, _index: int) -> None:
            combo = getattr(self, "_quick_selection_level", None)
            if combo is None:
                return
            level = SelectionLevel(str(combo.currentData() or SelectionLevel.PART.value))
            controller = self.viewer.controller
            controller.set_selection_level(level)
            current = controller.get_selection()
            if current:
                promoted = tuple(
                    dict.fromkeys(
                        controller.index.selectable_node_for_level(node_id, level)
                        for node_id in current
                    )
                )
                controller.set_selection(promoted, mode="replace")
            panel = getattr(self, "_selection_panel", None)
            if panel is not None:
                panel.refresh()
            self.statusBar().showMessage(
                "Selectieniveau: Merk / assembly" if level == SelectionLevel.ASSEMBLY else "Selectieniveau: Onderdeel",
                3500,
            )

        # --------------------------------------------------------------
        # Use editable Phase-2 review state while preserving lazy review UI
        def _install_t5_review_workspace(self) -> None:
            scene = self.viewer.controller.index.scene
            self._review_service = FeelV2ReviewWorkspaceService(
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
                    self._phase1_failures["review_sidecar"] = f"{type(exc).__name__}: {exc}"

            self._review_dock = self._make_lazy_dock(
                key="review",
                title="Review / Issues",
                area=QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
                hint=(
                    "Saved Views, Markups en Issues zijn beschikbaar via de Views-strip en de "
                    "Reviewwerkruimte. Het zware reviewpaneel blijft on-demand."
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

        def _install_views_strip(self) -> None:
            strip = CwsViewsStripV2(self._review_service, self)
            strip.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 4500)
            )
            dock = QtWidgets.QDockWidget("Views", self)
            dock.setObjectName("cwsV15Dock_views_strip")
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)
            dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
            # A lightweight strip should look like part of the viewer rather than
            # another engineering tool window.
            title_bar = QtWidgets.QWidget(dock)
            title_bar.setFixedHeight(1)
            dock.setTitleBarWidget(title_bar)
            dock.setWidget(strip)
            dock.setMinimumHeight(100)
            dock.setMaximumHeight(180)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, dock)
            self._views_strip = strip
            self._views_strip_dock = dock
            self._v15_docks["views_strip"] = dock
            dock.show()
            try:
                self.resizeDocks([dock], [124], QtCore.Qt.Orientation.Vertical)
            except Exception:
                pass

        # --------------------------------------------------------------
        # 3D/tree/grid selection is one stable-ID selection state
        def _connect_grid_bidirectional_selection(self) -> None:
            grid = getattr(self, "_project_grid", None)
            if grid is not None:
                grid.entities_selected.connect(self._grid_selection_feedback)

        def _grid_selection_feedback(self, entity_ids: tuple[str, ...]) -> None:
            if self._syncing:
                return
            if not entity_ids:
                self.viewer.controller.set_selection((), mode="replace")

        def _selection_changed(self, selection: Any) -> None:
            super()._selection_changed(selection)
            combo = getattr(self, "_quick_selection_level", None)
            if combo is not None:
                level = self.viewer.controller.session.selection_level.value
                combo.blockSignals(True)
                combo.setCurrentIndex(max(0, combo.findData(level)))
                combo.blockSignals(False)
            grid = getattr(self, "_project_grid", None)
            if grid is not None and hasattr(grid, "table"):
                selection_model = grid.table.selectionModel()
                if selection_model is not None:
                    selection_model.blockSignals(True)
                    try:
                        grid.select_entities(selection.entity_ids)
                    finally:
                        selection_model.blockSignals(False)

        # --------------------------------------------------------------
        # Live from→to measurement feedback
        def _start_measurement(self, kind: Any) -> None:
            super()._start_measurement(kind)
            self.viewer.set_measurement_preview_anchor(None, kind)

        def _viewer_pick(self, pick: Any) -> None:
            active_before = self._measurement_kind
            super()._viewer_pick(pick)
            if active_before is None:
                return
            if self._measurement_anchors:
                self.viewer.set_measurement_preview_anchor(
                    self._measurement_anchors[-1].world_point,
                    self._measurement_kind,
                )
            else:
                self.viewer.set_measurement_preview_anchor(None, None)

        def _clear_measurements(self) -> None:
            self.viewer.set_measurement_preview_anchor(None, None)
            super()._clear_measurements()

        def _cancel_tool(self) -> None:
            self.viewer.set_measurement_preview_anchor(None, None)
            super()._cancel_tool()

else:

    class CwsViewerV15TrimbleFeelV2CockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15TrimbleFeelV2CockpitWindow",
    "FEEL_V2_BUILD",
    "trimble_feel_v2_workspace_contract",
]
