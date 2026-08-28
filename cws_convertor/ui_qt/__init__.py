"""Single composed PySide6 product shell for CWS Convertor."""

INTEGRATED_VIEWER_HOST = "VtkRealProjectWidgetFeelV2"

from .main_window import (
    IntegratedProjectPage,
    WorkspaceRouter,
)
from .unified_shell import U3_CONTEXT_PROPERTY, U3_CONTEXT_TOKEN
from .product_workspaces import ProductionWorkflowPanel
from .u4_shell import (
    CWSMainWindow,
    CwsConvertorMainWindow,
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
    "WorkspaceRouter",
    "run_qt_application",
]
