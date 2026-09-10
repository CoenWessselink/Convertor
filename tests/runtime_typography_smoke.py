"""Real glyph shaping regression for unreadable frozen Windows main-window text."""
from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtGui, QtWidgets
from cws_convertor.ui_qt.runtime_typography import (
    ensure_ui_font, inspect_visible_text, text_glyph_evidence,
)


class RuntimeTypographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_production_font_shapes_dutch_engineering_text(self):
        font = ensure_ui_font(self.app)
        evidence = text_glyph_evidence("CWS Convertor – Hoeveelheden, beïnvloeden, Ø20 ±0,5 mm", font)
        self.assertEqual(evidence["status"], "passed", evidence)
        self.assertEqual(evidence["missing_glyphs"], 0)

    def test_initialization_is_idempotent(self):
        first = ensure_ui_font(self.app)
        second = ensure_ui_font(self.app)
        self.assertEqual(first.family(), second.family())

    def test_visible_widget_is_checked_not_just_screenshot_size(self):
        label = QtWidgets.QLabel("Project openen – PDF / Tekening")
        label.setFont(ensure_ui_font(self.app))
        label.show()
        self.app.processEvents()
        try:
            result = inspect_visible_text(label)
            self.assertEqual(result["status"], "passed", result)
            self.assertGreater(result["checked_glyphs"], 10)
        finally:
            label.close()

    def test_missing_glyph_is_rejected(self):
        result = text_glyph_evidence("A\U0010ffffB", ensure_ui_font(self.app))
        self.assertEqual(result["status"], "failed", result)
        self.assertGreater(result["missing_glyphs"], 0)

    def test_empty_capture_is_not_acceptance(self):
        window = QtWidgets.QWidget()
        window.show()
        self.app.processEvents()
        try:
            self.assertEqual(inspect_visible_text(window)["status"], "failed")
        finally:
            window.close()

    def test_both_entry_points_share_one_verified_font_after_a_cold_start(self):
        from cws_convertor.ui_qt.ui_fonts import ensure_readable_ui_font
        self.app.setProperty("cws_readable_font_family", None)
        self.app.setProperty("cws_verified_ui_font", None)
        current = ensure_readable_ui_font()
        self.assertEqual(current, self.app.property("cws_verified_ui_font"))
        self.assertEqual(current, ensure_ui_font(self.app).family())

    def test_cached_production_font_reestablishes_the_verified_attestation(self):
        from cws_convertor.ui_qt.ui_fonts import ensure_readable_ui_font
        family = ensure_readable_ui_font()
        self.app.setProperty("cws_verified_ui_font", None)
        self.assertEqual(family, ensure_readable_ui_font())
        self.assertEqual(family, self.app.property("cws_verified_ui_font"))

    def test_non_application_target_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "QApplication"):
            ensure_ui_font(None)
        with self.assertRaisesRegex(RuntimeError, "QApplication"):
            ensure_ui_font(QtWidgets.QLabel("Not the application"))

    def test_design_system_uses_the_verified_available_family(self):
        from cws_convertor.ui_qt.design_system.stylesheet import apply_v52_design_system
        self.app.setProperty("cws_verified_ui_font", None)
        self.app.setProperty("cws_readable_font_family", None)
        label = QtWidgets.QLabel("Materiaal S355JR – Revisie B")
        apply_v52_design_system(label)
        label.show()
        self.app.processEvents()
        try:
            family = str(self.app.property("cws_verified_ui_font"))
            self.assertIn(f"font-family: '{family}'", label.styleSheet())
            self.assertEqual(inspect_visible_text(label)["status"], "passed")
        finally:
            label.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
