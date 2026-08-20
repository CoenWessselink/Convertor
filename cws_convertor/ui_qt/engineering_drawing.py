from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont

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
        if view == "front":
            return np.array((1.0, 0.0, 0.0)), np.array((0.0, 1.0, 0.0)), np.array((0.0, 0.0, 1.0))
        if view == "top":
            return np.array((1.0, 0.0, 0.0)), np.array((0.0, 0.0, 1.0)), np.array((0.0, -1.0, 0.0))
        if view == "side":
            return np.array((0.0, 1.0, 0.0)), np.array((0.0, 0.0, 1.0)), np.array((1.0, 0.0, 0.0))
        direction = np.array((1.0, -1.0, 0.78), dtype=float)
        direction /= np.linalg.norm(direction)
        u = np.array((1.0, 1.0, 0.0), dtype=float)
        u /= np.linalg.norm(u)
        v = np.cross(direction, u)
        v /= np.linalg.norm(v)
        return u, v, direction

    @classmethod
    def _project(cls, vertices: np.ndarray, view: str) -> tuple[np.ndarray, np.ndarray]:
        u, v, direction = cls._basis(view)
        return np.column_stack((vertices @ u, vertices @ v)), vertices @ direction

    @staticmethod
    def _visible_edges(triangles: np.ndarray, depths: np.ndarray, vertices: np.ndarray) -> set[tuple[int, int]]:
        adjacency: dict[tuple[int, int], list[int]] = {}
        normals: list[np.ndarray] = []
        for triangle_index, triangle in enumerate(triangles):
            a, b, c = (int(value) for value in triangle)
            normal = np.cross(vertices[b] - vertices[a], vertices[c] - vertices[a])
            length = float(np.linalg.norm(normal))
            normals.append(normal / length if length > 1.0e-9 else np.zeros(3))
            for start, end in ((a, b), (b, c), (c, a)):
                edge = (start, end) if start < end else (end, start)
                adjacency.setdefault(edge, []).append(triangle_index)
        result: set[tuple[int, int]] = set()
        for edge, faces in adjacency.items():
            if len(faces) == 1:
                result.add(edge)
                continue
            first, second = normals[faces[0]], normals[faces[1]]
            if float(np.dot(first, second)) < math.cos(math.radians(18.0)):
                result.add(edge)
                continue
            face_depths = [float(depths[triangles[index]].mean()) for index in faces]
            if max(face_depths) - min(face_depths) > 0.25:
                result.add(edge)
        return result

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
            width = max(1.0, float(rectangle[2] - rectangle[0] - 70)) / px_per_mm
            height = max(1.0, float(rectangle[3] - rectangle[1] - 105)) / px_per_mm
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
    ) -> None:
        left, top, right, bottom = rectangle
        draw.rounded_rectangle(rectangle, radius=6, outline=(190, 205, 221), width=2, fill=(252, 253, 255))
        draw.text((left + 14, top + 11), label, fill=(28, 68, 112), font=self._font(19, bold=True))
        projected, depths = self._project(vertices, view)
        center = (projected.min(axis=0) + projected.max(axis=0)) * 0.5
        scale = px_per_mm / float(denominator)
        usable_left, usable_top = left + 32, top + 44
        usable_right, usable_bottom = right - 32, bottom - (54 if dimensions else 25)
        screen_center = np.array(((usable_left + usable_right) * 0.5, (usable_top + usable_bottom) * 0.5))
        screen = np.empty_like(projected)
        screen[:, 0] = (projected[:, 0] - center[0]) * scale + screen_center[0]
        screen[:, 1] = screen_center[1] - ((projected[:, 1] - center[1]) * scale)
        for first, second in self._visible_edges(triangles, depths, vertices):
            draw.line((float(screen[first, 0]), float(screen[first, 1]), float(screen[second, 0]), float(screen[second, 1])), fill=(24, 60, 96), width=2)
        if dimensions:
            minimum, maximum = screen.min(axis=0), screen.max(axis=0)
            model_span = projected.max(axis=0) - projected.min(axis=0)
            dimension_value = float(np.ptp(vertices[:, 0])) if view == "iso" else float(model_span[0])
            y = min(bottom - 22, int(maximum[1] + 26))
            x0, x1 = int(minimum[0]), int(maximum[0])
            draw.line((x0, y, x1, y), fill=(0, 102, 220), width=2)
            draw.line((x0, y - 7, x0, y + 7), fill=(0, 102, 220), width=2)
            draw.line((x1, y - 7, x1, y + 7), fill=(0, 102, 220), width=2)
            draw.text(((x0 + x1) // 2 - 34, y - 25), f"{dimension_value:,.1f} mm", fill=(0, 102, 220), font=self._font(14))

    def generate(
        self,
        output_directory: str | Path,
        *, entity_id: str | None = None, sheet_format: str = "A3", scale_label: str = "Auto",
        unit: str = "mm", make_png: bool = True, make_pdf: bool = True,
        views: Sequence[str] = ("front", "top", "side", "iso"), dimensions: bool = True,
        title_block: bool = True,
    ) -> DrawingOutput:
        entity, _node, resolved_entity_id, vertices, triangles = self._resolve(entity_id)
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
        draw.text((36, 28), "CWS CONVERTOR", fill=(0, 68, 136), font=self._font(25, bold=True))
        draw.text((285, 31), "TECHNISCHE WERKPLAATSTEKENING", fill=(34, 58, 87), font=self._font(18, bold=True))
        rectangles = self._rectangles(len(drawing_views), (34, 76, width - 34, height - title_height - 16))
        px_per_mm = width / paper_width
        requested = self._requested_scale(scale_label)
        denominator, adjusted = self._fit_scale(vertices, drawing_views, rectangles, px_per_mm, requested)
        for source_view, drawing_view, rectangle in zip(selected_views, drawing_views, rectangles):
            self._draw_view(draw, vertices, triangles, drawing_view, rectangle, labels[source_view], denominator, px_per_mm, dimensions)
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
            profile = str(getattr(entity, "profile_designation", "") or getattr(entity, "profile", "") or "Niet herkend")
            material = str(getattr(entity, "material_grade", "") or getattr(entity, "material", "") or "Niet herkend")
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
            image.save(pdf_path, format="PDF", resolution=300.0)
        return DrawingOutput(png_path=png_path, pdf_path=pdf_path, warnings=tuple(warnings), scale_label=f"1:{denominator}")
