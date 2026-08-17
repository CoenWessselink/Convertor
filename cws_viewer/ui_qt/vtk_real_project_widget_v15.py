"""V15 T3 interaction host with Trimble-style point orbit and camera checkpoints."""
from __future__ import annotations

from typing import Any

from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.core.v15_navigation import V15ViewNavigationService
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_real_project_widget import NavigationMode, VtkRealProjectWidget


if qt_available():
    QtCore, _QtGui, _QtWidgets = require_qt()

    class VtkRealProjectWidgetV15(VtkRealProjectWidget):
        """Keep the V14 renderer/input contract and add V15 parity interactions."""

        zoom_area_completed = QtCore.Signal(object)

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._v15_view_navigation = V15ViewNavigationService(self.controller)
            self._v15_zoom_area = False

        @property
        def view_navigation(self) -> V15ViewNavigationService:
            return self._v15_view_navigation

        @property
        def zoom_area_enabled(self) -> bool:
            return bool(self._v15_zoom_area)

        def set_zoom_area(self, enabled: bool = True) -> None:
            self._v15_zoom_area = bool(enabled)
            if self._v15_zoom_area:
                self._area_selection = False
                self._rubber_band.hide()
                self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
                self.interaction_message.emit(
                    "Zoomgebied: sleep een venster rond het gewenste modelgebied · Esc annuleert"
                )
            else:
                self._rubber_band.hide()
                try:
                    self.set_navigation_mode(self.navigation_mode)
                except Exception:
                    self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

        def set_area_selection(self, enabled: bool = True) -> None:
            self._v15_zoom_area = False
            super().set_area_selection(enabled)

        def _temporary_alt_selection_level(self) -> SelectionLevel | None:
            """Invert Object/Assembly for one click without changing persistent mode."""
            level = self.controller.session.selection_level
            if level == SelectionLevel.PART:
                return SelectionLevel.ASSEMBLY
            if level == SelectionLevel.ASSEMBLY:
                return SelectionLevel.PART
            return None

        def _pick(self, pos: Any, modifiers: Any, *, emit: bool = True):
            temporary = None
            if modifiers & QtCore.Qt.KeyboardModifier.AltModifier:
                temporary = self._temporary_alt_selection_level()
            if temporary is None:
                return super()._pick(pos, modifiers, emit=emit)

            x, y = self._vtk_xy(pos)
            pick = self.controller.pick_at_level(
                x,
                y,
                level=temporary,
                mode=self._selection_mode(modifiers),
            )
            if pick is not None and emit:
                self.node_picked.emit(pick.node_id)
                self.pick_result.emit(pick)
            return pick

        def _bind_orbit_pivot_from_screen(self, pos: Any) -> bool:
            """Bind a rotate drag to the exact visible model point under the cursor."""
            try:
                x, y = self._vtk_xy(pos)
                probe = self.controller.probe_at(x, y)
                if probe is None:
                    return False
                self._v15_view_navigation.set_orbit_pivot(probe.world_point)
                return True
            except Exception as exc:
                self.backend_failed.emit(f"{type(exc).__name__}: {exc}")
                return False

        def mousePressEvent(self, event: Any) -> None:
            if self._v15_zoom_area and event.button() == QtCore.Qt.MouseButton.LeftButton:
                self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
                self._press_pos = event.position()
                self._last_pos = event.position()
                self._pressed_button = event.button()
                self._dragging = False
                origin = event.position().toPoint()
                self._rubber_band.setGeometry(QtCore.QRect(origin, origin))
                self._rubber_band.show()
                event.accept()
                return
            if (
                not self._area_selection
                and event.button() in {
                    QtCore.Qt.MouseButton.LeftButton,
                    QtCore.Qt.MouseButton.MiddleButton,
                }
            ):
                self._v15_view_navigation.camera_checkpoint()
            if (
                not self._area_selection
                and event.button() == QtCore.Qt.MouseButton.LeftButton
                and self.navigation_mode == NavigationMode.ORBIT
            ):
                # Rotate binds to the exact point under mouse-down. Probe only:
                # selection is still decided on release when the gesture was a click.
                self._bind_orbit_pivot_from_screen(event.position())
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event: Any) -> None:
            if self._v15_zoom_area and self._press_pos is not None:
                current = event.position()
                if not self._dragging and self._distance(current, self._press_pos) >= self._drag_threshold_px:
                    self._dragging = True
                if self._dragging:
                    self._rubber_band.setGeometry(
                        QtCore.QRect(self._press_pos.toPoint(), current.toPoint()).normalized()
                    )
                event.accept()
                return
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event: Any) -> None:
            if (
                self._v15_zoom_area
                and self._press_pos is not None
                and self._pressed_button == QtCore.Qt.MouseButton.LeftButton
            ):
                start = self._press_pos
                end = event.position()
                dragged = self._dragging
                self._press_pos = None
                self._last_pos = None
                self._pressed_button = None
                self._dragging = False
                self._rubber_band.hide()
                try:
                    if dragged:
                        x0, y0 = self._vtk_xy(start)
                        x1, y1 = self._vtk_xy(end)
                        crossing = float(end.x()) < float(start.x())
                        nodes = self._v15_view_navigation.zoom_area_screen_rect(
                            x0, y0, x1, y1, crossing=crossing
                        )
                        self.zoom_area_completed.emit(nodes)
                        self.interaction_message.emit(
                            f"Zoomgebied toegepast op {len(nodes):,} object(en)"
                            if nodes
                            else "Zoomgebied bevatte geen renderbare objecten"
                        )
                except Exception as exc:
                    self.backend_failed.emit(f"{type(exc).__name__}: {exc}")
                finally:
                    self.set_zoom_area(False)
                event.accept()
                return
            super().mouseReleaseEvent(event)

        def mouseDoubleClickEvent(self, event: Any) -> None:
            if (
                event.button() == QtCore.Qt.MouseButton.LeftButton
                and event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier
            ):
                try:
                    # Orthogonal surface view is a camera operation, not an
                    # Object/Assembly selection inversion. Use a non-mutating probe.
                    x, y = self._vtk_xy(event.position())
                    pick = self.controller.probe_at(x, y)
                    if pick is not None and pick.normal is not None:
                        self._v15_view_navigation.view_from_normal(
                            pick.normal,
                            target=pick.world_point,
                            fit=False,
                        )
                        self.interaction_message.emit(
                            "Orthogonaal aan gekozen vlak"
                        )
                    event.accept()
                    return
                except Exception as exc:
                    self.backend_failed.emit(f"{type(exc).__name__}: {exc}")
                    event.accept()
                    return
            super().mouseDoubleClickEvent(event)

        def wheelEvent(self, event: Any) -> None:
            self._v15_view_navigation.camera_checkpoint()
            super().wheelEvent(event)

        def keyPressEvent(self, event: Any) -> None:
            key = event.key()
            modifiers = event.modifiers()

            if key == QtCore.Qt.Key.Key_F11:
                window = self.window()
                if window.isFullScreen():
                    window.showNormal()
                    self.interaction_message.emit("Volledig scherm uit")
                else:
                    window.showFullScreen()
                    self.interaction_message.emit("Volledig scherm aan")
                event.accept()
                return

            if key == QtCore.Qt.Key.Key_Escape:
                if self._v15_zoom_area:
                    self.set_zoom_area(False)
                    self.tool_cancelled.emit()
                else:
                    super().keyPressEvent(event)
                    if self.controller.get_selection():
                        self.controller.set_selection((), mode="replace")
                    self.interaction_message.emit("Selectie gewist")
                event.accept()
                return

            if modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
                mode = {
                    QtCore.Qt.Key.Key_U: NavigationMode.ORBIT,
                    QtCore.Qt.Key.Key_I: NavigationMode.PAN,
                    QtCore.Qt.Key.Key_O: NavigationMode.WALK,
                    QtCore.Qt.Key.Key_P: NavigationMode.LOOK,
                }.get(key)
                if mode is not None:
                    self.set_navigation_mode(mode)
                    event.accept()
                    return

            if key == QtCore.Qt.Key.Key_Backspace:
                selected = self.controller.get_selection()
                if selected:
                    if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier:
                        self.controller.isolate(selected, ghost_context=False)
                        self.interaction_message.emit(
                            f"Andere objecten verborgen · {len(selected):,} geselecteerd"
                        )
                    else:
                        self.controller.hide(selected)
                        self.interaction_message.emit(
                            f"{len(selected):,} geselecteerd(e) object(en) verborgen"
                        )
                    event.accept()
                    return

            if key in {
                QtCore.Qt.Key.Key_W,
                QtCore.Qt.Key.Key_A,
                QtCore.Qt.Key.Key_S,
                QtCore.Qt.Key.Key_D,
                QtCore.Qt.Key.Key_Q,
                QtCore.Qt.Key.Key_E,
            }:
                self._v15_view_navigation.camera_checkpoint()
            super().keyPressEvent(event)

else:

    class VtkRealProjectWidgetV15:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["VtkRealProjectWidgetV15"]
