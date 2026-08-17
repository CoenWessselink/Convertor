"""CWS Viewer handling/rendering repair cockpit built on Phase 2."""
from __future__ import annotations

from typing import Any

from cws_viewer.core.viewer_feel_navigation import viewer_feel_navigation_contract
from cws_viewer.ui_qt import cockpit_phase2_v15 as _phase2
from cws_viewer.ui_qt.cockpit_phase2_v15 import (
    CwsViewerV15Phase2CockpitWindow,
    phase2_workspace_contract,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_real_project_widget_feel import VtkRealProjectWidgetFeel

FEEL_FIX_BUILD = "viewer-feel-fix-1"


def viewer_feel_workspace_contract() -> dict[str, Any]:
    contract = phase2_workspace_contract()
    caps = dict(contract.get("capabilities", {}))
    caps.update(viewer_feel_navigation_contract()["capabilities"])
    caps.update(
        {
            "tessellation_edges_suppressed": True,
            "hard_edge_normals": True,
            "selection_feature_edge_outline": True,
            "interactive_fxaa": True,
            "interactive_msaa_8x": True,
            "quality_light_background": True,
            "phase2_review_preserved": True,
            "phase1_fast_start_preserved": True,
        }
    )
    contract["capabilities"] = caps
    contract["feel_fix"] = {
        "build": FEEL_FIX_BUILD,
        "renderer": "VtkProjectMeshFeelBackend",
        "input_host": "VtkRealProjectWidgetFeel",
        "navigation": viewer_feel_navigation_contract(),
        "visual_policy": {
            "normal_shaded_triangle_edges": False,
            "selection_triangle_wireframe": False,
            "hard_edge_normals": True,
            "fxaa_when_available": True,
            "msaa_interactive_samples": 8,
        },
    }
    return contract


if qt_available():
    _QtCore, _QtGui, QtWidgets = require_qt()

    class CwsViewerV15FeelFixCockpitWindow(CwsViewerV15Phase2CockpitWindow):
        """Construct Phase 2 using the repaired renderer/input host."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            previous = _phase2.VtkRealProjectWidgetPhase2
            _phase2.VtkRealProjectWidgetPhase2 = VtkRealProjectWidgetFeel
            try:
                super().__init__(*args, **kwargs)
            finally:
                _phase2.VtkRealProjectWidgetPhase2 = previous

            if not isinstance(self.viewer, VtkRealProjectWidgetFeel):
                raise RuntimeError("Viewer handling repair host kon niet worden geactiveerd")
            self.setObjectName("cwsViewerV15FeelFixCockpitWindow")
            for label in self.findChildren(QtWidgets.QLabel):
                if label.objectName() == "cwsVersion":
                    label.setText("V15 · Quality Fix")
                    break
            self.statusBar().showMessage(
                "Quality Fix actief · cursorzoom · scherpe shaded weergave · soepele 60–100 Hz input-coalescing",
                7500,
            )

else:

    class CwsViewerV15FeelFixCockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CwsViewerV15FeelFixCockpitWindow",
    "FEEL_FIX_BUILD",
    "viewer_feel_workspace_contract",
]
