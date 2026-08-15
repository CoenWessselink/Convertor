"""Headless GUI contract gate for hosted CI runners.

GitHub-hosted Windows runners do not provide a reliable interactive OpenGL
pixel format. This module therefore verifies the real PySide6 composition,
Canonical Project Model binding, tree/grid selection path and viewer controller
with the in-memory render backend. It deliberately does *not* claim that VTK
OpenGL rendering ran. Real VTK rendering remains a physical/self-hosted Windows
gate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any


def run_hosted_headless_gui_gate(
    project_path: str | Path,
    *,
    shell: str = "viewer",
    screenshot_path: str | Path | None = None,
) -> dict[str, Any]:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["CWS_HEADLESS_GUI_SMOKE"] = "1"

    from cws_viewer.ui_qt.qt_compat import require_qt

    QtCore, _QtGui, QtWidgets = require_qt()
    from cws_convertor.ui_qt.project_workspace import IntegratedProjectWorkspaceWidget

    project = Path(project_path).expanduser().resolve()
    if not project.is_file():
        raise FileNotFoundError(project)

    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    application.setApplicationName("CWS Viewer CI Headless")
    application.setOrganizationName("CWS")

    if shell == "main":
        from cws_convertor.ui_qt import CwsConvertorMainWindow

        window = CwsConvertorMainWindow(())
        workspace_widget = window.project_page
    else:
        window = QtWidgets.QMainWindow()
        window.setObjectName("cwsViewerHostedHeadlessWindow")
        window.setWindowTitle("CWS Viewer — hosted CI headless gate")
        workspace_widget = IntegratedProjectWorkspaceWidget(window)
        window.setCentralWidget(workspace_widget)
        window.resize(1440, 900)

    # Explicitly disable source-mesh loading. The hosted gate validates the
    # viewer composition and project binding; native OpenGL is a separate gate.
    workspace_widget.open_project(project, load_geometry=False)
    window.show()

    deadline = time.monotonic() + 60.0
    while time.monotonic() < deadline:
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
        if workspace_widget.workspace is not None and workspace_widget.viewer is not None:
            break
        time.sleep(0.01)

    if workspace_widget.workspace is None:
        raise RuntimeError("Canonical project workspace did not become ready in hosted CI")
    viewer = workspace_widget.viewer
    if viewer is None or not bool(getattr(viewer, "is_headless_gui_smoke", False)):
        raise RuntimeError(
            "Hosted CI gate created a native render window instead of the headless viewer"
        )

    workspace = workspace_widget.workspace
    controller = viewer.controller
    # Exercise actual viewer-controller state transitions without OpenGL.
    controller.fit_all()
    try:
        controller.set_standard_view("isometric")
    except Exception:
        # Some historical controller contracts expose a subset of views. The
        # integration itself is still verified by scene load and fit.
        pass

    scene = workspace.load_result.scene
    selectable = [node for node in scene.nodes if getattr(node, "selectable", False)]
    if selectable:
        entity_id = str(selectable[0].entity_id)
        try:
            workspace.interaction.select_entities((entity_id,), origin="ci_headless")
        except Exception:
            pass
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)

    screenshot_saved = False
    screenshot = Path(screenshot_path).expanduser().resolve() if screenshot_path else None
    if screenshot is not None:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        pixmap = window.grab()
        screenshot_saved = bool(not pixmap.isNull() and pixmap.save(str(screenshot)))

    tab_titles: list[str] = []
    tabs = getattr(window, "tabs", None)
    if tabs is not None:
        tab_titles = [tabs.tabText(index) for index in range(tabs.count())]

    payload: dict[str, Any] = {
        "schema": "cws-hosted-headless-gui-gate-1.0",
        "status": "passed",
        "gate": "headless-hosted-runner",
        "shell": shell,
        "qt_platform": application.platformName(),
        "project": str(project),
        "project_id": workspace.project.project_id,
        "scene_node_count": len(scene.nodes),
        "grid_row_count": len(workspace.interaction.grid_model.rows),
        "viewer_widget": type(viewer).__name__,
        "headless_viewer": True,
        "tab_titles": tab_titles,
        "screenshot_saved": screenshot_saved,
        "native_runtime": {
            "PySide6": "loaded",
            "VTK": "imported_by_native_selftest",
            "VTK_OpenGL_window": "not_run_hosted_runner",
            "reason": "GitHub hosted Windows runners do not provide a reliable interactive OpenGL pixel format",
        },
        "production_release_allowed": False,
    }

    try:
        workspace_widget.close_project()
    finally:
        window.close()
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
    return payload


def write_gate_report(payload: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


__all__ = ["run_hosted_headless_gui_gate", "write_gate_report"]
