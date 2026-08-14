#!/usr/bin/env python3
"""GUI/native self-test entrypoint for separate V1 PyInstaller spikes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.technology.contracts import TechnologyBackendName
from cws_viewer.technology.fixtures import build_box_grid_scene
from cws_viewer.ui_qt.qt_compat import require_qt


def run_gui_probe(
    backend: TechnologyBackendName | str,
    *,
    output: str | Path,
    node_count: int = 100,
    timeout_ms: int = 15_000,
) -> dict[str, Any]:
    name = TechnologyBackendName(backend)
    output_path = Path(output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot = output_path.with_suffix(".png")
    QtCore, QtGui, QtWidgets = require_qt()
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    application.setApplicationName("CWS Viewer V1 packaged probe")
    if name == TechnologyBackendName.OCCT_AIS:
        from cws_viewer.ui_qt.occt_widget import OcctAisWidget

        widget = OcctAisWidget()
    else:
        from cws_viewer.ui_qt.vtk_widget import VtkMeshWidget

        widget = VtkMeshWidget()
    widget.resize(800, 600)
    widget.show()
    scene = build_box_grid_scene(node_count)
    result: dict[str, Any] = {
        "status": "failed",
        "backend": name.value,
        "node_count": node_count,
        "platform": platform.platform(),
        "python": sys.version.replace("\n", " "),
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": str(Path(sys.executable).resolve()),
        "screenshot": str(screenshot),
        "error": "probe did not complete",
    }
    started = time.perf_counter()
    loop = QtCore.QEventLoop()

    def fail(message: str) -> None:
        result["error"] = message
        loop.quit()

    def execute() -> None:
        try:
            widget.load_scene(scene)
            application.processEvents()
            widget.backend.set_isometric_view()
            widget.backend.fit_all()
            widget.backend.render()
            application.processEvents()
            widget.backend.set_clip_plane(origin=scene.bounds.center, normal=scene.box_size.normalized())
            widget.backend.render()
            application.processEvents()
            widget.backend.clear_clip_planes()
            widget.backend.capture_png(screenshot)
            target = scene.instances[len(scene.instances) // 2]
            widget.backend.set_top_view()
            widget.backend.fit_all()
            widget.backend.render()
            application.processEvents()
            x, y = widget.backend.world_to_display(target.center)
            picked = widget.backend.pick_at(x, y)
            if picked != target.node_id:
                raise AssertionError(f"stable pick mismatch: expected {target.node_id}, got {picked}")
            result.update(
                {
                    "status": "passed",
                    "error": "",
                    "picked_node_id": picked,
                    "screenshot_bytes": screenshot.stat().st_size,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "capabilities": widget.backend.capabilities().__dict__
                    if hasattr(widget.backend.capabilities(), "__dict__")
                    else {
                        field: getattr(widget.backend.capabilities(), field)
                        for field in widget.backend.capabilities().__dataclass_fields__
                    },
                }
            )
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            loop.quit()

    QtCore.QTimer.singleShot(250, execute)
    QtCore.QTimer.singleShot(timeout_ms, lambda: fail("timeout"))
    loop.exec()
    try:
        widget.close()
        application.processEvents()
    finally:
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--backend", required=True, choices=[item.value for item in TechnologyBackendName])
    result.add_argument("--output", required=True)
    result.add_argument("--nodes", type=int, default=100)
    return result


def main() -> int:
    args = parser().parse_args()
    report = run_gui_probe(args.backend, output=args.output, node_count=args.nodes)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
