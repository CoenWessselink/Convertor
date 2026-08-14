from __future__ import annotations
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

import cadquery as cq
from cws_viewer.exact import (
    PolylinePlateDefinition,
    build_exact_runtime,
    build_polyline_plate,
    build_rounded_plate,
    build_slotted_plate,
)


class ViewerV6ContourFeatureTests(unittest.TestCase):
    def test_rounded_plate_retains_true_radii(self):
        runtime=build_exact_runtime(build_rounded_plate(radius=13.5),part_id='rounded')
        curves=[item for item in runtime.snapshot.subshapes if item.kind.value=='edge' and item.geometry_type in {'CIRCLE','ARC'}]
        self.assertGreaterEqual(len(curves),4)
        self.assertTrue(all(abs((item.radius or 0)-13.5)<1e-6 for item in curves))
        radii=[item for item in runtime.snapshot.features if item.feature_type=='contour_radii']
        self.assertEqual(1,len(radii))
        self.assertFalse(any(item.feature_type=='cylindrical_pocket' for item in runtime.snapshot.features))

    def test_through_slot_is_one_analytical_feature(self):
        runtime=build_exact_runtime(build_slotted_plate(),part_id='slot')
        slots=[item for item in runtime.snapshot.features if item.feature_type=='through_slot']
        self.assertEqual(1,len(slots),[item.to_dict() for item in runtime.snapshot.features])
        slot=slots[0]
        self.assertAlmostEqual(18.0,slot.diameter or 0,places=6)
        metadata=dict(slot.metadata)
        self.assertAlmostEqual(50.0,float(metadata['slot_length_mm']),places=6)
        self.assertAlmostEqual(12.0,slot.depth or 0,places=6)

    def test_self_intersecting_contour_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'kruist zichzelf'):
            PolylinePlateDefinition(((0,0),(100,100),(0,100),(100,0)),10)

    def test_valid_polyline_contour_builds_closed_solid(self):
        definition=PolylinePlateDefinition(((0,0),(120,0),(120,80),(60,110),(0,80)),8)
        runtime=build_exact_runtime(build_polyline_plate(definition),part_id='polygon')
        self.assertTrue(runtime.snapshot.properties.valid)
        self.assertEqual(1,runtime.snapshot.properties.solid_count)
        self.assertGreater(runtime.snapshot.properties.volume_mm3,0)


if __name__=='__main__': unittest.main(verbosity=2)
