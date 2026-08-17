"""V15 T3 camera, view, selection and clipping panel."""
from __future__ import annotations

from typing import Any

from cws_viewer.contracts.enums import ProjectionType, SelectionLevel, StandardView
from cws_viewer.math3d import Vector3
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class V15ViewNavigationPanel(QtWidgets.QWidget):
        status_changed = QtCore.Signal(str)

        def __init__(self, viewer: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.viewer = viewer
            self.service = viewer.view_navigation
            self.controller = viewer.controller
            self._last_pick: Any | None = None
            self._building = False
            self._build_ui()
            if hasattr(viewer, "pick_result"):
                viewer.pick_result.connect(self._remember_pick)
            if hasattr(viewer, "zoom_area_completed"):
                viewer.zoom_area_completed.connect(lambda _ids: self.refresh())
            self.refresh()

        def _build_ui(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(7, 7, 7, 7)
            root.setSpacing(7)

            camera_group = QtWidgets.QGroupBox("Camera, selectie en navigatie")
            camera_layout = QtWidgets.QVBoxLayout(camera_group)

            selection_row = QtWidgets.QHBoxLayout()
            selection_row.addWidget(QtWidgets.QLabel("Selectiemodus"))
            self.selection_level = QtWidgets.QComboBox()
            self.selection_level.addItem("Object", SelectionLevel.PART.value)
            self.selection_level.addItem("Assembly", SelectionLevel.ASSEMBLY.value)
            self.selection_level.setToolTip(
                "Object selecteert onderdelen; Assembly promoveert een klik naar de bovenliggende assembly. "
                "Houd Alt ingedrukt om Object/Assembly tijdelijk om te keren."
            )
            selection_row.addWidget(self.selection_level)
            selection_hint = QtWidgets.QLabel("Alt = tijdelijk omkeren")
            selection_hint.setObjectName("cwsMuted")
            selection_row.addWidget(selection_hint)
            selection_row.addStretch(1)
            camera_layout.addLayout(selection_row)

            history = QtWidgets.QHBoxLayout()
            self.back = QtWidgets.QPushButton("← Vorige camera")
            self.forward = QtWidgets.QPushButton("Volgende camera →")
            self.fit = QtWidgets.QPushButton("Fit alles")
            self.fit_selection = QtWidgets.QPushButton("Fit selectie")
            history.addWidget(self.back)
            history.addWidget(self.forward)
            history.addWidget(self.fit)
            history.addWidget(self.fit_selection)
            camera_layout.addLayout(history)

            views = QtWidgets.QHBoxLayout()
            for label, view in (
                ("Iso", StandardView.ISOMETRIC),
                ("Voor", StandardView.FRONT),
                ("Rechts", StandardView.RIGHT),
                ("Boven", StandardView.TOP),
            ):
                button = QtWidgets.QPushButton(label)
                button.clicked.connect(lambda _checked=False, v=view: self._run_view(v))
                views.addWidget(button)
            self.projection = QtWidgets.QComboBox()
            self.projection.addItem("Perspectief", ProjectionType.PERSPECTIVE.value)
            self.projection.addItem("Orthografisch", ProjectionType.ORTHOGRAPHIC.value)
            views.addWidget(self.projection)
            camera_layout.addLayout(views)

            action_row = QtWidgets.QHBoxLayout()
            self.zoom_area = QtWidgets.QPushButton("Zoomgebied")
            self.from_face = QtWidgets.QPushButton("Loodrecht op gekozen vlak")
            self.save_view = QtWidgets.QPushButton("View opslaan")
            action_row.addWidget(self.zoom_area)
            action_row.addWidget(self.from_face)
            action_row.addWidget(self.save_view)
            camera_layout.addLayout(action_row)

            grid = QtWidgets.QGridLayout()
            self._camera_fields: dict[str, Any] = {}
            for row, (label, prefix) in enumerate((("Camera", "eye"), ("Target", "target"))):
                grid.addWidget(QtWidgets.QLabel(label), row, 0)
                for column, axis in enumerate(("x", "y", "z"), start=1):
                    spin = QtWidgets.QDoubleSpinBox()
                    spin.setRange(-1_000_000_000.0, 1_000_000_000.0)
                    spin.setDecimals(3)
                    spin.setSingleStep(100.0)
                    spin.setPrefix(axis.upper() + " ")
                    self._camera_fields[f"{prefix}_{axis}"] = spin
                    grid.addWidget(spin, row, column)
            self.apply_camera = QtWidgets.QPushButton("Camera toepassen")
            grid.addWidget(self.apply_camera, 0, 4, 2, 1)
            camera_layout.addLayout(grid)
            root.addWidget(camera_group)

            section_group = QtWidgets.QGroupBox("Doorsneden en clipping")
            section_layout = QtWidgets.QVBoxLayout(section_group)
            quick = QtWidgets.QHBoxLayout()
            self.section_x = QtWidgets.QPushButton("+ X")
            self.section_y = QtWidgets.QPushButton("+ Y")
            self.section_z = QtWidgets.QPushButton("+ Z")
            self.flip = QtWidgets.QPushButton("Flip")
            self.remove = QtWidgets.QPushButton("Verwijder")
            self.clear = QtWidgets.QPushButton("Alles wissen")
            for button in (self.section_x, self.section_y, self.section_z, self.flip, self.remove, self.clear):
                quick.addWidget(button)
            section_layout.addLayout(quick)

            self.sections = QtWidgets.QTreeWidget()
            self.sections.setHeaderLabels(["Actief", "Plane ID", "Normaal", "Flipped"])
            self.sections.setRootIsDecorated(False)
            self.sections.itemChanged.connect(self._section_item_changed)
            section_layout.addWidget(self.sections, 1)

            clip_row = QtWidgets.QHBoxLayout()
            self.clip_80 = QtWidgets.QPushButton("Clipping box 80%")
            self.clear_clip = QtWidgets.QPushButton("Clipping uit")
            self.clip_state = QtWidgets.QLabel("Clipping: uit")
            clip_row.addWidget(self.clip_80)
            clip_row.addWidget(self.clear_clip)
            clip_row.addWidget(self.clip_state)
            clip_row.addStretch(1)
            section_layout.addLayout(clip_row)
            root.addWidget(section_group, 1)

            self.state = QtWidgets.QLabel()
            self.state.setWordWrap(True)
            self.state.setObjectName("cwsMuted")
            root.addWidget(self.state)

            self.selection_level.currentIndexChanged.connect(self._selection_level_changed)
            self.back.clicked.connect(lambda: self._run("Vorige camera", self.service.camera_back))
            self.forward.clicked.connect(lambda: self._run("Volgende camera", self.service.camera_forward))
            self.fit.clicked.connect(lambda: self._run("Fit alles", self.service.fit_all))
            self.fit_selection.clicked.connect(lambda: self._run("Fit selectie", self.service.fit_selection))
            self.projection.currentIndexChanged.connect(self._projection_changed)
            self.zoom_area.clicked.connect(lambda: self.viewer.set_zoom_area(True))
            self.from_face.clicked.connect(self._view_from_last_face)
            self.save_view.clicked.connect(self._save_named_view)
            self.apply_camera.clicked.connect(self._apply_camera)
            self.section_x.clicked.connect(lambda: self._add_section(Vector3(1.0, 0.0, 0.0)))
            self.section_y.clicked.connect(lambda: self._add_section(Vector3(0.0, 1.0, 0.0)))
            self.section_z.clicked.connect(lambda: self._add_section(Vector3(0.0, 0.0, 1.0)))
            self.flip.clicked.connect(self._flip_selected)
            self.remove.clicked.connect(self._remove_selected)
            self.clear.clicked.connect(lambda: self._run("Alle doorsneden gewist", self.service.clear_sections))
            self.clip_80.clicked.connect(lambda: self._run("Clipping box 80%", self.service.set_clip_box_fraction, 0.8))
            self.clear_clip.clicked.connect(lambda: self._run("Clipping uit", self.service.clear_clip_box))

        def _run(self, message: str, function: Any, *args: Any, **kwargs: Any) -> Any:
            try:
                result = function(*args, **kwargs)
                self.refresh()
                self.status_changed.emit(message)
                return result
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "CWS Viewer V15", f"{type(exc).__name__}: {exc}")
                return None

        def _remember_pick(self, pick: Any) -> None:
            self._last_pick = pick
            normal = getattr(pick, "normal", None)
            self.from_face.setEnabled(normal is not None and normal.length() > 1e-12)
            self.refresh()

        def _selection_level_changed(self, _index: int) -> None:
            if self._building:
                return
            value = self.selection_level.currentData()
            if value:
                level = SelectionLevel(str(value))
                self.controller.set_selection_level(level)
                self.status_changed.emit(
                    "Selectiemodus: Assembly · Alt selecteert tijdelijk Object"
                    if level == SelectionLevel.ASSEMBLY
                    else "Selectiemodus: Object · Alt selecteert tijdelijk Assembly"
                )

        def _run_view(self, view: StandardView) -> None:
            self._run(f"Aanzicht: {view.value}", self.service.set_standard_view, view)

        def _projection_changed(self, _index: int) -> None:
            if self._building:
                return
            value = self.projection.currentData()
            if value:
                self._run("Projectie gewijzigd", self.service.set_projection, ProjectionType(str(value)))

        def _view_from_last_face(self) -> None:
            normal = getattr(self._last_pick, "normal", None)
            if normal is None or normal.length() <= 1e-12:
                QtWidgets.QMessageBox.information(
                    self,
                    "Aanzicht uit vlak",
                    "Klik eerst een vlak of geometriepunt met een geldige normaal.",
                )
                return
            point = getattr(self._last_pick, "world_point", None)
            self._run(
                "Camera loodrecht op gekozen vlak",
                self.service.view_from_normal,
                normal,
                target=point,
            )

        def _save_named_view(self) -> None:
            name, ok = QtWidgets.QInputDialog.getText(self, "View opslaan", "Naam van de view:")
            if ok and str(name).strip():
                self._run("View opgeslagen", self.service.save_named_view, str(name).strip())

        def _apply_camera(self) -> None:
            position = Vector3(
                float(self._camera_fields["eye_x"].value()),
                float(self._camera_fields["eye_y"].value()),
                float(self._camera_fields["eye_z"].value()),
            )
            target = Vector3(
                float(self._camera_fields["target_x"].value()),
                float(self._camera_fields["target_y"].value()),
                float(self._camera_fields["target_z"].value()),
            )
            self._run("Camerapositie toegepast", self.service.set_camera_position, position, target=target)

        def _add_section(self, normal: Vector3) -> None:
            self._run("Doorsnede toegevoegd", self.service.add_section, normal)

        def _selected_plane_id(self) -> str | None:
            items = self.sections.selectedItems()
            if not items:
                return None
            value = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
            return str(value) if value else None

        def _section_item_changed(self, item: Any, _column: int) -> None:
            if self._building:
                return
            plane_id = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            if plane_id:
                enabled = item.checkState(0) == QtCore.Qt.CheckState.Checked
                self._run("Doorsnede status gewijzigd", self.service.set_section_enabled, str(plane_id), enabled)

        def _flip_selected(self) -> None:
            plane_id = self._selected_plane_id()
            if plane_id:
                self._run("Doorsnede geflipt", self.service.flip_section, plane_id)

        def _remove_selected(self) -> None:
            plane_id = self._selected_plane_id()
            if plane_id:
                self._run("Doorsnede verwijderd", self.service.remove_section, plane_id)

        def refresh(self) -> None:
            self._building = True
            try:
                camera = self.controller.get_camera()
                values = {
                    "eye_x": camera.position.x,
                    "eye_y": camera.position.y,
                    "eye_z": camera.position.z,
                    "target_x": camera.target.x,
                    "target_y": camera.target.y,
                    "target_z": camera.target.z,
                }
                for key, value in values.items():
                    self._camera_fields[key].setValue(float(value))
                selection_index = self.selection_level.findData(
                    self.controller.session.selection_level.value
                )
                if selection_index >= 0:
                    self.selection_level.setCurrentIndex(selection_index)
                projection_index = self.projection.findData(camera.projection.value)
                self.projection.setCurrentIndex(max(0, projection_index))
                self.back.setEnabled(self.service.can_camera_back)
                self.forward.setEnabled(self.service.can_camera_forward)
                normal = getattr(self._last_pick, "normal", None)
                self.from_face.setEnabled(normal is not None and normal.length() > 1e-12)

                self.sections.blockSignals(True)
                self.sections.clear()
                for plane_id, plane in sorted(self.controller.session.section_planes.items()):
                    n = plane.normal.normalized()
                    item = QtWidgets.QTreeWidgetItem(
                        [
                            "",
                            str(plane_id),
                            f"({n.x:.3f}, {n.y:.3f}, {n.z:.3f})",
                            "ja" if plane.flipped else "nee",
                        ]
                    )
                    item.setData(0, QtCore.Qt.ItemDataRole.UserRole, str(plane_id))
                    item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(
                        0,
                        QtCore.Qt.CheckState.Checked if plane.enabled else QtCore.Qt.CheckState.Unchecked,
                    )
                    self.sections.addTopLevelItem(item)
                self.sections.blockSignals(False)
                self.sections.resizeColumnToContents(0)
                self.sections.resizeColumnToContents(1)
                self.clip_state.setText(
                    "Clipping: actief" if self.controller.session.clipping_box is not None else "Clipping: uit"
                )
                self.state.setText(
                    f"Selectie {self.controller.session.selection_level.value} · "
                    f"Camera ({camera.projection.value}) · sections {len(self.controller.session.section_planes)} · "
                    f"saved views {len(self.controller.list_viewpoints())} · view-state is display/review-only"
                )
            finally:
                self._building = False

else:

    class V15ViewNavigationPanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["V15ViewNavigationPanel"]
