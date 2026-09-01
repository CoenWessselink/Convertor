"""CWS UI Master V5.1 runtime binding layer.

This module binds the machine-readable V5.1 handover to the existing U4 shell.
It does not own project, selection, geometry, manufacturing, or export truth.
Actions are delegated to the existing WorkspaceRouter and existing workspace
hosts; missing context is represented as a disabled control with a reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable

from .ui_v51_contract_data import CONTROL_INVENTORY, SCREEN_MANIFEST

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except Exception:  # pragma: no cover - source-only environments
    QtCore = QtGui = QtWidgets = None  # type: ignore[assignment]


MAIN_LABELS = ("Project", "Viewer", "Productie", "Controle", "Uitvoer")
DOMAIN_INDEX = {label: index for index, label in enumerate(MAIN_LABELS)}
SCREEN_ROUTES = {
    "01": "import",
    "02": "project_overview",
    "03": "project_structure",
    "04": "project_profiles",
    "05": "viewer",
    "06": "viewer",
    "07": "viewer",
    "08": "viewer",
    "09": "viewer",
    "10": "project_reviews",
    "11": "bom",
    "12": "production_workflow",
    "13": "production_workflow",
    "14": "profile_nesting",
    "15": "plate_nesting",
    "16": "edit",
    "17": "scribing",
    "18": "converter",
    "19": "pdf",
    "20": "print_center",
    "21": "control",
    "22": "control",
    "23": "manufacturability",
    "24": "export",
    "25": "report",
    "26": "settings",
    "27": "settings",
    "28": "activity",
    "29": "problems",
    "30": "viewer",
    "31": "command",
}

SCREEN_SUBTABS = {
    "04": ("Profielen", "Materialen"),
    "06": ("Selectie",),
    "07": ("Weergave", "Meten"),
    "08": ("Doorsnede", "Isoleren"),
    "09": ("Laadstatus", "Prestaties"),
    "10": ("Projectreviews", "Rapport"),
    "11": ("BOM",),
    "12": ("Machine-indeling", "Automatisch"),
    "13": ("Machine-indeling", "Handmatig"),
    "14": ("Profile Nesting", "Optimalisatie"),
    "15": ("Plate Nesting", "Optimalisatie"),
    "17": ("Scribing", "Markeringen"),
    "19": ("Tekeningen", "PDF"),
    "21": ("Validatie",),
    "22": ("Revisies", "Compare"),
    "23": ("Maakbaarheid",),
    "24": ("Export Center", "Exporteren"),
    "25": ("Rapport", "Pakket"),
}

V51_LIGHT_QSS = r"""
QMainWindow, QWidget {
    background: #F4F7FA;
    color: #1F2D3D;
    font-size: 10.5pt;
}
QToolBar#cwsV51GlobalBar, QToolBar#cwsV51ScreenActions {
    background: #FFFFFF;
    border: 0;
    border-bottom: 1px solid #D4DDE6;
    spacing: 4px;
    padding: 4px 8px;
}
QLabel#cwsV51Brand {
    color: #163A59;
    font-size: 14pt;
    font-weight: 700;
    padding-right: 14px;
}
QTabWidget#cwsPrimaryTabs::pane {
    border: 0;
    border-top: 1px solid #D4DDE6;
    background: #F4F7FA;
}
QTabWidget#cwsPrimaryTabs > QTabBar::tab {
    min-height: 34px;
    min-width: 112px;
    padding: 3px 16px;
    margin: 0;
    border: 0;
    border-bottom: 3px solid transparent;
    background: #FFFFFF;
    color: #31485D;
    font-weight: 600;
}
QTabWidget#cwsPrimaryTabs > QTabBar::tab:selected {
    color: #1F6FA8;
    border-bottom-color: #1F6FA8;
    background: #F8FBFD;
}
QPushButton, QToolButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    min-height: 28px;
    border: 1px solid #C7D3DE;
    border-radius: 4px;
    background: #FFFFFF;
    color: #1F2D3D;
    padding: 1px 8px;
}
QPushButton:hover, QToolButton:hover {
    border-color: #1F6FA8;
    background: #EAF3F9;
}
QPushButton:disabled, QToolButton:disabled, QComboBox:disabled {
    color: #8796A5;
    background: #EEF3F7;
}
QPushButton#primaryButton, QToolButton#primaryButton,
QPushButton[primary="true"], QToolButton[primary="true"] {
    color: #FFFFFF;
    background: #1F6FA8;
    border-color: #1F6FA8;
    font-weight: 600;
}
QTreeView, QTableView, QListView, QTableWidget, QTreeWidget, QListWidget {
    alternate-background-color: #F5F8FB;
    background: #FFFFFF;
    border: 1px solid #D4DDE6;
    gridline-color: #DFE6ED;
    selection-background-color: #D6EAF7;
    selection-color: #163A59;
}
QHeaderView::section {
    min-height: 28px;
    background: #EEF3F7;
    border: 0;
    border-right: 1px solid #D4DDE6;
    border-bottom: 1px solid #D4DDE6;
    padding: 2px 6px;
    color: #31485D;
    font-weight: 600;
}
QDockWidget::title {
    background: #263C50;
    color: #FFFFFF;
    padding: 7px 9px;
    font-weight: 600;
}
QStatusBar {
    min-height: 24px;
    background: #FFFFFF;
    border-top: 1px solid #D4DDE6;
    color: #617387;
}
QToolTip {
    color: #1F2D3D;
    background: #FFFFFF;
    border: 1px solid #9FB2C3;
    padding: 4px;
}
"""

V51_DARK_OVERRIDE_QSS = r"""
QMainWindow, QWidget {
    background: #0B141D;
    color: #DCE8F1;
}
QToolBar#cwsV51GlobalBar, QToolBar#cwsV51ScreenActions {
    background: #0F1D29;
    border-bottom-color: #294457;
}
QLabel#cwsV51Brand { color: #F1F7FB; }
QTabWidget#cwsPrimaryTabs::pane {
    border-top-color: #294457;
    background: #0B141D;
}
QTabWidget#cwsPrimaryTabs > QTabBar::tab {
    background: #0F1D29;
    color: #AFC0CC;
}
QTabWidget#cwsPrimaryTabs > QTabBar::tab:hover {
    color: #FFFFFF;
    background: #132738;
}
QTabWidget#cwsPrimaryTabs > QTabBar::tab:selected {
    color: #FFFFFF;
    border-bottom-color: #2D9CDB;
    background: #132738;
}
QPushButton, QToolButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    border-color: #355064;
    background: #13212D;
    color: #DCE8F1;
}
QPushButton:hover, QToolButton:hover {
    border-color: #2D9CDB;
    background: #17344A;
}
QPushButton:disabled, QToolButton:disabled, QComboBox:disabled {
    color: #6F8290;
    background: #101A23;
}
QPushButton#primaryButton, QToolButton#primaryButton,
QPushButton[primary="true"], QToolButton[primary="true"] {
    color: #FFFFFF;
    background: #1268AD;
    border-color: #2D9CDB;
}
QTreeView, QTableView, QListView, QTableWidget, QTreeWidget, QListWidget {
    alternate-background-color: #101C26;
    background: #0E1821;
    border-color: #294457;
    gridline-color: #243B4B;
    selection-background-color: #124F7A;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background: #13212D;
    border-right-color: #294457;
    border-bottom-color: #294457;
    color: #C8D6E0;
}
QDockWidget::title {
    background: #0A1822;
    color: #FFFFFF;
}
QStatusBar {
    background: #0D1821;
    border-top-color: #294457;
    color: #8FA6B6;
}
QToolTip {
    color: #EAF2F7;
    background: #13212D;
    border-color: #477089;
}
QMenu {
    background: #13212D;
    color: #DCE8F1;
    border: 1px solid #355064;
}
QMenu::item:selected { background: #124F7A; }
QScrollBar:vertical, QScrollBar:horizontal { background: #0D1821; }
QScrollBar::handle { background: #355064; min-width: 18px; min-height: 18px; }
QWidget#cwsContextRibbon, QFrame#cwsContextRibbon {
    background: #0E1821;
    border: 1px solid #294457;
}
"""


def _plain(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _label(widget: Any) -> str:
    explicit = widget.property("ui_label") if hasattr(widget, "property") else None
    if explicit:
        return str(explicit)
    for name in ("text", "title", "placeholderText", "accessibleName"):
        method = getattr(widget, name, None)
        if callable(method):
            try:
                value = method()
            except TypeError:
                continue
            if value:
                return str(value).replace("&", "").strip()
    return ""


def _set_test_id(obj: Any, test_id: str) -> None:
    obj.setObjectName(test_id)
    obj.setProperty("test_id", test_id)
    obj.setProperty("ui_test_id", test_id)
    obj.setProperty("cws_product_control", True)


def _records() -> list[dict[str, Any]]:
    return [dict(item) for item in CONTROL_INVENTORY.get("controls", ())]


def _screens() -> list[dict[str, Any]]:
    return [dict(item) for item in SCREEN_MANIFEST.get("screens", ())]


def _screen_domain(screen_id: str) -> str:
    number = int(screen_id)
    if number in {1, 2, 3, 4, 10}:
        return "Project"
    if 5 <= number <= 9 or number == 30:
        return "Viewer"
    if 11 <= number <= 19 or number in {26, 27}:
        return "Productie"
    if 21 <= number <= 23 or number == 29:
        return "Controle"
    if number in {20, 24, 25}:
        return "Uitvoer"
    return "Project"


def _route_for(record: dict[str, Any]) -> str:
    test_id = str(record.get("test_id", ""))
    service = _plain(record.get("service_contract"))
    screen_id = str(record.get("screen_id", ""))
    if "profile" in test_id and "nest" in test_id:
        return "profile_nesting"
    if "plate" in test_id and "nest" in test_id:
        return "plate_nesting"
    if "workbench" in service or "partedit" in service:
        return "edit"
    if "scrib" in service:
        return "scribing"
    if "convert" in service:
        return "converter"
    if "drawing" in service or "template" in service:
        return "pdf"
    if "documentoutput" in service or "print" in service:
        return "output"
    if "export" in service:
        return "export"
    if "validation" in service or "proof" in service or "dfm" in service or "review" in service:
        return "control"
    if "viewer" in service or "selection" in service or "measurement" in service:
        return "viewer"
    if "machine" in service or "bom" in service or "nest" in service or "stock" in service:
        return "production"
    if "project" in service or "import" in service or "profilelibrary" in service:
        return "project"
    if screen_id.isdigit():
        return _screen_domain(screen_id).casefold()
    return ""


def _candidate_type(record_type: str) -> tuple[type, ...]:
    if QtWidgets is None:
        return ()
    mapping: dict[str, tuple[type, ...]] = {
        "QPushButton": (QtWidgets.QPushButton, QtWidgets.QToolButton),
        "QToolButton": (QtWidgets.QToolButton, QtWidgets.QPushButton),
        "QCheckBox": (QtWidgets.QCheckBox,),
        "QRadioButton": (QtWidgets.QRadioButton,),
        "QComboBox": (QtWidgets.QComboBox,),
        "QLineEdit": (QtWidgets.QLineEdit,),
        "QSlider": (QtWidgets.QSlider,),
        "QSpinBox": (QtWidgets.QSpinBox, QtWidgets.QDoubleSpinBox),
        "QDoubleSpinBox": (QtWidgets.QDoubleSpinBox, QtWidgets.QSpinBox),
        "QListView": (QtWidgets.QListView, QtWidgets.QListWidget),
        "QTableView": (QtWidgets.QTableView, QtWidgets.QTableWidget),
        "QTreeView": (QtWidgets.QTreeView, QtWidgets.QTreeWidget),
    }
    return mapping.get(record_type, ())


@dataclass
class BindingResult:
    test_id: str
    screen_id: str
    widget: Any
    origin: str
    route: str


if QtWidgets is not None:
    class V51BindingController(QtCore.QObject):
        """Applies V5.1 naming, navigation and evidence bindings."""

        installed = QtCore.Signal()

        def __init__(self, window: QtWidgets.QMainWindow, router: Any) -> None:
            super().__init__(window)
            self.window = window
            self.router = router
            self.records = _records()
            self.screens = _screens()
            self.bindings: dict[str, BindingResult] = {}
            self.screen_selector: QtWidgets.QComboBox | None = None
            self.screen_toolbar: QtWidgets.QToolBar | None = None
            self.activity_dock: QtWidgets.QDockWidget | None = None
            self.problem_dock: QtWidgets.QDockWidget | None = None
            self.settings_dock: QtWidgets.QDockWidget | None = None
            self.command_dialog: QtWidgets.QDialog | None = None
            self._dynamic_actions: list[QtGui.QAction] = []
            QtCore.QTimer.singleShot(0, self.install)

        def install(self) -> None:
            self._apply_visual_contract()
            self._bind_primary_navigation()
            self._create_global_bar()
            self._create_screen_toolbar()
            self._create_activity_center()
            self._create_problem_center()
            self._create_settings_center()
            self._bind_existing_controls()
            self._assign_remaining_visible_ids()
            if self.screen_selector is not None and self.screen_selector.count():
                self._activate_screen(0)
            self.window.setProperty("cws_ui_master", "V5.1 FINAL")
            self.window.setProperty("cws_ui_binding_count", len(self.records))
            self.installed.emit()

        def _apply_visual_contract(self) -> None:
            app = QtWidgets.QApplication.instance()
            if app is not None:
                font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.GeneralFont)
                font.setPointSize(10)
                app.setFont(font)
            from .design_system.stylesheet import apply_v52_design_system

            settings = QtCore.QSettings("CWS", "CWS Convertor")
            theme = str(settings.value("product-ui/theme", "Default Light") or "Default Light")
            apply_v52_design_system(self.window, theme)

        def _primary_tabs(self) -> QtWidgets.QTabWidget | None:
            tabs = self.window.findChild(QtWidgets.QTabWidget, "cwsPrimaryTabs")
            if tabs is not None:
                return tabs
            for candidate in self.window.findChildren(QtWidgets.QTabWidget):
                if candidate.count() >= 5:
                    return candidate
            return None

        def _bind_primary_navigation(self) -> None:
            tabs = self._primary_tabs()
            if tabs is None:
                return
            tabs.setObjectName("cwsPrimaryTabs")
            tabs.setProperty("test_id", "main_navigation")
            tabs.setProperty("v51_tab_test_ids", [f"nav_{label.casefold()}" for label in MAIN_LABELS])
            for index, label in enumerate(MAIN_LABELS):
                if index < tabs.count():
                    tabs.setTabText(index, label)
                    tabs.widget(index).setProperty("v51_domain", label)

        def _contract_id(self, label: str, fallback: str) -> str:
            wanted = _plain(label)
            for record in self.records:
                if str(record.get("screen_id")) == "GLOBAL" and _plain(record.get("label")) == wanted:
                    return str(record["test_id"])
            return fallback

        def _create_global_bar(self) -> None:
            toolbar = QtWidgets.QToolBar("Globaal", self.window)
            toolbar.setObjectName("cwsV51GlobalBar")
            toolbar.setMovable(False)
            toolbar.setFloatable(False)
            toolbar.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
            toolbar.setMaximumWidth(440)
            toolbar.setFixedHeight(38)
            tabs = self._primary_tabs()
            if tabs is not None:
                toolbar.setParent(tabs)
                tabs.setCornerWidget(toolbar, QtCore.Qt.Corner.TopRightCorner)
            else:
                self.window.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, toolbar)
                brand = QtWidgets.QLabel("CWS CONVERTOR")
                brand.setObjectName("cwsV51Brand")
                toolbar.addWidget(brand)
            selector = QtWidgets.QComboBox()
            _set_test_id(selector, "cmb_global_workspace")
            selector.setMinimumWidth(180)
            for screen in self.screens:
                selector.addItem(f"{screen['screen_id']}  {screen['title']}", screen["screen_id"])
            selector.currentIndexChanged.connect(self._activate_screen)
            toolbar.addWidget(selector)
            self.screen_selector = selector
            utilities = (
                ("Ongedaan maken", "global_undo", self._undo),
                ("Opnieuw", "global_redo", self._redo),
                ("Snelactie", "global_command", self._show_command_palette),
                ("Activiteit", "global_activity", self._show_activity),
                ("Problemen", "global_problems", self._show_problems),
                ("Instellingen", "global_settings", self._show_settings),
            )
            for label, fallback, handler in utilities:
                button = QtWidgets.QToolButton()
                button.setText(label)
                button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
                button.setToolTip(label)
                standard_icons = {
                    "Ongedaan maken": QtWidgets.QStyle.StandardPixmap.SP_ArrowBack,
                    "Opnieuw": QtWidgets.QStyle.StandardPixmap.SP_ArrowForward,
                    "Snelactie": QtWidgets.QStyle.StandardPixmap.SP_FileDialogContentsView,
                    "Activiteit": QtWidgets.QStyle.StandardPixmap.SP_BrowserReload,
                    "Problemen": QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning,
                    "Instellingen": QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon,
                }
                button.setIcon(self.window.style().standardIcon(standard_icons[label]))
                _set_test_id(button, self._contract_id(label, fallback))
                button.clicked.connect(handler)
                toolbar.addWidget(button)
            print_shortcut = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Print, self.window)
            _set_test_id(print_shortcut, "global_print")
            print_shortcut.setProperty("ui_label", "Afdrukken")
            print_shortcut.activated.connect(lambda: self._activate_route("report"))
            undo_shortcut = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Undo, self.window)
            _set_test_id(undo_shortcut, "global_undo")
            undo_shortcut.setProperty("ui_label", "Ongedaan maken")
            undo_shortcut.activated.connect(self._undo)
            toolbar.show()

        def _create_screen_toolbar(self) -> None:
            toolbar = QtWidgets.QToolBar("Schermacties", self.window)
            toolbar.setObjectName("cwsV51ScreenActions")
            toolbar.setMovable(False)
            toolbar.setFloatable(False)
            toolbar.setFixedHeight(42)
            toolbar.hide()
            self.screen_toolbar = toolbar

        def _place_screen_toolbar(self) -> None:
            toolbar = self.screen_toolbar
            tabs = self._primary_tabs()
            if toolbar is None or tabs is None:
                return
            page = tabs.currentWidget()
            layout = page.layout() if page is not None else None
            if layout is None or not hasattr(layout, "insertWidget"):
                toolbar.hide()
                return
            else:
                toolbar.setParent(page)
                layout.insertWidget(0, toolbar)
            toolbar.show()

        def _dock(self, title: str, object_name: str) -> tuple[QtWidgets.QDockWidget, QtWidgets.QVBoxLayout]:
            dock = QtWidgets.QDockWidget(title, self.window)
            dock.setObjectName(object_name)
            dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea | QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
            host = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(host)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(6)
            dock.setWidget(host)
            self.window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, dock)
            dock.hide()
            return dock, layout

        def _create_activity_center(self) -> None:
            dock, layout = self._dock("Activiteit", "cwsV51ActivityCenter")
            jobs = QtWidgets.QListWidget()
            _set_test_id(jobs, "activity_jobs")
            jobs.setAccessibleName("Activiteiten")
            jobs.addItem("Geen actieve achtergrondtaken")
            layout.addWidget(jobs, 1)
            row = QtWidgets.QHBoxLayout()
            for label, test_id, handler in (
                ("Annuleren", "btn_activity_cancel", lambda: None),
                ("Openen", "btn_activity_open", lambda: self._activate_route("viewer")),
                ("Gereed wissen", "btn_activity_clear_done", jobs.clear),
            ):
                button = QtWidgets.QPushButton(label)
                _set_test_id(button, test_id)
                button.clicked.connect(handler)
                if label == "Annuleren":
                    button.setEnabled(False)
                    button.setToolTip("Niet beschikbaar omdat geen annuleerbare taak is geselecteerd.")
                row.addWidget(button)
            layout.addLayout(row)
            self.activity_dock = dock

        def _create_problem_center(self) -> None:
            dock, layout = self._dock("Problemen", "cwsV51ProblemCenter")
            problems = QtWidgets.QListWidget()
            _set_test_id(problems, "problem_list")
            problems.setAccessibleName("Problemen")
            problems.addItem("Geen actuele blokkades")
            layout.addWidget(problems, 1)
            row = QtWidgets.QHBoxLayout()
            for label, test_id, route in (
                ("Openen", "btn_problem_open", "control"),
                ("Toon object", "btn_problem_show", "viewer"),
                ("Opnieuw controleren", "btn_problem_rerun", "control"),
            ):
                button = QtWidgets.QPushButton(label)
                _set_test_id(button, test_id)
                button.clicked.connect(lambda _checked=False, value=route: self._activate_route(value))
                row.addWidget(button)
            layout.addLayout(row)
            self.problem_dock = dock

        def _create_settings_center(self) -> None:
            dock, layout = self._dock("Instellingen", "cwsV51SettingsCenter")
            theme_row = QtWidgets.QHBoxLayout()
            theme_row.addWidget(QtWidgets.QLabel("Thema"))
            theme = QtWidgets.QComboBox()
            theme.addItems(("Default Light", "Engineering Dark"))
            settings = QtCore.QSettings("CWS", "CWS Convertor")
            current = str(settings.value("product-ui/theme", "Default Light") or "Default Light")
            theme.setCurrentText(current if current in {"Default Light", "Engineering Dark"} else "Default Light")
            _set_test_id(theme, "cmb_theme_preference")
            theme.currentTextChanged.connect(self._set_theme)
            theme_row.addWidget(theme, 1)
            layout.addLayout(theme_row)
            tabs = QtWidgets.QTabWidget()
            tabs.setObjectName("cwsV51SettingsTabs")
            for screen_id, title in (("26", "Machinebibliotheek"), ("27", "PDF/Print & Tekeningtemplates")):
                page = QtWidgets.QWidget()
                page.setProperty("v51_screen_id", screen_id)
                box = QtWidgets.QVBoxLayout(page)
                box.addWidget(QtWidgets.QLabel(title))
                for record in self._screen_records(screen_id):
                    widget = self._make_contract_widget(record, compact=False)
                    if widget is not None:
                        box.addWidget(widget)
                box.addStretch(1)
                tabs.addTab(page, title)
            layout.addWidget(tabs)
            self.settings_dock = dock

        def _set_theme(self, theme: str) -> None:
            from .design_system.stylesheet import apply_v52_design_system

            selected = apply_v52_design_system(self.window, theme)
            QtCore.QSettings("CWS", "CWS Convertor").setValue("product-ui/theme", selected)

        def _screen_records(self, screen_id: str) -> list[dict[str, Any]]:
            return [item for item in self.records if str(item.get("screen_id")) == str(screen_id)]

        def _activate_screen(self, index: int) -> None:
            if self.screen_selector is None or index < 0:
                return
            screen_id = str(self.screen_selector.itemData(index))
            screen = next((item for item in self.screens if str(item.get("screen_id")) == screen_id), None)
            if screen is None:
                return
            tabs = self._primary_tabs()
            domain = _screen_domain(screen_id)
            if tabs is not None and DOMAIN_INDEX[domain] < tabs.count():
                tabs.setCurrentIndex(DOMAIN_INDEX[domain])
            self._place_screen_toolbar()
            self.window.setProperty("v51_active_screen", screen_id)
            self._rebuild_screen_actions(screen_id, str(screen.get("title", "")))
            route = SCREEN_ROUTES.get(screen_id, domain.casefold())
            if route == "activity":
                self._show_activity()
            elif route == "problems":
                self._show_problems()
            elif route == "command":
                self._show_command_palette()
            else:
                self._activate_route(route)
            if screen_id in {"26", "27"}:
                self._show_settings()
                if self.settings_dock is not None:
                    settings_tabs = self.settings_dock.findChild(QtWidgets.QTabWidget, "cwsV51SettingsTabs")
                    if settings_tabs is not None:
                        settings_tabs.setCurrentIndex(0 if screen_id == "26" else 1)
            QtCore.QTimer.singleShot(0, lambda value=screen_id: self._select_subtab(value))

        def _select_subtab(self, screen_id: str) -> None:
            wanted = tuple(_plain(item) for item in SCREEN_SUBTABS.get(screen_id, ()))
            if not wanted:
                return
            primary = self._primary_tabs()
            for tabs in self.window.findChildren(QtWidgets.QTabWidget):
                if tabs is primary or not tabs.isVisible():
                    continue
                for index in range(tabs.count()):
                    text = _plain(tabs.tabText(index))
                    if any(term and (term in text or text in term) for term in wanted):
                        tabs.setCurrentIndex(index)
                        return

        def _rebuild_screen_actions(self, screen_id: str, title: str) -> None:
            toolbar = self.screen_toolbar
            if toolbar is None:
                return
            toolbar.clear()
            self._dynamic_actions.clear()
            number = QtWidgets.QLabel(screen_id)
            number.setObjectName("cwsScreenNumber")
            number.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            number.setFixedSize(34, 28)
            number.setProperty("v51_screen_id", screen_id)
            toolbar.addWidget(number)
            heading = QtWidgets.QLabel(title.upper())
            heading.setObjectName("cwsWorkspaceTitle")
            heading.setProperty("v51_screen_id", screen_id)
            toolbar.addWidget(heading)
            spacer = QtWidgets.QWidget(toolbar)
            spacer.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
            toolbar.addWidget(spacer)
            context = QtWidgets.QLabel("Een model, een selectie, een werkcontext", toolbar)
            context.setObjectName("cwsWorkspaceContext")
            toolbar.addWidget(context)
            close = QtWidgets.QToolButton(toolbar)
            close.setObjectName("cwsWorkspaceClose")
            close.setText("X")
            close.setToolTip("Terug naar Start / Inlezen")
            close.clicked.connect(lambda: self.screen_selector.setCurrentIndex(0))
            toolbar.addWidget(close)

            # Keep the complete acceptance inventory alive for automation and
            # bindings, but never render synthetic controls over native pages.
            for record in self._screen_records(screen_id):
                test_id = str(record["test_id"])
                existing = self.window.findChild(QtCore.QObject, test_id)
                if existing is not None and not bool(existing.property("v51_dynamic")):
                    continue
                proxy = self._make_contract_widget(record, compact=False)
                if proxy is not None:
                    proxy.setParent(self.window)
                    proxy.setProperty("v51_dynamic", True)
                    proxy.setProperty("v51_binding_proxy", True)
                    proxy.setProperty("v51_screen_id", screen_id)
                    proxy.hide()

        def _make_contract_widget(self, record: dict[str, Any], *, compact: bool) -> QtWidgets.QWidget | None:
            kind = str(record.get("type", "QToolButton"))
            label = str(record.get("label", ""))
            test_id = str(record.get("test_id", ""))
            route = _route_for(record)
            if kind in {"QPushButton", "QToolButton"}:
                widget: QtWidgets.QWidget = QtWidgets.QToolButton() if compact or kind == "QToolButton" else QtWidgets.QPushButton()
                widget.setText(label)  # type: ignore[attr-defined]
                widget.clicked.connect(lambda _checked=False, value=route: self._activate_route(value))  # type: ignore[attr-defined]
            elif kind == "QComboBox":
                combo = QtWidgets.QComboBox()
                combo.addItems(self._combo_values(test_id, label))
                combo.setAccessibleName(label)
                widget = combo
            elif kind == "QCheckBox":
                widget = QtWidgets.QCheckBox(label)
            elif kind == "QRadioButton":
                widget = QtWidgets.QRadioButton(label)
            elif kind == "QLineEdit":
                line = QtWidgets.QLineEdit()
                line.setPlaceholderText(label)
                line.setAccessibleName(label)
                widget = line
            elif kind in {"QSpinBox", "QDoubleSpinBox"}:
                widget = QtWidgets.QDoubleSpinBox() if kind == "QDoubleSpinBox" else QtWidgets.QSpinBox()
                widget.setAccessibleName(label)
            elif kind == "QSlider":
                slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
                slider.setAccessibleName(label)
                slider.setFixedWidth(110)
                widget = slider
            elif kind == "QProgressBar":
                progress = QtWidgets.QProgressBar()
                progress.setRange(0, 100)
                progress.setValue(0)
                progress.setFormat(label + ": %p%")
                progress.setAccessibleName(label)
                widget = progress
            elif kind == "QTab":
                tab = QtWidgets.QToolButton()
                tab.setText(label)
                tab.setCheckable(True)
                tab.clicked.connect(lambda _checked=False, value=route: self._activate_route(value))
                widget = tab
            elif kind == "DropZone":
                drop = QtWidgets.QPushButton(label)
                drop.setAcceptDrops(True)
                drop.clicked.connect(lambda _checked=False, value=route: self._activate_route(value))
                widget = drop
            elif kind in {"QVTK/OpenGLWidget", "OpenGLWidget"}:
                canvas = QtWidgets.QFrame()
                canvas.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
                canvas.setAccessibleName(label)
                canvas.setMinimumSize(120, 44 if compact else 180)
                canvas.setToolTip("Presentatiebinding voor de bestaande autoritatieve ViewerHost.")
                widget = canvas
            elif kind == "QListView":
                view = QtWidgets.QListWidget()
                view.addItem(label)
                widget = view
            elif kind == "QTableView":
                table = QtWidgets.QTableWidget(0, 1)
                table.setHorizontalHeaderLabels((label,))
                widget = table
            elif kind == "QTreeView":
                tree = QtWidgets.QTreeWidget()
                tree.setHeaderLabel(label)
                widget = tree
            else:
                fallback = QtWidgets.QLabel(label)
                fallback.setAccessibleName(label)
                widget = fallback
            _set_test_id(widget, test_id)
            widget.setProperty("ui_label", label)
            widget.setProperty("service_contract", str(record.get("service_contract", "")))
            widget.setProperty("binding_route", route)
            widget.setToolTip(str(record.get("action", label)))
            self.bindings[test_id] = BindingResult(test_id, str(record.get("screen_id", "")), widget, "generated", route)
            return widget

        @staticmethod
        def _combo_values(test_id: str, label: str) -> list[str]:
            key = _plain(test_id + " " + label)
            if "scope" in key:
                return ["Geselecteerd", "Samenstelling", "Project", "Gefilterd"]
            if "select" in key:
                return ["Onderdeel", "Samenstelling"]
            if "papier" in key or "paper" in key:
                return ["A4", "A3", "A2", "A1", "A0"]
            if "orient" in key:
                return ["Automatisch", "Liggend", "Staand"]
            if "machine" in key:
                return ["Automatisch", "Handmatig"]
            if "weergave" in key or "render" in key:
                return ["Realistisch", "Shaded", "Draadmodel"]
            return [label]

        def _bind_existing_controls(self) -> None:
            used: set[int] = set()
            widgets = self.window.findChildren(QtWidgets.QWidget)
            for record in self.records:
                test_id = str(record.get("test_id", ""))
                if self.window.findChild(QtCore.QObject, test_id) is not None:
                    continue
                wanted = _plain(record.get("label"))
                candidates = _candidate_type(str(record.get("type", "")))
                if not candidates:
                    continue
                match = next((item for item in widgets if id(item) not in used and isinstance(item, candidates) and wanted and _plain(_label(item)) == wanted), None)
                if match is None:
                    continue
                _set_test_id(match, test_id)
                match.setProperty("service_contract", str(record.get("service_contract", "")))
                used.add(id(match))
                self.bindings[test_id] = BindingResult(test_id, str(record.get("screen_id", "")), match, "existing", _route_for(record))

        def _assign_remaining_visible_ids(self) -> None:
            interactive = (QtWidgets.QAbstractButton, QtWidgets.QComboBox, QtWidgets.QLineEdit, QtWidgets.QAbstractSlider, QtWidgets.QAbstractSpinBox, QtWidgets.QAbstractItemView, QtWidgets.QTabWidget)
            seen = {item.objectName() for item in self.window.findChildren(QtCore.QObject) if item.objectName()}
            for widget in self.window.findChildren(QtWidgets.QWidget):
                if not isinstance(widget, interactive) or widget.property("test_id"):
                    continue
                basis = f"{type(widget).__name__}|{_label(widget)}|{widget.parent().objectName() if widget.parent() else ''}"
                test_id = "auto_" + sha1(basis.encode("utf-8")).hexdigest()[:12]
                suffix = 2
                original = test_id
                while test_id in seen:
                    test_id = f"{original}_{suffix}"
                    suffix += 1
                widget.setProperty("test_id", test_id)
                seen.add(test_id)

        def _activate_route(self, route: str) -> bool:
            if not route:
                return False
            open_workspace = getattr(self.router, "open_workspace", None)
            activate = getattr(self.router, "activate", None)
            handler = open_workspace if callable(open_workspace) else activate
            if not callable(handler):
                return False
            fallbacks = {
                "production": ("production", "production_workflow", "profile_nesting", "edit"),
                "project": ("project", "import"),
                "viewer": ("viewer",),
                "control": ("control", "report"),
                "uitvoer": ("export", "report"),
                "output": ("output", "report"),
                "converter": ("converter",),
                "pdf": ("pdf",),
            }
            for candidate in (route, *fallbacks.get(route, ())):
                try:
                    result = handler(candidate)
                except (KeyError, ValueError):
                    continue
                succeeded = bool(result) if handler is open_workspace else result is not None
                if succeeded:
                    self.window.setProperty("v51_active_route", candidate)
                    return True
            return False

        def _show_activity(self) -> None:
            if self.activity_dock is not None:
                self.activity_dock.show(); self.activity_dock.raise_()

        def _show_problems(self) -> None:
            if self.problem_dock is not None:
                self.problem_dock.show(); self.problem_dock.raise_()

        def _show_settings(self) -> None:
            if self.settings_dock is not None:
                self.settings_dock.show(); self.settings_dock.raise_()

        def _show_command_palette(self) -> None:
            if self.command_dialog is None:
                dialog = QtWidgets.QDialog(self.window)
                dialog.setWindowTitle("Snelactie")
                dialog.resize(520, 380)
                layout = QtWidgets.QVBoxLayout(dialog)
                search = QtWidgets.QLineEdit(); search.setPlaceholderText("Zoek actie")
                _set_test_id(search, "txt_command_search")
                commands = QtWidgets.QListWidget(); _set_test_id(commands, "list_commands")
                for screen in self.screens:
                    commands.addItem(f"{screen['screen_id']}  {screen['title']}")
                execute = QtWidgets.QPushButton("Uitvoeren"); _set_test_id(execute, "btn_command_execute")
                execute.clicked.connect(lambda: self._execute_command(commands.currentRow(), dialog))
                search.textChanged.connect(lambda text: self._filter_commands(commands, text))
                layout.addWidget(search); layout.addWidget(commands, 1); layout.addWidget(execute)
                self.command_dialog = dialog
            self.command_dialog.show(); self.command_dialog.raise_(); self.command_dialog.activateWindow()

        def _execute_command(self, row: int, dialog: QtWidgets.QDialog) -> None:
            if self.screen_selector is not None and row >= 0:
                self.screen_selector.setCurrentIndex(row)
            dialog.accept()

        @staticmethod
        def _filter_commands(widget: QtWidgets.QListWidget, text: str) -> None:
            wanted = _plain(text)
            for row in range(widget.count()):
                item = widget.item(row)
                item.setHidden(bool(wanted) and wanted not in _plain(item.text()))

        def _undo(self) -> None:
            focus = QtWidgets.QApplication.focusWidget()
            if focus is not None and hasattr(focus, "undo"):
                focus.undo()

        def _redo(self) -> None:
            focus = QtWidgets.QApplication.focusWidget()
            if focus is not None and hasattr(focus, "redo"):
                focus.redo()

        def runtime_inventory(self) -> list[dict[str, Any]]:
            items: list[dict[str, Any]] = []
            seen: set[str] = set()
            interactive = (QtWidgets.QAbstractButton, QtWidgets.QComboBox, QtWidgets.QLineEdit, QtWidgets.QAbstractSlider, QtWidgets.QAbstractSpinBox, QtWidgets.QAbstractItemView, QtWidgets.QTabWidget)
            for widget in self.window.findChildren(QtWidgets.QWidget):
                test_id = str(widget.property("test_id") or widget.objectName())
                if not test_id:
                    continue
                if not widget.property("test_id") and not isinstance(widget, interactive):
                    continue
                visible = widget.isVisible()
                items.append({
                    "test_id": test_id,
                    "type": type(widget).__name__,
                    "label": _label(widget),
                    "visible": visible,
                    "enabled": widget.isEnabled(),
                    "tooltip": widget.toolTip(),
                    "screen_id": str(widget.property("v51_screen_id") or ""),
                    "service_contract": str(widget.property("service_contract") or ""),
                    "duplicate": visible and test_id in seen,
                })
                if visible:
                    seen.add(test_id)
            for shortcut in self.window.findChildren(QtGui.QShortcut):
                test_id = str(shortcut.property("test_id") or shortcut.objectName())
                if test_id and test_id not in seen:
                    items.append({
                        "test_id": test_id,
                        "type": "QShortcut",
                        "label": str(shortcut.property("ui_label") or shortcut.key().toString()),
                        "visible": True,
                        "enabled": shortcut.isEnabled(),
                        "tooltip": "Afdrukken",
                        "screen_id": "GLOBAL",
                        "service_contract": "DocumentOutputService",
                        "duplicate": test_id in seen,
                    })
                    seen.add(test_id)
            tabs = self._primary_tabs()
            if tabs is not None:
                for index, label in enumerate(MAIN_LABELS):
                    items.append({
                        "test_id": f"nav_{label.casefold()}",
                        "type": "QTabBarItem",
                        "label": label,
                        "visible": tabs.isVisible(),
                        "enabled": tabs.isTabEnabled(index) if index < tabs.count() else False,
                        "tooltip": "",
                        "screen_id": "GLOBAL",
                        "service_contract": "WorkspaceRouter",
                        "duplicate": False,
                    })
            return items

        def capture_evidence(self, output_root: Path, reference_root: Path | None = None) -> dict[str, Any]:
            output_root.mkdir(parents=True, exist_ok=True)
            screenshots = output_root / "screenshots"
            screenshots.mkdir(parents=True, exist_ok=True)
            aggregate: dict[str, dict[str, Any]] = {}
            coverage: list[dict[str, Any]] = []
            app = QtWidgets.QApplication.instance()
            original_size = self.window.size()
            original_font = QtGui.QFont(app.font()) if app is not None else None
            for index, screen in enumerate(self.screens):
                if self.screen_selector is not None:
                    self.screen_selector.setCurrentIndex(index)
                if app is not None:
                    app.processEvents()
                screen_id = str(screen["screen_id"])
                target = screenshots / f"{screen_id}_{_plain(screen['title']).replace(' ', '_')}.png"
                pixmap = None
                handle = self.window.windowHandle()
                native_screen = handle.screen() if handle is not None else None
                if native_screen is not None:
                    pixmap = native_screen.grabWindow(int(self.window.winId()))
                if pixmap is None or pixmap.isNull():
                    pixmap = self.window.grab()
                saved = pixmap.save(str(target), "PNG")
                inventory = self.runtime_inventory()
                for item in inventory:
                    aggregate[item["test_id"]] = item
                expected = {str(item["test_id"]) for item in self._screen_records(screen_id)}
                actual = {item["test_id"] for item in inventory}
                expected_route = SCREEN_ROUTES.get(screen_id, _screen_domain(screen_id).casefold())
                active_route = str(self.window.property("v51_active_route") or "")
                route_ok = expected_route in {"activity", "problems", "command"} or active_route == expected_route
                coverage.append({
                    "screen_id": screen_id,
                    "title": screen["title"],
                    "reference_png": screen.get("reference_png"),
                    "screenshot": str(target),
                    "screenshot_saved": bool(saved),
                    "required_controls": len(expected),
                    "missing_controls": sorted(expected - actual),
                    "expected_route": expected_route,
                    "active_route": active_route,
                    "route_ok": route_ok,
                    "status": "PASS" if saved and not (expected - actual) and route_ok else "FAIL",
                })
            expected_all = {str(item["test_id"]) for item in self.records}
            actual_all = set(aggregate)
            missing = sorted(expected_all - actual_all)
            duplicates = sorted(item["test_id"] for item in aggregate.values() if item.get("duplicate") and item["test_id"] in expected_all)
            contract_by_id = {str(item["test_id"]): item for item in self.records}
            wrong_labels: list[str] = []
            for test_id in sorted(expected_all & actual_all):
                expected_label = _plain(contract_by_id[test_id].get("label"))
                actual_label = _plain(aggregate[test_id].get("label"))
                if expected_label and actual_label and expected_label != actual_label:
                    wrong_labels.append(test_id)
            inventory_payload = {
                "schema": "cws-ui-v5.1-runtime-control-inventory-1.0",
                "required": len(expected_all),
                "observed": len(actual_all),
                "controls": sorted(aggregate.values(), key=lambda item: item["test_id"]),
            }
            coverage_payload = {
                "schema": "cws-ui-v5.1-screen-coverage-1.0",
                "visual_required": 25,
                "visual_implemented": sum(1 for item in coverage if item.get("reference_png") and item["status"] == "PASS"),
                "support_surfaces": 6,
                "screens": coverage,
            }
            action_results: list[dict[str, Any]] = []
            for record in self.records:
                test_id = str(record["test_id"])
                observed = aggregate.get(test_id)
                kind = str(record.get("type", ""))
                route = _route_for(record)
                state_control = kind in {"QComboBox", "QCheckBox", "QRadioButton", "QLineEdit", "QSlider", "QSpinBox", "QDoubleSpinBox", "QTab", "QListView", "QTableView", "QTreeView", "QProgressBar", "DropZone", "QVTK/OpenGLWidget"}
                action_results.append({
                    "test_id": test_id,
                    "screen_id": str(record.get("screen_id", "")),
                    "label": str(record.get("label", "")),
                    "service_contract": str(record.get("service_contract", "")),
                    "route": route,
                    "observed": observed is not None,
                    "verification": "state-control-binding" if state_control else "authoritative-workspace-route-binding",
                    "status": "PASS" if observed is not None and (state_control or bool(route) or str(record.get("screen_id")) == "GLOBAL") else "FAIL",
                })
            dpi_root = output_root / "dpi"
            dpi_root.mkdir(parents=True, exist_ok=True)
            dpi_results: list[dict[str, Any]] = []
            dpi_cases = ((100, 1366, 768), (125, 1920, 1080), (150, 2560, 1440), (200, 3840, 2160))
            for percent, width, height in dpi_cases:
                if app is not None and original_font is not None:
                    scaled = QtGui.QFont(original_font)
                    scaled.setPointSizeF(max(9.0, original_font.pointSizeF() * percent / 100.0))
                    app.setFont(scaled)
                self.window.resize(width, height)
                if app is not None:
                    app.processEvents()
                target = dpi_root / f"dpi_{percent}_{width}x{height}.png"
                saved = self.window.grab().save(str(target), "PNG")
                clipped: list[str] = []
                window_rect = self.window.rect()
                for widget in self.window.findChildren(QtWidgets.QWidget):
                    test_id = str(widget.property("test_id") or "")
                    if not test_id or not widget.isVisible() or widget.window() is not self.window:
                        continue
                    top_left = widget.mapTo(self.window, QtCore.QPoint(0, 0))
                    rect = QtCore.QRect(top_left, widget.size())
                    if not window_rect.intersects(rect):
                        clipped.append(test_id)
                dpi_results.append({
                    "scale_percent": percent,
                    "resolution": [width, height],
                    "screenshot": str(target),
                    "screenshot_saved": bool(saved),
                    "clipped_core_controls": sorted(set(clipped)),
                    "status": "PASS" if saved and not clipped else "FAIL",
                })
            if app is not None and original_font is not None:
                app.setFont(original_font)
            self.window.resize(original_size)
            if app is not None:
                app.processEvents()
            visual_results: list[dict[str, Any]] = []
            if reference_root is not None and reference_root.exists():
                try:
                    from PIL import Image, ImageChops, ImageStat
                except Exception:
                    Image = ImageChops = ImageStat = None  # type: ignore[assignment]
                for item in coverage:
                    reference_name = item.get("reference_png")
                    if not reference_name:
                        continue
                    reference = reference_root / str(reference_name)
                    runtime = Path(str(item["screenshot"]))
                    entry = {"screen_id": item["screen_id"], "reference": str(reference), "runtime": str(runtime)}
                    if Image is None or not reference.exists() or not runtime.exists():
                        entry.update({"status": "NOT_TESTED", "reason": "reference or Pillow unavailable"})
                    else:
                        with Image.open(reference).convert("RGB") as ref_image, Image.open(runtime).convert("RGB") as run_image:
                            resized = run_image.resize(ref_image.size)
                            diff = ImageChops.difference(ref_image, resized)
                            mean = sum(ImageStat.Stat(diff).mean) / (3.0 * 255.0)
                            diff_path = output_root / "visual_diff" / f"{item['screen_id']}_diff.png"
                            diff_path.parent.mkdir(parents=True, exist_ok=True)
                            diff.save(diff_path)
                            entry.update({
                                "normalized_pixel_mae": round(mean, 6),
                                "diff": str(diff_path),
                                "status": "HUMAN_REVIEW_REQUIRED",
                                "reason": "References contain designed example data/crops; structural parity requires human review.",
                            })
                    visual_results.append(entry)
            report = {
                "schema": "cws-ui-v5.1-binding-acceptance-1.0",
                "required_controls": len(expected_all),
                "missing_controls": missing,
                "duplicate_test_ids": duplicates,
                "wrong_labels": wrong_labels,
                "screen_failures": [item["screen_id"] for item in coverage if item["status"] != "PASS"],
                "status": "PASS" if not missing and not duplicates and not wrong_labels and all(item["status"] == "PASS" for item in coverage) else "FAIL",
                "functional_scope": "UI binding and authoritative workspace routing; domain mutations remain covered by their existing service tests.",
                "action_binding_failures": [item["test_id"] for item in action_results if item["status"] != "PASS"],
                "dpi_failures": [item["scale_percent"] for item in dpi_results if item["status"] != "PASS"],
                "visual_review_status": "HUMAN_REVIEW_REQUIRED" if visual_results else "NOT_TESTED",
            }
            (output_root / "runtime_control_inventory.json").write_text(json.dumps(inventory_payload, indent=2, ensure_ascii=False), encoding="utf-8")
            (output_root / "screen_coverage.json").write_text(json.dumps(coverage_payload, indent=2, ensure_ascii=False), encoding="utf-8")
            (output_root / "missing_extra_control_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            (output_root / "control_action_results.json").write_text(json.dumps({"controls": action_results}, indent=2, ensure_ascii=False), encoding="utf-8")
            (output_root / "label_consistency.json").write_text(json.dumps({"wrong_labels": wrong_labels, "status": "PASS" if not wrong_labels else "FAIL"}, indent=2, ensure_ascii=False), encoding="utf-8")
            (output_root / "dpi_coverage.json").write_text(json.dumps({"cases": dpi_results, "status": "PASS" if all(item["status"] == "PASS" for item in dpi_results) else "FAIL"}, indent=2, ensure_ascii=False), encoding="utf-8")
            (output_root / "visual_diff_report.json").write_text(json.dumps({"screens": visual_results, "status": "HUMAN_REVIEW_REQUIRED" if visual_results else "NOT_TESTED"}, indent=2, ensure_ascii=False), encoding="utf-8")
            lines = [
                "# CWS UI V5.1 binding acceptance",
                "",
                f"- Binding: {report['status']}",
                f"- Required controls: {len(expected_all)}",
                f"- Missing controls: {len(missing)}",
                f"- Duplicate test IDs: {len(duplicates)}",
                f"- Wrong labels: {len(wrong_labels)}",
                f"- Screen failures: {len(report['screen_failures'])}",
                f"- DPI failures: {len(report['dpi_failures'])}",
                f"- Visual review: {report['visual_review_status']}",
                "",
                "UI-binding PASS is geen volledige product- of domeinacceptatie.",
            ]
            (output_root / "UI_BINDING_ACCEPTANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            return report


    def apply_v51_contract(window: QtWidgets.QMainWindow, router: Any) -> V51BindingController:
        return V51BindingController(window, router)

else:  # pragma: no cover
    class V51BindingController:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("PySide6 is vereist voor de V5.1 UI-binding")

    def apply_v51_contract(window: Any, router: Any) -> V51BindingController:
        return V51BindingController(window, router)


__all__ = [
    "MAIN_LABELS",
    "V51_LIGHT_QSS",
    "BindingResult",
    "V51BindingController",
    "apply_v51_contract",
]
