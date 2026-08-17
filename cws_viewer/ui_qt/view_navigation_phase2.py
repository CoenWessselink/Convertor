"""Phase 2 navigation/review controls for practical clipping parity."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from cws_viewer.contracts.state import SectionPlane
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.view_navigation_v15 import V15ViewNavigationPanel


PHASE2_NAVIGATION_SCHEMA = "cws-viewer-navigation-phase2-1.0"
PHASE2_NAVIGATION_VERSION = "1.4.0-v15-phase2.1"


def phase2_navigation_contract() -> dict[str, Any]:
    return {
        "schema": PHASE2_NAVIGATION_SCHEMA,
        "version": PHASE2_NAVIGATION_VERSION,
        "capabilities": {
            "picked_surface_section_plane": True,
            "section_plane_offset_control": True,
            "variable_clip_box_fraction": True,
            "section_plane_enable_disable": True,
            "section_plane_flip_remove": True,
            "clipping_box": True,
        },
        "safety": {
            "clipping_mutates_canonical_geometry": False,
            "section_plane_is_manufacturing_cut": False,
        },
    }


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class V15ViewNavigationPanelPhase2(V15ViewNavigationPanel):
        def __init__(self, viewer: Any, parent: Any | None = None) -> None:
            super().__init__(viewer, parent)
            self._install_phase2_clipping_controls()
            self.refresh()

        def _install_phase2_clipping_controls(self) -> None:
            group = QtWidgets.QGroupBox("Interactieve clipping · Phase 2")
            layout = QtWidgets.QGridLayout(group)

            self.section_from_surface = QtWidgets.QPushButton(
                "Doorsnede uit gekozen vlak"
            )
            self.section_from_surface.setToolTip(
                "Klik eerst een modelvlak. De nieuwe section plane gebruikt exact "
                "het gekozen wereldpunt en de beschikbare vlaknormaal."
            )
            self.section_offset = QtWidgets.QDoubleSpinBox()
            self.section_offset.setRange(0.1, 1_000_000.0)
            self.section_offset.setDecimals(2)
            self.section_offset.setValue(100.0)
            self.section_offset.setSuffix(" mm")
            self.section_minus = QtWidgets.QPushButton("− verplaats")
            self.section_plus = QtWidgets.QPushButton("+ verplaats")

            self.clip_fraction = QtWidgets.QSpinBox()
            self.clip_fraction.setRange(5, 100)
            self.clip_fraction.setValue(80)
            self.clip_fraction.setSuffix(" %")
            self.apply_clip_fraction = QtWidgets.QPushButton("Clipping box toepassen")

            layout.addWidget(self.section_from_surface, 0, 0, 1, 2)
            layout.addWidget(QtWidgets.QLabel("Section stap"), 1, 0)
            layout.addWidget(self.section_offset, 1, 1)
            layout.addWidget(self.section_minus, 2, 0)
            layout.addWidget(self.section_plus, 2, 1)
            layout.addWidget(QtWidgets.QLabel("Clipping box"), 3, 0)
            layout.addWidget(self.clip_fraction, 3, 1)
            layout.addWidget(self.apply_clip_fraction, 4, 0, 1, 2)

            hint = QtWidgets.QLabel(
                "Section/clipping blijft uitsluitend viewerstate. Verplaatsen of flippen "
                "wijzigt geen bronmodel, NC- of productiegeometrie."
            )
            hint.setWordWrap(True)
            hint.setObjectName("cwsMuted")
            layout.addWidget(hint, 5, 0, 1, 2)

            root = self.layout()
            if root is not None:
                root.insertWidget(max(0, root.count() - 1), group)

            self.section_from_surface.clicked.connect(self._section_from_pick)
            self.section_minus.clicked.connect(lambda: self._move_selected_section(-1.0))
            self.section_plus.clicked.connect(lambda: self._move_selected_section(1.0))
            self.apply_clip_fraction.clicked.connect(self._apply_variable_clip)

        def _section_from_pick(self) -> None:
            pick = self._last_pick
            normal = getattr(pick, "normal", None) if pick is not None else None
            point = getattr(pick, "world_point", None) if pick is not None else None
            if point is None or normal is None or normal.length() <= 1e-12:
                QtWidgets.QMessageBox.information(
                    self,
                    "Doorsnede uit vlak",
                    "Klik eerst een modelvlak met een geldige oppervlaknormaal.",
                )
                return
            try:
                plane_id = self.controller.add_section_plane(
                    SectionPlane(
                        origin=point,
                        normal=normal.normalized(),
                        owner="CWS Viewer Phase 2",
                    )
                )
                self.refresh()
                for index in range(self.sections.topLevelItemCount()):
                    item = self.sections.topLevelItem(index)
                    if str(item.data(0, QtCore.Qt.ItemDataRole.UserRole) or "") == plane_id:
                        self.sections.setCurrentItem(item)
                        break
                self.status_changed.emit("Doorsnede op gekozen modelvlak toegevoegd")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Doorsnede uit vlak", f"{type(exc).__name__}: {exc}"
                )

        def _move_selected_section(self, direction: float) -> None:
            plane_id = self._selected_plane_id()
            if not plane_id:
                QtWidgets.QMessageBox.information(
                    self, "Section verplaatsen", "Selecteer eerst een section plane."
                )
                return
            plane = self.controller.session.section_planes.get(plane_id)
            if plane is None:
                return
            try:
                step = float(self.section_offset.value()) * float(direction)
                axis = plane.normal.normalized()
                if plane.flipped:
                    axis = axis * -1.0
                self.controller.update_section_plane(
                    plane_id,
                    replace(plane, origin=plane.origin + axis * step),
                )
                self.refresh()
                self.status_changed.emit(
                    f"Section {step:+.2f} mm langs actieve normaal verplaatst"
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Section verplaatsen", f"{type(exc).__name__}: {exc}"
                )

        def _apply_variable_clip(self) -> None:
            fraction = float(self.clip_fraction.value()) / 100.0
            self._run(
                f"Clipping box {self.clip_fraction.value()}%",
                self.service.set_clip_box_fraction,
                fraction,
            )

        def refresh(self) -> None:
            super().refresh()
            if hasattr(self, "section_from_surface"):
                normal = getattr(self._last_pick, "normal", None)
                self.section_from_surface.setEnabled(
                    normal is not None and normal.length() > 1e-12
                )

else:

    class V15ViewNavigationPanelPhase2:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = [
    "PHASE2_NAVIGATION_SCHEMA",
    "PHASE2_NAVIGATION_VERSION",
    "V15ViewNavigationPanelPhase2",
    "phase2_navigation_contract",
]
