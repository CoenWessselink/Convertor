"""Second-generation interactive quality renderer for the CWS Viewer.

The renderer keeps the previous triangle-edge suppression, adds source-colour
friendly lighting/contact shading, a stronger selected-object highlight and
measurement graphics that stay readable while the camera moves.
"""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Any, Iterable

from cws_viewer.backends.vtk_project_mesh_feel import VtkProjectMeshFeelBackend
from cws_viewer.contracts.enums import MeasurementKind
from cws_viewer.contracts.state import ViewerCapabilities
from cws_viewer.math3d import Rgba, Vector3


class VtkProjectMeshFeelV2Backend(VtkProjectMeshFeelBackend):
    """High-quality large-model renderer with non-destructive review overlays."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._highlighted_nodes: set[str] = set()
        self._measurement_label_bindings: list[tuple[Any, Vector3, tuple[int, int]]] = []
        self._measurement_preview_actors: list[Any] = []
        self._measurement_preview_labels: list[tuple[Any, Vector3, tuple[int, int]]] = []
        self._ssao_pass: Any | None = None
        self._light_kit: Any | None = None

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

        try:
            kit = vtk.vtkLightKit()
            for name, value in (
                ("SetKeyLightIntensity", 0.78),
                ("SetKeyToFillRatio", 2.6),
                ("SetKeyToHeadRatio", 3.0),
                ("SetKeyToBackRatio", 3.8),
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

        # Screen-space ambient occlusion supplies the contact-shadow depth that
        # was visibly missing in the user screenshots. Radius is updated from
        # the real scene diagonal in ``apply_state`` because project units are
        # millimetres and a fixed 0.x world-unit radius would be invisible.
        if not self._offscreen:
            try:
                if hasattr(vtk, "vtkSSAOPass") and hasattr(vtk, "vtkRenderStepsPass"):
                    basic = vtk.vtkRenderStepsPass()
                    ssao = vtk.vtkSSAOPass()
                    ssao.SetDelegatePass(basic)
                    for name, value in (
                        ("SetRadius", 25.0),
                        ("SetBias", 0.015),
                        ("SetKernelSize", 64),
                    ):
                        method = getattr(ssao, name, None)
                        if callable(method):
                            method(value)
                    blur = getattr(ssao, "BlurOn", None)
                    if callable(blur):
                        blur()
                    renderer.SetPass(ssao)
                    self._ssao_pass = ssao
            except Exception:
                self._ssao_pass = None

    @staticmethod
    def _quality_material(prop: Any) -> None:
        prop.SetInterpolationToPhong()
        prop.SetAmbient(0.18)
        prop.SetDiffuse(0.76)
        prop.SetSpecular(0.22)
        prop.SetSpecularPower(30.0)

    @staticmethod
    def _blend_selection(rgba: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        target = (255, 205, 66)
        amount = 0.38
        return (
            int(round(rgba[0] * (1.0 - amount) + target[0] * amount)),
            int(round(rgba[1] * (1.0 - amount) + target[1] * amount)),
            int(round(rgba[2] * (1.0 - amount) + target[2] * amount)),
            rgba[3],
        )

    def _sync_selection_fill(self, state: Any, index: Any) -> None:
        selected = set(state.selected_node_ids)
        affected = self._highlighted_nodes | selected
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
            if node_id in selected:
                rgba = self._blend_selection(rgba)
            current = tuple(int(value) for value in group.colors.GetTuple(instance_index))
            if current != rgba:
                group.colors.SetTypedTuple(instance_index, rgba)
                changed_groups.add(id(group))
        for group in self._mesh_groups:
            if id(group) in changed_groups:
                group.colors.Modified()
                group.polydata.Modified()
                group.mapper.Modified()
        self._highlighted_nodes = selected

    def _update_contact_shadow_scale(self) -> None:
        ssao = self._ssao_pass
        if ssao is None:
            return
        diagonal = self._scene_diagonal()
        # Structural IFCs use mm. Around 0.5% of model diagonal gives visible
        # local contact depth while avoiding a broad muddy halo on large halls.
        radius = max(8.0, min(350.0, diagonal * 0.005))
        try:
            ssao.SetRadius(float(radius))
        except Exception:
            pass

    def apply_state(self, state: Any, index: Any) -> None:
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
        self._position_measurement_labels(self._measurement_label_bindings)
        self._position_measurement_labels(self._measurement_preview_labels)
        super().render()

    def clear_scene(self) -> None:
        self._remove_overlay_actors(self._measurement_preview_actors)
        self._measurement_label_bindings.clear()
        self._measurement_preview_labels.clear()
        self._highlighted_nodes.clear()
        super().clear_scene()


__all__ = ["VtkProjectMeshFeelV2Backend"]
