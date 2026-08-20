"""Qt Export Center panel for CWS Viewer V15 T7."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.export_center import (
    ExportJobStatus,
    ExportScope,
    ExportScopeKind,
    V15ExportCenterService,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class _ExportWorker(QtCore.QObject):
        progress = QtCore.Signal(float, str)
        finished = QtCore.Signal(object)

        def __init__(self, service: V15ExportCenterService, job_id: str, output_dir: str) -> None:
            super().__init__()
            self.service = service
            self.job_id = job_id
            self.output_dir = output_dir

        @QtCore.Slot()
        def run(self) -> None:
            job = self.service.execute_job(
                self.job_id,
                self.output_dir,
                progress=lambda value, text: self.progress.emit(float(value), str(text)),
            )
            self.finished.emit(job)


    class V15ExportCenterPanel(QtWidgets.QWidget):
        status_changed = QtCore.Signal(str)

        SCOPE_ROWS = (
            ("Huidige selectie", ExportScopeKind.CURRENT_SELECTION),
            ("Onderdeel-ID's", ExportScopeKind.ENTITY_IDS),
            ("Partposities / nummers", ExportScopeKind.PART_POSITIONS),
            ("Assemblymerken", ExportScopeKind.ASSEMBLY_MARKS),
            ("Bouw-/projectfase", ExportScopeKind.PROJECT_PHASE),
            ("Revisie-delta (part-ID's)", ExportScopeKind.REVISION_DELTA),
            ("Batch / productieorder", ExportScopeKind.BATCH),
            ("Nesting-run", ExportScopeKind.NESTING_RUN),
            ("Nesting-bar", ExportScopeKind.NESTING_BAR),
            ("Volledig project — expliciet", ExportScopeKind.FULL_PROJECT),
        )

        FORMAT_ROWS = (
            ("NC1", "nc1", True),
            ("STEP", "step", True),
            ("IFC", "ifc", True),
            ("Productie-PDF", "production_pdf", True),
            ("DXF", "dxf", False),
            ("CSV", "csv", False),
            ("Label-PDF", "label_pdf", False),
            ("Preview PNG", "preview_png", False),
            ("JSON", "json", False),
        )

        def __init__(
            self,
            viewer: Any,
            project: Any,
            *,
            default_output_dir: str | Path | None = None,
            parent: Any = None,
        ) -> None:
            super().__init__(parent)
            self.viewer = viewer
            self.project = project
            self.service = V15ExportCenterService(
                project,
                selection_entity_ids=self._selected_entity_ids,
            )
            self._job_id = ""
            self._thread = None
            self._worker = None
            self._format_boxes: dict[str, Any] = {}
            self._build_ui(default_output_dir)
            if not self._selected_entity_ids():
                full_index = self.scope_combo.findData(ExportScopeKind.FULL_PROJECT.value)
                if full_index >= 0:
                    self.scope_combo.setCurrentIndex(full_index)
            self._scope_changed()

        def _build_ui(self, default_output_dir: str | Path | None) -> None:
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(7)

            header = QtWidgets.QLabel("Exporteren")
            header.setObjectName("cwsPanelTitle")
            layout.addWidget(header)
            hint = QtWidgets.QLabel("Kies wat u wilt exporteren, selecteer de formaten en voer daarna de controle uit.")
            hint.setWordWrap(True)
            layout.addWidget(hint)
            self.quick_export_button = QtWidgets.QPushButton("Controleren en direct exporteren")
            self.quick_export_button.setMinimumHeight(38)
            self.quick_export_button.setStyleSheet(
                "QPushButton { color: white; background: #0067c5; border: 1px solid #0056a5; "
                "border-radius: 4px; padding: 7px 16px; font-weight: 700; }"
                "QPushButton:hover { background: #005bab; }"
            )
            self.quick_export_button.clicked.connect(self._preflight_and_execute)
            layout.addWidget(self.quick_export_button)

            scope_group = QtWidgets.QGroupBox("1. Exportscope")
            scope_form = QtWidgets.QFormLayout(scope_group)
            self.scope_combo = QtWidgets.QComboBox()
            for label, kind in self.SCOPE_ROWS:
                self.scope_combo.addItem(label, kind.value)
            self.scope_combo.currentIndexChanged.connect(self._scope_changed)
            scope_form.addRow("Scope", self.scope_combo)
            self.scope_values = QtWidgets.QLineEdit()
            self.scope_values.setPlaceholderText("Komma- of puntkomma-gescheiden waarden")
            scope_form.addRow("Waarden", self.scope_values)
            self.recursive = QtWidgets.QCheckBox("Onderliggende assemblies meenemen")
            self.recursive.setChecked(True)
            scope_form.addRow("", self.recursive)
            layout.addWidget(scope_group)

            format_group = QtWidgets.QGroupBox("2. Formaten")
            format_layout = QtWidgets.QGridLayout(format_group)
            for index, (label, fmt, checked) in enumerate(self.FORMAT_ROWS):
                box = QtWidgets.QToolButton()
                box.setText(label)
                box.setCheckable(True)
                box.setChecked(bool(checked))
                box.setMinimumHeight(34)
                box.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
                box.setStyleSheet(
                    "QToolButton { text-align: left; padding: 6px 10px; border: 1px solid #b8c4d1; border-radius: 3px; background: white; }"
                    "QToolButton:checked { color: white; background: #0067c5; border-color: #0056a5; }"
                )
                self._format_boxes[fmt] = box
                format_layout.addWidget(box, index // 3, index % 3)
            layout.addWidget(format_group)

            output_group = QtWidgets.QGroupBox("3. Doelmap")
            output_layout = QtWidgets.QHBoxLayout(output_group)
            self.output_edit = QtWidgets.QLineEdit()
            default = Path(default_output_dir).expanduser() if default_output_dir else Path.home() / "Documents" / "CWS Exports"
            self.output_edit.setText(str(default))
            output_layout.addWidget(self.output_edit, 1)
            browse = QtWidgets.QPushButton("Kies…")
            browse.clicked.connect(self._browse)
            output_layout.addWidget(browse)
            layout.addWidget(output_group)

            actions = QtWidgets.QHBoxLayout()
            self.preflight_button = QtWidgets.QPushButton("Preflight")
            self.preflight_button.clicked.connect(self._preflight)
            actions.addWidget(self.preflight_button)
            self.export_button = QtWidgets.QPushButton("Export uitvoeren")
            self.export_button.setEnabled(False)
            self.export_button.clicked.connect(self._execute)
            actions.addWidget(self.export_button)
            self.cancel_button = QtWidgets.QPushButton("Voorbereide job annuleren")
            self.cancel_button.setEnabled(False)
            self.cancel_button.clicked.connect(self._cancel)
            actions.addWidget(self.cancel_button)
            actions.addStretch(1)
            layout.addLayout(actions)

            self.progress = QtWidgets.QProgressBar()
            self.progress.setRange(0, 1000)
            self.progress.setValue(0)
            layout.addWidget(self.progress)

            self.summary = QtWidgets.QPlainTextEdit()
            self.summary.setReadOnly(True)
            self.summary.setMinimumHeight(170)
            layout.addWidget(self.summary, 1)

        def _selected_entity_ids(self) -> tuple[str, ...]:
            controller = self.viewer.controller
            result: list[str] = []
            for node_id in controller.get_selection():
                try:
                    entity_id = str(controller.index.node(node_id).entity_id or "")
                except Exception:
                    entity_id = ""
                if entity_id and entity_id not in result:
                    result.append(entity_id)
            return tuple(result)

        def _scope_changed(self) -> None:
            kind = ExportScopeKind(str(self.scope_combo.currentData()))
            needs_values = kind not in {ExportScopeKind.CURRENT_SELECTION, ExportScopeKind.FULL_PROJECT}
            self.scope_values.setEnabled(needs_values)
            self.recursive.setEnabled(kind == ExportScopeKind.ASSEMBLY_MARKS)
            placeholders = {
                ExportScopeKind.ENTITY_IDS: "P123, P124",
                ExportScopeKind.PART_POSITIONS: "101, 102, 103",
                ExportScopeKind.ASSEMBLY_MARKS: "M001, M002",
                ExportScopeKind.PROJECT_PHASE: "Fase 1",
                ExportScopeKind.REVISION_DELTA: "part-ID's uit revisie-delta",
                ExportScopeKind.BATCH: "BATCH-01",
                ExportScopeKind.NESTING_RUN: "NEST-01",
                ExportScopeKind.NESTING_BAR: "BAR-01",
            }
            self.scope_values.setPlaceholderText(placeholders.get(kind, ""))
            self._invalidate_job("Scope gewijzigd; voer preflight opnieuw uit")

        def _invalidate_job(self, message: str = "") -> None:
            self._job_id = ""
            self.export_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            if message:
                self.status_changed.emit(message)

        def _values(self) -> tuple[str, ...]:
            text = self.scope_values.text().replace(";", ",")
            return tuple(value.strip() for value in text.split(",") if value.strip())

        def _scope(self) -> ExportScope:
            kind = ExportScopeKind(str(self.scope_combo.currentData()))
            values = self._values()
            if kind in {ExportScopeKind.ENTITY_IDS, ExportScopeKind.REVISION_DELTA}:
                return ExportScope(kind, entity_ids=values, recursive=self.recursive.isChecked())
            return ExportScope(kind, values=values, recursive=self.recursive.isChecked())

        def _formats(self) -> tuple[str, ...]:
            return tuple(fmt for fmt, box in self._format_boxes.items() if box.isChecked())

        def _browse(self) -> None:
            selected = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "Exportdoel kiezen",
                self.output_edit.text() or str(Path.home()),
            )
            if selected:
                self.output_edit.setText(selected)

        def _preflight(self) -> None:
            if ExportScopeKind(str(self.scope_combo.currentData())) == ExportScopeKind.CURRENT_SELECTION and not self._selected_entity_ids():
                full_index = self.scope_combo.findData(ExportScopeKind.FULL_PROJECT.value)
                if full_index >= 0:
                    self.scope_combo.setCurrentIndex(full_index)
                    self.summary.setPlainText("Er was geen selectie. De exportscope is gewijzigd naar Volledig project.")
            try:
                job = self.service.prepare_job(self._scope(), self._formats())
            except Exception as exc:
                self._invalidate_job()
                self.summary.setPlainText(f"Preflight fout\n{type(exc).__name__}: {exc}")
                self.status_changed.emit(f"Export-preflight fout: {type(exc).__name__}: {exc}")
                return
            self._job_id = job.job_id
            self.cancel_button.setEnabled(job.status == ExportJobStatus.READY)
            self.export_button.setEnabled(job.status == ExportJobStatus.READY)
            lines = [
                f"Job: {job.job_id}",
                f"Status: {job.status.value}",
                f"Scope hash: {job.preflight.resolution.manifest_sha256}",
                f"Preflight hash: {job.preflight.manifest_sha256}",
                f"Geselecteerde maakdelen: {len(job.preflight.resolution.selected_part_ids)}",
                "",
            ]
            if job.preflight.resolution.messages:
                lines.append("Scope-meldingen:")
                lines.extend(f"  • {item}" for item in job.preflight.resolution.messages)
                lines.append("")
            blocked_items = [item for item in job.preflight.items if not item.ready]
            if blocked_items:
                lines.append("Release blockers:")
                for item in blocked_items:
                    lines.append(f"  {item.part_position or item.part_id} [{item.part_id}]")
                    lines.extend(
                        f"    • {code}: {text}"
                        for code, text in zip(item.blocking_codes, item.messages)
                    )
            elif job.preflight.allowed:
                lines.append("Preflight groen. De runtime export voert nog een verse canonical rebuild/roundtrip uit.")
            self.summary.setPlainText("\n".join(lines))
            self.status_changed.emit(
                "Export-preflight groen" if job.preflight.allowed else "Export-preflight geblokkeerd"
            )

        def _preflight_and_execute(self) -> None:
            self._preflight()
            if self.export_button.isEnabled() and self._job_id:
                self._execute()

        def _execute(self) -> None:
            if not self._job_id:
                return
            output_dir = self.output_edit.text().strip()
            if not output_dir:
                QtWidgets.QMessageBox.warning(self, "Export Center", "Kies eerst een doelmap.")
                return
            self.export_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            self.preflight_button.setEnabled(False)
            self.quick_export_button.setEnabled(False)
            self.progress.setValue(10)
            self.status_changed.emit("Export gestart; verse releasevalidatie wordt uitgevoerd")
            thread = QtCore.QThread(self)
            worker = _ExportWorker(self.service, self._job_id, output_dir)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.progress.connect(self._progress_changed)
            worker.finished.connect(self._finished)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            self._thread = thread
            self._worker = worker
            thread.start()

        @QtCore.Slot(float, str)
        def _progress_changed(self, value: float, text: str) -> None:
            self.progress.setValue(int(max(0.0, min(1.0, value)) * 1000))
            self.status_changed.emit(text)

        @QtCore.Slot(object)
        def _finished(self, job: Any) -> None:
            self.preflight_button.setEnabled(True)
            self.quick_export_button.setEnabled(True)
            self.progress.setValue(int(float(job.progress) * 1000))
            lines = [
                self.summary.toPlainText(),
                "",
                "Runtime resultaat:",
                f"  Status: {job.status.value}",
                f"  Package: {job.package_path or '-'}",
                f"  Export manifest: {job.export_manifest_sha256 or '-'}",
            ]
            if job.error:
                lines.append(f"  Fout/blokkade: {job.error}")
            self.summary.setPlainText("\n".join(lines))
            if job.status == ExportJobStatus.COMPLETED:
                self.status_changed.emit("Export compleet en checksum-/manifestgebonden")
            else:
                self.status_changed.emit(f"Export geëindigd met status {job.status.value}")
            self._worker = None
            self._thread = None

        def _cancel(self) -> None:
            if not self._job_id:
                return
            try:
                job = self.service.cancel_job(self._job_id)
            except Exception as exc:
                self.status_changed.emit(f"Annuleren geweigerd: {exc}")
                return
            self.export_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            self.summary.appendPlainText(f"\nJob geannuleerd vóór schrijven: {job.job_id}")
            self.status_changed.emit("Exportjob geannuleerd vóór schrijven")

else:

    class V15ExportCenterPanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["V15ExportCenterPanel"]
