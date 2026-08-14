"""Integrated PySide6 desktop shell for CWS Convertor V9.

The package is import-safe when PySide6 is absent; construction of a widget
requires :func:`cws_viewer.ui_qt.qt_compat.require_qt` to succeed.
"""
from .main_window import (
    CWSMainWindow,
    CwsConvertorMainWindow,
    IntegratedProjectPage,
    run_qt_application,
)

__all__ = [
    "CWSMainWindow",
    "CwsConvertorMainWindow",
    "IntegratedProjectPage",
    "run_qt_application",
]
