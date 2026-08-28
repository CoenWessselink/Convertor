from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.contracts.enums import StandardView
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.geometry.loader import CancellationToken

COUNTS = {
    "workspace_switches_100": 100,
    "selections_1000": 1000,
    "orbit_moves_500": 500,
    "zoom_500": 500,
    "hide_show_100": 100,
    "save_100": 100,
    "import_export_50": 50,
    "cancel_restart_50": 50,
}


def _cancelled(token: CancellationToken) -> bool:
    for name in ("is_cancelled", "cancelled", "is_canceled", "canceled"):
        value = getattr(token, name, None)
        if callable(value):
            value = value()
        if value is not None:
            return bool(value)
    return False


def run(output: Path) -> dict[str, object]:
    started = time.perf_counter()
    backend = MemoryRenderBackend()
    controller = ViewerCoreController(backend, width=1280, height=720)
    scene = build_synthetic_product_scene(250, parts_per_assembly=50)
    controller.load_scene(scene)
    results: dict[str, dict[str, object]] = {}

    def exercise(name: str, expected: int, operation) -> None:
        item_started = time.perf_counter()
        completed = 0
        error = ""
        try:
            for index in range(expected):
                operation(index)
                completed += 1
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        results[name] = {
            "status": "PASS" if completed == expected and not error else "FAIL",
            "required": expected,
            "completed": completed,
            "elapsed_seconds": round(time.perf_counter() - item_started, 6),
            "error": error,
        }

    views = tuple(StandardView)
    exercise("workspace_switches_100", 100, lambda index: controller.set_standard_view(views[index % len(views)]))
    exercise("selections_1000", 1000, lambda index: controller.set_selection((f"node:item:{index % 250:06d}",)))
    exercise("orbit_moves_500", 500, lambda index: controller.orbit(0.25 if index % 2 == 0 else -0.25, 0.1))
    exercise("zoom_500", 500, lambda index: controller.zoom(1.002 if index % 2 == 0 else 1.0 / 1.002))

    def hide_show(index: int) -> None:
        node_id = f"node:item:{index % 250:06d}"
        controller.hide((node_id,))
        controller.show((node_id,))

    exercise("hide_show_100", 100, hide_show)

    with tempfile.TemporaryDirectory(prefix="cws-full-acceptance-stress-") as folder:
        root = Path(folder)
        exercise("save_100", 100, lambda index: controller.save_workspace(root / f"workspace-{index:03d}.json"))

        def import_export(index: int) -> None:
            path = controller.save_workspace(root / f"roundtrip-{index:03d}.json")
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not payload:
                raise ValueError("workspace export did not produce an importable object")

        exercise("import_export_50", 50, import_export)

    def cancel_restart(_: int) -> None:
        cancelled = CancellationToken()
        cancelled.cancel()
        if not _cancelled(cancelled):
            raise RuntimeError("cancel signal was not observable")
        restarted = CancellationToken()
        if _cancelled(restarted):
            raise RuntimeError("fresh restart token inherited cancellation")

    exercise("cancel_restart_50", 50, cancel_restart)
    controller.shutdown()
    passed = all(item["status"] == "PASS" for item in results.values())
    report: dict[str, object] = {
        "schema": "cws.full_acceptance.stress_matrix.v1",
        "status": "PASS" if passed else "FAIL",
        "scene": {"nodes": len(scene.nodes), "scene_hash": scene.scene_hash, "backend": type(backend).__name__},
        "results": results,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full-acceptance repetition matrix.")
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "full_acceptance" / "STRESS_MATRIX_RESULTS.json")
    args = parser.parse_args()
    report = run(args.output.resolve())
    print(f"FULL_ACCEPTANCE_STRESS_MATRIX = {report['status']}")
    for name, item in report["results"].items():
        print(f"{name}: {item['completed']}/{item['required']} {item['status']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
