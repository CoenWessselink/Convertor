"""VTK V2 project-scene renderer.

V2 renders validated :class:`ProjectScene` nodes as instanced display boxes.
This is intentionally a display representation based on node bounds; exact BREP
and subshape picking remain the OCCT Part Workbench responsibility (V6).
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.metadata
from pathlib import Path
import tempfile
from typing import Any, Iterable

from cws_viewer.contracts.enums import MeasurementKind, NodeKind, ProjectionType, RenderMode
from cws_viewer.contracts.scene import ProjectScene, SceneNode, StyleDefinition
from cws_viewer.contracts.state import (
    CameraState,
    PickResult,
    ScreenshotOptions,
    ViewerCapabilities,
    ViewerDisplayPreferences,
)
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import Rgba, Vector3
from cws_viewer.rendering.contracts import RenderState


def _vtk_module() -> Any:
    try:
        import vtk  # type: ignore

        return vtk
    except Exception as exc:  # pragma: no cover - diagnostics/Windows CI
        raise ViewerError(
            "VTK-projectrenderer is niet beschikbaar",
            code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            context={"backend": "vtk-project-v2", "error": str(exc)},
        ) from exc


def _version() -> str:
    try:
        return importlib.metadata.version("vtk")
    except importlib.metadata.PackageNotFoundError:
        return ""


_DEFAULT_COLORS: dict[NodeKind, Rgba] = {
    NodeKind.PART: Rgba(0.30, 0.62, 0.88, 1.0),
    NodeKind.PURCHASED_ITEM: Rgba(0.56, 0.64, 0.72, 1.0),
    NodeKind.FASTENER: Rgba(0.95, 0.74, 0.26, 1.0),
    NodeKind.WELD: Rgba(0.88, 0.38, 0.52, 1.0),
    NodeKind.REFERENCE: Rgba(0.48, 0.55, 0.62, 0.65),
    NodeKind.FEATURE: Rgba(0.35, 0.84, 0.64, 1.0),
}


@dataclass(slots=True)
class _ActorGroup:
    mode: RenderMode
    actor: Any
    mapper: Any
    polydata: Any
    points: Any
    source: Any
    node_ids: tuple[str, ...]


class VtkProjectBackend:
    """Instanced VTK renderer for the complete V2 project scene."""

    def __init__(self, *, render_window: Any | None = None, offscreen: bool = True) -> None:
        self._external_render_window = render_window
        self._offscreen = bool(offscreen)
        self._vtk: Any | None = None
        self._render_window: Any | None = None
        self._renderer: Any | None = None
        self._scene: ProjectScene | None = None
        self._index: SceneIndex | None = None
        self._state: RenderState | None = None
        self._groups: list[_ActorGroup] = []
        self._actor_to_group: dict[int, _ActorGroup] = {}
        self._selection_groups: list[_ActorGroup] = []
        self._pick_actor: Any | None = None
        self._pick_polydata: Any | None = None
        self._pick_node_ids: tuple[str, ...] = ()
        self._initialized = False
        self._width = 0
        self._height = 0
        self._base_signature = ""
        self._selection_signature = ""
        self._last_pick: PickResult | None = None
        self._clipping_signature = ""

    def capabilities(self) -> ViewerCapabilities:
        return ViewerCapabilities(
            renderer_backend="vtk-project-v2",
            backend_version=_version(),
            supports_large_mesh_scene=True,
            supports_exact_brep=False,
            supports_subshape_picking=False,
            supports_multi_section=True,
            supports_measurements=frozenset({MeasurementKind.POINT, MeasurementKind.COORDINATES}),
            supports_point_clouds=False,
            supports_offscreen_render=True,
            supports_hardware_acceleration=not self._offscreen,
            max_clip_planes=12,
            notes=(
                "V2 gebruikt instanced bounding-box glyphs voor het synthetische projectmodel.",
                "Exacte meshresources en lazy geometry volgen in V3; exact BREP blijft OCCT/V6.",
            ),
        )

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._renderer is None or self._render_window is None:
            raise ViewerError(
                "VTK-projectrenderer is niet geïnitialiseerd",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
                context={"backend": "vtk-project-v2"},
            )

    def initialize(self, *, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Rendererafmetingen moeten positief zijn")
        vtk = _vtk_module()
        self._vtk = vtk
        self._width = int(width)
        self._height = int(height)
        renderer = vtk.vtkRenderer()
        renderer.SetBackground(0.055, 0.070, 0.095)
        renderer.SetBackground2(0.15, 0.18, 0.23)
        renderer.GradientBackgroundOn()
        # Full depth peeling is useful on an interactive GPU, but it turns a
        # 10k-node ghost-context screenshot into a pathological software-Mesa
        # workload.  CI/offscreen keeps deterministic alpha blending, while
        # the desktop backend uses a bounded number of peels.
        if self._offscreen:
            renderer.SetUseDepthPeeling(False)
        else:
            renderer.SetUseDepthPeeling(True)
            renderer.SetMaximumNumberOfPeels(8)
            renderer.SetOcclusionRatio(0.15)

        if self._external_render_window is None:
            render_window = vtk.vtkRenderWindow()
            if self._offscreen:
                render_window.SetOffScreenRendering(1)
        else:
            render_window = self._external_render_window
        render_window.SetSize(self._width, self._height)
        render_window.SetMultiSamples(4)
        render_window.AddRenderer(renderer)
        render_window.SetWindowName("CWS Viewer V2 — Projectscene")

        self._renderer = renderer
        self._render_window = render_window
        self._initialized = True

    def load_scene(self, scene: ProjectScene, index: SceneIndex) -> None:
        self._ensure_initialized()
        self.clear_scene()
        self._scene = scene
        self._index = index
        self._base_signature = ""
        self._selection_signature = ""

    def _style_for_node(
        self,
        node: SceneNode,
        *,
        colors: dict[str, Rgba],
        transparency: dict[str, float],
        ghosted: frozenset[str],
        preferences: ViewerDisplayPreferences | None = None,
    ) -> tuple[RenderMode, Rgba]:
        index = self._index
        assert index is not None
        style: StyleDefinition | None = (
            index.styles_by_id.get(node.style_id) if node.style_id else None
        )
        prefs = preferences or ViewerDisplayPreferences()
        mode = prefs.render_mode or (style.mode if style else RenderMode.SHADED_EDGES)
        color = colors.get(node.node_id) or (style.color if style else None) or _DEFAULT_COLORS.get(
            node.kind, Rgba(0.45, 0.65, 0.82, 1.0)
        )
        alpha = color.alpha * (1.0 - transparency.get(node.node_id, 0.0))
        if node.node_id in ghosted:
            alpha = min(alpha, prefs.ghost_opacity)
            color = Rgba(0.62, 0.68, 0.74, alpha)
        else:
            alpha = max(0.0, min(1.0, alpha))
            color = Rgba(color.red, color.green, color.blue, alpha)
        return mode, color

    @staticmethod
    def _rgba_bytes(color: Rgba) -> tuple[int, int, int, int]:
        return tuple(int(round(value * 255.0)) for value in (
            color.red,
            color.green,
            color.blue,
            color.alpha,
        ))  # type: ignore[return-value]

    def _build_group(
        self,
        mode: RenderMode,
        size: Vector3,
        entries: list[tuple[str, Vector3, Rgba]],
        *,
        selection: bool = False,
    ) -> _ActorGroup:
        vtk = self._vtk
        assert vtk is not None and self._renderer is not None
        points = vtk.vtkPoints()
        points.SetDataTypeToFloat()
        colors = vtk.vtkUnsignedCharArray()
        colors.SetName("cws_rgba")
        colors.SetNumberOfComponents(4)
        node_ids: list[str] = []

        for node_id, center, color in entries:
            points.InsertNextPoint(center.x, center.y, center.z)
            colors.InsertNextTypedTuple(self._rgba_bytes(color))
            node_ids.append(node_id)

        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.GetPointData().AddArray(colors)

        factor = 1.035 if selection else 1.0
        source = vtk.vtkCubeSource()
        source.SetXLength(max(size.x * factor, 1e-6))
        source.SetYLength(max(size.y * factor, 1e-6))
        source.SetZLength(max(size.z * factor, 1e-6))
        source.SetCenter(0.0, 0.0, 0.0)
        source.Update()

        mapper = vtk.vtkGlyph3DMapper()
        mapper.SetInputData(polydata)
        mapper.SetSourceConnection(source.GetOutputPort())
        mapper.ScalingOff()
        mapper.OrientOff()
        mapper.SetScalarModeToUsePointFieldData()
        mapper.SelectColorArray("cws_rgba")
        mapper.SetColorModeToDirectScalars()
        mapper.ScalarVisibilityOn()
        mapper.SetUseSelectionIds(False)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetInterpolationToPhong()
        if selection:
            prop.SetRepresentationToWireframe()
            prop.SetWidth(3.0)
            prop.SetEdgeVisibility(True)
            prop.LightingOff()
        elif mode == RenderMode.WIREFRAME:
            prop.SetRepresentationToWireframe()
            prop.SetLineWidth(1.3)
        elif mode == RenderMode.SHADED:
            prop.SetRepresentationToSurface()
            prop.SetEdgeVisibility(False)
        else:
            prop.SetRepresentationToSurface()
            prop.SetEdgeVisibility(True)
            prop.SetEdgeColor(0.07, 0.10, 0.14)
            prop.SetLineWidth(0.65)

        self._renderer.AddActor(actor)
        return _ActorGroup(mode, actor, mapper, polydata, points, source, tuple(node_ids))

    def _remove_groups(self, groups: Iterable[_ActorGroup]) -> None:
        if self._renderer is None:
            return
        for group in groups:
            self._renderer.RemoveActor(group.actor)
            self._actor_to_group.pop(id(group.actor), None)

    def _remove_pick_actor(self) -> None:
        if self._renderer is not None and self._pick_actor is not None:
            self._renderer.RemoveActor(self._pick_actor)
        self._pick_actor = None
        self._pick_polydata = None
        self._pick_node_ids = ()

    def _rebuild_pick_actor(self, state: RenderState, index: SceneIndex) -> None:
        """Build a transparent centre-point actor with stable point IDs