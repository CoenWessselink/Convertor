"""OCCT/AIS exact-shape backend used by the V1 technology spike.

The backend hosts an OpenCascade V3d view in an externally supplied native
window.  The same implementation can be hosted by Tk during headless CI and by
PySide6/Qt in the V1 GUI harness.  It proves exact BREP presentation, stable AIS
object picking, clipping and capture without making the viewer a second source
of manufacturing truth.
"""
from __future__ import annotations

import importlib.metadata
import math
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

from .native_window import bind_neutral_window


def _version() -> str:
    for candidate in ("cadquery-ocp", "OCP"):
        try:
            return importlib.metadata.version(candidate)
        except importlib.metadata.PackageNotFoundError:
            continue
    return ""


def _imports() -> dict[str, Any]:
    try:
        from OCP.AIS import AIS_ConnectedInteractive, AIS_InteractiveContext, AIS_Shape
        from OCP.Aspect import Aspect_DisplayConnection, Aspect_NeutralWindow
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCP.Graphic3d import Graphic3d_ClipPlane
        from OCP.OpenGl import OpenGl_GraphicDriver
        from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
        from OCP.V3d import V3d_Viewer
        from OCP.gp import gp_Dir, gp_Pln, gp_Pnt, gp_Trsf, gp_Vec

        return locals()
    except Exception as exc:  # pragma: no cover - exercised by packaged CI
        raise ViewerError(
            "OCCT/AIS-renderer is niet beschikbaar",
            code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            context={"backend": TechnologyBackendName.OCCT_AIS.value, "error": str(exc)},
        ) from exc


class OcctAisSpikeBackend:
    """AIS renderer with one exact box BREP and N connected instances."""

    def __init__(self) -> None:
        self._ocp: dict[str, Any] | None = None
        self._display_connection: Any | None = None
        self._driver: Any | None = None
        self._viewer: Any | None = None
        self._context: Any | None = None
        self._view: Any | None = None
        self._window: Any | None = None
        self._native_handle_capsule: Any | None = None
        self._base_shape: Any | None = None
        self._instances: list[Any] = []
        self._node_by_object: dict[Any, str] = {}
        self._scene: TechnologyScene | None = None
        self._clip_plane: Any | None = None
        self._initialized = False
        self._width = 0
        self._height = 0

    @property
    def name(self) -> TechnologyBackendName:
        return TechnologyBackendName.OCCT_AIS

    def capabilities(self) -> TechnologyBackendCapabilities:
        return TechnologyBackendCapabilities(
            backend=self.name,
            backend_version=_version(),
            exact_brep=True,
            mesh_instancing=False,
            stable_node_picking=True,
            clipping_plane=True,
            offscreen_capture=True,
            native_window_required=True,
            qt_host_available=self._qt_host_available(),
            notes=(
                "V1 gebruikt AIS_ConnectedInteractive rond één exacte TopoDS box-shape.",
                "Dit pad is kandidaat voor exact Part Workbench BREP/subshape-picking, niet de enige projectscene.",
            ),
        )

    @staticmethod
    def _qt_host_available() -> bool:
        try:
            import PySide6  # noqa: F401

            return True
        except Exception:
            return False

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._view is None or self._context is None:
            raise ViewerError(
                "OCCT/AIS-backend is niet geïnitialiseerd",
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
        if native_window is None:
            raise ViewerError(
                "OCCT/AIS vereist een native window handle",
                code=ViewerErrorCode.RENDERER_INIT_FAILED,
                context={"backend": self.name.value},
            )
        if width <= 0 or height <= 0:
            raise ValueError("Rendererafmetingen moeten positief zijn")
        ocp = _imports()
        self._ocp = ocp
        self._width = int(width)
        self._height = int(height)
        try:
            display_connection = ocp["Aspect_DisplayConnection"]()
            driver = ocp["OpenGl_GraphicDriver"](display_connection)
            viewer = ocp["V3d_Viewer"](driver)
            viewer.SetDefaultLights()
            viewer.SetLightOn()
            context = ocp["AIS_InteractiveContext"](viewer)
            context.SetDisplayMode(1, False)
            view = viewer.CreateView()
            window = ocp["Aspect_NeutralWindow"]()
            self._native_handle_capsule = bind_neutral_window(window, native_window.handle)
            window.SetSize(self._width, self._height)
            window.Map()
            view.SetWindow(window)
            view.SetBackgroundColor(
                ocp["Quantity_Color"](0.075, 0.095, 0.13, ocp["Quantity_TOC_RGB"])
            )
            self._display_connection = display_connection
            self._driver = driver
            self._viewer = viewer
            self._context = context
            self._view = view
            self._window = window
            self._initialized = True
        except Exception as exc:
            self.dispose()
            raise ViewerError(
                "OCCT/AIS OpenGL-view kon niet worden geïnitialiseerd",
                code=ViewerErrorCode.RENDERER_INIT_FAILED,
                context={
                    "backend": self.name.value,
                    "native_handle": native_window.handle,
                    "width": width,
                    "height": height,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            ) from exc

    def load_scene(self, scene: TechnologyScene) -> None:
        self._ensure_initialized()
        assert self._ocp is not None and self._context is not None
        self.clear_scene()
        ocp = self._ocp
        shape = ocp["BRepPrimAPI_MakeBox"](
            scene.box_size.x,
            scene.box_size.y,
            scene.box_size.z,
        ).Shape()
        base = ocp["AIS_Shape"](shape)
        base.SetColor(ocp["Quantity_Color"](0.42, 0.68, 0.88, ocp["Quantity_TOC_RGB"]))
        self._base_shape = base

        half = scene.box_size * 0.5
        instances: list[Any] = []
        node_by_object: dict[Any, str] = {}
        for item in scene.instances:
            translation = item.center - half
            transform = ocp["gp_Trsf"]()
            transform.SetTranslation(
                ocp["gp_Vec"](translation.x, translation.y, translation.z)
            )
            interactive = ocp["AIS_ConnectedInteractive"]()
            interactive.Connect(base, transform)
            self._context.Display(interactive, False)
            instances.append(interactive)
            node_by_object[interactive] = item.node_id

        self._instances = instances
        self._node_by_object = node_by_object
        self._scene = scene
        self._clip_plane = None

    def clear_scene(self) -> None:
        if self._context is not None:
            self._context.RemoveAll(False)
        self._instances = []
        self._node_by_object = {}
        self._base_shape = None
        self._scene = None
        self._clip_plane = None

    def fit_all(self) -> None:
        self._ensure_initialized()
        assert self._view is not None
        self._view.FitAll(0.03, False)
        self._view.ZFitAll()

    def set_top_view(self) -> None:
        self._ensure_initialized()
        assert self._view is not None
        self._view.SetProj(0.0, 0.0, 1.0)
        self.fit_all()

    def set_isometric_view(self) -> None:
        self._ensure_initialized()
        assert self._view is not None
        self._view.SetProj(1.0, -1.0, 1.0)
        self.fit_all()

    def orbit_step(self, angle_degrees: float) -> None:
        self._ensure_initialized()
        assert self._view is not None
        radians = math.radians(float(angle_degrees))
        self._view.Rotate(0.0, radians, 0.0, True)

    def render(self) -> None:
        self._ensure_initialized()
        assert self._view is not None
        self._view.Redraw()

    def world_to_display(self, point: Vector3) -> tuple[int, int]:
        self._ensure_initialized()
        assert self._view is not None
        x, y = self._view.Convert(point.x, point.y, point.z)
        return int(x), int(y)

    def pick_at(self, x: int, y: int) -> str | None:
        self._ensure_initialized()
        assert self._context is not None and self._view is not None
        self._context.MoveTo(int(x), int(y), self._view, False)
        detected = self._context.DetectedInteractive()
        if detected is None:
            return None
        return self._node_by_object.get(detected)

    def set_clip_plane(self, *, origin: Vector3, normal: Vector3) -> None:
        self._ensure_initialized()
        if normal.length() <= 1e-12:
            raise ValueError("Clipvlaknormal mag niet nul zijn")
        assert self._ocp is not None and self._view is not None
        self.clear_clip_planes()
        direction = normal.normalized()
        plane = self._ocp["Graphic3d_ClipPlane"](
            self._ocp["gp_Pln"](
                self._ocp["gp_Pnt"](origin.x, origin.y, origin.z),
                self._ocp["gp_Dir"](direction.x, direction.y, direction.z),
            )
        )
        self._view.AddClipPlane(plane)
        self._clip_plane = plane

    def clear_clip_planes(self) -> None:
        if self._clip_plane is not None and self._view is not None:
            self._view.RemoveClipPlane(self._clip_plane)
        self._clip_plane = None

    def capture_png(self, output: str | Path) -> Path:
        self._ensure_initialized()
        assert self._view is not None
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.render()
        if not self._view.Dump(str(path)):
            raise RuntimeError("OCCT/AIS-screenshot kon niet worden geschreven")
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("OCCT/AIS-screenshot ontbreekt of is leeg")
        return path

    def resize(self, width: int, height: int) -> None:
        self._ensure_initialized()
        if width <= 0 or height <= 0:
            return
        self._width = int(width)
        self._height = int(height)
        assert self._window is not None and self._view is not None
        self._window.SetSize(self._width, self._height)
        self._view.MustBeResized()

    def dispose(self) -> None:
        try:
            if self._context is not None:
                self._context.RemoveAll(False)
            if self._view is not None:
                try:
                    self._view.Remove()
                except Exception:
                    pass
        finally:
            self._instances = []
            self._node_by_object = {}
            self._base_shape = None
            self._clip_plane = None
            self._scene = None
            self._window = None
            self._native_handle_capsule = None
            self._view = None
            self._context = None
            self._viewer = None
            self._driver = None
            self._display_connection = None
            self._ocp = None
            self._initialized = False


__all__ = ["OcctAisSpikeBackend"]
