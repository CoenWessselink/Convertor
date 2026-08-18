"""Integrated PySide6 desktop shell for CWS Convertor.

U4 layers the production workflow on the U3 single-project context.  Before the
shell modules are imported, the embedded project workspace is bound to the same
V15 Trimble-feel V2 host used by the standalone viewer.  This removes the former
V9-versus-V15 runtime split without creating a second project or selection truth.
"""
from cws_viewer.ui_qt.qt_compat import qt_available

INTEGRATED_VIEWER_HOST = "headless-unavailable"

if qt_available():
    # ``project_workspace`` imports the public VtkRealProjectWidget symbol while
    # the package below is initialising. Bind that symbol to the production V15
    # host first, so every integrated workspace receives the same navigation,
    # renderer and review foundation as CWS Viewer standalone.
    from cws_viewer.ui_qt import vtk_real_project_widget as _real_widget_module
    from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import (
        VtkRealProjectWidgetFeelV2,
    )

    _real_widget_module.VtkRealProjectWidget = VtkRealProjectWidgetFeelV2
    INTEGRATED_VIEWER_HOST = "VtkRealProjectWidgetFeelV2"

from .main_window import IntegratedProjectPage
from .unified_shell import U3_CONTEXT_PROPERTY, U3_CONTEXT_TOKEN
from .u4_shell import (
    CWSMainWindow,
    CwsConvertorMainWindow,
    ProductionWorkflowPanel,
    U4_WORKFLOW_PROPERTY,
    U4_WORKFLOW_TOKEN,
    run_qt_application,
)

__all__ = [
    "CWSMainWindow",
    "CwsConvertorMainWindow",
    "IntegratedProjectPage",
    "INTEGRATED_VIEWER_HOST",
    "ProductionWorkflowPanel",
    "U3_CONTEXT_PROPERTY",
    "U3_CONTEXT_TOKEN",
    "U4_WORKFLOW_PROPERTY",
    "U4_WORKFLOW_TOKEN",
    "run_qt_application",
]
