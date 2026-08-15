"""Deterministic IFC grid/stamien extraction for the CWS project viewer.

The grid catalogue is source-derived review/display metadata.  It never becomes
manufacturing geometry.  The parser uses the same dependency-light Part 21 graph
as the semantic importer and preserves IFC entity IDs for auditability.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

from cws_convertor.importers.ifc_project import _detect_units
from cws_convertor.importers.p21 import P21Document


_EPS = 1e-12


def _identity() -> tuple[tuple[float, float, float, float], ...]:
    return (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def _matmul(a, b):
    return tuple(
        tuple(sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4))
        for r in range(4)
    )


def _normalise(values: Iterable[float], fallback: tuple[float, float, float]) -> tuple[float, float, float]:
    raw = [float(v) for v in values][:3]
    raw += [0.0] * (3 - len(raw))
    n = math.sqrt(sum(v * v for v in raw))
    if n <= _EPS:
        return fallback
    return tuple(v / n for v in raw)  # type: ignore[return-value]


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b) -> float:
    return sum(a[i] * b[i] for i in range(3))


def _point(document: P21Document, entity_id: int | None) -> tuple[float, float, float]:
    if entity_id is None:
        return (0.0, 0.0, 0.0)
    entity = document.get(entity_id)
    if entity is None or entity.type_name != "IFCCARTESIANPOINT":
        return (0.0, 0.0, 0.0)
    values = entity.scalar(0, []) or []
    raw = [float(value) for value in values][:3]
    raw += [0.0] * (3 - len(raw))
    return tuple(raw)  # type: ignore[return-value]


def _direction(document: P21Document, entity_id: int | None, fallback: tuple[float, float, float]):
    if entity_id is None:
        return fallback
    entity = document.get(entity_id)
    if entity is None or entity.type_name != "IFCDIRECTION":
        return fallback
    return _normalise(entity.scalar(0, []) or [], fallback)


def _axis2placement(document: P21Document, entity_id: int | None):
    if entity_id is None:
        return _identity()
    entity = document.get(entity_id)
    if entity is None:
        return _identity()
    if entity.type_name == "IFCAXIS2PLACEMENT2D":
        p = _point(document, entity.ref(0))
        x = _direction(document, entity.ref(1), (1.0, 0.0, 0.0))
        x = _normalise((x[0], x[1], 0.0), (1.0, 0.0, 0.0))
        y = (-x[1], x[0], 0.0)
        return (
            (x[0], y[0], 0.0, p[0]),
            (x[1], y[1], 0.0, p[1]),
            (0.0, 0.0, 1.0, p[2]),
            (0.0, 0.0, 0.0, 1.0),
        )
    if entity.type_name != "IFCAXIS2PLACEMENT3D":
        return _identity()
    p = _point(document, entity.ref(0))
    z = _direction(document, entity.ref(1), (0.0, 0.0, 1.0))
    x0 = _direction(document, entity.ref(2), (1.0, 0.0, 0.0))
    x = _normalise(tuple(x0[i] - _dot(x0, z) * z[i] for i in range(3)), (1.0, 0.0, 0.0))
    y = _normalise(_cross(z, x), (0.0, 1.0, 0.0))
    x = _normalise(_cross(y, z), (1.0, 0.0, 0.0))
    return (
        (x[0], y[0], z[0], p[0]),
        (x[1], y[1], z[1], p[1]),
        (x[2], y[2], z[2], p[2]),
        (0.0, 0.0, 0.0, 1.0),
    )


def _local_placement(document: P21Document, entity_id: int | None, _active: set[int] | None = None):
    if entity_id is None:
        return _identity()
    active = _active if _active is not None else set()
    if entity_id in active:
        return _identity()
    entity = document.get(entity_id)
    if entity is None or entity.type_name != "IFCLOCALPLACEMENT":
        return _identity()
    active.add(entity_id)
    try:
        parent = _local_placement(document, entity.ref(0), active)
        relative = _axis2placement(document, entity.ref(1))
        return _matmul(parent, relative)
    finally:
        active.discard(entity_id)


def _transform_point(matrix, point, scale: float):
    x, y, z = (float(point[0]), float(point[1]), float(point[2]))
    return (
        (matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3]) * scale,
        (matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3]) * scale,
        (matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3]) * scale,
    )


def _polyline_points(document: P21Document, curve_id: int | None) -> tuple[tuple[float, float, float], ...]:
    if curve_id is None:
        return ()
    curve = document.get(curve_id)
    if curve is None:
        return ()
    if curve.type_name == "IFCPOLYLINE":
        return tuple(_point(document, ref) for ref in curve.refs(0))
    if curve.type_name == "IFCCOMPOSITECURVE":
        values: list[tuple[float, float, float]] = []
        for segment_id in curve.refs(0):
            segment = document.get(segment_id)
            if segment is None or segment.type_name != "IFCCOMPOSITECURVESEGMENT":
                continue
            points = list(_polyline_points(document, segment.ref(2)))
            if segment.string(1).upper() == "F":
                points.reverse()
            if values and points and math.dist(values[-1], points[0]) <= 1e-9:
                points = points[1:]
            values.extend(points)
        return tuple(values)
    return ()


def _axis_record(document: P21Document, axis_id: int, family: str, transform, scale: float) -> tuple[dict[str, Any] | None, str | None]:
    axis = document.get(axis_id)
    if axis is None or axis.type_name != "IFCGRIDAXIS":
        return None, f"#{axis_id} is geen IFCGRIDAXIS"
    points = _polyline_points(document, axis.ref(1))
    if len(points) < 2:
        curve = document.get(axis.ref(1))
        kind = "ontbrekend" if curve is None else curve.type_name
        return None, f"Grid-as #{axis_id} ({axis.string(0)}) gebruikt niet-ondersteunde curve {kind}"
    world = tuple(_transform_point(transform, point, scale) for point in points)
    return {
        "source_entity_id": str(axis_id),
        "tag": axis.string(0) or str(axis_id),
        "family": family,
        "same_sense": axis.string(2).upper() != "F",
        "points_mm": [list(point) for point in world],
    }, None


def extract_ifc_grid_catalog_from_document(
    document: P21Document,
    *,
    source_id: str = "",
    source_file: str = "",
) -> dict[str, Any]:
    """Return serialisable IFC grid metadata from an already parsed document."""
    units = _detect_units(document)
    scale = float(units.length_to_mm)
    grids: list[dict[str, Any]] = []
    warnings: list[str] = []

    for grid in document.iter_type("IFCGRID"):
        transform = _local_placement(document, grid.ref(5))
        axes: list[dict[str, Any]] = []
        for family, index in (("U", 7), ("V", 8), ("W", 9)):
            for axis_id in grid.refs(index):
                record, warning = _axis_record(document, axis_id, family, transform, scale)
                if record is not None:
                    axes.append(record)
                if warning:
                    warnings.append(warning)
        if not axes:
            continue
        origin = _transform_point(transform, (0.0, 0.0, 0.0), scale)
        grids.append(
            {
                "source_entity_id": str(grid.entity_id),
                "name": grid.string(2) or f"Grid {grid.entity_id}",
                "object_type": grid.string(4),
                "elevation_mm": float(origin[2]),
                "origin_mm": list(origin),
                "axes": axes,
            }
        )

    grids.sort(key=lambda item: (round(float(item["elevation_mm"]), 6), str(item["name"]), int(item["source_entity_id"])))
    return {
        "schema": "cws-ifc-grid-catalog-1.0",
        "source_id": str(source_id),
        "source_file": source_file or document.path.name,
        "source_schema": document.schema,
        "units_to_mm": scale,
        "grid_count": len(grids),
        "axis_count": sum(len(grid["axes"]) for grid in grids),
        "grids": grids,
        "warnings": list(dict.fromkeys(warnings)),
    }


def extract_ifc_grid_catalog(source_path: str | Path, *, source_id: str = "") -> dict[str, Any]:
    """Parse one IFC source and return serialisable grid metadata in millimetres."""
    path = Path(source_path).expanduser().resolve()
    document = P21Document.load(path)
    try:
        return extract_ifc_grid_catalog_from_document(
            document, source_id=source_id, source_file=path.name
        )
    finally:
        document.release_caches()


__all__ = ["extract_ifc_grid_catalog", "extract_ifc_grid_catalog_from_document"]
