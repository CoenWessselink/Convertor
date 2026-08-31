from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.ui_qt.ui_v51_contract import MAIN_LABELS
from cws_convertor.ui_qt.ui_v51_contract_data import CONTROL_INVENTORY, SCREEN_MANIFEST


class UiV51BindingContractTests(unittest.TestCase):
    def test_contract_counts_and_navigation(self) -> None:
        self.assertEqual(MAIN_LABELS, ("Project", "Viewer", "Productie", "Controle", "Uitvoer"))
        self.assertEqual(len(SCREEN_MANIFEST["screens"]), 31)
        self.assertEqual(len(CONTROL_INVENTORY["controls"]), 226)
        self.assertEqual(len({item["test_id"] for item in CONTROL_INVENTORY["controls"]}), 226)

    def test_visual_and_support_surface_counts(self) -> None:
        screens = SCREEN_MANIFEST["screens"]
        self.assertEqual(sum(bool(item.get("reference_png")) for item in screens), 25)
        self.assertEqual(sum(not bool(item.get("reference_png")) for item in screens), 6)


if __name__ == "__main__":
    unittest.main()
