from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.model import Assembly, Part, ProjectModel, SourceFileRecord, SourceIdentity
from cws_viewer.adapters import CwsProjectSceneAdapter
from cws_viewer.backends import HeadlessViewerController
from cws_viewer.contracts.enums import NodeKind


class ViewerProjectAdapterTests(unittest.TestCase):
    def _project(self) -> ProjectModel:
        project = ProjectModel.new(project_name="Viewer adapter test")
        project.sources["source-ifc"] = SourceFileRecord(
            source_id="source-ifc",
            file_name="viewer-reference.ifc",
            source_format="ifc",
            sha256="0" * 64,
            size_bytes=1,
            semantic_import_complete=True,
        )
        assembly = Assembly(
            internal_id="assembly-mlo4",
            name="MLO4",
            assembly_mark="MLO4",
            source_identity=SourceIdentity(
                source_format="ifc",
                source_file_id="source-ifc",
                source_entity_id="#100",
                global_id="0MLO4",
                assembly_mark="MLO4",
            ),
            part_ids=["part-lo4-a", "part-lo4-b"],
        )
        project.add_entity(assembly)
        for index in range(2):
            part = Part(
                internal_id=f"part-lo4-{'ab'[index]}",
                name=f"LO4 occurrence {index + 1}",
                part_position="LO4",
                assembly_ids=[assembly.internal_id],
                profile="STRIP5*120",
                material="S235JR",
                length_mm=160.0,
                part_type="plate",
                geometry_descriptor={
                    "bounding_box": {
                        "minimum": [0.0, 0.0, 0.0],
                        "maximum": [160.0, 120.0, 5.0],
                    }
                },
                source_identity=SourceIdentity(
                    source_format="ifc",
                    source_file_id="source-ifc",
                    source_entity_id=f"#{200 + index}",
                    part_position="LO4",
                    assembly_mark="MLO4",
                ),
            )
            part.recompute_hashes()
            project.add_entity(part)
        project.validate()
        return project

    def test_project_adapter_preserves_one_scene_node_per_entity(self) -> None:
        project = self._project()
        before = project.semantic_sha256()
        adapter = CwsProjectSceneAdapter()
        scene = adapter.build_scene(project)
        after = project.semantic_sha256()
        self.assertEqual(before, after, "Vieweradapter mag ProjectModel niet muteren")
        self.assertEqual(len(scene.nodes), len({node.node_id for node in scene.nodes}))
        selectable = [node for node in scene.nodes if node.selectable]
        self.assertEqual(3, len(selectable))
        self.assertEqual(2, sum(node.kind == NodeKind.PART for node in selectable))
        self.assertEqual(1, len(scene.geometry), "Identieke geometry hash moet instancing delen")
        self.assertIsNotNone(adapter.last_report)
        self.assertEqual(3, adapter.last_report.selectable_count)

    def test_selection_works_with_stable_scene_node_ids(self) -> None:
        scene = CwsProjectSceneAdapter().build_scene(self._project())
        controller = HeadlessViewerController()
        controller.load_scene(scene)
        node_id = "entity:part-lo4-a"
        controller.set_selection((node_id,))
        self.assertEqual((node_id,), controller.get_selection())
        controller.isolate((node_id,), ghost_context=True)
        self.assertTrue(controller.ghost_context)
        controller.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
