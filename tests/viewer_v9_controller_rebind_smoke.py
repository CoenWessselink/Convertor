from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.integration import IntegratedProjectWorkspace, create_synthetic_integration_project
from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.core.controller import ViewerCoreController


class ViewerV9ControllerRebindTests(unittest.TestCase):
    def test_rebinding_interactive_controller_preserves_one_scene_and_selection_bus(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-v9-rebind-") as directory:
            path = create_synthetic_integration_project(Path(directory) / "project.cwscproj")
            workspace = IntegratedProjectWorkspace.open(path, read_only=True, load_all_geometry=False)
            try:
                replacement = ViewerCoreController(MemoryRenderBackend())
                workspace.bind_controller(replacement)
                self.assertIs(workspace.controller, replacement)
                self.assertEqual(
                    workspace.load_result.scene.scene_hash,
                    workspace.controller.scene.scene_hash,
                )
                workspace.select_entities(("part-v9",), origin="rebind-test")
                self.assertEqual("part-v9", workspace.interaction.selection.primary_entity_id)
                self.assertEqual("part-v9", workspace.selection_bus.selection.primary_entity_id)
                self.assertEqual("rebind-test", workspace.selection_bus.selection.origin)
            finally:
                workspace.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
