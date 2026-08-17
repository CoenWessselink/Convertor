"""Deterministic V15 navigation, camera-history and clipping helpers.

This module adds the T3 interaction layer without changing canonical project or
manufacturing data.  It deliberately wraps the stable V14 controller instead of
forking rendering truth.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from cws_viewer.contracts.enums import ProjectionType, StandardView
from cws_viewer.contracts.state import CameraState, ClippingBox, SectionPlane, Viewpoint
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import BoundingBox, Vector3

V15_T3_SCHEMA = "cws-viewer-navigation-15.3"
V15_T3_VERSION = "1.4.0-v15-preview.2"


def navigation_contract() -> dict[str, Any]:
    return {
        "schema": V15_T3_SCHEMA,
        "version": V15_T3_VERSION,
        "capabilities": {
            "orbit_pan_zoom": True,
            "orbit_around_picked_point": True,
            "selection_orbit_focus": True,
            "object_assembly_selection_mode": True,
            "temporary_alt_selection_inversion": True,
            "zoom_to_fit": True,
            "zoom_area": True,
            "camera_history": True,
            "view_from_face_normal": True,
            "orthogonal_surface_double_click": True,
            "camera_positioning": True,
            "perspective_orthographic": True,
            "predefined_views": True,
            "keyboard_navigation": True,
            "trimble_camera_shortcuts": True,
            "section_plane_enable_disable": True,
            "section_plane_flip_remove": True,
            "clipping_box": True,
            "saved_view_contract": True,
            "deterministic_view_state": True,
        },
    }


class V15ViewNavigationService:
    """View-only T3 service over an existing viewer controller.

    Camera history is explicit rather than tied to every low-level mouse delta.
    A drag gesture therefore creates one checkpoint, while individual renderer
    updates remain smooth and deterministic.
    """

    def __init__(self, controller: Any, *, history_limit: int = 64) -> None:
        self.controller = controller
        self.history_limit = max(2, int(history_limit))
        self._camera_back: list[CameraState] = []
        self._camera_forward: list[CameraState] = []

    @property
    def can_camera_back(self) -> bool:
        return bool(self._camera_back)

    @property
    def can_camera_forward(self) -> bool:
        return bool(self._camera_forward)

    def clear_camera_history(self) -> None:
        self._camera_back.clear()
        self._camera_forward.clear()

    def camera_checkpoint(self) -> CameraState:
        camera = self.controller.get_camera()
        if not self._camera_back or self._camera_back[-1] != camera:
            self._camera_back.append(camera)
            if len(self._camera_back) > self.history_limit:
                del self._camera_back[0]
        self._camera_forward.clear()
        return camera

    def camera_back(self) -> bool:
        if not self._camera_back:
            return False
        current = self.controller.get_camera()
        target = self._camera_back.pop()
        if target == current and self._camera_back:
            target = self._camera_back.pop()
        if target == current:
            return False
        self._camera_forward.append(current)
        self.controller.set_camera(target)
        return True

    def camera_forward(self) -> bool:
        if not self._camera_forward:
            return False
        current = self.controller.get_camera()
        target = self._camera_forward.pop()
        if target == current:
            return False
        self._camera_back.append(current)
        self.controller.set_camera(target)
        return True

    def set_orbit_pivot(self, point: Vector3) -> Vector3:
        """Bind orbit to a world-space model point without reframing the view."""
        setter = getattr(self.controller, "set_orbit_pivot", None)
        if not callable(setter):
            raise ViewerError(
                "Deze viewercontroller ondersteunt geen expliciete orbitpivot",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            )
        return setter(point)

    def focus_orbit_on_selection(self) -> Vector3 | None:
        focus = getattr(self.controller, "focus_orbit_on_selection", None)
        if not callable(focus):
            raise ViewerError(
                "Deze viewercontroller ondersteunt geen selectiegebonden orbitpivot",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            )
        return focus()

    def fit_all(self) -> None:
        self.camera_checkpoint()
        self.controller.fit_all()

    def fit_selection(self) -> None:
        self.camera_checkpoint()
        self.controller.fit_selection()

    def set_standard_view(self, view: StandardView) -> None:
        self.camera_checkpoint()
        self.controller.set_standard_view(StandardView(view))

    def set_projection(self, projection: ProjectionType) -> None:
        self.camera_checkpoint()
        self.controller.set_projection(ProjectionType(projection))

    def set_camera_position(
        self,
        position: Vector3,
        *,
        target: Vector3 | None = None,
        up: Vector3 | None = None,
    ) -> CameraState:
        self.camera_checkpoint()
        current = self.controller.get_camera()
        updated = replace(
            current,
            position=position,
            target=current.target if target is None else target,
            up=current.up if up is None else up,
        )
        self.controller.set_camera(updated)
        return updated

    @staticmethod
    def _stable_up(normal: Vector3, requested: Vector3 | None = None) -> Vector3:
        n = normal.normalized()
        candidate = requested or Vector3(0.0, 0.0, 1.0)
        if candidate.length() <= 1e-12:
            candidate = Vector3(0.0, 0.0, 1.0)
        candidate = candidate.normalized()
        if abs(candidate.dot(n)) > 0.95:
            candidate = Vector3(0.0, 1.0, 0.0)
        projected = candidate - n * candidate.dot(n)
        if projected.length() <= 1e-12:
            projected = Vector3(1.0, 0.0, 0.0)
        return projected.normalized()

    def view_from_normal(
        self,
        normal: Vector3,
        *,
        target: Vector3 | None = None,
        up_hint: Vector3 | None = None,
        fit: bool = False,
    ) -> CameraState:
        """Place the camera orthogonal to a surface normal.

        ``target`` may be the exact picked surface point.  When omitted, the
        active orbit focus is used (normally the selected object's bounds
        center), never an unrelated stale scene target.  Orientation does not
        implicitly perform Fit All; fitting is an explicit separate action.
        """
        if normal.length() <= 1e-12:
            raise ValueError("Vlaknormaal mag geen nulvector zijn")
        self.camera_checkpoint()
        current = self.controller.get_camera()
        n = normal.normalized()
        default_anchor = getattr(self.controller, "orbit_pivot", current.target)
        anchor = default_anchor if target is None else target
        distance = max((current.position - current.target).length(), 1.0)
        updated = replace(
            current,
            target=anchor,
            position=anchor + n * distance,
            up=self._stable_up(n, up_hint),
        )
        self.controller.set_camera(updated)
        self.set_orbit_pivot(anchor)
        if fit:
            self.controller.fit_all()
            updated = self.controller.get_camera()
        return updated

    def zoom_area_screen_rect(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        *,
        crossing: bool = True,
    ) -> tuple[str, ...]:
        index = self.controller.index
        backend = getattr(self.controller, "_backend", None)
        selector = getattr(backend, "nodes_in_screen_rect", None)
        if not callable(selector):
            raise ViewerError(
                "Zoomgebied wordt niet door deze renderer ondersteund",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            )
        raw = tuple(
            dict.fromkeys(
                str(value)
                for value in selector(
                    int(x0), int(y0), int(x1), int(y1), index, crossing=bool(crossing)
                )
                if str(value) in index.nodes_by_id
            )
        )
        if not raw:
            return ()
        bounds = index.bounds_for(raw, include_descendants=True)
        if bounds is None:
            return ()
        self.camera_checkpoint()
        fit_bounds = getattr(self.controller, "_fit_bounds", None)
        if not callable(fit_bounds):
            raise ViewerError(
                "Zoomgebied kan niet op camerabounds worden toegepast",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            )
        fit_bounds(bounds)
        reset_pivot = getattr(self.controller, "reset_orbit_pivot", None)
        if callable(reset_pivot):
            reset_pivot()
        return raw

    def _scene_bounds(self) -> BoundingBox:
        bounds = self.controller.index.scene_bounds()
        if bounds is None:
            raise RuntimeError("Scene bevat geen renderbare objecten")
        return bounds

    def add_section(self, normal: Vector3, *, owner: str = "CWS Viewer V15") -> str:
        center = self._scene_bounds().center
        return self.controller.add_section_plane(
            SectionPlane(origin=center, normal=normal.normalized(), owner=owner)
        )

    def set_section_enabled(self, plane_id: str, enabled: bool) -> None:
        plane = self.controller.session.section_planes.get(str(plane_id))
        if plane is None:
            raise KeyError(plane_id)
        self.controller.update_section_plane(str(plane_id), replace(plane, enabled=bool(enabled)))

    def flip_section(self, plane_id: str) -> None:
        plane = self.controller.session.section_planes.get(str(plane_id))
        if plane is None:
            raise KeyError(plane_id)
        self.controller.update_section_plane(str(plane_id), replace(plane, flipped=not plane.flipped))

    def remove_section(self, plane_id: str) -> None:
        self.controller.remove_section_plane(str(plane_id))

    def clear_sections(self) -> None:
        for plane_id in tuple(self.controller.session.section_planes):
            self.controller.remove_section_plane(plane_id)

    def set_clip_box_fraction(self, fraction: float = 0.8) -> ClippingBox:
        value = float(fraction)
        if not 0.01 <= value <= 1.0:
            raise ValueError("Clippingfractie moet tussen 0.01 en 1.0 liggen")
        bounds = self._scene_bounds()
        center = bounds.center
        half = bounds.size * (value * 0.5)
        box = ClippingBox(BoundingBox(center - half, center + half))
        self.controller.set_clipping_box(box)
        return box

    def clear_clip_box(self) -> None:
        self.controller.set_clipping_box(None)

    def save_named_view(self, name: str, *, owner: str = "CWS Viewer V15") -> Viewpoint:
        return self.controller.save_viewpoint(str(name), owner=owner)


__all__ = [
    "V15_T3_SCHEMA",
    "V15_T3_VERSION",
    "V15ViewNavigationService",
    "navigation_contract",
]
