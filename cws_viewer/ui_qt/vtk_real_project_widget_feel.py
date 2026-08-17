"""Single-build interaction repair for the Phase-2 project viewer."""
from __future__ import annotations

import math
from typing import Any

from cws_viewer.backends.vtk_project_mesh_feel import VtkProjectMeshFeelBackend
from cws_viewer.core.viewer_feel_navigation import (
    ViewerFeelNavigationService,
    WHEEL_ZOOM_PER_NOTCH,
)
from cws_viewer.ui_qt import vtk_real_project_widget as _base_widget
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_real_project_widget import NavigationMode
from cws_viewer.ui_qt.vtk_real_project_widget_phase2 import VtkRealProjectWidgetPhase2


if qt_available():
    QtCore, _QtGui, _QtWidgets = require_qt()

    class VtkRealProjectWidgetFeel(VtkRealProjectWidgetPhase2):
        """Phase-2 viewer with cursor zoom and coalesced mouse navigation."""

        ORBIT_DEG_PER_PIXEL = 0.22
        LOOK_DEG_PER_PIXEL = 0.20
        WALK_DISTANCE_PER_PIXEL = 0.0018
        NAVIGATION_FRAME_MS = 10

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            # The original VTK widget constructs its backend from a module-level
            # class reference. Replace that reference only during construction
            # so all higher-level controller contracts remain unchanged.
            previous_backend = _base_widget.VtkProjectMeshV14Backend
            _base_widget.VtkProjectMeshV14Backend = VtkProjectMeshFeelBackend
            try:
                super().__init__(*args, **kwargs)
            finally:
                _base_widget.VtkProjectMeshV14Backend = previous_backend

            if not isinstance(self.backend, VtkProjectMeshFeelBackend):
                raise RuntimeError("Quality renderer kon niet worden geactiveerd")

            self._v15_view_navigation = ViewerFeelNavigationService(self.controller)
            self._feel_pending_dx = 0.0
            self._feel_pending_dy = 0.0
            self._feel_motion_timer = QtCore.QTimer(self)
            self._feel_motion_timer.setSingleShot(True)
            self._feel_motion_timer.setInterval(self.NAVIGATION_FRAME_MS)
            self._feel_motion_timer.timeout.connect(self._flush_navigation_motion)
            self.set_navigation_mode(self.navigation_mode)

        def set_navigation_mode(self, mode: NavigationMode | str) -> None:
            super().set_navigation_mode(mode)
            # Selection and rotate use the normal pointer. Pan is deliberately
            # the only hand cursor, matching the requested CAD/viewer behaviour.
            cursor = (
                QtCore.Qt.CursorShape.OpenHandCursor
                if self.navigation_mode == NavigationMode.PAN
                else QtCore.Qt.CursorShape.ArrowCursor
            )
            self.setCursor(cursor)

        def _schedule_navigation_motion(self, dx: float, dy: float) -> None:
            self._feel_pending_dx += float(dx)
            self._feel_pending_dy += float(dy)
            if not self._feel_motion_timer.isActive():
                self._feel_motion_timer.start()

        def _flush_navigation_motion(self) -> None:
            dx = self._feel_pending_dx
            dy = self._feel_pending_dy
            self._feel_pending_dx = 0.0
            self._feel_pending_dy = 0.0
            if abs(dx) <= 1e-12 and abs(dy) <= 1e-12:
                return
            button = self._pressed_button
            if button is None:
                return
            try:
                if button == QtCore.Qt.MouseButton.MiddleButton or (
                    button == QtCore.Qt.MouseButton.LeftButton
                    and self.navigation_mode == NavigationMode.PAN
                ):
                    self.controller.pan_pixels(dx, dy, anchor=self._v15_pan_anchor)
                elif button == QtCore.Qt.MouseButton.LeftButton:
                    if self.navigation_mode == NavigationMode.ORBIT:
                        self.controller.orbit(
                            -dx * self.ORBIT_DEG_PER_PIXEL,
                            -dy * self.ORBIT_DEG_PER_PIXEL,
                        )
                    elif self.navigation_mode == NavigationMode.LOOK:
                        self.controller.look(
                            -dx * self.LOOK_DEG_PER_PIXEL,
                            -dy * self.LOOK_DEG_PER_PIXEL,
                        )
                    elif self.navigation_mode == NavigationMode.WALK:
                        camera = self.controller.get_camera()
                        distance = max((camera.target - camera.position).length(), 1.0)
                        self.controller.walk(
                            forward=-dy * distance * self.WALK_DISTANCE_PER_PIXEL,
                            right=dx * distance * self.WALK_DISTANCE_PER_PIXEL,
                        )
                overlay = getattr(self, "_phase2_markup_overlay", None)
                if overlay is not None:
                    overlay.update()
            except Exception as exc:
                self.backend_failed.emit(f"{type(exc).__name__}: {exc}")

        def mousePressEvent(self, event: Any) -> None:
            if self.markup_tool_active:
                super().mousePressEvent(event)
                return
            self._feel_pending_dx = 0.0
            self._feel_pending_dy = 0.0
            self._feel_motion_timer.stop()
            super().mousePressEvent(event)
            if (
                self.navigation_mode == NavigationMode.PAN
                and event.button() == QtCore.Qt.MouseButton.LeftButton
            ):
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)

        def mouseMoveEvent(self, event: Any) -> None:
            if (
                self.markup_tool_active
                or self._v15_zoom_area
                or self._area_selection
                or self._press_pos is None
                or self._last_pos is None
                or self._pressed_button is None
            ):
                super().mouseMoveEvent(event)
                return

            if self._pressed_button not in {
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.MouseButton.MiddleButton,
            }:
                super().mouseMoveEvent(event)
                return

            current = event.position()
            if (
                not self._dragging
                and self._distance(current, self._press_pos) >= self._drag_threshold_px
            ):
                self._dragging = True
            if not self._dragging:
                event.accept()
                return

            dx = float(current.x() - self._last_pos.x())
            dy = float(current.y() - self._last_pos.y())
            self._last_pos = current
            self._schedule_navigation_motion(dx, dy)
            event.accept()

        def mouseReleaseEvent(self, event: Any) -> None:
            if not self.markup_tool_active and event.button() in {
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.MouseButton.MiddleButton,
            }:
                self._feel_motion_timer.stop()
                self._flush_navigation_motion()
            super().mouseReleaseEvent(event)
            if not self.markup_tool_active:
                self.setCursor(
                    QtCore.Qt.CursorShape.OpenHandCursor
                    if self.navigation_mode == NavigationMode.PAN
                    else QtCore.Qt.CursorShape.ArrowCursor
                )

        def _wheel_anchor(self, pos: Any):
            probe = self._probe_screen(pos)
            if probe is not None:
                return probe.world_point
            reference = getattr(
                self.controller, "orbit_pivot", self.controller.get_camera().target
            )
            try:
                x, y = self._vtk_xy(pos)
                return self.backend.world_point_at_display_depth(x, y, reference)
            except Exception:
                return reference

        def wheelEvent(self, event: Any) -> None:
            delta = float(event.angleDelta().y())
            if abs(delta) <= 1e-12:
                pixel = event.pixelDelta()
                delta = float(pixel.y()) if not pixel.isNull() else 0.0
            if abs(delta) <= 1e-12:
                event.accept()
                return

            # A standard Windows wheel detent is 120 units. 8% per detent gives
            # a controlled CAD-style step instead of the former 15% jump.
            steps = delta / 120.0
            steps = max(-12.0, min(12.0, steps))
            factor = math.pow(WHEEL_ZOOM_PER_NOTCH, steps)
            try:
                self.view_navigation.camera_checkpoint()
                anchor = self._wheel_anchor(event.position())
                self.view_navigation.zoom_about_point(factor, anchor)
                overlay = getattr(self, "_phase2_markup_overlay", None)
                if overlay is not None:
                    overlay.update()
            except Exception as exc:
                self.backend_failed.emit(f"{type(exc).__name__}: {exc}")
            event.accept()

        def closeEvent(self, event: Any) -> None:
            self._feel_motion_timer.stop()
            super().closeEvent(event)

else:

    class VtkRealProjectWidgetFeel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["VtkRealProjectWidgetFeel"]
