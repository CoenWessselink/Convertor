from __future__ import annotations

from typing import Any

from .tokens import TOKENS


_C = TOKENS["colors"]
V52_DARK_QSS = f"""
QWidget {{
    background: {_C['canvas']}; color: {_C['text']};
    font-family: 'Bahnschrift', 'Segoe UI'; font-size: 9pt;
}}
QMainWindow, QDialog, QDockWidget {{ background: {_C['canvas']}; }}
QFrame[cwsSurface='true'], QGroupBox {{ background: {_C['surface']}; }}
QLabel {{ background: transparent; }}
QMenuBar, QMenu {{ background: #0B141C; border: 1px solid {_C['border']}; spacing: 2px; }}
QMenu::item {{ padding: 6px 24px 6px 10px; }}
QMenu::item:selected {{ background: {_C['ui_selection']}; }}
QPushButton, QToolButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    min-height: 28px; padding: 2px 8px; background: {_C['surface']};
    border: 1px solid {_C['border']}; border-radius: 3px;
}}
QPushButton:hover, QToolButton:hover {{ background: {_C['surface_alt']}; border-color: {_C['primary']}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {_C['ui_selection']}; }}
QPushButton:checked, QToolButton:checked {{ background: {_C['primary_pressed']}; color: white; border-color: {_C['primary']}; }}
QPushButton[cwsRole='primary'] {{ background: {_C['primary']}; color: white; border-color: {_C['primary']}; }}
QPushButton[cwsRole='primary']:hover {{ background: {_C['primary_hover']}; }}
QPushButton#primaryButton {{
    min-height: 31px; background: #176FB8; color: #FFFFFF;
    border: 1px solid #2A8BD4; font-weight: 600;
}}
QPushButton#primaryButton:hover {{ background: #2087D4; border-color: #56B6F2; }}
QCheckBox, QRadioButton {{ spacing: 7px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QSlider::groove:horizontal {{ height: 4px; background: #304553; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 14px; margin: -5px 0; background: #39A9EA;
    border: 1px solid #8AD4FC; border-radius: 7px;
}}
QAbstractItemView {{
    background: {_C['surface']}; alternate-background-color: {_C['surface_alt']};
    border: 1px solid {_C['border']}; selection-background-color: {_C['ui_selection']};
    selection-color: {_C['text']}; outline: 0;
}}
QHeaderView::section {{
    min-height: 26px; background: {_C['surface_alt']}; border: 0;
    border-right: 1px solid {_C['border']}; border-bottom: 1px solid {_C['border']};
    padding: 3px 6px; color: {_C['text_muted']};
}}
QTreeView, QTableView, QListView, QTreeWidget, QTableWidget, QListWidget {{ gridline-color: {_C['border']}; }}
QPlainTextEdit, QTextEdit {{
    background: {_C['surface']}; color: {_C['text']};
    border: 1px solid {_C['border']}; border-radius: 2px; padding: 5px;
}}
QTabWidget::pane {{ border: 0; border-top: 1px solid {_C['border']}; }}
QTabBar::tab {{
    min-height: 27px; background: {_C['surface']}; padding: 3px 12px;
    border: 0; border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{ color: #FFFFFF; background: {_C['surface_alt']}; }}
QTabBar::tab:selected {{ color: #FFFFFF; background: {_C['primary_pressed']}; border-bottom-color: #2BA7EA; }}
QTabBar#cwsPrimaryNavigationBar {{ background: #09131B; }}
QTabBar#cwsPrimaryNavigationBar::tab {{
    min-width: 98px; min-height: 34px; padding: 2px 16px;
    background: #09131B; color: #9FB3C1; font-weight: 600;
}}
QTabBar#cwsPrimaryNavigationBar::tab:selected {{
    color: #FFFFFF; background: #102635; border-bottom: 3px solid #22A8F0;
}}
QGroupBox {{ border: 1px solid {_C['border']}; margin-top: 9px; padding-top: 8px; }}
QGroupBox::title {{ color: {_C['text_muted']}; subcontrol-origin: margin; left: 8px; padding: 0 4px; }}
QScrollBar:vertical {{ background: {_C['canvas']}; width: 12px; }}
QScrollBar::handle:vertical {{ background: {_C['border_strong']}; min-height: 28px; border-radius: 3px; }}
QScrollBar:horizontal {{ background: {_C['canvas']}; height: 12px; }}
QScrollBar::handle:horizontal {{ background: {_C['border_strong']}; min-width: 28px; border-radius: 3px; }}
QStatusBar {{ background: #0B1218; color: {_C['text_muted']}; border-top: 1px solid {_C['border']}; }}
QToolTip {{ background: #071018; color: white; border: 1px solid {_C['border_strong']}; padding: 4px; }}
QFrame#cwsProductHeader {{ background: #09131B; border: 0; border-right: 1px solid {_C['border']}; }}
QFrame#cwsProductHeader QLabel#productName {{ color: #F4F9FC; font-size: 12pt; font-weight: 700; padding: 0 4px; }}
QFrame#cwsProductHeader QLabel#versionBadge {{
    color: #77C8F6; background: #102B3C; border: 1px solid #245675;
    border-radius: 3px; padding: 3px 6px;
}}
QFrame#cwsProductHeader QToolButton {{
    min-width: 27px; max-width: 27px; min-height: 27px; max-height: 27px; padding: 0;
}}
QToolBar#cwsV51GlobalNav {{
    min-height: 36px; max-height: 36px; background: #09131B;
    border: 0; border-left: 1px solid {_C['border']}; spacing: 2px; padding: 0 5px;
}}
QToolBar#cwsV51GlobalNav QComboBox {{ min-height: 27px; max-height: 27px; min-width: 170px; }}
QToolBar#cwsV51GlobalNav QToolButton {{
    min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; padding: 0;
}}
QToolBar#cwsV51ScreenActions {{
    min-height: 41px; max-height: 41px; background: #08131C;
    border: 0; border-bottom: 1px solid #294657; padding: 0 8px;
}}
QLabel#cwsScreenNumber {{
    color: #FFFFFF; background: #0D71B9; border: 1px solid #238FD4;
    border-radius: 3px; font-weight: 700; font-size: 10pt;
}}
QLabel#cwsWorkspaceTitle {{
    color: #F2F7FA; font-weight: 700; font-size: 11pt;
    letter-spacing: 0.5px; padding-left: 8px;
}}
QLabel#cwsWorkspaceContext {{ color: {_C['text_muted']}; padding-right: 6px; }}
QToolButton#cwsWorkspaceClose {{
    min-width: 27px; max-width: 27px; min-height: 27px; max-height: 27px;
    color: #C7D5DE; background: transparent; border: 1px solid transparent; padding: 0;
}}
QToolButton#cwsWorkspaceClose:hover {{ color: #FFFFFF; background: #7D3030; border-color: #B94C4C; }}
QFrame#cwsContextRibbon {{ background: #101D27; border: 0; border-bottom: 1px solid {_C['border']}; }}
QFrame#ribbonGroup {{ background: transparent; border: 0; border-right: 1px solid {_C['border']}; }}
QToolButton#ribbonButton {{ background: transparent; border: 1px solid transparent; border-radius: 3px; padding: 0; }}
QToolButton#ribbonButton:hover {{ background: #18384B; border-color: #2A6689; }}
QFrame#cwsQuickWorkspaceBar {{
    min-height: 35px; max-height: 35px; background: #0B141C;
    border-top: 1px solid {_C['border']};
}}
QFrame#cwsQuickWorkspaceBar QLabel#mutedText {{
    color: #708897; font-size: 8pt; font-weight: 700; padding: 0 8px 0 2px;
}}
QFrame#cwsQuickWorkspaceBar QToolButton {{
    min-height: 27px; max-height: 27px; padding: 0 10px; background: #111F29;
}}
QFrame#productWorkspaceHeader {{
    min-height: 0; max-height: 0; margin: 0; padding: 0;
    border: 0; background: transparent;
}}
QLabel#workspaceTitle, QFrame#productWorkspaceHeader QLabel {{ max-height: 0; color: transparent; }}
QLabel#contextChip {{
    color: #8CCDF3; background: #102A3B; border: 1px solid #28546D;
    border-radius: 3px; padding: 3px 8px;
}}
QLabel#summaryCard {{
    min-height: 72px; background: #14242F; border: 1px solid #2A4556;
    border-radius: 3px; padding: 10px; font-size: 10pt;
}}
QLabel#safetyStatus {{
    min-height: 25px; color: #E8BE69; background: #2A2518;
    border: 1px solid #66552B; padding: 3px 8px;
}}
QLabel#selectionContext {{ color: #89CFF4; padding: 4px 8px; }}
QDockWidget::title {{
    background: #101D27; border-bottom: 1px solid {_C['border']};
    padding: 6px; font-weight: 700;
}}
QSplitter::handle {{ background: {_C['border']}; }}
*:disabled {{ color: {_C['disabled']}; }}
"""

# Compatibility name for callers that still import the old constant.
V52_LIGHT_QSS = V52_DARK_QSS


def apply_v52_design_system(application: Any) -> None:
    application.setStyleSheet(V52_DARK_QSS)
    application.setProperty("cws_ui_master", "V5.2")
    application.setProperty("cws_theme", "Engineering Dark")
