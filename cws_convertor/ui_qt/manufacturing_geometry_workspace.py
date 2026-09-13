from __future__ import annotations

from pathlib import Path
from copy import deepcopy
import hashlib
import json
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets

from cws_convertor.manufacturing_interpreter import (
    ManufacturingGeometryInterpreter,
    ManufacturingInterpretationRequest,
)
from cws_convertor.manufacturing_interpreter.cli import _step_inspection
from cws_convertor.manufacturing_interpreter.contracts import InterpretationConfirmation
from cws_convertor.manufacturing_interpreter.promotion import WorkbenchPromotionCoordinator
from cws_convertor.manufacturing_interpreter.isolated import analyze_step_isolated
from cws_convertor.manufacturing_interpreter.report_store import save_report
from cws_convertor.manufacturing_interpreter.recognition_cache import stable_sha256
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
        self._completed_reports: dict[str, Any] = {}
        self._selected_source_options: dict[str, Any] = {}
        self._selected_part_hash = ""
        self._selected_part_id = ""
        self.current_source = Path()
        self.current_job_id = ""
        self._submitted_source = ""
        self._submitted_generation = 0
        self._submitted_binding_hash = ""
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
        self.browse_button = QtWidgets.QPushButton("Bron openen")
        self.browse_button.setProperty("ui_test_id", "mgi.source.open")
        self.browse_button.setToolTip("Open een exacte STEP/STP BREP-bron")
        self.browse_button.clicked.connect(self._browse)
        self.analyze_button = QtWidgets.QPushButton("Analyseren")
        self.analyze_button.setObjectName("cwsPrimaryButton")
        self.analyze_button.setProperty("ui_test_id", "mgi.analyze")
        self.analyze_button.setToolTip("Start read-only manufacturing geometry analysis")
        self.analyze_button.clicked.connect(self.analyze_current_source)
        self.cancel_button = QtWidgets.QPushButton("Annuleren")
        self.cancel_button.setProperty("ui_test_id", "mgi.cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_analysis)
        self.retry_button = QtWidgets.QPushButton("Opnieuw")
        self.retry_button.setProperty("ui_test_id", "mgi.retry")
        self.retry_button.setEnabled(False)
        self.retry_button.clicked.connect(self.retry_analysis)
        self.save_button = QtWidgets.QPushButton("Evidence opslaan")
        self.save_button.setProperty("ui_test_id", "mgi.evidence.save")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save)
        source_bar.addWidget(self.source_edit, 1)
        source_bar.addWidget(self.browse_button)
        source_bar.addWidget(self.analyze_button)
        source_bar.addWidget(self.cancel_button)
        source_bar.addWidget(self.retry_button)
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
        self.feature_table = self._table(["Feature", "Geometrie", "Semantiek", "Matchscore", "Proof"])
        self.feature_table.setProperty("ui_test_id", "mgi.features.table")
        self.feature_table.itemSelectionChanged.connect(self._feature_selected)
        self.hypothesis_table = self._table(["Hypothese", "Features", "Unknown", "Proof", "Score"])
        self.output_table = self._table(["Target", "Status", "Lossless", "Roundtrip", "Blockers"])
        self.proof_table = self._table(["Proof metric", "Waarde"])
        self.tabs.addTab(self.foundation_table, "Foundation")
        self.tabs.addTab(self.feature_table, "Features")
        self.tabs.addTab(self.hypothesis_table, "Hypotheses")
        self.tabs.addTab(self.output_table, "Representability")
        self.tabs.addTab(self.proof_table, "Residual proof")
        self.section_table = self._table(["Station (mm)", "Meting", "Oppervlak (mm²)", "Omtrek (mm)", "Holtes", "Ixx (mm⁴)", "Iyy (mm⁴)", "Reden"])
        self.catalogue_table = self._table(["Kandidaat", "Contourbewijs", "Ontbreekt (mm²)", "Extra (mm²)", "Afstandsteekproef (mm)", "Catalogusbron"])
        self.material_table = self._table(["Eigenschap / bron", "Waarde"])
        self.body_table = self._table(["Bronbody-occurrence", "Soort", "Geometrie", "Volume (mm³)", "Profiel", "Fysiek maakdeel bewezen"])
        for table, name, identity in ((self.section_table, "Doorsneden", "mgi.sections.table"),
                                       (self.catalogue_table, "Profielbewijs", "mgi.catalogue.table"),
                                       (self.material_table, "Materiaalbronnen", "mgi.material.table"),
                                       (self.body_table, "Bronbodies", "mgi.bodies.table")):
            table.setProperty("ui_test_id", identity)
            self.tabs.addTab(table, name)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        root.addWidget(splitter, 1)

        footer = QtWidgets.QHBoxLayout()
        self.cache_label = QtWidgets.QLabel("Cache: 0 warm / 0 cold")
        self.source_gate_label = QtWidgets.QLabel("Bron-gate: niet uitgevoerd")
        self.promote_button = QtWidgets.QPushButton("Bevestigen en naar Part Workbench")
        self.promote_button.setProperty("ui_test_id", "mgi.promote")
        self.promote_button.setToolTip("Promoveer uitsluitend een bevestigde, actuele en bewezen hypothese")
        self.promote_button.setEnabled(False)
        self.promote_button.clicked.connect(self._promote)
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

    def set_context(self, snapshot: Any, selection: Any = None) -> None:
        """Bind exactly one existing selected part, never a geometry-list index."""
        self.project = getattr(snapshot, "project", None)
        self._selected_source_options = {}
        self._selected_part_hash = ""
        self._selected_part_id = ""
        ids = tuple(getattr(selection, "entity_ids", ()) or ())
        parts = getattr(self.project, "parts", {})
        if len(ids) == 1 and ids[0] in parts:
            part = parts[ids[0]]
            record = self.project.sources.get(part.source_identity.source_file_id)
            session = getattr(snapshot, "session", None)
            path = getattr(session, "source_paths", {}).get(part.source_identity.source_file_id)
            if record is not None and path and str(part.source_identity.source_format).upper() in {"STEP", "STP"}:
                from cws_convertor.manufacturing_interpreter.material_evidence import material_evidence_from_part
                self.source_edit.setText(str(path))
                self._selected_part_id = part.internal_id
                self._selected_part_hash = stable_sha256(part.base_to_dict())
                self._selected_source_options = {
                    "source_part": deepcopy(part.base_to_dict()), "source_record": deepcopy(record.to_dict()),
                    "source_sha256": part.source_identity.source_sha256,
                    "material_evidence": material_evidence_from_part(part),
                    "project_part_link": (("project_part_id", part.internal_id),
                                          ("occurrence_id", part.source_identity.occurrence_id)),
                }
        self.promote_button.setEnabled(False)

    def _binding_current(self) -> bool:
        if not self._selected_part_id:
            return not self._selected_source_options
        part = getattr(self.project, "parts", {}).get(self._selected_part_id)
        return part is not None and stable_sha256(part.base_to_dict()) == self._selected_part_hash

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
        self._submitted_source = str(source.resolve())
        self._submitted_binding_hash = stable_sha256(self._selected_source_options)
        self.current_job_id = self.job_manager.submit(
            "manufacturing-geometry-interpretation-v3",
            self._analyze_job,
            source,
            deepcopy(self._selected_source_options),
            description=f"MGI V3 analyse {source.name}",
            timeout=120.0,
            max_retries=1,
            resource_budget={"workers": 1, "memory_mb": 2048},
        )
        self._submitted_generation = self.job_manager.get(self.current_job_id).generation
        self.analyze_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.retry_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Analytische topologie, secties en feature-hypotheses...")
        self.status_badge.setText("ANALYSEERT")
        self._timer.start()

    def _analyze_job(self, context: Any, source: Path, options: dict[str, Any] | None = None) -> Any:
        report = analyze_step_isolated(
            source,
            timeout_seconds=120.0,
            cancel_check=context.is_cancelled,
            **(options or {}),
        )
        context.check_cancelled()
        if not context.is_current_generation():
            raise RuntimeError("Verouderde herkenningstaak")
        self._completed_reports[context.job_id] = report
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
        self.retry_button.setEnabled(record.status in {"failed", "cancelled", "timed_out"})
        current_source = str(Path(self.source_edit.text().strip()).resolve()) if self.source_edit.text().strip() else ""
        if (
            record.generation != self._submitted_generation
            or not self.job_manager.is_current_generation(self.current_job_id)
            or current_source != self._submitted_source
            or not self._binding_current()
            or stable_sha256(self._selected_source_options) != self._submitted_binding_hash
        ):
            self._completed_reports.pop(self.current_job_id, None)
            self._completed_report = None
            self.progress.setValue(0)
            self.progress.setFormat("Verouderd jobresultaat genegeerd")
            self.status_badge.setText("STALE")
            return
        if record.status == "completed" and record.result is not None:
            report = self._completed_reports.pop(self.current_job_id, None)
            self._completed_report = None
            if report is None:
                self.progress.setValue(0)
                self.progress.setFormat("Jobresultaat bevat geen bindbaar V3-rapport")
                self.status_badge.setText("FAILED")
                return
            try:
                with Path(current_source).open("rb") as stream:
                    current_sha = hashlib.file_digest(stream, "sha256").hexdigest()
            except OSError:
                current_sha = ""
            if current_sha != report.source_sha256:
                self.status_badge.setText("STALE")
                self.progress.setFormat("Bronbestand gewijzigd vóór publicatie; analyseer opnieuw")
                return
            self.set_report(report)
        else:
            self._completed_reports.pop(self.current_job_id, None)
            self.progress.setValue(0)
            self.progress.setFormat(record.error or record.message or "Analyse mislukt")
            self.status_badge.setText("FAILED")

    def cancel_analysis(self) -> None:
        if self.current_job_id:
            self.job_manager.cancel(self.current_job_id)

    def retry_analysis(self) -> None:
        if not self.current_job_id:
            return
        self.current_job_id = self.job_manager.retry(self.current_job_id)
        record = self.job_manager.get(self.current_job_id)
        self._submitted_generation = record.generation
        self._completed_report = None
        self.retry_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.analyze_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.progress.setFormat("Analyse opnieuw gestart...")
        self._timer.start()

    def set_report(self, report: Any) -> None:
        self.current_report = report
        self.save_button.setEnabled(True)
        self.promote_button.setEnabled(report.readiness.value == "READY" and self.project is not None)
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
        self._fill(self.section_table, [
            [f"{station.position_mm:.4f}", station.status,
             f"{station.signature.area_mm2:.5f}" if station.safe else "ONBEKEND",
             f"{station.signature.perimeter_mm:.5f}" if station.safe else "ONBEKEND",
             str(station.void_count) if station.safe else "ONBEKEND",
             f"{station.moments[0]:.5f}" if station.safe else "ONBEKEND",
             f"{station.moments[1]:.5f}" if station.safe else "ONBEKEND", station.reason]
            for station in report.section_stations])
        candidates = []
        for name, encoded in report.profile.boundary_evidence:
            proof = json.loads(encoded)
            candidates.append([name, str(proof.get("status", "NOT_RUN")),
                               str(proof.get("source_minus_catalogue_mm2", "ONBEKEND")),
                               str(proof.get("catalogue_minus_source_mm2", "ONBEKEND")),
                               str(proof.get("boundary_sample_max_mm", "ONBEKEND")),
                               str(proof.get("catalogue_source", ""))])
        self._fill(self.catalogue_table, candidates or [[name, "KANDIDAAT; GEEN CONTOURBEWIJS", "", "", "", ""] for name in report.profile.candidates])
        material = report.material_evidence
        self._fill(self.material_table, [["Bewijsstatus", material.status.value], ["Materiaal", material.material or "ONBEKEND"],
            ["Grade", material.grade or "ONBEKEND"], ["Bron", material.source], ["Bronobject", material.source_entity_id],
            ["Reden", material.reason], ["Bestand SHA256", report.source_sha256],
            ["Geometriehash", report.source_geometry_hash], ["Catalogusversiehash", report.profile_database_hash],
            *[[str(k), str(v)] for k, v in material.evidence]])
        bodies = dict(report.body_inventory).get("bodies", [])
        children = {x.part_id: x for x in report.component_reports}
        self._fill(self.body_table, [[row["body_occurrence_id"], row["topology_kind"], row["status"],
            str(row["volume_mm3"]) if row["volume_mm3"] is not None else "ONBEKEND",
            children[row["body_occurrence_id"]].profile.designation if row["body_occurrence_id"] in children else "", "NEE; BRONBODY ≠ BESTELREGEL"]
            for row in bodies])
        self._update_viewer_overlay(report)
        self.report_changed.emit(report)

    def _populate_summary(self, report: Any) -> None:
        self.summary_tree.clear()
        rows = [
            ("Engine", report.engine_version),
            ("Bronobject / occurrence", report.part_id),
            ("Bronbestand SHA256", report.source_sha256),
            ("Profielbesluit", report.profile.designation or report.profile.status.value),
            ("Fabricageherkomst", "Niet bewezen door doorsnedegelijkenis"),
            ("BOM", "Bron behouden; geen automatische decompositie"),
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

    def _feature_selected(self) -> None:
        row = self.feature_table.currentRow()
        if row < 0 or self.current_report is None or row >= len(self.current_report.features):
            return
        feature_id = self.current_report.features[row].feature_id
        viewer = getattr(self.viewer_host, "viewer", self.viewer_host)
        highlighter = getattr(viewer, "set_manufacturing_overlay_highlight", None)
        if callable(highlighter):
            highlighter({"active_interpretation_feature_id": feature_id})

    def _promote(self) -> None:
        if self.current_report is None or self.project is None or not self.current_report.hypotheses:
            QtWidgets.QMessageBox.warning(self, "Promotie geblokkeerd", "Een actief project en bewezen hypothese zijn vereist.")
            return
        if not self._binding_current():
            QtWidgets.QMessageBox.warning(self, "Verouderd bewijs", "Projectonderdeel of bronrevisie gewijzigd; analyseer opnieuw.")
            return
        part = getattr(self.project, "parts", {}).get(self.current_report.part_id)
        if part is None or part.geometry_descriptor.get("source_geometry_hash") != self.current_report.source_geometry_hash:
            QtWidgets.QMessageBox.warning(self, "Bronkoppeling vereist", "Dit rapport hoort niet bij de actuele geselecteerde projectgeometrie.")
            return
        hypothesis = self.current_report.hypotheses[0]
        report_hash = stable_sha256(self.current_report)
        answer = QtWidgets.QMessageBox.question(
            self,
            "Hypothese bevestigen",
            f"Bevestig hypothese {hypothesis.hypothesis_id} en neem deze transactioneel over in de Part Workbench?",
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        confirmation = InterpretationConfirmation(
            confirmation_id=f"confirmation-{report_hash[:20]}",
            report_hash=report_hash,
            hypothesis_id=hypothesis.hypothesis_id,
            user="interactive-user",
        )
        result = WorkbenchPromotionCoordinator().promote(
            report=self.current_report,
            confirmation=confirmation,
            project=self.project,
            user="interactive-user",
            current_source_geometry_hash=self.current_report.source_geometry_hash,
            current_tolerance_policy_hash=self.current_report.tolerance_policy_hash,
            current_profile_database_hash=self.current_report.profile_database_hash,
        )
        if result.status == "PROMOTED":
            QtWidgets.QMessageBox.information(self, "Promotie voltooid", f"Workbench revisie: {result.revision_hash}")
        else:
            QtWidgets.QMessageBox.warning(self, "Promotie geblokkeerd", "\n".join(result.blockers))

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
