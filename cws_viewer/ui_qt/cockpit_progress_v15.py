"""Visible scene-loading runner for CWS Viewer V15 preview.2."""
from __future__ import annotations

from pathlib import Path

from cws_viewer.adapters.project_scene_loader import ProjectSceneLoader
from cws_viewer.core.color_palette_feel_v2 import install_feel_v2_palette
from cws_viewer.ui_qt.cockpit_trimble_feel_v2 import CwsViewerV15TrimbleFeelV2CockpitWindow
from cws_viewer.ui_qt.design_system import DEFAULT_THEME, theme_qss
from cws_viewer.ui_qt.loading_dialog import create_loading_dialog
from cws_viewer.ui_qt.qt_compat import require_qt

PREVIEW2_VERSION = "1.4.0-v15-preview.2"


def run_cws_viewer_cockpit_v15(
    project_path: str | Path,
    *,
    cache_root: str | Path | None = None,
    source_search_roots: tuple[str | Path, ...] = (),
    ci_smoke: bool = False,
    screenshot_path: str | Path | None = None,
) -> int:
    """Open preview.2 while preserving the Phase-1 fast-start architecture."""
    QtCore, _QtGui, QtWidgets = require_qt()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setApplicationName("CWS Viewer")
    app.setOrganizationName("CWS")
    app.setStyleSheet(theme_qss(DEFAULT_THEME))
    install_feel_v2_palette()

    path = Path(project_path).expanduser().resolve()
    loading = create_loading_dialog(version=PREVIEW2_VERSION, source_path=path)
    loading.set_progress(
        0.04,
        "Projectstructuur openen…",
        "CWS controleert de geometriecache en leest IFC-presentatiekleuren naast de geometrie-identiteit.",
    )

    def geometry_progress(fraction: float, message: str) -> None:
        value = 0.08 + 0.82 * max(0.0, min(1.0, float(fraction)))
        loading.restore_determinate()
        loading.set_progress(
            value,
            message or "3D-geometrie laden…",
            "Gecachte geometrie wordt parallel voorbereid; ontbrekende IFC/STEP-geometrie blijft crash-geïsoleerd en fail-closed.",
        )

    try:
        result = ProjectSceneLoader(
            cache_root=cache_root,
            source_search_roots=source_search_roots,
        ).load(path, progress=geometry_progress)
        hits = int(getattr(result.geometry_report, "cache_hit_count", 0) or 0)
        requested = int(getattr(result.geometry_report, "requested_count", 0) or 0)
        source_styles = sum(
            1 for style in result.scene.styles if style.style_id.startswith("style-source-ifc-")
        )
        loading.set_progress(
            0.92,
            "3D Viewer openen…",
            f"Geometrie gereed · cache {hits}/{requested} · {source_styles} IFC-bronkleur(en). Viewer, Views en selectie worden eerst geactiveerd.",
        )
        window = CwsViewerV15TrimbleFeelV2CockpitWindow(result)
        loading.set_progress(
            0.985,
            "Model zichtbaar maken…",
            "preview.2 gereed: waterpas orbit, bronkleuren, contactschaduw, geselecteerde highlight, Views-strip en live meten.",
        )
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

            QtCore.QTimer.singleShot(950, verify)
        return int(app.exec())
    finally:
        if loading is not None:
            try:
                loading.close()
                app.processEvents()
            except Exception:
                pass


__all__ = ["PREVIEW2_VERSION", "run_cws_viewer_cockpit_v15"]
