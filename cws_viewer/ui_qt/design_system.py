"""CWS Viewer application-wide visual design system.

The default V14 theme is a bright engineering workspace: white work surfaces,
subtle neutral borders, dark neutral text and CWS blue for active tools.  It is
an original CWS theme informed by common desktop engineering-viewer conventions;
no third-party theme resources, icons or compiled assets are embedded.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    key: str
    title: str
    app_bg: str
    panel: str
    toolbar: str
    viewer_frame: str
    text: str
    muted: str
    border: str
    accent: str
    accent_dark: str
    accent_soft: str
    selection: str
    selection_text: str
    ok: str
    warn: str
    fail: str
    destructive: str


# The neutral text/destructive values intentionally align with explicit colour
# strings visible in the supplied Trimble Connect static metadata (#363644 and
# #D52A33).  The complete proprietary theme is *not* extracted or copied; CWS
# supplies its own accent, spacing, widgets and states around those neutrals.
ENGINEERING_LIGHT = ThemeTokens(
    key="engineering_light",
    title="Engineering licht",
    app_bg="#f2f4f7",
    panel="#ffffff",
    toolbar="#f7f8fa",
    viewer_frame="#e6e9ed",
    text="#363644",
    muted="#69707a",
    border="#d7dce2",
    accent="#0b5bd3",
    accent_dark="#0747a6",
    accent_soft="#e8f1ff",
    selection="#d9e9ff",
    selection_text="#15345f",
    ok="#258a55",
    warn="#b97812",
    fail="#D52A33",
    destructive="#D52A33",
)

CWS_LIGHT = ThemeTokens(
    key="cws_light",
    title="CWS licht",
    app_bg="#f4f7fb",
    panel="#ffffff",
    toolbar="#f7f9fc",
    viewer_frame="#dfe7f0",
    text="#172235",
    muted="#69798a",
    border="#d8e1eb",
    accent="#0b5bd3",
    accent_dark="#0647a5",
    accent_soft="#eaf2ff",
    selection="#dbeaff",
    selection_text="#0f2f62",
    ok="#1f9d61",
    warn="#d99614",
    fail="#d64545",
    destructive="#d64545",
)

CWS_DARK = ThemeTokens(
    key="cws_dark",
    title="CWS donker",
    app_bg="#111820",
    panel="#18222d",
    toolbar="#1d2935",
    viewer_frame="#0e151d",
    text="#e7eef5",
    muted="#a9b7c4",
    border="#314354",
    accent="#3187e8",
    accent_dark="#1d6ec5",
    accent_soft="#243c56",
    selection="#245b8b",
    selection_text="#ffffff",
    ok="#4ec58c",
    warn="#e5a63a",
    fail="#ed636a",
    destructive="#ed636a",
)

THEMES: dict[str, ThemeTokens] = {
    item.key: item for item in (ENGINEERING_LIGHT, CWS_LIGHT, CWS_DARK)
}
DEFAULT_THEME = ENGINEERING_LIGHT.key

# Backward-compatible token names used by startup/loading code.
CWS_BLUE = CWS_LIGHT.accent
CWS_BLUE_DARK = CWS_LIGHT.accent_dark
CWS_BLUE_SOFT = CWS_LIGHT.accent_soft
CWS_BORDER = CWS_LIGHT.border
CWS_TEXT = CWS_LIGHT.text
CWS_MUTED = CWS_LIGHT.muted
CWS_PANEL = CWS_LIGHT.panel
CWS_BG = CWS_LIGHT.app_bg
CWS_OK = CWS_LIGHT.ok
CWS_WARN = CWS_LIGHT.warn
CWS_FAIL = CWS_LIGHT.fail


def theme_tokens(key: str | None) -> ThemeTokens:
    return THEMES.get(str(key or ""), ENGINEERING_LIGHT)


def theme_qss(key: str | None = None) -> str:
    t = theme_tokens(key)
    return f"""
QMainWindow, QWidget#cwsCockpitRoot, QWidget#cwsViewerRoot {{
    background: {t.app_bg};
    color: {t.text};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 9.5pt;
}}
QFrame#cwsHeader, QFrame#cwsRibbon, QFrame#cwsPanel, QFrame#cwsViewerCard,
QFrame#cwsStatusStrip, QFrame#cwsModuleOverview, QFrame#cwsToolGroup {{
    background: {t.panel};
    border: 1px solid {t.border};
    border-radius: 4px;
}}
QLabel#cwsProductTitle {{ color: {t.accent_dark}; font-size: 22pt; font-weight: 700; }}
QLabel#cwsVersion {{ color: {t.muted}; font-size: 9pt; }}
QLabel#cwsSubtitle {{ color: {t.accent_dark}; font-size: 11pt; font-weight: 600; }}
QLabel#cwsPanelTitle, QLabel#cwsToolGroupTitle {{ color: {t.text}; font-weight: 650; }}
QLabel#cwsSectionTitle {{ color: {t.accent_dark}; font-weight: 700; }}
QLabel#cwsMuted {{ color: {t.muted}; }}
QLabel#cwsStatusOk {{ color: {t.ok}; font-weight: 600; }}
QLabel#cwsStatusWarning {{ color: {t.warn}; font-weight: 600; }}
QLabel#cwsStatusFail {{ color: {t.fail}; font-weight: 600; }}
QLabel#statusPill {{ border-radius: 8px; padding: 3px 8px; background: {t.accent_soft}; color: {t.accent_dark}; }}
QLabel#warningPill {{ border-radius: 8px; padding: 3px 8px; background: #fff2d8; color: #855800; }}
QToolBar {{
    background: {t.toolbar};
    color: {t.text};
    border: none;
    border-bottom: 1px solid {t.border};
    spacing: 2px;
    padding: 3px;
}}
QToolBar::separator {{ background: {t.border}; width: 1px; margin: 4px 5px; }}
QToolButton, QPushButton {{
    background: transparent;
    color: {t.text};
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 5px 7px;
    min-height: 22px;
}}
QToolButton:hover, QPushButton:hover {{ background: {t.accent_soft}; border-color: {t.border}; }}
QToolButton:checked, QPushButton:checked {{ background: {t.accent}; color: white; border-color: {t.accent}; }}
QPushButton#cwsPrimaryButton {{ background: {t.accent}; color: white; border: 1px solid {t.accent}; font-weight: 600; }}
QPushButton#cwsPrimaryButton:hover {{ background: {t.accent_dark}; }}
QPushButton#cwsDangerButton {{ color: {t.destructive}; border-color: {t.destructive}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    background: {t.panel};
    color: {t.text};
    border: 1px solid {t.border};
    border-radius: 3px;
    min-height: 23px;
    padding: 2px 5px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {t.accent}; }}
QComboBox QAbstractItemView {{ background: {t.panel}; color: {t.text}; selection-background-color: {t.selection}; }}
QTreeWidget, QTableWidget, QTableView, QPlainTextEdit, QListWidget {{
    background: {t.panel};
    alternate-background-color: {t.toolbar};
    color: {t.text};
    border: 1px solid {t.border};
    gridline-color: {t.border};
    selection-background-color: {t.selection};
    selection-color: {t.selection_text};
}}
QHeaderView::section {{
    background: {t.toolbar};
    color: {t.text};
    border: none;
    border-right: 1px solid {t.border};
    border-bottom: 1px solid {t.border};
    padding: 5px;
    font-weight: 600;
}}
QTreeWidget::item, QListWidget::item {{ min-height: 22px; }}
QTreeWidget::item:selected, QTableView::item:selected, QTableWidget::item:selected, QListWidget::item:selected {{
    background: {t.selection};
    color: {t.selection_text};
}}
QDockWidget {{ color: {t.text}; }}
QDockWidget::title {{ background: {t.toolbar}; color: {t.text}; border-bottom: 1px solid {t.border}; padding: 5px; font-weight: 600; }}
QTabWidget::pane {{ background: {t.panel}; border: 1px solid {t.border}; top: -1px; }}
QTabBar::tab {{ background: {t.toolbar}; color: {t.muted}; border: 1px solid {t.border}; padding: 5px 9px; }}
QTabBar::tab:selected {{ background: {t.panel}; color: {t.accent_dark}; border-bottom-color: {t.panel}; font-weight: 600; }}
QProgressBar {{ border: none; background: {t.border}; border-radius: 4px; height: 8px; text-align: right; color: {t.text}; }}
QProgressBar::chunk {{ background: {t.accent}; border-radius: 4px; }}
QSplitter::handle {{ background: {t.border}; width: 2px; height: 2px; }}
QMenu {{ background: {t.panel}; color: {t.text}; border: 1px solid {t.border}; padding: 4px; }}
QMenu::item {{ padding: 6px 24px 6px 8px; border-radius: 3px; }}
QMenu::item:selected {{ background: {t.accent_soft}; color: {t.accent_dark}; }}
QMenu::separator {{ height: 1px; background: {t.border}; margin: 4px 8px; }}
QStatusBar {{ background: {t.panel}; color: {t.muted}; border-top: 1px solid {t.border}; }}
QScrollBar:vertical {{ background: {t.toolbar}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {t.border}; min-height: 24px; border-radius: 5px; }}
QScrollBar:horizontal {{ background: {t.toolbar}; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {t.border}; min-width: 24px; border-radius: 5px; }}
"""


LIGHT_QSS = theme_qss(DEFAULT_THEME)


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
    "ThemeTokens", "ENGINEERING_LIGHT", "CWS_LIGHT", "CWS_DARK", "THEMES",
    "DEFAULT_THEME", "theme_tokens", "theme_qss", "LIGHT_QSS",
    "CWS_BLUE", "CWS_BLUE_DARK", "CWS_BLUE_SOFT", "CWS_BORDER", "CWS_TEXT",
    "CWS_MUTED", "CWS_PANEL", "CWS_BG", "CWS_OK", "CWS_WARN", "CWS_FAIL",
    "RibbonModule", "RIBBON_MODULES",
]
