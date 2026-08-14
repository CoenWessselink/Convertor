"""VTK instanced-mesh backend used by the V1 technology spike.

This backend is intentionally limited to the shared synthetic box fixture.  It
proves the project-renderer primitives that matter for the technology choice:
instancing, stable node picking, clipping, camera motion and off-screen capture.
It is not yet the V2 production renderer.
"""
from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Any

from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import Vector3
from cws_viewer.technology.contracts import (
    NativeWindow,
    TechnologyBackendCapabilities,
    TechnologyBackendName,
    TechnologyScene,
)


def _vtk_module() -> Any:
    try:
        import vtk  # type: ignore

        return vtk
    except Exception as exc:  # pragma: no cover - exercised by diagnostics/CI
        raise ViewerError(
            "VTK-meshrenderer is niet beschikbaar",
            code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            context={"backend": TechnologyBackendName.VTK_MESH.value, "error": str(exc)},
        ) from exc


def _version() -> str:
    try:
        return importlib.metadata.version("vtk")
    except importlib.metadata.PackageNotFoundError:
        return ""


class VtkMeshSpikeBackend:
    """One-glyph-actor VTK backend with stable point-index node mapping."""

    def __init__(self, *, render_window: Any | None = None, offscreen: bool = True) -> None:
        self._external_render_window = render_window
        self._offscreen = bool(offscreen)
        self._vtk: Any | None = None
        self._render_window: Any | None = None
        self._renderer: Any | None = None
        self._mapper: Any | None = None
        self._actor: Any | None = None
        self._points: Any | None = None
        self._polydata: Any | None = None
        self._cube_source: Any | None = None
        self._node_ids: tuple[str, ...] = ()
        self._scene: TechnologyScene | None = None
        self._clip_plane: Any | None = None
        self._clip_glyph_filter: Any | None = None
        self._clip_filter: Any | None = None
        self._clip_mapper: Any | None = None
        self._initialized = False
        self._width = 0
        self._height = 0

    @property
    def name(self) -> TechnologyBackendName:
        return TechnologyBackendName.VTK_MESH

    def capabilities(self) -> TechnologyBackendCapabilities:
        return TechnologyBackendCapabilities(
            backend=self.name,
            backend_version=_version(),
            exact_brep=False,
            mesh_instancing=True,
            stable_node_picking=True,
            clipping_plane=True,
            offscreen_capture=True,
            native_window_required=False,
            qt_host_available=self._qt_host_available(),
            notes=(
                "V1 gebruikt vtkGlyph3DMapper: één gedeelde boxmesh, N stabiele instances.",
                "Exacte BREP/subshape-identiteit blijft een aparte OCCT-verantwoordelijkheid.",
            ),
        )

    @staticmethod
    def _qt_host_available() -> bool:
        try:
            from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor  # noqa: F401

            return True
        except Exception:
            return False

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._render_window is None or self._renderer is None:
            raise ViewerError(
                "VTK-backend is niet geïnitialiseerd",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
                context={"backend": self.name.value},
            )

    def initialize(
        self,
        *,
        width: int,
        height: int,
        native_window: NativeWindow | None = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Rendererafmetingen moeten positief zijn")
        vtk = _vtk_module()
        self._vtk = vtk
        self._width = int(width)
        self._height = int(height)
        renderer = vtk.vtkRenderer()
        renderer.SetBackground(0.075, 0.095, 0.13)
        renderer.SetBackground2(0.16, 0.19, 0.24)
        renderer.GradientBackgroundOn()
        if self._external_render_window is None:
            render_window = vtk.vtkRenderWindow()
            if self._offscreen:
                render_window.SetOffScreenRendering(1)
        else:
            render_window = self._external_render_window
        render_window.SetSize(self._width, self._height)
        render_window.AddRenderer(renderer)
        render_window.SetWindowName("CWS Viewer V1 — VTK mesh spike")
        self._renderer = renderer
        self._render_window = render_window
        self._initialized = True

    def load_scene(self, scene: TechnologyScene) -> None:
        self._ensure_initialized()
        vtk = self._vtk
        assert vtk is not None and self._renderer is not None
        self.clear_scene()

        points = vtk.vtkPoints()
        points.SetDataTypeToFloat()
        for instance in scene.instances:
            points.InsertNextPoint(instance.center.x, instance.center.y, instance.center.z)
        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)

        cube = vtk.vtkCubeSource()
        cube.SetXLength(scene.box_size.x)
        cube.SetYLength(scene.box_size.y)
        cube.SetZLength(scene.box_size.z)

        mapper = vtk.vtkGlyph3DMapper()
        mapper.SetInputData(polydata)
        mapper.SetSourceConnection(cube.GetOutputPort())
        mapper.ScalingOff()
        mapper.OrientOff()
        mapper.SetUseSelectionIds(False)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.42, 0.68, 0.88)
        actor.GetProperty().SetEdgeColor(0.08, 0.16, 0.24)
        actor.GetProperty().SetEdgeVisibility(True)
        actor.GetProperty().SetLineWidth(0.7)
        actor.GetProperty().SetInterpolationToPhong()

        self._renderer.AddActor(actor)
        self._points = points
        self._polydata = polydata
        self._cube_source = cube
        self._mapper = mapper
        self._actor = actor
        self._node_ids = tuple(instance.node_id for instance in scene.instances)
        self._scene = scene
        self._clip_plane = None
        self._clip_glyph_filter = None
        self._clip_filter = None
        self._clip_mapper = None

    def clear_scene(self) -> None:
        if self._renderer is not None:
            self._renderer.RemoveAllViewProps()
        self._mapper = None
        self._actor = None
        self._points = None
        self._polydata = None
        self._cube_source = None
        self._node_ids = ()
        self._scene = None
        self._clip_plane = None
        self._clip_glyph_filter = None
        self._clip_filter = None
        self._clip_mapper = None

    def fit_all(self) -> None:
        self._ensure_initialized()
        assert self._renderer is not None
        self._renderer.ResetCamera()
        self._renderer.ResetCameraClippingRange()

    def set_top_view(self) -> None:
        self._ensure_initialized()
        if self._scene is None:
            return
        assert self._renderer is not None
        bounds = self._scene.bounds
        center = bounds.center
        size = bounds.size
        distance = max(size.x, size.y, size.z, 1.0) * 2.0
        camera = self._renderer.GetActiveCamera()
        camera.SetFocalPoint(center.x, center.y, center.z)
        camera.SetPosition(center.x, center.y, center.z + distance)
        camera.SetViewUp(0.0, 1.0, 0.0)
        camera.ParallelProjectionOn()
        self.fit_all()

    def set_isometric_view(self) -> None:
        self._ensure_initialized()
        if self._scene is None:
            return
        assert self._renderer is not None
        bounds = self._scene.bounds
        center = bounds.center
        size = bounds.size
        distance = max(size.x, size.y, size.z, 1.0) * 2.3
        camera = self._renderer.GetActiveCamera()
        camera.SetFocalPoint(center.x, center.y, center.z)
        camera.SetPosition(center.x + distance, center.y - distance, center.z + distance)
        camera.SetViewUp(0.0, 0.0, 1.0)
        camera.ParallelProjectionOff()
        self.fit_all()

    def orbit_step(self, angle_degrees: float) -> None:
        self._ensure_initialized()
        assert self._renderer is not None
        camera = self._renderer.GetActiveCamera()
        camera.Azimuth(float(angle_degrees))
        camera.OrthogonalizeViewUp()

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

    def pick_at(self, x: int, y: int) -> str | None:
        self._ensure_initialized()
        if not self._node_ids:
            return None
        assert self._vtk is not None and self._renderer is not None
        picker = self._vtk.vtkPointPicker()
        picker.SetTolerance(0.01)
        if not picker.Pick(float(x), float(y), 0.0, self._renderer):
            return None
        point_id = int(picker.GetPointId())
        if point_id < 0 or point_id >= len(self._node_ids):
            return None
        return self._node_ids[point_id]

    def set_clip_plane(self, *, origin: Vector3, normal: Vector3) -> None:
        self._ensure_initialized()
        if normal.length() <= 1e-12:
            raise ValueError("Clipvlaknormal mag niet nul zijn")
        assert self._vtk is not None and self._actor is not None
        assert self._polydata is not None and self._cube_source is not None
        self.clear_clip_planes()
        plane = self._vtk.vtkPlane()
        plane.SetOrigin(origin.x, origin.y, origin.z)
        plane.SetNormal(normal.x, normal.y, normal.z)

        # vtkGlyph3DMapper 9.6 has a dynamic clipping shader regression on
        # some Mesa/driver combinations.  Use an explicit temporary geometry
        # pipeline for the section proof instead of accepting shader errors.
        glyph = self._vtk.vtkGlyph3D()
        glyph.SetInputData(self._polydata)
        glyph.SetSourceConnection(self._cube_source.GetOutputPort())
        glyph.ScalingOff()
        glyph.OrientOff()
        clip = self._vtk.vtkClipPolyData()
        clip.SetInputConnection(glyph.GetOutputPort())
        clip.SetClipFunction(plane)
        clip.InsideOutOn()
        clip.GenerateClippedOutputOff()
        mapper = self._vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(clip.GetOutputPort())
        mapper.ScalarVisibilityOff()
        self._actor.SetMapper(mapper)
        self._actor.Modified()
        self._clip_plane = plane
        self._clip_glyph_filter = glyph
        self._clip_filter = clip
        self._clip_mapper = mapper

    def clear_clip_planes(self) -> None:
        if self._actor is not None and self._mapper is not None:
            self._actor.SetMapper(self._mapper)
            self._actor.Modified()
        self._clip_plane = None
        self._clip_glyph_filter = None
        self._clip_filter = None
        self._clip_mapper = None

    def capture_png(self, output: str | Path) -> Path:
        self._ensure_initialized()
        assert self._vtk is not None and self._render_window is not None
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.render()
        image_filter = self._vtk.vtkWindowToImageFilter()
        image_filter.SetInput(self._render_window)
        image_filter.SetInputBufferTypeToRGB()
        image_filter.ReadFrontBufferOff()
        image_filter.Update()
        writer = self._vtk.vtkPNGWriter()
        writer.SetFileName(str(path))
        writer.SetInputConnection(image_filter.GetOutputPort())
        writer.Write()
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("VTK-screenshot kon niet worden geschreven")
        return path

    def resize(self, width: int, height: int) -> None:
        self._ensure_initialized()
        if width <= 0 or height <= 0:
            return
        self._width = int(width)
        self._height = int(height)
        assert self._render_window is not None
        self._render_window.SetSize(self._width, self._height)

    def dispose(self) -> None:
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


__all__ = ["VtkMeshSpikeBackend"]
