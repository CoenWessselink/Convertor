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
        font = ensure_ui_font(cls_app := self.app)
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

    def test_design_system_uses_the_verified_available_family(self):
        from cws_convertor.ui_qt.design_system.stylesheet import apply_v52_design_system
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
