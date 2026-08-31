"""Cached thumbnails derived from real IFC world-coordinate geometry."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Iterable
import os


def _cache_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CWS" / "model-thumbnails"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _cache_path(source: Path) -> Path:
    stat = source.stat()
    key = sha256(f"{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")).hexdigest()
    return _cache_root() / f"{key}.png"


def _project_sidecar(source: Path) -> Path:
    return source.with_suffix(".thumbnail.png")


def create_ifc_thumbnail(source_path: str | Path, output_path: str | Path | None = None, *, max_shapes: int = 900) -> Path | None:
    source = Path(source_path).expanduser().resolve()
    if not source.is_file() or source.suffix.casefold() != ".ifc":
        return None
    target = Path(output_path).expanduser().resolve() if output_path else _cache_path(source)
    if target.is_file() and target.stat().st_size > 512:
        return target
    try:
        import ifcopenshell
        import ifcopenshell.geom
        from PIL import Image, ImageDraw
    except Exception:
        return None
    model = ifcopenshell.open(str(source))
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    clouds: list[tuple[list[tuple[float, float]], tuple[int, int, int]]] = []
    all_points: list[tuple[float, float]] = []
    products: Iterable[object] = model.by_type("IfcProduct")
    for index, product in enumerate(products):
        if index >= max_shapes:
            break
        if getattr(product, "Representation", None) is None:
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
            vertices = list(shape.geometry.verts)
        except Exception:
            continue
        points: list[tuple[float, float]] = []
        for offset in range(0, len(vertices) - 2, 3):
            x, y, z = float(vertices[offset]), float(vertices[offset + 1]), float(vertices[offset + 2])
            points.append((x - y * 0.72, z + (x + y) * 0.22))
        if not points:
            continue
        xs = [item[0] for item in points]
        ys = [item[1] for item in points]
        bounds = [(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))]
        color = (45, 123, 157) if product.is_a("IfcBeam") else (59, 92, 132) if product.is_a("IfcColumn") else (110, 139, 85) if product.is_a("IfcMember") else (125, 145, 164)
        clouds.append((bounds, color))
        all_points.extend(bounds)
    if not all_points:
        return None
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    width, height, margin = 840, 448, 28
    sx = (width - 2 * margin) / max(max_x - min_x, 1e-9)
    sy = (height - 2 * margin) / max(max_y - min_y, 1e-9)
    scale = min(sx, sy)
    image = Image.new("RGB", (width, height), "#f5f8fb")
    draw = ImageDraw.Draw(image, "RGBA")
    def mapped(point: tuple[float, float]) -> tuple[float, float]:
        return margin + (point[0] - min_x) * scale, height - margin - (point[1] - min_y) * scale
    for bounds, color in sorted(clouds, key=lambda item: sum(point[1] for point in item[0])):
        polygon = [mapped(point) for point in bounds]
        draw.polygon(polygon, fill=(*color, 180), outline=(25, 52, 75, 230), width=2)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp.png")
    image.save(temporary, format="PNG", optimize=True)
    temporary.replace(target)
    return target


def thumbnail_for_recent(source_path: str | Path, *, render_if_missing: bool = True) -> Path | None:
    source = Path(source_path).expanduser().resolve()
    if source.suffix.casefold() == ".cwscproj":
        sidecar = _project_sidecar(source)
        return sidecar if sidecar.is_file() else None
    if source.suffix.casefold() == ".ifc":
        cached = _cache_path(source)
        if cached.is_file():
            return cached
        return create_ifc_thumbnail(source, cached) if render_if_missing else None
    return None


__all__ = ["create_ifc_thumbnail", "thumbnail_for_recent"]

