"""Geometry completeness/status panel for the real project viewer.

A large project can contain thousands of nodes but only hundreds of unique
meshes because profile/plate geometry is intentionally instanced.  This panel
therefore reports the actual geometry-load evidence instead of treating
``node_count != mesh_count`` as a failure.
"""
from __future__ import annotations

from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class GeometryStatusPanel(QtWidgets.QWidget):
        geometry_selected = QtCore.Signal(str)

        def __init__(self, load_result: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.load_result = load_result
            self.setObjectName("cwsGeometryStatusPanel")
            self._build_ui()
            self.refresh()

        def _build_ui(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(6, 6, 6, 6)
            root.setSpacing(6)

            self.summary = QtWidgets.QLabel()
            self.summary.setWordWrap(True)
            root.addWidget(self.summary)

            filters = QtWidgets.QHBoxLayout()
            self.filter = QtWidgets.QComboBox()
            self.filter.addItem("Alles", "all")
            self.filter.addItem("Waarschuwing / proxy", "attention")
            self.filter.addItem("Alleen failed", "failed")
            self.search = QtWidgets.QLineEdit()
            self.search.setPlaceholderText("Geometry ID, source ID, fout of waarschuwing…")
            self.search.setClearButtonEnabled(True)
            filters.addWidget(QtWidgets.QLabel("Filter"))
            filters.addWidget(self.filter)
            filters.addWidget(self.search, 1)
            root.addLayout(filters)

            self.table = QtWidgets.QTableWidget(0, 8)
            self.table.setHorizontalHeaderLabels(
                ["Status", "Geometry ID", "Bronformaat", "Source entity", "Exactheid", "Vertices", "Triangles", "Melding"]
            )
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            self.table.setAlternatingRowColors(True)
            self.table.horizontalHeader().setStretchLastSection(True)
            self.table.itemDoubleClicked.connect(self._double_clicked)
            root.addWidget(self.table, 1)

            note = QtWidgets.QLabel(
                "READY/source_tessellation = bronmesh. PARTIAL/display_proxy = veilige viewerproxy; "
                "deze proxy is nooit productiegeometrie. Meerdere modelobjecten mogen dezelfde unieke mesh delen."
            )
            note.setWordWrap(True)
            note.setObjectName("cwsMuted")
            root.addWidget(note)

            self.filter.currentIndexChanged.connect(self.refresh)
            self.search.textChanged.connect(self.refresh)

        def _rows(self) -> list[dict[str, Any]]:
            values: list[dict[str, Any]] = []
            for result in tuple(getattr(self.load_result.geometry_report, "results", ()) or ()):
                mesh = getattr(result, "mesh", None)
                request = result.request
                values.append(
                    {
                        "status": str(getattr(result.status, "value", result.status)),
                        "geometry_id": request.geometry_id,
                        "source_format": request.source_format,
                        "source_entity_id": request.source_entity_id,
                        "exactness": "" if mesh is None else str(mesh.exactness),
                        "vertices": 0 if mesh is None else int(mesh.vertex_count),
                        "triangles": 0 if mesh is None else int(mesh.triangle_count),
                        "message": "; ".join(
                            value for value in [str(getattr(result, "error", "") or ""), *map(str, getattr(result, "warnings", ()) or ())] if value
                        ),
                    }
                )
            return values

        def refresh(self, *_: Any) -> None:
            report = self.load_result.geometry_report
            scene = self.load_result.scene
            repository = self.load_result.repository
            renderable = sum(1 for node in scene.nodes if getattr(node, "geometry_id", None))
            self.summary.setText(
                f"Projectnodes: {len(scene.nodes):,} · renderbare nodes: {renderable:,} · "
                f"unieke meshes: {len(repository):,} · READY: {report.ready_count:,} · "
                f"PARTIAL: {report.partial_count:,} · proxy: {report.proxy_count:,} · "
                f"FAILED: {report.failed_count:,} · cache hits: {report.cache_hit_count:,}"
            )
            mode = str(self.filter.currentData() or "all")
            query = self.search.text().strip().lower()
            rows = []
            for row in self._rows():
                if mode == "failed" and row["status"] != "failed":
                    continue
                if mode == "attention" and not (
                    row["status"] in {"partial", "failed"}
                    or row["exactness"] in {"display_proxy", "display_approximation"}
                    or row["message"]
                ):
                    continue
                haystack = " ".join(map(str, row.values())).lower()
                if query and query not in haystack:
                    continue
                rows.append(row)
            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                values = (
                    row["status"], row["geometry_id"], row["source_format"], row["source_entity_id"],
                    row["exactness"], f"{row['vertices']:,}", f"{row['triangles']:,}", row["message"],
                )
                for c, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(str(value))
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, row["geometry_id"])
                    self.table.setItem(r, c, item)
            self.table.resizeColumnsToContents()

        def _double_clicked(self, item: Any) -> None:
            geometry_id = str(item.data(QtCore.Qt.ItemDataRole.UserRole) or "")
            if geometry_id:
                self.geometry_selected.emit(geometry_id)

else:

    class GeometryStatusPanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["GeometryStatusPanel"]
