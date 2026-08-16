"""V15 T6 coordination panel for assemblies, compare, clash and sequence."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_convertor.project.storage import ProjectStore
from cws_viewer.coordination import SequenceKind, V15CoordinationService
from cws_viewer.model_control import GeometryConfidence
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.revision_compare import RevisionComparePanel


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class V15CoordinationPanel(QtWidgets.QWidget):
        status_changed = QtCore.Signal(str)

        def __init__(
            self,
            viewer: Any,
            project: Any,
            *,
            review_service: Any | None = None,
            parent: Any | None = None,
        ) -> None:
            super().__init__(parent)
            self.viewer = viewer
            self.controller = viewer.controller
            self.project = project
            self.review_service = review_service
            self.service = V15CoordinationService(self.controller, project)
            self._compare_panel: Any | None = None
            self._active_plan: Any | None = None
            self._build_ui()
            self.refresh_assemblies()
            self.refresh_sequence_summary()

        def _build_ui(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(6, 6, 6, 6)
            root.setSpacing(6)
            self.tabs = QtWidgets.QTabWidget()
            root.addWidget(self.tabs, 1)
            self.tabs.addTab(self._build_assembly_tab(), "Assemblies")
            self.tabs.addTab(self._build_compare_tab(), "Compare")
            self.tabs.addTab(self._build_clash_tab(), "Clash / preflight")
            self.tabs.addTab(self._build_sequence_tab(), "Sequence")
            self.footer = QtWidgets.QLabel(
                "T6 coördinatie is viewer/review-state. Approximate clash evidence wordt nooit opgewaardeerd tot exact en sequence is geen machineplanning."
            )
            self.footer.setWordWrap(True)
            self.footer.setObjectName("cwsMuted")
            root.addWidget(self.footer)

        def _build_assembly_tab(self) -> Any:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.setContentsMargins(0, 5, 0, 0)
            self.assemblies = QtWidgets.QTreeWidget()
            self.assemblies.setHeaderLabels(
                ["Assembly / merk", "Main part", "Secondair", "Inkoop", "Child assemblies"]
            )
            self.assemblies.itemDoubleClicked.connect(lambda *_: self._isolate_assembly())
            layout.addWidget(self.assemblies, 1)
            row = QtWidgets.QHBoxLayout()
            self.select_assembly = QtWidgets.QPushButton("Selecteer assembly")
            self.isolate_assembly = QtWidgets.QPushButton("Isoleer + fit")
            self.main_part = QtWidgets.QPushButton("Main part")
            self.secondary_parts = QtWidgets.QPushButton("Secundaire delen")
            self.parent_assembly = QtWidgets.QPushButton("Naar parent")
            for button in (
                self.select_assembly,
                self.isolate_assembly,
                self.main_part,
                self.secondary_parts,
                self.parent_assembly,
            ):
                row.addWidget(button)
            row.addStretch(1)
            layout.addLayout(row)
            self.assembly_detail = QtWidgets.QPlainTextEdit()
            self.assembly_detail.setReadOnly(True)
            self.assembly_detail.setMaximumHeight(125)
            layout.addWidget(self.assembly_detail)
            self.assemblies.itemSelectionChanged.connect(self._assembly_detail_changed)
            self.select_assembly.clicked.connect(self._select_assembly)
            self.isolate_assembly.clicked.connect(self._isolate_assembly)
            self.main_part.clicked.connect(self._select_main)
            self.secondary_parts.clicked.connect(self._select_secondary)
            self.parent_assembly.clicked.connect(self._go_parent)
            return widget

        def _build_compare_tab(self) -> Any:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.setContentsMargins(0, 5, 0, 0)
            row = QtWidgets.QHBoxLayout()
            self.compare_open = QtWidgets.QPushButton("Open vorige .cwscproj en vergelijk")
            self.compare_clear = QtWidgets.QPushButton("Vergelijking wissen")
            row.addWidget(self.compare_open)
            row.addWidget(self.compare_clear)
            row.addStretch(1)
            layout.addLayout(row)
            self.compare_summary = QtWidgets.QLabel("Nog geen revisievergelijking geladen.")
            self.compare_summary.setWordWrap(True)
            layout.addWidget(self.compare_summary)
            self.compare_host = QtWidgets.QStackedWidget()
            self.compare_empty = QtWidgets.QLabel(
                "Selecteer een eerder CWS-projectpakket. De bestaande canonical revision comparator bepaalt stable-ID/correspondence en manufacturing impact."
            )
            self.compare_empty.setWordWrap(True)
            self.compare_host.addWidget(self.compare_empty)
            layout.addWidget(self.compare_host, 1)
            self.compare_open.clicked.connect(self._compare_previous)
            self.compare_clear.clicked.connect(self._clear_compare)
            return widget

        def _build_clash_tab(self) -> Any:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.setContentsMargins(0, 5, 0, 0)
            row = QtWidgets.QHBoxLayout()
            self.scan_all = QtWidgets.QPushButton("Scan zichtbaar project")
            self.scan_selected = QtWidgets.QPushButton("Scan selectie")
            self.clash_to_issue = QtWidgets.QPushButton("Maak issue van clash")
            row.addWidget(self.scan_all)
            row.addWidget(self.scan_selected)
            row.addWidget(self.clash_to_issue)
            row.addStretch(1)
            layout.addLayout(row)
            self.clash_summary = QtWidgets.QLabel("Nog geen clash/preflight scan uitgevoerd.")
            self.clash_summary.setWordWrap(True)
            layout.addWidget(self.clash_summary)
            self.clashes = QtWidgets.QTreeWidget()
            self.clashes.setHeaderLabels(
                ["ID", "A", "B", "Categorie", "Severity", "Confidence", "Minimum afstand", "Evidence"]
            )
            self.clashes.setRootIsDecorated(False)
            self.clashes.itemDoubleClicked.connect(lambda *_: self._select_clash())
            layout.addWidget(self.clashes, 1)
            self.scan_all.clicked.connect(lambda: self._run_clash_scan(selected_only=False))
            self.scan_selected.clicked.connect(lambda: self._run_clash_scan(selected_only=True))
            self.clash_to_issue.clicked.connect(self._clash_issue)
            return widget

        def _build_sequence_tab(self) -> Any:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.setContentsMargins(0, 5, 0, 0)
            row = QtWidgets.QHBoxLayout()
            self.sequence_kind = QtWidgets.QComboBox()
            self.sequence_kind.addItem("Bouwvolgorde", SequenceKind.CONSTRUCTION.value)
            self.sequence_kind.addItem("Montage / assembly", SequenceKind.ASSEMBLY.value)
            self.sequence_kind.addItem("Productie-review", SequenceKind.PRODUCTION_REVIEW.value)
            self.sequence_build = QtWidgets.QPushButton("Bouw sequence")
            self.sequence_reset = QtWidgets.QPushButton("Sequence uit")
            row.addWidget(QtWidgets.QLabel("Type:"))
            row.addWidget(self.sequence_kind)
            row.addWidget(self.sequence_build)
            row.addWidget(self.sequence_reset)
            row.addStretch(1)
            layout.addLayout(row)
            self.sequence_summary = QtWidgets.QLabel()
            self.sequence_summary.setWordWrap(True)
            layout.addWidget(self.sequence_summary)
            self.sequence_steps = QtWidgets.QTreeWidget()
            self.sequence_steps.setHeaderLabels(["Stap", "Naam", "Assembly", "Entities", "Mode"])
            self.sequence_steps.setRootIsDecorated(False)
            self.sequence_steps.itemDoubleClicked.connect(lambda *_: self._apply_sequence())
            layout.addWidget(self.sequence_steps, 1)
            controls = QtWidgets.QHBoxLayout()
            self.sequence_prev = QtWidgets.QPushButton("← Vorige")
            self.sequence_apply = QtWidgets.QPushButton("Toon stap")
            self.sequence_next = QtWidgets.QPushButton("Volgende →")
            controls.addWidget(self.sequence_prev)
            controls.addWidget(self.sequence_apply)
            controls.addWidget(self.sequence_next)
            controls.addStretch(1)
            layout.addLayout(controls)
            self.sequence_build.clicked.connect(self._build_sequence)
            self.sequence_reset.clicked.connect(self._reset_sequence)
            self.sequence_apply.clicked.connect(self._apply_sequence)
            self.sequence_prev.clicked.connect(lambda: self._move_sequence(-1))
            self.sequence_next.clicked.connect(lambda: self._move_sequence(1))
            return widget

        def _selected_assembly_id(self) -> str | None:
            items = self.assemblies.selectedItems()
            if not items:
                return None
            value = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
            return str(value) if value else None

        def refresh_assemblies(self) -> None:
            self.assemblies.clear()
            contexts = {item.assembly_id: item for item in self.service.assembly_contexts()}
            items: dict[str, Any] = {}
            for context in contexts.values():
                item = QtWidgets.QTreeWidgetItem(
                    [
                        context.assembly_mark or context.name or context.assembly_id,
                        context.main_part_id or "",
                        str(len(context.secondary_part_ids)),
                        str(len(context.purchased_item_ids)),
                        str(len(context.child_assembly_ids)),
                    ]
                )
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, context.assembly_id)
                items[context.assembly_id] = item
            for context in contexts.values():
                item = items[context.assembly_id]
                if context.parent_assembly_id and context.parent_assembly_id in items:
                    items[context.parent_assembly_id].addChild(item)
                else:
                    self.assemblies.addTopLevelItem(item)
            self.assemblies.expandToDepth(1)
            for column in range(self.assemblies.columnCount()):
                self.assemblies.resizeColumnToContents(column)
            self._assembly_detail_changed()

        def _assembly_detail_changed(self) -> None:
            assembly_id = self._selected_assembly_id()
            if not assembly_id:
                self.assembly_detail.clear()
                return
            context = self.service.assembly_context(assembly_id)
            recursive = self.service.assembly_entity_ids(assembly_id, recursive=True)
            lines = [
                f"{context.assembly_mark or context.name} · {context.assembly_id}",
                f"Parent: {context.parent_assembly_id or '-'} · children: {', '.join(context.child_assembly_ids) or '-'}",
                f"Main: {context.main_part_id or '-'} · secondary: {', '.join(context.secondary_part_ids) or '-'}",
                f"Purchased: {', '.join(context.purchased_item_ids) or '-'}",
                f"Fasteners: {', '.join(context.fastener_ids) or '-'} · welds: {', '.join(context.weld_ids) or '-'}",
                f"Recursive entity scope: {len(recursive)}",
            ]
            self.assembly_detail.setPlainText("\n".join(lines))

        def _select_assembly(self) -> None:
            assembly_id = self._selected_assembly_id()
            if assembly_id:
                nodes = self.service.select_assembly(assembly_id)
                self.status_changed.emit(f"Assemblyselectie: {len(nodes)} renderbare nodes")

        def _isolate_assembly(self) -> None:
            assembly_id = self._selected_assembly_id()
            if assembly_id:
                nodes = self.service.isolate_assembly(assembly_id)
                self.status_changed.emit(f"Assembly geïsoleerd: {len(nodes)} renderbare nodes")

        def _select_main(self) -> None:
            assembly_id = self._selected_assembly_id()
            if assembly_id:
                self.service.select_main_part(assembly_id)

        def _select_secondary(self) -> None:
            assembly_id = self._selected_assembly_id()
            if assembly_id:
                self.service.select_secondary_parts(assembly_id)

        def _go_parent(self) -> None:
            assembly_id = self._selected_assembly_id()
            if not assembly_id:
                return
            parent = self.service.assembly_context(assembly_id).parent_assembly_id
            if not parent:
                return
            iterator = QtWidgets.QTreeWidgetItemIterator(self.assemblies)
            while iterator.value():
                item = iterator.value()
                if str(item.data(0, QtCore.Qt.ItemDataRole.UserRole) or "") == parent:
                    self.assemblies.setCurrentItem(item)
                    item.setExpanded(True)
                    break
                iterator += 1

        def _compare_previous(self) -> None:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Open vorige CWS revisie",
                "",
                "CWS Project (*.cwscproj)",
            )
            if not path:
                return
            try:
                package = ProjectStore().open(path)
                evidence = self.service.compare_revisions(package.project)
                self._show_compare(evidence)
                self.status_changed.emit(
                    f"Revisievergelijking gereed · manifest {evidence.manifest_sha256[:12]}"
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Revisievergelijking", f"{type(exc).__name__}: {exc}"
                )

        def _show_compare(self, evidence: Any) -> None:
            if self._compare_panel is not None:
                self.compare_host.removeWidget(self._compare_panel)
                self._compare_panel.deleteLater()
            panel = RevisionComparePanel(evidence.report, self)
            panel.change_selected.connect(self.service.select_change)
            self.compare_host.addWidget(panel)
            self.compare_host.setCurrentWidget(panel)
            self._compare_panel = panel
            counts = evidence.report.counts
            self.compare_summary.setText(
                " · ".join(f"{key}: {value}" for key, value in counts.items() if value)
                + f" · evidence {evidence.manifest_sha256[:12]} · production safe: {'ja' if evidence.report.production_safe else 'nee'}"
            )

        def _clear_compare(self) -> None:
            if self._compare_panel is not None:
                self.compare_host.removeWidget(self._compare_panel)
                self._compare_panel.deleteLater()
                self._compare_panel = None
            self.compare_host.setCurrentWidget(self.compare_empty)
            self.compare_summary.setText("Nog geen revisievergelijking geladen.")

        def _selected_entity_ids(self) -> tuple[str, ...]:
            values: list[str] = []
            for node_id in self.controller.get_selection():
                try:
                    entity_id = str(self.controller.index.node(node_id).entity_id or "")
                except Exception:
                    entity_id = ""
                if entity_id:
                    values.append(entity_id)
            return tuple(dict.fromkeys(values))

        def _run_clash_scan(self, *, selected_only: bool) -> None:
            try:
                entities = self._selected_entity_ids() if selected_only else None
                if selected_only and len(entities or ()) < 2:
                    QtWidgets.QMessageBox.information(
                        self, "Clash scan", "Selecteer minimaal twee onderdelen."
                    )
                    return
                evidence = self.service.scan_clashes(entity_ids=entities)
                self._populate_clashes(evidence)
                self.status_changed.emit(
                    f"Clash/preflight gereed · {len(evidence.scan.records)} resultaten · evidence {evidence.manifest_sha256[:12]}"
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Clash / preflight", f"{type(exc).__name__}: {exc}"
                )

        def _populate_clashes(self, evidence: Any) -> None:
            scan = evidence.scan
            self.clashes.clear()
            for record in scan.records:
                distance = "" if record.minimum_distance_mm is None else f"{record.minimum_distance_mm:.3f} mm"
                item = QtWidgets.QTreeWidgetItem(
                    [
                        record.clash_id,
                        record.part_a_id,
                        record.part_b_id,
                        record.category,
                        record.severity,
                        record.geometry_confidence,
                        distance,
                        record.evidence,
                    ]
                )
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, record.clash_id)
                self.clashes.addTopLevelItem(item)
            stats = scan.stats
            self.clash_summary.setText(
                f"Objects {stats.object_count} · theoretische paren {stats.theoretical_pairs:,} · broad-phase kandidaten {stats.broad_phase_candidates:,} · "
                f"geëvalueerd {stats.evaluated_pairs:,} · resultaten {stats.results:,} · evidence {evidence.manifest_sha256[:12]}"
            )
            for column in range(self.clashes.columnCount()):
                self.clashes.resizeColumnToContents(column)

        def _selected_clash_id(self) -> str | None:
            items = self.clashes.selectedItems()
            if not items:
                return None
            value = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
            return str(value) if value else None

        def _select_clash(self) -> None:
            clash_id = self._selected_clash_id()
            if clash_id:
                self.service.select_clash(clash_id)

        def _clash_issue(self) -> None:
            clash_id = self._selected_clash_id()
            evidence = self.service.last_clash
            if not clash_id or evidence is None:
                return
            if self.review_service is None:
                QtWidgets.QMessageBox.information(
                    self, "Issue maken", "T5 reviewservice is niet gekoppeld."
                )
                return
            record = next(item for item in evidence.scan.records if item.clash_id == clash_id)
            issue = self.review_service.create_issue(
                f"Clash {record.part_a_id} ↔ {record.part_b_id}",
                description=(
                    f"Categorie: {record.category}\nGeometry confidence: {record.geometry_confidence}\n"
                    f"Evidence: {record.evidence}\nClash evidence manifest: {evidence.manifest_sha256}"
                ),
                created_by="CWS Model Control",
                linked_entity_ids=(record.part_a_id, record.part_b_id),
                linked_clash_ids=(record.clash_id,),
            )
            try:
                self.review_service.save()
            except Exception:
                pass
            self.status_changed.emit(f"Issue gemaakt: {issue.issue_id}")

        def _build_sequence(self) -> None:
            kind = SequenceKind(str(self.sequence_kind.currentData()))
            self._active_plan = self.service.build_sequence(kind)
            self.sequence_steps.clear()
            for step in self._active_plan.steps:
                item = QtWidgets.QTreeWidgetItem(
                    [
                        str(step.index + 1),
                        step.name,
                        ", ".join(step.assembly_ids),
                        str(len(step.entity_ids)),
                        "cumulatief" if self._active_plan.cumulative else "stap-isolatie",
                    ]
                )
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, step.index)
                self.sequence_steps.addTopLevelItem(item)
            if self._active_plan.steps:
                self.sequence_steps.setCurrentItem(self.sequence_steps.topLevelItem(0))
            self.refresh_sequence_summary()
            self.status_changed.emit(
                f"Sequence opgebouwd · {len(self._active_plan.steps)} stappen · {self._active_plan.manifest_sha256[:12]}"
            )

        def _selected_sequence_index(self) -> int | None:
            items = self.sequence_steps.selectedItems()
            if not items:
                return None
            value = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
            return None if value is None else int(value)

        def _apply_sequence(self) -> None:
            if self._active_plan is None:
                self._build_sequence()
            index = self._selected_sequence_index()
            if self._active_plan is None or index is None:
                return
            step = self.service.apply_sequence_step(self._active_plan, index)
            self.refresh_sequence_summary()
            self.status_changed.emit(f"Sequence stap {step.index + 1}: {step.name}")

        def _move_sequence(self, delta: int) -> None:
            if self._active_plan is None or not self._active_plan.steps:
                self._build_sequence()
            if self._active_plan is None or not self._active_plan.steps:
                return
            current = self._selected_sequence_index()
            target = 0 if current is None else max(0, min(len(self._active_plan.steps) - 1, current + int(delta)))
            self.sequence_steps.setCurrentItem(self.sequence_steps.topLevelItem(target))
            self._apply_sequence()

        def _reset_sequence(self) -> None:
            self.service.reset_sequence()
            self.refresh_sequence_summary()
            self.status_changed.emit("Sequenceweergave uit")

        def refresh_sequence_summary(self) -> None:
            plan, active = self.service.active_sequence
            if plan is None:
                self.sequence_summary.setText(
                    "Geen actieve sequence. Sequence is uitsluitend viewer/review-volgorde en geen machine-, zaag- of robotplanning."
                )
                return
            active_text = "-" if active is None else str(active + 1)
            self.sequence_summary.setText(
                f"{plan.kind.value} · {len(plan.steps)} stappen · actief {active_text} · "
                f"{'cumulatief' if plan.cumulative else 'stap-isolatie'} · manifest {plan.manifest_sha256[:12]} · viewer-only"
            )

else:

    class V15CoordinationPanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["V15CoordinationPanel"]
