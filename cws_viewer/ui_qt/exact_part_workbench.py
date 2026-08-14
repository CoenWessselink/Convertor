"""PySide6 Exact Part Workbench shell backed by OCCT/AIS and V6 services."""
from __future__ import annotations

from typing import Any

from cws_viewer.backends.occt_exact import OcctExactPartBackend
from cws_viewer.exact.model import ExactPartRuntime, SubshapeKind
from cws_viewer.exact.workbench import ExactPartWorkbenchService
from cws_viewer.technology.contracts import NativeWindow
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class ExactOcctWidget(QtWidgets.QWidget):  # type: ignore[misc]
        subshape_picked = QtCore.Signal(str)
        backend_failed = QtCore.Signal(str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.setObjectName("cwsExactOcctWidget")
            self.setMinimumSize(520, 360)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NativeWindow, True)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_PaintOnScreen, True)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
            self.setMouseTracking(True)
            self.backend = OcctExactPartBackend()
            self._initialized = False
            self._pending: tuple[ExactPartRuntime, ExactPartRuntime | None] | None = None

        def paintEngine(self):
            return None

        def _ensure_initialized(self) -> None:
            if self._initialized or not self.isVisible():
                return
            try:
                self.backend.initialize(
                    width=max(1, self.width()), height=max(1, self.height()),
                    native_window=NativeWindow(int(self.winId()), max(1,self.width()), max(1,self.height())),
                )
                self._initialized = True
                if self._pending:
                    source, canonical = self._pending; self._pending = None
                    self.backend.load_parts(source, canonical)
            except Exception as exc:
                self.backend_failed.emit(f"{type(exc).__name__}: {exc}")

        def showEvent(self, event: Any) -> None:
            super().showEvent(event); QtCore.QTimer.singleShot(0, self._ensure_initialized)

        def paintEvent(self, event: Any) -> None:
            if self._initialized: self.backend.render()
            event.accept()

        def resizeEvent(self, event: Any) -> None:
            super().resizeEvent(event)
            if self._initialized:
                self.backend.resize(event.size().width(), event.size().height()); self.backend.render()

        def mousePressEvent(self, event: Any) -> None:
            if self._initialized and event.button() == QtCore.Qt.MouseButton.LeftButton:
                point=event.position(); stable_id=self.backend.pick_at(int(point.x()),int(point.y()))
                if stable_id: self.subshape_picked.emit(stable_id)
            super().mousePressEvent(event)

        def load_parts(self, source: ExactPartRuntime, canonical: ExactPartRuntime | None = None) -> None:
            if not self._initialized:
                self._pending=(source,canonical); self._ensure_initialized(); return
            self.backend.load_parts(source,canonical)

        def closeEvent(self,event:Any)->None:
            self.backend.dispose(); self._initialized=False; super().closeEvent(event)


    class ExactPartWorkbenchPanel(QtWidgets.QWidget):  # type: ignore[misc]
        """Functional review shell; production release remains outside the viewer."""

        def __init__(self, service: ExactPartWorkbenchService, parent: Any | None = None) -> None:
            super().__init__(parent); self.service=service; self.setObjectName("cwsExactPartWorkbench")
            self._build_ui(); self._populate(); self.viewer.load_parts(service.source,service.canonical)

        def _build_ui(self)->None:
            layout=QtWidgets.QVBoxLayout(self); layout.setContentsMargins(6,6,6,6)
            toolbar=QtWidgets.QToolBar(); toolbar.setObjectName("cwsExactWorkbenchToolbar")
            self.selection_combo=QtWidgets.QComboBox(); self.selection_combo.addItems(["Face","Edge","Vertex"])
            self.selection_combo.currentTextChanged.connect(self._selection_mode)
            toolbar.addWidget(QtWidgets.QLabel("Selectie: ")); toolbar.addWidget(self.selection_combo)
            for label,slot in (("Fit",lambda:self.viewer.backend.fit_all()),("Iso",lambda:self.viewer.backend.set_isometric_view()),("Boven",lambda:self.viewer.backend.set_top_view()),("Voor",lambda:self.viewer.backend.set_front_view())):
                action=toolbar.addAction(label); action.triggered.connect(slot)
            self.validate_action=toolbar.addAction("Vergelijk exact"); self.validate_action.triggered.connect(self._validate)
            layout.addWidget(toolbar)

            splitter=QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal); layout.addWidget(splitter,1)
            left=QtWidgets.QWidget(); left_layout=QtWidgets.QVBoxLayout(left); left_layout.setContentsMargins(0,0,0,0)
            self.tabs=QtWidgets.QTabWidget(); left_layout.addWidget(self.tabs)
            self.subshape_table=QtWidgets.QTableWidget(0,5); self.subshape_table.setHorizontalHeaderLabels(["ID","Type","Geometrie","Maat","Bewijs"])
            self.subshape_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows); self.subshape_table.itemSelectionChanged.connect(self._table_selection)
            self.tabs.addTab(self.subshape_table,"Geometrie")
            self.feature_table=QtWidgets.QTableWidget(0,6); self.feature_table.setHorizontalHeaderLabels(["Feature","Type","Ø/R","Diepte","Confidence","Subshapes"])
            self.tabs.addTab(self.feature_table,"Bewerkingen")
            self.reference_table=QtWidgets.QTableWidget(0,4); self.reference_table.setHorizontalHeaderLabels(["Rol","Face ID","Bevestigd","Herkomst"])
            self.tabs.addTab(self.reference_table,"Assen / referentiezijden")
            self.general=QtWidgets.QPlainTextEdit(); self.general.setReadOnly(True); self.tabs.addTab(self.general,"Algemeen")
            self.provenance=QtWidgets.QPlainTextEdit(); self.provenance.setReadOnly(True); self.tabs.addTab(self.provenance,"Herkomst / validatie")
            splitter.addWidget(left)

            right=QtWidgets.QWidget(); right_layout=QtWidgets.QVBoxLayout(right); right_layout.setContentsMargins(0,0,0,0)
            self.viewer=ExactOcctWidget(); self.viewer.subshape_picked.connect(self._picked); right_layout.addWidget(self.viewer,1)
            self.status=QtWidgets.QLabel("Bron grijs · canonical cyaan · productie blijft geblokkeerd tot validatie")
            self.status.setObjectName("cwsExactStatus"); right_layout.addWidget(self.status)
            splitter.addWidget(right); splitter.setStretchFactor(0,0); splitter.setStretchFactor(1,1); splitter.setSizes([430,900])

        def _populate(self)->None:
            snapshot=self.service.source.snapshot
            self.subshape_table.setRowCount(len(snapshot.subshapes))
            for row,item in enumerate(snapshot.subshapes):
                values=(item.stable_id,item.kind.value,item.geometry_type,f"{item.measure:.4f}","Exact BREP")
                for col,value in enumerate(values): self.subshape_table.setItem(row,col,QtWidgets.QTableWidgetItem(str(value)))
            self.subshape_table.resizeColumnsToContents()
            self.feature_table.setRowCount(len(snapshot.features))
            for row,item in enumerate(snapshot.features):
                values=(item.feature_id,item.feature_type,item.diameter or item.radius or "",item.depth or "",f"{item.confidence:.0%}",", ".join(item.subshape_ids))
                for col,value in enumerate(values): self.feature_table.setItem(row,col,QtWidgets.QTableWidgetItem(str(value)))
            self.feature_table.resizeColumnsToContents()
            self.reference_table.setRowCount(len(snapshot.reference_faces))
            for row,item in enumerate(snapshot.reference_faces):
                values=(item.role,item.face_id,"Ja" if item.confirmed else "Nee",item.provenance)
                for col,value in enumerate(values): self.reference_table.setItem(row,col,QtWidgets.QTableWidgetItem(str(value)))
            p=snapshot.properties
            self.general.setPlainText(
                f"Onderdeel: {snapshot.part_id}\nBron: {snapshot.source_name}\nBREP hash: {snapshot.exact_geometry_hash}\n"
                f"Volume: {p.volume_mm3:.6f} mm³\nOppervlak: {p.surface_area_mm2:.6f} mm²\n"
                f"Hoofdmaten: {p.bounds.size.x:.3f} × {p.bounds.size.y:.3f} × {p.bounds.size.z:.3f} mm\n"
                f"Faces/Edges/Vertices: {p.face_count}/{p.edge_count}/{p.vertex_count}"
            )
            self.provenance.setPlainText("Exact source-BREP\nStable subshape IDs\nGeen displaymesh als productiewaarheid")

        def _selection_mode(self,text:str)->None:
            mapping={"Face":SubshapeKind.FACE,"Edge":SubshapeKind.EDGE,"Vertex":SubshapeKind.VERTEX}
            self.viewer.backend.set_selection_kind(mapping[text])

        def _table_selection(self)->None:
            rows=self.subshape_table.selectionModel().selectedRows()
            if rows:
                stable_id=self.subshape_table.item(rows[0].row(),0).text(); self.service.select_subshape(stable_id); self.viewer.backend.highlight(stable_id)

        def _picked(self,stable_id:str)->None:
            self.service.select_subshape(stable_id)
            for row in range(self.subshape_table.rowCount()):
                if self.subshape_table.item(row,0).text()==stable_id:
                    self.subshape_table.selectRow(row); break

        def _validate(self)->None:
            try:
                report=self.service.validate(); self.status.setText(f"Exact compare: {report.overall.value.upper()} · max Δ {max(report.source_to_canonical_max_mm,report.canonical_to_source_max_mm):.6f} mm")
            except Exception as exc:
                self.status.setText(f"Validatie geblokkeerd: {exc}")

else:
    class ExactOcctWidget:  # pragma: no cover
        def __init__(self,*_:Any,**__:Any)->None: require_qt()
    class ExactPartWorkbenchPanel:  # pragma: no cover
        def __init__(self,*_:Any,**__:Any)->None: require_qt()


__all__=["ExactOcctWidget","ExactPartWorkbenchPanel"]
