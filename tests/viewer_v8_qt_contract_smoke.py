from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib
import unittest


class ViewerV8QtContractTests(unittest.TestCase):
    def test_property_grid_is_import_safe_and_contains_required_controls(self) -> None:
        module = importlib.import_module("cws_viewer.ui_qt.property_grid")
        self.assertTrue(hasattr(module, "ProfessionalPropertyGridPanel"))
        source = Path(module.__file__).read_text(encoding="utf-8")
        for token in (
            "QAbstractTableModel",
            "setSectionsMovable(True)",
            "FieldChooserDialog",
            "GridScope.CHANGED",
            "GridScope.BLOCKED",
            "export_grid_csv",
            "export_grid_xlsx",
            "open_part_workbench_requested",
            "setAccessibleName",
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
