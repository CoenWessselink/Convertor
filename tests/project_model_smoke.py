from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import (
    Assembly,
    EntityCategory,
    Part,
    ProjectModel,
    ProjectValidationError,
    ReviewStatus,
    SourceIdentity,
    StockItem,
    Transform3D,
)


def translated(x: float, y: float, z: float) -> Transform3D:
    return Transform3D(
        [
            [1.0, 0.0, 0.0, x],
            [0.0, 1.0, 0.0, y],
            [0.0, 0.0, 1.0, z],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


class ProjectModelTests(unittest.TestCase):
    def _build_project(self) -> ProjectModel:
        with tempfile.TemporaryDirectory(prefix="cws_model_") as folder_name:
            source_path = Path(folder_name) / "model.ifc"
            source_path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
            project = ProjectModel.new(
                "Defensie onderbouw",
                customer="RVB",
                order_number="CWS-001",
                project_phase="1",
                created_by="tester",
            )
            source = project.add_source_path(source_path, source_format="IFC", user="tester")
            project.mark_source_semantic_import_pending(source.source_id, user="tester")

            identity = SourceIdentity(
                source_format="IFC",
                source_file_id=source.source_id,
                source_sha256=source.sha256,
                source_entity_id="#161",
                global_id="3SAMPLE",
                part_position="LO4",
                assembly_mark="MLO4",
            )
            part_id = project.stable_entity_id("part", identity)
            part = Part(
                internal_id=part_id,
                source_identity=identity,
                part_position="LO4",
                name="LOSSE PLAAT",
                category=EntityCategory.MAKE_PART.value,
                profile="STRIP5*120",
                profile_type="B",
                material="S235JR",
                material_grade="S235JR",
                length_mm=160.0,
                quantity_total=4,
                geometry_descriptor={
                    "kind": "plate",
                    "bbox_mm": [160.0, 120.0, 5.0],
                    "outer_contour": [[0.0, 0.0], [160.0, 0.0], [160.0, 120.0], [0.0, 120.0]],
                },
                production_features=[
                    {"kind": "hole", "diameter": 14.0, "x": 20.0, "q": 20.0}
                ],
                nc1_eligible=True,
                status=ReviewStatus.VALIDATED.value,
            )
            part.recompute_hashes()
            project.add_entity(part, user="tester")

            assembly_identity = SourceIdentity(
                source_format="IFC",
                source_file_id=source.source_id,
                source_sha256=source.sha256,
                source_entity_id="#46",
                global_id="3ASSEMBLY",
                assembly_mark="MLO4",
            )
            assembly_id = project.stable_entity_id("assembly", assembly_identity)
            assembly = Assembly(
                internal_id=assembly_id,
                source_identity=assembly_identity,
                assembly_mark="MLO4",
                name="MLO4",
                part_ids=[part.internal_id],
                main_part_id=part.internal_id,
                quantity=1,
            )
            part.assembly_ids.append(assembly_id)
            part.quantity_per_assembly[assembly_id] = 4
            part.recompute_hashes()
            project.add_entity(part, user="tester")
            project.add_entity(assembly, user="tester")
            project.validate()
            return ProjectModel.from_dict(project.to_dict())

    def test_roundtrip_summary_identity_and_gate(self) -> None:
        project = self._build_project()
        restored = ProjectModel.from_dict(json.loads(project.to_json_bytes()))
        self.assertEqual(restored.project_name, "Defensie onderbouw")
        self.assertEqual(next(iter(restored.parts.values())).part_position, "LO4")
        self.assertEqual(next(iter(restored.assemblies.values())).assembly_mark, "MLO4")
        self.assertEqual(restored.entity_counts()["part"], 1)
        self.assertEqual(restored.entity_counts()["assembly"], 1)
        self.assertEqual(project.semantic_sha256(), restored.semantic_sha256())
        self.assertFalse(restored.production_gate()["allowed"])
        self.assertEqual(len(restored.production_gate()["source_failures"]), 1)

    def test_stable_entity_id_is_repeatable(self) -> None:
        project = ProjectModel.new("ID-test")
        identity = SourceIdentity(
            source_format="IFC",
            source_sha256="a" * 64,
            global_id="ABC",
        )
        self.assertEqual(
            project.stable_entity_id("part", identity),
            project.stable_entity_id("part", identity),
        )
        self.assertNotEqual(
            project.stable_entity_id("part", identity),
            project.stable_entity_id("assembly", identity),
        )

    def test_geometry_hash_is_placement_independent(self) -> None:
        part = Part(
            internal_id="part-1",
            profile="HEA140",
            profile_type="I",
            material="S355JR",
            length_mm=2200.0,
            geometry_descriptor={"brep_signature": ["face:a", "face:b"]},
            production_features=[{"kind": "hole", "diameter": 18.0, "x": 80.0}],
        )
        first_geometry, first_manufacturing = part.recompute_hashes()
        part.global_placement = translated(1000.0, 2000.0, 3000.0)
        second_geometry, second_manufacturing = part.recompute_hashes()
        self.assertEqual(first_geometry, second_geometry)
        self.assertEqual(first_manufacturing, second_manufacturing)

    def test_manufacturing_hash_changes_for_material_and_mirror(self) -> None:
        part = Part(
            internal_id="part-2",
            profile="L50*5",
            profile_type="L",
            material="S235JR",
            length_mm=500.0,
            geometry_descriptor={"edges": [1, 2, 3]},
        )
        geometry, manufacturing = part.recompute_hashes()
        part.material = "S355JR"
        geometry_after_material, manufacturing_after_material = part.recompute_hashes()
        self.assertEqual(geometry, geometry_after_material)
        self.assertNotEqual(manufacturing, manufacturing_after_material)
        part.material = "S235JR"
        part.mirrored = True
        mirrored_geometry, mirrored_manufacturing = part.recompute_hashes()
        self.assertNotEqual(geometry, mirrored_geometry)
        self.assertNotEqual(manufacturing, mirrored_manufacturing)

    def test_semantic_completion_keeps_failed_validation_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_gate_") as folder_name:
            source = Path(folder_name) / "one.step"
            source.write_text("ISO-10303-21;", encoding="utf-8")
            project = ProjectModel.new("Gate")
            record = project.add_source_path(source, source_format="STEP")
            project.mark_source_semantic_import_pending(record.source_id)
            project.mark_source_semantic_import_complete(
                record.source_id,
                production_export_allowed=False,
            )
            gate = project.production_gate()
            self.assertFalse(gate["allowed"])
            self.assertTrue(record.semantic_import_complete)
            self.assertFalse(record.production_export_allowed)
            self.assertEqual(project.status, ReviewStatus.REVIEW_REQUIRED.value)
            self.assertTrue(
                any(issue.code == "CWS-PROJECT-SOURCE-PRODUCTION-BLOCKED" for issue in project.blocking_issues())
            )
            project.mark_source_semantic_import_complete(
                record.source_id,
                production_export_allowed=True,
            )
            self.assertTrue(project.production_gate()["allowed"])
            self.assertEqual(project.status, ReviewStatus.VALIDATED.value)

    def test_invalid_left_handed_transform_is_rejected(self) -> None:
        transform = Transform3D(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, -1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
        with self.assertRaises(ProjectValidationError):
            transform.validate()

    def test_scaled_or_sheared_transform_is_rejected(self) -> None:
        for matrix in (
            [
                [2.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            [
                [1.0, 0.2, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        ):
            with self.subTest(matrix=matrix), self.assertRaises(ProjectValidationError):
                Transform3D(matrix).validate()

    def test_deep_assembly_cycle_is_rejected(self) -> None:
        project = ProjectModel.new("Cycle")
        first = Assembly(internal_id="assembly-a", child_assembly_ids=["assembly-b"])
        second = Assembly(internal_id="assembly-b", child_assembly_ids=["assembly-c"])
        third = Assembly(internal_id="assembly-c", child_assembly_ids=["assembly-a"])
        for assembly in (first, second, third):
            project.add_entity(assembly)
        with self.assertRaisesRegex(ProjectValidationError, "Cyclische assemblystructuur"):
            project.validate()

    def test_part_assembly_relation_must_be_reciprocal(self) -> None:
        project = ProjectModel.new("Relations")
        part = Part(internal_id="part-a")
        part.recompute_hashes()
        assembly = Assembly(internal_id="assembly-a", part_ids=[part.internal_id])
        project.add_entity(part)
        project.add_entity(assembly)
        with self.assertRaisesRegex(ProjectValidationError, "niet wederkerig"):
            project.validate()

    def test_invalid_quantities_and_overreservation_are_rejected(self) -> None:
        project = ProjectModel.new("Quantities")
        part = Part(internal_id="part-a", quantity_total=0)
        part.recompute_hashes()
        project.add_entity(part)
        with self.assertRaises(ProjectValidationError):
            project.validate()

        project = ProjectModel.new("Stock")
        stock = StockItem(
            internal_id="stock-a",
            available_quantity=2.0,
            reserved_quantity=3.0,
        )
        project.add_entity(stock)
        with self.assertRaisesRegex(ProjectValidationError, "meer dan beschikbaar"):
            project.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
