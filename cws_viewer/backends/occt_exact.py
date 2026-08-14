"""Native OCCT/AIS exact source-versus-canonical Part Workbench backend."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.exact.model import ExactPartRuntime, SubshapeKind
from cws_viewer.exact.occt_selection import OcctSubshapeSelectionBridge
from cws_viewer.math3d import Vector3
from cws_viewer.technology.contracts import NativeWindow

from .native_window import bind_neutral_window


def _imports() -> dict[str, Any]:
    try:
        from OCP.AIS import AIS_InteractiveContext, AIS_Shape
        from OCP.Aspect import Aspect_DisplayConnection, Aspect_NeutralWindow
        from OCP.OpenGl import OpenGl_GraphicDriver
        from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
        from OCP.V3d import V3d_Viewer
        from OCP.gp import gp_Dir
        return locals()
    except Exception as exc:  # pragma: no cover - packaged runtime gate
        raise ViewerError(
            "OCCT exact Part Workbench runtime ontbreekt",
            code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            context={"error": str(exc)},
        ) from exc


class OcctExactPartBackend:
    def __init__(self) -> None:
        self._ocp: dict[str, Any] | None = None
        self._display_connection = None
        self._driver = None
        self._viewer = None
        self._context = None
        self._view = None
        self._window = None
        self._native_handle_capsule = None
        self._source_ais = None
        self._canonical_ais = None
        self._source: ExactPartRuntime | None = None
        self._canonical: ExactPartRuntime | None = None
        self._bridge: OcctSubshapeSelectionBridge | None = None
        self._width = 0
        self._height = 0
        self._initialized = False
        self._selection_kind = SubshapeKind.FACE

    @property
    def source(self) -> ExactPartRuntime | None:
        return self._source

    def initialize(self, *, width: int, height: int, native_window: NativeWindow) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Rendererafmetingen moeten positief zijn")
        ocp = _imports(); self._ocp = ocp; self._width = int(width); self._height = int(height)
        try:
            connection = ocp["Aspect_DisplayConnection"]()
            driver = ocp["OpenGl_GraphicDriver"](connection)
            viewer = ocp["V3d_Viewer"](driver); viewer.SetDefaultLights(); viewer.SetLightOn()
            context = ocp["AIS_InteractiveContext"](viewer); context.SetDisplayMode(1, False)
            view = viewer.CreateView(); window = ocp["Aspect_NeutralWindow"]()
            self._native_handle_capsule = bind_neutral_window(window, native_window.handle)
            window.SetSize(self._width, self._height); window.Map(); view.SetWindow(window)
            view.SetBackgroundColor(ocp["Quantity_Color"](0.035,0.055,0.085,ocp["Quantity_TOC_RGB"]))
            self._display_connection=connection; self._driver=driver; self._viewer=viewer
            self._context=context; self._view=view; self._window=window; self._initialized=True
        except Exception as exc:
            self.dispose()
            raise ViewerError(
                "OCCT exact Part Workbench kon niet initialiseren",
                code=ViewerErrorCode.RENDERER_INIT_FAILED,
                context={"error":f"{type(exc).__name__}: {exc}"},
            ) from exc

    def _ensure(self) -> None:
        if not self._initialized or self._context is None or self._view is None:
            raise RuntimeError("OCCT exact backend is niet geïnitialiseerd")

    def load_parts(self, source: ExactPartRuntime, canonical: ExactPartRuntime | None = None) -> None:
        self._ensure(); assert self._ocp and self._context
        self._context.RemoveAll(False)
        source_ais=self._ocp["AIS_Shape"](source.shape.wrapped)
        source_ais.SetColor(self._ocp["Quantity_Color"](0.68,0.72,0.78,self._ocp["Quantity_TOC_RGB"]))
        source_ais.SetTransparency(0.58)
        self._context.Display(source_ais,False)
        canonical_ais=None
        if canonical is not None:
            canonical_ais=self._ocp["AIS_Shape"](canonical.shape.wrapped)
            canonical_ais.SetColor(self._ocp["Quantity_Color"](0.08,0.78,0.94,self._ocp["Quantity_TOC_RGB"]))
            canonical_ais.SetTransparency(0.28)
            self._context.Display(canonical_ais,False)
        self._source_ais=source_ais; self._canonical_ais=canonical_ais
        self._source=source; self._canonical=canonical; self._bridge=OcctSubshapeSelectionBridge(source)
        self.set_selection_kind(self._selection_kind)
        self.set_isometric_view(); self.fit_all(); self.render()

    def set_selection_kind(self, kind: SubshapeKind) -> None:
        self._selection_kind=SubshapeKind(kind)
        if self._context is not None and self._source_ais is not None:
            OcctSubshapeSelectionBridge.activate_context(self._context,self._source_ais,self._selection_kind)

    def pick_at(self, x: int, y: int) -> str | None:
        self._ensure(); assert self._context is not None and self._view is not None
        if self._bridge is None:
            return None
        self._context.MoveTo(int(x),int(y),self._view,True)
        if not self._context.HasDetectedShape():
            return None
        stable_id=self._bridge.stable_id_for_shape(self._context.DetectedShape())
        if stable_id is not None:
            self.highlight(stable_id)
        return stable_id

    def highlight(self, stable_id: str | None) -> None:
        self._ensure(); assert self._context is not None
        self._context.ClearSelected(False)
        if stable_id is None or self._bridge is None:
            self.render(); return
        shape=self._bridge.shape_for_stable_id(stable_id)
        # AddOrRemoveSelected accepts TopoDS_Shape in current OCP binding.
        try:
            self._context.AddOrRemoveSelected(shape.wrapped if hasattr(shape,"wrapped") else shape,False)
        except TypeError:
            pass
        self._context.HilightSelected(False); self.render()

    def fit_all(self) -> None:
        self._ensure(); self._view.FitAll(0.03,False); self._view.ZFitAll()

    def set_isometric_view(self) -> None:
        self._ensure(); self._view.SetProj(1.0,-1.0,1.0)

    def set_top_view(self) -> None:
        self._ensure(); self._view.SetProj(0.0,0.0,1.0); self.fit_all()

    def set_front_view(self) -> None:
        self._ensure(); self._view.SetProj(0.0,-1.0,0.0); self.fit_all()

    def render(self) -> None:
        self._ensure(); self._view.Redraw()

    def world_to_display(self, point: Vector3) -> tuple[int,int]:
        self._ensure(); x,y=self._view.Convert(point.x,point.y,point.z); return int(x),int(y)

    def capture_png(self, output: str | Path) -> Path:
        self._ensure(); path=Path(output); path.parent.mkdir(parents=True,exist_ok=True); self.render()
        if not self._view.Dump(str(path)) or not path.is_file() or path.stat().st_size==0:
            raise RuntimeError("OCCT screenshot kon niet worden geschreven")
        return path

    def resize(self,width:int,height:int)->None:
        self._ensure(); self._width=max(1,int(width)); self._height=max(1,int(height))
        self._window.SetSize(self._width,self._height); self._view.MustBeResized()

    def dispose(self)->None:
        try:
            if self._context is not None: self._context.RemoveAll(False)
            if self._view is not None:
                try: self._view.Remove()
                except Exception: pass
        finally:
            self._source_ais=None; self._canonical_ais=None; self._source=None; self._canonical=None; self._bridge=None
            self._window=None; self._native_handle_capsule=None; self._view=None; self._context=None; self._viewer=None; self._driver=None; self._display_connection=None; self._ocp=None; self._initialized=False


__all__=["OcctExactPartBackend"]
