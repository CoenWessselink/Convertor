"""V15 T5 saved views, markups and issue-management panel."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.review import (
    MarkupKind,
    ReviewPriority,
    ReviewSeverity,
    ReviewStatus,
    V15ReviewWorkspaceService,
)
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class V15ReviewPanel(QtWidgets.QWidget):
        status_changed = QtCore.Signal(str)

        def __init__(
            self,
            viewer: Any,
            service: V15ReviewWorkspaceService,
            parent: Any | None = None,
        ) -> None:
            super().__init__(parent)
            self.viewer = viewer
            self.controller = viewer.controller
            self.service = service
            self._last_pick: Any | None = None
            self._build_ui()
            if hasattr(viewer, "pick_result"):
                viewer.pick_result.connect(self._remember_pick)
            self.refresh()

        def _build_ui(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(6, 6, 6, 6)
            root.setSpacing(6)
            self.tabs = QtWidgets.QTabWidget()
            root.addWidget(self.tabs, 1)

            self.tabs.addTab(self._build_views_tab(), "Views")
            self.tabs.addTab(self._build_issues_tab(), "Issues / ToDos")
            self.tabs.addTab(self._build_markups_tab(), "Markups")

            io = QtWidgets.QHBoxLayout()
            self.save_store = QtWidgets.QPushButton("Review opslaan")
            self.reload_store = QtWidgets.QPushButton("Heropen")
            self.export_package = QtWidgets.QPushButton("Exporteer .cwsreview")
            self.export_bcf = QtWidgets.QPushButton("Exporteer BCF 2.1")
            io.addWidget(self.save_store)
            io.addWidget(self.reload_store)
            io.addWidget(self.export_package)
            io.addWidget(self.export_bcf)
            io.addStretch(1)
            root.addLayout(io)
            self.summary = QtWidgets.QLabel()
            self.summary.setWordWrap(True)
            self.summary.setObjectName("cwsMuted")
            root.addWidget(self.summary)

            self.save_store.clicked.connect(self._save)
            self.reload_store.clicked.connect(self._reload)
            self.export_package.clicked.connect(self._export_package)
            self.export_bcf.clicked.connect(self._export_bcf)

        def _build_views_tab(self) -> Any:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.setContentsMargins(0, 5, 0, 0)
            self.views = QtWidgets.QTreeWidget()
            self.views.setHeaderLabels(["Naam", "Viewpoint ID", "Scene", "Owner"])
            self.views.setRootIsDecorated(False)
            self.views.itemDoubleClicked.connect(lambda *_: self._activate_view())
            layout.addWidget(self.views, 1)
            row = QtWidgets.QHBoxLayout()
            self.new_view = QtWidgets.QPushButton("Huidige view opslaan")
            self.apply_view = QtWidgets.QPushButton("View activeren")
            self.delete_view = QtWidgets.QPushButton("View verwijderen")
            row.addWidget(self.new_view)
            row.addWidget(self.apply_view)
            row.addWidget(self.delete_view)
            row.addStretch(1)
            layout.addLayout(row)
            note = QtWidgets.QLabel(
                "Saved Views zijn zelfstandige reviewobjecten. Een issue kan ernaar verwijzen, maar bezit de view niet."
            )
            note.setWordWrap(True)
            note.setObjectName("cwsMuted")
            layout.addWidget(note)
            self.new_view.clicked.connect(self._new_view)
            self.apply_view.clicked.connect(self._activate_view)
            self.delete_view.clicked.connect(self._delete_view)
            return widget

        def _build_issues_tab(self) -> Any:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.setContentsMargins(0, 5, 0, 0)
            self.issues = QtWidgets.QTreeWidget()
            self.issues.setHeaderLabels(
                ["Titel", "Status", "Prioriteit", "Assignee", "Due", "Referenties"]
            )
            self.issues.setRootIsDecorated(False)
            layout.addWidget(self.issues, 1)

            row1 = QtWidgets.QHBoxLayout()
            self.new_issue = QtWidgets.QPushButton("Nieuw uit selectie")
            self.status_issue = QtWidgets.QPushButton("Status")
            self.priority_issue = QtWidgets.QPushButton("Prioriteit")
            self.assign_issue = QtWidgets.QPushButton("Toewijzen")
            self.due_issue = QtWidgets.QPushButton("Due date")
            for button in (
                self.new_issue,
                self.status_issue,
                self.priority_issue,
                self.assign_issue,
                self.due_issue,
            ):
                row1.addWidget(button)
            row1.addStretch(1)
            layout.addLayout(row1)

            row2 = QtWidgets.QHBoxLayout()
            self.comment_issue = QtWidgets.QPushButton("Opmerking")
            self.attach_issue = QtWidgets.QPushButton("Bijlage")
            self.link_view = QtWidgets.QPushButton("Koppel geselecteerde view")
            self.unlink_view = QtWidgets.QPushButton("Ontkoppel view")
            self.delete_issue = QtWidgets.QPushButton("Issue verwijderen")
            for button in (
                self.comment_issue,
                self.attach_issue,
                self.link_view,
                self.unlink_view,
                self.delete_issue,
            ):
                row2.addWidget(button)
            row2.addStretch(1)
            layout.addLayout(row2)

            self.issue_detail = QtWidgets.QPlainTextEdit()
            self.issue_detail.setReadOnly(True)
            self.issue_detail.setMaximumHeight(125)
            layout.addWidget(self.issue_detail)

            self.issues.itemSelectionChanged.connect(self._show_issue_detail)
            self.new_issue.clicked.connect(self._new_issue)
            self.status_issue.clicked.connect(self._set_status)
            self.priority_issue.clicked.connect(self._set_priority)
            self.assign_issue.clicked.connect(self._assign)
            self.due_issue.clicked.connect(self._due_date)
            self.comment_issue.clicked.connect(self._comment)
            self.attach_issue.clicked.connect(self._attach)
            self.link_view.clicked.connect(self._link_selected_view)
            self.unlink_view.clicked.connect(self._unlink_view)
            self.delete_issue.clicked.connect(self._delete_issue)
            return widget

        def _build_markups_tab(self) -> Any:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.setContentsMargins(0, 5, 0, 0)
            self.markups = QtWidgets.QTreeWidget()
            self.markups.setHeaderLabels(["Type", "Tekst", "Anchor", "Bewijs", "Status"])
            self.markups.setRootIsDecorated(False)
            layout.addWidget(self.markups, 1)
            row = QtWidgets.QHBoxLayout()
            self.add_text = QtWidgets.QPushButton("Tekst")
            self.add_arrow = QtWidgets.QPushButton("Pijl")
            self.add_cloud = QtWidgets.QPushButton("Cloud")
            self.add_freehand = QtWidgets.QPushButton("Freehand-record")
            self.delete_markup = QtWidgets.QPushButton("Markup verwijderen")
            for button in (
                self.add_text,
                self.add_arrow,
                self.add_cloud,
                self.add_freehand,
                self.delete_markup,
            ):
                row.addWidget(button)
            row.addStretch(1)
            layout.addLayout(row)
            self.pick_hint = QtWidgets.QLabel(
                "Klik eerst een objectpunt in de 3D Viewer. Markups zijn reviewdata en wijzigen geen staalgeometrie."
            )
            self.pick_hint.setWordWrap(True)
            self.pick_hint.setObjectName("cwsMuted")
            layout.addWidget(self.pick_hint)
            self.add_text.clicked.connect(lambda: self._new_markup(MarkupKind.TEXT))
            self.add_arrow.clicked.connect(lambda: self._new_markup(MarkupKind.ARROW))
            self.add_cloud.clicked.connect(lambda: self._new_markup(MarkupKind.CLOUD))
            self.add_freehand.clicked.connect(lambda: self._new_markup(MarkupKind.FREEHAND))
            self.delete_markup.clicked.connect(self._delete_markup)
            return widget

        def _remember_pick(self, pick: Any) -> None:
            self._last_pick = pick
            try:
                point = pick.world_point
                self.pick_hint.setText(
                    f"Laatste pick: {pick.entity_id} · X {point.x:.2f} Y {point.y:.2f} Z {point.z:.2f} mm"
                )
            except Exception:
                pass

        @staticmethod
        def _actor() -> str:
            return "CWS Reviewer"

        def _persist_quiet(self) -> None:
            if self.service.store_path is None:
                return
            try:
                self.service.save()
            except Exception as exc:
                self.status_changed.emit(f"Review kon niet automatisch opslaan: {type(exc).__name__}: {exc}")

        def _selected_view_id(self) -> str | None:
            items = self.views.selectedItems()
            if not items:
                return None
            value = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
            return str(value) if value else None

        def _selected_issue_id(self) -> str | None:
            items = self.issues.selectedItems()
            if not items:
                return None
            value = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
            return str(value) if value else None

        def _selected_markup_id(self) -> str | None:
            items = self.markups.selectedItems()
            if not items:
                return None
            value = items[0].data(0, QtCore.Qt.ItemDataRole.UserRole)
            return str(value) if value else None

        def _new_view(self) -> None:
            name, ok = QtWidgets.QInputDialog.getText(self, "Saved View", "Naam:")
            if not ok or not str(name).strip():
                return
            self.service.capture_view(str(name).strip(), owner=self._actor())
            self._persist_quiet()
            self.refresh()
            self.status_changed.emit("Saved View opgeslagen")

        def _activate_view(self) -> None:
            viewpoint_id = self._selected_view_id()
            if not viewpoint_id:
                return
            viewpoint = next(
                (item for item in self.controller.list_viewpoints() if item.viewpoint_id == viewpoint_id),
                None,
            )
            if viewpoint is None:
                return
            try:
                self.controller.activate_viewpoint(viewpoint, allow_scene_mismatch=True)
                self.status_changed.emit(f"View geactiveerd: {viewpoint.name}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Saved View", f"{type(exc).__name__}: {exc}")

        def _delete_view(self) -> None:
            viewpoint_id = self._selected_view_id()
            if viewpoint_id:
                self.service.delete_view(viewpoint_id)
                self._persist_quiet()
                self.refresh()

        def _new_issue(self) -> None:
            title, ok = QtWidgets.QInputDialog.getText(self, "Nieuw issue", "Titel:")
            if not ok or not str(title).strip():
                return
            description, _ = QtWidgets.QInputDialog.getMultiLineText(
                self, "Nieuw issue", "Omschrijving:", ""
            )
            issue = self.service.create_issue(
                str(title).strip(),
                description=str(description),
                severity=ReviewSeverity.INFO,
                priority=ReviewPriority.NORMAL,
                created_by=self._actor(),
            )
            self._persist_quiet()
            self.refresh(select_issue=issue.issue_id)

        def _set_status(self) -> None:
            issue_id = self._selected_issue_id()
            if not issue_id:
                return
            values = [item.value for item in ReviewStatus]
            value, ok = QtWidgets.QInputDialog.getItem(
                self, "Issue status", "Status:", values, editable=False
            )
            if ok:
                self.service.set_status(issue_id, str(value), actor=self._actor())
                self._persist_quiet(); self.refresh(select_issue=issue_id)

        def _set_priority(self) -> None:
            issue_id = self._selected_issue_id()
            if not issue_id:
                return
            values = [item.value for item in ReviewPriority]
            value, ok = QtWidgets.QInputDialog.getItem(
                self, "Issue prioriteit", "Prioriteit:", values, editable=False
            )
            if ok:
                self.service.set_priority(issue_id, str(value), actor=self._actor())
                self._persist_quiet(); self.refresh(select_issue=issue_id)

        def _assign(self) -> None:
            issue_id = self._selected_issue_id()
            if not issue_id:
                return
            current = self.service.issue(issue_id).assignee
            value, ok = QtWidgets.QInputDialog.getText(
                self, "Issue toewijzen", "Assignee:", text=current
            )
            if ok:
                self.service.assign(issue_id, str(value), actor=self._actor())
                self._persist_quiet(); self.refresh(select_issue=issue_id)

        def _due_date(self) -> None:
            issue_id = self._selected_issue_id()
            if not issue_id:
                return
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Due date")
            layout = QtWidgets.QVBoxLayout(dialog)
            edit = QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime().addDays(7))
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd HH:mm")
            layout.addWidget(edit)
            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
                | QtWidgets.QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                due = edit.dateTime().toUTC().toString(QtCore.Qt.DateFormat.ISODate)
                self.service.set_due_date(issue_id, due, actor=self._actor())
                self._persist_quiet(); self.refresh(select_issue=issue_id)

        def _comment(self) -> None:
            issue_id = self._selected_issue_id()
            if not issue_id:
                return
            text, ok = QtWidgets.QInputDialog.getMultiLineText(
                self, "Opmerking toevoegen", "Opmerking:", ""
            )
            if ok and str(text).strip():
                self.service.add_comment(issue_id, self._actor(), str(text).strip())
                self._persist_quiet(); self.refresh(select_issue=issue_id)

        def _attach(self) -> None:
            issue_id = self._selected_issue_id()
            if not issue_id:
                return
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Bijlage kiezen")
            if not path:
                return
            try:
                self.service.add_attachment(issue_id, path, actor=self._actor())
                self._persist_quiet(); self.refresh(select_issue=issue_id)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Bijlage", f"{type(exc).__name__}: {exc}")

        def _link_selected_view(self) -> None:
            issue_id = self._selected_issue_id()
            viewpoint_id = self._selected_view_id()
            if not issue_id:
                return
            if not viewpoint_id:
                QtWidgets.QMessageBox.information(
                    self,
                    "View koppelen",
                    "Selecteer eerst een Saved View in het tabblad Views.",
                )
                return
            self.service.link_viewpoint(issue_id, viewpoint_id, actor=self._actor())
            self._persist_quiet(); self.refresh(select_issue=issue_id)

        def _unlink_view(self) -> None:
            issue_id = self._selected_issue_id()
            if issue_id:
                self.service.link_viewpoint(issue_id, None, actor=self._actor())
                self._persist_quiet(); self.refresh(select_issue=issue_id)

        def _delete_issue(self) -> None:
            issue_id = self._selected_issue_id()
            if issue_id:
                self.service.delete_issue(issue_id)
                self._persist_quiet(); self.refresh()

        def _new_markup(self, kind: MarkupKind) -> None:
            if self._last_pick is None:
                QtWidgets.QMessageBox.information(
                    self, "Markup", "Klik eerst een punt/object in de 3D Viewer."
                )
                return
            text, ok = QtWidgets.QInputDialog.getText(
                self, f"{kind.value} markup", "Tekst / label:"
            )
            if not ok:
                return
            markup = self.service.create_markup_from_pick(
                self._last_pick,
                kind=kind,
                text=str(text),
                created_by=self._actor(),
            )
            self._persist_quiet(); self.refresh(select_markup=markup.markup_id)

        def _delete_markup(self) -> None:
            markup_id = self._selected_markup_id()
            if markup_id:
                self.service.delete_markup(markup_id)
                self._persist_quiet(); self.refresh()

        def _show_issue_detail(self) -> None:
            issue_id = self._selected_issue_id()
            if not issue_id:
                self.issue_detail.clear(); return
            issue = self.service.issue(issue_id)
            health = self.service.reference_health(issue_id)
            lines = [
                f"{issue.issue_id}",
                issue.description or "(geen omschrijving)",
                f"Entities: {', '.join(issue.linked_entity_ids) or '-'}",
                f"Viewpoint: {issue.viewpoint_id or '-'}",
                f"Markups: {', '.join(issue.markup_ids) or '-'}",
                f"Comments: {len(issue.comments)} · Attachments: {len(issue.attachments)}",
                f"Reference health: {health.state.value}",
            ]
            if health.is_stale:
                lines.append(f"Stale details: {health.to_dict()}")
            self.issue_detail.setPlainText("\n".join(lines))

        def _save(self) -> None:
            try:
                target = self.service.save()
                self.status_changed.emit(f"Review opgeslagen: {target.name}")
                self.refresh()
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Review opslaan", f"{type(exc).__name__}: {exc}")

        def _reload(self) -> None:
            try:
                report = self.service.load()
                self.status_changed.emit(
                    f"Review heropend · {report['issues']} issues · {report['stale_issues']} stale"
                )
                self.refresh()
            except FileNotFoundError:
                QtWidgets.QMessageBox.information(self, "Review heropenen", "Nog geen opgeslagen review sidecar gevonden.")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Review heropenen", f"{type(exc).__name__}: {exc}")

        def _export_package(self) -> None:
            default = "review.cwsreview"
            if self.service.store_path is not None:
                default = str(self.service.store_path.with_suffix(".cwsreview"))
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Exporteer reviewpakket", default, "CWS Review (*.cwsreview)"
            )
            if not path:
                return
            try:
                assets_root = (
                    self.service.store_path.parent
                    if self.service.store_path is not None
                    else Path(path).parent
                )
                output = self.service.export_package(path, assets_root=assets_root)
                self.status_changed.emit(f"Reviewpakket geëxporteerd: {output.name}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "Review export", f"{type(exc).__name__}: {exc}")

        def _export_bcf(self) -> None:
            default = "review.bcfzip"
            if self.service.store_path is not None:
                default = str(self.service.store_path.with_suffix(".bcfzip"))
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Exporteer buildingSMART BCF 2.1", default, "BCF 2.1 (*.bcfzip *.bcf)"
            )
            if not path:
                return
            try:
                output = self.service.export_bcf(path)
                self.status_changed.emit(f"BCF 2.1 XSD-gevalideerd: {output.name}")
            except Exception as exc:
                QtWidgets.QMessageBox.critical(self, "BCF export", f"{type(exc).__name__}: {exc}")

        def refresh(
            self,
            *,
            select_issue: str | None = None,
            select_markup: str | None = None,
        ) -> None:
            self.views.clear()
            current_scene = self.controller.index.scene.scene_hash
            for viewpoint in self.controller.list_viewpoints():
                item = QtWidgets.QTreeWidgetItem(
                    [
                        viewpoint.name,
                        viewpoint.viewpoint_id,
                        "actueel" if viewpoint.scene_hash == current_scene else "vorige revisie",
                        viewpoint.owner,
                    ]
                )
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, viewpoint.viewpoint_id)
                self.views.addTopLevelItem(item)

            self.issues.clear()
            issue_to_select = None
            for issue in self.service.list_issues():
                health = self.service.reference_health(issue.issue_id)
                due = issue.due_date_utc or ""
                if len(due) > 16:
                    due = due[:16].replace("T", " ")
                item = QtWidgets.QTreeWidgetItem(
                    [
                        issue.title,
                        issue.status,
                        issue.priority,
                        issue.assignee,
                        due,
                        "STALE" if health.is_stale else health.state.value,
                    ]
                )
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, issue.issue_id)
                self.issues.addTopLevelItem(item)
                if issue.issue_id == select_issue:
                    issue_to_select = item
            if issue_to_select is not None:
                self.issues.setCurrentItem(issue_to_select)

            self.markups.clear()
            markup_to_select = None
            for markup in self.service.list_markups():
                anchor = markup.anchors[0] if markup.anchors else None
                item = QtWidgets.QTreeWidgetItem(
                    [
                        markup.kind,
                        markup.text,
                        (anchor.entity_id if anchor else "") or "",
                        (anchor.evidence if anchor else "") or "",
                        "stale" if self.service._markup_is_stale(markup) else markup.status,
                    ]
                )
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, markup.markup_id)
                self.markups.addTopLevelItem(item)
                if markup.markup_id == select_markup:
                    markup_to_select = item
            if markup_to_select is not None:
                self.markups.setCurrentItem(markup_to_select)

            stale = sum(1 for item in self.service.reference_health_all() if item.is_stale)
            self.summary.setText(
                f"Saved Views {len(self.controller.list_viewpoints())} · Issues {len(self.service.issues)} · "
                f"Markups {len(self.service.markups)} · Stale issues {stale} · review hash {self.service.review_hash[:12]}"
            )
            self._show_issue_detail()

else:

    class V15ReviewPanel:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["V15ReviewPanel"]
