from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.accuracy import AccuracyStatus, ViewerAccuracyProvider
from cws_viewer.contracts.enums import ColorScheme, NodeKind
from cws_viewer.contracts.geometry import MeshData
from cws_viewer.core.color_schemes import ProjectColorizer
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.geometry import MeshRepository


@dataclass
class FakeEntity:
    internal_id: str
    normalized_material: str = "S355JR"
    normalized_profile: str = "HEA140"
    classification_status: str = "validated"
    properties: dict[str, str] = field(default_factory=lambda: {"Phase": "1"})
    source_identity: object = field(default_factory=lambda: SimpleNamespace(source_file_id="source:ifc"))
    assembly_ids: tuple[str, ...] = ("assembly:M0001",)


class FakeProject:
    def __init__(self, entities: dict[str, FakeEntity]) -> None:
        self.entities = entities
        self.assemblies = {}
        self.parts = entities
        self.purchased_items = {}
        self.fasteners = {}
        self.welds = {}

    def get_entity(self, entity_id: str):
        return self.entities.get(entity_id)


def _mesh(source_hash: str, *, exactness: str, warnings: tuple[str, ...] = ()) -> MeshData:
    vertices = np.array(
        [[0, 0, 0], [10, 0, 0], [0, 10, 0], [0, 0, 10]], dtype=np.float64
    )
    triangles = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], dtype=np.int32)
    return MeshData(
        vertices=vertices,
        triangles=triangles,
        source_geometry_hash=source_hash,
        provider="v4-test-provider",
        exactness=exactness,
        warnings=warnings,
    )


class ViewerV4ColorAndAccuracyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scene = build_synthetic_product_scene(40, parts_per_assembly=20)
        self.index = SceneIndex.build(self.scene)
        entities: dict[str, FakeEntity] = {}
        for number, node_id in enumerate(self.index.renderable_node_ids):
            node = self.index.node(node_id)
            entities[node.entity_id] = FakeEntity(
                internal_id=node.entity_id,
                normalized_material="S355JR" if number % 2 == 0 else "S235JR",
                normalized_profile="HEA140" if number % 3 else "PL10",
                classification_status="blocked" if number % 7 == 0 else "validated",
                properties={"Phase": str(1 + number % 3)},
                assembly_ids=(f"assembly:M{1 + number // 20:04d}",),
            )
        self.project = FakeProject(entities)

    def test_color_schemes_are_deterministic_and_complete(self) -> None:
        colorizer = ProjectColorizer(self.project, self.index)
        for scheme in (
            ColorScheme.CATEGORY,
            ColorScheme.MATERIAL,
            ColorScheme.PROFILE,
            ColorScheme.STATUS,
            ColorScheme.PHASE,
            ColorScheme.SOURCE_MODEL,
            ColorScheme.ASSEMBLY,
            ColorScheme.MONOCHROME,
        ):
            first = colorizer.assignments(scheme)
            second = colorizer.assignments(scheme)
            self.assertEqual(first, second)
            self.assertEqual(len(self.index.renderable_node_ids), len(first))
            self.assertTrue(colorizer.legend(scheme))
        self.assertEqual((), colorizer.assignments(ColorScheme.ORIGINAL))
        materials = colorizer.legend(ColorScheme.MATERIAL)
        self.assertEqual(40, sum(item.count for item in materials))
        self.assertEqual({"S235JR", "S355JR"}, {item.key for item in materials})

    def test_accuracy_pass_warning_and_fail_are_explicit(self) -> None:
        node_id = next(
            node_id
            for node_id in self.index.renderable_node_ids
            if self.index.node(node_id).kind == NodeKind.PART
            and self.project.entities[self.index.node(node_id).entity_id].classification_status
            == "validated"
        )
        node = self.index.node(node_id)
        assert node.geometry_id is not None and node.geometry_hash is not None
        source_hash = self.index.geometry_by_id[node.geometry_id].content_hash
        repository = MeshRepository()
        provider = ViewerAccuracyProvider(self.index, self.project, repository)

        repository.put(node.geometry_id, _mesh(source_hash, exactness="source_tessellation"))
        passed = provider.record(node_id)
        self.assertEqual(AccuracyStatus.PASS, passed.status)
        self.assertTrue(passed.right_handed)
        self.assertEqual("mm", passed.scene_units)

        repository.put(
            node.geometry_id,
            _mesh(
                source_hash,
                exactness="display_proxy",
                warnings=("Fallback proxy gebruikt",),
            ),
        )
        warning = provider.record(node_id)
        self.assertEqual(AccuracyStatus.WARNING, warning.status)
        self.assertIn("CWS-ACCURACY-DISPLAY-PROXY", {issue.code for issue in warning.issues})

        wrong_hash = hashlib.sha256(b"wrong-source-geometry").hexdigest()
        repository.put(node.geometry_id, _mesh(wrong_hash, exactness="source_tessellation"))
        failed = provider.record(node_id)
        self.assertEqual(AccuracyStatus.FAIL, failed.status)
        self.assertIn(
            "CWS-ACCURACY-SOURCE-GEOMETRY-HASH-MISMATCH",
            {issue.code for issue in failed.issues},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
