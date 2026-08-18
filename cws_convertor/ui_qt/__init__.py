"""Integrated PySide6 desktop shell for CWS Convertor.

U4 layers the production-workflow surface on top of the U3 central application
context. The historical V9 IntegratedProjectPage remains the same widget and the
package stays import-safe when PySide6 is absent.
"""
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
    "ProductionWorkflowPanel",
    "U3_CONTEXT_PROPERTY",
    "U3_CONTEXT_TOKEN",
    "U4_WORKFLOW_PROPERTY",
    "U4_WORKFLOW_TOKEN",
    "run_qt_application",
]
