"""Native navigation of the existing product router; no duplicate workspace state."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from cws_viewer.ui_qt.qt_compat import require_qt
QtCore, QtGui, QtWidgets = require_qt()
ROUTES = (("import","Inlezen"),("viewer","Viewer"),("edit","Bewerken"),("converter","Converteren"),
          ("control","Controleren"),("pdf","PDF / Tekening"),("scribing","Scribing"),("bom","BOM / Hoeveelheden"),
          ("profile_nesting","Profielnesting"),("plate_nesting","Plaatnesting"),("export","Export Center"),("pdf_review","PDF-analyse"))


def save_project(window: Any) -> None:
    workspace = getattr(window, "workspace", None)
    if workspace is None:
        window.statusBar().showMessage("Open eerst een project", 5000); return
    session=workspace.session
    if session.read_only:
        window.statusBar().showMessage("Project is alleen-lezen", 5000); return
    try:
        path=getattr(session,"path",None)
        if path is None:
            value,_=QtWidgets.QFileDialog.getSaveFileName(window,"Project opslaan","","CWS project (*.cwscproj)")
            if not value:return
            path=Path(value)
        session.save(path, user="qt-gui", revision_message="Opgeslagen via hoofdprogramma")
        window.pdf_page._update_dimension_properties()
        window.statusBar().showMessage("Project opgeslagen",5000)
    except Exception as exc:
        window.statusBar().showMessage("Opslaan mislukt: "+str(exc),10000)


def sync_navigation(window: Any, route: str) -> None:
    for name, button in getattr(window,"native_workspace_buttons",{}).items():
        with QtCore.QSignalBlocker(button):button.setChecked(name==route)
    binding=getattr(window,"_v51_binding",None)
    if binding is not None:
        from .ui_v51_contract import SCREEN_ROUTES
        selector=binding.screen_selector
        if selector is not None:
            index=next((i for i in range(selector.count()) if SCREEN_ROUTES.get(str(selector.itemData(i)))==route),-1)
            if index>=0:
                with QtCore.QSignalBlocker(selector):selector.setCurrentIndex(index)
        if binding.screen_toolbar is not None:
            binding._place_screen_toolbar()


def install_native_navigation(window: Any) -> None:
    dock=QtWidgets.QDockWidget("Werkruimten",window)
    dock.setObjectName("cwsNativeWorkspaceNavigation")
    dock.setAllowedAreas(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea | QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
    dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable)
    body=QtWidgets.QWidget(dock);layout=QtWidgets.QVBoxLayout(body);layout.setContentsMargins(6,8,6,8);layout.setSpacing(5)
    group=QtWidgets.QButtonGroup(body);group.setExclusive(True);window.native_workspace_buttons={}
    for route,label in ROUTES:
        button=QtWidgets.QToolButton(body);button.setText(label);button.setCheckable(True)
        button.setObjectName("workspace_route_"+route);button.setAccessibleName(label)
        button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setMinimumWidth(174);button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,QtWidgets.QSizePolicy.Policy.Fixed)
        button.setToolTip(label+" — behoud project, selectie en viewer")
        button.clicked.connect(lambda _checked=False, name=route:window.workspace_router.open_workspace(name))
        group.addButton(button);layout.addWidget(button);window.native_workspace_buttons[route]=button
    layout.addStretch(1);dock.setWidget(body);window.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,dock)
    window.native_navigation_dock=dock
    menu=window.menuBar();menu.clear();menu.show()
    def action(host:Any,title:str,callback:Any,shortcut:str="") -> Any:
        item=QtGui.QAction(title,window);item.triggered.connect(callback)
        if shortcut:item.setShortcut(QtGui.QKeySequence(shortcut))
        host.addAction(item);return item
    filemenu=menu.addMenu("Bestand")
    action(filemenu,"Project openen…",window._choose_project,"Ctrl+O")
    action(filemenu,"Project opslaan",lambda:save_project(window),"Ctrl+S")
    action(filemenu,"Bestanden inlezen",lambda:window.workspace_router.open_workspace("import"))
    action(filemenu,"PDF openen…",lambda:window._ribbon_action("pdf:open"))
    action(filemenu,"Afsluiten",window.close,"Ctrl+Q")
    drawing=menu.addMenu("Tekening")
    action(drawing,"Geselecteerd object tekenen",lambda:window.workspace_router.open_workspace("pdf"))
    action(drawing,"PDF exporteren",window.pdf_page.export_pdf)
    action(drawing,"Trusted PDF exporteren",window.pdf_page.export_trusted_pdf)
    action(drawing,"Ongedaan maken",window._v51_binding._undo)
    action(drawing,"Opnieuw",window._v51_binding._redo)
    spaces=menu.addMenu("Werkruimten")
    for route,label in ROUTES:action(spaces,label,lambda _checked=False,name=route:window.workspace_router.open_workspace(name))
    spaces.addSeparator();spaces.addAction(dock.toggleViewAction())
    sync_navigation(window,getattr(window,"_active_workspace_name","import"))
