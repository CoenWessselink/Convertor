"""Qt input surface for the persistent drawing dimension editor."""
from __future__ import annotations

import math
from typing import Any, Iterable

from cws_convertor.drawings.interactive import SnapCandidate, nearest_snap_candidate
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class InteractiveDrawingCanvas(QtWidgets.QWidget):
        sheet_clicked = QtCore.Signal(object, object, object)
        pointer_moved = QtCore.Signal(object, object)
        command_requested = QtCore.Signal(str)
        dimension_dragged = QtCore.Signal(str, object, bool)
        area_selected = QtCore.Signal(object, object, object)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("interactiveDrawingCanvas")
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
            self.setMouseTracking(True)
            self.setMinimumHeight(500)
            self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
            self._pixmap = QtGui.QPixmap()
            self._document = None
            self._candidates: list[SnapCandidate] = []
            self._hover_candidates: list[SnapCandidate] = []
            self._hover_index = 0
            self._draft_points: list[tuple[float, float]] = []
            self._pointer_sheet: tuple[float, float] | None = None
            self._selected_ids: set[str] = set()
            self._zoom = 1.0
            self._pan = QtCore.QPointF(0.0, 0.0)
            self._panning = False
            self._last_mouse = QtCore.QPointF()
            self._drag_dimension_id = ""
            self._drag_origin_sheet: tuple[float, float] | None = None
            self._drag_current_sheet: tuple[float, float] | None = None
            self._drag_text_only = False
            self._selection_enabled = True
            self._selection_origin_sheet: tuple[float, float] | None = None
            self._selection_current_sheet: tuple[float, float] | None = None
            self._selection_modifiers = QtCore.Qt.KeyboardModifier.NoModifier
            self._placeholder = "Selecteer een onderdeel en vernieuw het voorbeeld"
            self._page_index = 0

        @property
        def current_candidate(self) -> SnapCandidate | None:
            if not self._hover_candidates:
                return None
            return self._hover_candidates[self._hover_index % len(self._hover_candidates)]

        def set_drawing(self, pixmap: Any, document: Any, candidates: Iterable[SnapCandidate]) -> None:
            self._pixmap = QtGui.QPixmap(pixmap)
            self._document = document
            page_count = len(getattr(document, "pages", ()) or ())
            self._page_index = min(self._page_index, max(0, page_count - 1))
            self._candidates = list(candidates)
            self._hover_candidates.clear()
            self._hover_index = 0
            self.update()

        def set_active_page(self, page_index: int) -> None:
            page_count = len(getattr(self._document, "pages", ()) or ())
            self._page_index = min(max(0, int(page_index)), max(0, page_count - 1))
            self._hover_candidates.clear()
            self._hover_index = 0
            self.update()

        def setText(self, value: str) -> None:
            self._placeholder = str(value)
            if self._pixmap.isNull():
                self.update()

        def set_candidates(self, candidates: Iterable[SnapCandidate]) -> None:
            self._candidates = list(candidates)
            self._hover_candidates.clear()
            self._hover_index = 0
            self.update()

        def set_draft(self, points: Iterable[tuple[float, float]], pointer: tuple[float, float] | None = None) -> None:
            self._draft_points = list(points)
            self._pointer_sheet = pointer
            self.update()

        def set_selected_ids(self, dimension_ids: Iterable[str]) -> None:
            self._selected_ids = {str(item) for item in dimension_ids}
            self.update()

        def set_selection_mode(self, enabled: bool) -> None:
            self._selection_enabled = bool(enabled)
            if not enabled:
                self._selection_origin_sheet = None
                self._selection_current_sheet = None
            self.update()

        @property
        def page_index(self) -> int:
            return self._page_index

        def fit_to_view(self) -> None:
            self._zoom = 1.0
            self._pan = QtCore.QPointF(0.0, 0.0)
            self.update()

        def zoom_to_selected(self) -> None:
            if self._document is None or not self._selected_ids:
                return
            bounds = [
                primitive.bounds()
                for primitive in self._document.pages[self._page_index].primitives
                if primitive.semantic_id in self._selected_ids and primitive.bounds()
            ]
            if not bounds:
                return
            left = min(value[0] for value in bounds)
            top = min(value[1] for value in bounds)
            right = max(value[2] for value in bounds)
            bottom = max(value[3] for value in bounds)
            page_width, page_height = self._page_size()
            self._zoom = min(
                8.0,
                max(
                    1.0,
                    min(
                        page_width * 0.75 / max(1.0, right - left),
                        page_height * 0.75 / max(1.0, bottom - top),
                    ),
                ),
            )
            self._pan = QtCore.QPointF(0.0, 0.0)
            target = self.sheet_to_widget(((left + right) * 0.5, (top + bottom) * 0.5))
            self._pan = QtCore.QPointF(self.width() * 0.5 - target.x(), self.height() * 0.5 - target.y())
            self.update()

        def _page_size(self) -> tuple[float, float]:
            if self._document is not None and getattr(self._document, "pages", None):
                page = self._document.pages[self._page_index]
                return float(page.width_mm), float(page.height_mm)
            if not self._pixmap.isNull():
                return float(self._pixmap.width()), float(self._pixmap.height())
            return 1.0, 1.0

        def _drawing_rect(self) -> Any:
            if self._pixmap.isNull():
                return QtCore.QRectF()
            available = QtCore.QSizeF(max(1, self.width() - 12), max(1, self.height() - 12))
            source = QtCore.QSizeF(self._pixmap.size())
            factor = min(available.width() / source.width(), available.height() / source.height()) * self._zoom
            size = QtCore.QSizeF(source.width() * factor, source.height() * factor)
            center = QtCore.QPointF(self.width() * 0.5, self.height() * 0.5) + self._pan
            return QtCore.QRectF(center.x() - size.width() * 0.5, center.y() - size.height() * 0.5, size.width(), size.height())

        def sheet_to_widget(self, point: tuple[float, float]) -> Any:
            rect = self._drawing_rect()
            width, height = self._page_size()
            return QtCore.QPointF(rect.left() + point[0] / width * rect.width(), rect.top() + point[1] / height * rect.height())

        def widget_to_sheet(self, point: Any) -> tuple[float, float] | None:
            rect = self._drawing_rect()
            if rect.isEmpty() or not rect.contains(QtCore.QPointF(point)):
                return None
            width, height = self._page_size()
            return (
                (float(point.x()) - rect.left()) / rect.width() * width,
                (float(point.y()) - rect.top()) / rect.height() * height,
            )

        @staticmethod
        def _distance_to_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
            dx, dy = end[0] - start[0], end[1] - start[1]
            length_squared = dx * dx + dy * dy
            if length_squared <= 1.0e-12:
                return math.hypot(point[0] - start[0], point[1] - start[1])
            position = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared))
            projected = (start[0] + position * dx, start[1] + position * dy)
            return math.hypot(point[0] - projected[0], point[1] - projected[1])

        def dimension_at(self, point: tuple[float, float], dimension_ids: Iterable[str]) -> str:
            if self._document is None or not getattr(self._document, "pages", None):
                return ""
            ids = {str(item) for item in dimension_ids}
            rect = self._drawing_rect()
            width, _height = self._page_size()
            threshold = 10.0 * width / max(1.0, rect.width())
            hits: list[tuple[float, str]] = []
            for primitive in self._document.pages[self._page_index].primitives:
                semantic_id = str(primitive.semantic_id or "")
                if semantic_id not in ids:
                    continue
                if primitive.kind in {"line", "polyline"} and len(primitive.points) >= 2:
                    for left, right in zip(primitive.points, primitive.points[1:]):
                        distance = self._distance_to_segment(point, tuple(left), tuple(right))
                        if distance <= threshold:
                            hits.append((distance, semantic_id))
                else:
                    bounds = primitive.bounds()
                    if bounds and bounds[0] - threshold <= point[0] <= bounds[2] + threshold and bounds[1] - threshold <= point[1] <= bounds[3] + threshold:
                        hits.append((0.0, semantic_id))
            return min(hits)[1] if hits else ""

        def cycle_candidate(self) -> None:
            if self._hover_candidates:
                self._hover_index = (self._hover_index + 1) % len(self._hover_candidates)
                self.update()

        def _update_hover(self, widget_point: Any) -> None:
            sheet = self.widget_to_sheet(widget_point)
            self._pointer_sheet = sheet
            if sheet is None:
                self._hover_candidates.clear()
                self.update()
                return
            nearby = []
            for candidate in self._candidates:
                if candidate.anchor.page_number != self._page_index + 1:
                    continue
                widget_candidate = self.sheet_to_widget(candidate.point)
                distance = math.hypot(widget_candidate.x() - float(widget_point.x()), widget_candidate.y() - float(widget_point.y()))
                if distance <= 11.0:
                    nearby.append((distance, candidate.candidate_id, candidate))
            # A projected feature can be emitted by more than one vector primitive
            # (for example its visible line and annotation helper).  Candidate IDs
            # are semantic identities, so keep one entry per identity; otherwise
            # Tab appears to cycle while resolving to the exact same snap target.
            distinct: dict[str, SnapCandidate] = {}
            for _distance, _candidate_id, candidate in sorted(nearby):
                distinct.setdefault(candidate.candidate_id, candidate)
            self._hover_candidates = list(distinct.values())
            if not self._hover_candidates and self._document is not None:
                page_width, _page_height = self._page_size()
                rect = self._drawing_rect()
                nearest = nearest_snap_candidate(
                    self._document,
                    sheet,
                    page_number=self._page_index + 1,
                    maximum_distance_sheet=11.0 * page_width / max(1.0, rect.width()),
                )
                if nearest is not None:
                    self._hover_candidates = [nearest]
            self._hover_index = min(self._hover_index, max(0, len(self._hover_candidates) - 1))
            self.pointer_moved.emit(sheet, self.current_candidate)
            self.update()

        def mouseMoveEvent(self, event: Any) -> None:
            if self._panning:
                current = QtCore.QPointF(event.position())
                self._pan += current - self._last_mouse
                self._last_mouse = current
                self.update()
                return
            if self._drag_dimension_id and self._drag_origin_sheet is not None:
                self._drag_current_sheet = self.widget_to_sheet(event.position())
                self.update()
                return
            if self._selection_enabled and self._selection_origin_sheet is not None:
                self._selection_current_sheet = self.widget_to_sheet(event.position())
                self.update()
                return
            self._update_hover(event.position())

        def mousePressEvent(self, event: Any) -> None:
            self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
            if event.button() == QtCore.Qt.MouseButton.MiddleButton:
                self._panning = True
                self._last_mouse = QtCore.QPointF(event.position())
                self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                return
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                point = self.widget_to_sheet(event.position())
                if point is not None:
                    selected_hit = self.dimension_at(point, self._selected_ids)
                    if selected_hit:
                        self._drag_dimension_id = selected_hit
                        self._drag_origin_sheet = point
                        self._drag_current_sheet = point
                        self._drag_text_only = bool(event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier)
                    elif self._selection_enabled:
                        self._selection_origin_sheet = point
                        self._selection_current_sheet = point
                        self._selection_modifiers = event.modifiers()
                    self.sheet_clicked.emit(point, self.current_candidate, event.modifiers())

        def mouseReleaseEvent(self, event: Any) -> None:
            if event.button() == QtCore.Qt.MouseButton.MiddleButton:
                self._panning = False
                self.unsetCursor()
            elif event.button() == QtCore.Qt.MouseButton.LeftButton and self._drag_dimension_id:
                if self._drag_origin_sheet is not None and self._drag_current_sheet is not None:
                    delta = (
                        self._drag_current_sheet[0] - self._drag_origin_sheet[0],
                        self._drag_current_sheet[1] - self._drag_origin_sheet[1],
                    )
                    if math.hypot(*delta) > 0.2:
                        self.dimension_dragged.emit(self._drag_dimension_id, delta, self._drag_text_only)
                self._drag_dimension_id = ""
                self._drag_origin_sheet = None
                self._drag_current_sheet = None
                self.update()
            elif event.button() == QtCore.Qt.MouseButton.LeftButton and self._selection_origin_sheet is not None:
                start = self._selection_origin_sheet
                end = self._selection_current_sheet or start
                if math.hypot(end[0] - start[0], end[1] - start[1]) > 1.0:
                    self.area_selected.emit(start, end, self._selection_modifiers)
                self._selection_origin_sheet = None
                self._selection_current_sheet = None
                self.update()

        def wheelEvent(self, event: Any) -> None:
            factor = 1.18 if event.angleDelta().y() > 0 else 1.0 / 1.18
            self._zoom = min(8.0, max(0.4, self._zoom * factor))
            self.update()

        def keyPressEvent(self, event: Any) -> None:
            modifiers = event.modifiers()
            key = event.key()
            if key == QtCore.Qt.Key.Key_Escape:
                self.command_requested.emit("cancel")
            elif key == QtCore.Qt.Key.Key_Backspace:
                self.command_requested.emit("backspace")
            elif key in {QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Back}:
                self.command_requested.emit("delete")
            elif key in {QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter}:
                self.command_requested.emit("enter")
            elif key == QtCore.Qt.Key.Key_Tab:
                self.cycle_candidate()
                event.accept()
                return
            elif key == QtCore.Qt.Key.Key_Z and modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
                self.command_requested.emit("redo" if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier else "undo")
            elif key == QtCore.Qt.Key.Key_Y and modifiers & QtCore.Qt.KeyboardModifier.ControlModifier:
                self.command_requested.emit("redo")
            elif not modifiers & (QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.AltModifier):
                shortcuts = {
                    QtCore.Qt.Key.Key_S: "tool:select",
                    QtCore.Qt.Key.Key_H: "tool:horizontal",
                    QtCore.Qt.Key.Key_V: "tool:vertical",
                    QtCore.Qt.Key.Key_A: "tool:aligned",
                    QtCore.Qt.Key.Key_R: "tool:radius",
                    QtCore.Qt.Key.Key_D: "tool:diameter",
                    QtCore.Qt.Key.Key_L: "tool:leader",
                    QtCore.Qt.Key.Key_T: "tool:text",
                }
                command = shortcuts.get(key)
                if command is None:
                    super().keyPressEvent(event)
                    return
                self.command_requested.emit(command)
            else:
                super().keyPressEvent(event)
                return
            event.accept()

        def paintEvent(self, event: Any) -> None:
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.fillRect(self.rect(), QtGui.QColor("#dce4eb"))
            rect = self._drawing_rect()
            if self._pixmap.isNull():
                painter.setPen(QtGui.QColor("#5b6b79"))
                painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, self._placeholder)
                return
            painter.drawPixmap(rect, self._pixmap, QtCore.QRectF(self._pixmap.rect()))
            painter.setPen(QtGui.QPen(QtGui.QColor("#ff8a00"), 2.0))
            for point in self._draft_points:
                target = self.sheet_to_widget(point)
                painter.drawEllipse(target, 4.0, 4.0)
            if self._draft_points and self._pointer_sheet is not None:
                painter.setPen(QtGui.QPen(QtGui.QColor("#ff8a00"), 1.5, QtCore.Qt.PenStyle.DashLine))
                painter.drawLine(self.sheet_to_widget(self._draft_points[-1]), self.sheet_to_widget(self._pointer_sheet))
            if self._drag_origin_sheet is not None and self._drag_current_sheet is not None:
                painter.setPen(QtGui.QPen(QtGui.QColor("#e6007e"), 2.0, QtCore.Qt.PenStyle.DashLine))
                painter.drawLine(self.sheet_to_widget(self._drag_origin_sheet), self.sheet_to_widget(self._drag_current_sheet))
            if self._selection_origin_sheet is not None and self._selection_current_sheet is not None:
                first = self.sheet_to_widget(self._selection_origin_sheet)
                second = self.sheet_to_widget(self._selection_current_sheet)
                selection_rect = QtCore.QRectF(first, second).normalized()
                crossing = self._selection_current_sheet[0] < self._selection_origin_sheet[0]
                painter.setPen(
                    QtGui.QPen(
                        QtGui.QColor("#d97706" if crossing else "#0066dc"),
                        1.5,
                        QtCore.Qt.PenStyle.DashLine,
                    )
                )
                painter.setBrush(QtGui.QColor(217, 119, 6, 30) if crossing else QtGui.QColor(0, 102, 220, 30))
                painter.drawRect(selection_rect)
            if self._document is not None and self._selected_ids:
                painter.setPen(QtGui.QPen(QtGui.QColor("#e6007e"), 3.0))
                grip_points: set[tuple[float, float]] = set()
                for primitive in self._document.pages[self._page_index].primitives:
                    if primitive.semantic_id not in self._selected_ids:
                        continue
                    if len(primitive.points) >= 2:
                        path = QtGui.QPainterPath(self.sheet_to_widget(tuple(primitive.points[0])))
                        for point in primitive.points[1:]:
                            path.lineTo(self.sheet_to_widget(tuple(point)))
                        painter.drawPath(path)
                        grip_points.add(tuple(float(value) for value in primitive.points[0]))
                        grip_points.add(tuple(float(value) for value in primitive.points[-1]))
                    else:
                        bounds = primitive.bounds()
                        if bounds:
                            top_left = self.sheet_to_widget((bounds[0], bounds[1]))
                            bottom_right = self.sheet_to_widget((bounds[2], bounds[3]))
                            painter.drawRect(QtCore.QRectF(top_left, bottom_right).normalized())
                            grip_points.add(((bounds[0] + bounds[2]) * 0.5, (bounds[1] + bounds[3]) * 0.5))
                painter.setPen(QtGui.QPen(QtGui.QColor("#5a0039"), 1.0))
                painter.setBrush(QtGui.QColor("#ffffff"))
                for point in sorted(grip_points):
                    target = self.sheet_to_widget(point)
                    painter.drawRect(QtCore.QRectF(target.x() - 4.0, target.y() - 4.0, 8.0, 8.0))
            candidate = self.current_candidate
            if candidate is not None:
                target = self.sheet_to_widget(candidate.point)
                color = QtGui.QColor("#00a15a" if candidate.valid else "#c62828")
                painter.setPen(QtGui.QPen(color, 2.0))
                painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 210)))
                marker = candidate.snap_type
                if marker == "midpoint":
                    polygon = QtGui.QPolygonF((target + QtCore.QPointF(0, -6), target + QtCore.QPointF(6, 5), target + QtCore.QPointF(-6, 5)))
                    painter.drawPolygon(polygon)
                elif marker == "center":
                    painter.drawEllipse(target, 6.0, 6.0)
                elif marker == "intersection":
                    painter.drawLine(target + QtCore.QPointF(-6, -6), target + QtCore.QPointF(6, 6))
                    painter.drawLine(target + QtCore.QPointF(-6, 6), target + QtCore.QPointF(6, -6))
                elif marker in {"datum", "feature"}:
                    painter.drawPolygon(
                        QtGui.QPolygonF(
                            (
                                target + QtCore.QPointF(0, -6),
                                target + QtCore.QPointF(6, 0),
                                target + QtCore.QPointF(0, 6),
                                target + QtCore.QPointF(-6, 0),
                            )
                        )
                    )
                else:
                    painter.drawRect(QtCore.QRectF(target.x() - 5, target.y() - 5, 10, 10))
                text_rect = QtCore.QRectF(target.x() + 9, target.y() - 24, 360, 22)
                painter.fillRect(text_rect, QtGui.QColor(25, 43, 58, 225))
                painter.setPen(QtGui.QColor("white"))
                painter.drawText(text_rect.adjusted(6, 1, -4, -1), QtCore.Qt.AlignmentFlag.AlignVCenter, candidate.label)

else:
    class InteractiveDrawingCanvas:
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["InteractiveDrawingCanvas"]
