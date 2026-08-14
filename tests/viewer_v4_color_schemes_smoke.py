from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.contracts.enums import ColorScheme
from cws_viewer.core.color_schemes import ProjectColorizer
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.fixtures import build_synthetic_product_scene


class _Project:
    def __init__(self, entities):
        self._entities = entities
        self.assemblies = {}
        self.parts = entities
        self.purchased_items = {}
        self.fasteners = {}
        self.welds = {}

    def get_entity(self, entity_id):
        return self._entities.get(entity_id)


class ViewerV4ColorSchemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scene = build_synthetic_product_scene(240, parts_per_assembly=80)
        cls.index = SceneIndex.build(cls.scene)
        entities = {}
        for index, node_id in enumerate(cls.index.renderable_node_ids):
            node = cls.index.node(node_id)
            status = "blocked" if index % 17 == 0 else "review" if index % 5 == 0 else "validated"
            entities[node.entity_id] = SimpleNamespace(
                normalized_material=("S355JR" if index % 2 else "S235JR"),
                material="",
                normalized_profile=("HEA140" if index % 3 else "STRIP5*120"),
                profile="",
                classification_status=status,
                status=status,
                export_status=status,
                properties={"Phase": str(index % 4 + 1)},
                assembly_mark=f"M{index // 80 + 1:03d}",
                source_identity=SimpleNamespace(
                    source_file_id=f"source-{index % 2 + 1}",
                    assembly_mark=f"M{index // 80 + 1:03d}",
                ),
                assembly_ids=(f"assembly-{index // 80 + 1}",),
                validation_issues=(),
            )
        cls.project = _Project(entities)

    def test_assignments_and_legends_are_deterministic(self) -> None:
        first = ProjectColorizer(self.project, self.index)
        second = ProjectColorizer(self.project, self.index)
        for scheme in ColorScheme:
            assignments_a = first.assignments(scheme)
            assignments_b = second.assignments(scheme)
            self.assertEqual(assignments_a, assignments_b)
            self.assertEqual(first.legend(scheme), second.legend(scheme))
            if scheme == ColorScheme.ORIGINAL:
                self.assertFalse(assignments_a)
            else:
                self.assertEqual(len(self.index.renderable_node_ids), len(assignments_a))

    def test_material_profile_status_and_assembly_grouping(self) -> None:
        colorizer = ProjectColorizer(self.project, self.index)
        material = colorizer.legend(ColorScheme.MATERIAL)
        profile = colorizer.legend(ColorScheme.PROFILE)
        status = colorizer.legend(ColorScheme.STATUS)
        assembly = colorizer.legend(ColorScheme.ASSEMBLY)
        self.assertEqual(2, len(material))
        self.assertEqual(2, len(profile))
        self.assertGreaterEqual(len(status), 3)
        self.assertEqual(3, len(assembly))
        self.assertEqual(240, sum(item.count for item in material))
        self.assertEqual(240, sum(item.count for item in assembly))


if __name__ == "__main__":
    unittest.main(verbosity=2)
