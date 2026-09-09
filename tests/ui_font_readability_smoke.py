"""Actual Qt glyph checks, including the bundled fallback and negative gate."""
from __future__ import annotations
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


@unittest.skipUnless(qt_available(), "Real Qt runtime is required")
class UIFontReadabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core, cls.gui, cls.widgets = require_qt()
        cls.app = cls.widgets.QApplication.instance() or cls.widgets.QApplication([])

    def test_production_font_contains_dutch_letters_digits_and_symbols(self):
        from cws_convertor.ui_qt.ui_fonts import GLYPH_PROBE, ensure_readable_ui_font
        family = ensure_readable_ui_font()
        raw = self.gui.QRawFont.fromFont(self.gui.QFont(family, 9))
        self.assertTrue(raw.isValid())
        self.assertNotIn(0, raw.glyphIndexesForString(GLYPH_PROBE))
        self.assertEqual(family, self.app.property("cws_readable_font_family"))

    def test_selection_is_idempotent(self):
        from cws_convertor.ui_qt.ui_fonts import ensure_readable_ui_font
        self.assertEqual(ensure_readable_ui_font(), ensure_readable_ui_font())

    def test_existing_bundled_font_resource_is_readable(self):
        from cws_convertor.ui_qt.ui_fonts import _bundled_families, _has_glyphs
        families = _bundled_families()
        self.assertTrue(families)
        self.assertTrue(all(_has_glyphs(self.gui.QFont(f, 9)) for f in families))

    def test_both_themes_render_real_label_fonts_without_missing_glyphs(self):
        from cws_convertor.ui_qt.design_system.stylesheet import apply_v52_design_system
        from cws_convertor.ui_qt.ui_fonts import verify_widget_text_fonts
        window = self.widgets.QWidget()
        layout = self.widgets.QVBoxLayout(window)
        layout.addWidget(self.widgets.QLabel("BOM wijzigen – materiaal S355J2 – één profiel, € 10,00"))
        for theme in ("Default Light", "Engineering Dark"):
            apply_v52_design_system(window, theme)
            window.show()
            self.app.processEvents()
            report = verify_widget_text_fonts(window)
            self.assertEqual("PASS", report["status"])
            self.assertGreaterEqual(report["checked_widgets"], 2)
            self.assertIn(str(window.property("cws_font_family")), window.styleSheet())
        window.close()

    def test_recent_placeholder_uses_real_readable_painter_font(self):
        from cws_convertor.ui_qt.workspace_pages import IntakeDashboard
        from cws_convertor.ui_qt.ui_fonts import _has_glyphs, ensure_readable_ui_font
        widget = self.widgets.QWidget()
        icon = IntakeDashboard._preview_icon(widget, "project", "CWS")
        self.assertFalse(icon.isNull())
        self.assertEqual(ensure_readable_ui_font(), widget.property("cws_recent_preview_font"))
        self.assertTrue(_has_glyphs(self.gui.QFont(widget.property("cws_recent_preview_font"), 10)))
        self.assertFalse(icon.pixmap(420, 224).isNull())
        widget.close()

    def test_missing_glyphs_are_a_failure_not_a_valid_screenshot(self):
        from cws_convertor.ui_qt.ui_fonts import verify_widget_text_fonts
        widget = self.widgets.QLabel("BOM")
        with patch("cws_convertor.ui_qt.ui_fonts._has_glyphs", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "Onleesbaar"):
                verify_widget_text_fonts(widget)
        widget.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
