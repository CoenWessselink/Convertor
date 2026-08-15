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
            prop.SetLineWidth(3.0)
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
        """Build a transparent centre-point actor with stable point IDs.

        ``vtkPointPicker`` does not reliably expose the input-instance index of
        ``vtkGlyph3DMapper`` on every OpenGL/VTK backend.  The visible scene can
        therefore stay instanced, while a tiny nearly transparent point actor
        supplies a deterministic 1:1 mapping from picked point ID to CWS node
        ID.  This is a *project-level* pick proxy only; exact face/edge/feature
        picking remains the OCCT Part Workbench responsibility.
        """

        self._remove_pick_actor()
        vtk = self._vtk
        assert vtk is not None and self._renderer is not None

        points = vtk.vtkPoints()
        points.SetDataTypeToFloat()
        vertices = vtk.vtkCellArray()
        node_ids: list[str] = []
        for node_id in index.renderable_node_ids:
            if node_id not in state.visible_set:
                continue
            center = index.world_bounds_by_node[node_id].center + state.explode_offsets.get(node_id, Vector3.zero())
            point_id = points.InsertNextPoint(center.x, center.y, center.z)
            vertices.InsertNextCell(1)
            vertices.InsertCellPoint(point_id)
            node_ids.append(node_id)

        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetVerts(vertices)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.PickableOn()
        actor.GetProperty().SetRepresentationToPoints()
        actor.GetProperty().SetPointSize(1.0)
        # Visibility must remain on for VTK's software point picker.  A very
        # small opacity makes the proxy visually negligible in screenshots.
        actor.GetProperty().SetOpacity(0.001)
        actor.GetProperty().SetColor(0.055, 0.070, 0.095)
        actor.GetProperty().LightingOff()
        self._renderer.AddActor(actor)

        self._pick_actor = actor
        self._pick_polydata = polydata
        self._pick_node_ids = tuple(node_ids)

    @staticmethod
    def _signature(*values: object) -> str:
        digest = hashlib.sha256()
        for value in values:
            digest.update(repr(value).encode("utf-8", "surrogatepass"))
            digest.update(b"\0")
        return digest.hexdigest()

    def _rebuild_base(self, state: RenderState, index: SceneIndex) -> None:
        self._remove_groups(self._groups)
        self._groups = []
        visible = state.visible_set
        ghosted = state.ghosted_set
        transparency = state.transparency
        colors = state.colors
        entries_by_key: dict[tuple[RenderMode, tuple[float, float, float]], list[tuple[str, Vector3, Rgba]]] = {}
        for node_id in index.renderable_node_ids:
            if node_id not in visible:
                continue
            node = index.node(node_id)
            bounds = index.world_bounds_by_node[node_id]
            mode, color = self._style_for_node(
                node,
                colors=colors,
                transparency=transparency,
                ghosted=ghosted,
                preferences=state.display_preferences,
            )
            size_key = tuple(round(value, 6) for value in bounds.size.to_tuple())
            entries_by_key.setdefault((mode, size_key), []).append(
                (node_id, bounds.center + state.explode_offsets.get(node_id, Vector3.zero()), color)
            )
        for mode, size_key in sorted(entries_by_key, key=lambda item: (item[0].value, item[1])):
            group = self._build_group(mode, Vector3(*size_key), entries_by_key[(mode, size_key)])
            self._groups.append(group)
            self._actor_to_group[id(group.actor)] = group
        self._rebuild_pick_actor(state, index)

    def _rebuild_selection(self, state: RenderState, index: SceneIndex) -> None:
        if self._selection_groups:
            self._remove_groups(self._selection_groups)
            self._selection_groups = []
        visible = state.visible_set
        if not state.display_preferences.show_selection_outline:
            return
        entries_by_size: dict[tuple[float, float, float], list[tuple[str, Vector3, Rgba]]] = {}
        for node_id in state.selected_node_ids:
            if node_id not in visible or node_id not in index.world_bounds_by_node:
                continue
            bounds = index.world_bounds_by_node[node_id]
            size_key = tuple(round(value, 6) for value in bounds.size.to_tuple())
            entries_by_size.setdefault(size_key, []).append(
                (
                    node_id,
                    bounds.center + state.explode_offsets.get(node_id, Vector3.zero()),
                    state.display_preferences.selection_color,
                )
            )
        for size_key in sorted(entries_by_size):
            group = self._build_group(
                RenderMode.WIREFRAME,
                Vector3(*size_key),
                entries_by_size[size_key],
                selection=True,
            )
            self._selection_groups.append(group)
            self._actor_to_group[id(group.actor)] = group

    def _apply_background_theme(self, state: RenderState) -> None:
        if self._renderer is None:
            return
        theme = state.display_preferences.background_theme.value
        if theme == "light":
            self._renderer.SetBackground(0.90, 0.92, 0.95)
            self._renderer.SetBackground2(0.72, 0.78, 0.85)
        elif theme == "slate":
            self._renderer.SetBackground(0.10, 0.13, 0.17)
            self._renderer.SetBackground2(0.24, 0.28, 0.34)
        else:
            self._renderer.SetBackground(0.035, 0.045, 0.065)
            self._renderer.SetBackground2(0.11, 0.14, 0.19)
        self._renderer.GradientBackgroundOn()

    def _clip_planes(self, state: RenderState) -> list[Any]:
        """Build VTK clipping planes for the immutable render state."""
        if self._vtk is None:
            return []
        planes: list[Any] = []
        for section in state.section_planes[:12]:
            if not section.enabled:
                continue
            normal = section.normal.normalized()
            if section.flipped:
                normal = -normal
            plane = self._vtk.vtkPlane()
            plane.SetOrigin(*section.origin.to_tuple())
            plane.SetNormal(*normal.to_tuple())
            planes.append(plane)
        box = state.clipping_box
        if box is not None and box.enabled:
            minimum, maximum = box.bounds.minimum, box.bounds.maximum
            definitions = (
                (minimum, Vector3(1, 0, 0)),
                (maximum, Vector3(-1, 0, 0)),
                (minimum, Vector3(0, 1, 0)),
                (maximum, Vector3(0, -1, 0)),
                (minimum, Vector3(0, 0, 1)),
                (maximum, Vector3(0, 0, -1)),
            )
            for origin, normal in definitions:
                if box.inverted:
                    normal = -normal
                plane = self._vtk.vtkPlane()
                plane.SetOrigin(*origin.to_tuple())
                plane.SetNormal(*normal.to_tuple())
                planes.append(plane)
        return planes

    @staticmethod
    def _apply_planes_to_groups(groups: Iterable[_ActorGroup], planes: Iterable[Any]) -> None:
        plane_values = tuple(planes)
        for group in groups:
            mapper = group.mapper
            if not hasattr(mapper, "RemoveAllClippingPlanes"):
                continue
            mapper.RemoveAllClippingPlanes()
            for plane in plane_values:
                mapper.AddClippingPlane(plane)
            mapper.Modified()

    def apply_state(self, state: RenderState, index: SceneIndex) -> None:
        self._ensure_initialized()
        if self._scene is None or state.scene_hash != self._scene.scene_hash:
            raise ViewerError(
                "RenderState hoort niet bij de geladen scene",
                code=ViewerErrorCode.SCENE_HASH_MISMATCH,
                context={"state": state.scene_hash, "scene": getattr(self._scene, "scene_hash", None)},
            )
        self._state = state
        self._apply_background_theme(state)
        base_signature = self._signature(
            state.visible_node_ids,
            state.ghosted_node_ids,
            state.transparency_by_node,
            tuple((node_id, color) for node_id, color in state.color_by_node),
            state.display_preferences,
            state.section_planes,
            state.clipping_box,
            state.explode_offsets_by_node,
        )
        base_rebuilt = False
        if base_signature != self._base_signature:
            self._rebuild_base(state, index)
            self._base_signature = base_signature
            self._selection_signature = ""
            base_rebuilt = True
        selection_signature = self._signature(
            state.selected_node_ids,
            state.visible_node_ids,
            state.display_preferences.selection_color,
            state.display_preferences.show_selection_outline,
        )
        selection_rebuilt = False
        if selection_signature != self._selection_signature:
            self._rebuild_selection(state, index)
            self._selection_signature = selection_signature
            selection_rebuilt = True

        clipping_signature = self._signature(state.section_planes, state.clipping_box)
        has_clipping = bool(state.section_planes) or (
            state.clipping_box is not None and state.clipping_box.enabled
        )
        if base_rebuilt or clipping_signature != self._clipping_signature:
            planes = self._clip_planes(state)
            self._apply_planes_to_groups(self._groups, planes)
            self._apply_planes_to_groups(self._selection_groups, planes)
            self._clipping_signature = clipping_signature
        elif selection_rebuilt and has_clipping:
            # Selection actors are transient.  Reapply only to the new overlay;
            # do not invalidate every 10k-instance base mapper on each pick.
            self._apply_planes_to_groups(self._selection_groups, self._clip_planes(state))

    def set_camera(self, camera: CameraState) -> None:
        self._ensure_initialized()
        assert self._renderer is not None
        vtk_camera = self._renderer.GetActiveCamera()
        vtk_camera.SetPosition(*camera.position.to_tuple())
        vtk_camera.SetFocalPoint(*camera.target.to_tuple())
        vtk_camera.SetViewUp(*camera.up.to_tuple())
        vtk_camera.SetViewAngle(camera.field_of_view_deg)
        vtk_camera.SetParallelScale(camera.ortho_scale * 0.5)
        if camera.projection == ProjectionType.ORTHOGRAPHIC:
            vtk_camera.ParallelProjectionOn()
        else:
            vtk_camera.ParallelProjectionOff()
        vtk_camera.SetClippingRange(camera.near_plane, camera.far_plane)
        vtk_camera.OrthogonalizeViewUp()
        self._renderer.ResetCameraClippingRange()

    def render(self) -> None:
        self._ensure_initialized()
        assert self._render_window is not None
        self._render_window.Render()

    def world_to_display(self, point: Vector3) -> tuple[int, int]:
        self._ensure_initialized()
        assert self._renderer is not None
        self._renderer.SetWorldPoint(point.x, point.y, point.z, 1.0)
        self._renderer.WorldToDisplay()
        x, y, _ = self._renderer.GetDisplayPoint()
        return int(round(x)), int(round(y))

    def node_display_point(self, node_id: str) -> tuple[int, int]:
        if self._index is None:
            raise ViewerError("Geen scene geladen", code=ViewerErrorCode.NODE_NOT_FOUND)
        return self.world_to_display(self._index.world_bounds_by_node[node_id].center)

    def pick_at(self, x: int, y: int, index: SceneIndex) -> PickResult | None:
        self._ensure_initialized()
        assert self._vtk is not None and self._renderer is not None
        if self._pick_actor is None:
            self._last_pick = None
            return None
        picker = self._vtk.vtkPointPicker()
        picker.SetTolerance(0.012)
        picker.PickFromListOn()
        picker.AddPickList(self._pick_actor)
        if not picker.Pick(float(x), float(y), 0.0, self._renderer):
            self._last_pick = None
            return None
        point_id = int(picker.GetPointId())
        if point_id < 0 or point_id >= len(self._pick_node_ids):
            self._last_pick = None
            return None
        node_id = self._pick_node_ids[point_id]
        node = index.node(node_id)
        world_point_raw = picker.GetPickPosition()
        world_point = Vector3(*world_point_raw)
        local_point = node.local_bounds.center
        result = PickResult(
            node_id=node_id,
            entity_id=node.entity_id,
            part_id=(
                node.entity_id
                if node.kind in {NodeKind.PART, NodeKind.PURCHASED_ITEM}
                else None
            ),
            feature_id=(node.entity_id if node.kind == NodeKind.FEATURE else None),
            source_entity_id=node.source_entity_id,
            subshape_type=None,
            subshape_id=None,
            world_point=world_point,
            local_point=local_point,
            normal=None,
        )
        self._last_pick = result
        return result

    def screenshot(self, options: ScreenshotOptions) -> bytes:
        suffix = ".png" if options.format.lower() == "png" else ".png"
        with tempfile.TemporaryDirectory(prefix="cws-viewer-v2-shot-") as temp:
            path = Path(temp) / f"screenshot{suffix}"
            self.capture_png(path, width=options.width, height=options.height)
            return path.read_bytes()

    def capture_png(
        self,
        output: str | Path,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> Path:
        self._ensure_initialized()
        assert self._vtk is not None and self._render_window is not None
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        original_size = tuple(self._render_window.GetSize())
        if width and height:
            self._render_window.SetSize(int(width), int(height))
        try:
            self.render()
            image_filter = self._vtk.vtkWindowToImageFilter()
            image_filter.SetInput(self._render_window)
            image_filter.SetInputBufferTypeToRGBA()
            image_filter.ReadFrontBufferOff()
            image_filter.Update()
            writer = self._vtk.vtkPNGWriter()
            writer.SetFileName(str(path))
            writer.SetInputConnection(image_filter.GetOutputPort())
            writer.Write()
        finally:
            if width and height:
                self._render_window.SetSize(*original_size)
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("VTK-screenshot kon niet worden geschreven")
        return path

    def resize(self, width: int, height: int) -> None:
        self._ensure_initialized()
        if width <= 0 or height <= 0:
            raise ValueError("Rendererafmetingen moeten positief zijn")
        self._width = int(width)
        self._height = int(height)
        assert self._render_window is not None
        self._render_window.SetSize(self._width, self._height)

    def clear_scene(self) -> None:
        self._remove_pick_actor()
        if self._renderer is not None:
            self._renderer.RemoveAllViewProps()
        self._groups = []
        self._actor_to_group.clear()
        self._selection_groups = []
        self._state = None
        self._scene = None
        self._index = None
        self._base_signature = ""
        self._selection_signature = ""
        self._clipping_signature = ""
        self._last_pick = None

    def shutdown(self) -> None:
        if not self._initialized:
            return
        try:
            self.clear_scene()
            if self._render_window is not None and self._renderer is not None:
                self._render_window.RemoveRenderer(self._renderer)
                finalize = getattr(self._render_window, "Finalize", None)
                if callable(finalize):
                    finalize()
        finally:
            self._renderer = None
            self._render_window = None
            self._vtk = None
            self._initialized = False


__all__ = ["VtkProjectBackend"]
