"""V15 T3 interaction host with zoom-area and explicit camera checkpoints."""
from __future__ import annotations

from typing import Any

from cws_viewer.core.v15_navigation import V15ViewNavigationService
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_real_project_widget import VtkRealProjectWidget


if qt_available():
    QtCore, _QtGui, _QtWidgets = require_qt()

    class VtkRealProjectWidgetV15(VtkRealProjectWidget):
        """Keep the V14 renderer/input contract and add V15 T3 view actions."""

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

        def wheelEvent(self, event: Any) -> None:
            self._v15_view_navigation.camera_checkpoint()
            super().wheelEvent(event)

        def keyPressEvent(self, event: Any) -> None:
            if event.key() == QtCore.Qt.Key.Key_Escape and self._v15_zoom_area:
                self.set_zoom_area(False)
                self.tool_cancelled.emit()
                event.accept()
                return
            if event.key() in {
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
