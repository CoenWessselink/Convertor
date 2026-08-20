"""Production-oriented before/after converter workspace."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class _ConversionWorker(QtCore.QObject):
        progress = QtCore.Signal(int, str)
        finished = QtCore.Signal(dict)
        failed = QtCore.Signal(str)

        def __init__(
            self,
            files: tuple[Path, ...],
            output: Path,
            direction: str,
            material: str,
            *,
            project_path: Path | None = None,
            entity_id: str = "",
        ) -> None:
            super().__init__()
            self.files, self.output, self.direction, self.material = files, output, direction, material
            self.project_path = project_path
            self.entity_id = str(entity_id or "")
            self._cancel_requested = False
            self._process: subprocess.Popen[Any] | None = None

        def request_cancel(self) -> None:
            self._cancel_requested = True
            process = self._process
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass

        @staticmethod
        def _command(job: Path, result: Path) -> list[str]:
            arguments = ["--conversion-worker", str(job), "--conversion-result", str(result)]
            if bool(getattr(sys, "frozen", False)):
                return [sys.executable, *arguments]
            launcher = Path(__file__).resolve().parents[2] / "CWS_Convertor_App.py"
            return [sys.executable, str(launcher), *arguments]

        @staticmethod
        def _stop_process(process: subprocess.Popen[Any]) -> None:
            if process.poll() is not None:
                return
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

        @QtCore.Slot()
        def run(self) -> None:
            try:
                results = []
                timeout_seconds = max(
                    30.0,
                    float(os.environ.get("CWS_CONVERSION_TIMEOUT_SECONDS", "900")),
                )
                for index, source in enumerate(self.files, start=1):
                    if self._cancel_requested:
                        raise RuntimeError("Conversie door gebruiker geannuleerd")
                    base_percent = int(((index - 1) / max(1, len(self.files))) * 100)
                    self.progress.emit(base_percent, f"{index}/{len(self.files)} · {source.name} voorbereiden")
                    with tempfile.TemporaryDirectory(prefix="cws-conversion-job-") as folder:
                        job_path = Path(folder) / "job.json"
                        result_path = Path(folder) / "result.json"
                        log_path = Path(folder) / "worker.log"
                        job_path.write_text(
                            json.dumps(
                                {
                                    "source": str(source),
                                    "output": str(self.output),
                                    "direction": self.direction,
                                    "material": self.material,
                                    "project_path": str(self.project_path or ""),
                                    "entity_id": self.entity_id,
                                },
                                ensure_ascii=False,
                            ),
                            encoding="utf-8",
                        )
                        started = time.monotonic()
                        with log_path.open("wb") as worker_log:
                            self._process = subprocess.Popen(
                                self._command(job_path, result_path),
                                stdout=worker_log,
                                stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                            )
                            while self._process.poll() is None:
                                elapsed = time.monotonic() - started
                                if self._cancel_requested:
                                    self._stop_process(self._process)
                                    raise RuntimeError("Conversie door gebruiker geannuleerd")
                                if elapsed >= timeout_seconds:
                                    self._stop_process(self._process)
                                    raise TimeoutError(
                                        f"{source.name}: worker-timeout na {timeout_seconds:.0f} s. "
                                        "Het bronbestand is niet stil blijven hangen; de native worker is gestopt."
                                    )
                                within_file = min(90, int((elapsed / timeout_seconds) * 90))
                                total_percent = min(
                                    99,
                                    base_percent + int(within_file / max(1, len(self.files))),
                                )
                                self.progress.emit(
                                    total_percent,
                                    f"{index}/{len(self.files)} · {source.name} · {elapsed:.0f} s · native worker actief",
                                )
                                time.sleep(0.25)
                        return_code = self._process.returncode
                        self._process = None
                        if not result_path.exists():
                            details = log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
                            raise RuntimeError(
                                f"Conversieworker stopte zonder resultaat (code {return_code}). {details}"
                            )
                        payload = json.loads(result_path.read_text(encoding="utf-8"))
                        if payload.get("status") != "passed":
                            raise RuntimeError(str(payload.get("error") or "Onbekende conversieworkerfout"))
                        results.append(dict(payload["result"]))
                    self.progress.emit(
                        int((index / max(1, len(self.files))) * 100),
                        f"{index}/{len(self.files)} · {source.name} afgerond",
                    )
                self.finished.emit({"status": "passed", "results": results})
            except Exception as exc:
                process = self._process
                if process is not None:
                    try:
                        self._stop_process(process)
                    except Exception:
                        pass
                    self._process = None
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
            self._selected_part_id = ""
            self._syncing_compact_bom = False
            self._build_ui()
            self._install_compact_bom()

        def _install_compact_bom(self) -> None:
            """Add a compact view over the canonical BOM used by Converteren."""
            group = QtWidgets.QGroupBox("Kleine BOM - centrale selectie")
            group.setObjectName("converterCompactBom")
            layout = QtWidgets.QVBoxLayout(group)
            layout.setContentsMargins(8, 6, 8, 8)
            layout.setSpacing(4)
            self.compact_bom_context = QtWidgets.QLabel(
                "Open een project; klik daarna een maakdeel om uitsluitend dat onderdeel te converteren."
            )
            self.compact_bom_context.setObjectName("mutedText")
            layout.addWidget(self.compact_bom_context)
            self.compact_bom = QtWidgets.QTableWidget(0, 6)
            self.compact_bom.setHorizontalHeaderLabels(
                ("Merk", "Positie", "Profiel", "Materiaal", "Lengte (mm)", "Aantal")
            )
            self.compact_bom.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.compact_bom.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
            self.compact_bom.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.compact_bom.setAlternatingRowColors(True)
            self.compact_bom.verticalHeader().setVisible(False)
            self.compact_bom.horizontalHeader().setStretchLastSection(True)
            self.compact_bom.itemSelectionChanged.connect(self._compact_bom_selection_changed)
            self.compact_bom.setMaximumHeight(142)
            layout.addWidget(self.compact_bom)
            root = self.layout()
            if root is not None:
                root.insertWidget(max(0, root.count() - 1), group)

        @staticmethod
        def _selection_part_id(workspace: Any | None, selection: Any | None) -> str:
            if workspace is None:
                return ""
            primary = str(getattr(selection, "primary_entity_id", "") or "")
            candidates = (primary,) + tuple(
                str(value) for value in (getattr(selection, "entity_ids", ()) or ()) if str(value)
            )
            for entity_id in dict.fromkeys(candidates):
                if entity_id in workspace.project.parts:
                    return entity_id
            return ""

        @staticmethod
        def _part_value(part: Any, *names: str, fallback: str = "-") -> str:
            for name in names:
                value = getattr(part, name, None)
                if value not in (None, ""):
                    return str(value)
            return fallback

        def _refresh_compact_bom(self) -> None:
            self._syncing_compact_bom = True
            try:
                self.compact_bom.setRowCount(0)
                workspace = self._workspace
                if workspace is None:
                    self.compact_bom_context.setText("Geen project geopend.")
                    return
                project = workspace.project
                selected = self._selected_part_id
                selected_part = project.parts.get(selected) if selected else None
                selected_source = getattr(selected_part, "source_identity", None)
                selected_mark = str(
                    getattr(selected_part, "assembly_mark", "")
                    or getattr(selected_source, "assembly_mark", "")
                    or ""
                )
                rows: list[tuple[str, Any]] = []
                for entity_id, part in sorted(project.parts.items()):
                    source = getattr(part, "source_identity", None)
                    mark = str(
                        getattr(part, "assembly_mark", "")
                        or getattr(source, "assembly_mark", "")
                        or ""
                    )
                    if selected_mark and mark != selected_mark:
                        continue
                    rows.append((str(entity_id), part))
                if not rows:
                    rows = [(str(entity_id), part) for entity_id, part in sorted(project.parts.items())]
                rows = rows[:24]
                self.compact_bom.setRowCount(len(rows))
                selected_row = -1
                for row, (entity_id, part) in enumerate(rows):
                    source = getattr(part, "source_identity", None)
                    mark = self._part_value(part, "assembly_mark", fallback="") or self._part_value(
                        source, "assembly_mark", fallback="-"
                    )
                    position = self._part_value(part, "part_position", fallback="") or self._part_value(
                        source, "part_position", fallback=entity_id
                    )
                    profile = self._part_value(part, "normalized_profile", "profile")
                    material = self._part_value(part, "normalized_material", "material")
                    try:
                        length = f"{float(getattr(part, 'length_mm', 0.0) or 0.0):,.0f}"
                    except (TypeError, ValueError):
                        length = "-"
                    quantity = str(int(getattr(part, "quantity", 1) or 1))
                    for column, value in enumerate((mark or "-", position, profile, material, length, quantity)):
                        item = QtWidgets.QTableWidgetItem(str(value))
                        item.setData(QtCore.Qt.ItemDataRole.UserRole, entity_id)
                        self.compact_bom.setItem(row, column, item)
                    if entity_id == selected:
                        selected_row = row
                self.compact_bom.resizeColumnsToContents()
                if selected_row >= 0:
                    self.compact_bom.selectRow(selected_row)
                    self.compact_bom.scrollToItem(self.compact_bom.item(selected_row, 0))
                    self.compact_bom_context.setText(
                        "Geselecteerd maakdeel wordt exact uit de projectbron geisoleerd en geconverteerd."
                    )
                elif rows:
                    self.compact_bom_context.setText(
                        "Selecteer een maakdeel in Viewer of klik een BOM-regel; assemblies en bouten zijn geen NC-maakdelen."
                    )
                else:
                    self.compact_bom_context.setText("Dit project bevat geen converteerbare maakdelen.")
            finally:
                self._syncing_compact_bom = False

        def _compact_bom_selection_changed(self) -> None:
            if self._syncing_compact_bom or self._workspace is None:
                return
            rows = self.compact_bom.selectionModel().selectedRows()
            if not rows:
                return
            item = self.compact_bom.item(rows[0].row(), 0)
            entity_id = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "") if item else ""
            if entity_id:
                self._workspace.interaction.select_entities((entity_id,), origin="converter_compact_bom")

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
            self.cancel_button = QtWidgets.QPushButton("Annuleren")
            self.cancel_button.setEnabled(False)
            self.cancel_button.clicked.connect(self._cancel)
            grid.addWidget(QtWidgets.QLabel("Richting"), 0, 0)
            grid.addWidget(self.direction, 1, 0)
            grid.addWidget(QtWidgets.QLabel("Materiaal"), 0, 1)
            grid.addWidget(self.material, 1, 1)
            grid.addWidget(QtWidgets.QLabel("Uitvoermap"), 0, 2)
            grid.addWidget(self.output, 1, 2)
            grid.addWidget(browse, 1, 3)
            grid.addWidget(self.run_button, 1, 4)
            grid.addWidget(self.cancel_button, 1, 5)
            self.conversion_progress = QtWidgets.QProgressBar()
            self.conversion_progress.setRange(0, 100)
            self.conversion_progress.setValue(0)
            self.conversion_progress.setFormat("Gereed")
            grid.addWidget(self.conversion_progress, 2, 0, 1, 6)
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
            self._selected_part_id = self._selection_part_id(workspace, selection)
            entity_id = str(getattr(selection, "primary_entity_id", "") or "")
            if workspace is None:
                self.selection_context.setText("Bron: losse modelbestanden")
                self._refresh_compact_bom()
                return
            entity = workspace.project.parts.get(self._selected_part_id) if self._selected_part_id else None
            name = str(getattr(entity, "part_position", "") or entity_id or "geen object geselecteerd")
            self.selection_context.setText(f"Project: {workspace.project.project_name} · Selectie: {name}")
            self.source_preview.set_caption(name)
            self.target_preview.set_caption("Doelpreview wordt na conversie bijgewerkt")
            self._refresh_compact_bom()

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
            if self._thread is not None:
                return
            project_path: Path | None = None
            files = tuple(self._files)
            if self._workspace is not None and self._selected_part_id:
                project_path = Path(self._workspace.project_path)
                files = (project_path,)
            if not files:
                message = (
                    "Selecteer eerst een maakdeel in Viewer of Kleine BOM, of voeg losse bronbestanden toe. "
                    "Assemblies en bouten kunnen niet rechtstreeks als NC-maakdeel worden geconverteerd."
                    if self._workspace is not None
                    else "Selecteer eerst bestanden."
                )
                QtWidgets.QMessageBox.information(self, "Converteren", message)
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
            validation_files = () if project_path is not None else files
            invalid = [path.name for path in validation_files if path.suffix.lower() not in expected]
            if invalid:
                QtWidgets.QMessageBox.warning(self, "Converteren", f"De gekozen richting past niet bij: {', '.join(invalid)}")
                return
            self.run_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.conversion_progress.setValue(0)
            self.conversion_progress.setFormat("Conversie starten · %p%")
            self.log.appendPlainText("Conversie gestart...")
            thread = QtCore.QThread(self)
            worker = _ConversionWorker(
                files,
                target,
                direction,
                self.material.currentText(),
                project_path=project_path,
                entity_id=self._selected_part_id,
            )
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.progress.connect(self._conversion_progress)
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

        @QtCore.Slot(int, str)
        def _conversion_progress(self, percent: int, message: str) -> None:
            value = max(0, min(100, int(percent)))
            self.conversion_progress.setValue(value)
            self.conversion_progress.setFormat(f"{message} · %p%")
            self.status.setText(message)

        def _cancel(self) -> None:
            worker = self._worker
            if worker is None:
                return
            self.cancel_button.setEnabled(False)
            self.status.setText("Conversie wordt gecontroleerd gestopt...")
            worker.request_cancel()

        @QtCore.Slot(dict)
        def _finished(self, payload: dict) -> None:
            self.run_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            outputs = []
            for row in payload.get("results", []):
                self.log.appendPlainText(f"OK  {Path(row['source']).name}")
                for output in row.get("outputs", []):
                    outputs.append(output)
                    self.log.appendPlainText(f"    {output}")
                for warning in row.get("warnings", []):
                    self.log.appendPlainText(f"WAARSCHUWING  {warning}")
            self.status.setText("Conversie succesvol afgerond")
            self.conversion_progress.setValue(100)
            self.conversion_progress.setFormat("Conversie succesvol afgerond · 100%")
            self.target_preview.set_caption(Path(outputs[-1]).name if outputs else "Conversie gereed")

        @QtCore.Slot(str)
        def _failed(self, message: str) -> None:
            self.run_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.status.setText("Conversie mislukt")
            self.conversion_progress.setFormat("Conversie gestopt of mislukt")
            self.log.appendPlainText(f"FOUT  {message}")
            QtWidgets.QMessageBox.critical(self, "Conversie mislukt", message)
else:
    class ConverterPanel:
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

__all__ = ["ConverterPanel"]
