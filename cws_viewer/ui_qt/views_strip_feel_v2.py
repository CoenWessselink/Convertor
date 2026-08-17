"""Always-visible lightweight Saved Views strip for CWS Viewer V15 preview.2."""
from __future__ import annotations

from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class CwsViewsStripV2(QtWidgets.QWidget):
        status_changed = QtCore.Signal(str)

        def __init__(self, service: Any, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.service = service
            self._slideshow_ids: tuple[str, ...] = ()
            self._slideshow_index = 0
            self._known_signature: tuple[str, ...] = ()
            self._slide_timer = QtCore.QTimer(self)
            self._slide_timer.timeout.connect(self._next_slide)
            self._build_ui()
            self._poll = QtCore.QTimer(self)
            self._poll.setInterval(1400)
            self._poll.timeout.connect(self._refresh_if_changed)
            self._poll.start()
            self.refresh()

        def _build_ui(self) -> None:
            self.setObjectName("cwsViewsStripV2")
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(7, 5, 7, 5)
            root.setSpacing(4)

            header = QtWidgets.QHBoxLayout()
            title = QtWidgets.QLabel("Views")
            title.setObjectName("cwsViewsStripTitle")
            header.addWidget(title)
            self.group = QtWidgets.QComboBox()
            self.group.setMinimumWidth(150)
            self.group.currentIndexChanged.connect(lambda _i: self.refresh())
            header.addWidget(self.group)
            self.create_view = QtWidgets.QToolButton()
            self.create_view.setText("+ View")
            self.create_view.clicked.connect(self._create_view)
            header.addWidget(self.create_view)
            self.create_group = QtWidgets.QToolButton()
            self.create_group.setText("+ Groep")
            self.create_group.clicked.connect(self._create_group)
            header.addWidget(self.create_group)
            self.play = QtWidgets.QToolButton()
            self.play.setText("▶")
            self.play.setToolTip("Slideshow afspelen / stoppen")
            self.play.clicked.connect(self._toggle_slideshow)
            header.addWidget(self.play)
            header.addStretch(1)
            self.search = QtWidgets.QLineEdit()
            self.search.setPlaceholderText("Zoek view…")
            self.search.setClearButtonEnabled(True)
            self.search.setMaximumWidth(230)
            self.search.textChanged.connect(lambda _text: self.refresh())
            header.addWidget(self.search)
            root.addLayout(header)

            self.scroll = QtWidgets.QScrollArea()
            self.scroll.setWidgetResizable(True)
            self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.cards_host = QtWidgets.QWidget()
            self.cards = QtWidgets.QHBoxLayout(self.cards_host)
            self.cards.setContentsMargins(0, 0, 0, 0)
            self.cards.setSpacing(6)
            self.cards.addStretch(1)
            self.scroll.setWidget(self.cards_host)
            root.addWidget(self.scroll, 1)

        def _current_group_id(self) -> str:
            return str(self.group.currentData() or "")

        def _all_views(self) -> tuple[Any, ...]:
            return tuple(self.service.controller.list_viewpoints())

        def _visible_views(self) -> tuple[Any, ...]:
            views = self._all_views()
            group_id = self._current_group_id()
            if group_id:
                group = self.service.view_groups.get(group_id)
                if group is None:
                    return ()
                by_id = {item.viewpoint_id: item for item in views}
                views = tuple(by_id[value] for value in group.viewpoint_ids if value in by_id)
            query = self.search.text().casefold().strip()
            if query:
                views = tuple(item for item in views if query in item.name.casefold())
            return views

        def _refresh_groups(self) -> None:
            current = self._current_group_id()
            self.group.blockSignals(True)
            self.group.clear()
            self.group.addItem("Eigen views", "")
            for group in self.service.list_view_groups():
                self.group.addItem(group.name, group.group_id)
            index = self.group.findData(current)
            self.group.setCurrentIndex(max(0, index))
            self.group.blockSignals(False)

        def _clear_cards(self) -> None:
            while self.cards.count():
                item = self.cards.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        def refresh(self) -> None:
            self._refresh_groups()
            self._clear_cards()
            for viewpoint in self._visible_views():
                button = QtWidgets.QPushButton(viewpoint.name)
                button.setObjectName("cwsViewCard")
                button.setMinimumSize(132, 48)
                button.setMaximumWidth(190)
                button.setToolTip("Klik: view openen · rechtsklik: beheren")
                button.clicked.connect(
                    lambda _checked=False, value=viewpoint.viewpoint_id: self._activate(value)
                )
                button.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
                button.customContextMenuRequested.connect(
                    lambda pos, b=button, value=viewpoint.viewpoint_id: self._view_menu(b, pos, value)
                )
                self.cards.addWidget(button)
            self.cards.addStretch(1)
            self._known_signature = tuple(
                f"{item.viewpoint_id}:{item.name}" for item in self._all_views()
            ) + tuple(
                f"G:{item.group_id}:{item.name}:{','.join(item.viewpoint_ids)}"
                for item in self.service.list_view_groups()
            )

        def _refresh_if_changed(self) -> None:
            signature = tuple(
                f"{item.viewpoint_id}:{item.name}" for item in self._all_views()
            ) + tuple(
                f"G:{item.group_id}:{item.name}:{','.join(item.viewpoint_ids)}"
                for item in self.service.list_view_groups()
            )
            if signature != self._known_signature:
                self.refresh()

        def _activate(self, viewpoint_id: str) -> None:
            try:
                self.service.activate_saved_view(viewpoint_id)
                self.status_changed.emit("Saved View geopend")
            except Exception as exc:
                self.status_changed.emit(f"View kon niet worden geopend: {type(exc).__name__}: {exc}")

        def _create_view(self) -> None:
            name, ok = QtWidgets.QInputDialog.getText(self, "Nieuwe View", "Naam:", text="Nieuwe View")
            if not ok or not name.strip():
                return
            view = self.service.capture_view(name.strip())
            group_id = self._current_group_id()
            if group_id:
                self.service.add_view_to_group(group_id, view.viewpoint_id)
            try:
                self.service.save()
            except Exception:
                pass
            self.refresh()
            self.status_changed.emit(f"View opgeslagen: {view.name}")

        def _create_group(self) -> None:
            name, ok = QtWidgets.QInputDialog.getText(self, "Nieuwe View Group", "Naam:")
            if not ok or not name.strip():
                return
            group = self.service.create_view_group(name.strip())
            try:
                self.service.save()
            except Exception:
                pass
            self.refresh()
            index = self.group.findData(group.group_id)
            if index >= 0:
                self.group.setCurrentIndex(index)

        def _view_menu(self, button: Any, pos: Any, viewpoint_id: str) -> None:
            menu = QtWidgets.QMenu(button)
            menu.addAction("Open", lambda: self._activate(viewpoint_id))
            menu.addAction("Update vanuit huidige 3D-view", lambda: self._update_view(viewpoint_id))
            menu.addAction("Hernoemen", lambda: self._rename_view(viewpoint_id))
            groups = self.service.list_view_groups()
            if groups:
                group_menu = menu.addMenu("Toevoegen aan groep")
                for group in groups:
                    group_menu.addAction(
                        group.name,
                        lambda _checked=False, gid=group.group_id: self._add_to_group(gid, viewpoint_id),
                    )
            current_group = self._current_group_id()
            if current_group:
                menu.addSeparator()
                menu.addAction("Naar links", lambda: self._move_in_group(current_group, viewpoint_id, -1))
                menu.addAction("Naar rechts", lambda: self._move_in_group(current_group, viewpoint_id, 1))
                menu.addAction("Uit groep", lambda: self._remove_from_group(current_group, viewpoint_id))
            menu.addSeparator()
            menu.addAction("Verwijderen", lambda: self._delete_view(viewpoint_id))
            menu.exec(button.mapToGlobal(pos))

        def _rename_view(self, viewpoint_id: str) -> None:
            view = next((item for item in self._all_views() if item.viewpoint_id == viewpoint_id), None)
            if view is None:
                return
            name, ok = QtWidgets.QInputDialog.getText(self, "View hernoemen", "Naam:", text=view.name)
            if ok and name.strip():
                self.service.rename_view(viewpoint_id, name.strip())
                self._save_refresh()

        def _update_view(self, viewpoint_id: str) -> None:
            self.service.update_view_from_current_state(viewpoint_id)
            self._save_refresh()
            self.status_changed.emit("View bijgewerkt vanuit huidige 3D-state")

        def _delete_view(self, viewpoint_id: str) -> None:
            self.service.delete_view(viewpoint_id)
            self._save_refresh()

        def _add_to_group(self, group_id: str, viewpoint_id: str) -> None:
            self.service.add_view_to_group(group_id, viewpoint_id)
            self._save_refresh()

        def _remove_from_group(self, group_id: str, viewpoint_id: str) -> None:
            self.service.remove_view_from_group(group_id, viewpoint_id)
            self._save_refresh()

        def _move_in_group(self, group_id: str, viewpoint_id: str, offset: int) -> None:
            self.service.move_view_in_group(group_id, viewpoint_id, offset)
            self._save_refresh()

        def _save_refresh(self) -> None:
            try:
                self.service.save()
            except Exception:
                pass
            self.refresh()

        def _toggle_slideshow(self) -> None:
            if self._slide_timer.isActive():
                self._slide_timer.stop()
                self.play.setText("▶")
                self.status_changed.emit("View slideshow gestopt")
                return
            views = self._visible_views()
            if not views:
                return
            self._slideshow_ids = tuple(item.viewpoint_id for item in views)
            self._slideshow_index = 0
            interval = 1800
            group_id = self._current_group_id()
            if group_id and group_id in self.service.view_groups:
                interval = int(self.service.view_groups[group_id].interval_seconds * 1000.0)
            self.play.setText("■")
            self._show_slide(0)
            self._slide_timer.start(max(250, interval))
            self.status_changed.emit("View slideshow gestart")

        def _show_slide(self, index: int) -> None:
            if not self._slideshow_ids:
                return
            self._slideshow_index = index % len(self._slideshow_ids)
            self._activate(self._slideshow_ids[self._slideshow_index])

        def _next_slide(self) -> None:
            if not self._slideshow_ids:
                self._slide_timer.stop()
                return
            self._show_slide(self._slideshow_index + 1)

        def closeEvent(self, event: Any) -> None:
            self._poll.stop()
            self._slide_timer.stop()
            super().closeEvent(event)

else:

    class CwsViewsStripV2:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["CwsViewsStripV2"]
