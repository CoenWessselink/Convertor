from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from cws_convertor.manufacturing_interpreter import (
    ManufacturingGeometryInterpreter,
    ManufacturingInterpretationRequest,
)
from cws_convertor.manufacturing_interpreter.cli import _step_inspection
from cws_convertor.manufacturing_interpreter.report_store import save_report
from cws_convertor.project.jobs import JobManager


class ManufacturingGeometryWorkspace(QtWidgets.QWidget):
    """Production MGI workspace hosted by the existing Controle surface."""

    report_changed = QtCore.Signal(object)

    def __init__(
        self,
        viewer_host: Any,
        project: Any = None,
        *,
        job_manager: JobManager | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("cwsManufacturingGeometryWorkspace")
        self.viewer_host = viewer_host
        self.project = project
        self.job_manager = job_manager or JobManager(max_workers=1)
        self._owns_job_manager = job_manager is None
        self.interpreter = ManufacturingGeometryInterpreter()
        self.current_report: Any = None
        self._completed_report: Any = None
        self.current_source = Path()
        self.current_job_id = ""
        self._build_ui()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll_job)

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        header = QtWidgets.QHBoxLayout()
        badge = QtWidgets.QLabel("MGI V3")
        badge.setObjectName("cwsMgiBadge")
        title = QtWidgets.QLabel("Manufacturing Geometry Interpreter")
        title.setObjectName("cwsWorkspaceTitle")
        self.status_badge = QtWidgets.QLabel("GEEN RAPPORT")
        self.status_badge.setObjectName("cwsMgiStatus")
        header.addWidget(badge)
        header.addWidget(title, 1)
        header.addWidget(self.status_badge)
        root.addLayout(header)

        source_bar = QtWidgets.QHBoxLayout()
        self.source_edit = QtWidgets.QLineEdit()
        self.source_edit.setPlaceholderText("Selecteer een exacte STEP/STP BREP-bron...")
        browse = QtWidgets.QPushButton("Bron openen")
        browse.clicked.connect(self._browse)
        self.analyze_button = QtWidgets.QPushButton("Analyseren")
        self.analyze_button.setObjectName("cwsPrimaryButton")
        self.analyze_button.clicked.connect(self.analyze_current_source)
        self.cancel_button = QtWidgets.QPushButton("Annuleren")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_analysis)
        self.save_button = QtWidgets.QPushButton("Evidence opslaan")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save)
        source_bar.addWidget(self.source_edit, 1)
        source_bar.addWidget(browse)
        source_bar.addWidget(self.analyze_button)
        source_bar.addWidget(self.cancel_button)
        source_bar.addWidget(self.save_button)
        root.addLayout(source_bar)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("Gereed")
        root.addWidget(self.progress)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.summary_tree = QtWidgets.QTreeWidget()
        self.summary_tree.setHeaderLabels(["Onderdeel", "Status / waarde"])
        self.summary_tree.setMinimumWidth(330)
        splitter.addWidget(self.summary_tree)

        self.tabs = QtWidgets.QTabWidget()
        self.foundation_table = self._table(["Evidence", "Waarde"])
        self.feature_table = self._table(["Feature", "Geometrie", "Semantiek", "Confidence", "Proof"])
        self.hypothesis_table = self._table(["Hypothese", "Features", "Unknown", "Proof", "Score"])
        self.output_table = self._table(["Target", "Status", "Lossless", "Roundtrip", "Blockers"])
        self.proof_table = self._table(["Proof metric", "Waarde"])
        self.tabs.addTab(self.foundation_table, "Foundation")
        self.tabs.addTab(self.feature_table, "Features")
        self.tabs.addTab(self.hypothesis_table, "Hypotheses")
        self.tabs.addTab(self.output_table, "Representability")
        self.tabs.addTab(self.proof_table, "Residual proof")
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        footer = QtWidgets.QHBoxLayout()
        self.cache_label = QtWidgets.QLabel("Cache: 0 warm / 0 cold")
        self.source_gate_label = QtWidgets.QLabel("Bron-gate: niet uitgevoerd")
        self.promote_button = QtWidgets.QPushButton("Bevestigen en naar Part Workbench")
        self.promote_button.setEnabled(False)
        footer.addWidget(self.cache_label)
        footer.addWidget(self.source_gate_label)
        footer.addStretch(1)
        footer.addWidget(self.promote_button)
        root.addLayout(footer)

        self.setStyleSheet(
            "#cwsManufacturingGeometryWorkspace{background:#0d1a24;color:#dce8f2;}"
            "#cwsMgiBadge{background:#087bc1;color:white;font-weight:800;padding:7px 12px;border-radius:3px;}"
            "#cwsWorkspaceTitle{font-size:19px;font-weight:700;color:#f4f8fb;}"
            "#cwsMgiStatus{color:#f6b83f;font-weight:700;padding:5px 10px;border:1px solid #6f5927;}"
            "QLineEdit,QTreeWidget,QTableWidget,QTabWidget::pane{background:#10212c;color:#dce8f2;border:1px solid #315165;}"
            "QHeaderView::section{background:#173446;color:#c9e7f8;padding:6px;border:1px solid #315165;}"
            "QTabBar::tab{background:#132632;color:#b9ccda;padding:8px 14px;border:1px solid #315165;}"
            "QTabBar::tab:selected{background:#087bc1;color:white;}"
            "QPushButton{background:#173446;color:#e8f3fa;border:1px solid #3f657a;padding:7px 12px;}"
            "QPushButton#cwsPrimaryButton{background:#087bc1;border-color:#1da6e8;font-weight:700;}"
            "QPushButton:disabled{color:#667985;background:#12212a;}"
            "QProgressBar{background:#08141c;color:white;border:1px solid #315165;text-align:center;}"
            "QProgressBar::chunk{background:#1da6e8;}"
        )

    @staticmethod
    def _table(headers: list[str]) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    @staticmethod
    def _fill(table: QtWidgets.QTableWidget, rows: list[list[str]]) -> None:
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                table.setItem(row_index, column_index, QtWidgets.QTableWidgetItem(value))
        table.resizeColumnsToContents()

    def set_context(self, snapshot: Any) -> None:
        self.project = getattr(snapshot, "project", self.project)

    def _browse(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Exacte BREP-bron", "", "STEP (*.step *.stp)")
        if filename:
            self.source_edit.setText(filename)

    def analyze_current_source(self) -> None:
        source = Path(self.source_edit.text().strip())
        if not source.is_file() or source.suffix.lower() not in {".step", ".stp"}:
            QtWidgets.QMessageBox.warning(self, "Bron vereist", "Selecteer een bestaande STEP/STP-bron.")
            return
        self.current_source = source
        self.current_job_id = self.job_manager.submit(
            "manufacturing-geometry-interpretation-v3",
            self._analyze_job,
            source,
            description=f"MGI V3 analyse {source.name}",
            timeout=120.0,
            max_retries=1,
            resource_budget={"workers": 1, "memory_mb": 2048},
        )
        self.analyze_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Analytische topologie, secties en feature-hypotheses...")
        self.status_badge.setText("ANALYSEERT")
        self._timer.start()

    def _analyze_job(self, context: Any, source: Path) -> Any:
        inspection = _step_inspection(source)
        report = self.interpreter.analyze(ManufacturingInterpretationRequest(inspection=inspection))
        self._completed_report = report
        return report.to_dict()

    def _poll_job(self) -> None:
        if not self.current_job_id:
            return
        record = self.job_manager.get(self.current_job_id)
        if record.status in {"queued", "running", "cancelling"}:
            return
        self._timer.stop()
        self.progress.setRange(0, 100)
        self.analyze_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if record.status == "completed" and record.result is not None:
            report = self._completed_report
            self._completed_report = None
            if report is None:
                self.progress.setValue(0)
                self.progress.setFormat("Jobresultaat bevat geen bindbaar V3-rapport")
                self.status_badge.setText("FAILED")
                return
            self.set_report(report)
        else:
            self.progress.setValue(0)
            self.progress.setFormat(record.error or record.message or "Analyse mislukt")
            self.status_badge.setText("FAILED")

    def cancel_analysis(self) -> None:
        if self.current_job_id:
            self.job_manager.cancel(self.current_job_id)

    def set_report(self, report: Any) -> None:
        self.current_report = report
        self.save_button.setEnabled(True)
        self.promote_button.setEnabled(report.readiness.value == "READY")
        self.progress.setValue(100)
        self.progress.setFormat(f"Analyse voltooid: {report.readiness.value}")
        self.status_badge.setText(report.readiness.value)
        self.source_gate_label.setText(f"Bron-gate: {report.source_gate.value}")
        self.cache_label.setText(
            f"Cache: {self.interpreter.persistent_cache_hits} warm / {self.interpreter.persistent_cache_misses} cold"
        )
        self._populate_summary(report)
        self._fill(self.foundation_table, [[key, value] for key, value in report.evidence])
        self._fill(
            self.feature_table,
            [
                [feature.feature_id, feature.geometric_type.value, feature.semantic_type.value, f"{feature.confidence_score:.3f}", feature.proof_status.value]
                for feature in report.features
            ],
        )
        self._fill(
            self.hypothesis_table,
            [
                [item.hypothesis_id, str(len(item.positive_feature_ids) + len(item.negative_feature_ids)), str(len(item.unknown_region_ids)), item.proof_status.value, f"{item.score.total:.6f}"]
                for item in report.hypotheses
            ],
        )
        self._fill(
            self.output_table,
            [
                [target.target, target.status.value, str(target.lossless), str(target.roundtrip_available), ", ".join(target.blockers)]
                for target in (report.representability_report.targets if report.representability_report else ())
            ],
        )
        proof = report.equivalence
        self._fill(
            self.proof_table,
            [
                ["Status", proof.status.value],
                ["Source - reconstruction", f"{proof.source_minus_reconstruction_mm3:.9f} mm3"],
                ["Reconstruction - source", f"{proof.reconstruction_minus_source_mm3:.9f} mm3"],
                ["Boundary p95", f"{proof.boundary_distance_p95_mm:.6f} mm"],
                ["Boundary max", f"{proof.boundary_distance_max_mm:.6f} mm"],
                ["Boolean kernel", proof.boolean_kernel_status],
            ],
        )
        self._update_viewer_overlay(report)
        self.report_changed.emit(report)

    def _populate_summary(self, report: Any) -> None:
        self.summary_tree.clear()
        rows = [
            ("Engine", report.engine_version),
            ("Readiness", report.readiness.value),
            ("Analytische groepen", str(len(report.topology.analytic_groups) if report.topology else 0)),
            ("Sectiestations", str(len(report.section_stations))),
            ("Extrusieregio's", str(len(report.extrusion_regions))),
            ("Features", str(len(report.features))),
            ("Hypotheses", str(len(report.hypotheses))),
            ("Blockers", str(len(report.blockers))),
        ]
        for key, value in rows:
            self.summary_tree.addTopLevelItem(QtWidgets.QTreeWidgetItem([key, value]))

    def _update_viewer_overlay(self, report: Any) -> None:
        viewer = getattr(self.viewer_host, "viewer", self.viewer_host)
        payload = {
            "source_geometry_hash": report.source_geometry_hash,
            "frame": report.manufacturing_frame.frame_id if report.manufacturing_frame else "",
            "features": [
                {
                    "feature_id": feature.feature_id,
                    "semantic_type": feature.semantic_type.value,
                    "parameters": dict(feature.parameters),
                }
                for feature in report.features
            ],
            "residual_components": [component.component_id for component in (report.residual_report.components if report.residual_report else ())],
        }
        setter = getattr(viewer, "set_manufacturing_overlay", None)
        if callable(setter):
            setter(payload)
        visible = getattr(viewer, "set_overlay_visible", None) or getattr(viewer, "set_overlay_enabled", None)
        if callable(visible):
            visible(True)

    def _save(self) -> None:
        if self.current_report is None:
            return
        default = self.current_source.with_suffix(".manufacturing-v3.json") if self.current_source else Path("manufacturing-v3.json")
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Evidence opslaan", str(default), "JSON (*.json)")
        if filename:
            save_report(self.current_report, filename)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._owns_job_manager:
            self.job_manager.shutdown(wait=False, cancel_pending=True)
        super().closeEvent(event)


__all__ = ["ManufacturingGeometryWorkspace"]
