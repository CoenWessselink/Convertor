"""Single composed PySide6 product shell for CWS Convertor."""

INTEGRATED_VIEWER_HOST = "VtkRealProjectWidgetFeelV2"

from .main_window import (
    CWSMainWindow,
    CwsConvertorMainWindow,
    IntegratedProjectPage,
    WorkspaceRouter,
    run_qt_application,
)
from .unified_shell import U3_CONTEXT_PROPERTY, U3_CONTEXT_TOKEN
from .product_workspaces import ProductionWorkflowPanel
from .u4_shell import U4_WORKFLOW_PROPERTY, U4_WORKFLOW_TOKEN

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
    "WorkspaceRouter",
    "run_qt_application",
]
