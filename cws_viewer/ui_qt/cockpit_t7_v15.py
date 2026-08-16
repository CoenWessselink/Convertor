"""CWS Viewer V15 T7 cockpit: scope-first verified Export Center."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.export_center import V15_T7_SCHEMA, V15_T7_VERSION, export_center_contract
from cws_viewer.ui_qt.cockpit_t6_v15 import CwsViewerV15T6CockpitWindow, t6_workspace_contract
from cws_viewer.ui_qt.export_center_v15 import V15ExportCenterPanel
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

V15_T7_WORKSPACE_SCHEMA = "cws-viewer-workspace-15.1"
V15_T7_WORKSPACE_STATE_VERSION = 15


def t7_workspace_contract() -> dict[str, Any]:
    contract = t6_workspace_contract()
    contract["schema"] = V15_T7_WORKSPACE_SCHEMA
    contract["state_version"] = V15_T7_WORKSPACE_STATE_VERSION
    contract["version"] = V15_T7_VERSION
    contract["docks"] = [
        *contract.get("docks", []),
        {
            "key": "export_center",
            "title": "Export Center",
            "area": "right",
            "default_size": 390,
        },
    ]
    capabilities = dict(contract.get("capabilities", {}))
    capabilities.update(export_center_contract()["capabilities"])
    contract["capabilities"] = capabilities
    contract["export_center"] = export_center_contract()
    return contract


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class CwsViewerV15T7CockpitWindow(CwsViewerV15T6CockpitWindow):
        """T7 viewer shell with explicit, fail-closed production-export scope."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.setObjectName("cwsViewerV15T7CockpitWindow")
            self.setWindowTitle(
                f"CWS Viewer V15 T7 — {getattr(self.project, 'project_name', 'Project')}"
            )
            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText(V15_T7_VERSION)
                    break
            self._install_t7_export_center()
            self._restore_v15_state()
            self.statusBar().showMessage(
                "T7 actief · scope-first export · fail-closed preflight · canonical release-engine · checksums",
                9000,
            )

        def _default_export_dir(self) -> Path:
            source = Path(self.load_result.project_path).expanduser().resolve()
            return source.parent / "CWS_Exports"

        def _install_t7_export_center(self) -> None:
            panel = V15ExportCenterPanel(
                self.viewer,
                self.project,
                default_output_dir=self._default_export_dir(),
                parent=self,
            )
            panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 6500)
            )
            dock = QtWidgets.QDockWidget("Export Center", self)
            dock.setObjectName("cwsV15Dock_export_center")
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
            dock.setFeatures(
                QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            )
            dock.setWidget(panel)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
            self._export_center_panel = panel
            self._export_center_dock = dock
            self._v15_docks["export_center"] = dock
            try:
                self.tabifyDockWidget(self._details_dock, self._export_center_dock)
                self._details_dock.raise_()
            except Exception:
                pass

            menu = self.menuBar().addMenu("Export T7")
            menu.addAction(dock.toggleViewAction())
            menu.addAction("Export Center openen", self._show_export_center)
            menu.addSeparator()
            menu.addAction("Preflight huidige scope", panel._preflight)

        def _show_export_center(self) -> None:
            self._export_center_dock.show()
            self._export_center_dock.raise_()

        def _selection_changed(self, selection: Any) -> None:
            super()._selection_changed(selection)
            panel = getattr(self, "_export_center_panel", None)
            if panel is not None:
                try:
                    if str(panel.scope_combo.currentData()) == "current_selection":
                        panel._invalidate_job("Selectie gewijzigd; export-preflight opnieuw vereist")
                except Exception:
                    pass

        def _reset_v15_layout(self) -> None:
            super()._reset_v15_layout()
            if hasattr(self, "_export_center_dock"):
                self._export_center_dock.setFloating(False)
                self.addDockWidget(
                    QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                    self._export_center_dock,
                )
                self._export_center_dock.show()
                try:
                    self.tabifyDockWidget(self._details_dock, self._export_center_dock)
                except Exception:
                    pass

else:

    class CwsViewerV15T7CockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15T7CockpitWindow",
    "V15_T7_SCHEMA",
    "V15_T7_VERSION",
    "V15_T7_WORKSPACE_SCHEMA",
    "V15_T7_WORKSPACE_STATE_VERSION",
    "t7_workspace_contract",
]
