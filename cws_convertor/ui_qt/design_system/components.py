from __future__ import annotations

from PySide6 import QtWidgets

from .test_ids import set_ui_test_id


class CwsPrimaryButton(QtWidgets.QPushButton):
    def __init__(self, text: str, test_id: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setProperty("cwsRole", "primary")
        set_ui_test_id(self, test_id)


class CwsSecondaryButton(QtWidgets.QPushButton):
    def __init__(self, text: str, test_id: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setProperty("cwsRole", "secondary")
        set_ui_test_id(self, test_id)


class CwsSurface(QtWidgets.QFrame):
    def __init__(self, test_id: str, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("cwsSurface", True)
        set_ui_test_id(self, test_id)

