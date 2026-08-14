"""PySide6 revision/compare workspace for V7.

The panel is a review surface only.  It visualises deterministic compare reports
and exposes no production-release bypass.
"""
from __future__ import annotations

import json
from typing import Any

from cws_viewer.revisions.model import ChangeKind, ProjectRevisionCompareReport
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class RevisionComparePanel(QtWidgets.QWidget):  # type: ignore[misc]
        change_selected = QtCore.Signal(str)

        def __init__(self, report: ProjectRevisionCompareReport, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.report = report
            self.setObjectName("cwsRevisionComparePanel")
            self._build_ui()
            self._populate()

        def _build_ui(self) -> None:
            layout = QtWidgets.QVBoxLayout(self); layout.setContentsMargins(6, 6, 6, 6)
            header = QtWidgets.QHBoxLayout()
            self.title = QtWidgets.QLabel("Revisievergelijking")
            font = self.title.font(); font.setPointSize(max(11, font.pointSize()+2)); font.setBold(True); self.title.setFont(font)
            header.addWidget(self.title); header.addStretch(1)
            self.filter = QtWidgets.QComboBox(); self.filter.addItem("Alle wijzigingen", "all")
            for kind in ChangeKind: self.filter.addItem(kind.value.replace("_", " ").title(), kind.value)
            self.filter.currentIndexChanged.connect(self._apply_filter)
            header.addWidget(QtWidgets.QLabel("Filter:")); header.addWidget(self.filter)
            layout.addLayout(header)

            self.summary = QtWidgets.QLabel(); self.summary.setObjectName("cwsRevisionCompareSummary"); self.summary.setWordWrap(True)
            layout.addWidget(self.summary)
            splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal); layout.addWidget(splitter, 1)
            self.table = QtWidgets.QTableWidget(0, 11)
            self.table.setHorizontalHeaderLabels([
                "Status", "Oud ID", "Nieuw ID", "Positie", "Methode", "Confidence", "Impact", "Δ verplaatsing",
                "Planning gewijzigd", "Partproductie herbruikbaar", "Blokkades"
            ])
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setSortingEnabled(True)
            self.table.itemSelectionChanged.connect(self._selected)
            splitter.addWidget(self.table)
            self.details = QtWidgets.QPlainTextEdit(); self.details.setReadOnly(True); self.details.setObjectName("cwsRevisionCompareDetails")
            splitter.addWidget(self.details); splitter.setSizes([900, 420])
            self.status = QtWidgets.QLabel("Viewer toont vergelijking; production readiness blijft bij CWS-validatieservice")
            layout.addWidget(self.status)

        def _color(self, kind: ChangeKind):
            values = {
                ChangeKind.UNCHANGED: "#6b7280", ChangeKind.ADDED: "#22c55e", ChangeKind.REMOVED: "#ef4444",
                ChangeKind.MOVED: "#3b82f6", ChangeKind.CHANGED: "#f59e0b", ChangeKind.AMBIGUOUS: "#d946ef",
            }
            return QtGui.QColor(values[kind])

        def _populate(self) -> None:
            counts = self.report.counts
            self.summary.setText(
                f"Oud: {self.report.old_revision_id[:12]}…  →  Nieuw: {self.report.new_revision_id[:12]}…   |   "
                + " · ".join(f"{key}: {value}" for key, value in counts.items() if value)
                + ("   |   BLOKKADES: " + ", ".join(self.report.blocking_codes) if self.report.blocking_codes else "   |   Geen globale correspondence-blokkade")
            )
            self.table.setSortingEnabled(False); self.table.setRowCount(len(self.report.changes))
            for row, change in enumerate(self.report.changes):
                delta = "" if change.placement_delta is None else f"{change.placement_delta.translation_distance_mm:.3f} mm / {change.placement_delta.rotation_delta_deg:.3f}°"
                values = (
                    change.kind.value, change.old_entity_id or "", change.new_entity_id or "",
                    change.new_part_position or change.old_part_position, change.correspondence_method.value,
                    f"{change.confidence:.1%}", ", ".join(item.value for item in change.impacts), delta,
                    "Ja" if change.planning_changed else "Nee",
                    "Ja" if change.production_reuse_allowed else "Nee", ", ".join(change.blocking_codes),
                )
                for column, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(str(value)); item.setData(QtCore.Qt.ItemDataRole.UserRole, change.change_id)
                    if column == 0: item.setForeground(self._color(change.kind)); item.setFont(QtGui.QFont(item.font().family(), item.font().pointSize(), QtGui.QFont.Weight.Bold))
                    self.table.setItem(row, column, item)
            self.table.resizeColumnsToContents(); self.table.setSortingEnabled(True)
            self._apply_filter()

        def _apply_filter(self) -> None:
            selected = str(self.filter.currentData())
            for row, change in enumerate(self.report.changes):
                self.table.setRowHidden(row, selected != "all" and change.kind.value != selected)

        def _selected(self) -> None:
            rows = self.table.selectionModel().selectedRows()
            if not rows: return
            change_id = str(self.table.item(rows[0].row(), 0).data(QtCore.Qt.ItemDataRole.UserRole))
            change = next(item for item in self.report.changes if item.change_id == change_id)
            self.details.setPlainText(json.dumps(change.to_dict(), ensure_ascii=False, indent=2))
            self.change_selected.emit(change_id)


    class ExactComparePanel(QtWidgets.QWidget):  # type: ignore[misc]
        correspondence_selected = QtCore.Signal(str, str)

        def __init__(self, bundle, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.bundle = bundle
            self.setObjectName("cwsExactComparePanel")
            self._build_ui()
            self._populate()

        def _build_ui(self) -> None:
            layout = QtWidgets.QVBoxLayout(self); layout.setContentsMargins(6, 6, 6, 6)
            self.summary = QtWidgets.QLabel(); self.summary.setWordWrap(True); self.summary.setObjectName("cwsExactCompareSummary")
            layout.addWidget(self.summary)
            tabs = QtWidgets.QTabWidget(); layout.addWidget(tabs, 1)
            self.metrics = QtWidgets.QTableWidget(0, 6)
            self.metrics.setHorizontalHeaderLabels(["Meting", "Bron", "Doel", "Δ", "Tolerantie", "Status"]); self.metrics.setSortingEnabled(True)
            tabs.addTab(self.metrics, "Exacte metrics")
            self.correspondence = QtWidgets.QTableWidget(0, 8)
            self.correspondence.setHorizontalHeaderLabels(["Type", "Bron-ID", "Doel-ID", "Status", "Methode", "Confidence", "Score", "Bewijs"]); self.correspondence.setSortingEnabled(True)
            self.correspondence.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
            self.correspondence.itemSelectionChanged.connect(self._selected)
            tabs.addTab(self.correspondence, "Subshapes / features")
            self.details = QtWidgets.QPlainTextEdit(); self.details.setReadOnly(True); tabs.addTab(self.details, "Manifest / blokkades")
            self.status = QtWidgets.QLabel("Exacte vergelijking is reviewbewijs; productiepoort blijft deterministisch en format-specifiek.")
            layout.addWidget(self.status)

        def _populate(self) -> None:
            bundle = self.bundle
            deviation = bundle.deviation
            self.summary.setText(
                f"{bundle.relation.value}: {bundle.source_part_id} → {bundle.target_part_id} · "
                f"max Δ {deviation.maximum_mm:.6f} mm · p95 {deviation.p95_mm:.6f} mm · "
                f"correspondence matched {bundle.correspondence.matched_count}, ambiguous {bundle.correspondence.ambiguous_count}, "
                f"unmatched {bundle.correspondence.unmatched_count} · productie veilig: {'JA' if bundle.production_safe else 'NEE'}"
            )
            metrics = list(bundle.exact_report.metrics)
            self.metrics.setSortingEnabled(False); self.metrics.setRowCount(len(metrics))
            for row, metric in enumerate(metrics):
                values = (metric.name, metric.source_value, metric.canonical_value, metric.absolute_delta, metric.tolerance, metric.severity.value)
                for column, value in enumerate(values): self.metrics.setItem(row, column, QtWidgets.QTableWidgetItem(str(value)))
            self.metrics.resizeColumnsToContents(); self.metrics.setSortingEnabled(True)

            records = [("subshape", item) for item in bundle.correspondence.subshapes] + [("feature", item) for item in bundle.correspondence.features]
            self.correspondence.setSortingEnabled(False); self.correspondence.setRowCount(len(records))
            for row, (record_type, item) in enumerate(records):
                values = (record_type + ":" + item.kind, item.source_id or "", item.target_id or "", item.status.value, item.method.value, f"{item.confidence:.1%}", f"{item.score:.6f}", " | ".join(item.reasons))
                for column, value in enumerate(values):
                    cell = QtWidgets.QTableWidgetItem(str(value)); cell.setData(QtCore.Qt.ItemDataRole.UserRole, (item.source_id or "", item.target_id or "")); self.correspondence.setItem(row, column, cell)
            self.correspondence.resizeColumnsToContents(); self.correspondence.setSortingEnabled(True)
            self.details.setPlainText(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2))

        def _selected(self) -> None:
            rows = self.correspondence.selectionModel().selectedRows()
            if not rows: return
            value = self.correspondence.item(rows[0].row(), 0).data(QtCore.Qt.ItemDataRole.UserRole)
            source_id, target_id = value if isinstance(value, tuple) else ("", "")
            self.correspondence_selected.emit(str(source_id), str(target_id))

else:
    class RevisionComparePanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None: require_qt()

    class ExactComparePanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None: require_qt()


__all__ = ["RevisionComparePanel", "ExactComparePanel"]
