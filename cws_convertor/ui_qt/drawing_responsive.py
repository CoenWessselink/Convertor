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
        """Reflow existing controls without changing their signals or authorities."""
        root = panel.layout()
        toolbar_frame = panel.findChild(QtWidgets.QFrame, "dimensionEditorToolbar")
        toolbar = toolbar_frame.layout()
        instruction = panel.dimension_instruction
        for index in range(toolbar.count()):
            if toolbar.itemAt(index).widget() is instruction:
                toolbar.takeAt(index)
                break
        instruction.setWordWrap(True)
        instruction.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        root.insertWidget(3, instruction)

        names = {
            "select": "Selecteer", "horizontal": "Horizontaal", "vertical": "Verticaal",
            "aligned": "Uitgelijnd", "chain": "Ketting", "baseline": "Nulpunt",
            "ordinate_x": "Ordinaat X", "ordinate_y": "Ordinaat Y", "angle": "Hoek",
            "radius": "Radius", "diameter": "Diameter", "center_distance": "Hartafstand",
            "leader": "Leader", "text": "Tekst",
        }
        from cws_convertor.ui_qt.ribbon_icons import ribbon_icon
        for key, button in panel.dimension_tool_buttons.items():
            name = names.get(key, key.replace("_", " ").capitalize())
            button.setAccessibleName(name)
            button.setText(name)
            button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setIcon(ribbon_icon("select" if key == "select" else "maatvoering", name))
            button.setIconSize(QtCore.QSize(18, 18))
        action_names = ("Toon/verberg", "Heranker", "Dupliceer", "Verwijder", "Undo", "Redo", "Fit", "Zoom", "Reset", "Vrijgeven")
        for name, button in zip(action_names, panel.dimension_action_buttons.values()):
            button.setText(name)
            button.setAccessibleName(button.toolTip())
        panel.preview_button.setText("Vernieuwen")
        panel.png_button.setText("PNG")
        panel.pdf_button.setText("PDF exporteren")
        panel.add_dimension_button.setText("Handmatig…")
        panel.clear_dimensions_button.setText("Verwijderen")
        for combo in (panel.page_selector, panel.annotation_kind):
            combo.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(9)
            combo.setMaximumWidth(160)
        panel.title.setMaximumWidth(360)
        panel.title.setMinimumWidth(120)
        panel.title.setWordWrap(True)
        panel.status.setWordWrap(True)
        panel.preview.setMinimumHeight(240)
        panel.dimension_properties.setMinimumWidth(0)
        panel.dimension_properties.header().setStretchLastSection(True)
        panel.inspector_frame = panel.dimension_properties.parentWidget()
        panel.inspector_frame.setMinimumWidth(250)
        panel.inspector_frame.setMaximumWidth(315)
        panel.inspector_toggle = QtWidgets.QToolButton(panel)
        panel.inspector_toggle.setText("Eigenschappen")
        panel.inspector_toggle.setObjectName("drawingInspectorToggle")
        panel.inspector_toggle.setToolTip("Maateigenschappen inklappen of uitklappen")
        panel.inspector_toggle.setCheckable(True)
        panel.inspector_toggle.setChecked(True)
        panel.inspector_toggle.toggled.connect(panel.inspector_frame.setVisible)
        root.itemAt(0).layout().addWidget(panel.inspector_toggle)
        resize_filter = _InspectorResizeFilter(panel)
        panel._inspector_resize_filter = resize_filter
        panel.inspector_toggle.clicked.connect(lambda: setattr(resize_filter, "explicit", True))
        panel.installEventFilter(resize_filter)
