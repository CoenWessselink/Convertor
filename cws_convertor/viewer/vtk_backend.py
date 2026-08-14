"""Off-screen VTK renderer used by the Tk project workspace.

The PyPI VTK wheel does not ship ``vtkRenderingTk.dll`` on Windows. Rendering
to PNG keeps the application on one Tk UI stack while still using VTK for the
actual mesh, camera, depth buffer and picking pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
import colorsys
import hashlib
import json
import math
import time
from typing import Any, Callable, Mapping

from cws_convertor.steel_model.contracts import (
    STEEL_MODEL_SCHEMA_VERSION,
    SteelEntityRecord,
    SteelModelSnapshot,
)
from cws_convertor.steel_model.viewer_boundary import (
    CORE_VIEWER_CAPABILITIES,
    VIEWER_HOST_CONTRACT_VERSION,
    ViewerHandshake,
    ViewerHostSnapshot,
)
from .mesh_resources import ViewerMeshResource


BUILTIN_RENDERER_NAME = "CWS VTK Mesh Renderer"
BUILTIN_RENDERER_VERSION = "0.6-integrated"
BUILTIN_RENDERER_CAPABILITIES: tuple[str, ...] = tuple(
    sorted(
        set(CORE_VIEWER_CAPABILITIES)
        | {
            "camera.projection",
            "clipping.box",
            "display.background",
            "display.color_schemes",
            "display.explode",
            "display.render_modes",
            "measurement.state",
            "screenshot.capture",
            "section.planes",
            "viewer.workspace",
            "visibility.hide_show",
            "visibility.isolate",
            "visibility.ghost",
        }
    )
)


@dataclass(slots=True)
class _ActorRecord:
    entity: SteelEntityRecord
    resource: ViewerMeshResource
    viewer_node_id: str
    actor: Any
    user_matrix: Any
    clip_filter: Any | None = None


class VtkOffscreenRenderer:
    """Command-driven VTK scene with deterministic resource verification."""

    def __init__(
        self,
        *,
        image_callback: Callable[[bytes, Mapping[str, Any]], None] | None = None,
        selection_callback: Callable[[str], None] | None = None,
        width: int = 900,
        height: int = 560,
    ) -> None:
        from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkRenderer
        import vtkmodules.vtkRenderingFreeType  # noqa: F401
        import vtkmodules.vtkRenderingOpenGL2  # noqa: F401

        self.image_callback = image_callback or (lambda _png, _telemetry: None)
        self.selection_callback = selection_callback or (lambda _node_id: None)
        self._renderer = vtkRenderer()
        self._renderer.SetBackground(0.0706, 0.0863, 0.0784)
        self._renderer.SetBackground2(0.1059, 0.1294, 0.1176)
        self._renderer.GradientBackgroundOn()
        self._window = vtkRenderWindow()
        self._window.SetOffScreenRendering(1)
        self._window.SetMultiSamples(0)
        self._window.SetSize(max(64, int(width)), max(64, int(height)))
        self._window.AddRenderer(self._renderer)

        self._steel_model: SteelModelSnapshot | None = None
        self._viewer_host: ViewerHostSnapshot | None = None
        self._entities: dict[str, SteelEntityRecord] = {}
        self._bindings_by_model: dict[str, Any] = {}
        self._model_by_node: dict[str, str] = {}
        self._actors: dict[str, _ActorRecord] = {}
        self._node_by_actor_address: dict[str, str] = {}
        self._polydata_by_hash: dict[str, Any] = {}
        self._selected_nodes: set[str] = set()
        self._selection_mode = False
        self._accuracy_debug = True
        self._hidden_nodes: set[str] = set()
        self._isolation_nodes: set[str] = set()
        self._ghost_nodes: set[str] = set()
        self._transparency: dict[str, float] = {}
        self._render_mode = "shaded_edges"
        self._projection = "perspective"
        self._color_scheme = "accuracy"
        self._background_theme = "dark"
        self._section_planes: dict[str, dict[str, Any]] = {}
        self._clipping_box: tuple[float, float, float, float, float, float] | None = None
        self._explode_factor = 0.0
        self._measurement_mode = ""
        self._measurement_points: list[tuple[float, float, float]] = []
        self._measurements: list[dict[str, Any]] = []
        self._viewpoints: dict[str, dict[str, Any]] = {}
        self._last_png = b""
        self._last_render_ms = 0.0
        self._render_count = 0

    @property
    def handshake(self) -> ViewerHandshake:
        return ViewerHandshake(
            component_name=BUILTIN_RENDERER_NAME,
            component_version=BUILTIN_RENDERER_VERSION,
            contract_version=VIEWER_HOST_CONTRACT_VERSION,
            steel_model_schema_version=STEEL_MODEL_SCHEMA_VERSION,
            capabilities=BUILTIN_RENDERER_CAPABILITIES,
        )

    @property
    def actor_count(self) -> int:
        return len(self._actors)

    def command(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        value = dict(payload or {})
        if command == "scene.load":
            self._load_scene(value)
        elif command == "scene.patch":
            self._patch_scene(value)
        elif command == "selection.set":
            self._set_selection(value.get("viewer_node_ids") or ())
        elif command == "selection.begin":
            self._selection_mode = True
        elif command == "camera.fit_all":
            self.fit_all()
        elif command == "camera.standard_view":
            self.standard_view(str(value.get("view") or "isometric"))
        elif command == "visibility.isolate":
            self.isolate(value.get("viewer_node_ids") or (), ghost_context=bool(value.get("ghost_context", False)))
        elif command == "visibility.hide":
            self.hide(value.get("viewer_node_ids") or ())
        elif command == "visibility.show":
            self.show(value.get("viewer_node_ids") or ())
        elif command == "visibility.show_all":
            self.show_all()
        elif command == "visibility.ghost":
            self.isolate(value.get("viewer_node_ids") or (), ghost_context=True)
        elif command == "style.transparency":
            self.set_transparency(value.get("viewer_node_ids") or (), float(value.get("value", 0.55)))
        elif command == "display.render_mode":
            self.set_render_mode(str(value.get("mode") or "shaded_edges"))
        elif command == "display.projection":
            self.set_projection(str(value.get("projection") or "perspective"))
        elif command == "display.color_scheme":
            self.set_color_scheme(str(value.get("scheme") or "accuracy"))
        elif command == "display.background":
            self.set_background(str(value.get("theme") or "dark"))
        elif command == "display.explode":
            self.set_explode(float(value.get("factor", 0.0)))
        elif command == "section.begin":
            self.toggle_section(str(value.get("axis") or "z"), float(value.get("offset_mm", 0.0)))
        elif command == "section.set":
            self.set_section(
                str(value.get("plane_id") or "primary"),
                value.get("normal") or (0.0, 0.0, 1.0),
                value.get("origin") or (0.0, 0.0, float(value.get("offset_mm", 0.0))),
            )
        elif command == "section.clear":
            self._section_planes.clear()
            self._apply_clipping()
            self.render()
        elif command == "clipping_box.toggle":
            self.toggle_clipping_box()
        elif command == "clipping_box.set":
            raw = value.get("bounds")
            self._clipping_box = tuple(float(item) for item in raw) if raw else None
            self._apply_clipping()
            self.render()
        elif command == "measurement.begin":
            self._measurement_mode = str(value.get("kind") or "distance")
            self._measurement_points.clear()
        elif command == "measurement.clear":
            self._measurement_points.clear()
            self._measurements.clear()
            self.render()
        elif command == "viewpoint.save":
            self.save_viewpoint(str(value.get("name") or f"Viewpoint {len(self._viewpoints) + 1}"))
        elif command == "viewpoint.restore":
            self.restore_viewpoint(str(value.get("name") or ""))
        elif command == "workspace.load":
            self.load_workspace(dict(value.get("workspace") or {}))
        elif command == "screenshot.capture":
            self.render()
            result = self.telemetry()
            result["png"] = self._last_png
            return result
        elif command == "workspace.export":
            result = self.telemetry()
            result["workspace"] = self.workspace()
            return result
        elif command == "accuracy_debug.set":
            self._accuracy_debug = bool(value.get("enabled", True))
            self._refresh_actor_styles()
            self.render()
        elif command == "large_model.telemetry":
            pass
        else:
            raise ValueError(f"Unsupported built-in renderer command {command!r}")
        return self.telemetry()

    def _load_scene(self, payload: Mapping[str, Any]) -> None:
        steel_model = SteelModelSnapshot.from_dict(dict(payload.get("steel_model") or {}))
        viewer_host = ViewerHostSnapshot.from_dict(dict(payload.get("viewer_host") or {}))
        if steel_model.project_id != viewer_host.project_id:
            raise ValueError("Renderer scene project IDs do not match")
        if steel_model.snapshot_sha256 != viewer_host.steel_model_snapshot_sha256:
            raise ValueError("Renderer host does not bind the supplied SteelModel")
        if str(payload.get("steel_model_snapshot_sha256") or "") != steel_model.snapshot_sha256:
            raise ValueError("Renderer scene SteelModel hash does not match its payload")
        if str(payload.get("viewer_host_snapshot_sha256") or "") != viewer_host.snapshot_sha256:
            raise ValueError("Renderer scene host hash does not match its payload")

        self._clear_scene()
        self._steel_model = steel_model
        self._viewer_host = viewer_host
        self._entities = {item.steel_model_id: item for item in steel_model.entities}
        self._set_host_bindings(viewer_host)
        for raw in payload.get("mesh_resources") or ():
            self._upsert_resource(ViewerMeshResource.from_dict(raw))
        self.render()

    def _patch_scene(self, payload: Mapping[str, Any]) -> None:
        if self._steel_model is None or self._viewer_host is None:
            raise ValueError("Renderer scene must be loaded before a patch")
        if str(payload.get("project_id") or "") != self._steel_model.project_id:
            raise ValueError("Renderer patch belongs to another project")
        if (
            str(payload.get("steel_model_snapshot_sha256") or "")
            != self._steel_model.snapshot_sha256
        ):
            raise ValueError("Renderer patch belongs to another SteelModel snapshot")
        previous = str(payload.get("previous_viewer_host_snapshot_sha256") or "")
        if previous != self._viewer_host.snapshot_sha256:
            raise ValueError("Renderer patch does not continue the active viewer host")
        viewer_host = ViewerHostSnapshot.from_dict(dict(payload.get("viewer_host") or {}))
        if viewer_host.steel_model_snapshot_sha256 != self._steel_model.snapshot_sha256:
            raise ValueError("Renderer patch host does not bind the active SteelModel")
        if str(payload.get("viewer_host_snapshot_sha256") or "") != viewer_host.snapshot_sha256:
            raise ValueError("Renderer patch host hash does not match its payload")
        self._viewer_host = viewer_host
        self._set_host_bindings(viewer_host)
        for raw in payload.get("resources") or ():
            self._upsert_resource(ViewerMeshResource.from_dict(raw))
        self.render()

    def _set_host_bindings(self, host: ViewerHostSnapshot) -> None:
        self._bindings_by_model = {item.steel_model_id: item for item in host.bindings}
        self._model_by_node = {
            item.viewer_node_id: item.steel_model_id for item in host.bindings
        }

    def _clear_scene(self) -> None:
        self._renderer.RemoveAllViewProps()
        self._actors.clear()
        self._node_by_actor_address.clear()
        self._polydata_by_hash.clear()
        self._selected_nodes.clear()
        self._hidden_nodes.clear()
        self._isolation_nodes.clear()
        self._ghost_nodes.clear()
        self._transparency.clear()
        self._section_planes.clear()
        self._clipping_box = None
        self._measurement_points.clear()
        self._measurements.clear()

    def _polydata(self, resource: ViewerMeshResource) -> Any:
        cached = self._polydata_by_hash.get(resource.geometry_content_sha256)
        if cached is not None:
            return cached

        from vtkmodules.vtkCommonCore import vtkPoints
        from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
        from vtkmodules.vtkFiltersCore import vtkPolyDataNormals

        points = vtkPoints()
        points.SetDataTypeToDouble()
        points.SetNumberOfPoints(len(resource.vertices_mm))
        for index, vertex in enumerate(resource.vertices_mm):
            points.SetPoint(index, *vertex)
        cells = vtkCellArray()
        for first, second, third in resource.triangles:
            cells.InsertNextCell(3)
            cells.InsertCellPoint(first)
            cells.InsertCellPoint(second)
            cells.InsertCellPoint(third)
        polydata = vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(cells)

        normals = vtkPolyDataNormals()
        normals.SetInputData(polydata)
        normals.ConsistencyOn()
        normals.AutoOrientNormalsOn()
        normals.SplittingOff()
        normals.ComputePointNormalsOn()
        normals.Update()
        output = normals.GetOutput()
        self._polydata_by_hash[resource.geometry_content_sha256] = output
        return output

    def _upsert_resource(self, resource: ViewerMeshResource) -> None:
        if self._steel_model is None or self._viewer_host is None:
            raise ValueError("Cannot add a mesh without an active scene")
        if resource.project_id != self._steel_model.project_id:
            raise ValueError("Viewer mesh belongs to another renderer scene")
        entity = self._entities.get(resource.steel_model_id)
        binding = self._bindings_by_model.get(resource.steel_model_id)
        if entity is None or binding is None:
            raise ValueError("Viewer mesh refers to an unknown scene entity")
        if binding.viewer_geometry_id != resource.viewer_geometry_id:
            raise ValueError("Viewer mesh geometry ID does not match renderer binding")
        if binding.viewer_geometry_content_sha256 != resource.geometry_content_sha256:
            raise ValueError("Viewer mesh content hash does not match renderer binding")
        if resource.source_file_id != entity.source.source_file_id:
            raise ValueError("Viewer mesh source does not match renderer entity")

        from vtkmodules.vtkCommonMath import vtkMatrix4x4
        from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper

        previous = self._actors.pop(resource.steel_model_id, None)
        if previous is not None:
            self._renderer.RemoveActor(previous.actor)
            self._node_by_actor_address.pop(previous.actor.GetAddressAsString(""), None)
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(self._polydata(resource))
        mapper.ScalarVisibilityOff()
        actor = vtkActor()
        actor.SetMapper(mapper)
        matrix = vtkMatrix4x4()
        for row in range(4):
            for column in range(4):
                matrix.SetElement(row, column, entity.global_transform[row * 4 + column])
        actor.SetUserMatrix(matrix)
        actor.GetProperty().EdgeVisibilityOff()
        record = _ActorRecord(
            entity=entity,
            resource=resource,
            viewer_node_id=binding.viewer_node_id,
            actor=actor,
            user_matrix=matrix,
        )
        self._actors[resource.steel_model_id] = record
        self._node_by_actor_address[actor.GetAddressAsString("")] = binding.viewer_node_id
        self._renderer.AddActor(actor)
        self._apply_actor_style(record)
        if self._hidden_nodes or self._isolation_nodes:
            self._apply_visibility()
        if self._section_planes or self._clipping_box is not None:
            self._apply_clipping()
        if self._explode_factor:
            self._apply_explode()

    @staticmethod
    def _accuracy_color(status: str) -> tuple[float, float, float]:
        return {
            "exact": (0.32, 0.68, 0.55),
            "tolerance_verified": (0.30, 0.55, 0.82),
            "approximate": (0.88, 0.62, 0.24),
            "manual_validation_required": (0.80, 0.28, 0.24),
            "not_applicable": (0.62, 0.67, 0.64),
        }.get(status, (0.62, 0.67, 0.64))

    def _apply_actor_style(self, record: _ActorRecord) -> None:
        selected = record.viewer_node_id in self._selected_nodes
        if selected:
            color = (0.98, 0.78, 0.20)
        elif self._color_scheme == "accuracy":
            color = self._accuracy_color(record.resource.accuracy_status)
        else:
            color = self._scheme_color(record)
        prop = record.actor.GetProperty()
        prop.SetColor(*color)
        prop.SetAmbient(0.18)
        prop.SetDiffuse(0.78)
        prop.SetSpecular(0.16)
        prop.SetSpecularPower(18.0)
        prop.SetRepresentationToWireframe() if self._render_mode == "wireframe" else prop.SetRepresentationToSurface()
        prop.SetEdgeVisibility(self._render_mode == "shaded_edges")
        prop.SetEdgeColor(0.12, 0.16, 0.18)
        opacity = self._transparency.get(record.viewer_node_id, 0.0)
        if record.viewer_node_id in self._ghost_nodes:
            opacity = max(opacity, 0.78)
        prop.SetOpacity(max(0.03, 1.0 - opacity))

    def _scheme_color(self, record: _ActorRecord) -> tuple[float, float, float]:
        properties = dict(record.entity.display_properties)
        key = {
            "material": properties.get("material") or properties.get("material_grade"),
            "profile": properties.get("profile") or properties.get("normalized_profile"),
            "assembly": properties.get("assembly_mark") or properties.get("assembly_ids"),
            "phase": properties.get("phase") or properties.get("project_phase"),
            "status": record.entity.accuracy_status,
        }.get(self._color_scheme)
        if not key:
            return (0.72, 0.76, 0.73)
        digest = hashlib.sha256(str(key).encode("utf-8")).digest()
        hue = int.from_bytes(digest[:2], "big") / 65535.0
        saturation = 0.42 + digest[2] / 255.0 * 0.20
        value = 0.68 + digest[3] / 255.0 * 0.20
        return colorsys.hsv_to_rgb(hue, saturation, value)

    def _refresh_actor_styles(self) -> None:
        for record in self._actors.values():
            self._apply_actor_style(record)

    def _set_selection(self, viewer_node_ids: Any) -> None:
        self._selected_nodes = {
            str(item) for item in viewer_node_ids if str(item) in self._model_by_node
        }
        self._refresh_actor_styles()
        self.render()

    def _apply_visibility(self) -> None:
        for record in self._actors.values():
            node_id = record.viewer_node_id
            visible = node_id not in self._hidden_nodes
            if self._isolation_nodes and not self._ghost_nodes:
                visible = visible and node_id in self._isolation_nodes
            record.actor.SetVisibility(visible)

    def isolate(self, viewer_node_ids: Any, *, ghost_context: bool = False) -> None:
        self._isolation_nodes = {str(item) for item in viewer_node_ids}
        self._ghost_nodes = (
            set(self._model_by_node) - self._isolation_nodes if ghost_context else set()
        )
        self._apply_visibility()
        self._refresh_actor_styles()
        self.render()

    def hide(self, viewer_node_ids: Any) -> None:
        self._hidden_nodes.update(str(item) for item in viewer_node_ids)
        self._apply_visibility()
        self.render()

    def show(self, viewer_node_ids: Any) -> None:
        self._hidden_nodes.difference_update(str(item) for item in viewer_node_ids)
        self._apply_visibility()
        self.render()

    def show_all(self) -> None:
        self._hidden_nodes.clear()
        self._isolation_nodes.clear()
        self._ghost_nodes.clear()
        self._apply_visibility()
        self._refresh_actor_styles()
        self.render()

    def set_transparency(self, viewer_node_ids: Any, value: float) -> None:
        amount = min(1.0, max(0.0, float(value)))
        for node_id in viewer_node_ids:
            self._transparency[str(node_id)] = amount
        self._refresh_actor_styles()
        self.render()

    def set_render_mode(self, mode: str) -> None:
        if mode not in {"shaded", "shaded_edges", "wireframe"}:
            raise ValueError(f"Unsupported render mode {mode!r}")
        self._render_mode = mode
        self._refresh_actor_styles()
        self.render()

    def set_projection(self, projection: str) -> None:
        if projection not in {"perspective", "orthographic"}:
            raise ValueError(f"Unsupported projection {projection!r}")
        self._projection = projection
        camera = self._renderer.GetActiveCamera()
        camera.SetParallelProjection(projection == "orthographic")
        self.render()

    def set_color_scheme(self, scheme: str) -> None:
        if scheme not in {"original", "accuracy", "material", "profile", "assembly", "phase", "status"}:
            raise ValueError(f"Unsupported color scheme {scheme!r}")
        self._color_scheme = scheme
        self._refresh_actor_styles()
        self.render()

    def set_background(self, theme: str) -> None:
        themes = {
            "dark": ((0.0706, 0.0863, 0.0784), (0.1059, 0.1294, 0.1176)),
            "light": ((0.88, 0.91, 0.92), (0.70, 0.75, 0.77)),
            "white": ((1.0, 1.0, 1.0), (1.0, 1.0, 1.0)),
        }
        if theme not in themes:
            raise ValueError(f"Unsupported background {theme!r}")
        self._background_theme = theme
        first, second = themes[theme]
        self._renderer.SetBackground(*first)
        self._renderer.SetBackground2(*second)
        self._renderer.SetGradientBackground(first != second)
        self.render()

    def _scene_bounds(self) -> tuple[float, float, float, float, float, float] | None:
        values = [record.actor.GetBounds() for record in self._actors.values() if record.actor.GetVisibility()]
        if not values:
            return None
        return (
            min(item[0] for item in values), max(item[1] for item in values),
            min(item[2] for item in values), max(item[3] for item in values),
            min(item[4] for item in values), max(item[5] for item in values),
        )

    def toggle_section(self, axis: str, offset_mm: float) -> None:
        if self._section_planes:
            self._section_planes.clear()
        else:
            normal = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}.get(axis.lower())
            if normal is None:
                raise ValueError(f"Unsupported section axis {axis!r}")
            bounds = self._scene_bounds() or (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            center = ((bounds[0]+bounds[1])/2, (bounds[2]+bounds[3])/2, (bounds[4]+bounds[5])/2)
            index = {"x": 0, "y": 1, "z": 2}[axis.lower()]
            origin = list(center)
            origin[index] += float(offset_mm)
            self._section_planes["primary"] = {"normal": normal, "origin": tuple(origin)}
        self._apply_clipping()
        self.render()

    def set_section(self, plane_id: str, normal: Any, origin: Any) -> None:
        self._section_planes[plane_id] = {
            "normal": tuple(float(item) for item in normal),
            "origin": tuple(float(item) for item in origin),
        }
        self._apply_clipping()
        self.render()

    def toggle_clipping_box(self) -> None:
        if self._clipping_box is not None:
            self._clipping_box = None
        else:
            bounds = self._scene_bounds()
            if bounds is not None:
                self._clipping_box = tuple(float(item) for item in bounds)
        self._apply_clipping()
        self.render()

    def _apply_clipping(self) -> None:
        from vtkmodules.vtkCommonDataModel import vtkBox, vtkPlane
        from vtkmodules.vtkCommonTransforms import vtkTransform
        from vtkmodules.vtkFiltersCore import vtkClipPolyData
        from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter

        planes = []
        for definition in self._section_planes.values():
            plane = vtkPlane()
            plane.SetNormal(*definition["normal"])
            plane.SetOrigin(*definition["origin"])
            planes.append(plane)
        if len(planes) > 6:
            raise ValueError("VTK ondersteunt maximaal zes gelijktijdige section planes")
        for record in self._actors.values():
            mapper = record.actor.GetMapper()
            mapper.RemoveAllClippingPlanes()
            if self._clipping_box is None:
                record.clip_filter = None
                mapper.SetInputData(self._polydata(record.resource))
                record.actor.SetUserMatrix(record.user_matrix)
            else:
                transform = vtkTransform()
                transform.SetMatrix(record.user_matrix)
                transformed = vtkTransformPolyDataFilter()
                transformed.SetTransform(transform)
                transformed.SetInputData(self._polydata(record.resource))
                box = vtkBox()
                box.SetBounds(*self._clipping_box)
                clip = vtkClipPolyData()
                clip.SetInputConnection(transformed.GetOutputPort())
                clip.SetClipFunction(box)
                clip.InsideOutOn()
                clip.GenerateClippedOutputOff()
                mapper.SetInputConnection(clip.GetOutputPort())
                record.actor.SetUserMatrix(None)
                record.clip_filter = (transform, transformed, clip)
            for plane in planes:
                mapper.AddClippingPlane(plane)

    def set_explode(self, factor: float) -> None:
        self._explode_factor = min(1.0, max(0.0, float(factor)))
        self._apply_explode()
        self._renderer.ResetCameraClippingRange()
        self.render()

    def _apply_explode(self) -> None:
        for record in self._actors.values():
            record.actor.SetPosition(0.0, 0.0, 0.0)
        bounds = self._scene_bounds()
        if bounds is None:
            return
        center = ((bounds[0]+bounds[1])/2, (bounds[2]+bounds[3])/2, (bounds[4]+bounds[5])/2)
        span = max(bounds[1]-bounds[0], bounds[3]-bounds[2], bounds[5]-bounds[4], 1.0)
        for record in self._actors.values():
            actor_center = record.actor.GetCenter()
            vector = tuple(actor_center[index] - center[index] for index in range(3))
            length = math.sqrt(sum(item * item for item in vector)) or 1.0
            amount = span * 0.22 * self._explode_factor
            record.actor.SetPosition(*(item / length * amount for item in vector))

    def fit_all(self) -> None:
        if self._actors:
            self._renderer.ResetCamera()
            self._renderer.ResetCameraClippingRange()
        self.render()

    def standard_view(self, view: str) -> None:
        if not self._actors:
            self.render()
            return
        self._renderer.ResetCamera()
        camera = self._renderer.GetActiveCamera()
        focal = camera.GetFocalPoint()
        distance = max(1.0, camera.GetDistance())
        directions = {
            "front": (0.0, -1.0, 0.0),
            "back": (0.0, 1.0, 0.0),
            "left": (-1.0, 0.0, 0.0),
            "right": (1.0, 0.0, 0.0),
            "top": (0.0, 0.0, 1.0),
            "bottom": (0.0, 0.0, -1.0),
            "isometric": (1.0, -1.0, 0.8),
        }
        direction = directions.get(view, directions["isometric"])
        magnitude = sum(item * item for item in direction) ** 0.5
        direction = tuple(item / magnitude for item in direction)
        camera.SetPosition(
            focal[0] + direction[0] * distance,
            focal[1] + direction[1] * distance,
            focal[2] + direction[2] * distance,
        )
        camera.SetViewUp(0.0, 1.0, 0.0) if abs(direction[2]) > 0.95 else camera.SetViewUp(0.0, 0.0, 1.0)
        camera.OrthogonalizeViewUp()
        self._renderer.ResetCameraClippingRange()
        self.render()

    def orbit(self, delta_x: float, delta_y: float) -> None:
        if not self._actors:
            return
        camera = self._renderer.GetActiveCamera()
        camera.Azimuth(float(delta_x) * 0.35)
        camera.Elevation(float(delta_y) * 0.35)
        camera.OrthogonalizeViewUp()
        self._renderer.ResetCameraClippingRange()
        self.render()

    def zoom(self, factor: float) -> None:
        if not self._actors or not math_is_positive(factor):
            return
        self._renderer.GetActiveCamera().Dolly(float(factor))
        self._renderer.ResetCameraClippingRange()
        self.render()

    def resize(self, width: int, height: int, *, render: bool = True) -> None:
        size = (max(64, int(width)), max(64, int(height)))
        if tuple(self._window.GetSize()) != size:
            self._window.SetSize(*size)
        if render:
            self.render()

    def pick(self, x: float, y: float) -> str:
        if not self._actors:
            return ""
        from vtkmodules.vtkRenderingCore import vtkPropPicker

        width, height = self._window.GetSize()
        picker = vtkPropPicker()
        found = picker.Pick(float(x), float(height - y - 1), 0.0, self._renderer)
        actor = picker.GetActor() if found else None
        node_id = (
            self._node_by_actor_address.get(actor.GetAddressAsString(""), "")
            if actor is not None
            else ""
        )
        if node_id:
            if self._measurement_mode:
                point = tuple(float(item) for item in picker.GetPickPosition())
                self._measurement_points.append(point)
                if len(self._measurement_points) == 2:
                    first, second = self._measurement_points
                    distance = math.sqrt(sum((second[i] - first[i]) ** 2 for i in range(3)))
                    self._measurements.append({
                        "kind": self._measurement_mode,
                        "points_mm": [list(first), list(second)],
                        "value_mm": distance,
                        "evidence": "display_mesh",
                    })
                    self._measurement_points.clear()
            self._set_selection((node_id,))
            self.selection_callback(node_id)
        return node_id

    def render(self) -> bytes:
        from vtkmodules.vtkIOImage import vtkPNGWriter
        from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter

        started = time.perf_counter()
        self._window.Render()
        capture = vtkWindowToImageFilter()
        capture.SetInput(self._window)
        capture.SetInputBufferTypeToRGB()
        capture.ReadFrontBufferOff()
        capture.Update()
        writer = vtkPNGWriter()
        writer.SetWriteToMemory(True)
        writer.SetInputConnection(capture.GetOutputPort())
        writer.Write()
        png = memoryview(writer.GetResult()).tobytes()
        self._last_png = png
        self._last_render_ms = (time.perf_counter() - started) * 1000.0
        self._render_count += 1
        self.image_callback(png, self.telemetry())
        return png

    def telemetry(self) -> dict[str, Any]:
        visible = sum(record.actor.GetVisibility() for record in self._actors.values())
        return {
            "backend": "vtk_offscreen_png",
            "actor_count": len(self._actors),
            "visible_actor_count": int(visible),
            "unique_geometry_count": len(self._polydata_by_hash),
            "vertex_count": sum(
                len(item.resource.vertices_mm) for item in self._actors.values()
            ),
            "triangle_count": sum(
                len(item.resource.triangles) for item in self._actors.values()
            ),
            "render_count": self._render_count,
            "last_render_ms": round(self._last_render_ms, 3),
            "viewport": list(self._window.GetSize()),
            "projection": self._projection,
            "render_mode": self._render_mode,
            "color_scheme": self._color_scheme,
            "background_theme": self._background_theme,
            "hidden_count": len(self._hidden_nodes),
            "isolation_count": len(self._isolation_nodes),
            "ghost_count": len(self._ghost_nodes),
            "section_count": len(self._section_planes),
            "clipping_box_active": self._clipping_box is not None,
            "explode_factor": self._explode_factor,
            "measurement_count": len(self._measurements),
            "last_measurement": self._measurements[-1] if self._measurements else None,
        }

    def save_viewpoint(self, name: str) -> None:
        camera = self._renderer.GetActiveCamera()
        self._viewpoints[name] = {
            "position": list(camera.GetPosition()),
            "focal_point": list(camera.GetFocalPoint()),
            "view_up": list(camera.GetViewUp()),
            "parallel_scale": float(camera.GetParallelScale()),
            "projection": self._projection,
        }

    def restore_viewpoint(self, name: str) -> None:
        value = self._viewpoints.get(name)
        if value is None:
            raise KeyError(name)
        camera = self._renderer.GetActiveCamera()
        camera.SetPosition(*value["position"])
        camera.SetFocalPoint(*value["focal_point"])
        camera.SetViewUp(*value["view_up"])
        camera.SetParallelScale(value["parallel_scale"])
        self.set_projection(value["projection"])

    def workspace(self) -> dict[str, Any]:
        camera = self._renderer.GetActiveCamera()
        color_scheme = "status" if self._color_scheme == "accuracy" else self._color_scheme
        background_theme = "light" if self._background_theme == "white" else self._background_theme
        payload = {
            "schema_version": "1.1",
            "project_id": self._steel_model.project_id if self._steel_model is not None else "",
            "scene_hash": self._viewer_host.snapshot_sha256 if self._viewer_host is not None else "",
            "camera": {
                "position": dict(zip(("x", "y", "z"), camera.GetPosition())),
                "target": dict(zip(("x", "y", "z"), camera.GetFocalPoint())),
                "up": dict(zip(("x", "y", "z"), camera.GetViewUp())),
                "projection": self._projection,
                "field_of_view_deg": float(camera.GetViewAngle()),
                "ortho_scale": float(camera.GetParallelScale()),
                "near_plane": float(camera.GetClippingRange()[0]),
                "far_plane": float(camera.GetClippingRange()[1]),
                "coordinate_system": "world-mm",
                "version": 1,
            },
            "selection_level": "part",
            "selected_node_ids": sorted(self._selected_nodes),
            "hidden_node_ids": sorted(self._hidden_nodes),
            "isolation_node_ids": sorted(self._isolation_nodes),
            "ghost_context": bool(self._ghost_nodes),
            "transparency_by_node": [[key, value] for key, value in sorted(self._transparency.items())],
            "color_by_node": [],
            "display_preferences": {
                "render_mode": self._render_mode,
                "color_scheme": color_scheme,
                "background_theme": background_theme,
                "ghost_opacity": 0.22,
                "selection_color": {"red": 0.98, "green": 0.78, "blue": 0.20, "alpha": 1.0},
                "edge_width": 0.65,
                "show_selection_outline": True,
                "version": 1,
            },
            "section_planes": [
                {"plane_id": key, **value} for key, value in sorted(self._section_planes.items())
            ],
            "clipping_box": (
                None if self._clipping_box is None else {"bounds": list(self._clipping_box)}
            ),
            "viewpoints": [
                {"name": key, **value} for key, value in sorted(self._viewpoints.items())
            ],
            "visibility_sets": [],
            "accuracy_mode": self._accuracy_debug,
            "active_viewpoint_id": None,
            "explode_offsets": [
                {"scope": "project", "factor": self._explode_factor}
            ] if self._explode_factor else [],
            "measurements": list(self._measurements),
            "measurement_settings": {"active_kind": self._measurement_mode or None, "units": "mm"},
        }
        payload["state_hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        return payload

    def load_workspace(self, workspace: Mapping[str, Any]) -> None:
        if workspace.get("schema_version") != "1.1":
            raise ValueError("Unsupported viewer workspace schema")
        if self._steel_model is None or workspace.get("project_id") != self._steel_model.project_id:
            raise ValueError("Viewer workspace belongs to another project")
        expected_payload = dict(workspace)
        actual_hash = str(expected_payload.pop("state_hash", ""))
        expected_hash = hashlib.sha256(
            json.dumps(expected_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError("Viewer workspace checksum does not match its content")
        existing = set(self._model_by_node)
        self._selected_nodes = set(workspace.get("selected_node_ids") or ()) & existing
        self._hidden_nodes = set(workspace.get("hidden_node_ids") or ()) & existing
        self._isolation_nodes = set(workspace.get("isolation_node_ids") or ()) & existing
        self._ghost_nodes = set(existing - self._isolation_nodes) if workspace.get("ghost_context") else set()
        self._transparency = {
            str(key): float(value)
            for key, value in workspace.get("transparency_by_node") or ()
            if key in existing
        }
        display = dict(workspace.get("display_preferences") or {})
        self._render_mode = str(display.get("render_mode") or "shaded_edges")
        self._color_scheme = str(display.get("color_scheme") or "original")
        self._background_theme = str(display.get("background_theme") or "dark")
        explode = list(workspace.get("explode_offsets") or ())
        self._explode_factor = float(explode[0].get("factor", 0.0)) if explode else 0.0
        self._section_planes = {
            str(item.get("plane_id") or f"plane-{index}"): {
                "normal": tuple(item.get("normal") or (0.0, 0.0, 1.0)),
                "origin": tuple(item.get("origin") or (0.0, 0.0, 0.0)),
            }
            for index, item in enumerate(workspace.get("section_planes") or ())
        }
        raw_box = workspace.get("clipping_box")
        self._clipping_box = tuple(float(item) for item in raw_box.get("bounds", ())) if raw_box else None
        self._measurements = [dict(item) for item in workspace.get("measurements") or ()]
        self._measurement_mode = str(dict(workspace.get("measurement_settings") or {}).get("active_kind") or "")
        self._viewpoints = {
            str(item.get("name") or f"Viewpoint {index + 1}"): {
                key: value for key, value in dict(item).items() if key != "name"
            }
            for index, item in enumerate(workspace.get("viewpoints") or ())
        }
        camera_data = dict(workspace.get("camera") or {})
        camera = self._renderer.GetActiveCamera()
        if camera_data:
            camera.SetPosition(*(camera_data["position"][key] for key in ("x", "y", "z")))
            camera.SetFocalPoint(*(camera_data["target"][key] for key in ("x", "y", "z")))
            camera.SetViewUp(*(camera_data["up"][key] for key in ("x", "y", "z")))
            camera.SetParallelScale(float(camera_data["ortho_scale"]))
            camera.SetViewAngle(float(camera_data.get("field_of_view_deg", 45.0)))
            self._projection = str(camera_data.get("projection") or "perspective")
            camera.SetParallelProjection(self._projection == "orthographic")
        if self._background_theme == "slate":
            self._background_theme = "dark"
        self.set_background(self._background_theme)
        self._apply_visibility(); self._refresh_actor_styles(); self._apply_clipping(); self._apply_explode(); self.render()

    def actor_bounds(self, steel_model_id: str) -> tuple[float, ...]:
        record = self._actors.get(steel_model_id)
        if record is None:
            return ()
        return tuple(float(item) for item in record.actor.GetBounds())

    def close(self) -> None:
        self._clear_scene()
        self._window.Finalize()


def math_is_positive(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number > 0.0 and number < float("inf")


__all__ = [
    "BUILTIN_RENDERER_CAPABILITIES",
    "BUILTIN_RENDERER_NAME",
    "BUILTIN_RENDERER_VERSION",
    "VtkOffscreenRenderer",
]
