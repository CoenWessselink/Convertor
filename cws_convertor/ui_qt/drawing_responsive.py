"""Responsive layout of the existing drawing workspace; no alternate UI/runtime."""
from __future__ import annotations

from typing import Any
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class WrappingToolLayout(QtWidgets.QLayout):
        """A height-for-width layout which keeps each field/control reachable."""

        def __init__(self, parent: Any = None, spacing: int = 5) -> None:
            super().__init__(parent)
            self._items: list[Any] = []
            self.setContentsMargins(0, 0, 0, 0)
            self.setSpacing(spacing)

        def addItem(self, item: Any) -> None:
            self._items.append(item)
            self.invalidate()

        def addStretch(self, _stretch: int = 0) -> None:
            pass

        def addSpacing(self, _spacing: int) -> None:
            pass

        def count(self) -> int:
            return len(self._items)

        def itemAt(self, index: int) -> Any:
            return self._items[index] if 0 <= index < len(self._items) else None

        def takeAt(self, index: int) -> Any:
            if 0 <= index < len(self._items):
                item = self._items.pop(index)
                self.invalidate()
                return item
            return None

        def expandingDirections(self) -> Any:
            return QtCore.Qt.Orientation(0)

        def hasHeightForWidth(self) -> bool:
            return True

        def heightForWidth(self, width: int) -> int:
            return self._arrange(QtCore.QRect(0, 0, max(1, width), 0), test=True)

        def setGeometry(self, rect: Any) -> None:
            super().setGeometry(rect)
            self._arrange(rect, test=False)

        def sizeHint(self) -> Any:
            return QtCore.QSize(900, self.heightForWidth(900))

        def minimumSize(self) -> Any:
            size = QtCore.QSize()
            for item in self._items:
                if not item.isEmpty():
                    size = size.expandedTo(item.minimumSize())
            left, top, right, bottom = self.getContentsMargins()
            return size + QtCore.QSize(left + right, top + bottom)

        def _arrange(self, rect: Any, test: bool) -> int:
            left, top, right, bottom = self.getContentsMargins()
            area = rect.adjusted(left, top, -right, -bottom)
            x, y, row_height = area.x(), area.y(), 0
            for item in self._items:
                if item.isEmpty():
                    continue
                size = item.sizeHint().expandedTo(item.minimumSize())
                # Wide combo box values/title text may elide, never widen the app.
                size.setWidth(min(size.width(), max(1, area.width())))
                if x > area.x() and x + size.width() > area.right() + 1:
                    x, y, row_height = area.x(), y + row_height + self.spacing(), 0
                if not test:
                    item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), size))
                x += size.width() + self.spacing()
                row_height = max(row_height, size.height())
            return y + row_height - rect.y() + bottom

    class _InspectorResizeFilter(QtCore.QObject):
        def __init__(self, panel: Any) -> None:
            super().__init__(panel)
            self.panel = panel
            self.explicit = False

        def eventFilter(self, watched: Any, event: Any) -> bool:
            if event.type() == QtCore.QEvent.Type.Resize and not self.explicit:
                visible = self.panel.width() >= 1100
                button = self.panel.inspector_toggle
                if button.isChecked() != visible:
                    button.setChecked(visible)
            return False

    def install_responsive_drawing_controls(panel: Any) -> None:
        """Reparent the original controls into the V3 native workspace layout."""
        from .drawing_workspace_layout import install_layout
        install_layout(panel)
