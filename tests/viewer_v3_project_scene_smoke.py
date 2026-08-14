from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.storage import ProjectStore
from cws_viewer.adapters import (
    CwsProjectSceneAdapter,
    ProjectGeometryCatalog,
    ProjectSourceResolver,
)
from cws_viewer.geometry import MeshRepository
from tests.viewer_v3_fixture import load_lo4_mesh
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.math3d import Matrix4

DEFAULT_PROJECT = Path(
    "/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/"
    "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
)


class ViewerV3ProjectSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_path = Path(os.environ.get("CWS_V3_REFERENCE_PROJECT", DEFAULT_PROJECT))
        if not cls.project_path.is_file():
            raise unittest.SkipTest(f"V3 referentieproject ontbreekt: {cls.project_path}")
        cls.project = ProjectStore().open(cls.project_path, read_only=True).project
        cls.resolver = ProjectSourceResolver(
            cls.project,
            project_package_path=cls.project_path,
            search_roots=(Path("/mnt/data"),),
        )
        cls.catalog = ProjectGeometryCatalog().build(cls.project, cls.resolver)
        cls.lo4_parts = [p for p in cls.project.parts.values() if p.part_position == "LO4"]
        cls.lo4_geometry_id = cls.catalog.records_by_entity[cls.lo4_parts[0].internal_id].geometry_id

    def test_lazy_single_geometry_scene_and_relative_placements(self) -> None:
        geometry_id, mesh, manifest = load_lo4_mesh()
        self.assertEqual(self.lo4_geometry_id, geometry_id)
        repository = MeshRepository()
        repository.put(geometry_id, mesh)
        adapter = CwsProjectSceneAdapter()
        scene = adapter.build_scene(
            self.project,
            geometry_catalog=self.catalog,
            mesh_repository=repository,
        )
        report = adapter.last_report
        self.assertIsNotNone(report)
        self.assertEqual(6168, report.node_count)
        self.assertEqual(6162, report.selectable_count)
        self.assertEqual(673, report.geometry_resource_count)
        self.assertEqual(1, report.loaded_geometry_count)
        self.assertEqual(672, report.deferred_geometry_count)
        self.assertEqual(0, report.proxy_geometry_count)

        index = SceneIndex.build(scene)
        self.assertEqual("source_tessellation", mesh.exactness)
        size = sorted(round(value, 6) for value in mesh.bounds.size.to_tuple())
        self.assertEqual([5.0, 120.0, 160.0], size)
        self.assertEqual(180, mesh.vertex_count)
        self.assertEqual(116, mesh.triangle_count)

        for part in self.lo4_parts:
            node_id = f"entity:{part.internal_id}"
            node = index.node(node_id)
            self.assertEqual(self.lo4_geometry_id, node.geometry_id)
            expected = Matrix4.from_rows(part.global_placement.matrix)
            actual = index.world_transform_by_node[node_id]
            for a, b in zip(actual.values, expected.values):
                self.assertAlmostEqual(a, b, places=6)

        repeat = CwsProjectSceneAdapter().build_scene(
            self.project,
            geometry_catalog=self.catalog,
            mesh_repository=repository,
        )
        self.assertEqual(scene.scene_hash, repeat.scene_hash)

    def test_no_duplicate_project_entity_nodes(self) -> None:
        scene = CwsProjectSceneAdapter().build_scene(self.project)
        entity_nodes = [node for node in scene.nodes if node.node_id.startswith("entity:")]
        self.assertEqual(len(entity_nodes), len({node.entity_id for node in entity_nodes}))
        self.assertEqual(
            353 + 2432 + 723 + 2654,
            len(entity_nodes),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
