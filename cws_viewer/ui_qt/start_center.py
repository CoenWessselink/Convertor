"""Project-less startup centre for the standalone CWS Viewer.

The Windows desktop shortcut deliberately launches CWS Viewer without a file
argument.  This module owns that state: the application opens first, and only
opens a file picker after an explicit user action.  It is also safe to run on a
hosted CI runner because the start centre itself does not create a VTK/OpenGL
window.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cws_viewer.ui_qt.design_system import LIGHT_QSS
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

SUPPORTED_EXTENSIONS = (".cwscproj", ".ifc", ".step", ".stp")
OPEN_FILTER = (
    "CWS Convertor project (*.cwscproj);;"
    "IFC model (*.ifc);;"
    "STEP model (*.step *.stp);;"
    "Alle ondersteunde bestanden (*.cwscproj *.ifc *.step *.stp)"
)


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class StartCenterDialog(QtWidgets.QDialog):
        """Real application start state used when no model/project is supplied."""

        def __init__(self, *, version: str) -> None:
            super().__init__()
            self.version = version
            self.selected_path: Path | None = None
            self.file_dialog_opened = False
            self.setObjectName("cwsCockpitRoot")
            self.setWindowTitle(f"CWS Viewer {version}")
            self.resize(1120, 700)
            self.setMinimumSize(860, 560)
            self.setAcceptDrops(True)
            self.setStyleSheet(LIGHT_QSS)
            self._settings = QtCore.QSettings("CWS", "CWS Viewer")
            self._build_ui()
            self._load_recent_files()

        def _build_ui(self) -> None:
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(18, 18, 18, 18)
            outer.setSpacing(12)

            header = QtWidgets.QFrame()
            header.setObjectName("cwsHeader")
            header_layout = QtWidgets.QHBoxLayout(header)
            header_layout.setContentsMargins(18, 14, 18, 14)
            title_box = QtWidgets.QVBoxLayout()
            title = QtWidgets.QLabel("CWS Viewer")
            title.setObjectName("cwsProductTitle")
            subtitle = QtWidgets.QLabel("Model bekijken, controleren en analyseren")
            subtitle.setObjectName("cwsSubtitle")
            title_box.addWidget(title)
            title_box.addWidget(subtitle)
            header_layout.addLayout(title_box)
            header_layout.addStretch(1)
            version = QtWidgets.QLabel(self.version)
            version.setObjectName("cwsVersion")
            header_layout.addWidget(version, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            outer.addWidget(header)

            body = QtWidgets.QHBoxLayout()
            body.setSpacing(12)

            open_panel = QtWidgets.QFrame()
            open_panel.setObjectName("cwsPanel")
            open_layout = QtWidgets.QVBoxLayout(open_panel)
            open_layout.setContentsMargins(28, 28, 28, 28)
            open_layout.setSpacing(12)

            heading = QtWidgets.QLabel("Welkom")
            heading.setObjectName("cwsSectionTitle")
            heading_font = heading.font()
            heading_font.setPointSize(max(16, heading_font.pointSize() + 5))
            heading.setFont(heading_font)
            open_layout.addWidget(heading)

            intro = QtWidgets.QLabel(
                "Open een CWS-project, IFC-model of STEP-model. "
                "CWS Viewer start voortaan altijd eerst als applicatie; "
                "een bestandsvenster verschijnt alleen nadat je daarvoor kiest."
            )
            intro.setWordWrap(True)
            intro.setObjectName("cwsMuted")
            open_layout.addWidget(intro)
            open_layout.addSpacing(12)

            self.open_button = QtWidgets.QPushButton("Project of model openen")
            self.open_button.setObjectName("cwsPrimaryButton")
            self.open_button.setMinimumHeight(46)
            self.open_button.clicked.connect(self._open_file_dialog)
            open_layout.addWidget(self.open_button)

            drop = QtWidgets.QLabel(
                "Of sleep een .cwscproj, .ifc, .step of .stp bestand naar dit venster."
            )
            drop.setObjectName("cwsMuted")
            drop.setWordWrap(True)
            open_layout.addWidget(drop)
            open_layout.addStretch(1)

            supported_title = QtWidgets.QLabel("Ondersteunde invoer")
            supported_title.setObjectName("cwsPanelTitle")
            open_layout.addWidget(supported_title)
            supported = QtWidgets.QLabel(
                "CWS Convertor project  .cwscproj\n"
                "Industry Foundation Classes  .ifc\n"
                "STEP  .step / .stp"
            )
            supported.setObjectName("cwsMuted")
            supported.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )
            open_layout.addWidget(supported)
            body.addWidget(open_panel, 3)

            recent_panel = QtWidgets.QFrame()
            recent_panel.setObjectName("cwsPanel")
            recent_layout = QtWidgets.QVBoxLayout(recent_panel)
            recent_layout.setContentsMargins(18, 18, 18, 18)
            recent_layout.setSpacing(8)
            recent_title = QtWidgets.QLabel("Recent geopend")
            recent_title.setObjectName("cwsPanelTitle")
            recent_layout.addWidget(recent_title)
            self.recent_list = QtWidgets.QListWidget()
            self.recent_list.setObjectName("cwsRecentFiles")
            self.recent_list.itemDoubleClicked.connect(self._open_recent_item)
            recent_layout.addWidget(self.recent_list, 1)
            recent_hint = QtWidgets.QLabel("Dubbelklik om opnieuw te openen")
            recent_hint.setObjectName("cwsMuted")
            recent_layout.addWidget(recent_hint)
            body.addWidget(recent_panel, 2)
            outer.addLayout(body, 1)

            status = QtWidgets.QFrame()
            status.setObjectName("cwsStatusStrip")
            status_layout = QtWidgets.QHBoxLayout(status)
            status_layout.setContentsMargins(14, 8, 14, 8)
            ready = QtWidgets.QLabel("Gereed — geen project geopend")
            ready.setObjectName("cwsStatusOk")
            status_layout.addWidget(ready)
            status_layout.addStretch(1)
            safety = QtWidgets.QLabel("Viewer/read-review · productie-uitvoer geblokkeerd")
            safety.setObjectName("cwsMuted")
            status_layout.addWidget(safety)
            outer.addWidget(status)

            open_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
            open_shortcut.activated.connect(self._open_file_dialog)
            self._open_shortcut = open_shortcut

        def _recent_paths(self) -> list[Path]:
            value = self._settings.value("recentFiles", [])
            if isinstance(value, str):
                values = [value]
            elif value is None:
                values = []
            else:
                values = list(value)
            result: list[Path] = []
            for raw in values:
                path = Path(str(raw)).expanduser()
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    result.append(path)
            return result[:10]

        def _load_recent_files(self) -> None:
            self.recent_list.clear()
            paths = self._recent_paths()
            if not paths:
                item = QtWidgets.QListWidgetItem("Nog geen recente bestanden")
                item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
                self.recent_list.addItem(item)
                return
            for path in paths:
                item = QtWidgets.QListWidgetItem(path.name)
                item.setToolTip(str(path))
                item.setData(QtCore.Qt.ItemDataRole.UserRole, str(path))
                self.recent_list.addItem(item)

        def _remember(self, path: Path) -> None:
            values = [str(path)]
            values.extend(str(existing) for existing in self._recent_paths() if existing != path)
            self._settings.setValue("recentFiles", values[:10])
            self._settings.sync()

        def _initial_directory(self) -> str:
            recent = self._recent_paths()
            if recent:
                return str(recent[0].parent)
            documents = QtCore.QStandardPaths.writableLocation(
                QtCore.QStandardPaths.StandardLocation.DocumentsLocation
            )
            return documents or str(Path.home())

        def _open_file_dialog(self) -> None:
            self.file_dialog_opened = True
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Openen in CWS Viewer",
                self._initial_directory(),
                OPEN_FILTER,
            )
            if filename:
                self._accept_path(Path(filename))

        def _open_recent_item(self, item: Any) -> None:
            value = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if value:
                self._accept_path(Path(str(value)))

        def _accept_path(self, path: Path) -> None:
            path = path.expanduser().resolve()
            if not path.is_file():
                QtWidgets.QMessageBox.warning(
                    self, "Bestand niet gevonden", f"Dit bestand bestaat niet meer:\n{path}"
                )
                self._load_recent_files()
                return
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Niet ondersteund bestand",
                    "Kies een .cwscproj, .ifc, .step of .stp bestand.",
                )
                return
            self.selected_path = path
            self._remember(path)
            self.accept()

        def dragEnterEvent(self, event: Any) -> None:
            urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
            if any(
                url.isLocalFile()
                and Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS
                for url in urls
            ):
                event.acceptProposedAction()
            else:
                event.ignore()

        def dropEvent(self, event: Any) -> None:
            for url in event.mimeData().urls():
                if not url.isLocalFile():
                    continue
                path = Path(url.toLocalFile())
                if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    event.acceptProposedAction()
                    self._accept_path(path)
                    return
            event.ignore()


    def run_start_center(
        *,
        version: str,
        ci_smoke: bool = False,
        ci_headless: bool = False,
        report_path: str | Path | None = None,
        screenshot_path: str | Path | None = None,
    ) -> tuple[int, Path | None]:
        """Run the no-project application state and optionally return a chosen file."""
        if ci_headless:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setApplicationName("CWS Viewer")
        app.setOrganizationName("CWS")
        dialog = StartCenterDialog(version=version)
        smoke: dict[str, Any] = {"status": "not_run"}

        if ci_smoke:
            report = Path(report_path) if report_path else None
            screenshot = Path(screenshot_path) if screenshot_path else None

            def verify_startup() -> None:
                try:
                    if dialog.file_dialog_opened:
                        raise RuntimeError("Bestandsdialoog werd automatisch geopend")
                    if dialog.selected_path is not None:
                        raise RuntimeError("Startcentrum selecteerde onverwacht een bestand")
                    if not dialog.open_button.isVisible():
                        raise RuntimeError("Open-knop is niet zichtbaar")
                    if screenshot:
                        screenshot.parent.mkdir(parents=True, exist_ok=True)
                        dialog.grab().save(str(screenshot), "PNG")
                    smoke.update(
                        {
                            "status": "passed",
                            "schema": "cws-viewer-startup-smoke-1.0",
                            "window_title": dialog.windowTitle(),
                            "object_name": dialog.objectName(),
                            "file_dialog_opened": dialog.file_dialog_opened,
                            "selected_path": None,
                            "supported_extensions": list(SUPPORTED_EXTENSIONS),
                            "qt_version": QtCore.qVersion(),
                            "headless": bool(ci_headless),
                        }
                    )
                except Exception as exc:  # pragma: no cover - Windows evidence
                    smoke.update(
                        {
                            "status": "failed",
                            "schema": "cws-viewer-startup-smoke-1.0",
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                finally:
                    if report:
                        report.parent.mkdir(parents=True, exist_ok=True)
                        report.write_text(json.dumps(smoke, indent=2), encoding="utf-8")
                    dialog.reject()

            QtCore.QTimer.singleShot(300, verify_startup)

        result = int(dialog.exec())
        if ci_smoke:
            return (0 if smoke.get("status") == "passed" else 2), None
        if result == int(QtWidgets.QDialog.DialogCode.Accepted):
            return 0, dialog.selected_path
        return 0, None

else:

    class StartCenterDialog:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    def run_start_center(**_: Any) -> tuple[int, Path | None]:  # pragma: no cover
        require_qt()
        return 2, None


__all__ = [
    "SUPPORTED_EXTENSIONS",
    "OPEN_FILTER",
    "StartCenterDialog",
    "run_start_center",
]
