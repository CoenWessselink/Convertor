"""CWS Viewer V15 T3 cockpit composition.

T0-T2 remain frozen in ``cockpit_v15``.  This layer adds the view/navigation
workspace for T3 while reusing the same canonical project, renderer and V14
interaction baseline.
"""
from __future__ import annotations

from typing import Any

from cws_viewer.core.v15_navigation import V15_T3_SCHEMA, V15_T3_VERSION, navigation_contract
from cws_viewer.ui_qt import cockpit as _v14
from cws_viewer.ui_qt.cockpit_v15 import CwsViewerV15CockpitWindow, workspace_contract
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.view_navigation_v15 import V15ViewNavigationPanel
from cws_viewer.ui_qt.vtk_real_project_widget_v15 import VtkRealProjectWidgetV15

V15_T3_WORKSPACE_SCHEMA = "cws-viewer-workspace-15.1"
V15_T3_WORKSPACE_STATE_VERSION = 15


def t3_workspace_contract() -> dict[str, Any]:
    contract = workspace_contract()
    contract["schema"] = V15_T3_WORKSPACE_SCHEMA
    contract["state_version"] = V15_T3_WORKSPACE_STATE_VERSION
    contract["version"] = V15_T3_VERSION
    contract["docks"] = [
        *contract.get("docks", []),
        {
            "key": "view",
            "title": "Aanzicht / clipping",
            "area": "right",
            "default_size": 360,
        },
    ]
    capabilities = dict(contract.get("capabilities", {}))
    capabilities.update(navigation_contract()["capabilities"])
    capabilities["selected_object_details_shortcut"] = True
    contract["capabilities"] = capabilities
    contract["navigation"] = navigation_contract()
    return contract


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class CwsViewerV15T3CockpitWindow(CwsViewerV15CockpitWindow):
        """T3 view/navigation/clipping shell over the proven T0-T2 workspace."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            previous_widget = _v14.VtkRealProjectWidget
            _v14.VtkRealProjectWidget = VtkRealProjectWidgetV15
            try:
                super().__init__(*args, **kwargs)
            finally:
                _v14.VtkRealProjectWidget = previous_widget

            if not isinstance(self.viewer, VtkRealProjectWidgetV15):
                raise RuntimeError("V15 T3 viewerhost kon niet worden geactiveerd")

            self.setObjectName("cwsViewerV15T3CockpitWindow")
            self.setWindowTitle(
                f"CWS Viewer V15 T3 — {getattr(self.project, 'project_name', 'Project')}"
            )
            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText(V15_T3_VERSION)
                    break

            self._install_t3_view_dock()
            self._install_t3_view_menu()
            self._install_t3_selection_shortcuts()
            self._restore_v15_state()
            self._set_navigation(_v14.NavigationMode.ORBIT)
            self.statusBar().showMessage(
                "T3 actief · selectiegebonden orbit · picked-depth pan · view-from-face · section/clipping",
                6500,
            )

        def _install_t3_view_dock(self) -> None:
            self._t3_view_panel = V15ViewNavigationPanel(self.viewer, self)
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

        def _install_t3_view_menu(self) -> None:
            menu = self.menuBar().addMenu("Aanzicht T3")
            menu.addAction(self._view_dock.toggleViewAction())
            menu.addSeparator()
            back = QtGui.QAction("Vorige camera", self)
            back.setShortcut(QtGui.QKeySequence("Alt+Left"))
            back.triggered.connect(lambda: self._camera_menu_action(self.viewer.view_navigation.camera_back))
            menu.addAction(back)
            forward = QtGui.QAction("Volgende camera", self)
            forward.setShortcut(QtGui.QKeySequence("Alt+Right"))
            forward.triggered.connect(lambda: self._camera_menu_action(self.viewer.view_navigation.camera_forward))
            menu.addAction(forward)
            zoom = QtGui.QAction("Zoomgebied", self)
            zoom.setShortcut(QtGui.QKeySequence("Z"))
            zoom.triggered.connect(lambda: self.viewer.set_zoom_area(True))
            menu.addAction(zoom)
            menu.addSeparator()
            menu.addAction("Aanzicht / clipping panel", lambda: self._view_dock.show())

        def _install_t3_selection_shortcuts(self) -> None:
            # Trimble Connect for Windows uses Enter to open the selected
            # object's details. CWS maps that visible workflow to the existing
            # canonical Properties/Provenance dock instead of inventing a second
            # details window.
            self._details_return_shortcut = QtGui.QShortcut(
                QtGui.QKeySequence("Return"), self
            )
            self._details_return_shortcut.activated.connect(self._focus_selected_details)
            self._details_enter_shortcut = QtGui.QShortcut(
                QtGui.QKeySequence("Enter"), self
            )
            self._details_enter_shortcut.activated.connect(self._focus_selected_details)

        def _focus_selected_details(self) -> None:
            if not self.viewer.controller.get_selection():
                self.statusBar().showMessage("Selecteer eerst een object om details te openen", 3500)
                return
            try:
                self._properties_dock.show()
                self._properties_dock.raise_()
            except Exception:
                pass
            self._properties.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)
            self.statusBar().showMessage("Eigenschappen van selectie actief", 3500)

        def _camera_menu_action(self, function: Any) -> None:
            function()
            self._t3_view_panel.refresh()

        def _set_navigation(self, mode: Any) -> None:
            super()._set_navigation(mode)
            if mode == _v14.NavigationMode.ORBIT:
                self._tool_status.setText(
                    "Roteren · selectie = draaipunt op onderdeel/assembly · zonder selectie = exact punt onder muis"
                )
            elif mode == _v14.NavigationMode.PAN:
                self._tool_status.setText(
                    "Pan · beweging volgt de diepte van het punt waar de sleepbeweging start"
                )

        def _reset_v15_layout(self) -> None:
            super()._reset_v15_layout()
            if hasattr(self, "_view_dock"):
                self._view_dock.setFloating(False)
                self.addDockWidget(
                    QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self._view_dock
                )
                self._view_dock.show()

        def closeEvent(self, event: Any) -> None:
            try:
                self._settings.setValue("viewer/v15WorkspaceSchema", V15_T3_WORKSPACE_SCHEMA)
            except Exception:
                pass
            super().closeEvent(event)

else:

    class CwsViewerV15T3CockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15T3CockpitWindow",
    "V15_T3_SCHEMA",
    "V15_T3_VERSION",
    "V15_T3_WORKSPACE_SCHEMA",
    "V15_T3_WORKSPACE_STATE_VERSION",
    "t3_workspace_contract",
]
