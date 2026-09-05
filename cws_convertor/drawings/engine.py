"""Single production drawing engine for preview, PDF and print output."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .document import DrawingDocument, DrawingPage, DrawingPrimitive, page_size_mm
from .linter import DrawingLinter
from .projection import DrawingProjectionModel


STANDARD_SCALES = (1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000)
VIEW_LABELS = {
    "front": "VOORAANZICHT",
    "top": "BOVENAANZICHT",
    "side": "ZIJAANZICHT",
    "end": "EINDAANZICHT",
    "iso": "ISOMETRISCH",
    "3d": "3D-AANZICHT",
}


def _hash_mesh(vertices: np.ndarray, triangles: np.ndarray) -> str:
    digest = sha256()
    digest.update(np.asarray(vertices, dtype="<f8").tobytes())
    digest.update(np.asarray(triangles, dtype="<i8").tobytes())
    return digest.hexdigest()


def _number(mapping: Mapping[str, Any], *names: str, default: float = 0.0) -> float:
    for name in names:
        value = mapping.get(name)
        if value not in (None, ""):
            try:
                number = float(str(value).replace(",", "."))
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                return number
    return float(default)


def _format_value(value_mm: float, unit: str) -> str:
    value = float(value_mm) / (10.0 if unit == "cm" else 1.0)
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return f"{text} {unit}"


def _line(
    layer: str,
    start: Sequence[float],
    end: Sequence[float],
    *,
    color: str = "#173b5d",
    width: float = 0.25,
    dash: Sequence[float] = (),
    refs: Sequence[str] = (),
    semantic_id: str = "",
) -> DrawingPrimitive:
    return DrawingPrimitive(
        "line",
        layer,
        points=[[float(start[0]), float(start[1])], [float(end[0]), float(end[1])]],
        color=color,
        width=width,
        dash=[float(value) for value in dash],
        refs=list(refs),
        semantic_id=semantic_id,
    )


def _text(
    layer: str,
    x: float,
    y: float,
    value: str,
    *,
    size: float = 3.0,
    bold: bool = False,
    color: str = "#243d55",
    refs: Sequence[str] = (),
    semantic_id: str = "",
) -> DrawingPrimitive:
    return DrawingPrimitive(
        "text",
        layer,
        points=[[float(x), float(y)]],
        text=str(value),
        color=color,
        font_size=float(size),
        bold=bool(bold),
        refs=list(refs),
        semantic_id=semantic_id,
    )


def _rect(
    layer: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    *,
    color: str = "#8ca1b4",
    width: float = 0.18,
    fill: str = "",
    refs: Sequence[str] = (),
    semantic_id: str = "",
) -> DrawingPrimitive:
    return DrawingPrimitive(
        "rect",
        layer,
        points=[[left, top], [right, bottom]],
        color=color,
        fill=fill,
        width=width,
        refs=list(refs),
        semantic_id=semantic_id,
    )


@dataclass(slots=True)
class DrawingBuildRequest:
    entity_id: str
    vertices: np.ndarray
    triangles: np.ndarray
    views: Sequence[str] = ("front", "top", "side", "iso")
    sheet_format: str = "A3"
    orientation: str = "landscape"
    scale_denominator: int | None = None
    unit: str = "mm"
    dimensions_enabled: bool = True
    dimension_mode: str = "Hoofdmaten"
    title_block_enabled: bool = True
    include_sections: bool = True
    include_details: bool = True
    features: Sequence[Mapping[str, Any]] = ()
    dimensions: Sequence[Mapping[str, Any]] = ()
    dimension_chains: Sequence[Mapping[str, Any]] = ()
    manual_dimensions: Sequence[Mapping[str, Any]] = ()
    dimension_style: Mapping[str, Any] = field(default_factory=dict)
    dimension_audit: Sequence[Mapping[str, Any]] = ()
    dimension_editor_schema: str = ""
    dimension_editor_status: str = ""
    title_block: Mapping[str, Any] = field(default_factory=dict)
    revisions: Sequence[Mapping[str, Any]] = ()
    bom: Sequence[Mapping[str, Any]] = ()
    notes: Sequence[str] = ()
    document_type: str = "part"
    geometry_basis: str = "viewer_mesh"
    geometry_sha256: str = ""
    manufacturing_sha256: str = ""
    expected_manufacturing_sha256: str = ""
    source_revision: str = ""
    canonical_rebuild_current: bool = False
    canonical_payload_current: bool = False
    roundtrip_current: bool = False
    exact_shape: Any | None = None
    assembly_components: Sequence[Mapping[str, Any]] = ()


class ProductionDrawingEngine:
    """Create one complete and linted ``DrawingDocument``."""

    @staticmethod
    def next_standard_scale(required: float) -> int:
        for value in STANDARD_SCALES:
            if value + 1.0e-9 >= required:
                return value
        return int(math.ceil(required / 500.0) * 500.0)

    @staticmethod
    def _view_rectangles(
        count: int,
        width: float,
        height: float,
        *,
        title_block: bool,
    ) -> list[tuple[float, float, float, float]]:
        left, top, right = 10.0, 22.0, width - 10.0
        bottom = height - (39.0 if title_block else 10.0)
        gap = 5.0
        if count <= 1:
            return [(left, top, right, bottom)]
        columns = 2
        rows = int(math.ceil(count / columns))
        cell_w = (right - left - gap) / 2.0
        cell_h = (bottom - top - gap * (rows - 1)) / rows
        result = []
        for index in range(count):
            row, column = divmod(index, columns)
            x0 = left + column * (cell_w + gap)
            y0 = top + row * (cell_h + gap)
            result.append((x0, y0, x0 + cell_w, y0 + cell_h))
        if count == 3:
            x0, y0, _x1, y1 = result[2]
            result[2] = (x0, y0, right, y1)
        return result

    @classmethod
    def _fit_scale(
        cls,
        vertices: np.ndarray,
        views: Sequence[str],
        rectangles: Sequence[tuple[float, float, float, float]],
        requested: int | None,
    ) -> tuple[int, bool]:
        required = 1.0
        for view, rectangle in zip(views, rectangles):
            projected, _depth = DrawingProjectionModel.project(vertices, view)
            span = np.maximum(projected.max(axis=0) - projected.min(axis=0), 1.0)
            available_width = max(1.0, rectangle[2] - rectangle[0] - 28.0)
            available_height = max(1.0, rectangle[3] - rectangle[1] - 30.0)
            required = max(
                required,
                float(span[0]) / available_width,
                float(span[1]) / available_height,
            )
        fitted = cls.next_standard_scale(required * 1.05)
        if requested is None:
            return fitted, False
        return max(int(requested), fitted), fitted > int(requested)

    @staticmethod
    def _base_page(number: int, title: str, width: float, height: float) -> DrawingPage:
        return DrawingPage(
            number,
            title,
            width,
            height,
            primitives=[
                _rect("sheet", 5.0, 5.0, width - 5.0, height - 5.0, color="#244665", width=0.45),
                _text("sheet", 10.0, 15.0, "CWS", size=7.0, bold=True, color="#004ea2"),
                _text("sheet", 28.0, 15.0, title, size=4.2, bold=True),
            ],
        )

    @staticmethod
    def _normalise_features(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
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
            "countersunk_hole": "countersink",
            "countersink_hole": "countersink",
            "mitre": "miter",
            "saw_cut": "miter",
            "end_cut": "miter",
            "notch": "cope",
            "mark": "scribe",
        }
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, item in enumerate(values, start=1):
            record = dict(item)
            kind = str(
                record.get("kind")
                or record.get("type")
                or record.get("operation")
                or record.get("operation_type")
                or "feature"
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
            identity = str(record.get("feature_id") or record.get("id") or f"feature-{index:03d}")
            if identity in seen:
                continue
            seen.add(identity)
            record["feature_id"] = identity
            result.append(record)
        return result

    @staticmethod
    def _normalise_manual(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for index, item in enumerate(values, start=1):
            record = dict(item)
            record["id"] = str(record.get("id") or record.get("dimension_id") or f"manual-{index:03d}")
            is_interactive = bool(record.get("anchors"))
            record["critical"] = bool(record.get("critical", not is_interactive))
            record["value_mm"] = abs(_number(
                record,
                "nominal_value_mm",
                "value_mm",
                default=_number(record, "end") - _number(record, "start"),
            ))
            result.append(record)
        return result

    @staticmethod
    def _projected_to_sheet(
        point: Sequence[float],
        geometry: tuple[np.ndarray, np.ndarray, float, tuple[float, float, float, float]],
    ) -> tuple[float, float]:
        projected, _screen, scale, rectangle = geometry
        center = (projected.min(axis=0) + projected.max(axis=0)) * 0.5
        target_center = np.array(((rectangle[0] + rectangle[2]) * 0.5, (rectangle[1] + rectangle[3]) * 0.5 + 2.0))
        return (
            (float(point[0]) - float(center[0])) * scale + float(target_center[0]),
            float(target_center[1]) - (float(point[1]) - float(center[1])) * scale,
        )

    @classmethod
    def _interactive_anchor_point(
        cls,
        anchor: Mapping[str, Any],
        geometry: tuple[np.ndarray, np.ndarray, float, tuple[float, float, float, float]],
    ) -> tuple[float, float] | None:
        if str(anchor.get("proof") or "") == "non_geometric_annotation":
            sheet = anchor.get("sheet_point")
            if isinstance(sheet, Sequence) and not isinstance(sheet, (str, bytes)) and len(sheet) >= 2:
                return float(sheet[0]), float(sheet[1])
        projected = anchor.get("projected_point")
        if isinstance(projected, Sequence) and not isinstance(projected, (str, bytes)) and len(projected) >= 2:
            try:
                return cls._projected_to_sheet((float(projected[0]), float(projected[1])), geometry)
            except (TypeError, ValueError):
                return None
        sheet = anchor.get("sheet_point")
        if isinstance(sheet, Sequence) and not isinstance(sheet, (str, bytes)) and len(sheet) >= 2:
            try:
                return float(sheet[0]), float(sheet[1])
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _screen_transform(
        projected: np.ndarray,
        rectangle: tuple[float, float, float, float],
        denominator: int,
    ) -> tuple[np.ndarray, float]:
        center = (projected.min(axis=0) + projected.max(axis=0)) * 0.5
        left, top, right, bottom = rectangle
        scale = 1.0 / max(1.0, float(denominator))
        screen_center = np.array(((left + right) * 0.5, (top + bottom) * 0.5 + 2.0))
        screen = np.empty_like(projected)
        screen[:, 0] = (projected[:, 0] - center[0]) * scale + screen_center[0]
        screen[:, 1] = screen_center[1] - (projected[:, 1] - center[1]) * scale
        return screen, scale

    @classmethod
    def _add_view(
        cls,
        page: DrawingPage,
        *,
        vertices: np.ndarray,
        triangles: np.ndarray,
        view: str,
        rectangle: tuple[float, float, float, float],
        denominator: int,
        exact_shape: Any | None,
        assembly_components: Sequence[Mapping[str, Any]] = (),
    ) -> tuple[np.ndarray, np.ndarray, float, str]:
        view_id = f"sheet-{page.number}-{view}-{len(page.view_ids) + 1}"
        page.view_ids.append(view_id)
        page.primitives.extend(
            (
                _rect("views", *rectangle, color="#b8c8d6", width=0.18, semantic_id=view_id),
                _text("views", rectangle[0] + 2.0, rectangle[1] + 5.0, VIEW_LABELS.get(view, view.upper()), size=2.8, bold=True),
            )
        )
        projected, _depth = DrawingProjectionModel.project(vertices, view)
        screen, scale = cls._screen_transform(projected, rectangle, denominator)
        layers: list[tuple[str, list[list[tuple[float, float]]], list[list[tuple[float, float]]], str]] = []
        if assembly_components:
            for component in assembly_components:
                component_vertices = np.asarray(component.get("vertices", ()), dtype=float).reshape((-1, 3))
                component_triangles = np.asarray(component.get("triangles", ()), dtype=int).reshape((-1, 3))
                if component_vertices.size == 0 or component_triangles.size == 0:
                    continue
                component_visible, component_hidden, component_method = DrawingProjectionModel.edge_layers(
                    component_vertices,
                    component_triangles,
                    view,
                    exact_shape=component.get("exact_shape"),
                )
                layers.append(
                    (
                        str(component.get("entity_id") or "component"),
                        component_visible,
                        component_hidden,
                        component_method,
                    )
                )
        if not layers:
            visible, hidden, hlr_method = DrawingProjectionModel.edge_layers(
                vertices,
                triangles,
                view,
                exact_shape=exact_shape,
            )
            layers = [("", visible, hidden, hlr_method)]
        hlr_method = "occt_hlr" if layers and all(value[3] == "occt_hlr" for value in layers) else "mesh_fallback"
        center = (projected.min(axis=0) + projected.max(axis=0)) * 0.5
        target_center = np.array(((rectangle[0] + rectangle[2]) * 0.5, (rectangle[1] + rectangle[3]) * 0.5 + 2.0))

        def place(point: Sequence[float]) -> list[float]:
            return [
                (float(point[0]) - float(center[0])) * scale + float(target_center[0]),
                float(target_center[1]) - (float(point[1]) - float(center[1])) * scale,
            ]

        for component_index, (component_id, visible, hidden, _method) in enumerate(layers, start=1):
            reference = [f"entity:{component_id}"] if component_id else []
            semantic_component = f"component-{component_id}-" if component_id else ""
            for index, polyline in enumerate(hidden):
                points = [place(point) for point in polyline]
                if len(points) >= 2:
                    page.primitives.append(
                        DrawingPrimitive(
                            "polyline",
                            "hidden",
                            points=points,
                            color="#70879d",
                            width=0.15,
                            dash=[2.0, 1.2],
                            refs=reference,
                            semantic_id=f"{view_id}-{semantic_component}hidden-{component_index}-{index + 1}",
                        )
                    )
            for index, polyline in enumerate(visible):
                points = [place(point) for point in polyline]
                if len(points) >= 2:
                    page.primitives.append(
                        DrawingPrimitive(
                            "polyline",
                            "visible",
                            points=points,
                            color="#173b5d",
                            width=0.28,
                            refs=reference,
                            semantic_id=f"{view_id}-{semantic_component}visible-{component_index}-{index + 1}",
                        )
                    )
        if view in {"front", "top", "side", "end"}:
            minimum, maximum = screen.min(axis=0), screen.max(axis=0)
            center_x = float((minimum[0] + maximum[0]) * 0.5)
            center_y = float((minimum[1] + maximum[1]) * 0.5)
            page.primitives.extend(
                (
                    _line("centerlines", (float(minimum[0]) - 2.0, center_y), (float(maximum[0]) + 2.0, center_y), color="#52789b", width=0.12, dash=(4.0, 1.0, 0.8, 1.0), semantic_id=f"{view_id}-axis-x"),
                    _line("centerlines", (center_x, float(minimum[1]) - 2.0), (center_x, float(maximum[1]) + 2.0), color="#52789b", width=0.12, dash=(4.0, 1.0, 0.8, 1.0), semantic_id=f"{view_id}-axis-y"),
                )
            )
        return projected, screen, scale, hlr_method

    @staticmethod
    def _feature_target_view(kind: str, side: str, views: Sequence[str]) -> str:
        candidates = []
        if side in {"o", "u"} or any(token in side for token in ("top", "boven", "flange")):
            candidates.append("top")
        elif side in {"v", "h"} or any(token in side for token in ("front", "voor", "web")):
            candidates.append("front")
        elif any(token in side for token in ("side", "zijde", "end", "kop")):
            candidates.append("side")
        if kind in {"miter", "scribe"}:
            candidates.extend(("front", "top"))
        candidates.extend(("front", "top", "side", "end"))
        return next((value for value in candidates if value in views), views[0])

    @classmethod
    def _add_features(
        cls,
        page: DrawingPage,
        *,
        features: Sequence[Mapping[str, Any]],
        views: Sequence[str],
        geometry: Mapping[str, tuple[np.ndarray, np.ndarray, float, tuple[float, float, float, float]]],
        unit: str,
    ) -> None:
        lane_by_view: dict[str, int] = {}
        for feature in features:
            kind = str(feature.get("kind") or "feature")
            parameters = dict(feature.get("parameters") or {})
            feature_id = str(feature.get("feature_id") or feature.get("id") or "")
            side = str(feature.get("reference_side") or parameters.get("reference_side") or parameters.get("face") or "").lower()
            view = cls._feature_target_view(kind, side, views)
            projected, screen, scale, rectangle = geometry[view]
            minimum = screen.min(axis=0)
            maximum = screen.max(axis=0)
            model_span = np.maximum(projected.max(axis=0) - projected.min(axis=0), 1.0)
            x_mm = _number(parameters, "x_mm", "x", "offset_x_mm", "position_x_mm")
            y_mm = _number(parameters, "y_mm", "y", "q", "q_mm", "offset_y_mm", "position_y_mm")
            x_ratio = min(1.0, max(0.0, x_mm / float(model_span[0])))
            y_ratio = min(1.0, max(0.0, y_mm / float(model_span[1])))
            cx = float(minimum[0]) + x_ratio * float(maximum[0] - minimum[0])
            cy = float(maximum[1]) - y_ratio * float(maximum[1] - minimum[1])
            lane = lane_by_view.get(view, 0)
            lane_by_view[view] = lane + 1
            label_x = min(rectangle[2] - 36.0, max(rectangle[0] + 2.0, cx + 6.0))
            label_y = min(rectangle[3] - 3.0, rectangle[1] + 12.0 + lane * 4.3)
            refs = (feature_id,)
            diameter = max(1.0, _number(parameters, "diameter_mm", "diameter", "width_mm", default=1.0))
            radius = max(1.2, diameter * scale * 0.5)
            if kind in {"hole", "countersink", "slot"}:
                if kind == "slot":
                    length = max(diameter, _number(parameters, "length_mm", "slot_length_mm", default=diameter * 2.0))
                    page.primitives.append(
                        _rect(
                            "annotations",
                            cx - length * scale * 0.5,
                            cy - radius,
                            cx + length * scale * 0.5,
                            cy + radius,
                            refs=refs,
                            semantic_id=f"{feature_id}-slot",
                        )
                    )
                    callout = f"SLEUF { _format_value(diameter, unit) } x { _format_value(length, unit) }"
                else:
                    page.primitives.append(
                        DrawingPrimitive(
                            "circle",
                            "annotations",
                            center=[cx, cy],
                            radius=radius,
                            refs=list(refs),
                            semantic_id=f"{feature_id}-hole",
                        )
                    )
                    outer = _number(parameters, "countersink_diameter_mm", "outer_diameter_mm", "head_diameter_mm")
                    if kind == "countersink" or outer > diameter:
                        outer = max(outer, diameter * 1.6)
                        page.primitives.append(
                            DrawingPrimitive(
                                "circle",
                                "annotations",
                                center=[cx, cy],
                                radius=max(radius + 0.8, outer * scale * 0.5),
                                width=0.16,
                                refs=list(refs),
                                semantic_id=f"{feature_id}-countersink",
                            )
                        )
                        callout = f"VERZONKEN Ø{_format_value(diameter, unit)} / Ø{_format_value(outer, unit)}"
                    else:
                        callout = f"Ø{_format_value(diameter, unit)}"
                page.primitives.extend(
                    (
                        _line("centerlines", (cx - radius - 2.0, cy), (cx + radius + 2.0, cy), color="#1670d6", width=0.14, dash=(3.0, 0.8, 0.6, 0.8), refs=refs),
                        _line("centerlines", (cx, cy - radius - 2.0), (cx, cy + radius + 2.0), color="#1670d6", width=0.14, dash=(3.0, 0.8, 0.6, 0.8), refs=refs),
                    )
                )
            elif kind in {"pocket", "cope", "cutout", "notch"}:
                width = max(4.0, _number(parameters, "width_mm", default=20.0) * scale)
                height = max(3.0, _number(parameters, "height_mm", "depth_mm", default=12.0) * scale)
                page.primitives.append(
                    _rect("annotations", cx - width / 2.0, cy - height / 2.0, cx + width / 2.0, cy + height / 2.0, refs=refs, semantic_id=f"{feature_id}-{kind}")
                )
                callout = kind.upper()
            elif kind == "scribe":
                length = max(5.0, _number(parameters, "length_mm", default=30.0) * scale)
                page.primitives.append(
                    _line("annotations", (cx - length / 2.0, cy), (cx + length / 2.0, cy), color="#7b3fb2", width=0.2, dash=(4.0, 1.0), refs=refs, semantic_id=f"{feature_id}-scribe")
                )
                callout = "SCRIBE / MARKERING"
            elif kind in {"miter", "cut", "angle_cut"}:
                angle = abs(_number(parameters, "primary_angle_deg", "angle_deg", "saw_angle_deg", "miter_angle_deg"))
                page.primitives.append(
                    _line("annotations", (cx - 3.0, cy + 4.0), (cx + 3.0, cy - 4.0), color="#1670d6", width=0.25, refs=refs, semantic_id=f"{feature_id}-miter")
                )
                callout = f"KOPSE SNEDE {angle:g}°"
            else:
                page.primitives.append(
                    DrawingPrimitive("circle", "annotations", center=[cx, cy], radius=1.3, refs=list(refs), semantic_id=f"{feature_id}-{kind}")
                )
                callout = kind.upper()
            page.primitives.extend(
                (
                    _line("annotations", (cx, cy), (label_x - 1.0, label_y - 1.0), color="#1670d6", width=0.16, refs=refs),
                    _text("annotations", label_x, label_y, callout, size=2.2, bold=True, color="#1670d6", refs=refs, semantic_id=f"{feature_id}-callout"),
                )
            )

    @staticmethod
    def _dimension_line(
        page: DrawingPage,
        *,
        start: tuple[float, float],
        end: tuple[float, float],
        label: str,
        dimension_id: str,
        vertical: bool = False,
        refs: Sequence[str] = (),
        color: str = "#0066dc",
        width: float = 0.2,
        text_size: float = 2.2,
        arrow: float = 1.6,
    ) -> None:
        page.primitives.append(_line("dimensions", start, end, color=color, width=width, refs=refs, semantic_id=dimension_id))
        if vertical:
            x, y = start
            page.primitives.extend(
                (
                    _line("dimensions", (x - arrow * 0.625, y + arrow), (x, y), color=color, width=width, semantic_id=dimension_id),
                    _line("dimensions", (x + arrow * 0.625, y + arrow), (x, y), color=color, width=width, semantic_id=dimension_id),
                    _line("dimensions", (end[0] - arrow * 0.625, end[1] - arrow), end, color=color, width=width, semantic_id=dimension_id),
                    _line("dimensions", (end[0] + arrow * 0.625, end[1] - arrow), end, color=color, width=width, semantic_id=dimension_id),
                    _text("dimensions", x + 1.8, (y + end[1]) / 2.0, label, size=text_size, color=color, semantic_id=dimension_id),
                )
            )
        else:
            x, y = start
            page.primitives.extend(
                (
                    _line("dimensions", (x + arrow, y - arrow * 0.625), (x, y), color=color, width=width, semantic_id=dimension_id),
                    _line("dimensions", (x + arrow, y + arrow * 0.625), (x, y), color=color, width=width, semantic_id=dimension_id),
                    _line("dimensions", (end[0] - arrow, end[1] - arrow * 0.625), end, color=color, width=width, semantic_id=dimension_id),
                    _line("dimensions", (end[0] - arrow, end[1] + arrow * 0.625), end, color=color, width=width, semantic_id=dimension_id),
                    _text("dimensions", (x + end[0]) / 2.0 - len(label) * 0.55, y - 1.8, label, size=text_size, color=color, semantic_id=dimension_id),
                )
            )

    @staticmethod
    def _aligned_dimension_line(
        page: DrawingPage,
        *,
        start: tuple[float, float],
        end: tuple[float, float],
        label: str,
        dimension_id: str,
        refs: Sequence[str] = (),
        color: str = "#0066dc",
        width: float = 0.2,
        text_size: float = 2.2,
        arrow: float = 1.4,
    ) -> None:
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = max(1.0e-9, math.hypot(dx, dy))
        nx, ny = -dy / length, dx / length
        page.primitives.extend(
            (
                _line("dimensions", start, end, color=color, width=width, refs=refs, semantic_id=dimension_id),
                _line("dimensions", (start[0] + dx / length * arrow + nx, start[1] + dy / length * arrow + ny), start, color=color, width=width, semantic_id=dimension_id),
                _line("dimensions", (start[0] + dx / length * arrow - nx, start[1] + dy / length * arrow - ny), start, color=color, width=width, semantic_id=dimension_id),
                _line("dimensions", (end[0] - dx / length * arrow + nx, end[1] - dy / length * arrow + ny), end, color=color, width=width, semantic_id=dimension_id),
                _line("dimensions", (end[0] - dx / length * arrow - nx, end[1] - dy / length * arrow - ny), end, color=color, width=width, semantic_id=dimension_id),
                _text("dimensions", (start[0] + end[0]) * 0.5, (start[1] + end[1]) * 0.5 - 1.5, label, size=text_size, color=color, semantic_id=dimension_id),
            )
        )

    @staticmethod
    def _interactive_label(item: Mapping[str, Any], unit: str) -> str:
        label = str(item.get("label") or "").strip()
        style = dict(item.get("style") or {})
        if not label:
            kind = str(item.get("kind") or "")
            numeric = _number(item, "nominal_value_mm", "value_mm") / (10.0 if unit == "cm" else 1.0)
            decimals = max(0, min(6, int(style.get("decimals", 1))))
            value_text = f"{numeric:.{decimals}f}"
            if not bool(style.get("trailing_zeros", False)):
                value_text = value_text.rstrip("0").rstrip(".")
            if str(style.get("decimal_separator") or ",") == ",":
                value_text = value_text.replace(".", ",")
            value = f"{value_text} {unit}"
            if kind == "diameter":
                value = f"{style.get('diameter_symbol') or 'Ø'}{value}"
            elif kind == "radius":
                value = f"{style.get('radius_prefix') or 'R'}{value}"
            elif kind == "angle":
                value = f"{value_text}{style.get('angle_suffix') or '°'}"
            quantity = int(dict(item.get("metadata") or {}).get("quantity") or 0)
            if quantity > 1:
                value = str(style.get("quantity_format") or "{count}x {value}").format(count=quantity, value=value)
            label = value
        prefix = str(item.get("prefix") or "")
        suffix = str(item.get("suffix") or "")
        upper = item.get("tolerance_upper_mm")
        lower = item.get("tolerance_lower_mm")
        tolerance = ""
        try:
            if upper is not None or lower is not None:
                divisor = 10.0 if unit == "cm" else 1.0
                upper_value = float(upper or 0.0) / divisor
                lower_value = float(lower or 0.0) / divisor
                tolerance = f" +{upper_value:g}/{lower_value:g}"
        except (TypeError, ValueError):
            tolerance = ""
        reference = " REF" if bool(item.get("reference", False)) else ""
        inspection = " ⌑" if bool(item.get("inspection", False)) else ""
        typical = " TYP" if bool(dict(item.get("metadata") or {}).get("typical", False)) else ""
        return f"{prefix}{label}{suffix}{tolerance}{reference}{inspection}{typical}"

    @classmethod
    def _add_dimensions(
        cls,
        page: DrawingPage,
        *,
        geometry: Mapping[str, tuple[np.ndarray, np.ndarray, float, tuple[float, float, float, float]]],
        primary_view: str,
        dimensions: Sequence[Mapping[str, Any]],
        manual_dimensions: Sequence[Mapping[str, Any]],
        unit: str,
        enabled: bool,
        include_overall: bool = True,
    ) -> None:
        if not enabled:
            return
        projected, screen, scale, rectangle = geometry[primary_view]
        minimum, maximum = screen.min(axis=0), screen.max(axis=0)
        by_id = {str(item.get("id") or ""): item for item in dimensions if item.get("id")}
        overall_x = by_id.get("overall-x")
        overall_y = by_id.get("overall-y")
        span = projected.max(axis=0) - projected.min(axis=0)
        x_value = _number(overall_x or {}, "value_mm", default=float(span[0]))
        y_value = _number(overall_y or {}, "value_mm", default=float(span[1]))
        if include_overall:
            cls._dimension_line(
                page,
                start=(float(minimum[0]), min(rectangle[3] - 3.0, float(maximum[1]) + 6.0)),
                end=(float(maximum[0]), min(rectangle[3] - 3.0, float(maximum[1]) + 6.0)),
                label=_format_value(x_value, unit),
                dimension_id="overall-x",
                refs=tuple(overall_x.get("feature_refs") or ()) if overall_x else (),
            )
            cls._dimension_line(
                page,
                start=(max(rectangle[0] + 3.0, float(minimum[0]) - 6.0), float(minimum[1])),
                end=(max(rectangle[0] + 3.0, float(minimum[0]) - 6.0), float(maximum[1])),
                label=_format_value(y_value, unit),
                dimension_id="overall-y",
                vertical=True,
                refs=tuple(overall_y.get("feature_refs") or ()) if overall_y else (),
            )
        for index, item in enumerate(manual_dimensions):
            if int(item.get("page_number") or 1) != page.number:
                continue
            if not bool(item.get("visible", True)):
                continue
            view = str(item.get("view") or item.get("view_id") or primary_view)
            if view not in geometry and "-" in view:
                view = next((name for name in geometry if f"-{name}-" in str(item.get("view_id") or "")), primary_view)
            if view == "iso" and "iso" not in geometry:
                continue
            target = geometry.get(view, geometry[primary_view])
            target_projected, target_screen, target_scale, target_rectangle = target
            anchors = [dict(value) for value in item.get("anchors") or () if isinstance(value, Mapping)]
            if anchors:
                points = [cls._interactive_anchor_point(anchor, target) for anchor in anchors]
                points = [point for point in points if point is not None]
                if not points:
                    continue
                dimension_id = str(item.get("id") or f"manual-{index + 1:03d}")
                label = cls._interactive_label(item, unit)
                refs = tuple(dict.fromkeys(
                    str(value)
                    for anchor in anchors
                    for value in (anchor.get("entity_id"), anchor.get("feature_id"), anchor.get("subshape_id"))
                    if str(value or "")
                ))
                projected_position = item.get("line_projected_position")
                position_raw = item.get("line_position") or item.get("text_position") or points[-1]
                try:
                    if isinstance(projected_position, Sequence) and not isinstance(projected_position, (str, bytes)) and len(projected_position) >= 2:
                        position = cls._projected_to_sheet(projected_position, target)
                    else:
                        position = (float(position_raw[0]), float(position_raw[1]))
                except (TypeError, ValueError, IndexError):
                    position = points[-1]
                kind = str(item.get("kind") or "aligned")
                style = dict(item.get("style") or {})
                color = str(style.get("line_color") or "#0066dc")
                line_width = max(0.05, _number(style, "line_width_mm", default=0.2))
                text_size = max(1.0, _number(style, "text_height_mm", default=2.2))
                arrow_size = max(0.5, _number(style, "arrow_size_mm", default=1.6))
                if kind in {"leader", "text"}:
                    start = points[0]
                    metadata = dict(item.get("metadata") or {})
                    projected_bends = [
                        cls._projected_to_sheet((float(value[0]), float(value[1])), target)
                        for value in metadata.get("leader_bend_projected_points") or ()
                        if isinstance(value, Sequence)
                        and not isinstance(value, (str, bytes))
                        and len(value) >= 2
                    ]
                    bend_points = projected_bends or [
                        (float(value[0]), float(value[1]))
                        for value in metadata.get("leader_bend_points") or ()
                        if isinstance(value, Sequence)
                        and not isinstance(value, (str, bytes))
                        and len(value) >= 2
                    ]
                    page.primitives.append(
                        DrawingPrimitive(
                            "polyline",
                            "dimensions",
                            points=[start, *bend_points, position],
                            color=color,
                            width=line_width,
                            refs=list(refs),
                            semantic_id=dimension_id,
                        )
                    )
                    page.primitives.append(
                        _text(
                            "dimensions",
                            position[0] + 1.0,
                            position[1],
                            label or "NOTITIE",
                            size=text_size,
                            color=color,
                            refs=refs,
                            semantic_id=dimension_id,
                        )
                    )
                elif kind == "angle" and len(points) >= 3:
                    vertex = points[1]
                    page.primitives.extend(
                        (
                            _line("dimensions", vertex, points[0], color=color, width=line_width, refs=refs, semantic_id=dimension_id),
                            _line("dimensions", vertex, points[2], color=color, width=line_width, refs=refs, semantic_id=dimension_id),
                            _text("dimensions", position[0], position[1], label, size=text_size, color=color, refs=refs, semantic_id=dimension_id),
                        )
                    )
                elif kind in {"radius", "diameter"}:
                    start = points[0]
                    cls._aligned_dimension_line(page, start=start, end=position, label=label, dimension_id=dimension_id, refs=refs, color=color, width=line_width, text_size=text_size, arrow=arrow_size)
                elif kind in {"chain", "baseline"} and len(points) >= 2:
                    pairs = zip(points, points[1:]) if kind == "chain" else ((points[0], point) for point in points[1:])
                    segment_ids = list(dict(item.get("metadata") or {}).get("segment_ids") or ())
                    for segment_index, (first, second) in enumerate(pairs):
                        delta = (position[0] - (first[0] + second[0]) * 0.5, position[1] - (first[1] + second[1]) * 0.5)
                        cls._aligned_dimension_line(
                            page,
                            start=(first[0] + delta[0], first[1] + delta[1]),
                            end=(second[0] + delta[0], second[1] + delta[1]),
                            label=label if segment_index == 0 else _format_value(math.hypot(second[0] - first[0], second[1] - first[1]) / max(target_scale, 1.0e-9), unit),
                            dimension_id=dimension_id,
                            refs=(*refs, str(segment_ids[segment_index])) if segment_index < len(segment_ids) else refs,
                            color=color,
                            width=line_width,
                            text_size=text_size,
                            arrow=arrow_size,
                        )
                elif len(points) >= 2:
                    first, second = points[0], points[1]
                    if kind in {"horizontal", "ordinate_x"}:
                        cls._dimension_line(page, start=(first[0], position[1]), end=(second[0], position[1]), label=label, dimension_id=dimension_id, refs=refs, color=color, width=line_width, text_size=text_size, arrow=arrow_size)
                    elif kind in {"vertical", "ordinate_y"}:
                        cls._dimension_line(page, start=(position[0], first[1]), end=(position[0], second[1]), label=label, dimension_id=dimension_id, vertical=True, refs=refs, color=color, width=line_width, text_size=text_size, arrow=arrow_size)
                    else:
                        midpoint = ((first[0] + second[0]) * 0.5, (first[1] + second[1]) * 0.5)
                        delta = (position[0] - midpoint[0], position[1] - midpoint[1])
                        cls._aligned_dimension_line(
                            page,
                            start=(first[0] + delta[0], first[1] + delta[1]),
                            end=(second[0] + delta[0], second[1] + delta[1]),
                            label=label,
                            dimension_id=dimension_id,
                            refs=refs,
                            color=color,
                            width=line_width,
                            text_size=text_size,
                            arrow=arrow_size,
                        )
                continue
            target_min = target_projected.min(axis=0)
            target_center = (target_screen.min(axis=0) + target_screen.max(axis=0)) * 0.5
            start_offset = _number(item, "start")
            end_offset = _number(item, "end")
            dimension_id = str(item.get("id") or f"manual-{index + 1:03d}")
            label = str(item.get("label") or "").strip() or _format_value(abs(end_offset - start_offset), unit)
            if str(item.get("axis") or "horizontal") == "vertical":
                x = max(target_rectangle[0] + 2.0, float(target_screen[:, 0].min()) - 9.0 - index * 3.0)
                start_y = float(target_center[1]) - (float(target_min[1]) + start_offset - float(target_projected[:, 1].mean())) * target_scale
                end_y = float(target_center[1]) - (float(target_min[1]) + end_offset - float(target_projected[:, 1].mean())) * target_scale
                cls._dimension_line(page, start=(x, start_y), end=(x, end_y), label=label, dimension_id=dimension_id, vertical=True, refs=(str(item.get("feature_id") or ""),))
            else:
                y = min(target_rectangle[3] - 2.0, float(target_screen[:, 1].max()) + 10.0 + index * 3.0)
                start_x = float(target_center[0]) + (float(target_min[0]) + start_offset - float(target_projected[:, 0].mean())) * target_scale
                end_x = float(target_center[0]) + (float(target_min[0]) + end_offset - float(target_projected[:, 0].mean())) * target_scale
                cls._dimension_line(page, start=(start_x, y), end=(end_x, y), label=label, dimension_id=dimension_id, refs=(str(item.get("feature_id") or ""),))

    @staticmethod
    def _add_title_block(
        page: DrawingPage,
        values: Mapping[str, Any],
        *,
        sheet_format: str,
        orientation: str,
        denominator: int,
        unit: str,
        sheet_count: int,
    ) -> None:
        left, top, right, bottom = 8.0, page.height_mm - 34.0, page.width_mm - 8.0, page.height_mm - 8.0
        page.primitives.append(_rect("title", left, top, right, bottom, color="#244665", width=0.25))
        entries = (
            ("Project", values.get("project", "")),
            ("Onderdeel", values.get("entity", "")),
            ("Profiel", values.get("profile", "")),
            ("Materiaal", values.get("material", "")),
            ("Formaat / schaal", f"{sheet_format} {orientation} / 1:{denominator}"),
            ("Eenheid", unit),
            ("Revisie / status", f"{values.get('revision', '')} / {values.get('status', '')}"),
            ("Blad", f"{page.number} van {sheet_count}"),
        )
        columns = 4
        column_width = (right - left) / columns
        row_height = (bottom - top) / 2.0
        for index, (key, value) in enumerate(entries):
            column, row = index % columns, index // columns
            x = left + column * column_width
            y = top + row * row_height
            if column:
                page.primitives.append(_line("title", (x, top), (x, bottom), color="#8ca1b4", width=0.12))
            if row:
                page.primitives.append(_line("title", (left, y), (right, y), color="#8ca1b4", width=0.12))
            page.primitives.append(_text("title", x + 1.5, y + 4.0, f"{key}: {value}", size=2.4, bold=key in {"Onderdeel", "Blad"}))

    @staticmethod
    def _add_schedule(
        page: DrawingPage,
        *,
        title: str,
        rows: Sequence[tuple[str, str, str]],
        left: float,
        top: float,
        right: float,
        layer: str,
    ) -> None:
        page.primitives.append(_text(layer, left, top, title, size=3.2, bold=True))
        y = top + 5.0
        row_height = 4.8
        page.primitives.append(_rect(layer, left, y, right, min(page.height_mm - 42.0, y + row_height * (len(rows) + 1)), color="#8ca1b4", width=0.15))
        for header_x, header in zip((left + 1.0, left + (right - left) * 0.28, left + (right - left) * 0.70), ("ID", "Waarde", "Bron / omschrijving")):
            page.primitives.append(_text(layer, header_x, y + 3.4, header, size=2.2, bold=True))
        for index, row in enumerate(rows):
            row_y = y + row_height * (index + 1)
            if row_y + row_height > page.height_mm - 40.0:
                break
            page.primitives.append(_line(layer, (left, row_y), (right, row_y), color="#b8c8d6", width=0.1))
            for x, value in zip((left + 1.0, left + (right - left) * 0.28, left + (right - left) * 0.70), row):
                semantic_id = row[0] if layer == "dimensions" else ""
                page.primitives.append(_text(layer, x, row_y + 3.3, value, size=2.1, semantic_id=semantic_id))

    @classmethod
    def _add_section_view(
        cls,
        page: DrawingPage,
        *,
        vertices: np.ndarray,
        triangles: np.ndarray,
        rectangle: tuple[float, float, float, float],
        denominator: int,
        exact_shape: Any | None,
    ) -> tuple[str, tuple[np.ndarray, np.ndarray, float, tuple[float, float, float, float]]]:
        view_id = f"sheet-{page.number}-section-a-a"
        try:
            if exact_shape is None:
                raise RuntimeError("geen exact BREP")
            polylines = DrawingProjectionModel.exact_section_polylines(exact_shape, axis="x")
        except Exception:
            # This remains useful as a review projection, while the linter
            # prevents it from masquerading as a production section.
            primitive_start = len(page.primitives)
            projected, screen, scale, _method = cls._add_view(
                page,
                vertices=vertices,
                triangles=triangles,
                view="side",
                rectangle=rectangle,
                denominator=denominator,
                exact_shape=exact_shape,
            )
            generated_id = page.view_ids[-1]
            page.view_ids[-1] = view_id
            for primitive in page.primitives[primitive_start:]:
                if primitive.semantic_id == generated_id:
                    primitive.semantic_id = view_id
                elif primitive.semantic_id.startswith(f"{generated_id}-"):
                    primitive.semantic_id = f"{view_id}{primitive.semantic_id[len(generated_id):]}"
            for primitive in page.primitives[primitive_start:]:
                if primitive.layer == "views" and primitive.kind == "text":
                    primitive.text = "SECTION A-A"
                    break
            page.primitives.append(
                _text(
                    "annotations",
                    rectangle[0] + 2.0,
                    rectangle[1] + 10.0,
                    "REVIEWPROJECTIE - GEEN BREP-SNEDE",
                    size=2.2,
                    bold=True,
                    color="#a23b32",
                )
            )
            return "projection_fallback", (projected, screen, scale, rectangle)

        page.view_ids.append(view_id)
        page.primitives.extend(
            (
                _rect("views", *rectangle, color="#b8c8d6", width=0.18, semantic_id=view_id),
                _text("views", rectangle[0] + 2.0, rectangle[1] + 5.0, "SECTION A-A", size=2.8, bold=True),
            )
        )

        all_points = np.vstack(polylines)
        minimum = all_points.min(axis=0)
        maximum = all_points.max(axis=0)
        center = (minimum + maximum) * 0.5
        available = np.asarray(
            (
                max(1.0, rectangle[2] - rectangle[0] - 14.0),
                max(1.0, rectangle[3] - rectangle[1] - 18.0),
            )
        )
        span = np.maximum(maximum - minimum, 1.0)
        scale = min(1.0 / max(1.0, float(denominator)), float(np.min(available / span)))
        target = np.asarray(
            (
                (rectangle[0] + rectangle[2]) * 0.5,
                (rectangle[1] + rectangle[3]) * 0.5 + 2.0,
            )
        )

        def place(polyline: np.ndarray) -> np.ndarray:
            result = np.empty_like(polyline, dtype=float)
            result[:, 0] = (polyline[:, 0] - center[0]) * scale + target[0]
            result[:, 1] = target[1] - (polyline[:, 1] - center[1]) * scale
            return result

        screen_polylines = tuple(place(polyline) for polyline in polylines)
        for index, polyline in enumerate(screen_polylines, start=1):
            page.primitives.append(
                DrawingPrimitive(
                    "polyline",
                    "visible",
                    points=polyline.tolist(),
                    color="#173b5d",
                    width=0.32,
                    refs=["section-a-a"],
                    semantic_id=f"{view_id}-edge-{index}",
                )
            )

        # Clip 45-degree hatch strokes to the exact section boundaries by an
        # even/odd intersection rule, including internal openings.
        screen_points = np.vstack(screen_polylines)
        hatch_value = float(np.min(screen_points[:, 0] + screen_points[:, 1])) + 1.5
        hatch_end = float(np.max(screen_points[:, 0] + screen_points[:, 1]))
        while hatch_value < hatch_end:
            intersections: list[np.ndarray] = []
            for polyline in screen_polylines:
                for first, second in zip(polyline, polyline[1:]):
                    first_distance = float(first[0] + first[1] - hatch_value)
                    second_distance = float(second[0] + second[1] - hatch_value)
                    if first_distance * second_distance > 0.0 or abs(first_distance - second_distance) < 1.0e-9:
                        continue
                    ratio = first_distance / (first_distance - second_distance)
                    if -1.0e-9 <= ratio <= 1.0 + 1.0e-9:
                        intersections.append(first + ratio * (second - first))
            unique = {
                (round(float(point[0]), 5), round(float(point[1]), 5)): point
                for point in intersections
            }
            ordered = sorted(unique.values(), key=lambda point: float(point[0]))
            for index in range(0, len(ordered) - 1, 2):
                page.primitives.append(
                    _line(
                        "hatch",
                        ordered[index],
                        ordered[index + 1],
                        color="#70879d",
                        width=0.1,
                        refs=("section-a-a",),
                    )
                )
            hatch_value += 3.0
        return "occt_brep_section", (all_points, screen_points, scale, rectangle)

    @classmethod
    def build(cls, request: DrawingBuildRequest) -> DrawingDocument:
        vertices = np.asarray(request.vertices, dtype=float).reshape((-1, 3))
        triangles = np.asarray(request.triangles, dtype=int).reshape((-1, 3))
        if vertices.size == 0 or triangles.size == 0:
            raise ValueError("DrawingDocument vereist niet-lege geometrie")
        views = tuple(dict.fromkeys(view for view in request.views if view in VIEW_LABELS))
        if not views:
            raise ValueError("Selecteer ten minste één geldig aanzicht")
        sheet_format = str(request.sheet_format).upper()
        orientation = str(request.orientation).lower()
        unit = str(request.unit).lower()
        width, height = page_size_mm(sheet_format, orientation)
        rectangles = cls._view_rectangles(len(views), width, height, title_block=request.title_block_enabled)
        denominator, adjusted = cls._fit_scale(vertices, views, rectangles, request.scale_denominator)
        features = cls._normalise_features(request.features)
        manual = cls._normalise_manual(request.manual_dimensions)
        semantic_dimensions = [dict(item) for item in request.dimensions]
        if request.dimensions_enabled:
            present = {str(item.get("id") or "") for item in semantic_dimensions}
            projected, _ = DrawingProjectionModel.project(vertices, views[0])
            span = projected.max(axis=0) - projected.min(axis=0)
            if "overall-x" not in present:
                semantic_dimensions.append({"id": "overall-x", "kind": "linear", "axis": "x", "value_mm": float(span[0]), "critical": True, "feature_refs": []})
            if "overall-y" not in present:
                semantic_dimensions.append({"id": "overall-y", "kind": "linear", "axis": "y", "value_mm": float(span[1]), "critical": True, "feature_refs": []})
            semantic_dimensions.extend(manual)
        mode = str(request.dimension_mode or "Hoofdmaten")
        manual_ids = {str(item.get("id") or "") for item in manual}
        if mode == "Productiematen":
            display_dimensions = list(semantic_dimensions)
        elif mode == "Contour + gaten":
            display_dimensions = [
                item
                for item in semantic_dimensions
                if str(item.get("id") or "") in manual_ids
                or str(item.get("id") or "").startswith(("overall-", "hole-", "contour-"))
                or str(item.get("display_group") or "") in {"overall", "holes", "radii", "hole-positions-x", "hole-positions-y"}
            ]
        else:
            display_dimensions = [
                item
                for item in semantic_dimensions
                if str(item.get("id") or "") in manual_ids
                or str(item.get("id") or "").startswith("overall-")
                or str(item.get("display_group") or "") == "overall"
            ]
        page = cls._base_page(1, "TECHNISCHE WERKPLAATSTEKENING", width, height)
        geometry: dict[str, tuple[np.ndarray, np.ndarray, float, tuple[float, float, float, float]]] = {}
        view_contexts: list[dict[str, Any]] = []
        hlr_methods: list[str] = []
        section_method = "not_requested"
        for view, rectangle in zip(views, rectangles):
            projected, screen, scale, method = cls._add_view(
                page,
                vertices=vertices,
                triangles=triangles,
                view=view,
                rectangle=rectangle,
                denominator=denominator,
                exact_shape=request.exact_shape,
                assembly_components=request.assembly_components,
            )
            geometry[view] = (projected, screen, scale, rectangle)
            projected_center = (projected.min(axis=0) + projected.max(axis=0)) * 0.5
            view_contexts.append(
                {
                    "view": view,
                    "view_id": page.view_ids[-1],
                    "page_number": page.number,
                    "sheet_id": f"sheet-{page.number}",
                    "rectangle": [float(value) for value in rectangle],
                    "projected_center": [float(value) for value in projected_center],
                    "sheet_center": [
                        float((rectangle[0] + rectangle[2]) * 0.5),
                        float((rectangle[1] + rectangle[3]) * 0.5 + 2.0),
                    ],
                    "scale": float(scale),
                }
            )
            hlr_methods.append(method)
        cls._add_features(page, features=features, views=views, geometry=geometry, unit=unit)
        cls._add_dimensions(
            page,
            geometry=geometry,
            primary_view=views[0],
            dimensions=display_dimensions,
            manual_dimensions=manual,
            unit=unit,
            enabled=request.dimensions_enabled,
        )

        pages = [page]
        schedule_required = bool(
            request.include_sections
            or request.include_details
            or display_dimensions
            or request.bom
            or request.notes
            or request.document_type == "assembly"
        )
        if schedule_required:
            detail_page = cls._base_page(2, "DETAILS / PRODUCTIEGEGEVENS", width, height)
            top = 23.0
            half = width * 0.5
            if request.include_sections:
                section_rect = (10.0, top, half - 4.0, min(height * 0.48, height - 52.0))
                section_method, section_geometry = cls._add_section_view(
                    detail_page,
                    vertices=vertices,
                    triangles=triangles,
                    rectangle=section_rect,
                    denominator=denominator,
                    exact_shape=request.exact_shape,
                )
                section_projected, _section_screen, section_scale, _section_rectangle = section_geometry
                section_id = detail_page.view_ids[-1]
                section_center = (section_projected.min(axis=0) + section_projected.max(axis=0)) * 0.5
                view_contexts.append(
                    {
                        "view": "section",
                        "view_id": section_id,
                        "page_number": detail_page.number,
                        "sheet_id": f"sheet-{detail_page.number}",
                        "rectangle": [float(value) for value in section_rect],
                        "projected_center": [float(value) for value in section_center],
                        "sheet_center": [float((section_rect[0] + section_rect[2]) * 0.5), float((section_rect[1] + section_rect[3]) * 0.5 + 2.0)],
                        "scale": float(section_scale),
                    }
                )
                cls._add_dimensions(
                    detail_page,
                    geometry={"section": section_geometry},
                    primary_view="section",
                    dimensions=(),
                    manual_dimensions=tuple(item for item in manual if str(item.get("view_id") or item.get("view") or "") == section_id),
                    unit=unit,
                    enabled=request.dimensions_enabled,
                    include_overall=False,
                )
            if request.include_details and features:
                detail_rect = (half + 4.0, top, width - 10.0, min(height * 0.48, height - 52.0))
                first = features[0]
                first_kind = str(first.get("kind") or "feature")
                first_side = str(first.get("reference_side") or dict(first.get("parameters") or {}).get("face") or "").lower()
                detail_view = cls._feature_target_view(first_kind, first_side, views)
                detail_projected, detail_screen, detail_scale, method = cls._add_view(
                    detail_page,
                    vertices=vertices,
                    triangles=triangles,
                    view=detail_view,
                    rectangle=detail_rect,
                    denominator=max(1, denominator // 2),
                    exact_shape=request.exact_shape,
                )
                hlr_methods.append(method)
                detail_id = detail_page.view_ids[-1]
                detail_center = (detail_projected.min(axis=0) + detail_projected.max(axis=0)) * 0.5
                view_contexts.append(
                    {
                        "view": detail_view,
                        "view_id": detail_id,
                        "page_number": detail_page.number,
                        "sheet_id": f"sheet-{detail_page.number}",
                        "rectangle": [float(value) for value in detail_rect],
                        "projected_center": [float(value) for value in detail_center],
                        "sheet_center": [float((detail_rect[0] + detail_rect[2]) * 0.5), float((detail_rect[1] + detail_rect[3]) * 0.5 + 2.0)],
                        "scale": float(detail_scale),
                        "feature_id": str(first.get("feature_id") or ""),
                        "detail": True,
                    }
                )
                cls._add_features(
                    detail_page,
                    features=(first,),
                    views=(detail_view,),
                    geometry={detail_view: (detail_projected, detail_screen, detail_scale, detail_rect)},
                    unit=unit,
                )
                first_feature = str(first.get("feature_id") or "H1")
                detail_page.primitives.append(_text("annotations", detail_rect[0] + 2.0, detail_rect[1] + 10.0, f"DETAIL {first_feature}", size=2.6, bold=True, refs=(first_feature,), semantic_id=f"{first_feature}-detail"))
                cls._add_dimensions(
                    detail_page,
                    geometry={detail_view: (detail_projected, detail_screen, detail_scale, detail_rect)},
                    primary_view=detail_view,
                    dimensions=(),
                    manual_dimensions=tuple(item for item in manual if str(item.get("view_id") or item.get("view") or "") == detail_id),
                    unit=unit,
                    enabled=request.dimensions_enabled,
                    include_overall=False,
                )

            schedule_top = max(height * 0.50, 82.0)
            dimension_rows = [
                (
                    str(item.get("id") or ""),
                    _format_value(_number(item, "value_mm"), unit),
                    str(item.get("source_field") or item.get("kind") or "maatobject"),
                )
                for item in display_dimensions
            ]
            bom_rows = [
                (
                    str(item.get("mark") or item.get("position") or item.get("id") or ""),
                    str(item.get("quantity") or item.get("qty") or "1"),
                    str(item.get("profile") or item.get("description") or item.get("material") or ""),
                )
                for item in request.bom
            ]
            first_capacity = max(1, int((height - 47.0 - schedule_top) / 4.8))
            if dimension_rows:
                cls._add_schedule(detail_page, title="MAATVOERING / DIMENSIONGRAPH", rows=dimension_rows[:first_capacity], left=10.0, top=schedule_top, right=half - 4.0, layer="dimensions")
            if bom_rows:
                cls._add_schedule(detail_page, title="BOM / MATERIAALLIJST", rows=bom_rows[:first_capacity], left=half + 4.0, top=schedule_top, right=width - 10.0, layer="bom")
            notes_need_page = bool(
                (request.notes or request.revisions)
                and max(len(dimension_rows), len(bom_rows)) > 8
            )
            notes_top = min(height - 48.0, schedule_top + 15.0 + min(len(bom_rows), 8) * 4.8)
            if request.notes and not notes_need_page:
                detail_page.primitives.append(_text("notes", half + 4.0, notes_top, "ALGEMENE NOTITIES", size=3.0, bold=True))
                for index, note in enumerate(request.notes[:8], start=1):
                    detail_page.primitives.append(_text("notes", half + 4.0, notes_top + 4.5 * index, f"{index}. {note}", size=2.2))
            if request.revisions and not notes_need_page:
                revision_top = notes_top + 5.0 * (len(request.notes[:8]) + 2)
                detail_page.primitives.append(_text("notes", half + 4.0, revision_top, "REVISIETABEL", size=3.0, bold=True))
                for index, revision in enumerate(request.revisions[:8], start=1):
                    label = " | ".join(
                        str(revision.get(key) or "")
                        for key in ("revision", "status", "date", "author")
                        if str(revision.get(key) or "")
                    )
                    detail_page.primitives.append(_text("notes", half + 4.0, revision_top + 4.5 * index, label, size=2.2))
            pages.append(detail_page)

            if request.include_details and len(features) > 1:
                for offset in range(1, len(features), 4):
                    chunk = features[offset : offset + 4]
                    detail_sheet = cls._base_page(len(pages) + 1, "FEATUREDETAILS", width, height)
                    detail_rectangles = cls._view_rectangles(
                        len(chunk),
                        width,
                        height,
                        title_block=request.title_block_enabled,
                    )
                    for feature, feature_rectangle in zip(chunk, detail_rectangles):
                        feature_id = str(feature.get("feature_id") or "FEATURE")
                        feature_kind = str(feature.get("kind") or "feature")
                        feature_side = str(
                            feature.get("reference_side")
                            or dict(feature.get("parameters") or {}).get("face")
                            or ""
                        ).lower()
                        feature_view = cls._feature_target_view(feature_kind, feature_side, views)
                        projected, screen, detail_scale, method = cls._add_view(
                            detail_sheet,
                            vertices=vertices,
                            triangles=triangles,
                            view=feature_view,
                            rectangle=feature_rectangle,
                            denominator=max(1, denominator // 2),
                            exact_shape=request.exact_shape,
                        )
                        hlr_methods.append(method)
                        detail_id = detail_sheet.view_ids[-1]
                        detail_center = (projected.min(axis=0) + projected.max(axis=0)) * 0.5
                        view_contexts.append(
                            {
                                "view": feature_view,
                                "view_id": detail_id,
                                "page_number": detail_sheet.number,
                                "sheet_id": f"sheet-{detail_sheet.number}",
                                "rectangle": [float(value) for value in feature_rectangle],
                                "projected_center": [float(value) for value in detail_center],
                                "sheet_center": [float((feature_rectangle[0] + feature_rectangle[2]) * 0.5), float((feature_rectangle[1] + feature_rectangle[3]) * 0.5 + 2.0)],
                                "scale": float(detail_scale),
                                "feature_id": feature_id,
                                "detail": True,
                            }
                        )
                        cls._add_features(
                            detail_sheet,
                            features=(feature,),
                            views=(feature_view,),
                            geometry={feature_view: (projected, screen, detail_scale, feature_rectangle)},
                            unit=unit,
                        )
                        detail_sheet.primitives.append(
                            _text(
                                "annotations",
                                feature_rectangle[0] + 2.0,
                                feature_rectangle[1] + 10.0,
                                f"DETAIL {feature_id}",
                                size=2.6,
                                bold=True,
                                refs=(feature_id,),
                                semantic_id=f"{feature_id}-detail",
                            )
                        )
                        cls._add_dimensions(
                            detail_sheet,
                            geometry={feature_view: (projected, screen, detail_scale, feature_rectangle)},
                            primary_view=feature_view,
                            dimensions=(),
                            manual_dimensions=tuple(item for item in manual if str(item.get("view_id") or item.get("view") or "") == detail_id),
                            unit=unit,
                            enabled=request.dimensions_enabled,
                            include_overall=False,
                        )
                    pages.append(detail_sheet)

            dimension_cursor = first_capacity
            bom_cursor = first_capacity
            continuation_top = 23.0
            continuation_capacity = max(1, int((height - 47.0 - continuation_top) / 4.8))
            while dimension_cursor < len(dimension_rows) or bom_cursor < len(bom_rows):
                continuation = cls._base_page(len(pages) + 1, "PRODUCTIEGEGEVENS - VERVOLG", width, height)
                if dimension_cursor < len(dimension_rows):
                    chunk = dimension_rows[dimension_cursor : dimension_cursor + continuation_capacity]
                    cls._add_schedule(continuation, title="MAATVOERING / DIMENSIONGRAPH - VERVOLG", rows=chunk, left=10.0, top=continuation_top, right=half - 4.0, layer="dimensions")
                    dimension_cursor += len(chunk)
                if bom_cursor < len(bom_rows):
                    chunk = bom_rows[bom_cursor : bom_cursor + continuation_capacity]
                    cls._add_schedule(continuation, title="BOM / MATERIAALLIJST - VERVOLG", rows=chunk, left=half + 4.0, top=continuation_top, right=width - 10.0, layer="bom")
                    bom_cursor += len(chunk)
                pages.append(continuation)
            if notes_need_page:
                note_page = cls._base_page(len(pages) + 1, "ALGEMENE NOTITIES / REVISIES", width, height)
                note_page.primitives.append(_text("notes", 10.0, 27.0, "ALGEMENE NOTITIES", size=3.2, bold=True))
                for index, note in enumerate(request.notes[:40], start=1):
                    note_page.primitives.append(_text("notes", 10.0, 27.0 + 5.0 * index, f"{index}. {note}", size=2.4))
                revision_top = 37.0 + 5.0 * min(len(request.notes), 40)
                note_page.primitives.append(_text("notes", 10.0, revision_top, "REVISIETABEL", size=3.2, bold=True))
                for index, revision in enumerate(request.revisions[:30], start=1):
                    label = " | ".join(
                        str(revision.get(key) or "")
                        for key in ("revision", "status", "date", "author")
                        if str(revision.get(key) or "")
                    )
                    note_page.primitives.append(_text("notes", 10.0, revision_top + 5.0 * index, label, size=2.4))
                pages.append(note_page)

        title_block = dict(request.title_block)
        if adjusted:
            notes = list(request.notes) + [f"Schaal automatisch aangepast naar 1:{denominator} om clipping te voorkomen."]
        else:
            notes = list(request.notes)
        if request.title_block_enabled:
            for current_page in pages:
                cls._add_title_block(
                    current_page,
                    title_block,
                    sheet_format=sheet_format,
                    orientation=orientation,
                    denominator=denominator,
                    unit=unit,
                    sheet_count=len(pages),
                )

        document = DrawingDocument(
            entity_id=str(request.entity_id),
            document_type=str(request.document_type),
            sheet_format=sheet_format,
            orientation=orientation,
            unit=unit,
            scale_denominator=denominator,
            geometry_basis=str(request.geometry_basis),
            geometry_sha256=str(request.geometry_sha256 or _hash_mesh(vertices, triangles)),
            manufacturing_sha256=str(request.manufacturing_sha256),
            expected_manufacturing_sha256=str(request.expected_manufacturing_sha256),
            source_revision=str(request.source_revision),
            pages=pages,
            title_block=title_block,
            revisions=[dict(item) for item in request.revisions],
            bom=[dict(item) for item in request.bom],
            notes=notes,
            dimensions=semantic_dimensions,
            dimension_chains=[dict(item) for item in request.dimension_chains],
            features=features,
            manual_dimensions=manual,
            view_contexts=view_contexts,
            dimension_style=dict(request.dimension_style),
            dimension_audit=[dict(item) for item in request.dimension_audit],
            dimension_editor_schema=str(request.dimension_editor_schema),
            dimension_editor_status=str(request.dimension_editor_status),
            hlr_method="occt_hlr" if hlr_methods and all(value == "occt_hlr" for value in hlr_methods) else "mesh_fallback",
            sections_requested=bool(request.include_sections),
            section_method=section_method,
            canonical_rebuild_current=bool(request.canonical_rebuild_current),
            canonical_payload_current=bool(request.canonical_payload_current),
            roundtrip_current=bool(request.roundtrip_current),
            dimension_mode=mode,
            dimensions_enabled=bool(request.dimensions_enabled),
            title_block_enabled=bool(request.title_block_enabled),
        )
        document.lint = DrawingLinter.lint(document).to_dict()
        document.seal()
        document.validate()
        return document


__all__ = ["DrawingBuildRequest", "ProductionDrawingEngine", "STANDARD_SCALES"]
