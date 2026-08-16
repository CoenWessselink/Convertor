from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.ui_qt.cockpit_v15 import (
    V15_DOCK_SPECS,
    V15_VERSION,
    V15_WORKSPACE_SCHEMA,
    V15_WORKSPACE_STATE_VERSION,
    workspace_contract,
)


class ViewerV15WorkspaceContractTests(unittest.TestCase):
    def test_contract_is_versioned_and_complete(self) -> None:
        contract = workspace_contract()
        self.assertEqual("cws-viewer-workspace-15.1", V15_WORKSPACE_SCHEMA)
        self.assertEqual(15, V15_WORKSPACE_STATE_VERSION)
        self.assertEqual(V15_WORKSPACE_SCHEMA, contract["schema"])
        self.assertEqual(V15_VERSION, contract["version"])
        self.assertEqual(["project", "properties", "workbench"], [d["key"] for d in contract["docks"]])

    def test_all_panels_are_dockable_and_persistent(self) -> None:
        caps = workspace_contract()["capabilities"]
        self.assertTrue(caps["dockable_panels"])
        self.assertTrue(caps["floating_panels"])
        self.assertTrue(caps["persistent_layout"])
        self.assertTrue(caps["focus_viewer_mode"])
        self.assertTrue(caps["reset_layout"])
        self.assertTrue(caps["v14_functionality_preserved"])
        self.assertEqual({"left", "right", "bottom"}, {spec.area for spec in V15_DOCK_SPECS})


if __name__ == "__main__":
    unittest.main(verbosity=2)
