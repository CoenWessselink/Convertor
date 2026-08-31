"""Regression gate for reported viewer geometry and interaction defects."""

from __future__ import annotations

import inspect
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.vtk_project_mesh_feel_v2 import VtkProjectMeshFeelV2Backend
from cws_viewer.geometry.ifc_provider import IfcMeshProvider, PROVIDER_VERSION
from cws_viewer.ui_qt.trimble_navigation_overlay import TrimbleNavigationOverlay
from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2


def main() -> int:
    backend_source = inspect.getsource(VtkProjectMeshFeelV2Backend.set_realistic_rendering)
    overlay_source = inspect.getsource(TrimbleNavigationOverlay)
    provider_source = inspect.getsource(IfcMeshProvider.load)

    checks = {
        "no_triangle_cell_edges": "EdgeVisibilityOn" not in backend_source,
        "global_model_opacity": hasattr(VtkProjectMeshFeelV2Backend, "set_global_opacity"),
        "ifcopenshell_primary": "ifcopenshell.geom.create_shape" in provider_source,
        "profile_radii_quality": "circle_segments" in provider_source,
        "legacy_fallback_auditable": "legacy_fallback" in provider_source,
        "compact_pan_control": '"Slepen"' in overlay_source,
        "compact_orbit_control": '"Orbit"' in overlay_source,
        "compact_fit_control": '"Fit"' in overlay_source,
        "transparency_slider": "opacity_slider" in overlay_source,
        "mouse_orbit_pivot": "_bind_orbit_pivot_from_screen" in overlay_source,
        "explicit_selection_pick": 'getattr(self._viewer, "_pick"' in overlay_source,
        "selection_api_present": hasattr(VtkRealProjectWidgetFeelV2, "_pick"),
        "pivot_api_present": hasattr(VtkRealProjectWidgetFeelV2, "_bind_orbit_pivot_from_screen"),
        "provider_version_current": PROVIDER_VERSION == "cws-ifc-display-v6-balanced-tessellation",
    }
    failed = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print(f"VIEWER_VISUAL_GEOMETRY_REGRESSION = {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
