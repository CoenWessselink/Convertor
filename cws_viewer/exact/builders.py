"""Deterministic canonical BREP builders used by Exact Part Workbench tests.

These builders are intentionally explicit and support only proven feature
classes. Unsupported operations must remain blocked instead of being silently
approximated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cws_viewer.math3d import Vector3


@dataclass(frozen=True, slots=True)
class RoundHole:
    center_x: float
    center_y: float
    diameter: float

    def __post_init__(self) -> None:
        if self.diameter <= 0:
            raise ValueError("Gatdiameter moet positief zijn")


@dataclass(frozen=True, slots=True)
class PlateDefinition:
    length_x: float
    width_y: float
    thickness_z: float
    holes: tuple[RoundHole, ...] = ()

    def __post_init__(self) -> None:
        if min(self.length_x, self.width_y, self.thickness_z) <= 0:
            raise ValueError("Plaatafmetingen moeten positief zijn")
        object.__setattr__(self, "holes", tuple(self.holes))
        for hole in self.holes:
            radius = hole.diameter * 0.5
            if not (radius < hole.center_x < self.length_x - radius and radius < hole.center_y < self.width_y - radius):
                raise ValueError("Gat ligt niet volledig binnen de plaat")


def build_plate(definition: PlateDefinition):
    import cadquery as cq

    result = cq.Solid.makeBox(definition.length_x, definition.width_y, definition.thickness_z)
    for hole in definition.holes:
        cutter = cq.Solid.makeCylinder(
            hole.diameter * 0.5,
            definition.thickness_z,
            cq.Vector(hole.center_x, hole.center_y, 0.0),
            cq.Vector(0.0, 0.0, 1.0),
        )
        result = result.cut(cutter)
    return result.clean()


def build_round_bar(length: float, diameter: float, *, origin: Vector3 = Vector3.zero(), axis: Vector3 = Vector3(1, 0, 0)):
    import cadquery as cq

    if length <= 0 or diameter <= 0:
        raise ValueError("Rondstaaflengte en diameter moeten positief zijn")
    direction = axis.normalized()
    return cq.Solid.makeCylinder(
        diameter * 0.5,
        length,
        cq.Vector(origin.x, origin.y, origin.z),
        cq.Vector(direction.x, direction.y, direction.z),
    )


def p1811_definition(*, changed_hole_diameter: float | None = None) -> PlateDefinition:
    diameters = [18.0, 18.0, 18.0, 18.0]
    if changed_hole_diameter is not None:
        diameters[0] = float(changed_hole_diameter)
    centers = ((31.5, 35.0), (91.5, 35.0), (31.5, 95.0), (91.5, 95.0))
    return PlateDefinition(
        length_x=123.0,
        width_y=130.0,
        thickness_z=10.0,
        holes=tuple(RoundHole(x, y, diameter) for (x, y), diameter in zip(centers, diameters)),
    )


__all__ = ["RoundHole", "PlateDefinition", "build_plate", "build_round_bar", "p1811_definition"]

@dataclass(frozen=True, slots=True)
class PolylinePlateDefinition:
    points: tuple[tuple[float, float], ...]
    thickness_z: float
    holes: tuple[RoundHole, ...] = ()

    def __post_init__(self) -> None:
        points = tuple((float(x), float(y)) for x, y in self.points)
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "holes", tuple(self.holes))
        if self.thickness_z <= 0:
            raise ValueError("Plaatrekking moet positief zijn")
        if len(points) < 3:
            raise ValueError("Contour vereist minimaal drie punten")
        if points[0] == points[-1]:
            points = points[:-1]
            object.__setattr__(self, "points", points)
        for index in range(len(points)):
            if points[index] == points[(index + 1) % len(points)]:
                raise ValueError("Contour bevat een segment met nul lengte")
        if _polygon_self_intersects(points):
            raise ValueError("Contour kruist zichzelf")
        area = abs(_polygon_area(points))
        if area <= 1e-9:
            raise ValueError("Contouroppervlak is nul")


def _polygon_area(points: tuple[tuple[float, float], ...]) -> float:
    return 0.5 * sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )


def _orientation(a, b, c, tolerance=1e-12):
    value = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if abs(value) <= tolerance:
        return 0
    return 1 if value > 0 else 2


def _segments_intersect(a, b, c, d) -> bool:
    o1, o2, o3, o4 = _orientation(a, b, c), _orientation(a, b, d), _orientation(c, d, a), _orientation(c, d, b)
    return o1 != o2 and o3 != o4 and 0 not in {o1, o2, o3, o4}


def _polygon_self_intersects(points: tuple[tuple[float, float], ...]) -> bool:
    count = len(points)
    for first in range(count):
        a, b = points[first], points[(first + 1) % count]
        for second in range(first + 1, count):
            if second in {first, (first + 1) % count} or first in {second, (second + 1) % count}:
                continue
            if first == 0 and second == count - 1:
                continue
            c, d = points[second], points[(second + 1) % count]
            if _segments_intersect(a, b, c, d):
                return True
    return False


def build_polyline_plate(definition: PolylinePlateDefinition):
    import cadquery as cq

    wire = cq.Workplane("XY").moveTo(*definition.points[0]).polyline(definition.points[1:]).close()
    result = wire.extrude(float(definition.thickness_z))
    for hole in definition.holes:
        cutter = cq.Solid.makeCylinder(
            hole.diameter * 0.5,
            definition.thickness_z,
            cq.Vector(hole.center_x, hole.center_y, 0.0),
            cq.Vector(0.0, 0.0, 1.0),
        )
        result = result.cut(cutter)
    return result.val().clean()


def build_rounded_plate(
    *,
    length_x: float = 160.0,
    width_y: float = 120.0,
    thickness_z: float = 8.0,
    radius: float = 13.5,
):
    import cadquery as cq

    if radius <= 0 or radius >= min(length_x, width_y) * 0.5:
        raise ValueError("Ongeldige hoekradius")
    return (
        cq.Workplane("XY")
        .box(float(length_x), float(width_y), float(thickness_z), centered=(False, False, False))
        .edges("|Z")
        .fillet(float(radius))
        .val()
    )


def build_slotted_plate(
    *,
    length_x: float = 180.0,
    width_y: float = 120.0,
    thickness_z: float = 12.0,
    slot_center: tuple[float, float] = (70.0, 60.0),
    slot_length: float = 50.0,
    slot_width: float = 18.0,
):
    import cadquery as cq

    plate = cq.Workplane("XY").box(length_x, width_y, thickness_z, centered=(False, False, False))
    slot = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .center(*slot_center)
        .slot2D(slot_length, slot_width)
        .extrude(thickness_z + 2.0)
    )
    return plate.cut(slot).val().clean()


__all__ += [
    "PolylinePlateDefinition",
    "build_polyline_plate",
    "build_rounded_plate",
    "build_slotted_plate",
]
