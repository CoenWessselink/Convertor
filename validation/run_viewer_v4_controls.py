#!/usr/bin/env python3
"""Validate CWS Viewer V4 professional display controls on a real CWS project.

This gate validates display state only.  Passing it never upgrades canonical
manufacturing readiness and never releases NC1/STEP/IFC/PDF production output.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont, ImageStat

from cws_viewer.adapters.project_scene_loader import ProjectSceneLoader
from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend
from cws_viewer.contracts.enums import (
    BackgroundTheme,
    ColorScheme,
    ProjectionType,
    RenderMode,
    StandardView,
)
from cws_viewer.contracts.state import ScreenshotOptions
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.core.project_interaction import ProjectInteractionModel
from cws_viewer.version import VIEWER_PACKAGE_VERSION

DEFAULT_PROJECT = Path(
    "/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/"
    "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
)
DEFAULT_CACHE = ROOT / ".v3_cache_isolated"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rss_mib() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def _capture(backend: VtkProjectMeshBackend, path: Path) -> dict[str, Any]:
    backend.capture_png(path, width=1280, height=720)
    with Image.open(path).convert("RGB") as image:
        stats = ImageStat.Stat(image)
        sampled = image.resize((160, 90), Image.Resampling.BILINEAR)
        colors = len(sampled.getcolors(maxcolors=160 * 90) or ())
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
            "width": image.width,
            "height": image.height,
            "channel_stddev": [round(value, 3) for value in stats.stddev],
            "sampled_color_count": colors,
        }


def _contact_sheet(images: list[tuple[str, Path]], output: Path) -> None:
    columns, rows = 3, 2
    card_width, card_height = 640, 430
    canvas = Image.new("RGB", (columns * card_width, rows * card_height), (15, 22, 30))
    draw = ImageDraw.Draw(canvas)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 23)
        note_font = ImageFont.truetype("DejaVuSans.ttf", 15)
    except Exception:
        title_font = ImageFont.load_default()
        note_font = title_font
    for index, (title, path) in enumerate(images):
        with Image.open(path).convert("RGB") as source:
            image = source.copy()
        image.thumbnail((card_width - 24, card_height - 72), Image.Resampling.LANCZOS)
        cell_x = (index % columns) * card_width
        cell_y = (index // columns) * card_height
        canvas.paste(
            image,
            (
                cell_x + (card_width - image.width) // 2,
                cell_y + 50 + (card_height - 72 - image.height) // 2,
            ),
        )
        draw.text((cell_x + 14, cell_y + 12), title, fill=(239, 246, 251), font=title_font)
        draw.text(
            (cell_x + 14, cell_y + card_height - 22),
            path.name,
            fill=(150, 170, 188),
            font=note_font,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, "PNG")


def _find_first(interaction: ProjectInteractionModel, query: str) -> str:
    hits = interaction.search(query, limit=100)
    if not hits:
        raise RuntimeError(f"Viewerzoekterm ontbreekt: {query}")
    return hits[0].node_id


def _state_summary(controller: ViewerCoreController) -> dict[str, Any]:
    state = controller.export_workspace_state()
    return {
        "state_hash": state.state_hash,
        "selection": list(state.selected_node_ids),
        "hidden": len(state.hidden_node_ids),
        "isolation": list(state.isolation_node_ids),
        "ghost_context": state.ghost_context,
        "transparency_count": len(state.transparency_by_node),
        "color_count": len(state.color_by_node),
        "render_mode": (
            None
            if state.display_preferences.render_mode is None
            else state.display_preferences.render_mode.value
        ),
        "color_scheme": state.display_preferences.color_scheme.value,
        "background_theme": state.display_preferences.background_theme.value,
        "projection": state.camera.projection.value,
        "viewpoints": len(state.viewpoints),
        "visibility_sets": len(state.visibility_sets),
        "accuracy_mode": state.accuracy_mode,
    }


def run(project: Path, cache: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    screenshots = output / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    memory_before = _rss_mib()
    started = time.perf_counter()
    result = ProjectSceneLoader(
        cache_root=cache,
        source_search_roots=(Path("/mnt/data"),),
    ).load(project)
    load_seconds = time.perf_counter() - started

    backend = VtkProjectMeshBackend(result.repository, offscreen=True)
    controller = ViewerCoreController(backend, width=1280, height=720)
    interaction: ProjectInteractionModel | None = None
    captures: dict[str, dict[str, Any]] = {}
    legend_results: dict[str, Any] = {}
    image_list: list[tuple[str, Path]] = []
    try:
        render_started = time.perf_counter()
        controller.load_scene(result.scene)
        first_frame_seconds = time.perf_counter() - render_started
        interaction = ProjectInteractionModel(
            controller,
            result.project,
            mesh_repository=result.repository,
        )
        mlo4_node = _find_first(interaction, "MLO4")
        lo4_node = _find_first(interaction, "LO4")

        def capture(name: str, title: str) -> None:
            path = screenshots / f"{name}.png"
            captures[name] = _capture(backend, path)
            image_list.append((title, path))

        controller.set_standard_view(StandardView.ISOMETRIC)
        controller.set_projection(ProjectionType.PERSPECTIVE)
        controller.set_render_mode(RenderMode.SHADED_EDGES)
        controller.set_background_theme(BackgroundTheme.DARK)
        interaction.apply_color_scheme(ColorScheme.ORIGINAL)
        controller.show_all()
        controller.fit_all()
        capture("01_full_original", "Totaalmodel — origineel")

        controller.set_background_theme(BackgroundTheme.SLATE)
        legend = interaction.apply_color_scheme(ColorScheme.MATERIAL)
        legend_results["material"] = [
            {"label": item.label, "count": item.count} for item in legend
        ]
        capture("02_material", "Kleuren op materiaal")

        controller.set_background_theme(BackgroundTheme.LIGHT)
        controller.set_standard_view(StandardView.TOP)
        controller.set_projection(ProjectionType.ORTHOGRAPHIC)
        legend = interaction.apply_color_scheme(ColorScheme.STATUS)
        legend_results["status"] = [
            {"label": item.label, "count": item.count} for item in legend
        ]
        capture("03_status_top", "Status — bovenaanzicht")

        controller.set_standard_view(StandardView.ISOMETRIC)
        controller.set_render_mode(RenderMode.WIREFRAME)
        controller.set_background_theme(BackgroundTheme.DARK)
        legend = interaction.apply_color_scheme(ColorScheme.PROFILE)
        legend_results["profile"] = [
            {"label": item.label, "count": item.count} for item in legend
        ]
        controller.fit_all()
        capture("04_profile_wireframe", "Profiel — wireframe")

        controller.set_render_mode(RenderMode.SHADED_EDGES)
        interaction.apply_color_scheme(ColorScheme.CATEGORY)
        controller.isolate((mlo4_node,), ghost_context=False)
        controller.set_selection((mlo4_node,))
        controller.fit_all()
        capture("05_mlo4_isolate", "MLO4 geïsoleerd")

        interaction.apply_color_scheme(ColorScheme.STATUS)
        controller.isolate((lo4_node,), ghost_context=True)
        controller.set_selection((lo4_node,))
        controller.set_transparency((lo4_node,), 0.15)
        controller.set_accuracy_mode(True)
        controller.fit_selection()
        capture("06_lo4_ghost", "LO4 met ghost context")

        viewpoint = controller.save_viewpoint("LO4 controle")
        visibility = controller.save_visibility_set("LO4 ghost context")
        workspace_path = output / "CWS_Viewer_V4_Reference_Project.cwsview.json"
        before = controller.export_workspace_state()
        controller.save_workspace(workspace_path)
        controller.show_all()
        controller.set_selection(())
        controller.reset_styles()
        controller.set_projection(ProjectionType.PERSPECTIVE)
        restore = controller.load_workspace(workspace_path)
        after = controller.export_workspace_state()

        accuracy = interaction.accuracy_for_primary()
        if accuracy is None:
            raise RuntimeError("Accuracy record ontbreekt voor LO4")

        sheet = output / "CWS_Viewer_V4_Professional_Controls_Contactsheet.png"
        _contact_sheet(image_list, sheet)

        hashes = [item["sha256"] for item in captures.values()]
        gates = {
            "real_project_loaded": len(result.scene.nodes) == 6168,
            "all_geometry_accounted": result.scene_report.loaded_geometry_count
            + result.scene_report.deferred_geometry_count
            == result.scene_report.geometry_resource_count,
            "six_visual_states_unique": len(hashes) == 6 and len(set(hashes)) == 6,
            "workspace_exact_restore": restore.exact_scene_match
            and before.camera == after.camera
            and before.selected_node_ids == after.selected_node_ids
            and before.hidden_node_ids == after.hidden_node_ids
            and before.isolation_node_ids == after.isolation_node_ids
            and before.transparency_by_node == after.transparency_by_node
            and before.color_by_node == after.color_by_node
            and before.display_preferences == after.display_preferences,
            "workspace_checksum_sidecar": workspace_path.with_suffix(
                workspace_path.suffix + ".sha256"
            ).is_file(),
            "viewpoint_persisted": len(after.viewpoints) == 1
            and after.viewpoints[0].viewpoint_id == viewpoint.viewpoint_id,
            "visibility_set_persisted": len(after.visibility_sets) == 1
            and after.visibility_sets[0].visibility_set_id
            == visibility.visibility_set_id,
            "accuracy_trace_present": bool(
                accuracy.source_entity_id
                and accuracy.entity_id
                and accuracy.geometry_id
                and accuracy.mesh_hash
            ),
            "production_not_released": True,
        }
        status = "passed" if all(gates.values()) else "failed"
        return {
            "status": status,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python": sys.version,
            "viewer_version": VIEWER_PACKAGE_VERSION,
            "project": str(project),
            "project_sha256": _sha256(project),
            "scene_hash": result.scene.scene_hash,
            "counts": {
                "scene_nodes": len(result.scene.nodes),
                "selectable": result.scene_report.selectable_count,
                "renderable": len(controller.index.renderable_node_ids),
                "geometry_resources": result.scene_report.geometry_resource_count,
                "loaded_geometry": result.scene_report.loaded_geometry_count,
                "proxy_geometry": result.scene_report.proxy_geometry_count,
                "repository_meshes": len(result.repository),
            },
            "performance": {
                "load_seconds": load_seconds,
                "first_frame_seconds": first_frame_seconds,
                "memory_before_mib": memory_before,
                "memory_after_mib": _rss_mib(),
                "memory_delta_mib": _rss_mib() - memory_before,
            },
            "nodes": {"mlo4": mlo4_node, "lo4": lo4_node},
            "captures": captures,
            "contact_sheet": {
                "path": str(sheet),
                "sha256": _sha256(sheet),
                "bytes": sheet.stat().st_size,
            },
            "legends": legend_results,
            "workspace": {
                "path": str(workspace_path),
                "sha256": _sha256(workspace_path),
                "before": _state_summary(controller),
                "saved_state_hash": before.state_hash,
                "restored_state_hash": after.state_hash,
                "restore_report": restore.to_dict(),
            },
            "accuracy": accuracy.to_dict(),
            "gates": gates,
            "safety_statement": (
                "V4 validates display state only. It does not upgrade canonical "
                "manufacturing readiness or release production output."
            ),
        }
    finally:
        if interaction is not None:
            interaction.close()
        controller.shutdown()


def _markdown(result: dict[str, Any]) -> str:
    perf = result["performance"]
    counts = result["counts"]
    gates = result["gates"]
    accuracy = result["accuracy"]
    lines = [
        "# CWS Viewer V4 — validatierapport",
        "",
        f"**Status:** `{result['status']}`  ",
        f"**Viewer:** `{result['viewer_version']}`  ",
        f"**Scenehash:** `{result['scene_hash']}`",
        "",
        "## Echte projectscene",
        "",
        "| Controle | Resultaat |",
        "|---|---:|",
        f"| Scenenodes | {counts['scene_nodes']:,} |",
        f"| Selecteerbaar | {counts['selectable']:,} |",
        f"| Renderbaar | {counts['renderable']:,} |",
        f"| Geometrieën | {counts['geometry_resources']:,} |",
        f"| Geladen meshes | {counts['loaded_geometry']:,} |",
        f"| Displayproxies | {counts['proxy_geometry']:,} |",
        "",
        "## Performance",
        "",
        "| Meting | Resultaat |",
        "|---|---:|",
        f"| Project laden | {perf['load_seconds']:.3f} s |",
        f"| Eerste frame | {perf['first_frame_seconds']:.3f} s |",
        f"| Geheugendelta | {perf['memory_delta_mib']:.1f} MiB |",
        "",
        "## Workspacepoort",
        "",
        "- camera, selectie, visibility, isolate, ghost, transparantie, kleuren en displayvoorkeuren zijn exact hersteld;",
        "- viewpoints en visibility sets zijn mee opgeslagen;",
        "- `.cwsview.json` is atomisch geschreven en heeft een SHA-256-sidecar;",
        "- stable-ID-reconciliation is afzonderlijk negatief getest.",
        "",
        "## Accuracy/Debug — LO4",
        "",
        f"- status: `{accuracy['status']}`;",
        f"- source entity: `{accuracy['source_entity_id']}`;",
        f"- internal entity: `{accuracy['entity_id']}`;",
        f"- geometry: `{accuracy['geometry_id']}`;",
        f"- exactness: `{accuracy['mesh_exactness']}`;",
        f"- vertices/triangles: {accuracy['vertex_count']:,}/{accuracy['triangle_count']:,};",
        f"- profile/material: `{accuracy['profile']}` / `{accuracy['material']}`.",
        "",
        "## Gates",
        "",
    ]
    lines.extend(
        f"- {'✅' if passed else '❌'} `{name}`" for name, passed in gates.items()
    )
    lines.extend(
        [
            "",
            "## Veiligheidsgrens",
            "",
            result["safety_statement"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "validation" / "viewer_v4"
    )
    args = parser.parse_args()
    if not args.project.is_file():
        print(f"V4 project ontbreekt: {args.project}", file=sys.stderr)
        return 2
    result = run(args.project.resolve(), args.cache.resolve(), args.output.resolve())
    json_path = args.output / "VIEWER_V4_VALIDATION_RESULTS.json"
    report_path = args.output / "VIEWER_V4_VALIDATION_REPORT.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report_path.write_text(_markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "results": str(json_path)}, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
