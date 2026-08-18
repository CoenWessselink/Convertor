"""Qt production workflow surface for unified phase U4."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_convertor.integration.production_workflow import (
    DEFAULT_WORKFLOW_FORMATS,
    ProductionWorkflowCoordinator,
    ProductionWorkflowPlan,
    U4_SAFETY_FLAGS,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class ProductionWorkflowPage(QtWidgets.QWidget):
        """One production-plan/release surface over the active U3 context."""

        action_requested = QtCore.Signal(str)

        def __init__(self, application_context: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.application_context = application_context
            self.coordinator = ProductionWorkflowCoordinator(application_context)
            self._unsubscribe = None
            self._plan: ProductionWorkflowPlan | None = None
            self._build()
            self._unsubscribe = application_context.subscribe(self._context_changed, emit_current=True)

        def _build(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(8)

            top = QtWidgets.QHBoxLayout()
            title = QtWidgets.QLabel("Productieworkflow")
            title.setObjectName("workspaceTitle")
            self.context_label = QtWidgets.QLabel("Geen project geopend")
            self.context_label.setObjectName("mutedText")
            top.addWidget(title)
            top.addWidget(self.context_label, 1)
            root.addLayout(top)

            safety = QtWidgets.QLabel(
                "U4 bouwt uitsluitend gevalideerde productie-/reviewbestanden via de bestaande release-engine. "
                "Directe machine-transfer blijft gesloten."
            )
            safety.setObjectName("cwsSafety")
            safety.setWordWrap(True)
            root.addWidget(safety)

            options = QtWidgets.QGroupBox("Productieplan")
            options_layout = QtWidgets.QGridLayout(options)
            self.selection_only = QtWidgets.QCheckBox("Alleen huidige canonical selectie")
            self.selection_only.stateChanged.connect(self._invalidate_plan)
            options_layout.addWidget(self.selection_only, 0, 0, 1, 3)
            self.format_checks: dict[str, Any] = {}
            labels = {
                "nc1": "DSTV / NC1",
                "step": "STEP",
                "ifc": "IFC",
                "production_pdf": "Productie-PDF",
                "review_pdf": "Review-PDF",
                "json": "JSON",
            }
            for index, fmt in enumerate(DEFAULT_WORKFLOW_FORMATS):
                check = QtWidgets.QCheckBox(labels.get(fmt, fmt.upper()))
                check.setChecked(True)
                check.stateChanged.connect(self._invalidate_plan)
                self.format_checks[fmt] = check
                options_layout.addWidget(check, 1 + index // 3, index % 3)
            root.addWidget(options)

            destination = QtWidgets.QHBoxLayout()
            self.output = QtWidgets.QLineEdit(str(Path.home() / "CWS_Convertor_Production"))
            choose = QtWidgets.QToolButton()
            choose.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon))
            choose.setToolTip("Uitvoermap kiezen")
            choose.clicked.connect(self._choose_output)
            destination.addWidget(QtWidgets.QLabel("Uitvoermap"))
            destination.addWidget(self.output, 1)
            destination.addWidget(choose)
            root.addLayout(destination)

            self.table = QtWidgets.QTreeWidget()
            self.table.setRootIsDecorated(False)
            self.table.setAlternatingRowColors(True)
            root.addWidget(self.table, 1)

            self.blockers = QtWidgets.QPlainTextEdit()
            self.blockers.setReadOnly(True)
            self.blockers.setMaximumHeight(120)
            root.addWidget(self.blockers)

            footer = QtWidgets.QHBoxLayout()
            self.status = QtWidgets.QLabel("Maak eerst een productieplan")
            self.plan_button = QtWidgets.QPushButton("Plan controleren")
            self.plan_button.clicked.connect(self.refresh_plan)
            self.export_button = QtWidgets.QPushButton("Gevalideerd pakket bouwen")
            self.export_button.setObjectName("primaryButton")
            self.export_button.setEnabled(False)
            self.export_button.clicked.connect(self._execute)
            footer.addWidget(self.status, 1)
            footer.addWidget(self.plan_button)
            footer.addWidget(self.export_button)
            root.addLayout(footer)

        def _selected_formats(self) -> tuple[str, ...]:
            return tuple(fmt for fmt, check in self.format_checks.items() if check.isChecked())

        def _context_changed(self, snapshot: Any) -> None:
            if snapshot.project_attached:
                primary = snapshot.selection.primary_entity_id or "geen selectie"
                self.context_label.setText(
                    f"{snapshot.project_name or snapshot.project_id} · schema {snapshot.project_schema} · selectie {primary}"
                )
            else:
                self.context_label.setText("Geen project geopend")
            self._invalidate_plan()
            self.plan_button.setEnabled(snapshot.project_attached)

        def _invalidate_plan(self, *_: Any) -> None:
            self._plan = None
            self.export_button.setEnabled(False)
            if self.application_context.workspace is None:
                self.status.setText("Geen project geopend")
            else:
                self.status.setText("Productieplan moet opnieuw worden gecontroleerd")

        def _choose_output(self) -> None:
            name = QtWidgets.QFileDialog.getExistingDirectory(self, "Productie-uitvoermap", self.output.text())
            if name:
                self.output.setText(name)

        def refresh_plan(self) -> ProductionWorkflowPlan:
            plan = self.coordinator.build_plan(
                self._selected_formats(), selection_only=self.selection_only.isChecked()
            )
            self._plan = plan
            formats = plan.requested_formats
            self.table.setHeaderLabels(["Onderdeel", "Positie", *[fmt.upper() for fmt in formats], "Status"])
            self.table.clear()
            for row in plan.parts:
                item = QtWidgets.QTreeWidgetItem(self.table)
                item.setText(0, row.part_id)
                item.setText(1, row.part_position)
                for column, fmt in enumerate(formats, start=2):
                    item.setText(column, "OK" if row.allowed.get(fmt, False) else "GEBLOKKEERD")
                item.setText(2 + len(formats), "productiegereed" if row.production_ready else "review / gate")
            self.table.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
            self.blockers.setPlainText("\n".join(plan.blocking_codes) if plan.blocking_codes else "Geen blokkades in dit plan.")
            self.export_button.setEnabled(plan.can_execute)
            if plan.can_execute:
                self.status.setText(
                    f"Plan vrijgegeven · {len(plan.part_ids)} onderdeel(en) · SHA {plan.plan_sha256[:12]}"
                )
            else:
                self.status.setText(f"Plan geblokkeerd · {len(plan.blocking_codes)} blokkade(s)")
            return plan

        def _execute(self) -> None:
            plan = self._plan or self.refresh_plan()
            if not plan.can_execute:
                return
            self.export_button.setEnabled(False)
            self.status.setText("Productiepakket wordt via de bestaande release-engine gebouwd …")
            QtWidgets.QApplication.processEvents()
            try:
                receipt = self.coordinator.execute_plan(plan, self.output.text(), user="u4-qt")
                self.status.setText(
                    f"Pakket gereed · manifest {receipt.manifest_sha256[:12]} · project opslaan vereist"
                    if receipt.project_save_required
                    else f"Pakket gereed · manifest {receipt.manifest_sha256[:12]}"
                )
                self.blockers.setPlainText(
                    f"Workflow receipt: {receipt.receipt_sha256}\n"
                    f"Map: {receipt.output_root}\nZIP: {receipt.zip_path or '-'}\n"
                    "Machine-transfer uitgevoerd: NEE"
                )
            except Exception as exc:
                self.status.setText("Productieworkflow geblokkeerd of mislukt")
                self.blockers.setPlainText(f"{type(exc).__name__}: {exc}")
                QtWidgets.QMessageBox.critical(self, "Productieworkflow", f"{type(exc).__name__}: {exc}")
            finally:
                self._plan = None
                self.export_button.setEnabled(False)

        def closeEvent(self, event: Any) -> None:
            if self._unsubscribe is not None:
                self._unsubscribe()
                self._unsubscribe = None
            super().closeEvent(event)


else:
    class ProductionWorkflowPage:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["ProductionWorkflowPage"]
