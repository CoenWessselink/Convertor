from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing.contact import (
    CONTACT_NOT_FOUND,
    CONTACT_WRONG_GEOMETRY,
    ContactGeometryService,
    ContactPatchValidator,
    ExactContactGeometryEngine,
)
from cws_convertor.manufacturing.contact_model import ContactPatch, ContactResolutionReport
from cws_convertor.project.model import Assembly, Part, ProjectModel, Transform3D, Weld, stable_sha256
from cws_convertor.project.workbench import create_workbench_state, evaluate_workbench_revision


def _transform(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Transform3D:
    return Transform3D(
        [
            [1.0, 0.0, 0.0, float(x)],
            [0.0, 1.0, 0.0, float(y)],
            [0.0, 0.0, 1.0, float(z)],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def _workbench_part(part_id: str, placement: Transform3D) -> Part:
    part = Part(
        internal_id=part_id,
        name=part_id,
        part_position=part_id,
        profile="RHS_TEST",
        profile_type="M",
        material="S235",
        material_grade="S235JR",
        length_mm=1000.0,
        local_placement=placement,
        global_placement=placement,
        geometry_descriptor={"dimensions": [1000.0, 100.0, 100.0]},
    )
    part.recompute_hashes()
    state = create_workbench_state(part, user="test", source_geometry_hash=part.geometry_hash)
    revision = deepcopy(state["current_revision"])
    revision["part_form"] = "profile"
    revision["recognition"] = {"candidate": "RHS_TEST", "confidence": 1.0, "confirmed": True}
    revision["production_frame"] = {"matrix": Transform3D.identity().matrix}
    revision["dimensions"] = {"length_mm": 1000.0}
    revision["production_properties"] = {
        "profile": "RHS_TEST",
        "material": "S235",
        "material_grade": "S235JR",
        "part_position": part_id,
        "assembly_position": "",
    }
    revision["reference_sides"] = [
        {"side_id": "review", "label": "review", "face_ref": "canonical", "confirmed": True}
    ]
    revision["contours"] = []
    revision["features"] = []
    revision["validation_issues"] = evaluate_workbench_revision(revision)
    assert not revision["validation_issues"], revision["validation_issues"]
    state["current_revision"] = revision
    snapshot = deepcopy(revision)
    state["revision_history"] = [
        {
            "revision_id": snapshot["revision_id"],
            "revision_number": snapshot["revision_number"],
            "timestamp": snapshot["modified_at"],
            "user": "test",
            "reason": snapshot["reason"],
            "snapshot_sha256": stable_sha256(snapshot),
            "snapshot": snapshot,
        }
    ]
    state["commands"] = []
    state["command_cursor"] = 0
    part.workbench = state
    return part


def _fixture(*, secondary_z: float = 100.0, add_weld: bool = False) -> tuple[ProjectModel, dict[str, cq.Shape]]:
    project = ProjectModel.new("Manufacturing contact fixture")
    project.parts["P1"] = _workbench_part("P1", _transform())
    project.parts["P2"] = _workbench_part("P2", _transform(100.0, 35.0, secondary_z))
    project.assemblies["A1"] = Assembly(
        internal_id="A1",
        name="Frame",
        assembly_mark="M1",
        part_ids=["P1", "P2"],
        main_part_id="P1",
    )
    if add_weld:
        project.welds["W1"] = Weld(
            internal_id="W1",
            name="W1",
            weld_type="fillet",
            size_mm=5.0,
            length_mm=100.0,
            connected_part_ids=["P1", "P2"],
        )
        project.assemblies["A1"].weld_ids = ["W1"]
    shapes = {
        "P1": cq.Solid.makeBox(1000.0, 100.0, 100.0),
        "P2": cq.Solid.makeBox(100.0, 30.0, 10.0),
    }
    return project, shapes


def _provider(shapes: dict[str, cq.Shape]):
    return lambda part_id: shapes[part_id]


class ManufacturingContactCoreTests(unittest.TestCase):
    def test_exact_surface_contact_builds_dual_face_local_patch(self) -> None:
        project, shapes = _fixture()
        engine = ExactContactGeometryEngine(project, shape_provider=_provider(shapes))
        report = engine.resolve()
        self.assertTrue(report.passed)
        self.assertEqual((("P1", "P2"),), report.candidate_pairs)
        self.assertEqual(1, len(report.patches))
        patch = report.patches[0]
        self.assertEqual("P1", patch.main_part_id)
        self.assertEqual("P2", patch.secondary_part_id)
        self.assertAlmostEqual(3000.0, patch.area_mm2, places=4)
        self.assertAlmostEqual(0.0, patch.gap_mm, places=6)
        self.assertAlmostEqual(0.0, patch.penetration_mm3, places=6)
        self.assertTrue(patch.exact_boundary_world_mm)
        self.assertEqual(len(patch.exact_boundary_world_mm), len(patch.projected_boundary_main_2d))
        self.assertEqual(len(patch.exact_boundary_world_mm), len(patch.projected_boundary_secondary_2d))
        self.assertTrue(patch.production_usable)
        self.assertFalse(ContactPatchValidator().validate(project, report, engine.face_reports))

    def test_contact_hash_is_invariant_for_rigid_whole_assembly_translation(self) -> None:
        project, shapes = _fixture()
        first_engine = ExactContactGeometryEngine(project, shape_provider=_provider(shapes))
        first = first_engine.resolve().patches[0]

        moved = deepcopy(project)
        for part in moved.parts.values():
            x, y, z = part.global_placement.translation_mm()
            part.global_placement = _transform(x + 5000.0, y - 1250.0, z + 750.0)
            part.local_placement = part.global_placement
        second_engine = ExactContactGeometryEngine(moved, shape_provider=_provider(shapes))
        second = second_engine.resolve().patches[0]
        self.assertEqual(first.geometry_hash, second.geometry_hash)
        self.assertEqual(first.contact_id, second.contact_id)
        self.assertNotEqual(first.exact_boundary_world_mm, second.exact_boundary_world_mm)
        self.assertEqual(first.projected_boundary_main_2d, second.projected_boundary_main_2d)
        self.assertEqual(first.projected_boundary_secondary_2d, second.projected_boundary_secondary_2d)

    def test_assembly_proximity_without_contact_is_warning_not_verified_patch(self) -> None:
        project, shapes = _fixture(secondary_z=100.2)
        report = ExactContactGeometryEngine(
            project,
            shape_provider=_provider(shapes),
            contact_tolerance_mm=0.05,
        ).resolve()
        self.assertTrue(report.passed)
        self.assertFalse(report.patches)
        self.assertFalse(report.blocking_codes)
        self.assertTrue(any("0.2000 mm" in warning for warning in report.warnings))

    def test_explicit_weld_relation_without_contact_blocks(self) -> None:
        project, shapes = _fixture(secondary_z=100.2, add_weld=True)
        report = ExactContactGeometryEngine(
            project,
            shape_provider=_provider(shapes),
            contact_tolerance_mm=0.05,
        ).resolve()
        self.assertFalse(report.passed)
        self.assertFalse(report.patches)
        self.assertIn(CONTACT_NOT_FOUND, report.blocking_codes)

    def test_penetration_blocks_contact_instead_of_becoming_a_scribing_patch(self) -> None:
        project, shapes = _fixture(secondary_z=95.0)
        report = ExactContactGeometryEngine(project, shape_provider=_provider(shapes)).resolve()
        self.assertFalse(report.passed)
        self.assertFalse(report.patches)
        self.assertIn(CONTACT_WRONG_GEOMETRY, report.blocking_codes)
        self.assertTrue(any("penetreert" in warning for warning in report.warnings))

    def test_edge_contact_is_not_upgraded_to_surface_contact(self) -> None:
        project, shapes = _fixture()
        project.parts["P2"].global_placement = _transform(100.0, 100.0, 100.0)
        project.parts["P2"].local_placement = project.parts["P2"].global_placement
        report = ExactContactGeometryEngine(project, shape_provider=_provider(shapes)).resolve()
        self.assertTrue(report.passed)
        self.assertFalse(report.patches)
        self.assertTrue(any("geen exact 2D BREP-contactvlak" in warning for warning in report.warnings))

    def test_candidate_generation_is_relation_driven_not_global_n_squared(self) -> None:
        project, shapes = _fixture()
        for index in range(3, 53):
            part_id = f"P{index}"
            project.parts[part_id] = _workbench_part(part_id, _transform(index * 2500.0, 0.0, 0.0))
            shapes[part_id] = cq.Solid.makeBox(100.0, 50.0, 20.0)
        engine = ExactContactGeometryEngine(project, shape_provider=_provider(shapes))
        candidates = engine.candidate_pairs()
        self.assertEqual(1, len(candidates))
        theoretical = len(project.parts) * (len(project.parts) - 1) // 2
        self.assertGreater(theoretical, len(candidates) * 100)

    def test_corrupted_world_boundary_is_detected_by_independent_validator(self) -> None:
        project, shapes = _fixture()
        engine = ExactContactGeometryEngine(project, shape_provider=_provider(shapes))
        report = engine.resolve()
        patch = report.patches[0]
        loops = [list(loop) for loop in patch.exact_boundary_world_mm]
        first = list(loops[0][0])
        first[0] += 2.0
        loops[0][0] = tuple(first)
        corrupted = replace(patch, exact_boundary_world_mm=tuple(tuple(loop) for loop in loops))
        bad_report = ContactResolutionReport.create(
            project_id=report.project_id,
            candidate_pairs=report.candidate_pairs,
            patches=(corrupted,),
            contact_tolerance_mm=report.contact_tolerance_mm,
            penetration_tolerance_mm3=report.penetration_tolerance_mm3,
        )
        issues = ContactPatchValidator().validate(project, bad_report, engine.face_reports)
        self.assertTrue(any("projection mismatch" in issue for issue in issues))

    def test_contact_patch_serialization_is_hash_verified(self) -> None:
        project, shapes = _fixture()
        engine = ExactContactGeometryEngine(project, shape_provider=_provider(shapes))
        patch = engine.resolve().patches[0]
        payload = patch.to_dict()
        restored = ContactPatch.from_dict(payload)
        self.assertEqual(patch.geometry_hash, restored.geometry_hash)
        payload["projected_boundary_main_2d"][0][0][0] += 1.0
        with self.assertRaises(ValueError):
            ContactPatch.from_dict(payload)

    def test_service_persistence_keeps_production_marking_locked(self) -> None:
        project, shapes = _fixture()
        service = ContactGeometryService(project, shape_provider=_provider(shapes))
        report = service.build(persist=True)
        stored = project.settings["manufacturing_contacts"]
        self.assertEqual(report.report_sha256, stored["report_sha256"])
        self.assertFalse(stored["production_marking_released"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
