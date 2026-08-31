from __future__ import annotations

import math
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from cws_convertor.drawings import DrawingProjectionModel
from cws_convertor.output import DocumentOutputService

SHEET_MM: dict[str, tuple[float, float]] = {
    "A4": (297.0, 210.0), "A3": (420.0, 297.0), "A2": (594.0, 420.0),
    "A1": (841.0, 594.0), "A0": (1189.0, 841.0),
}
STANDARD_SCALES = (1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000)


@dataclass(frozen=True, slots=True)
class DrawingOutput:
    png_path: Path | None
    pdf_path: Path | None
    warnings: tuple[str, ...] = ()
    scale_label: str = "Auto"


class EngineeringDrawingGenerator:
    def __init__(self, workspace: Any) -> None:
        self.workspace = workspace

    @staticmethod
    def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
        names = (
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        )
        for name in names:
            if Path(name).exists():
                return ImageFont.truetype(name, size=size)
        return ImageFont.load_default()

    @classmethod
    def _draw_logo(cls, draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
        """Draw the product mark as vectors so PNG and PDF never miss an asset."""
        draw.rounded_rectangle((x, y, x + 70, y + 42), radius=5, fill=(0, 78, 162))
        draw.text((x + 8, y + 5), "CWS", fill="white", font=cls._font(25, bold=True))
        draw.text((x + 82, y + 7), "CONVERTOR", fill=(20, 58, 99), font=cls._font(22, bold=True))
        draw.line((x + 82, y + 34, x + 236, y + 34), fill=(22, 112, 214), width=2)

    @staticmethod
    def _number(mapping: Mapping[str, Any], *names: str, default: float = 0.0) -> float:
        for name in names:
            value = mapping.get(name)
            if value not in (None, ""):
                try:
                    return float(str(value).replace(",", "."))
                except (TypeError, ValueError):
                    continue
        return float(default)

    @classmethod
    def _draw_feature_overlay(
        cls,
        draw: ImageDraw.ImageDraw,
        *,
        features: Sequence[Mapping[str, Any]],
        view: str,
        screen: np.ndarray,
        projected: np.ndarray,
        rectangle: tuple[int, int, int, int],
        scale: float,
        dimensions: bool,
        dimension_mode: str,
    ) -> None:
        if not features or view == "iso":
            return
        minimum, maximum = screen.min(axis=0), screen.max(axis=0)
        model_span = np.maximum(projected.max(axis=0) - projected.min(axis=0), 1.0)
        left, _top, _right, bottom = rectangle
        dimension_points: list[tuple[float, float, float, float, float]] = []

        for feature in features:
            kind = str(feature.get("kind") or feature.get("type") or "").lower()
            if kind in {"cut", "miter", "mitre", "saw_cut", "end_cut", "angle_cut"}:
                parameters = dict(feature.get("parameters") or feature)
                angle = cls._number(
                    parameters, "primary_angle_deg", "angle_deg", "saw_angle_deg", "miter_angle_deg"
                )
                if abs(angle) > 0.05:
                    at_end = str(parameters.get("end") or parameters.get("position") or "end").lower() not in {
                        "start", "front", "begin", "left",
                    }
                    cls._draw_angle_dimension(
                        draw,
                        center=(
                            float(maximum[0] if at_end else minimum[0]),
                            float((minimum[1] + maximum[1]) * 0.5),
                        ),
                        angle_deg=abs(angle),
                        reverse=at_end,
                    )
                continue
            if kind not in {"hole", "slot", "countersink", "countersunk_hole"}:
                continue
            parameters = dict(feature.get("parameters") or feature)
            side = str(
                feature.get("reference_side")
                or parameters.get("reference_side")
                or parameters.get("face")
                or ""
            ).strip().lower()
            visible = (
                not side
                or (view == "top" and (side in {"o", "u"} or any(token in side for token in ("top", "boven", "bottom", "onder", "flange"))))
                or (view == "front" and (side in {"v", "h"} or any(token in side for token in ("front", "voor", "back", "achter", "web"))))
                or (view == "side" and any(token in side for token in ("side", "zijde", "left", "right", "end", "kop")))
            )
            if not visible:
                continue

            x_mm = cls._number(
                parameters,
                "x_mm",
                "x",
                "offset_x_mm",
                "position_x_mm",
                "distance_x_mm",
            )
            y_mm = cls._number(
                parameters,
                "y_mm",
                "y",
                "offset_y_mm",
                "position_y_mm",
                "distance_y_mm",
            )
            if not (-0.02 * model_span[0] <= x_mm <= 1.02 * model_span[0]):
                continue
            if not (-0.02 * model_span[1] <= y_mm <= 1.02 * model_span[1]):
                centered_y = y_mm + float(model_span[1]) * 0.5
                if -0.02 * model_span[1] <= centered_y <= 1.02 * model_span[1]:
                    y_mm = centered_y
                else:
                    continue
            cx = float(minimum[0]) + (x_mm / float(model_span[0])) * float(maximum[0] - minimum[0])
            cy = float(maximum[1]) - (y_mm / float(model_span[1])) * float(maximum[1] - minimum[1])
            diameter = max(
                cls._number(
                    parameters,
                    "diameter_mm",
                    "diameter",
                    "d_mm",
                    "hole_diameter_mm",
                    "diameter_top_mm",
                    "diameter_bottom_mm",
                    "width_mm",
                    default=1.0,
                ),
                1.0,
            )
            radius = max(2.4, diameter * scale * 0.5)

            if kind == "slot":
                length = max(
                    cls._number(
                        parameters,
                        "length_mm",
                        "slot_length_mm",
                        "overall_length_mm",
                        default=diameter * 2.0,
                    ),
                    diameter,
                )
                half = max(0.0, (length - diameter) * scale * 0.5)
                angle = math.radians(cls._number(parameters, "angle_deg", "rotation_deg"))
                ux, uy = math.cos(angle), -math.sin(angle)
                vx, vy = -uy, ux
                points: list[tuple[float, float]] = []
                for index in range(13):
                    theta = math.pi * 0.5 + math.pi * index / 12.0
                    points.append((cx - ux * half + (ux * math.cos(theta) + vx * math.sin(theta)) * radius,
                                   cy - uy * half + (uy * math.cos(theta) + vy * math.sin(theta)) * radius))
                for index in range(13):
                    theta = -math.pi * 0.5 + math.pi * index / 12.0
                    points.append((cx + ux * half + (ux * math.cos(theta) + vx * math.sin(theta)) * radius,
                                   cy + uy * half + (uy * math.cos(theta) + vy * math.sin(theta)) * radius))
                draw.polygon(points, fill=(255, 255, 255))
                draw.line(points + [points[0]], fill=(20, 58, 99), width=2, joint="curve")
                callout = f"{diameter:g} x {length:g}"
            else:
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill="white", outline=(20, 58, 99), width=2)
                countersink = cls._number(
                    parameters,
                    "countersink_diameter_mm",
                    "outer_diameter_mm",
                    "head_diameter_mm",
                )
                if countersink > diameter:
                    outer = max(radius + 2.0, countersink * scale * 0.5)
                    draw.ellipse((cx - outer, cy - outer, cx + outer, cy + outer), outline=(20, 58, 99), width=1)
                callout = f"Ø{diameter:g}"

            blue = (22, 112, 214)
            draw.line((cx - radius - 4, cy, cx + radius + 4, cy), fill=blue, width=1)
            draw.line((cx, cy - radius - 4, cx, cy + radius + 4), fill=blue, width=1)
            draw.line((cx + radius, cy - radius, cx + radius + 22, cy - radius - 17), fill=blue, width=1)
            draw.text((cx + radius + 25, cy - radius - 26), callout, fill=blue, font=cls._font(12, bold=True))
            dimension_points.append((x_mm, y_mm, cx, cy, radius))

        if dimensions and dimension_mode != "Hoofdmaten" and dimension_points:
            x_points: dict[float, tuple[float, float, float, float, float]] = {}
            y_points: dict[float, tuple[float, float, float, float, float]] = {}
            for point in dimension_points:
                x_points.setdefault(round(point[0], 6), point)
                y_points.setdefault(round(point[1], 6), point)
            for level, point in enumerate(sorted(x_points.values(), key=lambda item: item[0])[:8]):
                x_mm, _y_mm, cx, cy, radius = point
                datum_y = min(float(bottom - 10), float(maximum[1] + 42 + level * 16))
                cls._draw_dimension(
                    draw,
                    orientation="horizontal",
                    start=(float(minimum[0]), datum_y),
                    end=(cx, datum_y),
                    witness_start=(float(minimum[0]), float(maximum[1]) + 4),
                    witness_end=(cx, cy + radius + 4),
                    label=f"{max(0.0, x_mm):,.1f} mm",
                )
            for level, point in enumerate(sorted(y_points.values(), key=lambda item: item[1])[:6]):
                _x_mm, y_mm, cx, cy, radius = point
                datum_x = max(float(left + 10), float(minimum[0] - 44 - level * 20))
                cls._draw_dimension(
                    draw,
                    orientation="vertical",
                    start=(datum_x, float(maximum[1])),
                    end=(datum_x, cy),
                    witness_start=(float(minimum[0]) - 4, float(maximum[1])),
                    witness_end=(cx - radius - 4, cy),
                    label=f"{max(0.0, y_mm):,.1f} mm",
                )

    def _resolve(self, entity_id: str | None) -> tuple[Any, Any, str, np.ndarray, np.ndarray]:
        project = self.workspace.project
        entity = None
        resolved_entity_id = str(entity_id or "")
        if entity_id:
            for collection in (project.parts, project.assemblies, project.purchased_items, project.fasteners, project.welds):
                if entity_id in collection:
                    entity = collection[entity_id]
                    break
        if entity_id and entity is None:
            raise ValueError(f"Onderdeel {entity_id} bestaat niet in het actieve project")
        if entity is None:
            fallback = next(iter(project.parts.items()), None)
            if fallback is not None:
                resolved_entity_id, entity = str(fallback[0]), fallback[1]
        if entity is None:
            raise ValueError("Geen maakbaar onderdeel beschikbaar voor de tekening")
        node_id = self.workspace.interaction.node_for_entity(resolved_entity_id)
        node = self.workspace.controller.index.node(node_id)
        if node.geometry_id is None:
            raise ValueError("Het geselecteerde onderdeel heeft geen tekenbare 3D-geometrie")
        mesh = self.workspace.load_result.repository.get(node.geometry_id)
        if mesh is None:
            raise ValueError("De 3D-geometrie van het geselecteerde onderdeel is nog niet geladen")
        vertices = np.asarray(mesh.vertices, dtype=float).reshape((-1, 3))
        triangles = np.asarray(mesh.triangles, dtype=int).reshape((-1, 3))
        if vertices.size == 0 or triangles.size == 0:
            raise ValueError("Het geselecteerde onderdeel heeft lege 3D-geometrie")
        return entity, node, resolved_entity_id, self._principal_orientation(vertices), triangles

    @staticmethod
    def _principal_orientation(vertices: np.ndarray) -> np.ndarray:
        centered = vertices - vertices.mean(axis=0)
        covariance = np.cov(centered, rowvar=False)
        values, vectors = np.linalg.eigh(covariance)
        axes = vectors[:, np.argsort(values)[::-1]]
        if np.linalg.det(axes) < 0.0:
            axes[:, 2] *= -1.0
        oriented = centered @ axes
        extreme = int(np.argmax(np.abs(oriented[:, 0])))
        if oriented[extreme, 0] < 0.0:
            oriented[:, 0] *= -1.0
        return oriented

    @staticmethod
    def _basis(view: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return DrawingProjectionModel.basis(view)

    @classmethod
    def _project(cls, vertices: np.ndarray, view: str) -> tuple[np.ndarray, np.ndarray]:
        return DrawingProjectionModel.project(vertices, view)

    @staticmethod
    def _visible_edges(
        triangles: np.ndarray,
        vertices: np.ndarray,
        direction: np.ndarray,
    ) -> set[tuple[int, int]]:
        return set(DrawingProjectionModel.visible_edges(triangles, vertices, direction))

    @classmethod
    def _draw_dimension(
        cls,
        draw: ImageDraw.ImageDraw,
        *,
        orientation: str,
        start: tuple[float, float],
        end: tuple[float, float],
        witness_start: tuple[float, float],
        witness_end: tuple[float, float],
        label: str,
    ) -> None:
        blue = (0, 102, 220)
        draw.line((*witness_start, *start), fill=blue, width=1)
        draw.line((*witness_end, *end), fill=blue, width=1)
        draw.line((*start, *end), fill=blue, width=2)
        if orientation == "horizontal":
            draw.line((start[0], start[1], start[0] + 8, start[1] - 5), fill=blue, width=2)
            draw.line((start[0], start[1], start[0] + 8, start[1] + 5), fill=blue, width=2)
            draw.line((end[0], end[1], end[0] - 8, end[1] - 5), fill=blue, width=2)
            draw.line((end[0], end[1], end[0] - 8, end[1] + 5), fill=blue, width=2)
            box = draw.textbbox((0, 0), label, font=cls._font(14))
            tx = (start[0] + end[0] - (box[2] - box[0])) * 0.5
            ty = start[1] - 25
        else:
            draw.line((start[0], start[1], start[0] - 5, start[1] + 8), fill=blue, width=2)
            draw.line((start[0], start[1], start[0] + 5, start[1] + 8), fill=blue, width=2)
            draw.line((end[0], end[1], end[0] - 5, end[1] - 8), fill=blue, width=2)
            draw.line((end[0], end[1], end[0] + 5, end[1] - 8), fill=blue, width=2)
            box = draw.textbbox((0, 0), label, font=cls._font(14))
            tx = start[0] - (box[2] - box[0]) - 9
            ty = (start[1] + end[1] - (box[3] - box[1])) * 0.5
        draw.rounded_rectangle((tx - 3, ty - 2, tx + (box[2] - box[0]) + 3, ty + (box[3] - box[1]) + 3), radius=2, fill="white")
        draw.text((tx, ty), label, fill=blue, font=cls._font(14))

    @classmethod
    def _draw_angle_dimension(
        cls,
        draw: ImageDraw.ImageDraw,
        *,
        center: tuple[float, float],
        angle_deg: float,
        reverse: bool = False,
    ) -> None:
        blue = (0, 102, 220)
        radius = 34.0
        cx, cy = center
        sign = -1.0 if reverse else 1.0
        base_angle = 180.0 if reverse else 0.0
        target_angle = base_angle + sign * max(0.1, min(179.9, float(angle_deg)))
        for value in (base_angle, target_angle):
            radians = math.radians(value)
            draw.line(
                (cx, cy, cx + math.cos(radians) * (radius + 12), cy - math.sin(radians) * (radius + 12)),
                fill=blue,
                width=2,
            )
        start, end = sorted((base_angle, target_angle))
        draw.arc((cx - radius, cy - radius, cx + radius, cy + radius), start=360.0 - end, end=360.0 - start, fill=blue, width=2)
        draw.text((cx - 18, cy - radius - 24), f"{float(angle_deg):g}\N{DEGREE SIGN}", fill=blue, font=cls._font(13, bold=True))

    @staticmethod
    def _rectangles(count: int, area: tuple[int, int, int, int]) -> list[tuple[int, int, int, int]]:
        left, top, right, bottom = area
        gap = 22
        if count <= 1:
            return [(left, top, right, bottom)]
        if count == 2:
            middle = (left + right) // 2
            return [(left, top, middle - gap // 2, bottom), (middle + gap // 2, top, right, bottom)]
        middle_x = (left + right) // 2
        middle_y = (top + bottom) // 2
        result = [
            (left, top, middle_x - gap // 2, middle_y - gap // 2),
            (middle_x + gap // 2, top, right, middle_y - gap // 2),
            (left, middle_y + gap // 2, middle_x - gap // 2, bottom),
            (middle_x + gap // 2, middle_y + gap // 2, right, bottom),
        ]
        if count == 3:
            result[2] = (left, middle_y + gap // 2, right, bottom)
        return result[:count]

    @staticmethod
    def _requested_scale(value: str) -> int | None:
        text = str(value).strip().lower()
        if text in {"", "auto", "automatisch"}:
            return None
        try:
            return max(1, int(float(text.split(":")[-1].replace(",", "."))))
        except ValueError:
            return None

    @staticmethod
    def _next_standard_scale(required: float) -> int:
        for value in STANDARD_SCALES:
            if value + 1.0e-9 >= required:
                return value
        return int(math.ceil(required / 500.0) * 500.0)

    def _fit_scale(
        self,
        vertices: np.ndarray,
        views: Sequence[str],
        rectangles: Sequence[tuple[int, int, int, int]],
        px_per_mm: float,
        requested: int | None,
    ) -> tuple[int, bool]:
        required = 1.0
        for view, rectangle in zip(views, rectangles):
            projected, _depths = self._project(vertices, view)
            span = np.maximum(projected.max(axis=0) - projected.min(axis=0), 1.0)
            width = max(1.0, float(rectangle[2] - rectangle[0] - 150)) / px_per_mm
            height = max(1.0, float(rectangle[3] - rectangle[1] - 145)) / px_per_mm
            required = max(required, float(span[0] / width), float(span[1] / height))
        fitted = self._next_standard_scale(required * 1.05)
        if requested is None:
            return fitted, False
        return max(requested, fitted), fitted > requested

    def _draw_view(
        self,
        draw: ImageDraw.ImageDraw,
        vertices: np.ndarray,
        triangles: np.ndarray,
        view: str,
        rectangle: tuple[int, int, int, int],
        label: str,
        denominator: int,
        px_per_mm: float,
        dimensions: bool,
        dimension_mode: str,
        manual_dimensions: Sequence[Mapping[str, Any]],
        production_features: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        left, top, right, bottom = rectangle
        draw.rounded_rectangle(rectangle, radius=6, outline=(190, 205, 221), width=2, fill=(252, 253, 255))
        draw.text((left + 14, top + 11), label, fill=(28, 68, 112), font=self._font(19, bold=True))
        projected, depths = self._project(vertices, view)
        _u, _v, direction = self._basis(view)
        center = (projected.min(axis=0) + projected.max(axis=0)) * 0.5
        scale = px_per_mm / float(denominator)
        usable_left, usable_top = left + (78 if dimensions else 32), top + 48
        usable_right, usable_bottom = right - 40, bottom - (92 if dimensions else 25)
        screen_center = np.array(((usable_left + usable_right) * 0.5, (usable_top + usable_bottom) * 0.5))
        screen = np.empty_like(projected)
        screen[:, 0] = (projected[:, 0] - center[0]) * scale + screen_center[0]
        screen[:, 1] = screen_center[1] - ((projected[:, 1] - center[1]) * scale)

        # Paint back-to-front faces first. This removes the transparent
        # wireframe appearance while retaining crisp manufacturing edges.
        face_depths = depths[triangles].mean(axis=1)
        for triangle_index in np.argsort(face_depths):
            triangle = triangles[int(triangle_index)]
            points = [(float(screen[int(index), 0]), float(screen[int(index), 1])) for index in triangle]
            a, b, c = (vertices[int(index)] for index in triangle)
            normal = np.cross(b - a, c - a)
            normal_length = float(np.linalg.norm(normal))
            facing = abs(float(np.dot(normal / normal_length, direction))) if normal_length > 1.0e-9 else 0.0
            shade = int(round(236.0 - 43.0 * facing))
            draw.polygon(points, fill=(shade - 10, shade, min(255, shade + 12)))

        for first, second in self._visible_edges(triangles, vertices, direction):
            draw.line((float(screen[first, 0]), float(screen[first, 1]), float(screen[second, 0]), float(screen[second, 1])), fill=(24, 60, 96), width=2)
        self._draw_feature_overlay(
            draw,
            features=production_features,
            view=view,
            screen=screen,
            projected=projected,
            rectangle=rectangle,
            scale=scale,
            dimensions=dimensions,
            dimension_mode=str(dimension_mode),
        )
        if dimensions:
            minimum, maximum = screen.min(axis=0), screen.max(axis=0)
            model_span = projected.max(axis=0) - projected.min(axis=0)
            x0, x1 = float(minimum[0]), float(maximum[0])
            y0, y1 = float(maximum[1]), float(minimum[1])
            dimension_y = min(float(bottom - 23), float(maximum[1] + 28))
            self._draw_dimension(
                draw, orientation="horizontal", start=(x0, dimension_y), end=(x1, dimension_y),
                witness_start=(x0, float(maximum[1]) + 4), witness_end=(x1, float(maximum[1]) + 4),
                label=f"{float(model_span[0]):,.1f} mm",
            )
            if view != "iso":
                dimension_x = max(float(left + 20), float(minimum[0] - 28))
                self._draw_dimension(
                    draw, orientation="vertical", start=(dimension_x, y0), end=(dimension_x, y1),
                    witness_start=(float(minimum[0]) - 4, y0), witness_end=(float(minimum[0]) - 4, y1),
                    label=f"{float(model_span[1]):,.1f} mm",
                )

            projected_min = projected.min(axis=0)
            for level, dimension in enumerate(item for item in manual_dimensions if str(item.get("view", "")) in {view, "3d" if view == "iso" else view}):
                axis = str(dimension.get("axis", "horizontal"))
                start_offset = float(dimension.get("start", 0.0))
                end_offset = float(dimension.get("end", 0.0))
                custom_label = str(dimension.get("label", "")).strip() or f"{abs(end_offset - start_offset):,.1f} mm"
                if axis == "vertical":
                    start_y = screen_center[1] - ((projected_min[1] + start_offset - center[1]) * scale)
                    end_y = screen_center[1] - ((projected_min[1] + end_offset - center[1]) * scale)
                    dimension_x = max(float(left + 14), float(minimum[0] - 52 - level * 22))
                    self._draw_dimension(
                        draw, orientation="vertical", start=(dimension_x, start_y), end=(dimension_x, end_y),
                        witness_start=(float(minimum[0]) - 4, start_y), witness_end=(float(minimum[0]) - 4, end_y), label=custom_label,
                    )
                else:
                    start_x = (projected_min[0] + start_offset - center[0]) * scale + screen_center[0]
                    end_x = (projected_min[0] + end_offset - center[0]) * scale + screen_center[0]
                    custom_y = min(float(bottom - 14), float(maximum[1] + 50 + level * 22))
                    self._draw_dimension(
                        draw, orientation="horizontal", start=(start_x, custom_y), end=(end_x, custom_y),
                        witness_start=(start_x, float(maximum[1]) + 4), witness_end=(end_x, float(maximum[1]) + 4), label=custom_label,
                    )

    def generate(
        self,
        output_directory: str | Path,
        *, entity_id: str | None = None, sheet_format: str = "A3", scale_label: str = "Auto",
        unit: str = "mm", make_png: bool = True, make_pdf: bool = True,
        views: Sequence[str] = ("front", "top", "side", "iso"), dimensions: bool = True,
        title_block: bool = True, dimension_mode: str = "Hoofdmaten",
        manual_dimensions: Sequence[Mapping[str, Any]] = (),
    ) -> DrawingOutput:
        entity, _node, resolved_entity_id, vertices, triangles = self._resolve(entity_id)
        aliases = {
            "drill": "hole",
            "drilling": "hole",
            "round_hole": "hole",
            "bore": "hole",
            "slotted_hole": "slot",
            "elongated_hole": "slot",
            "oblong": "slot",
            "csk": "countersink",
            "countersunk": "countersink",
            "countersink_hole": "countersink",
        }
        normalized_features: list[Mapping[str, Any]] = []
        seen_features: set[str] = set()
        feature_sources: list[Any] = [
            getattr(entity, "production_features", None),
            getattr(entity, "features", None),
        ]
        workbench = getattr(entity, "workbench", {}) or {}
        if isinstance(workbench, Mapping):
            revision = workbench.get("current_revision") or {}
            if isinstance(revision, Mapping):
                feature_sources.append(revision.get("features"))
        for source_items in feature_sources:
            for item in (source_items or ()):
                if not isinstance(item, Mapping):
                    continue
                record = dict(item)
                kind = str(
                    record.get("kind")
                    or record.get("type")
                    or record.get("operation")
                    or record.get("operation_type")
                    or ""
                ).strip().lower()
                record["kind"] = aliases.get(kind, kind)
                parameters = record.get("parameters")
                if not isinstance(parameters, Mapping):
                    parameters = {
                        str(key): value
                        for key, value in record.items()
                        if key not in {"id", "feature_id", "kind", "type"}
                    }
                record["parameters"] = dict(parameters)
                identity = str(record.get("feature_id") or record.get("id") or "")
                if not identity:
                    identity = repr(
                        sorted((str(key), repr(value)) for key, value in record.items())
                    )
                if identity in seen_features:
                    continue
                seen_features.add(identity)
                normalized_features.append(record)
        for attribute, end_name in (("start_cut", "start"), ("end_cut", "end")):
            raw_cut = getattr(entity, attribute, None)
            if raw_cut is None:
                continue
            if is_dataclass(raw_cut):
                cut_parameters = asdict(raw_cut)
            elif isinstance(raw_cut, Mapping):
                cut_parameters = dict(raw_cut)
            else:
                cut_parameters = dict(getattr(raw_cut, "__dict__", {}) or {})
            if cut_parameters:
                cut_parameters.setdefault("end", end_name)
                normalized_features.append({"kind": "miter", "parameters": cut_parameters})
        production_features = tuple(normalized_features)
        selected_views = tuple(view for view in views if view in {"front", "top", "side", "3d", "iso"})
        if not selected_views:
            raise ValueError("Selecteer ten minste een aanzicht")
        drawing_views = tuple("iso" if view == "3d" else view for view in selected_views)
        labels = {"front": "VOORAANZICHT", "top": "BOVENAANZICHT", "side": "ZIJAANZICHT", "3d": "3D", "iso": "ISOMETRISCH"}
        sheet_key = sheet_format if sheet_format in SHEET_MM else "A3"
        paper_width, paper_height = SHEET_MM[sheet_key]
        width = 1800
        height = int(round(width * paper_height / paper_width))
        title_height = 135 if title_block else 20
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((12, 12, width - 12, height - 12), outline=(37, 70, 108), width=3)
        self._draw_logo(draw, 36, 22)
        draw.text((355, 31), "TECHNISCHE WERKPLAATSTEKENING", fill=(34, 58, 87), font=self._font(18, bold=True))
        rectangles = self._rectangles(len(drawing_views), (34, 76, width - 34, height - title_height - 16))
        px_per_mm = width / paper_width
        requested = self._requested_scale(scale_label)
        denominator, adjusted = self._fit_scale(vertices, drawing_views, rectangles, px_per_mm, requested)
        for source_view, drawing_view, rectangle in zip(selected_views, drawing_views, rectangles):
            self._draw_view(
                draw, vertices, triangles, drawing_view, rectangle, labels[source_view], denominator,
                px_per_mm, dimensions, dimension_mode, manual_dimensions, production_features,
            )
        warnings: list[str] = []
        if adjusted:
            warnings.append(f"Gevraagde schaal paste niet op {sheet_key}; aangepast naar 1:{denominator}")
        if title_block:
            top = height - title_height
            draw.rectangle((34, top, width - 34, height - 34), outline=(37, 70, 108), width=2)
            columns = (34, 465, 900, 1335, width - 34)
            for x in columns[1:-1]:
                draw.line((x, top, x, height - 34), fill=(91, 116, 145), width=1)
            middle = top + 48
            draw.line((34, middle, width - 34, middle), fill=(91, 116, 145), width=1)
            part_id = str(getattr(entity, "part_position", "") or getattr(entity, "position", "") or getattr(entity, "name", "") or resolved_entity_id)
            profile = str(
                getattr(entity, "normalized_profile", "")
                or getattr(entity, "profile_designation", "")
                or getattr(entity, "profile", "")
                or "Niet herkend"
            )
            material = str(
                getattr(entity, "normalized_material", "")
                or getattr(entity, "material_grade", "")
                or getattr(entity, "material", "")
                or "Niet herkend"
            )
            project_label = str(
                getattr(self.workspace.project, "project_name", "")
                or getattr(self.workspace.project, "name", "")
                or getattr(self.workspace.project, "project_id", "")
                or "CWS project"
            )
            entries = (("Project", project_label), ("Onderdeel", part_id), ("Profiel", profile),
                       ("Materiaal", material), ("Formaat / schaal", f"{sheet_key} / 1:{denominator}"),
                       ("Eenheid", unit), ("Revisie", "A"), ("Blad", "1 van 1"))
            for index, (key, value) in enumerate(entries):
                column, row = index % 4, index // 4
                draw.text((columns[column] + 10, top + 7 + row * 49), f"{key}: {value}", fill=(37, 60, 86), font=self._font(14, bold=key in {"Onderdeel", "Formaat / schaal"}))
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        stem = str(getattr(entity, "part_position", "") or getattr(entity, "position", "") or getattr(entity, "name", "") or resolved_entity_id or "onderdeel").replace("/", "-")
        png_path = output / f"{stem}_tekening.png" if make_png else None
        pdf_path = output / f"{stem}_tekening.pdf" if make_pdf else None
        if png_path is not None:
            image.save(png_path, format="PNG", optimize=True, dpi=(300, 300))
        if pdf_path is not None:
            DrawingProjectionModel.export_pdf(pdf_path,vertices,triangles,views=drawing_views,sheet_mm=(paper_width,paper_height),scale_denominator=denominator,title="TECHNISCHE WERKPLAATSTEKENING",metadata={"Onderdeel":stem,"Formaat":sheet_key,"Eenheid":unit})
            DocumentOutputService.shared().register(pdf_path,kind="engineering_drawing",producer="EngineeringDrawingGenerator",entity_ids=(resolved_entity_id,))
        return DrawingOutput(png_path=png_path, pdf_path=pdf_path, warnings=tuple(warnings), scale_label=f"1:{denominator}")
