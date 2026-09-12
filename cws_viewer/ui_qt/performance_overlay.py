"""Opt-in developer diagnostics over the existing integrated VTK viewport."""
from __future__ import annotations

import os
from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class ViewerPerformanceOverlay(QtWidgets.QLabel):
        def __init__(self, viewport: Any) -> None:
            super().__init__(viewport)
            self.viewport = viewport
            self.setObjectName("cwsViewerPerformanceOverlay")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.setStyleSheet("QLabel { background: rgba(18,24,32,230); color: #f3f5f7; "
                               "border: 1px solid #75869a; border-radius: 4px; "
                               "padding: 9px; font-family: monospace; font-size: 11px; }")
            self._timer = QtCore.QTimer(self)
            self._timer.setInterval(500)
            self._timer.timeout.connect(self.refresh)
            self._shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+F12"), viewport)
            self._shortcut.activated.connect(lambda: self.set_enabled(not self.isVisible()))
            self.set_enabled(os.environ.get("CWS_VIEWER_PERF_OVERLAY", "") == "1")

        def set_enabled(self, enabled: bool) -> None:
            self.setVisible(bool(enabled))
            if enabled:
                self.refresh()
                self._timer.start()
            else:
                self._timer.stop()

        @staticmethod
        def _time(stages: dict[str, Any], name: str) -> str:
            value = stages.get(name, {}).get("p95_ms")
            return "niet gemeten" if value is None else f"{float(value):.1f} ms"

        def refresh(self) -> None:
            snapshot = self.viewport.backend.performance_snapshot()
            stages, gauges, counters = snapshot["stages"], snapshot["gauges"], snapshot["counters"]
            cache = gauges.get("shared_cache", {})
            hits, misses = cache.get("hits", 0), cache.get("misses", 0)
            hit_rate = "n.v.t." if not hits + misses else f"{100 * hits / (hits + misses):.0f}%"
            try:
                import psutil
                ram = f"{psutil.Process().memory_info().rss / (1024 ** 3):.2f} GB"
            except ImportError:
                ram = "niet gemeten"
            self.setText(
                f"CWS Viewer | performance (Ctrl+Shift+F12)\n"
                f"Renders laatste seconde  {snapshot['actual_renders_last_second']}\n"
                f"Frame p95                {self._time(stages, 'render')}\n"
                f"Input → render-einde p95 {self._time(stages, 'input_to_render_end_oldest')}\n"
                f"Selectie p95             {self._time(stages, 'selection')}\n"
                f"Zichtbaar                {gauges.get('visible_objects', 0)} / {gauges.get('physical_objects', 0)}\n"
                f"Basis / selectie actors  {gauges.get('base_actor_count', 0)} / {gauges.get('selection_actor_count', 0)}\n"
                f"Render requests / echt   {counters.get('render_requests', 0)} / {counters.get('actual_renders', 0)}\n"
                f"Input ontvangen / samen  {counters.get('input_received', 0)} / {counters.get('input_coalesced', 0)}\n"
                f"Gedeelde RAM-cache hit   {hit_rate}\n"
                f"RAM                      {ram}\n"
                "GPU-tijd / fysiek beeld: niet gemeten"
            )
            self.adjustSize()
            self.move(max(12, self.viewport.width() - self.width() - 12), 58)
            self.raise_()
else:
    class ViewerPerformanceOverlay:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()
