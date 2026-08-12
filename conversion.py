"""Uitgebreide conversielaag voor NC1 ↔ STEP v0.2.

Deze module bouwt voort op de geteste v0.1-kern en voegt toe:
- STEP → NC1 voor standaardprofielen via een lokale profielendatabase;
- U/C-profielen en ronde buizen in de NC1 → STEP-opbouw;
- volumecontrole na de reverse-conversie;
- hulpfuncties voor de visuele vergelijking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math
from typing import Iterable

import cadquery as cq
import numpy as np

import converter as core
from profile_database import ProfileDatabase, ProfileDefinition, ProfileMatch
from canonical_model import (
    CanonicalPart,
    canonical_from_nc1_part,
    embed_part_in_nc1,
    embed_part_in_step,
    extract_part_from_nc1,
    extract_part_from_step,
    sha256_bytes,
)

__version__ = "0.5.0"


# ---------------------------------------------------------------------------
# Uitgebreide NC1 → STEP-opbouw
# ---------------------------------------------------------------------------

def _cut_wall_holes(
    part: core.NC1Part,
    solid: cq.Workplane,
    profile_type: str,
    h: float,
    b: float,
    tf: float,
    tw: float,
) -> cq.Workplane:
    result = solid
    for hole in part.holes:
        if hole.operation or hole.depth > 0:
            raise NotImplementedError("Speciale BO-bewerkingen zijn voor dit profiel nog niet ondersteund")
        radius = hole.diameter / 2.0
        if radius <= 0:
            raise ValueError("Ongeldige gatdiameter")
        if profile_type == "U":
            if hole.face in {"v", "h"}:
                cutter = core._cylinder(radius, tw + 2.0, (hole.x, -1.0, hole.q), (0.0, 1.0, 0.0))
            elif hole.face == "o":
                cutter = core._cylinder(radius, tf + 2.0, (hole.x, hole.q, h - tf - 1.0), (0.0, 0.0, 1.0))
            elif hole.face == "u":
                cutter = core._cylinder(radius, tf + 2.0, (hole.x, hole.q, -1.0), (0.0, 0.0, 1.0))
            else:
                raise NotImplementedError(f"Onbekend U-profielvlak: {hole.face}")
        elif profile_type == "M":
            wall = min(value for value in (tf, tw) if value > 0)
            if hole.face == "v":
                cutter = core._cylinder(radius, wall + 2.0, (hole.x, -1.0, hole.q), (0.0, 1.0, 0.0))
            elif hole.face == "h":
                cutter = core._cylinder(radius, wall + 2.0, (hole.x, b - wall - 1.0, hole.q), (0.0, 1.0, 0.0))
            elif hole.face == "u":
                cutter = core._cylinder(radius, wall + 2.0, (hole.x, hole.q, -1.0), (0.0, 0.0, 1.0))
            elif hole.face == "o":
                cutter = core._cylinder(radius, wall + 2.0, (hole.x, hole.q, h - wall - 1.0), (0.0, 0.0, 1.0))
            else:
                raise NotImplementedError(f"Onbekend kokerprofielvlak: {hole.face}")
        else:
            raise NotImplementedError(profile_type)

        before = result.val().Volume()
        candidate = result.cut(cutter)
        if before - candidate.val().Volume() <= 1e-6:
            raise ValueError(f"Gat Ø{hole.diameter:g} op vlak {hole.face} snijdt het profiel niet")
        result = candidate
    return result


def build_u_profile(part: core.NC1Part) -> cq.Workplane:
    header = part.header
    length, h, b, tf, tw, radius = (
        header.length,
        header.dim1,
        header.dim2,
        header.dim3,
        header.dim4,
        header.radius,
    )
    if min(length, h, b, tf, tw) <= 0 or h <= 2 * tf or b <= tw:
        raise ValueError("Ongeldige afmetingen voor U/C-profiel")

    fallback = core._box(length + 20.0, b + 20.0, h + 20.0, -10.0, -10.0, -10.0)
    vmask = core._first_mask(part, "v", b, fallback)
    omask = core._first_mask(part, "o", h, fallback)
    umask = core._first_mask(part, "u", h, fallback)

    web = core._box(length, tw, h).intersect(vmask)
    top = core._box(length, b, tf, 0.0, 0.0, h - tf).intersect(omask)
    bottom = core._box(length, b, tf).intersect(umask)
    result = web.union(top).union(bottom)

    if radius > 0:
        patches = [
            (core._fillet_patch_x(length, tw, h - tf - radius, radius, tw + radius, h - tf - radius), omask),
            (core._fillet_patch_x(length, tw, tf, radius, tw + radius, tf + radius), umask),
        ]
        for patch, flange_mask in patches:
            try:
                result = result.union(patch.intersect(vmask).intersect(flange_mask))
            except Exception as exc:
                part.warnings.append(f"U-profielradius gedeeltelijk overgeslagen: {exc}")
    return _cut_wall_holes(part, result, "U", h, b, tf, tw)


def build_m_profile(part: core.NC1Part) -> cq.Workplane:
    header = part.header
    length, h, b, ty, tz, radius = (
        header.length,
        header.dim1,
        header.dim2,
        header.dim3,
        header.dim4,
        header.radius,
    )
    positive = [value for value in (ty, tz) if value > 0]
    if min(length, h, b) <= 0 or not positive:
        raise ValueError("Ongeldige kokerafmetingen")
    wall = min(positive)
    outer = core._box(length, b, h)
    if radius > 0:
        outer = outer.edges("|X").fillet(radius)
    inner_h, inner_b = h - 2 * wall, b - 2 * wall
    if min(inner_h, inner_b) <= 0:
        raise ValueError("Kokerwand is te dik voor de opgegeven buitenmaten")
    inner = core._box(length + 2.0, inner_b, inner_h, -1.0, wall, wall)
    inner_radius = max(radius - wall, 0.0)
    if inner_radius > 0:
        inner = inner.edges("|X").fillet(inner_radius)
    result = outer.cut(inner)
    if part.holes:
        result = _cut_wall_holes(part, result, "M", h, b, wall, wall)
    part.warnings.append(
        "Koker opgebouwd uit nominale maten en radius; controleer fabrikant-specifieke hoekgeometrie."
    )
    return result


def build_round_tube(part: core.NC1Part) -> cq.Workplane:
    header = part.header
    diameter = header.dim1 if header.dim1 > 0 else header.dim2
    thicknesses = [value for value in (header.dim3, header.dim4) if value > 0]
    thickness = min(thicknesses) if thicknesses else 0.0
    if header.length <= 0 or diameter <= 0 or thickness <= 0 or diameter <= 2 * thickness:
        raise ValueError("Ongeldige ronde-buisafmetingen")
    if part.holes:
        raise NotImplementedError("Gaten in ronde buizen worden nog niet automatisch teruggebouwd")
    outer = core._cylinder(diameter / 2.0, header.length, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    inner = core._cylinder(
        diameter / 2.0 - thickness,
        header.length + 2.0,
        (-1.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
    )
    return outer.cut(inner)


def build_shape(part: core.NC1Part) -> cq.Workplane:
    profile_type = part.header.profile_type.upper()
    if profile_type in {"U", "C"}:
        return build_u_profile(part)
    if profile_type == "M":
        return build_m_profile(part)
    if profile_type == "RO":
        return build_round_tube(part)
    return core.build_shape(part)


def convert_nc1_to_step(input_path: str | Path, output_path: str | Path) -> core.NC1Part:
    """Converteer NC1 naar STEP via het canonieke productieobject.

    Wanneer de NC1 door deze converter is gemaakt en een geldige, gehashte
    oorspronkelijke STEP-bijlage bevat, wordt die exacte analytische STEP-vorm
    hersteld. Anders wordt de beproefde NC1-geometriekern gebruikt en krijgt de
    STEP een lossless canonieke payload voor volgende conversiestappen.
    """

    source = Path(input_path)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = core.parse_nc1(source)
    payload = extract_part_from_nc1(source, strict=False)

    if payload is not None:
        step_bytes = payload.attachment_bytes("step")
        if step_bytes:
            target.write_bytes(step_bytes)
            # Plaats de geverifieerde payload opnieuw in de herstelde STEP.
            embed_part_in_step(target, payload)
            return part

    if any(contour.kind == "IK" for contour in part.contours):
        raise NotImplementedError("IK-binnencontouren zijn nog niet geïmplementeerd")
    non_geometric = {"SI", "PU", "KO"}
    unsupported = sorted(set(part.unsupported_blocks) - non_geometric)
    if unsupported:
        raise NotImplementedError("Niet-ondersteunde DSTV-geometrieblokken: " + ", ".join(unsupported))
    shape = build_shape(part)
    cq.exporters.export(shape, str(target), exportType="STEP")

    solid = shape.val()
    box = solid.BoundingBox()
    canonical = canonical_from_nc1_part(
        part,
        source_bytes=source.read_bytes(),
        converter_version=__version__,
        geometry={
            "volume_mm3": float(solid.Volume()),
            "area_mm2": float(solid.Area()),
            "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
            "solids": len(solid.Solids()),
        },
    )
    canonical.add_attachment("step", target.name, "model/step", target.read_bytes())
    embed_part_in_step(target, canonical)
    return part


# ---------------------------------------------------------------------------
# STEP-profielanalyse
# ---------------------------------------------------------------------------

@dataclass
class LocalFrame:
    x_dir: np.ndarray
    y_dir: np.ndarray
    z_dir: np.ndarray
    minimum: np.ndarray
    maximum: np.ndarray

    @property
    def length(self) -> float:
        return float(self.maximum[0] - self.minimum[0])


@dataclass
class StepProfileAnalysis:
    source: Path
    part_number: str
    quantity: int
    profile: ProfileDefinition
    match: ProfileMatch
    frame: LocalFrame
    contours: dict[str, list[tuple[float, float]]]
    holes: list[tuple[str, float, float, float]]
    source_volume: float
    source_area: float
    warnings: list[str] = field(default_factory=list)


@dataclass
class StepToNC1Result:
    source: Path
    output: Path
    kind: str
    part_number: str
    profile_designation: str
    profile_type: str
    confidence: float
    matched_by: str
    source_volume: float
    reconstructed_volume: float
    volume_delta_percent: float
    source_area: float
    reconstructed_area: float
    area_delta_percent: float
    warnings: list[str] = field(default_factory=list)


def _unit(vector: np.ndarray | tuple[float, float, float]) -> np.ndarray:
    value = np.asarray(vector, dtype=float)
    norm = float(np.linalg.norm(value))
    if norm <= 1e-12:
        raise ValueError("Nulvector als geometrie-as")
    return value / norm


def _canonical_axis(vector: np.ndarray | tuple[float, float, float]) -> np.ndarray:
    value = _unit(vector)
    index = int(np.argmax(np.abs(value)))
    return value if value[index] >= 0 else -value


def _mesh_points(shape: cq.Shape, tolerance: float = 0.5) -> np.ndarray:
    vertices, _ = shape.tessellate(tolerance, 0.2)
    points = np.asarray([vertex.toTuple() for vertex in vertices], dtype=float)
    if len(points) < 4:
        points = np.asarray([vertex.Center().toTuple() for vertex in shape.Vertices()], dtype=float)
    if len(points) < 4:
        raise ValueError("Onvoldoende STEP-geometriepunten")
    return points


def _principal_axis(points: np.ndarray) -> np.ndarray:
    centered = points - points.mean(axis=0)
    _, eigenvectors = np.linalg.eigh(np.cov(centered, rowvar=False))
    axes = [eigenvectors[:, index] for index in range(3)]
    extents = [float(np.ptp(centered @ axis)) for axis in axes]
    return _canonical_axis(axes[int(np.argmax(extents))])


def _longitudinal_face_axes(
    shape: cq.Shape,
    approximate_x: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    groups: list[list[object]] = []
    for face in shape.Faces():
        if face.geomType() != "PLANE":
            continue
        normal = _unit(np.asarray(face.normalAt().toTuple(), dtype=float))
        if abs(float(np.dot(normal, approximate_x))) > 0.12:
            continue
        normal = _canonical_axis(normal)
        area = float(face.Area())
        for group in groups:
            if abs(float(np.dot(normal, group[0]))) > 0.9995:
                group[1] = float(group[1]) + area
                break
        else:
            groups.append([normal, area])

    best: tuple[float, np.ndarray, np.ndarray] | None = None
    for index, first in enumerate(groups):
        for second in groups[index + 1 :]:
            if abs(float(np.dot(first[0], second[0]))) > 0.08:
                continue
            score = float(first[1]) + float(second[1])
            if best is None or score > best[0]:
                best = (score, first[0], second[0])
    if best is None:
        return None
    first, second = _unit(best[1]), _unit(best[2])
    exact_x = _unit(np.cross(first, second))
    if float(np.dot(exact_x, approximate_x)) < 0:
        exact_x = -exact_x
    return _canonical_axis(exact_x), first, second


def _mid_cross_section(
    shape: cq.Shape,
    points: np.ndarray,
    x_dir: np.ndarray,
    helper_dir: np.ndarray,
) -> cq.Face:
    projection = points @ x_dir
    middle = float((projection.min() + projection.max()) / 2.0)
    center = points.mean(axis=0)
    origin = center + x_dir * (middle - float(center @ x_dir))
    plane = cq.Plane(cq.Vector(*origin), cq.Vector(*helper_dir), cq.Vector(*x_dir))
    section = cq.Workplane(plane).newObject([shape]).section().val()
    faces = section.Faces()
    if not faces:
        raise ValueError("Middendoorsnede kon niet worden bepaald")
    return max(faces, key=lambda face: face.Area())


def _profile_signature(face: cq.Face) -> str:
    outer = face.outerWire()
    inner = [wire for wire in face.Wires() if not wire.isSame(outer)]
    outer_edges = outer.Edges()
    outer_circle = len(outer_edges) == 1 and outer_edges[0].geomType() == "CIRCLE"
    if inner:
        circular_inner = all(len(wire.Edges()) == 1 and wire.Edges()[0].geomType() == "CIRCLE" for wire in inner)
        return "RO" if outer_circle and circular_inner and len(inner) == 1 else "M"
    if outer_circle:
        return "RU"
    edge_count = len(outer_edges)
    if edge_count <= 8:
        return "L"
    if edge_count <= 11:
        return "U"
    return "I"


def _make_frame(
    points: np.ndarray,
    profile: ProfileDefinition,
    approximate_x: np.ndarray,
    face_axes: tuple[np.ndarray, np.ndarray, np.ndarray] | None,
) -> LocalFrame:
    if face_axes is not None:
        x_dir, first, second = face_axes
        options = []
        for y_dir, z_dir in ((first, second), (second, first)):
            y_extent = float(np.ptp(points @ y_dir))
            z_extent = float(np.ptp(points @ z_dir))
            options.append((abs(y_extent - profile.width) + abs(z_extent - profile.height), y_dir, z_dir))
        _, y_dir, z_dir = min(options, key=lambda item: item[0])
    else:
        x_dir = approximate_x
        helper = np.array([1.0, 0.0, 0.0])
        if abs(float(np.dot(helper, x_dir))) > 0.9:
            helper = np.array([0.0, 1.0, 0.0])
        y_dir = _unit(helper - x_dir * float(np.dot(helper, x_dir)))
        z_dir = _unit(np.cross(x_dir, y_dir))

    x_dir, y_dir, z_dir = _canonical_axis(x_dir), _canonical_axis(y_dir), _canonical_axis(z_dir)
    projections = np.column_stack((points @ x_dir, points @ y_dir, points @ z_dir))
    return LocalFrame(x_dir, y_dir, z_dir, projections.min(axis=0), projections.max(axis=0))


def _section_face(
    shape: cq.Shape,
    frame: LocalFrame,
    axis: str,
    coordinate: float,
) -> tuple[cq.Face, np.ndarray, float]:
    middle = (frame.minimum + frame.maximum) / 2.0
    if axis == "y":
        origin = frame.x_dir * middle[0] + frame.y_dir * coordinate + frame.z_dir * middle[2]
        normal, q_axis, q_min = frame.y_dir, frame.z_dir, float(frame.minimum[2])
    elif axis == "z":
        origin = frame.x_dir * middle[0] + frame.y_dir * middle[1] + frame.z_dir * coordinate
        normal, q_axis, q_min = frame.z_dir, frame.y_dir, float(frame.minimum[1])
    else:
        raise ValueError(axis)
    plane = cq.Plane(cq.Vector(*origin), cq.Vector(*frame.x_dir), cq.Vector(*normal))
    section = cq.Workplane(plane).newObject([shape]).section().val()
    faces = section.Faces()
    if not faces:
        raise ValueError(f"Geen profielvlakdoorsnede voor {axis}={coordinate:.3f}")
    return max(faces, key=lambda face: face.Area()), q_axis, q_min


def _flip_axis(frame: LocalFrame, points: np.ndarray, axis: str) -> LocalFrame:
    x_dir, y_dir, z_dir = frame.x_dir.copy(), frame.y_dir.copy(), frame.z_dir.copy()
    if axis == "y":
        y_dir = -y_dir
    elif axis == "z":
        z_dir = -z_dir
    elif axis == "x":
        x_dir = -x_dir
    else:
        raise ValueError(axis)
    projections = np.column_stack((points @ x_dir, points @ y_dir, points @ z_dir))
    return LocalFrame(x_dir, y_dir, z_dir, projections.min(axis=0), projections.max(axis=0))


def _orient_asymmetric(
    shape: cq.Shape,
    points: np.ndarray,
    frame: LocalFrame,
    profile: ProfileDefinition,
) -> LocalFrame:
    def area(active: LocalFrame, axis: str, coordinate: float) -> float:
        try:
            face, _, _ = _section_face(shape, active, axis, coordinate)
            return float(face.Area())
        except Exception:
            return 0.0

    if profile.profile_type in {"L", "U", "C"}:
        low = area(frame, "y", float(frame.minimum[1] + profile.dim4 / 2.0))
        high = area(frame, "y", float(frame.maximum[1] - profile.dim4 / 2.0))
        if high > low:
            frame = _flip_axis(frame, points, "y")
    if profile.profile_type == "L":
        low = area(frame, "z", float(frame.minimum[2] + profile.dim3 / 2.0))
        high = area(frame, "z", float(frame.maximum[2] - profile.dim3 / 2.0))
        if high > low:
            frame = _flip_axis(frame, points, "z")
    return frame


def _wire_coordinates(
    wire: cq.Wire,
    frame: LocalFrame,
    q_axis: np.ndarray,
    q_min: float,
    q_span: float,
) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for vertex in wire.Vertices():
        point = np.asarray(vertex.Center().toTuple(), dtype=float)
        x = float(point @ frame.x_dir - frame.minimum[0])
        q = float(point @ q_axis - q_min)
        if abs(x) < 0.08:
            x = 0.0
        elif abs(x - frame.length) < 0.08:
            x = frame.length
        if abs(q) < 0.08:
            q = 0.0
        elif abs(q - q_span) < 0.08:
            q = q_span
        candidate = (x, q)
        if not result or math.dist(result[-1], candidate) > 1e-5:
            result.append(candidate)
    if len(result) > 1 and math.dist(result[0], result[-1]) < 1e-5:
        result.pop()
    if len(result) < 3:
        raise ValueError("Profielcontour heeft minder dan drie punten")
    if core._polygon_area(result) < 0:
        result.reverse()
    start = min(range(len(result)), key=lambda index: (round(result[index][0], 5), round(result[index][1], 5)))
    return result[start:] + result[:start]


def _extract_face(
    shape: cq.Shape,
    frame: LocalFrame,
    face_code: str,
    axis: str,
    coordinate: float,
    q_span: float,
) -> tuple[list[tuple[float, float]], list[tuple[str, float, float, float]]]:
    face, q_axis, q_min = _section_face(shape, frame, axis, coordinate)
    outer = face.outerWire()
    contour = _wire_coordinates(outer, frame, q_axis, q_min, q_span)
    holes: list[tuple[str, float, float, float]] = []
    for wire in face.Wires():
        if wire.isSame(outer):
            continue
        edges = wire.Edges()
        if len(edges) != 1 or edges[0].geomType() not in {"CIRCLE", "ELLIPSE"}:
            raise NotImplementedError(
                f"Niet-rond binnenkenmerk op profielvlak {face_code}; alleen ronde doorlopende gaten zijn toegestaan"
            )
        edge = edges[0]
        if edge.geomType() == "ELLIPSE":
            # Een zeer licht scheve doorsnede kan OCC als ellips rapporteren. Alleen
            # accepteren wanneer beide radii praktisch gelijk zijn.
            try:
                major, minor = edge._geomAdaptor().Ellipse().MajorRadius(), edge._geomAdaptor().Ellipse().MinorRadius()
            except Exception as exc:
                raise NotImplementedError("Ellipsvormige uitsparing wordt niet ondersteund") from exc
            if abs(major - minor) > 0.03:
                raise NotImplementedError("Echte ellipsvormige uitsparing wordt niet ondersteund")
            radius = (major + minor) / 2.0
        else:
            radius = float(edge.radius())
        center = np.asarray(edge.arcCenter().toTuple(), dtype=float)
        holes.append(
            (
                face_code,
                float(center @ frame.x_dir - frame.minimum[0]),
                float(center @ q_axis - q_min),
                radius * 2.0,
            )
        )
    return contour, holes


def _rectangle(length: float, span: float) -> list[tuple[float, float]]:
    return [(0.0, 0.0), (length, 0.0), (length, span), (0.0, span)]


def analyze_step_profile(
    path: str | Path,
    *,
    profile_database: ProfileDatabase | None = None,
    preferred_profile: str = "",
    tolerance_mm: float = 1.0,
) -> StepProfileAnalysis:
    source = Path(path)
    shape = cq.importers.importStep(str(source)).val()
    if len(shape.Solids()) != 1:
        raise NotImplementedError("Profielherkenning verwacht precies één STEP-solid")

    points = _mesh_points(shape)
    approximate_x = _principal_axis(points)
    face_axes = _longitudinal_face_axes(shape, approximate_x)
    if face_axes:
        x_dir, helper, other = face_axes
    else:
        x_dir = approximate_x
        helper = np.array([1.0, 0.0, 0.0])
        if abs(float(np.dot(helper, x_dir))) > 0.9:
            helper = np.array([0.0, 1.0, 0.0])
        helper = _unit(helper - x_dir * float(np.dot(helper, x_dir)))
        other = _unit(np.cross(x_dir, helper))

    cross_section = _mid_cross_section(shape, points, x_dir, helper)
    signature = _profile_signature(cross_section)
    length = float(np.ptp(points @ x_dir))
    if length <= 0:
        raise ValueError("Ongeldige profiellengte")

    cross_a = float(np.ptp(points @ helper))
    cross_b = float(np.ptp(points @ other))
    database = profile_database or ProfileDatabase()
    if preferred_profile:
        selected = database.find(preferred_profile)
        if selected is None:
            raise LookupError(f"Profiel {preferred_profile!r} staat niet in de database")
        expected_type = "U" if selected.profile_type == "C" else selected.profile_type
        if expected_type != signature:
            raise LookupError(
                f"Gekozen profiel is type {selected.profile_type}, maar STEP lijkt type {signature}"
            )
        dim_error = min(
            max(abs(cross_a - selected.width), abs(cross_b - selected.height)),
            max(abs(cross_a - selected.height), abs(cross_b - selected.width)),
        )
        area_est = float(shape.Volume()) / length
        area_error = abs(area_est - selected.area_mm2) / max(selected.area_mm2, 1e-9) * 100.0
        confidence = max(0.50, min(1.0, 1.0 - dim_error / max(tolerance_mm * 4.0, 4.0)))
        match = ProfileMatch(selected, confidence, dim_error, area_error, "handmatige keuze + geometriecontrole")
    else:
        match = database.match(
            filename=source.name,
            signature_type=signature,
            cross_extent_a=cross_a,
            cross_extent_b=cross_b,
            area_estimate_mm2=float(shape.Volume()) / length,
            tolerance_mm=tolerance_mm,
        )

    frame = _make_frame(points, match.profile, approximate_x, face_axes)
    frame = _orient_asymmetric(shape, points, frame, match.profile)
    if frame.length < 1.20 * max(match.profile.width, match.profile.height):
        raise NotImplementedError("Onderdeel is te kort voor betrouwbare automatische profielherkenning")

    profile = match.profile
    h, b, tf, tw = profile.dim1, profile.dim2, profile.dim3, profile.dim4
    specifications: dict[str, tuple[str, float, float]]
    if profile.profile_type == "I":
        specifications = {
            "v": ("y", float((frame.minimum[1] + frame.maximum[1]) / 2.0), h),
            "o": ("z", float(frame.maximum[2] - tf / 2.0), b),
            "u": ("z", float(frame.minimum[2] + tf / 2.0), b),
        }
    elif profile.profile_type in {"U", "C"}:
        specifications = {
            "v": ("y", float(frame.minimum[1] + tw / 2.0), h),
            "o": ("z", float(frame.maximum[2] - tf / 2.0), b),
            "u": ("z", float(frame.minimum[2] + tf / 2.0), b),
        }
    elif profile.profile_type == "L":
        specifications = {
            "v": ("y", float(frame.minimum[1] + tw / 2.0), h),
            "u": ("z", float(frame.minimum[2] + tf / 2.0), b),
        }
    elif profile.profile_type == "M":
        wall = min(value for value in (tf, tw) if value > 0)
        specifications = {
            "v": ("y", float(frame.minimum[1] + wall / 2.0), h),
            "h": ("y", float(frame.maximum[1] - wall / 2.0), h),
            "u": ("z", float(frame.minimum[2] + wall / 2.0), b),
            "o": ("z", float(frame.maximum[2] - wall / 2.0), b),
        }
    else:
        specifications = {}

    contours: dict[str, list[tuple[float, float]]] = {}
    holes: list[tuple[str, float, float, float]] = []
    warnings = [f"Profielherkenning: {profile.designation} ({match.confidence:.0%}, {match.matched_by})"]
    for face_code, (axis, coordinate, span) in specifications.items():
        try:
            contour, face_holes = _extract_face(shape, frame, face_code, axis, coordinate, span)
            contours[face_code] = contour
            holes.extend(face_holes)
        except Exception as exc:
            if profile.profile_type == "M":
                contours[face_code] = _rectangle(frame.length, span)
                warnings.append(f"Vlak {face_code}: standaardcontour gebruikt ({exc})")
            else:
                raise

    if profile.profile_type in {"RU", "RO"}:
        contours["v"] = _rectangle(frame.length, profile.dim1)

    unique_holes: list[tuple[str, float, float, float]] = []
    for hole in holes:
        rounded = (hole[0], round(hole[1], 4), round(hole[2], 4), round(hole[3], 4))
        if not any(
            existing[0] == rounded[0]
            and abs(existing[1] - rounded[1]) < 0.05
            and abs(existing[2] - rounded[2]) < 0.05
            and abs(existing[3] - rounded[3]) < 0.03
            for existing in unique_holes
        ):
            unique_holes.append(rounded)

    bits = source.stem.split("_")
    part_number = bits[0] or "PART"
    quantity = 1
    if len(bits) > 1:
        try:
            quantity = int(bits[1])
        except ValueError:
            pass

    return StepProfileAnalysis(
        source,
        part_number,
        quantity,
        profile,
        match,
        frame,
        contours,
        unique_holes,
        float(shape.Volume()),
        float(shape.Area()),
        warnings,
    )


def _write_profile_nc1(
    analysis: StepProfileAnalysis,
    output_path: str | Path,
    *,
    material: str,
    order_number: str,
) -> None:
    profile = analysis.profile
    material = core._ascii_safe(material, "S235JR")
    order_number = core._ascii_safe(order_number, "STEP")
    part_number = core._ascii_safe(analysis.part_number, "PART")
    length = round(analysis.frame.length, 2)
    source_name = core._ascii_safe(analysis.source.name, "source.step")
    mass = profile.mass_kg_m or profile.area_mm2 * 0.00785
    lines = [
        "ST",
        f"** Generated by NC1-STEP Converter v{__version__} from {source_name}",
        f"  {order_number}",
        f"  {part_number}",
        "  1",
        f"  {part_number}",
        f"  {material}",
        f"  {analysis.quantity}",
        f"  {core._ascii_safe(profile.designation, 'PROFILE')}",
        f"  {profile.profile_type}",
        f"  {length:9.2f},{length:.2f}",
        f"  {profile.dim1:9.2f}",
        f"  {profile.dim2:9.2f}",
        f"  {profile.dim3:9.2f}",
        f"  {profile.dim4:9.2f}",
        f"  {profile.radius:9.2f}",
        f"  {mass:8.3f}",
        f"  {0.0:8.3f}",
        f"  {0.0:8.3f}",
        f"  {0.0:8.3f}",
        f"  {0.0:8.3f}",
        f"  {0.0:8.3f}",
        "",
        "",
        "",
        "",
    ]
    for face_code in ("v", "o", "u", "h"):
        contour = analysis.contours.get(face_code)
        if not contour:
            continue
        lines.append("AK")
        closed = [(round(x, 2), round(q, 2)) for x, q in contour]
        if closed[0] != closed[-1]:
            closed.append(closed[0])
        for index, (x, q) in enumerate(closed):
            lines.append(core._ak_line(face_code if index == 0 else "", x, "s" if index == 0 else "", q))
    if analysis.holes:
        lines.append("BO")
        for face_code, x, q, diameter in sorted(analysis.holes):
            lines.append(core._bo_line(face_code, round(x, 2), "s", round(q, 2), round(diameter, 2)))
    lines.append("EN")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="ascii", newline="") as handle:
        handle.write("\r\n".join(lines) + "\r\n")


def _delta(first: float, second: float) -> float:
    return (second - first) / first * 100.0 if abs(first) > 1e-12 else 0.0


def step_to_nc1(
    input_path: str | Path,
    output_path: str | Path,
    *,
    material: str = "S235JR",
    order_number: str = "STEP",
    profile_database: ProfileDatabase | None = None,
    preferred_profile: str = "",
    tolerance_mm: float = 1.0,
    strict_validation: bool = True,
    embed_converter_payload: bool = False,
) -> StepToNC1Result:
    """Converteer STEP naar NC1 met lossless payload-prioriteit.

    Een geldige converterpayload wordt alleen gebruikt na schema-, bijlage- en
    checksumcontrole. De herstelde NC1 wordt daarna nog steeds geometrisch
    opgebouwd en aan dezelfde volumebeveiliging onderworpen. Externe STEP zonder
    payload volgt de bestaande plaat-/profielherkenning en krijgt bij uitvoer een
    canonieke payload, zodat een volgende NC1→STEP-stap analytisch lossless kan.
    """

    source, target = Path(input_path), Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    source_shape = cq.importers.importStep(str(source)).val()
    source_volume, source_area = float(source_shape.Volume()), float(source_shape.Area())

    payload = extract_part_from_step(source, strict=False)
    if payload is not None:
        nc1_bytes = payload.attachment_bytes("nc1")
        if nc1_bytes:
            target.write_bytes(nc1_bytes)
            # Productie-NC1 blijft standaard schoon. Alleen interne transport-
            # routes mogen expliciet een converterpayload in DSTV-commentaar zetten.
            if embed_converter_payload:
                embed_part_in_nc1(target, payload)
            try:
                reconstructed_part = core.parse_nc1(target)
                reconstructed_shape = build_shape(reconstructed_part).val()
            except Exception:
                target.unlink(missing_ok=True)
                raise

            header = reconstructed_part.header
            profile_type = header.profile_type
            reconstructed_volume = float(reconstructed_shape.Volume())
            reconstructed_area = float(reconstructed_shape.Area())
            volume_delta = _delta(source_volume, reconstructed_volume)
            area_delta = _delta(source_area, reconstructed_area)
            warnings = list(payload.warnings) + list(reconstructed_part.warnings)
            warnings.insert(0, "NC1 lossless hersteld uit geverifieerde canonieke converterpayload")
            warning_limit = 0.15 if profile_type in {"B", "I", "U", "C", "RU", "RO"} else 0.50
            failure_limit = 0.75 if profile_type in {"B", "I", "U", "C", "RU", "RO"} else 2.00
            if abs(volume_delta) > warning_limit:
                warnings.append(
                    f"Volumecontrole payload: {volume_delta:+.4f}% verschil tussen STEP en NC1-reconstructie"
                )
            if strict_validation and abs(volume_delta) > failure_limit:
                target.unlink(missing_ok=True)
                raise ValueError(
                    f"Veiligheidscontrole afgekeurd: volumeverschil {volume_delta:+.4f}% "
                    f"is groter dan {failure_limit:.2f}%."
                )
            return StepToNC1Result(
                source=source,
                output=target,
                kind="plate" if profile_type == "B" else "profile",
                part_number=header.part_number,
                profile_designation=header.profile,
                profile_type=profile_type,
                confidence=1.0,
                matched_by="lossless converterpayload",
                source_volume=source_volume,
                reconstructed_volume=reconstructed_volume,
                volume_delta_percent=volume_delta,
                source_area=source_area,
                reconstructed_area=reconstructed_area,
                area_delta_percent=area_delta,
                warnings=warnings,
            )

    plate_error: Exception | None = None
    try:
        plate = core.step_plate_to_nc1(source, target, material=material, order_number=order_number)
        kind = "plate"
        part_number = plate.part_number
        profile_name = f"PL{core._fmt_number(plate.thickness)}*{core._fmt_number(plate.width)}"
        profile_type = "B"
        confidence, matched_by, warnings = 1.0, "plaatgeometrie", []
    except Exception as exc:
        plate_error = exc
        try:
            analysis = analyze_step_profile(
                source,
                profile_database=profile_database,
                preferred_profile=preferred_profile,
                tolerance_mm=tolerance_mm,
            )
        except Exception as profile_exc:
            raise NotImplementedError(
                "STEP-model kon niet veilig naar NC1 worden geconverteerd. "
                f"Plaatcontrole: {plate_error}. Profielcontrole: {profile_exc}"
            ) from profile_exc
        _write_profile_nc1(analysis, target, material=material, order_number=order_number)
        kind, part_number = "profile", analysis.part_number
        profile_name, profile_type = analysis.profile.designation, analysis.profile.profile_type
        confidence, matched_by, warnings = (
            analysis.match.confidence,
            analysis.match.matched_by,
            list(analysis.warnings),
        )

    try:
        reconstructed_part = core.parse_nc1(target)
        reconstructed_shape = build_shape(reconstructed_part).val()
        warnings.extend(reconstructed_part.warnings)
    except Exception:
        target.unlink(missing_ok=True)
        raise

    reconstructed_volume, reconstructed_area = (
        float(reconstructed_shape.Volume()),
        float(reconstructed_shape.Area()),
    )
    volume_delta, area_delta = (
        _delta(source_volume, reconstructed_volume),
        _delta(source_area, reconstructed_area),
    )
    warning_limit = 0.15 if profile_type in {"B", "I", "U", "C", "RU", "RO"} else 0.50
    failure_limit = 0.75 if profile_type in {"B", "I", "U", "C", "RU", "RO"} else 2.00
    if abs(volume_delta) > warning_limit:
        warnings.append(f"Volumecontrole: {volume_delta:+.4f}% verschil tussen STEP en NC1-reconstructie")
    if strict_validation and abs(volume_delta) > failure_limit:
        target.unlink(missing_ok=True)
        raise ValueError(
            f"Veiligheidscontrole afgekeurd: volumeverschil {volume_delta:+.4f}% is groter dan {failure_limit:.2f}%."
        )

    # Bouw het canonieke model uit de daadwerkelijk gevalideerde NC1-uitvoer en
    # koppel zowel de bron-STEP als de productie-NC1 als gehashte bijlage.
    generated_nc1 = target.read_bytes()
    box = reconstructed_shape.BoundingBox()
    canonical = canonical_from_nc1_part(
        reconstructed_part,
        source_bytes=generated_nc1,
        converter_version=__version__,
        geometry={
            "volume_mm3": reconstructed_volume,
            "area_mm2": reconstructed_area,
            "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
            "solids": len(reconstructed_shape.Solids()),
        },
        recognition={
            "method": matched_by,
            "confidence": float(confidence),
            "tolerance_mm": float(tolerance_mm),
            "source_volume_delta_percent": volume_delta,
        },
    )
    canonical.source_format = "STEP"
    canonical.source_file = source.name
    canonical.source_sha256 = sha256_bytes(source.read_bytes())
    canonical.add_attachment("step", source.name, "model/step", source.read_bytes())
    # Vervang de NC1-bijlage expliciet door de nog payloadvrije productie-uitvoer.
    canonical.add_attachment("nc1", target.name, "application/x-dstv", generated_nc1)
    if embed_converter_payload:
        embed_part_in_nc1(target, canonical)

    return StepToNC1Result(
        source,
        target,
        kind,
        part_number,
        profile_name,
        profile_type,
        confidence,
        matched_by,
        source_volume,
        reconstructed_volume,
        volume_delta,
        source_area,
        reconstructed_area,
        area_delta,
        warnings,
    )


# ---------------------------------------------------------------------------
# Profielendatabase import en preview helpers
# ---------------------------------------------------------------------------

def profile_from_nc1(path: str | Path) -> ProfileDefinition:
    header = core.parse_nc1(path).header
    if header.profile_type == "B":
        raise ValueError("Plaatprofielen worden niet aan de standaardprofielendatabase toegevoegd")
    area = header.weight / 0.00785 if header.weight > 0 else 0.0
    return ProfileDefinition(
        designation=header.profile,
        profile_type=header.profile_type,
        family=header.profile.rstrip("0123456789/.-") or header.profile_type,
        dim1=header.dim1,
        dim2=header.dim2,
        dim3=header.dim3,
        dim4=header.dim4,
        radius=header.radius,
        mass_kg_m=header.weight,
        area_mm2=area,
        standard="Imported from NC1",
        source=str(Path(path).name),
    )


def import_profiles_from_nc1(paths: Iterable[str | Path], database: ProfileDatabase) -> tuple[int, list[str]]:
    profiles: list[ProfileDefinition] = []
    errors: list[str] = []
    for item in paths:
        path = Path(item)
        candidates = sorted(path.glob("*.nc1")) + sorted(path.glob("*.nc")) if path.is_dir() else [path]
        for candidate in candidates:
            try:
                profiles.append(profile_from_nc1(candidate))
            except ValueError:
                continue
            except Exception as exc:
                errors.append(f"{candidate.name}: {exc}")
    return database.add_many(profiles), errors


def load_shape(path: str | Path) -> cq.Shape:
    source = Path(path)
    if source.suffix.lower() in {".step", ".stp"}:
        return cq.importers.importStep(str(source)).val()
    if source.suffix.lower() in {".nc", ".nc1"}:
        return build_shape(core.parse_nc1(source)).val()
    if source.suffix.lower() == ".ifc":
        from ifc_support import combined_mesh, mesh_to_cq_shape
        points, faces, _metrics = combined_mesh(source)
        return mesh_to_cq_shape(points, faces, make_solid=True)
    raise ValueError(f"Niet-ondersteund voorbeeldbestand: {source.suffix}")


def shape_metrics(shape: cq.Shape) -> dict[str, object]:
    box = shape.BoundingBox()
    return {
        "volume": float(shape.Volume()),
        "area": float(shape.Area()),
        "bbox": tuple(sorted((float(box.xlen), float(box.ylen), float(box.zlen)), reverse=True)),
        "solids": len(shape.Solids()),
    }


def convert_file(
    input_path: str | Path,
    output_directory: str | Path,
    direction: str,
    *,
    material: str = "S235JR",
    order_number: str = "STEP",
    profile_database: ProfileDatabase | None = None,
    preferred_profile: str = "",
    tolerance_mm: float = 1.0,
    strict_validation: bool = True,
) -> tuple[list[Path], list[str], list[str]]:
    """Converteer één bestand en retourneer (outputs, warnings, failures).

    Deze helper wordt gebruikt door GUI en CLI voor eenvoudige conversiepaden.
    IFC-richtingen worden lazy geïmporteerd, zodat de NC1/STEP-kern blijft werken
    wanneer IfcOpenShell niet is geïnstalleerd.
    """
    source = Path(input_path)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    normalised = direction.lower().replace(" ", "").replace("/", "")
    normalised = normalised.replace("dstv", "nc1").replace("→", "-").replace("_", "-").replace("to", "-")

    if normalised in {"nc1-step", "nc1-step", "nc1step"}:
        target = output / f"{source.stem}.step"
        part = convert_nc1_to_step(source, target)
        return [target], list(part.warnings), []

    if normalised in {"step-nc1", "stepnc1"}:
        target = output / f"{source.stem}.nc1"
        result = step_to_nc1(
            source,
            target,
            material=material,
            order_number=order_number,
            profile_database=profile_database,
            preferred_profile=preferred_profile,
            tolerance_mm=tolerance_mm,
            strict_validation=strict_validation,
        )
        warnings = list(result.warnings)
        warnings.insert(0, f"{result.profile_designation}; confidence {result.confidence:.0%}; volume {result.volume_delta_percent:+.6f}%")
        return [target], warnings, []

    if normalised in {"ifc-step", "ifcstep"}:
        from ifc_support import ifc_to_step
        result = ifc_to_step(source, output / f"{source.stem}.step")
        return result.outputs, result.warnings, result.failures

    if normalised in {"step-ifc", "stepifc"}:
        from ifc_support import step_to_ifc
        result = step_to_ifc(source, output / f"{source.stem}.ifc", material=material)
        return result.outputs, result.warnings, result.failures

    if normalised in {"nc1-ifc", "nc1ifc"}:
        from ifc_support import dstv_to_ifc
        result = dstv_to_ifc(source, output / f"{source.stem}.ifc", material=material)
        return result.outputs, result.warnings, result.failures

    if normalised in {"ifc-nc1", "ifcnc1"}:
        from ifc_support import ifc_to_dstv
        result = ifc_to_dstv(
            source,
            output / source.stem,
            material=material,
            order_number=order_number,
            profile_database=profile_database,
            preferred_profile=preferred_profile,
            tolerance_mm=tolerance_mm,
            strict_validation=strict_validation,
        )
        return result.outputs, result.warnings, result.failures

    raise ValueError(f"Onbekende conversierichting: {direction}")
