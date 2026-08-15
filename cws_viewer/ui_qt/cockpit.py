"""CWS Viewer light engineering cockpit.

This is the standalone product shell.  It intentionally reuses the proven
V4/V9 tree/grid/property/scene core and exposes the V5–V11 functions instead of
introducing a second viewer truth.  The interaction model follows familiar
professional BIM-viewer conventions, while all implementation, styling and
assets remain original CWS work.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.adapters.project_scene_loader import ProjectSceneLoadResult, ProjectSceneLoader
from cws_viewer.contracts.enums import (
    BackgroundTheme,
    ColorScheme,
    ProjectionType,
    RenderMode,
    SelectionLevel,
    StandardView,
)
from cws_viewer.model_grids import extract_project_model_grids
from cws_viewer.ui_qt.design_system import (
    CWS_LIGHT,
    THEMES,
    persist_theme_key,
    qss_for_theme,
    theme_by_key,
)
from cws_viewer.ui_qt.project_viewer import RealProjectViewerWindow
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()
    from cws_convertor.ui_qt.viewer_tools import IntegratedViewerToolsPanel
    from cws_viewer.ui_qt.geometry_status import GeometryStatusPanel

    class CwsViewerCockpitWindow(RealProjectViewerWindow):
        """One-model professional CWS desktop viewer."""

        def __init__(self, load_result: ProjectSceneLoadResult) -> None:
            super().__init__(load_result)
            self.setObjectName("cwsCockpitRoot")
            self.setWindowTitle("CWS Viewer — Projectviewer")
            self.resize(1760, 1020)
            self.controller = self.viewer.controller
            self.project = load_result.project
            self._theme_key = CWS_LIGHT.key
            self._grid_level_actions: dict[float, Any] = {}
            self._navigation_actions: dict[str, Any] = {}
            self._exact_workspace: Any | None = None

            self._apply_theme(self._theme_key)
            self._reconfigure_legacy_surfaces()
            self._create_navigation_toolbar()
            self._create_tools_toolbar()
            self._create_viewer_tools_dock()
            self._create_geometry_status_dock()
            self._install_context_menu()
            self._load_model_grids()
            self._connect_cockpit_signals()
            self._set_navigation_mode("rotate")
            self.controller.set_background_theme(BackgroundTheme.LIGHT)
            self.controller.set_render_mode(RenderMode.SHADED_EDGES)
            self.statusBar().showMessage(
                "CWS Viewer gereed · Ctrl+U Rotate · Ctrl+I Pan · Ctrl+O Walk · Ctrl+P Look · Space Fit",
                9000,
            )

        # ------------------------------------------------------------------
        # Theme/layout
        # ------------------------------------------------------------------
        def _apply_theme(self, key: str) -> None:
            palette = theme_by_key(key)
            self._theme_key = persist_theme_key(palette.key)
            self.setStyleSheet(qss_for_theme(palette))
            background = BackgroundTheme.LIGHT if palette.key == CWS_LIGHT.key else BackgroundTheme.DARK
            try:
                self.controller.set_background_theme(background)
            except Exception:
                pass

        def _reconfigure_legacy_surfaces(self) -> None:
            for name in ("cwsV4ViewerToolbar", "cwsV4WorkspaceToolbar"):
                toolbar = self.findChild(QtWidgets.QToolBar, name)
                if toolbar is not None:
                    toolbar.hide()
            search = self.findChild(QtWidgets.QToolBar, "cwsV4SearchToolbar")
            if search is not None:
                search.setWindowTitle("Zoeken / filteren")

            tree_dock = self.findChild(QtWidgets.QDockWidget, "cwsV4ProjectTreeDock")
            grid_dock = self.findChild(QtWidgets.QDockWidget, "cwsV4ProjectGridDock")
            props_dock = self.findChild(QtWidgets.QDockWidget, "cwsV4PropertiesDock")
            workspace_dock = self.findChild(QtWidgets.QDockWidget, "cwsV4WorkspaceDock")
            if tree_dock is not None:
                tree_dock.setWindowTitle("Modelstructuur")
                tree_dock.setMinimumWidth(245)
            if props_dock is not None:
                props_dock.setWindowTitle("Eigenschappen")
                props_dock.setMinimumWidth(315)
            if workspace_dock is not None:
                workspace_dock.setWindowTitle("Views / Visibility / Accuracy")
                workspace_dock.setMinimumWidth(315)
            if grid_dock is not None:
                grid_dock.setWindowTitle("Onderdelen / merken / hoeveelheden")
                grid_dock.setMinimumHeight(170)
            if props_dock is not None and workspace_dock is not None:
                self.tabifyDockWidget(props_dock, workspace_dock)
                props_dock.raise_()
            if tree_dock is not None and props_dock is not None:
                self.resizeDocks([tree_dock, props_dock], [270, 335], QtCore.Qt.Orientation.Horizontal)
            if grid_dock is not None:
                self.resizeDocks([grid_dock], [210], QtCore.Qt.Orientation.Vertical)

        def _action(
            self,
            toolbar: Any,
            text: str,
            slot: Any,
            shortcut: str | None = None,
            *,
            checkable: bool = False,
        ) -> Any:
            action = QtGui.QAction(text, self)
            action.setCheckable(checkable)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(slot)
            toolbar.addAction(action)
            return action

        def _tool_button(self, toolbar: Any, text: str, menu: Any) -> Any:
            button = QtWidgets.QToolButton()
            button.setText(text)
            button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            button.setMenu(menu)
            toolbar.addWidget(button)
            return button

        # ------------------------------------------------------------------
        # Main controls
        # ------------------------------------------------------------------
        def _create_navigation_toolbar(self) -> None:
            self.addToolBarBreak()
            toolbar = QtWidgets.QToolBar("Navigatie en selectie", self)
            toolbar.setObjectName("cwsCockpitNavigationToolbar")
            toolbar.setMovable(False)
            self.addToolBar(toolbar)

            toolbar.addWidget(QtWidgets.QLabel("Selectie "))
            self._selection_level_combo = QtWidgets.QComboBox()
            self._selection_level_combo.addItem("Onderdeel", SelectionLevel.PART.value)
            self._selection_level_combo.addItem("Assembly", SelectionLevel.ASSEMBLY.value)
            self._selection_level_combo.addItem("Model", SelectionLevel.MODEL.value)
            self._selection_level_combo.currentIndexChanged.connect(self._selection_level_changed)
            toolbar.addWidget(self._selection_level_combo)
            toolbar.addSeparator()

            for mode, title, shortcut in (
                ("rotate", "Rotate", "Ctrl+U"),
                ("pan", "Pan", "Ctrl+I"),
                ("walk", "Walk", "Ctrl+O"),
                ("look", "Look", "Ctrl+P"),
            ):
                self._navigation_actions[mode] = self._action(
                    toolbar,
                    title,
                    lambda _checked=False, value=mode: self._set_navigation_mode(value),
                    shortcut,
                    checkable=True,
                )
            toolbar.addSeparator()
            self._action(toolbar, "Fit", self.controller.fit_all, "F")
            self._action(toolbar, "Fit selectie", self.controller.fit_selection, "Space")

            view_menu = QtWidgets.QMenu(self)
            for title, value in (
                ("Isometrisch", StandardView.ISOMETRIC),
                ("Voor", StandardView.FRONT),
                ("Achter", StandardView.BACK),
                ("Links", StandardView.LEFT),
                ("Rechts", StandardView.RIGHT),
                ("Boven", StandardView.TOP),
                ("Onder", StandardView.BOTTOM),
            ):
                view_menu.addAction(
                    title,
                    lambda checked=False, preset=value: self.controller.set_standard_view(preset),
                )
            self._tool_button(toolbar, "Aanzicht ▾", view_menu)

            projection_menu = QtWidgets.QMenu(self)
            projection_menu.addAction(
                "Perspectief", lambda: self.controller.set_projection(ProjectionType.PERSPECTIVE)
            )
            projection_menu.addAction(
                "Orthografisch", lambda: self.controller.set_projection(ProjectionType.ORTHOGRAPHIC)
            )
            self._tool_button(toolbar, "Projectie ▾", projection_menu)
            self._action(toolbar, "Volledig scherm", self._toggle_fullscreen, "F11")

        def _create_tools_toolbar(self) -> None:
            toolbar = QtWidgets.QToolBar("Viewer gereedschappen", self)
            toolbar.setObjectName("cwsCockpitToolsToolbar")
            toolbar.setMovable(False)
            self.addToolBar(toolbar)

            self._action(toolbar, "Verberg", self._hide_selected, "Backspace")
            self._action(toolbar, "Verberg overige", self._isolate_selected, "Shift+Backspace")
            self._action(toolbar, "Ghost overige", self._ghost_selected)
            self._action(toolbar, "Alles tonen", self.controller.show_all)
            toolbar.addSeparator()

            self._grid_button = QtWidgets.QToolButton()
            self._grid_button.setText("Stamien ▾")
            self._grid_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
            self._grid_menu = QtWidgets.QMenu(self._grid_button)
            self._grid_button.setMenu(self._grid_menu)
            toolbar.addWidget(self._grid_button)

            measure_menu = QtWidgets.QMenu(self)
            measure_menu.addAction("Afstand", lambda: self._measurement_button("distance"))
            measure_menu.addAction("Horizontaal", lambda: self._measurement_button("horizontal"))
            measure_menu.addAction("Verticaal", lambda: self._measurement_button("vertical"))
            measure_menu.addAction("XYZ / punt", lambda: self._measurement_button("coordinates"))
            measure_menu.addSeparator()
            measure_menu.addAction("Meetwerkruimte / rapport", self._show_viewer_tools)
            measure_menu.addAction("Exact face/edge/radius/diameter", self._open_exact_workbench)
            self._tool_button(toolbar, "Meten ▾", measure_menu)

            section_menu = QtWidgets.QMenu(self)
            section_menu.addAction("Doorsnede X", lambda: self._viewer_tools.section_x.click())
            section_menu.addAction("Doorsnede Y", lambda: self._viewer_tools.section_y.click())
            section_menu.addAction("Doorsnede Z", lambda: self._viewer_tools.section_z.click())
            section_menu.addSeparator()
            section_menu.addAction("Clipping box", lambda: self._viewer_tools.clip_box.click())
            section_menu.addAction("Alle doorsneden wissen", lambda: self._viewer_tools.clear_sections.click())
            section_menu.addAction("Clipping wissen", lambda: self._viewer_tools.clear_clip.click())
            self._tool_button(toolbar, "Doorsnede ▾", section_menu)

            explode_menu = QtWidgets.QMenu(self)
            explode_menu.addAction("Explode selectie", lambda: self._viewer_tools.explode_selection.click())
            explode_menu.addAction("Explode reset", lambda: self._viewer_tools.reset_explode.click())
            self._tool_button(toolbar, "Explode ▾", explode_menu)
            toolbar.addSeparator()

            display_menu = QtWidgets.QMenu(self)
            display_menu.addAction(
                "Shaded + randen", lambda: self.controller.set_render_mode(RenderMode.SHADED_EDGES)
            )
            display_menu.addAction("Shaded", lambda: self.controller.set_render_mode(RenderMode.SHADED))
            display_menu.addAction(
                "Hidden line", lambda: self.controller.set_render_mode(RenderMode.HIDDEN_LINE)
            )
            display_menu.addAction(
                "Wireframe", lambda: self.controller.set_render_mode(RenderMode.WIREFRAME)
            )
            self._tool_button(toolbar, "Weergave ▾", display_menu)

            color_menu = QtWidgets.QMenu(self)
            for title, scheme in (
                ("Origineel", ColorScheme.ORIGINAL),
                ("Categorie", ColorScheme.CATEGORY),
                ("Materiaal", ColorScheme.MATERIAL),
                ("Profiel", ColorScheme.PROFILE),
                ("Status", ColorScheme.STATUS),
                ("Fase", ColorScheme.PHASE),
                ("Bronmodel", ColorScheme.SOURCE_MODEL),
                ("Assembly", ColorScheme.ASSEMBLY),
                ("Monochroom", ColorScheme.MONOCHROME),
            ):
                color_menu.addAction(
                    title,
                    lambda checked=False, value=scheme: self._apply_color_scheme(value),
                )
            self._tool_button(toolbar, "Modelkleur ▾", color_menu)

            toolbar.addWidget(QtWidgets.QLabel(" Transparantie "))
            self._cockpit_transparency = QtWidgets.QSpinBox()
            self._cockpit_transparency.setRange(0, 95)
            self._cockpit_transparency.setValue(50)
            self._cockpit_transparency.setSuffix(" %")
            self._cockpit_transparency.setMaximumWidth(78)
            toolbar.addWidget(self._cockpit_transparency)
            self._action(toolbar, "Toepassen", self._apply_cockpit_transparency)
            self._action(toolbar, "Reset stijl", self.controller.reset_styles)
            toolbar.addSeparator()

            theme_menu = QtWidgets.QMenu(self)
            for key, theme in THEMES.items():
                theme_menu.addAction(
                    theme.title, lambda checked=False, value=key: self._apply_theme(value)
                )
            self._tool_button(toolbar, "Thema ▾", theme_menu)

            review_menu = QtWidgets.QMenu(self)
            review_menu.addAction("Exact Part Workbench", self._open_exact_workbench)
            review_menu.addAction("Revisie vergelijken", self._compare_revision)
            review_menu.addAction("Geometriestatus", self._show_geometry_status)
            review_menu.addAction("Accuracy / herkomst", lambda: self._toggle_accuracy_mode(True))
            self._tool_button(toolbar, "Controleren ▾", review_menu)
            toolbar.addSeparator()

            self._action(toolbar, "Undo", self.controller.undo_viewer, "Ctrl+Z")
            self._action(toolbar, "Redo", self.controller.redo_viewer, "Ctrl+Y")
            self._action(toolbar, "Viewpoint", self._save_viewpoint_dialog, "Ctrl+B")
            self._action(toolbar, "Screenshot", self._save_screenshot_dialog, "Ctrl+Shift+S")

        # ------------------------------------------------------------------
        # Existing V11 tools exposed in cockpit docks
        # ------------------------------------------------------------------
        def _create_viewer_tools_dock(self) -> None:
            self._viewer_tools = IntegratedViewerToolsPanel(self, self)
            self._viewer_tools.status_changed.connect(
                lambda text: self.statusBar().showMessage(text, 5000)
            )
            self._tools_dock = QtWidgets.QDockWidget(
                "Viewer Tools — meten / doorsnede / explode", self
            )
            self._tools_dock.setObjectName("cwsCockpitViewerToolsDock")
            self._tools_dock.setWidget(self._viewer_tools)
            self._tools_dock.setMinimumHeight(180)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self._tools_dock)
            grid_dock = self.findChild(QtWidgets.QDockWidget, "cwsV4ProjectGridDock")
            if grid_dock is not None:
                self.tabifyDockWidget(grid_dock, self._tools_dock)
                grid_dock.raise_()

        def _create_geometry_status_dock(self) -> None:
            self._geometry_status = GeometryStatusPanel(self.load_result, self)
            self._geometry_dock = QtWidgets.QDockWidget("Geometriestatus", self)
            self._geometry_dock.setObjectName("cwsCockpitGeometryStatusDock")
            self._geometry_dock.setWidget(self._geometry_status)
            self._geometry_dock.setMinimumWidth(440)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, self._geometry_dock)
            workspace_dock = self.findChild(QtWidgets.QDockWidget, "cwsV4WorkspaceDock")
            if workspace_dock is not None:
                self.tabifyDockWidget(workspace_dock, self._geometry_dock)
                workspace_dock.raise_()

        # ------------------------------------------------------------------
        # IFC model grids / stamien
        # ------------------------------------------------------------------
        def _source_search_roots(self) -> tuple[Path, ...]:
            roots: list[Path] = []
            for source in dict(getattr(self.project, "sources", {}) or {}).values():
                raw = str(getattr(source, "original_path", "") or "")
                if raw:
                    path = Path(raw).expanduser()
                    if path.parent not in roots:
                        roots.append(path.parent)
            return tuple(roots)

        def _load_model_grids(self) -> None:
            try:
                catalog = extract_project_model_grids(
                    self.project,
                    project_package_path=self.load_result.project_path,
                    source_search_roots=self._source_search_roots(),
                )
                self.viewer.set_model_grids(catalog)
                self._rebuild_grid_menu(catalog.levels)
                if catalog.axis_count:
                    self.statusBar().showMessage(
                        f"Stamien: {catalog.axis_count} assen · {len(catalog.levels)} niveau(s)",
                        6000,
                    )
                elif catalog.warnings:
                    self.statusBar().showMessage(
                        "IFC bevat geen ondersteunde/resolveerbare stamienassen", 5000
                    )
            except Exception as exc:
                self._grid_button.setEnabled(False)
                self._grid_button.setToolTip(f"Stamien kon niet worden geladen: {exc}")

        def _rebuild_grid_menu(self, levels: tuple[float, ...]) -> None:
            self._grid_menu.clear()
            self._grid_level_actions.clear()
            if not levels:
                action = self._grid_menu.addAction("Geen IFC-stamien in bron")
                action.setEnabled(False)
                self._grid_button.setEnabled(False)
                return
            self._grid_button.setEnabled(True)
            show = self._grid_menu.addAction("Stamien tonen")
            show.setCheckable(True)
            show.setChecked(True)
            show.toggled.connect(self.viewer.set_grids_visible)
            self._grid_menu.addSeparator()
            visible = set(self.viewer.visible_grid_levels())
            for level in levels:
                label = "0 mm" if abs(level) < 1e-3 else f"{level:,.0f} mm"
                action = self._grid_menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(level in visible)
                action.toggled.connect(
                    lambda checked, value=level: self.viewer.set_grid_level_visible(value, checked)
                )
                self._grid_level_actions[level] = action

        # ------------------------------------------------------------------
        # Review / exact / diagnostics
        # ------------------------------------------------------------------
        def _selected_entity_id(self) -> str | None:
            return self.interaction.selection.primary_entity_id

        def _ensure_exact_workspace(self):
            if self._exact_workspace is not None:
                return self._exact_workspace
            from cws_convertor.integration import IntegratedProjectWorkspace

            self.statusBar().showMessage("Exacte brongeometrie voorbereiden…")
            self._exact_workspace = IntegratedProjectWorkspace.open(
                self.load_result.project_path,
                read_only=True,
                source_search_roots=self._source_search_roots(),
                load_all_geometry=False,
                allow_proxy=False,
            )
            return self._exact_workspace

        def _open_exact_workbench(self) -> None:
            entity_id = self._selected_entity_id()
            if not entity_id:
                QtWidgets.QMessageBox.information(
                    self, "Exact Part Workbench", "Selecteer eerst één productieonderdeel."
                )
                return
            try:
                workspace = self._ensure_exact_workspace()
                result = workspace.open_exact_part(entity_id)
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Exact Part Workbench", f"{type(exc).__name__}: {exc}"
                )
                return
            if not result.available:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Exact Part Workbench geblokkeerd",
                    "\n".join([result.status, *result.blocking_codes, *result.notes]),
                )
                return
            from cws_viewer.ui_qt.exact_part_workbench import ExactPartWorkbenchPanel

            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"Exact Part Workbench — {entity_id}")
            dialog.resize(1500, 900)
            layout = QtWidgets.QVBoxLayout(dialog)
            banner = QtWidgets.QLabel(
                "Exact OCCT/BREP review · viewer kan productie niet zelfstandig vrijgeven"
            )
            banner.setObjectName("warningPill")
            layout.addWidget(banner)
            layout.addWidget(ExactPartWorkbenchPanel(result.service), 1)
            dialog.exec()

        def _compare_revision(self) -> None:
            name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Vergelijk huidige projectversie met oudere CWS-revisie",
                "",
                "CWS-project (*.cwscproj)",
            )
            if not name:
                return
            try:
                from cws_convertor.project.service import ProjectSession
                from cws_viewer.revisions.project_compare import compare_project_revisions
                from cws_viewer.ui_qt.revision_compare import RevisionComparePanel

                old_session = ProjectSession.open(Path(name), read_only=True)
                try:
                    report = compare_project_revisions(old_session.project, self.project)
                finally:
                    old_session.close()
                dialog = QtWidgets.QDialog(self)
                dialog.setWindowTitle("CWS Viewer — revisiecompare")
                dialog.resize(1550, 900)
                layout = QtWidgets.QVBoxLayout(dialog)
                layout.addWidget(RevisionComparePanel(report), 1)
                dialog.exec()
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "Revisiecompare", f"{type(exc).__name__}: {exc}"
                )

        def _show_geometry_status(self) -> None:
            self._geometry_status.refresh()
            self._geometry_dock.show()
            self._geometry_dock.raise_()

        # ------------------------------------------------------------------
        # Interaction / menus
        # ------------------------------------------------------------------
        def _connect_cockpit_signals(self) -> None:
            self.viewer.navigation_mode_changed.connect(self._sync_navigation_actions)
            self.viewer.grids_changed.connect(lambda _enabled, _levels: self._update_status())

        def _install_context_menu(self) -> None:
            self.viewer.context_requested.connect(self._show_viewer_context_menu)

        def _show_viewer_context_menu(self, global_pos: Any) -> None:
            menu = QtWidgets.QMenu(self)
            selected = bool(self.controller.get_selection())
            fit = menu.addAction("Fit selectie", self.controller.fit_selection)
            fit.setEnabled(selected)
            menu.addSeparator()
            for title, callback in (
                ("Verbergen", self._hide_selected),
                ("Alleen selectie tonen", self._isolate_selected),
                ("Selectie + omgeving ghost", self._ghost_selected),
            ):
                action = menu.addAction(title, callback)
                action.setEnabled(selected)
            menu.addAction("Alles tonen", self.controller.show_all)
            menu.addSeparator()
            measure = menu.addMenu("Meten")
            measure.addAction("Afstand", lambda: self._measurement_button("distance"))
            measure.addAction("Horizontaal", lambda: self._measurement_button("horizontal"))
            measure.addAction("Verticaal", lambda: self._measurement_button("vertical"))
            measure.addAction("XYZ", lambda: self._measurement_button("coordinates"))
            menu.addAction("Doorsnede / clipping…", self._show_viewer_tools)
            exact = menu.addAction("Exact Part Workbench", self._open_exact_workbench)
            exact.setEnabled(bool(self._selected_entity_id()))
            menu.addAction("Eigenschappen", self._show_properties_dock)
            menu.addAction("Accuracy / herkomst", lambda: self._toggle_accuracy_mode(True))
            menu.addAction("Geometriestatus", self._show_geometry_status)
            menu.addSeparator()
            menu.addAction("Screenshot", self._save_screenshot_dialog)
            menu.exec(global_pos)

        def _selection_level_changed(self, index: int) -> None:
            value = self._selection_level_combo.itemData(index)
            if value:
                self.controller.set_selection_level(SelectionLevel(value))

        def _set_navigation_mode(self, mode: str) -> None:
            self.viewer.set_navigation_mode(mode)
            self._sync_navigation_actions(mode)

        def _sync_navigation_actions(self, mode: str) -> None:
            for key, action in self._navigation_actions.items():
                blocked = action.blockSignals(True)
                action.setChecked(key == mode)
                action.blockSignals(blocked)
            self.statusBar().showMessage(f"Navigatie: {mode}", 2500)

        def _apply_color_scheme(self, scheme: ColorScheme) -> None:
            legend = self.interaction.apply_color_scheme(scheme)
            self._populate_legend(legend)
            self.statusBar().showMessage(f"Modelkleur: {scheme.value}", 3000)

        def _apply_cockpit_transparency(self) -> None:
            blocked = self._transparency.blockSignals(True)
            self._transparency.setValue(float(self._cockpit_transparency.value()))
            self._transparency.blockSignals(blocked)
            self._apply_transparency_to_selection()

        def _show_viewer_tools(self) -> None:
            self._tools_dock.show()
            self._tools_dock.raise_()
            self._viewer_tools.refresh()

        def _measurement_button(self, mode: str) -> None:
            self._show_viewer_tools()
            mapping = {
                "distance": self._viewer_tools.quick_distance,
                "horizontal": self._viewer_tools.quick_horizontal,
                "vertical": self._viewer_tools.quick_vertical,
                "coordinates": self._viewer_tools.quick_coordinates,
            }
            mapping[mode].click()

        def _show_properties_dock(self) -> None:
            dock = self.findChild(QtWidgets.QDockWidget, "cwsV4PropertiesDock")
            if dock is not None:
                dock.show()
                dock.raise_()

        def _toggle_fullscreen(self) -> None:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

        def closeEvent(self, event: Any) -> None:
            if self._exact_workspace is not None:
                try:
                    self._exact_workspace.close()
                except Exception:
                    pass
                self._exact_workspace = None
            super().closeEvent(event)


    def run_cws_viewer_cockpit(
        project_path: str | Path,
        *,
        cache_root: str | Path | None = None,
        source_search_roots: tuple[str | Path, ...] = (),
        ci_smoke: bool = False,
        screenshot_path: str | Path | None = None,
    ) -> int:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        app.setApplicationName("CWS Viewer")
        app.setOrganizationName("CWS")
        result = ProjectSceneLoader(
            cache_root=cache_root,
            source_search_roots=source_search_roots,
        ).load(project_path)
        window = CwsViewerCockpitWindow(result)
        window.show()
        if ci_smoke:
            def finish() -> None:
                try:
                    window.controller.fit_all()
                    window.controller.render()
                    if screenshot_path:
                        window.controller.screenshot_to_file(Path(screenshot_path))
                finally:
                    window.close()
                    app.quit()
            QtCore.QTimer.singleShot(1000, finish)
        return int(app.exec())

else:

    class CwsViewerCockpitWindow:  # pragma: no cover
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()

    def run_cws_viewer_cockpit(*_: Any, **__: Any) -> int:  # pragma: no cover
        require_qt()
        return 2


__all__ = ["CwsViewerCockpitWindow", "run_cws_viewer_cockpit"]
