"""Compatibility exports for the single concrete product shell.

The active application shell lives in :mod:`cws_convertor.ui_qt.main_window`.
This module intentionally contains no subclass, reparenting or monkeypatch.
"""
from __future__ import annotations

from typing import Any

from cws_convertor.integration.ui_context import U3_SAFETY_FLAGS, UnifiedUiContextSnapshot
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from .main_window import CWSMainWindow, CwsConvertorMainWindow, run_qt_application


U3_CONTEXT_PROPERTY = "cwsApplicationContext"
U3_CONTEXT_TOKEN = "CWS-APPLICATION-CONTEXT-2"


if qt_available():
    _QtCore, _QtGui, QtWidgets = require_qt()

    class UnifiedContextStrip(QtWidgets.QFrame):
        """Small read-only projection of the authoritative ApplicationContext."""

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            layout = QtWidgets.QHBoxLayout(self)
            self.project = QtWidgets.QLabel("Geen project")
            self.selection = QtWidgets.QLabel("Geen selectie")
            self.workspace = QtWidgets.QLabel("Workspace: start")
            self.safety = QtWidgets.QLabel("machine-transfer: gesloten")
            layout.addWidget(self.project, 1)
            layout.addWidget(self.selection, 1)
            layout.addWidget(self.workspace)
            layout.addWidget(self.safety)

        def apply_snapshot(self, snapshot: UnifiedUiContextSnapshot) -> None:
            self.project.setText(snapshot.project_name or snapshot.project_id or "Geen project")
            self.selection.setText(snapshot.selection.primary_entity_id or "Geen selectie")
            self.workspace.setText(f"Workspace: {snapshot.workspace_context.active_workspace}")
            self.safety.setText(
                "machine-transfer: gesloten"
                if not any(U3_SAFETY_FLAGS.values())
                else "machine-transfer: BLOKKER OPEN"
            )
else:
    class UnifiedContextStrip:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "CWSMainWindow",
    "CwsConvertorMainWindow",
    "U3_CONTEXT_PROPERTY",
    "U3_CONTEXT_TOKEN",
    "UnifiedContextStrip",
    "run_qt_application",
]
