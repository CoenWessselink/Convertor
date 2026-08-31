"""Concrete V5 task surfaces backed by canonical project services."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from PySide6 import QtCore, QtWidgets

from cws_convertor.optimization.plate_nesting import PlatePart, StockPlate, solve_plate_nesting, validate_plate_nesting
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
    def __init__(self, parent=None) -> None:
        super().__init__("15", "OPTIMALISATIE - PLATE NESTING", "Deterministische plaatindeling", parent)
        controls = QtWidgets.QHBoxLayout(); self.stock_w = QtWidgets.QDoubleSpinBox(); self.stock_w.setRange(100, 30000); self.stock_w.setValue(3000); self.stock_h = QtWidgets.QDoubleSpinBox(); self.stock_h.setRange(100, 10000); self.stock_h.setValue(1500); self.kerf = QtWidgets.QDoubleSpinBox(); self.kerf.setRange(0, 25); self.kerf.setValue(3); self.margin = QtWidgets.QDoubleSpinBox(); self.margin.setRange(0, 100); self.margin.setValue(10)
        for label, widget in (("Plaatbreedte", self.stock_w), ("Plaathoogte", self.stock_h), ("Snede", self.kerf), ("Rand", self.margin)): controls.addWidget(QtWidgets.QLabel(label)); controls.addWidget(widget)
        run = QtWidgets.QPushButton("Optimaliseren"); run.setObjectName("primaryButton"); run.clicked.connect(self.solve); controls.addWidget(run); self.root.addLayout(controls)
        self.status = QtWidgets.QLabel("Open een project met plaatdelen."); self.root.addWidget(self.status); self.visual = PlateNestingVisualization(); self.root.addWidget(self.visual, 1)
        output = QtWidgets.QHBoxLayout(); export = QtWidgets.QPushButton("PDF genereren"); export.clicked.connect(self.export_pdf); preview = QtWidgets.QPushButton("Voorbeeld openen"); preview.clicked.connect(self.preview); output.addStretch(1); output.addWidget(export); output.addWidget(preview); self.root.addLayout(output); self._last_pdf = None

    @staticmethod
    def _plate(part_id: str, part: Any) -> PlatePart | None:
        profile = str(getattr(part, "normalized_profile", "") or getattr(part, "profile_designation", "") or getattr(part, "profile", "")); numbers = [float(value.replace(",", ".")) for value in re.findall(r"\d+(?:[\.,]\d+)?", profile)]
        if not any(token in profile.upper() for token in ("PL", "PLAAT", "STRIP", "FL")) or len(numbers) < 2: return None
        thickness, width = numbers[0], numbers[1]; length = float(getattr(part, "length_mm", 0.) or getattr(part, "length", 0.) or 0.)
        if width <= 0 or length <= 0 or thickness <= 0: return None
        return PlatePart(str(part_id), length, width, max(1, int(getattr(part, "quantity", 1) or 1)), True)

    def solve(self) -> None:
        project = _project(self._workspace); parts = [] if project is None else [item for item in (self._plate(str(part_id), part) for part_id, part in (getattr(project, "parts", {}) or {}).items()) if item is not None]
        if not parts: self.status.setText("Geen plaatdelen met bewezen lengte/breedte gevonden; er wordt niets verzonnen."); self.visual.set_plan({}); return
        plan = solve_plate_nesting(parts, (StockPlate("PLATE_LINE", self.stock_w.value(), self.stock_h.value(), max(1, len(parts) * 2)),), kerf_mm=self.kerf.value(), margin_mm=self.margin.value()); validation = validate_plate_nesting(plan); payload = asdict(plan); self.visual.set_plan(payload); self.status.setText(f"{plan.placed_count} geplaatst | {len(plan.unplaced_instance_ids)} niet geplaatst | {'GELDIG' if validation.passed else 'GEBLOKKEERD'}")
        settings = getattr(project, "settings", None)
        if isinstance(settings, dict): settings.setdefault("plate_nesting_runs", {})[datetime.now(timezone.utc).isoformat()] = {"plan": payload, "validation": asdict(validation)}

    def export_pdf(self) -> None:
        target = Path.home() / "Documents" / "CWS Convertor" / "Nesting" / "plate_nesting.pdf"; self._last_pdf = DocumentOutputService.shared().export_widget_pdf(self.visual, target, title="CWS Plate Nesting").path; self.status.setText(f"PDF opgeslagen: {self._last_pdf}")

    def preview(self) -> None:
        if self._last_pdf is None: self.export_pdf()
        if self._last_pdf is not None: DocumentOutputService.shared().preview(self._last_pdf)


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
