"""Independent synthetic regressions for the existing MGI pipeline.

Expected dimensions are fixture design parameters, never recognizer outputs.
These cases do not certify supplier files, steel grades or machine operation.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import math
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq
from cws_convertor.manufacturing_interpreter.contracts import (
    CrossSectionSignature, ManufacturingFrame, SourceTopologyEvidence,
)
from cws_convertor.manufacturing_interpreter.foundation import build_sections_and_regions

FRAME = ManufacturingFrame('analytic-x', (0, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0))
BASE = CrossSectionSignature('independent-rectangle', '', 300, 80, 30, 10, 4, 0,
                             (('LINE', 4),), 'B')
TOPOLOGY = SourceTopologyEvidence('fixture', 1, (), (), ())


def sample(shape, frame=FRAME, base=BASE):
    return build_sections_and_regions(shape, frame, base, linear_mm=0.05,
                                     area_relative=0.001, topology=TOPOLOGY)


class MeasuredSectionTests(unittest.TestCase):
    def test_plain_extrusion_actual_area_and_moments(self):
        stations, intervals, regions = sample(cq.Workplane('YZ').rect(30, 10).extrude(200).val())
        self.assertGreaterEqual(len(stations), 3)
        for station in stations:
            self.assertTrue(station.safe)
            self.assertAlmostEqual(station.signature.area_mm2, 300, places=6)
            self.assertAlmostEqual(station.moments[0], 2500, places=4)
            self.assertAlmostEqual(station.moments[1], 22500, places=4)
        self.assertTrue(all(item.invariant for item in intervals))
        self.assertTrue(regions)
        self.assertLessEqual(sum(r.source_coverage for r in regions), 1.0)

    def test_taper_cannot_repeat_reference_section(self):
        shape = cq.Workplane('YZ').rect(30, 10).workplane(offset=200).rect(20, 10).loft().val()
        stations, intervals, regions = sample(shape)
        for station in stations:
            self.assertAlmostEqual(station.signature.area_mm2,
                                   300 - station.position_mm * 0.5, places=4)
        self.assertTrue(any(not item.invariant for item in intervals))
        self.assertFalse(regions)

    def test_local_hole_changes_measured_sections(self):
        shape = cq.Workplane('YZ').rect(30, 10).extrude(200).val()
        tool = cq.Workplane('XY').center(60, 0).circle(4).extrude(30, both=True).val()
        stations, intervals, _ = sample(shape.cut(tool))
        self.assertLess(min(s.signature.area_mm2 for s in stations if s.safe), 290)
        self.assertTrue(any(not item.invariant for item in intervals))

    def test_full_length_strip_is_not_filtered_out(self):
        base = cq.Workplane('YZ').rect(30, 10).extrude(200).val()
        strip = cq.Workplane('YZ').center(0, 7.5).rect(5, 5).extrude(200).val()
        stations, _, _ = sample(base.fuse(strip))
        self.assertTrue(stations)
        for station in stations:
            self.assertAlmostEqual(station.signature.area_mm2, 325, places=5)

    def test_equal_area_shift_is_not_constant_extrusion(self):
        shape = (cq.Workplane('YZ').rect(30, 10).workplane(offset=200)
                 .center(15, 0).rect(30, 10).loft().val())
        stations, intervals, regions = sample(shape)
        self.assertTrue(any(not i.invariant for i in intervals))
        self.assertFalse(regions)
        self.assertGreater(max(s.centroid_2d_mm[0] for s in stations)
                           - min(s.centroid_2d_mm[0] for s in stations), 10)

    def test_missing_geometry_never_copies_valid_reference(self):
        stations, intervals, regions = sample(None)
        self.assertFalse(any(s.safe for s in stations))
        self.assertFalse(any(i.invariant for i in intervals))
        self.assertFalse(regions)

    def test_rotation_and_large_placement_preserve_measurement(self):
        shape = cq.Workplane('YZ').rect(30, 10).extrude(200).val()
        rotation = cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 2, 3), 37)
        translation = cq.Location(cq.Vector(1e6, -2e6, 3e6))
        placement = translation * rotation
        moved = shape.moved(placement)
        def rotate_vector(value):
            return cq.Vertex.makeVertex(*value).moved(rotation).Center().toTuple()
        origin = cq.Vertex.makeVertex(0, 0, 0).moved(placement).Center().toTuple()
        frame = replace(FRAME, origin_mm=origin, x_axis=rotate_vector(FRAME.x_axis),
                        y_axis=rotate_vector(FRAME.y_axis), z_axis=rotate_vector(FRAME.z_axis))
        stations, intervals, _ = sample(moved, frame)
        self.assertTrue(stations)
        self.assertTrue(all(s.safe for s in stations))
        for station in stations:
            self.assertAlmostEqual(station.signature.area_mm2, 300, places=4)
        self.assertTrue(all(i.invariant for i in intervals))


if __name__ == '__main__':
    unittest.main(verbosity=2)
