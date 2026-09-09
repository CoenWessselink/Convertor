"""Readable native Qt text in installed, source and offscreen Windows runtimes.

Never bundle system fonts. Register the fonts already installed on the machine
when the platform plugin does not enumerate them. Screenshots must pass actual
glyph shaping, not just file-size checks. No screenshot pixels are modified.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_SAMPLE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789éëïöüÉØ°±"
_PREFERRED = ("Bahnschrift", "Segoe UI", "Arial", "DejaVu Sans", "Liberation Sans", "Noto Sans")


def ensure_ui_font(application: Any) -> Any:
    from cws_viewer.ui_qt.qt_compat import require_qt

    _core, gui, _widgets = require_qt()
    if application is None:
        raise RuntimeError("Create QApplication before initializing the UI fonts")
    previous = application.property("cws_verified_ui_font")
    if previous:
        return gui.QFont(str(previous), 9)
    loaded = []
    # Windows' offscreen plugin can have an empty system font database. Use OS
    # fonts, including bold variants and symbols; never a private font package.
    if os.name == "nt":
        directory = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for name in ("bahnschrift.ttf", "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf",
                     "arial.ttf", "arialbd.ttf", "seguisym.ttf", "seguiemj.ttf"):
            path = directory / name
            if path.is_file():
                font_id = gui.QFontDatabase.addApplicationFont(str(path))
                if font_id >= 0:
                    loaded.extend(gui.QFontDatabase.applicationFontFamilies(font_id))
    candidates = dict.fromkeys((*_PREFERRED, application.font().family(),
                              *gui.QFontDatabase.families()))
    available = set(gui.QFontDatabase.families())
    for family in candidates:
        if family not in available:
            continue
        font = gui.QFont(family, 9)
        raw = gui.QRawFont.fromFont(font)
        if raw.isValid() and all(raw.supportsCharacter(ord(c)) for c in _SAMPLE):
            application.setFont(font)
            application.setProperty("cws_verified_ui_font", family)
            application.setProperty("cws_loaded_os_font_families", list(dict.fromkeys(loaded)))
            return font
    raise RuntimeError("Geen leesbaar UI-lettertype gevonden. Herstel een standaard "
                       "systeemlettertype (Segoe UI/Arial/DejaVu Sans) en start opnieuw.")


def text_glyph_evidence(text: str, font: Any) -> dict[str, Any]:
    """Shape text with Qt fallback enabled; index zero is the missing-glyph box."""
    from cws_viewer.ui_qt.qt_compat import require_qt

    _core, gui, _widgets = require_qt()
    # Layout a single normalized line so labels with line breaks are all tested.
    value = " ".join(str(text).split())
    if not value:
        return {"status": "empty", "glyphs": 0, "missing_glyphs": 0, "families": []}
    layout = gui.QTextLayout(value, font)
    layout.beginLayout()
    while True:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(1_000_000.0)
    layout.endLayout()
    runs = layout.glyphRuns()
    indexes = [index for run in runs for index in run.glyphIndexes()]
    missing = sum(index == 0 for index in indexes)
    return {"status": "passed" if indexes and not missing else "failed",
            "glyphs": len(indexes), "missing_glyphs": missing,
            "families": sorted({run.rawFont().familyName() for run in runs})}


def inspect_visible_text(window: Any) -> dict[str, Any]:
    """Inspect actual visible widget fonts; fail closed when no text is checked."""
    from cws_viewer.ui_qt.qt_compat import require_qt

    _core, _gui, widgets = require_qt()
    records = []
    for widget in (window, *window.findChildren(widgets.QWidget)):
        if not widget.isVisible():
            continue
        values = []
        if isinstance(widget, (widgets.QLabel, widgets.QAbstractButton, widgets.QLineEdit)):
            values.append(widget.text())
        elif isinstance(widget, widgets.QComboBox):
            values.append(widget.currentText())
        elif isinstance(widget, widgets.QTabBar):
            values.extend(widget.tabText(i) for i in range(widget.count())
                          if widget.isTabVisible(i))
        for text in values:
            if not text.strip():
                continue
            result = text_glyph_evidence(text, widget.font())
            records.append(dict(widget=widget.objectName(), text=text, **result))
    failures = [item for item in records if item["status"] != "passed"]
    return {"schema": "cws-visible-glyph-evidence-1.0",
            "status": "passed" if records and not failures else "failed",
            "checked_texts": len(records),
            "checked_glyphs": sum(item["glyphs"] for item in records),
            "missing_glyphs": sum(item["missing_glyphs"] for item in records),
            "failures": failures, "records": records}
