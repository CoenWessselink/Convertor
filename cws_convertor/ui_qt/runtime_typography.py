"""Readable native Qt text in installed, source and offscreen Windows runtimes.

Never bundle system fonts. Register the fonts already installed on the machine
when the platform plugin does not enumerate them. Screenshots must pass actual
glyph shaping, not just file-size checks. No screenshot pixels are modified.
"""
from __future__ import annotations

from typing import Any

def ensure_ui_font(application: Any) -> Any:
    """Compatibility entry point backed by the production font selector.

    The older PDF proof and the current design system must not select different
    families or maintain independent validation caches. The shared selector
    validates Dutch and engineering glyphs on every cached-font use.
    """
    from cws_viewer.ui_qt.qt_compat import require_qt
    from .ui_fonts import ensure_readable_ui_font

    _core, gui, widgets = require_qt()
    if application is None or application is not widgets.QApplication.instance():
        raise RuntimeError("Use the active QApplication when initializing UI fonts")
    return gui.QFont(ensure_readable_ui_font(), 9)


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
