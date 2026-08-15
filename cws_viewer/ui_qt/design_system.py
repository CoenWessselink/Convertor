"""CWS Viewer light industrial design system.

The visual system follows the user supplied CWS target layout: bright desktop
surface, strong CWS blue accent, compact engineering tables and a central 3D
cockpit. It is original CWS styling; no Trimble resources are embedded.
"""
from __future__ import annotations

from dataclasses import dataclass

CWS_BLUE = "#0b5bd3"
CWS_BLUE_DARK = "#0647a5"
CWS_BLUE_SOFT = "#eaf2ff"
CWS_BORDER = "#d8e1eb"
CWS_TEXT = "#172235"
CWS_MUTED = "#69798a"
CWS_PANEL = "#ffffff"
CWS_BG = "#f4f7fb"
CWS_OK = "#1f9d61"
CWS_WARN = "#d99614"
CWS_FAIL = "#d64545"


LIGHT_QSS = f"""
QMainWindow, QWidget#cwsCockpitRoot {{
    background: {CWS_BG};
    color: {CWS_TEXT};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}}
QFrame#cwsHeader, QFrame#cwsRibbon, QFrame#cwsPanel, QFrame#cwsViewerCard,
QFrame#cwsStatusStrip, QFrame#cwsModuleOverview {{
    background: {CWS_PANEL};
    border: 1px solid {CWS_BORDER};
    border-radius: 7px;
}}
QLabel#cwsProductTitle {{ color: {CWS_BLUE_DARK}; font-size: 22pt; font-weight: 700; }}
QLabel#cwsVersion {{ color: #2c3440; font-size: 10pt; }}
QLabel#cwsSubtitle {{ color: {CWS_BLUE_DARK}; font-size: 11pt; font-weight: 600; }}
QLabel#cwsPanelTitle {{ color: {CWS_TEXT}; font-weight: 700; }}
QLabel#cwsSectionTitle {{ color: {CWS_BLUE_DARK}; font-weight: 700; }}
QLabel#cwsMuted {{ color: {CWS_MUTED}; }}
QLabel#cwsStatusOk {{ color: {CWS_OK}; font-weight: 600; }}
QLabel#cwsStatusWarning {{ color: {CWS_WARN}; font-weight: 600; }}
QLabel#cwsStatusFail {{ color: {CWS_FAIL}; font-weight: 600; }}
QPushButton, QToolButton {{
    background: #ffffff;
    color: {CWS_TEXT};
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 5px 8px;
}}
QPushButton:hover, QToolButton:hover {{ background: {CWS_BLUE_SOFT}; border-color: #bfd3f4; }}
QPushButton:checked, QToolButton:checked {{ background: {CWS_BLUE}; color: white; border-color: {CWS_BLUE}; }}
QPushButton#cwsPrimaryButton {{ background: {CWS_BLUE}; color: white; border: 1px solid {CWS_BLUE}; font-weight: 600; }}
QPushButton#cwsPrimaryButton:hover {{ background: {CWS_BLUE_DARK}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background: #ffffff;
    color: {CWS_TEXT};
    border: 1px solid #cdd8e4;
    border-radius: 4px;
    min-height: 24px;
    padding: 2px 6px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {CWS_BLUE}; }}
QTreeWidget, QTableWidget, QTableView, QPlainTextEdit, QListWidget {{
    background: #ffffff;
    alternate-background-color: #f8fafc;
    color: {CWS_TEXT};
    border: 1px solid #dbe4ed;
    gridline-color: #e6ecf2;
    selection-background-color: #dbeaff;
    selection-color: #0f2f62;
}}
QHeaderView::section {{
    background: #f4f7fb;
    color: #34485f;
    border: none;
    border-right: 1px solid #e1e7ed;
    border-bottom: 1px solid #d7e0e8;
    padding: 6px;
    font-weight: 600;
}}
QTreeWidget::item, QListWidget::item {{ min-height: 24px; }}
QTreeWidget::item:selected, QTableView::item:selected, QTableWidget::item:selected, QListWidget::item:selected {{
    background: #dbeaff;
    color: #0c3c85;
}}
QTabWidget::pane {{ background: #ffffff; border: 1px solid {CWS_BORDER}; top: -1px; }}
QTabBar::tab {{ background: #f6f8fb; color: #506276; border: 1px solid {CWS_BORDER}; padding: 6px 11px; }}
QTabBar::tab:selected {{ background: #ffffff; color: {CWS_BLUE_DARK}; border-bottom-color: #ffffff; font-weight: 600; }}
QProgressBar {{ border: none; background: #e6ebf1; border-radius: 4px; height: 8px; text-align: right; color: #445; }}
QProgressBar::chunk {{ background: {CWS_BLUE}; border-radius: 4px; }}
QSplitter::handle {{ background: transparent; width: 4px; height: 4px; }}
QMenu {{ background: white; color: {CWS_TEXT}; border: 1px solid #cbd6e1; padding: 4px; }}
QMenu::item {{ padding: 6px 24px 6px 8px; border-radius: 3px; }}
QMenu::item:selected {{ background: {CWS_BLUE_SOFT}; color: {CWS_BLUE_DARK}; }}
QStatusBar {{ background: #ffffff; color: #44576c; border-top: 1px solid {CWS_BORDER}; }}
QScrollBar:vertical {{ background: #f3f6f9; width: 10px; }}
QScrollBar::handle:vertical {{ background: #c5d0db; min-height: 24px; border-radius: 5px; }}
"""


@dataclass(frozen=True, slots=True)
class RibbonModule:
    key: str
    title: str
    line1: str
    line2: str = ""
    icon_text: str = ""


RIBBON_MODULES: tuple[RibbonModule, ...] = (
    RibbonModule("open", "Inlezen", "Bestanden importeren", "Project openen", "▣"),
    RibbonModule("viewer", "Viewer (Project)", "Model bekijken", "Meten, analyseren", "◇"),
    RibbonModule("edit", "Bewerken", "Objecten bewerken", "Productie aanpassen", "✎"),
    RibbonModule("convert", "Converteren", "Naar viewerformaat", "Converteren", "↔"),
    RibbonModule("check", "Controleren", "Validatie, verificatie", "Rapportage", "✓"),
    RibbonModule("pdf", "PDF / Tekening", "Documenten", "Tekenen & afdruk", "◫"),
    RibbonModule("drawings", "Tekeningen", "Productietekeningen", "Genereren", "▤"),
    RibbonModule("scribing", "Scribing", "Contacten & scribing", "Genereren", "⌁"),
    RibbonModule("excel", "Hoeveelheden / Excel", "Overzichten", "Exporteren", "▦"),
    RibbonModule("export", "Exporteren", "Bestanden exporteren", "NC / DSTV", "⇥"),
)


__all__ = [
    "CWS_BLUE", "CWS_BLUE_DARK", "CWS_BLUE_SOFT", "CWS_BORDER", "CWS_TEXT",
    "CWS_MUTED", "CWS_PANEL", "CWS_BG", "CWS_OK", "CWS_WARN", "CWS_FAIL",
    "LIGHT_QSS", "RibbonModule", "RIBBON_MODULES",
]
