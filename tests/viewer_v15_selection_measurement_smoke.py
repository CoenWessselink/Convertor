from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.core.v15_selection_measurement import (
    TOLERANCE_PROFILES,
    V15SelectionMeasurementService,
    V15_T4_SCHEMA,
    selection_measurement_contract,
)
from cws_viewer.exact import candidates_for_subshape, load_step_exact
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.measurements import MeasurementProof, SnapType


class ViewerV15SelectionMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.exact = load_step_exact(
            ROOT / "validation" / "v0.2_generated_step" / "P1811.step",
            part_id="P1811",
        )

    def setUp(self) -> None:
        self.backend = MemoryRenderBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1200, height=800)
        self.scene = build_synthetic_product_scene(30, parts_per_assembly=10)
        self.controller.load_scene(self.scene)
        self.service = V15SelectionMeasurementService(self.controller)

    def tearDown(self) -> None:
        self.controller.shutdown()

    def test_contract_separates_snap_tolerance_from_production_tolerance(self) -> None:
        contract = selection_measurement_contract()
        self.assertEqual("cws-viewer-selection-measurement-15.3", V15_T4_SCHEMA)
        self.assertTrue(contract["capabilities"]["exact_brep_snapping"])
        self.assertTrue(contract["capabilities"]["grouped_properties"])
        self.assertFalse(contract["capabilities"]["ai_derived_dimensions"])
        self.assertFalse(
            contract["safety"]["interaction_tolerances_are_production_tolerances"]
        )
        self.assertEqual(1.0, TOLERANCE_PROFILES["fine"].snap_tolerance_mm)

    def test_selection_level_promotes_visible_nodes_deterministically(self) -> None:
        self.service.set_selection_level(SelectionLevel.ASSEMBLY)
        selected = self.service.select_all_visible()
        self.assertTrue(selected)
        self.assertEqual(selected, tuple(dict.fromkeys(selected)))
        for node_id in selected:
            node = self.controller.index.node(node_id)
            self.assertEqual("assembly", node.kind.value)

    def test_invert_visible_selection_is_deterministic(self) -> None:
        self.service.set_selection_level(SelectionLevel.PART)
        all_visible = self.service.visible_selectable()
        first = all_visible[:3]
        self.controller.set_selection(first)
        inverted = self.service.invert_visible_selection()
        self.assertFalse(set(first) & set(inverted))
        self.assertEqual(set(all_visible) - set(first), set(inverted))

    def test_project_pick_without_exact_repository_is_review_only(self) -> None:
        node_id = self.controller.index.renderable_node_ids[0]
        self.backend.pick_node_id = node_id
        pick = self.controller.pick_at(10, 10)
        self.assertIsNotNone(pick)
        assert pick is not None
        anchor = self.service.anchor_from_project_pick(pick)
        self.assertEqual(MeasurementProof.DISPLAY_PROXY, anchor.proof)
        self.assertFalse(anchor.proof.production_eligible)

    def test_exact_circle_center_snap_is_analytical(self) -> None:
        edge = next(
            item
            for item in self.exact.snapshot.subshapes
            if item.kind.value == "edge"
            and item.geometry_type == "CIRCLE"
            and item.axis_origin is not None
        )
        assert edge.axis_origin is not None
        anchor = self.service.exact_snap_anchor(
            self.exact,
            edge.axis_origin,
            allowed=(SnapType.CENTER,),
            tolerance_mm=0.01,
        )
        self.assertIsNotNone(anchor)
        assert anchor is not None
        self.assertEqual(SnapType.CENTER, anchor.snap_type)
        self.assertEqual(MeasurementProof.ANALYTICAL_BREP, anchor.proof)
        self.assertTrue(anchor.proof.production_eligible)

    def test_exact_line_endpoint_distance_is_geometry_based(self) -> None:
        edge = next(
            item
            for item in self.exact.snapshot.subshapes
            if item.kind.value == "edge"
            and item.geometry_type == "LINE"
            and item.start is not None
            and item.end is not None
            and item.measure > 100.0
        )
        assert edge.start is not None and edge.end is not None
        start = self.service.exact_snap_anchor(
            self.exact,
            edge.start,
            allowed=(SnapType.ENDPOINT,),
            tolerance_mm=0.01,
        )
        end = self.service.exact_snap_anchor(
            self.exact,
            edge.end,
            allowed=(SnapType.ENDPOINT,),
            tolerance_mm=0.01,
        )
        self.assertIsNotNone(start)
        self.assertIsNotNone(end)
        assert start is not None and end is not None
        record = self.service.add_distance(start, end)
        self.assertAlmostEqual(edge.measure, record.value, places=6)
        self.assertEqual(MeasurementProof.ANALYTICAL_BREP, record.proof)
        self.assertTrue(record.production_eligible)
        self.assertIn(record.measurement_id, {m.measurement_id for m in self.controller.list_measurements()})

    def test_exact_radius_and_diameter_use_analytical_radius(self) -> None:
        edge = next(
            item
            for item in self.exact.snapshot.subshapes
            if item.kind.value == "edge"
            and item.geometry_type == "CIRCLE"
            and item.axis_origin is not None
            and item.radius is not None
        )
        assert edge.axis_origin is not None and edge.radius is not None
        anchor = self.service.exact_snap_anchor(
            self.exact,
            edge.axis_origin,
            allowed=(SnapType.CENTER,),
            tolerance_mm=0.01,
        )
        assert anchor is not None
        r = self.service.add_radius(anchor)
        d = self.service.add_diameter(anchor)
        self.assertAlmostEqual(edge.radius, r.value, places=9)
        self.assertAlmostEqual(edge.radius * 2.0, d.value, places=9)
        self.assertTrue(r.production_eligible)
        self.assertTrue(d.production_eligible)

    def test_measurement_state_is_exportable_and_restorable(self) -> None:
        edge = next(
            item
            for item in self.exact.snapshot.subshapes
            if item.kind.value == "edge"
            and item.geometry_type == "LINE"
            and item.start is not None
            and item.end is not None
            and item.measure > 100.0
        )
        assert edge.start is not None and edge.end is not None
        candidates = candidates_for_subshape(self.exact, edge.stable_id, edge.center)
        endpoints = [item for item in candidates if item.snap_type == SnapType.ENDPOINT]
        self.assertGreaterEqual(len(endpoints), 2)
        from cws_viewer.exact import anchor_from_candidate

        record = self.service.add_distance(
            anchor_from_candidate(self.exact, endpoints[0]),
            anchor_from_candidate(self.exact, endpoints[1]),
        )
        state = self.controller.export_workspace_state()
        self.assertEqual(record.measurement_id, state.measurements[0].measurement_id)
        self.controller.remove_measurement(record.measurement_id)
        self.assertEqual(0, len(self.controller.list_measurements()))
        self.controller.restore_workspace_state(state)
        self.assertEqual(record.measurement_id, self.controller.list_measurements()[0].measurement_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
