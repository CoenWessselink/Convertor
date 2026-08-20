from __future__ import annotations

import unittest

from cws_convertor.ui_qt.engineering_drawing import EngineeringDrawingGenerator
from cws_convertor.viewer.mesh_resources import _project_world_to_entity_local_vertices
from cws_viewer.backends.vtk_project_mesh_adaptive import VtkProjectMeshAdaptiveBackend


class Parity0102Tests(unittest.TestCase):
    def test_world_vertices_return_to_entity_local_frame(self) -> None:
        transform = (
            0.0, -1.0, 0.0, 100.0,
            1.0, 0.0, 0.0, 200.0,
            0.0, 0.0, 1.0, 300.0,
            0.0, 0.0, 0.0, 1.0,
        )
        local = _project_world_to_entity_local_vertices(((98.0, 201.0, 303.0),), transform)
        self.assertEqual(local, ((1.0, 2.0, 3.0),))

    def test_drawing_scale_rounds_up_to_engineering_series(self) -> None:
        self.assertEqual(EngineeringDrawingGenerator._next_standard_scale(21.0), 25)
        self.assertEqual(EngineeringDrawingGenerator._next_standard_scale(51.0), 100)

    def test_navigation_does_not_reduce_multisampling(self) -> None:
        self.assertEqual(VtkProjectMeshAdaptiveBackend.INTERACTIVE_MULTISAMPLES, 8)


if __name__ == "__main__":
    unittest.main()
