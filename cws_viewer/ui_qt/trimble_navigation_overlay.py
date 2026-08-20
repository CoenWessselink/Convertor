from __future__ import annotations

from typing import Any, Callable

from PySide6 import QtCore, QtGui, QtWidgets


class TrimbleNavigationOverlay(QtWidgets.QWidget):
    """Compact icon-only navigation overlay for the integrated V15 viewer."""

    def __init__(self, viewer: QtWidgets.QWidget, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent or viewer)
        self.viewer = viewer
        self.controller = getattr(viewer, "controller", None)
        self.setObjectName("trimbleNavigationOverlay")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "#trimbleNavigationOverlay { background: transparent; }"
            "QToolButton { background: rgba(255,255,255,242); border: 1px solid #aeb8c4;"
            " border-radius: 2px; padding: 4px; color: #172b45; }"
            "QToolButton:hover { background: #eef6ff; border-color: #1676d2; }"
            "QToolButton:checked { background: #0063a8; color: white; border-color: #00518a; }"
        )
        self.setFixedSize(206, 224)
        self._build()

    def _button(
        self,
        tooltip: str,
        icon: QtWidgets.QStyle.StandardPixmap,
        callback: Callable[[], None],
        *,
        checkable: bool = False,
        size: int = 32,
    ) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton(self)
        button.setIcon(self.style().standardIcon(icon))
        button.setIconSize(QtCore.QSize(18, 18))
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setCheckable(checkable)
        button.setFixedSize(size, size)
        button.clicked.connect(callback)
        return button

    def _build(self) -> None:
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(1)
        top.addWidget(self._button("Alles passend in beeld", QtWidgets.QStyle.SP_DialogResetButton, self._fit))
        top.addWidget(self._button("Panmodus", QtWidgets.QStyle.SP_ArrowUp, lambda: self._mode("pan"), checkable=True))
        top.addWidget(self._button("Loopmodus", QtWidgets.QStyle.SP_ArrowForward, lambda: self._mode("walk"), checkable=True))
        top.addWidget(self._button("Orbitmodus", QtWidgets.QStyle.SP_BrowserReload, lambda: self._mode("orbit"), checkable=True))
        top.addWidget(self._button("Viewer in apart venster", QtWidgets.QStyle.SP_TitleBarNormalButton, self._open_detached))
        top.addWidget(self._button("Volledig scherm", QtWidgets.QStyle.SP_TitleBarMaxButton, self._fullscreen))
        self._mode_buttons = [top.itemAt(index).widget() for index in (1, 2, 3)]
        self._mode_buttons[2].setChecked(True)

        pad = QtWidgets.QGridLayout()
        pad.setHorizontalSpacing(1)
        pad.setVerticalSpacing(1)
        pad.addWidget(self._button("Omhoog", QtWidgets.QStyle.SP_ArrowUp, lambda: self._orbit(0, 8)), 0, 1)
        pad.addWidget(self._button("Links", QtWidgets.QStyle.SP_ArrowLeft, lambda: self._orbit(-8, 0)), 1, 0)
        pad.addWidget(self._button("Orientatie herstellen", QtWidgets.QStyle.SP_BrowserReload, self._fit), 1, 1)
        pad.addWidget(self._button("Rechts", QtWidgets.QStyle.SP_ArrowRight, lambda: self._orbit(8, 0)), 1, 2)
        pad.addWidget(self._button("Omlaag", QtWidgets.QStyle.SP_ArrowDown, lambda: self._orbit(0, -8)), 2, 1)

        zoom = QtWidgets.QVBoxLayout()
        zoom.setSpacing(1)
        zoom.addWidget(self._button("Inzoomen", QtWidgets.QStyle.SP_ArrowUp, lambda: self._zoom(1.18), size=34))
        zoom.addWidget(self._button("Uitzoomen", QtWidgets.QStyle.SP_ArrowDown, lambda: self._zoom(1.0 / 1.18), size=34))

        navigation = QtWidgets.QHBoxLayout()
        navigation.addLayout(pad)
        navigation.addStretch(1)
        navigation.addLayout(zoom)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(8)
        layout.addLayout(top)
        layout.addLayout(navigation)
        layout.addStretch(1)

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
        for button in self._mode_buttons:
            button.setChecked(False)
        self._mode_buttons[{"pan": 0, "walk": 1, "orbit": 2}[mode]].setChecked(True)
        if self.controller is not None:
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
