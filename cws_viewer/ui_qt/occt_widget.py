"""PySide6 native-window host for :class:`OcctAisSpikeBackend`."""
from __future__ import annotations

from typing import Any

from cws_viewer.backends.occt_ais import OcctAisSpikeBackend
from cws_viewer.technology.contracts import NativeWindow, TechnologyScene
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class OcctAisWidget(QtWidgets.QWidget):  # type: ignore[misc]
        """Thin Qt host; all rendering remains in the backend."""

        backend_ready = QtCore.Signal()
        backend_failed = QtCore.Signal(str)
        node_picked = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsOcctAisWidget")
            self.setMinimumSize(320, 240)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow, True)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_PaintOnScreen, True)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
            self.setMouseTracking(True)
            self._backend = OcctAisSpikeBackend()
            self._initialized = False
            self._pending_scene: TechnologyScene | None = None

        @property
        def backend(self) -> OcctAisSpikeBackend:
            return self._backend

        def paintEngine(self) -> None:  # Qt must not create a QPainter OpenGL surface
            return None

        def _ensure_initialized(self) -> None:
            if self._initialized or not self.isVisible():
                return
            try:
                handle = int(self.winId())
                width = max(1, self.width())
                height = max(1, self.height())
                self._backend.initialize(
                    width=width,
                    height=height,
                    native_window=NativeWindow(handle, width, height),
                )
                self._initialized = True
                if self._pending_scene is not None:
                    scene = self._pending_scene
                    self._pending_scene = None
                    self.load_scene(scene)
                self.backend_ready.emit()
            except Exception as exc:
                self.backend_failed.emit(f"{type(exc).__name__}: {exc}")
                raise

        def showEvent(self, event: Any) -> None:
            super().showEvent(event)
            QtCore.QTimer.singleShot(0, self._ensure_initialized)

        def paintEvent(self, event: Any) -> None:
            if self._initialized:
                self._backend.render()
            event.accept()

        def resizeEvent(self, event: Any) -> None:
            super().resizeEvent(event)
            if self._initialized:
                size = event.size()
                self._backend.resize(size.width(), size.height())
                self._backend.render()

        def mousePressEvent(self, event: Any) -> None:
            if self._initialized and event.button() == QtCore.Qt.MouseButton.LeftButton:
                point = event.position()
                picked = self._backend.pick_at(int(point.x()), int(point.y()))
                if picked:
                    self.node_picked.emit(picked)
            super().mousePressEvent(event)

        def load_scene(self, scene: TechnologyScene) -> None:
            if not self._initialized:
                self._pending_scene = scene
                self._ensure_initialized()
                return
            self._backend.load_scene(scene)
            self._backend.set_isometric_view()
            self._backend.fit_all()
            self._backend.render()

        def closeEvent(self, event: Any) -> None:
            self._backend.dispose()
            self._initialized = False
            super().closeEvent(event)

else:

    class OcctAisWidget:  # pragma: no cover - simple dependency guard
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["OcctAisWidget"]
