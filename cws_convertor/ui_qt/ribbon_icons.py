"""Self-contained blue line icons for the CWS product ribbon."""
from __future__ import annotations

from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, _QtWidgets = require_qt()

    def ribbon_icon(action: str, title: str = "") -> Any:
        key = f"{action} {title}".lower()
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        pen = QtGui.QPen(QtGui.QColor("#075fce"), 1.8)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        def line(*values: float) -> None:
            points = [QtCore.QPointF(values[i], values[i + 1]) for i in range(0, len(values), 2)]
            painter.drawPolyline(QtGui.QPolygonF(points))

        def rect(x: float, y: float, width: float, height: float) -> None:
            painter.drawRoundedRect(QtCore.QRectF(x, y, width, height), 1.5, 1.5)

        def circle(x: float, y: float, radius: float) -> None:
            painter.drawEllipse(QtCore.QPointF(x, y), radius, radius)

        if any(token in key for token in ("zoeken", "search")):
            circle(13, 13, 6.5); line(18, 18, 25, 25)
        elif any(token in key for token in ("wissen", "clear", "verwijder", "annuleer")):
            circle(16, 16, 10); line(11, 11, 21, 21); line(21, 11, 11, 21)
        elif any(token in key for token in ("opslaan", "save")):
            rect(7, 5, 18, 22); rect(11, 5, 10, 7); rect(11, 18, 10, 7)
        elif any(token in key for token in ("export", "pdf genereren")):
            rect(6, 15, 20, 11); line(16, 21, 16, 5); line(11, 10, 16, 5, 21, 10)
        elif any(token in key for token in ("instelling", "settings")):
            circle(16, 16, 5); circle(16, 16, 11)
            for values in ((16,2,16,6),(16,26,16,30),(2,16,6,16),(26,16,30,16),(6,6,9,9),(23,23,26,26),(26,6,23,9),(9,23,6,26)):
                line(*values)
        elif any(token in key for token in ("select", "bewerk modus")):
            path = QtGui.QPainterPath(QtCore.QPointF(8, 5))
            path.lineTo(23, 16); path.lineTo(16.5, 17.5); path.lineTo(20, 25)
            path.lineTo(16, 27); path.lineTo(12.5, 19); path.lineTo(8, 23)
            path.closeSubpath(); painter.drawPath(path)
        elif any(token in key for token in ("isol", "spook", "ghost", "weergave", "aanzicht")):
            line(7, 10, 16, 5, 25, 10, 16, 15, 7, 10, 7, 21, 16, 27, 25, 21, 25, 10)
            line(16, 15, 16, 27); line(7, 21, 16, 15, 25, 21)
        elif any(token in key for token in ("transparant", "raster", "grid", "tabel", "kolom")):
            rect(6, 6, 20, 20); line(12.5, 6, 12.5, 26); line(19.5, 6, 19.5, 26)
            line(6, 12.5, 26, 12.5); line(6, 19.5, 26, 19.5)
        elif any(token in key for token in ("verbergen", "zichtbaar", "show_all")):
            path = QtGui.QPainterPath(QtCore.QPointF(4, 16))
            path.cubicTo(9, 8, 23, 8, 28, 16); path.cubicTo(23, 24, 9, 24, 4, 16)
            painter.drawPath(path); circle(16, 16, 4); line(6, 27, 27, 6)
        elif any(token in key for token in ("meten", "maatvoering", "schaal")):
            line(6, 24, 25, 5); line(5, 20, 10, 25); line(21, 4, 27, 10)
            line(11, 17, 14, 20); line(16, 12, 19, 15)
        elif any(token in key for token in ("boren", "gaten")):
            circle(16, 16, 10); circle(16, 16, 4); line(16, 3, 16, 8); line(16, 24, 16, 29)
        elif any(token in key for token in ("scribe", "markering", "lijnen", "tekst")):
            line(7, 24, 10, 17, 23, 4, 28, 9, 15, 22, 7, 24); line(10, 17, 15, 22)
        elif any(token in key for token in ("snappen", "snap", "assen")):
            circle(16, 16, 7); line(16, 3, 16, 29); line(3, 16, 29, 16); circle(16, 16, 2)
        elif any(token in key for token in ("doorsnede", "clip")):
            rect(6, 7, 20, 18); line(16, 4, 16, 28); line(12, 9, 12, 23); line(20, 9, 20, 23)
        elif any(token in key for token in ("valid", "control", "herken")):
            circle(16, 16, 11); line(10, 16, 14, 20, 23, 10)
        elif any(token in key for token in ("converter", "converteren", "vernieuw", "reset", "automatisch")):
            path = QtGui.QPainterPath(QtCore.QPointF(24, 11)); path.cubicTo(20, 4, 9, 5, 7, 14)
            painter.drawPath(path); line(20, 7, 24, 11, 27, 6)
            path = QtGui.QPainterPath(QtCore.QPointF(8, 21)); path.cubicTo(13, 28, 24, 26, 25, 17)
            painter.drawPath(path); line(12, 25, 8, 21, 5, 26)
        elif any(token in key for token in ("toevoegen", "nieuw", "add")):
            circle(16, 16, 11); line(16, 10, 16, 22); line(10, 16, 22, 16)
        elif any(token in key for token in ("omhoog", "up")):
            line(8, 17, 16, 9, 24, 17); line(16, 9, 16, 27)
        elif any(token in key for token in ("omlaag", "down")):
            line(8, 15, 16, 23, 24, 15); line(16, 5, 16, 23)
        elif any(token in key for token in ("duplic", "kopie")):
            rect(6, 8, 15, 17); rect(11, 5, 15, 17)
        elif any(token in key for token in ("filter", "groeper")):
            line(5, 7, 27, 7, 19, 16, 19, 25, 13, 27, 13, 16, 5, 7)
        elif any(token in key for token in ("sort", "a-z")):
            line(8, 7, 8, 25); line(4, 21, 8, 25, 12, 21)
            painter.drawText(QtCore.QRectF(14, 4, 14, 12), "A"); painter.drawText(QtCore.QRectF(14, 17, 14, 12), "Z")
        elif any(token in key for token in ("meer", "acties")):
            circle(8, 16, 1.5); circle(16, 16, 1.5); circle(24, 16, 1.5)
        elif any(token in key for token in ("bestand", "import", "open", "template", "rapport", "log", "tekening")):
            path = QtGui.QPainterPath(QtCore.QPointF(8, 4))
            path.lineTo(20, 4); path.lineTo(26, 10); path.lineTo(26, 28); path.lineTo(8, 28); path.closeSubpath()
            painter.drawPath(path); line(20, 4, 20, 10, 26, 10); line(12, 16, 22, 16); line(12, 21, 22, 21)
        else:
            circle(16, 16, 10); line(16, 10, 16, 18); circle(16, 23, 1)

        painter.end()
        return QtGui.QIcon(pixmap)


else:
    def ribbon_icon(action: str, title: str = "") -> Any:  # pragma: no cover
        del action, title
        return None


__all__ = ["ribbon_icon"]
