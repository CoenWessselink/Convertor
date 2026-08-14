from __future__ import annotations

from pathlib import Path
import copy
from dataclasses import replace
from io import BytesIO
import json
import os
import sys
import tempfile
import time
import tkinter as tk
import unittest

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import Part, ProjectSession, SourceIdentity, Transform3D
from cws_convertor.project.source_geometry import SourceGeometryInspection
from cws_convertor.steel_model.adapter import build_steel_model_snapshot
from cws_convertor.steel_model.contracts import AccuracyStatus
from cws_convertor.steel_model.viewer_boundary import build_viewer_host_snapshot
from cws_convertor.viewer.mesh_resources import (
    ViewerMeshResource,
    build_canonical_viewer_mesh_resource,
    build_viewer_mesh_resource,
)
from cws_convertor.viewer.vtk_backend import VtkOffscreenRenderer
from cws_convertor.viewer.workspace import ViewerWorkspaceState
from cws_convertor.ui.project_viewer import ProjectViewerPanel


GOLDEN = ROOT / "tests" / "golden" / "viewer_mesh_v1.json"
HEADLESS_GITHUB_WINDOWS = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def export_step(path: Path) -> None:
    import cadquery as cq

    shape = cq.Workplane("XY").box(100.0, 50.0, 10.0).val()
    cq.exporters.export(shape, str(path))


def translated(x: float, y: float, z: float) -> Transform3D:
    return Transform3D(
        [
            [1.0, 0.0, 0.0, x],
            [0.0, 1.0, 0.0, y],
            [0.0, 0.0, 1.0, z],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def state_for(session: ProjectSession) -> ViewerWorkspaceState:
    steel_model = build_steel_model_snapshot(session.project)
    return ViewerWorkspaceState(steel_model, build_viewer_host_snapshot(steel_model))


def visual_fingerprint(rendered: bytes, blank: bytes) -> dict[str, object]:
    image = Image.open(BytesIO(rendered)).convert("RGB")
    background = Image.open(BytesIO(blank)).convert("RGB")
    difference = ImageChops.difference(image, background).convert("L")
    mask = difference.point(lambda value: 255 if value >= 8 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise AssertionError("Rendered image contains no pixels different from the blank scene")
    histogram = mask.histogram()
    changed = int(histogram[255])
    centroid_x = 0.0
    centroid_y = 0.0
    weighted = 0
    pixels = mask.load()
    for y in range(mask.height):
        for x in range(mask.width):
            if pixels[x, y]:
                centroid_x += x
                centroid_y += y
                weighted += 1
    return {
        "viewport": [image.width, image.height],
        "changed_pixel_count": changed,
        "object_bbox_px": list(bbox),
        "centroid_px": [centroid_x / weighted, centroid_y / weighted],
    }


class ViewerMeshRendererTests(unittest.TestCase):
    @unittest.skipIf(
        HEADLESS_GITHUB_WINDOWS,
        "GitHub Windows runner has no stable OpenGL render context; native VTK pipeline is tested separately",
    )
    def test_exact_step_resource_hash_transform_and_visual_golden(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_viewer_step_") as folder_name:
            source = Path(folder_name) / "plate.step"
            export_step(source)
            session = ProjectSession.new("Viewer STEP")
            try:
                registration = session.register_sources(
                    [source],
                    include_step_geometry=True,
                )[0]
                session.semantic_import_source(registration.source.source_id)
                part = next(iter(session.project.parts.values()))
                part.global_placement = translated(1000.0, 2000.0, 3000.0)
                inspection = session.inspect_part_source_geometry(
                    part.internal_id,
                    persist=False,
                )
                state = state_for(session)
                entity = state.entity(part.internal_id)
                binding = state.binding(part.internal_id)
                resource = build_viewer_mesh_resource(
                    inspection,
                    project_id=state.steel_model.project_id,
                    entity=entity,
                    binding=binding,
                )
                repeated = build_viewer_mesh_resource(
                    inspection,
                    project_id=state.steel_model.project_id,
                    entity=entity,
                    binding=binding,
                )
                self.assertEqual(resource.geometry_content_sha256, repeated.geometry_content_sha256)
                self.assertEqual(resource.resource_sha256, repeated.resource_sha256)
                self.assertEqual(resource.geometry_basis, "source_native_brep")
                self.assertEqual(resource.units, "mm")
                self.assertEqual(resource.coordinate_space, "entity_local")
                extents = (
                    resource.bounds_mm[1] - resource.bounds_mm[0],
                    resource.bounds_mm[3] - resource.bounds_mm[2],
                    resource.bounds_mm[5] - resource.bounds_mm[4],
                )
                self.assertEqual(sorted(round(item, 6) for item in extents), [10.0, 50.0, 100.0])

                canonical_entity = replace(
                    entity,
                    geometry_kind="canonical_part",
                    accuracy_status=AccuracyStatus.TOLERANCE_VERIFIED,
                )
                canonical_binding = replace(
                    binding,
                    accuracy_status=AccuracyStatus.TOLERANCE_VERIFIED.value,
                )
                canonical_resource = build_canonical_viewer_mesh_resource(
                    inspection.native_shape,
                    project_id=state.steel_model.project_id,
                    entity=canonical_entity,
                    binding=canonical_binding,
                )
                self.assertEqual(
                    canonical_resource.geometry_basis,
                    "canonical_rebuild_brep",
                )
                with self.assertRaisesRegex(ValueError, "current canonical BREP"):
                    build_viewer_mesh_resource(
                        inspection,
                        project_id=state.steel_model.project_id,
                        entity=canonical_entity,
                        binding=canonical_binding,
                    )

                renderer = VtkOffscreenRenderer(width=360, height=260)
                try:
                    blank = renderer.render()
                    renderer.command("scene.load", state.scene_payload())
                    patch = state.attach_mesh_resource(resource)
                    renderer.command("scene.patch", patch)
                    renderer.command("camera.standard_view", {"view": "isometric"})
                    rendered = renderer.render()
                    bounds = renderer.actor_bounds(part.internal_id)
                    self.assertEqual(
                        [round((bounds[index * 2] + bounds[index * 2 + 1]) / 2.0, 6) for index in range(3)],
                        [1000.0, 2000.0, 3000.0],
                    )
                    self.assertEqual(renderer.telemetry()["actor_count"], 1)
                    self.assertEqual(renderer.telemetry()["unique_geometry_count"], 1)
                    fingerprint = visual_fingerprint(rendered, blank)
                finally:
                    renderer.close()

                golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
                self.assertEqual(fingerprint["viewport"], golden["viewport"])
                self.assertGreaterEqual(
                    fingerprint["changed_pixel_count"], golden["changed_pixel_count"][0]
                )
                self.assertLessEqual(
                    fingerprint["changed_pixel_count"], golden["changed_pixel_count"][1]
                )
                for found, expected in zip(
                    fingerprint["object_bbox_px"], golden["object_bbox_px"]
                ):
                    self.assertGreaterEqual(found, expected[0])
                    self.assertLessEqual(found, expected[1])
                for found, expected in zip(fingerprint["centroid_px"], golden["centroid_px"]):
                    self.assertGreaterEqual(found, expected[0])
                    self.assertLessEqual(found, expected[1])

                raw = copy.deepcopy(resource.to_dict())
                raw["vertices_mm"][0][0] += 1.0
                with self.assertRaisesRegex(ValueError, "geometry hash"):
                    ViewerMeshResource.from_dict(raw)
            finally:
                session.close()

    def test_manual_or_unverified_inspection_never_becomes_geometry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_viewer_guard_") as folder_name:
            source = Path(folder_name) / "guard.ifc"
            source.write_text("guard", encoding="ascii")
            session = ProjectSession.new("Viewer guard")
            try:
                source_record = session.project.add_source_path(source)
                identity = SourceIdentity(
                    source_file_id=source_record.source_id,
                    source_format="IFC",
                    source_sha256=source_record.sha256,
                    source_entity_id="#9",
                )
                part = Part(
                    internal_id="guard-part",
                    name="Guard",
                    source_identity=identity,
                    geometry_descriptor={"source_geometry_hash": "b" * 64},
                )
                part.recompute_hashes()
                session.project.add_entity(part)
                state = state_for(session)
                inspection = SourceGeometryInspection(
                    part_id=part.internal_id,
                    source_file_id=source_record.source_id,
                    source_sha256=source_record.sha256,
                    source_geometry_hash="b" * 64,
                    status="manual_validation_required",
                    scope="unknown",
                    geometry_kind="semantic_reference",
                    selection_verified=False,
                    production_geometry_exact=False,
                    blocking_reasons=["manual validation required"],
                )
                with self.assertRaisesRegex(ValueError, "Unverified"):
                    build_viewer_mesh_resource(
                        inspection,
                        project_id=state.steel_model.project_id,
                        entity=state.entity(part.internal_id),
                        binding=state.binding(part.internal_id),
                    )
            finally:
                session.close()

    @unittest.skipIf(
        HEADLESS_GITHUB_WINDOWS,
        "GitHub Windows runner has no stable OpenGL render context; local packaged load gate remains required",
    )
    def test_many_transformed_instances_share_geometry_without_crash(self) -> None:
        instance_count = 600
        with tempfile.TemporaryDirectory(prefix="cws_viewer_load_") as folder_name:
            source = Path(folder_name) / "instances.ifc"
            source.write_text("deterministic generated load fixture", encoding="ascii")
            session = ProjectSession.new("Viewer load fixture")
            try:
                source_record = session.project.add_source_path(source)
                for index in range(instance_count):
                    identity = SourceIdentity(
                        source_file_id=source_record.source_id,
                        source_format="IFC",
                        source_sha256=source_record.sha256,
                        source_entity_id=f"#{index + 1}",
                    )
                    part = Part(
                        internal_id=f"load-{index:04d}",
                        name=f"Load {index:04d}",
                        source_identity=identity,
                        global_placement=translated(
                            float(index % 30) * 140.0,
                            float((index // 30) % 20) * 90.0,
                            float(index // 600) * 70.0,
                        ),
                        geometry_descriptor={
                            "source_geometry_hash": "c" * 64,
                            "source_inspection": {
                                "selection_verified": True,
                                "production_geometry_exact": False,
                                "geometry_kind": "triangulated_mesh",
                            },
                        },
                    )
                    part.recompute_hashes()
                    session.project.add_entity(part)
                state = state_for(session)
                vertices = (
                    (-50.0, -25.0, -5.0),
                    (50.0, -25.0, -5.0),
                    (50.0, 25.0, -5.0),
                    (-50.0, 25.0, -5.0),
                    (-50.0, -25.0, 5.0),
                    (50.0, -25.0, 5.0),
                    (50.0, 25.0, 5.0),
                    (-50.0, 25.0, 5.0),
                )
                triangles = (
                    (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
                    (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
                    (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
                )
                resources = []
                for entity in state.steel_model.entities:
                    binding = state.binding(entity.steel_model_id)
                    resources.append(
                        ViewerMeshResource(
                            project_id=state.steel_model.project_id,
                            steel_model_id=entity.steel_model_id,
                            viewer_geometry_id=binding.viewer_geometry_id,
                            source_file_id=source_record.source_id,
                            source_sha256=source_record.sha256,
                            source_entity_id=entity.source.source_entity_id,
                            source_geometry_hash="c" * 64,
                            geometry_basis="source_ifc_triangulation",
                            accuracy_status=entity.accuracy_status.value,
                            vertices_mm=vertices,
                            triangles=triangles,
                            tessellation={"method": "generated_load_fixture"},
                        )
                    )
                started = time.perf_counter()
                state.attach_mesh_resources(resources)
                renderer = VtkOffscreenRenderer(width=640, height=420)
                try:
                    png = renderer.command("scene.load", state.scene_payload())
                    renderer.command("camera.standard_view", {"view": "isometric"})
                    image = renderer.render()
                    telemetry = renderer.telemetry()
                finally:
                    renderer.close()
                elapsed = time.perf_counter() - started
                self.assertTrue(png)
                self.assertGreater(len(image), 1000)
                self.assertEqual(telemetry["actor_count"], instance_count)
                self.assertEqual(telemetry["visible_actor_count"], instance_count)
                self.assertEqual(telemetry["unique_geometry_count"], 1)
                self.assertEqual(telemetry["triangle_count"], instance_count * 12)
                self.assertLess(elapsed, 30.0)
            finally:
                session.close()

    @unittest.skipIf(
        HEADLESS_GITHUB_WINDOWS,
        "GitHub Windows runner has no stable OpenGL render context; local GUI render gate remains required",
    )
    def test_visible_tk_workspace_loads_mesh_asynchronously(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk-weergave niet beschikbaar: {exc}")
        root.geometry("760x560+10000+10000")
        with tempfile.TemporaryDirectory(prefix="cws_viewer_ui_mesh_") as folder_name:
            source = Path(folder_name) / "ui.step"
            export_step(source)
            session = ProjectSession.new("Viewer UI mesh")
            panel = None
            try:
                registration = session.register_sources(
                    [source],
                    include_step_geometry=True,
                )[0]
                session.semantic_import_source(registration.source.source_id)
                part = next(iter(session.project.parts.values()))
                inspection = session.inspect_part_source_geometry(
                    part.internal_id,
                    persist=False,
                )
                resource_state = state_for(session)
                resource = build_viewer_mesh_resource(
                    inspection,
                    project_id=resource_state.steel_model.project_id,
                    entity=resource_state.entity(part.internal_id),
                    binding=resource_state.binding(part.internal_id),
                )
                panel = ProjectViewerPanel(root)
                panel.pack(fill="both", expand=True)
                panel.load_project(
                    session.project,
                    mesh_provider=lambda _part_id: resource,
                )
                panel.select_entity(part.internal_id)
                deadline = time.monotonic() + 12.0
                while time.monotonic() < deadline:
                    root.update()
                    if panel.state.mesh_resource(part.internal_id) is not None:
                        break
                    time.sleep(0.02)
                self.assertIsNotNone(panel.state.mesh_resource(part.internal_id))
                self.assertIsNotNone(panel._scene_photo)
                self.assertEqual(panel._builtin_renderer.actor_count, 1)
                self.assertEqual(str(panel.fit_button["state"]), "normal")
                self.assertEqual(str(panel.measure_button["state"]), "disabled")
                self.assertFalse(panel.state.handshake_report["complete"])
            finally:
                if panel is not None:
                    panel.destroy()
                session.close()
                root.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
