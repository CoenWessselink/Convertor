from __future__ import annotations

from typing import Any, Callable

from PySide6 import QtCore, QtGui, QtWidgets


def _navigation_icon(name: str) -> QtGui.QIcon:
    def pixmap(color: str) -> QtGui.QPixmap:
        image = QtGui.QPixmap(24, 24)
        image.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        pen = QtGui.QPen(QtGui.QColor(color), 1.8, QtCore.Qt.PenStyle.SolidLine)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        if name in {"fit", "fullscreen"}:
            inset = 4 if name == "fit" else 3
            length = 5
            for x, y, sx, sy in (
                (inset, inset, 1, 1), (24 - inset, inset, -1, 1),
                (inset, 24 - inset, 1, -1), (24 - inset, 24 - inset, -1, -1),
            ):
                painter.drawLine(x, y, x + sx * length, y)
                painter.drawLine(x, y, x, y + sy * length)
        elif name == "orbit":
            painter.drawArc(QtCore.QRectF(4.5, 4.5, 15, 15), 30 * 16, 285 * 16)
            painter.drawLine(18.5, 5.5, 18.0, 10.0)
            painter.drawLine(18.5, 5.5, 14.3, 6.7)
            painter.drawEllipse(QtCore.QPointF(12, 12), 1.7, 1.7)
        elif name == "pan":
            painter.drawRoundedRect(QtCore.QRectF(7, 10, 10, 9), 3, 3)
            for x, top in ((8, 6), (11, 4), (14, 5), (17, 7)):
                painter.drawLine(x, top, x, 13)
            painter.drawLine(7, 13, 4.5, 11)
        elif name == "walk":
            painter.setBrush(QtGui.QColor(color))
            painter.drawEllipse(QtCore.QRectF(6, 4, 5, 8))
            painter.drawEllipse(QtCore.QRectF(13, 12, 5, 8))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        elif name in {"zoom_in", "zoom_out"}:
            painter.drawEllipse(QtCore.QRectF(4, 4, 12, 12))
            painter.drawLine(14.5, 14.5, 20, 20)
            painter.drawLine(7, 10, 13, 10)
            if name == "zoom_in":
                painter.drawLine(10, 7, 10, 13)
        elif name == "detach":
            painter.drawRoundedRect(QtCore.QRectF(4, 7, 11, 11), 1, 1)
            painter.drawRoundedRect(QtCore.QRectF(9, 4, 11, 11), 1, 1)
            painter.drawLine(14, 9, 19, 4)
            painter.drawLine(15.5, 4, 19, 4)
            painter.drawLine(19, 4, 19, 7.5)
        painter.end()
        return image

    icon = QtGui.QIcon()
    icon.addPixmap(pixmap("#075fcf"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    icon.addPixmap(pixmap("#ffffff"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
    return icon


class TrimbleNavigationOverlay(QtWidgets.QWidget):
    """Compact vector navigation bar for the integrated V15 viewer."""

    def __init__(self, viewer: QtWidgets.QWidget, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent or viewer)
        self.viewer = viewer
        self.controller = getattr(viewer, "controller", None)
        self.setObjectName("trimbleNavigationOverlay")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "#trimbleNavigationOverlay { background: rgba(255,255,255,248);"
            " border: 1px solid #cbd6e3; border-radius: 6px; }"
            "QToolButton { background: transparent; border: 1px solid transparent;"
            " border-radius: 4px; padding: 4px; }"
            "QToolButton:hover { background: #eaf3ff; border-color: #a8c7ec; }"
            "QToolButton:pressed { background: #d8eaff; }"
            "QToolButton:checked { background: #075fcf; border-color: #0754b8; }"
        )
        self.setFixedSize(298, 42)
        self._build()

    def _button(
        self,
        tooltip: str,
        icon_name: str,
        callback: Callable[[], None],
        *,
        checkable: bool = False,
    ) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton(self)
        button.setIcon(_navigation_icon(icon_name))
        button.setIconSize(QtCore.QSize(20, 20))
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setCheckable(checkable)
        button.setFixedSize(34, 32)
        button.clicked.connect(callback)
        return button

    def _build(self) -> None:
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(self._button("Alles passend in beeld", "fit", self._fit))
        orbit = self._button("Orbit: model draaien", "orbit", lambda: self._mode("orbit"), checkable=True)
        pan = self._button("Pan: beeld verschuiven", "pan", lambda: self._mode("pan"), checkable=True)
        walk = self._button("Lopen door model", "walk", lambda: self._mode("walk"), checkable=True)
        self._mode_buttons = {"orbit": orbit, "pan": pan, "walk": walk}
        self._mode_group = QtWidgets.QButtonGroup(self)
        self._mode_group.setExclusive(True)
        for button in self._mode_buttons.values():
            self._mode_group.addButton(button)
            layout.addWidget(button)
        orbit.setChecked(True)
        layout.addWidget(self._button("Inzoomen", "zoom_in", lambda: self._zoom(1.18)))
        layout.addWidget(self._button("Uitzoomen", "zoom_out", lambda: self._zoom(1.0 / 1.18)))
        layout.addWidget(self._button("Viewer in apart venster", "detach", self._open_detached))
        layout.addWidget(self._button("Volledig scherm", "fullscreen", self._fullscreen))

    def _fit(self) -> None:
        if self.controller is not None:
            self.controller.fit_all()

    def _orbit(self, dx: float, dy: float) -> None:
        if self.controller is not None:
            self.controller.orbit(dx, dy)

    def _zoom(self, factor: float) -> None:
        if self.controller is not None:
            self.controller.zoom(factor)

    def _mode(self, mode: str) -> None:
        self._mode_buttons[mode].setChecked(True)
        setter = getattr(self.viewer, "set_navigation_mode", None)
        if not callable(setter) and self.controller is not None:
            setter = getattr(self.controller, "set_navigation_mode", None)
        if callable(setter):
            setter(mode)

    def _open_detached(self) -> None:
        current: QtWidgets.QWidget | None = self.viewer
        while current is not None:
            for name in ("open_detached_viewer", "_open_detached_viewer", "show_detached_viewer"):
                callback = getattr(current, name, None)
                if callable(callback):
                    callback()
                    return
            for action in current.findChildren(QtGui.QAction):
                label = action.text().lower()
                if "apart venster" in label or "los venster" in label:
                    action.trigger()
                    return
            current = current.parentWidget()
        QtWidgets.QMessageBox.information(self, "Viewer", "Open de losse Viewer V15 via Meer > Viewer in apart venster.")

    def _fullscreen(self) -> None:
        window = self.viewer.window()
        window.showNormal() if window.isFullScreen() else window.showFullScreen()

    def reposition(self) -> None:
        self.move(max(0, self.viewer.width() - self.width() - 18), 14)
        self.raise_()


def install_trimble_navigation_overlay(viewer: QtWidgets.QWidget) -> TrimbleNavigationOverlay:
    existing = getattr(viewer, "_trimble_navigation_overlay", None)
    if isinstance(existing, TrimbleNavigationOverlay):
        return existing
    overlay = TrimbleNavigationOverlay(viewer, viewer)
    overlay.reposition()
    overlay.show()
    original_resize = viewer.resizeEvent

    def resize_event(event: Any) -> None:
        original_resize(event)
        overlay.reposition()

    viewer.resizeEvent = resize_event  # type: ignore[method-assign]
    viewer._trimble_navigation_overlay = overlay  # type: ignore[attr-defined]
    return overlay
