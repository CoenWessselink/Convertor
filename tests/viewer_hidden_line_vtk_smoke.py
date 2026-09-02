from __future__ import annotations

import os
import inspect
import unittest

import numpy as np

from cws_viewer.backends.vtk_project_mesh_feel_v2 import VtkProjectMeshFeelV2Backend
from cws_viewer.contracts.enums import RenderMode
from cws_viewer.contracts.geometry import MeshData
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.geometry import MeshRepository


class ViewerHiddenLinePipelineContractTests(unittest.TestCase):
    def test_production_backend_uses_feature_edges_with_depth_writing_surface(self) -> None:
        source = inspect.getsource(VtkProjectMeshFeelV2Backend._ensure_static_groups)
        mode = inspect.getsource(VtkProjectMeshFeelV2Backend._configure_group_mode)
        update = inspect.getsource(VtkProjectMeshFeelV2Backend._update_instance_state)
        self.assertIn("_feature_edges_polydata", source)
        self.assertIn("ScalarVisibilityOff", mode)
        self.assertIn("EdgeVisibilityOff", mode)
        self.assertIn("RenderMode.HIDDEN_LINE", update)


@unittest.skipUnless(
    os.environ.get("CWS_RUN_NATIVE_VTK_TESTS", "") == "1",
    "Enable only on a qualified native OpenGL runner; packaged UI acceptance covers CI",
)
class ViewerHiddenLineVtkTests(unittest.TestCase):
    def test_hidden_line_uses_depth_surface_and_feature_edge_actors(self) -> None:
        scene = build_synthetic_product_scene(24, parts_per_assembly=8)
        repository = MeshRepository()
        vertices = np.array(
            ((0, 0, 0), (80, 0, 0), (0, 80, 0), (0, 0, 80)), dtype=np.float64
        )
        triangles = np.array(((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)), dtype=np.int32)
        for resource in scene.geometry:
            repository.put(
                resource.geometry_id,
                MeshData(vertices, triangles, resource.content_hash, "hidden-line-test"),
            )
        backend = VtkProjectMeshFeelV2Backend(repository, offscreen=True)
        controller = V14ViewerCoreController(backend, width=640, height=480)
        try:
            controller.load_scene(scene)
            controller.set_render_mode(RenderMode.HIDDEN_LINE)
            controller.render()
            self.assertTrue(backend._hidden_line_actors)
            self.assertTrue(all(actor.GetVisibility() for actor in backend._hidden_line_actors))
            self.assertTrue(all(not group.mapper.GetScalarVisibility() for group in backend._mesh_groups))
            self.assertTrue(all(not group.actor.GetProperty().GetEdgeVisibility() for group in backend._mesh_groups))

            controller.set_render_mode(RenderMode.SHADED)
            controller.render()
            self.assertTrue(all(not actor.GetVisibility() for actor in backend._hidden_line_actors))
            self.assertTrue(all(group.mapper.GetScalarVisibility() for group in backend._mesh_groups))
        finally:
            controller.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
