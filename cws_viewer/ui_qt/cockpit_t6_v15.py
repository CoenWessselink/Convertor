"""CWS Viewer V15 T6 cockpit: assemblies, compare, clash and sequence."""
from __future__ import annotations

from typing import Any

from cws_viewer.coordination import (
    V15_T6_SCHEMA,
    V15_T6_VERSION,
    coordination_contract,
)
from cws_viewer.coordination.review_bridge import T6ReviewServiceBridge
from cws_viewer.ui_qt.cockpit_t5_v15 import (
    CwsViewerV15T5CockpitWindow,
    t5_workspace_contract,
)
from cws_viewer.ui_qt.coordination_v15 import V15CoordinationPanel
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

V15_T6_WORKSPACE_SCHEMA = "cws-viewer-workspace-15.1"
V15_T6_WORKSPACE_STATE_VERSION = 15


def t6_workspace_contract() -> dict[str, Any]:
    contract = t5_workspace_contract()
    contract["schema"] = V15_T6_WORKSPACE_SCHEMA
    contract["state_version"] = V15_T6_WORKSPACE_STATE_VERSION
    contract["version"] = V15_T6_VERSION
    contract["docks"] = [
        *contract.get("docks", []),
        {
            "key": "coordination",
            "title": "Assemblies / Compare / Clash / Sequence",
            "area": "bottom",
            "default_size": 370,
        },
    ]
    capabilities = dict(contract.get("capabilities", {}))
    capabilities.update(coordination_contract()["capabilities"])
    contract["capabilities"] = capabilities
    contract["coordination"] = coordination_contract()
    return contract


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class CwsViewerV15T6CockpitWindow(CwsViewerV15T5CockpitWindow):
        """T6 coordination shell; all mutations remain viewer/review state."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.setObjectName("cwsViewerV15T6CockpitWindow")
            self.setWindowTitle(
                f"CWS Viewer V15 T6 — {getattr(self.project, 'project_name', 'Project')}"
            )
            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText(V15_T6_VERSION)
                    break
            self._install_t6_coordination_workspace()
            self._restore_v15_state()
            self.statusBar().showMessage(
                "T6 actief · assembly drilldown · canonical compare · spatial clash/preflight · viewer sequence",
                8000,
            )

        def _install_t6_coordination_workspace(self) -> None:
            review_service = getattr(self, "_review_service", None)
            review_bridge = (
                None if review_service is None else T6ReviewServiceBridge(review_service)
            )
            panel = V15CoordinationPanel(
                self.viewer,
                self.project,
                review_service=review_bridge,
                parent=self,
            )
            panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 5200)
            )
            dock = QtWidgets.QDockWidget(
                "Assemblies / Compare / Clash / Sequence", self
            )
            dock.setObjectName("cwsV15Dock_coordination")
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
            dock.setFeatures(
                QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            )
            dock.setWidget(panel)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, dock)
            self._coordination_panel = panel
            self._coordination_dock = dock
            self._v15_docks["coordination"] = dock
            try:
                self.tabifyDockWidget(self._review_dock, self._coordination_dock)
                self._review_dock.raise_()
            except Exception:
                pass

            menu = self.menuBar().addMenu("Coördinatie T6")
            menu.addAction(dock.toggleViewAction())
            menu.addAction("Assemblies", lambda: self._show_coordination_tab(0))
            menu.addAction("Compare", lambda: self._show_coordination_tab(1))
            menu.addAction("Clash / preflight", lambda: self._show_coordination_tab(2))
            menu.addAction("Sequence", lambda: self._show_coordination_tab(3))
            menu.addSeparator()
            menu.addAction("Sequence reset", panel._reset_sequence)

        def _show_coordination_tab(self, index: int) -> None:
            self._coordination_dock.show()
            self._coordination_dock.raise_()
            self._coordination_panel.tabs.setCurrentIndex(int(index))

        def _selection_changed(self, selection: Any) -> None:
            super()._selection_changed(selection)
            panel = getattr(self, "_coordination_panel", None)
            if panel is not None:
                panel.refresh_sequence_summary()

        def _reset_v15_layout(self) -> None:
            super()._reset_v15_layout()
            if hasattr(self, "_coordination_dock"):
                self._coordination_dock.setFloating(False)
                self.addDockWidget(
                    QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
                    self._coordination_dock,
                )
                self._coordination_dock.show()
                try:
                    self.tabifyDockWidget(self._review_dock, self._coordination_dock)
                except Exception:
                    pass

else:

    class CwsViewerV15T6CockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15T6CockpitWindow",
    "V15_T6_SCHEMA",
    "V15_T6_VERSION",
    "V15_T6_WORKSPACE_SCHEMA",
    "V15_T6_WORKSPACE_STATE_VERSION",
    "t6_workspace_contract",
]
