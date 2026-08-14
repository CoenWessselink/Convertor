from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.storage import ProjectStore
from cws_viewer.adapters.project_model import CwsProjectSceneAdapter
from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.core.project_interaction import ProjectInteractionModel
from cws_viewer.properties import GridColumn, ProjectGridModel, ProjectPropertyProvider
from cws_viewer.search import ViewerSearchIndex

DEFAULT_PROJECT = Path(
    "/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/"
    "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
)
PROJECT_PATH = Path(os.environ.get("CWS_V3_REFERENCE_PROJECT", DEFAULT_PROJECT))


@unittest.skipUnless(PROJECT_PATH.is_file(), f"V3 referentieproject ontbreekt: {PROJECT_PATH}")
class ViewerV3SearchPropertyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_path = PROJECT_PATH
        cls.project = ProjectStore().open(cls.project_path, read_only=True).project
        cls.scene = CwsProjectSceneAdapter().build_scene(cls.project)

    def test_search_properties_grid_and_layout(self) -> None:
        search = ViewerSearchIndex(self.scene, self.project)
        lo4_hits = search.search("LO4")
        mlo4_hits = search.search("MLO4")
        lo4_parts = [hit for hit in lo4_hits if hit.entity_id in self.project.parts]
        mlo4_assemblies = [hit for hit in mlo4_hits if hit.entity_id in self.project.assemblies]
        self.assertEqual(4, len(lo4_parts))
        self.assertEqual(4, len(mlo4_assemblies))
        # Exact part position LO4 must outrank substring match MLO4.
        self.assertIn(lo4_hits[0].entity_id, self.project.parts)
        self.assertEqual("LO4", self.project.parts[lo4_hits[0].entity_id].part_position)
        self.assertIn(mlo4_hits[0].entity_id, self.project.assemblies)
        self.assertEqual("MLO4", self.project.assemblies[mlo4_hits[0].entity_id].assembly_mark)

        provider = ProjectPropertyProvider(self.project)
        records = provider.records(lo4_parts[0].entity_id)
        values = {record.key: record.value for record in records}
        self.assertEqual("LO4", values["part_position"])
        self.assertEqual("STRIP5*120", values["profile"])
        self.assertEqual("S235JR", values["material"])
        self.assertAlmostEqual(160.0, float(values["length_mm"]), places=6)

        grid = ProjectGridModel(self.project)
        rows = grid.query("LO4 S235JR", filters={"profile": "STRIP5*120"})
        self.assertEqual(4, len(rows))
        groups = grid.groups("profile", rows)
        self.assertEqual(4, len(groups["STRIP5*120"]))
        with tempfile.TemporaryDirectory(prefix="cws-v3-grid-") as temp:
            path = Path(temp) / "layout.json"
            columns = list(grid.columns)
            columns[0] = GridColumn(columns[0].key, columns[0].label, 222, True, 5)
            grid.set_columns(columns)
            grid.save_layout(path)
            restored = ProjectGridModel(self.project)
            restored.load_layout(path)
            status = next(c for c in restored.columns if c.key == "status")
            self.assertEqual(222, status.width)

    def test_v3_qt_shell_is_import_safe_without_qt(self) -> None:
        from cws_viewer.ui_qt import qt_available
        from cws_viewer.ui_qt.project_viewer import (
            RealProjectViewerWindow,
            run_real_project_viewer,
        )
        from cws_viewer.ui_qt.vtk_real_project_widget import VtkRealProjectWidget

        self.assertIsInstance(qt_available(), bool)
        self.assertTrue(callable(run_real_project_viewer))
        self.assertIsNotNone(RealProjectViewerWindow)
        self.assertIsNotNone(VtkRealProjectWidget)

    def test_tree_grid_renderer_selection_is_bidirectional(self) -> None:
        backend = MemoryRenderBackend()
        controller = ViewerCoreController(backend)
        controller.load_scene(self.scene)
        interaction = ProjectInteractionModel(controller, self.project)
        events = []
        unsubscribe = interaction.subscribe(events.append)
        try:
            part_id = next(p.internal_id for p in self.project.parts.values() if p.part_position == "LO4")
            node_id = interaction.node_for_entity(part_id)
            interaction.select_entities((part_id,), origin="grid")
            self.assertEqual((node_id,), controller.get_selection())
            self.assertEqual("grid", events[-1].origin)
            controller.set_selection((node_id,))
            self.assertEqual(part_id, interaction.selection.primary_entity_id)
            self.assertEqual("viewer", interaction.selection.origin)
            self.assertEqual("LO4", {r.key: r.value for r in interaction.properties_for_primary()}["part_position"])
        finally:
            unsubscribe()
            interaction.close()
            controller.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
