"""Compact project-aware edit and drawing workspaces for the U4 shell."""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    def _selection_id(selection: Any | None) -> str:
        if selection is None:
            return ""
        if isinstance(selection, dict):
            return str(selection.get("primary_entity_id") or selection.get("entity_id") or "")
        return str(getattr(selection, "primary_entity_id", "") or getattr(selection, "entity_id", "") or "")

    def _workspace_entity(context: Any, selection: Any | None) -> tuple[Any | None, Any | None, str]:
        workspace = context if hasattr(context, "project") else getattr(context, "workspace", None)
        entity_id = _selection_id(selection)
        if not entity_id and isinstance(context, dict):
            entity_id = _selection_id(context.get("selection") or context)
        entity = None
        if workspace is not None and entity_id:
            project = workspace.project
            for collection in (project.parts, project.assemblies, project.purchased_items, project.fasteners, project.welds):
                if entity_id in collection:
                    entity = collection[entity_id]
                    break
        return workspace, entity, entity_id

    def _value(entity: Any | None, *names: str, default: str = "") -> str:
        for name in names:
            value = getattr(entity, name, None) if entity is not None else None
            if value not in (None, ""):
                return str(value)
        return default

    class _LegacyEditWorkspacePanel(QtWidgets.QWidget):
        """Part-first editing that leaves the shared Viewer V15 readable."""

        action_requested = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsEditFunctionalPanel")
            self.setMinimumHeight(340)
            self.setMaximumHeight(540)
            self._workspace = self._entity = None
            self._entity_id = ""
            try:
                from profile_database import ProfileDatabase
                from material_database import MaterialDatabase

                self._profile_database = ProfileDatabase()
                self._material_database = MaterialDatabase()
            except Exception:
                self._profile_database = self._material_database = None
            self._build()

        def _build(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(12, 9, 12, 9)
            root.setSpacing(7)
            heading = QtWidgets.QHBoxLayout()
            self.title = QtWidgets.QLabel("Bewerken")
            self.title.setObjectName("workspaceTitle")
            self.context = QtWidgets.QLabel("Selecteer een onderdeel in Viewer of modelstructuur")
            self.context.setObjectName("mutedText")
            live = QtWidgets.QLabel("●  Live gekoppeld aan Viewer V15")
            live.setObjectName("liveStatus")
            heading.addWidget(self.title)
            heading.addWidget(self.context, 1)
            heading.addWidget(live)
            root.addLayout(heading)

            self.tabs = QtWidgets.QTabWidget()
            self.tabs.setDocumentMode(True)
            root.addWidget(self.tabs, 1)
            general = QtWidgets.QWidget()
            grid = QtWidgets.QGridLayout(general)
            grid.setContentsMargins(8, 8, 8, 8)
            self.part_id = QtWidgets.QLineEdit()
            self.part_id.setReadOnly(True)
            self.profile = QtWidgets.QComboBox()
            self.profile.setEditable(True)
            profile_names = [profile.designation for profile in getattr(self._profile_database, "profiles", ())]
            self.profile.addItems(["", *sorted(profile_names)])
            self.material = QtWidgets.QComboBox()
            self.material.setEditable(True)
            material_names = [material.code for material in getattr(self._material_database, "materials", ())]
            self.material.addItems(["", *sorted(material_names)])
            self.length = QtWidgets.QLineEdit()
            self.length.setReadOnly(True)
            self.description = QtWidgets.QLineEdit()
            for index, (label, widget) in enumerate((("Part ID", self.part_id), ("Profiel", self.profile), ("Materiaal", self.material), ("Lengte", self.length), ("Omschrijving", self.description))):
                row, column = divmod(index, 3)
                grid.addWidget(QtWidgets.QLabel(label), row * 2, column)
                grid.addWidget(widget, row * 2 + 1, column)
            for column in range(3):
                grid.setColumnStretch(column, 1)
            self.tabs.addTab(general, "Algemeen")

            recognition = QtWidgets.QWidget()
            recognition_layout = QtWidgets.QVBoxLayout(recognition)
            recognition_layout.setContentsMargins(8, 8, 8, 8)
            self.recognition_state = QtWidgets.QLabel("Selecteer een onderdeel voor profiel- en materiaalherkenning")
            self.recognition_state.setWordWrap(True)
            self.recognition_state.setObjectName("safetyStatus")
            recognition_layout.addWidget(self.recognition_state)
            recognition_tools = QtWidgets.QHBoxLayout()
            self.profile_search = QtWidgets.QLineEdit()
            self.profile_search.setPlaceholderText("Zoek profiel, familie of norm")
            self.profile_search.setClearButtonEnabled(True)
            self.profile_search.textChanged.connect(self._refresh_profile_suggestions)
            self.confirm_profile = QtWidgets.QPushButton("Geselecteerd profiel handmatig bevestigen")
            self.confirm_profile.clicked.connect(self._confirm_profile_selection)
            recognition_tools.addWidget(self.profile_search, 1)
            recognition_tools.addWidget(self.confirm_profile)
            recognition_layout.addLayout(recognition_tools)
            self.profile_matches = QtWidgets.QTableWidget(0, 6)
            self.profile_matches.setHorizontalHeaderLabels(("Profiel", "Type", "Familie", "h", "b", "kg/m"))
            self.profile_matches.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.profile_matches.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
            self.profile_matches.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.profile_matches.verticalHeader().hide()
            self.profile_matches.horizontalHeader().setStretchLastSection(True)
            self.profile_matches.itemDoubleClicked.connect(lambda _item: self._confirm_profile_selection())
            recognition_layout.addWidget(self.profile_matches, 1)
            self.tabs.addTab(recognition, "Profielherkenning")
            self._refresh_profile_suggestions()

            operations = QtWidgets.QWidget()
            operation_layout = QtWidgets.QVBoxLayout(operations)
            operation_layout.setContentsMargins(8, 8, 8, 8)
            tools = QtWidgets.QHBoxLayout()
            self.add_operation = QtWidgets.QPushButton("＋ Toevoegen")
            self.delete_operation = QtWidgets.QPushButton("Verwijderen")
            self.duplicate_operation = QtWidgets.QPushButton("Dupliceren")
            self.validate = QtWidgets.QPushButton("Valideren")
            for button in (self.add_operation, self.delete_operation, self.duplicate_operation, self.validate):
                tools.addWidget(button)
            tools.addStretch(1)
            operation_layout.addLayout(tools)
            self.features = QtWidgets.QTableWidget(0, 10)
            self.features.setHorizontalHeaderLabels(["#", "Type", "Aanzicht", "X (mm)", "Y (mm)", "Referentie", "Maat", "Diepte", "Omschrijving", "Status"])
            self.features.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.features.setAlternatingRowColors(True)
            self.features.horizontalHeader().setStretchLastSection(True)
            self.features.verticalHeader().hide()
            operation_layout.addWidget(self.features, 1)
            self.tabs.addTab(operations, "Bewerkingen")

            footer = QtWidgets.QHBoxLayout()
            self.status = QtWidgets.QLabel("Geen onderdeel geselecteerd")
            self.status.setObjectName("mutedText")
            self.save = QtWidgets.QPushButton("Opslaan")
            self.save.setObjectName("primaryButton")
            self.save.setEnabled(False)
            footer.addWidget(self.status, 1)
            footer.addWidget(self.save)
            root.addLayout(footer)
            self.add_operation.clicked.connect(self._add_row)
            self.delete_operation.clicked.connect(self._delete_row)
            self.duplicate_operation.clicked.connect(self._duplicate_row)
            self.validate.clicked.connect(self._validate)
            self.save.clicked.connect(self._save)

        def set_context(self, context: object, selection: object | None = None) -> None:
            self._selection = selection
            workspace, entity, entity_id = _workspace_entity(context, selection)
            if workspace is None and type(context).__name__ == "UnifiedUiContextSnapshot":
                return
            self._workspace, self._entity, self._entity_id = workspace, entity, entity_id
            entity = self._entity
            self.part_id.setText(_value(entity, "part_position", "mark", default=self._entity_id))
            self.profile.setCurrentText(_value(entity, "normalized_profile", "profile", "profile_name"))
            self.material.setCurrentText(_value(entity, "normalized_material", "material", "material_name"))
            length = _value(entity, "length_mm", "length")
            self.length.setText(f"{float(length):,.3f} mm" if length else "")
            self.description.setText(_value(entity, "description", "name"))
            name = self.part_id.text() or "Geen onderdeel"
            self.title.setText(f"Bewerken - {name}" if self._entity_id else "Bewerken")
            self.context.setText("Selectie, eigenschappen en Viewer zijn gesynchroniseerd" if entity is not None else "Selecteer een maakdeel om te bewerken")
            self.save.setEnabled(entity is not None)
            self._populate_features(entity)
            self._update_recognition_state(entity)

        def _update_recognition_state(self, entity: Any | None) -> None:
            if entity is None:
                self.recognition_state.setText("Selecteer een onderdeel voor profiel- en materiaalherkenning")
                return
            from cws_convertor.project.classification import normalize_profile
            profile_value = normalize_profile(_value(entity, "normalized_profile", "profile"))
            material_value = _value(entity, "normalized_material", "material_grade", "material")
            profile_match = self._profile_database.find(profile_value) if self._profile_database and profile_value else None
            material_matches = []
            if self._material_database and material_value:
                from material_database import normalise_material
                key = normalise_material(material_value)
                material_matches = [item for item in self._material_database.materials if key in item.search_names]
            profile_confidence = 1.0 if profile_match is not None else float(getattr(entity, "profile_confidence", 0.0) or 0.0)
            material_confidence = 1.0 if material_matches else float(getattr(entity, "material_confidence", 0.0) or 0.0)
            material_confidence = float(getattr(entity, "material_confidence", 0.0) or 0.0)
            profile_text = f"catalogus: {profile_match.designation}" if profile_match else "niet exact in profielendatabase"
            material_text = f"catalogus: {material_matches[0].code}" if len(material_matches) == 1 else "handmatig controleren"
            self.recognition_state.setText(
                f"Profiel {profile_value or '-'} ({profile_confidence:.0%}, {profile_text})  |  "
                f"Materiaal {material_value or '-'} ({material_confidence:.0%}, {material_text}). "
                "Niet-exacte herkenning blijft reviewplichtig."
            )
            self.profile_search.setText(profile_value)

        def _refresh_profile_suggestions(self) -> None:
            database = self._profile_database
            if database is None or not hasattr(self, "profile_matches"):
                return
            rows = database.filtered(text=self.profile_search.text().strip())[:250]
            self.profile_matches.setRowCount(len(rows))
            for row, profile in enumerate(rows):
                values = (profile.designation, profile.profile_type, profile.family, f"{profile.height:g}", f"{profile.width:g}", f"{profile.mass_kg_m:g}")
                for column, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, profile.designation)
                    self.profile_matches.setItem(row, column, item)

        def _confirm_profile_selection(self) -> None:
            row = self.profile_matches.currentRow()
            if row < 0:
                return
            item = self.profile_matches.item(row, 0)
            if item is None:
                return
            designation = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or item.text())
            self.profile.setCurrentText(designation)
            self.recognition_state.setText(
                f"{designation} handmatig gekozen. Opslaan registreert dit als 100% bevestigde cataloguskeuze."
            )

        def _populate_features(self, entity: Any | None) -> None:
            rows: list[tuple[str, ...]] = []
            profile = _value(entity, "profile", "profile_name")
            if entity is not None:
                rows.append(("1", "Basisprofiel", "3D", "—", "—", profile or "Brongeometrie", "—", "—", profile or "Basisprofiel", "OK"))
                raw = getattr(entity, "features", ()) or ()
                if isinstance(raw, dict):
                    raw = raw.values()
                for index, feature in enumerate(raw, start=2):
                    if isinstance(feature, dict):
                        kind = str(feature.get("type") or feature.get("kind") or "Bewerking")
                        description = str(feature.get("description") or feature.get("name") or kind)
                        size = str(feature.get("diameter_mm") or feature.get("size") or "—")
                    else:
                        kind, description, size = type(feature).__name__, str(feature), "—"
                    rows.append((str(index), kind, "3D", "—", "—", "Bron", size, "—", description, "Review"))
            self.features.setRowCount(len(rows))
            for row, values in enumerate(rows):
                for column, value in enumerate(values):
                    self.features.setItem(row, column, QtWidgets.QTableWidgetItem(value))
            self.status.setText(f"{len(rows)} bewerking(en)" if rows else "Geen onderdeel geselecteerd")

        def _add_row(self) -> None:
            row = self.features.rowCount()
            self.features.insertRow(row)
            values = (str(row + 1), "Gat", "Boven", "0", "0", "Referentievlak", "Ø18", "Doorlopend", "Nieuwe bewerking", "Concept")
            for column, value in enumerate(values):
                self.features.setItem(row, column, QtWidgets.QTableWidgetItem(value))
            self.features.selectRow(row)
            self.status.setText("Conceptbewerking toegevoegd; valideer voor productiegebruik")

        def _delete_row(self) -> None:
            for row in sorted({index.row() for index in self.features.selectionModel().selectedRows()}, reverse=True):
                if row > 0:
                    self.features.removeRow(row)

        def _duplicate_row(self) -> None:
            rows = self.features.selectionModel().selectedRows()
            if not rows:
                return
            source, target = rows[0].row(), self.features.rowCount()
            self.features.insertRow(target)
            for column in range(self.features.columnCount()):
                item = self.features.item(source, column)
                self.features.setItem(target, column, QtWidgets.QTableWidgetItem("" if item is None else item.text()))
            self.features.item(target, 0).setText(str(target + 1))
            self.features.selectRow(target)

        def _validate(self) -> None:
            self.status.setText("Legacy-validatie is gesloten; gebruik de actieve Part Workbench")

        def _save(self) -> None:
            QtWidgets.QMessageBox.warning(
                self,
                "Legacy Bewerken gesloten",
                "Deze diagnostische editor heeft geen write-path. Gebruik de actieve Part Workbench.",
            )

    class EditWorkspacePanel(QtWidgets.QWidget):
        """Transactional part editor coupled to the shared Project Model and Viewer V15."""

        action_requested = QtCore.Signal(str)

        _FEATURE_LABELS = {
            "hole": "Gat",
            "countersunk_hole": "Verzonken gat",
            "slot": "Sleufgat",
            "cutout": "Uitsparing",
            "end_cut": "Kopse snede",
            "miter": "Verstek",
            "scribe": "Markering",
        }
        _FEATURE_DEFAULTS = {
            "hole": {"x_mm": 0.0, "y_mm": 0.0, "diameter_mm": 18.0, "depth": "Doorlopend"},
            "countersunk_hole": {"x_mm": 0.0, "y_mm": 0.0, "diameter_mm": 18.0, "countersink_mm": 26.0, "depth": "Doorlopend"},
            "slot": {"x_mm": 0.0, "y_mm": 0.0, "length_mm": 22.0, "width_mm": 14.0, "angle_deg": 0.0, "depth": "Doorlopend"},
            "cutout": {"x_mm": 0.0, "y_mm": 0.0, "width_mm": 80.0, "height_mm": 35.0, "angle_deg": 0.0},
            "end_cut": {"angle_deg": 0.0, "reference": "Linker uiteinde"},
            "miter": {"angle_deg": 45.0, "reference": "Links + rechts"},
            "scribe": {"x_mm": 0.0, "y_mm": 0.0, "text": "Nieuwe markering"},
        }
        _WORKBENCH_FEATURE_KINDS = {
            "hole", "countersunk_hole", "slot", "cope", "cutout", "pocket", "radius", "arc",
            "chamfer", "bevel", "end_cut", "scribe",
        }

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsEditFunctionalPanel")
            self.setMinimumHeight(410)
            self.setMaximumHeight(650)
            self._workspace = self._entity = None
            self._entity_id = ""
            self._draft_features: list[dict[str, Any]] = []
            self._dirty = False
            self._loading = False
            try:
                from profile_database import ProfileDatabase
                from material_database import MaterialDatabase

                self._profile_database = ProfileDatabase()
                self._material_database = MaterialDatabase()
            except Exception:
                self._profile_database = self._material_database = None
            self._build()

        @staticmethod
        def _number(value: Any, default: float = 0.0) -> float:
            try:
                return float(str(value).replace(",", "."))
            except (TypeError, ValueError):
                return default

        @staticmethod
        def _new_spin(*, maximum: float = 1_000_000_000.0, suffix: str = "") -> Any:
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(0.0, maximum)
            spin.setDecimals(3)
            spin.setSingleStep(1.0)
            if suffix:
                spin.setSuffix(suffix)
            return spin

        def _build(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(12, 8, 12, 8)
            root.setSpacing(6)

            heading = QtWidgets.QHBoxLayout()
            self.title = QtWidgets.QLabel("Bewerken")
            self.title.setObjectName("workspaceTitle")
            self.context = QtWidgets.QLabel("Selecteer een onderdeel in Viewer, Project Explorer of BOM")
            self.context.setObjectName("mutedText")
            self.live_status = QtWidgets.QLabel("●  Centrale selectie actief")
            self.live_status.setObjectName("liveStatus")
            heading.addWidget(self.title)
            heading.addWidget(self.context, 1)
            heading.addWidget(self.live_status)
            root.addLayout(heading)

            self.tabs = QtWidgets.QTabWidget()
            self.tabs.setDocumentMode(True)
            root.addWidget(self.tabs, 1)
            self._build_general_tab()
            self._build_extra_tab()
            self._build_operations_tab()
            self.angle_table = self._build_subset_tab("Hoeken", {"cutout", "end_cut", "miter"})
            self.hole_table = self._build_subset_tab("Gaten", {"hole", "countersunk_hole", "slot"})
            self._build_codes_tab()
            self._build_prices_tab()
            self._build_times_tab()

            lifecycle = QtWidgets.QHBoxLayout()
            self.workbench_status = QtWidgets.QLabel("Part Workbench: niet gestart")
            self.workbench_status.setObjectName("mutedText")
            self.start_workbench_button = QtWidgets.QPushButton("Workbench starten")
            self.undo_workbench_button = QtWidgets.QPushButton("Ongedaan")
            self.redo_workbench_button = QtWidgets.QPushButton("Opnieuw")
            self.review_workbench_button = QtWidgets.QPushButton("Review valideren")
            self.rebuild_workbench_button = QtWidgets.QPushButton("Canonical rebuild")
            self.roundtrip_workbench_button = QtWidgets.QPushButton("4-formaat roundtrip")
            self.release_workbench_button = QtWidgets.QPushButton("Vrijgeven")
            lifecycle.addWidget(self.workbench_status, 1)
            for button in (
                self.start_workbench_button, self.undo_workbench_button,
                self.redo_workbench_button, self.review_workbench_button,
                self.rebuild_workbench_button, self.roundtrip_workbench_button,
                self.release_workbench_button,
            ):
                button.setEnabled(False)
                lifecycle.addWidget(button)
            root.addLayout(lifecycle)

            footer = QtWidgets.QHBoxLayout()
            self.status = QtWidgets.QLabel("Geen onderdeel geselecteerd")
            self.status.setObjectName("mutedText")
            self.refresh_button = QtWidgets.QPushButton("Vernieuwen")
            self.validate = QtWidgets.QPushButton("Valideren")
            self.calculate = QtWidgets.QPushButton("Berekenen")
            self.cancel = QtWidgets.QPushButton("Annuleren")
            self.save = QtWidgets.QPushButton("Opslaan")
            self.save.setObjectName("primaryButton")
            for button in (self.refresh_button, self.validate, self.calculate, self.cancel, self.save):
                button.setEnabled(False)
            footer.addWidget(self.status, 1)
            footer.addWidget(self.refresh_button)
            footer.addWidget(self.validate)
            footer.addWidget(self.calculate)
            footer.addWidget(self.cancel)
            footer.addWidget(self.save)
            root.addLayout(footer)

            self.refresh_button.clicked.connect(self.refresh_from_project)
            self.validate.clicked.connect(self.validate_draft)
            self.calculate.clicked.connect(self.calculate_draft)
            self.cancel.clicked.connect(self.cancel_changes)
            self.save.clicked.connect(self.save_changes)
            self.start_workbench_button.clicked.connect(self.start_part_workbench)
            self.undo_workbench_button.clicked.connect(self.undo_part_workbench)
            self.redo_workbench_button.clicked.connect(self.redo_part_workbench)
            self.review_workbench_button.clicked.connect(self.review_part_workbench)
            self.rebuild_workbench_button.clicked.connect(self.rebuild_part_canonical)
            self.roundtrip_workbench_button.clicked.connect(self.validate_part_roundtrips)
            self.release_workbench_button.clicked.connect(self.release_part_workbench)
            self._connect_dirty_signals()

        def _build_general_tab(self) -> None:
            general = QtWidgets.QWidget()
            grid = QtWidgets.QGridLayout(general)
            grid.setContentsMargins(8, 8, 8, 8)
            grid.setHorizontalSpacing(10)
            self.part_id = QtWidgets.QLineEdit()
            self.profile = QtWidgets.QComboBox()
            self.profile.setEditable(True)
            profile_names = [profile.designation for profile in getattr(self._profile_database, "profiles", ())]
            self.profile.addItems(["", *sorted(profile_names)])
            self.material = QtWidgets.QComboBox()
            self.material.setEditable(True)
            material_names = [material.code for material in getattr(self._material_database, "materials", ())]
            self.material.addItems(["", *sorted(material_names)])
            self.length = self._new_spin(suffix=" mm")
            self.description = QtWidgets.QLineEdit()
            self.coating = QtWidgets.QLineEdit()
            widgets = (
                ("Part ID / positie", self.part_id),
                ("Profiel", self.profile),
                ("Materiaal", self.material),
                ("Lengte", self.length),
                ("Omschrijving", self.description),
                ("Coating", self.coating),
            )
            for index, (label, widget) in enumerate(widgets):
                row, column = divmod(index, 3)
                grid.addWidget(QtWidgets.QLabel(label), row * 2, column)
                grid.addWidget(widget, row * 2 + 1, column)
            for column in range(3):
                grid.setColumnStretch(column, 1)
            self.tabs.addTab(general, "Algemeen")

        def _build_extra_tab(self) -> None:
            extra = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(extra)
            layout.setContentsMargins(8, 8, 8, 8)
            self.recognition_state = QtWidgets.QLabel("Selecteer een onderdeel voor profiel- en materiaalherkenning")
            self.recognition_state.setWordWrap(True)
            self.recognition_state.setObjectName("safetyStatus")
            layout.addWidget(self.recognition_state)
            tools = QtWidgets.QHBoxLayout()
            self.profile_search = QtWidgets.QLineEdit()
            self.profile_search.setPlaceholderText("Zoek profiel, familie of norm")
            self.profile_search.setClearButtonEnabled(True)
            self.confirm_profile = QtWidgets.QPushButton("Profiel bevestigen")
            tools.addWidget(self.profile_search, 1)
            tools.addWidget(self.confirm_profile)
            layout.addLayout(tools)
            self.profile_matches = QtWidgets.QTableWidget(0, 6)
            self.profile_matches.setHorizontalHeaderLabels(("Profiel", "Type", "Familie", "h", "b", "kg/m"))
            self.profile_matches.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.profile_matches.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
            self.profile_matches.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.profile_matches.verticalHeader().hide()
            self.profile_matches.horizontalHeader().setStretchLastSection(True)
            layout.addWidget(self.profile_matches, 1)
            self.source_info = QtWidgets.QLabel("Bron: -")
            self.source_info.setObjectName("mutedText")
            layout.addWidget(self.source_info)
            self.tabs.addTab(extra, "Extra info.")
            self.profile_search.textChanged.connect(self._refresh_profile_suggestions)
            self.confirm_profile.clicked.connect(self._confirm_profile_selection)
            self.profile_matches.itemDoubleClicked.connect(lambda _item: self._confirm_profile_selection())
            self._refresh_profile_suggestions()

        def _build_operations_tab(self) -> None:
            operations = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(operations)
            layout.setContentsMargins(8, 8, 8, 8)
            tools = QtWidgets.QHBoxLayout()
            self.add_operation = QtWidgets.QToolButton()
            self.add_operation.setText("Toevoegen")
            self.add_operation.setObjectName("editAddOperation")
            self.add_operation.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup)
            add_menu = QtWidgets.QMenu(self.add_operation)
            for kind in ("hole", "countersunk_hole", "slot", "cutout", "end_cut", "miter", "scribe"):
                action = add_menu.addAction(self._FEATURE_LABELS[kind])
                action.triggered.connect(lambda _checked=False, value=kind: self.add_feature(value))
            self.add_operation.setMenu(add_menu)
            self.add_operation.clicked.connect(lambda: self.add_feature("hole"))
            self.delete_operation = QtWidgets.QPushButton("Verwijderen")
            self.duplicate_operation = QtWidgets.QPushButton("Dupliceren")
            self.move_up = QtWidgets.QPushButton("Omhoog")
            self.move_down = QtWidgets.QPushButton("Omlaag")
            self.import_button = QtWidgets.QPushButton("Importeren")
            self.actions_button = QtWidgets.QToolButton()
            self.actions_button.setText("Acties")
            self.actions_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            actions_menu = QtWidgets.QMenu(self.actions_button)
            actions_menu.addAction("Bewerkingen importeren...", self.choose_import)
            actions_menu.addAction("Bewerkingen exporteren...", self.choose_export)
            actions_menu.addSeparator()
            actions_menu.addAction("Conceptbewerkingen verwijderen", self.remove_concepts)
            actions_menu.addAction("Opnieuw laden uit Project Model", lambda: self.refresh_from_project(force=True))
            self.actions_button.setMenu(actions_menu)
            for button in (
                self.add_operation,
                self.delete_operation,
                self.duplicate_operation,
                self.move_up,
                self.move_down,
                self.import_button,
                self.actions_button,
            ):
                tools.addWidget(button)
            tools.addStretch(1)
            layout.addLayout(tools)
            self.features = QtWidgets.QTableWidget(0, 13)
            self.features.setHorizontalHeaderLabels((
                "#", "Type", "Aanzicht", "X (mm)", "Y (mm)", "Referentie", "Maat",
                "Diepte", "Breedte", "Hoogte", "Hoek", "Omschrijving", "Status",
            ))
            self.features.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.features.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            self.features.setAlternatingRowColors(True)
            self.features.horizontalHeader().setStretchLastSection(True)
            self.features.verticalHeader().hide()
            layout.addWidget(self.features, 1)
            self.tabs.addTab(operations, "Bewerkingen")
            self.delete_operation.clicked.connect(self.delete_selected_features)
            self.duplicate_operation.clicked.connect(self.duplicate_selected_feature)
            self.move_up.clicked.connect(lambda: self.move_selected_feature(-1))
            self.move_down.clicked.connect(lambda: self.move_selected_feature(1))
            self.import_button.clicked.connect(self.choose_import)
            self.features.itemChanged.connect(self._feature_item_changed)

        def _build_subset_tab(self, title: str, kinds: set[str]) -> Any:
            page = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(page)
            layout.setContentsMargins(8, 8, 8, 8)
            help_text = QtWidgets.QLabel(
                "Dubbelklik een regel om dezelfde bewerking in de centrale bewerkingstabel te openen."
            )
            help_text.setObjectName("mutedText")
            layout.addWidget(help_text)
            table = QtWidgets.QTableWidget(0, 6)
            table.setProperty("featureKinds", tuple(sorted(kinds)))
            table.setHorizontalHeaderLabels(("#", "Type", "Positie", "Maat", "Omschrijving", "Status"))
            table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
            table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.verticalHeader().hide()
            table.horizontalHeader().setStretchLastSection(True)
            table.itemDoubleClicked.connect(lambda item, source=table: self._open_subset_feature(source, item.row()))
            layout.addWidget(table, 1)
            self.tabs.addTab(page, title)
            return table

        def _build_codes_tab(self) -> None:
            page = QtWidgets.QWidget()
            form = QtWidgets.QFormLayout(page)
            form.setContentsMargins(12, 12, 12, 12)
            self.mark_code = QtWidgets.QLineEdit()
            self.revision = QtWidgets.QLineEdit()
            self.phase = QtWidgets.QLineEdit()
            self.article_code = QtWidgets.QLineEdit()
            form.addRow("Merk / naam", self.mark_code)
            form.addRow("Revisie", self.revision)
            form.addRow("Fase", self.phase)
            form.addRow("Artikelcode", self.article_code)
            self.tabs.addTab(page, "Coderingen")

        def _build_prices_tab(self) -> None:
            page = QtWidgets.QWidget()
            form = QtWidgets.QFormLayout(page)
            form.setContentsMargins(12, 12, 12, 12)
            self.material_cost = self._new_spin(suffix=" EUR")
            self.hourly_rate = self._new_spin(maximum=100_000.0, suffix=" EUR/u")
            self.operation_cost = self._new_spin(suffix=" EUR")
            self.total_cost = self._new_spin(suffix=" EUR")
            self.total_cost.setReadOnly(True)
            form.addRow("Materiaalkosten", self.material_cost)
            form.addRow("Uurtarief", self.hourly_rate)
            form.addRow("Bewerkingskosten", self.operation_cost)
            form.addRow("Totaal", self.total_cost)
            self.tabs.addTab(page, "Prijzen")

        def _build_times_tab(self) -> None:
            page = QtWidgets.QWidget()
            form = QtWidgets.QFormLayout(page)
            form.setContentsMargins(12, 12, 12, 12)
            self.setup_minutes = self._new_spin(maximum=1_000_000.0, suffix=" min")
            self.processing_minutes = self._new_spin(maximum=1_000_000.0, suffix=" min")
            self.total_minutes = self._new_spin(maximum=1_000_000.0, suffix=" min")
            self.total_minutes.setReadOnly(True)
            form.addRow("Insteltijd", self.setup_minutes)
            form.addRow("Bewerkingstijd", self.processing_minutes)
            form.addRow("Totale tijd", self.total_minutes)
            self.tabs.addTab(page, "Bewerkingstijden")

        def _connect_dirty_signals(self) -> None:
            for widget in (
                self.part_id, self.description, self.coating, self.mark_code,
                self.revision, self.phase, self.article_code,
            ):
                widget.textEdited.connect(self.mark_dirty)
            for combo in (self.profile, self.material):
                combo.currentTextChanged.connect(self.mark_dirty)
            for spin in (
                self.length, self.material_cost, self.hourly_rate, self.operation_cost,
                self.setup_minutes, self.processing_minutes,
            ):
                spin.valueChanged.connect(self.mark_dirty)

        def set_context(self, context: object, selection: object | None = None) -> None:
            workspace, entity, entity_id = _workspace_entity(context, selection)
            if workspace is None and type(context).__name__ == "UnifiedUiContextSnapshot":
                return
            if entity_id == self._entity_id and entity is self._entity and self._dirty:
                self._workspace = workspace
                self._selection = selection
                return
            self._workspace, self._entity, self._entity_id, self._selection = workspace, entity, entity_id, selection
            self._load_entity_state()

        def _load_entity_state(self) -> None:
            self._loading = True
            try:
                entity = self._entity
                self.part_id.setText(_value(entity, "part_position", "mark", default=self._entity_id))
                self.profile.setCurrentText(_value(entity, "normalized_profile", "profile", "profile_name"))
                self.material.setCurrentText(_value(entity, "normalized_material", "material_grade", "material"))
                self.length.setValue(self._number(_value(entity, "length_mm", "length")))
                self.description.setText(_value(entity, "description", "name"))
                self.coating.setText(_value(entity, "coating"))
                self.mark_code.setText(_value(entity, "mark", "name", default=self.part_id.text()))
                self.revision.setText(_value(entity, "revision", default="A"))
                self.phase.setText(_value(entity, "phase"))
                self.article_code.setText(_value(entity, "article_code", "article_number"))
                workbench = getattr(entity, "workbench", {}) if entity is not None else {}
                workbench = workbench if isinstance(workbench, dict) else {}
                properties = getattr(entity, "properties", {}) if entity is not None else {}
                properties = properties if isinstance(properties, dict) else {}
                editor = properties.get("ui_editor") if isinstance(properties.get("ui_editor"), dict) else {}
                if not editor and isinstance(workbench.get("ui_editor"), dict):
                    editor = workbench["ui_editor"]
                if "description" in editor:
                    self.description.setText(str(editor.get("description") or ""))
                if "coating" in editor:
                    self.coating.setText(str(editor.get("coating") or ""))
                if "mark" in editor:
                    self.mark_code.setText(str(editor.get("mark") or ""))
                if "revision" in editor:
                    self.revision.setText(str(editor.get("revision") or ""))
                if "phase" in editor:
                    self.phase.setText(str(editor.get("phase") or ""))
                if "article_code" in editor:
                    self.article_code.setText(str(editor.get("article_code") or ""))
                self.material_cost.setValue(self._number(editor.get("material_cost")))
                self.hourly_rate.setValue(self._number(editor.get("hourly_rate"), 75.0))
                self.operation_cost.setValue(self._number(editor.get("operation_cost")))
                self.total_cost.setValue(self._number(editor.get("total_cost")))
                self.setup_minutes.setValue(self._number(editor.get("setup_minutes")))
                self.processing_minutes.setValue(self._number(editor.get("processing_minutes")))
                self.total_minutes.setValue(self._number(editor.get("total_minutes")))
                revision = workbench.get("current_revision") if isinstance(workbench.get("current_revision"), dict) else {}
                raw = revision.get("features")
                if raw is None:
                    raw = getattr(entity, "production_features", None) if entity is not None else None
                if raw is None:
                    raw = getattr(entity, "features", ()) if entity is not None else ()
                if isinstance(raw, dict):
                    raw = list(raw.values())
                self._draft_features = [self._normalise_feature(item) for item in (raw or ())]
                self._refresh_feature_views()
                name = self.part_id.text() or "Geen onderdeel"
                self.title.setText(f"Bewerken - {name}" if self._entity_id else "Bewerken")
                self.context.setText(
                    "Selectie, eigenschappen en Viewer zijn gesynchroniseerd"
                    if entity is not None else "Selecteer een maakdeel om te bewerken"
                )
                source = getattr(entity, "source_identity", None) if entity is not None else None
                source_format = getattr(source, "source_format", "-") if source is not None else "-"
                source_id = getattr(source, "source_entity_id", "-") if source is not None else "-"
                self.source_info.setText(f"Bron: {source_format} | bronobject: {source_id}")
                self._update_recognition_state(entity)
                self._set_enabled(entity is not None)
                self._refresh_workbench_controls()
                self.set_dirty(False)
                self.status.setText(
                    f"{len(self._draft_features)} productiebewerking(en) geladen"
                    if entity is not None else "Geen onderdeel geselecteerd"
                )
            finally:
                self._loading = False

        def _set_enabled(self, enabled: bool) -> None:
            for button in (
                self.add_operation, self.delete_operation, self.duplicate_operation,
                self.move_up, self.move_down, self.import_button, self.actions_button,
                self.refresh_button, self.validate, self.calculate, self.save,
            ):
                button.setEnabled(enabled)
            self.cancel.setEnabled(enabled and self._dirty)

        def _selected_project_part(self) -> tuple[Any | None, Any | None]:
            session = getattr(self._workspace, "session", None)
            project = getattr(self._workspace, "project", None)
            parts = getattr(project, "parts", {}) if project is not None else {}
            part = parts.get(self._entity_id) if hasattr(parts, "get") else None
            return session, part

        def _refresh_workbench_controls(self) -> None:
            _session, part = self._selected_project_part()
            state = getattr(part, "workbench", {}) if part is not None else {}
            state = state if isinstance(state, dict) else {}
            revision = state.get("current_revision") if isinstance(state.get("current_revision"), dict) else {}
            commands = list(state.get("commands") or [])
            cursor = int(state.get("command_cursor") or 0)
            started = bool(revision)
            clean = not self._dirty
            rebuild = state.get("canonical_rebuild") if isinstance(state.get("canonical_rebuild"), dict) else {}
            roundtrip = revision.get("roundtrip_validation") if isinstance(revision.get("roundtrip_validation"), dict) else {}
            if part is None:
                text = "Part Workbench: alleen beschikbaar voor maakdelen"
            elif not started:
                text = "Part Workbench: niet gestart"
            else:
                text = (
                    f"Part Workbench: {revision.get('review_status', 'review_required')} | "
                    f"rebuild {rebuild.get('status', 'not_run')} | "
                    f"roundtrip {roundtrip.get('status', 'not_run')}"
                )
            self.workbench_status.setText(text)
            self.start_workbench_button.setEnabled(part is not None and not started and clean)
            self.undo_workbench_button.setEnabled(started and clean and cursor > 0)
            self.redo_workbench_button.setEnabled(started and clean and cursor < len(commands))
            for button in (
                self.review_workbench_button, self.rebuild_workbench_button,
                self.roundtrip_workbench_button, self.release_workbench_button,
            ):
                button.setEnabled(started and clean)

        def mark_dirty(self, *_: Any) -> None:
            if not self._loading and self._entity is not None:
                self.set_dirty(True)

        def set_dirty(self, dirty: bool) -> None:
            self._dirty = bool(dirty)
            if hasattr(self, "cancel"):
                self.cancel.setEnabled(self._entity is not None and self._dirty)
            if hasattr(self, "save"):
                self.save.setEnabled(self._entity is not None)
            if self._entity is not None:
                self.live_status.setText("●  Niet-opgeslagen wijzigingen" if self._dirty else "●  Centrale selectie actief")
            if hasattr(self, "workbench_status"):
                self._refresh_workbench_controls()

        def _normalise_feature(self, feature: Any) -> dict[str, Any]:
            if not isinstance(feature, dict):
                return {
                    "feature_id": str(uuid4()), "kind": "scribe", "view": "3D",
                    "reference_side": "", "parameters": {}, "description": str(feature),
                    "status": "proposed", "confidence": 1.0,
                    "provenance": {"method": "user", "source": "qt_part_workbench"},
                    "contract_version": "1.0",
                }
            item = copy.deepcopy(feature)
            kind = str(item.get("kind") or item.get("type") or "scribe").strip().lower().replace(" ", "_")
            aliases = {"gat": "hole", "sleufgat": "slot", "uitsparing": "cutout", "verstrek": "miter", "verstek": "miter", "markering": "scribe"}
            kind = aliases.get(kind, kind)
            parameters = item.get("parameters") if isinstance(item.get("parameters"), dict) else {}
            parameters = copy.deepcopy(parameters)
            for key in ("x_mm", "y_mm", "diameter_mm", "length_mm", "width_mm", "height_mm", "angle_deg", "depth", "reference", "text", "countersink_mm"):
                if key in item and key not in parameters:
                    parameters[key] = item[key]
            raw_status = str(item.get("status") or "proposed").strip().lower()
            status = {
                "ok": "confirmed", "concept": "proposed", "review": "proposed",
                "bevestigd": "confirmed", "afgewezen": "rejected",
            }.get(raw_status, raw_status)
            if status not in {"proposed", "confirmed", "rejected"}:
                status = "proposed"
            return {
                "feature_id": str(item.get("feature_id") or uuid4()),
                "kind": kind,
                "view": str(item.get("view") or item.get("side") or "3D"),
                "reference_side": str(item.get("reference_side") or parameters.get("reference") or "").strip(),
                "parameters": parameters,
                "description": str(item.get("description") or item.get("name") or self._FEATURE_LABELS.get(kind, kind.title())),
                "status": status,
                "confidence": self._number(item.get("confidence"), 1.0),
                "provenance": copy.deepcopy(item.get("provenance") or {"method": "user", "source": "qt_part_workbench"}),
                "contract_version": str(item.get("contract_version") or "1.0"),
            }

        def _default_reference_side(self) -> str:
            workbench = getattr(self._entity, "workbench", {}) if self._entity is not None else {}
            revision = workbench.get("current_revision") if isinstance(workbench, dict) else {}
            confirmed = [
                str(side.get("side_id") or "").strip()
                for side in list(revision.get("reference_sides") or [])
                if isinstance(side, dict) and side.get("confirmed") and str(side.get("face_ref") or "").strip()
            ] if isinstance(revision, dict) else []
            return confirmed[0] if len(confirmed) == 1 else ""

        def add_feature(self, kind: str = "hole") -> None:
            if self._entity is None:
                self.status.setText("Selecteer eerst een maakdeel")
                return
            kind = kind if kind in self._FEATURE_DEFAULTS else "hole"
            self._draft_features.append({
                "feature_id": str(uuid4()),
                "kind": kind,
                "view": "Boven" if kind in {"hole", "countersunk_hole", "slot"} else "3D",
                "reference_side": self._default_reference_side(),
                "parameters": copy.deepcopy(self._FEATURE_DEFAULTS[kind]),
                "description": f"Nieuwe {self._FEATURE_LABELS[kind].lower()}",
                "status": "proposed",
                "confidence": 1.0,
                "provenance": {"method": "user", "source": "qt_part_workbench"},
                "contract_version": "1.0",
            })
            index = len(self._draft_features) - 1
            self._refresh_feature_views(select_index=index)
            self.set_dirty(True)
            self.status.setText(f"{self._FEATURE_LABELS[kind]} toegevoegd; valideer voor opslaan")

        def _selected_feature_indices(self) -> list[int]:
            indices: set[int] = set()
            for model_index in self.features.selectionModel().selectedRows():
                item = self.features.item(model_index.row(), 0)
                if item is not None:
                    value = item.data(QtCore.Qt.ItemDataRole.UserRole)
                    if isinstance(value, int) and value >= 0:
                        indices.add(value)
            return sorted(indices)

        def delete_selected_features(self) -> None:
            indices = self._selected_feature_indices()
            if not indices:
                self.status.setText("Selecteer eerst een bewerking; het basisprofiel kan niet worden verwijderd")
                return
            for index in reversed(indices):
                del self._draft_features[index]
            self._refresh_feature_views()
            self.set_dirty(True)
            self.status.setText(f"{len(indices)} bewerking(en) verwijderd")

        def duplicate_selected_feature(self) -> None:
            indices = self._selected_feature_indices()
            if len(indices) != 1:
                self.status.setText("Selecteer precies één bewerking om te dupliceren")
                return
            source = indices[0]
            duplicate = copy.deepcopy(self._draft_features[source])
            duplicate["feature_id"] = str(uuid4())
            duplicate["description"] = f"{duplicate['description']} (kopie)"
            duplicate["status"] = "proposed"
            self._draft_features.insert(source + 1, duplicate)
            self._refresh_feature_views(select_index=source + 1)
            self.set_dirty(True)

        def move_selected_feature(self, direction: int) -> None:
            indices = self._selected_feature_indices()
            if len(indices) != 1:
                self.status.setText("Selecteer precies één bewerking om te verplaatsen")
                return
            source = indices[0]
            target = max(0, min(len(self._draft_features) - 1, source + (-1 if direction < 0 else 1)))
            if source == target:
                return
            self._draft_features[source], self._draft_features[target] = self._draft_features[target], self._draft_features[source]
            self._refresh_feature_views(select_index=target)
            self.set_dirty(True)

        def _feature_values(self, index: int, feature: dict[str, Any]) -> tuple[str, ...]:
            parameters = feature["parameters"]
            kind = feature["kind"]
            size = "-"
            if kind in {"hole", "countersunk_hole"}:
                size = f"Ø{self._number(parameters.get('diameter_mm')):g}"
                if kind == "countersunk_hole":
                    size += f" / Ø{self._number(parameters.get('countersink_mm')):g}"
            elif kind == "slot":
                size = f"{self._number(parameters.get('length_mm')):g}x{self._number(parameters.get('width_mm')):g}"
            elif kind == "cutout":
                size = f"{self._number(parameters.get('width_mm')):g}x{self._number(parameters.get('height_mm')):g}"
            return (
                str(index + 2), self._FEATURE_LABELS.get(kind, kind.title()), str(feature.get("view") or "3D"),
                self._display_number(parameters.get("x_mm")), self._display_number(parameters.get("y_mm")),
                str(feature.get("reference_side") or "Onbevestigd"), size, str(parameters.get("depth") or parameters.get("depth_mm") or "-"),
                self._display_number(parameters.get("width_mm")), self._display_number(parameters.get("height_mm")),
                self._display_number(parameters.get("angle_deg")), str(feature.get("description") or ""),
                str(feature.get("status") or "Review"),
            )

        def _display_number(self, value: Any) -> str:
            return "-" if value in (None, "") else f"{self._number(value):g}"

        def _refresh_feature_views(self, select_index: int | None = None) -> None:
            self._loading = True
            try:
                profile = self.profile.currentText().strip() if hasattr(self, "profile") else ""
                self.features.setRowCount(1 + len(self._draft_features))
                base = ("1", "Basisprofiel", "3D", "-", "-", profile or "Brongeometrie", "-", "-", "-", "-", "-", profile or "Basisprofiel", "OK")
                for column, value in enumerate(base):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, -1)
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                    self.features.setItem(0, column, item)
                for index, feature in enumerate(self._draft_features):
                    for column, value in enumerate(self._feature_values(index, feature)):
                        item = QtWidgets.QTableWidgetItem(value)
                        item.setData(QtCore.Qt.ItemDataRole.UserRole, index)
                        if column in {0, 1}:
                            item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                        self.features.setItem(index + 1, column, item)
                self._populate_subset(self.angle_table, {"cutout", "end_cut", "miter"})
                self._populate_subset(self.hole_table, {"hole", "countersunk_hole", "slot"})
                if select_index is not None and 0 <= select_index < len(self._draft_features):
                    self.features.selectRow(select_index + 1)
            finally:
                self._loading = False

        def _populate_subset(self, table: Any, kinds: set[str]) -> None:
            rows = [(index, feature) for index, feature in enumerate(self._draft_features) if feature["kind"] in kinds]
            table.setRowCount(len(rows))
            for row, (index, feature) in enumerate(rows):
                parameters = feature["parameters"]
                position = f"X={self._display_number(parameters.get('x_mm'))}, Y={self._display_number(parameters.get('y_mm'))}"
                values = (
                    str(index + 1), self._FEATURE_LABELS.get(feature["kind"], feature["kind"]), position,
                    self._feature_values(index, feature)[6], feature["description"], feature["status"],
                )
                for column, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, index)
                    table.setItem(row, column, item)

        def _open_subset_feature(self, table: Any, row: int) -> None:
            item = table.item(row, 0)
            index = item.data(QtCore.Qt.ItemDataRole.UserRole) if item is not None else None
            if isinstance(index, int):
                self.tabs.setCurrentIndex(2)
                self.features.selectRow(index + 1)
                self.features.scrollToItem(self.features.item(index + 1, 0))

        def _feature_item_changed(self, item: Any) -> None:
            if self._loading or item is None:
                return
            index = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if not isinstance(index, int) or not (0 <= index < len(self._draft_features)):
                return
            feature = self._draft_features[index]
            parameters = feature["parameters"]
            column = item.column()
            if column == 2:
                feature["view"] = item.text().strip() or "3D"
            elif column in {3, 4, 8, 9, 10}:
                key = {3: "x_mm", 4: "y_mm", 8: "width_mm", 9: "height_mm", 10: "angle_deg"}[column]
                parameters[key] = self._number(item.text())
            elif column == 5:
                feature["reference_side"] = item.text().strip()
            elif column == 7:
                parameters["depth"] = item.text().strip()
            elif column == 11:
                feature["description"] = item.text().strip()
            elif column == 12:
                feature["status"] = item.text().strip()
            self.set_dirty(True)
            self._populate_subset(self.angle_table, {"cutout", "end_cut", "miter"})
            self._populate_subset(self.hole_table, {"hole", "countersunk_hole", "slot"})

        def validate_draft(self) -> bool:
            _session, part = self._selected_project_part()
            state = getattr(part, "workbench", {}) if part is not None else {}
            revision = state.get("current_revision") if isinstance(state, dict) else None
            if not isinstance(revision, dict):
                self.status.setText("Start eerst de Part Workbench voor onafhankelijke validatie")
                return False
            try:
                from cws_convertor.project.workbench import evaluate_workbench_revision

                candidate = copy.deepcopy(revision)
                dimensions = copy.deepcopy(candidate.get("dimensions") or {})
                dimensions["length_mm"] = self.length.value()
                properties = copy.deepcopy(candidate.get("production_properties") or {})
                properties.update({
                    "profile": self.profile.currentText().strip(),
                    "material": self.material.currentText().strip(),
                    "part_position": self.part_id.text().strip(),
                })
                candidate.update({
                    "dimensions": dimensions,
                    "production_properties": properties,
                    "features": self._canonical_workbench_features(),
                })
                issues = evaluate_workbench_revision(candidate)
                messages = [str(item.get("message") or item.get("code")) for item in issues]
                self.status.setText(
                    "Onafhankelijke workbenchvalidatie: geslaagd"
                    if not messages else " | ".join(messages[:3])
                )
                return not issues
            except Exception as exc:
                self.status.setText(f"Validatie geblokkeerd: {type(exc).__name__}: {exc}")
                return False

        def calculate_draft(self) -> None:
            factors = {"hole": 0.65, "countersunk_hole": 0.95, "slot": 1.40, "cutout": 2.20, "end_cut": 1.25, "miter": 1.50, "scribe": 0.45}
            processing = sum(factors.get(feature["kind"], 1.0) for feature in self._draft_features)
            self._loading = True
            try:
                self.processing_minutes.setValue(processing)
                total_minutes = self.setup_minutes.value() + processing
                self.total_minutes.setValue(total_minutes)
                operation_cost = total_minutes / 60.0 * self.hourly_rate.value()
                self.operation_cost.setValue(operation_cost)
                self.total_cost.setValue(self.material_cost.value() + operation_cost)
            finally:
                self._loading = False
            self.set_dirty(True)
            self.status.setText(f"Berekend: {self.total_minutes.value():.2f} min | {self.total_cost.value():.2f} EUR")

        def choose_import(self) -> None:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Bewerkingen importeren", "", "Bewerkingen (*.json *.csv)")
            if path:
                self.import_operations(Path(path))

        def import_operations(self, path: Path) -> int:
            path = Path(path)
            if path.suffix.lower() == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                rows = payload.get("features", []) if isinstance(payload, dict) else payload
            elif path.suffix.lower() == ".csv":
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    rows = list(csv.DictReader(handle))
            else:
                raise ValueError("Alleen JSON- en CSV-bewerkingsbestanden worden ondersteund")
            imported = [self._normalise_feature(row) for row in rows if isinstance(row, dict)]
            self._draft_features.extend(imported)
            self._refresh_feature_views(select_index=len(self._draft_features) - 1 if imported else None)
            if imported:
                self.set_dirty(True)
            self.status.setText(f"{len(imported)} bewerking(en) geïmporteerd uit {path.name}")
            return len(imported)

        def choose_export(self) -> None:
            default = f"{self.part_id.text() or 'onderdeel'}_bewerkingen.json"
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Bewerkingen exporteren", default, "JSON (*.json)")
            if path:
                self.export_operations(Path(path))

        def export_operations(self, path: Path) -> Path:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"schema_version": "1.0", "part_id": self.part_id.text(), "features": self._draft_features}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            self.status.setText(f"Bewerkingen geëxporteerd naar {path}")
            return path

        def remove_concepts(self) -> None:
            before = len(self._draft_features)
            self._draft_features = [feature for feature in self._draft_features if str(feature.get("status", "")).lower() not in {"concept", "proposed"}]
            removed = before - len(self._draft_features)
            self._refresh_feature_views()
            if removed:
                self.set_dirty(True)
            self.status.setText(f"{removed} conceptbewerking(en) verwijderd")

        def refresh_from_project(self, _checked: bool = False, *, force: bool = False) -> None:
            if self._dirty and not force:
                self.status.setText("Niet-opgeslagen wijzigingen aanwezig; gebruik Annuleren om opnieuw te laden")
                return
            self._load_entity_state()
            self.status.setText("Onderdeel vernieuwd vanuit het centrale Project Model")

        def cancel_changes(self) -> None:
            self._load_entity_state()
            self.status.setText("Niet-opgeslagen wijzigingen geannuleerd")

        def save_changes(self) -> bool:
            if self._workspace is None or self._entity is None:
                self.status.setText("Selecteer eerst een maakdeel")
                return False
            if not self.validate_draft():
                self.status.setText("Opslaan geblokkeerd: corrigeer eerst de gemarkeerde bewerkingen")
                return False
            try:
                profile_value = self.profile.currentText().strip()
                material_value = self.material.currentText().strip()
                profile_match = self._profile_database.find(profile_value) if self._profile_database and profile_value else None
                if profile_match is not None:
                    profile_value = profile_match.designation
                if self._material_database and material_value:
                    from material_database import normalise_material
                    key = normalise_material(material_value)
                    matches = [item for item in self._material_database.materials if key in item.search_names]
                    if len(matches) == 1:
                        material_value = matches[0].code
                session, part = self._selected_project_part()
                if part is not None and session is not None:
                    state = session.start_part_workbench(self._entity_id, user="qt-gui")
                    revision = copy.deepcopy(state.get("current_revision") or {})
                    production_properties = copy.deepcopy(revision.get("production_properties") or {})
                    production_properties.update({
                        "profile": profile_value,
                        "material": material_value,
                        "part_position": self.part_id.text().strip(),
                    })
                    dimensions = copy.deepcopy(revision.get("dimensions") or {})
                    dimensions["length_mm"] = self.length.value()
                    changes = {
                        "production_properties": production_properties,
                        "dimensions": dimensions,
                        "features": self._canonical_workbench_features(),
                    }
                    changes = {key: value for key, value in changes.items() if value != revision.get(key)}
                    if changes:
                        session.update_part_workbench(
                            self._entity_id, changes, user="qt-gui",
                            reason="Production Editor fase 2 bijgewerkt",
                        )
                    self._entity = part
                properties = copy.deepcopy(getattr(self._entity, "properties", {}) or {})
                properties["ui_editor"] = {
                    "description": self.description.text().strip(),
                    "coating": self.coating.text().strip(),
                    "mark": self.mark_code.text().strip(),
                    "revision": self.revision.text().strip(),
                    "phase": self.phase.text().strip(),
                    "article_code": self.article_code.text().strip(),
                    "material_cost": self.material_cost.value(),
                    "hourly_rate": self.hourly_rate.value(),
                    "operation_cost": self.operation_cost.value(),
                    "total_cost": self.total_cost.value(),
                    "setup_minutes": self.setup_minutes.value(),
                    "processing_minutes": self.processing_minutes.value(),
                    "total_minutes": self.total_minutes.value(),
                }
                if hasattr(self._entity, "properties"):
                    self._entity.properties = properties
                if hasattr(self._entity, "name") and self.description.text().strip():
                    self._entity.name = self.description.text().strip()
                if hasattr(self._entity, "coating"):
                    self._entity.coating = self.coating.text().strip()
                if hasattr(self._entity, "revision"):
                    self._entity.revision = self.revision.text().strip()
                self._workspace.session.save(user="qt-gui", revision_message=f"Onderdeel {self.part_id.text()} bijgewerkt")
                self.set_dirty(False)
                self.status.setText("Workbench-revisie en metadata opgeslagen in het centrale Project Model")
                self._update_recognition_state(self._entity)
                self._refresh_workbench_controls()
                return True
            except Exception as exc:
                self.status.setText(f"Opslaan mislukt: {type(exc).__name__}: {exc}")
                QtWidgets.QMessageBox.critical(self, "Bewerken", f"{type(exc).__name__}: {exc}")
                return False

        def _canonical_workbench_features(self) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            for index, feature in enumerate(self._draft_features, start=1):
                kind = str(feature.get("kind") or "").strip().lower()
                if kind == "miter":
                    raise ValueError("Verstek is ambigu; leg iedere kopsnede expliciet als start of end vast")
                if kind not in self._WORKBENCH_FEATURE_KINDS:
                    raise ValueError(f"Bewerking {kind or index} wordt niet ondersteund door Part Workbench 1.1")
                parameters = copy.deepcopy(feature.get("parameters") or {})
                if kind == "countersunk_hole":
                    parameters["countersink_diameter_mm"] = parameters.pop(
                        "countersink_mm",
                        parameters.get("countersink_diameter_mm"),
                    )
                    parameters.setdefault("countersink_angle_deg", 90.0)
                parameters.pop("reference", None)
                depth = parameters.pop("depth", None)
                if depth not in (None, "", "-", "Doorlopend", "doorlopend"):
                    depth_mm = self._number(depth, -1.0)
                    if depth_mm <= 0.0:
                        raise ValueError(f"Bewerking {index} heeft geen expliciete positieve diepte")
                    parameters["through"] = False
                    parameters["depth_mm"] = depth_mm
                elif kind in {"hole", "slot", "cope", "cutout"}:
                    parameters.setdefault("through", True)
                if kind in {"cope", "cutout", "pocket"}:
                    parameters.setdefault("angle_deg", 0.0)
                    parameters.setdefault("corner_radius_mm", 0.0)
                if kind == "end_cut":
                    reference = str(feature.get("parameters", {}).get("reference") or parameters.get("end") or "").strip().lower()
                    end_map = {"linker uiteinde": "start", "links": "start", "rechter uiteinde": "end", "rechts": "end"}
                    parameters["end"] = end_map.get(reference, reference)
                if kind == "scribe":
                    if not isinstance(parameters.get("points"), (list, tuple)) or len(parameters["points"]) < 2:
                        raise ValueError(f"Markering {index} vereist minimaal twee expliciete punten")
                    parameters.pop("x_mm", None)
                    parameters.pop("y_mm", None)
                result.append({
                    "feature_id": str(feature.get("feature_id") or uuid4()),
                    "kind": kind,
                    "reference_side": str(feature.get("reference_side") or "").strip(),
                    "parameters": parameters,
                    "operation_class": "marking" if kind == "scribe" else "material_removal",
                    "status": str(feature.get("status") or "proposed").strip().lower(),
                    "confidence": self._number(feature.get("confidence"), 1.0),
                    "provenance": copy.deepcopy(feature.get("provenance") or {"method": "user", "source": "qt_part_workbench"}),
                })
            return result

        def _run_clean_workbench_action(self, callback: Any, success: str) -> Any | None:
            if self._dirty:
                self.status.setText("Actie geblokkeerd: sla wijzigingen op of annuleer ze eerst")
                return None
            session, part = self._selected_project_part()
            if session is None or part is None:
                self.status.setText("Selecteer eerst een maakdeel")
                return None
            try:
                result = callback(session, part)
                session.save(user="qt-gui", revision_message=success)
                self._entity = self._workspace.project.parts[self._entity_id]
                self._load_entity_state()
                self.status.setText(success)
                return result
            except Exception as exc:
                self.status.setText(f"{success} mislukt: {type(exc).__name__}: {exc}")
                QtWidgets.QMessageBox.critical(self, "Part Workbench", f"{type(exc).__name__}: {exc}")
                return None

        def start_part_workbench(self, _checked: bool = False) -> None:
            self._run_clean_workbench_action(
                lambda session, _part: session.start_part_workbench(self._entity_id, user="qt-gui"),
                "Part Workbench gestart",
            )

        def undo_part_workbench(self, _checked: bool = False) -> None:
            self._run_clean_workbench_action(
                lambda session, _part: session.undo_part_workbench(self._entity_id, user="qt-gui"),
                "Laatste workbench-commando ongedaan gemaakt",
            )

        def redo_part_workbench(self, _checked: bool = False) -> None:
            self._run_clean_workbench_action(
                lambda session, _part: session.redo_part_workbench(self._entity_id, user="qt-gui"),
                "Workbench-commando opnieuw uitgevoerd",
            )

        def review_part_workbench(self, _checked: bool = False) -> None:
            self._run_clean_workbench_action(
                lambda session, _part: session.review_part_workbench(self._entity_id, user="qt-gui", release=False),
                "Part Workbench gevalideerd",
            )

        def rebuild_part_canonical(self, _checked: bool = False) -> None:
            self._run_clean_workbench_action(
                lambda session, _part: session.rebuild_part_canonical(self._entity_id, user="qt-gui"),
                "Canonical rebuild uitgevoerd en opgeslagen",
            )

        def validate_part_roundtrips(self, _checked: bool = False) -> None:
            folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Map voor NC1/STEP/IFC/PDF-roundtripartefacten")
            if not folder:
                return
            self._run_clean_workbench_action(
                lambda session, _part: session.validate_part_roundtrips(
                    self._entity_id, Path(folder), user="qt-gui", formats=("NC1", "STEP", "IFC", "PDF")
                ),
                "NC1/STEP/IFC/PDF-roundtripvalidatie uitgevoerd",
            )

        def release_part_workbench(self, _checked: bool = False) -> None:
            self._run_clean_workbench_action(
                lambda session, _part: session.review_part_workbench(self._entity_id, user="qt-gui", release=True),
                "Part Workbench vrijgegeven",
            )

        def handle_ribbon(self, command: str) -> None:
            handlers = {
                "add": lambda: self.add_feature("hole"),
                "delete": self.delete_selected_features,
                "duplicate": self.duplicate_selected_feature,
                "move_up": lambda: self.move_selected_feature(-1),
                "move_down": lambda: self.move_selected_feature(1),
                "import": self.choose_import,
                "refresh": self.refresh_from_project,
                "validate": self.validate_draft,
                "calculate": self.calculate_draft,
                "save": self.save_changes,
                "cancel": self.cancel_changes,
            }
            if command == "actions":
                self.actions_button.showMenu()
                return
            handler = handlers.get(str(command))
            if handler is None:
                raise ValueError(f"Onbekende Bewerken-actie: {command}")
            handler()

        def _update_recognition_state(self, entity: Any | None) -> None:
            if entity is None:
                self.recognition_state.setText("Selecteer een onderdeel voor profiel- en materiaalherkenning")
                return
            from cws_convertor.project.classification import normalize_profile
            profile_value = normalize_profile(_value(entity, "normalized_profile", "profile"))
            material_value = _value(entity, "normalized_material", "material_grade", "material")
            profile_match = self._profile_database.find(profile_value) if self._profile_database and profile_value else None
            material_matches = []
            if self._material_database and material_value:
                from material_database import normalise_material
                key = normalise_material(material_value)
                material_matches = [item for item in self._material_database.materials if key in item.search_names]
            profile_confidence = 1.0 if profile_match is not None else float(getattr(entity, "profile_confidence", 0.0) or 0.0)
            material_confidence = float(getattr(entity, "material_confidence", 0.0) or 0.0)
            profile_text = f"catalogus: {profile_match.designation}" if profile_match else "niet exact in profielendatabase"
            material_text = f"catalogus: {material_matches[0].code}" if len(material_matches) == 1 else "handmatig controleren"
            self.recognition_state.setText(
                f"Profiel {profile_value or '-'} ({profile_confidence:.0%}, {profile_text}) | "
                f"Materiaal {material_value or '-'} ({material_confidence:.0%}, {material_text}). "
                "Niet-exacte herkenning blijft reviewplichtig."
            )
            self.profile_search.setText(profile_value)

        def _refresh_profile_suggestions(self) -> None:
            database = self._profile_database
            if database is None or not hasattr(self, "profile_matches"):
                return
            rows = database.filtered(text=self.profile_search.text().strip())[:250]
            self.profile_matches.setRowCount(len(rows))
            for row, profile in enumerate(rows):
                values = (profile.designation, profile.profile_type, profile.family, f"{profile.height:g}", f"{profile.width:g}", f"{profile.mass_kg_m:g}")
                for column, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, profile.designation)
                    self.profile_matches.setItem(row, column, item)

        def _confirm_profile_selection(self) -> None:
            row = self.profile_matches.currentRow()
            if row < 0:
                self.status.setText("Selecteer eerst een profiel in de catalogus")
                return
            item = self.profile_matches.item(row, 0)
            if item is None:
                return
            designation = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or item.text())
            self.profile.setCurrentText(designation)
            self.recognition_state.setText(f"{designation} handmatig gekozen; Opslaan registreert de bevestigde cataloguskeuze.")
            self.set_dirty(True)


    class DrawingWorkspacePanel(QtWidgets.QWidget):
        """Large live technical drawing sheet with PNG and PDF output."""

        action_requested = QtCore.Signal(str)
        generate_pdf = QtCore.Signal()

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsDrawingFunctionalPanel")
            self._workspace = None
            self._entity_id = ""
            self._last_png: Path | None = None
            self._manual_dimensions: list[dict[str, Any]] = []
            self._build()
            self.generate_pdf.connect(self.export_pdf)

        def _build(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(12, 9, 12, 9)
            root.setSpacing(7)
            top = QtWidgets.QHBoxLayout()
            self.title = QtWidgets.QLabel("Review-PDF / Tekening")
            self.title.setObjectName("workspaceTitle")
            live = QtWidgets.QLabel("●  Voorbeeld (live)")
            live.setObjectName("liveStatus")
            self.format = QtWidgets.QComboBox()
            self.format.addItems(["A4", "A3", "A2", "A1", "A0"])
            self.format.setCurrentText("A3")
            self.scale = QtWidgets.QComboBox()
            self.scale.addItems(["Auto", "1:1", "1:2", "1:5", "1:10", "1:20", "1:25", "1:50", "1:100", "1:200"])
            self.unit = QtWidgets.QComboBox()
            self.unit.addItems(["mm", "cm"])
            self.preview_button = QtWidgets.QPushButton("Voorbeeld vernieuwen")
            self.png_button = QtWidgets.QPushButton("PNG exporteren")
            self.pdf_button = QtWidgets.QPushButton("Review-PDF genereren")
            self.pdf_button.setObjectName("primaryButton")
            top.addWidget(self.title)
            top.addWidget(live)
            top.addStretch(1)
            for label, widget in (("Formaat", self.format), ("Schaal", self.scale), ("Eenheid", self.unit)):
                top.addWidget(QtWidgets.QLabel(label))
                top.addWidget(widget)
            top.addWidget(self.preview_button)
            top.addWidget(self.png_button)
            top.addWidget(self.pdf_button)
            root.addLayout(top)
            views = QtWidgets.QHBoxLayout()
            views.addWidget(QtWidgets.QLabel("Aanzichten"))
            self.view_buttons: dict[str, Any] = {}
            for key, label in (("front", "Voor"), ("top", "Boven"), ("side", "Zij"), ("3d", "3D"), ("iso", "Iso")):
                button = QtWidgets.QPushButton(label)
                button.setCheckable(True)
                button.setChecked(key in {"front", "top", "side"})
                button.toggled.connect(lambda _checked: QtCore.QTimer.singleShot(0, self.refresh_preview))
                self.view_buttons[key] = button
                views.addWidget(button)
            self.dimensions_button = QtWidgets.QPushButton("Maatvoering")
            self.dimensions_button.setCheckable(True)
            self.dimensions_button.setChecked(True)
            self.title_block_button = QtWidgets.QPushButton("Titelblok")
            self.title_block_button.setCheckable(True)
            self.title_block_button.setChecked(True)
            self.dimension_mode = QtWidgets.QComboBox()
            self.dimension_mode.addItems(("Hoofdmaten", "Contour + gaten", "Productiematen"))
            self.add_dimension_button = QtWidgets.QPushButton("Eigen maat toevoegen...")
            self.clear_dimensions_button = QtWidgets.QPushButton("Eigen maten wissen")
            views.addSpacing(18)
            views.addWidget(self.dimensions_button)
            views.addWidget(self.dimension_mode)
            views.addWidget(self.add_dimension_button)
            views.addWidget(self.clear_dimensions_button)
            views.addWidget(self.title_block_button)
            views.addStretch(1)
            root.addLayout(views)
            self.sheet_frame = QtWidgets.QFrame()
            self.sheet_frame.setObjectName("drawingSheetFrame")
            sheet_layout = QtWidgets.QVBoxLayout(self.sheet_frame)
            sheet_layout.setContentsMargins(18, 14, 18, 14)
            self.preview = QtWidgets.QLabel("Selecteer een onderdeel en kies Voorbeeld vernieuwen")
            self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.preview.setMinimumHeight(500)
            self.preview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
            sheet_layout.addWidget(self.preview, 1)
            root.addWidget(self.sheet_frame, 1)
            self.status = QtWidgets.QLabel("Geen project geopend")
            self.status.setObjectName("mutedText")
            root.addWidget(self.status)
            self.preview_button.clicked.connect(self.refresh_preview)
            self.png_button.clicked.connect(self.export_png)
            self.pdf_button.clicked.connect(self.export_pdf)
            self.format.currentTextChanged.connect(lambda _text: self.refresh_preview())
            self.scale.currentTextChanged.connect(lambda _text: self.refresh_preview())
            self.dimensions_button.toggled.connect(lambda _checked: QtCore.QTimer.singleShot(0, self.refresh_preview))
            self.title_block_button.toggled.connect(lambda _checked: QtCore.QTimer.singleShot(0, self.refresh_preview))
            self.dimension_mode.currentTextChanged.connect(lambda _text: self.refresh_preview())
            self.add_dimension_button.clicked.connect(self._add_manual_dimension)
            self.clear_dimensions_button.clicked.connect(self._clear_manual_dimensions)

        def _add_manual_dimension(self) -> None:
            if not self._entity_id:
                QtWidgets.QMessageBox.information(self, "Eigen maat", "Selecteer eerst een onderdeel.")
                return
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Eigen maat toevoegen")
            form = QtWidgets.QFormLayout(dialog)
            view = QtWidgets.QComboBox(dialog)
            view.addItem("Vooraanzicht", "front")
            view.addItem("Bovenaanzicht", "top")
            view.addItem("Zijaanzicht", "side")
            view.addItem("Isometrisch", "iso")
            axis = QtWidgets.QComboBox(dialog)
            axis.addItem("Horizontaal", "horizontal")
            axis.addItem("Verticaal", "vertical")
            feature = QtWidgets.QComboBox(dialog)
            feature.addItem("Onderdeelomtrek / stabiele datum", "part-envelope")
            entity = None
            if self._workspace is not None:
                entity = self._workspace.project.parts.get(self._entity_id)
            workbench = getattr(entity, "workbench", {}) if entity is not None else {}
            revision = workbench.get("current_revision") if isinstance(workbench, dict) else {}
            for item in list(revision.get("features") or []) if isinstance(revision, dict) else []:
                if isinstance(item, dict) and item.get("feature_id"):
                    feature.addItem(
                        f"{item.get('kind', 'feature')} · {item['feature_id']}",
                        str(item["feature_id"]),
                    )
            anchor_type = QtWidgets.QComboBox(dialog)
            anchor_type.addItem("Datum-offset", "datum_offset")
            anchor_type.addItem("Featurecentrum", "feature_center")
            anchor_type.addItem("Geprojecteerde rand", "edge_projection")
            start = QtWidgets.QDoubleSpinBox(dialog)
            end = QtWidgets.QDoubleSpinBox(dialog)
            for control in (start, end):
                control.setRange(-1000000.0, 1000000.0)
                control.setDecimals(1)
                control.setSuffix(" mm")
            end.setValue(100.0)
            label = QtWidgets.QLineEdit(dialog)
            label.setPlaceholderText("Leeg = berekende maat")
            tolerance = QtWidgets.QDoubleSpinBox(dialog)
            tolerance.setRange(0.0, 1000.0)
            tolerance.setDecimals(3)
            tolerance.setSuffix(" mm")
            form.addRow("Aanzicht", view)
            form.addRow("Richting", axis)
            form.addRow("Objectanker", feature)
            form.addRow("Ankertype", anchor_type)
            form.addRow("Begin vanaf referentierand", start)
            form.addRow("Einde vanaf referentierand", end)
            form.addRow("Tekst", label)
            form.addRow("Tolerantie ±", tolerance)
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
                parent=dialog,
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            form.addRow(buttons)
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return
            if abs(end.value() - start.value()) < 1.0e-9:
                QtWidgets.QMessageBox.information(self, "Eigen maat", "Begin en einde moeten van elkaar verschillen.")
                return
            self._manual_dimensions.append({
                "view": str(view.currentData()), "axis": str(axis.currentData()),
                "start": float(start.value()), "end": float(end.value()), "label": label.text().strip(),
                "entity_id": self._entity_id,
                "feature_id": str(feature.currentData()),
                "subshape_id": "",
                "anchor_type": str(anchor_type.currentData()),
                "nominal_value_mm": abs(float(end.value()) - float(start.value())),
                "tolerance_mm": float(tolerance.value()),
                "provenance": {"method": "user", "surface": "review_snapshot"},
            })
            self.dimensions_button.setChecked(True)
            self.status.setText(f"Eigen maat toegevoegd ({len(self._manual_dimensions)} totaal)")
            self.refresh_preview()

        def _clear_manual_dimensions(self) -> None:
            self._manual_dimensions.clear()
            self.status.setText("Eigen maatvoering gewist")
            self.refresh_preview()

        def set_context(self, context: object, selection: object | None = None) -> None:
            workspace, entity, entity_id = _workspace_entity(context, selection)
            if workspace is None and type(context).__name__ == "UnifiedUiContextSnapshot":
                return
            previous_entity_id = self._entity_id
            self._workspace, self._entity_id = workspace, entity_id
            name = _value(entity, "part_position", "mark", "name", default=self._entity_id)
            self.title.setText(f"Review-PDF / Tekening - {name}" if name else "Review-PDF / Tekening")
            self.status.setText("Gereed voor live tekenvoorbeeld" if self._workspace is not None else "Geen project geopend")
            if self._workspace is not None and self._entity_id and self._entity_id != previous_entity_id:
                QtCore.QTimer.singleShot(0, self.refresh_preview)

        def show_project_selection(self, selection: object) -> None:
            self.set_context(self._workspace, selection)

        def _output_folder(self) -> Path:
            target = Path.home() / "Documents" / "CWS Convertor" / "Tekeningen"
            target.mkdir(parents=True, exist_ok=True)
            return target

        def _resolved_drawing_entity_id(self) -> str:
            """Accept every selected object with geometry, then fall back to a make part."""
            if self._workspace is None:
                return ""
            project = self._workspace.project
            current = str(self._entity_id or "")

            collections = (project.parts, project.assemblies, project.purchased_items, project.fasteners, project.welds)

            def exists(entity_id: str) -> bool:
                return any(entity_id in collection for collection in collections)

            def drawable(entity_id: str) -> bool:
                if not entity_id or not exists(entity_id):
                    return False
                try:
                    node_id = self._workspace.interaction.node_for_entity(entity_id)
                    node = self._workspace.controller.index.node(node_id)
                    return node.geometry_id is not None and self._workspace.load_result.repository.get(node.geometry_id) is not None
                except Exception:
                    return False

            # A fastener or assembly may have renderable geometry, but a
            # production drawing must resolve to its canonical make part.
            if current in project.parts and drawable(current):
                return current

            candidates: list[str] = []

            def add_assembly_parts(assembly: Any | None) -> None:
                if assembly is None:
                    return
                main = str(getattr(assembly, "main_part_id", "") or "")
                if main in project.parts:
                    candidates.append(main)
                for part_id in getattr(assembly, "part_ids", ()) or ():
                    part_id = str(part_id)
                    if part_id in project.parts:
                        candidates.append(part_id)

            add_assembly_parts(project.assemblies.get(current))
            if current:
                for assembly in project.assemblies.values():
                    related_ids = (
                        tuple(getattr(assembly, "fastener_ids", ()) or ())
                        + tuple(getattr(assembly, "weld_ids", ()) or ())
                        + tuple(getattr(assembly, "purchased_item_ids", ()) or ())
                    )
                    if current in related_ids:
                        add_assembly_parts(assembly)

            ordered = tuple(dict.fromkeys(candidates))
            for candidate in ordered:
                if drawable(candidate):
                    return candidate
            if drawable(current):
                return current
            for collection in (project.parts, project.purchased_items):
                for entity_id in collection:
                    if drawable(str(entity_id)):
                        return str(entity_id)
            return ""

        def _generate(self, *, make_png: bool, make_pdf: bool):
            if self._workspace is None:
                self.status.setText("Open eerst een project en selecteer daarna een maakdeel.")
                self.preview.setText("Geen project geopend")
                return None
            resolved_part_id = self._resolved_drawing_entity_id()
            if not resolved_part_id:
                self.status.setText("Selecteer een geometrisch onderdeel in de Viewer, modelstructuur of BOM.")
                self.preview.setText(
                    "Deze selectie heeft geen geladen 3D-geometrie.\n"
                    "Selecteer een profiel, plaat, bevestiger of ander zichtbaar onderdeel."
                )
                return None
            if resolved_part_id != self._entity_id:
                self._entity_id = resolved_part_id
                part = next(
                    collection[resolved_part_id]
                    for collection in (
                        self._workspace.project.parts, self._workspace.project.assemblies,
                        self._workspace.project.purchased_items, self._workspace.project.fasteners,
                        self._workspace.project.welds,
                    )
                    if resolved_part_id in collection
                )
                name = _value(part, "part_position", "mark", "name", default=resolved_part_id)
                self.title.setText(f"Review-PDF / Tekening - {name}")
                self.status.setText(f"Gekoppeld maakdeel geselecteerd: {name}")
            try:
                from cws_convertor.ui_qt.engineering_drawing import EngineeringDrawingGenerator
                selected_views = tuple(key for key, button in self.view_buttons.items() if button.isChecked())
                result = EngineeringDrawingGenerator(self._workspace).generate(
                    self._output_folder(), entity_id=self._entity_id,
                    sheet_format=self.format.currentText(), scale_label=self.scale.currentText(),
                    unit=self.unit.currentText(), make_png=make_png, make_pdf=make_pdf,
                    views=selected_views, dimensions=self.dimensions_button.isChecked(),
                    title_block=self.title_block_button.isChecked(),
                    dimension_mode=self.dimension_mode.currentText(),
                    manual_dimensions=tuple(self._manual_dimensions),
                )
                if result.png_path:
                    self._last_png = Path(result.png_path)
                    self._show_pixmap()
                warning = f" | {result.warnings[0]}" if result.warnings else ""
                self.status.setText(
                    f"Reviewdocument gegenereerd op schaal {result.scale_label}: "
                    f"{result.pdf_path or result.png_path}{warning} | geen productie-vrijgave"
                )
                return result
            except Exception as exc:
                self.status.setText("Tekening genereren mislukt")
                QtWidgets.QMessageBox.critical(self, "Review-PDF / Tekening", f"{type(exc).__name__}: {exc}")
                return None

        def refresh_preview(self) -> None:
            self._generate(make_png=True, make_pdf=False)

        def export_png(self) -> None:
            self._generate(make_png=True, make_pdf=False)

        def export_pdf(self) -> None:
            self._generate(make_png=True, make_pdf=True)

        def _show_pixmap(self) -> None:
            if self._last_png is None or not self._last_png.is_file():
                return
            pixmap = QtGui.QPixmap(str(self._last_png))
            self.preview.setPixmap(pixmap.scaled(self.preview.size() - QtCore.QSize(12, 12), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))

        def resizeEvent(self, event: Any) -> None:
            super().resizeEvent(event)
            self._show_pixmap()
else:
    class _Unavailable:
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()
    EditWorkspacePanel = DrawingWorkspacePanel = _Unavailable

__all__ = ["DrawingWorkspacePanel", "EditWorkspacePanel"]
