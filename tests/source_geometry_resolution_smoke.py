from __future__ import annotations

from pathlib import Path
import json
import multiprocessing
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectModel, ProjectSession, ProjectValidationError
from cws_convertor.steel_model.adapter import build_steel_model_snapshot
from cws_convertor.steel_model.viewer_boundary import build_viewer_host_snapshot
from cws_convertor.viewer.mesh_resources import build_viewer_mesh_resource
from cws_convertor.viewer.workspace import ViewerWorkspaceState
from canonical_model import CanonicalPart
from cli import EXIT_OK, EXIT_REVIEW_REQUIRED, main as cli_main


def export_step(path: Path, *, multi_solid: bool = False) -> None:
    import cadquery as cq

    first = cq.Workplane("XY").box(100.0, 50.0, 10.0).val()
    shape = first
    if multi_solid:
        second = cq.Workplane("XY").box(20.0, 20.0, 20.0).translate((200.0, 0.0, 0.0)).val()
        shape = cq.Compound.makeCompound([first, second])
    cq.exporters.export(shape, str(path))


def _export_ifc_worker(path: str) -> None:
    import ifcopenshell
    import ifcopenshell.api

    model = ifcopenshell.file(schema="IFC4")
    project = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcProject", name="Source geometry test"
    )
    ifcopenshell.api.run("unit.assign_unit", model)
    model_context = ifcopenshell.api.run(
        "context.add_context", model, context_type="Model"
    )
    body = ifcopenshell.api.run(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    site = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcSite", name="Site"
    )
    building = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcBuilding", name="Building"
    )
    storey = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcBuildingStorey", name="Storey"
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", model, products=[site], relating_object=project
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", model, products=[building], relating_object=site
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", model, products=[storey], relating_object=building
    )
    plate = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcPlate", name="Plate"
    )
    representation = ifcopenshell.api.run(
        "geometry.add_wall_representation",
        model,
        context=body,
        length=2.0,
        height=1.0,
        thickness=0.1,
    )
    ifcopenshell.api.run(
        "geometry.assign_representation",
        model,
        product=plate,
        representation=representation,
    )
    ifcopenshell.api.run(
        "spatial.assign_container",
        model,
        products=[plate],
        relating_structure=storey,
    )
    model.write(path)


def export_ifc(path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    process = context.Process(target=_export_ifc_worker, args=(str(path),))
    process.start()
    process.join(timeout=30.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=5.0)
        raise RuntimeError("IFC-testfixtureworker reageert niet")
    if process.exitcode != 0 or not path.is_file():
        raise RuntimeError(f"IFC-testfixtureworker faalde met exitcode {process.exitcode}")


class SourceGeometryResolutionTests(unittest.TestCase):
    def test_cli_import_and_source_geometry_inspection_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_source_cli_") as folder_name:
            folder = Path(folder_name)
            source = folder / "plate.ifc"
            project = folder / "plate.cwscproj"
            import_report = folder / "import.json"
            inspection_report = folder / "inspection.json"
            export_ifc(source)

            self.assertEqual(
                cli_main(["project-new", str(project), "--name", "CLI source inspection"]),
                EXIT_OK,
            )
            self.assertEqual(
                cli_main(
                    [
                        "project-import",
                        str(project),
                        str(source),
                        "--json-report",
                        str(import_report),
                    ]
                ),
                EXIT_REVIEW_REQUIRED,
            )
            imported = json.loads(import_report.read_text(encoding="utf-8"))
            self.assertEqual(imported["status"], "review_required")

            with ProjectSession.open(project, read_only=True) as session:
                part_id = next(iter(session.project.parts))
            self.assertEqual(
                cli_main(
                    [
                        "project-inspect-source-geometry",
                        str(project),
                        part_id,
                        "--json-report",
                        str(inspection_report),
                    ]
                ),
                EXIT_OK,
            )
            payload = json.loads(inspection_report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(payload["inspection"]["status"], "resolved_mesh")
            self.assertTrue(payload["inspection"]["selection_verified"])
            self.assertFalse(payload["inspection"]["production_geometry_exact"])

    def test_single_step_solid_resolves_as_exact_native_brep_and_persists(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_source_step_") as folder_name:
            folder = Path(folder_name)
            source = folder / "single.step"
            project_path = folder / "single.cwscproj"
            export_step(source)
            source_hash_before = source.read_bytes()

            session = ProjectSession.new("Exact STEP source")
            registration = session.register_sources([source], include_step_geometry=True)[0]
            session.semantic_import_source(registration.source.source_id)
            part = next(iter(session.project.parts.values()))
            locator = part.geometry_descriptor["source_locator"]
            self.assertEqual(locator["selector"]["kind"], "step_brep_roots")
            self.assertEqual(len(locator["selector"]["entity_ids"]), 1)

            inspection = session.inspect_part_source_geometry(part.internal_id, user="tester")
            self.assertEqual(inspection.status, "resolved_exact")
            self.assertEqual(inspection.scope, "part")
            self.assertEqual(inspection.geometry_kind, "native_brep")
            self.assertTrue(inspection.selection_verified)
            self.assertTrue(inspection.production_geometry_exact)
            self.assertIsNotNone(inspection.native_shape)
            self.assertEqual(inspection.metrics["solid_count"], 1)
            self.assertAlmostEqual(inspection.metrics["volume_mm3"], 50_000.0, places=6)
            self.assertAlmostEqual(part.surface_area_each_m2, 0.013, places=9)
            self.assertAlmostEqual(part.properties["volume_mm3"], 50_000.0, places=6)
            self.assertEqual(
                sorted(inspection.metrics["bbox_mm"], reverse=True),
                [100.0, 50.0, 10.0],
            )
            self.assertNotIn("native_shape", inspection.to_dict())
            self.assertEqual(source.read_bytes(), source_hash_before)

            session.save(project_path, embed_sources=True, user="tester")
            session.close()
            with ProjectSession.open(project_path, read_only=True) as reopened:
                stored = reopened.project.parts[part.internal_id].geometry_descriptor
                self.assertEqual(stored["source_inspection"]["status"], "resolved_exact")
                self.assertEqual(stored["cad_metrics"]["scope"], "exact_part")
                self.assertAlmostEqual(
                    reopened.project.parts[part.internal_id].surface_area_each_m2,
                    0.013,
                    places=9,
                )
                self.assertAlmostEqual(
                    reopened.project.parts[part.internal_id].properties["volume_mm3"],
                    50_000.0,
                    places=6,
                )
                resolved_again = reopened.inspect_part_source_geometry(
                    part.internal_id,
                    persist=False,
                )
                self.assertEqual(resolved_again.status, "resolved_exact")

    def test_exact_source_inspection_never_overwrites_canonical_metrics(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_source_canonical_") as folder_name:
            source = Path(folder_name) / "single.step"
            export_step(source)
            session = ProjectSession.new("Canonical metric ownership")
            registration = session.register_sources([source], include_step_geometry=True)[0]
            session.semantic_import_source(registration.source.source_id)
            part = next(iter(session.project.parts.values()))
            part.set_canonical(CanonicalPart(part_id=part.internal_id))
            part.surface_area_each_m2 = 9.25
            part.properties["volume_mm3"] = 123.0

            inspection = session.inspect_part_source_geometry(part.internal_id, user="tester")

            self.assertEqual(inspection.status, "resolved_exact")
            self.assertEqual(part.surface_area_each_m2, 9.25)
            self.assertEqual(part.properties["volume_mm3"], 123.0)

    def test_multi_solid_step_never_selects_a_part_by_native_list_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_source_multistep_") as folder_name:
            source = Path(folder_name) / "assembly.step"
            export_step(source, multi_solid=True)
            session = ProjectSession.new("Ambiguous STEP source")
            registration = session.register_sources([source], include_step_geometry=True)[0]
            result = session.semantic_import_source(registration.source.source_id)
            self.assertEqual(result.entity_counts["parts"], 2)
            part = next(iter(session.project.parts.values()))
            inspection = session.inspect_part_source_geometry(
                part.internal_id,
                persist=False,
            )
            self.assertEqual(inspection.status, "manual_validation_required")
            self.assertEqual(inspection.scope, "unknown")
            self.assertFalse(inspection.selection_verified)
            self.assertFalse(inspection.production_geometry_exact)
            self.assertIsNone(inspection.native_shape)
            self.assertIn("volgorde", inspection.blocking_reasons[0])

    def test_ifc_product_resolves_to_part_scoped_mesh_but_not_production_brep(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_source_ifc_") as folder_name:
            folder = Path(folder_name)
            source = folder / "plate.ifc"
            project_path = folder / "plate.cwscproj"
            export_ifc(source)

            session = ProjectSession.new("IFC source mesh")
            registration = session.register_sources([source], include_step_geometry=False)[0]
            session.semantic_import_source(registration.source.source_id)
            part = next(iter(session.project.parts.values()))
            locator = part.geometry_descriptor["source_locator"]
            self.assertEqual(locator["selector"]["kind"], "ifc_product_entity")

            inspection = session.inspect_part_source_geometry(part.internal_id, user="tester")
            self.assertEqual(inspection.status, "resolved_mesh")
            self.assertEqual(inspection.scope, "part")
            self.assertEqual(inspection.geometry_kind, "triangulated_mesh")
            self.assertTrue(inspection.selection_verified)
            self.assertFalse(inspection.production_geometry_exact)
            self.assertEqual(len(inspection.mesh_vertices_mm), 8)
            self.assertEqual(len(inspection.mesh_triangles), 12)
            self.assertTrue(inspection.topology["closed_mesh"])
            self.assertEqual(
                sorted(round(value, 6) for value in inspection.metrics["bbox_mm"]),
                [100.0, 1000.0, 2000.0],
            )
            self.assertAlmostEqual(
                inspection.metrics["volume_mm3"],
                200_000_000.0,
                places=3,
            )
            self.assertNotIn("cad_metrics", part.geometry_descriptor)
            self.assertEqual(
                part.geometry_descriptor["source_mesh_metrics"]["fidelity"],
                "triangulated_mesh",
            )
            steel_model = build_steel_model_snapshot(session.project)
            viewer_state = ViewerWorkspaceState(
                steel_model,
                build_viewer_host_snapshot(steel_model),
            )
            viewer_resource = build_viewer_mesh_resource(
                inspection,
                project_id=steel_model.project_id,
                entity=viewer_state.entity(part.internal_id),
                binding=viewer_state.binding(part.internal_id),
            )
            self.assertEqual(viewer_resource.geometry_basis, "source_ifc_triangulation")
            self.assertEqual(len(viewer_resource.vertices_mm), 8)
            self.assertEqual(len(viewer_resource.triangles), 12)
            viewer_state.attach_mesh_resource(viewer_resource)
            self.assertEqual(
                viewer_state.binding(part.internal_id).viewer_geometry_content_sha256,
                viewer_resource.geometry_content_sha256,
            )

            session.save(project_path, embed_sources=True, user="tester")
            session.close()
            with ProjectSession.open(project_path, read_only=True) as reopened:
                stored = reopened.project.parts[part.internal_id].geometry_descriptor
                self.assertEqual(stored["source_inspection"]["status"], "resolved_mesh")
                self.assertFalse(stored["source_inspection"]["production_geometry_exact"])

    def test_tampered_locator_source_hash_is_rejected_on_project_load(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_source_tamper_") as folder_name:
            source = Path(folder_name) / "single.step"
            export_step(source)
            session = ProjectSession.new("Tamper source locator")
            registration = session.register_sources([source], include_step_geometry=False)[0]
            session.semantic_import_source(registration.source.source_id)
            raw = session.project.to_dict()
            part = next(iter(raw["parts"].values()))
            part["geometry_descriptor"]["source_locator"]["source_sha256"] = "0" * 64
            with self.assertRaises(ProjectValidationError):
                ProjectModel.from_dict(raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
