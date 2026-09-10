"""Validated UI font selection for both native Windows and offscreen runtimes."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from cws_viewer.ui_qt.qt_compat import require_qt

GLYPH_PROBE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789 éëïöü É Ø ± € × °"
PREFERRED_FAMILIES = ("Bahnschrift", "Segoe UI Variable", "Segoe UI", "Arial", "DejaVu Sans")


def _has_glyphs(font: Any) -> bool:
    _core, gui, _widgets = require_qt()
    raw = gui.QRawFont.fromFont(font)
    indexes = tuple(raw.glyphIndexesForString(GLYPH_PROBE)) if raw.isValid() else ()
    return bool(indexes) and all(index != 0 for index in indexes)


def _load_font(path: Path) -> tuple[str, ...]:
    _core, gui, _widgets = require_qt()
    if not path.is_file():
        return ()
    font_id = gui.QFontDatabase.addApplicationFont(str(path))
    return tuple(gui.QFontDatabase.applicationFontFamilies(font_id)) if font_id >= 0 else ()


def _bundled_families() -> tuple[str, ...]:
    # Matplotlib already ships this runtime resource; no external download or
    # additional user font installation is needed.
    from matplotlib import get_data_path
    return _load_font(Path(get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf")


def ensure_readable_ui_font() -> str:
    _core, gui, widgets = require_qt()
    app = widgets.QApplication.instance()
    if app is None:
        raise RuntimeError("Een QApplication is nodig voor de lettertypecontrole")
    cached = str(app.property("cws_readable_font_family") or "")
    if cached and _has_glyphs(gui.QFont(cached, 9)):
        # Both historical entry points attest the same currently validated font.
        app.setProperty("cws_verified_ui_font", cached)
        return cached
    # The offscreen Windows plugin does not reliably enumerate installed GDI
    # fonts. Register the existing OS files before choosing the production font.
    if str(app.platformName()).lower() == "offscreen":
        directory = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for filename in ("bahnschrift.ttf", "segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf",
                         "arial.ttf", "arialbd.ttf", "seguisym.ttf", "seguiemj.ttf"):
            _load_font(directory / filename)
    known = {str(f).casefold() for f in gui.QFontDatabase.families()}
    chosen = next((f for f in PREFERRED_FAMILIES
                   if f.casefold() in known and _has_glyphs(gui.QFont(f, 9))), "")
    if not chosen:
        chosen = next((f for f in _bundled_families() if _has_glyphs(gui.QFont(f, 9))), "")
    if not chosen:
        raise RuntimeError("Geen leesbaar lettertype voor de Nederlandse interface gevonden")
    # Custom painters still request the product's historical family names.
    # They receive the same verified fallback if an OS family is unavailable.
    for family in PREFERRED_FAMILIES:
        if family != chosen:
            gui.QFont.insertSubstitution(family, chosen)
    app.setFont(gui.QFont(chosen, 9))
    app.setProperty("cws_readable_font_family", chosen)
    app.setProperty("cws_verified_ui_font", chosen)
    return chosen


def verify_widget_text_fonts(widget: Any) -> dict[str, Any]:
    _core, gui, widgets = require_qt()
    candidates = [widget, *(w for w in widget.findChildren(widgets.QWidget) if w.isVisible())]
    families: set[str] = set()
    signatures: set[str] = set()
    for item in candidates:
        font = item.font()
        signature = font.toString()
        if signature not in signatures:
            if not _has_glyphs(font):
                raise RuntimeError("Onleesbaar UI-lettertype: " + font.family())
            signatures.add(signature)
            families.add(gui.QRawFont.fromFont(font).familyName())
    return {"status": "PASS", "checked_widgets": len(candidates),
            "checked_font_signatures": len(signatures), "font_families": sorted(families),
            "glyph_probe": GLYPH_PROBE}
