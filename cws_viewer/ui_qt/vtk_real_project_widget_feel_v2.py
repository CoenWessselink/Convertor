"""Trimble-feel V2 input host with adaptive interaction rendering.

The widget keeps upright orbit, Ctrl multiselect and live measuring while adding
an explicit low-latency interaction state.  Full SSAO/antialiasing quality is
restored once pointer input has been idle for a short, deterministic debounce.
"""
from __future__ import annotations

import time
from typing import Any

from cws_viewer.backends.vtk_project_mesh_adaptive import VtkProjectMeshAdaptiveBackend
from cws_viewer.contracts.enums import RenderMode, SelectionLevel
from cws_viewer.core.viewer_feel_navigation_v2 import ViewerFeelNavigationV2Service
from cws_viewer.core.viewer_interaction_profile import (
    TRIMBLE_STYLE_INTERACTION_PROFILE,
)
from cws_viewer.performance import FrameTimeRecorder
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
        NAVIGATION_FRAME_MS = TRIMBLE_STYLE_INTERACTION_PROFILE.navigation_frame_ms
        MEASURE_PREVIEW_MS = TRIMBLE_STYLE_INTERACTION_PROFILE.measurement_preview_ms
        INTERACTION_IDLE_MS = TRIMBLE_STYLE_INTERACTION_PROFILE.interaction_idle_ms

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            # Prevent VTK's native diagnostic window from floating through the
            # embedded viewport. Application errors remain visible normally.
            try:
                from vtkmodules.vtkCommonCore import vtkOutputWindow, vtkStringOutputWindow
                vtkOutputWindow.SetInstance(vtkStringOutputWindow())
            except Exception:
                pass
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
            self._navigation_frame_metrics = FrameTimeRecorder()
            self._install_viewport_controls()

        RAL_COLOURS = (
            ("IFC / originele kleuren", None),
            ("RAL 1003 Signaalgeel", (249, 168, 0)),
            ("RAL 2004 Zuiver oranje", (228, 94, 15)),
            ("RAL 3000 Vuurrood", (175, 43, 30)),
            ("RAL 5010 Gentiaanblauw", (0, 79, 124)),
            ("RAL 6005 Mosgroen", (15, 67, 54)),
            ("RAL 6018 Geelgroen", (87, 166, 57)),
            ("RAL 7016 Antracietgrijs", (56, 62, 66)),
            ("RAL 7035 Lichtgrijs", (203, 208, 204)),
            ("RAL 9005 Gitzwart", (10, 10, 13)),
            ("RAL 9010 Zuiver wit", (241, 236, 225)),
        )

        def _install_viewport_controls(self) -> None:
            panel = _QtWidgets.QFrame(self)
            panel.setObjectName("cwsV15ViewportControls")
            panel.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
            panel.setStyleSheet(
                "QFrame#cwsV15ViewportControls { background: rgba(255,255,255,238); "
                "border: 1px solid #aebdce; border-radius: 4px; }"
                "QComboBox { min-height: 25px; padding: 2px 7px; background: white; "
                "border: 1px solid #b8c6d6; border-radius: 3px; }"
                "QPushButton#cwsRealisticButton { min-height: 27px; padding: 2px 13px; "
                "color: white; font-weight: 700; background: #0875d1; "
                "border: 1px solid #075fa8; border-radius: 3px; }"
                "QPushButton#cwsRealisticButton:hover { background: #0868b8; }"
                "QPushButton#cwsRealisticButton:pressed { background: #064f8c; }"
                "QLabel { color: #1b3552; font-weight: 600; }"
            )
            layout = _QtWidgets.QHBoxLayout(panel)
            layout.setContentsMargins(8, 5, 8, 5)
            layout.setSpacing(6)

            layout.addWidget(_QtWidgets.QLabel("Selecteren"))
            selection = _QtWidgets.QComboBox(panel)
            selection.setMinimumWidth(205)
            selection.addItem("Onderdeel (één maakdeel)", SelectionLevel.PART.value)
            selection.addItem("Samenstelling / merk", SelectionLevel.ASSEMBLY.value)
            current = self.controller.session.selection_level.value
            selection.setCurrentIndex(max(0, selection.findData(current)))
            selection.setToolTip("Bepaalt of een klik één onderdeel of de bovenliggende samenstelling selecteert")
            selection.currentIndexChanged.connect(self._viewport_selection_level_changed)
            layout.addWidget(selection)

            layout.addWidget(_QtWidgets.QLabel("Weergave"))
            rendering = _QtWidgets.QComboBox(panel)
            rendering.addItem("Realistisch + schaduw", True)
            rendering.addItem("Technisch scherp", False)
            rendering.currentIndexChanged.connect(self._viewport_rendering_changed)
            layout.addWidget(rendering)

            ral = _QtWidgets.QComboBox(panel)
            ral.setMinimumWidth(205)
            for label, rgb in self.RAL_COLOURS:
                ral.addItem(label, rgb)
            ral.setToolTip("RAL Classic-kleuren als gekalibreerde sRGB-schermweergave")
            ral.currentIndexChanged.connect(self._viewport_ral_changed)
            layout.addWidget(ral)

            realistic = _QtWidgets.QPushButton("Realistisch", panel)
            realistic.setObjectName("cwsRealisticButton")
            realistic.setToolTip(
                "Render het volledige model met originele IFC-kleuren, "
                "realistische materialen, belichting en schaduw"
            )
            realistic.clicked.connect(self._apply_best_realistic_rendering)
            layout.addWidget(realistic)

            panel.adjustSize()
            panel.move(12, 12)
            panel.raise_()
            self._viewport_controls = panel
            self._viewport_selection_combo = selection
            self._viewport_render_combo = rendering
            self._viewport_ral_combo = ral
            self._viewport_realistic_button = realistic

        def _viewport_selection_level_changed(self, _index: int) -> None:
            value = str(self._viewport_selection_combo.currentData() or SelectionLevel.PART.value)
            self.controller.set_selection_level(SelectionLevel(value))

        def _viewport_rendering_changed(self, _index: int) -> None:
            self.backend.set_realistic_rendering(bool(self._viewport_render_combo.currentData()))

        def _viewport_ral_changed(self, _index: int) -> None:
            value = self._viewport_ral_combo.currentData()
            rgb = None if value is None else tuple(int(channel) for channel in value)
            self.backend.set_ral_colour(rgb)

        def _apply_best_realistic_rendering(self) -> None:
            """Apply the highest-quality realistic preset to the complete scene."""
            render_blocker = QtCore.QSignalBlocker(self._viewport_render_combo)
            colour_blocker = QtCore.QSignalBlocker(self._viewport_ral_combo)
            self._viewport_render_combo.setCurrentIndex(0)
            self._viewport_ral_combo.setCurrentIndex(0)
            del render_blocker, colour_blocker

            try:
                self.backend.set_interaction_quality(False)
                self.controller.set_render_mode(RenderMode.SHADED_EDGES)
                self.backend.set_ral_colour(None)
                self.backend.set_realistic_rendering(True)

                overlay = getattr(self, "_trimble_navigation_overlay", None)
                opacity_slider = getattr(overlay, "opacity_slider", None)
                if opacity_slider is not None:
                    opacity_slider.setValue(100)
                else:
                    opacity_setter = getattr(self.backend, "set_global_opacity", None)
                    if callable(opacity_setter):
                        opacity_setter(1.0)

                self.backend.render()
            except Exception as exc:
                self.backend_failed.emit(f"{type(exc).__name__}: {exc}")

        def resizeEvent(self, event: Any) -> None:
            super().resizeEvent(event)
            controls = getattr(self, "_viewport_controls", None)
            if controls is not None:
                controls.move(12, 12)
                controls.raise_()

        def showEvent(self, event: Any) -> None:
            super().showEvent(event)
            controls = getattr(self, "_viewport_controls", None)
            if controls is not None:
                controls.raise_()

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
            frame_started = time.perf_counter()
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
            finally:
                self._navigation_frame_metrics.record((time.perf_counter() - frame_started) * 1000.0)

        def performance_diagnostics(self) -> dict[str, Any]:
            return {
                "schema": "cws-viewer-interaction-performance-2.0",
                "navigation": self._navigation_frame_metrics.to_dict(),
                "interaction_quality_active": self.interaction_quality_active,
                "navigation_frame_ms": self.NAVIGATION_FRAME_MS,
                "measurement_preview_ms": self.MEASURE_PREVIEW_MS,
                "interaction_idle_ms": self.INTERACTION_IDLE_MS,
            }

        def mousePressEvent(self, event: Any) -> None:
            if not self.markup_tool_active and event.button() in {
                QtCore.Qt.MouseButton.LeftButton,
                QtCore.Qt.MouseButton.MiddleButton,
            }:
                self._begin_interaction_quality()
                # Bind each orbit gesture to the actual surface under the
                # cursor without changing the central project selection.
                if (
                    event.button() == QtCore.Qt.MouseButton.LeftButton
                    and self.navigation_mode == NavigationMode.ORBIT
                ):
                    try:
                        backend = getattr(self, "backend", None) or getattr(self, "_backend", None)
                        if backend is not None:
                            x, y = self._vtk_xy(event.position())
                            hit = backend.pick_at(x, y, self.controller.index)
                            if hit is not None:
                                self.controller.set_orbit_pivot(hit.world_point)
                    except Exception:
                        # Clicking empty space, or clicking while a scene is
                        # loading, preserves the last valid model pivot.
                        pass
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
