"""Viewer state contracts independent from renderer/UI technology."""
from __future__ import annotations

from dataclasses import dataclass
import datetime as _dt
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from cws_viewer.math3d import BoundingBox, Rgba, Vector3

from .enums import (
    BackgroundTheme,
    ColorScheme,
    JobState,
    MeasurementKind,
    ProjectionType,
    RenderMode,
    SelectionLevel,
    StandardView,
)


def utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True, slots=True)
class ViewerCapabilities:
    renderer_backend: str
    backend_version: str
    supports_large_mesh_scene: bool
    supports_exact_brep: bool
    supports_subshape_picking: bool
    supports_multi_section: bool
    supports_measurements: frozenset[MeasurementKind]
    supports_point_clouds: bool
    supports_offscreen_render: bool
    supports_hardware_acceleration: bool
    max_clip_planes: int
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "supports_measurements",
            frozenset(MeasurementKind(value) for value in self.supports_measurements),
        )
        object.__setattr__(self, "notes", tuple(str(note) for note in self.notes))
        if self.max_clip_planes < 0:
            raise ValueError("max_clip_planes mag niet negatief zijn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "renderer_backend": self.renderer_backend,
            "backend_version": self.backend_version,
            "supports_large_mesh_scene": self.supports_large_mesh_scene,
            "supports_exact_brep": self.supports_exact_brep,
            "supports_subshape_picking": self.supports_subshape_picking,
            "supports_multi_section": self.supports_multi_section,
            "supports_measurements": sorted(item.value for item in self.supports_measurements),
            "supports_point_clouds": self.supports_point_clouds,
            "supports_offscreen_render": self.supports_offscreen_render,
            "supports_hardware_acceleration": self.supports_hardware_acceleration,
            "max_clip_planes": self.max_clip_planes,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ViewerDisplayPreferences:
    """Display-only settings; never manufacturing or canonical truth."""

    render_mode: RenderMode | None = None
    color_scheme: ColorScheme = ColorScheme.ORIGINAL
    background_theme: BackgroundTheme = BackgroundTheme.DARK
    ghost_opacity: float = 0.12
    selection_color: Rgba = Rgba(0.12, 0.92, 1.0, 1.0)
    edge_width: float = 0.65
    show_selection_outline: bool = True
    version: int = 1

    def __post_init__(self) -> None:
        if self.render_mode is not None:
            object.__setattr__(self, "render_mode", RenderMode(self.render_mode))
        object.__setattr__(self, "color_scheme", ColorScheme(self.color_scheme))
        object.__setattr__(self, "background_theme", BackgroundTheme(self.background_theme))
        if not 0.0 <= float(self.ghost_opacity) <= 1.0:
            raise ValueError("ghost_opacity moet tussen 0 en 1 liggen")
        if float(self.edge_width) <= 0.0:
            raise ValueError("edge_width moet positief zijn")
        if int(self.version) < 1:
            raise ValueError("ViewerDisplayPreferences version moet minimaal 1 zijn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "render_mode": None if self.render_mode is None else self.render_mode.value,
            "color_scheme": self.color_scheme.value,
            "background_theme": self.background_theme.value,
            "ghost_opacity": self.ghost_opacity,
            "selection_color": {
                "red": self.selection_color.red,
                "green": self.selection_color.green,
                "blue": self.selection_color.blue,
                "alpha": self.selection_color.alpha,
            },
            "edge_width": self.edge_width,
            "show_selection_outline": self.show_selection_outline,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "ViewerDisplayPreferences":
        data = dict(value or {})
        color = data.get("selection_color") or {}
        return cls(
            render_mode=(
                None
                if data.get("render_mode") in {None, "", "original"}
                else RenderMode(str(data["render_mode"]))
            ),
            color_scheme=ColorScheme(str(data.get("color_scheme", ColorScheme.ORIGINAL.value))),
            background_theme=BackgroundTheme(
                str(data.get("background_theme", BackgroundTheme.DARK.value))
            ),
            ghost_opacity=float(data.get("ghost_opacity", 0.12)),
            selection_color=Rgba(
                float(color.get("red", 0.12)),
                float(color.get("green", 0.92)),
                float(color.get("blue", 1.0)),
                float(color.get("alpha", 1.0)),
            ),
            edge_width=float(data.get("edge_width", 0.65)),
            show_selection_outline=bool(data.get("show_selection_outline", True)),
            version=int(data.get("version", 1)),
        )


@dataclass(frozen=True, slots=True)
class CameraState:
    position: Vector3
    target: Vector3
    up: Vector3
    projection: ProjectionType = ProjectionType.PERSPECTIVE
    field_of_view_deg: float = 45.0
    ortho_scale: float = 1000.0
    near_plane: float = 0.1
    far_plane: float = 10_000_000.0
    coordinate_system: str = "world"
    version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "projection", ProjectionType(self.projection))
        if (self.position - self.target).length() <= 1e-12:
            raise ValueError("Camerapositie en target mogen niet samenvallen")
        if self.up.length() <= 1e-12:
            raise ValueError("Camera-upvector mag geen nulvector zijn")
        if not 1.0 <= float(self.field_of_view_deg) < 179.0:
            raise ValueError("field_of_view_deg moet tussen 1 en 179 liggen")
        if self.ortho_scale <= 0 or self.near_plane <= 0 or self.far_plane <= self.near_plane:
            raise ValueError("Ongeldige camera clip-/schaalinstellingen")

    @classmethod
    def default(cls) -> "CameraState":
        return cls(
            position=Vector3(1000.0, -1000.0, 1000.0),
            target=Vector3.zero(),
            up=Vector3(0.0, 0.0, 1.0),
        )


@dataclass(frozen=True, slots=True)
class ColorAssignment:
    node_id: str
    color: Rgba


@dataclass(frozen=True, slots=True)
class SectionPlane:
    origin: Vector3
    normal: Vector3
    enabled: bool = True
    flipped: bool = False
    cap_mode: str = "none"
    display_color: Rgba = Rgba(0.15, 0.55, 0.95, 0.65)
    owner: str = ""
    coordinate_system: str = "world"
    plane_id: str = ""

    def __post_init__(self) -> None:
        if self.normal.length() <= 1e-12:
            raise ValueError("SectionPlane normal mag geen nulvector zijn")

    def with_id(self, plane_id: str | None = None) -> "SectionPlane":
        return SectionPlane(
            origin=self.origin,
            normal=self.normal.normalized(),
            enabled=self.enabled,
            flipped=self.flipped,
            cap_mode=self.cap_mode,
            display_color=self.display_color,
            owner=self.owner,
            coordinate_system=self.coordinate_system,
            plane_id=plane_id or self.plane_id or f"section-{uuid4()}",
        )


@dataclass(frozen=True, slots=True)
class ClippingBox:
    bounds: BoundingBox
    enabled: bool = True
    inverted: bool = False
    coordinate_system: str = "world"


@dataclass(frozen=True, slots=True)
class ScreenshotOptions:
    width: int = 1920
    height: int = 1080
    transparent_background: bool = False
    include_overlays: bool = True
    format: str = "png"

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Screenshotafmetingen moeten positief zijn")
        if self.format.lower() not in {"png", "jpeg", "jpg", "webp"}:
            raise ValueError("Niet-ondersteund screenshotformaat")


@dataclass(frozen=True, slots=True)
class ScenePatch:
    expected_scene_hash: str
    replacement_scene: Any | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class CompareScene:
    source_scene_hash: str
    target_scene_hash: str
    mapping_strategy: str = "stable_id_then_geometry"
    tolerance_profile: str = "cws-default"
    object_scope: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MeasurementAnchor:
    node_id: str
    entity_id: str
    feature_id: str | None
    subshape_type: str | None
    subshape_id: str | None
    world_point: Vector3
    local_point: Vector3 | None = None
    geometry_hash: str | None = None


@dataclass(frozen=True, slots=True)
class Measurement:
    measurement_id: str
    kind: MeasurementKind
    anchors: tuple[MeasurementAnchor, ...]
    value: float
    unit: str
    formatted_text: str
    provenance: str
    validity_hash: str
    status: str = "valid"

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", MeasurementKind(self.kind))
        object.__setattr__(self, "anchors", tuple(self.anchors))


@dataclass(frozen=True, slots=True)
class Viewpoint:
    viewpoint_id: str
    name: str
    camera: CameraState
    visible_node_ids: tuple[str, ...]
    hidden_node_ids: tuple[str, ...]
    selected_node_ids: tuple[str, ...]
    section_planes: tuple[SectionPlane, ...]
    clipping_box: ClippingBox | None
    scene_hash: str
    isolation_node_ids: tuple[str, ...] = ()
    ghost_context: bool = False
    transparency_by_node: tuple[tuple[str, float], ...] = ()
    color_by_node: tuple[tuple[str, Rgba], ...] = ()
    display_preferences: ViewerDisplayPreferences = ViewerDisplayPreferences()
    created_at: str = ""
    owner: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "visible_node_ids", tuple(self.visible_node_ids))
        object.__setattr__(self, "hidden_node_ids", tuple(self.hidden_node_ids))
        object.__setattr__(self, "selected_node_ids", tuple(self.selected_node_ids))
        object.__setattr__(self, "section_planes", tuple(self.section_planes))
        object.__setattr__(self, "isolation_node_ids", tuple(self.isolation_node_ids))
        object.__setattr__(
            self,
            "transparency_by_node",
            tuple((str(node_id), float(value)) for node_id, value in self.transparency_by_node),
        )
        object.__setattr__(
            self,
            "color_by_node",
            tuple((str(node_id), color) for node_id, color in self.color_by_node),
        )
        if not isinstance(self.display_preferences, ViewerDisplayPreferences):
            object.__setattr__(
                self,
                "display_preferences",
                ViewerDisplayPreferences.from_dict(self.display_preferences),
            )
        if not self.created_at:
            object.__setattr__(self, "created_at", utc_now_iso())


@dataclass(frozen=True, slots=True)
class PickResult:
    node_id: str
    entity_id: str
    part_id: str | None
    feature_id: str | None
    source_entity_id: str | None
    subshape_type: str | None
    subshape_id: str | None
    world_point: Vector3
    local_point: Vector3 | None
    normal: Vector3 | None


@dataclass(frozen=True, slots=True)
class SelectionSet:
    node_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    primary_node_id: str | None
    level: SelectionLevel
    timestamp: str = ""
    feature_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_ids", tuple(self.node_ids))
        object.__setattr__(self, "entity_ids", tuple(self.entity_ids))
        object.__setattr__(self, "level", SelectionLevel(self.level))
        if not self.timestamp:
            object.__setattr__(self, "timestamp", utc_now_iso())


@dataclass(frozen=True, slots=True)
class JobHandle:
    job_id: str
    state: JobState
    progress: float = 1.0
    message: str = ""
    result_ref: str | None = None
    error: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", JobState(self.state))
        if not 0.0 <= self.progress <= 1.0:
            raise ValueError("Jobprogress moet tussen 0 en 1 liggen")
        if self.error is not None:
            object.__setattr__(self, "error", MappingProxyType(dict(self.error)))

    @classmethod
    def succeeded(cls, message: str = "", *, result_ref: str | None = None) -> "JobHandle":
        return cls(
            job_id=f"job-{uuid4()}",
            state=JobState.SUCCEEDED,
            progress=1.0,
            message=message,
            result_ref=result_ref,
        )


__all__ = [
    "ViewerCapabilities",
    "ViewerDisplayPreferences",
    "CameraState",
    "ColorAssignment",
    "SectionPlane",
    "ClippingBox",
    "ScreenshotOptions",
    "ScenePatch",
    "CompareScene",
    "MeasurementAnchor",
    "Measurement",
    "Viewpoint",
    "PickResult",
    "SelectionSet",
    "JobHandle",
    "utc_now_iso",
]
