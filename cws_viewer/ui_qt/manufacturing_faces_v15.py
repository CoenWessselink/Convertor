"""Read-only ManufacturingFace inspection dock for CWS Viewer V15 T8."""
from __future__ import annotations

import math
from typing import Any

from cws_convertor.manufacturing import (
    FaceProofStatus,
    ManufacturingFace,
    ManufacturingFaceService,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


def _transform_point(matrix: list[list[float]], point: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = point
    return (
        matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3],
        matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3],
        matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3],
    )


def _transform_vector(matrix: list[list[float]], vector: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = vector
    result = (
        matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z,
        matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z,
        matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z,
    )
    length = math.sqrt(sum(value * value for value in result))
    return result if length <= 1e-12 else tuple(value / length for value in result)


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class ManufacturingFacesPanel(QtWidgets.QWidget):
        status_changed = QtCore.Signal(str)

        def __init__(self, viewer: Any, project: Any, parent: Any = None) -> None:
            super().__init__(parent)
            self.viewer = viewer
            self.project = project
            self.service = ManufacturingFaceService()
            self._part_id = ""
            self._report = None
            self._overlay_actors: list[Any] = []
            self._build_ui()

        def _build_ui(self) -> None:
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(6)
            title = QtWidgets.QLabel("Manufacturing Faces · T8")
            title.setObjectName("cwsPanelTitle")
            layout.addWidget(title)
            hint = QtWidgets.QLabel(
                "Canonical productie-vlakken uit de gereviewde Part Workbench/BREP. "
                "DSTV v/h/o/u is uitsluitend adaptermapping en blijft geblokkeerd zolang het vlak niet eenduidig bevestigd is."
            )
            hint.setWordWrap(True)
            layout.addWidget(hint)

            actions = QtWidgets.QHBoxLayout()
            self.analyse_button = QtWidgets.QPushButton("Analyseer geselecteerd onderdeel")
            self.analyse_button.clicked.connect(self.analyse_selection)
            actions.addWidget(self.analyse_button)
            clear = QtWidgets.QPushButton("Overlay wissen")
            clear.clicked.connect(self.clear_overlay)
            actions.addWidget(clear)
            actions.addStretch(1)
            layout.addLayout(actions)

            self.summary = QtWidgets.QLabel("Selecteer een maakdeel en start de face-analyse.")
            self.summary.setWordWrap(True)
            layout.addWidget(self.summary)

            self.table = QtWidgets.QTableWidget(0, 7)
            self.table.setHorizontalHeaderLabels(
                ["Role", "Kind", "Surface", "Area mm²", "DSTV", "Proof", "Face ID"]
            )
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.verticalHeader().setVisible(False)
            self.table.itemSelectionChanged.connect(self._selected_face_changed)
            layout.addWidget(self.table, 1)

            self.details = QtWidgets.QPlainTextEdit()
            self.details.setReadOnly(True)
            self.details.setMaximumHeight(150)
            layout.addWidget(self.details)

        def selection_changed(self) -> None:
            selected = self._selected_part_id()
            if selected != self._part_id:
                self._part_id = ""
                self._report = None
                self.table.setRowCount(0)
                self.details.clear()
                self.clear_overlay()
                if selected:
                    self.summary.setText(
                        f"Geselecteerd: {selected}. Face-analyse is nog niet uitgevoerd voor deze selectie."
                    )

        def _selected_part_id(self) -> str:
            controller = self.viewer.controller
            for node_id in controller.get_selection():
                try:
                    entity_id = str(controller.index.node(node_id).entity_id or "")
                except Exception:
                    continue
                if entity_id in self.project.parts:
                    return entity_id
            return ""

        def analyse_selection(self) -> None:
            part_id = self._selected_part_id()
            if not part_id:
                self.summary.setText("Geen onderdeel geselecteerd.")
                self.status_changed.emit("Manufacturing Faces: selecteer eerst een onderdeel")
                return
            part = self.project.parts[part_id]
            try:
                report = self.service.build(part, persist=False)
            except Exception as exc:
                self.summary.setText(f"Face-analyse geblokkeerd: {type(exc).__name__}: {exc}")
                self.table.setRowCount(0)
                self.clear_overlay()
                self.status_changed.emit("Manufacturing Face analyse geblokkeerd")
                return
            self._part_id = part_id
            self._report = report
            self.table.setRowCount(len(report.faces))
            for row, face in enumerate(report.faces):
                values = (
                    face.semantic_role.value,
                    face.canonical_kind,
                    face.surface_type.value,
                    f"{face.area_mm2:,.2f}",
                    "/".join(face.dstv_side_candidates) or "—",
                    face.proof_status.value,
                    face.face_id,
                )
                for column, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(str(value))
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, face.face_id)
                    self.table.setItem(row, column, item)
            self.table.resizeColumnsToContents()
            status = "GROEN" if report.passed else "GEBLOKKEERD"
            self.summary.setText(
                f"{part.part_position or part_id} · {len(report.faces)} canonical faces · "
                f"status {status} · report {report.report_sha256[:16]}…"
            )
            self._draw_overlay(selected_face_id="")
            if report.faces:
                self.table.selectRow(0)
            self.status_changed.emit(
                f"Manufacturing Faces: {len(report.faces)} vlak(ken), {len(report.blocking_codes)} blocker(s)"
            )

        def _backend(self) -> Any | None:
            backend = getattr(self.viewer, "backend", None)
            if backend is None:
                backend = getattr(self.viewer, "_backend", None)
            return backend

        def clear_overlay(self) -> None:
            backend = self._backend()
            renderer = getattr(backend, "_renderer", None) if backend is not None else None
            if renderer is not None:
                for actor in self._overlay_actors:
                    try:
                        renderer.RemoveViewProp(actor)
                    except Exception:
                        try:
                            renderer.RemoveActor(actor)
                        except Exception:
                            pass
            self._overlay_actors.clear()
            try:
                if backend is not None:
                    backend.render()
            except Exception:
                pass

        @staticmethod
        def _status_rgb(face: ManufacturingFace, selected: bool) -> tuple[float, float, float]:
            if selected:
                return (0.16, 0.52, 0.95)
            if face.proof_status == FaceProofStatus.VERIFIED:
                return (0.20, 0.72, 0.34)
            if face.proof_status == FaceProofStatus.BLOCKED:
                return (0.90, 0.22, 0.20)
            return (0.96, 0.58, 0.14)

        def _draw_overlay(self, *, selected_face_id: str) -> None:
            self.clear_overlay()
            if self._report is None or not self._part_id:
                return
            backend = self._backend()
            vtk = getattr(backend, "_vtk", None) if backend is not None else None
            renderer = getattr(backend, "_renderer", None) if backend is not None else None
            if vtk is None or renderer is None:
                return
            part = self.project.parts[self._part_id]
            matrix = part.global_placement.matrix
            diagonal = max(float(part.length_mm or 0.0), 250.0)
            normal_length = min(max(diagonal * 0.05, 25.0), 250.0)
            for face in self._report.faces:
                selected = face.face_id == selected_face_id
                rgb = self._status_rgb(face, selected)
                for loop in face.outline_loops_part_mm:
                    if len(loop) < 2:
                        continue
                    points = vtk.vtkPoints()
                    line = vtk.vtkPolyLine()
                    line.GetPointIds().SetNumberOfIds(len(loop))
                    for index, raw in enumerate(loop):
                        point_id = points.InsertNextPoint(*_transform_point(matrix, raw))
                        line.GetPointIds().SetId(index, point_id)
                    cells = vtk.vtkCellArray()
                    cells.InsertNextCell(line)
                    data = vtk.vtkPolyData()
                    data.SetPoints(points)
                    data.SetLines(cells)
                    mapper = vtk.vtkPolyDataMapper()
                    mapper.SetInputData(data)
                    actor = vtk.vtkActor()
                    actor.SetMapper(mapper)
                    actor.GetProperty().SetColor(*rgb)
                    actor.GetProperty().SetLineWidth(4.0 if selected else 2.0)
                    actor.SetPickable(False)
                    renderer.AddActor(actor)
                    self._overlay_actors.append(actor)
                if selected:
                    origin = _transform_point(matrix, face.local_frame.origin_mm)
                    normal = _transform_vector(matrix, face.local_frame.normal)
                    tip = tuple(origin[index] + normal[index] * normal_length for index in range(3))
                    source = vtk.vtkLineSource()
                    source.SetPoint1(*origin)
                    source.SetPoint2(*tip)
                    mapper = vtk.vtkPolyDataMapper()
                    mapper.SetInputConnection(source.GetOutputPort())
                    actor = vtk.vtkActor()
                    actor.SetMapper(mapper)
                    actor.GetProperty().SetColor(*rgb)
                    actor.GetProperty().SetLineWidth(4.0)
                    actor.SetPickable(False)
                    renderer.AddActor(actor)
                    self._overlay_actors.append(actor)
            backend.render()

        def _selected_face_changed(self) -> None:
            if self._report is None:
                return
            rows = self.table.selectionModel().selectedRows()
            if not rows:
                self._draw_overlay(selected_face_id="")
                return
            row = rows[0].row()
            item = self.table.item(row, 0)
            face_id = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "") if item else ""
            face = next((candidate for candidate in self._report.faces if candidate.face_id == face_id), None)
            if face is None:
                return
            mapping = {
                "Face": face.face_id,
                "Role": face.semantic_role.value,
                "Canonical kind": face.canonical_kind,
                "Surface": face.surface_type.value,
                "Area mm²": f"{face.area_mm2:.4f}",
                "Proof": face.proof_status.value,
                "Confidence": f"{face.confidence:.3f}",
                "DSTV candidates": ", ".join(face.dstv_side_candidates) or "geen",
                "Geometry hash": face.geometry_hash,
                "Frame hash": face.local_frame.frame_sha256,
                "Source": face.source_geometry_ref,
            }
            self.details.setPlainText("\n".join(f"{key}: {value}" for key, value in mapping.items()))
            self._draw_overlay(selected_face_id=face.face_id)

else:

    class ManufacturingFacesPanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["ManufacturingFacesPanel"]
