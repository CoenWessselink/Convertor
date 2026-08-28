"""DSTV/NC1 ↔ STEP conversiekern, prototype v0.1."""
from __future__ import annotations

from cws_convertor.product import APP_NAME, APP_VERSION

__version__ = APP_VERSION

from dataclasses import dataclass, field
from pathlib import Path
import math
import re
from typing import Iterable

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.TopoDS import TopoDS

BLOCK_RE = re.compile(r"^(ST|EN|BO|SI|AK|IK|PU|KO|SC|TO|UE|PR|KA|IN|E[0-9]|B[0-9]|A[0-9]|I[0-9]|P[0-9]|K[0-9]|S[0-9])$")
NUMBER_TOKEN_RE = re.compile(
    r"^([+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[Ee][+-]?\d+)?)([A-Za-z]?)$"
)


def _float(text: str, default: float = 0.0) -> float:
    text = text.strip().replace(',', '.')
    if not text:
        return default
    return float(text)


def _block_name(line: str) -> str:
    """Return a DSTV block name only when it starts in column zero.

    Header values are indented and may legitimately equal ``P8`` or ``A1``.
    Stripping before block detection therefore truncated valid headers.
    """

    if not line or line[0].isspace():
        return ""
    token = line.strip()
    return token if BLOCK_RE.fullmatch(token) else ""


def _number_with_suffix(text: str, allowed_suffixes: str = "") -> tuple[float, str]:
    """Parse a DSTV number with an optional attached datum/operation code."""

    token = text.strip()
    match = NUMBER_TOKEN_RE.fullmatch(token)
    if not match:
        raise ValueError(f"ongeldig DSTV-getal: {text!r}")
    suffix = match.group(2).lower()
    if suffix and suffix not in allowed_suffixes:
        raise ValueError(f"onbekende DSTV-code '{suffix}' in {text!r}")
    return float(match.group(1).replace(",", ".")), suffix


@dataclass
class Header:
    order_number: str
    drawing_number: str
    part_number: str
    position_number: str
    material: str
    quantity: int
    profile: str
    profile_type: str
    length: float
    saw_length: float
    dim1: float
    dim2: float
    dim3: float
    dim4: float
    radius: float
    weight: float
    paint_area: float
    web_miter_front: float
    web_miter_rear: float
    flange_miter_front: float
    flange_miter_rear: float
    info: list[str] = field(default_factory=list)

    @property
    def plate_thickness(self) -> float:
        candidates = [self.dim2, self.dim3, self.dim4]
        positive = [v for v in candidates if v > 0]
        return min(positive) if positive else 0.0


@dataclass
class ContourPoint:
    x: float
    q: float
    datum: str = ""
    notch: str = ""
    radius: float = 0.0
    weld: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class Contour:
    kind: str
    face: str
    points: list[ContourPoint]

    @property
    def geometry_points(self) -> list[ContourPoint]:
        # Lines marked t/w are DSTV notch-information lines, not contour vertices.
        return [p for p in self.points if p.notch not in {"t", "w"}]


@dataclass
class Hole:
    face: str
    x: float
    q: float
    diameter: float
    datum: str = ""
    operation: str = ""
    depth: float = 0.0
    slot_length: float = 0.0
    angle_deg: float = 0.0


@dataclass
class Numbering:
    """DSTV SI numbering / hardstamp record (7th edition, July 1998)."""

    face: str
    x: float
    q: float
    angle_deg: float
    text_height_mm: int
    text: str
    datum: str = ""
    turn_behavior: str = ""


@dataclass
class SurfaceMark:
    """One DSTV PU/KO mark contour in a standard part face."""

    kind: str
    face: str
    points: list[ContourPoint]


@dataclass
class NC1Part:
    source: Path
    header: Header
    contours: list[Contour]
    holes: list[Hole]
    numberings: list[Numbering] = field(default_factory=list)
    surface_marks: list[SurfaceMark] = field(default_factory=list)
    unsupported_blocks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def contours_for(self, face: str, kind: str = "AK") -> list[Contour]:
        return [c for c in self.contours if c.face == face and c.kind == kind]


class NC1ParseError(ValueError):
    pass


def parse_nc1(path: str | Path) -> NC1Part:
    path = Path(path)
    lines = path.read_text(encoding="ascii", errors="replace").splitlines()
    try:
        st_idx = next(i for i, line in enumerate(lines) if line.strip() == "ST")
    except StopIteration as exc:
        raise NC1ParseError(f"Geen ST-blok gevonden in {path.name}") from exc

    i = st_idx + 1
    while i < len(lines) and lines[i].lstrip().startswith("**"):
        i += 1

    header_lines: list[str] = []
    while i < len(lines):
        if _block_name(lines[i]):
            break
        header_lines.append(lines[i])
        i += 1

    values = [line.strip() for line in header_lines if line.strip()]
    if len(values) < 20:
        raise NC1ParseError(
            f"Onvolledige kopgegevens in {path.name}: {len(values)} velden, minimaal 20 verwacht"
        )

    length_bits = [bit.strip() for bit in values[8].split(",", 1)]
    length = _float(length_bits[0])
    saw_length = _float(length_bits[1], length) if len(length_bits) > 1 else length

    header = Header(
        order_number=values[0],
        drawing_number=values[1],
        part_number=values[2],
        position_number=values[3],
        material=values[4],
        quantity=int(float(values[5])),
        profile=values[6],
        profile_type=values[7].upper(),
        length=length,
        saw_length=saw_length,
        dim1=_float(values[9]),
        dim2=_float(values[10]),
        dim3=_float(values[11]),
        dim4=_float(values[12]),
        radius=_float(values[13]),
        weight=_float(values[14]),
        paint_area=_float(values[15]),
        web_miter_front=_float(values[16]),
        web_miter_rear=_float(values[17]),
        flange_miter_front=_float(values[18]),
        flange_miter_rear=_float(values[19]),
        info=values[20:],
    )

    contours: list[Contour] = []
    holes: list[Hole] = []
    numberings: list[Numbering] = []
    surface_marks: list[SurfaceMark] = []
    unsupported: list[str] = []
    warnings: list[str] = []

    while i < len(lines):
        block = _block_name(lines[i])
        if not lines[i].strip():
            i += 1
            continue
        if block == "EN":
            break
        if not block:
            warnings.append(f"Onverwachte regel buiten blok op regel {i + 1}: {lines[i]!r}")
            i += 1
            continue

        i += 1
        data: list[str] = []
        while i < len(lines) and not _block_name(lines[i]):
            if lines[i].strip() and not lines[i].lstrip().startswith("**"):
                data.append(lines[i])
            i += 1

        if block in {"AK", "IK"}:
            current_face = ""
            pts: list[ContourPoint] = []
            for raw in data:
                fields = raw.split()
                face = fields[0].lower() if fields and fields[0].lower() in "vouh" else current_face
                if face:
                    current_face = face
                if not current_face:
                    warnings.append(f"Contour zonder vlak in {path.name}: {raw!r}")
                    continue
                try:
                    offset = 1 if fields and fields[0].lower() in "vouh" else 0
                    if len(fields) < offset + 2:
                        raise ValueError("onvoldoende contourvelden")
                    x, datum = _number_with_suffix(fields[offset], "osu")
                    q, notch = _number_with_suffix(fields[offset + 1], "tw")
                    remainder = fields[offset + 2 :]
                    radius = _float(remainder[0]) if remainder else 0.0
                    weld_values = [_float(value) for value in remainder[1:5]]
                    weld_values.extend([0.0] * (4 - len(weld_values)))
                    weld = tuple(weld_values[:4])
                    pts.append(ContourPoint(x, q, datum, notch, radius, weld))
                except ValueError as exc:
                    warnings.append(f"Contourregel niet gelezen in {path.name}: {raw!r} ({exc})")
            if pts:
                contours.append(Contour(block, current_face, pts))
        elif block == "BO":
            for raw in data:
                fields = raw.split()
                face = fields[0].lower() if fields and fields[0].lower() in "vouh" else ""
                if not face:
                    warnings.append(f"Boorgat zonder vlak in {path.name}: {raw!r}")
                    continue
                try:
                    if len(fields) < 4:
                        raise ValueError("onvoldoende boorgatvelden")
                    x, datum = _number_with_suffix(fields[1], "osu")
                    q, op = _number_with_suffix(fields[2], "glms")
                    diameter, diameter_op = _number_with_suffix(fields[3], "glms")
                    op = op or diameter_op
                    details = fields[4:]
                    depth = _float(details[0]) if op and details else 0.0
                    slot_length = _float(details[1]) if op == "l" and len(details) > 1 else 0.0
                    angle_deg = _float(details[-1]) if op and len(details) >= 4 else 0.0
                    holes.append(Hole(face, x, q, diameter, datum, op, depth, slot_length, angle_deg))
                except ValueError as exc:
                    warnings.append(f"Boorgatregel niet gelezen in {path.name}: {raw!r} ({exc})")
        elif block == "SI":
            number_re = re.compile(
                r"^\s*([vouh])\s*([-+]?\d+(?:[.,]\d+)?)\s*([osu]?)\s*"
                r"([-+]?\d+(?:[.,]\d+)?)\s+([-+]?\d+(?:[.,]\d+)?)\s+"
                r"(\d+)\s*(.*)$",
                re.I,
            )
            for raw in data:
                match = number_re.match(raw)
                if not match:
                    warnings.append(f"SI-regel niet gelezen in {path.name}: {raw!r}")
                    continue
                face, x, datum, q, angle, height, tail = match.groups()
                tail = tail.strip()
                behavior = ""
                text = tail
                bits = tail.split(None, 1)
                if bits and bits[0].lower() in {"r", "z"} and len(bits) > 1:
                    behavior = bits[0].lower()
                    text = bits[1]
                try:
                    numberings.append(
                        Numbering(
                            face.lower(),
                            _float(x),
                            _float(q),
                            _float(angle),
                            int(height),
                            text,
                            datum.lower(),
                            behavior,
                        )
                    )
                except ValueError as exc:
                    warnings.append(f"SI-regel niet gelezen in {path.name}: {raw!r} ({exc})")
        elif block in {"PU", "KO"}:
            current_face = ""
            points: list[ContourPoint] = []
            mark_re = re.compile(
                r"^\s*([vouh]?)\s*([-+]?\d+(?:[.,]\d+)?)\s*([osu]?)\s*"
                r"([-+]?\d+(?:[.,]\d+)?)\s+([-+]?\d+(?:[.,]\d+)?)",
                re.I,
            )
            for raw in data:
                match = mark_re.match(raw)
                if not match:
                    warnings.append(f"{block}-regel niet gelezen in {path.name}: {raw!r}")
                    continue
                face, x, datum, q, radius = match.groups()
                face = face.lower() or current_face
                if not face:
                    warnings.append(f"{block}-markering zonder vlak in {path.name}: {raw!r}")
                    continue
                current_face = face
                try:
                    points.append(ContourPoint(_float(x), _float(q), datum.lower(), "", _float(radius)))
                except ValueError as exc:
                    warnings.append(f"{block}-regel niet gelezen in {path.name}: {raw!r} ({exc})")
            if points:
                surface_marks.append(SurfaceMark(block, current_face, points))
        else:
            unsupported.append(block)

    if unsupported:
        warnings.append("Niet-ondersteunde DSTV-blokken aangetroffen: " + ", ".join(sorted(set(unsupported))))
    if any(contour.kind == "IK" for contour in contours):
        warnings.append("IK-binnencontouren worden wel gelezen maar nog niet in de 3D-solid verwerkt")

    return NC1Part(path, header, contours, holes, numberings, surface_marks, unsupported, warnings)


def _shape_wp(shape: cq.Shape) -> cq.Workplane:
    return cq.Workplane("XY").newObject([shape])


def _box(length: float, width: float, height: float, x=0.0, y=0.0, z=0.0) -> cq.Workplane:
    return cq.Workplane("XY").box(length, width, height, centered=(False, False, False)).translate((x, y, z))


def _cylinder(radius: float, height: float, start: tuple[float, float, float], direction: tuple[float, float, float]) -> cq.Workplane:
    solid = cq.Solid.makeCylinder(radius, height, cq.Vector(*start), cq.Vector(*direction))
    return _shape_wp(solid)


def _clean_poly_points(contour: Contour) -> list[tuple[float, float]]:
    pts = [(p.x, p.q) for p in contour.geometry_points]
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-7:
        pts.pop()
    # Remove immediately repeated points.
    cleaned: list[tuple[float, float]] = []
    for point in pts:
        if not cleaned or math.dist(cleaned[-1], point) > 1e-9:
            cleaned.append(point)
    return cleaned


def _rounded_vertex_geometry_2d(
    previous: tuple[float, float],
    current: tuple[float, float],
    following: tuple[float, float],
    radius: float,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], float] | None:
    """Return tangent-in, tangent-out, centre and signed arc extent.

    DSTV stores a corner radius on the vertex.  The old prototype ignored this
    and replaced every arc by a sharp corner.  The construction below keeps the
    analytical circular edge while capping an impossible radius to 45% of both
    adjacent segments.  That cap mirrors the drawing renderer and prevents
    self-intersecting fillets from malformed source data.
    """

    px, py = previous
    cx, cy = current
    nx, ny = following
    incoming = (px - cx, py - cy)
    outgoing = (nx - cx, ny - cy)
    lin = math.hypot(*incoming)
    lout = math.hypot(*outgoing)
    if radius <= 1e-9 or lin <= 1e-9 or lout <= 1e-9:
        return None
    incoming = (incoming[0] / lin, incoming[1] / lin)
    outgoing = (outgoing[0] / lout, outgoing[1] / lout)
    cosine = max(-1.0, min(1.0, incoming[0] * outgoing[0] + incoming[1] * outgoing[1]))
    angle = math.acos(cosine)
    if angle <= 1e-6 or abs(math.pi - angle) <= 1e-6:
        return None
    tangent_distance = radius / math.tan(angle / 2.0)
    tangent_distance = min(tangent_distance, lin * 0.45, lout * 0.45)
    if tangent_distance <= 1e-9:
        return None
    actual_radius = tangent_distance * math.tan(angle / 2.0)
    tangent_in = (cx + incoming[0] * tangent_distance, cy + incoming[1] * tangent_distance)
    tangent_out = (cx + outgoing[0] * tangent_distance, cy + outgoing[1] * tangent_distance)
    bisector = (incoming[0] + outgoing[0], incoming[1] + outgoing[1])
    bisector_length = math.hypot(*bisector)
    if bisector_length <= 1e-9:
        return None
    bisector = (bisector[0] / bisector_length, bisector[1] / bisector_length)
    centre_distance = actual_radius / math.sin(angle / 2.0)
    centre = (cx + bisector[0] * centre_distance, cy + bisector[1] * centre_distance)
    start_angle = math.atan2(tangent_in[1] - centre[1], tangent_in[0] - centre[0])
    end_angle = math.atan2(tangent_out[1] - centre[1], tangent_out[0] - centre[0])
    cross = (tangent_in[0] - centre[0]) * (tangent_out[1] - centre[1]) - (tangent_in[1] - centre[1]) * (tangent_out[0] - centre[0])
    if cross >= 0:
        extent = (end_angle - start_angle) % (2.0 * math.pi)
    else:
        extent = -((start_angle - end_angle) % (2.0 * math.pi))
    if abs(extent) > math.pi:
        extent = extent - 2.0 * math.pi if extent > 0 else extent + 2.0 * math.pi
    return tangent_in, tangent_out, centre, extent


def _contour_wire(contour: Contour) -> cq.Wire:
    """Build an exact planar wire from straight and radius-tagged DSTV points."""

    source_points = list(contour.geometry_points)
    if len(source_points) > 1 and math.dist(
        (source_points[0].x, source_points[0].q),
        (source_points[-1].x, source_points[-1].q),
    ) < 1e-7:
        source_points.pop()
    cleaned: list[ContourPoint] = []
    for point in source_points:
        if not cleaned or math.dist((cleaned[-1].x, cleaned[-1].q), (point.x, point.q)) > 1e-9:
            cleaned.append(point)
    if len(cleaned) < 3:
        raise ValueError(f"Contour {contour.kind}/{contour.face} heeft minder dan 3 geometriepunten")

    points = [(float(point.x), float(point.q)) for point in cleaned]
    rounded = [
        _rounded_vertex_geometry_2d(
            points[index - 1],
            points[index],
            points[(index + 1) % len(points)],
            max(0.0, float(cleaned[index].radius)),
        )
        for index in range(len(points))
    ]
    edges: list[cq.Edge] = []
    for index, current in enumerate(points):
        next_index = (index + 1) % len(points)
        start = rounded[index][1] if rounded[index] is not None else current
        end = rounded[next_index][0] if rounded[next_index] is not None else points[next_index]
        if math.dist(start, end) > 1e-8:
            edges.append(cq.Edge.makeLine(cq.Vector(start[0], start[1], 0.0), cq.Vector(end[0], end[1], 0.0)))
        next_round = rounded[next_index]
        if next_round is not None:
            tangent_in, tangent_out, centre, extent = next_round
            start_angle = math.atan2(tangent_in[1] - centre[1], tangent_in[0] - centre[0])
            radius = math.hypot(tangent_in[0] - centre[0], tangent_in[1] - centre[1])
            middle_angle = start_angle + extent / 2.0
            middle = (
                centre[0] + radius * math.cos(middle_angle),
                centre[1] + radius * math.sin(middle_angle),
            )
            edges.append(
                cq.Edge.makeThreePointArc(
                    cq.Vector(tangent_in[0], tangent_in[1], 0.0),
                    cq.Vector(middle[0], middle[1], 0.0),
                    cq.Vector(tangent_out[0], tangent_out[1], 0.0),
                )
            )
    wire = cq.Wire.assembleEdges(edges)
    if not wire.IsClosed() or not wire.isValid():
        raise ValueError(f"Contour {contour.kind}/{contour.face} kon niet als gesloten analytische wire worden opgebouwd")
    return wire


def _contour_mask(contour: Contour, span: float) -> cq.Workplane:
    pts = _clean_poly_points(contour)
    if len(pts) < 3:
        raise ValueError(f"Contour {contour.kind}/{contour.face} heeft minder dan 3 geometriepunten")
    if contour.face in {"v", "h"}:
        # XZ workplane extrudes in -Y for positive values. A negative extrusion covers Y=0..span.
        return cq.Workplane("XZ").polyline(pts).close().extrude(-span)
    if contour.face in {"o", "u"}:
        return cq.Workplane("XY").polyline(pts).close().extrude(span)
    raise ValueError(f"Onbekend DSTV-vlak: {contour.face}")


def _first_mask(part: NC1Part, face: str, span: float, fallback: cq.Workplane) -> cq.Workplane:
    contours = part.contours_for(face)
    if not contours:
        return fallback
    if len(contours) > 1:
        part.warnings.append(f"Meerdere AK-contouren voor vlak {face}; eerste contour gebruikt in prototype")
    contour = contours[0]
    if any(point.notch in {"t", "w"} or abs(point.radius) > 1e-9 for point in contour.points):
        warning = f"AK-contour {face} bevat boogradii/klinkinformatie; prototype benadert deze lokaal met rechte segmenten"
        if warning not in part.warnings:
            part.warnings.append(warning)
    try:
        return _contour_mask(contour, span)
    except Exception as exc:
        part.warnings.append(f"AK-contour {face} kon niet als solid worden opgebouwd: {exc}")
        return fallback


def _fillet_patch_x(length: float, y0: float, z0: float, radius: float, center_y: float, center_z: float) -> cq.Workplane:
    square = _box(length, radius, radius, 0.0, y0, z0)
    cutter = _cylinder(radius, length + 2.0, (-1.0, center_y, center_z), (1.0, 0.0, 0.0))
    return square.cut(cutter)


def _apply_holes(part: NC1Part, solid: cq.Workplane, profile_type: str, h: float, b: float, t1: float, t2: float) -> cq.Workplane:
    if profile_type == "M" and part.holes:
        raise NotImplementedError(
            "BO-gaten in holle M-profielen worden nog niet betrouwbaar per afzonderlijke wand verwerkt"
        )

    result = solid
    # Through holes are cut before countersinks so the latter only removes the
    # annular cone around the already existing bore.
    holes = sorted(part.holes, key=lambda item: bool(item.operation or item.depth > 0))
    unique_holes = []
    seen_holes: set[tuple[object, ...]] = set()
    for hole in holes:
        hole_key = (
            hole.face,
            round(hole.x, 6),
            round(hole.q, 6),
            round(hole.diameter, 6),
            hole.operation,
            round(hole.depth, 6),
            round(hole.slot_length, 6),
            round(hole.angle_deg, 6),
        )
        if hole_key in seen_holes:
            part.warnings.append(
                f"Dubbele BO-bewerking overgeslagen: Ø{hole.diameter:g} op "
                f"{hole.face} ({hole.x:g}, {hole.q:g})"
            )
            continue
        seen_holes.add(hole_key)
        unique_holes.append(hole)
    holes = unique_holes
    for hole in holes:
        if hole.diameter <= 0:
            raise ValueError(f"Ongeldige gatdiameter: {hole.diameter:g}")
        r = hole.diameter / 2.0
        expected_wall = 0.0
        try:
            origin = (hole.x, hole.q, -1.0)
            direction = (0.0, 0.0, 1.0)
            if profile_type == "B":
                if hole.face not in {"v", "h"}:
                    raise NotImplementedError("Randboringen in plaatdelen worden nog niet ondersteund")
                expected_wall = t1
                origin, direction = (hole.x, hole.q, -1.0), (0.0, 0.0, 1.0)
            elif profile_type == "I":
                web_y0 = (b - t2) / 2.0
                if hole.face in {"v", "h"}:
                    expected_wall = t2
                    origin, direction = (hole.x, web_y0 - 1.0, hole.q), (0.0, 1.0, 0.0)
                elif hole.face == "o":
                    expected_wall = t1
                    origin, direction = (hole.x, hole.q, h - t1 - 1.0), (0.0, 0.0, 1.0)
                elif hole.face == "u":
                    expected_wall = t1
                    origin, direction = (hole.x, hole.q, -1.0), (0.0, 0.0, 1.0)
                else:
                    raise NotImplementedError(f"Onbekend boorvlak voor I-profiel: {hole.face}")
            elif profile_type == "L":
                if hole.face in {"v", "h"}:
                    expected_wall = t2
                    origin, direction = (hole.x, -1.0, hole.q), (0.0, 1.0, 0.0)
                elif hole.face in {"o", "u"}:
                    expected_wall = t1
                    origin, direction = (hole.x, hole.q, -1.0), (0.0, 0.0, 1.0)
                else:
                    raise NotImplementedError(f"Onbekend boorvlak voor L-profiel: {hole.face}")
            else:
                raise NotImplementedError(f"Boorgaten voor profieltype {profile_type} worden nog niet ondersteund")

            if hole.operation == "s":
                depth = min(max(float(hole.depth), 0.1), expected_wall)
                paired = next(
                    (
                        candidate for candidate in holes
                        if not candidate.operation
                        and candidate.face == hole.face
                        and abs(candidate.x - hole.x) < 0.01
                        and abs(candidate.q - hole.q) < 0.01
                        and candidate.diameter < hole.diameter
                    ),
                    None,
                )
                inner_r = paired.diameter / 2.0 if paired is not None else max(0.1, r - depth)
                if hole.face == "o" and profile_type == "I":
                    cone_origin, cone_direction = (hole.x, hole.q, h + 0.01), (0.0, 0.0, -1.0)
                elif hole.face in {"o", "u"}:
                    cone_origin, cone_direction = (hole.x, hole.q, expected_wall + 0.01), (0.0, 0.0, -1.0)
                elif hole.face in {"v", "h"}:
                    cone_origin, cone_direction = (hole.x, -0.01, hole.q), (0.0, 1.0, 0.0)
                else:
                    raise NotImplementedError(f"Verzinking op DSTV-vlak {hole.face} wordt niet ondersteund")
                cone = cq.Solid.makeCone(
                    r,
                    inner_r,
                    depth + 0.02,
                    cq.Vector(*cone_origin),
                    cq.Vector(*cone_direction),
                )
                cutter = cq.Workplane("XY").newObject([cone])
            elif hole.operation == "l" and hole.slot_length > hole.diameter:
                half_run = (hole.slot_length - hole.diameter) / 2.0
                first = _cylinder(r, expected_wall + 2.0, origin, direction)
                shifted = (origin[0] + 2.0 * half_run, origin[1], origin[2])
                second = _cylinder(r, expected_wall + 2.0, shifted, direction)
                if direction[1]:
                    bridge = _box(2.0 * half_run, expected_wall + 2.0, 2.0 * r, origin[0], origin[1], origin[2] - r)
                else:
                    bridge = _box(2.0 * half_run, 2.0 * r, expected_wall + 2.0, origin[0], origin[1] - r, origin[2])
                cutter = first.union(second).union(bridge)
            elif hole.operation:
                raise NotImplementedError(
                    f"Speciale BO-bewerking '{hole.operation}' bij gat Ø{hole.diameter:g} wordt niet ondersteund"
                )
            else:
                cutter = _cylinder(r, expected_wall + 2.0, origin, direction)

            before = result.val().Volume()
            candidate = result.cut(cutter)
            removed = max(0.0, before - candidate.val().Volume())
            expected = math.pi * r * r * expected_wall if not hole.operation else max(removed, 1e-6)
            if removed <= max(1e-6, expected * 0.05):
                raise ValueError(
                    f"Boorgat Ø{hole.diameter:g} op {hole.face} snijdt het onderdeel niet of nauwelijks"
                )
            if expected > 0 and not (0.70 * expected <= removed <= 1.30 * expected):
                part.warnings.append(
                    f"Boorgat Ø{hole.diameter:g} op {hole.face}: verwijderd volume wijkt af; positie nabij rand/overgang controleren"
                )
            result = candidate
        except (NotImplementedError, ValueError):
            raise
        except Exception as exc:
            raise ValueError(f"Boorgat Ø{hole.diameter:g} op {hole.face} kon niet worden verwerkt: {exc}") from exc
    return result


def build_plate(part: NC1Part) -> cq.Workplane:
    h = part.header
    thickness = h.plate_thickness
    if h.length <= 0 or thickness <= 0:
        raise ValueError("Ongeldige plaatlengte of -dikte")
    contours = part.contours_for("v") or part.contours_for("o")
    if contours:
        contour = contours[0]
        try:
            wire = _contour_wire(contour)
            solid_shape = cq.Solid.extrudeLinear(wire, [], cq.Vector(0.0, 0.0, thickness))
            solid = cq.Workplane("XY").newObject([solid_shape])
        except Exception as exc:
            raise ValueError(f"Plaatcontour kon niet analytisch worden opgebouwd: {exc}") from exc
    else:
        pts = [(0.0, 0.0), (h.length, 0.0), (h.length, h.dim1), (0.0, h.dim1)]
        part.warnings.append("Geen AK-contour; omhullende rechthoek gebruikt")
        solid = cq.Workplane("XY").polyline(pts).close().extrude(thickness)
    inner_contours = part.contours_for("v", "IK") or part.contours_for("o", "IK")
    for contour in inner_contours:
        try:
            wire = _contour_wire(contour).translate(cq.Vector(0.0, 0.0, -1.0))
            cutter_shape = cq.Solid.extrudeLinear(
                wire,
                [],
                cq.Vector(0.0, 0.0, thickness + 2.0),
            )
            before = float(solid.val().Volume())
            solid = solid.cut(cq.Workplane("XY").newObject([cutter_shape]))
            if before - float(solid.val().Volume()) <= 1e-6:
                raise ValueError("binnencontour snijdt de plaat niet")
        except Exception as exc:
            raise ValueError(f"Plaat-binnencontour kon niet analytisch worden opgebouwd: {exc}") from exc
    return _apply_holes(part, solid, "B", h.dim1, h.length, thickness, thickness)


def build_i_profile(part: NC1Part) -> cq.Workplane:
    hd = part.header
    length, h, b, tf, tw, r = hd.length, hd.dim1, hd.dim2, hd.dim3, hd.dim4, hd.radius
    if min(length, h, b, tf, tw) <= 0 or h <= 2 * tf or b <= tw:
        raise ValueError("Ongeldige afmetingen voor I-profiel")
    web_y0 = (b - tw) / 2.0

    fallback = _box(length + 20.0, b + 20.0, h + 20.0, -10.0, -10.0, -10.0)
    vmask = _first_mask(part, "v", b, fallback)
    omask = _first_mask(part, "o", h, fallback)
    umask = _first_mask(part, "u", h, fallback)

    web = _box(length, tw, h, 0.0, web_y0, 0.0).intersect(vmask)
    top = _box(length, b, tf, 0.0, 0.0, h - tf).intersect(omask)
    bottom = _box(length, b, tf, 0.0, 0.0, 0.0).intersect(umask)
    result = web.union(top).union(bottom)

    if r > 0:
        # Four root fillets: square minus a quarter-cylinder, clipped by adjacent plate contours.
        top_z0 = h - tf
        bottom_z0 = tf
        patches = [
            (_fillet_patch_x(length, web_y0 - r, top_z0 - r, r, web_y0 - r, top_z0 - r), vmask, omask),
            (_fillet_patch_x(length, web_y0 + tw, top_z0 - r, r, web_y0 + tw + r, top_z0 - r), vmask, omask),
            (_fillet_patch_x(length, web_y0 - r, bottom_z0, r, web_y0 - r, bottom_z0 + r), vmask, umask),
            (_fillet_patch_x(length, web_y0 + tw, bottom_z0, r, web_y0 + tw + r, bottom_z0 + r), vmask, umask),
        ]
        for patch, mask1, mask2 in patches:
            try:
                result = result.union(patch.intersect(mask1).intersect(mask2))
            except Exception as exc:
                part.warnings.append(f"Walsradius gedeeltelijk overgeslagen: {exc}")

    return _apply_holes(part, result, "I", h, b, tf, tw)


def build_l_profile(part: NC1Part) -> cq.Workplane:
    hd = part.header
    length, h, b, t_horiz, t_vert, r = hd.length, hd.dim1, hd.dim2, hd.dim3, hd.dim4, hd.radius
    if min(length, h, b, t_horiz, t_vert) <= 0 or t_horiz >= h or t_vert >= b:
        raise ValueError("Ongeldige afmetingen voor L-profiel")
    part.warnings.append(
        "L-profiel opgebouwd uit nominale benen, diktes en wortelradius; niet-opgegeven teenradii kunnen afwijken"
    )
    fallback = _box(length + 20.0, b + 20.0, h + 20.0, -10.0, -10.0, -10.0)
    vmask = _first_mask(part, "v", b, fallback)
    umask = _first_mask(part, "u", h, fallback)

    vertical = _box(length, t_vert, h).intersect(vmask)
    horizontal = _box(length, b, t_horiz).intersect(umask)
    result = vertical.union(horizontal)
    if r > 0:
        patch = _fillet_patch_x(length, t_vert, t_horiz, r, t_vert + r, t_horiz + r)
        result = result.union(patch.intersect(vmask).intersect(umask))
    return _apply_holes(part, result, "L", h, b, t_horiz, t_vert)


def build_m_profile(part: NC1Part) -> cq.Workplane:
    hd = part.header
    length, h, b, ty, tz, r = hd.length, hd.dim1, hd.dim2, hd.dim3, hd.dim4, hd.radius
    positive_thicknesses = [v for v in (ty, tz) if v > 0]
    if min(length, h, b) <= 0 or not positive_thicknesses:
        raise ValueError("Ongeldige afmetingen voor M-profiel")
    t = min(positive_thicknesses)
    part.warnings.append(
        "M-profiel opgebouwd uit nominale maten en opgegeven buitenradius; exacte fabrieksdoorsnede kan afwijken"
    )
    outer = _box(length, b, h)
    if r > 0:
        outer = outer.edges("|X").fillet(r)
    inner_h = h - 2 * t
    inner_b = b - 2 * t
    if inner_h <= 0 or inner_b <= 0:
        raise ValueError("Ongeldige kokerafmetingen")
    inner = _box(length + 2.0, inner_b, inner_h, -1.0, t, t)
    inner_r = max(r - t, 0.0)
    if inner_r > 0:
        inner = inner.edges("|X").fillet(inner_r)
    result = outer.cut(inner)
    # The sample M profile has straight end contours. Complex four-face trims are intentionally deferred.
    if any(part.contours_for(face) for face in "vouh"):
        tolerance = 0.05
        has_intermediate_x = any(
            any(abs(point.x) > tolerance and abs(point.x - length) > tolerance for point in contour.geometry_points)
            for contour in part.contours
        )
        if has_intermediate_x:
            part.warnings.append("Complexe AK-eindcontouren op kokers zijn in deze prototypeversie niet volledig verwerkt")
    return _apply_holes(part, result, "M", h, b, t, t)


def build_round(part: NC1Part) -> cq.Workplane:
    hd = part.header
    if part.holes:
        raise NotImplementedError("BO-gaten in massief rond (RU) worden nog niet ondersteund")
    diameter = hd.dim1 if hd.dim1 > 0 else hd.dim2
    if diameter <= 0 and hd.radius > 0:
        diameter = hd.radius * 2
    if hd.length <= 0 or diameter <= 0:
        raise ValueError("Ongeldige lengte of diameter voor massief rond")
    return _cylinder(diameter / 2.0, hd.length, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))


def build_shape(part: NC1Part) -> cq.Workplane:
    profile_type = part.header.profile_type
    if profile_type == "B":
        return build_plate(part)
    if profile_type == "I":
        return build_i_profile(part)
    if profile_type == "L":
        return build_l_profile(part)
    if profile_type == "M":
        return build_m_profile(part)
    if profile_type == "RU":
        return build_round(part)
    if profile_type == "RO":
        raise NotImplementedError("Ronde buizen (RO) zijn nog niet ondersteund; alleen massief rond (RU)")
    raise NotImplementedError(f"Profieltype {profile_type} wordt nog niet ondersteund")


def convert_nc1_to_step(input_path: str | Path, output_path: str | Path) -> NC1Part:
    part = parse_nc1(input_path)
    if any(contour.kind == "IK" for contour in part.contours):
        raise NotImplementedError("IK-binnencontouren zijn nog niet geïmplementeerd; conversie afgebroken om geometrieverlies te voorkomen")
    non_geometric_blocks = {"SI", "PU", "KO"}
    geometry_blocks = sorted(set(part.unsupported_blocks) - non_geometric_blocks)
    if geometry_blocks:
        raise NotImplementedError(
            "Niet-ondersteunde DSTV-geometrieblokken: " + ", ".join(geometry_blocks)
        )
    shape = build_shape(part)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(shape, str(output_path), exportType="STEP")
    return part


@dataclass
class StepPlate:
    source: Path
    part_number: str
    quantity: int
    thickness: float
    contour: list[tuple[float, float]]
    holes: list[tuple[float, float, float]]  # x, q, diameter
    length: float
    width: float
    gross_area: float
    outer_perimeter: float


def _polygon_area(points: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )


def analyze_step_plate(path: str | Path) -> StepPlate:
    path = Path(path)
    shape = cq.importers.importStep(str(path)).val()
    solids = shape.Solids()
    if len(solids) != 1:
        raise NotImplementedError(
            f"STEP→NC1 verwacht precies één solid; aangetroffen: {len(solids)}"
        )

    planar = [f for f in shape.Faces() if f.geomType() == "PLANE"]
    if not planar:
        raise ValueError("STEP-model bevat geen vlakke oppervlakken")
    face = max(planar, key=lambda f: f.Area())
    outer = face.outerWire()
    line_edges = [e for e in outer.Edges() if e.geomType() == "LINE"]
    if not line_edges or len(line_edges) != len(outer.Edges()):
        raise NotImplementedError("STEP→NC1 ondersteunt in deze versie alleen plaatbuitencontouren met rechte segmenten")

    normal = face.normalAt().normalized()
    longest = max(line_edges, key=lambda e: e.Length())
    va, vb = longest.Vertices()
    x_dir = (vb.Center() - va.Center()).normalized()
    y_dir = normal.cross(x_dir).normalized()

    raw = [(v.Center().dot(x_dir), v.Center().dot(y_dir)) for v in outer.Vertices()]
    min_x = min(x for x, _ in raw)
    min_y = min(y for _, y in raw)
    contour = [(x - min_x, y - min_y) for x, y in raw]
    cleaned: list[tuple[float, float]] = []
    for p in contour:
        if not cleaned or math.dist(cleaned[-1], p) > 1e-6:
            cleaned.append(p)
    contour = cleaned
    if _polygon_area(contour) < 0:
        contour.reverse()

    length = max(x for x, _ in contour)
    width = max(y for _, y in contour)
    all_proj = [v.Center().dot(normal) for v in shape.Vertices()]
    min_proj, max_proj = min(all_proj), max(all_proj)
    thickness = max_proj - min_proj
    if min(length, width) <= 0 or thickness > 0.35 * min(length, width):
        raise NotImplementedError(
            f"Model is niet betrouwbaar als plaat herkend (dikte {thickness:.3f}, vlakmaat {length:.3f} × {width:.3f})"
        )

    # Een ondersteunde plaat is een constante extrusie: twee hoofdvlakken loodrecht
    # op de dikterichting en zijvlakken die daar exact haaks op staan. Schuine
    # afschuinvlakken en extra tussenliggende pocket-/bossvlakken worden afgewezen.
    plane_tolerance = max(0.02, thickness * 0.001)
    for planar_face in planar:
        candidate_normal = planar_face.normalAt().normalized()
        alignment = abs(candidate_normal.dot(normal))
        if alignment >= 1.0 - 1e-6:
            offset = planar_face.Center().dot(normal)
            if min(abs(offset - min_proj), abs(offset - max_proj)) > plane_tolerance:
                raise NotImplementedError(
                    "Tussenliggend vlak aangetroffen; blinde pockets, bussen en getrapte plaatdiktes worden niet ondersteund"
                )
        elif alignment > 1e-6:
            raise NotImplementedError(
                "Schuin vlak of dikte-afschuining aangetroffen; STEP→NC1 ondersteunt alleen constante plaatdiktes"
            )

    # Zoek het evenwijdige plaatvlak aan de overzijde. Een cirkel wordt alleen als
    # doorlopend gat geaccepteerd wanneer dezelfde cirkel op beide hoofdvlakken voorkomt.
    face_offset = face.Center().dot(normal)
    opposite_candidates = []
    for candidate in planar:
        if candidate.isSame(face):
            continue
        candidate_normal = candidate.normalAt().normalized()
        if abs(abs(candidate_normal.dot(normal)) - 1.0) > 1e-6:
            continue
        offset = abs(candidate.Center().dot(normal) - face_offset)
        if abs(offset - thickness) <= max(0.05, thickness * 0.002):
            opposite_candidates.append(candidate)
    opposite = min(opposite_candidates, key=lambda f: abs(f.Area() - face.Area())) if opposite_candidates else None
    if opposite is None:
        raise NotImplementedError("Tegenoverliggend hoofdvlak van de plaat kon niet betrouwbaar worden vastgesteld")
    if abs(opposite.Area() - face.Area()) / max(face.Area(), opposite.Area(), 1.0) > 0.001:
        raise NotImplementedError(
            "De twee hoofdvlakken hebben verschillende netto-oppervlakken; pockets, verzinkingen of niet-constante extrusie vermoed"
        )

    def circular_inner_wires(surface):
        surface_outer = surface.outerWire()
        circles = []
        for wire in surface.Wires():
            if wire.isSame(surface_outer):
                continue
            edges = wire.Edges()
            if len(edges) != 1 or edges[0].geomType() != "CIRCLE":
                raise NotImplementedError("Niet-cirkelvormige binnencontouren zijn in STEP→NC1 nog niet ondersteund")
            edge = edges[0]
            center = edge.arcCenter()
            circles.append((center.dot(x_dir) - min_x, center.dot(y_dir) - min_y, edge.radius()))
        return circles

    face_circles = circular_inner_wires(face)
    opposite_circles = circular_inner_wires(opposite) if opposite is not None else []
    if (face_circles or opposite_circles) and opposite is None:
        raise NotImplementedError("Cirkelvormige uitsparing is niet als doorlopend gat bevestigd op het tegenoverliggende plaatvlak")

    def circle_matches(circle, candidates) -> bool:
        x, y, radius = circle
        return any(
            math.hypot(x - ox, y - oy) <= 0.05 and abs(radius - other_radius) <= 0.02
            for ox, oy, other_radius in candidates
        )

    # Controleer in beide richtingen. Zo wordt ook een blind gat aan uitsluitend
    # de andere plaatzijde opgemerkt wanneer het grootste vlak zelf geen binnenwire heeft.
    if any(not circle_matches(circle, opposite_circles) for circle in face_circles) or any(
        not circle_matches(circle, face_circles) for circle in opposite_circles
    ):
        raise NotImplementedError(
            "Blind gat, verzinking of afwijkende cirkeluitsparing aangetroffen; alleen ronde doorlopende gaten worden ondersteund"
        )

    holes: list[tuple[float, float, float]] = [
        (x, y, radius * 2.0) for x, y, radius in face_circles
    ]

    # Sta alleen de cilindermantels toe die bij de bevestigde, doorlopende gaten horen.
    # Hierdoor worden onder meer zijboringen, bussen, verzinkingen, rondingen en vrije
    # oppervlakken niet stilzwijgend uit de NC1-uitvoer weggelaten.
    for curved_face in (f for f in shape.Faces() if f.geomType() != "PLANE"):
        adaptor = BRepAdaptor_Surface(TopoDS.Face_s(curved_face.wrapped))
        if adaptor.GetType() != GeomAbs_Cylinder:
            raise NotImplementedError(
                f"Niet-ondersteund gebogen oppervlak aangetroffen ({curved_face.geomType()}); alleen cilindermantels van doorlopende gaten zijn toegestaan"
            )
        cylinder = adaptor.Cylinder()
        axis_direction = cylinder.Axis().Direction()
        axis = cq.Vector(axis_direction.X(), axis_direction.Y(), axis_direction.Z()).normalized()
        if abs(abs(axis.dot(normal)) - 1.0) > 1e-6:
            raise NotImplementedError("Zijboring of cilindrisch oppervlak met afwijkende asrichting aangetroffen")
        location = cylinder.Axis().Location()
        axis_point = cq.Vector(location.X(), location.Y(), location.Z())
        cx = axis_point.dot(x_dir) - min_x
        cy = axis_point.dot(y_dir) - min_y
        radius = cylinder.Radius()
        if not any(
            math.hypot(cx - hx, cy - hy) <= 0.05 and abs(radius * 2.0 - diameter) <= 0.02
            for hx, hy, diameter in holes
        ):
            raise NotImplementedError(
                "Cilindrisch kenmerk kon niet aan een rond doorlopend gat worden gekoppeld"
            )

    stem_bits = path.stem.split("_")
    part_number = stem_bits[0]
    quantity = 1
    if len(stem_bits) > 1:
        try:
            quantity = int(stem_bits[1])
        except ValueError:
            pass

    gross_area = abs(_polygon_area(contour))
    perimeter = sum(e.Length() for e in line_edges)
    return StepPlate(path, part_number, quantity, thickness, contour, holes, length, width, gross_area, perimeter)


def _ascii_safe(value: object, fallback: str = "-") -> str:
    text = str(value).strip() or fallback
    return text.encode("ascii", errors="replace").decode("ascii")


def _fmt_number(value: float) -> str:
    rounded = round(value, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def _ak_line(face: str, x: float, datum: str, q: float, notch: str = "", radius: float = 0.0) -> str:
    return (
        "  " + (face[:1] if face else " ")
        + f"{x:11.2f}"
        + (datum[:1] if datum else " ")
        + f"{q:10.2f}"
        + (notch[:1] if notch else " ")
        + f"{radius:10.2f}"
        + f"{0.0:11.2f}{0.0:11.2f}{0.0:11.2f}{0.0:11.2f}"
    )


def _bo_line(face: str, x: float, datum: str, q: float, diameter: float) -> str:
    return "  " + face[:1] + f"{x:11.2f}" + (datum[:1] if datum else " ") + f"{q:10.2f}" + f"{diameter:11.2f}"


def step_plate_to_nc1(
    input_path: str | Path,
    output_path: str | Path,
    *,
    material: str = "S235JR",
    order_number: str = "STEP",
) -> StepPlate:
    plate = analyze_step_plate(input_path)
    material = _ascii_safe(material, "S235JR")
    order_number = _ascii_safe(order_number, "STEP")
    part_number = _ascii_safe(plate.part_number, "PART")
    source_name = _ascii_safe(Path(input_path).name, "source.step")
    t = round(plate.thickness, 2)
    length = round(plate.length, 2)
    width = round(plate.width, 2)
    gross_area = max(plate.gross_area, 1e-9)
    weight = t * 7.85
    paint = 2.0 + plate.outer_perimeter * t / gross_area
    profile = f"PL{_fmt_number(t)}*{_fmt_number(width)}"

    contour = [(round(x, 2), round(y, 2)) for x, y in plate.contour]
    # Rotate to the lexicographically smallest coordinate for stable output.
    start = min(range(len(contour)), key=lambda idx: (contour[idx][0], contour[idx][1]))
    contour = contour[start:] + contour[:start]
    if _polygon_area(contour) < 0:
        contour.reverse()
    contour.append(contour[0])

    lines = [
        "ST",
        f"** Generated by {APP_NAME} from {source_name}",
        f"  {order_number}",
        f"  {part_number}",
        "  1",
        f"  {part_number}",
        f"  {material}",
        f"  {plate.quantity}",
        f"  {profile}",
        "  B",
        f"  {length:9.2f},{length:.2f}",
        f"  {width:9.2f}",
        f"  {t:9.2f}",
        f"  {t:9.2f}",
        f"  {t:9.2f}",
        f"  {0.0:9.2f}",
        f"  {weight:8.3f}",
        f"  {paint:8.3f}",
        f"  {0.0:8.3f}",
        f"  {0.0:8.3f}",
        f"  {0.0:8.3f}",
        f"  {0.0:8.3f}",
        "",
        "",
        "",
        "",
        "AK",
    ]
    for idx, (x, q) in enumerate(contour):
        lines.append(_ak_line("v" if idx == 0 else "", x, "u" if idx == 0 else "", q))
    if plate.holes:
        lines.append("BO")
        for x, q, diameter in sorted(plate.holes):
            lines.append(_bo_line("v", round(x, 2), "s", round(q, 2), round(diameter, 2)))
    lines.append("EN")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="ascii", newline="") as handle:
        handle.write("\r\n".join(lines) + "\r\n")
    return plate


def convert_file(
    input_path: str | Path,
    output_directory: str | Path,
    direction: str,
    *,
    material: str = "S235JR",
) -> tuple[Path, list[str]]:
    """Converteer één bestand en retourneer uitvoerpad plus waarschuwingen."""
    source = Path(input_path)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    normalized = direction.lower().replace(" ", "")
    if normalized in {"nc1-step", "nc1→step", "nc1tostep", "nc1_to_step"}:
        target = output_directory / f"{source.stem}.step"
        part = convert_nc1_to_step(source, target)
        return target, list(part.warnings)
    if normalized in {"step-nc1", "step→nc1", "steptonc1", "step_to_nc1"}:
        target = output_directory / f"{source.stem}.nc1"
        step_plate_to_nc1(source, target, material=material)
        return target, []
    raise ValueError(f"Onbekende conversierichting: {direction}")
