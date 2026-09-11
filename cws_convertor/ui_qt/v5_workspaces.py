"""Concrete V5 task surfaces backed by canonical project services."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from PySide6 import QtCore, QtWidgets

from cws_convertor.output import DocumentOutputService
from cws_convertor.ui_qt.nesting_visualization import PlateNestingVisualization


def _project(workspace: Any | None) -> Any | None:
    return getattr(workspace, "project", None)


def _text(value: Any) -> str:
    return str(value if value not in (None, "") else "-")


class _TaskPage(QtWidgets.QWidget):
    def __init__(self, number: str, title: str, subtitle: str, parent=None) -> None:
        super().__init__(parent); self._workspace = None; self._selection = None
        self.root = QtWidgets.QVBoxLayout(self); self.root.setContentsMargins(10, 10, 10, 10); self.root.setSpacing(8)
        header = QtWidgets.QFrame(); header.setObjectName("v5TaskHeader"); row = QtWidgets.QHBoxLayout(header); row.setContentsMargins(10, 7, 10, 7)
        badge = QtWidgets.QLabel(number); badge.setObjectName("screenBadge"); heading = QtWidgets.QLabel(title); heading.setObjectName("screenTitle"); context = QtWidgets.QLabel(subtitle); context.setObjectName("screenContext")
        row.addWidget(badge); row.addWidget(heading); row.addWidget(context, 1); self.root.addWidget(header)

    def set_context(self, workspace: Any | None, selection: Any | None = None) -> None:
        self._workspace, self._selection = workspace, selection


class ProjectOverviewPanel(_TaskPage):
    def __init__(self, parent=None) -> None:
        super().__init__("02", "PROJECTOVERZICHT", "Actieve projectwaarheid", parent)
        cards = QtWidgets.QHBoxLayout(); self.labels = []
        for title in ("Project", "Onderdelen", "Samenstellingen", "Bronnen"):
            label = QtWidgets.QLabel(f"{title}\n-"); label.setObjectName("summaryCard"); cards.addWidget(label); self.labels.append(label)
        self.root.addLayout(cards); self.details = QtWidgets.QPlainTextEdit(); self.details.setReadOnly(True); self.root.addWidget(self.details, 1)

    def set_context(self, workspace, selection=None) -> None:
        super().set_context(workspace, selection); project = _project(workspace)
        if project is None: self.details.setPlainText("Geen project geopend."); return
        values = (getattr(project, "project_name", "") or getattr(project, "name", "") or getattr(project, "project_id", ""), len(getattr(project, "parts", {}) or {}), len(getattr(project, "assemblies", {}) or {}), len(getattr(project, "sources", {}) or {}))
        for label, title, value in zip(self.labels, ("Project", "Onderdelen", "Samenstellingen", "Bronnen"), values): label.setText(f"{title}\n{_text(value)}")
        self.details.setPlainText(f"Project-ID: {_text(getattr(project, 'project_id', ''))}\nSchema: {_text(getattr(project, 'schema_version', ''))}\nPad: {_text(getattr(workspace, 'project_path', ''))}")


class ProjectStructurePanel(_TaskPage):
    def __init__(self, parent=None) -> None:
        super().__init__("03", "PROJECTSTRUCTUUR", "Canonieke onderdelenboom", parent); self.tree = QtWidgets.QTreeWidget(); self.tree.setHeaderLabels(("Projectitem", "Type", "Aantal")); self.root.addWidget(self.tree, 1)

    def set_context(self, workspace, selection=None) -> None:
        super().set_context(workspace, selection); self.tree.clear(); project = _project(workspace)
        if project is None: return
        root = QtWidgets.QTreeWidgetItem(self.tree, (_text(getattr(project, "project_name", "Project")), "project", ""))
        for label, name in (("Samenstellingen", "assemblies"), ("Onderdelen", "parts"), ("Bevestigers", "fasteners"), ("Lassen", "welds"), ("Inkoopdelen", "purchased_items")):
            values = getattr(project, name, {}) or {}; group = QtWidgets.QTreeWidgetItem(root, (label, "groep", str(len(values))))
            for entity_id, entity in list(values.items())[:5000]: QtWidgets.QTreeWidgetItem(group, (_text(getattr(entity, "part_position", "") or getattr(entity, "name", "") or entity_id), name[:-1], "1"))
        root.setExpanded(True)


class ProjectReviewsPanel(_TaskPage):
    def __init__(self, parent=None) -> None:
        super().__init__("10", "PROJECTREVIEWS", "Revisies en opmerkingen", parent); self.table = QtWidgets.QTreeWidget(); self.table.setHeaderLabels(("Revisie", "Datum", "Auteur", "Opmerking")); self.root.addWidget(self.table, 1)

    def set_context(self, workspace, selection=None) -> None:
        super().set_context(workspace, selection); self.table.clear(); project = _project(workspace); settings = getattr(project, "settings", {}) if project is not None else {}; reviews = settings.get("project_reviews", {}) if isinstance(settings, dict) else {}; items = reviews.items() if isinstance(reviews, dict) else enumerate(reviews or (), 1)
        for key, raw in items:
            value = raw if isinstance(raw, dict) else {}; QtWidgets.QTreeWidgetItem(self.table, (_text(key), _text(value.get("date")), _text(value.get("author")), _text(value.get("comment"))))


class PlateNestingPanel(_TaskPage):
    """Shared project/stock planner: explicit scope, no synthetic inventory."""
    def __init__(self, parent=None) -> None:
        super().__init__("15", "PLAATNESTING", "Projectvraag en actuele voorraad · planning, geen CNC-vrijgave", parent)
        self._inputs = self._plan = self._saved = None
        self._job_id = None
        self._last_pdf = None
        self._job_manager = getattr(self.window(), 'job_manager', None)
        controls = QtWidgets.QHBoxLayout()
        self.scope_combo = QtWidgets.QComboBox()
        self.scope_combo.addItem('Hele project', 'project'); self.scope_combo.addItem('Huidige selectie', 'selection')
        self.scope_combo.currentIndexChanged.connect(self._scope_changed)
        controls.addWidget(self.scope_combo)
        self.include_remnants = QtWidgets.QCheckBox('Reststukken meenemen')
        self.include_remnants.setChecked(True)
        self.include_remnants.toggled.connect(lambda _checked: self._scope_changed())
        controls.addWidget(self.include_remnants)
        self.kerf = QtWidgets.QDoubleSpinBox(); self.kerf.setRange(0, 25); self.kerf.setValue(3); self.kerf.setSuffix(' mm')
        self.margin = QtWidgets.QDoubleSpinBox(); self.margin.setRange(0, 100); self.margin.setValue(10); self.margin.setSuffix(' mm')
        for label, widget in (('Snede', self.kerf), ('Rand', self.margin)):
            controls.addWidget(QtWidgets.QLabel(label)); controls.addWidget(widget)
        controls.addStretch()
        self.run_button = QtWidgets.QPushButton('Optimaliseren'); self.run_button.setObjectName('primaryButton'); self.run_button.clicked.connect(self.solve)
        self.cancel_button = QtWidgets.QPushButton('Berekening stoppen'); self.cancel_button.setEnabled(False); self.cancel_button.clicked.connect(self._cancel_job)
        controls.addWidget(self.run_button); controls.addWidget(self.cancel_button); self.root.addLayout(controls)
        self.status = QtWidgets.QLabel('Open een project met plaatdelen.'); self.status.setWordWrap(True); self.root.addWidget(self.status)
        self.inventory = QtWidgets.QTableWidget(0, 6)
        self.inventory.setHorizontalHeaderLabels(('Voorraad-ID', 'Breedte mm', 'Hoogte mm', 'Dikte mm', 'Kwaliteit', 'Vrij aantal'))
        self.inventory.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers); self.inventory.setMaximumHeight(170)
        self.root.addWidget(self.inventory)
        add = QtWidgets.QPushButton('Werkelijke voorraadplaat toevoegen…'); add.clicked.connect(self._add_stock); self.root.addWidget(add)
        self.issues = QtWidgets.QPlainTextEdit(); self.issues.setReadOnly(True); self.issues.setMaximumHeight(95); self.root.addWidget(self.issues)
        self.sheet_combo = QtWidgets.QComboBox(); self.sheet_combo.currentIndexChanged.connect(self._show_sheet); self.root.addWidget(self.sheet_combo)
        self.visual = PlateNestingVisualization(); self.root.addWidget(self.visual, 1)
        output = QtWidgets.QHBoxLayout()
        self.reserve_button = QtWidgets.QPushButton('Actueel plan reserveren en opslaan'); self.reserve_button.clicked.connect(self._reserve)
        self.undo_button = QtWidgets.QPushButton('Reservering intrekken'); self.undo_button.clicked.connect(self._undo)
        self.pdf_button = QtWidgets.QPushButton('Planningsrapport PDF'); self.pdf_button.clicked.connect(self.export_pdf)
        self.preview_button = QtWidgets.QPushButton('Voorbeeld openen'); self.preview_button.clicked.connect(self.preview)
        for widget in (self.reserve_button, self.undo_button, self.pdf_button, self.preview_button): output.addWidget(widget)
        self.root.addLayout(output)
        self._timer = QtCore.QTimer(self); self._timer.setInterval(100); self._timer.timeout.connect(self._poll)
        self._update_buttons()

    def set_context(self, workspace, selection=None):
        previous = _project(self._workspace)
        previous_ids = tuple(getattr(self._selection, 'entity_ids', ()) or ())
        super().set_context(workspace, selection)
        if (previous is _project(workspace) and self.scope_combo.currentData() == 'selection'
                and previous_ids != tuple(getattr(selection, 'entity_ids', ()) or ())):
            self._scope_changed()
        if previous is not _project(workspace):
            self._cancel_job(); self._inputs = self._plan = self._saved = None
            self.sheet_combo.clear(); self.visual.set_plan({})
            project = _project(workspace)
            if project is not None:
                from cws_convertor.optimization.plate_nesting.project_service import verify_saved_plan
                records = list(project.settings.get('plate_nesting_runs', {}).values())
                for record in reversed(records):
                    try:
                        self._plan = verify_saved_plan(project, record); self._saved = record
                        self.include_remnants.blockSignals(True)
                        self.include_remnants.setChecked(bool(record["inputs"].get("include_remnants", True)))
                        self.include_remnants.blockSignals(False)
                        self._show_plan(); break
                    except (ValueError, KeyError, TypeError):
                        continue
        self._refresh_input()

    def _scope_changed(self):
        self._cancel_job()
        self._plan = self._saved = None
        self.sheet_combo.clear(); self.visual.set_plan({}); self._refresh_input()

    def _refresh_input(self):
        project = _project(self._workspace)
        if project is None:
            return
        from cws_convertor.optimization.plate_nesting.project_service import collect_project_input
        inputs = collect_project_input(project, scope=self.scope_combo.currentData(), entity_ids=getattr(self._selection, 'entity_ids', ()) or (), include_remnants=self.include_remnants.isChecked())
        self.inventory.setRowCount(len(inputs.stock))
        for index, stock in enumerate(inputs.stock):
            for col, value in enumerate((stock.stock_id, stock.width_mm, stock.height_mm, stock.thickness_mm, stock.grade, stock.quantity)):
                self.inventory.setItem(index, col, QtWidgets.QTableWidgetItem(str(value)))
        self.inventory.resizeColumnsToContents()
        messages = [('BLOKKADE' if r['blocking'] else 'UITGESLOTEN') + ' · ' + r['id'] + ': ' + r['reason'] for r in inputs.exclusions]
        messages += [r['id'] + ': ' + r['basis'] for r in inputs.geometry_basis if 'omhulling' in r['basis']]
        self.issues.setPlainText('\n'.join(messages) or 'Geen invoerblokkades.')
        if self._plan is None:
            self.status.setText(f'{inputs.requested_count} geldige gevraagde exemplaren · {len(inputs.blockers)} invoerblokkades · {sum(s.quantity for s in inputs.stock)} vrije voorraadplaten. Niet oplossen met verzonnen voorraad.')
        self._update_buttons()

    def solve(self):
        from uuid import uuid4
        self._bom_generation = uuid4().hex
        from cws_convertor.optimization.plate_nesting.project_service import collect_project_input, plan_project_input
        project = _project(self._workspace)
        if project is None:
            self.status.setText('Geen project geopend.'); return
        self._plan = self._saved = None; self._last_pdf = None
        self.sheet_combo.clear(); self.visual.set_plan({}); self._update_buttons()
        try:
            inputs = collect_project_input(project, scope=self.scope_combo.currentData(), entity_ids=getattr(self._selection, 'entity_ids', ()) or (), include_remnants=self.include_remnants.isChecked())
            if inputs.blockers or not inputs.demands:
                raise ValueError('Onvolledige plaatvraag; zie invoerblokkades. Geen exemplaren stil weggelaten.')
            self._inputs = inputs
            settings = {'kerf_mm': self.kerf.value(), 'edge_margin_mm': self.margin.value()}
            self._job_manager = getattr(self.window(), 'job_manager', self._job_manager)
            if self._job_manager is None:
                # Standalone panel/test host only; the composed app owns one manager.
                self._plan = plan_project_input(inputs, **settings); self._show_plan()
            else:
                def calculate(context):
                    context.stage('planning', 0.1, 'Contouren, aantallen en materiaalgebonden voorraad')
                    return plan_project_input(inputs, check_cancelled=context.check_cancelled, **settings)
                self._job_id = self._job_manager.submit('canonical-plate-nesting', calculate, project_id=project.project_id, timeout=120, resource_budget={'workers': 1})
                self.status.setText('Berekening loopt; project blijft bedienbaar.')
                self.run_button.setEnabled(False); self.cancel_button.setEnabled(True); self._timer.start()
        except (ValueError, TypeError) as exc:
            self.status.setText('GEBLOKKEERD · ' + str(exc))
            self._refresh_input()

    def _poll(self):
        if not self._job_id:
            self._timer.stop(); return
        job = self._job_manager.get(self._job_id)
        if job.status in {'queued', 'running'}:
            return
        self._timer.stop(); self._job_id = None; self.cancel_button.setEnabled(False); self.run_button.setEnabled(True)
        from cws_convertor.optimization.plate_nesting.project_service import project_binding
        project = _project(self._workspace)
        if job.status != 'completed' or project is None or project_binding(project, self._inputs.entity_ids) != self._inputs.project_binding:
            self.status.setText('Resultaat verworpen · ' + (job.error or 'Invoer gewijzigd of berekening gestopt'))
        else:
            # JobManager snapshots serialize dataclasses to plain dictionaries.
            # Rehydrate and independently validate before exposing the proposal.
            from cws_convertor.optimization.plate_nesting.canonical import PlateCutPlan, validate_canonical_plate_nesting
            try:
                plan = PlateCutPlan.from_dict(job.result) if isinstance(job.result, dict) else job.result
                validation = validate_canonical_plate_nesting(plan, self._inputs.demands, self._inputs.stock, stock_boundaries=self._inputs.boundaries)
                if not validation.passed and plan.complete:
                    raise ValueError(', '.join(validation.blocking_codes))
                self._plan = plan; self._show_plan()
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                self._plan = None
                self.status.setText('Resultaat geblokkeerd: ' + str(exc))
        self._update_buttons()

    def _cancel_job(self):
        if self._job_id and self._job_manager:
            self._job_manager.cancel(self._job_id)
            self._job_id = None
            self._timer.stop(); self.cancel_button.setEnabled(False); self.run_button.setEnabled(True)

    def _show_plan(self):
        self.sheet_combo.blockSignals(True); self.sheet_combo.clear()
        for layout in self._plan.layouts:
            p = layout.placements[0]
            self.sheet_combo.addItem(f'{layout.stock_instance_id} · {p.grade} · {p.thickness_mm:g} mm · {len(layout.placements)} delen')
        self.sheet_combo.blockSignals(False); self._show_sheet()
        requested = self._plan.placed_count + len(self._plan.unplaced_instance_ids)
        self.status.setText(f'Vraag {requested} · {self._plan.placed_count} geplaatst · {len(self._plan.unplaced_instance_ids)} niet geplaatst · ' + ('GERESERVEERDE PLANNING' if self._saved else 'VOORSTEL — nog niet gereserveerd') + ' · geen CNC-vrijgave')
        self._update_buttons()

    def _show_sheet(self):
        if not self._plan:
            return
        payload = self._plan.to_dict()
        index = self.sheet_combo.currentIndex()
        payload['layouts'] = payload['layouts'][index:index + 1] if index >= 0 else []
        raw = self._saved['inputs'] if self._saved else asdict(self._inputs)
        payload['geometries'] = {r['part_id']: r['geometry'] for r in raw['demands']}
        self.visual.set_plan(payload)

    def _update_buttons(self):
        self.reserve_button.setEnabled(self._plan is not None and self._plan.complete and self._saved is None)
        self.undo_button.setEnabled(self._saved is not None)
        self.pdf_button.setEnabled(self._saved is not None)
        self.preview_button.setEnabled(self._saved is not None)

    def _dirty(self):
        session = getattr(self._workspace, 'session', None)
        if session is not None: session.dirty = True

    def _reserve(self):
        from cws_convertor.optimization.plate_nesting.project_service import accept_project_plan
        if not self._plan: return
        try:
            self._saved = accept_project_plan(_project(self._workspace), self._inputs, self._plan)
            self._dirty(); self._show_plan(); self._refresh_input()
        except ValueError as exc:
            self.status.setText('Reserveren geblokkeerd · ' + str(exc))
            self.reserve_button.setEnabled(False)

    def _undo(self):
        from cws_convertor.optimization.plate_nesting.project_service import cancel_project_plan
        if not self._saved: return
        try:
            cancel_project_plan(_project(self._workspace), self._plan.run_id)
            self._dirty(); self._saved = self._plan = None; self.visual.set_plan({}); self.sheet_combo.clear(); self._refresh_input()
        except (ValueError, RuntimeError) as exc:
            self.status.setText('Intrekken geblokkeerd · ' + str(exc))

    def _add_stock(self):
        project = _project(self._workspace)
        if project is None: return
        dialog = QtWidgets.QDialog(self); dialog.setWindowTitle('Werkelijk beschikbare voorraadplaat')
        form = QtWidgets.QFormLayout(dialog)
        identifier = QtWidgets.QLineEdit(); grade = QtWidgets.QLineEdit(); grade.setPlaceholderText('Exacte kwaliteit, bijvoorbeeld S355J2')
        dimensions = []
        for label in ('Breedte mm', 'Hoogte mm', 'Dikte mm'):
            value = QtWidgets.QDoubleSpinBox(); value.setRange(0, 30000); value.setDecimals(3); form.addRow(label, value); dimensions.append(value)
        count = QtWidgets.QSpinBox(); count.setRange(0, 10000)
        form.addRow('Unieke voorraad-ID', identifier); form.addRow('Kwaliteit uit bron', grade); form.addRow('Werkelijk vrij aantal', count)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted: return
        from material_database import MaterialDatabase
        from cws_convertor.project.model import StockItem
        code = MaterialDatabase().resolve(grade.text().strip())
        key = identifier.text().strip()
        if not key or key in project.stock_items or not code.resolved or not count.value() or any(d.value() <= 0 for d in dimensions):
            self.status.setText('Voorraad niet toegevoegd: unieke ID, exacte kwaliteit, maten en werkelijk aantal vereist.'); return
        project.add_entity(StockItem(internal_id=key, material=code.definition.code, grade=code.definition.code, profile=f'PL{dimensions[2].value():g}', plate_size_mm=[d.value() for d in dimensions], available_quantity=count.value()))
        project.audit('plate_nesting.stock_added', entity_id=key, details={'origin': 'explicit_operator_entry', 'certificate_confirmed': False})
        self._dirty(); self._refresh_input()

    def export_pdf(self):
        if not self._saved:
            self.status.setText('Reserveer eerst een actueel geldig plan.'); return
        from cws_convertor.optimization.plate_nesting.report import export_planning_pdf
        target = Path.home() / 'Documents' / 'CWS Convertor' / 'Nesting' / f'plate_{self._plan.plan_sha256[:16]}.pdf'
        try:
            self._last_pdf = export_planning_pdf(_project(self._workspace), self._saved, target)
            self.status.setText('Planningsrapport opgeslagen: ' + str(self._last_pdf))
        except (ValueError, OSError) as exc:
            self.status.setText('Rapport geblokkeerd · ' + str(exc)); self._last_pdf = None

    def preview(self):
        self.export_pdf()  # Always revalidate freshness; never open a stale report silently.
        if self._last_pdf is not None:
            from PySide6 import QtGui
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self._last_pdf)))



class PrintCenterPanel(_TaskPage):
    def __init__(self, parent=None) -> None:
        super().__init__("20", "AFDRUKKEN / PRINT CENTER", "Centrale documentuitvoer", parent); buttons = QtWidgets.QHBoxLayout(); refresh = QtWidgets.QPushButton("Documenten vernieuwen"); refresh.clicked.connect(self.refresh); preview = QtWidgets.QPushButton("Voorbeeld openen"); preview.clicked.connect(self.preview); printing = QtWidgets.QPushButton("Afdrukken"); printing.setObjectName("primaryButton"); printing.clicked.connect(self.print_selected); buttons.addWidget(refresh); buttons.addStretch(1); buttons.addWidget(preview); buttons.addWidget(printing); self.root.addLayout(buttons); self.table = QtWidgets.QTreeWidget(); self.table.setHeaderLabels(("Document", "Type", "Producent", "Grootte", "SHA-256")); self.root.addWidget(self.table, 1); self.status = QtWidgets.QLabel("Geen document geselecteerd."); self.root.addWidget(self.status)

    def set_context(self, workspace, selection=None) -> None: super().set_context(workspace, selection); self.refresh()
    def refresh(self) -> None:
        self.table.clear(); records = DocumentOutputService.shared().discover((Path.home() / "Documents" / "CWS Convertor",))
        for record in records:
            item = QtWidgets.QTreeWidgetItem(self.table, (record.path.name, record.kind, record.producer, f"{record.bytes / 1024:.1f} KiB", record.sha256[:16])); item.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(record.path))
        self.status.setText(f"{len(records)} uitvoerdocumenten geregistreerd.")
    def _selected(self) -> Path | None:
        item = self.table.currentItem(); return Path(str(item.data(0, QtCore.Qt.ItemDataRole.UserRole))) if item is not None else None
    def preview(self) -> None:
        path = self._selected(); self.status.setText("Selecteer eerst een document." if path is None else ("Voorbeeld geopend." if DocumentOutputService.shared().preview(path) else "Voorbeeld kon niet worden geopend."))
    def print_selected(self) -> None:
        path = self._selected()
        if path is None: self.status.setText("Selecteer eerst een PDF."); return
        if path.suffix.casefold() != ".pdf": self.status.setText("Alleen PDF-documenten kunnen rechtstreeks worden afgedrukt."); return
        self.status.setText("Afdrukopdracht voltooid." if DocumentOutputService.shared().print(path, parent=self) else "Afdrukken geannuleerd.")


class ManufacturabilityPanel(_TaskPage):
    def __init__(self, parent=None) -> None:
        super().__init__("23", "MAAKBAARHEID", "Fail-closed productiegates", parent); self.progress = QtWidgets.QProgressBar(); self.progress.setRange(0, 100); self.root.addWidget(self.progress); self.table = QtWidgets.QTreeWidget(); self.table.setHeaderLabels(("Onderdeel", "Resultaat", "Toegestaan", "Blokkades")); self.root.addWidget(self.table, 1); self.status = QtWidgets.QLabel("Geen project geopend."); self.root.addWidget(self.status)
    def set_context(self, workspace, selection=None) -> None: super().set_context(workspace, selection); self.refresh()
    def refresh(self) -> None:
        self.table.clear()
        if self._workspace is None: self.progress.setValue(0); return
        from cws_convertor.ui_qt.product_workspaces import build_production_workflow_snapshot
        selected = tuple(getattr(self._selection, "entity_ids", ()) or ()); report = build_production_workflow_snapshot(self._workspace, selected)
        for part in report.part_statuses: QtWidgets.QTreeWidgetItem(self.table, (part.mark, "GESCHIKT" if part.production_ready else "NIET GESCHIKT", ", ".join(part.allowed_formats) or "-", ", ".join(part.blocking_codes) or "-"))
        percentage = int(round(100 * report.ready_part_count / max(1, report.part_count))); self.progress.setValue(percentage); self.status.setText(f"{report.ready_part_count}/{report.part_count} geschikt ({percentage}%) | machine-transfer blijft gesloten")


__all__ = ["ManufacturabilityPanel", "PlateNestingPanel", "PrintCenterPanel", "ProjectOverviewPanel", "ProjectReviewsPanel", "ProjectStructurePanel"]
