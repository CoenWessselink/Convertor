"""Integrated PySide6 desktop shell for CWS Convertor.

U3 makes the Viewer V15 based unified shell the default desktop entry point;
U4 adds the production workflow surface on top of the same application context.
The package stays import-safe when PySide6 is absent.
"""
from .main_window import IntegratedProjectPage
from .unified_shell import (
    CWSMainWindow,
    CwsConvertorMainWindow,
    U3_CONTEXT_PROPERTY,
    U3_CONTEXT_TOKEN,
    U4_WORKFLOW_PROPERTY,
    U4_WORKFLOW_TOKEN,
    run_qt_application,
)

__all__ = [
    "CWSMainWindow",
    "CwsConvertorMainWindow",
    "IntegratedProjectPage",
    "U3_CONTEXT_PROPERTY",
    "U3_CONTEXT_TOKEN",
    "U4_WORKFLOW_PROPERTY",
    "U4_WORKFLOW_TOKEN",
    "run_qt_application",
]
