from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PIL import Image
from PySide6 import QtWidgets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.ui_qt.u4_shell import CWSMainWindow
from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import (
    VtkRealProjectWidgetFeelV2,
)


def _pump(app: QtWidgets.QApplication, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=float, default=25.0)
    args = parser.parse_args()

    result: dict[str, object] = {
        "schema": "cws-full-acceptance-qt-viewer-visual-1.0",
        "status": "FAIL",
        "project_path": str(args.project.resolve()),
    }
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    window: CWSMainWindow | None = None
    try:
        window = CWSMainWindow()
        window.resize(1920, 1080)
        window.show()
        window._open_project(args.project.resolve())
        started = False
        load_started_at = time.monotonic()
        deadline = load_started_at + args.wait_seconds
        while time.monotonic() < deadline:
            app.processEvents()
            worker_active = any(
                value is not None
                for value in (
                    window.project_page._worker,
                    window.project_page._exact_worker,
                )
            )
            started = started or worker_active
            if not worker_active and window.workspace is not None:
                break
            time.sleep(0.01)
        result["load_and_exact_seconds"] = time.monotonic() - load_started_at
        result["worker_activity_observed"] = started
        result["workspace_published"] = window.workspace is not None
        result["workers_finished"] = (
            window.project_page._worker is None
            and window.project_page._exact_worker is None
        )
        if not result["workspace_published"]:
            raise RuntimeError("Projectworkspace is niet tijdig gepubliceerd")
        if not result["workers_finished"]:
            raise RuntimeError("Exacte geometrieworker is niet tijdig afgerond")

        viewer = window.project_page.findChild(
            VtkRealProjectWidgetFeelV2,
            "cwsVtkRealProjectWidget",
        )
        if viewer is None or not viewer.isVisible():
            raise RuntimeError("De echte VTK-projectviewer is niet zichtbaar")

        backend = next(
            (
                value
                for value in vars(viewer.controller).values()
                if hasattr(value, "_node_instance")
            ),
            None,
        )
        if backend is None or getattr(backend, "_active_index", None) is None:
            raise RuntimeError("Actieve scene-index ontbreekt")
        scene_index = backend._active_index
        candidates: list[tuple[float, str]] = []
        for node_id in scene_index.renderable_node_ids:
            bounds = scene_index.world_bounds_by_node[node_id]
            size = bounds.size
            dimensions = sorted((size.x, size.y, size.z))
            if dimensions[2] >= 1000.0 and dimensions[1] >= 40.0 and dimensions[0] >= 4.0:
                candidates.append((bounds.center.z + dimensions[2] * 0.01, node_id))
        if not candidates:
            raise RuntimeError("Geen zichtbaar groot selectieonderdeel gevonden")
        selected_node_id = max(candidates)[1]
        viewer.controller.set_selection({selected_node_id})
        result["controller_selection"] = sorted(viewer.controller.get_selection())
        result["backend_type"] = None if backend is None else type(backend).__name__
        if backend is not None:
            node_instance = getattr(backend, "_node_instance", {})
            result["backend_has_selected_instance"] = selected_node_id in node_instance
            result["backend_highlighted_nodes"] = sorted(
                getattr(backend, "_highlighted_nodes", set())
            )
            result["selection_overlay_groups"] = len(
                getattr(backend, "_selection_groups", ())
            )
            if selected_node_id in node_instance:
                group, instance_index = node_instance[selected_node_id]
                result["selected_instance_rgba"] = [
                    int(value) for value in group.colors.GetTuple(instance_index)
                ]
        viewer.controller.fit_selection()
        _pump(app, 1.0)
        if backend is not None:
            fill_groups = getattr(backend, "_selection_fill_groups", ())
            result["selection_fill_groups"] = len(fill_groups)
            if fill_groups:
                actor = fill_groups[0].actor
                prop = actor.GetProperty()
                result["selection_fill_actor"] = {
                    "visible": bool(actor.GetVisibility()),
                    "color": list(prop.GetColor()),
                    "opacity": float(prop.GetOpacity()),
                    "representation": int(prop.GetRepresentation()),
                    "scalar_visibility": bool(actor.GetMapper().GetScalarVisibility()),
                    "bounds": list(actor.GetBounds()),
                }

        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        viewer.controller.screenshot_to_file(str(args.screenshot))
        _pump(app, 0.25)
        if not args.screenshot.is_file():
            raise RuntimeError("Renderer-native screenshot ontbreekt")

        with Image.open(args.screenshot).convert("RGB") as image:
            pixels = list(image.getdata())
            non_background = sum(
                1 for red, green, blue in pixels if min(red, green, blue) < 225
            )
            yellow = sum(
                1
                for red, green, blue in pixels
                if red >= 190 and green >= 140 and blue <= 80
            )
            result.update(
                screenshot=str(args.screenshot.resolve()),
                screenshot_size=list(image.size),
                non_background_pixels=non_background,
                yellow_selection_pixels=yellow,
                selected_node_id=selected_node_id,
            )
        if non_background < 10_000:
            raise RuntimeError("Te weinig zichtbare modelpixels")
        if yellow < 20:
            raise RuntimeError("Gele selectie is niet zichtbaar")
        result["status"] = "PASS"
        return_code = 0
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return_code = 1
    finally:
        if window is not None:
            window.close()
            app.processEvents()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
