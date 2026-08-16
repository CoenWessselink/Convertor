"""V15 T4 selection and measurement review panel."""
from __future__ import annotations

from typing import Any

from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.core.v15_selection_measurement import (
    TOLERANCE_PROFILES,
    V15SelectionMeasurementService,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class V15SelectionMeasurementPanel(QtWidgets.QWidget):
        status_changed = QtCore.Signal(str)
        open_measurements_requested = QtCore.Signal()
        open_exact_workbench_requested = QtCore.Signal()

        def __init__(
            self,
            viewer: Any,
            *,
            mesh_repository: Any | None = None,
            parent: Any | None = None,
        ) -> None:
            super().__init__(parent)
            self.viewer = viewer
            self.controller = viewer.controller
            self.service = V15SelectionMeasurementService(
                self.controller, mesh_repository=mesh_repository
            )
            self._last_pick: Any | None = None
            self._build_ui()
            if hasattr(viewer, "pick_result"):
                viewer.pick_result.connect(self._pick_feedback)
            self.refresh()

        def _build_ui(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(7, 7, 7, 7)
            root.setSpacing(7)

            selection = QtWidgets.QGroupBox("Selectie")
            layout = QtWidgets.QGridLayout(selection)
            self.level = QtWidgets.QComboBox()
            for label, value in (
                ("Model", SelectionLevel.MODEL),
                ("Assembly", SelectionLevel.ASSEMBLY),
                ("Onderdeel", SelectionLevel.PART),
                ("Feature", SelectionLevel.FEATURE),
            ):
                self.level.addItem(label, value.value)
            self.area = QtWidgets.QPushButton("Vensterselectie")
            self.all_visible = QtWidgets.QPushButton("Alles zichtbaar selecteren")
            self.invert = QtWidgets.QPushButton("Selectie omkeren")
            self.clear = QtWidgets.QPushButton("Selectie wissen")
            layout.addWidget(QtWidgets.QLabel("Selectieniveau"), 0, 0)
            layout.addWidget(self.level, 0, 1, 1, 2)
            layout.addWidget(self.area, 1, 0)
            layout.addWidget(self.all_visible, 1, 1)
            layout.addWidget(self.invert, 1, 2)
            layout.addWidget(self.clear, 2, 0, 1, 3)
            root.addWidget(selection)

            snapping = QtWidgets.QGroupBox("Snapping / picking")
            snap_layout = QtWidgets.QGridLayout(snapping)
            self.tolerance = QtWidgets.QComboBox()
            for key, profile in TOLERANCE_PROFILES.items():
                self.tolerance.addItem(
                    f"{profile.name} · {profile.snap_tolerance_mm:g} mm", key
                )
            normal_index = self.tolerance.findData("normal")
            self.tolerance.setCurrentIndex(max(0, normal_index))
            self.last_snap = QtWidgets.QLabel("Nog geen pick")
            self.last_snap.setWordWrap(True)
            self.exact = QtWidgets.QPushButton("Exact snapping in Part Workbench")
            snap_layout.addWidget(QtWidgets.QLabel("Interactietolerantie"), 0, 0)
            snap_layout.addWidget(self.tolerance, 0, 1)
            snap_layout.addWidget(self.exact, 0, 2)
            snap_layout.addWidget(self.last_snap, 1, 0, 1, 3)
            warning = QtWidgets.QLabel(
                "Deze tolerantie stuurt alleen cursor/snappinggedrag. Het is geen productie- of maatvoeringstolerantie."
            )
            warning.setWordWrap(True)
            warning.setObjectName("cwsMuted")
            snap_layout.addWidget(warning, 2, 0, 1, 3)
            root.addWidget(snapping)

            measurements = QtWidgets.QGroupBox("Meetstatus")
            measure_layout = QtWidgets.QVBoxLayout(measurements)
            self.measure_state = QtWidgets.QLabel()
            self.measure_state.setWordWrap(True)
            measure_layout.addWidget(self.measure_state)
            row = QtWidgets.QHBoxLayout()
            self.open_measurements = QtWidgets.QPushButton("Meetwerkruimte openen")
            self.open_exact_measure = QtWidgets.QPushButton("Exact Part Workbench")
            row.addWidget(self.open_measurements)
            row.addWidget(self.open_exact_measure)
            row.addStretch(1)
            measure_layout.addLayout(row)
            proof = QtWidgets.QLabel(
                "Bewijs: analytical_brep/canonical_feature kan productie-eligible zijn; verified_mesh/display_proxy blijft reviewbewijs."
            )
            proof.setWordWrap(True)
            proof.setObjectName("cwsMuted")
            measure_layout.addWidget(proof)
            root.addWidget(measurements)

            self.state = QtWidgets.QLabel()
            self.state.setWordWrap(True)
            root.addWidget(self.state)
            root.addStretch(1)

            self.level.currentIndexChanged.connect(self._level_changed)
            self.area.clicked.connect(lambda: self.viewer.set_area_selection(True))
            self.all_visible.clicked.connect(
                lambda: self._run("Alle zichtbare objecten geselecteerd", self.service.select_all_visible)
            )
            self.invert.clicked.connect(
                lambda: self._run("Zichtbare selectie omgekeerd", self.service.invert_visible_selection)
            )
            self.clear.clicked.connect(
                lambda: self._run("Selectie gewist", self.service.clear_selection)
            )
            self.tolerance.currentIndexChanged.connect(self._tolerance_changed)
            self.exact.clicked.connect(self.open_exact_workbench_requested.emit)
            self.open_measurements.clicked.connect(self.open_measurements_requested.emit)
            self.open_exact_measure.clicked.connect(self.open_exact_workbench_requested.emit)

        def _run(self, message: str, function: Any, *args: Any) -> Any:
            try:
                result = function(*args)
                self.refresh()
                self.status_changed.emit(message)
                return result
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "CWS Viewer V15", f"{type(exc).__name__}: {exc}"
                )
                return None

        def _level_changed(self, _index: int) -> None:
            value = self.level.currentData()
            if value:
                self._run(
                    f"Selectieniveau: {value}",
                    self.service.set_selection_level,
                    SelectionLevel(str(value)),
                )

        def _tolerance_changed(self, _index: int) -> None:
            key = str(self.tolerance.currentData() or "normal")
            self.service.set_tolerance_profile(key)
            self.status_changed.emit(
                f"Interactietolerantie: {self.service.tolerance_profile.snap_tolerance_mm:g} mm"
            )
            self.refresh()

        def _pick_feedback(self, pick: Any) -> None:
            self._last_pick = pick
            try:
                anchor = self.service.anchor_from_project_pick(pick)
                point = anchor.world_point
                self.last_snap.setText(
                    f"Pick {anchor.entity_id} · snap {anchor.snap_type.value} · bewijs {anchor.proof.value} · "
                    f"X {point.x:.3f} · Y {point.y:.3f} · Z {point.z:.3f} mm"
                )
            except Exception as exc:
                self.last_snap.setText(f"Pickfeedback niet beschikbaar: {type(exc).__name__}: {exc}")
            self.refresh()

        def refresh(self) -> None:
            current = self.controller.session.selection_level.value
            index = self.level.findData(current)
            self.level.blockSignals(True)
            self.level.setCurrentIndex(max(0, index))
            self.level.blockSignals(False)
            records = self.controller.list_measurements()
            production = sum(1 for item in records if item.production_eligible)
            review = len(records) - production
            self.measure_state.setText(
                f"Metingen: {len(records)} · production-eligible bewijs: {production} · review-only: {review}"
            )
            self.state.setText(
                f"Selectie: {len(self.controller.get_selection())} · niveau: {current} · "
                f"snap-profiel: {self.service.tolerance_profile.name} ({self.service.tolerance_profile.snap_tolerance_mm:g} mm)"
            )

else:

    class V15SelectionMeasurementPanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["V15SelectionMeasurementPanel"]
