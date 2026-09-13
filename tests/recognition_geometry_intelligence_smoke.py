"""Independent synthetic section oracles; native CAD absence is a failure.

All expected dimensions come from the explicit construction below, not the
recognizer. Source preservation and complete-region proofs are separate checks.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import math
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq
from cws_convertor.manufacturing_interpreter.contracts import AxisCandidate
from cws_convertor.manufacturing_interpreter.foundation import build_manufacturing_frame, build_sections_and_regions
from cws_convertor.manufacturing_interpreter.topology import analyze_topology, section_signature
from cws_convertor.manufacturing_interpreter.recognition_geometry import reference_section_faces
from cws_convertor.steel_model.tolerances import DEFAULT_TOLERANCE_POLICY as POLICY


def analyse(shape, direction=(0., 0., 1.), origin=(0., 0., 0.), length=1000.):
    topology, _ = analyze_topology(shape, POLICY)
    axis = AxisCandidate('independent-axis', direction, origin,
                         tuple(origin[i]+direction[i]*length for i in range(3)),
                         length, 'synthetic construction direction', 1.)
    base = section_signature(reference_section_faces(shape, axis), axis, topology)
    return build_sections_and_regions(shape, build_manufacturing_frame(axis), base,
                                      linear_mm=.05, area_relative=.001, topology=topology)


class ActualSectionTests(unittest.TestCase):
    def test_straight_prism_has_measured_sections_and_proven_regions(self):
        shape = cq.Solid.makeBox(20., 10., 1000.)
        stations, intervals, regions = analyse(shape)
        self.assertGreaterEqual(len(stations), 3)
        self.assertTrue(all(s.safe and abs(s.signature.area_mm2-200.) < 1e-5 for s in stations))
        self.assertTrue(intervals and all(i.invariant for i in intervals))
        self.assertTrue(regions)
        self.assertTrue(all(r.length_mm > 0 and 0 < r.source_coverage <= 1 for r in regions))

    def test_midspan_notch_is_not_a_copied_end_section(self):
        shape = cq.Solid.makeBox(20., 10., 1000.).cut(cq.Solid.makeBox(5., 10., 200., cq.Vector(15., 0., 400.)))
        stations, intervals, _ = analyse(shape)
        areas = [round(s.signature.area_mm2, 4) for s in stations if s.safe]
        self.assertIn(150., areas)
        self.assertIn(200., areas)
        self.assertTrue(any(not i.invariant for i in intervals))

    def test_taper_is_not_reported_as_constant_extrusion(self):
        shape = cq.Workplane('XY').rect(20., 10.).workplane(offset=1000.).rect(40., 10.).loft().val()
        stations, intervals, regions = analyse(shape)
        areas = [s.signature.area_mm2 for s in stations if s.safe]
        self.assertGreater(max(areas)-min(areas), 190.)
        self.assertTrue(all(not i.invariant for i in intervals))
        self.assertFalse(regions)

    def test_equal_area_moving_void_is_not_same_contour(self):
        outer = cq.Solid.makeBox(40., 30., 1000.)
        hole = cq.Solid.makeCylinder(3., 1000., cq.Vector(10., 15., 0.))
        other = cq.Solid.makeCylinder(3., 500., cq.Vector(25., 15., 500.))
        shape = outer.cut(hole).cut(other)
        stations, intervals, _ = analyse(shape)
        voids = {s.void_count for s in stations if s.safe}
        self.assertEqual({1, 2}, voids)
        self.assertTrue(any(not i.invariant for i in intervals))

    def test_do_not_filter_a_full_length_attached_strip(self):
        shape = cq.Solid.makeBox(20., 10., 1000.).fuse(cq.Solid.makeBox(5., 8., 1000., cq.Vector(20., 0., 0.)))
        stations, intervals, _ = analyse(shape)
        self.assertTrue(all(abs(s.signature.area_mm2-240.) < 1e-5 for s in stations))
        self.assertTrue(all(i.invariant for i in intervals))

    def test_actual_area_moments_not_bounding_box_estimates(self):
        shape = cq.Solid.makeBox(20., 10., 1000.)
        stations, _, _ = analyse(shape)
        moments = sorted(stations[0].moments[:2])
        self.assertAlmostEqual(200.*10.**2/12., moments[0], places=4)
        self.assertAlmostEqual(200.*20.**2/12., moments[1], places=4)

    def test_rotated_large_placement_preserves_measured_area_series(self):
        shape = cq.Solid.makeBox(20., 10., 1000.).cut(cq.Solid.makeBox(5., 10., 200., cq.Vector(15., 0., 400.)))
        reference = analyse(shape)
        rotation = cq.Location(cq.Vector(1e6, -2e6, 3e6), cq.Vector(1., 2., 3.), 37.)
        transformed = shape.located(rotation)
        origin = cq.Vertex.makeVertex(0.,0.,0.).located(rotation).Center().toTuple()
        end = cq.Vertex.makeVertex(0.,0.,1.).located(rotation).Center().toTuple()
        direction = tuple(end[i]-origin[i] for i in range(3))
        result = analyse(transformed, direction=direction, origin=origin)
        expected = sorted({round(s.signature.area_mm2, 3) for s in reference[0] if s.safe})
        actual = sorted({round(s.signature.area_mm2, 3) for s in result[0] if s.safe})
        self.assertEqual(expected, actual)

    def test_analysis_does_not_modify_source_shape(self):
        shape = cq.Solid.makeBox(20., 10., 1000.)
        before = (shape.Volume(),shape.Area(),len(shape.Faces()),tuple(v.Center().toTuple() for v in shape.Vertices()))
        analyse(shape)
        self.assertEqual(before,(shape.Volume(),shape.Area(),len(shape.Faces()),tuple(v.Center().toTuple() for v in shape.Vertices())))


if __name__ == '__main__':
    unittest.main(verbosity=2)
