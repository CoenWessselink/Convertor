"""Off-screen VTK renderer used by the Tk project workspace.

The PyPI VTK wheel does not ship ``vtkRenderingTk.dll`` on Windows. Rendering
to PNG keeps the application on one Tk UI stack while still using VTK for the
actual mesh, camera, depth buffer and picking pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
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
BUILTIN_RENDERER_VERSION = "0.1"
BUILTIN_RENDERER_CAPABILITIES: tuple[str, ...] = tuple(
    sorted(set(CORE_VIEWER_CAPABILITIES) | {"visibility.isolate"})
)


@dataclass(slots=True)
class _ActorRecord:
    entity: SteelEntityRecord
    resource: ViewerMeshResource
    viewer_node_id: str
    actor: Any


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
            self.isolate(value.get("viewer_node_ids") or ())
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
        )
        self._actors[resource.steel_model_id] = record
        self._node_by_actor_address[actor.GetAddressAsString("")] = binding.viewer_node_id
        self._renderer.AddActor(actor)
        self._apply_actor_style(record)

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
        elif self._accuracy_debug:
            color = self._accuracy_color(record.resource.accuracy_status)
        else:
            color = (0.72, 0.76, 0.73)
        record.actor.GetProperty().SetColor(*color)
        record.actor.GetProperty().SetAmbient(0.18)
        record.actor.GetProperty().SetDiffuse(0.78)
        record.actor.GetProperty().SetSpecular(0.16)
        record.actor.GetProperty().SetSpecularPower(18.0)

    def _refresh_actor_styles(self) -> None:
        for record in self._actors.values():
            self._apply_actor_style(record)

    def _set_selection(self, viewer_node_ids: Any) -> None:
        self._selected_nodes = {
            str(item) for item in viewer_node_ids if str(item) in self._model_by_node
        }
        self._refresh_actor_styles()
        self.render()

    def isolate(self, viewer_node_ids: Any) -> None:
        visible = {str(item) for item in viewer_node_ids}
        show_all = not visible
        for record in self._actors.values():
            record.actor.SetVisibility(show_all or record.viewer_node_id in visible)
        self.render()

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
        }

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
