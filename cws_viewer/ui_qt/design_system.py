"""CWS Viewer application-wide engineering design system.

The default visual language is deliberately light and neutral, following the
same ergonomic principles visible in professional BIM/CAD desktop viewers:
white work surfaces, restrained grey chrome, high contrast text and one blue
interaction accent.  It is an original CWS theme; no third-party resources,
icons, style sheets or binaries are embedded.

All colours live in :class:`ThemePalette`.  Viewer, start centre and the future
CWS Convertor shell can therefore share one persisted theme instead of growing
per-window hard-coded QSS fragments.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ThemePalette:
    key: str
    title: str
    app_bg: str
    panel: str
    panel_alt: str
    toolbar: str
    border: str
    border_strong: str
    text: str
    text_muted: str
    accent: str
    accent_dark: str
    accent_soft: str
    selection: str
    selection_text: str
    viewport_top: str
    viewport_bottom: str
    grid: str
    grid_label: str
    ok: str
    warn: str
    fail: str


# Light is the product default.  Values are intentionally kept in one place so
# company/user themes can be introduced without touching individual widgets.
CWS_LIGHT = ThemePalette(
    key="cws_light",
    title="CWS Licht",
    app_bg="#f3f5f7",
    panel="#ffffff",
    panel_alt="#f8f9fa",
    toolbar="#ffffff",
    border="#d9dee4",
    border_strong="#c6cdd5",
    text="#26323d",
    text_muted="#687783",
    accent="#0877bd",
    accent_dark="#005f99",
    accent_soft="#e8f3fa",
    selection="#d8ecf8",
    selection_text="#0b466d",
    viewport_top="#f7f8fa",
    viewport_bottom="#e5eaee",
    grid="#71869a",
    grid_label="#3c596f",
    ok="#18864b",
    warn="#bf7b00",
    fail="#c63d3d",
)

CWS_DARK = ThemePalette(
    key="cws_dark",
    title="CWS Donker",
    app_bg="#101720",
    panel="#141e29",
    panel_alt="#182431",
    toolbar="#182332",
    border="#2a3a4a",
    border_strong="#3b5269",
    text="#e7eef5",
    text_muted="#a9bac8",
    accent="#2f9bd3",
    accent_dark="#176896",
    accent_soft="#203b50",
    selection="#1b6798",
    selection_text="#ffffff",
    viewport_top="#26313d",
    viewport_bottom="#0f151d",
    grid="#70869a",
    grid_label="#c6d3dd",
    ok="#66d79b",
    warn="#ffbf54",
    fail="#ff7479",
)

THEMES: Mapping[str, ThemePalette] = {
    CWS_LIGHT.key: CWS_LIGHT,
    CWS_DARK.key: CWS_DARK,
}
DEFAULT_THEME_KEY = CWS_LIGHT.key

# Compatibility constants used by earlier V13 modules.
CWS_BLUE = CWS_LIGHT.accent
CWS_BLUE_DARK = CWS_LIGHT.accent_dark
CWS_BLUE_SOFT = CWS_LIGHT.accent_soft
CWS_BORDER = CWS_LIGHT.border
CWS_TEXT = CWS_LIGHT.text
CWS_MUTED = CWS_LIGHT.text_muted
CWS_PANEL = CWS_LIGHT.panel
CWS_BG = CWS_LIGHT.app_bg
CWS_OK = CWS_LIGHT.ok
CWS_WARN = CWS_LIGHT.warn
CWS_FAIL = CWS_LIGHT.fail


def qss_for_theme(p: ThemePalette) -> str:
    """Return one application stylesheet for all CWS Qt viewer surfaces."""
    return f"""
QMainWindow, QWidget {{
    background: {p.app_bg};
    color: {p.text};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 9pt;
}}
QWidget#cwsCockpitRoot, QWidget#cwsStartCenterRoot {{ background: {p.app_bg}; }}
QFrame#cwsHeader, QFrame#cwsRibbon, QFrame#cwsPanel, QFrame#cwsViewerCard,
QFrame#cwsStatusStrip, QFrame#cwsModuleOverview {{
    background: {p.panel}; border: 1px solid {p.border}; border-radius: 5px;
}}
QLabel#cwsProductTitle {{ color: {p.accent_dark}; font-size: 21pt; font-weight: 700; }}
QLabel#cwsVersion {{ color: {p.text_muted}; }}
QLabel#cwsSubtitle {{ color: {p.accent_dark}; font-size: 10pt; font-weight: 600; }}
QLabel#cwsPanelTitle, QGroupBox {{ color: {p.text}; font-weight: 600; }}
QLabel#cwsSectionTitle {{ color: {p.accent_dark}; font-weight: 700; }}
QLabel#cwsMuted {{ color: {p.text_muted}; }}
QLabel#cwsStatusOk {{ color: {p.ok}; font-weight: 600; }}
QLabel#cwsStatusWarning {{ color: {p.warn}; font-weight: 600; }}
QLabel#cwsStatusFail {{ color: {p.fail}; font-weight: 600; }}
QLabel#statusPill {{ border-radius: 7px; padding: 3px 8px; background: #eaf7f0; color: {p.ok}; }}
QLabel#warningPill {{ border-radius: 7px; padding: 3px 8px; background: #fff4dc; color: #8b5b00; }}
QLabel#accuracyPass {{ color: {p.ok}; font-weight: 600; }}
QLabel#accuracyWarning {{ color: {p.warn}; font-weight: 600; }}
QLabel#accuracyFail {{ color: {p.fail}; font-weight: 600; }}
QToolBar {{
    background: {p.toolbar};
    border: 0;
    border-bottom: 1px solid {p.border};
    spacing: 2px;
    padding: 3px 4px;
}}
QToolBar::separator {{ background: {p.border}; width: 1px; margin: 4px 5px; }}
QToolButton, QPushButton {{
    background: {p.panel}; color: {p.text}; border: 1px solid transparent;
    border-radius: 4px; padding: 4px 7px; min-height: 20px;
}}
QToolButton:hover, QPushButton:hover {{ background: {p.accent_soft}; border-color: #b9d8e9; }}
QToolButton:pressed, QPushButton:pressed {{ background: #d9ebf5; }}
QToolButton:checked, QPushButton:checked {{ background: {p.accent}; color: white; border-color: {p.accent}; }}
QPushButton#cwsPrimaryButton {{ background: {p.accent}; color: white; border: 1px solid {p.accent}; font-weight: 600; }}
QPushButton#cwsPrimaryButton:hover {{ background: {p.accent_dark}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background: {p.panel}; color: {p.text}; border: 1px solid {p.border_strong};
    border-radius: 3px; min-height: 22px; padding: 2px 5px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {p.accent}; }}
QTreeWidget, QTableWidget, QTableView, QPlainTextEdit, QListWidget {{
    background: {p.panel}; alternate-background-color: {p.panel_alt}; color: {p.text};
    border: 1px solid {p.border}; gridline-color: #e6e9ed;
    selection-background-color: {p.selection}; selection-color: {p.selection_text};
}}
QTreeWidget::item, QListWidget::item {{ min-height: 21px; }}
QTreeWidget::item:selected, QTableView::item:selected, QTableWidget::item:selected,
QListWidget::item:selected {{ background: {p.selection}; color: {p.selection_text}; }}
QHeaderView::section {{
    background: #eef1f4; color: #40505d; border: none;
    border-right: 1px solid {p.border}; border-bottom: 1px solid {p.border};
    padding: 5px; font-weight: 600;
}}
QDockWidget {{ color: {p.text}; }}
QDockWidget::title {{
    background: #eef1f4; color: #40505d; padding: 5px 7px;
    border-top: 1px solid {p.border}; border-bottom: 1px solid {p.border};
    font-weight: 600;
}}
QTabWidget::pane {{ background: {p.panel}; border: 1px solid {p.border}; top: -1px; }}
QTabBar::tab {{
    background: #eef1f4; color: #50606d; border: 1px solid {p.border};
    padding: 5px 9px; min-width: 54px;
}}
QTabBar::tab:selected {{ background: {p.panel}; color: {p.accent_dark}; border-bottom-color: {p.panel}; font-weight: 600; }}
QGroupBox {{ background: {p.panel}; border: 1px solid {p.border}; border-radius: 4px; margin-top: 8px; padding-top: 7px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 3px; background: {p.panel}; }}
QProgressBar {{ border: none; background: #e3e7eb; border-radius: 3px; height: 7px; text-align: right; color: {p.text_muted}; }}
QProgressBar::chunk {{ background: {p.accent}; border-radius: 3px; }}
QSplitter::handle {{ background: transparent; width: 4px; height: 4px; }}
QMenu {{ background: {p.panel}; color: {p.text}; border: 1px solid {p.border_strong}; padding: 3px; }}
QMenu::item {{ padding: 5px 24px 5px 8px; border-radius: 3px; }}
QMenu::item:selected {{ background: {p.accent_soft}; color: {p.accent_dark}; }}
QMenu::separator {{ height: 1px; background: {p.border}; margin: 4px 5px; }}
QStatusBar {{ background: {p.panel}; color: #536573; border-top: 1px solid {p.border}; }}
QScrollBar:vertical {{ background: #f1f3f5; width: 10px; }}
QScrollBar::handle:vertical {{ background: #c6cdd4; min-height: 24px; border-radius: 5px; }}
QScrollBar:horizontal {{ background: #f1f3f5; height: 10px; }}
QScrollBar::handle:horizontal {{ background: #c6cdd4; min-width: 24px; border-radius: 5px; }}
"""


LIGHT_QSS = qss_for_theme(CWS_LIGHT)
DARK_QSS = qss_for_theme(CWS_DARK)


def theme_by_key(key: str | None) -> ThemePalette:
    return THEMES.get(str(key or ""), CWS_LIGHT)


def persisted_theme_key() -> str:
    """Read global CWS appearance without importing settings into core code."""
    try:
        from PySide6 import QtCore

        value = str(QtCore.QSettings("CWS", "CWS Appearance").value("theme", DEFAULT_THEME_KEY))
        return value if value in THEMES else DEFAULT_THEME_KEY
    except Exception:
        return DEFAULT_THEME_KEY


def persist_theme_key(key: str) -> str:
    selected = theme_by_key(key).key
    try:
        from PySide6 import QtCore

        QtCore.QSettings("CWS", "CWS Appearance").setValue("theme", selected)
    except Exception:
        pass
    return selected


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
    "ThemePalette", "CWS_LIGHT", "CWS_DARK", "THEMES", "DEFAULT_THEME_KEY",
    "CWS_BLUE", "CWS_BLUE_DARK", "CWS_BLUE_SOFT", "CWS_BORDER", "CWS_TEXT",
    "CWS_MUTED", "CWS_PANEL", "CWS_BG", "CWS_OK", "CWS_WARN", "CWS_FAIL",
    "qss_for_theme", "LIGHT_QSS", "DARK_QSS", "theme_by_key",
    "persisted_theme_key", "persist_theme_key", "RibbonModule", "RIBBON_MODULES",
]
