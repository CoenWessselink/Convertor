from __future__ import annotations

from typing import Any

from .tokens import DARK_COLORS, LIGHT_COLORS


def _stylesheet(colors: dict[str, str], *, dark: bool) -> str:
    c = colors
    tooltip_bg = "#142331" if dark else "#263C50"
    danger_hover = "#7D3030" if dark else "#FDE8E7"
    return f"""
QWidget {{ background: {c['canvas']}; color: {c['text']}; font-family: 'Bahnschrift', 'Segoe UI Variable', 'Segoe UI'; font-size: 9pt; }}
QMainWindow, QDialog, QDockWidget {{ background: {c['canvas']}; }}
QFrame[cwsSurface='true'], QGroupBox {{ background: {c['surface']}; }}
QLabel {{ background: transparent; }}
QMenuBar, QMenu {{ background: {c['surface']}; border: 1px solid {c['border']}; spacing: 2px; }}
QMenu::item {{ padding: 6px 24px 6px 10px; }}
QMenu::item:selected {{ background: {c['ui_selection']}; }}
QPushButton, QToolButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{ min-height: 28px; padding: 2px 8px; background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 3px; }}
QPushButton:hover, QToolButton:hover {{ background: {c['surface_alt']}; border-color: {c['primary']}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {c['ui_selection']}; }}
QPushButton:checked, QToolButton:checked {{ background: {c['primary_pressed']}; color: white; border-color: {c['primary']}; }}
QPushButton[cwsRole='primary'], QPushButton#primaryButton {{ min-height: 31px; background: {c['primary']}; color: white; border: 1px solid {c['primary']}; font-weight: 600; }}
QPushButton[cwsRole='primary']:hover, QPushButton#primaryButton:hover {{ background: {c['primary_hover']}; }}
QCheckBox, QRadioButton {{ spacing: 7px; background: transparent; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 15px; height: 15px; }}
QSlider::groove:horizontal {{ height: 4px; background: {c['border']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 14px; margin: -5px 0; background: {c['primary']}; border: 1px solid {c['primary_hover']}; border-radius: 7px; }}
QAbstractItemView {{ background: {c['surface']}; alternate-background-color: {c['surface_alt']}; border: 1px solid {c['border']}; selection-background-color: {c['ui_selection']}; selection-color: {c['text']}; outline: 0; }}
QHeaderView::section {{ min-height: 26px; background: {c['surface_alt']}; border: 0; border-right: 1px solid {c['border']}; border-bottom: 1px solid {c['border']}; padding: 3px 6px; color: {c['text_muted']}; font-weight: 600; }}
QTreeView, QTableView, QListView, QTreeWidget, QTableWidget {{ gridline-color: {c['border']}; }}
QPlainTextEdit, QTextEdit {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 2px; padding: 5px; }}
QTabWidget::pane {{ border: 0; border-top: 1px solid {c['border']}; background: {c['surface']}; }}
QTabBar::tab {{ min-height: 27px; background: {c['surface']}; padding: 3px 12px; border: 0; border-bottom: 2px solid transparent; }}
QTabBar::tab:hover {{ background: {c['surface_alt']}; }}
QTabBar::tab:selected {{ color: {c['primary']}; background: {c['surface']}; border-bottom-color: {c['primary']}; font-weight: 700; }}
QTabBar#cwsPrimaryNavigationBar {{ background: {c['nav_background']}; }}
QTabBar#cwsPrimaryNavigationBar::tab {{ min-width: 98px; min-height: 34px; padding: 2px 16px; background: {c['nav_background']}; color: #DDE8F0; font-weight: 600; }}
QTabBar#cwsPrimaryNavigationBar::tab:hover {{ color: #FFFFFF; background: #31516B; }}
QTabBar#cwsPrimaryNavigationBar::tab:selected {{ color: #FFFFFF; background: {c['nav_active']}; border-bottom: 3px solid #55B6E9; }}
QGroupBox {{ border: 1px solid {c['border']}; margin-top: 9px; padding-top: 8px; }}
QGroupBox::title {{ color: {c['text_muted']}; subcontrol-origin: margin; left: 8px; padding: 0 4px; }}
QScrollBar:vertical {{ background: {c['canvas']}; width: 12px; }}
QScrollBar::handle:vertical {{ background: {c['border_strong']}; min-height: 28px; border-radius: 3px; }}
QScrollBar:horizontal {{ background: {c['canvas']}; height: 12px; }}
QScrollBar::handle:horizontal {{ background: {c['border_strong']}; min-width: 28px; border-radius: 3px; }}
QStatusBar {{ background: {c['surface']}; color: {c['text_muted']}; border-top: 1px solid {c['border']}; }}
QToolTip {{ background: {tooltip_bg}; color: white; border: 1px solid {c['border_strong']}; padding: 4px; }}
QFrame#cwsProductHeader {{ background: {c['nav_background']}; border: 0; border-right: 1px solid {c['border']}; }}
QFrame#cwsProductHeader QLabel#productName {{ color: #FFFFFF; font-size: 12pt; font-weight: 700; padding: 0 4px; }}
QFrame#cwsProductHeader QLabel#versionBadge {{ color: #D9EEFB; background: {c['nav_active']}; border: 1px solid #5D88A8; border-radius: 3px; padding: 3px 6px; }}
QFrame#cwsProductHeader QToolButton {{ min-width: 27px; max-width: 27px; min-height: 27px; max-height: 27px; padding: 0; color: white; background: transparent; }}
QToolBar#cwsV51GlobalNav, QToolBar#cwsV51GlobalBar {{ min-height: 36px; max-height: 38px; background: {c['nav_background']}; border: 0; spacing: 2px; padding: 0 5px; }}
QToolBar#cwsV51GlobalNav QComboBox, QToolBar#cwsV51GlobalBar QComboBox {{ min-height: 27px; max-height: 27px; min-width: 170px; }}
QToolBar#cwsV51GlobalNav QToolButton, QToolBar#cwsV51GlobalBar QToolButton {{ min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; padding: 0; color: white; background: transparent; }}
QToolBar#cwsV51ScreenActions {{ min-height: 41px; max-height: 41px; background: {c['surface']}; border: 0; border-bottom: 1px solid {c['border']}; padding: 0 8px; }}
QLabel#cwsScreenNumber {{ color: #FFFFFF; background: {c['primary']}; border: 1px solid {c['primary_hover']}; border-radius: 3px; font-weight: 700; font-size: 10pt; }}
QLabel#cwsWorkspaceTitle {{ color: {c['text']}; font-weight: 700; font-size: 11pt; letter-spacing: 0.5px; padding-left: 8px; }}
QLabel#cwsWorkspaceContext {{ color: {c['text_muted']}; padding-right: 6px; }}
QToolButton#cwsWorkspaceClose {{ min-width: 27px; max-width: 27px; min-height: 27px; max-height: 27px; color: {c['text_muted']}; background: transparent; border: 1px solid transparent; padding: 0; }}
QToolButton#cwsWorkspaceClose:hover {{ color: {c['error']}; background: {danger_hover}; border-color: {c['error']}; }}
QFrame#cwsContextRibbon {{ background: {c['surface']}; border: 0; border-bottom: 1px solid {c['border']}; }}
QFrame#ribbonGroup {{ background: transparent; border: 0; border-right: 1px solid {c['border']}; }}
QToolButton#ribbonButton {{ background: transparent; border: 1px solid transparent; border-radius: 3px; padding: 0; }}
QToolButton#ribbonButton:hover {{ background: {c['surface_alt']}; border-color: {c['primary']}; }}
QFrame#cwsQuickWorkspaceBar {{ min-height: 35px; max-height: 35px; background: {c['surface']}; border-top: 1px solid {c['border']}; }}
QFrame#cwsQuickWorkspaceBar QLabel#mutedText {{ color: {c['text_muted']}; font-size: 8pt; font-weight: 700; padding: 0 8px 0 2px; }}
QFrame#cwsQuickWorkspaceBar QToolButton {{ min-height: 27px; max-height: 27px; padding: 0 10px; background: {c['surface_alt']}; }}
QFrame#productWorkspaceHeader {{ min-height: 0; max-height: 0; margin: 0; padding: 0; border: 0; background: transparent; }}
QLabel#workspaceTitle, QFrame#productWorkspaceHeader QLabel {{ max-height: 0; color: transparent; }}
QLabel#contextChip {{ color: {c['primary']}; background: {c['surface_alt']}; border: 1px solid {c['border']}; border-radius: 3px; padding: 3px 8px; }}
QLabel#summaryCard {{ min-height: 72px; background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 3px; padding: 10px; font-size: 10pt; }}
QLabel#safetyStatus {{ min-height: 25px; color: {c['warning']}; background: {c['surface_alt']}; border: 1px solid {c['border']}; padding: 3px 8px; }}
QLabel#selectionContext {{ color: {c['primary']}; padding: 4px 8px; }}
QDockWidget::title {{ background: {c['surface_alt']}; border-bottom: 1px solid {c['border']}; padding: 6px; font-weight: 700; }}
QSplitter::handle {{ background: {c['border']}; }}
*:disabled {{ color: {c['disabled']}; }}
"""


V52_LIGHT_QSS = _stylesheet(LIGHT_COLORS, dark=False)
V52_DARK_QSS = _stylesheet(DARK_COLORS, dark=True)


def apply_v52_design_system(application: Any, theme: str = "Default Light") -> str:
    selected = "Engineering Dark" if str(theme).casefold() == "engineering dark" else "Default Light"
    application.setStyleSheet(V52_DARK_QSS if selected == "Engineering Dark" else V52_LIGHT_QSS)
    application.setProperty("cws_ui_master", "V5.2")
    application.setProperty("cws_theme", selected)
    return selected
