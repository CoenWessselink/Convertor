from __future__ import annotations

from io import BytesIO
import argparse
import json
from pathlib import Path
import sys
import tempfile

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession, Transform3D
from cws_convertor.steel_model.adapter import build_steel_model_snapshot
from cws_convertor.steel_model.viewer_boundary import build_viewer_host_snapshot
from cws_convertor.viewer.mesh_resources import build_viewer_mesh_resource
from cws_convertor.viewer.vtk_backend import VtkOffscreenRenderer
from cws_convertor.viewer.workspace import ViewerWorkspaceState


def _export_step(path: Path) -> None:
    import cadquery as cq

    cq.exporters.export(cq.Workplane("XY").box(100.0, 50.0, 10.0).val(), str(path))


def _translation(x: float, y: float, z: float) -> Transform3D:
    return Transform3D(
        [
            [1.0, 0.0, 0.0, x],
            [0.0, 1.0, 0.0, y],
            [0.0, 0.0, 1.0, z],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def _fingerprint(rendered: bytes, blank: bytes) -> dict[str, object]:
    image = Image.open(BytesIO(rendered)).convert("RGB")
    background = Image.open(BytesIO(blank)).convert("RGB")
    mask = ImageChops.difference(image, background).convert("L").point(
        lambda value: 255 if value >= 8 else 0
    )
    bbox = mask.getbbox()
    if bbox is None:
        raise AssertionError("VTK-uitvoer bevat geen zichtbare meshpixels")
    histogram = mask.histogram()
    pixels = mask.load()
    total_x = 0.0
    total_y = 0.0
    count = 0
    for y in range(mask.height):
        for x in range(mask.width):
            if pixels[x, y]:
                total_x += x
                total_y += y
                count += 1
    return {
        "viewport": [image.width, image.height],
        "changed_pixel_count": int(histogram[255]),
        "object_bbox_px": list(bbox),
        "centroid_px": [round(total_x / count, 3), round(total_y / count, 3)],
    }


def run(output: Path, image_output: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="cws_phase_b_mesh_") as folder_name:
        source = Path(folder_name) / "verified-box.step"
        _export_step(source)
        session = ProjectSession.new("Phase B mesh evidence")
        try:
            registration = session.register_sources(
                [source],
                include_step_geometry=True,
            )[0]
            session.semantic_import_source(registration.source.source_id)
            part = next(iter(session.project.parts.values()))
            part.global_placement = _translation(1000.0, 2000.0, 3000.0)
            inspection = session.inspect_part_source_geometry(
                part.internal_id,
                persist=False,
            )
            steel_model = build_steel_model_snapshot(session.project)
            state = ViewerWorkspaceState(
                steel_model,
                build_viewer_host_snapshot(steel_model),
            )
            resource = build_viewer_mesh_resource(
                inspection,
                project_id=steel_model.project_id,
                entity=state.entity(part.internal_id),
                binding=state.binding(part.internal_id),
            )
            renderer = VtkOffscreenRenderer(width=360, height=260)
            try:
                blank = renderer.render()
                renderer.command("scene.load", state.scene_payload())
                patch = state.attach_mesh_resource(resource)
                renderer.command("scene.patch", patch)
                renderer.command("camera.standard_view", {"view": "isometric"})
                png = renderer.render()
                bounds = renderer.actor_bounds(part.internal_id)
                telemetry = renderer.telemetry()
            finally:
                renderer.close()
        finally:
            session.close()

    image_output.parent.mkdir(parents=True, exist_ok=True)
    image_output.write_bytes(png)
    center = [
        round((bounds[index * 2] + bounds[index * 2 + 1]) / 2.0, 6)
        for index in range(3)
    ]
    result = {
        "schema_version": "phase-b-mesh-renderer-evidence-v1",
        "status": "passed",
        "mesh_contract": {
            "geometry_basis": resource.geometry_basis,
            "geometry_content_sha256": resource.geometry_content_sha256,
            "units": resource.units,
            "coordinate_space": resource.coordinate_space,
            "vertex_count": len(resource.vertices_mm),
            "triangle_count": len(resource.triangles),
            "local_bounds_mm": list(resource.bounds_mm),
        },
        "source_evidence": {
            "status": inspection.status,
            "selection_verified": inspection.selection_verified,
            "production_geometry_exact": inspection.production_geometry_exact,
            "geometry_kind": inspection.geometry_kind,
        },
        "transform_evidence": {
            "expected_center_mm": [1000.0, 2000.0, 3000.0],
            "rendered_actor_center_mm": center,
            "status": "passed" if center == [1000.0, 2000.0, 3000.0] else "failed",
        },
        "visual_evidence": {
            **_fingerprint(png, blank),
            "image": image_output.name,
            "golden_policy": "tests/golden/viewer_mesh_v1.json",
        },
        "renderer": {
            key: value
            for key, value in telemetry.items()
            if key not in {"last_render_ms", "render_count"}
        },
        "regression_suite": {
            "script": "tests/viewer_mesh_renderer_smoke.py",
            "test_count": 4,
            "generated_instance_load_count": 600,
        },
        "open_gate": {
            "owner_validated_large_model": "manual_validation_required",
            "reason": (
                "De 600-instance test bewijst rendererbelasting en gedeelde geometrie, "
                "maar is geen eigenaar-gevalideerd complex referentiemodel."
            ),
        },
    }
    if result["transform_evidence"]["status"] != "passed":
        raise AssertionError(result["transform_evidence"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "validation" / "results" / "phase-b-mesh-renderer.json",
    )
    parser.add_argument(
        "--image",
        type=Path,
        default=ROOT / "validation" / "results" / "phase-b-mesh-renderer.png",
    )
    args = parser.parse_args()
    result = run(args.output, args.image)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
