"""Phase 2 review-markup overlay for the CWS VTK project viewer.

The overlay is deliberately Qt/display-only review state. World-space markup
points are projected through the active CWS renderer on every repaint, so the
markup follows orbit/pan/zoom without becoming canonical/manufacturing geometry.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from cws_viewer.math3d import Vector3
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class ReviewMarkupOverlay(QtWidgets.QWidget):
        def __init__(self, viewer: Any) -> None:
            super().__init__(viewer)
            self.viewer = viewer
            self._records: tuple[Any, ...] = ()
            self._preview_kind = ""
            self._preview_points: tuple[tuple[float, float, float], ...] = ()
            self._preview_text = ""
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setGeometry(viewer.rect())
            self.show()
            self.raise_()

        def set_records(self, records: Iterable[Any]) -> None:
            self._records = tuple(records)
            self.update()

        def set_preview(
            self,
            kind: str = "",
            points: Iterable[tuple[float, float, float]] = (),
            *,
            text: str = "",
        ) -> None:
            self._preview_kind = str(kind or "")
            self._preview_points = tuple(
                (float(point[0]), float(point[1]), float(point[2])) for point in points
            )
            self._preview_text = str(text or "")
            self.update()

        def clear_preview(self) -> None:
            self.set_preview()

        def _screen(self, raw: tuple[float, float, float]) -> Any | None:
            try:
                x, y, _z = self.viewer.backend.world_to_display(Vector3(*raw))
                return QtCore.QPointF(float(x), float(self.viewer.height()) - float(y) - 1.0)
            except Exception:
                return None

        @staticmethod
        def _polyline_path(points: tuple[Any, ...], *, close: bool = False) -> Any:
            path = QtGui.QPainterPath()
            if not points:
                return path
            path.moveTo(points[0])
            for point in points[1:]:
                path.lineTo(point)
            if close and len(points) >= 3:
                path.closeSubpath()
            return path

        @staticmethod
        def _draw_arrow_head(painter: Any, first: Any, second: Any, color: Any) -> None:
            dx = float(second.x() - first.x())
            dy = float(second.y() - first.y())
            length = math.hypot(dx, dy)
            if length <= 1e-6:
                return
            ux, uy = dx / length, dy / length
            size = max(8.0, min(16.0, length * 0.18))
            bx, by = second.x() - ux * size, second.y() - uy * size
            px, py = -uy * size * 0.42, ux * size * 0.42
            polygon = QtGui.QPolygonF(
                [
                    QtCore.QPointF(second.x(), second.y()),
                    QtCore.QPointF(bx + px, by + py),
                    QtCore.QPointF(bx - px, by - py),
                ]
            )
            painter.setBrush(color)
            painter.drawPolygon(polygon)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        def _draw_text_label(self, painter: Any, point: Any, text: str, color: Any) -> None:
            label = str(text or "").strip()
            if not label:
                return
            font = painter.font()
            font.setPointSizeF(max(9.0, font.pointSizeF()))
            font.setBold(True)
            painter.setFont(font)
            metrics = QtGui.QFontMetricsF(font)
            bounds = metrics.boundingRect(label).adjusted(-6.0, -4.0, 6.0, 4.0)
            bounds.moveTopLeft(QtCore.QPointF(point.x() + 8.0, point.y() - bounds.height() - 5.0))
            painter.setPen(QtGui.QPen(QtGui.QColor("#c9d3df"), 1.0))
            painter.setBrush(QtGui.QColor(255, 255, 255, 226))
            painter.drawRoundedRect(bounds, 4.0, 4.0)
            painter.setPen(QtGui.QPen(color, 1.0))
            painter.drawText(bounds, QtCore.Qt.AlignmentFlag.AlignCenter, label)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        def _draw_record(
            self,
            painter: Any,
            kind: str,
            raw_points: tuple[tuple[float, float, float], ...],
            *,
            color_text: str,
            width: float,
            text: str = "",
            preview: bool = False,
        ) -> None:
            points = tuple(point for point in (self._screen(raw) for raw in raw_points) if point is not None)
            if not points:
                return
            color = QtGui.QColor(str(color_text or "#0b5bd3"))
            if not color.isValid():
                color = QtGui.QColor("#0b5bd3")
            pen = QtGui.QPen(color, max(1.0, float(width)))
            pen.setCosmetic(True)
            if preview:
                pen.setStyle(QtCore.Qt.PenStyle.DashLine)
                color.setAlpha(190)
                pen.setColor(color)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

            value = str(kind or "").casefold()
            if value == "text":
                painter.setBrush(color)
                painter.drawEllipse(points[0], 3.5, 3.5)
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                self._draw_text_label(painter, points[0], text, color)
                return

            close = value == "cloud"
            if len(points) >= 2:
                painter.drawPath(self._polyline_path(points, close=close))
            else:
                painter.drawEllipse(points[0], 3.0, 3.0)

            if value == "arrow" and len(points) >= 2:
                self._draw_arrow_head(painter, points[-2], points[-1], color)
            if value == "cloud" and len(points) >= 3:
                # A light node rhythm makes the review cloud visibly distinct
                # without copying a third-party asset/style.
                for point in points:
                    painter.drawEllipse(point, 2.5, 2.5)
            if text and value != "text":
                self._draw_text_label(painter, points[-1], text, color)

        def paintEvent(self, event: Any) -> None:
            super().paintEvent(event)
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            for record in self._records:
                if not bool(getattr(record, "visible", True)):
                    continue
                points = tuple(tuple(float(v) for v in point) for point in getattr(record, "world_points_mm", ()) or ())
                self._draw_record(
                    painter,
                    str(getattr(record, "kind", "")),
                    points,
                    color_text=str(getattr(record, "color", "#0b5bd3")),
                    width=float(getattr(record, "line_width", 2.0)),
                    text=str(getattr(record, "text", "")),
                )
            if self._preview_kind and self._preview_points:
                self._draw_record(
                    painter,
                    self._preview_kind,
                    self._preview_points,
                    color_text="#0b5bd3",
                    width=2.0,
                    text=self._preview_text,
                    preview=True,
                )
            painter.end()

else:

    class ReviewMarkupOverlay:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["ReviewMarkupOverlay"]


# A permanently visible transparent QWidget over a native Win32 OpenGL child
# can retain pixels from the widget that previously occupied that screen area.
# Keep the review layer physically absent while it has nothing to draw and use
# a true translucent/no-background surface while markup is active.
if qt_available():
    _cws_markup_init = ReviewMarkupOverlay.__init__
    _cws_markup_set_records = ReviewMarkupOverlay.set_records
    _cws_markup_set_preview = ReviewMarkupOverlay.set_preview
    _cws_markup_clear_preview = ReviewMarkupOverlay.clear_preview

    def _cws_review_markup_init(self, viewer):
        _cws_markup_init(self, viewer)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.hide()

    def _cws_review_markup_visibility(self) -> None:
        active = bool(getattr(self, "_records", ())) or bool(getattr(self, "_preview_kind", ""))
        self.setVisible(active)
        if active:
            self.raise_()
            self.update()

    def _cws_review_markup_set_records(self, records):
        _cws_markup_set_records(self, records)
        _cws_review_markup_visibility(self)

    def _cws_review_markup_set_preview(self, kind="", points=(), *, text=""):
        _cws_markup_set_preview(self, kind, points, text=text)
        _cws_review_markup_visibility(self)

    def _cws_review_markup_clear_preview(self):
        _cws_markup_clear_preview(self)
        _cws_review_markup_visibility(self)

    ReviewMarkupOverlay.__init__ = _cws_review_markup_init
    ReviewMarkupOverlay.set_records = _cws_review_markup_set_records
    ReviewMarkupOverlay.set_preview = _cws_review_markup_set_preview
    ReviewMarkupOverlay.clear_preview = _cws_review_markup_clear_preview
