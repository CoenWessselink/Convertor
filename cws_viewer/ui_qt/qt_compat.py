"""Lazy PySide6 compatibility helpers.

The V1 source must remain importable in offline/headless environments where
PySide6 is not installed. Production Qt classes are only constructed when the
optional dependency is actually available.
"""
from __future__ import annotations

import importlib.util
from typing import Any

from cws_viewer.errors import ViewerError, ViewerErrorCode


def qt_available() -> bool:
    return importlib.util.find_spec("PySide6") is not None


def require_qt() -> tuple[Any, Any, Any]:
    try:
        from PySide6 import QtCore, QtGui, QtWidgets

        return QtCore, QtGui, QtWidgets
    except Exception as exc:
        raise ViewerError(
            "PySide6/Qt is niet beschikbaar voor de CWS Viewer-harness",
            code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            context={"dependency": "PySide6", "error": str(exc)},
        ) from exc


__all__ = ["qt_available", "require_qt"]
