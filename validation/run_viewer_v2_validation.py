#!/usr/bin/env python3
"""Run the CWS Viewer V2 synthetic-scene acceptance gate."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont, ImageStat

from cws_viewer.backends.vtk_project import VtkProjectBackend
from cws_viewer.contracts.enums import ProjectionType, StandardView
from cws_viewer.contracts.state import ColorAssignment, ScenePatch
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.fixtures import build_synthetic_product_scene, stable_sample_node_ids
from cws_viewer.math3d import Rgba
from cws_viewer.version import VIEWER_PACKAGE_VERSION


def _version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]


def _rss_mib() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture(backend: VtkProjectBackend, path: Path) -> dict[str, Any]:
    backend.capture_png(path, width=1280, height=720)
    with Image.open(path).convert("RGB") as image:
        statistics_image = ImageStat.Stat(image)
        channel_stddev = tuple(round(value, 3) for value in statistics_image.stddev)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "width": 1280,
        "height": 720,
        "channel_stddev": channel_stddev,
    }


def _compose_contact_sheet(images: list[tuple[str, Path]], output: Path) -> None:
    loaded = [(title, Image.open(path).convert("RGB")) for title, path in images]
    card_width, card_height = 720, 450
    canvas = Image.new("RGB", (card_width * 2, card_height * 2), (18, 25, 34))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    for index, (title, image) in enumerate(loaded):
        image.thumbnail((card_width - 24, card_height - 58), Image.Resampling.LANCZOS)
        x = (index % 2) * card_width + (card_width - image.width) // 2
        y = (index // 2) * card_height + 45
        canvas.paste(image, (x, y))
        draw.text(((index % 2) * card_width + 18, (index // 2) * card_height + 10), title, fill=(226, 236, 245), font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, "PNG")


def run_validation(node_count: int, output_dir: Path, *, pick_samples: int = 50) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir = output_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    rss_before = _rss_mib()

    started = time.perf_counter()
    scene = build_synthetic_product_scene(node_count)
    scene_build_ms = (time.perf_counter() - started) * 1000.0
    deterministic = scene.scene_hash == build_synthetic_product_scene(node_count).scene_hash

    started = time.perf_counter()
    index = SceneIndex.build(scene)
    index_build_ms = (time.perf_counter() - started) * 1000.0

    backend = VtkProjectBackend(offscreen=True)
    controller = ViewerCoreController(backend, width=1280, height=720)
    screenshots: dict[str, Any] = {}
    try:
        started = time.perf_counter()
        controller.load_scene(scene)
        load_and_first_frame_ms = (time.perf_counter() - started) * 1000.0
        controller.set_standard_view(StandardView.ISOMETRIC)
        controller.fit_all()
        screenshots["full"] = _capture(backend, screenshots_dir / "01_full_model.png")

        frame_times: list[float] = []
        for _ in range(18):
            frame_started = time.perf_counter()
            controller.orbit(3.0, 0.5)
            frame_times.append((time.perf_counter() - frame_started) * 1000.0)
        controller.pan(0.015, -0.01)
        controller.zoom(1.08)

        controller.set_standard_view(StandardView.TOP)
        controller.set_projection(ProjectionType.ORTHOGRAPHIC)
        controller.fit_all()
        sample_ids = stable_sample_node_ids(node_count, sample_count=pick_samples)
        pick_times: list[float] = []
        picked_ids: list[str | None] = []
        for node_id in sample_ids:
            x, y = backend.node_display_point(node_id)
            pick_started = time.perf_counter()
            pick = controller.pick_at(x, y)
            pick_times.append((time.perf_counter() - pick_started) * 1000.0)
            picked_ids.append(pick.node_id if pick is not None else None)
        picking_correct = sum(
            1 for expected, actual in zip(sample_ids, picked_ids) if expected == actual
        )
        picking_rate = picking_correct / max(len(sample_ids), 1)

        selected = (sample_ids[len(sample_ids) // 2],)
        controller.set_selection(selected)
        controller.colorize((ColorAssignment(selected[0], Rgba(0.10, 0.92, 0.98, 1.0)),))
        controller.set_standard_view(StandardView.ISOMETRIC)
        controller.fit_selection()
        screenshots["selected"] = _capture(backend, screenshots_dir / "02_selected.png")

        hide_started = time.perf_counter()
        controller.hide(("node:assembly:0000",))
        hide_ms = (time.perf_counter() - hide_started) * 1000.0
        hidden_visible_count = len(controller.session.render_state(controller.index).visible_node_ids)
        controller.show(("node:assembly:0000",))

        isolate_started = time.perf_counter()
        controller.isolate(("node:assembly:0001",), ghost_context=False)
        isolate_ms = (time.perf_counter() - isolate_started) * 1000.0
        isolate_state = controller.session.render_state(controller.index)
        controller.set_standard_view(StandardView.ISOMETRIC)
        controller.fit_all()
        screenshots["isolate"] = _capture(backend, screenshots_dir / "03_isolate.png")

        controller.colorize(
            (ColorAssignment("node:assembly:0001", Rgba(0.10, 0.92, 0.98, 1.0)),)
        )
        controller.isolate(("node:assembly:0001",), ghost_context=True)
        ghost_state = controller.session.render_state(controller.index)
        controller.set_standard_view(StandardView.ISOMETRIC)
        controller.fit_all()
        screenshots["ghost"] = _capture(backend, screenshots_dir / "04_ghost_context.png")

        controller.set_selection(("node:item:000101", "node:item:000102"))
        controller.hide(("node:item:000103",))
        replacement = build_synthetic_product_scene(
            node_count,
            revision_id="V2-B",
            name_suffix="-revision-B",
        )
        reload_started = time.perf_counter()
        controller.update_scene(
            ScenePatch(
                expected_scene_hash=scene.scene_hash,
                replacement_scene=replacement,
                reason="V2 stable-ID reload gate",
            )
        )
        reload_ms = (time.perf_counter() - reload_started) * 1000.0
        stable_reload = (
            controller.get_selection() == ("node:item:000101", "node:item:000102")
            and "node:item:000103" in controller.session.hidden
            and controller.session.scene_hash == replacement.scene_hash
        )

        rss_after = _rss_mib()
        contact_sheet = output_dir / "CWS_Viewer_V2_Core_Contactsheet.png"
        _compose_contact_sheet(
            [
                ("Volledig model", Path(screenshots["full"]["path"])),
                ("Selectie", Path(screenshots["selected"]["path"])),
                ("Isoleren", Path(screenshots["isolate"]["path"])),
                ("Ghost context", Path(screenshots["ghost"]["path"])),
            ],
            contact_sheet,
        )

        screenshot_hashes = {item["sha256"] for item in screenshots.values()}
        screenshots_are_visual = all(
            item["bytes"] > 10_000 and max(item["channel_stddev"]) > 5.0
            for item in screenshots.values()
        )
        acceptance = {
            "renderable_count_10k": len(index.renderable_node_ids) == node_count,
            "deterministic_scene_hash": deterministic,
            "navigation_executed": len(frame_times) == 18,
            "picking_p95_under_100_ms": _p95(pick_times) < 100.0,
            "picking_100_percent": picking_rate == 1.0,
            "hide_show": hidden_visible_count == max(0, node_count - min(100, node_count)),
            "isolate": len(isolate_state.visible_node_ids) == min(100, max(0, node_count - 100)),
            "ghost_context": len(ghost_state.visible_node_ids) == node_count and len(ghost_state.ghosted_node_ids) == max(0, node_count - min(100, max(0, node_count - 100))),
            "stable_ids_after_reload": stable_reload,
            "screenshots_created": all(Path(item["path"]).exists() for item in screenshots.values()),
            "screenshots_distinct": len(screenshot_hashes) == len(screenshots),
            "screenshots_visual_content": screenshots_are_visual,
        }
        status = "passed" if all(acceptance.values()) else "failed"
        result = {
            "status": status,
            "phase": "V2",
            "viewer_version": VIEWER_PACKAGE_VERSION,
            "started_at": started_at,
            "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python": sys.version,
            "dependencies": {
                "vtk": _version("vtk"),
                "OCP": _version("cadquery-ocp"),
                "PySide6": _version("PySide6"),
                "Pillow": _version("Pillow"),
            },
            "scene": {
                "node_count": len(scene.nodes),
                "renderable_count": len(index.renderable_node_ids),
                "assembly_count": index.counts_by_kind().get("assembly", 0),
                "scene_hash": scene.scene_hash,
                "replacement_scene_hash": replacement.scene_hash,
                "deterministic": deterministic,
            },
            "timings_ms": {
                "scene_build": round(scene_build_ms, 3),
                "index_build": round(index_build_ms, 3),
                "load_and_first_frame": round(load_and_first_frame_ms, 3),
                "orbit_mean": round(statistics.fmean(frame_times), 3),
                "orbit_p95": round(_p95(frame_times), 3),
                "pick_mean": round(statistics.fmean(pick_times), 3),
                "pick_p95": round(_p95(pick_times), 3),
                "hide": round(hide_ms, 3),
                "isolate": round(isolate_ms, 3),
                "reload": round(reload_ms, 3),
            },
            "picking": {
                "sample_count": len(sample_ids),
                "correct_count": picking_correct,
                "success_rate": picking_rate,
            },
            "visibility": {
                "after_hide_visible": hidden_visible_count,
                "isolate_visible": len(isolate_state.visible_node_ids),
                "ghost_visible": len(ghost_state.visible_node_ids),
                "ghosted": len(ghost_state.ghosted_node_ids),
            },
            "memory_mib": {
                "before": round(rss_before, 3),
                "after": round(rss_after, 3),
                "delta": round(max(0.0, rss_after - rss_before), 3),
            },
            "stable_reload": stable_reload,
            "acceptance": acceptance,
            "screenshots": screenshots,
            "contact_sheet": {
                "path": str(contact_sheet),
                "bytes": contact_sheet.stat().st_size,
                "sha256": _sha256(contact_sheet),
            },
            "limitations": [
                "V2 rendert synthetische display-boxes; echte projectmeshresources volgen in V3.",
                "Exact source/canonical BREP en subshapepicking blijven gepland voor V6.",
                "PySide6 Qt-runtime is alleen via de Windows gate bewijsbaar wanneer lokaal niet geïnstalleerd.",
            ],
        }
        return result
    finally:
        controller.shutdown()


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    json_path = output_dir / "VIEWER_V2_VALIDATION_RESULTS.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_path = output_dir / "VIEWER_V2_METRICS.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["metric", "value"])
        for section in ("scene", "timings_ms", "picking", "visibility", "memory_mib"):
            for key, value in result[section].items():
                writer.writerow([f"{section}.{key}", value])
        for key, value in result["acceptance"].items():
            writer.writerow([f"acceptance.{key}", value])

    report = [
        "# CWS Viewer V2 — validatierapport",
        "",
        f"**Status:** {result['status']}",
        f"**Viewer:** {result['viewer_version']}",
        f"**Platform:** {result['platform']}",
        "",
        "## Acceptatiepoort",
        "",
        "| Controle | Resultaat |",
        "|---|---|",
    ]
    for key, value in result["acceptance"].items():
        report.append(f"| `{key}` | {'✅' if value else '❌'} |")
    report.extend(
        [
            "",
            "## Metingen",
            "",
            "| Metriek | Waarde |",
            "|---|---:|",
        ]
    )
    for key, value in result["timings_ms"].items():
        report.append(f"| {key} | {value} ms |")
    report.extend(
        [
            "",
            "## Scene",
            "",
            f"- Renderable nodes: **{result['scene']['renderable_count']:,}**",
            f"- Assemblies: **{result['scene']['assembly_count']:,}**",
            f"- Picking: **{result['picking']['correct_count']}/{result['picking']['sample_count']}**",
            f"- Scenehash: `{result['scene']['scene_hash']}`",
            f"- Stable reload: **{result['stable_reload']}**",
            "",
            "## Open grenzen",
            "",
        ]
    )
    report.extend(f"- {item}" for item in result["limitations"])
    (output_dir / "VIEWER_V2_VALIDATION_REPORT.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=10_000)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pick-samples", type=int, default=50)
    args = parser.parse_args()
    result = run_validation(args.nodes, args.output, pick_samples=args.pick_samples)
    write_outputs(result, args.output)
    print(json.dumps({"status": result["status"], "output": str(args.output)}, indent=2))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
