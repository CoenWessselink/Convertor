"""Editable machine, stock, plate and remnant workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtWidgets

from cws_convertor.manufacturing.machine_settings import (
    add_plate_stock,
    add_profile_stock,
    add_remnant,
    apply_machine_settings,
    parse_construsteel_machine_xml,
    project_profile_catalog,
    return_remnant_to_stock,
    set_trade_lengths,
)


def _float(value: str) -> float:
    return float(str(value).strip().replace(",", "."))


class MachineSettingsPanel(QtWidgets.QWidget):
    changed = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: Any = None
        self.persist_callback: Any = None
        root = QtWidgets.QVBoxLayout(self)
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Machine-instellingen, handelslengtes en materiaalvoorraad")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #173f67;")
        header.addWidget(title)
        header.addStretch(1)
        import_xml = QtWidgets.QPushButton("Machine-XML importeren")
        import_xml.clicked.connect(self._import_xml)
        save = QtWidgets.QPushButton("Project opslaan")
        save.clicked.connect(self._save)
        header.addWidget(import_xml)
        header.addWidget(save)
        root.addLayout(header)
        self.tabs = QtWidgets.QTabWidget()
        root.addWidget(self.tabs, 1)
        self.machine_table = self._table(("Machine", "Parameter", "Waarde", "Eenheid/bron"))
        self.tabs.addTab(self.machine_table, "Machineparameters")
        self.trade_page = self._trade_page()
        self.tabs.addTab(self.trade_page, "Handelslengtes profielen")
        self.plate_page = self._plate_page()
        self.tabs.addTab(self.plate_page, "Beschikbare platen")
        self.remnant_page = self._remnant_page()
        self.tabs.addTab(self.remnant_page, "Reststukken")
        self.tool_table = self._table(("Gereedschap", "Type", "Diameter", "Lengte", "Machine"))
        self.tabs.addTab(self.tool_table, "Gereedschappen")
        self.status = QtWidgets.QLabel("Open een project om instellingen te beheren.")
        root.addWidget(self.status)

    @staticmethod
    def _table(headers: tuple[str, ...]) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        return table

    @staticmethod
    def _line(placeholder: str, value: str = "") -> QtWidgets.QLineEdit:
        edit = QtWidgets.QLineEdit(value)
        edit.setPlaceholderText(placeholder)
        return edit

    def _trade_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        form = QtWidgets.QHBoxLayout()
        self.trade_profile = QtWidgets.QComboBox()
        self.trade_profile.setEditable(True)
        self.trade_material = self._line("Materiaal", "STEEL")
        self.trade_grade = self._line("Kwaliteit", "S355JR")
        self.trade_lengths = self._line("Lengtes in mm", "6000; 12000; 15000; 18000")
        self.trade_quantity = self._line("Aantal fysiek", "0")
        add = QtWidgets.QPushButton("Handelslengtes toevoegen")
        add.clicked.connect(self._add_trade)
        for widget in (self.trade_profile, self.trade_material, self.trade_grade, self.trade_lengths, self.trade_quantity, add):
            form.addWidget(widget)
        layout.addLayout(form)
        self.trade_table = self._table(("Profiel", "Materiaal", "Kwaliteit", "Lengte mm", "Type", "Beschikbaar"))
        layout.addWidget(self.trade_table, 1)
        return page

    def _plate_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        form = QtWidgets.QHBoxLayout()
        self.plate_material = self._line("Materiaal", "STEEL")
        self.plate_grade = self._line("Kwaliteit", "S355JR")
        self.plate_thickness = self._line("Dikte", "10")
        self.plate_width = self._line("Breedte", "2000")
        self.plate_height = self._line("Lengte", "6000")
        self.plate_quantity = self._line("Aantal", "1")
        add = QtWidgets.QPushButton("Plaat toevoegen")
        add.clicked.connect(self._add_plate)
        for widget in (self.plate_material, self.plate_grade, self.plate_thickness, self.plate_width, self.plate_height, self.plate_quantity, add):
            form.addWidget(widget)
        layout.addLayout(form)
        self.plate_table = self._table(("ID", "Materiaal", "Kwaliteit", "Dikte", "Breedte", "Lengte", "Aantal", "Locatie"))
        layout.addWidget(self.plate_table, 1)
        return page

    def _remnant_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        form = QtWidgets.QHBoxLayout()
        self.remnant_profile = QtWidgets.QComboBox()
        self.remnant_profile.setEditable(True)
        self.remnant_material = self._line("Materiaal", "STEEL")
        self.remnant_grade = self._line("Kwaliteit", "S355JR")
        self.remnant_length = self._line("Restlengte mm", "1000")
        add = QtWidgets.QPushButton("Reststuk registreren")
        add.clicked.connect(self._add_remnant)
        restore = QtWidgets.QPushButton("Terug naar beschikbare voorraad")
        restore.clicked.connect(self._restore_remnant)
        for widget in (self.remnant_profile, self.remnant_material, self.remnant_grade, self.remnant_length, add, restore):
            form.addWidget(widget)
        layout.addLayout(form)
        self.remnant_table = self._table(("ID", "Profiel", "Materiaal", "Kwaliteit", "Restlengte", "Status", "Locatie"))
        layout.addWidget(self.remnant_table, 1)
        return page

    def set_project(self, project: Any, persist_callback: Any = None) -> None:
        self.project = project
        self.persist_callback = persist_callback
        self.refresh()

    @staticmethod
    def _fill(table: QtWidgets.QTableWidget, rows: list[tuple[Any, ...]]) -> None:
        table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                table.setItem(row, column, QtWidgets.QTableWidgetItem(str(value)))

    def refresh(self) -> None:
        project = self.project
        for table in (self.machine_table, self.trade_table, self.plate_table, self.remnant_table, self.tool_table):
            table.setRowCount(0)
        self.trade_profile.clear()
        self.remnant_profile.clear()
        if project is None:
            return
        catalog = project_profile_catalog(project)
        for entry in catalog:
            self.trade_profile.addItem(entry["profile"], entry)
            self.remnant_profile.addItem(entry["profile"], entry)
        machine_rows: list[tuple[Any, ...]] = []
        for machine_id, raw in sorted(dict(getattr(project, "profile_nesting_machine_profiles", {}) or {}).items()):
            data = dict(raw)
            for name in ("kerf_mm", "head_trim_mm", "tail_trim_mm", "min_saw_angle_deg", "max_saw_angle_deg", "clamp_width_left_mm", "clamp_width_right_mm", "common_cut_policy"):
                machine_rows.append((machine_id, name, data.get(name, ""), "project / vendor XML"))
        self._fill(self.machine_table, machine_rows)
        trade_rows = [(value.get("profile_id", ""), value.get("material", ""), value.get("material_grade", ""), value.get("length_mm", ""), "handelslengte", value.get("available_quantity", "onbeperkt")) for value in dict(getattr(project, "profile_nesting_purchase_options", {}) or {}).values()]
        trade_rows += [(item.profile, item.material, item.grade, item.stock_length_mm, "fysieke voorraad", item.available_quantity) for item in project.stock_items.values() if item.stock_length_mm > 0]
        self._fill(self.trade_table, trade_rows)
        plate_rows = [(item.internal_id, item.material, item.grade, item.plate_size_mm[2] if len(item.plate_size_mm) > 2 else "", item.plate_size_mm[0] if item.plate_size_mm else "", item.plate_size_mm[1] if len(item.plate_size_mm) > 1 else "", item.available_quantity, item.location) for item in project.stock_items.values() if item.plate_size_mm]
        self._fill(self.plate_table, plate_rows)
        remnants = sorted(project.remnants.values(), key=lambda item: item.internal_id)
        self._fill(self.remnant_table, [(item.internal_id, item.profile, item.material, item.grade, item.remaining_length_mm, item.status, item.location) for item in remnants])
        for row, item in enumerate(remnants):
            self.remnant_table.item(row, 0).setData(QtCore.Qt.ItemDataRole.UserRole, item.internal_id)
        tool_rows = [(tool_id, value.get("tool_type", ""), value.get("diameter_mm", ""), value.get("length_mm", ""), ", ".join(value.get("allowed_machine_ids", []))) for tool_id, value in sorted(dict(getattr(project, "profile_nesting_tool_library", {}) or {}).items())]
        self._fill(self.tool_table, tool_rows)
        self.status.setText(f"{len(machine_rows)} machineparameters | {len(trade_rows)} profielbronnen | {len(plate_rows)} platen | {len(remnants)} reststukken")

    def _persist(self) -> None:
        if callable(self.persist_callback):
            self.persist_callback()
        self.changed.emit()
        self.refresh()

    def _save(self) -> None:
        self._persist()
        self.status.setText("Machine- en voorraadinstellingen in het project opgeslagen.")

    def _import_xml(self) -> None:
        if self.project is None:
            return
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Machine-instellingen importeren", "", "Machine XML (*.xml)")
        if not path:
            return
        try:
            imported = parse_construsteel_machine_xml(path)
            apply_machine_settings(self.project, imported)
            self._persist()
            self.status.setText(f"{imported.name} geïmporteerd: {len(imported.profile_capabilities)} profieltypen, {len(imported.tools)} gereedschappen.")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Machine-import geblokkeerd", str(exc))

    def _selected_profile(self, combo: QtWidgets.QComboBox) -> tuple[str, str]:
        data = combo.currentData()
        return (str(data.get("profile_id") or combo.currentText()), str(data.get("section_hash") or "")) if isinstance(data, dict) else (combo.currentText().strip(), "")

    def _add_trade(self) -> None:
        if self.project is None:
            return
        try:
            profile, section_hash = self._selected_profile(self.trade_profile)
            lengths = [_float(value) for value in self.trade_lengths.text().replace(",", ".").replace(";", " ").split()]
            set_trade_lengths(self.project, profile, self.trade_material.text(), self.trade_grade.text(), lengths, section_hash=section_hash)
            quantity = _float(self.trade_quantity.text() or "0")
            if quantity > 0:
                for length in lengths:
                    add_profile_stock(self.project, profile, self.trade_material.text(), self.trade_grade.text(), length, quantity, section_hash=section_hash)
            self._persist()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Handelslengte niet toegevoegd", str(exc))

    def _add_plate(self) -> None:
        if self.project is None:
            return
        try:
            add_plate_stock(self.project, self.plate_material.text(), self.plate_grade.text(), _float(self.plate_thickness.text()), _float(self.plate_width.text()), _float(self.plate_height.text()), _float(self.plate_quantity.text()))
            self._persist()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Plaat niet toegevoegd", str(exc))

    def _add_remnant(self) -> None:
        if self.project is None:
            return
        try:
            profile, _ = self._selected_profile(self.remnant_profile)
            add_remnant(self.project, profile, self.remnant_material.text(), self.remnant_grade.text(), _float(self.remnant_length.text()))
            self._persist()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Reststuk niet toegevoegd", str(exc))

    def _restore_remnant(self) -> None:
        if self.project is None:
            return
        row = self.remnant_table.currentRow()
        if row < 0:
            return
        identifier = str(self.remnant_table.item(row, 0).data(QtCore.Qt.ItemDataRole.UserRole) or self.remnant_table.item(row, 0).text())
        return_remnant_to_stock(self.project, identifier)
        self._persist()


__all__ = ["MachineSettingsPanel"]

