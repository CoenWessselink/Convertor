"""Production-oriented before/after converter workspace."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class _ConversionWorker(QtCore.QObject):
        progress = QtCore.Signal(str)
        finished = QtCore.Signal(dict)
        failed = QtCore.Signal(str)

        def __init__(self, files: tuple[Path, ...], output: Path, direction: str, material: str) -> None:
            super().__init__()
            self.files, self.output, self.direction, self.material = files, output, direction, material

        @QtCore.Slot()
        def run(self) -> None:
            try:
                from conversion import convert_file
                results = []
                for index, source in enumerate(self.files, start=1):
                    self.progress.emit(f"{index}/{len(self.files)} · {source.name}")
                    if source.suffix.lower() == ".pdf":
                        from pdf_support import pdf_to_ifc, pdf_to_nc1, pdf_to_step

                        target_suffix = {"pdf-nc1": ".nc1", "pdf-step": ".step", "pdf-ifc": ".ifc"}.get(self.direction)
                        if target_suffix is None:
                            raise ValueError("Kies voor een PDF-bron de richting PDF → NC1, STEP of IFC")
                        target = self.output / f"{source.stem}{target_suffix}"
                        if self.direction == "pdf-nc1":
                            result = pdf_to_nc1(source, target)
                        elif self.direction == "pdf-step":
                            result = pdf_to_step(source, target)
                        else:
                            result = pdf_to_ifc(source, target, material=self.material)
                        outputs, warnings, failures = result.outputs, result.warnings, []
                    else:
                        outputs, warnings, failures = convert_file(source, self.output, self.direction, material=self.material, strict_validation=True)
                    if failures:
                        raise RuntimeError("; ".join(str(value) for value in failures))
                    results.append({"source": str(source), "outputs": [str(path) for path in outputs], "warnings": list(warnings), "failures": list(failures)})
                self.finished.emit({"status": "passed", "results": results})
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")

    class _ModelPreview(QtWidgets.QFrame):
        def __init__(self, title: str, target: bool = False) -> None:
            super().__init__()
            self.title, self.target, self.caption = title, target, "Wacht op selectie"
            self.setMinimumHeight(155)
            self.setObjectName("modelPreview")

        def set_caption(self, text: str) -> None:
            self.caption = text
            self.update()

        def paintEvent(self, event: Any) -> None:
            super().paintEvent(event)
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.setPen(QtGui.QColor("#183a63"))
            painter.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Weight.DemiBold))
            painter.drawText(16, 24, self.title)
            rect = self.rect().adjusted(55, 38, -55, -32)
            body = QtCore.QRectF(rect.left() + 30, rect.center().y() - 18, rect.width() - 60, 36)
            painter.setBrush(QtGui.QColor("#2d86e8" if self.target else "#9eabb9"))
            painter.setPen(QtGui.QPen(QtGui.QColor("#145fb8"), 2))
            painter.drawRect(body)
            painter.setBrush(QtGui.QColor("#dce5ef"))
            painter.drawRect(QtCore.QRectF(body.left() - 8, body.top() - 12, 8, 60))
            painter.drawRect(QtCore.QRectF(body.right(), body.top() - 12, 8, 60))
            painter.setPen(QtGui.QPen(QtGui.QColor("#1f6fd2"), 1, QtCore.Qt.PenStyle.DashLine))
            painter.drawLine(QtCore.QPointF(body.left(), body.center().y()), QtCore.QPointF(body.right(), body.center().y()))
            painter.setPen(QtGui.QColor("#63758a"))
            painter.setFont(QtGui.QFont("Segoe UI", 8))
            painter.drawText(self.rect().adjusted(16, 0, -16, -8), QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignLeft, self.caption)

    class ConverterPanel(QtWidgets.QWidget):
        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self._thread = self._worker = None
            self._files: list[Path] = []
            self._workspace = self._selection = None
            self._build_ui()

        def _build_ui(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(12, 9, 12, 9)
            root.setSpacing(7)
            header = QtWidgets.QHBoxLayout()
            title = QtWidgets.QLabel("Converteren")
            title.setObjectName("workspaceTitle")
            self.selection_context = QtWidgets.QLabel("Bron: losse modelbestanden")
            self.selection_context.setObjectName("mutedText")
            header.addWidget(title)
            header.addWidget(self.selection_context, 1)
            root.addLayout(header)
            comparison = QtWidgets.QHBoxLayout()
            self.source_preview = _ModelPreview("VOOR CONVERSIE · Bron")
            self.target_preview = _ModelPreview("NA CONVERSIE · Doel", True)
            comparison.addWidget(self.source_preview, 1)
            comparison.addWidget(self.target_preview, 1)
            root.addLayout(comparison)
            settings = QtWidgets.QFrame()
            settings.setObjectName("settingsPanel")
            grid = QtWidgets.QGridLayout(settings)
            grid.setContentsMargins(10, 8, 10, 8)
            self.direction = QtWidgets.QComboBox()
            for label, value in (("NC1 / DSTV → STEP", "nc1-step"), ("STEP → NC1 / DSTV", "step-nc1"), ("IFC → STEP", "ifc-step"), ("STEP → IFC", "step-ifc"), ("IFC → NC1 / DSTV", "ifc-nc1"), ("NC1 / DSTV → IFC", "nc1-ifc"), ("PDF → STEP (gecontroleerd)", "pdf-step"), ("PDF → NC1 / DSTV (gecontroleerd)", "pdf-nc1"), ("PDF → IFC (gecontroleerd)", "pdf-ifc")):
                self.direction.addItem(label, value)
            self.direction.currentIndexChanged.connect(self._direction_changed)
            self.material = QtWidgets.QComboBox()
            self.material.setEditable(True)
            self.material.addItems(["S235JR", "S355JR", "S355J2"])
            self.output = QtWidgets.QLineEdit(str(Path.home() / "CWS Convertor uitvoer"))
            browse = QtWidgets.QPushButton("Kies map")
            browse.clicked.connect(self._choose_output)
            self.run_button = QtWidgets.QPushButton("Converteren")
            self.run_button.setObjectName("primaryButton")
            self.run_button.clicked.connect(self._run)
            grid.addWidget(QtWidgets.QLabel("Richting"), 0, 0)
            grid.addWidget(self.direction, 1, 0)
            grid.addWidget(QtWidgets.QLabel("Materiaal"), 0, 1)
            grid.addWidget(self.material, 1, 1)
            grid.addWidget(QtWidgets.QLabel("Uitvoermap"), 0, 2)
            grid.addWidget(self.output, 1, 2)
            grid.addWidget(browse, 1, 3)
            grid.addWidget(self.run_button, 1, 4)
            grid.setColumnStretch(2, 1)
            root.addWidget(settings)
            lower = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            files_box = QtWidgets.QWidget()
            files_layout = QtWidgets.QVBoxLayout(files_box)
            files_layout.setContentsMargins(0, 0, 0, 0)
            file_tools = QtWidgets.QHBoxLayout()
            add = QtWidgets.QPushButton("Bestanden toevoegen")
            add.clicked.connect(self._choose_files)
            clear = QtWidgets.QPushButton("Lijst wissen")
            clear.clicked.connect(self._clear)
            file_tools.addWidget(add)
            file_tools.addWidget(clear)
            file_tools.addStretch(1)
            files_layout.addLayout(file_tools)
            self.files = QtWidgets.QListWidget()
            self.files.setMaximumHeight(90)
            files_layout.addWidget(self.files)
            self.log = QtWidgets.QPlainTextEdit()
            self.log.setReadOnly(True)
            self.log.setMaximumBlockCount(2000)
            self.log.setPlaceholderText("Conversielog en waarschuwingen")
            lower.addWidget(files_box)
            lower.addWidget(self.log)
            lower.setStretchFactor(0, 1)
            lower.setStretchFactor(1, 1)
            root.addWidget(lower, 1)
            self.status = QtWidgets.QLabel("Gereed")
            self.status.setObjectName("mutedText")
            root.addWidget(self.status)

        def set_project_selection(self, workspace: Any | None, selection: Any | None) -> None:
            self._workspace, self._selection = workspace, selection
            entity_id = str(getattr(selection, "primary_entity_id", "") or "")
            if workspace is None:
                self.selection_context.setText("Bron: losse modelbestanden")
                return
            entity = workspace.project.parts.get(entity_id) if entity_id else None
            name = str(getattr(entity, "part_position", "") or entity_id or "geen object geselecteerd")
            self.selection_context.setText(f"Project: {workspace.project.project_name} · Selectie: {name}")
            self.source_preview.set_caption(name)
            self.target_preview.set_caption("Doelpreview wordt na conversie bijgewerkt")

        def add_files(self, paths) -> None:
            allowed = {".nc", ".nc1", ".step", ".stp", ".ifc", ".pdf"}
            for value in paths:
                path = Path(value).expanduser().resolve()
                if path.suffix.lower() in allowed and path.is_file() and path not in self._files:
                    self._files.append(path)
                    self.files.addItem(f"{path}  [{self._recognize_file(path)}]")
            self.status.setText(f"{len(self._files)} bestand(en) geselecteerd")
            if self._files:
                self.source_preview.set_caption(self._files[0].name)
                self._select_direction_for(self._files[0])

        @staticmethod
        def _recognize_file(path: Path) -> str:
            with path.open("rb") as stream:
                head = stream.read(4096)
            upper = head.upper()
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                return "PDF herkend; trusted payload of vrijgegeven analyse vereist" if head.startswith(b"%PDF-") else "ongeldige PDF"
            if suffix == ".ifc":
                return "IFC herkend" if b"ISO-10303-21" in upper and b"IFC" in upper else "IFC-extensie, inhoud onzeker"
            if suffix in {".step", ".stp"}:
                return "STEP herkend" if b"ISO-10303-21" in upper else "STEP-extensie, inhoud onzeker"
            return "DSTV / NC herkend"

        def _select_direction_for(self, path: Path) -> None:
            preferred = {".pdf": "pdf-step", ".ifc": "ifc-step", ".step": "step-nc1", ".stp": "step-nc1", ".nc": "nc1-step", ".nc1": "nc1-step"}.get(path.suffix.lower())
            if preferred:
                index = self.direction.findData(preferred)
                if index >= 0:
                    self.direction.setCurrentIndex(index)

        def _direction_changed(self, _index: int = -1) -> None:
            label = self.direction.currentText().split("→", 1)[-1].strip()
            self.target_preview.set_caption(f"Doelformaat: {label}")

        def _choose_files(self) -> None:
            names, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Model- of tekeningbestanden kiezen", "", "Ondersteunde bestanden (*.nc *.nc1 *.step *.stp *.ifc *.pdf)")
            self.add_files(names)

        def _choose_output(self) -> None:
            name = QtWidgets.QFileDialog.getExistingDirectory(self, "Uitvoermap", self.output.text())
            if name:
                self.output.setText(name)

        def _clear(self) -> None:
            self._files.clear()
            self.files.clear()
            self.status.setText("Geen bestanden geselecteerd")
            self.source_preview.set_caption("Wacht op selectie")

        def _run(self) -> None:
            if not self._files:
                QtWidgets.QMessageBox.information(self, "Converteren", "Selecteer eerst bestanden.")
                return
            target = Path(self.output.text()).expanduser()
            target.mkdir(parents=True, exist_ok=True)
            direction = str(self.direction.currentData())
            expected = {
                "nc1-step": {".nc", ".nc1"}, "nc1-ifc": {".nc", ".nc1"},
                "step-nc1": {".step", ".stp"}, "step-ifc": {".step", ".stp"},
                "ifc-step": {".ifc"}, "ifc-nc1": {".ifc"},
                "pdf-step": {".pdf"}, "pdf-nc1": {".pdf"}, "pdf-ifc": {".pdf"},
            }.get(direction, set())
            invalid = [path.name for path in self._files if path.suffix.lower() not in expected]
            if invalid:
                QtWidgets.QMessageBox.warning(self, "Converteren", f"De gekozen richting past niet bij: {', '.join(invalid)}")
                return
            self.run_button.setEnabled(False)
            self.log.appendPlainText("Conversie gestart...")
            thread = QtCore.QThread(self)
            worker = _ConversionWorker(tuple(self._files), target, direction, self.material.currentText())
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.progress.connect(self.status.setText)
            worker.finished.connect(self._finished)
            worker.failed.connect(self._failed)
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            worker.failed.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(lambda: setattr(self, "_thread", None))
            thread.finished.connect(lambda: setattr(self, "_worker", None))
            self._worker, self._thread = worker, thread
            thread.start()

        @QtCore.Slot(dict)
        def _finished(self, payload: dict) -> None:
            self.run_button.setEnabled(True)
            outputs = []
            for row in payload.get("results", []):
                self.log.appendPlainText(f"OK  {Path(row['source']).name}")
                for output in row.get("outputs", []):
                    outputs.append(output)
                    self.log.appendPlainText(f"    {output}")
                for warning in row.get("warnings", []):
                    self.log.appendPlainText(f"WAARSCHUWING  {warning}")
            self.status.setText("Conversie succesvol afgerond")
            self.target_preview.set_caption(Path(outputs[-1]).name if outputs else "Conversie gereed")

        @QtCore.Slot(str)
        def _failed(self, message: str) -> None:
            self.run_button.setEnabled(True)
            self.status.setText("Conversie mislukt")
            self.log.appendPlainText(f"FOUT  {message}")
            QtWidgets.QMessageBox.critical(self, "Conversie mislukt", message)
else:
    class ConverterPanel:
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

__all__ = ["ConverterPanel"]
