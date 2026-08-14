from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.core.project_interaction import ProjectInteractionModel
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.properties import GridQuery, GridScope, GridViewerBridge


def _entity(entity_id: str, index: int):
    return SimpleNamespace(
        internal_id=entity_id,
        status="validated",
        category="make_part",
        part_position=f"P{index:04d}",
        assembly_ids=[],
        name=entity_id,
        profile="HEA140" if index % 2 else "D20",
        normalized_profile="HEA140" if index % 2 else "D20",
        material="S355JR",
        normalized_material="S355JR",
        length_mm=1000.0 + index,
        quantity_total=1,
        mass_each_kg=1.0,
        surface_area_each_m2=0.1,
        classification_status="confirmed",
        export_status="ready",
        nc1_eligible=True,
        validation_issues=(),
        source_identity=SimpleNamespace(source_entity_id=str(index), source_format="fixture", assembly_mark="", part_position=f"P{index:04d}"),
        confidence=1.0,
        geometry_hash="a" * 64,
        manufacturing_hash="b" * 64,
    )


class ViewerV8BridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scene = build_synthetic_product_scene(250, parts_per_assembly=100)
        parts = {}
        purchased_items = {}
        fasteners = {}
        welds = {}
        assemblies = {}
        for node in self.scene.nodes:
            if node.kind.value == "assembly":
                assemblies[node.entity_id] = SimpleNamespace(
                    internal_id=node.entity_id, status="validated", category="assembly", assembly_mark=node.name,
                    name=node.name, quantity=1, total_weight_kg=0.0, surface_area_m2=0.0,
                    part_ids=[], fastener_ids=[], weld_ids=[], source_identity=SimpleNamespace(source_entity_id=node.source_entity_id, source_format="fixture", assembly_mark=node.name, part_position=""),
                    validation_issues=(), confidence=1.0, production_status="validated",
                )
            elif node.kind.value == "part":
                parts[node.entity_id] = _entity(node.entity_id, len(parts))
            elif node.kind.value == "purchased_item":
                item = _entity(node.entity_id, len(purchased_items)); item.category="purchased_item"; item.quantity=1.0; item.unit_price=1.0; item.description=item.name; item.purchase_status="validated"; item.article_number=item.part_position
                purchased_items[node.entity_id] = item
            elif node.kind.value == "fastener":
                item = _entity(node.entity_id, len(fasteners)); item.category="fastener"; item.fastener_type="bolt"; item.quantity=1; item.diameter_mm=16.0; item.grade="8.8"; item.standard="EN"; item.connected_part_ids=[]; item.hole_diameter_mm=18.0
                fasteners[node.entity_id] = item
            elif node.kind.value == "weld":
                item = _entity(node.entity_id, len(welds)); item.category="weld"; item.weld_type="fillet"; item.size_mm=5.0; item.process="135"; item.side="both"; item.location="workshop"; item.time_minutes=1.0; item.cost=1.0; item.connected_part_ids=[]
                welds[node.entity_id] = item
        self.project = SimpleNamespace(project_phase="Fixture", parts=parts, assemblies=assemblies, purchased_items=purchased_items, fasteners=fasteners, welds=welds)
        self.backend = MemoryRenderBackend()
        self.controller = ViewerCoreController(self.backend)
        self.controller.load_scene(self.scene)
        self.interaction = ProjectInteractionModel(self.controller, self.project)
        self.bridge = GridViewerBridge(self.interaction, self.interaction.grid_model)

    def tearDown(self) -> None:
        self.interaction.close()
        self.controller.shutdown()

    def test_selection_scope_isolation_and_colour(self) -> None:
        part_rows = [row for row in self.interaction.grid_model.rows if row.entity_type == "part"]
        selected = tuple(row.entity_id for row in part_rows[:3])
        self.bridge.select_entities(selected)
        self.assertEqual(set(selected), set(self.interaction.selection.entity_ids))
        selected_result = self.interaction.grid_model.execute(GridQuery(scope=GridScope.SELECTED))
        self.assertEqual(3, selected_result.row_count)
        self.bridge.isolate_result(selected_result, ghost_context=True)
        self.assertTrue(self.controller.session.isolation)
        legend = self.bridge.colourize(selected_result, "profile")
        self.assertTrue(legend)
        self.assertTrue(self.controller.session.colors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
