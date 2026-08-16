"""CWS Viewer V15 T5 cockpit: Saved Views, Markups and Issues/ToDos."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.review import (
    V15ReviewWorkspaceService,
    V15_T5_SCHEMA,
    V15_T5_VERSION,
    review_workspace_contract,
)
from cws_viewer.ui_qt.cockpit_t4_v15 import (
    CwsViewerV15T4CockpitWindow,
    t4_workspace_contract,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.review_v15 import V15ReviewPanel

V15_T5_WORKSPACE_SCHEMA = "cws-viewer-workspace-15.1"
V15_T5_WORKSPACE_STATE_VERSION = 15


def t5_workspace_contract() -> dict[str, Any]:
    contract = t4_workspace_contract()
    contract["schema"] = V15_T5_WORKSPACE_SCHEMA
    contract["state_version"] = V15_T5_WORKSPACE_STATE_VERSION
    contract["version"] = V15_T5_VERSION
    contract["docks"] = [
        *contract.get("docks", []),
        {
            "key": "review",
            "title": "Review / Issues",
            "area": "bottom",
            "default_size": 330,
        },
    ]
    capabilities = dict(contract.get("capabilities", {}))
    capabilities.update(review_workspace_contract()["capabilities"])
    contract["capabilities"] = capabilities
    contract["review"] = review_workspace_contract()
    return contract


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class CwsViewerV15T5CockpitWindow(CwsViewerV15T4CockpitWindow):
        """T5 review shell with independent saved-view and issue lifecycles."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.setObjectName("cwsViewerV15T5CockpitWindow")
            self.setWindowTitle(
                f"CWS Viewer V15 T5 — {getattr(self.project, 'project_name', 'Project')}"
            )
            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText(V15_T5_VERSION)
                    break
            self._install_t5_review_workspace()
            self._restore_v15_state()
            self.statusBar().showMessage(
                "T5 actief · Saved Views onafhankelijk · Markups · Issues/ToDos · stale-reference detectie",
                7500,
            )

        def _review_store_path(self) -> Path:
            source = Path(self.load_result.project_path).expanduser().resolve()
            return source.with_suffix(source.suffix + ".cwsreview.json")

        def _project_review_metadata(self) -> dict[str, Any]:
            return {
                "project_name": str(getattr(self.project, "project_name", "") or ""),
                "client": str(getattr(self.project, "client", "") or ""),
                "order": str(
                    getattr(self.project, "order", getattr(self.project, "order_number", ""))
                    or ""
                ),
                "revision_id": str(
                    getattr(self.project, "revision_id", getattr(self.project, "revision", ""))
                    or ""
                ),
            }

        def _install_t5_review_workspace(self) -> None:
            scene = self.viewer.controller.index.scene
            self._review_service = V15ReviewWorkspaceService(
                self.viewer.controller,
                project_id=scene.project_id,
                scene_hash=scene.scene_hash,
                store_path=self._review_store_path(),
                project_metadata=self._project_review_metadata(),
            )
            panel = V15ReviewPanel(self.viewer, self._review_service, self)
            panel.status_changed.connect(
                lambda text: self.statusBar().showMessage(str(text), 5000)
            )
            dock = QtWidgets.QDockWidget("Review / Issues", self)
            dock.setObjectName("cwsV15Dock_review")
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
            dock.setFeatures(
                QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            )
            dock.setWidget(panel)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, dock)
            self._review_panel = panel
            self._review_dock = dock
            self._v15_docks["review"] = dock
            try:
                self.tabifyDockWidget(self._workbench_dock, self._review_dock)
                self._workbench_dock.raise_()
            except Exception:
                pass

            menu = self.menuBar().addMenu("Review T5")
            menu.addAction(dock.toggleViewAction())
            menu.addAction("Saved Views", lambda: self._show_review_tab(0))
            menu.addAction("Issues / ToDos", lambda: self._show_review_tab(1))
            menu.addAction("Markups", lambda: self._show_review_tab(2))
            menu.addSeparator()
            menu.addAction("Review opslaan", self._save_review)
            menu.addAction("Review heropenen", self._reload_review)

            if self._review_service.store_path and self._review_service.store_path.exists():
                try:
                    report = self._review_service.load()
                    panel.refresh()
                    self.statusBar().showMessage(
                        f"Review sidecar hersteld · {report['issues']} issues · {report['stale_issues']} stale",
                        6500,
                    )
                except Exception as exc:
                    self.statusBar().showMessage(
                        f"Review sidecar niet automatisch geladen: {type(exc).__name__}: {exc}",
                        7000,
                    )

        def _show_review_tab(self, index: int) -> None:
            self._review_dock.show()
            self._review_dock.raise_()
            self._review_panel.tabs.setCurrentIndex(int(index))

        def _save_review(self) -> None:
            try:
                self._review_service.save()
                self._review_panel.refresh()
                self.statusBar().showMessage("Review sidecar opgeslagen", 4500)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Review opslaan", f"{type(exc).__name__}: {exc}"
                )

        def _reload_review(self) -> None:
            try:
                report = self._review_service.load()
                self._review_panel.refresh()
                self.statusBar().showMessage(
                    f"Review heropend · {report['issues']} issues · {report['stale_issues']} stale",
                    5000,
                )
            except FileNotFoundError:
                QtWidgets.QMessageBox.information(
                    self, "Review heropenen", "Er is nog geen review sidecar opgeslagen."
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Review heropenen", f"{type(exc).__name__}: {exc}"
                )

        def _selection_changed(self, selection: Any) -> None:
            super()._selection_changed(selection)
            panel = getattr(self, "_review_panel", None)
            if panel is not None:
                panel.refresh()

        def _reset_v15_layout(self) -> None:
            super()._reset_v15_layout()
            if hasattr(self, "_review_dock"):
                self._review_dock.setFloating(False)
                self.addDockWidget(
                    QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self._review_dock
                )
                self._review_dock.show()
                try:
                    self.tabifyDockWidget(self._workbench_dock, self._review_dock)
                except Exception:
                    pass

        def closeEvent(self, event: Any) -> None:
            service = getattr(self, "_review_service", None)
            if service is not None and service.store_path is not None:
                try:
                    service.save()
                except Exception as exc:
                    self.statusBar().showMessage(
                        f"Review autosave mislukt: {type(exc).__name__}: {exc}", 3000
                    )
            super().closeEvent(event)

else:

    class CwsViewerV15T5CockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15T5CockpitWindow",
    "V15_T5_SCHEMA",
    "V15_T5_VERSION",
    "V15_T5_WORKSPACE_SCHEMA",
    "V15_T5_WORKSPACE_STATE_VERSION",
    "t5_workspace_contract",
]
