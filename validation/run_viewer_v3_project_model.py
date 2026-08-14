#!/usr/bin/env python3
"""Run the CWS Viewer V3 real-project acceptance gate.

This validation intentionally measures *display* geometry only.  A successful
result never upgrades canonical manufacturing readiness and never authorises
NC1/STEP/IFC/PDF production export.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont, ImageStat

from cws_viewer.adapters.project_scene_loader import ProjectSceneLoader
from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend
from cws_viewer.contracts.enums import ProjectionType, StandardView
from cws_viewer.contracts.geometry import TessellationSettings
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.core.project_interaction import ProjectInteractionModel
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.math3d import Matrix4
from cws_viewer.version import VIEWER_PACKAGE_VERSION

DEFAULT_PROJECT = Path(
    "/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/"
    "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
)
DEFAULT_CACHE = ROOT / ".v3_cache_isolated"


def _version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _rss_mib() -> float:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def _p95(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture(backend: VtkProjectMeshBackend, path: Path) -> dict[str, Any]:
    backend.capture_png(path, width=1280, height=720)
    with Image.open(path).convert("RGB") as image:
        stats = ImageStat.Stat(image)
        stddev = tuple(round(value, 3) for value in stats.stddev)
        colors = len(image.resize((160, 90)).getcolors(maxcolors=160 * 90) or ())
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "width": 1280,
        "height": 720,
        "channel_stddev": stddev,
        "sampled_color_count": colors,
    }


def _contact_sheet(images: list[tuple[str, Path]], output: Path) -> None:
    card_width, card_height = 840, 520
    canvas = Image.new("RGB", (card_width * 2, card_height * 2), (17, 24, 33))
    draw = ImageDraw.Draw(canvas)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 17)
    except Exception:
        title_font = ImageFont.load_default()
        small_font = title_font
    for index, (title, path) in enumerate(images):
        with Image.open(path).convert("RGB") as source:
            image = source.copy()
        image.thumbnail((card_width - 30, card_height - 88), Image.Resampling.LANCZOS)
        cell_x = (index % 2) * card_width
        cell_y = (index // 2) * card_height
        x = cell_x + (card_width - image.width) // 2
        y = cell_y + 60
        canvas.paste(image, (x, y))
        draw.text((cell_x + 18, cell_y + 14), title, fill=(235, 242, 248), font=title_font)
        draw.text(
            (cell_x + 18, cell_y + card_height - 25),
            path.name,
            fill=(152, 171, 189),
            font=small_font,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, "PNG")


def _entity_counts(project: Any) -> dict[str, int]:
    return {
        "assemblies": len(getattr(project, "assemblies", {}) or {}),
        "parts": len(getattr(project, "parts", {}) or {}),
        "purchased_items": len(getattr(project, "purchased_items", {}) or {}),
        "fasteners": len(getattr(project, "fasteners", {}) or {}),
        "welds": len(getattr(project, "welds", {}) or {}),
    }


def _proxy_exceptions(result: Any) -> list[dict[str, Any]]:
    by_geometry: dict[str, list[Any]] = defaultdict(list)
    for record in result.catalog.records_by_entity.values():
        by_geometry[record.geometry_id].append(record)
    values: list[dict[str, Any]] = []
    for geometry_id in result.repository.ids():
        mesh = result.repository.require(geometry_id)
        if mesh.exactness != "display_proxy":
            continue
        entities = []
        for record in by_geometry.get(geometry_id, ()):
            entity = result.project.get_entity(record.internal_id)
            entities.append(
                {
                    "internal_id": record.internal_id,
                    "source_entity_id": record.source_entity_id,
                    "source_item_ids": list(record.source_item_ids),
                    "entity_type": type(entity).__name__,
                    "name": str(getattr(entity, "name", "") or ""),
                    "part_position": str(getattr(entity, "part_position", "") or ""),
                    "profile": str(getattr(entity, "profile", "") or ""),
                    "material": str(getattr(entity, "material", "") or ""),
                    "length_mm": float(getattr(entity, "length_mm", 0) or 0),
                }
            )
        values.append(
            {
                "geometry_id": geometry_id,
                "provider": mesh.provider,
                "warnings": list(mesh.warnings),
                "bounds_mm": mesh.bounds.size.to_tuple() if mesh.bounds else (),
                "entities": entities,
                "safety_effect": "Alleen displayproxy; geen productieclaim of exportvrijgave.",
            }
        )
    return values


def _safe_pick_samples(
    backend: VtkProjectMeshBackend,
    controller: ViewerCoreController,
    node_ids: Iterable[str],
    *,
    target: int = 24,
    bucket_px: int = 36,
) -> tuple[list[str], list[str | None], list[float]]:
    """Select front-most, spatially separated pick targets.

    A complete BIM model often contains several object centres on one camera
    ray.  Testing a hidden centre would correctly select the front-most object
    and falsely report a mapping failure.  The gate therefore chooses the
    picker-consistent display-depth candidate per screen bucket before exercising the
    public pick API.
    """
    buckets: dict[tuple[int, int], tuple[str, int, int, float]] = {}
    for node_id in node_ids:
        try:
            x, y, z = backend.node_display_position(node_id)
        except Exception:
            continue
        if not (3 <= x < 1277 and 3 <= y < 717 and 0.0 <= z <= 1.0):
            continue
        key = (x // bucket_px, y // bucket_px)
        current = buckets.get(key)
        if current is None or z > current[3]:
            buckets[key] = (node_id, x, y, z)
    ordered = sorted(
        buckets.values(),
        key=lambda item: (item[2] // bucket_px, item[1] // bucket_px, item[3]),
    )
    if len(ordered) > target:
        step = len(ordered) / target
        candidates = [ordered[min(len(ordered) - 1, int(i * step))] for i in range(target)]
    else:
        candidates = ordered
    expected: list[str] = []
    actual: list[str | None] = []
    timings: list[float] = []
    for node_id, x, y, _ in candidates:
        started = time.perf_counter()
        pick = controller.pick_at(x, y)
        timings.append((time.perf_counter() - started) * 1000.0)
        expected.append(node_id)
        actual.append(None if pick is None else pick.node_id)
    return expected, actual, timings


def _isolated_pick_samples(
    backend: VtkProjectMeshBackend,
    controller: ViewerCoreController,
    node_ids: Iterable[str],
    *,
    target: int = 12,
) -> tuple[list[str], list[str | None], list[float], list[float]]:
    expected: list[str] = []
    actual: list[str | None] = []
    pick_times: list[float] = []
    cycle_times: list[float] = []
    for node_id in tuple(dict.fromkeys(node_ids))[:target]:
        cycle_started = time.perf_counter()
        controller.isolate((node_id,), ghost_context=False)
        controller.set_selection((node_id,))
        controller.fit_selection()
        x, y = backend.node_display_point(node_id)
        pick_started = time.perf_counter()
        pick = controller.pick_at(x, y)
        pick_times.append((time.perf_counter() - pick_started) * 1000.0)
        cycle_times.append((time.perf_counter() - cycle_started) * 1000.0)
        expected.append(node_id)
        actual.append(None if pick is None else pick.node_id)
    return expected, actual, pick_times, cycle_times


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({field for row in rows for field in row})
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_validation(project_path: Path, cache_root: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir = output_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    rss_before = _rss_mib()
    settings = TessellationSettings(
        linear_deflection_mm=2.0,
        angular_deflection_rad=0.45,
        circle_segments=20,
    )

    print("[V3] project + geometry laden", flush=True)
    load_started = time.perf_counter()
    result = ProjectSceneLoader(
        cache_root=cache_root,
        source_search_roots=(project_path.parent, Path("/mnt/data")),
        settings=settings,
    ).load(project_path)
    project_load_ms = (time.perf_counter() - load_started) * 1000.0
    rss_after_project = _rss_mib()

    project = result.project
    scene = result.scene
    repository = result.repository
    index_started = time.perf_counter()
    index = SceneIndex.build(scene)
    index_build_ms = (time.perf_counter() - index_started) * 1000.0

    entities = _entity_counts(project)
    exactness = Counter(repository.require(gid).exactness for gid in repository.ids())
    warning_counts = Counter(
        warning
        for gid in repository.ids()
        for warning in repository.require(gid).warnings
    )
    instance_counts = Counter(
        node.geometry_id
        for node in scene.nodes
        if node.geometry_id and repository.get(node.geometry_id) is not None
    )
    instanced_geometry_count = sum(1 for count in instance_counts.values() if count > 1)
    max_instance_count = max(instance_counts.values(), default=0)

    assemblies_mlo4 = [
        assembly
        for assembly in project.assemblies.values()
        if str(getattr(assembly, "assembly_mark", "") or "") == "MLO4"
    ]
    parts_lo4 = [
        part
        for part in project.parts.values()
        if str(getattr(part, "part_position", "") or "") == "LO4"
    ]
    mlo4_nodes = tuple(f"entity:{entity.internal_id}" for entity in assemblies_mlo4)
    lo4_nodes = tuple(f"entity:{entity.internal_id}" for entity in parts_lo4)
    lo4_geometry_ids = tuple(
        result.catalog.record_for_entity(entity.internal_id).geometry_id
        for entity in parts_lo4
        if result.catalog.record_for_entity(entity.internal_id) is not None
    )
    placement_max_delta = 0.0
    for part in parts_lo4:
        node_id = f"entity:{part.internal_id}"
        expected = Matrix4.from_rows(part.global_placement.matrix)
        actual = index.world_transform_by_node[node_id]
        placement_max_delta = max(
            placement_max_delta,
            max(abs(a - b) for a, b in zip(actual.values, expected.values)),
        )

    step_11881: dict[str, Any] = {}
    for part in project.parts.values():
        identity = getattr(part, "source_identity", None)
        source_id = str(getattr(identity, "source_file_id", "") or "")
        source = project.sources.get(source_id)
        if source is None or "11881" not in str(getattr(source, "file_name", "")):
            continue
        record = result.catalog.record_for_entity(part.internal_id)
        mesh = None if record is None else repository.get(record.geometry_id)
        step_11881 = {
            "part_id": part.internal_id,
            "name": str(getattr(part, "name", "") or ""),
            "source_file": str(getattr(source, "file_name", "") or ""),
            "geometry_id": "" if record is None else record.geometry_id,
            "solid_index": None if record is None else record.solid_index,
            "vertex_count": 0 if mesh is None else mesh.vertex_count,
            "triangle_count": 0 if mesh is None else mesh.triangle_count,
            "bounds_mm": () if mesh is None or mesh.bounds is None else mesh.bounds.size.to_tuple(),
            "exactness": "" if mesh is None else mesh.exactness,
            "provider": "" if mesh is None else mesh.provider,
        }
        break

    print("[V3] VTK backend initialiseren", flush=True)
    backend = VtkProjectMeshBackend(repository, offscreen=True)
    controller = ViewerCoreController(backend, width=1280, height=720)
    interaction: ProjectInteractionModel | None = None
    screenshots: dict[str, dict[str, Any]] = {}
    try:
        print("[V3] totaalmodel renderen", flush=True)
        render_started = time.perf_counter()
        controller.load_scene(scene)
        first_frame_ms = (time.perf_counter() - render_started) * 1000.0
        interaction = ProjectInteractionModel(controller, project)

        controller.set_standard_view(StandardView.ISOMETRIC)
        controller.set_projection(ProjectionType.PERSPECTIVE)
        controller.fit_all()
        screenshots["full"] = _capture(backend, screenshots_dir / "01_full_project.png")

        orbit_times: list[float] = []
        for _ in range(12):
            started = time.perf_counter()
            controller.orbit(2.5, 0.7)
            orbit_times.append((time.perf_counter() - started) * 1000.0)
        controller.pan(0.008, -0.004)
        controller.zoom(1.04)

        controller.set_standard_view(StandardView.TOP)
        controller.set_projection(ProjectionType.ORTHOGRAPHIC)
        controller.fit_all()
        sample_candidates = [
            node_id
            for node_id in index.renderable_node_ids
            if repository.get(index.node(node_id).geometry_id or "") is not None
        ]
        full_expected_picks, full_actual_picks, full_pick_times = _safe_pick_samples(
            backend, controller, sample_candidates, target=24
        )
        full_correct_picks = sum(
            expected == actual
            for expected, actual in zip(full_expected_picks, full_actual_picks)
        )
        isolated_candidates = [*lo4_nodes]
        if step_11881.get("part_id"):
            isolated_candidates.append(f"entity:{step_11881['part_id']}")
        for node_id in sample_candidates:
            if node_id not in isolated_candidates:
                isolated_candidates.append(node_id)
            if len(isolated_candidates) >= 12:
                break
        (
            expected_picks,
            actual_picks,
            pick_times,
            isolated_pick_cycle_times,
        ) = _isolated_pick_samples(
            backend, controller, isolated_candidates, target=12
        )
        correct_picks = sum(
            expected == actual for expected, actual in zip(expected_picks, actual_picks)
        )

        hide_ms = 0.0
        hidden_delta = 0
        isolate_ms = 0.0
        ghost_ms = 0.0
        isolated_visible = 0
        ghosted_count = 0
        if mlo4_nodes:
            controller.show_all()
            before_visible = len(controller.session.render_state(controller.index).visible_node_ids)
            started = time.perf_counter()
            controller.hide((mlo4_nodes[0],))
            hide_ms = (time.perf_counter() - started) * 1000.0
            hidden_visible = len(controller.session.render_state(controller.index).visible_node_ids)
            hidden_delta = before_visible - hidden_visible
            controller.show((mlo4_nodes[0],))

            started = time.perf_counter()
            controller.isolate((mlo4_nodes[0],), ghost_context=False)
            isolate_ms = (time.perf_counter() - started) * 1000.0
            isolated_state = controller.session.render_state(controller.index)
            isolated_visible = len(isolated_state.visible_node_ids)
            controller.set_standard_view(StandardView.ISOMETRIC)
            controller.fit_all()
            print("[V3] MLO4 isolate screenshot", flush=True)
            screenshots["mlo4_isolate"] = _capture(
                backend, screenshots_dir / "02_mlo4_isolate.png"
            )

            started = time.perf_counter()
            controller.isolate((mlo4_nodes[0],), ghost_context=True)
            ghost_ms = (time.perf_counter() - started) * 1000.0
            ghost_state = controller.session.render_state(controller.index)
            ghosted_count = len(ghost_state.ghosted_node_ids)
            controller.set_standard_view(StandardView.ISOMETRIC)
            controller.fit_all()
            print("[V3] MLO4 ghost screenshot", flush=True)
            screenshots["mlo4_ghost"] = _capture(
                backend, screenshots_dir / "03_mlo4_ghost.png"
            )

        lo4_pick_ok = False
        selection_sync_grid = False
        selection_sync_viewer = False
        property_count = 0
        search_mlo4_count = 0
        search_lo4_count = 0
        search_11881_count = 0
        search_ms = 0.0
        grid_rows = len(interaction.grid_model.rows)
        grid_group_count = len(interaction.grid_model.groups("material"))
        if interaction is not None:
            started = time.perf_counter()
            mlo4_hits = interaction.search("MLO4", limit=100)
            lo4_hits = interaction.search("LO4", limit=100)
            step_hits = interaction.search("11881", limit=100)
            search_ms = (time.perf_counter() - started) * 1000.0
            search_mlo4_count = len(mlo4_hits)
            search_lo4_count = len(lo4_hits)
            search_11881_count = len(step_hits)

        if lo4_nodes and interaction is not None:
            controller.isolate((lo4_nodes[0],), ghost_context=False)
            interaction.select_entities((parts_lo4[0].internal_id,), origin="grid")
            selection_sync_grid = interaction.selection.primary_node_id == lo4_nodes[0]
            controller.set_selection((lo4_nodes[0],))
            selection_sync_viewer = interaction.selection.primary_entity_id == parts_lo4[0].internal_id
            property_count = len(interaction.properties_for_primary())
            controller.set_standard_view(StandardView.ISOMETRIC)
            controller.fit_selection()
            print("[V3] LO4 selectiescreenshot", flush=True)
            screenshots["lo4_selected"] = _capture(
                backend, screenshots_dir / "04_lo4_selected.png"
            )
            x, y = backend.node_display_point(lo4_nodes[0])
            picked = controller.pick_at(x, y)
            lo4_pick_ok = picked is not None and picked.node_id == lo4_nodes[0]

        rss_after_render = _rss_mib()
    finally:
        if interaction is not None:
            interaction.close()
        controller.shutdown()

    contact_sheet = output_dir / "CWS_Viewer_V3_Real_Project_Contactsheet.png"
    if len(screenshots) == 4:
        _contact_sheet(
            [
                ("Volledig Tekla-model", Path(screenshots["full"]["path"])),
                ("MLO4 geïsoleerd", Path(screenshots["mlo4_isolate"]["path"])),
                ("MLO4 met ghost context", Path(screenshots["mlo4_ghost"]["path"])),
                ("LO4 geselecteerd", Path(screenshots["lo4_selected"]["path"])),
            ],
            contact_sheet,
        )

    proxy_exceptions = _proxy_exceptions(result)
    (output_dir / "DISPLAY_PROXY_EXCEPTIONS.json").write_text(
        json.dumps(proxy_exceptions, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    screenshot_hashes = {item["sha256"] for item in screenshots.values()}
    visual_screenshots = all(
        item["bytes"] > 20_000
        and max(item["channel_stddev"]) > 5.0
        and item["sampled_color_count"] > 20
        for item in screenshots.values()
    )
    entity_node_ids = [
        node.entity_id for node in scene.nodes if node.node_id.startswith("entity:")
    ]
    acceptance = {
        "project_counts": entities
        == {
            "assemblies": 353,
            "parts": 2432,
            "purchased_items": 0,
            "fasteners": 723,
            "welds": 2654,
        },
        "scene_counts": len(scene.nodes) == 6168 and len(index.renderable_node_ids) == 5809,
        "all_geometry_loaded": len(repository) == 673 and result.geometry_report.failed_count == 0,
        "declared_display_limitations_only": exactness
        == Counter(
            {
                "source_tessellation": 577,
                "display_approximation": 94,
                "display_proxy": 2,
            }
        ),
        "geometry_cache_complete": result.geometry_report.cache_hit_count == 673,
        "no_duplicate_project_entities": len(entity_node_ids) == len(set(entity_node_ids)) == 6162,
        "mlo4_lo4_counts": len(assemblies_mlo4) == 4 and len(parts_lo4) == 4,
        "lo4_geometry_instanced": len(set(lo4_geometry_ids)) == 1 and len(lo4_geometry_ids) == 4,
        "placements_preserved": placement_max_delta <= 1e-6,
        "instancing_present": instanced_geometry_count > 0 and max_instance_count >= 4,
        "tree_grid_viewer_selection_sync": selection_sync_grid and selection_sync_viewer,
        "properties_and_search": property_count > 0
        and search_mlo4_count >= 4
        and search_lo4_count >= 4
        and search_11881_count >= 1,
        "real_step_11881_mesh": step_11881.get("vertex_count", 0) > 10_000
        and step_11881.get("triangle_count", 0) > 10_000
        and step_11881.get("exactness") == "source_tessellation",
        "navigation_executed": len(orbit_times) == 12,
        "picking_sample_available": len(expected_picks) >= 10,
        "isolated_picking_correct": correct_picks == len(expected_picks),
        "isolated_picking_p95_under_100_ms": _p95(pick_times) < 100.0,
        "mlo4_hide_isolate_ghost": hidden_delta >= 1
        and isolated_visible >= 1
        and ghosted_count >= 1,
        "lo4_pick": lo4_pick_ok,
        "screenshots_created": len(screenshots) == 4
        and all(Path(item["path"]).is_file() for item in screenshots.values()),
        "screenshots_distinct": len(screenshot_hashes) == len(screenshots) == 4,
        "screenshots_visual": visual_screenshots,
        "viewer_has_no_production_release_path": not hasattr(controller, "release_production")
        and not hasattr(controller, "export_nc1"),
    }
    hard_pass = all(acceptance.values())
    status = "passed_with_declared_display_limitations" if hard_pass else "failed"

    result_payload: dict[str, Any] = {
        "status": status,
        "phase": "V3",
        "scope": "real CWS project display model; not manufacturing truth",
        "viewer_version": VIEWER_PACKAGE_VERSION,
        "started_at": started_at,
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "vtk": _version("vtk"),
            "cadquery": _version("cadquery"),
            "numpy": _version("numpy"),
            "psutil": _version("psutil"),
            "pillow": _version("Pillow"),
            "display": os.environ.get("DISPLAY", ""),
        },
        "project": {
            "path": str(project_path),
            "sha256": _sha256(project_path),
            "schema_version": str(getattr(project, "schema_version", "")),
            "project_id": str(getattr(project, "project_id", "")),
            "name": str(getattr(project, "project_name", "")),
            "entity_counts": entities,
            "scene_node_count": len(scene.nodes),
            "selectable_count": result.scene_report.selectable_count,
            "renderable_count": len(index.renderable_node_ids),
            "scene_hash": scene.scene_hash,
        },
        "load": result.to_dict(),
        "geometry": {
            "unique_geometry_count": len(repository),
            "entity_geometry_count": result.catalog_report.entity_count,
            "exactness": dict(sorted(exactness.items())),
            "warning_counts": dict(sorted(warning_counts.items())),
            "total_mesh_bytes": repository.total_bytes,
            "instanced_geometry_count": instanced_geometry_count,
            "max_instance_count": max_instance_count,
            "proxy_exception_count": len(proxy_exceptions),
            "proxy_exception_file": str(output_dir / "DISPLAY_PROXY_EXCEPTIONS.json"),
        },
        "references": {
            "mlo4_assembly_count": len(assemblies_mlo4),
            "lo4_part_count": len(parts_lo4),
            "lo4_geometry_ids": list(lo4_geometry_ids),
            "lo4_placement_max_delta": placement_max_delta,
            "step_11881": step_11881,
        },
        "interaction": {
            "search_mlo4_count": search_mlo4_count,
            "search_lo4_count": search_lo4_count,
            "search_11881_count": search_11881_count,
            "search_elapsed_ms": search_ms,
            "grid_row_count": grid_rows,
            "grid_material_group_count": grid_group_count,
            "property_count": property_count,
            "selection_sync_grid_to_3d": selection_sync_grid,
            "selection_sync_3d_to_grid": selection_sync_viewer,
        },
        "performance": {
            "project_load_ms": project_load_ms,
            "project_loader_timings_ms": {
                name: seconds * 1000.0 for name, seconds in result.timings
            },
            "scene_index_ms": index_build_ms,
            "first_frame_ms": first_frame_ms,
            "orbit_average_ms": statistics.mean(orbit_times) if orbit_times else 0.0,
            "orbit_p95_ms": _p95(orbit_times),
            "full_scene_center_proxy_sample_count": len(full_expected_picks),
            "full_scene_center_proxy_correct_count": full_correct_picks,
            "full_scene_center_proxy_average_ms": statistics.mean(full_pick_times) if full_pick_times else 0.0,
            "full_scene_center_proxy_p95_ms": _p95(full_pick_times),
            "isolated_picking_sample_count": len(expected_picks),
            "isolated_picking_correct_count": correct_picks,
            "isolated_picking_average_ms": statistics.mean(pick_times) if pick_times else 0.0,
            "isolated_picking_p95_ms": _p95(pick_times),
            "isolated_pick_cycle_average_ms": statistics.mean(isolated_pick_cycle_times) if isolated_pick_cycle_times else 0.0,
            "isolated_pick_cycle_p95_ms": _p95(isolated_pick_cycle_times),
            "hide_ms": hide_ms,
            "isolate_ms": isolate_ms,
            "ghost_ms": ghost_ms,
            "hide_visible_delta": hidden_delta,
            "isolated_visible_count": isolated_visible,
            "ghosted_count": ghosted_count,
            "rss_before_mib": rss_before,
            "rss_after_project_mib": rss_after_project,
            "rss_after_render_mib": rss_after_render,
            "rss_delta_mib": max(0.0, rss_after_render - rss_before),
        },
        "screenshots": screenshots,
        "contact_sheet": str(contact_sheet) if contact_sheet.is_file() else "",
        "acceptance": acceptance,
        "limitations": [
            "94 unieke geometrieën zijn expliciete display-approximaties van profielradii/slopes; cache-hits behouden dezelfde waarschuwingsevidence.",
            "2 unieke IFC-geometrieën zijn zichtbare displayproxies nadat native tessellatie veilig geïsoleerd faalde.",
            "De viewer geeft geen productie-export vrij; canonical manufacturing validation blijft apart.",
            "Full-scene project picking gebruikt in V3 nog een centre-point proxy; overlappende centra zijn informatief gemeten en exact subshape-picking volgt in OCCT.",
            "PySide6/Windows packaging wordt in een afzonderlijke Windows-gate gevalideerd.",
        ],
    }

    output_json = output_dir / "VIEWER_V3_VALIDATION_RESULTS.json"
    output_json.write_text(
        json.dumps(result_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    geometry_rows = []
    for geometry_id in repository.ids():
        mesh = repository.require(geometry_id)
        geometry_rows.append(
            {
                "geometry_id": geometry_id,
                "exactness": mesh.exactness,
                "provider": mesh.provider,
                "vertex_count": mesh.vertex_count,
                "triangle_count": mesh.triangle_count,
                "byte_length": mesh.byte_length,
                "instance_count": instance_counts.get(geometry_id, 0),
                "warnings": " | ".join(mesh.warnings),
                "mesh_hash": mesh.mesh_hash,
                "source_geometry_hash": mesh.source_geometry_hash,
            }
        )
    _write_csv(output_dir / "VIEWER_V3_GEOMETRY_INVENTORY.csv", geometry_rows)

    print(
        json.dumps(
            {
                "status": status,
                "scene_nodes": len(scene.nodes),
                "renderable_nodes": len(index.renderable_node_ids),
                "unique_geometry": len(repository),
                "exactness": dict(exactness),
                "project_load_ms": round(project_load_ms, 3),
                "first_frame_ms": round(first_frame_ms, 3),
                "orbit_p95_ms": round(_p95(orbit_times), 3),
                "picking": f"{correct_picks}/{len(expected_picks)}",
                "isolated_picking_p95_ms": round(_p95(pick_times), 3),
                "full_scene_center_proxy": f"{full_correct_picks}/{len(full_expected_picks)}",
                "rss_delta_mib": round(max(0.0, rss_after_render - rss_before), 3),
                "output": str(output_json),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return result_payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "validation" / "viewer_v3"
    )
    args = parser.parse_args()
    if not args.project.is_file():
        parser.error(f"Referentieproject ontbreekt: {args.project}")
    payload = run_validation(args.project.resolve(), args.cache.resolve(), args.output.resolve())
    return 0 if payload["status"].startswith("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
