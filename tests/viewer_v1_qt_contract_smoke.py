from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.errors import ViewerError
from cws_viewer.ui_qt import OcctAisWidget, VtkMeshWidget, qt_available


class ViewerV1QtContractTests(unittest.TestCase):
    def test_qt_layer_is_import_safe_and_explicit(self) -> None:
        if not qt_available():
            with self.assertRaises(ViewerError):
                OcctAisWidget()
            with self.assertRaises(ViewerError):
                VtkMeshWidget()
            return

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6 import QtWidgets

        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        occt = OcctAisWidget()
        self.assertIsNotNone(occt)
        if QtWidgets.QApplication.platformName() == "offscreen":
            self.assertTrue(isinstance(VtkMeshWidget, type))
            occt.close()
            application.processEvents()
            return
        vtk = VtkMeshWidget()
        self.assertIsNotNone(vtk)
        vtk.close()
        occt.close()
        application.processEvents()


if __name__ == "__main__":
    unittest.main(verbosity=2)
