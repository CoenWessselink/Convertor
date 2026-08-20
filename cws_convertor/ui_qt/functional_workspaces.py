"""Compact project-aware edit and drawing workspaces for the U4 shell."""
from __future__ import annotations

from pathlib import Path
from typing import Any

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

    class EditWorkspacePanel(QtWidgets.QWidget):
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
            profile_value = _value(entity, "normalized_profile", "profile")
            material_value = _value(entity, "normalized_material", "material_grade", "material")
            profile_match = self._profile_database.find(profile_value) if self._profile_database and profile_value else None
            material_matches = []
            if self._material_database and material_value:
                from material_database import normalise_material
                key = normalise_material(material_value)
                material_matches = [item for item in self._material_database.materials if key in item.search_names]
            profile_confidence = float(getattr(entity, "profile_confidence", 0.0) or 0.0)
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
            for row in range(self.features.rowCount()):
                item = self.features.item(row, 9)
                if item is not None:
                    item.setText("OK")
            self.status.setText("Bewerkingen lokaal gevalideerd")

        def _save(self) -> None:
            if self._workspace is None or self._entity is None:
                return
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
                for name, value in (("profile", profile_value), ("material", material_value), ("description", self.description.text().strip())):
                    if hasattr(self._entity, name):
                        setattr(self._entity, name, value)
                for name, value in (("normalized_profile", profile_value), ("normalized_material", material_value), ("profile_confidence", 1.0 if profile_match else 0.65), ("material_confidence", 1.0 if material_value else 0.0)):
                    if hasattr(self._entity, name):
                        setattr(self._entity, name, value)
                recompute = getattr(self._entity, "recompute_hashes", None)
                if callable(recompute):
                    recompute()
                self._workspace.session.save(user="qt-gui", revision_message=f"Onderdeel {self.part_id.text()} bijgewerkt")
                self.status.setText("Wijzigingen opgeslagen in het centrale Project Model")
                self._update_recognition_state(self._entity)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Bewerken", f"{type(exc).__name__}: {exc}")

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
            self._build()
            self.generate_pdf.connect(self.export_pdf)

        def _build(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(12, 9, 12, 9)
            root.setSpacing(7)
            top = QtWidgets.QHBoxLayout()
            self.title = QtWidgets.QLabel("PDF / Tekening")
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
            self.pdf_button = QtWidgets.QPushButton("PDF genereren")
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
                button.setChecked(key in {"front", "top", "side", "iso"})
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
            views.addSpacing(18)
            views.addWidget(self.dimensions_button)
            views.addWidget(self.dimension_mode)
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

        def set_context(self, context: object, selection: object | None = None) -> None:
            workspace, entity, entity_id = _workspace_entity(context, selection)
            if workspace is None and type(context).__name__ == "UnifiedUiContextSnapshot":
                return
            previous_entity_id = self._entity_id
            self._workspace, self._entity_id = workspace, entity_id
            name = _value(entity, "part_position", "mark", "name", default=self._entity_id)
            self.title.setText(f"PDF / Tekening - {name}" if name else "PDF / Tekening")
            self.status.setText("Gereed voor live tekenvoorbeeld" if self._workspace is not None else "Geen project geopend")
            if self._workspace is not None and self._entity_id and self._entity_id != previous_entity_id:
                QtCore.QTimer.singleShot(0, self.refresh_preview)

        def show_project_selection(self, selection: object) -> None:
            self.set_context(self._workspace, selection)

        def _output_folder(self) -> Path:
            target = Path.home() / "Documents" / "CWS Convertor" / "Tekeningen"
            target.mkdir(parents=True, exist_ok=True)
            return target

        def _generate(self, *, make_png: bool, make_pdf: bool):
            if self._workspace is None:
                QtWidgets.QMessageBox.information(self, "PDF / Tekening", "Open eerst een project en selecteer een onderdeel.")
                return None
            if not self._entity_id or self._entity_id not in self._workspace.project.parts:
                QtWidgets.QMessageBox.information(
                    self,
                    "PDF / Tekening",
                    "Selecteer eerst één maakdeel in Viewer, modelstructuur of BOM. De tekening wordt uitsluitend van die centrale selectie gemaakt.",
                )
                return None
            try:
                from cws_convertor.ui_qt.engineering_drawing import EngineeringDrawingGenerator
                selected_views = tuple(key for key, button in self.view_buttons.items() if button.isChecked())
                result = EngineeringDrawingGenerator(self._workspace).generate(
                    self._output_folder(), entity_id=self._entity_id,
                    sheet_format=self.format.currentText(), scale_label=self.scale.currentText(),
                    unit=self.unit.currentText(), make_png=make_png, make_pdf=make_pdf,
                    views=selected_views, dimensions=self.dimensions_button.isChecked(),
                    title_block=self.title_block_button.isChecked(),
                )
                if result.png_path:
                    self._last_png = Path(result.png_path)
                    self._show_pixmap()
                warning = f" | {result.warnings[0]}" if result.warnings else ""
                self.status.setText(f"Gegenereerd op schaal {result.scale_label}: {result.pdf_path or result.png_path}{warning}")
                return result
            except Exception as exc:
                self.status.setText("Tekening genereren mislukt")
                QtWidgets.QMessageBox.critical(self, "PDF / Tekening", f"{type(exc).__name__}: {exc}")
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
