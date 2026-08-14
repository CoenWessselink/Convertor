"""Optional PySide6/Qt host layer for CWS Viewer."""
from __future__ import annotations

from typing import Any

from .qt_compat import qt_available, require_qt

__all__ = [
    "qt_available",
    "require_qt",
    "OcctAisWidget",
    "VtkMeshWidget",
    "VtkProjectWidget",
    "VtkRealProjectWidget",
    "ViewerMainWindow",
    "RealProjectViewerWindow",
    "create_viewer_window",
    "run_viewer_shell",
    "run_real_project_viewer",
    "create_harness_window",
    "run_harness",
]


def __getattr__(name: str) -> Any:
    if name == "OcctAisWidget":
        from .occt_widget import OcctAisWidget
        return OcctAisWidget
    if name == "VtkMeshWidget":
        from .vtk_widget import VtkMeshWidget
        return VtkMeshWidget
    if name == "VtkProjectWidget":
        from .vtk_project_widget import VtkProjectWidget
        return VtkProjectWidget
    if name == "VtkRealProjectWidget":
        from .vtk_real_project_widget import VtkRealProjectWidget
        return VtkRealProjectWidget
    if name in {"ViewerMainWindow", "create_viewer_window", "run_viewer_shell"}:
        from .viewer_shell import ViewerMainWindow, create_viewer_window, run_viewer_shell
        return {"ViewerMainWindow": ViewerMainWindow, "create_viewer_window": create_viewer_window, "run_viewer_shell": run_viewer_shell}[name]
    if name in {"RealProjectViewerWindow", "run_real_project_viewer"}:
        from .project_viewer import RealProjectViewerWindow, run_real_project_viewer
        return {"RealProjectViewerWindow": RealProjectViewerWindow, "run_real_project_viewer": run_real_project_viewer}[name]
    if name in {"create_harness_window", "run_harness"}:
        from .technology_harness import create_harness_window, run_harness
        return {"create_harness_window": create_harness_window, "run_harness": run_harness}[name]
    raise AttributeError(name)

from .exact_part_workbench import ExactOcctWidget, ExactPartWorkbenchPanel
