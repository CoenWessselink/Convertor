"""Qt timer adapter; the QVTK native context remains owned by its widget."""
from __future__ import annotations

from typing import Any
from cws_viewer.performance.render_scheduler import DirtyFlag, RenderScheduler
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, _QtGui, _QtWidgets = require_qt()

    class QtRenderScheduler(QtCore.QObject):
        def __init__(self, viewport: Any) -> None:
            super().__init__(viewport)
            self.viewport = viewport
            self._callback: Any = None
            self._timer = QtCore.QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)
            self._timer.timeout.connect(self._dispatch)
            self.scheduler = RenderScheduler(
                viewport.backend.render_now, self._arm,
                profiler=viewport.backend.profiler,
            )

        def _arm(self, milliseconds: int, callback: Any) -> None:
            self._callback = callback
            self._timer.start(milliseconds)

        def _dispatch(self) -> None:
            callback, self._callback = self._callback, None
            if callback is not None:
                try:
                    callback()
                except Exception as exc:
                    self.viewport.backend_failed.emit(f"{type(exc).__name__}: {exc}")

        def request(self, dirty: DirtyFlag = DirtyFlag.OVERLAY) -> None:
            self.scheduler.request(dirty)

        def flush(self) -> None:
            self._timer.stop()
            self._callback = None
            self.scheduler.flush()

        def close(self) -> None:
            self._timer.stop()
            self._callback = None
            self.scheduler.close()
else:
    class QtRenderScheduler:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()
