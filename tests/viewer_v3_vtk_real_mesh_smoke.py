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
from cws_viewer.adapters import CwsProjectSceneAdapter, ProjectGeometryCatalog, ProjectSourceResolver
from cws_viewer.backends import VtkProjectMeshBackend
from cws_viewer.contracts.enums import StandardView
from cws_viewer.geometry import MeshRepository
from tests.viewer_v3_fixture import load_lo4_mesh
from cws_viewer.core.controller import ViewerCoreController

DEFAULT_PROJECT = Path(
    "/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/"
    "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
)


@unittest.skipIf(
    os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
    "GitHub Windows has no stable native OpenGL window; viewer_ci_headless_smoke covers the native pipeline",
)
class ViewerV3VtkRealMeshTests(unittest.TestCase):
    def test_lo4_real_source_mesh_render_and_pick(self) -> None:
        project_path = Path(os.environ.get("CWS_V3_REFERENCE_PROJECT", DEFAULT_PROJECT))
        if not project_path.is_file():
            self.skipTest(f"V3 referentieproject ontbreekt: {project_path}")
        project = ProjectStore().open(project_path, read_only=True).project
        resolver = ProjectSourceResolver(
            project, project_package_path=project_path, search_roots=(Path("/mnt/data"),)
        )
        catalog = ProjectGeometryCatalog().build(project, resolver)
        parts = [part for part in project.parts.values() if part.part_position == "LO4"]
        geometry_id = catalog.records_by_entity[parts[0].internal_id].geometry_id
        geometry_id_fixture, mesh, _ = load_lo4_mesh()
        self.assertEqual(geometry_id, geometry_id_fixture)
        repository = MeshRepository()
        repository.put(geometry_id, mesh)
        scene = CwsProjectSceneAdapter().build_scene(
            project, geometry_catalog=catalog, mesh_repository=repository
        )
        with tempfile.TemporaryDirectory(prefix="cws-v3-vtk-") as temp:
            backend = VtkProjectMeshBackend(repository, offscreen=True)
            controller = ViewerCoreController(backend, width=960, height=640)
            try:
                controller.load_scene(scene)
                correct = 0
                for part in parts:
                    node_id = f"entity:{part.internal_id}"
                    controller.isolate((node_id,), ghost_context=False)
                    controller.set_selection((node_id,))
                    controller.set_standard_view(StandardView.ISOMETRIC)
                    controller.fit_selection()
                    x, y = backend.node_display_point(node_id)
                    pick = controller.pick_at(x, y)
                    if pick is not None and pick.node_id == node_id:
                        correct += 1
                self.assertEqual(4, correct)
                output = Path(temp) / "lo4_source_mesh.png"
                backend.capture_png(output, width=1280, height=720)
                self.assertTrue(output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertGreater(output.stat().st_size, 20_000)
            finally:
                controller.shutdown()



if __name__ == "__main__":
    unittest.main(verbosity=2)
