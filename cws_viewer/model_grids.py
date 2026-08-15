"""IFC model-grid extraction for the CWS project viewer.

Grid axes are *reference presentation*, never manufacturing geometry.  They are
read from the SHA-verified IFC source behind the canonical project and rendered
as a separate viewer layer.  No IfcGrid/IfcGridAxis is materialised as a part,
and grid visibility cannot change geometry/manufacturing hashes.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Iterable

from cws_viewer.adapters.source_geometry import ProjectSourceResolver
from cws_viewer.math3d import Vector3


@dataclass(frozen=True, slots=True)
class GridAxis:
    source_id: str
    grid_id: str
    axis_tag: str
    family: str
    level_mm: float
    points: tuple[Vector3, ...]


@dataclass(frozen=True, slots=True)
class ModelGridCatalog:
    axes: tuple[GridAxis, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def levels(self) -> tuple[float, ...]:
        return tuple(sorted({round(axis.level_mm, 3) for axis in self.axes}))

    @property
    def axis_count(self) -> int:
        return len(self.axes)

    @property
    def default_visible_levels(self) -> tuple[float, ...]:
        levels = self.levels
        if not levels:
            return ()
        for value in levels:
            if abs(value) <= 1e-3:
                return (value,)
        return (min(levels, key=abs),)


def _coords(value: Any) -> tuple[float, float, float]:
    raw = tuple(float(v) for v in getattr(value, "Coordinates", ()) or ())
    if len(raw) >= 3:
        return raw[0], raw[1], raw[2]
    if len(raw) == 2:
        return raw[0], raw[1], 0.0
    if len(raw) == 1:
        return raw[0], 0.0, 0.0
    return 0.0, 0.0, 0.0


def _direction(value: Any) -> tuple[float, float, float]:
    raw = tuple(float(v) for v in getattr(value, "DirectionRatios", ()) or ())
    if len(raw) >= 3:
        xyz = raw[:3]
    elif len(raw) == 2:
        xyz = (raw[0], raw[1], 0.0)
    else:
        xyz = (1.0, 0.0, 0.0)
    length = math.sqrt(sum(v * v for v in xyz)) or 1.0
    return tuple(v / length for v in xyz)  # type: ignore[return-value]


def _curve_points(curve: Any, *, fallback_extent: float) -> tuple[tuple[float, float, float], ...]:
    if curve is None:
        return ()
    kind = str(curve.is_a()).upper()
    if kind == "IFCPOLYLINE":
        return tuple(_coords(point) for point in (getattr(curve, "Points", ()) or ()))
    if kind == "IFCINDEXEDPOLYCURVE":
        points = getattr(curve, "Points", None)
        coords = getattr(points, "CoordList", ()) if points is not None else ()
        result = []
        for row in coords or ():
            values = tuple(float(v) for v in row)
            result.append((values[0], values[1], values[2] if len(values) > 2 else 0.0))
        return tuple(result)
    if kind == "IFCCOMPOSITECURVE":
        merged: list[tuple[float, float, float]] = []
        for segment in getattr(curve, "Segments", ()) or ():
            points = _curve_points(getattr(segment, "ParentCurve", None), fallback_extent=fallback_extent)
            if not points:
                continue
            if merged and merged[-1] == points[0]:
                merged.extend(points[1:])
            else:
                merged.extend(points)
        return tuple(merged)
    if kind == "IFCTRIMMEDCURVE":
        return _curve_points(getattr(curve, "BasisCurve", None), fallback_extent=fallback_extent)
    if kind == "IFCLINE":
        point = _coords(getattr(curve, "Pnt", None))
        vector = getattr(curve, "Dir", None)
        orientation = getattr(vector, "Orientation", None)
        direction = _direction(orientation)
        magnitude = float(getattr(vector, "Magnitude", 1.0) or 1.0)
        direction = tuple(v * magnitude for v in direction)
        extent = max(float(fallback_extent), 10_000.0)
        norm = math.sqrt(sum(v * v for v in direction)) or 1.0
        unit = tuple(v / norm for v in direction)
        return (
            tuple(point[i] - unit[i] * extent for i in range(3)),
            tuple(point[i] + unit[i] * extent for i in range(3)),
        )
    return ()


def _transform(matrix: Any, point: tuple[float, float, float]) -> Vector3:
    try:
        x, y, z = point
        return Vector3(
            float(matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3]),
            float(matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3]),
            float(matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3]),
        )
    except Exception:
        return Vector3(*point)


def extract_project_model_grids(
    project: Any,
    *,
    project_package_path: str | Path,
    source_search_roots: Iterable[str | Path] = (),
    fallback_extent_mm: float = 50_000.0,
) -> ModelGridCatalog:
    """Extract all resolvable IFC grids behind a canonical project."""
    warnings: list[str] = []
    axes: list[GridAxis] = []
    resolver = ProjectSourceResolver(
        project,
        project_package_path=project_package_path,
        search_roots=source_search_roots,
    )
    try:
        import ifcopenshell
        from ifcopenshell.util.placement import get_local_placement
    except Exception as exc:
        return ModelGridCatalog((), (f"IfcOpenShell gridlaag niet beschikbaar: {exc}",))

    for source_id, source in sorted(dict(getattr(project, "sources", {}) or {}).items()):
        if str(getattr(source, "source_format", "") or "").upper() != "IFC":
            continue
        try:
            resolved = resolver.resolve(str(source_id))
            model = ifcopenshell.open(str(resolved.path))
        except Exception as exc:
            warnings.append(f"{source_id}: IFC-gridbron kon niet worden geopend: {exc}")
            continue
        try:
            grids = tuple(model.by_type("IfcGrid"))
        except Exception as exc:
            warnings.append(f"{source_id}: IfcGrid-query mislukt: {exc}")
            continue
        for grid_index, grid in enumerate(grids, start=1):
            grid_id = str(getattr(grid, "GlobalId", "") or f"grid-{grid_index}")
            try:
                matrix = get_local_placement(getattr(grid, "ObjectPlacement", None))
            except Exception:
                matrix = (
                    (1.0, 0.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0, 0.0),
                    (0.0, 0.0, 1.0, 0.0),
                    (0.0, 0.0, 0.0, 1.0),
                )
            families = (
                ("U", getattr(grid, "UAxes", ()) or ()),
                ("V", getattr(grid, "VAxes", ()) or ()),
                ("W", getattr(grid, "WAxes", ()) or ()),
            )
            for family, grid_axes in families:
                for axis_index, axis in enumerate(grid_axes, start=1):
                    tag = str(getattr(axis, "AxisTag", "") or f"{family}{axis_index}")
                    local = _curve_points(
                        getattr(axis, "AxisCurve", None),
                        fallback_extent=fallback_extent_mm,
                    )
                    if len(local) < 2:
                        warnings.append(f"{source_id}/{grid_id}/{tag}: ascurve niet ondersteund")
                        continue
                    world = tuple(_transform(matrix, point) for point in local)
                    level = sum(point.z for point in world) / len(world)
                    axes.append(
                        GridAxis(
                            source_id=str(source_id),
                            grid_id=grid_id,
                            axis_tag=tag,
                            family=family,
                            level_mm=round(float(level), 6),
                            points=world,
                        )
                    )
    axes.sort(key=lambda item: (item.source_id, item.level_mm, item.grid_id, item.family, item.axis_tag))
    return ModelGridCatalog(tuple(axes), tuple(warnings))


__all__ = ["GridAxis", "ModelGridCatalog", "extract_project_model_grids"]
