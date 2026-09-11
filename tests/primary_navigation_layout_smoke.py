"""Regression of the actual shell at narrow widths, with real Qt events.

The full native STEP/VTK and installed EXE proof calls the same traversal.
This fast layout-only test does not replace those native acceptance gates.
"""
from __future__ import annotations
import os
from pathlib import Path
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6 import QtCore, QtWidgets, QtTest
from cws_convertor.ui_qt import CWSMainWindow
from cws_convertor.ui_qt.pdf_ui_v3_evidence import _exercise_primary_navigation


class PrimaryNavigationLayoutTests(unittest.TestCase):
    def test_all_primary_tabs_and_global_controls_at_three_widths(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with tempfile.TemporaryDirectory(prefix="cws-nav-settings-") as folder:
            # Isolate settings without overwriting any user's persisted layout.
            QtCore.QSettings.setDefaultFormat(QtCore.QSettings.Format.IniFormat)
            QtCore.QSettings.setPath(QtCore.QSettings.Format.IniFormat,
                                    QtCore.QSettings.Scope.UserScope, folder)
            window = CWSMainWindow()
            try:
                window.resize(1920, 1120)
                window.show()
                def flush(duration=.03):
                    app.processEvents()
                    QtTest.QTest.qWait(round(duration * 1000))
                    app.processEvents()
                flush(.1)
                rows = _exercise_primary_navigation(window,
                    lambda name, result: self.assertTrue(result, name), flush, None)
                self.assertEqual([row['requested_width'] for row in rows], [1280,1440,1920])
                self.assertTrue(all(len(row['tabs']) == 5 for row in rows))
                # Direct sidebar changes must update the existing heading, not
                # leave a floating stale '01 / Inlezen' strip over the menu.
                button = window.native_workspace_buttons['viewer']
                QtTest.QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
                flush()
                bar = window._v51_binding.screen_toolbar
                self.assertTrue(bar.isVisible())
                self.assertIsNot(bar.parentWidget(), window)
                number = bar.findChild(QtWidgets.QLabel, 'cwsScreenNumber')
                self.assertEqual(number.text(), str(window._v51_binding.screen_selector.currentData()))
            finally:
                window.close()
                app.processEvents()


if __name__ == '__main__':
    unittest.main(verbosity=2)
