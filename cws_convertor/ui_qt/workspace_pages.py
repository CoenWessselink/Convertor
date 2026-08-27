"""Context-aware Qt workspaces for the integrated CWS Convertor shell.

These widgets only route stable project IDs to existing services. They do not
own project data or introduce an alternative conversion/geometry model.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    def _entity_summary(workspace: Any | None, selection: Any | None) -> tuple[str, str]:
        if workspace is None:
            return "Geen project geopend", "Open een CWS-project in Inlezen."
        entity_id = str(getattr(selection, "primary_entity_id", "") or "")
        entity_ids = tuple(getattr(selection, "entity_ids", ()) or ())
        if not entity_id:
            return workspace.project.project_name, "Geen object geselecteerd"
        project = workspace.project
        entity = None
        entity_type = "Object"
        for label, collection in (
            ("Onderdeel", project.parts),
            ("Samenstelling", project.assemblies),
            ("Inkoopdeel", project.purchased_items),
            ("Bevestiger", project.fasteners),
            ("Las", project.welds),
        ):
            if entity_id in collection:
                entity = collection[entity_id]
                entity_type = label
                break
        name = str(
            getattr(entity, "part_position", "")
            or getattr(entity, "mark", "")
            or getattr(entity, "name", "")
            or entity_id
        )
        detail = f"{entity_type} | {entity_id}"
        if len(entity_ids) > 1:
            detail += f" | {len(entity_ids)} objecten geselecteerd"
        return name, detail


    class ImportPanel(QtWidgets.QWidget):
        """File intake surface that routes existing formats to proven handlers."""

        project_requested = QtCore.Signal(str)
        models_requested = QtCore.Signal(tuple)
        pdf_requested = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self._paths: list[Path] = []
            self._build()

        def _build(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(7)
            header = QtWidgets.QHBoxLayout()
            title = QtWidgets.QLabel("Inlezen")
            title.setObjectName("workspaceTitle")
            header.addWidget(title)
            header.addStretch(1)
            add_files = QtWidgets.QPushButton("Bestanden toevoegen")
            add_files.clicked.connect(self._choose_files)
            add_folder = QtWidgets.QPushButton("Map toevoegen")
            add_folder.clicked.connect(self._choose_folder)
            clear = QtWidgets.QToolButton()
            clear.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogResetButton))
            clear.setToolTip("Lijst leegmaken")
            clear.clicked.connect(self.clear)
            header.addWidget(add_files)
            header.addWidget(add_folder)
            header.addWidget(clear)
            root.addLayout(header)

            self.files = QtWidgets.QTreeWidget()
            self.files.setHeaderLabels(["Bestand", "Type", "Grootte", "Status"])
            self.files.setRootIsDecorated(False)
            self.files.setAlternatingRowColors(True)
            self.files.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
            self.files.header().setStretchLastSection(False)
            self.files.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
            for column, width in ((1, 100), (2, 110), (3, 160)):
                self.files.header().resizeSection(column, width)
            root.addWidget(self.files, 1)

            settings = QtWidgets.QGroupBox("Projectinstellingen")
            form = QtWidgets.QGridLayout(settings)
            self.project_name = QtWidgets.QLineEdit()
            self.project_number = QtWidgets.QLineEdit()
            self.units = QtWidgets.QComboBox()
            self.units.addItem("Millimeter", "mm")
            self.material = QtWidgets.QComboBox()
            self.material.setEditable(True)
            self.material.addItems(["S355JR", "S235JR", "S355J2"])
            self.tolerance = QtWidgets.QDoubleSpinBox()
            self.tolerance.setRange(0.01, 25.0)
            self.tolerance.setDecimals(2)
            self.tolerance.setValue(2.0)
            self.tolerance.setSuffix(" mm")
            form.addWidget(QtWidgets.QLabel("Projectnaam"), 0, 0)
            form.addWidget(self.project_name, 0, 1)
            form.addWidget(QtWidgets.QLabel("Projectnummer"), 0, 2)
            form.addWidget(self.project_number, 0, 3)
            form.addWidget(QtWidgets.QLabel("Eenheden"), 1, 0)
            form.addWidget(self.units, 1, 1)
            form.addWidget(QtWidgets.QLabel("Materiaal"), 1, 2)
            form.addWidget(self.material, 1, 3)
            form.addWidget(QtWidgets.QLabel("Tolerantie"), 1, 4)
            form.addWidget(self.tolerance, 1, 5)
            root.addWidget(settings)

            footer = QtWidgets.QHBoxLayout()
            self.status = QtWidgets.QLabel("Geen bestanden geladen")
            self.open_button = QtWidgets.QPushButton("Project openen / Naar Viewer")
            self.open_button.setObjectName("primaryButton")
            self.open_button.clicked.connect(self._route_selected)
            footer.addWidget(self.status)
            footer.addStretch(1)
            footer.addWidget(self.open_button)
            root.addLayout(footer)

        def add_paths(self, values: Iterable[str | Path]) -> None:
            allowed = {".cwscproj", ".nc", ".nc1", ".step", ".stp", ".ifc", ".pdf", ".dxf"}
            for value in values:
                path = Path(value).expanduser().resolve()
                if not path.is_file() or path.suffix.lower() not in allowed or path in self._paths:
                    continue
                self._paths.append(path)
                item = QtWidgets.QTreeWidgetItem(self.files)
                item.setText(0, path.name)
                item.setText(1, path.suffix.lower().lstrip(".").upper())
                item.setText(2, f"{path.stat().st_size / (1024 * 1024):.2f} MB")
                item.setText(3, "Gereed")
                item.setToolTip(0, str(path))
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(path))
            self.status.setText(f"{len(self._paths)} bestand(en) geladen")

        def clear(self) -> None:
            self._paths.clear()
            self.files.clear()
            self.status.setText("Geen bestanden geladen")

        def _choose_files(self) -> None:
            names, _ = QtWidgets.QFileDialog.getOpenFileNames(
                self,
                "CWS-bestanden kiezen",
                "",
                "CWS-bestanden (*.cwscproj *.ifc *.step *.stp *.nc *.nc1 *.pdf *.dxf)",
            )
            self.add_paths(names)

        def _choose_folder(self) -> None:
            name = QtWidgets.QFileDialog.getExistingDirectory(self, "Map kiezen")
            if not name:
                return
            allowed = {".cwscproj", ".nc", ".nc1", ".step", ".stp", ".ifc", ".pdf", ".dxf"}
            self.add_paths(path for path in Path(name).iterdir() if path.suffix.lower() in allowed)

        def _route_selected(self) -> None:
            selected = [Path(str(item.data(0, QtCore.Qt.ItemDataRole.UserRole))) for item in self.files.selectedItems()]
            values = selected or list(self._paths)
            project = next((path for path in values if path.suffix.lower() == ".cwscproj"), None)
            models = tuple(path for path in values if path.suffix.lower() in {".nc", ".nc1", ".step", ".stp", ".ifc"})
            pdf = next((path for path in values if path.suffix.lower() == ".pdf"), None)
            if project is not None:
                self.project_requested.emit(str(project))
                return
            if models:
                self.models_requested.emit(tuple(str(path) for path in models))
                return
            if pdf is not None:
                self.pdf_requested.emit(str(pdf))
                return
            QtWidgets.QMessageBox.information(self, "Inlezen", "Selecteer eerst een ondersteund bestand.")


    class ContextActionPage(QtWidgets.QWidget):
        """Compact workspace that keeps the active canonical selection visible."""

        action_requested = QtCore.Signal(str)

        def __init__(
            self,
            title: str,
            *,
            actions: tuple[tuple[str, str], ...],
            empty_text: str = "Selecteer een object in Viewer / Project.",
            parent: Any | None = None,
        ) -> None:
            super().__init__(parent)
            self._workspace = None
            self._selection = None
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(8)
            label = QtWidgets.QLabel(title)
            label.setObjectName("workspaceTitle")
            root.addWidget(label)
            context = QtWidgets.QFrame()
            context.setObjectName("selectionContext")
            context_layout = QtWidgets.QHBoxLayout(context)
            self.selection_name = QtWidgets.QLabel("Geen selectie")
            self.selection_name.setObjectName("selectionName")
            self.selection_detail = QtWidgets.QLabel(empty_text)
            self.selection_detail.setObjectName("mutedText")
            context_layout.addWidget(self.selection_name)
            context_layout.addWidget(self.selection_detail, 1)
            root.addWidget(context)

            self.properties = QtWidgets.QTreeWidget()
            self.properties.setHeaderLabels(["Eigenschap", "Waarde", "Herkomst"])
            self.properties.setRootIsDecorated(False)
            self.properties.setAlternatingRowColors(True)
            self.properties.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
            self.properties.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
            root.addWidget(self.properties, 1)

            buttons = QtWidgets.QHBoxLayout()
            for text, key in actions:
                button = QtWidgets.QPushButton(text)
                if key not in {"viewer"}:
                    button.setObjectName("primaryButton")
                button.clicked.connect(lambda _checked=False, value=key: self.action_requested.emit(value))
                buttons.addWidget(button)
            buttons.addStretch(1)
            root.addLayout(buttons)

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            self._workspace = workspace
            self._selection = selection
            name, detail = _entity_summary(workspace, selection)
            self.selection_name.setText(name)
            self.selection_detail.setText(detail)
            self.properties.clear()
            if workspace is None or not getattr(selection, "primary_entity_id", None):
                return
            for record in workspace.interaction.properties_for_primary():
                item = QtWidgets.QTreeWidgetItem(self.properties)
                item.setText(0, str(record.label))
                item.setText(1, str(record.value))
                item.setText(2, str(record.provenance))


    class ProfilesPanel(QtWidgets.QWidget):
        """Searchable read surface over the existing local profile database."""

        action_requested = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            from profile_database import ProfileDatabase

            self.database = ProfileDatabase()
            self._workspace = None
            self._selection = None
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(10, 10, 10, 10)
            header = QtWidgets.QHBoxLayout()
            title = QtWidgets.QLabel("Profielen")
            title.setObjectName("workspaceTitle")
            self.context = QtWidgets.QLabel("Geen object geselecteerd")
            self.context.setObjectName("mutedText")
            self.search = QtWidgets.QLineEdit()
            self.search.setPlaceholderText("Zoek profiel")
            self.search.setClearButtonEnabled(True)
            self.search.textChanged.connect(self.refresh)
            header.addWidget(title)
            header.addWidget(self.context, 1)
            header.addWidget(self.search)
            root.addLayout(header)
            self.table = QtWidgets.QTreeWidget()
            self.table.setHeaderLabels(["Profiel", "Type", "Familie", "h", "b", "kg/m", "Norm", "Bron"])
            self.table.setRootIsDecorated(False)
            self.table.setAlternatingRowColors(True)
            root.addWidget(self.table, 1)
            footer = QtWidgets.QHBoxLayout()
            self.status = QtWidgets.QLabel()
            manage = QtWidgets.QPushButton("Profielbeheer openen")
            manage.clicked.connect(lambda: self.action_requested.emit("legacy_profiles"))
            footer.addWidget(self.status)
            footer.addStretch(1)
            footer.addWidget(manage)
            root.addLayout(footer)
            self.refresh()

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            self._workspace = workspace
            self._selection = selection
            name, detail = _entity_summary(workspace, selection)
            self.context.setText(f"{name} | {detail}")
            if workspace is not None and getattr(selection, "primary_entity_id", None):
                entity = workspace.project.parts.get(str(selection.primary_entity_id))
                profile = str(getattr(entity, "normalized_profile", "") or getattr(entity, "profile", "") or "")
                if profile:
                    self.search.setText(profile)

        def refresh(self) -> None:
            rows = self.database.filtered(text=self.search.text())[:500]
            self.table.clear()
            for profile in rows:
                item = QtWidgets.QTreeWidgetItem(self.table)
                values = (
                    profile.designation, profile.profile_type, profile.family,
                    f"{profile.dim1:g}", f"{profile.dim2:g}", f"{profile.mass_kg_m:g}",
                    profile.standard, profile.source,
                )
                for column, value in enumerate(values):
                    item.setText(column, str(value))
            self.status.setText(f"{len(rows)} van {len(self.database.profiles)} profielen")


    class OptimizationPanel(QtWidgets.QWidget):
        """Honest capability status for the not-yet-implemented optimizer."""

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)
            title = QtWidgets.QLabel("Optimalisatie")
            title.setObjectName("workspaceTitle")
            root.addWidget(title)
            state = QtWidgets.QFrame()
            state.setObjectName("warningPanel")
            layout = QtWidgets.QVBoxLayout(state)
            heading = QtWidgets.QLabel("UI integration gap")
            heading.setObjectName("panelHeading")
            detail = QtWidgets.QLabel(
                "De huidige repository bevat nog geen gevalideerde solver voor handelslengtes, "
                "plaatnesting of machineplanning. Er wordt daarom geen optimalisatieactie aangeboden."
            )
            detail.setWordWrap(True)
            layout.addWidget(heading)
            layout.addWidget(detail)
            root.addWidget(state)
            root.addStretch(1)


    class ExportPanel(QtWidgets.QWidget):
        """Project production export through the existing strict session gate."""

        action_requested = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self._workspace = None
            self._selection = None
            self._thread = None
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(10, 10, 10, 10)
            title = QtWidgets.QLabel("Exporteren")
            title.setObjectName("workspaceTitle")
            root.addWidget(title)
            self.context = QtWidgets.QLabel("Geen project geopend")
            self.context.setObjectName("selectionContext")
            root.addWidget(self.context)
            contract = QtWidgets.QLabel(
                "Productievrijgave vereist per onderdeel een vrijgegeven Workbench, een actuele "
                "canonical rebuild en een verse geslaagde NC1/STEP/IFC/Trusted-PDF-matrix."
            )
            contract.setWordWrap(True)
            contract.setObjectName("mutedText")
            root.addWidget(contract)
            formats = QtWidgets.QGroupBox("Bestanden")
            format_layout = QtWidgets.QGridLayout(formats)
            self.format_checks: dict[str, Any] = {}
            for index, (key, label) in enumerate((
                ("nc1", "DSTV / NC1"), ("step", "STEP"), ("ifc", "IFC"),
                ("production_pdf", "Trusted productie-PDF"), ("dxf", "Plaat-DXF"),
                ("json", "Part-JSON"), ("csv", "Part-CSV"),
                ("label_pdf", "QR-label PDF"), ("preview_png", "Part-preview PNG"),
                ("review_pdf", "Losse review-PDF"), ("review_png", "Losse review-PNG"),
            )):
                check = QtWidgets.QCheckBox(label)
                check.setChecked(key in {"review_pdf", "review_png"})
                self.format_checks[key] = check
                format_layout.addWidget(check, index // 3, index % 3)
            preset_row = QtWidgets.QHBoxLayout()
            self.full_release = QtWidgets.QPushButton("Volledig productiepakket")
            self.review_only = QtWidgets.QPushButton("Alleen review")
            self.full_release.clicked.connect(self._select_full_release)
            self.review_only.clicked.connect(self._select_review_only)
            preset_row.addStretch(1)
            preset_row.addWidget(self.full_release)
            preset_row.addWidget(self.review_only)
            format_layout.addLayout(preset_row, 4, 0, 1, 3)
            root.addWidget(formats)
            row = QtWidgets.QHBoxLayout()
            self.output = QtWidgets.QLineEdit(str(Path.home() / "CWS_Convertor_Exports"))
            choose = QtWidgets.QToolButton()
            choose.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirOpenIcon))
            choose.setToolTip("Uitvoermap kiezen")
            choose.clicked.connect(self._choose_output)
            self.selection_only = QtWidgets.QCheckBox("Alleen huidige selectie")
            row.addWidget(QtWidgets.QLabel("Uitvoermap"))
            row.addWidget(self.output, 1)
            row.addWidget(choose)
            row.addWidget(self.selection_only)
            root.addLayout(row)
            package_options = QtWidgets.QHBoxLayout()
            self.create_zip = QtWidgets.QCheckBox("Deterministische ZIP maken")
            self.create_zip.setChecked(True)
            self.include_blocked_review = QtWidgets.QCheckBox("Reviewbestanden opnemen bij blokkade")
            self.include_blocked_review.setChecked(True)
            package_options.addWidget(self.create_zip)
            package_options.addWidget(self.include_blocked_review)
            package_options.addStretch(1)
            root.addLayout(package_options)
            self.log = QtWidgets.QPlainTextEdit()
            self.log.setReadOnly(True)
            root.addWidget(self.log, 1)
            footer = QtWidgets.QHBoxLayout()
            self.status = QtWidgets.QLabel("Gereed")
            self.run = QtWidgets.QPushButton("Export starten")
            self.run.setObjectName("primaryButton")
            self.run.clicked.connect(self._run)
            footer.addWidget(self.status)
            footer.addStretch(1)
            footer.addWidget(self.run)
            root.addLayout(footer)

        def set_context(self, workspace: Any | None, selection: Any | None) -> None:
            self._workspace = workspace
            self._selection = selection
            name, detail = _entity_summary(workspace, selection)
            self.context.setText(f"{name} | {detail}")
            self.run.setEnabled(workspace is not None and self._thread is None)

        def _choose_output(self) -> None:
            name = QtWidgets.QFileDialog.getExistingDirectory(self, "Uitvoermap", self.output.text())
            if name:
                self.output.setText(name)

        def _select_full_release(self) -> None:
            release_formats = {
                "nc1", "step", "ifc", "production_pdf", "dxf", "json", "csv",
                "label_pdf", "preview_png",
            }
            for key, check in self.format_checks.items():
                check.setChecked(key in release_formats)

        def _select_review_only(self) -> None:
            for key, check in self.format_checks.items():
                check.setChecked(key in {"review_pdf", "review_png"})

        def _run(self) -> None:
            if self._workspace is None:
                return
            formats = [key for key, check in self.format_checks.items() if check.isChecked()]
            if not formats:
                QtWidgets.QMessageBox.information(self, "Exporteren", "Selecteer minstens een formaat.")
                return
            selected_ids = tuple(getattr(self._selection, "entity_ids", ()) or ()) if self.selection_only.isChecked() else ()
            part_ids = tuple(value for value in selected_ids if value in self._workspace.project.parts)
            assembly_marks = tuple(
                self._workspace.project.assemblies[value].assembly_mark
                for value in selected_ids
                if value in self._workspace.project.assemblies
                and self._workspace.project.assemblies[value].assembly_mark
            )
            if self.selection_only.isChecked() and not part_ids and not assembly_marks:
                QtWidgets.QMessageBox.information(
                    self, "Exporteren", "De huidige selectie bevat geen maakdeel of assemblymerk."
                )
                return
            target = Path(self.output.text()).expanduser()
            target.mkdir(parents=True, exist_ok=True)
            review_formats = {"review_pdf", "review_png"}
            production_formats = [value for value in formats if value not in review_formats]
            messages = []
            review_output = None
            try:
                if review_formats.intersection(formats):
                    from cws_convertor.ui_qt.engineering_drawing import EngineeringDrawingGenerator
                    primary = str(getattr(self._selection, "primary_entity_id", "") or "")
                    review_output = EngineeringDrawingGenerator(self._workspace).generate(
                        target / "Review",
                        entity_id=primary,
                        make_png="review_png" in formats,
                        make_pdf="review_pdf" in formats,
                    )
                    messages.append(f"Reviewtekening: {review_output.pdf_path or review_output.png_path}")
                if production_formats:
                    manifest, package_root, zip_path = self._workspace.session.export_production_package(
                        target,
                        formats=production_formats,
                        part_ids=part_ids,
                        assembly_marks=assembly_marks,
                        create_zip=self.create_zip.isChecked(),
                        include_blocked_review_files=self.include_blocked_review.isChecked(),
                        user="qt-gui",
                    )
                    self._workspace.session.save(user="qt-gui", revision_message="Productiepakket geexporteerd")
                    from cws_convertor.production_export import verify_export_directory, verify_export_zip

                    directory_verification = verify_export_directory(package_root)
                    zip_verification = verify_export_zip(zip_path) if zip_path is not None else None
                    messages.extend((
                        f"Productie: {manifest.summary}",
                        f"Scope parts: {', '.join(part_ids) if part_ids else 'project'}",
                        f"Scope merken: {', '.join(assembly_marks) if assembly_marks else 'project'}",
                        f"Map: {package_root}",
                        f"Mapverificatie: geldig ({directory_verification['checked_files']} bestanden)",
                        f"ZIP: {zip_path or 'niet aangevraagd'}",
                        f"ZIP-verificatie: {'geldig' if zip_verification else 'niet van toepassing'}",
                        f"Manifest: {manifest.manifest_sha256}",
                    ))
                self.log.setPlainText("\n".join(messages))
                if not production_formats:
                    self.status.setText("Reviewuitvoer gereed; geen productievrijgave")
                elif manifest.summary.get("production_ready"):
                    self.status.setText("Productiepakket geverifieerd en gereed")
                else:
                    self.status.setText("Productie geblokkeerd; geverifieerd reviewpakket gemaakt")
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Productievrijgave geblokkeerd",
                        "Het pakket is technisch geverifieerd, maar niet productie-ready. "
                        "Bekijk manifest en blokkades in het exportlog.",
                    )
            except Exception as exc:
                prefix = "\n".join(messages)
                self.status.setText("Review gereed; productie geblokkeerd" if review_output else "Export geblokkeerd of mislukt")
                self.log.setPlainText((prefix + "\n" if prefix else "") + f"Productieblokkade: {type(exc).__name__}: {exc}")
                if review_output is None:
                    QtWidgets.QMessageBox.critical(self, "Exporteren", f"{type(exc).__name__}: {exc}")
                else:
                    QtWidgets.QMessageBox.information(
                        self,
                        "Reviewuitvoer",
                        "De reviewtekening is gemaakt. Productie-export blijft veilig geblokkeerd totdat het onderdeel een maakdeel en vrijgegeven is.",
                    )


else:
    class _Unavailable:
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    ImportPanel = ContextActionPage = ProfilesPanel = OptimizationPanel = ExportPanel = _Unavailable


__all__ = [
    "ContextActionPage",
    "ExportPanel",
    "ImportPanel",
    "OptimizationPanel",
    "ProfilesPanel",
]

if qt_available():
    _LegacyImportPanel = ImportPanel

    class IntakeDashboard(_LegacyImportPanel):
        """Project intake dashboard matching the product reference."""

        FORMAT_FILTERS = {
            "IFC": "IFC modellen (*.ifc)",
            "STEP": "STEP modellen (*.step *.stp)",
            "NC / NC1": "DSTV bestanden (*.nc *.nc1)",
            "PDF": "Technische PDF (*.pdf)",
            "DXF": "Technische DXF (*.dxf)",
            "Pakket (ZIP)": "CWS pakketten (*.zip *.cwscproj)",
        }

        def _build(self) -> None:
            self.setAcceptDrops(True)
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(22, 18, 22, 18)
            root.setSpacing(16)
            actions = QtWidgets.QHBoxLayout()
            new_project = QtWidgets.QPushButton("＋  Nieuw project")
            new_project.setObjectName("primaryOutlineButton")
            new_project.clicked.connect(self._choose_files)
            open_project = QtWidgets.QPushButton("Open projectbestand")
            open_project.clicked.connect(self._open_project)
            import_files = QtWidgets.QPushButton("Importeren")
            import_files.clicked.connect(self._choose_files)
            actions.addWidget(new_project)
            actions.addWidget(open_project)
            actions.addWidget(import_files)
            actions.addStretch(1)
            root.addLayout(actions)
            title = QtWidgets.QLabel("Importeren vanuit")
            title.setObjectName("sectionTitle")
            root.addWidget(title)
            cards = QtWidgets.QHBoxLayout()
            cards.setSpacing(12)
            for card_title, subtitle in (("IFC", "IFC 2x3 / IFC4"), ("STEP", ".step / .stp"), ("NC / NC1", "DSTV productie"), ("PDF", "Herkennen / converteren"), ("Pakket (ZIP)", "CWS-projectpakket")):
                button = QtWidgets.QPushButton(f"{card_title}\n{subtitle}")
                button.setObjectName("formatCard")
                button.setMinimumHeight(72)
                button.clicked.connect(
                    lambda _checked=False, title=card_title: self._choose_files(
                        format_filter=self.FORMAT_FILTERS[title]
                    )
                )
                cards.addWidget(button, 1)
            root.addLayout(cards)
            body = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            recent_box = QtWidgets.QGroupBox("Recente projecten")
            recent_layout = QtWidgets.QVBoxLayout(recent_box)
            self.recent = QtWidgets.QListWidget()
            self.recent.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
            self.recent.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
            self.recent.setMovement(QtWidgets.QListView.Movement.Static)
            self.recent.setIconSize(QtCore.QSize(210, 112))
            self.recent.setGridSize(QtCore.QSize(235, 162))
            self.recent.setWordWrap(True)
            self.recent.itemDoubleClicked.connect(self._open_recent)
            recent_layout.addWidget(self.recent)
            body.addWidget(recent_box)
            queue_box = QtWidgets.QGroupBox("Nieuwe projectimport")
            queue_layout = QtWidgets.QVBoxLayout(queue_box)
            self.files = QtWidgets.QTreeWidget()
            self.files.setHeaderLabels(["Bestand", "Type", "Grootte", "Status"])
            self.files.setRootIsDecorated(False)
            self.files.setAlternatingRowColors(True)
            self.files.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
            queue_layout.addWidget(self.files, 1)
            queue_actions = QtWidgets.QHBoxLayout()
            clear = QtWidgets.QPushButton("Lijst wissen")
            clear.clicked.connect(self.clear)
            self.create = QtWidgets.QPushButton("Project aanmaken en openen")
            self.create.setObjectName("primaryButton")
            self.create.setEnabled(False)
            self.create.clicked.connect(self._emit_models)
            queue_actions.addWidget(clear)
            queue_actions.addStretch(1)
            queue_actions.addWidget(self.create)
            queue_layout.addLayout(queue_actions)
            body.addWidget(queue_box)
            body.setStretchFactor(0, 2)
            body.setStretchFactor(1, 3)
            root.addWidget(body, 1)
            self.progress = QtWidgets.QProgressBar()
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.status = QtWidgets.QLabel("Sleep IFC-, STEP-, NC1- of projectbestanden naar dit scherm")
            self.status.setObjectName("mutedText")
            root.addWidget(self.progress)
            root.addWidget(self.status)
            self._load_recent()

        def _load_recent(self) -> None:
            self.recent.clear()
            root = Path.home() / "Documents" / "CWS Convertor Projects"
            stored = QtCore.QSettings("CWS", "CWS Convertor").value("recent_inputs", [], list) or []
            candidates = [Path(value) for value in stored if Path(value).is_file()]
            if root.exists():
                candidates.extend(root.glob("*.cwscproj"))
            paths = sorted(
                {path.resolve() for path in candidates if path.is_file()},
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )[:12]
            if not paths:
                item = QtWidgets.QListWidgetItem("Nog geen recente projecten\nImporteer IFC, STEP, NC1 of PDF")
                item.setIcon(self._preview_icon("project", "CWS"))
                item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
                self.recent.addItem(item)
                return
            for path in paths:
                kind = "project" if path.suffix.lower() in {".ifc", ".cwscproj", ".zip"} else "part"
                item = QtWidgets.QListWidgetItem(f"{path.stem}\n{path.suffix.upper().lstrip('.')}")
                item.setIcon(self._preview_icon(kind, path.stem))
                item.setToolTip(str(path))
                item.setData(QtCore.Qt.ItemDataRole.UserRole, str(path))
                self.recent.addItem(item)

        def _preview_icon(self, kind: str, seed: str) -> QtGui.QIcon:
            pixmap = QtGui.QPixmap(420, 224)
            pixmap.fill(QtGui.QColor("#f7faff"))
            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            painter.setPen(QtGui.QPen(QtGui.QColor("#a9bbcf"), 3))
            painter.setBrush(QtGui.QColor("#e9f1fa"))
            if kind == "project":
                for offset in (0, 72, 144, 216, 288):
                    x = 42 + offset
                    painter.drawLine(x, 176, x, 62)
                    painter.drawLine(x, 62, x + 42, 34)
                    painter.drawLine(x + 42, 34, x + 72, 62)
                    painter.drawLine(x, 102, x + 72, 102)
                    painter.drawLine(x, 142, x + 72, 142)
                painter.setPen(QtGui.QPen(QtGui.QColor("#1f6fd2"), 7))
                painter.drawLine(112, 142, 328, 102)
            else:
                painter.setBrush(QtGui.QColor("#d8e5f3"))
                painter.setPen(QtGui.QPen(QtGui.QColor("#65809c"), 3))
                body = QtCore.QRectF(58, 84, 304, 58)
                painter.drawRect(body)
                painter.drawRect(QtCore.QRectF(48, 64, 18, 98))
                painter.drawRect(QtCore.QRectF(354, 64, 18, 98))
                painter.setPen(QtGui.QPen(QtGui.QColor("#1f6fd2"), 4))
                painter.drawLine(66, 113, 354, 113)
            painter.setPen(QtGui.QColor("#52677c"))
            painter.setFont(QtGui.QFont("Segoe UI", 10))
            painter.drawText(12, 210, seed[:48])
            painter.end()
            return QtGui.QIcon(pixmap)

        def _remember_recent(self, path: Path) -> None:
            settings = QtCore.QSettings("CWS", "CWS Convertor")
            values = [str(path), *(settings.value("recent_inputs", [], list) or [])]
            settings.setValue("recent_inputs", list(dict.fromkeys(values))[:24])

        def _open_recent(self, item: QtWidgets.QListWidgetItem) -> None:
            value = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "")
            if not value:
                return
            path = Path(value)
            if path.suffix.lower() == ".cwscproj":
                self.project_requested.emit(str(path))
            else:
                self.add_paths((path,))

        @staticmethod
        def _inspect_format(path: Path) -> tuple[str, str, bool]:
            suffix = path.suffix.lower()
            try:
                with path.open("rb") as stream:
                    head = stream.read(8192)
            except OSError as exc:
                return suffix.upper().lstrip("."), f"Niet leesbaar: {exc}", False
            upper = head.upper()
            if suffix == ".pdf":
                return "PDF", "PDF-document herkend", head.startswith(b"%PDF-")
            if suffix == ".dxf":
                text = head.decode("latin-1", errors="ignore").upper()
                valid = head.startswith(b"AutoCAD Binary DXF") or (
                    "SECTION" in text and ("HEADER" in text or "ENTITIES" in text)
                )
                return "DXF", "CAD-uitwisselingstekening", valid
            if suffix == ".ifc":
                valid = b"ISO-10303-21" in upper and b"IFC" in upper
                edition = "IFC4" if b"IFC4" in upper else "IFC2x3 / IFC"
                return "IFC", edition, valid
            if suffix in {".step", ".stp"}:
                valid = b"ISO-10303-21" in upper and b"FILE_SCHEMA" in upper
                return "STEP", "ISO 10303 STEP", valid
            if suffix in {".nc", ".nc1"}:
                text = head.decode("latin-1", errors="ignore").lstrip()
                return "NC1", "DSTV / NC productie", bool(text and ("ST" in text[:80] or "BO" in text))
            if suffix == ".zip":
                return "ZIP", "CWS projectpakket", head.startswith(b"PK")
            if suffix == ".cwscproj":
                return "CWS", "CWS Project Model", True
            return suffix.upper().lstrip("."), "Onbekend formaat", False

        def add_paths(self, values: Iterable[str | Path]) -> None:
            allowed = {".ifc", ".step", ".stp", ".nc", ".nc1", ".pdf", ".dxf", ".zip", ".cwscproj"}
            for value in values:
                path = Path(value).expanduser().resolve()
                if not path.is_file() or path.suffix.lower() not in allowed:
                    continue
                if path.suffix.lower() == ".cwscproj":
                    self._remember_recent(path)
                    self.project_requested.emit(str(path))
                    continue
                if path.suffix.lower() == ".pdf":
                    kind, detail, valid = self._inspect_format(path)
                    self._remember_recent(path)
                    self.status.setText(f"{path.name}: {detail}" if valid else f"{path.name}: ongeldige {kind}-inhoud")
                    self.pdf_requested.emit(str(path))
                    continue
                if path not in self._paths:
                    self._paths.append(path)
                    kind, detail, valid = self._inspect_format(path)
                    item = QtWidgets.QTreeWidgetItem([path.name, kind, f"{path.stat().st_size / 1_048_576:.2f} MB", detail if valid else "Bestandsinhoud wijkt af van extensie"])
                    item.setToolTip(0, str(path))
                    if not valid:
                        item.setForeground(3, QtGui.QColor("#b34b00"))
                    self.files.addTopLevelItem(item)
                    self._remember_recent(path)
            self.create.setEnabled(bool(self._paths))
            self.status.setText(f"{len(self._paths)} bestand(en) gereed voor projectimport")
            self.progress.setValue(8 if self._paths else 0)

        def clear(self) -> None:
            self._paths.clear()
            self.files.clear()
            self.create.setEnabled(False)
            self.progress.setValue(0)
            self.status.setText("Sleep IFC-, STEP-, NC1-, PDF-, DXF- of projectbestanden naar dit scherm")

        def _choose_files(self, _checked: bool = False, *, format_filter: str = "") -> None:
            file_filter = format_filter or "CWS bestanden (*.cwscproj *.ifc *.step *.stp *.nc *.nc1 *.pdf *.dxf *.zip)"
            names, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Bestanden importeren", "", file_filter)
            self.add_paths(names)

        def _open_project(self) -> None:
            name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Project openen", "", "CWS Project (*.cwscproj)")
            if name:
                self.project_requested.emit(name)

        def _emit_models(self) -> None:
            if self._paths:
                self.progress.setValue(12)
                self.status.setText("Projectwizard wordt geopend...")
                self.models_requested.emit(tuple(str(path) for path in self._paths))

        def dragEnterEvent(self, event: Any) -> None:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()

        def dropEvent(self, event: Any) -> None:
            self.add_paths([url.toLocalFile() for url in event.mimeData().urls()])
            event.acceptProposedAction()

    ImportPanel = IntakeDashboard
