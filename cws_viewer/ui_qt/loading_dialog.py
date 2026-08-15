"""Visible model-loading state for the standalone CWS Viewer.

The start centre must never disappear into an apparently dead process while a
large IFC/STEP file is being analysed and tessellated.  This lightweight Qt
dialog stays visible during synchronous intake and geometry loading and pumps
Qt events whenever deterministic progress is reported.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.ui_qt.design_system import LIGHT_QSS
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class ViewerLoadingDialog(QtWidgets.QDialog):
        def __init__(self, *, version: str, source_path: str | Path) -> None:
            super().__init__()
            self.source_path = Path(source_path)
            self.setObjectName("cwsCockpitRoot")
            self.setWindowTitle(f"CWS Viewer {version} — model laden")
            self.setModal(False)
            self.resize(720, 310)
            self.setMinimumSize(600, 280)
            self.setStyleSheet(LIGHT_QSS)
            self.setWindowFlag(QtCore.Qt.WindowType.WindowContextHelpButtonHint, False)
            self._build_ui(version)

        def _build_ui(self, version: str) -> None:
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(20, 20, 20, 20)
            outer.setSpacing(12)

            header = QtWidgets.QFrame()
            header.setObjectName("cwsHeader")
            row = QtWidgets.QHBoxLayout(header)
            row.setContentsMargins(16, 12, 16, 12)
            title_box = QtWidgets.QVBoxLayout()
            title = QtWidgets.QLabel("CWS Viewer")
            title.setObjectName("cwsProductTitle")
            subtitle = QtWidgets.QLabel("Model wordt voorbereid voor de 3D-viewer")
            subtitle.setObjectName("cwsSubtitle")
            title_box.addWidget(title)
            title_box.addWidget(subtitle)
            row.addLayout(title_box)
            row.addStretch(1)
            label = QtWidgets.QLabel(version)
            label.setObjectName("cwsVersion")
            row.addWidget(label, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            outer.addWidget(header)

            panel = QtWidgets.QFrame()
            panel.setObjectName("cwsPanel")
            layout = QtWidgets.QVBoxLayout(panel)
            layout.setContentsMargins(22, 18, 22, 18)
            layout.setSpacing(9)

            self.stage_label = QtWidgets.QLabel("Voorbereiden…")
            self.stage_label.setObjectName("cwsSectionTitle")
            stage_font = self.stage_label.font()
            stage_font.setPointSize(max(12, stage_font.pointSize() + 2))
            self.stage_label.setFont(stage_font)
            layout.addWidget(self.stage_label)

            self.file_label = QtWidgets.QLabel(str(self.source_path))
            self.file_label.setObjectName("cwsMuted")
            self.file_label.setWordWrap(True)
            self.file_label.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )
            layout.addWidget(self.file_label)

            self.progress = QtWidgets.QProgressBar()
            self.progress.setRange(0, 1000)
            self.progress.setValue(0)
            self.progress.setTextVisible(True)
            self.progress.setFormat("0 %")
            self.progress.setMinimumHeight(18)
            layout.addWidget(self.progress)

            self.detail_label = QtWidgets.QLabel(
                "CWS Viewer blijft actief. Grote IFC/STEP-modellen kunnen enige tijd nodig hebben."
            )
            self.detail_label.setObjectName("cwsMuted")
            self.detail_label.setWordWrap(True)
            layout.addWidget(self.detail_label)
            outer.addWidget(panel, 1)

        def set_progress(self, fraction: float, message: str, detail: str | None = None) -> None:
            value = max(0.0, min(1.0, float(fraction)))
            self.stage_label.setText(str(message or "Model laden…"))
            self.progress.setValue(int(round(value * 1000.0)))
            self.progress.setFormat(f"{value * 100.0:.0f} %")
            if detail is not None:
                self.detail_label.setText(str(detail))
            self.show()
            self.raise_()
            QtWidgets.QApplication.processEvents(
                QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50
            )

        def set_indeterminate(self, message: str, detail: str | None = None) -> None:
            self.stage_label.setText(str(message))
            self.progress.setRange(0, 0)
            if detail is not None:
                self.detail_label.setText(str(detail))
            self.show()
            self.raise_()
            QtWidgets.QApplication.processEvents(
                QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50
            )

        def restore_determinate(self) -> None:
            if self.progress.maximum() == 0:
                self.progress.setRange(0, 1000)

        def finish_loading(self) -> None:
            self.restore_determinate()
            self.set_progress(1.0, "Viewer openen…")
            self.close()
            QtWidgets.QApplication.processEvents()


    def create_loading_dialog(*, version: str, source_path: str | Path) -> ViewerLoadingDialog:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setApplicationName("CWS Viewer")
        app.setOrganizationName("CWS")
        dialog = ViewerLoadingDialog(version=version, source_path=source_path)
        dialog.show()
        dialog.set_progress(0.01, "Model voorbereiden…")
        return dialog

else:

    class ViewerLoadingDialog:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    def create_loading_dialog(**_: Any):  # pragma: no cover
        require_qt()


__all__ = ["ViewerLoadingDialog", "create_loading_dialog"]
