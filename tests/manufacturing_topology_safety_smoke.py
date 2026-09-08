from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing_interpreter.contracts import (
    AxisCandidate,
    CrossSectionSignature,
    GeometryProofStatus,
)
from cws_convertor.manufacturing_interpreter.profiles import recognize_profile
from cws_convertor.manufacturing_interpreter.topology import (
    _edge_identity,
    find_end_faces,
    linear_tolerance,
    section_signature,
)


def _point(values):
    return SimpleNamespace(x=values[0], y=values[1], z=values[2])


class Edge:
    def __init__(self, start, end, *, kind="LINE", center=None, length=None, radius=1):
        self.start = start
        self.end = end
        self.kind = kind
        self.center = center or tuple((a + b) / 2 for a, b in zip(start, end))
        self.length = length if length is not None else math.dist(start, end)
        self.circle_radius = radius

    def startPoint(self):
        return _point(self.start)

    def endPoint(self):
        return _point(self.end)

    def Center(self):
        return _point(self.center)

    def Length(self):
        return self.length

    def geomType(self):
        return self.kind

    def radius(self):
        return self.circle_radius


class Face:
    def __init__(self, edges, area, center):
        self.edges = edges
        self.area = area
        self.center = center

    def outerWire(self):
        return SimpleNamespace(Edges=lambda: self.edges)

    def innerWires(self):
        return []

    def Area(self):
        return self.area

    def Center(self):
        return _point(self.center)

    def geomType(self):
        return "PLANE"

    def normalAt(self):
        return _point((0, 0, 1))


def _rectangle(x0, x1, y0, y1, z=0):
    points = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    return Face(
        [Edge(first, second) for first, second in zip(points, points[1:] + points[:1])],
        (x1 - x0) * (y1 - y0),
        ((x0 + x1) / 2, (y0 + y1) / 2, z),
    )


AXIS = AxisCandidate("axis", (0, 0, 1), (0, 0, 0), (0, 0, 1000), 1000, "test", 1)
POLICY = SimpleNamespace(linear_mm=0.05, relative=0.001)


def _signature(**overrides):
    value = CrossSectionSignature("section", "face", 1000, 220, 100, 10, 4, 0, (("LINE", 4),), "B")
    return replace(value, **overrides)


def _definition(designation="PL100X10", **overrides):
    value = dict(designation=designation, profile_type="B", family="B", height=100, width=10, area_mm2=1000)
    value.update(overrides)
    return SimpleNamespace(**value)


def _recognize(section, *definitions):
    return recognize_profile(section, SimpleNamespace(profiles=definitions), POLICY)


class ProfileSafetySmoke(unittest.TestCase):
    def test_known_rectangle_remains_recognized(self):
        result = _recognize(_signature(), _definition())
        self.assertEqual(result.status, GeometryProofStatus.PROVEN_WITHIN_POLICY)
        self.assertEqual(result.designation, "PL100X10")

    def test_custom_union_cannot_be_proven_by_bbox_and_area(self):
        for count in (1, 2, 3):
            with self.subTest(component_count=count):
                result = _recognize(_signature(inferred_family="CUSTOM", component_count=count), _definition())
                self.assertEqual(result.status, GeometryProofStatus.RECOGNITION_INCOMPLETE)
                self.assertEqual(result.designation, "")

    def test_missing_or_nonfinite_catalogue_area_never_matches(self):
        for area in (0, float("nan"), float("inf")):
            with self.subTest(area=area):
                result = _recognize(_signature(), _definition(area_mm2=area))
                self.assertEqual(result.status, GeometryProofStatus.RECOGNITION_INCOMPLETE)

    def test_invalid_observation_never_matches(self):
        for field in ("width_mm", "height_mm", "area_mm2"):
            for value in (0, -1, float("nan"), float("inf")):
                with self.subTest(field=field, value=value):
                    result = _recognize(_signature(**{field: value}), _definition())
                    self.assertEqual(result.status, GeometryProofStatus.RECOGNITION_INCOMPLETE)

    def test_two_within_policy_candidates_remain_ambiguous_without_score_tie(self):
        result = _recognize(_signature(), _definition("A"), _definition("B", width=10.001, area_mm2=1000.1))
        self.assertEqual(result.status, GeometryProofStatus.AMBIGUOUS)
        self.assertEqual(result.candidates, ("A", "B"))
        self.assertEqual(result.designation, "")

    def test_nonfinite_policy_cannot_allow_any_geometry(self):
        self.assertEqual(linear_tolerance(SimpleNamespace(linear_mm=float("inf"))), 0.05)


class TopologySafetySmoke(unittest.TestCase):
    def _topology(self, *faces):
        return SimpleNamespace(faces=tuple(SimpleNamespace(face_id=f"face-{i}", centroid_mm=face.center) for i, face in enumerate(faces)))

    def test_all_low_coplanar_faces_selected_but_not_high_end(self):
        left = _rectangle(0, 50, 0, 10)
        right = _rectangle(50, 100, 0, 10)
        high = _rectangle(0, 100, 0, 10, 1000)
        shape = SimpleNamespace(Faces=lambda: [high, right, left])
        self.assertEqual(find_end_faces(shape, AXIS), (left, right))
        signature = section_signature((left, right), AXIS, self._topology(left, right, high))
        self.assertEqual(signature.area_mm2, 1000)
        self.assertEqual((signature.width_mm, signature.height_mm), (100, 10))
        self.assertEqual(signature.perimeter_mm, 220)
        self.assertEqual(signature.component_count, 2)
        self.assertEqual(len(signature.supporting_face_ids), 2)

    def test_opposite_equal_length_arcs_are_not_shared_seams(self):
        first = Edge((-1, 0, 0), (1, 0, 0), kind="CIRCLE", center=(0, 0.6, 0), length=math.pi)
        second = Edge((1, 0, 0), (-1, 0, 0), kind="CIRCLE", center=(0, -0.6, 0), length=math.pi)
        self.assertNotEqual(_edge_identity(first, 1e-6), _edge_identity(second, 1e-6))

    def test_corner_radius_does_not_replace_section_dimensions(self):
        edges = [
            Edge((0, 0, 0), (99, 0, 0)),
            Edge((99, 0, 0), (100, 1, 0), kind="CIRCLE", radius=1),
            Edge((100, 1, 0), (100, 10, 0)),
            Edge((100, 10, 0), (0, 10, 0)),
            Edge((0, 10, 0), (0, 0, 0)),
        ]
        face = Face(edges, 999.7, (50, 5, 0))
        signature = section_signature(face, AXIS, self._topology(face))
        self.assertEqual((signature.width_mm, signature.height_mm), (100, 10))
        self.assertEqual(signature.inferred_family, "CUSTOM")

    def test_ellipse_is_not_round_bar(self):
        edge = Edge((20, 0, 0), (20, 0, 0), kind="ELLIPSE", center=(0, 0, 0), length=100)
        face = Face([edge], 600, (0, 0, 0))
        signature = section_signature(face, AXIS, self._topology(face))
        self.assertEqual(signature.inferred_family, "CUSTOM")


if __name__ == "__main__":
    unittest.main()
