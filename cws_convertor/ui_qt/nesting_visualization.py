"""Production-oriented, printable visualizations for profile and plate plans."""

from __future__ import annotations

from math import radians, tan
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets


def _dict(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, dict) else {}


def _mm(value: Any, units_per_mm: int) -> float:
    try:
        return float(value or 0.0) / float(units_per_mm)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


class ProfileNestingVisualization(QtWidgets.QWidget):
    """Draw real bar occupancy with miter faces, common cuts and remnants."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._record: dict[str, Any] = {}
        self.setMinimumSize(900, 440)
        self.setAutoFillBackground(True)

    def set_record(self, record: dict[str, Any] | None) -> None:
        self._record = _dict(record)
        bars = list(_dict(self._record.get("plan")).get("bars") or [])
        self.setMinimumHeight(max(440, 118 * len(bars) + 80))
        self.update()

    @staticmethod
    def _angle(piece: dict[str, Any], end: str) -> float:
        direct = piece.get(f"{end}_angle_deg")
        if direct is not None:
            return float(direct or 0.0)
        cut = _dict(piece.get(f"{end}_cut"))
        return float(cut.get("primary_angle_deg") or 0.0)

    @staticmethod
    def _section_name(piece: dict[str, Any], lines: dict[str, dict[str, Any]]) -> str:
        line = lines.get(str(piece.get("demand_line_id") or ""), {})
        return str(line.get("profile_name") or line.get("profile_id") or piece.get("profile") or "Profiel")

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#f5f8fb"))
        painter.setPen(QtGui.QColor("#16324f"))
        painter.setFont(QtGui.QFont("Aptos", 13, QtGui.QFont.Weight.DemiBold))
        painter.drawText(24, 32, "Profieloptimalisatie - zaagbeeld en materiaalbenutting")
        snapshot = _dict(self._record.get("input_snapshot"))
        units = int(_dict(snapshot.get("units")).get("units_per_mm") or 1000)
        lines = {str(_dict(item).get("demand_line_id") or ""): _dict(item) for item in list(snapshot.get("demand_lines") or [])}
        bars = [_dict(item) for item in list(_dict(self._record.get("plan")).get("bars") or [])]
        if not bars:
            painter.setFont(QtGui.QFont("Aptos", 11))
            painter.drawText(24, 70, "Selecteer of bereken een nestingrun om de handelslengtes te tonen.")
            painter.end()
            return
        width = max(200.0, self.width() - 240.0)
        top = 70.0
        palette = ("#1c87a6", "#4a9c57", "#d09a2d", "#5770b5", "#a95872", "#2c9284")
        for bar_index, bar in enumerate(bars):
            stock = _mm(bar.get("stock_length_units") or bar.get("stock_length_mm"), units) if bar.get("stock_length_units") is not None else float(bar.get("stock_length_mm") or 0.0)
            y = top + bar_index * 112.0
            x0 = 172.0
            scale = width / max(stock, 1.0)
            painter.setPen(QtGui.QPen(QtGui.QColor("#20384d"), 1.3))
            painter.setBrush(QtGui.QColor("#dfe8ef"))
            painter.drawRoundedRect(QtCore.QRectF(x0, y + 24, width, 46), 3, 3)
            painter.setFont(QtGui.QFont("Aptos", 9, QtGui.QFont.Weight.DemiBold))
            painter.drawText(20, int(y + 40), str(bar.get("bar_id") or f"Staaf {bar_index + 1}"))
            painter.setFont(QtGui.QFont("Aptos", 8))
            painter.drawText(20, int(y + 58), f"{stock:,.0f} mm".replace(",", "."))
            pieces = [_dict(item) for item in list(bar.get("placements") or bar.get("pieces") or [])]
            cursor = _mm(bar.get("head_trim_units"), units)
            for piece_index, piece in enumerate(pieces):
                start = _mm(piece.get("start_units"), units) if piece.get("start_units") is not None else cursor
                length = _mm(piece.get("length_units") or piece.get("nominal_length_units"), units)
                if length <= 0.0:
                    end = _mm(piece.get("end_units"), units)
                    length = max(0.0, end - start)
                end = start + length
                left = x0 + start * scale
                right = x0 + end * scale
                start_angle = self._angle(piece, "start")
                end_angle = self._angle(piece, "end")
                h = 42.0
                left_shift = max(-h * 0.75, min(h * 0.75, tan(radians(start_angle)) * h * 0.45))
                right_shift = max(-h * 0.75, min(h * 0.75, tan(radians(end_angle)) * h * 0.45))
                polygon = QtGui.QPolygonF((QtCore.QPointF(left + left_shift, y + 26), QtCore.QPointF(right + right_shift, y + 26), QtCore.QPointF(right - right_shift, y + 68), QtCore.QPointF(left - left_shift, y + 68)))
                color = QtGui.QColor(palette[piece_index % len(palette)])
                painter.setBrush(color)
                painter.setPen(QtGui.QPen(QtGui.QColor("#102b3f"), 1.25))
                painter.drawPolygon(polygon)
                if piece.get("common_cut_with_previous") or piece.get("common_cut"):
                    painter.setPen(QtGui.QPen(QtGui.QColor("#ffd400"), 3.0))
                    painter.drawLine(QtCore.QPointF(left + left_shift, y + 25), QtCore.QPointF(left - left_shift, y + 69))
                label = str(piece.get("part_position") or piece.get("instance_id") or piece.get("piece_id") or piece_index + 1)
                painter.setPen(QtGui.QColor("white"))
                painter.setFont(QtGui.QFont("Aptos", 8, QtGui.QFont.Weight.DemiBold))
                if right - left > 40:
                    painter.drawText(QtCore.QRectF(left + 3, y + 34, max(1.0, right - left - 6), 18), QtCore.Qt.AlignmentFlag.AlignCenter, label)
                painter.setPen(QtGui.QColor("#405b72"))
                painter.setFont(QtGui.QFont("Aptos", 7))
                painter.drawText(QtCore.QRectF(left, y + 73, max(46.0, right - left), 16), f"{length:.0f} | {start_angle:g}/{end_angle:g}")
                cursor = end
            reusable = _mm(bar.get("reusable_remnant_units"), units)
            waste = _mm(bar.get("waste_units"), units)
            painter.setPen(QtGui.QColor("#35556e"))
            painter.drawText(int(x0), int(y + 103), f"Reststuk: {reusable:.0f} mm   Afval: {waste:.0f} mm")
        painter.end()


class PlateNestingVisualization(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._plan: dict[str, Any] = {}
        self.setMinimumSize(760, 420)

    def set_plan(self, plan: dict[str, Any] | None) -> None:
        self._plan = _dict(plan)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#f7f9fb"))
        painter.setPen(QtGui.QColor("#16324f"))
        painter.setFont(QtGui.QFont("Aptos", 12, QtGui.QFont.Weight.DemiBold))
        painter.drawText(20, 30, "Plaatnesting - contouren, gaten en restplaat")
        layouts = [_dict(item) for item in list(self._plan.get("layouts") or [])]
        if not layouts:
            painter.setFont(QtGui.QFont("Aptos", 10))
            painter.drawText(20, 62, "Nog geen plaatnestingrun beschikbaar.")
            painter.end()
            return
        layout = layouts[0]
        width = float(layout.get("width_mm") or 1.0)
        height = float(layout.get("height_mm") or 1.0)
        area = QtCore.QRectF(50, 58, max(10.0, self.width() - 100.0), max(10.0, self.height() - 95.0))
        scale = min(area.width() / width, area.height() / height)
        stock = QtCore.QRectF(area.left(), area.top(), width * scale, height * scale)
        painter.setBrush(QtGui.QColor("#dce6ee"))
        painter.setPen(QtGui.QPen(QtGui.QColor("#233f55"), 2))
        painter.drawRect(stock)
        colors = ("#2d8da8", "#4a9c57", "#d09a2d", "#6a77b8")
        for index, raw in enumerate(list(layout.get("placements") or [])):
            item = _dict(raw)
            rect = QtCore.QRectF(stock.left() + float(item.get("x_mm") or 0.0) * scale, stock.top() + float(item.get("y_mm") or 0.0) * scale, float(item.get("width_mm") or 0.0) * scale, float(item.get("height_mm") or 0.0) * scale)
            painter.setBrush(QtGui.QColor(colors[index % len(colors)]))
            painter.setPen(QtGui.QPen(QtGui.QColor("#102b3f"), 1))
            painter.drawRect(rect)
            painter.setPen(QtGui.QColor("white"))
            painter.drawText(rect.adjusted(3, 3, -3, -3), QtCore.Qt.AlignmentFlag.AlignCenter, str(item.get("part_id") or item.get("instance_id") or index + 1))
        painter.end()


__all__ = ["PlateNestingVisualization", "ProfileNestingVisualization"]

