from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.contracts.enums import MeasurementKind
from cws_viewer.contracts.state import ClippingBox, SectionPlane
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import BoundingBox, Vector3
from cws_viewer.measurements import (
    ExactMeasurementAnchor,
    MeasurementProof,
    MeasurementSettings,
    SnapType,
    distance,
)


class ViewerV9DisplayToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scene = build_synthetic_product_scene(200, parts_per_assembly=100)
        self.backend = MemoryRenderBackend()
        self.controller = ViewerCoreController(self.backend, width=960, height=640)
        self.controller.load_scene(self.scene)

    def tearDown(self) -> None:
        self.controller.shutdown()

    def _anchor(self, node_id: str) -> ExactMeasurementAnchor:
        node = self.controller.index.node(node_id)
        return ExactMeasurementAnchor(
            node_id=node_id,
            entity_id=node.entity_id,
            source_entity_id=node.source_entity_id or "",
            world_point=self.controller.index.world_bounds_by_node[node_id].center,
            local_point=node.local_bounds.center,
            geometry_hash=node.geometry_hash,
            snap_type=SnapType.CENTER,
            proof=MeasurementProof.VERIFIED_MESH,
        )

    def test_sections_clipping_explode_measurements_persist_and_do_not_change_scene(self) -> None:
        before_hash = self.scene.scene_hash
        before_geometry = {
            node.node_id: (node.geometry_hash, node.manufacturing_hash, node.transform)
            for node in self.scene.nodes
        }

        plane_id = self.controller.add_section_plane(
            SectionPlane(origin=Vector3(500, 500, 0), normal=Vector3(1, 0, 0))
        )
        self.controller.set_clipping_box(
            ClippingBox(BoundingBox(Vector3(0, 0, -50), Vector3(1500, 1500, 100)))
        )
        exploded = self.controller.explode(("node:assembly:0001",), 75.0)
        self.assertEqual(100, len(exploded))
        self.controller.begin_measurement(MeasurementKind.DISTANCE)
        record = self.controller.add_measurement(
            distance(self._anchor("node:item:000100"), self._anchor("node:item:000101"))
        )
        self.controller.set_measurement_settings(
            MeasurementSettings(length_unit="mm", precision=4, trailing_zeroes=True)
        )

        state = self.controller.export_workspace_state()
        self.assertEqual((plane_id,), tuple(item.plane_id for item in state.section_planes))
        self.assertEqual(100, len(state.explode_offsets_by_node))
        self.assertEqual((record.measurement_id,), tuple(item.measurement_id for item in state.measurements))
        self.assertEqual(4, state.measurement_settings.precision)

        with tempfile.TemporaryDirectory(prefix="cws-v9-display-tools-") as temp:
            path = Path(temp) / "project.cwsview.json"
            self.controller.save_workspace(path)
            payload = path.read_text(encoding="utf-8")
            self.assertIn('"explode_offsets"', payload)
            self.assertIn('"measurements"', payload)
            self.assertIn('"measurement_settings"', payload)

            self.controller.reset_explode()
            self.controller.remove_section_plane(plane_id)
            self.controller.set_clipping_box(None)
            self.controller.remove_measurement(record.measurement_id)
            report = self.controller.load_workspace(path)

        self.assertEqual(100, report.explode_offsets_restored)
        self.assertEqual(1, report.measurements_restored)
        self.assertEqual(0, report.measurements_invalidated)
        self.assertEqual(100, len(self.controller.session.explode_offsets))
        self.assertEqual(1, len(self.controller.list_measurements()))
        self.assertEqual(4, self.controller.get_measurement_settings().precision)
        self.assertEqual(before_hash, self.controller.scene.scene_hash)
        self.assertEqual(
            before_geometry,
            {
                node.node_id: (node.geometry_hash, node.manufacturing_hash, node.transform)
                for node in self.controller.scene.nodes
            },
        )

    def test_measurement_changes_participate_in_viewer_undo_redo(self) -> None:
        record = distance(self._anchor("node:item:000000"), self._anchor("node:item:000001"))
        self.controller.add_measurement(record)
        self.assertEqual(1, len(self.controller.list_measurements()))
        self.assertTrue(self.controller.undo_viewer())
        self.assertEqual(0, len(self.controller.list_measurements()))
        self.assertTrue(self.controller.redo_viewer())
        self.assertEqual((record.measurement_id,), tuple(item.measurement_id for item in self.controller.list_measurements()))

    def test_geometry_change_invalidates_restored_measurement_instead_of_dropping_it(self) -> None:
        record = self.controller.add_measurement(
            distance(self._anchor("node:item:000010"), self._anchor("node:item:000011"))
        )
        state = self.controller.export_workspace_state()
        replacement = build_synthetic_product_scene(200, parts_per_assembly=100, revision_id="V9-B")
        # Deliberately modify the geometry hash of one stable node.
        from dataclasses import replace
        nodes = tuple(
            replace(node, geometry_hash="f" * 64)
            if node.node_id == "node:item:000010"
            else node
            for node in replacement.nodes
        )
        replacement = replacement.create(
            project_id=replacement.project_id,
            revision_id=replacement.revision_id,
            models=replacement.models,
            nodes=nodes,
            geometry=replacement.geometry,
            styles=replacement.styles,
        )
        from cws_viewer.contracts.state import ScenePatch
        self.controller.update_scene(
            ScenePatch(
                expected_scene_hash=self.scene.scene_hash,
                replacement_scene=replacement,
                reason="V9 measurement invalidation",
            )
        )
        report = self.controller.restore_workspace_state(state, allow_scene_mismatch=True)
        self.assertEqual(1, report.measurements_restored)
        self.assertEqual(1, report.measurements_invalidated)
        restored = self.controller.list_measurements()[0]
        self.assertEqual(record.measurement_id, restored.measurement_id)
        self.assertEqual("invalidated", restored.status.value)
        self.assertIn("geometry hash gewijzigd", restored.invalid_reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
