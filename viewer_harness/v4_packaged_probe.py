#!/usr/bin/env python3
"""Packaged Qt/VTK/native probe for CWS Viewer V4 professional controls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.contracts.enums import BackgroundTheme, ColorScheme, RenderMode
from cws_viewer.core.diagnostics import collect_runtime_report
from cws_viewer.fixtures import build_lo4_reference_scene
from cws_viewer.ui_qt.project_viewer import run_real_project_viewer
from cws_viewer.ui_qt.qt_compat import require_qt
from cws_viewer.ui_qt.vtk_real_project_widget import VtkRealProjectWidget


def run_fixture_probe(report: Path, screenshot: Path | None) -> int:
    QtCore, QtGui, QtWidgets = require_qt()
    scene, repository = build_lo4_reference_scene()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setApplicationName("CWS Viewer V4 packaged probe")
    window = QtWidgets.QMainWindow()
    window.resize(1180, 760)
    widget = VtkRealProjectWidget(repository, window)
    window.setCentralWidget(widget)
    widget.load_scene(scene)
    window.show()

    def execute() -> None:
        payload: dict[str, Any] = {"status": "failed", "mode": "lo4_v4_fixture"}
        try:
            controller = widget.controller
            node_id = "entity:lo4-1"
            controller.set_selection((node_id,))
            controller.isolate((node_id,), ghost_context=True)
            controller.set_render_mode(RenderMode.SHADED_EDGES)
            controller.set_color_scheme(ColorScheme.MATERIAL)
            controller.set_background_theme(BackgroundTheme.SLATE)
            controller.set_accuracy_mode(True)
            controller.fit_selection()
            viewpoint = controller.save_viewpoint("Packaged V4")
            visibility = controller.save_visibility_set("Packaged visibility")
            x, y = widget.backend.node_display_point(node_id)
            pick = controller.pick_at(x, y)
            if pick is None or pick.node_id != node_id:
                raise RuntimeError("LO4 fixture-picking faalde")
            with tempfile.TemporaryDirectory(prefix="cws-viewer-v4-package-") as temp:
                workspace = Path(temp) / "package.cwsview.json"
                controller.save_workspace(workspace)
                before = controller.export_workspace_state()
                controller.show_all()
                controller.set_selection(())
                restore = controller.load_workspace(workspace)
                after = controller.export_workspace_state()
                if not restore.exact_scene_match or before.selected_node_ids != after.selected_node_ids:
                    raise RuntimeError("Packaged workspace restore faalde")
                workspace_hash = before.state_hash
            if screenshot:
                screenshot.parent.mkdir(parents=True, exist_ok=True)
                window.grab().save(str(screenshot), "PNG")
            runtime = collect_runtime_report(deep=True, scan_root=ROOT)
            if not runtime.all_required_ok:
                failed = [
                    probe.module
                    for probe in runtime.probes
                    if probe.module in {
                        "casadi", "cadquery", "OCP", "ifcopenshell", "fitz",
                        "matplotlib", "PySide6", "vtk"
                    }
                    and probe.status != "ok"
                ]
                raise RuntimeError(f"Native runtime-selftest faalde: {failed}")
            if runtime.forbidden_reference_count:
                raise RuntimeError("Verboden Trimble-binaries aangetroffen")
            payload.update(
                {
                    "status": "passed",
                    "scene_hash": scene.scene_hash,
                    "node_count": len(scene.nodes),
                    "geometry_count": len(repository),
                    "selection": list(controller.get_selection()),
                    "picked_node": pick.node_id,
                    "viewpoint_id": viewpoint.viewpoint_id,
                    "visibility_set_id": visibility.visibility_set_id,
                    "workspace_state_hash": workspace_hash,
                    "display_preferences": controller.get_display_preferences().to_dict(),
                    "accuracy_mode": controller.session.accuracy_mode,
                    "qt_version": QtCore.qVersion(),
                    "runtime": runtime.to_dict(),
                }
            )
        except Exception as exc:  # pragma: no cover - Windows evidence
            payload["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            window.close()
            app.quit()

    QtCore.QTimer.singleShot(1400, execute)
    return int(app.exec())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--cache", type=Path, default=Path("viewer_v4_cache"))
    parser.add_argument("--source-root", action="append", default=[])
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    if args.project:
        if not args.project.is_file():
            parser.error(f"Project ontbreekt: {args.project}")
        return run_real_project_viewer(
            args.project,
            cache_root=args.cache,
            source_search_roots=tuple(args.source_root),
            ci_smoke=True,
            report_path=args.report,
            screenshot_path=args.screenshot,
        )
    return run_fixture_probe(args.report, args.screenshot)


if __name__ == "__main__":
    raise SystemExit(main())
