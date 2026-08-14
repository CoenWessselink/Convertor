from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import Assembly, EntityCategory, Part, ProjectModel, ProjectSession, SourceIdentity
from cws_convertor.viewer.mesh_resources import ViewerMeshResource
from cws_convertor.viewer.v6_integration import (
    build_integrated_exact_part,
    build_integrated_project_scene,
)


def _line(start: tuple[float, float], end: tuple[float, float]) -> dict:
    return {"kind": "line", "start": list(start), "end": list(end)}


def _rectangle(width: float, height: float) -> list[dict]:
    return [
        _line((0.0, 0.0), (width, 0.0)),
        _line((width, 0.0), (width, height)),
        _line((width, height), (0.0, height)),
        _line((0.0, height), (0.0, 0.0)),
    ]


class ViewerV6IntegrationTests(unittest.TestCase):
    def _project(self, folder: Path) -> tuple[ProjectModel, str]:
        source_path = folder / "foundation.step"
        source_path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
        project = ProjectModel.new("Integrated viewer", created_by="test")
        source = project.add_source_path(source_path, source_format="STEP", user="test")
        part_identity = SourceIdentity(
            source_format="STEP",
            source_file_id=source.source_id,
            source_sha256=source.sha256,
            source_entity_id="#42",
            product_id="P-001",
            occurrence_id="O-001",
            part_position="P1",
            assembly_mark="M1",
        )
        part_id = project.stable_entity_id("part", part_identity)
        part = Part(
            internal_id=part_id,
            name="P1",
            category=EntityCategory.MAKE_PART.value,
            source_identity=part_identity,
            part_position="P1",
            profile="PL10*50",
            material="S355JR",
            length_mm=100.0,
            geometry_descriptor={
                "kind": "plate",
                "source_inspection": {
                    "geometry_kind": "native_brep",
                    "selection_verified": True,
                    "production_geometry_exact": True,
                },
            },
        )
        part.recompute_hashes()
        assembly_identity = SourceIdentity(
            source_format="STEP",
            source_file_id=source.source_id,
            source_sha256=source.sha256,
            source_entity_id="#10",
            product_id="A-001",
            assembly_mark="M1",
        )
        assembly_id = project.stable_entity_id("assembly", assembly_identity)
        assembly = Assembly(
            internal_id=assembly_id,
            name="M1",
            source_identity=assembly_identity,
            assembly_mark="M1",
            part_ids=[part_id],
            main_part_id=part_id,
        )
        part.assembly_ids = [assembly_id]
        part.quantity_per_assembly = {assembly_id: 1}
        part.recompute_hashes()
        project.add_entity(part, user="test")
        project.add_entity(assembly, user="test")
        project.validate()
        return project, part_id

    def test_scene_preserves_owner_ids_hashes_and_relations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="viewer_v6_bridge_") as folder_name:
            project, part_id = self._project(Path(folder_name))
            before = project.semantic_sha256()
            first = build_integrated_project_scene(project)
            second = build_integrated_project_scene(project)

        self.assertEqual(before, project.semantic_sha256())
        self.assertEqual(first.scene.scene_hash, second.scene.scene_hash)
        self.assertEqual(first.steel_model.snapshot_sha256, second.steel_model.snapshot_sha256)
        part = first.steel_model.entity(part_id)
        binding = first.viewer_host.binding(part_id)
        node = next(item for item in first.scene.nodes if item.entity_id == part_id)
        self.assertEqual(binding.viewer_node_id, node.node_id)
        self.assertEqual(part.source.source_entity_id, node.source_entity_id)
        self.assertEqual(part.geometry_hash, node.geometry_hash)
        self.assertEqual(part.manufacturing_hash, node.manufacturing_hash)
        self.assertIsNone(node.geometry_id)

    def test_owner_mesh_is_an_immutable_derived_scene_resource(self) -> None:
        with tempfile.TemporaryDirectory(prefix="viewer_v6_mesh_") as folder_name:
            project, part_id = self._project(Path(folder_name))
            baseline = build_integrated_project_scene(project)
            part = baseline.steel_model.entity(part_id)
            binding = baseline.viewer_host.binding(part_id)
            resource = ViewerMeshResource(
                project_id=project.project_id,
                steel_model_id=part_id,
                viewer_geometry_id=binding.viewer_geometry_id,
                source_file_id=part.source.source_file_id,
                source_sha256=part.source.source_sha256,
                source_entity_id=part.source.source_entity_id,
                source_geometry_hash=part.geometry_hash,
                geometry_basis="source_native_brep",
                accuracy_status="exact",
                vertices_mm=((0.0, 0.0, 0.0), (100.0, 0.0, 0.0), (0.0, 50.0, 0.0)),
                triangles=((0, 1, 2),),
                tessellation={"linear_deflection_mm": 0.2},
            )
            result = build_integrated_project_scene(project, mesh_resources=(resource,))

        node = next(item for item in result.scene.nodes if item.entity_id == part_id)
        mesh = result.repository.require(binding.viewer_geometry_id)
        self.assertEqual(binding.viewer_geometry_id, node.geometry_id)
        self.assertEqual(1, len(result.scene.geometry))
        self.assertFalse(mesh.vertices.flags.writeable)
        self.assertFalse(mesh.triangles.flags.writeable)
        self.assertEqual("cws-convertor-owner-mesh-v1", mesh.provider)

    def test_exact_review_uses_owner_source_rebuild_and_hash(self) -> None:
        import cadquery as cq

        with tempfile.TemporaryDirectory(prefix="viewer_v6_exact_bridge_") as folder_name:
            source_path = Path(folder_name) / "plate.step"
            cq.exporters.export(cq.Solid.makeBox(100.0, 50.0, 10.0), str(source_path))
            session = ProjectSession.new("Exact integrated bridge", created_by="test")
            registration = session.register_sources([source_path], include_step_geometry=True)[0]
            session.semantic_import_source(registration.source.source_id)
            part = next(iter(session.project.parts.values()))
            session.inspect_part_source_geometry(part.internal_id, user="test")
            session.start_part_workbench(part.internal_id, user="test")
            session.update_part_workbench(
                part.internal_id,
                {
                    "part_form": "plate",
                    "recognition": {"candidate": "PL10", "confidence": 1.0, "confirmed": True},
                    "dimensions": {"length_mm": 100.0, "thickness_mm": 10.0, "diameter_mm": 0.0},
                    "reference_sides": [
                        {
                            "side_id": "top",
                            "label": "Bovenzijde",
                            "face_ref": "owner:top",
                            "confirmed": True,
                        }
                    ],
                    "contours": [
                        {
                            "contour_id": "outer-1",
                            "role": "outer",
                            "closed": True,
                            "segments": _rectangle(100.0, 50.0),
                        }
                    ],
                    "features": [],
                },
                user="test",
                reason="Owner canonical plate",
            )
            session.rebuild_part_canonical(part.internal_id, user="test")
            integrated = build_integrated_exact_part(session, part.internal_id)
            comparison = integrated.validate_compare()
            owner_hash = session.project.parts[part.internal_id].manufacturing_hash

        self.assertEqual("native_brep", integrated.source_inspection.geometry_kind)
        self.assertIsNotNone(integrated.canonical)
        self.assertEqual(owner_hash, integrated.service.manufacturing_hash())
        self.assertEqual("pass", comparison["status"])
        self.assertFalse(comparison["production_release_allowed"])
        self.assertFalse(integrated.owner_gates()["production_release_allowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
