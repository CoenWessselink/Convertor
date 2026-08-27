"""Compatibility facade for the single concrete CWS product shell.

U4 used to subclass U3 and patch viewer placement at import time. All active
composition now lives in one :class:`CWSMainWindow`; this module only preserves
stable public import names for packages and third-party launchers.
"""
from .main_window import (
    CWSMainWindow,
    CwsConvertorMainWindow,
    WorkspaceRouter,
    run_qt_application,
)
from .product_workspaces import ProductionWorkflowPanel


U4_WORKFLOW_PROPERTY = "cwsUnifiedProductionWorkflow"
U4_WORKFLOW_TOKEN = "CWS-SINGLE-PRODUCT-SHELL-2"


__all__ = [
    "CWSMainWindow",
    "CwsConvertorMainWindow",
    "ProductionWorkflowPanel",
    "U4_WORKFLOW_PROPERTY",
    "U4_WORKFLOW_TOKEN",
    "WorkspaceRouter",
    "run_qt_application",
]
