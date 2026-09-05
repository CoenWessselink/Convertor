"""Compact project-aware edit and drawing workspaces for the U4 shell."""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
import tempfile
from typing import Any
from uuid import uuid4

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()
    from cws_convertor.drawings.interactive import (
        DIMENSION_EDITOR_SCHEMA,
        DimensionDocumentStore,
        DimensionEditorModel,
        DimensionInteractionController,
        DimensionKind,
        DimensionStyle,
        DrawingRole,
        InteractionState,
        SnapFilter,
        build_snap_candidates,
    )
    from cws_convertor.ui_qt.drawing_dimension_canvas import InteractiveDrawingCanvas

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
            self._drawing_document = None
            self._dimension_document = None
            self._dimension_model = None
            self._dimension_controller = DimensionInteractionController()
            self._dimension_tool = "select"
            self._loaded_lock_version = 0
            self._snap_candidates = []
            self._dimension_clipboard: list[dict[str, Any]] = []
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
            self.orientation = QtWidgets.QComboBox()
            self.orientation.addItem("Liggend", "landscape")
            self.orientation.addItem("Staand", "portrait")
            self.scale = QtWidgets.QComboBox()
            self.scale.addItems(["Auto", "1:1", "1:2", "1:5", "1:10", "1:20", "1:25", "1:50", "1:100", "1:200"])
            self.unit = QtWidgets.QComboBox()
            self.unit.addItems(["mm", "cm"])
            self.preview_button = QtWidgets.QPushButton("Voorbeeld vernieuwen")
            self.png_button = QtWidgets.QPushButton("PNG exporteren")
            self.pdf_button = QtWidgets.QPushButton("PDF genereren")
            self.pdf_button.setObjectName("primaryButton")
            top.addWidget(self.title)
            top.addWidget(live)
            top.addStretch(1)
            for label, widget in (("Formaat", self.format), ("Oriëntatie", self.orientation), ("Schaal", self.scale), ("Eenheid", self.unit)):
                top.addWidget(QtWidgets.QLabel(label))
                top.addWidget(widget)
            top.addWidget(self.preview_button)
            top.addWidget(self.png_button)
            top.addWidget(self.pdf_button)
            root.addLayout(top)
            views = QtWidgets.QHBoxLayout()
            views.addWidget(QtWidgets.QLabel("Aanzichten"))
            self.view_buttons: dict[str, Any] = {}
            for key, label in (("front", "Voor"), ("top", "Boven"), ("side", "Zij"), ("end", "Eind"), ("3d", "3D"), ("iso", "Iso")):
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
            self.sections_button = QtWidgets.QPushButton("Doorsneden")
            self.sections_button.setCheckable(True)
            self.sections_button.setChecked(True)
            self.details_button = QtWidgets.QPushButton("Details")
            self.details_button.setCheckable(True)
            self.details_button.setChecked(True)
            self.add_dimension_button = QtWidgets.QPushButton("Eigen maat toevoegen...")
            self.clear_dimensions_button = QtWidgets.QPushButton("Selectie verwijderen")
            views.addSpacing(18)
            views.addWidget(self.dimensions_button)
            views.addWidget(self.dimension_mode)
            views.addWidget(self.sections_button)
            views.addWidget(self.details_button)
            views.addWidget(self.add_dimension_button)
            views.addWidget(self.clear_dimensions_button)
            views.addWidget(self.title_block_button)
            views.addSpacing(12)
            views.addWidget(QtWidgets.QLabel("Blad"))
            self.page_selector = QtWidgets.QComboBox()
            self.page_selector.addItem("1 / 1", 0)
            self.page_selector.setToolTip("Wissel tussen tekenbladen zonder selectie of maatbewerking te verliezen")
            views.addWidget(self.page_selector)
            views.addStretch(1)
            root.addLayout(views)
            self._build_dimension_toolbar(root)
            self.sheet_frame = QtWidgets.QFrame()
            self.sheet_frame.setObjectName("drawingSheetFrame")
            sheet_layout = QtWidgets.QHBoxLayout(self.sheet_frame)
            sheet_layout.setContentsMargins(18, 14, 18, 14)
            self.preview = InteractiveDrawingCanvas(self.sheet_frame)
            sheet_layout.addWidget(self.preview, 1)
            properties = QtWidgets.QFrame(self.sheet_frame)
            properties.setObjectName("drawingDimensionProperties")
            properties.setMinimumWidth(255)
            properties.setMaximumWidth(330)
            property_layout = QtWidgets.QVBoxLayout(properties)
            property_layout.setContentsMargins(8, 4, 4, 4)
            property_title = QtWidgets.QLabel("Maateigenschappen")
            property_title.setObjectName("workspaceTitle")
            property_layout.addWidget(property_title)
            self.dimension_properties = QtWidgets.QTreeWidget(properties)
            self.dimension_properties.setHeaderLabels(("Veld", "Waarde"))
            self.dimension_properties.setRootIsDecorated(False)
            self.dimension_properties.setAlternatingRowColors(True)
            property_layout.addWidget(self.dimension_properties, 1)
            self.revision_summary = QtWidgets.QLabel("Revisievergelijking: geen vrijgegeven basis", properties)
            self.revision_summary.setWordWrap(True)
            self.revision_summary.setObjectName("mutedText")
            property_layout.addWidget(self.revision_summary)
            self.dimension_issue_summary = QtWidgets.QLabel("Problemen: nog niet gelint", properties)
            self.dimension_issue_summary.setWordWrap(True)
            self.dimension_issue_summary.setObjectName("safetyStatus")
            property_layout.addWidget(self.dimension_issue_summary)
            self.edit_properties_button = QtWidgets.QPushButton("Eigenschappen wijzigen…")
            self.edit_properties_button.setEnabled(False)
            property_layout.addWidget(self.edit_properties_button)
            sheet_layout.addWidget(properties)
            root.addWidget(self.sheet_frame, 1)
            self.status = QtWidgets.QLabel("Geen project geopend")
            self.status.setObjectName("mutedText")
            root.addWidget(self.status)
            self.preview_button.clicked.connect(self.refresh_preview)
            self.png_button.clicked.connect(self.export_png)
            self.pdf_button.clicked.connect(self.export_pdf)
            self.format.currentTextChanged.connect(lambda _text: self.refresh_preview())
            self.orientation.currentIndexChanged.connect(lambda _index: self.refresh_preview())
            self.scale.currentTextChanged.connect(lambda _text: self.refresh_preview())
            self.unit.currentTextChanged.connect(lambda _text: self.refresh_preview())
            self.dimensions_button.toggled.connect(lambda _checked: QtCore.QTimer.singleShot(0, self.refresh_preview))
            self.title_block_button.toggled.connect(lambda _checked: QtCore.QTimer.singleShot(0, self.refresh_preview))
            self.sections_button.toggled.connect(lambda _checked: QtCore.QTimer.singleShot(0, self.refresh_preview))
            self.details_button.toggled.connect(lambda _checked: QtCore.QTimer.singleShot(0, self.refresh_preview))
            self.dimension_mode.currentTextChanged.connect(lambda _text: self.refresh_preview())
            self.add_dimension_button.clicked.connect(self._add_manual_dimension)
            self.clear_dimensions_button.clicked.connect(self._clear_manual_dimensions)
            self.preview.sheet_clicked.connect(self._on_dimension_canvas_click)
            self.preview.pointer_moved.connect(self._on_dimension_pointer)
            self.preview.command_requested.connect(self._on_dimension_command)
            self.preview.dimension_dragged.connect(self._on_dimension_dragged)
            self.preview.area_selected.connect(self._on_dimension_area_selected)
            self.edit_properties_button.clicked.connect(self._edit_dimension_properties)
            self.page_selector.currentIndexChanged.connect(lambda _index: self._show_pixmap())

        def _build_dimension_toolbar(self, root: Any) -> None:
            toolbar_frame = QtWidgets.QFrame(self)
            toolbar_frame.setObjectName("dimensionEditorToolbar")
            toolbar = QtWidgets.QHBoxLayout(toolbar_frame)
            toolbar.setContentsMargins(4, 3, 4, 3)
            toolbar.setSpacing(3)
            tools = (
                ("select", "⌖", "Selecteren/bewerken (S)"),
                (DimensionKind.HORIZONTAL.value, "↔", "Horizontale maat (H)"),
                (DimensionKind.VERTICAL.value, "↕", "Verticale maat (V)"),
                (DimensionKind.ALIGNED.value, "⟷", "Uitgelijnde maat (A)"),
                (DimensionKind.CHAIN.value, "⛓", "Kettingmaat; Enter sluit de reeks"),
                (DimensionKind.BASELINE.value, "⌞", "Baseline-/nulpuntmaat"),
                (DimensionKind.ORDINATE_X.value, "X₀", "Ordinaatmaat X"),
                (DimensionKind.ORDINATE_Y.value, "Y₀", "Ordinaatmaat Y"),
                (DimensionKind.ANGLE.value, "∠", "Hoekmaat"),
                (DimensionKind.RADIUS.value, "R", "Radiusmaat"),
                (DimensionKind.DIAMETER.value, "Ø", "Diametermaat"),
                (DimensionKind.CENTER_DISTANCE.value, "⊙↔⊙", "Hart-op-hartmaat"),
                (DimensionKind.LEADER.value, "↗", "Leader/callout"),
                (DimensionKind.TEXT.value, "T", "Tekstnotitie"),
            )
            self.dimension_tool_buttons: dict[str, Any] = {}
            group = QtWidgets.QButtonGroup(self)
            group.setExclusive(True)
            for key, label, tooltip in tools:
                button = QtWidgets.QToolButton(toolbar_frame)
                button.setText(label)
                button.setToolTip(tooltip)
                button.setCheckable(True)
                button.setAutoRaise(False)
                button.setMinimumSize(32, 28)
                button.clicked.connect(lambda _checked=False, value=key: self._activate_dimension_tool(value))
                group.addButton(button)
                toolbar.addWidget(button)
                self.dimension_tool_buttons[key] = button
            self.dimension_tool_buttons["select"].setChecked(True)
            toolbar.addSpacing(8)
            self.snap_filter = QtWidgets.QComboBox(toolbar_frame)
            for label, value in (
                ("Snap: alles", SnapFilter.ALL.value),
                ("Punten", SnapFilter.POINTS.value),
                ("Randen", SnapFilter.EDGES.value),
                ("Gaten/centra", SnapFilter.CENTERS.value),
                ("Hartlijnen", SnapFilter.CENTERLINES.value),
                ("Features", SnapFilter.FEATURES.value),
                ("Maatobjecten", SnapFilter.DIMENSIONS.value),
                ("Tekst/leaders", SnapFilter.TEXT_LEADERS.value),
            ):
                self.snap_filter.addItem(label, value)
            self.snap_filter.setToolTip("Selectiefilter voor geometrische snapreferenties")
            self.snap_filter.currentIndexChanged.connect(lambda _index: self._refresh_snap_candidates())
            toolbar.addWidget(self.snap_filter)
            self.annotation_kind = QtWidgets.QComboBox(toolbar_frame)
            for label, value in (
                ("Vrije annotatie", "free"), ("Featurecallout", "feature"), ("Gatcallout", "hole"),
                ("Sleufcallout", "slot"), ("Verzinking", "countersink"), ("Afschuining/verstek", "chamfer_miter"),
                ("Scribing/markering", "scribing"), ("Lassymbool", "weld_symbol"), ("Datumsymbool", "datum_symbol"),
                ("Geometrische tolerantie", "geometric_tolerance"), ("Oppervlakteruwheid", "surface_roughness"),
                ("Schroefdraad", "thread"), ("Plaatdikte", "plate_thickness"), ("Profielrichting", "profile_direction"),
                ("Montage/controle", "assembly_inspection"), ("Revisiewolk", "revision_cloud"),
            ):
                self.annotation_kind.addItem(label, value)
            self.annotation_kind.setToolTip("Semantisch type voor de volgende leader of tekstnotitie")
            self.annotation_kind.setMaximumWidth(145)
            toolbar.addWidget(self.annotation_kind)
            self.dimension_action_buttons: dict[str, Any] = {}
            for label, tooltip, callback in (
                ("◉", "Verberg/toon selectie", self._toggle_selected_dimension),
                ("⛓", "Geselecteerd anker opnieuw kiezen", self._start_reanchor),
                ("⧉", "Selectie dupliceren", self._duplicate_dimensions),
                ("⌫", "Verwijder alleen geselecteerde maat (Delete)", self._delete_selected_dimensions),
                ("↶", "Ongedaan maken (Ctrl+Z)", self._undo_dimensions),
                ("↷", "Opnieuw (Ctrl+Y)", self._redo_dimensions),
                ("Fit", "Tekening passend tonen", lambda: self.preview.fit_to_view()),
                ("Zoom", "Zoom naar geselecteerde maat", lambda: self.preview.zoom_to_selected()),
                ("Reset", "Reset automatische maatlayout", self._reset_dimension_layout),
                ("✓", "Conceptmaatvoering vrijgeven (rol: vrijgever)", self._release_dimension_revision),
            ):
                button = QtWidgets.QToolButton(toolbar_frame)
                button.setText(label)
                button.setToolTip(tooltip)
                button.clicked.connect(callback)
                toolbar.addWidget(button)
                self.dimension_action_buttons[tooltip] = button
            more_button = QtWidgets.QToolButton(toolbar_frame)
            more_button.setText("Meer ▾")
            more_button.setToolTip("Kopiëren, plakken, uitlijnen, verdelen, spiegelen en clustervolgorde")
            more_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            more_menu = QtWidgets.QMenu(more_button)
            for label, callback in (
                ("Kopiëren", self._copy_dimensions),
                ("Plakken", self._paste_dimensions),
                ("Horizontaal uitlijnen", lambda: self._align_dimensions("horizontal")),
                ("Verticaal uitlijnen", lambda: self._align_dimensions("vertical")),
                ("Horizontaal verdelen", lambda: self._distribute_dimensions("horizontal")),
                ("Verticaal verdelen", lambda: self._distribute_dimensions("vertical")),
                ("Naar andere zijde spiegelen", self._mirror_dimensions),
                ("Cluster naar voren", lambda: self._change_dimension_order(1)),
                ("Cluster naar achteren", lambda: self._change_dimension_order(-1)),
                ("Leaderknikpunt instellen…", self._set_leader_bend),
                ("Maatstijlprofiel…", self._edit_dimension_style),
            ):
                more_menu.addAction(label, callback)
            more_button.setMenu(more_menu)
            toolbar.addWidget(more_button)
            toolbar.addStretch(1)
            self.dimension_instruction = QtWidgets.QLabel("Selecteer een maatgereedschap")
            self.dimension_instruction.setObjectName("safetyStatus")
            toolbar.addWidget(self.dimension_instruction)
            root.addWidget(toolbar_frame)

        def _current_user(self) -> str:
            if self._workspace is None:
                return "system"
            project = self._workspace.project
            return str(getattr(project, "created_by", "") or "desktop-user")

        def _current_drawing_role(self) -> str:
            if self._workspace is None:
                return DrawingRole.READ_ONLY.value
            roles = dict(self._workspace.project.settings.get("drawing_user_roles") or {})
            return str(roles.get(self._current_user()) or DrawingRole.DRAFTER.value)

        def _entity_revision_context(self) -> tuple[str, str, str]:
            if self._workspace is None or not self._entity_id:
                return "", "", ""
            project = self._workspace.project
            entity = next(
                (
                    collection[self._entity_id]
                    for collection in (project.parts, project.assemblies, project.purchased_items, project.fasteners, project.welds)
                    if self._entity_id in collection
                ),
                None,
            )
            workbench = getattr(entity, "workbench", {}) if entity is not None else {}
            revision = dict(workbench.get("current_revision") or {}) if isinstance(workbench, dict) else {}
            source_revision = str(
                getattr(entity, "revision", "")
                or revision.get("revision_number")
                or revision.get("revision")
                or "A"
            )
            properties = getattr(entity, "properties", {}) if entity is not None else {}
            drawing_state = dict(properties.get("drawing_state") or {}) if isinstance(properties, dict) else {}
            geometry_sha256 = str(drawing_state.get("geometry_sha256") or "")
            manufacturing_sha256 = str(getattr(entity, "manufacturing_hash", "") or "")
            return source_revision, geometry_sha256, manufacturing_sha256

        def _load_dimension_editor(self) -> None:
            if self._workspace is None or not self._entity_id:
                self._dimension_document = None
                self._dimension_model = None
                self._loaded_lock_version = 0
                self._update_dimension_properties()
                return
            source_revision, geometry_sha256, manufacturing_sha256 = self._entity_revision_context()
            self._dimension_document = DimensionDocumentStore.load(
                self._workspace.project,
                entity_id=self._entity_id,
                source_revision=source_revision,
                geometry_sha256=geometry_sha256,
                manufacturing_sha256=manufacturing_sha256,
                user=self._current_user(),
            )
            self._loaded_lock_version = int(self._dimension_document.lock_version)
            self._dimension_model = DimensionEditorModel(self._dimension_document)
            self._manual_dimensions.clear()
            self._update_dimension_properties()

        def _persist_dimension_editor(self, action: str) -> bool:
            if self._workspace is None or self._dimension_document is None:
                return False
            try:
                self._loaded_lock_version = DimensionDocumentStore.save(
                    self._workspace.project,
                    self._dimension_document,
                    expected_lock_version=self._loaded_lock_version,
                    user=self._current_user(),
                )
                project = self._workspace.project
                if hasattr(project, "audit"):
                    project.audit(
                        action,
                        user=self._current_user(),
                        entity_id=self._entity_id,
                        details={
                            "drawing_id": self._dimension_document.drawing_id,
                            "drawing_revision": self._dimension_document.drawing_revision,
                            "dimension_ids": sorted(self._dimension_model.selected_ids if self._dimension_model else ()),
                            "lock_version": self._loaded_lock_version,
                        },
                    )
                session = getattr(self._workspace, "session", None)
                if session is not None:
                    session.dirty = True
                    if getattr(session, "path", None) is not None and not getattr(session, "read_only", False):
                        try:
                            session.autosave()
                        except Exception as exc:
                            self.status.setText(f"Maat opgeslagen; autosave-waarschuwing: {exc}")
                return True
            except RuntimeError as exc:
                self.status.setText(str(exc))
                QtWidgets.QMessageBox.warning(self, "Maatvoeringsconflict", str(exc))
                return False
            except Exception as exc:
                self.status.setText(f"Maatvoering opslaan mislukt: {exc}")
                return False

        def _manual_dimension_records(self) -> tuple[dict[str, Any], ...]:
            records = []
            if self._dimension_document is not None:
                records.extend(self._dimension_document.render_records())
            records.extend(dict(item) for item in self._manual_dimensions)
            return tuple(records)

        def _sheet_to_projected(self, point: tuple[float, float], view_id: str) -> tuple[float, float]:
            if self._drawing_document is None:
                return ()
            context = next(
                (
                    dict(item) for item in self._drawing_document.view_contexts
                    if str(item.get("view_id") or "") == str(view_id)
                ),
                None,
            )
            if context is None:
                return ()
            scale = float(context.get("scale") or 1.0)
            projected_center = tuple(float(value) for value in context.get("projected_center") or (0.0, 0.0))
            sheet_center = tuple(float(value) for value in context.get("sheet_center") or (0.0, 0.0))
            return (
                (float(point[0]) - sheet_center[0]) / scale + projected_center[0],
                -(float(point[1]) - sheet_center[1]) / scale + projected_center[1],
            )

        def _sync_layout_projection(self, dimension: Any) -> None:
            dimension.line_projected_position = self._sheet_to_projected(dimension.line_position, dimension.view_id)
            dimension.text_projected_position = self._sheet_to_projected(dimension.text_position, dimension.view_id)

        def _ensure_dimension_editable(self) -> bool:
            if self._workspace is None or self._dimension_document is None or self._dimension_model is None:
                return False
            session = getattr(self._workspace, "session", None)
            if session is not None and bool(getattr(session, "read_only", False)):
                self.status.setText("Project is alleen-lezen; maatvoering kan niet worden gewijzigd")
                return False
            if self._dimension_document.status != "released":
                return True
            reason, accepted = QtWidgets.QInputDialog.getText(
                self,
                "Nieuwe tekeningsrevisie",
                "De maatvoering is vrijgegeven. Geef de wijzigingsreden voor een nieuwe conceptrevisie:",
            )
            if not accepted or not reason.strip():
                self.status.setText("Vrijgegeven maatvoering blijft ongewijzigd")
                return False
            self._dimension_model.begin_revision(reason=reason.strip(), user=self._current_user())
            self._persist_dimension_editor("drawing.dimension_revision_forked")
            return True

        def _activate_dimension_tool(self, kind: str) -> None:
            self._dimension_tool = str(kind)
            if kind == "select":
                self.preview.set_selection_mode(True)
                self._dimension_controller.cancel()
                self._dimension_controller.set_state(InteractionState.IDLE)
                self.dimension_instruction.setText("Selecteer een maatobject; Ctrl voor multiselectie")
                self.preview.set_draft(())
                return
            if self._workspace is None or not self._entity_id:
                self.dimension_tool_buttons["select"].setChecked(True)
                self._dimension_tool = "select"
                self.status.setText("Selecteer eerst een geometrisch onderdeel")
                return
            if not self._ensure_dimension_editable():
                self.dimension_tool_buttons["select"].setChecked(True)
                self._dimension_tool = "select"
                return
            self.preview.set_selection_mode(False)
            if self._drawing_document is None:
                self.refresh_preview()
            self._dimension_controller.arm(kind)
            self.dimension_instruction.setText(self._dimension_controller.instruction)
            self.preview.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)

        def _on_dimension_pointer(self, point: object, candidate: object) -> None:
            if not isinstance(point, tuple):
                return
            self._dimension_controller.pointer = point
            self.preview.set_draft(
                (anchor.sheet_point for anchor in self._dimension_controller.anchors),
                point,
            )
            if candidate is not None and self._dimension_tool != "select":
                valid = "geldig" if candidate.valid else f"ongeldig: {candidate.reason}"
                self.status.setText(f"Snap {candidate.label} · {valid} · Tab wisselt overlappende kandidaten")

        def _on_dimension_canvas_click(self, point: object, candidate: object, modifiers: object) -> None:
            if not isinstance(point, tuple) or self._dimension_model is None or self._dimension_document is None:
                return
            if self._dimension_tool.startswith("reanchor:"):
                if candidate is None or not candidate.valid:
                    self.status.setText("Selecteer een geldige nieuwe snapreferentie")
                    return
                dimension_id, anchor_index = self._dimension_tool.split(":", 2)[1:]
                try:
                    self._dimension_model.reanchor(
                        dimension_id,
                        int(anchor_index),
                        candidate.anchor,
                        user=self._current_user(),
                    )
                except (IndexError, StopIteration, ValueError) as exc:
                    self.status.setText(str(exc))
                    return
                self._persist_dimension_editor("drawing.dimension_reanchored")
                self._dimension_tool = "select"
                self.preview.set_selection_mode(True)
                self.dimension_tool_buttons["select"].setChecked(True)
                self.dimension_instruction.setText("Anker opnieuw gekoppeld")
                self._update_dimension_properties()
                self.refresh_preview()
                return
            if self._dimension_tool == "select" or self._dimension_controller.state == InteractionState.IDLE:
                dimension_id = self.preview.dimension_at(
                    point,
                    (item.dimension_id for item in self._dimension_document.dimensions),
                )
                extend = bool(modifiers & QtCore.Qt.KeyboardModifier.ControlModifier)
                self._dimension_model.select((dimension_id,) if dimension_id else (), extend=extend)
                self.preview.set_selected_ids(self._dimension_model.selected_ids)
                self._dimension_controller.set_state(
                    InteractionState.EDIT_SELECTED if self._dimension_model.selected_ids else InteractionState.IDLE
                )
                self._update_dimension_properties()
                return
            state = self._dimension_controller.state
            if state in {InteractionState.PICK_FIRST_ANCHOR, InteractionState.PICK_NEXT_ANCHOR}:
                if candidate is None or not candidate.valid:
                    self.status.setText("Geen geldige snapreferentie; wijs een gemarkeerd punt, rand of centrum aan")
                    return
                if self._dimension_tool in {DimensionKind.RADIUS.value, DimensionKind.DIAMETER.value} and not candidate.anchor.curve_parameter:
                    self.status.setText("Selecteer voor radius/diameter het gemarkeerde centrum van een cirkel of gat")
                    return
                try:
                    self._dimension_controller.accept_anchor(candidate.anchor)
                except (ValueError, RuntimeError) as exc:
                    self.status.setText(str(exc))
                    return
                self.dimension_instruction.setText(self._dimension_controller.instruction)
                self.preview.set_draft((anchor.sheet_point for anchor in self._dimension_controller.anchors), point)
                return
            if state in {InteractionState.PLACE_DIMENSION_LINE, InteractionState.PLACE_TEXT}:
                if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier and self._dimension_controller.anchors:
                    reference = self._dimension_controller.anchors[-1].sheet_point
                    if abs(point[0] - reference[0]) >= abs(point[1] - reference[1]):
                        point = (point[0], reference[1])
                    else:
                        point = (reference[0], point[1])
                label = ""
                if not self._dimension_controller.anchors and self._drawing_document is not None:
                    active_page = int(self.page_selector.currentData() or 0) + 1
                    context = next(
                        (
                            dict(item) for item in self._drawing_document.view_contexts
                            if int(item.get("page_number") or 1) == active_page
                            and len(item.get("rectangle") or ()) == 4
                            and float(item["rectangle"][0]) <= point[0] <= float(item["rectangle"][2])
                            and float(item["rectangle"][1]) <= point[1] <= float(item["rectangle"][3])
                        ),
                        None,
                    )
                    if context is None:
                        self.status.setText("Plaats een tekstnotitie binnen een geldig aanzicht")
                        return
                    self._dimension_document.extensions["active_view_id"] = str(context.get("view_id") or "")
                    self._dimension_document.extensions["active_page_number"] = active_page
                if self._dimension_tool in {DimensionKind.LEADER.value, DimensionKind.TEXT.value}:
                    label, accepted = QtWidgets.QInputDialog.getText(self, "Annotatietekst", "Tekst")
                    if not accepted:
                        return
                try:
                    dimension = self._dimension_controller.place(
                        point,
                        document=self._dimension_document,
                        user=self._current_user(),
                        label=str(label).strip(),
                    )
                    if dimension.kind in {DimensionKind.LEADER.value, DimensionKind.TEXT.value}:
                        dimension.metadata["annotation_kind"] = str(self.annotation_kind.currentData() or "free")
                    self._sync_layout_projection(dimension)
                    self._dimension_model.add(dimension, user=self._current_user())
                except (ValueError, RuntimeError) as exc:
                    self.status.setText(str(exc))
                    return
                self._persist_dimension_editor("drawing.dimension_added")
                self._dimension_tool = "select"
                self.preview.set_selection_mode(True)
                self.dimension_tool_buttons["select"].setChecked(True)
                self._dimension_controller.set_state(InteractionState.IDLE)
                self.preview.set_draft(())
                self._update_dimension_properties()
                self.refresh_preview()

        def _on_dimension_area_selected(self, start: object, end: object, modifiers: object) -> None:
            if (
                self._dimension_model is None
                or self._dimension_document is None
                or self._drawing_document is None
                or not isinstance(start, tuple)
                or not isinstance(end, tuple)
            ):
                return
            left, right = sorted((float(start[0]), float(end[0])))
            top, bottom = sorted((float(start[1]), float(end[1])))
            crossing = float(end[0]) < float(start[0])
            valid_ids = {item.dimension_id for item in self._dimension_document.dimensions}
            selected: set[str] = set()
            page = self._drawing_document.pages[self.preview.page_index]
            for primitive in page.primitives:
                dimension_id = str(primitive.semantic_id or "")
                if dimension_id not in valid_ids:
                    continue
                bounds = primitive.bounds()
                if not bounds:
                    continue
                contained = left <= bounds[0] and top <= bounds[1] and bounds[2] <= right and bounds[3] <= bottom
                intersects = not (bounds[2] < left or bounds[0] > right or bounds[3] < top or bounds[1] > bottom)
                if contained or (crossing and intersects):
                    selected.add(dimension_id)
            extend = bool(modifiers & QtCore.Qt.KeyboardModifier.ControlModifier)
            self._dimension_model.select(selected, extend=extend)
            self.preview.set_selected_ids(self._dimension_model.selected_ids)
            self._update_dimension_properties()
            self.status.setText(
                f"Vensterselectie: {len(selected)} maatobject(en) · "
                + ("kruisend" if crossing else "volledig binnen venster")
            )

        def _on_dimension_command(self, command: str) -> None:
            if command.startswith("tool:"):
                tool = command.split(":", 1)[1]
                button = self.dimension_tool_buttons.get(tool)
                if button is not None:
                    button.setChecked(True)
                self._activate_dimension_tool(tool)
            elif command == "cancel":
                self._dimension_controller.cancel()
                self._dimension_tool = "select"
                self.preview.set_selection_mode(True)
                self.dimension_tool_buttons["select"].setChecked(True)
                self.dimension_instruction.setText("Bewerking geannuleerd")
                self.preview.set_draft(())
            elif command == "backspace" and self._dimension_tool != "select":
                self._dimension_controller.backspace()
                self.dimension_instruction.setText(self._dimension_controller.instruction)
                self.preview.set_draft(anchor.sheet_point for anchor in self._dimension_controller.anchors)
            elif command == "delete":
                self._delete_selected_dimensions()
            elif command == "undo":
                self._undo_dimensions()
            elif command == "redo":
                self._redo_dimensions()
            elif command == "enter":
                if self._dimension_controller.kind in {
                    DimensionKind.CHAIN.value,
                    DimensionKind.BASELINE.value,
                } and self._dimension_controller.state == InteractionState.PICK_NEXT_ANCHOR:
                    try:
                        self._dimension_controller.finish_anchor_series()
                        self.dimension_instruction.setText(self._dimension_controller.instruction)
                    except ValueError as exc:
                        self.status.setText(str(exc))
                elif self._dimension_controller.state in {InteractionState.PLACE_DIMENSION_LINE, InteractionState.PLACE_TEXT} and self._dimension_controller.pointer:
                    self._on_dimension_canvas_click(
                        self._dimension_controller.pointer,
                        None,
                        QtCore.Qt.KeyboardModifier.NoModifier,
                    )

        def _delete_selected_dimensions(self) -> None:
            if self._dimension_model is None or not self._dimension_model.selected_ids:
                self.status.setText("Selecteer eerst één of meer handmatige maatobjecten")
                return
            if not self._ensure_dimension_editable():
                return
            count = len(self._dimension_model.selected_ids)
            if count > 1 and QtWidgets.QMessageBox.question(
                self,
                "Maten verwijderen",
                f"{count} geselecteerde maatobjecten verwijderen?",
            ) != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            removed = self._dimension_model.delete_selected(user=self._current_user())
            if removed:
                self._persist_dimension_editor("drawing.dimensions_deleted")
                self.preview.set_selected_ids(())
                self._update_dimension_properties()
                self.refresh_preview()

        def _copy_dimensions(self) -> None:
            if self._dimension_model is None:
                return
            self._dimension_clipboard = self._dimension_model.copy_selected()
            self.status.setText(f"{len(self._dimension_clipboard)} maatobject(en) gekopieerd")

        def _paste_dimensions(self) -> None:
            if self._dimension_model is None or not self._dimension_clipboard or not self._ensure_dimension_editable():
                return
            if self._dimension_model.paste(self._dimension_clipboard, user=self._current_user()):
                for item in self._dimension_document.dimensions:
                    if item.dimension_id in self._dimension_model.selected_ids:
                        self._sync_layout_projection(item)
                self._persist_dimension_editor("drawing.dimensions_pasted")
                self._update_dimension_properties()
                self.refresh_preview()

        def _align_dimensions(self, axis: str) -> None:
            if self._dimension_model is None or not self._ensure_dimension_editable():
                return
            if self._dimension_model.align_selected(axis, user=self._current_user()):
                for item in self._dimension_document.dimensions:
                    if item.dimension_id in self._dimension_model.selected_ids:
                        self._sync_layout_projection(item)
                self._persist_dimension_editor(f"drawing.dimensions_aligned_{axis}")
                self.refresh_preview()

        def _distribute_dimensions(self, axis: str) -> None:
            if self._dimension_model is None or not self._ensure_dimension_editable():
                return
            if self._dimension_model.distribute_selected(axis, user=self._current_user()):
                for item in self._dimension_document.dimensions:
                    if item.dimension_id in self._dimension_model.selected_ids:
                        self._sync_layout_projection(item)
                self._persist_dimension_editor(f"drawing.dimensions_distributed_{axis}")
                self.refresh_preview()

        def _mirror_dimensions(self) -> None:
            if self._dimension_model is None or not self._ensure_dimension_editable():
                return
            if self._dimension_model.mirror_selected(user=self._current_user()):
                for item in self._dimension_document.dimensions:
                    if item.dimension_id in self._dimension_model.selected_ids:
                        self._sync_layout_projection(item)
                self._persist_dimension_editor("drawing.dimensions_mirrored")
                self.refresh_preview()

        def _change_dimension_order(self, delta: int) -> None:
            if self._dimension_model is None or not self._ensure_dimension_editable():
                return
            if self._dimension_model.change_cluster_order(delta, user=self._current_user()):
                self._persist_dimension_editor("drawing.dimension_cluster_order_changed")
                self.refresh_preview()

        def _set_leader_bend(self) -> None:
            if self._dimension_model is None or not self._ensure_dimension_editable():
                return
            selected = [
                item for item in self._dimension_document.dimensions
                if item.dimension_id in self._dimension_model.selected_ids and item.kind == DimensionKind.LEADER.value
            ]
            if not selected:
                self.status.setText("Selecteer eerst één of meer leaders")
                return
            reference = selected[0].line_position
            x, accepted = QtWidgets.QInputDialog.getDouble(self, "Leaderknikpunt", "X op blad", reference[0], -10000, 10000, 2)
            if not accepted:
                return
            y, accepted = QtWidgets.QInputDialog.getDouble(self, "Leaderknikpunt", "Y op blad", reference[1], -10000, 10000, 2)
            if not accepted:
                return
            if self._dimension_model.set_leader_bend(
                (x, y),
                projected_point=self._sheet_to_projected((x, y), selected[0].view_id),
                user=self._current_user(),
            ):
                self._persist_dimension_editor("drawing.leader_bend_changed")
                self.refresh_preview()

        def _edit_dimension_style(self) -> None:
            if self._dimension_model is None or self._dimension_document is None or not self._ensure_dimension_editable():
                return
            current = self._dimension_document.style
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("DimensionStyle-profiel")
            form = QtWidgets.QFormLayout(dialog)
            scope = QtWidgets.QComboBox(dialog)
            for label, value in (("CWS-standaard", "standard"), ("Bedrijf", "company"), ("Project", "project"), ("Maatobject", "object")):
                scope.addItem(label, value)
            scope.setCurrentIndex(max(0, scope.findData(current.profile_scope)))
            style_id = QtWidgets.QLineEdit(current.style_id, dialog)
            version = QtWidgets.QLineEdit(current.version, dialog)
            text_height = QtWidgets.QDoubleSpinBox(dialog)
            text_height.setRange(2.0, 12.0)
            text_height.setDecimals(2)
            text_height.setValue(current.text_height_mm)
            arrow_size = QtWidgets.QDoubleSpinBox(dialog)
            arrow_size.setRange(0.5, 12.0)
            arrow_size.setDecimals(2)
            arrow_size.setValue(current.arrow_size_mm)
            decimals = QtWidgets.QSpinBox(dialog)
            decimals.setRange(0, 6)
            decimals.setValue(current.decimals)
            decimal_separator = QtWidgets.QComboBox(dialog)
            decimal_separator.addItems((",", "."))
            decimal_separator.setCurrentText(current.decimal_separator)
            trailing = QtWidgets.QCheckBox("Trailing zeros tonen", dialog)
            trailing.setChecked(current.trailing_zeros)
            reason = QtWidgets.QLineEdit(dialog)
            reason.setPlaceholderText("Verplichte wijzigingsreden")
            form.addRow("Profielscope", scope)
            form.addRow("Stijl-ID", style_id)
            form.addRow("Versie", version)
            form.addRow("Teksthoogte op papier", text_height)
            form.addRow("Pijlgrootte", arrow_size)
            form.addRow("Decimalen", decimals)
            form.addRow("Decimaalteken", decimal_separator)
            form.addRow(trailing)
            form.addRow("Wijzigingsreden", reason)
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
                parent=dialog,
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            form.addRow(buttons)
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return
            scope_value = str(scope.currentData() or "standard")
            if scope_value == "standard":
                updated = DimensionStyle.cws_standard()
            else:
                updated = DimensionStyle.from_dict(current.to_dict())
                updated.profile_scope = scope_value
                updated.style_id = style_id.text().strip()
                updated.version = version.text().strip()
                updated.text_height_mm = float(text_height.value())
                updated.arrow_size_mm = float(arrow_size.value())
                updated.decimals = int(decimals.value())
                updated.decimal_separator = decimal_separator.currentText()
                updated.trailing_zeros = trailing.isChecked()
            try:
                self._dimension_model.update_style(
                    updated,
                    reason=reason.text().strip(),
                    role=self._current_drawing_role(),
                    user=self._current_user(),
                )
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(self, "Maatstijl", str(exc))
                return
            self._persist_dimension_editor("drawing.dimension_style_changed")
            self.refresh_preview()
            # The first render proves the new style and revalidates STALE
            # objects; the second refresh exposes the resulting lint verdict.
            self.refresh_preview()

        def _on_dimension_dragged(self, dimension_id: str, delta: object, text_only: bool) -> None:
            if self._dimension_model is None or not isinstance(delta, tuple):
                return
            if not self._ensure_dimension_editable():
                return
            self._dimension_model.select((dimension_id,))
            self._dimension_controller.set_state(
                InteractionState.DRAG_TEXT if bool(text_only) else InteractionState.DRAG_DIMENSION
            )
            if self._dimension_model.move_selected(delta, text_only=bool(text_only), user=self._current_user()):
                for item in self._dimension_document.dimensions:
                    if item.dimension_id in self._dimension_model.selected_ids:
                        self._sync_layout_projection(item)
                self._persist_dimension_editor(
                    "drawing.dimension_text_moved" if text_only else "drawing.dimension_line_moved"
                )
                self._update_dimension_properties()
                self.refresh_preview()
            self._dimension_controller.set_state(InteractionState.EDIT_SELECTED)

        def _start_reanchor(self) -> None:
            if self._dimension_model is None or self._dimension_document is None or len(self._dimension_model.selected_ids) != 1:
                self.status.setText("Selecteer precies één maat om opnieuw te ankeren")
                return
            if not self._ensure_dimension_editable():
                return
            item = next(value for value in self._dimension_document.dimensions if value.dimension_id in self._dimension_model.selected_ids)
            if not item.anchors:
                self.status.setText("Deze annotatie heeft geen geometrisch anker")
                return
            anchor_index = 0
            if len(item.anchors) > 1:
                labels = [f"Anker {index + 1}: {anchor.anchor_type} · {anchor.feature_id or anchor.subshape_id}" for index, anchor in enumerate(item.anchors)]
                selected, accepted = QtWidgets.QInputDialog.getItem(
                    self,
                    "Opnieuw ankeren",
                    "Welk anker wilt u vervangen?",
                    labels,
                    0,
                    False,
                )
                if not accepted:
                    return
                anchor_index = labels.index(selected)
            self._dimension_tool = f"reanchor:{item.dimension_id}:{anchor_index}"
            self.preview.set_selection_mode(False)
            self._dimension_controller.set_state(
                InteractionState.REANCHOR_FIRST if anchor_index == 0 else InteractionState.REANCHOR_SECOND
            )
            self.dimension_instruction.setText(f"Selecteer nieuw geometrisch anker {anchor_index + 1} · Esc annuleert")
            self.preview.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)

        def _duplicate_dimensions(self) -> None:
            if self._dimension_model is None or not self._dimension_model.selected_ids:
                self.status.setText("Selecteer eerst één of meer handmatige maten")
                return
            if not self._ensure_dimension_editable():
                return
            if self._dimension_model.duplicate_selected(user=self._current_user()):
                for item in self._dimension_document.dimensions:
                    if item.dimension_id in self._dimension_model.selected_ids:
                        self._sync_layout_projection(item)
                self._persist_dimension_editor("drawing.dimensions_duplicated")
                self._update_dimension_properties()
                self.refresh_preview()

        def _toggle_selected_dimension(self) -> None:
            if self._dimension_model is None or not self._dimension_model.selected_ids:
                self.status.setText("Selecteer eerst een handmatige maat")
                return
            if not self._ensure_dimension_editable():
                return
            selected = [
                item for item in self._dimension_document.dimensions
                if item.dimension_id in self._dimension_model.selected_ids
            ]
            visible = not all(item.visible for item in selected)
            self._dimension_model.set_visibility(visible, user=self._current_user())
            self._persist_dimension_editor("drawing.dimensions_visibility_changed")
            self._update_dimension_properties()
            self.refresh_preview()

        def _undo_dimensions(self) -> None:
            if not self._ensure_dimension_editable():
                return
            if self._dimension_model is not None and self._dimension_model.undo(user=self._current_user()):
                self._persist_dimension_editor("drawing.dimension_undo")
                self._update_dimension_properties()
                self.refresh_preview()

        def _redo_dimensions(self) -> None:
            if not self._ensure_dimension_editable():
                return
            if self._dimension_model is not None and self._dimension_model.redo(user=self._current_user()):
                self._persist_dimension_editor("drawing.dimension_redo")
                self._update_dimension_properties()
                self.refresh_preview()

        def _reset_dimension_layout(self) -> None:
            if not self._ensure_dimension_editable():
                return
            if self._dimension_model is not None and self._dimension_model.reset_layout(user=self._current_user()):
                for item in self._dimension_document.dimensions:
                    if not self._dimension_model.selected_ids or item.dimension_id in self._dimension_model.selected_ids:
                        self._sync_layout_projection(item)
                self._persist_dimension_editor("drawing.dimension_layout_reset")
                self._update_dimension_properties()
                self.refresh_preview()

        def _release_dimension_revision(self) -> None:
            if self._dimension_model is None or self._dimension_document is None:
                return
            if self._drawing_document is None:
                self.refresh_preview()
            ignored = {"DRAWING_DIMENSION_EDITOR_NOT_RELEASED"}
            blocking = [
                item for item in dict(getattr(self._drawing_document, "lint", {}) or {}).get("issues", ())
                if bool(item.get("blocking", True)) and str(item.get("code") or "") not in ignored
            ]
            if blocking:
                message = "Vrijgave geblokkeerd door DrawingLinter: " + ", ".join(
                    str(item.get("code") or "DRAWING_BLOCKED") for item in blocking[:5]
                )
                self.status.setText(message)
                QtWidgets.QMessageBox.warning(self, "Maatvoering vrijgeven", message)
                return
            try:
                self._dimension_model.release(role=self._current_drawing_role(), user=self._current_user())
            except (PermissionError, ValueError) as exc:
                self.status.setText(str(exc))
                QtWidgets.QMessageBox.warning(self, "Maatvoering vrijgeven", str(exc))
                return
            self._persist_dimension_editor("drawing.dimension_revision_released")
            self.status.setText(f"Maatvoering {self._dimension_document.drawing_revision} vrijgegeven")
            self._update_dimension_properties()
            self.refresh_preview()

        def _update_dimension_properties(self) -> None:
            if not hasattr(self, "dimension_properties"):
                return
            self.dimension_properties.clear()
            released = []
            if self._dimension_document is not None:
                released = list(self._dimension_document.extensions.get("released_revisions") or ())
            if released:
                previous = dict(released[-1])
                old_ids = {str(item.get("dimension_id") or "") for item in previous.get("dimensions") or ()}
                current_ids = {item.dimension_id for item in self._dimension_document.dimensions}
                self.revision_summary.setText(
                    f"Revisievergelijking {previous.get('drawing_revision', '-') } → {self._dimension_document.drawing_revision}: "
                    f"+{len(current_ids - old_ids)} / −{len(old_ids - current_ids)} / behouden {len(old_ids & current_ids)}"
                )
            else:
                self.revision_summary.setText("Revisievergelijking: geen vrijgegeven basis")
            lint_issues = list(dict(getattr(self._drawing_document, "lint", {}) or {}).get("issues", ()))
            blockers = [str(value.get("code") or "") for value in lint_issues if bool(value.get("blocking", True))]
            self.dimension_issue_summary.setText(
                "Problemen: geen blokkerende meldingen"
                if not blockers
                else "Problemen / vrijgave geblokkeerd: " + ", ".join(blockers[:4])
            )
            selected = []
            if self._dimension_model is not None and self._dimension_document is not None:
                selected = [
                    item for item in self._dimension_document.dimensions
                    if item.dimension_id in self._dimension_model.selected_ids
                ]
            self.edit_properties_button.setEnabled(bool(selected))
            if not selected:
                total = len(self._dimension_document.dimensions) if self._dimension_document is not None else 0
                QtWidgets.QTreeWidgetItem(self.dimension_properties, ("Selectie", f"geen · {total} maatobject(en)"))
                return
            if len(selected) > 1:
                QtWidgets.QTreeWidgetItem(self.dimension_properties, ("Selectie", f"{len(selected)} maatobjecten"))
                return
            item = selected[0]
            values = (
                ("Maat-ID", item.dimension_id),
                ("Type", item.kind),
                ("Waarde", f"{item.nominal_value_mm:g} mm"),
                ("Tekst", item.label or "automatisch"),
                ("Prefix / suffix", f"{item.prefix or '-'} / {item.suffix or '-'}"),
                ("Eenheid / decimalen", f"{self._dimension_document.style.unit} / {self._dimension_document.style.decimals}"),
                (
                    "Tolerantie",
                    f"+{float(item.tolerance_upper_mm or 0.0):g} / {float(item.tolerance_lower_mm or 0.0):g} mm",
                ),
                ("Aanzicht / blad", f"{item.view_id} / {item.page_number}"),
                ("Status", item.state),
                ("REF / inspectie", f"{'ja' if item.reference else 'nee'} / {'ja' if item.inspection else 'nee'}"),
                ("Zichtbaar", "ja" if item.visible else "nee"),
                ("Ankers", str(len(item.anchors))),
                ("Bronrevisie", item.source_revision),
                ("Tekeningrevisie", item.drawing_revision),
                ("Stijl", f"{item.style_id} {item.style_version}"),
                ("Annotatiesemantiek", str(item.metadata.get("annotation_kind") or "-")),
                ("Hoekmodus", str(item.metadata.get("angle_mode") or "-")),
                ("Override reden", item.override_reason or "-"),
                ("Override goedgekeurd", item.override_approved_by or "nee"),
                ("Waarschuwing", "vrijgave geblokkeerd" if item.state in {"ORPHANED", "ORPHANED_VIEW", "CONFLICT", "STALE"} else "geen"),
                ("Gewijzigd door", item.modified_by),
            )
            for label, value in values:
                QtWidgets.QTreeWidgetItem(self.dimension_properties, (label, str(value)))
            self.dimension_properties.resizeColumnToContents(0)

        def _edit_dimension_properties(self) -> None:
            if self._dimension_model is None or self._dimension_document is None or not self._dimension_model.selected_ids:
                return
            if not self._ensure_dimension_editable():
                return
            selected_items = [value for value in self._dimension_document.dimensions if value.dimension_id in self._dimension_model.selected_ids]
            item = selected_items[0]
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(
                f"Maateigenschappen · {item.dimension_id}"
                if len(selected_items) == 1
                else f"Maateigenschappen · {len(selected_items)} geselecteerd"
            )
            form = QtWidgets.QFormLayout(dialog)
            label = QtWidgets.QLineEdit(item.label, dialog)
            override_reason = QtWidgets.QLineEdit(item.override_reason, dialog)
            override_reason.setPlaceholderText("Verplicht wanneer geometrische maattekst wordt aangepast")
            prefix = QtWidgets.QLineEdit(item.prefix, dialog)
            suffix = QtWidgets.QLineEdit(item.suffix, dialog)
            upper = QtWidgets.QDoubleSpinBox(dialog)
            lower = QtWidgets.QDoubleSpinBox(dialog)
            for control in (upper, lower):
                control.setRange(-1000.0, 1000.0)
                control.setDecimals(3)
                control.setSuffix(" mm")
            upper.setValue(float(item.tolerance_upper_mm or 0.0))
            lower.setValue(float(item.tolerance_lower_mm or 0.0))
            reference = QtWidgets.QCheckBox("REF / referentiemaat", dialog)
            reference.setChecked(item.reference)
            inspection = QtWidgets.QCheckBox("Controle-/inspectiemaat", dialog)
            inspection.setChecked(item.inspection)
            visible = QtWidgets.QCheckBox("Zichtbaar", dialog)
            visible.setChecked(item.visible)
            angle_mode = QtWidgets.QComboBox(dialog)
            for mode_label, mode_value in (("Binnenhoek", "inside"), ("Buitenhoek", "outside"), ("Supplementair", "supplementary")):
                angle_mode.addItem(mode_label, mode_value)
            angle_mode.setCurrentIndex(max(0, angle_mode.findData(str(item.metadata.get("angle_mode") or "inside"))))
            form.addRow(
                "Berekende waarde",
                QtWidgets.QLabel(
                    f"{item.nominal_value_mm:g} mm (alleen-lezen)"
                    if len(selected_items) == 1
                    else "Meerdere geometrische waarden (alleen-lezen)"
                ),
            )
            form.addRow("Tekst", label)
            form.addRow("Reden tekstoverride", override_reason)
            form.addRow("Prefix", prefix)
            form.addRow("Suffix", suffix)
            form.addRow("Boventolerantie", upper)
            form.addRow("Ondertolerantie", lower)
            form.addRow(reference)
            form.addRow(inspection)
            form.addRow(visible)
            if any(value.kind == DimensionKind.ANGLE.value for value in selected_items):
                form.addRow("Hoekmodus", angle_mode)
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
                parent=dialog,
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            form.addRow(buttons)
            if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                return
            new_label = label.text().strip()
            geometric = any(value.kind not in {DimensionKind.TEXT.value, DimensionKind.LEADER.value} for value in selected_items)
            override_changed = geometric and new_label != item.label
            if override_changed and not override_reason.text().strip():
                QtWidgets.QMessageBox.warning(
                    self,
                    "Maattekstoverride",
                    "Een aangepaste geometrische maattekst vereist een wijzigingsreden en formele controle.",
                )
                return
            self._dimension_model.update_selected(
                {
                    "label": item.label if override_changed else new_label,
                    "prefix": prefix.text(),
                    "suffix": suffix.text(),
                    "tolerance_upper_mm": float(upper.value()),
                    "tolerance_lower_mm": float(lower.value()),
                    "reference": reference.isChecked(),
                    "inspection": inspection.isChecked(),
                    "visible": visible.isChecked(),
                },
                user=self._current_user(),
            )
            if override_changed:
                self._dimension_model.override_selected(
                    display_text=new_label,
                    reason=override_reason.text().strip(),
                    role=self._current_drawing_role(),
                    user=self._current_user(),
                )
            if any(value.kind == DimensionKind.ANGLE.value for value in selected_items):
                self._dimension_model.set_angle_mode(
                    str(angle_mode.currentData() or "inside"),
                    user=self._current_user(),
                )
            self._persist_dimension_editor("drawing.dimension_properties_changed")
            self._update_dimension_properties()
            self.refresh_preview()

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
            legacy_record = {
                "view": str(view.currentData()), "axis": str(axis.currentData()),
                "start": float(start.value()), "end": float(end.value()), "label": label.text().strip(),
                "entity_id": self._entity_id,
                "feature_id": str(feature.currentData()),
                "subshape_id": "",
                "anchor_type": str(anchor_type.currentData()),
                "nominal_value_mm": abs(float(end.value()) - float(start.value())),
                "tolerance_mm": float(tolerance.value()),
                "provenance": {"method": "user", "surface": "review_snapshot"},
            }
            if self._dimension_document is None:
                self._load_dimension_editor()
            if self._dimension_document is not None:
                if not self._ensure_dimension_editable():
                    return
                DimensionDocumentStore.migrate_legacy(
                    (legacy_record,),
                    self._dimension_document,
                    user=self._current_user(),
                )
                self._dimension_model = DimensionEditorModel(self._dimension_document)
                self._persist_dimension_editor("drawing.legacy_dimension_added")
            else:
                self._manual_dimensions.append(legacy_record)
            self.dimensions_button.setChecked(True)
            total = len(self._dimension_document.dimensions) if self._dimension_document is not None else len(self._manual_dimensions)
            self.status.setText(f"Eigen maat toegevoegd ({total} totaal); legacy offset blijft reviewplichtig")
            self.refresh_preview()

        def _clear_manual_dimensions(self) -> None:
            self._delete_selected_dimensions()

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
                self._drawing_document = None
                self._load_dimension_editor()
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

            # Assemblies now have their own multi-sheet drawing/BOM route.
            if current in project.assemblies and drawable(current):
                return current
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
                self._drawing_document = None
                self._load_dimension_editor()
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
                    manual_dimensions=self._manual_dimension_records(),
                    dimension_style=(self._dimension_document.style.to_dict() if self._dimension_document is not None else {}),
                    dimension_audit=(tuple(self._dimension_document.audit) if self._dimension_document is not None else ()),
                    dimension_editor_schema=(DIMENSION_EDITOR_SCHEMA if self._dimension_document is not None else ""),
                    dimension_editor_status=(self._dimension_document.status if self._dimension_document is not None else ""),
                    orientation=str(self.orientation.currentData() or "landscape"),
                    include_sections=self.sections_button.isChecked(),
                    include_details=self.details_button.isChecked(),
                )
                self._drawing_document = result.document
                if self._dimension_document is not None and result.document is not None:
                    if not self._dimension_document.dimensions:
                        self._dimension_document.geometry_sha256 = result.document.geometry_sha256
                        self._dimension_document.manufacturing_sha256 = result.document.manufacturing_sha256
                    previous_states = [item.state for item in self._dimension_document.dimensions]
                    self._dimension_model.revalidate(
                        result.document,
                        valid_view_ids=(str(item.get("view_id") or item.get("view") or "") for item in result.document.view_contexts),
                    )
                    if previous_states != [item.state for item in self._dimension_document.dimensions]:
                        self._persist_dimension_editor("drawing.dimension_anchors_revalidated")
                self._update_page_selector(result.page_count)
                if result.png_path:
                    self._last_png = Path(result.png_path)
                    self._show_pixmap()
                warning = f" | {result.warnings[0]}" if result.warnings else ""
                release = "productie-gereed" if result.release_ready else "review; productie geblokkeerd"
                self.status.setText(
                    f"Reviewdocument gegenereerd op schaal {result.scale_label}: "
                    f"{result.pdf_path or result.png_path}{warning} | {result.page_count} blad(en) | {release}"
                )
                self._update_dimension_properties()
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
            page_index = int(self.page_selector.currentData() or 0)
            if page_index == 0 or self._drawing_document is None:
                pixmap = QtGui.QPixmap(str(self._last_png))
            else:
                from cws_convertor.drawings import ProductionDrawingRenderer

                with tempfile.TemporaryDirectory(prefix="cws_drawing_page_") as folder:
                    temporary_pdf = Path(folder) / "preview.pdf"
                    temporary_png = Path(folder) / "preview.png"
                    ProductionDrawingRenderer.render_pdf(self._drawing_document, temporary_pdf)
                    ProductionDrawingRenderer.render_png(
                        temporary_pdf,
                        temporary_png,
                        page_number=page_index,
                    )
                    pixmap = QtGui.QPixmap(str(temporary_png)).copy()
            self._refresh_snap_candidates()
            self.preview.set_drawing(pixmap, self._drawing_document, self._snap_candidates)
            self.preview.set_active_page(page_index)
            if self._dimension_model is not None:
                self.preview.set_selected_ids(self._dimension_model.selected_ids)

        def _update_page_selector(self, page_count: int) -> None:
            current = min(int(self.page_selector.currentData() or 0), max(0, int(page_count) - 1))
            blocker = QtCore.QSignalBlocker(self.page_selector)
            self.page_selector.clear()
            for index in range(max(1, int(page_count))):
                title = ""
                if self._drawing_document is not None and index < len(self._drawing_document.pages):
                    title = f" · {self._drawing_document.pages[index].title}"
                self.page_selector.addItem(f"{index + 1} / {max(1, int(page_count))}{title}", index)
            self.page_selector.setCurrentIndex(current)
            del blocker

        def _refresh_snap_candidates(self) -> None:
            if self._drawing_document is None:
                self._snap_candidates = []
            else:
                self._snap_candidates = build_snap_candidates(
                    self._drawing_document,
                    entity_id=self._entity_id,
                    snap_filter=str(self.snap_filter.currentData() or SnapFilter.ALL.value),
                )
            if hasattr(self, "preview"):
                self.preview.set_candidates(self._snap_candidates)

        def resizeEvent(self, event: Any) -> None:
            super().resizeEvent(event)
            self.preview.update()
else:
    class _Unavailable:
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()
    EditWorkspacePanel = DrawingWorkspacePanel = _Unavailable

__all__ = ["DrawingWorkspacePanel", "EditWorkspacePanel"]
