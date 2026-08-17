"""Phase 2 input host: interactive review markups without selection mutation."""
from __future__ import annotations

import math
from typing import Any, Iterable

from cws_viewer.ui_qt.markup_overlay_phase2 import ReviewMarkupOverlay
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.vtk_real_project_widget_v15 import VtkRealProjectWidgetV15


_MARKUP_KINDS = frozenset({"text", "line", "arrow", "cloud", "freehand"})


if qt_available():
    QtCore, _QtGui, _QtWidgets = require_qt()

    class VtkRealProjectWidgetPhase2(VtkRealProjectWidgetV15):
        """Add a capture-state machine for visible review markup workflows.

        Markup tools only call ``probe_at`` through the V15 hidden/ghost-safe
        probe route. They never call semantic selection methods. This keeps the
        selected object/assembly and its orbit pivot stable while drawing.
        """

        markup_gesture_completed = QtCore.Signal(object)
        markup_tool_state_changed = QtCore.Signal(str)

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._phase2_markup_kind: str | None = None
            self._phase2_markup_text = ""
            self._phase2_markup_picks: list[Any] = []
            self._phase2_markup_points: list[tuple[float, float, float]] = []
            self._phase2_freehand_active = False
            self._phase2_last_sample_px: tuple[float, float] | None = None
            self._phase2_markup_overlay = ReviewMarkupOverlay(self)
            self._phase2_markup_overlay.raise_()

        @property
        def markup_tool_kind(self) -> str | None:
            return self._phase2_markup_kind

        @property
        def markup_tool_active(self) -> bool:
            return self._phase2_markup_kind is not None

        def set_review_markups(self, records: Iterable[Any]) -> None:
            self._phase2_markup_overlay.set_records(tuple(records))

        def start_markup_tool(self, kind: str, *, text: str = "") -> None:
            value = str(kind or "").casefold().strip()
            if value not in _MARKUP_KINDS:
                raise ValueError(f"Onbekend markuptype: {kind}")
            self._v15_zoom_area = False
            self._area_selection = False
            self._rubber_band.hide()
            self.controller.cancel_tool()
            self._phase2_markup_kind = value
            self._phase2_markup_text = str(text or "")
            self._reset_markup_capture(clear_preview=True)
            self.setCursor(QtCore.Qt.CursorShape.CrossCursor)
            hint = {
                "text": "Tekstmarkup: klik een modelpunt · Esc stopt",
                "line": "Lijnmarkup: klik beginpunt en eindpunt · Esc stopt",
                "arrow": "Pijlmarkup: klik beginpunt en eindpunt · Esc stopt",
                "cloud": "Cloudmarkup: klik minimaal 3 punten · dubbelklik/Enter/rechtsklik voltooit · Esc stopt",
                "freehand": "Freehand: houd links ingedrukt en teken over het model · Esc stopt",
            }[value]
            self.interaction_message.emit(hint)
            self.markup_tool_state_changed.emit(value)
            self.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)

        def cancel_markup_tool(self) -> None:
            had_tool = self._phase2_markup_kind is not None
            self._phase2_markup_kind = None
            self._phase2_markup_text = ""
            self._reset_markup_capture(clear_preview=True)
            try:
                self.set_navigation_mode(self.navigation_mode)
            except Exception:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            if had_tool:
                self.interaction_message.emit("Markupgereedschap beëindigd")
                self.markup_tool_state_changed.emit("")

        def _reset_markup_capture(self, *, clear_preview: bool) -> None:
            self._phase2_markup_picks.clear()
            self._phase2_markup_points.clear()
            self._phase2_freehand_active = False
            self._phase2_last_sample_px = None
            if clear_preview:
                self._phase2_markup_overlay.clear_preview()

        @staticmethod
        def _world_tuple(pick: Any) -> tuple[float, float, float]:
            point = pick.world_point
            return (float(point.x), float(point.y), float(point.z))

        @staticmethod
        def _screen_tuple(pos: Any) -> tuple[float, float]:
            return (float(pos.x()), float(pos.y()))

        def _sample_distance_ok(self, pos: Any, threshold: float = 5.0) -> bool:
            current = self._screen_tuple(pos)
            previous = self._phase2_last_sample_px
            if previous is None:
                return True
            return math.hypot(current[0] - previous[0], current[1] - previous[1]) >= threshold

        def _append_markup_probe(self, pos: Any, *, force: bool = False) -> Any | None:
            if not force and not self._sample_distance_ok(pos):
                return None
            probe = self._probe_screen(pos)
            if probe is None:
                return None
            raw = self._world_tuple(probe)
            if self._phase2_markup_points:
                previous = self._phase2_markup_points[-1]
                if math.dist(previous, raw) <= 1e-7:
                    self._phase2_last_sample_px = self._screen_tuple(pos)
                    return probe
            self._phase2_markup_picks.append(probe)
            self._phase2_markup_points.append(raw)
            self._phase2_last_sample_px = self._screen_tuple(pos)
            return probe

        def _preview(self, extra: tuple[float, float, float] | None = None) -> None:
            kind = self._phase2_markup_kind or ""
            points = list(self._phase2_markup_points)
            if extra is not None:
                if not points or math.dist(points[-1], extra) > 1e-7:
                    points.append(extra)
            self._phase2_markup_overlay.set_preview(
                kind,
                points,
                text=self._phase2_markup_text,
            )

        def _required_points(self) -> int:
            return {
                "text": 1,
                "line": 2,
                "arrow": 2,
                "cloud": 3,
                "freehand": 2,
            }.get(self._phase2_markup_kind or "", 1)

        def _complete_markup_gesture(self) -> bool:
            kind = self._phase2_markup_kind
            if kind is None:
                return False
            if len(self._phase2_markup_points) < self._required_points():
                self.interaction_message.emit(
                    f"{kind}: nog {self._required_points() - len(self._phase2_markup_points)} punt(en) nodig"
                )
                return False
            payload = {
                "kind": kind,
                "text": self._phase2_markup_text,
                "picks": tuple(self._phase2_markup_picks),
                "world_points_mm": tuple(self._phase2_markup_points),
            }
            self.markup_gesture_completed.emit(payload)
            self._reset_markup_capture(clear_preview=True)
            # Tool intentionally remains active, matching engineering review
            # workflows where several arrows/lines can be placed consecutively.
            self.markup_tool_state_changed.emit(kind)
            return True

        def _hover_preview(self, pos: Any) -> None:
            if not self.markup_tool_active or self._phase2_markup_kind == "freehand":
                return
            probe = self._probe_screen(pos)
            if probe is None:
                self._preview()
                return
            self._preview(self._world_tuple(probe))

        def mousePressEvent(self, event: Any) -> None:
            if not self.markup_tool_active:
                super().mousePressEvent(event)
                return
            self.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
            if event.button() == QtCore.Qt.MouseButton.RightButton:
                if self._phase2_markup_kind == "cloud":
                    self._complete_markup_gesture()
                event.accept()
                return
            if event.button() != QtCore.Qt.MouseButton.LeftButton:
                event.accept()
                return
            if self._phase2_markup_kind == "freehand":
                self._reset_markup_capture(clear_preview=True)
                self._phase2_freehand_active = True
                self._append_markup_probe(event.position(), force=True)
                self._preview()
            event.accept()

        def mouseMoveEvent(self, event: Any) -> None:
            if not self.markup_tool_active:
                super().mouseMoveEvent(event)
                self._phase2_markup_overlay.update()
                return
            if self._phase2_markup_kind == "freehand" and self._phase2_freehand_active:
                if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
                    self._append_markup_probe(event.position())
                    self._preview()
            else:
                self._hover_preview(event.position())
            event.accept()

        def mouseReleaseEvent(self, event: Any) -> None:
            if not self.markup_tool_active:
                super().mouseReleaseEvent(event)
                self._phase2_markup_overlay.update()
                return
            if event.button() != QtCore.Qt.MouseButton.LeftButton:
                event.accept()
                return
            kind = self._phase2_markup_kind
            if kind == "freehand":
                if self._phase2_freehand_active:
                    self._append_markup_probe(event.position(), force=True)
                    self._phase2_freehand_active = False
                    self._complete_markup_gesture()
                event.accept()
                return

            self._append_markup_probe(event.position(), force=True)
            if kind == "text" and self._phase2_markup_points:
                self._complete_markup_gesture()
            elif kind in {"line", "arrow"} and len(self._phase2_markup_points) >= 2:
                self._complete_markup_gesture()
            else:
                self._preview()
            event.accept()

        def mouseDoubleClickEvent(self, event: Any) -> None:
            if not self.markup_tool_active:
                super().mouseDoubleClickEvent(event)
                self._phase2_markup_overlay.update()
                return
            if (
                self._phase2_markup_kind == "cloud"
                and event.button() == QtCore.Qt.MouseButton.LeftButton
            ):
                self._append_markup_probe(event.position(), force=True)
                self._complete_markup_gesture()
            event.accept()

        def wheelEvent(self, event: Any) -> None:
            # Wheel zoom remains available while reviewing; it never commits a
            # markup point and the overlay simply reprojects afterwards.
            super().wheelEvent(event)
            self._phase2_markup_overlay.update()

        def keyPressEvent(self, event: Any) -> None:
            if self.markup_tool_active:
                key = event.key()
                if key == QtCore.Qt.Key.Key_Escape:
                    self.cancel_markup_tool()
                    self.tool_cancelled.emit()
                    event.accept()
                    return
                if self._phase2_markup_kind == "cloud" and key in {
                    QtCore.Qt.Key.Key_Return,
                    QtCore.Qt.Key.Key_Enter,
                }:
                    self._complete_markup_gesture()
                    event.accept()
                    return
                if (
                    self._phase2_markup_kind == "cloud"
                    and key == QtCore.Qt.Key.Key_Backspace
                    and self._phase2_markup_points
                ):
                    self._phase2_markup_points.pop()
                    if self._phase2_markup_picks:
                        self._phase2_markup_picks.pop()
                    self._preview()
                    event.accept()
                    return
            super().keyPressEvent(event)
            self._phase2_markup_overlay.update()

        def resizeEvent(self, event: Any) -> None:
            super().resizeEvent(event)
            self._phase2_markup_overlay.setGeometry(self.rect())
            self._phase2_markup_overlay.raise_()
            self._phase2_markup_overlay.update()

else:

    class VtkRealProjectWidgetPhase2:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["VtkRealProjectWidgetPhase2"]
