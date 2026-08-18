"""Trimble-feel V2 input host with adaptive interaction rendering.

The widget keeps upright orbit, Ctrl multiselect and live measuring while adding
an explicit low-latency interaction state.  Full SSAO/antialiasing quality is
restored once pointer input has been idle for a short, deterministic debounce.
"""
from __future__ import annotations

from typing import Any

from cws_viewer.backends.vtk_project_mesh_adaptive import VtkProjectMeshAdaptiveBackend
from cws_viewer.core.viewer_feel_navigation_v2 import ViewerFeelNavigationV2Service
from cws_viewer.ui_qt import vtk_real_project_widget_feel as _feel_module
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_real_project_widget import NavigationMode
from cws_viewer.ui_qt.vtk_real_project_widget_feel import VtkRealProjectWidgetFeel


if qt_available():
    QtCore, _QtGui, _QtWidgets = require_qt()

    class VtkRealProjectWidgetFeelV2(VtkRealProjectWidgetFeel):
        """Interaction profile matching the requested structural-viewer feel."""

        # A 60 Hz navigation scheduler avoids wasteful duplicate renders while
        # remaining perceptually direct. Measurement preview remains smooth at
        # roughly 22 Hz without rebuilding transient VTK actors for every raw
        # mouse event.
        NAVIGATION_FRAME_MS = 16
        MEASURE_PREVIEW_MS = 45
        INTERACTION_IDLE_MS = 180

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            previous = _feel_module.VtkProjectMeshFeelBackend
            _feel_module.VtkProjectMeshFeelBackend = VtkProjectMeshAdaptiveBackend
            try:
                super().__init__(*args, **kwargs)
            finally:
                _feel_module.VtkProjectMeshFeelBackend = previous
            if not isinstance(self.backend, VtkProjectMeshAdaptiveBackend):
                raise RuntimeError("Adaptieve Trimble-feel V15 renderer kon niet worden geactiveerd")

            self._v15_view_navigation = ViewerFeelNavigationV2Service(self.controller)
            self._measure_preview_start: Any | None = None
            self._measure_preview_kind: Any | None = None
            self._measure_preview_pos: Any | None = None
            self._measure_preview_timer = QtCore.QTimer(self)
            self._measure_preview_timer.setSingleShot(True)
            self._measure_preview_timer.setInterval(self.MEASURE_PREVIEW_MS)
            self._measure_preview_timer.timeout.connect(self._flush_measurement_preview)

            self._interaction_idle_timer = QtCore.QTimer(self)
            self._interaction_idle_timer.setSingleShot(True)
            self._interaction_idle_timer.setInterval(self.INTERACTION_IDLE_MS)
            self._interaction_idle_timer.timeout.connect(self._restore_idle_quality)

        @property
        def interaction_quality_active(self) -> bool:
            return bool(self.backend.interaction_quality_active)

        def _begin_interaction_quality(self) -> None:
            self.backend.set_interaction_quality(True)
            self._interaction_idle_timer.start()

        def _restore_idle_quality(self) -> None:
            changed = self.backend.set_interaction_quality(False)
            if changed:
                try:
                    self.backend.render()
                except Exception as exc:
                    self.backend_failed.emit(f"{type(exc).__name__}: {exc}")

        def _selection_mode(self, modifiers: Any) -> str:
            # Requested CWS desktop behaviour: Ctrl repeatedly builds/toggles a
            # multiselection; Shift remains a convenient add-only modifier.
            if modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
                return "toggle"
            if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier:
                return "add"
            return "replace"

        def _schedule_navigation_motion(self, dx: float, dy: float) -> None:
            self._begin_interaction_quality()
            super()._schedule_navigation_motion(dx, dy)

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

        def mousePressEvent(self, event: Any) -> None:
            if not self.markup_tool_active and event.button() in {
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.MouseButton.MiddleButton,
            }:
                self._begin_interaction_quality()
            super().mousePressEvent(event)

        def wheelEvent(self, event: Any) -> None:
            self._begin_interaction_quality()
            super().wheelEvent(event)

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
            if not self.markup_tool_active:
                self._interaction_idle_timer.start()

        def closeEvent(self, event: Any) -> None:
            self._measure_preview_timer.stop()
            self._interaction_idle_timer.stop()
            self.backend.set_interaction_quality(False)
            super().closeEvent(event)

else:

    class VtkRealProjectWidgetFeelV2:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["VtkRealProjectWidgetFeelV2"]
