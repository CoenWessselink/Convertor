"""Phase 2 review UI: interactive markups, review snapshots and View Groups."""
from __future__ import annotations

from typing import Any

from cws_viewer.review.phase2_service import Phase2ReviewWorkspaceService
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
from cws_viewer.ui_qt.review_v15 import V15ReviewPanel


if qt_available():
    QtCore, _QtGui, QtWidgets = require_qt()

    class V15ReviewPanelPhase2(V15ReviewPanel):
        def __init__(
            self,
            viewer: Any,
            service: Phase2ReviewWorkspaceService,
            parent: Any | None = None,
        ) -> None:
            self._phase2_slideshow_index = 0
            self._phase2_slideshow_group_id: str | None = None
            super().__init__(viewer, service, parent)
            self.service: Phase2ReviewWorkspaceService = service
            self._phase2_slideshow = QtCore.QTimer(self)
            self._phase2_slideshow.timeout.connect(self._slideshow_step)
            self._upgrade_markup_tab()
            self._upgrade_views_tab()
            self._upgrade_issue_filter()
            if hasattr(viewer, "markup_gesture_completed"):
                viewer.markup_gesture_completed.connect(self._complete_markup_gesture)
            if hasattr(viewer, "markup_tool_state_changed"):
                viewer.markup_tool_state_changed.connect(self._markup_state_changed)
            self.refresh()

        # ------------------------------------------------------------------
        # Interactive markups
        def _disconnect(self, button: Any) -> None:
            try:
                button.clicked.disconnect()
            except Exception:
                pass

        def _upgrade_markup_tab(self) -> None:
            tab = self.tabs.widget(2)
            layout = tab.layout()
            row = layout.itemAt(1).layout() if layout is not None and layout.count() > 1 else None
            for button in (self.add_text, self.add_arrow, self.add_cloud, self.add_freehand):
                self._disconnect(button)
            self.add_text.setText("Tekst")
            self.add_arrow.setText("Pijl")
            self.add_cloud.setText("Cloud")
            self.add_freehand.setText("Freehand")
            self.add_line = QtWidgets.QPushButton("Lijn")
            self.stop_markup = QtWidgets.QPushButton("Stop markup")
            self.toggle_markup = QtWidgets.QPushButton("Toon / verberg")
            if row is not None:
                row.insertWidget(1, self.add_line)
                row.insertWidget(max(0, row.count() - 1), self.toggle_markup)
                row.insertWidget(max(0, row.count() - 1), self.stop_markup)
            self.add_text.clicked.connect(lambda: self._start_markup_tool("text"))
            self.add_line.clicked.connect(lambda: self._start_markup_tool("line"))
            self.add_arrow.clicked.connect(lambda: self._start_markup_tool("arrow"))
            self.add_cloud.clicked.connect(lambda: self._start_markup_tool("cloud"))
            self.add_freehand.clicked.connect(lambda: self._start_markup_tool("freehand"))
            self.stop_markup.clicked.connect(self._stop_markup_tool)
            self.toggle_markup.clicked.connect(self._toggle_markup_visibility)
            self.pick_hint.setText(
                "Phase 2: kies een markuptool en teken direct in de 3D Viewer. "
                "De bestaande part/assembly-selectie blijft behouden. Esc stopt het gereedschap."
            )

        def _start_markup_tool(self, kind: str) -> None:
            label = ""
            if kind == "text":
                label, ok = QtWidgets.QInputDialog.getText(
                    self, "Tekstmarkup", "Tekst:"
                )
                if not ok or not str(label).strip():
                    return
            else:
                label, ok = QtWidgets.QInputDialog.getText(
                    self,
                    f"{kind.capitalize()} markup",
                    "Label (optioneel):",
                )
                if not ok:
                    return
            try:
                self.viewer.start_markup_tool(kind, text=str(label).strip())
                self.tabs.setCurrentIndex(2)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Markup", f"{type(exc).__name__}: {exc}"
                )

        def _stop_markup_tool(self) -> None:
            if hasattr(self.viewer, "cancel_markup_tool"):
                self.viewer.cancel_markup_tool()

        def _markup_state_changed(self, kind: str) -> None:
            if kind:
                self.pick_hint.setText(
                    f"Markupgereedschap actief: {kind}. Selectie wordt niet gewijzigd · Esc stopt."
                )
            else:
                self.pick_hint.setText(
                    "Markupgereedschap uit. Kies Tekst, Lijn, Pijl, Cloud of Freehand."
                )

        def _complete_markup_gesture(self, gesture: Any) -> None:
            try:
                markup = self.service.create_markup_from_gesture(
                    dict(gesture), created_by=self._actor()
                )
                self._persist_quiet()
                self.refresh(select_markup=markup.markup_id)
                self.status_changed.emit(
                    f"{markup.kind.capitalize()} markup opgeslagen · {len(markup.world_points_mm)} punt(en)"
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Markup", f"{type(exc).__name__}: {exc}"
                )

        def _toggle_markup_visibility(self) -> None:
            markup_id = self._selected_markup_id()
            if not markup_id:
                return
            markup = self.service.markups[markup_id]
            self.service.set_markup_visible(markup_id, not markup.visible)
            self._persist_quiet()
            self.refresh(select_markup=markup_id)

        def _delete_markup(self) -> None:
            super()._delete_markup()
            self._sync_markup_overlay()

        def _sync_markup_overlay(self) -> None:
            if hasattr(self.viewer, "set_review_markups"):
                self.viewer.set_review_markups(self.service.list_markups())

        # ------------------------------------------------------------------
        # Saved Views + View Groups / slideshow
        def _upgrade_views_tab(self) -> None:
            tab = self.tabs.widget(0)
            layout = tab.layout()
            group = QtWidgets.QGroupBox("View Groups / slideshow")
            group_layout = QtWidgets.QVBoxLayout(group)
            self.view_groups = QtWidgets.QTreeWidget()
            self.view_groups.setHeaderLabels(["Groep / view", "Volgorde", "Interval"])
            self.view_groups.setRootIsDecorated(True)
            group_layout.addWidget(self.view_groups, 1)

            row = QtWidgets.QHBoxLayout()
            self.new_group = QtWidgets.QPushButton("Nieuwe groep")
            self.delete_group = QtWidgets.QPushButton("Groep verwijderen")
            self.add_view_group = QtWidgets.QPushButton("View toevoegen")
            self.remove_view_group = QtWidgets.QPushButton("Uit groep")
            self.move_view_up = QtWidgets.QPushButton("↑")
            self.move_view_down = QtWidgets.QPushButton("↓")
            self.play_group = QtWidgets.QPushButton("▶ Afspelen")
            self.stop_group = QtWidgets.QPushButton("■ Stop")
            self.group_interval = QtWidgets.QDoubleSpinBox()
            self.group_interval.setRange(0.25, 60.0)
            self.group_interval.setSingleStep(0.25)
            self.group_interval.setValue(1.5)
            self.group_interval.setSuffix(" s")
            for widget in (
                self.new_group,
                self.delete_group,
                self.add_view_group,
                self.remove_view_group,
                self.move_view_up,
                self.move_view_down,
                self.play_group,
                self.stop_group,
                self.group_interval,
            ):
                row.addWidget(widget)
            row.addStretch(1)
            group_layout.addLayout(row)
            if layout is not None:
                layout.addWidget(group)

            self.new_group.clicked.connect(self._new_view_group)
            self.delete_group.clicked.connect(self._delete_view_group)
            self.add_view_group.clicked.connect(self._add_selected_view_to_group)
            self.remove_view_group.clicked.connect(self._remove_selected_view_from_group)
            self.move_view_up.clicked.connect(lambda: self._move_group_view(-1))
            self.move_view_down.clicked.connect(lambda: self._move_group_view(1))
            self.play_group.clicked.connect(self._play_selected_group)
            self.stop_group.clicked.connect(self._stop_slideshow)
            self.group_interval.valueChanged.connect(self._set_group_interval)
            self.view_groups.itemDoubleClicked.connect(lambda *_: self._activate_group_tree_view())

        def _selected_group_and_view(self) -> tuple[str | None, str | None]:
            items = self.view_groups.selectedItems()
            if not items:
                return None, None
            item = items[0]
            group_id = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
            viewpoint_id = item.data(1, QtCore.Qt.ItemDataRole.UserRole)
            if viewpoint_id:
                return str(group_id), str(viewpoint_id)
            return (str(group_id), None) if group_id else (None, None)

        def _new_view_group(self) -> None:
            name, ok = QtWidgets.QInputDialog.getText(self, "View Group", "Naam:")
            if not ok or not str(name).strip():
                return
            group = self.service.create_view_group(str(name).strip(), created_by=self._actor())
            self._persist_quiet()
            self._refresh_view_groups(select_group=group.group_id)

        def _delete_view_group(self) -> None:
            group_id, _view = self._selected_group_and_view()
            if group_id:
                self.service.delete_view_group(group_id)
                self._persist_quiet()
                self._refresh_view_groups()

        def _add_selected_view_to_group(self) -> None:
            viewpoint_id = self._selected_view_id()
            group_id, _child = self._selected_group_and_view()
            if not viewpoint_id:
                QtWidgets.QMessageBox.information(
                    self, "View Group", "Selecteer eerst een Saved View bovenaan."
                )
                return
            if not group_id:
                groups = self.service.list_view_groups()
                if len(groups) == 1:
                    group_id = groups[0].group_id
                else:
                    QtWidgets.QMessageBox.information(
                        self, "View Group", "Selecteer ook een View Group."
                    )
                    return
            self.service.add_view_to_group(group_id, viewpoint_id)
            self._persist_quiet()
            self._refresh_view_groups(select_group=group_id, select_view=viewpoint_id)

        def _remove_selected_view_from_group(self) -> None:
            group_id, viewpoint_id = self._selected_group_and_view()
            if group_id and viewpoint_id:
                self.service.remove_view_from_group(group_id, viewpoint_id)
                self._persist_quiet()
                self._refresh_view_groups(select_group=group_id)

        def _move_group_view(self, offset: int) -> None:
            group_id, viewpoint_id = self._selected_group_and_view()
            if group_id and viewpoint_id:
                self.service.move_view_in_group(group_id, viewpoint_id, offset)
                self._persist_quiet()
                self._refresh_view_groups(select_group=group_id, select_view=viewpoint_id)

        def _set_group_interval(self, seconds: float) -> None:
            group_id, _viewpoint_id = self._selected_group_and_view()
            if group_id:
                try:
                    self.service.set_view_group_interval(group_id, float(seconds))
                    self._persist_quiet()
                except Exception:
                    pass

        def _activate_group_tree_view(self) -> None:
            _group_id, viewpoint_id = self._selected_group_and_view()
            if viewpoint_id:
                self._activate_phase2_view(viewpoint_id)

        def _activate_phase2_view(self, viewpoint_id: str) -> None:
            try:
                viewpoint = self.service.activate_saved_view(viewpoint_id)
                self._sync_markup_overlay()
                self.status_changed.emit(f"View geactiveerd: {viewpoint.name}")
                self.refresh()
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Saved View", f"{type(exc).__name__}: {exc}"
                )

        def _activate_view(self) -> None:
            viewpoint_id = self._selected_view_id()
            if viewpoint_id:
                self._activate_phase2_view(viewpoint_id)

        def _new_view(self) -> None:
            name, ok = QtWidgets.QInputDialog.getText(self, "Saved View", "Naam:")
            if not ok or not str(name).strip():
                return
            self.service.capture_view(str(name).strip(), owner=self._actor())
            self._persist_quiet()
            self.refresh()
            self.status_changed.emit(
                "Saved View opgeslagen inclusief markup- en measurement-zichtbaarheid"
            )

        def _delete_view(self) -> None:
            viewpoint_id = self._selected_view_id()
            if viewpoint_id:
                self.service.delete_view(viewpoint_id)
                self._persist_quiet()
                self.refresh()

        def _play_selected_group(self) -> None:
            group_id, _viewpoint_id = self._selected_group_and_view()
            if not group_id:
                return
            group = self.service.view_groups[group_id]
            if not group.viewpoint_ids:
                QtWidgets.QMessageBox.information(
                    self, "Slideshow", "Deze View Group bevat nog geen views."
                )
                return
            self._phase2_slideshow_group_id = group_id
            self._phase2_slideshow_index = 0
            self._phase2_slideshow.setInterval(max(250, int(group.interval_seconds * 1000.0)))
            self._slideshow_step()
            self._phase2_slideshow.start()
            self.status_changed.emit(f"Slideshow gestart: {group.name}")

        def _stop_slideshow(self) -> None:
            self._phase2_slideshow.stop()
            self._phase2_slideshow_group_id = None
            self.status_changed.emit("Slideshow gestopt")

        def _slideshow_step(self) -> None:
            group_id = self._phase2_slideshow_group_id
            if not group_id or group_id not in self.service.view_groups:
                self._stop_slideshow()
                return
            group = self.service.view_groups[group_id]
            if not group.viewpoint_ids:
                self._stop_slideshow()
                return
            index = self._phase2_slideshow_index % len(group.viewpoint_ids)
            viewpoint_id = group.viewpoint_ids[index]
            self._phase2_slideshow_index = index + 1
            try:
                self.service.activate_saved_view(viewpoint_id)
                self._sync_markup_overlay()
                self._select_view_row(viewpoint_id)
            except Exception as exc:
                self._stop_slideshow()
                self.status_changed.emit(
                    f"Slideshow gestopt: {type(exc).__name__}: {exc}"
                )

        def _select_view_row(self, viewpoint_id: str) -> None:
            for index in range(self.views.topLevelItemCount()):
                item = self.views.topLevelItem(index)
                value = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if str(value or "") == str(viewpoint_id):
                    self.views.setCurrentItem(item)
                    break

        def _refresh_view_groups(
            self,
            *,
            select_group: str | None = None,
            select_view: str | None = None,
        ) -> None:
            self.view_groups.clear()
            viewpoints = {
                item.viewpoint_id: item for item in self.controller.list_viewpoints()
            }
            target = None
            for group in self.service.list_view_groups():
                top = QtWidgets.QTreeWidgetItem(
                    [group.name, str(len(group.viewpoint_ids)), f"{group.interval_seconds:g} s"]
                )
                top.setData(0, QtCore.Qt.ItemDataRole.UserRole, group.group_id)
                self.view_groups.addTopLevelItem(top)
                for position, viewpoint_id in enumerate(group.viewpoint_ids, start=1):
                    viewpoint = viewpoints.get(viewpoint_id)
                    child = QtWidgets.QTreeWidgetItem(
                        [
                            viewpoint.name if viewpoint is not None else f"MISSING {viewpoint_id}",
                            str(position),
                            "",
                        ]
                    )
                    child.setData(0, QtCore.Qt.ItemDataRole.UserRole, group.group_id)
                    child.setData(1, QtCore.Qt.ItemDataRole.UserRole, viewpoint_id)
                    top.addChild(child)
                    if group.group_id == select_group and viewpoint_id == select_view:
                        target = child
                if group.group_id == select_group and select_view is None:
                    target = top
                top.setExpanded(True)
            if target is not None:
                self.view_groups.setCurrentItem(target)
            group_id, _viewpoint = self._selected_group_and_view()
            if group_id and group_id in self.service.view_groups:
                self.group_interval.blockSignals(True)
                self.group_interval.setValue(
                    float(self.service.view_groups[group_id].interval_seconds)
                )
                self.group_interval.blockSignals(False)

        # ------------------------------------------------------------------
        # Issue filter
        def _upgrade_issue_filter(self) -> None:
            tab = self.tabs.widget(1)
            layout = tab.layout()
            self.issue_filter = QtWidgets.QLineEdit()
            self.issue_filter.setPlaceholderText(
                "Filter issue op titel, status, prioriteit, assignee, due of referentie…"
            )
            self.issue_filter.setClearButtonEnabled(True)
            if layout is not None:
                layout.insertWidget(0, self.issue_filter)
            self.issue_filter.textChanged.connect(self._apply_issue_filter)

        def _apply_issue_filter(self) -> None:
            query = str(self.issue_filter.text() if hasattr(self, "issue_filter") else "").casefold().strip()
            for index in range(self.issues.topLevelItemCount()):
                item = self.issues.topLevelItem(index)
                text = " ".join(item.text(column) for column in range(item.columnCount())).casefold()
                item.setHidden(bool(query and query not in text))

        def refresh(
            self,
            *,
            select_issue: str | None = None,
            select_markup: str | None = None,
        ) -> None:
            super().refresh(select_issue=select_issue, select_markup=select_markup)
            if hasattr(self, "view_groups"):
                self._refresh_view_groups()
            if hasattr(self, "issue_filter"):
                self._apply_issue_filter()
            self._sync_markup_overlay()
            if hasattr(self, "summary"):
                self.summary.setText(
                    self.summary.text()
                    + f" · View Groups {len(self.service.view_groups)} · snapshots {len(self.service.view_snapshots)}"
                )

        def closeEvent(self, event: Any) -> None:
            self._stop_slideshow()
            super().closeEvent(event)

else:

    class V15ReviewPanelPhase2:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["V15ReviewPanelPhase2"]
