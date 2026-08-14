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
            allowed = {".cwscproj", ".nc", ".nc1", ".step", ".stp", ".ifc", ".pdf"}
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
                "CWS-bestanden (*.cwscproj *.ifc *.step *.stp *.nc *.nc1 *.pdf)",
            )
            self.add_paths(names)

        def _choose_folder(self) -> None:
            name = QtWidgets.QFileDialog.getExistingDirectory(self, "Map kiezen")
            if not name:
                return
            allowed = {".cwscproj", ".nc", ".nc1", ".step", ".stp", ".ifc", ".pdf"}
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
            formats = QtWidgets.QGroupBox("Bestanden")
            format_layout = QtWidgets.QGridLayout(formats)
            self.format_checks: dict[str, Any] = {}
            for index, (key, label) in enumerate((
                ("nc1", "DSTV / NC1"), ("step", "STEP"), ("ifc", "IFC"),
                ("production_pdf", "Productie-PDF"), ("review_pdf", "Review-PDF"),
                ("json", "JSON"), ("csv", "CSV"),
            )):
                check = QtWidgets.QCheckBox(label)
                check.setChecked(key in {"nc1", "step", "ifc", "production_pdf", "review_pdf"})
                self.format_checks[key] = check
                format_layout.addWidget(check, index // 3, index % 3)
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

        def _run(self) -> None:
            if self._workspace is None:
                return
            formats = [key for key, check in self.format_checks.items() if check.isChecked()]
            if not formats:
                QtWidgets.QMessageBox.information(self, "Exporteren", "Selecteer minstens een formaat.")
                return
            selected_ids = tuple(getattr(self._selection, "entity_ids", ()) or ()) if self.selection_only.isChecked() else ()
            part_ids = tuple(value for value in selected_ids if value in self._workspace.project.parts)
            target = Path(self.output.text()).expanduser()
            target.mkdir(parents=True, exist_ok=True)
            try:
                manifest, root, zip_path = self._workspace.session.export_production_package(
                    target,
                    formats=formats,
                    part_ids=part_ids,
                    user="qt-gui",
                )
                self._workspace.session.save(user="qt-gui", revision_message="Productiepakket geexporteerd")
                self.log.setPlainText(
                    f"Status: {manifest.summary}\nMap: {root}\nZIP: {zip_path or '-'}\n"
                    f"Manifest: {manifest.manifest_sha256}"
                )
                self.status.setText("Export afgerond")
            except Exception as exc:
                self.status.setText("Export geblokkeerd of mislukt")
                self.log.setPlainText(f"{type(exc).__name__}: {exc}")
                QtWidgets.QMessageBox.critical(self, "Exporteren", f"{type(exc).__name__}: {exc}")


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
