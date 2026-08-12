"""Veilige analytische herkenning voor externe gefacetteerde geometrie.

De converter-eigen IFC-route gebruikt de lossless canonical payload. Deze module
is uitsluitend de gecontroleerde fallback voor externe IFC/STEP zonder die
metadata. Herkenning levert altijd meetafwijkingen en een confidence-score; een
productiebestand mag pas worden geschreven wanneer de aanroeper de drempel haalt.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import cadquery as cq
import numpy as np


@dataclass(frozen=True)
class CircleFit:
    center_xy: tuple[float, float]
    radius_mm: float
    rms_residual_mm: float
    max_residual_mm: float
    coverage_degrees: float
    confidence: float
    point_count: int


@dataclass(frozen=True)
class CylinderFit:
    base_center_mm: tuple[float, float, float]
    axis: tuple[float, float, float]
    length_mm: float
    radius_mm: float
    diameter_mm: float
    rms_residual_mm: float
    max_residual_mm: float
    volume_delta_percent: float
    confidence: float
    point_count: int


@dataclass(frozen=True)
class AnalyticRecognition:
    kind: str
    confidence: float
    shape: cq.Shape | None
    diagnostics: dict[str, float | str]


def _as_points(points: Iterable[Iterable[float]], dimensions: int | None = None) -> np.ndarray:
    values = np.asarray(list(points), dtype=float)
    if values.ndim != 2 or values.shape[0] == 0:
        raise ValueError("Puntenlijst is leeg of heeft geen matrixvorm")
    if dimensions is not None and values.shape[1] != dimensions:
        raise ValueError(f"Verwacht {dimensions} coördinaten per punt")
    if not np.isfinite(values).all():
        raise ValueError("Puntenlijst bevat niet-eindige waarden")
    return values


def _unit(vector: np.ndarray) -> np.ndarray:
    length = float(np.linalg.norm(vector))
    if length <= 1e-12:
        raise ValueError("Nulvector kan niet worden genormaliseerd")
    return vector / length


def simplify_collinear(
    points: Iterable[Iterable[float]],
    *,
    tolerance_mm: float = 0.05,
    closed: bool = True,
) -> np.ndarray:
    """Verwijder dubbele en collineaire punten zonder de contour te vervormen."""

    data = _as_points(points)
    if len(data) < (3 if closed else 2):
        return data.copy()
    tolerance = max(float(tolerance_mm), 1e-9)

    # Een herhaald eindpunt is representatie, geen apart geometrisch hoekpunt.
    if closed and len(data) > 3 and np.linalg.norm(data[0] - data[-1]) <= tolerance:
        data = data[:-1]

    cleaned: list[np.ndarray] = []
    for point in data:
        if not cleaned or np.linalg.norm(point - cleaned[-1]) > tolerance:
            cleaned.append(point)
    if closed and len(cleaned) > 3 and np.linalg.norm(cleaned[0] - cleaned[-1]) <= tolerance:
        cleaned.pop()

    minimum = 3 if closed else 2
    changed = True
    while changed and len(cleaned) > minimum:
        changed = False
        new: list[np.ndarray] = []
        count = len(cleaned)
        for index, current in enumerate(cleaned):
            if not closed and index in {0, count - 1}:
                new.append(current)
                continue
            previous = cleaned[(index - 1) % count]
            following = cleaned[(index + 1) % count]
            segment = following - previous
            segment_length = float(np.linalg.norm(segment))
            if segment_length <= tolerance:
                changed = True
                continue
            # Loodrechte afstand van current tot de oneindige lijn prev-next.
            relative = current - previous
            projection = float(np.dot(relative, segment) / (segment_length * segment_length))
            closest = previous + projection * segment
            distance = float(np.linalg.norm(current - closest))
            between = -1e-9 <= projection <= 1.0 + 1e-9
            if distance <= tolerance and between:
                changed = True
                continue
            new.append(current)
        if len(new) < minimum:
            break
        cleaned = new
    return np.asarray(cleaned, dtype=float)


def fit_circle_2d(
    points: Iterable[Iterable[float]],
    *,
    tolerance_mm: float = 0.25,
) -> CircleFit:
    """Least-squares cirkelfit met residual, hoekdekking en confidence."""

    data = _as_points(points, 2)
    # Duplicaten wegen een tessellatie-eindpunt anders onbedoeld dubbel.
    unique = np.unique(np.round(data, decimals=9), axis=0)
    if len(unique) < 3:
        raise ValueError("Minimaal drie unieke punten nodig voor cirkelfit")
    x = unique[:, 0]
    y = unique[:, 1]
    matrix = np.column_stack((2.0 * x, 2.0 * y, np.ones_like(x)))
    rhs = x * x + y * y
    solution, _residuals, rank, _singular = np.linalg.lstsq(matrix, rhs, rcond=None)
    if rank < 3:
        raise ValueError("Punten zijn collineair; cirkel is niet bepaalbaar")
    center_x, center_y, constant = (float(value) for value in solution)
    radius_sq = constant + center_x * center_x + center_y * center_y
    if radius_sq <= 1e-12:
        raise ValueError("Berekende cirkelstraal is nul of ongeldig")
    radius = math.sqrt(radius_sq)
    distances = np.hypot(x - center_x, y - center_y)
    residual = np.abs(distances - radius)
    rms = float(math.sqrt(float(np.mean(residual * residual))))
    maximum = float(np.max(residual))

    angles = np.sort(np.mod(np.arctan2(y - center_y, x - center_x), 2.0 * math.pi))
    gaps = np.diff(np.r_[angles, angles[0] + 2.0 * math.pi])
    coverage = 2.0 * math.pi - float(np.max(gaps))
    coverage_degrees = math.degrees(coverage)

    tolerance = max(float(tolerance_mm), 1e-6)
    residual_score = math.exp(-((rms / tolerance) ** 2))
    max_score = math.exp(-((maximum / (2.5 * tolerance)) ** 2))
    coverage_score = min(1.0, coverage_degrees / 300.0)
    sample_score = min(1.0, len(unique) / 12.0)
    confidence = max(0.0, min(1.0, residual_score * max_score * coverage_score * sample_score))
    return CircleFit(
        center_xy=(center_x, center_y),
        radius_mm=radius,
        rms_residual_mm=rms,
        max_residual_mm=maximum,
        coverage_degrees=coverage_degrees,
        confidence=confidence,
        point_count=len(unique),
    )


def _mesh_volume(vertices: np.ndarray, triangles: np.ndarray) -> float:
    if len(vertices) == 0 or len(triangles) == 0:
        return 0.0
    polygons = vertices[np.asarray(triangles, dtype=int)]
    signed = np.einsum(
        "ij,ij->i",
        polygons[:, 0],
        np.cross(polygons[:, 1], polygons[:, 2]),
    ).sum() / 6.0
    return abs(float(signed))


def _cross_basis(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Kies de minst evenwijdige wereldas voor numerieke stabiliteit.
    candidates = np.eye(3)
    helper = candidates[int(np.argmin(np.abs(candidates @ axis)))]
    first = _unit(np.cross(axis, helper))
    second = _unit(np.cross(axis, first))
    return first, second


def fit_cylinder_mesh(
    vertices_mm: Iterable[Iterable[float]],
    triangles: Iterable[Iterable[int]] | np.ndarray,
    *,
    radial_tolerance_mm: float = 0.35,
) -> CylinderFit:
    """Herken een gesloten rechte cilinder uit een driehoeksmesh.

    De fit combineert PCA-as, een 2D-cirkelfit en een onafhankelijke
    volumecontrole. Daardoor wordt een rechthoekige plaat niet alleen op basis
    van ongeveer gelijke bbox-maten ten onrechte als rondstaal geaccepteerd.
    """

    vertices = _as_points(vertices_mm, 3)
    faces = np.asarray(list(triangles), dtype=int)
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError("Driehoeken moeten drie indices bevatten")
    if len(vertices) < 8 or len(faces) < 8:
        raise ValueError("Te weinig meshdata voor betrouwbare cilinderherkenning")

    # Unieke geometriepunten voorkomen dat triangulatie-indexduplicaten wegen.
    points = np.unique(np.round(vertices, decimals=8), axis=0)
    origin = points.mean(axis=0)
    centered = points - origin
    covariance = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    axis = _unit(eigenvectors[:, int(np.argmax(eigenvalues))])
    # Deterministische richting maakt rapporten stabiel.
    dominant = int(np.argmax(np.abs(axis)))
    if axis[dominant] < 0:
        axis = -axis
    cross_u, cross_v = _cross_basis(axis)
    axial = centered @ axis
    cross = np.column_stack((centered @ cross_u, centered @ cross_v))

    circle = fit_circle_2d(cross, tolerance_mm=radial_tolerance_mm)
    minimum = float(np.min(axial))
    maximum = float(np.max(axial))
    length = maximum - minimum
    if length <= 1e-6:
        raise ValueError("Cilinderlengte is nul")
    radius = float(circle.radius_mm)
    diameter = 2.0 * radius
    if radius <= 1e-6:
        raise ValueError("Cilinderstraal is nul")

    axis_center = origin + cross_u * circle.center_xy[0] + cross_v * circle.center_xy[1]
    base = axis_center + axis * minimum
    actual_volume = _mesh_volume(vertices, faces)
    expected_volume = math.pi * radius * radius * length
    volume_delta = (
        (actual_volume - expected_volume) / expected_volume * 100.0
        if expected_volume > 1e-9
        else float("inf")
    )

    # Een langwerpig rondprofiel scoort hoog; zeer korte schijven blijven
    # herkenbaar maar krijgen een lagere automatische productievertrouwensscore.
    aspect = length / diameter
    aspect_score = min(1.0, max(0.35, aspect / 2.0))
    volume_score = math.exp(-((abs(volume_delta) / 1.0) ** 2))
    cross_spread = np.ptp(cross, axis=0)
    roundness_error = abs(float(cross_spread[0] - cross_spread[1])) / max(diameter, 1e-9)
    roundness_score = math.exp(-((roundness_error / 0.03) ** 2))
    confidence = max(
        0.0,
        min(1.0, circle.confidence * volume_score * roundness_score * aspect_score),
    )
    return CylinderFit(
        base_center_mm=tuple(float(value) for value in base),
        axis=tuple(float(value) for value in axis),
        length_mm=length,
        radius_mm=radius,
        diameter_mm=diameter,
        rms_residual_mm=circle.rms_residual_mm,
        max_residual_mm=circle.max_residual_mm,
        volume_delta_percent=volume_delta,
        confidence=confidence,
        point_count=len(points),
    )


def cylinder_shape(fit: CylinderFit) -> cq.Shape:
    return cq.Solid.makeCylinder(
        float(fit.radius_mm),
        float(fit.length_mm),
        cq.Vector(*fit.base_center_mm),
        cq.Vector(*fit.axis),
    )


def recognize_analytic_shape(
    vertices_mm: Iterable[Iterable[float]],
    triangles: Iterable[Iterable[int]] | np.ndarray,
    *,
    minimum_confidence: float = 0.92,
    radial_tolerance_mm: float = 0.35,
) -> AnalyticRecognition:
    """Probeer momenteel een rechte cilinder; geef altijd diagnostiek terug."""

    try:
        cylinder = fit_cylinder_mesh(
            vertices_mm,
            triangles,
            radial_tolerance_mm=radial_tolerance_mm,
        )
        diagnostics: dict[str, float | str] = {
            "diameter_mm": cylinder.diameter_mm,
            "length_mm": cylinder.length_mm,
            "rms_residual_mm": cylinder.rms_residual_mm,
            "max_residual_mm": cylinder.max_residual_mm,
            "volume_delta_percent": cylinder.volume_delta_percent,
            "confidence": cylinder.confidence,
        }
        if cylinder.confidence >= minimum_confidence:
            return AnalyticRecognition(
                kind="cylinder",
                confidence=cylinder.confidence,
                shape=cylinder_shape(cylinder),
                diagnostics=diagnostics,
            )
        return AnalyticRecognition(
            kind="unconfirmed-cylinder",
            confidence=cylinder.confidence,
            shape=None,
            diagnostics=diagnostics,
        )
    except Exception as exc:
        return AnalyticRecognition(
            kind="none",
            confidence=0.0,
            shape=None,
            diagnostics={"error": str(exc)},
        )
