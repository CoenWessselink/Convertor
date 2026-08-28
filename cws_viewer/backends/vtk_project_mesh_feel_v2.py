"""Second-generation interactive quality renderer for the CWS Viewer.

The renderer keeps the previous triangle-edge suppression, adds source-colour
friendly lighting/contact shading, a stronger selected-object highlight and
measurement graphics that stay readable while the camera moves.
"""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Any, Iterable

from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend
from cws_viewer.backends.vtk_project_mesh_feel import VtkProjectMeshFeelBackend
from cws_viewer.contracts.enums import MeasurementKind
from cws_viewer.contracts.state import ViewerCapabilities
from cws_viewer.math3d import Matrix4, Rgba, Vector3


class VtkProjectMeshFeelV2Backend(VtkProjectMeshFeelBackend):
    """High-quality large-model renderer with non-destructive review overlays."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._highlighted_nodes: set[str] = set()
        self._selection_fill_groups: list[Any] = []
        self._measurement_label_bindings: list[tuple[Any, Vector3, tuple[int, int]]] = []
        self._measurement_preview_actors: list[Any] = []
        self._measurement_preview_labels: list[tuple[Any, Vector3, tuple[int, int]]] = []
        self._ssao_pass: Any | None = None
        self._light_kit: Any | None = None
        self._realistic_rendering = True
        self._ral_override: tuple[int, int, int] | None = None
        self._ral_refresh_all = False
        self._active_index: Any | None = None

    def capabilities(self) -> ViewerCapabilities:
        base = super().capabilities()
        return replace(
            base,
            renderer_backend="vtk-project-mesh-feel-v2",
            notes=tuple(base.notes)
            + (
                "IFC-bronkleuren blijven de normale original-colour basis.",
                "Interactieve hardware gebruikt SSAO/contactschaduw waar VTK dit ondersteunt.",
                "Selectie combineert feature-edge outline met een lichte fill-highlight.",
                "Meetlabels zijn 2D foreground overlays gekoppeld aan 3D meetankers.",
            ),
        )

    def initialize(self, *, width: int, height: int) -> None:
        super().initialize(width=width, height=height)
        renderer = self._renderer
        vtk = self._vtk
        if renderer is None or vtk is None:
            return
        fxaa_off = getattr(renderer, "UseFXAAOff", None)
        if callable(fxaa_off):
            fxaa_off()
        try:
            from vtkmodules.vtkRenderingOpenGL2 import vtkRenderStepsPass, vtkSSAOPass

            render_steps = vtkRenderStepsPass()
            ssao_pass = vtkSSAOPass()
            ssao_pass.SetDelegatePass(render_steps)
            ssao_pass.SetRadius(120.0)
            ssao_pass.SetBias(0.01)
            ssao_pass.SetKernelSize(64)
            ssao_pass.BlurOn()
            renderer.SetPass(ssao_pass)
            self._ssao_pass = ssao_pass
        except Exception:
            renderer.SetPass(None)
            self._ssao_pass = None
        window = self._render_window
        if window is not None:
            for method_name in ("LineSmoothingOn", "PolygonSmoothingOn"):
                method = getattr(window, method_name, None)
                if callable(method):
                    method()

        try:
            kit = vtk.vtkLightKit()
            for name, value in (
                ("SetKeyLightIntensity", 0.90),
                ("SetKeyToFillRatio", 2.25),
                ("SetKeyToHeadRatio", 2.50),
                ("SetKeyToBackRatio", 3.20),
            ):
                method = getattr(kit, name, None)
                if callable(method):
                    method(value)
            add = getattr(kit, "AddLightsToRenderer", None)
            if callable(add):
                auto_off = getattr(renderer, "AutomaticLightCreationOff", None)
                if callable(auto_off):
                    auto_off()
                add(renderer)
                self._light_kit = kit
        except Exception:
            self._light_kit = None

        # SSAO is intentionally disabled. On large IFC scenes it introduced
        # stippling, blurred edges and a visible frame-time change while orbiting.

    @staticmethod
    def _quality_material(prop: Any) -> None:
        prop.SetInterpolationToPhong()
        # Keep source IFC RGB visually authoritative.  A high ambient share
        # prevents the camera lights from turning Trimble-bright object colours
        # into the much darker greens seen in the previous build, while a small
        # diffuse/specular share still gives profiles readable face depth.
        # Calibrated against the same live IFC in Trimble. The former material
        # measured only 51/152/51 for green steel versus 94/215/94 in Trimble.
        prop.SetAmbient(0.36)
        prop.SetDiffuse(0.60)
        prop.SetSpecular(0.08)
        prop.SetSpecularPower(28.0)

    def set_realistic_rendering(self, enabled: bool) -> None:
        """Switch between a realistic steel finish and a crisp review finish."""
        self._realistic_rendering = bool(enabled)
        renderer = self._renderer
        if renderer is not None:
            shadow_method = getattr(
                renderer,
                "UseShadowsOn" if self._realistic_rendering else "UseShadowsOff",
                None,
            )
            if callable(shadow_method):
                try:
                    shadow_method()
                except Exception:
                    pass
        for group in self._mesh_groups:
            prop = group.actor.GetProperty()
            if self._realistic_rendering:
                pbr = getattr(prop, "SetInterpolationToPBR", None)
                if callable(pbr):
                    pbr()
                    metallic = getattr(prop, "SetMetallic", None)
                    roughness = getattr(prop, "SetRoughness", None)
                    if callable(metallic):
                        metallic(0.12)
                    if callable(roughness):
                        roughness(0.34)
                else:
                    self._quality_material(prop)
                prop.SetAmbient(0.28)
                prop.SetDiffuse(0.68)
                prop.SetSpecular(0.22)
                prop.SetSpecularPower(42.0)
                prop.EdgeVisibilityOff()
                prop.SetEdgeColor(0.035, 0.05, 0.065)
                prop.SetLineWidth(1.0)
                prop.LightingOn()
            else:
                prop.SetInterpolationToPhong()
                prop.SetAmbient(0.48)
                prop.SetDiffuse(0.50)
                prop.SetSpecular(0.04)
                prop.SetSpecularPower(18.0)
                prop.SetEdgeColor(0.055, 0.075, 0.095)
                prop.SetLineWidth(0.8)
                prop.EdgeVisibilityOff()
                prop.LightingOn()
        self.render()

    def set_ral_colour(self, rgb: tuple[int, int, int] | None) -> None:
        """Apply an sRGB display representation of a RAL colour or restore IFC."""
        if rgb is None:
            self._ral_override = None
        else:
            self._ral_override = tuple(max(0, min(255, int(value))) for value in rgb)
        self._ral_refresh_all = True
        if self._state is not None and self._active_index is not None:
            self._sync_selection_fill(self._state, self._active_index)
        self.render()

    @staticmethod
    def _blend_selection(rgba: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        # The reference workflow consistently uses a saturated engineering blue
        # for selected steel.  Yellow-on-green was too subtle on IFC models.
        target = (255, 210, 0)
        amount = 0.94
        return (
            int(round(rgba[0] * (1.0 - amount) + target[0] * amount)),
            int(round(rgba[1] * (1.0 - amount) + target[1] * amount)),
            int(round(rgba[2] * (1.0 - amount) + target[2] * amount)),
            rgba[3],
        )

    def _apply_background_theme(self, state: Any) -> None:
        if self._renderer is None:
            return
        theme = state.display_preferences.background_theme.value
        if theme == "light":
            # Trimble's light workspace is neutral white.  The tiny lower tint
            # keeps white geometry readable without shifting source colours.
            self._renderer.SetBackground(0.988, 0.990, 0.994)
            self._renderer.SetBackground2(0.958, 0.968, 0.980)
        elif theme == "slate":
            self._renderer.SetBackground(0.115, 0.135, 0.165)
            self._renderer.SetBackground2(0.25, 0.285, 0.335)
        else:
            self._renderer.SetBackground(0.025, 0.032, 0.045)
            self._renderer.SetBackground2(0.085, 0.105, 0.145)
        self._renderer.GradientBackgroundOn()

    def _sync_selection_fill(self, state: Any, index: Any) -> None:
        selected = set(state.selected_node_ids)
        affected = (
            set(index.renderable_node_ids)
            if self._ral_override is not None or self._ral_refresh_all
            else self._highlighted_nodes | selected
        )
        changed_groups: set[int] = set()
        for node_id in affected:
            entry = self._node_instance.get(node_id)
            if entry is None:
                continue
            group, instance_index = entry
            node = index.node(node_id)
            _mode, color = self._style_for_node(
                node,
                colors=state.colors,
                transparency=state.transparency,
                ghosted=state.ghosted_set,
                preferences=state.display_preferences,
            )
            rgba = self._rgba_bytes(color)
            if self._ral_override is not None:
                rgba = (*self._ral_override, rgba[3])
            if node_id in selected:
                rgba = self._blend_selection(rgba)
            current = tuple(int(value) for value in group.colors.GetTuple(instance_index))
            if current != rgba:
                group.colors.SetTypedTuple(instance_index, rgba)
                changed_groups.add(id(group))
        for group in self._mesh_groups:
            if id(group) in changed_groups:
                group.colors.Modified()
                group.polydata.GetPointData().Modified()
                group.polydata.Modified()
                group.mapper.Modified()
                group.mapper.Update()
        self._highlighted_nodes = selected
        self._ral_refresh_all = False
        self._rebuild_selection_fill(state, index)

    def _rebuild_selection_fill(self, state: Any, index: Any) -> None:
        if self._selection_fill_groups:
            self._remove_groups(self._selection_fill_groups)
            self._selection_fill_groups = []
        if not state.display_preferences.show_selection_outline:
            return
        for node_id in sorted(state.selected_node_ids):
            if node_id not in state.visible_set or node_id not in index.nodes_by_id:
                continue
            node = index.node(node_id)
            base_entry = self._node_instance.get(node_id)
            if not node.geometry_id or base_entry is None:
                continue
            base_group, _instance_index = base_entry
            offset = state.explode_offsets.get(node_id, Vector3.zero())
            matrix = Matrix4.translation(offset) @ index.world_transform_by_node[node_id]
            fill_group = VtkProjectMeshBackend._build_mesh_group(
                self,
                node.geometry_id,
                base_group.mode,
                [(node_id, matrix, state.display_preferences.selection_color)],
                selection=True,
            )
            mapper = fill_group.actor.GetMapper()
            try:
                mapper.SetResolveCoincidentTopologyToPolygonOffset()
                mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(-2.0, -2.0)
            except Exception:
                pass
            prop = fill_group.actor.GetProperty()
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
            prop.SetColor(1.0, 0.82, 0.0)
            prop.SetOpacity(0.78)
            prop.LightingOff()
            fill_group.actor.PickableOff()
            self._selection_fill_groups.append(fill_group)

    def refresh_geometry(self, geometry_ids: tuple[str, ...] | None = None) -> None:
        if self._selection_fill_groups:
            self._remove_groups(self._selection_fill_groups)
            self._selection_fill_groups = []
        super().refresh_geometry(geometry_ids)

    def _update_contact_shadow_scale(self) -> None:
        ssao = self._ssao_pass
        if ssao is None:
            return
        diagonal = self._scene_diagonal()
        # Structural IFCs use mm. Around 0.5% of model diagonal gives visible
        # local contact depth while avoiding a broad muddy halo on large halls.
        radius = max(5.0, min(140.0, diagonal * 0.0015))
        try:
            ssao.SetRadius(float(radius))
        except Exception:
            pass

    def apply_state(self, state: Any, index: Any) -> None:
        self._active_index = index
        super().apply_state(state, index)
        self._update_contact_shadow_scale()
        self._sync_selection_fill(state, index)

    # ------------------------------------------------------------------
    # Measurement presentation
    @staticmethod
    def _measurement_colour(kind: str) -> tuple[float, float, float]:
        value = str(kind or "").casefold()
        if value in {
            MeasurementKind.HORIZONTAL_DISTANCE.value,
            MeasurementKind.VERTICAL_DISTANCE.value,
        }:
            return (0.05, 0.34, 0.88)
        return (0.88, 0.12, 0.10)

    def _scene_marker_size(self) -> float:
        return max(self._scene_diagonal() * 0.0010, 1.5)

    def _add_line_actor(
        self,
        points_world: Iterable[Vector3],
        colour: tuple[float, float, float],
        actors: list[Any],
        *,
        width: float = 2.2,
        dotted: bool = False,
    ) -> None:
        vtk = self._vtk
        renderer = self._renderer
        if vtk is None or renderer is None:
            return
        points_data = tuple(points_world)
        if len(points_data) < 2:
            return
        points = vtk.vtkPoints()
        polyline = vtk.vtkPolyLine()
        polyline.GetPointIds().SetNumberOfIds(len(points_data))
        for index, point in enumerate(points_data):
            pid = points.InsertNextPoint(*point.to_tuple())
            polyline.GetPointIds().SetId(index, pid)
        cells = vtk.vtkCellArray()
        cells.InsertNextCell(polyline)
        data = vtk.vtkPolyData()
        data.SetPoints(points)
        data.SetLines(cells)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(data)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.PickableOff()
        prop = actor.GetProperty()
        prop.SetColor(*colour)
        prop.SetLineWidth(float(width))
        prop.LightingOff()
        if dotted and hasattr(prop, "SetLineStipplePattern"):
            try:
                prop.SetLineStipplePattern(0x00FF)
                prop.SetLineStippleRepeatFactor(1)
            except Exception:
                pass
        renderer.AddActor(actor)
        actors.append(actor)

    def _add_endpoint_actor(
        self,
        point: Vector3,
        colour: tuple[float, float, float],
        actors: list[Any],
    ) -> None:
        vtk = self._vtk
        renderer = self._renderer
        if vtk is None or renderer is None:
            return
        source = vtk.vtkSphereSource()
        source.SetCenter(*point.to_tuple())
        source.SetRadius(self._scene_marker_size())
        source.SetThetaResolution(14)
        source.SetPhiResolution(10)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(source.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.PickableOff()
        actor.GetProperty().SetColor(*colour)
        actor.GetProperty().LightingOff()
        renderer.AddActor(actor)
        actors.append(actor)

    def _add_arrow_actor(
        self,
        point: Vector3,
        direction: Vector3,
        colour: tuple[float, float, float],
        actors: list[Any],
    ) -> None:
        vtk = self._vtk
        renderer = self._renderer
        if vtk is None or renderer is None or direction.length() <= 1e-12:
            return
        size = self._scene_marker_size() * 4.2
        unit = direction.normalized()
        cone = vtk.vtkConeSource()
        cone.SetDirection(*unit.to_tuple())
        cone.SetHeight(size)
        cone.SetRadius(size * 0.36)
        center = point - unit * (size * 0.35)
        cone.SetCenter(*center.to_tuple())
        cone.SetResolution(14)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(cone.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.PickableOff()
        actor.GetProperty().SetColor(*colour)
        actor.GetProperty().LightingOff()
        renderer.AddActor(actor)
        actors.append(actor)

    def _add_foreground_text(
        self,
        text: str,
        world_point: Vector3,
        colour: tuple[float, float, float],
        actors: list[Any],
        bindings: list[tuple[Any, Vector3, tuple[int, int]]],
        *,
        offset: tuple[int, int] = (10, 10),
        small: bool = False,
    ) -> None:
        vtk = self._vtk
        renderer = self._renderer
        if vtk is None or renderer is None:
            return
        actor = vtk.vtkTextActor()
        actor.SetInput(str(text))
        actor.PickableOff()
        prop = actor.GetTextProperty()
        prop.SetFontSize(13 if small else 16)
        prop.SetBold(not small)
        prop.SetColor(*colour)
        try:
            prop.SetBackgroundColor(1.0, 1.0, 1.0)
            prop.SetBackgroundOpacity(0.90)
            prop.SetFrame(True)
            prop.SetFrameColor(0.78, 0.80, 0.84)
        except Exception:
            pass
        renderer.AddActor2D(actor)
        actors.append(actor)
        bindings.append((actor, world_point, offset))

    def _position_measurement_labels(
        self,
        bindings: Iterable[tuple[Any, Vector3, tuple[int, int]]],
    ) -> None:
        renderer = self._renderer
        if renderer is None:
            return
        width = max(int(self._width), 100)
        height = max(int(self._height), 100)
        for actor, point, offset in bindings:
            renderer.SetWorldPoint(point.x, point.y, point.z, 1.0)
            renderer.WorldToDisplay()
            x, y, _depth = renderer.GetDisplayPoint()
            px = max(8, min(width - 190, int(round(x)) + int(offset[0])))
            py = max(8, min(height - 36, int(round(y)) + int(offset[1])))
            actor.SetPosition(px, py)

    def _add_measurement_geometry(
        self,
        *,
        kind: str,
        points: tuple[Vector3, ...],
        text: str,
        actors: list[Any],
        bindings: list[tuple[Any, Vector3, tuple[int, int]]],
        preview: bool = False,
    ) -> None:
        if not points:
            return
        colour = self._measurement_colour(kind)
        for point in points:
            self._add_endpoint_actor(point, colour, actors)
        if len(points) >= 2:
            self._add_line_actor(points, colour, actors, width=1.8 if preview else 2.4, dotted=preview)
            direction = points[-1] - points[0]
            self._add_arrow_actor(points[0], direction, colour, actors)
            self._add_arrow_actor(points[-1], -direction, colour, actors)
            self._add_foreground_text("A", points[0], colour, actors, bindings, offset=(7, 7), small=True)
            self._add_foreground_text("B", points[-1], colour, actors, bindings, offset=(7, 7), small=True)
        center = Vector3.zero()
        for point in points:
            center = center + point
        center = center * (1.0 / len(points))
        self._add_foreground_text(text, center, colour, actors, bindings, offset=(12, 12))

    def set_measurement_overlays(self, records: tuple[Any, ...]) -> None:
        self._ensure_initialized()
        self._remove_overlay_actors(self._measurement_actors)
        self._measurement_label_bindings.clear()
        for record in records:
            if not getattr(record, "visible", True):
                continue
            anchors = tuple(getattr(record, "anchors", ()) or ())
            points = tuple(anchor.world_point for anchor in anchors)
            self._add_measurement_geometry(
                kind=str(getattr(record, "kind", "distance")),
                points=points,
                text=str(getattr(record, "formatted_text", "")),
                actors=self._measurement_actors,
                bindings=self._measurement_label_bindings,
            )
        self.render()

    def set_measurement_preview(
        self,
        start: Vector3 | None,
        end: Vector3 | None,
        kind: MeasurementKind | str | None,
    ) -> None:
        self._ensure_initialized()
        self._remove_overlay_actors(self._measurement_preview_actors)
        self._measurement_preview_labels.clear()
        if start is None or end is None or kind is None:
            self.render()
            return
        kind_value = kind.value if isinstance(kind, MeasurementKind) else str(kind)
        delta = end - start
        if kind_value == MeasurementKind.HORIZONTAL_DISTANCE.value:
            value = math.hypot(delta.x, delta.y)
        elif kind_value == MeasurementKind.VERTICAL_DISTANCE.value:
            value = abs(delta.z)
        else:
            value = delta.length()
        self._add_measurement_geometry(
            kind=kind_value,
            points=(start, end),
            text=f"{value:.1f} mm",
            actors=self._measurement_preview_actors,
            bindings=self._measurement_preview_labels,
            preview=True,
        )
        self.render()

    def render(self) -> None:
        if self._renderer is not None:
            self._renderer.ResetCameraClippingRange()
        self._position_measurement_labels(self._measurement_label_bindings)
        self._position_measurement_labels(self._measurement_preview_labels)
        super().render()

    def clear_scene(self) -> None:
        if self._selection_fill_groups:
            self._remove_groups(self._selection_fill_groups)
            self._selection_fill_groups = []
        self._remove_overlay_actors(self._measurement_preview_actors)
        self._measurement_label_bindings.clear()
        self._measurement_preview_labels.clear()
        self._highlighted_nodes.clear()
        self._active_index = None
        super().clear_scene()


__all__ = ["VtkProjectMeshFeelV2Backend"]


# CWS visual-quality policy: model transparency and robust camera clipping.
def _cws_iter_model_actors(backend):
    renderer = getattr(backend, "_renderer", None)
    if renderer is None:
        return
    actors = renderer.GetActors()
    actors.InitTraversal()
    while True:
        actor = actors.GetNextActor()
        if actor is None:
            break
        yield actor


def _cws_set_global_opacity(self, opacity):
    opacity = max(0.15, min(1.0, float(opacity)))
    self._cws_global_opacity = opacity
    for actor in _cws_iter_model_actors(self):
        prop = actor.GetProperty()
        if prop is not None:
            prop.SetOpacity(opacity)
    renderer = getattr(self, "_renderer", None)
    if renderer is not None and renderer.GetRenderWindow() is not None:
        renderer.GetRenderWindow().Render()


_ORIGINAL_CWS_V2_RENDER = VtkProjectMeshFeelV2Backend.render


def _cws_render_with_safe_clipping(self):
    _ORIGINAL_CWS_V2_RENDER(self)
    renderer = getattr(self, "_renderer", None)
    if renderer is None:
        return
    camera = renderer.GetActiveCamera()
    if camera is None:
        return
    near_value, far_value = camera.GetClippingRange()
    safe_near = max(0.001, float(near_value) * 0.20)
    safe_far = max(safe_near + 1.0, float(far_value) * 1.75)
    camera.SetClippingRange(safe_near, safe_far)
    opacity = float(getattr(self, "_cws_global_opacity", 1.0))
    if opacity < 0.999:
        for actor in _cws_iter_model_actors(self):
            prop = actor.GetProperty()
            if prop is not None:
                prop.SetOpacity(opacity)
    window = renderer.GetRenderWindow()
    if window is not None:
        window.Render()


VtkProjectMeshFeelV2Backend.set_global_opacity = _cws_set_global_opacity
VtkProjectMeshFeelV2Backend.render = _cws_render_with_safe_clipping
