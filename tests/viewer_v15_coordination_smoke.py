from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.model import Assembly, Part, ProjectModel, Transform3D
from cws_viewer.adapters.project_model import CwsProjectSceneAdapter
from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.coordination import SequenceKind, V15CoordinationService, coordination_contract
from cws_viewer.coordination.review_bridge import T6ReviewServiceBridge
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.model_control import GeometryConfidence
from cws_viewer.review import V15ReviewWorkspaceService
from cws_viewer.ui_qt.cockpit_t6_v15 import t6_workspace_contract


def _transform(x: float, y: float = 0.0, z: float = 0.0) -> Transform3D:
    return Transform3D(
        [
            [1.0, 0.0, 0.0, float(x)],
            [0.0, 1.0, 0.0, float(y)],
            [0.0, 0.0, 1.0, float(z)],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


def _part(part_id: str, position: str, x: float, assembly_id: str) -> Part:
    part = Part(
        internal_id=part_id,
        name=position,
        part_position=position,
        assembly_ids=[assembly_id],
        profile="HEA100",
        profile_type="I",
        material="S235",
        material_grade="S235JR",
        length_mm=100.0,
        geometry_descriptor={"dimensions": [100.0, 100.0, 100.0]},
        local_placement=_transform(x),
        global_placement=_transform(x),
    )
    part.recompute_hashes()
    return part


def _project_fixture() -> ProjectModel:
    project = ProjectModel.new("T6 coordination fixture", customer="CWS", order_number="T6")
    root = Assembly(
        internal_id="A-ROOT",
        name="Hoofdframe",
        assembly_mark="M001",
        child_assembly_ids=["A-CHILD"],
        part_ids=["P1", "P2", "P5", "P6", "P7", "P8"],
        main_part_id="P1",
    )
    child = Assembly(
        internal_id="A-CHILD",
        name="Subframe",
        assembly_mark="M002",
        part_ids=["P3", "P4"],
        main_part_id="P3",
    )
    project.assemblies[root.internal_id] = root
    project.assemblies[child.internal_id] = child
    # P1/P2 overlap. Remaining parts are deliberately spaced so broad phase is
    # far smaller than theoretical N².
    locations = {
        "P1": ("P1", 0.0, "A-ROOT"),
        "P2": ("P2", 40.0, "A-ROOT"),
        "P3": ("P3", 1000.0, "A-CHILD"),
        "P4": ("P4", 2200.0, "A-CHILD"),
        "P5": ("P5", 3400.0, "A-ROOT"),
        "P6": ("P6", 4600.0, "A-ROOT"),
        "P7": ("P7", 5800.0, "A-ROOT"),
        "P8": ("P8", 7000.0, "A-ROOT"),
    }
    for part_id, (position, x, assembly_id) in locations.items():
        project.parts[part_id] = _part(part_id, position, x, assembly_id)
    return project


class ViewerV15CoordinationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = _project_fixture()
        self.scene = CwsProjectSceneAdapter().build_scene(self.project)
        self.backend = MemoryRenderBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1400, height=900)
        self.controller.load_scene(self.scene)
        self.service = V15CoordinationService(self.controller, self.project)
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.controller.shutdown()
        self.temp.cleanup()

    def test_contract_is_viewer_coordination_not_machine_release(self) -> None:
        contract = coordination_contract()
        self.assertTrue(contract["capabilities"]["assembly_drilldown"])
        self.assertTrue(contract["capabilities"]["clash_spatial_broad_phase"])
        self.assertTrue(contract["capabilities"]["clash_no_global_n_squared_bruteforce"])
        self.assertTrue(contract["capabilities"]["production_review_sequence"])
        self.assertFalse(contract["safety"]["sequence_is_machine_schedule"])
        self.assertFalse(contract["safety"]["approximate_aabb_is_exact_clash"])
        workspace = t6_workspace_contract()
        self.assertEqual(7, len(workspace["docks"]))
        self.assertTrue(workspace["capabilities"]["canonical_revision_compare"])

    def test_assembly_hierarchy_and_drilldown_are_canonical(self) -> None:
        self.assertEqual(("A-ROOT",), self.service.root_assembly_ids())
        self.assertEqual(
            ("A-ROOT", "A-CHILD"),
            self.service.assembly_descendants("A-ROOT"),
        )
        root = self.service.assembly_context("A-ROOT")
        self.assertEqual("P1", root.main_part_id)
        self.assertIn("P2", root.secondary_part_ids)
        recursive = self.service.assembly_entity_ids("A-ROOT", recursive=True)
        self.assertEqual(set(self.project.parts), set(recursive))
        main_nodes = self.service.select_main_part("A-ROOT")
        self.assertTrue(main_nodes)
        self.assertEqual(main_nodes, self.controller.get_selection())

    def test_sequence_plan_is_deterministic_and_viewer_only(self) -> None:
        plan1 = self.service.build_sequence(SequenceKind.CONSTRUCTION)
        plan2 = self.service.build_sequence(SequenceKind.CONSTRUCTION)
        self.assertEqual(plan1.manifest_sha256, plan2.manifest_sha256)
        self.assertEqual(plan1.plan_id, plan2.plan_id)
        self.assertTrue(plan1.viewer_only)
        self.assertTrue(plan1.cumulative)
        self.assertEqual(2, len(plan1.steps))
        step = self.service.apply_sequence_step(plan1, 0)
        self.assertEqual(0, step.index)
        visible = self.controller.export_workspace_state().visible_node_ids
        self.assertTrue(visible)
        self.service.reset_sequence()
        self.assertEqual((), self.controller.export_workspace_state().visible_node_ids)

    def test_production_review_sequence_is_not_machine_operation_order(self) -> None:
        plan = self.service.build_sequence(SequenceKind.PRODUCTION_REVIEW)
        self.assertFalse(plan.cumulative)
        self.assertEqual(len(self.project.parts), len(plan.steps))
        self.assertTrue(all(step.kind is SequenceKind.PRODUCTION_REVIEW for step in plan.steps))
        self.assertTrue(all("geen machine-operation sequence" in step.note for step in plan.steps))

    def test_revision_compare_uses_existing_canonical_engine_and_hashes_evidence(self) -> None:
        old = deepcopy(self.project)
        new = deepcopy(self.project)
        new.parts["P2"].global_placement = _transform(140.0)
        new.parts["P2"].local_placement = _transform(140.0)
        new.parts["P2"].recompute_hashes()
        new.parts["P3"].material_grade = "S355J2"
        new.parts["P3"].recompute_hashes()
        evidence1 = self.service.compare_revisions(old, new)
        evidence2 = self.service.compare_revisions(old, new)
        self.assertEqual(evidence1.manifest_sha256, evidence2.manifest_sha256)
        counts = evidence1.report.counts
        self.assertGreaterEqual(counts.get("moved", 0), 1)
        self.assertGreaterEqual(counts.get("manufacturing_changed", 0) + counts.get("changed", 0), 1)
        self.assertTrue(evidence1.report.changes)

    def test_spatial_clash_scan_avoids_global_n_squared_and_preserves_confidence(self) -> None:
        evidence1 = self.service.scan_clashes()
        evidence2 = self.service.scan_clashes()
        stats = evidence1.scan.stats
        self.assertGreater(stats.theoretical_pairs, stats.broad_phase_candidates)
        self.assertGreaterEqual(stats.results, 1)
        self.assertEqual(evidence1.manifest_sha256, evidence2.manifest_sha256)
        first = evidence1.scan.records[0]
        self.assertEqual(GeometryConfidence.APPROXIMATE.value, first.geometry_confidence)
        self.assertNotEqual("hard", first.category)
        self.assertIn("AABB", first.classification_reason)
        nodes = self.service.select_clash(first.clash_id)
        self.assertEqual(2, len(nodes))

    def test_clash_can_be_bridged_to_t5_issue_with_auditable_reference(self) -> None:
        evidence = self.service.scan_clashes()
        record = evidence.scan.records[0]
        review = V15ReviewWorkspaceService(
            self.controller,
            project_id=self.scene.project_id,
            scene_hash=self.scene.scene_hash,
            store_path=Path(self.temp.name) / "review.json",
        )
        bridge = T6ReviewServiceBridge(review)
        issue = bridge.create_issue(
            "Model control clash",
            description=evidence.manifest_sha256,
            created_by="CWS Model Control",
            linked_entity_ids=(record.part_a_id, record.part_b_id),
            linked_clash_ids=(record.clash_id,),
        )
        self.assertEqual((record.clash_id,), issue.linked_clash_ids)
        review.save()
        restored = V15ReviewWorkspaceService(
            self.controller,
            project_id=self.scene.project_id,
            scene_hash=self.scene.scene_hash,
            store_path=Path(self.temp.name) / "review.json",
        )
        restored.load()
        self.assertEqual((record.clash_id,), restored.issue(issue.issue_id).linked_clash_ids)

    def test_coordination_manifest_binds_compare_clash_sequence_without_release(self) -> None:
        self.service.compare_revisions(deepcopy(self.project), deepcopy(self.project))
        self.service.scan_clashes()
        self.service.build_sequence(SequenceKind.ASSEMBLY)
        manifest1 = self.service.evidence_manifest()
        manifest2 = self.service.evidence_manifest()
        self.assertEqual(manifest1["manifest_sha256"], manifest2["manifest_sha256"])
        self.assertFalse(manifest1["production_machine_transfer_allowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
