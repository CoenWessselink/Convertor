#!/usr/bin/env python3
"""Validate Viewer V4 professional controls, persistence and Accuracy mode."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
from io import BytesIO
import json
from pathlib import Path
import platform
import sys
import tempfile
import time
from types import SimpleNamespace
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.accuracy import ViewerAccuracyProvider
from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.backends.vtk_project import VtkProjectBackend
from cws_viewer.contracts.enums import BackgroundTheme, ColorScheme, ProjectionType, RenderMode, StandardView
from cws_viewer.contracts.geometry import MeshData
from cws_viewer.contracts.state import ScreenshotOptions
from cws_viewer.core.color_schemes import ProjectColorizer
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.geometry import MeshRepository
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.version import VIEWER_PACKAGE_VERSION


@dataclass
class _Entity:
    internal_id: str
    normalized_material: str
    normalized_profile: str
    classification_status: str
    properties: dict[str, str]
    source_identity: object
    assembly_ids: tuple[str, ...]
    validation_issues: tuple[Any, ...] = ()


class _Project:
    def __init__(self, entities: dict[str, _Entity]) -> None:
        self._entities = entities
        self.parts = entities
        self.assemblies: dict[str, Any] = {}
        self.purchased_items: dict[str, Any] = {}
        self.fasteners: dict[str, Any] = {}
        self.welds: dict[str, Any] = {}

    def get_entity(self, entity_id: str):
        return self._entities.get(entity_id)


def _project_for(index: SceneIndex) -> _Project:
    entities: dict[str, _Entity] = {}
    for number, node_id in enumerate(index.renderable_node_ids):
        node = index.node(node_id)
        status = "blocked" if number % 19 == 0 else "review" if number % 7 == 0 else "validated"
        entities[node.entity_id] = _Entity(
            internal_id=node.entity_id,
            normalized_material="S355JR" if number % 2 else "S235JR",
            normalized_profile="HEA140" if number % 3 else "STRIP5*120",
            classification_status=status,
            properties={"Phase": str(1 + number % 4)},
            source_identity=SimpleNamespace(source_file_id=f"source:{1 + number % 3}"),
            assembly_ids=(f"assembly:M{1 + number // 100:04d}",),
        )
    return _Project(entities)


def _accuracy_mesh(source_hash: str, *, exactness: str = "source_tessellation") -> MeshData:
    vertices = np.array(
        [[0, 0, 0], [80, 0, 0], [0, 16, 0], [0, 0, 12]], dtype=np.float64
    )
    triangles = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]], dtype=np.int32)
    return MeshData(
        vertices=vertices,
        triangles=triangles,
        source_geometry_hash=source_hash,
        provider="viewer-v4-validation",
        exactness=exactness,
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contact_sheet(images: list[tuple[str, Path]], output: Path) -> None:
    opened = [(label, Image.open(path).convert("RGB")) for label, path in images]
    width = max(image.width for _, image in opened)
    cell_height = max(image.height for _, image in opened) + 54
    columns = 2
    rows = (len(opened) + columns - 1) // columns
    sheet = Image.new("RGB", (width * columns, cell_height * rows), (18, 27, 38))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (label, image) in enumerate(opened):
        column = index % columns
        row = index // columns
        x = column * width
        y = row * cell_height
        sheet.paste(image, (x, y + 36))
        draw.rectangle((x, y, x + width, y + 35), fill=(29, 47, 63))
        draw.text((x + 12, y + 11), label, fill=(235, 244, 250), font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def run(output: Path, *, node_count: int) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    screenshots = output / "screenshots"
    screenshots.mkdir(exist_ok=True)
    started = time.perf_counter()
    scene = build_synthetic_product_scene(node_count, parts_per_assembly=100, revision_id="V4-A")
    index = SceneIndex.build(scene)
    project = _project_for(index)
    colorizer = ProjectColorizer(project, index)

    backend = VtkProjectBackend(offscreen=True)
    controller = ViewerCoreController(backend, width=1280, height=720)
    image_cases: list[tuple[str, Path]] = []
    timings: dict[str, float] = {}
    try:
        t0 = time.perf_counter()
        controller.load_scene(scene)
        timings["scene_load_ms"] = (time.perf_counter() - t0) * 1000.0
        controller.set_standard_view(StandardView.ISOMETRIC)
        controller.fit_all()

        def capture(label: str, filename: str) -> None:
            path = screenshots / filename
            controller.screenshot_to_file(path, ScreenshotOptions(1280, 720, "png"))
            image_cases.append((label, path))

        capture("Origineel · dark · shaded+edges", "01_original_dark_edges.png")
        controller.set_render_mode(RenderMode.SHADED)
        controller.set_background_theme(BackgroundTheme.SLATE)
        controller.reset_styles()
        controller.colorize(colorizer.assignments(ColorScheme.MATERIAL))
        controller.set_color_scheme(ColorScheme.MATERIAL)
        capture("Materiaal · slate · shaded", "02_material_slate_shaded.png")

        controller.set_render_mode(RenderMode.WIREFRAME)
        controller.set_background_theme(BackgroundTheme.LIGHT)
        controller.reset_styles()
        controller.colorize(colorizer.assignments(ColorScheme.STATUS))
        controller.set_color_scheme(ColorScheme.STATUS)
        capture("Status · light · wireframe", "03_status_light_wire.png")

        selected = "node:item:000101" if node_count > 101 else "node:item:000001"
        assembly = "node:assembly:0001" if node_count > 100 else "node:assembly:0000"
        controller.set_render_mode(RenderMode.SHADED_EDGES)
        controller.set_background_theme(BackgroundTheme.DARK)
        controller.reset_styles()
        controller.colorize(colorizer.assignments(ColorScheme.CATEGORY))
        controller.set_color_scheme(ColorScheme.CATEGORY)
        controller.set_selection((selected,))
        controller.isolate((assembly,), ghost_context=True)
        controller.fit_selection()
        capture("Selectie · isolate · ghost context", "04_selection_ghost.png")

        controller.set_projection(ProjectionType.ORTHOGRAPHIC)
        controller.set_accuracy_mode(True)
        viewpoint = controller.save_viewpoint("V4 validatie viewpoint", owner="validation")
        visibility = controller.save_visibility_set("V4 ghost visibility", owner="validation")

        workspace_path = output / "viewer_v4_validation.cwsview.json"
        controller.save_workspace(workspace_path)
        original_state = controller.export_workspace_state()

        memory = MemoryRenderBackend()
        restored = ViewerCoreController(memory)
        try:
            restored.load_scene(scene)
            restore_report = restored.load_workspace(workspace_path)
            restored_state = restored.export_workspace_state()
        finally:
            restored.shutdown()

        geometry_node = index.node(selected)
        repository = MeshRepository()
        assert geometry_node.geometry_id and geometry_node.geometry_hash
        geometry_resource = index.geometry_by_id[geometry_node.geometry_id]
        repository.put(
            geometry_node.geometry_id,
            _accuracy_mesh(geometry_resource.content_hash),
        )
        accuracy = ViewerAccuracyProvider(index, project, repository).record(selected)

        visual = {}
        for label, path in image_cases:
            image = Image.open(path).convert("RGB")
            visual[path.name] = {
                "label": label,
                "sha256": _sha(path),
                "bytes": path.stat().st_size,
                "variance": float(sum(ImageStat.Stat(image).var)),
                "size": list(image.size),
            }
        contact = output / "CWS_Viewer_V4_Professional_Controls_Contactsheet.png"
        _contact_sheet(image_cases, contact)

        workspace_equal = all(
            [
                original_state.camera == restored_state.camera,
                original_state.selected_node_ids == restored_state.selected_node_ids,
                original_state.hidden_node_ids == restored_state.hidden_node_ids,
                original_state.isolation_node_ids == restored_state.isolation_node_ids,
                original_state.transparency_by_node == restored_state.transparency_by_node,
                original_state.color_by_node == restored_state.color_by_node,
                original_state.display_preferences == restored_state.display_preferences,
                original_state.accuracy_mode == restored_state.accuracy_mode,
                len(restored_state.viewpoints) == 1,
                len(restored_state.visibility_sets) == 1,
            ]
        )
        hashes_unique = len({item["sha256"] for item in visual.values()}) == len(visual)
        hidden_line_blocked = False
        try:
            controller.set_render_mode(RenderMode.HIDDEN_LINE)
        except ViewerError as exc:
            hidden_line_blocked = exc.code == ViewerErrorCode.RENDERER_CAPABILITY_MISSING

        acceptance = {
            "scene_loaded": len(scene.nodes) > node_count,
            "render_modes_visual": hashes_unique,
            "screenshots_nonempty": all(item["bytes"] > 8_000 and item["variance"] > 20 for item in visual.values()),
            "workspace_exact_restore": bool(workspace_equal and restore_report.exact_scene_match),
            "workspace_checksum_sidecar": workspace_path.with_suffix(workspace_path.suffix + ".sha256").is_file(),
            "viewpoint_persisted": restored_state.viewpoints[0].viewpoint_id == viewpoint.viewpoint_id,
            "visibility_set_persisted": restored_state.visibility_sets[0].visibility_set_id == visibility.visibility_set_id,
            "accuracy_traceable": accuracy.status.value == "pass" and accuracy.node_id == selected,
            "color_schemes_deterministic": colorizer.assignments(ColorScheme.MATERIAL) == colorizer.assignments(ColorScheme.MATERIAL),
            "true_hidden_line_blocked": hidden_line_blocked,
            "no_production_release": True,
        }
        status = "passed" if all(acceptance.values()) else "failed"
        payload = {
            "schema_version": "1.0",
            "status": status,
            "viewer_version": VIEWER_PACKAGE_VERSION,
            "platform": platform.platform(),
            "python": sys.version.replace("\n", " "),
            "node_count": len(scene.nodes),
            "renderable_count": len(index.renderable_node_ids),
            "scene_hash": scene.scene_hash,
            "timings": timings,
            "workspace": {
                "path": str(workspace_path),
                "state_hash": original_state.state_hash,
                "file_sha256": _sha(workspace_path),
                "restore_report": restore_report.to_dict(),
                "functional_state_equal": workspace_equal,
            },
            "accuracy": accuracy.to_dict(),
            "visual": visual,
            "contactsheet": str(contact),
            "contactsheet_sha256": _sha(contact),
            "acceptance": acceptance,
            "steelconverter_requirement_mapping": {
                "product_name": "CWS Convertor",
                "steelmodel_mapping": "Canonical Project Model / Canonical Part Model",
                "accuracy_debug_mode": "implemented_in_v4",
                "expanded_measure_scope": "scheduled_v5",
                "scribing": "scheduled_v6",
            },
            "elapsed_seconds": time.perf_counter() - started,
        }
    finally:
        controller.shutdown()

    result_path = output / "VIEWER_V4_VALIDATION_RESULTS.json"
    result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = output / "VIEWER_V4_VALIDATION_REPORT.md"
    report.write_text(
        "# CWS Viewer V4 — validatierapport\n\n"
        f"- Status: **{payload['status']}**\n"
        f"- Viewer: `{payload['viewer_version']}`\n"
        f"- Scenenodes: **{payload['node_count']:,}**\n"
        f"- Renderables: **{payload['renderable_count']:,}**\n"
        f"- Scenehash: `{payload['scene_hash']}`\n"
        f"- Workspace state hash: `{payload['workspace']['state_hash']}`\n"
        f"- Accuracy record: **{payload['accuracy']['status'].upper()}**\n\n"
        "## Acceptatie\n\n"
        + "\n".join(
            f"- {'PASS' if value else 'FAIL'} — `{key}`" for key, value in payload["acceptance"].items()
        )
        + "\n\n## Begrenzingen\n\n"
        "- Dit is een display-/workspacevalidatie; de viewer geeft geen productie vrij.\n"
        "- Technische hidden-line removal is nog niet geïmplementeerd en wordt niet geclaimd.\n"
        "- PySide6/Windows packaged GUI blijft een afzonderlijke releasepoort.\n"
        "- De uitgebreide Measure-workspace uit de aanvullende superprompt volgt in V5.\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nodes", type=int, default=1_000)
    args = parser.parse_args()
    result = run(args.output.resolve(), node_count=args.nodes)
    print(json.dumps({"status": result["status"], "output": str(args.output.resolve())}, indent=2))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
