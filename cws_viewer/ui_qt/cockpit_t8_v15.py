"""CWS Viewer V15 T8 cockpit: canonical ManufacturingFace inspection."""
from __future__ import annotations

from typing import Any

from cws_viewer.ui_qt.cockpit_t7_v15 import CwsViewerV15T7CockpitWindow, t7_workspace_contract
from cws_viewer.ui_qt.manufacturing_faces_v15 import ManufacturingFacesPanel
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

V15_T8_VERSION = "1.4.0-v15-preview.1"
V15_T8_WORKSPACE_SCHEMA = "cws-viewer-workspace-15.2"
V15_T8_WORKSPACE_STATE_VERSION = 16


def t8_manufacturing_contract() -> dict[str, Any]:
    return {
        "schema": "cws-viewer-manufacturing-face-1.0",
        "version": V15_T8_VERSION,
        "capabilities": {
            "canonical_manufacturing_faces": True,
            "right_handed_face_local_frames": True,
            "standard_i_face_resolver": True,
            "standard_u_c_face_resolver": True,
            "standard_l_face_resolver": True,
            "standard_rhs_shs_face_resolver": True,
            "round_surface_special_case": True,
            "custom_profile_no_guessing": True,
            "face_geometry_hash": True,
            "independent_face_validator": True,
            "dstv_mapping_is_adapter": True,
            "ambiguous_dstv_mapping_blocks": True,
            "manufacturing_face_viewer_overlay": True,
            "face_normal_overlay": True,
            "face_status_visualization": True,
        },
        "safety": {
            "manufacturing_face_is_drawing_decoration": False,
            "dstv_label_is_canonical_face_identity": False,
            "unconfirmed_dstv_mapping_allowed": False,
            "custom_profile_role_guessing": False,
            "marking_feature_development": True,
            "production_marking_released": False,
            "machine_transfer_allowed": False,
        },
    }


def t8_workspace_contract() -> dict[str, Any]:
    contract = t7_workspace_contract()
    contract["schema"] = V15_T8_WORKSPACE_SCHEMA
    contract["state_version"] = V15_T8_WORKSPACE_STATE_VERSION
    contract["version"] = V15_T8_VERSION
    contract["docks"] = [
        *contract.get("docks", []),
        {
            "key": "manufacturing_faces",
            "title": "Manufacturing Faces",
            "area": "right",
            "default_size": 430,
        },
    ]
    capabilities = dict(contract.get("capabilities", {}))
    capabilities.update(t8_manufacturing_contract()["capabilities"])
    contract["capabilities"] = capabilities
    contract["manufacturing"] = t8_manufacturing_contract()
    return contract


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class CwsViewerV15T8CockpitWindow(CwsViewerV15T7CockpitWindow):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.setObjectName("cwsViewerV15T8CockpitWindow")
            self.setWindowTitle(
                f"CWS Viewer V15 T8 — {getattr(self.project, 'project_name', 'Project')}"
            )
            self._install_manufacturing_faces()
            self._restore_v15_state()
            self.statusBar().showMessage(
                "T8 actief · canonical manufacturing faces · face-local frames · DSTV adapter fail-closed",
                9000,
            )

        def _install_manufacturing_faces(self) -> None:
            panel = ManufacturingFacesPanel(self.viewer, self.project, parent=self)
            panel.status_changed.connect(lambda text: self.statusBar().showMessage(str(text), 6500))
            dock = QtWidgets.QDockWidget("Manufacturing Faces", self)
            dock.setObjectName("cwsV15Dock_manufacturing_faces")
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.AllDockWidgetAreas)
            dock.setFeatures(
                QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable
            )
            dock.setWidget(panel)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
            self._manufacturing_faces_panel = panel
            self._manufacturing_faces_dock = dock
            self._v15_docks["manufacturing_faces"] = dock
            try:
                self.tabifyDockWidget(self._export_center_dock, dock)
                self._details_dock.raise_()
            except Exception:
                pass
            menu = self.menuBar().addMenu("Manufacturing T8")
            menu.addAction(dock.toggleViewAction())
            menu.addAction("Analyseer geselecteerd onderdeel", panel.analyse_selection)
            menu.addAction("Face overlay wissen", panel.clear_overlay)

        def _selection_changed(self, selection: Any) -> None:
            super()._selection_changed(selection)
            panel = getattr(self, "_manufacturing_faces_panel", None)
            if panel is not None:
                panel.selection_changed()

        def _reset_v15_layout(self) -> None:
            super()._reset_v15_layout()
            if hasattr(self, "_manufacturing_faces_dock"):
                self._manufacturing_faces_dock.setFloating(False)
                self.addDockWidget(
                    QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
                    self._manufacturing_faces_dock,
                )
                self._manufacturing_faces_dock.show()
                try:
                    self.tabifyDockWidget(self._export_center_dock, self._manufacturing_faces_dock)
                except Exception:
                    pass

        def closeEvent(self, event: Any) -> None:
            try:
                if hasattr(self, "_manufacturing_faces_panel"):
                    self._manufacturing_faces_panel.clear_overlay()
            finally:
                super().closeEvent(event)

else:

    class CwsViewerV15T8CockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15T8CockpitWindow",
    "V15_T8_VERSION",
    "V15_T8_WORKSPACE_SCHEMA",
    "V15_T8_WORKSPACE_STATE_VERSION",
    "t8_manufacturing_contract",
    "t8_workspace_contract",
]
