"""Cached, presentation-quality thumbnails derived from real IFC geometry."""

from __future__ import annotations

from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Iterable
import zipfile


_RENDERER_VERSION = "realistic-ifc-v2"
_IMAGE_SIZE = (840, 448)
_MAX_TRIANGLES = 110_000
_STRUCTURAL_TYPES = {
    "IfcBeam",
    "IfcBuildingElementProxy",
    "IfcColumn",
    "IfcCurtainWall",
    "IfcFooting",
    "IfcMember",
    "IfcPlate",
    "IfcRailing",
    "IfcRamp",
    "IfcRoof",
    "IfcSlab",
    "IfcStair",
    "IfcWall",
    "IfcWallStandardCase",
}
_TYPE_COLORS = {
    "IfcBeam": (69, 91, 116),
    "IfcColumn": (55, 78, 106),
    "IfcMember": (92, 112, 132),
    "IfcPlate": (100, 116, 132),
    "IfcRailing": (221, 168, 43),
    "IfcStair": (84, 100, 117),
    "IfcSlab": (155, 158, 157),
    "IfcRoof": (112, 126, 139),
    "IfcWall": (166, 169, 166),
    "IfcWallStandardCase": (166, 169, 166),
    "IfcFooting": (137, 139, 137),
    "IfcBuildingElementProxy": (115, 130, 142),
}


def _cache_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CWS" / "model-thumbnails"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _cache_path(source: Path) -> Path:
    stat = source.stat()
    identity = f"{_RENDERER_VERSION}|{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
    return _cache_root() / f"{sha256(identity.encode('utf-8')).hexdigest()}.png"


def _project_sidecar(source: Path) -> Path:
    return source.with_suffix(".thumbnail.png")


def _metadata_path(thumbnail: Path) -> Path:
    return thumbnail.with_suffix(f"{thumbnail.suffix}.json")


def _render_is_current(thumbnail: Path, owner: Path | None = None) -> bool:
    if not thumbnail.is_file() or thumbnail.stat().st_size <= 512:
        return False
    if owner is not None and thumbnail.stat().st_mtime_ns < owner.stat().st_mtime_ns:
        return False
    try:
        metadata = json.loads(_metadata_path(thumbnail).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    return str(metadata.get("renderer") or "") == _RENDERER_VERSION


def _write_metadata(thumbnail: Path, source: Path) -> None:
    stat = source.stat()
    metadata = {
        "renderer": _RENDERER_VERSION,
        "source_name": source.name,
        "source_size": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
        "width": _IMAGE_SIZE[0],
        "height": _IMAGE_SIZE[1],
    }
    target = _metadata_path(thumbnail)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    os.replace(temporary, target)


def _even_sample(values: list[object], count: int) -> list[object]:
    if count <= 0:
        return []
    if len(values) <= count:
        return values
    if count == 1:
        return [values[len(values) // 2]]
    return [values[round(index * (len(values) - 1) / (count - 1))] for index in range(count)]


def _representative_products(products: Iterable[object], max_shapes: int) -> list[object]:
    represented = [item for item in products if getattr(item, "Representation", None) is not None]
    if len(represented) <= max_shapes:
        return represented
    primary = [item for item in represented if str(item.is_a()) in _STRUCTURAL_TYPES]
    secondary = [item for item in represented if str(item.is_a()) not in _STRUCTURAL_TYPES]
    if len(primary) >= max_shapes:
        return _even_sample(primary, max_shapes)
    return [*primary, *_even_sample(secondary, max_shapes - len(primary))]


def _product_color(product: object) -> tuple[int, int, int]:
    entity_type = str(product.is_a())
    if entity_type in _TYPE_COLORS:
        return _TYPE_COLORS[entity_type]
    if "Window" in entity_type or "Curtain" in entity_type:
        return 92, 145, 173
    if "Door" in entity_type:
        return 139, 111, 77
    if "Pipe" in entity_type or "Duct" in entity_type:
        return 102, 139, 151
    return 126, 140, 151


def _shade(color: tuple[int, int, int], normal: tuple[float, float, float]) -> tuple[int, int, int, int]:
    light = (-0.32, -0.42, 0.85)
    incidence = abs(normal[0] * light[0] + normal[1] * light[1] + normal[2] * light[2])
    factor = 0.58 + min(1.0, incidence) * 0.48
    return tuple(min(255, max(0, int(channel * factor))) for channel in color) + (255,)


def _normal(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    third: tuple[float, float, float],
) -> tuple[float, float, float]:
    ax, ay, az = second[0] - first[0], second[1] - first[1], second[2] - first[2]
    bx, by, bz = third[0] - first[0], third[1] - first[1], third[2] - first[2]
    nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length <= 1e-12:
        return 0.0, 0.0, 1.0
    return nx / length, ny / length, nz / length


def _project(point: tuple[float, float, float]) -> tuple[float, float, float]:
    yaw = math.radians(38.0)
    cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
    rotated_x = cos_yaw * point[0] - sin_yaw * point[1]
    rotated_y = sin_yaw * point[0] + cos_yaw * point[1]
    return rotated_x, point[2] * 0.94 - rotated_y * 0.34, rotated_y * 0.94 + point[2] * 0.34


def _robust_range(values: list[float]) -> tuple[float, float]:
    ordered = sorted(values)
    if len(ordered) < 400:
        return ordered[0], ordered[-1]
    inset = max(1, int(len(ordered) * 0.006))
    lower, upper = ordered[inset], ordered[-inset - 1]
    if upper - lower < (ordered[-1] - ordered[0]) * 0.15:
        return ordered[0], ordered[-1]
    return lower, upper


def create_ifc_thumbnail(
    source_path: str | Path,
    output_path: str | Path | None = None,
    *,
    max_shapes: int = 1200,
    force: bool = False,
) -> Path | None:
    """Render a sharp axonometric snapshot from actual IFC triangle meshes."""

    source = Path(source_path).expanduser().resolve()
    if not source.is_file() or source.suffix.casefold() != ".ifc":
        return None
    target = Path(output_path).expanduser().resolve() if output_path else _cache_path(source)
    if not force and _render_is_current(target):
        return target
    try:
        import ifcopenshell
        import ifcopenshell.geom
        from PIL import Image, ImageDraw, ImageFilter
    except Exception:
        return None

    model = ifcopenshell.open(str(source))
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    products = _representative_products(model.by_type("IfcProduct"), max(1, int(max_shapes)))
    if not products:
        return None

    triangle_cap = max(24, min(320, _MAX_TRIANGLES // len(products)))
    triangles: list[
        tuple[
            tuple[float, float, float],
            tuple[float, float, float],
            tuple[float, float, float],
            tuple[int, int, int],
        ]
    ] = []
    for product in products:
        try:
            geometry = ifcopenshell.geom.create_shape(settings, product).geometry
            vertices = tuple(float(value) for value in geometry.verts)
            faces = tuple(int(value) for value in geometry.faces)
        except Exception:
            continue
        triangle_count = len(faces) // 3
        if triangle_count <= 0:
            continue
        stride = max(1, math.ceil(triangle_count / triangle_cap))
        color = _product_color(product)
        for triangle_index in range(0, triangle_count, stride):
            face_offset = triangle_index * 3
            indices = faces[face_offset : face_offset + 3]
            if len(indices) != 3 or any(index < 0 or index * 3 + 2 >= len(vertices) for index in indices):
                continue
            points = tuple(
                (
                    vertices[index * 3],
                    vertices[index * 3 + 1],
                    vertices[index * 3 + 2],
                )
                for index in indices
            )
            triangles.append((points[0], points[1], points[2], color))

    if not triangles:
        return None
    projected = [
        (_project(first), _project(second), _project(third), color, _normal(first, second, third))
        for first, second, third, color in triangles
    ]
    projected_points = [
        point
        for first, second, third, _color, _face_normal in projected
        for point in (first, second, third)
    ]
    min_x, max_x = _robust_range([point[0] for point in projected_points])
    min_y, max_y = _robust_range([point[1] for point in projected_points])
    width, height = _IMAGE_SIZE
    margin_x, margin_y = 38, 30
    scale = min(
        (width - margin_x * 2) / max(max_x - min_x, 1e-9),
        (height - margin_y * 2) / max(max_y - min_y, 1e-9),
    )

    def mapped(point: tuple[float, float, float]) -> tuple[float, float]:
        return (
            margin_x + (point[0] - min_x) * scale,
            height - margin_y - (point[1] - min_y) * scale,
        )

    image = Image.new("RGBA", (width, height), (244, 248, 252, 255))
    background = ImageDraw.Draw(image)
    for row in range(height):
        ratio = row / max(height - 1, 1)
        tone = int(250 - 13 * ratio)
        background.line((0, row, width, row), fill=(tone, tone + 2, min(255, tone + 5), 255))
    background.line((0, height - 38, width, height - 38), fill=(183, 195, 205, 90), width=1)

    ordered = sorted(projected, key=lambda item: (item[0][2] + item[1][2] + item[2][2]) / 3.0)
    shadow_mask = Image.new("L", (width, height), 0)
    shadow_draw = ImageDraw.Draw(shadow_mask)
    for first, second, third, _color, _face_normal in ordered:
        shadow_draw.polygon(
            [(point[0] + 5, point[1] + 8) for point in (mapped(first), mapped(second), mapped(third))],
            fill=42,
        )
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=5.0))
    shadow = Image.new("RGBA", (width, height), (29, 44, 58, 0))
    shadow.putalpha(shadow_mask)
    image = Image.alpha_composite(image, shadow)

    drawing = ImageDraw.Draw(image)
    for first, second, third, color, face_normal in ordered:
        polygon = [mapped(first), mapped(second), mapped(third)]
        drawing.polygon(
            polygon,
            fill=_shade(color, face_normal),
            outline=(35, 51, 67, 78),
            width=1,
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp.png")
    image.convert("RGB").save(temporary, format="PNG", optimize=True)
    os.replace(temporary, target)
    _write_metadata(target, source)
    return target


def _embedded_ifc(source: Path, destination: Path) -> Path | None:
    try:
        with zipfile.ZipFile(source, "r") as archive:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            embedded = list(manifest.get("embedded_sources") or [])
            record = next(
                (item for item in embedded if str(item.get("path") or "").casefold().endswith(".ifc")),
                None,
            )
            if record is None:
                return None
            archive_name = str(record.get("path") or "")
            pure_path = PurePosixPath(archive_name)
            if pure_path.is_absolute() or ".." in pure_path.parts:
                return None
            expected_digest = str(record.get("sha256") or "").casefold()
            digest = sha256()
            with archive.open(archive_name, "r") as reader, destination.open("wb") as writer:
                while True:
                    chunk = reader.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    writer.write(chunk)
            if expected_digest and digest.hexdigest().casefold() != expected_digest:
                destination.unlink(missing_ok=True)
                return None
            return destination
    except (OSError, KeyError, ValueError, zipfile.BadZipFile):
        return None


def _refresh_project_thumbnail(source: Path, sidecar: Path) -> Path | None:
    with tempfile.TemporaryDirectory(prefix="project-preview-", dir=_cache_root()) as temporary:
        embedded = _embedded_ifc(source, Path(temporary) / "project.ifc")
        if embedded is None:
            return None
        return create_ifc_thumbnail(embedded, sidecar, force=True)


def thumbnail_for_recent(source_path: str | Path, *, render_if_missing: bool = True) -> Path | None:
    source = Path(source_path).expanduser().resolve()
    if source.suffix.casefold() == ".cwscproj":
        sidecar = _project_sidecar(source)
        if _render_is_current(sidecar, source):
            return sidecar
        return _refresh_project_thumbnail(source, sidecar) if render_if_missing else None
    if source.suffix.casefold() == ".ifc":
        cached = _cache_path(source)
        if _render_is_current(cached):
            return cached
        return create_ifc_thumbnail(source, cached) if render_if_missing else None
    return None


__all__ = ["create_ifc_thumbnail", "thumbnail_for_recent"]
