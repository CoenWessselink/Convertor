from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.math3d import Vector3
from cws_viewer.measurements import (
    ExactMeasurementAnchor, MeasurementCollection, MeasurementProof,
    MeasurementSettings, SnapType, angle_three_points, diameter, distance,
    scalar_record,
)


def anchor(point: Vector3, *, proof=MeasurementProof.ANALYTICAL_BREP, node="part:1", geometry="a" * 64, analytical=()):
    return ExactMeasurementAnchor(
        node_id=node, entity_id="part-1", world_point=point,
        geometry_hash=geometry, snap_type=SnapType.VERTEX, proof=proof,
        analytical_data=tuple(analytical),
    )


class ViewerV5MeasurementTests(unittest.TestCase):
    def test_exact_distance_angle_and_diameter(self) -> None:
        settings = MeasurementSettings(precision=3)
        first = anchor(Vector3(0, 0, 0))
        second = anchor(Vector3(3, 4, 12))
        self.assertAlmostEqual(13.0, distance(first, second, settings).value, places=9)
        angle = angle_three_points(
            anchor(Vector3(1, 0, 0)), anchor(Vector3.zero()), anchor(Vector3(0, 1, 0)), settings
        )
        self.assertAlmostEqual(90.0, angle.value, places=9)
        circle = anchor(Vector3.zero(), analytical=(("radius", 9.0),))
        self.assertEqual(18.0, diameter(circle, settings).value)

    def test_display_proxy_cannot_supply_exact_volume(self) -> None:
        proxy = anchor(Vector3.zero(), proof=MeasurementProof.DISPLAY_PROXY)
        with self.assertRaises(ValueError):
            scalar_record("volume", 1000.0, "mm3", (proxy,), production_value=True)

    def test_geometry_hash_change_invalidates_measurement(self) -> None:
        first = anchor(Vector3.zero(), geometry="1" * 64)
        second = anchor(Vector3(10, 0, 0), geometry="1" * 64)
        collection = MeasurementCollection()
        record = collection.add(distance(first, second))
        invalidated = collection.invalidate_for_geometry({"part:1": "2" * 64})
        self.assertEqual((record.measurement_id,), invalidated)
        self.assertEqual("invalidated", collection.records[record.measurement_id].status.value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
