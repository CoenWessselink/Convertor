"""Visible V14 cockpit scene-loading runner.

Direct IFC/STEP intake already has a visible progress dialog in the certified
rc3 launcher.  V14 adds a second deterministic geometry/scene phase before the
new cockpit can be shown.  This runner keeps a visible window throughout that
phase so a large project never appears to disappear between intake and 3D.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.adapters.project_scene_loader import ProjectSceneLoader
from cws_viewer.ui_qt.cockpit import CwsViewerCockpitWindow
from cws_viewer.ui_qt.loading_dialog import create_loading_dialog
from cws_viewer.ui_qt.qt_compat import require_qt

VERSION = "1.3.0-rc1"


def run_cws_viewer_cockpit_with_progress(
    project_path: str | Path,
    *,
    cache_root: str | Path | None = None,
    source_search_roots: tuple[str | Path, ...] = (),
    ci_smoke: bool = False,
    screenshot_path: str | Path | None = None,
) -> int:
    """Load the real project scene while a visible progress dialog is active."""
    QtCore, _QtGui, QtWidgets = require_qt()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setApplicationName("CWS Viewer")
    app.setOrganizationName("CWS")
    path = Path(project_path).expanduser().resolve()
    loading = create_loading_dialog(version=VERSION, source_path=path)
    loading.set_progress(
        0.04,
        "Projectstructuur openen…",
        "De bron is ingelezen. Nu wordt de 3D-scene opgebouwd en de displaygeometrie veilig geladen.",
    )

    def geometry_progress(fraction: float, message: str) -> None:
        # The geometry coordinator reports 0..1. Reserve the final 8% for Qt
        # cockpit construction so the bar only reaches 100% when a window exists.
        value = 0.08 + 0.84 * max(0.0, min(1.0, float(fraction)))
        loading.restore_determinate()
        loading.set_progress(
            value,
            message or "3D-geometrie laden…",
            "IFC/STEP-displaygeometrie wordt crash-geïsoleerd opgebouwd. Bron- en productiegeometrie blijven ongewijzigd.",
        )

    try:
        result = ProjectSceneLoader(
            cache_root=cache_root,
            source_search_roots=source_search_roots,
        ).load(path, progress=geometry_progress)
        loading.set_progress(
            0.94,
            "Stamienen, eigenschappen en werkruimtes voorbereiden…",
            "CWS Viewer bouwt de lichte projectcockpit, selection-sync en reviewlagen op.",
        )
        window = CwsViewerCockpitWindow(result)
        loading.set_progress(0.99, "3D Viewer gereedmaken…")
        window.show()
        window.raise_()
        window.activateWindow()
        loading.finish_loading()
        loading = None

        if ci_smoke:
            def verify() -> None:
                try:
                    if screenshot_path:
                        shot = Path(screenshot_path)
                        shot.parent.mkdir(parents=True, exist_ok=True)
                        window.grab().save(str(shot), "PNG")
                finally:
                    window.close()
            QtCore.QTimer.singleShot(500, verify)
        return int(app.exec())
    finally:
        if loading is not None:
            try:
                loading.close()
                app.processEvents()
            except Exception:
                pass


__all__ = ["run_cws_viewer_cockpit_with_progress"]
