"""Integrated viewer tools: sections, clipping, explode and measurements.

All operations are display/review state over the already-bound viewer
controller.  They never mutate canonical manufacturing geometry and can never
release production output.  On the real VTK viewer, measurements are driven by
actual mesh-surface clicks; headless/test viewers retain deterministic
selection-centre fallback behaviour.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    from cws_viewer.contracts.enums import MeasurementKind
    from cws_viewer.contracts.state import ClippingBox, SectionPlane
    from cws_viewer.math3d import BoundingBox, Vector3
    from cws_viewer.measurements import (
        ExactMeasurementAnchor,
        MeasurementProof,
        MeasurementSettings,
        SnapType,
        distance,
        horizontal_distance,
        point,
        vertical_distance,
    )
    from cws_viewer.measurements.export import export_csv, export_json, export_pdf

    class IntegratedViewerToolsPanel(QtWidgets.QWidget):
        status_changed = QtCore.Signal(str)

        def __init__(self, workspace: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.workspace = workspace
            self.setObjectName("cwsIntegratedViewerTools")
            self._build_ui()
            self._bind_interactive_viewer()
            self.refresh()

        @property
        def controller(self):
            return self.workspace.controller

        @property
        def viewer(self):
            return getattr(self.workspace, "viewer", None)

        def _bind_interactive_viewer(self) -> None:
            viewer = self.viewer
            signal = getattr(viewer, "measurement_completed", None)
            if signal is not None:
                signal.connect(self._interactive_measurement_completed)
            status_signal = getattr(viewer, "measurement_status", None)
            if status_signal is not None:
                status_signal.connect(self.status_changed)

        def _build_ui(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(7, 7, 7, 7)
            root.setSpacing(7)

            safety = QtWidgets.QLabel(
                "Viewer-tools zijn review/display-only. Metingen vermelden hun bewijsniveau; "
                "sections en explode wijzigen geen canonical geometry of manufacturing hash."
            )
            safety.setWordWrap(True)
            safety.setObjectName("warningPill")
            root.addWidget(safety)

            top = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
            root.addWidget(top)

            sections = QtWidgets.QGroupBox("Doorsneden / clipping")
            section_layout = QtWidgets.QGridLayout(sections)
            self.section_x = QtWidgets.QPushButton("Section X")
            self.section_y = QtWidgets.QPushButton("Section Y")
            self.section_z = QtWidgets.QPushButton("Section Z")
            self.clear_sections = QtWidgets.QPushButton("Sections wissen")
            self.clip_box = QtWidgets.QPushButton("Clipping box 80%")
            self.clear_clip = QtWidgets.QPushButton("Clipping wissen")
            for column, button in enumerate((self.section_x, self.section_y, self.section_z)):
                section_layout.addWidget(button, 0, column)
            section_layout.addWidget(self.clear_sections, 1, 0)
            section_layout.addWidget(self.clip_box, 1, 1)
            section_layout.addWidget(self.clear_clip, 1, 2)
            top.addWidget(sections)

            display = QtWidgets.QGroupBox("Explode / historie")
            display_layout = QtWidgets.QGridLayout(display)
            self.explode_distance = QtWidgets.QDoubleSpinBox()
            self.explode_distance.setRange(1.0, 100_000.0)
            self.explode_distance.setValue(250.0)
            self.explode_distance.setSuffix(" mm")
            self.explode_selection = QtWidgets.QPushButton("Explode selectie")
            self.reset_explode = QtWidgets.QPushButton("Explode reset")
            self.undo = QtWidgets.QPushButton("Undo")
            self.redo = QtWidgets.QPushButton("Redo")
            display_layout.addWidget(QtWidgets.QLabel("Afstand"), 0, 0)
            display_layout.addWidget(self.explode_distance, 0, 1)
            display_layout.addWidget(self.explode_selection, 0, 2)
            display_layout.addWidget(self.reset_explode, 1, 0)
            display_layout.addWidget(self.undo, 1, 1)
            display_layout.addWidget(self.redo, 1, 2)
            top.addWidget(display)

            measurements = QtWidgets.QGroupBox("Meten")
            measurement_layout = QtWidgets.QVBoxLayout(measurements)
            controls = QtWidgets.QHBoxLayout()
            self.quick_distance = QtWidgets.QPushButton("Afstand")
            self.quick_horizontal = QtWidgets.QPushButton("Horizontaal")
            self.quick_vertical = QtWidgets.QPushButton("Verticaal")
            self.quick_coordinates = QtWidgets.QPushButton("XYZ")
            for button in (
                self.quick_distance,
                self.quick_horizontal,
                self.quick_vertical,
                self.quick_coordinates,
            ):
                controls.addWidget(button)
            controls.addSpacing(8)
            self.unit = QtWidgets.QComboBox()
            self.unit.addItems(["mm", "cm", "m", "in", "ft"])
            self.precision = QtWidgets.QSpinBox()
            self.precision.setRange(0, 9)
            self.precision.setValue(3)
            self.trailing = QtWidgets.QCheckBox("Nullen")
            controls.addWidget(QtWidgets.QLabel("Eenheid"))
            controls.addWidget(self.unit)
            controls.addWidget(QtWidgets.QLabel("Precisie"))
            controls.addWidget(self.precision)
            controls.addWidget(self.trailing)
            controls.addStretch(1)
            measurement_layout.addLayout(controls)

            note = QtWidgets.QLabel(
                "Klik op zichtbare modeloppervlakken voor afstand/horizontaal/verticaal/XYZ. "
                "Projectmesh-metingen blijven reviewbewijs. Exacte face-, edge-, radius- en "
                "diametercontrole gebeurt in de Exact Part Workbench."
            )
            note.setWordWrap(True)
            note.setObjectName("cwsMuted")
            measurement_layout.addWidget(note)

            self.measure_table = QtWidgets.QTableWidget(0, 7)
            self.measure_table.setHorizontalHeaderLabels(
                ["Type", "Waarde", "Bewijs", "Status", "Productie-evidence", "Ankers", "ID"]
            )
            self.measure_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.measure_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.measure_table.setAlternatingRowColors(True)
            self.measure_table.horizontalHeader().setStretchLastSection(True)
            measurement_layout.addWidget(self.measure_table, 1)

            export_row = QtWidgets.QHBoxLayout()
            self.delete_measurement = QtWidgets.QPushButton("Meting verwijderen")
            self.stop_measurement = QtWidgets.QPushButton("Meetmodus stoppen")
            self.export_json = QtWidgets.QPushButton("JSON")
            self.export_csv = QtWidgets.QPushButton("CSV")
            self.export_pdf = QtWidgets.QPushButton("PDF")
            export_row.addWidget(self.delete_measurement)
            export_row.addWidget(self.stop_measurement)
            export_row.addStretch(1)
            export_row.addWidget(QtWidgets.QLabel("Meetrapport"))
            export_row.addWidget(self.export_json)
            export_row.addWidget(self.export_csv)
            export_row.addWidget(self.export_pdf)
            measurement_layout.addLayout(export_row)
            root.addWidget(measurements, 1)

            workspace_box = QtWidgets.QGroupBox("Viewerworkspace")
            workspace_layout = QtWidgets.QHBoxLayout(workspace_box)
            self.save_workspace = QtWidgets.QPushButton("Werkruimte opslaan")
            self.load_workspace = QtWidgets.QPushButton("Werkruimte openen")
            workspace_layout.addWidget(self.save_workspace)
            workspace_layout.addWidget(self.load_workspace)
            workspace_layout.addStretch(1)
            root.addWidget(workspace_box)

            self.state = QtWidgets.QLabel()
            self.state.setWordWrap(True)
            self.state.setObjectName("cwsMuted")
            root.addWidget(self.state)

            self.section_x.clicked.connect(lambda: self._add_section(Vector3(1, 0, 0)))
            self.section_y.clicked.connect(lambda: self._add_section(Vector3(0, 1, 0)))
            self.section_z.clicked.connect(lambda: self._add_section(Vector3(0, 0, 1)))
            self.clear_sections.clicked.connect(self._clear_sections)
            self.clip_box.clicked.connect(self._set_clip_box)
            self.clear_clip.clicked.connect(
                lambda: self._run("Clipping gewist", self.controller.set_clipping_box, None)
            )
            self.explode_selection.clicked.connect(self._explode_selection)
            self.reset_explode.clicked.connect(
                lambda: self._run("Explode gereset", self.controller.reset_explode)
            )
            self.undo.clicked.connect(lambda: self._run("Viewer undo", self.controller.undo_viewer))
            self.redo.clicked.connect(lambda: self._run("Viewer redo", self.controller.redo_viewer))
            self.quick_distance.clicked.connect(lambda: self._measure_pair("distance"))
            self.quick_horizontal.clicked.connect(lambda: self._measure_pair("horizontal"))
            self.quick_vertical.clicked.connect(lambda: self._measure_pair("vertical"))
            self.quick_coordinates.clicked.connect(self._measure_coordinates)
            self.stop_measurement.clicked.connect(self._stop_interactive_measurement)
            self.delete_measurement.clicked.connect(self._delete_measurement)
            self.export_json.clicked.connect(lambda: self._export("json"))
            self.export_csv.clicked.connect(lambda: self._export("csv"))
            self.export_pdf.clicked.connect(lambda: self._export("pdf"))
            self.save_workspace.clicked.connect(self._save_workspace)
            self.load_workspace.clicked.connect(self._load_workspace)
            self.unit.currentTextChanged.connect(self._settings_changed)
            self.precision.valueChanged.connect(self._settings_changed)
            self.trailing.toggled.connect(self._settings_changed)

        def _scene_bounds(self) -> BoundingBox:
            bounds = self.controller.index.scene_bounds()
            if bounds is None:
                raise RuntimeError("Scene bevat geen renderbare objecten")
            return bounds

        def _run(self, message: str, function: Callable[..., Any], *args: Any) -> Any:
            try:
                result = function(*args)
                self.refresh()
                self.status_changed.emit(message)
                return result
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Viewer Tools", f"{type(exc).__name__}: {exc}")
                return None

        def _add_section(self, normal: Vector3) -> None:
            center = self._scene_bounds().center
            self._run(
                "Doorsnede toegevoegd",
                self.controller.add_section_plane,
                SectionPlane(origin=center, normal=normal, owner="CWS Viewer"),
            )

        def _clear_sections(self) -> None:
            for plane_id in tuple(self.controller.session.section_planes):
                self.controller.remove_section_plane(plane_id)
            self.refresh()
            self.status_changed.emit("Alle doorsneden gewist")

        def _set_clip_box(self) -> None:
            bounds = self._scene_bounds()
            center = bounds.center
            half = bounds.size * 0.4
            self._run(
                "Clipping box ingesteld",
                self.controller.set_clipping_box,
                ClippingBox(BoundingBox(center - half, center + half)),
            )

        def _explode_selection(self) -> None:
            selected = self.controller.get_selection()
            if not selected:
                QtWidgets.QMessageBox.information(self, "Explode", "Selecteer eerst objecten of een assembly.")
                return
            self._run(
                "Selectie display-only geëxplodeerd",
                self.controller.explode,
                selected,
                float(self.explode_distance.value()),
            )

        def _proof_for_node(self, node_id: str) -> MeasurementProof:
            node = self.controller.index.node(node_id)
            repository = self.workspace.load_result.repository
            mesh = repository.get(node.geometry_id) if node.geometry_id else None
            if mesh is None or mesh.exactness in {"display_proxy", "display_approximation"}:
                return MeasurementProof.DISPLAY_PROXY
            return MeasurementProof.VERIFIED_MESH

        def _anchor_for_center(self, node_id: str) -> ExactMeasurementAnchor:
            node = self.controller.index.node(node_id)
            return ExactMeasurementAnchor(
                node_id=node_id,
                entity_id=node.entity_id,
                source_entity_id=node.source_entity_id or "",
                world_point=self.controller.index.world_bounds_by_node[node_id].center,
                local_point=node.local_bounds.center,
                geometry_hash=node.geometry_hash,
                snap_type=SnapType.CENTER,
                proof=self._proof_for_node(node_id),
            )

        def _anchor_from_pick(self, pick: Any) -> ExactMeasurementAnchor:
            node = self.controller.index.node(str(pick.node_id))
            return ExactMeasurementAnchor(
                node_id=str(pick.node_id),
                entity_id=str(pick.entity_id),
                source_entity_id=str(pick.source_entity_id or node.source_entity_id or ""),
                feature_id=pick.feature_id,
                subshape_type=pick.subshape_type,
                subshape_id=pick.subshape_id,
                world_point=pick.world_point,
                local_point=pick.local_point,
                geometry_hash=node.geometry_hash,
                snap_type=SnapType.NEAREST,
                proof=self._proof_for_node(str(pick.node_id)),
                normal=pick.normal,
            )

        def _settings_changed(self, *_: Any) -> None:
            try:
                self.controller.set_measurement_settings(
                    MeasurementSettings(
                        length_unit=self.unit.currentText(),
                        precision=int(self.precision.value()),
                        trailing_zeroes=bool(self.trailing.isChecked()),
                    )
                )
                self.refresh()
            except Exception:
                return

        def _start_interactive_measurement(self, mode: str) -> bool:
            starter = getattr(self.viewer, "start_measurement", None)
            if callable(starter):
                starter(mode)
                self.status_changed.emit(
                    "Meetmodus actief · klik op het model · Esc of 'Meetmodus stoppen' beëindigt"
                )
                return True
            return False

        def _stop_interactive_measurement(self) -> None:
            cancel = getattr(self.viewer, "cancel_measurement", None)
            if callable(cancel):
                cancel()

        def _measure_pair(self, mode: str) -> None:
            if self._start_interactive_measurement(mode):
                return
            selected = tuple(self.controller.get_selection())
            if len(selected) != 2:
                QtWidgets.QMessageBox.information(
                    self,
                    "Meten",
                    "Selecteer exact twee renderbare objecten. De headless/fallbackviewer meet tussen hun referentiepunten.",
                )
                return
            self._create_pair_record(mode, tuple(self._anchor_for_center(node_id) for node_id in selected))

        def _measure_coordinates(self) -> None:
            if self._start_interactive_measurement("coordinates"):
                return
            selected = tuple(self.controller.get_selection())
            if len(selected) != 1:
                QtWidgets.QMessageBox.information(self, "XYZ", "Selecteer één renderbaar object.")
                return
            self._create_coordinate_record(self._anchor_for_center(selected[0]))

        @QtCore.Slot(str, object)
        def _interactive_measurement_completed(self, mode: str, picks: Any) -> None:
            try:
                anchors = tuple(self._anchor_from_pick(pick) for pick in tuple(picks))
                if mode == "coordinates":
                    self._create_coordinate_record(anchors[0])
                else:
                    self._create_pair_record(mode, anchors)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Interactief meten", f"{type(exc).__name__}: {exc}"
                )

        def _create_pair_record(self, mode: str, anchors: tuple[ExactMeasurementAnchor, ...]) -> None:
            if len(anchors) != 2:
                raise ValueError("Afstandsmeting vereist twee ankers")
            first, second = anchors
            settings = self.controller.get_measurement_settings()
            if mode == "horizontal":
                record = horizontal_distance(first, second, settings)
            elif mode == "vertical":
                record = vertical_distance(first, second, settings)
            else:
                record = distance(first, second, settings)
            self.controller.add_measurement(record)
            self.refresh()
            self.status_changed.emit(
                f"{record.formatted_text} · bewijs {record.proof.value} · productie-evidence {'JA' if record.production_eligible else 'NEE'}"
            )

        def _create_coordinate_record(self, anchor: ExactMeasurementAnchor) -> None:
            record = point(anchor, self.controller.get_measurement_settings())
            self.controller.add_measurement(record)
            self.refresh()
            self.status_changed.emit(
                f"{record.formatted_text} · bewijs {record.proof.value}"
            )

        def _selected_measurement_id(self) -> str | None:
            rows = self.measure_table.selectionModel().selectedRows()
            if not rows:
                return None
            item = self.measure_table.item(rows[0].row(), 6)
            return None if item is None else item.text()

        def _delete_measurement(self) -> None:
            measurement_id = self._selected_measurement_id()
            if measurement_id:
                self._run("Meting verwijderd", self.controller.remove_measurement, measurement_id)

        def _export(self, kind: str) -> None:
            filters = {"json": "JSON (*.json)", "csv": "CSV (*.csv)", "pdf": "PDF (*.pdf)"}
            suffix = "." + kind
            name, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Metingen exporteren", f"CWS_Metingen{suffix}", filters[kind]
            )
            if not name:
                return
            path = Path(name)
            if path.suffix.lower() != suffix:
                path = path.with_suffix(suffix)
            records = self.controller.list_measurements()
            try:
                if kind == "json":
                    export_json(records, path)
                elif kind == "csv":
                    export_csv(records, path)
                else:
                    project_name = str(
                        getattr(self.workspace.project, "project_name", "CWS Project") or "CWS Project"
                    )
                    export_pdf(records, path, project_name=project_name)
                self.status_changed.emit(f"Meetrapport gemaakt: {path}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Meetrapport", f"{type(exc).__name__}: {exc}")

        def _save_workspace(self) -> None:
            project_name = str(
                getattr(self.workspace.project, "project_name", "CWS Project") or "CWS Project"
            )
            name, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Viewerworkspace opslaan",
                f"{project_name}.cwsview.json",
                "CWS Viewer Workspace (*.cwsview.json)",
            )
            if name:
                path = Path(name)
                if not str(path).lower().endswith(".cwsview.json"):
                    path = Path(str(path) + ".cwsview.json")
                self._run("Viewerworkspace opgeslagen", self.controller.save_workspace, path)

        def _load_workspace(self) -> None:
            name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Viewerworkspace openen", "", "CWS Viewer Workspace (*.cwsview.json)"
            )
            if name:
                self._run("Viewerworkspace hersteld", self.controller.load_workspace, Path(name))

        def refresh(self) -> None:
            settings = self.controller.get_measurement_settings()
            blocked = self.unit.blockSignals(True)
            self.unit.setCurrentText(settings.length_unit)
            self.unit.blockSignals(blocked)
            blocked = self.precision.blockSignals(True)
            self.precision.setValue(settings.precision)
            self.precision.blockSignals(blocked)
            blocked = self.trailing.blockSignals(True)
            self.trailing.setChecked(settings.trailing_zeroes)
            self.trailing.blockSignals(blocked)

            records = self.controller.list_measurements()
            self.measure_table.setRowCount(len(records))
            for row, record in enumerate(records):
                values = (
                    record.kind,
                    record.formatted_text or f"{record.value} {record.unit}",
                    record.proof.value,
                    record.status.value,
                    "JA" if record.production_eligible else "NEE",
                    str(len(record.anchors)),
                    record.measurement_id,
                )
                for column, value in enumerate(values):
                    self.measure_table.setItem(row, column, QtWidgets.QTableWidgetItem(str(value)))
            self.measure_table.resizeColumnsToContents()
            self.undo.setEnabled(self.controller.can_undo())
            self.redo.setEnabled(self.controller.can_redo())
            active_mode = str(getattr(self.viewer, "measurement_mode", "") or "")
            self.state.setText(
                f"Sections: {len(self.controller.session.section_planes)} · "
                f"Clipping: {'actief' if self.controller.session.clipping_box else 'uit'} · "
                f"Exploded: {len(self.controller.session.explode_offsets)} · "
                f"Metingen: {len(records)} · Meetmodus: {active_mode or 'uit'}"
            )

else:

    class IntegratedViewerToolsPanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["IntegratedViewerToolsPanel"]
