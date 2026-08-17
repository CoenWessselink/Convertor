"""Trimble-feel V2 input host: upright orbit, Ctrl multiselect and live measuring."""
from __future__ import annotations

from typing import Any

from cws_viewer.backends.vtk_project_mesh_feel_v2 import VtkProjectMeshFeelV2Backend
from cws_viewer.core.viewer_feel_navigation_v2 import ViewerFeelNavigationV2Service
from cws_viewer.ui_qt import vtk_real_project_widget_feel as _feel_module
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_real_project_widget import NavigationMode
from cws_viewer.ui_qt.vtk_real_project_widget_feel import VtkRealProjectWidgetFeel


if qt_available():
    QtCore, _QtGui, _QtWidgets = require_qt()

    class VtkRealProjectWidgetFeelV2(VtkRealProjectWidgetFeel):
        """Interaction profile matching the requested structural-viewer feel."""

        MEASURE_PREVIEW_MS = 28

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            previous = _feel_module.VtkProjectMeshFeelBackend
            _feel_module.VtkProjectMeshFeelBackend = VtkProjectMeshFeelV2Backend
            try:
                super().__init__(*args, **kwargs)
            finally:
                _feel_module.VtkProjectMeshFeelBackend = previous
            if not isinstance(self.backend, VtkProjectMeshFeelV2Backend):
                raise RuntimeError("Trimble-feel V2 renderer kon niet worden geactiveerd")

            self._v15_view_navigation = ViewerFeelNavigationV2Service(self.controller)
            self._measure_preview_start: Any | None = None
            self._measure_preview_kind: Any | None = None
            self._measure_preview_pos: Any | None = None
            self._measure_preview_timer = QtCore.QTimer(self)
            self._measure_preview_timer.setSingleShot(True)
            self._measure_preview_timer.setInterval(self.MEASURE_PREVIEW_MS)
            self._measure_preview_timer.timeout.connect(self._flush_measurement_preview)

        def _selection_mode(self, modifiers: Any) -> str:
            # Requested CWS desktop behaviour: Ctrl repeatedly builds/toggles a
            # multiselection; Shift remains a convenient add-only modifier.
            if modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
                return "toggle"
            if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier:
                return "add"
            return "replace"

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
                        self.view_navigation.orbit_upright(
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

        def set_measurement_preview_anchor(self, point: Any | None, kind: Any | None) -> None:
            self._measure_preview_start = point
            self._measure_preview_kind = kind
            if point is None or kind is None:
                self._measure_preview_timer.stop()
                self._measure_preview_pos = None
                self.backend.set_measurement_preview(None, None, None)

        def _schedule_measurement_preview(self, pos: Any) -> None:
            self._measure_preview_pos = QtCore.QPointF(float(pos.x()), float(pos.y()))
            if not self._measure_preview_timer.isActive():
                self._measure_preview_timer.start()

        def _flush_measurement_preview(self) -> None:
            start = self._measure_preview_start
            kind = self._measure_preview_kind
            pos = self._measure_preview_pos
            if start is None or kind is None or pos is None:
                return
            try:
                probe = self._probe_screen(pos)
                if probe is None:
                    self.backend.set_measurement_preview(None, None, None)
                else:
                    self.backend.set_measurement_preview(start, probe.world_point, kind)
            except Exception as exc:
                self.backend_failed.emit(f"{type(exc).__name__}: {exc}")

        def mouseMoveEvent(self, event: Any) -> None:
            if (
                self._measure_preview_start is not None
                and self._pressed_button is None
                and not self.markup_tool_active
            ):
                self._schedule_measurement_preview(event.position())
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event: Any) -> None:
            super().mouseReleaseEvent(event)
            if self._measure_preview_start is not None:
                self._schedule_measurement_preview(event.position())

        def closeEvent(self, event: Any) -> None:
            self._measure_preview_timer.stop()
            super().closeEvent(event)

else:

    class VtkRealProjectWidgetFeelV2:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["VtkRealProjectWidgetFeelV2"]
