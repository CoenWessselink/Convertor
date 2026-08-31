"""Compact, non-blocking navigation controls for the embedded VTK viewer."""

from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtWidgets


class TrimbleNavigationOverlay(QtWidgets.QFrame):
    """Small viewport toolbar that never covers the model work area."""

    def __init__(self, viewer: QtWidgets.QWidget) -> None:
        super().__init__(viewer)
        self._viewer = viewer
        self._select_active = False
        self.setObjectName("trimbleNavigationOverlay")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            """
            QFrame#trimbleNavigationOverlay {
                background: rgba(250, 252, 255, 238);
                border: 1px solid #9eb4cc;
                border-radius: 4px;
            }
            QToolButton {
                min-width: 28px;
                min-height: 26px;
                padding: 2px 5px;
                color: #093f79;
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                font-weight: 600;
            }
            QToolButton:hover { background: #e5f1ff; border-color: #9cc8f5; }
            QToolButton:checked { color: white; background: #0875d1; border-color: #075fa8; }
            QSlider::groove:horizontal { height: 4px; background: #c6d5e5; border-radius: 2px; }
            QSlider::handle:horizontal {
                width: 12px; margin: -5px 0; border-radius: 6px;
                background: #0875d1; border: 1px solid #075fa8;
            }
            QLabel { color: #24445f; font-size: 10px; }
            """
        )

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(3)

        self.select_button = self._button("Select", "Onderdeel selecteren", checkable=True)
        self.orbit_button = self._button("Orbit", "Draaien om de positie onder de muis", checkable=True)
        self.pan_button = self._button("Slepen", "Model slepen", checkable=True)
        self.fit_button = self._button("Fit", "Volledig model passend weergeven")
        self.area_button = self._button("Zoom", "Zoomvenster", checkable=True)

        self._mode_group = QtWidgets.QButtonGroup(self)
        self._mode_group.setExclusive(True)
        for button in (self.select_button, self.orbit_button, self.pan_button):
            self._mode_group.addButton(button)

        layout.addWidget(self.select_button)
        layout.addWidget(self.orbit_button)
        layout.addWidget(self.pan_button)
        layout.addWidget(self.fit_button)
        layout.addWidget(self.area_button)

        separator = QtWidgets.QFrame(self)
        separator.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        separator.setStyleSheet("color: #b9c7d5;")
        layout.addWidget(separator)

        opacity_label = QtWidgets.QLabel("Doorzichtig")
        opacity_label.setToolTip("Doorzichtigheid van het volledige model")
        layout.addWidget(opacity_label)
        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self.opacity_slider.setObjectName("trimbleOpacitySlider")
        self.opacity_slider.setRange(15, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(86)
        self.opacity_slider.setToolTip("Modeldoorzichtigheid")
        layout.addWidget(self.opacity_slider)

        self.select_button.clicked.connect(self._activate_select)
        self.orbit_button.clicked.connect(lambda: self._activate_navigation("orbit"))
        self.pan_button.clicked.connect(lambda: self._activate_navigation("pan"))
        self.fit_button.clicked.connect(self._fit_model)
        self.area_button.toggled.connect(self._set_zoom_area)
        self.opacity_slider.valueChanged.connect(self._set_opacity)

        self.orbit_button.setChecked(True)
        self._viewer.installEventFilter(self)
        self._install_filter_on_viewport_children()
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()

    def _button(self, text: str, tooltip: str, *, checkable: bool = False) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton(self)
        object_names = {
            "Select": "trimbleNavSelect",
            "Orbit": "trimbleNavOrbit",
            "Slepen": "trimbleNavPan",
            "Fit": "trimbleNavFit",
            "Zoom": "trimbleNavZoom",
        }
        button.setObjectName(object_names[text])
        button.setText(text)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        button.setAutoRaise(False)
        return button

    def _install_filter_on_viewport_children(self) -> None:
        for child in self._viewer.findChildren(QtWidgets.QWidget):
            if child is not self and not self.isAncestorOf(child):
                child.installEventFilter(self)

    def _event_position_for_viewer(self, watched: QtCore.QObject, event: Any) -> QtCore.QPointF:
        pos = event.position()
        if watched is self._viewer or not isinstance(watched, QtWidgets.QWidget):
            return pos
        global_pos = watched.mapToGlobal(pos.toPoint())
        return QtCore.QPointF(self._viewer.mapFromGlobal(global_pos))

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        event_type = event.type()
        if watched is self._viewer and event_type in (
            QtCore.QEvent.Type.Resize,
            QtCore.QEvent.Type.Show,
        ):
            QtCore.QTimer.singleShot(0, self._reposition)
        if event_type == QtCore.QEvent.Type.ChildAdded:
            QtCore.QTimer.singleShot(0, self._install_filter_on_viewport_children)

        if (
            event_type == QtCore.QEvent.Type.MouseButtonPress
            and hasattr(event, "button")
            and event.button() == QtCore.Qt.MouseButton.LeftButton
            and watched is not self
            and not self.isAncestorOf(watched)
        ):
            pos = self._event_position_for_viewer(watched, event)
            if self._select_active:
                picker = getattr(self._viewer, "_pick", None)
                if callable(picker):
                    picker(pos, event.modifiers(), emit=True)
                    return True
            elif self.orbit_button.isChecked():
                binder = getattr(self._viewer, "_bind_orbit_pivot_from_screen", None)
                if callable(binder):
                    binder(pos)
        return super().eventFilter(watched, event)

    def _activate_select(self) -> None:
        self._select_active = True
        self._viewer.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        zoom = getattr(self._viewer, "set_zoom_area", None)
        if callable(zoom):
            zoom(False)
        self.area_button.setChecked(False)

    def _activate_navigation(self, mode: str) -> None:
        self._select_active = False
        setter = getattr(self._viewer, "set_navigation_mode", None)
        if callable(setter):
            setter(mode)
        zoom = getattr(self._viewer, "set_zoom_area", None)
        if callable(zoom):
            zoom(False)
        self.area_button.setChecked(False)

    def _set_zoom_area(self, enabled: bool) -> None:
        if enabled:
            self._select_active = False
            self._mode_group.setExclusive(False)
            self.select_button.setChecked(False)
            self.orbit_button.setChecked(False)
            self.pan_button.setChecked(False)
            self._mode_group.setExclusive(True)
        setter = getattr(self._viewer, "set_zoom_area", None)
        if callable(setter):
            setter(enabled)

    def _backend(self) -> Any:
        return getattr(self._viewer, "_backend", None) or getattr(self._viewer, "backend", None)

    def _fit_model(self) -> None:
        candidates = (
            (self._viewer, "fit_all"),
            (self._viewer, "fit_view"),
            (self._viewer, "reset_camera"),
            (self._backend(), "fit_all"),
            (self._backend(), "fit_view"),
            (self._backend(), "reset_camera"),
        )
        for owner, name in candidates:
            method = getattr(owner, name, None) if owner is not None else None
            if callable(method):
                method()
                return
        renderer = getattr(self._backend(), "_renderer", None)
        if renderer is not None:
            renderer.ResetCamera()
            renderer.ResetCameraClippingRange()
            window = renderer.GetRenderWindow()
            if window is not None:
                window.Render()

    def _set_opacity(self, percent: int) -> None:
        backend = self._backend()
        setter = getattr(backend, "set_global_opacity", None) if backend is not None else None
        if callable(setter):
            setter(float(percent) / 100.0)

    def _reposition(self) -> None:
        if not self._viewer.isVisible():
            return
        self.adjustSize()
        x = max(8, self._viewer.width() - self.width() - 12)
        y = 10
        controls = getattr(self._viewer, "_viewport_controls", None)
        if controls is not None and controls.isVisible():
            controls_rect = controls.geometry().adjusted(-6, -4, 6, 4)
            candidate = QtCore.QRect(x, y, self.width(), self.height())
            if candidate.intersects(controls_rect):
                y = controls_rect.bottom() + 8
        self.move(x, y)
        self.raise_()

    def reposition(self) -> None:
        """Reposition the overlay through the stable host-widget API."""
        self._reposition()


def install_trimble_navigation_overlay(viewer: QtWidgets.QWidget) -> TrimbleNavigationOverlay:
    """Install one compact overlay per viewer and return it."""

    existing = getattr(viewer, "_trimble_navigation_overlay", None)
    if isinstance(existing, TrimbleNavigationOverlay):
        existing.show()
        existing.raise_()
        existing._reposition()
        return existing
    overlay = TrimbleNavigationOverlay(viewer)
    setattr(viewer, "_trimble_navigation_overlay", overlay)
    return overlay
