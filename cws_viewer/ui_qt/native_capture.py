"""Qt capture helper that composites native QVTK framebuffers deterministically."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.contracts.state import ScreenshotOptions
from cws_viewer.ui_qt.qt_compat import require_qt


def capture_window_with_native_renderers(window: Any, output_path: str | Path | None = None):
    """Capture a Qt window including native-child VTK content and Qt overlays."""
    QtCore, QtGui, QtWidgets = require_qt()
    pixmap = window.grab()
    painter = QtGui.QPainter(pixmap)
    try:
        for widget in window.findChildren(QtWidgets.QWidget):
            controller = getattr(widget, "controller", None)
            get_render_window = getattr(widget, "GetRenderWindow", None)
            if not widget.isVisible() or not callable(get_render_window) or controller is None:
                continue
            try:
                raw = controller.screenshot(
                    ScreenshotOptions(
                        width=max(1, widget.width()),
                        height=max(1, widget.height()),
                        include_overlays=False,
                        format="png",
                    )
                )
                image = QtGui.QImage.fromData(raw, "PNG")
                if image.isNull():
                    continue
                origin = widget.mapTo(window, QtCore.QPoint(0, 0))
                painter.drawImage(QtCore.QRect(origin, widget.size()), image)
                # QVTK is native, while review/navigation overlays are regular
                # Qt children. Repaint those after the framebuffer composition.
                overlays = (
                    getattr(widget, "_phase2_markup_overlay", None),
                    getattr(widget, "_trimble_navigation_overlay", None),
                )
                for overlay in overlays:
                    if overlay is None or not overlay.isVisible():
                        continue
                    overlay_origin = overlay.mapTo(window, QtCore.QPoint(0, 0))
                    painter.drawPixmap(overlay_origin, overlay.grab())
            except Exception:
                # Non-loaded viewer placeholders remain represented by the
                # ordinary Qt capture; a loaded native scene is never blanked.
                continue
    finally:
        painter.end()
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not pixmap.save(str(target), "PNG"):
            raise RuntimeError(f"Qt/VTK screenshot could not be saved: {target}")
    return pixmap


__all__ = ["capture_window_with_native_renderers"]
