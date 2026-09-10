"""V3 integration regressions: real engine and selected-assembly generator."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cws_convertor.drawings import DrawingBuildRequest, ProductionDrawingEngine
from cws_convertor.project.model import Assembly, Part, ProjectModel
from cws_convertor.ui_qt.engineering_drawing import EngineeringDrawingGenerator
from tests.production_drawing_engine_smoke import _box_mesh


def workspace_fixture():
    project = ProjectModel.new("V3 assembly QA", created_by="v3-test")
    project.parts["P1"] = Part(internal_id="P1", part_position="P1")
    project.parts["P2"] = Part(internal_id="P2", part_position="P2")
    project.assemblies["A1"] = Assembly(internal_id="A1", assembly_mark="A1", part_ids=["P1", "P2"], main_part_id="P1")
    vertices, triangles = _box_mesh()
    meshes = {key: SimpleNamespace(vertices=vertices.copy(), triangles=triangles.copy()) for key in ("P1", "P2")}
    nodes = {key: SimpleNamespace(geometry_id=key) for key in meshes}
    nodes["A1"] = SimpleNamespace(geometry_id=None)
    matrices = {}
    for key in nodes:
        matrix = np.eye(4)
        if key == "P2":
            matrix[0, 3] = 350.0
        matrices[key] = SimpleNamespace(to_rows=lambda matrix=matrix: matrix.tolist())
    index = SimpleNamespace(node=lambda key: nodes[key], world_transform_by_node=matrices)
    return SimpleNamespace(project=project, session=SimpleNamespace(read_only=False, dirty=False, path=None),
                           interaction=SimpleNamespace(node_for_entity=lambda key: key),
                           controller=SimpleNamespace(index=index), load_result=SimpleNamespace(repository=meshes))


class DrawingV3CompletionTests(unittest.TestCase):
    def test_fixed_scale_that_does_not_fit_is_rejected(self):
        vertices, triangles = _box_mesh()
        vertices *= 100
        with self.assertRaisesRegex(ValueError, "Vaste schaal 1:1 past niet"):
            ProductionDrawingEngine.build(DrawingBuildRequest(entity_id="P1", vertices=vertices, triangles=triangles, scale_denominator=1))

    def test_fitting_fixed_scale_is_never_silently_changed(self):
        vertices, triangles = _box_mesh()
        for denominator in (1, 3, 5, 20):
            drawing = ProductionDrawingEngine.build(DrawingBuildRequest(entity_id="P1", vertices=vertices, triangles=triangles,
                    views=("front",), scale_denominator=denominator, include_sections=False, include_details=False))
            self.assertEqual(drawing.scale_denominator, denominator)
            self.assertAlmostEqual(drawing.view_contexts[0]["scale"], 1.0 / denominator)

    def test_auto_scale_remains_available(self):
        vertices, triangles = _box_mesh()
        vertices *= 100
        drawing = ProductionDrawingEngine.build(DrawingBuildRequest(entity_id="P1", vertices=vertices, triangles=triangles))
        self.assertGreater(drawing.scale_denominator, 1)

    def test_malformed_scale_is_not_accepted_as_auto(self):
        for scale in ("wrong", "1:0", "1:-1", "1:nan", "1:inf", "2:20", "1:2.5"):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                EngineeringDrawingGenerator._requested_scale(scale)

    def test_assembly_without_parent_mesh_resolves_all_children(self):
        workspace = workspace_fixture()
        generator = EngineeringDrawingGenerator(workspace)
        entity, _, identity, vertices, triangles = generator._resolve("A1")
        self.assertEqual(identity, "A1")
        self.assertEqual(len(vertices), 16)
        self.assertEqual(len(triangles), 24)
        self.assertGreater(np.ptp(vertices[:, 0]), 450)
        self.assertEqual({v["entity_id"] for v in generator._assembly_component_geometry(entity)[2]}, {"P1", "P2"})

    def test_one_member_assembly_is_not_substituted(self):
        workspace = workspace_fixture()
        workspace.project.assemblies["A1"].part_ids = ["P1"]
        self.assertEqual(EngineeringDrawingGenerator(workspace)._resolve("A1")[2], "A1")

    def test_missing_component_blocks_incomplete_assembly(self):
        workspace = workspace_fixture()
        del workspace.load_result.repository["P2"]
        with self.assertRaisesRegex(ValueError, "componenten ontbreken: P2"):
            EngineeringDrawingGenerator(workspace)._resolve("A1")

    def test_nested_assembly_includes_transformed_descendants(self):
        workspace = workspace_fixture()
        workspace.project.assemblies["A1"].part_ids = ["P1"]
        workspace.project.assemblies["A1"].child_assembly_ids = ["A2"]
        workspace.project.assemblies["A2"] = Assembly(internal_id="A2", part_ids=["P2"])
        result = EngineeringDrawingGenerator(workspace)._resolve("A1")
        self.assertEqual(len(result[3]), 16)

    def test_cycle_and_missing_subassembly_fail_closed(self):
        workspace = workspace_fixture()
        for child in ("A1", "missing"):
            workspace.project.assemblies["A1"].child_assembly_ids = [child]
            with self.assertRaises(ValueError):
                EngineeringDrawingGenerator(workspace)._resolve("A1")

    def test_real_generator_keeps_assembly_entity_bom_and_component_refs(self):
        workspace = workspace_fixture()
        with TemporaryDirectory() as folder:
            result = EngineeringDrawingGenerator(workspace).generate(folder, entity_id="A1", make_pdf=True,
                include_sections=False, include_details=False)
            self.assertEqual(result.document.entity_id, "A1")
            self.assertEqual(result.document.document_type, "assembly")
            self.assertTrue(result.pdf_path.is_file())
            refs = {ref for page in result.document.pages for primitive in page.primitives for ref in primitive.refs}
            self.assertIn("entity:P1", refs)
            self.assertIn("entity:P2", refs)
            self.assertFalse(result.release_ready, "Mesh review is not production acceptance")


if __name__ == "__main__":
    unittest.main(verbosity=2)
