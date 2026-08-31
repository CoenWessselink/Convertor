from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import statistics

from PySide6 import QtCore, QtWidgets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.ui_qt.u4_shell import CWSMainWindow
from cws_viewer.contracts.state import ScreenshotOptions
from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.ui_qt.vtk_real_project_widget import NavigationMode


def run(project_path: Path, output_path: Path, screenshot_path: Path) -> dict[str, object]:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = CWSMainWindow()
    window.resize(1600, 900)
    window.show()
    started = {"value": 0.0}
    report: dict[str, object] = {
        "schema": "cws-full-acceptance-qt-progressive-exact-1.0",
        "status": "FAIL",
        "project_path": str(project_path),
    }

    def percentile(values: list[float], ratio: float) -> float:
        ordered = sorted(values)
        position = (len(ordered) - 1) * ratio
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        fraction = position - low
        return ordered[low] + (ordered[high] - ordered[low]) * fraction

    def rss_mb() -> float:
        try:
            import psutil
            return psutil.Process().memory_info().rss / (1024.0 * 1024.0)
        except Exception:
            return 0.0

    def open_project() -> None:
        started["value"] = time.perf_counter()
        window._open_project(project_path)

    def progress(_percent: int, message: str) -> None:
        if "Eerste interactieve modelweergave gereed" in message and "first_frame_seconds" not in report:
            report["first_frame_seconds"] = time.perf_counter() - started["value"]
            report["first_frame_workspace"] = window._workspace_name(window.tabs.currentWidget())
            report["viewer_visible"] = window.project_page.isVisible()
            report["first_frame_groups"] = len(window.project_page.viewer.backend._mesh_groups)

    def finish(success: bool, error: str = "") -> None:
        if report.get("finished"):
            return
        report["finished"] = True
        if error:
            report["error"] = error
        report["status"] = "PASS" if success else "FAIL"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        window.close()
        app.quit()

    def poll() -> None:
        try:
            status = window.project_page.status.text()
            if status.startswith("Exacte geometrie-upgrade mislukt"):
                finish(False, status)
                return
            if status.startswith("Brongeometrie compleet"):
                workspace = window.project_page.workspace
                viewer = window.project_page.viewer
                repository = workspace.load_result.repository
                meshes = [repository.require(value) for value in repository.ids()]
                proxies = [mesh for mesh in meshes if mesh.exactness == "display_proxy"]
                node_id = viewer.controller.index.renderable_node_ids[0]
                viewer.controller.set_selection((node_id,), mode="replace")
                selected = viewer.controller.get_selection()
                window.project_page.transparency_slider.setValue(45)
                transparent_count = len(viewer.controller.session.transparency)
                window.project_page.pan_action.trigger()
                pan_ok = viewer.navigation_mode == NavigationMode.PAN
                window.project_page.orbit_action.trigger()
                orbit_ok = viewer.navigation_mode == NavigationMode.ORBIT
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                viewer.controller.screenshot_to_file(
                    screenshot_path,
                    ScreenshotOptions(width=1200, height=700, format="png"),
                )
                preferences = viewer.controller.get_display_preferences()
                backend = viewer.backend
                before_rss = rss_mb()
                frame_samples: list[float] = []
                input_samples: list[float] = []
                pick_samples: list[float] = []
                selection_samples: list[float] = []
                wrong_picks = 0
                interaction_quality = getattr(backend, "set_interaction_quality", None)
                if callable(interaction_quality):
                    interaction_quality(True)
                for index in range(36):
                    before = time.perf_counter()
                    viewer.controller.orbit(0.45, 0.12 if index % 2 else -0.12)
                    input_samples.append((time.perf_counter() - before) * 1000.0)
                    app.processEvents()
                if callable(interaction_quality):
                    interaction_quality(False)
                for _ in range(48):
                    before = time.perf_counter()
                    viewer.controller.render()
                    frame_samples.append((time.perf_counter() - before) * 1000.0)
                    app.processEvents()
                bounds = viewer.controller.index.world_bounds_by_node[node_id]
                screen_x, screen_y = backend.world_to_display(bounds.center)
                for _ in range(24):
                    before = time.perf_counter()
                    picked = viewer.controller.pick_at_level(
                        screen_x,
                        screen_y,
                        level=SelectionLevel.PART,
                        mode="replace",
                    )
                    pick_samples.append((time.perf_counter() - before) * 1000.0)
                    if picked is None:
                        wrong_picks += 1
                for _ in range(24):
                    before = time.perf_counter()
                    viewer.controller.set_selection((node_id,), mode="replace")
                    selection_samples.append((time.perf_counter() - before) * 1000.0)
                after_rss = rss_mb()
                metrics = {
                    "frame_p50_ms": percentile(frame_samples, 0.50),
                    "frame_p95_ms": percentile(frame_samples, 0.95),
                    "frame_p99_ms": percentile(frame_samples, 0.99),
                    "input_to_render_p95_ms": percentile(input_samples, 0.95),
                    "input_to_render_p99_ms": percentile(input_samples, 0.99),
                    "pick_p95_ms": percentile(pick_samples, 0.95),
                    "pick_p99_ms": percentile(pick_samples, 0.99),
                    "selection_p95_ms": percentile(selection_samples, 0.95),
                    "wrong_instance_picks": wrong_picks,
                    "freeze_over_100ms_count": sum(value > 100.0 for value in input_samples + frame_samples),
                    "rss_start_mb": before_rss,
                    "rss_end_mb": after_rss,
                    "rss_drift_percent": 0.0 if before_rss <= 0.0 else ((after_rss - before_rss) / before_rss) * 100.0,
                    "frame_sample_count": len(frame_samples),
                    "input_sample_count": len(input_samples),
                    "pick_sample_count": len(pick_samples),
                }
                report.update(
                    exact_seconds=time.perf_counter() - started["value"],
                    repository_meshes=len(meshes),
                    proxy_meshes=len(proxies),
                    exact_meshes=sum(mesh.exactness == "source_tessellation" for mesh in meshes),
                    render_groups=len(viewer.backend._mesh_groups),
                    selected_node_ids=list(selected),
                    selection_color=preferences.selection_color.to_tuple(),
                    transparent_node_count=transparent_count,
                    pan_mode=pan_ok,
                    orbit_mode=orbit_ok,
                    screenshot=str(screenshot_path),
                    performance_metrics=metrics,
                )
                first_frame = float(report.get("first_frame_seconds", 999.0))
                success = bool(
                    first_frame <= 5.0
                    and report.get("first_frame_workspace") == "viewer"
                    and report.get("viewer_visible")
                    and len(meshes) > 0
                    and not proxies
                    and len(selected) == 1
                    and preferences.selection_color.red >= 0.95
                    and preferences.selection_color.green >= 0.75
                    and transparent_count > 0
                    and pan_ok
                    and orbit_ok
                )
                finish(success, "" if success else "Een of meer vieweracceptatievoorwaarden faalden")
                return
        except Exception as exc:
            finish(False, f"{type(exc).__name__}: {exc}")
            return
        QtCore.QTimer.singleShot(100, poll)

    window.project_page.load_progress.connect(progress)
    QtCore.QTimer.singleShot(100, open_project)
    QtCore.QTimer.singleShot(200, poll)
    QtCore.QTimer.singleShot(120_000, lambda: finish(False, "Timeout na 120 seconden"))
    app.exec()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        args.project.expanduser().resolve(),
        args.output.expanduser().resolve(),
        args.screenshot.expanduser().resolve(),
    )
    print(json.dumps(report, indent=2))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
