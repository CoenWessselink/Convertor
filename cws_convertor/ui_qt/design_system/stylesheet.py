from __future__ import annotations

from typing import Any

from .tokens import TOKENS


_C = TOKENS["colors"]
V52_DARK_QSS = f"""
QWidget {{
    background: {_C['canvas']}; color: {_C['text']};
    font-family: 'Segoe UI Variable', 'Segoe UI'; font-size: 9pt;
}}
QMainWindow, QDialog, QFrame[cwsSurface='true'], QDockWidget {{ background: {_C['surface']}; }}
QToolBar, QTabBar, QMenuBar, QMenu {{
    background: {_C['surface']}; border-bottom: 1px solid {_C['border']}; spacing: 2px;
}}
QPushButton, QToolButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    min-height: 28px; padding: 2px 8px; background: {_C['surface']};
    border: 1px solid {_C['border']}; border-radius: 3px;
}}
QPushButton:hover, QToolButton:hover {{ background: {_C['surface_alt']}; border-color: {_C['primary']}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {_C['ui_selection']}; }}
QPushButton:checked, QToolButton:checked {{ background: {_C['primary_pressed']}; color: white; border-color: {_C['primary']}; }}
QPushButton[cwsRole='primary'] {{ background: {_C['primary']}; color: white; border-color: {_C['primary']}; }}
QPushButton[cwsRole='primary']:hover {{ background: {_C['primary_hover']}; }}
QAbstractItemView {{
    background: {_C['surface']}; alternate-background-color: {_C['surface_alt']};
    border: 1px solid {_C['border']}; selection-background-color: {_C['ui_selection']};
    selection-color: {_C['text']}; outline: 0;
}}
QHeaderView::section {{ background: {_C['surface_alt']}; border: 0; border-right: 1px solid {_C['border']}; padding: 5px; }}
QTreeView, QTableView, QListView, QTreeWidget, QTableWidget, QListWidget {{ gridline-color: {_C['border']}; }}
QTabBar::tab {{ background: {_C['surface']}; padding: 7px 12px; border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: #FFFFFF; background: {_C['primary_pressed']}; border-bottom-color: {_C['primary']}; }}
QGroupBox {{ border: 1px solid {_C['border']}; margin-top: 9px; padding-top: 8px; }}
QGroupBox::title {{ color: {_C['text_muted']}; subcontrol-origin: margin; left: 8px; padding: 0 4px; }}
QScrollBar:vertical {{ background: {_C['canvas']}; width: 12px; }}
QScrollBar::handle:vertical {{ background: {_C['border_strong']}; min-height: 28px; border-radius: 3px; }}
QScrollBar:horizontal {{ background: {_C['canvas']}; height: 12px; }}
QScrollBar::handle:horizontal {{ background: {_C['border_strong']}; min-width: 28px; border-radius: 3px; }}
QStatusBar {{ background: #0B1218; color: {_C['text_muted']}; border-top: 1px solid {_C['border']}; }}
QToolTip {{ background: #071018; color: white; border: 1px solid {_C['border_strong']}; padding: 4px; }}
*:disabled {{ color: {_C['disabled']}; }}
"""

# Compatibility name for callers that still import the old constant.  The
# V5.2 visual source of truth is now the engineering-dark theme.
V52_LIGHT_QSS = V52_DARK_QSS


def apply_v52_design_system(application: Any) -> None:
    application.setStyleSheet(V52_DARK_QSS)
    application.setProperty("cws_ui_master", "V5.2")
    application.setProperty("cws_theme", "Engineering Dark")
