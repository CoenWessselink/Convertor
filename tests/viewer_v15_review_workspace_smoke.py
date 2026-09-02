from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.core.v14_controller import V14ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.review import (
    MarkupKind,
    Bcf21Verifier,
    ReferenceState,
    ReviewPackageReader,
    ReviewPackageVerifier,
    ReviewPriority,
    ReviewStatus,
    V15ReviewWorkspaceService,
    map_review_topic,
    review_workspace_contract,
)
from cws_viewer.ui_qt.cockpit_t5_v15 import t5_workspace_contract


class ViewerV15ReviewWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scene = build_synthetic_product_scene(30, parts_per_assembly=10)
        self.backend = MemoryRenderBackend()
        self.controller = V14ViewerCoreController(self.backend, width=1200, height=800)
        self.controller.load_scene(self.scene)
        self.store = self.root / "project.cwsreview.json"
        self.service = V15ReviewWorkspaceService(
            self.controller,
            project_id=self.scene.project_id,
            scene_hash=self.scene.scene_hash,
            store_path=self.store,
            project_metadata={"project_name": "T5 fixture", "revision_id": "R1"},
        )

    def tearDown(self) -> None:
        self.controller.shutdown()
        self.temp.cleanup()

    def _pick_first(self):
        node_id = self.controller.index.renderable_node_ids[0]
        self.backend.pick_node_id = node_id
        pick = self.controller.pick_at(10, 10)
        self.assertIsNotNone(pick)
        return pick

    def test_contract_keeps_review_non_destructive_and_views_independent(self) -> None:
        contract = review_workspace_contract()
        self.assertTrue(contract["capabilities"]["saved_views_independent_from_issues"])
        self.assertTrue(contract["capabilities"]["stale_reference_detection"])
        self.assertFalse(contract["capabilities"]["silent_reference_remap"])
        self.assertFalse(contract["capabilities"]["review_mutates_canonical_geometry"])
        workspace = t5_workspace_contract()
        self.assertEqual(6, len(workspace["docks"]))
        self.assertTrue(workspace["capabilities"]["issue_due_date"])

    def test_saved_view_issue_and_markup_roundtrip_without_geometry_mutation(self) -> None:
        before_hash = self.controller.index.scene.scene_hash
        first_node = self.controller.index.renderable_node_ids[0]
        self.controller.set_selection((first_node,))
        view = self.service.capture_view("R1 overzicht", owner="tester")
        markup = self.service.create_markup_from_pick(
            self._pick_first(), kind=MarkupKind.ARROW, text="Controleer las", created_by="tester"
        )
        issue = self.service.create_issue(
            "Lasdetail controleren",
            description="Review-only issue",
            priority=ReviewPriority.HIGH,
            created_by="tester",
            markup_ids=(markup.markup_id,),
            viewpoint_id=view.viewpoint_id,
        )
        self.service.set_status(issue.issue_id, ReviewStatus.ACTION_REQUIRED, actor="tester")
        self.service.assign(issue.issue_id, "werkvoorbereiding", actor="tester")
        self.service.set_due_date(issue.issue_id, "2026-08-31T12:00:00Z", actor="tester")
        self.service.add_comment(issue.issue_id, "tester", "Eerste controle uitgevoerd")
        attachment = self.root / "foto.txt"
        attachment.write_text("review evidence", encoding="utf-8")
        self.service.add_attachment(issue.issue_id, attachment, actor="tester", media_type="text/plain")
        self.service.save()
        self.assertEqual(before_hash, self.controller.index.scene.scene_hash)

        backend2 = MemoryRenderBackend()
        controller2 = V14ViewerCoreController(backend2, width=1200, height=800)
        controller2.load_scene(self.scene)
        try:
            restored = V15ReviewWorkspaceService(
                controller2,
                project_id=self.scene.project_id,
                scene_hash=self.scene.scene_hash,
                store_path=self.store,
            )
            report = restored.load()
            self.assertTrue(report["exact_scene_match"])
            self.assertEqual(1, report["issues"])
            self.assertEqual(1, report["markups"])
            restored_issue = restored.issue(issue.issue_id)
            self.assertEqual(ReviewPriority.HIGH.value, restored_issue.priority)
            self.assertEqual(ReviewStatus.ACTION_REQUIRED.value, restored_issue.status)
            self.assertEqual("werkvoorbereiding", restored_issue.assignee)
            self.assertEqual("2026-08-31T12:00:00Z", restored_issue.due_date_utc)
            self.assertEqual(1, len(restored_issue.attachments))
            self.assertEqual(1, len(restored_issue.comments))
            self.assertIn(view.viewpoint_id, {v.viewpoint_id for v in controller2.list_viewpoints()})
            self.assertEqual(ReferenceState.VALID, restored.reference_health(issue.issue_id).state)
        finally:
            controller2.shutdown()

    def test_issue_delete_does_not_delete_saved_view(self) -> None:
        view = self.service.capture_view("Independent", owner="tester")
        issue = self.service.create_issue("Temporary", viewpoint_id=view.viewpoint_id)
        self.service.delete_issue(issue.issue_id)
        self.assertNotIn(issue.issue_id, self.service.issues)
        self.assertIn(view.viewpoint_id, {v.viewpoint_id for v in self.controller.list_viewpoints()})

    def test_deleted_view_is_flagged_stale_not_silently_unlinked(self) -> None:
        view = self.service.capture_view("Delete me", owner="tester")
        issue = self.service.create_issue("View reference", viewpoint_id=view.viewpoint_id)
        self.service.delete_view(view.viewpoint_id)
        health = self.service.reference_health(issue.issue_id)
        self.assertTrue(health.is_stale)
        self.assertEqual(view.viewpoint_id, health.missing_viewpoint_id)
        self.assertEqual(view.viewpoint_id, self.service.issue(issue.issue_id).viewpoint_id)

    def test_missing_entity_and_markup_references_are_flagged_exactly(self) -> None:
        issue = self.service.create_issue(
            "Revision stale",
            linked_entity_ids=("ENTITY-DOES-NOT-EXIST",),
            markup_ids=("MK-DOES-NOT-EXIST",),
        )
        health = self.service.reference_health(issue.issue_id)
        self.assertEqual(ReferenceState.STALE, health.state)
        self.assertEqual(("ENTITY-DOES-NOT-EXIST",), health.missing_entity_ids)
        self.assertEqual(("MK-DOES-NOT-EXIST",), health.missing_markup_ids)

    def test_portable_review_package_has_independent_views_and_verified_assets(self) -> None:
        view = self.service.capture_view("Package view", owner="tester")
        issue = self.service.create_issue("Package issue", viewpoint_id=view.viewpoint_id)
        attachment = self.root / "evidence.txt"
        attachment.write_text("evidence", encoding="utf-8")
        self.service.add_attachment(issue.issue_id, attachment, actor="tester", media_type="text/plain")
        package = self.service.export_package(self.root / "review.cwsreview", assets_root=self.root)
        manifest = ReviewPackageVerifier().verify(package)
        self.assertEqual(1, manifest["counts"]["viewpoints"])
        self.assertFalse(manifest["source_models_embedded"])
        self.assertFalse(manifest["production_machine_transfer_allowed"])
        payload = ReviewPackageReader().read(package)
        self.assertEqual(view.viewpoint_id, payload["saved_views"][0]["viewpoint_id"])
        self.assertEqual(issue.issue_id, payload["issues"][0]["issue_id"])

    def test_bcf_2_1_export_is_schema_validated_with_viewpoint_and_ifc_selection(self) -> None:
        view = self.service.capture_view("BCF view", owner="tester")
        entity = self.controller.index.node(self.controller.index.renderable_node_ids[0]).entity_id
        issue = self.service.create_issue(
            "BCF semantic",
            priority=ReviewPriority.URGENT,
            linked_entity_ids=(str(entity),),
            viewpoint_id=view.viewpoint_id,
            created_by="tester@example.com",
        )
        self.service.add_comment(issue.issue_id, "tester@example.com", "Schema test")
        mapping = map_review_topic(issue, project_id=self.scene.project_id)
        self.assertEqual(ReviewPriority.URGENT.value, mapping.priority)
        self.service.project_metadata["ifc_guid_by_entity"] = {str(entity): "0" * 22}
        target = self.service.export_bcf(self.root / "review.bcfzip")
        report = Bcf21Verifier().verify(target)
        self.assertEqual("2.1", report.version)
        self.assertEqual(1, report.topic_count)
        self.assertEqual(1, report.viewpoint_count)
        with zipfile.ZipFile(target) as archive:
            viewpoint_name = next(name for name in archive.namelist() if name.endswith(".bcfv"))
            root = ET.fromstring(archive.read(viewpoint_name))
            self.assertEqual("0" * 22, root.find("./Components/Selection/Component").attrib["IfcGuid"])
        self.assertTrue(self.service.review_hash)
        self.assertIn(
            '"review" / "schemas"',
            (ROOT / "CWS_Convertor.spec").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
