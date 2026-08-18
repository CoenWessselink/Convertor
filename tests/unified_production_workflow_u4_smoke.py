from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from cws_convertor.integration import (
    ProductionWorkflowCoordinator,
    U4_SAFETY_FLAGS,
    UnifiedApplicationContext,
    create_synthetic_integration_project,
)


class UnifiedProductionWorkflowU4Tests(unittest.TestCase):
    def test_u4_plan_is_context_bound_format_specific_and_transfer_closed(self) -> None:
        from cws_convertor.integration.workspace import IntegratedProjectWorkspace

        self.assertFalse(any(U4_SAFETY_FLAGS.values()))
        with tempfile.TemporaryDirectory(prefix="cws-u4-plan-") as folder:
            project_path = create_synthetic_integration_project(Path(folder) / "u4.cwscproj")
            with IntegratedProjectWorkspace.open(project_path, read_only=False, load_all_geometry=False) as workspace:
                context = UnifiedApplicationContext(active_surface="production")
                context.attach_workspace(workspace)
                coordinator = ProductionWorkflowCoordinator(context)

                default_plan = coordinator.build_plan()
                self.assertEqual("2.25", default_plan.project_schema)
                self.assertIn("part-v9", default_plan.part_ids)
                self.assertFalse(default_plan.can_execute)
                self.assertIn("U4_FORMAT_BLOCKED:nc1", default_plan.blocking_codes)
                self.assertFalse(any(default_plan.to_dict()["safety"].values()))

                context.request_selection(("part-v9",), origin="u4-test")
                review_plan = coordinator.build_plan(("json", "review_pdf"), selection_only=True)
                self.assertTrue(review_plan.can_execute, review_plan.to_dict())
                self.assertEqual(("part-v9",), review_plan.part_ids)
                self.assertTrue(review_plan.format_allowed["json"])
                self.assertTrue(review_plan.format_allowed["review_pdf"])
                self.assertEqual(64, len(review_plan.plan_sha256))
                context.assert_consistent()

    def test_stale_selection_plan_is_rejected(self) -> None:
        from cws_convertor.integration.workspace import IntegratedProjectWorkspace

        with tempfile.TemporaryDirectory(prefix="cws-u4-stale-") as folder:
            project_path = create_synthetic_integration_project(Path(folder) / "u4.cwscproj")
            with IntegratedProjectWorkspace.open(project_path, read_only=False, load_all_geometry=False) as workspace:
                context = UnifiedApplicationContext(active_surface="production")
                context.attach_workspace(workspace)
                context.request_selection(("part-v9",), origin="u4-test")
                coordinator = ProductionWorkflowCoordinator(context)
                plan = coordinator.build_plan(("json",), selection_only=True)
                self.assertTrue(plan.can_execute)
                context.request_selection(("assembly-v9",), origin="u4-selection-changed")
                with self.assertRaisesRegex(RuntimeError, "U4_PLAN_STALE"):
                    coordinator.execute_plan(plan, Path(folder) / "out")

    def test_review_workflow_executes_existing_release_engine_and_writes_receipt(self) -> None:
        from cws_convertor.integration.workspace import IntegratedProjectWorkspace

        with tempfile.TemporaryDirectory(prefix="cws-u4-export-") as folder:
            project_path = create_synthetic_integration_project(Path(folder) / "u4.cwscproj")
            output = Path(folder) / "production"
            with IntegratedProjectWorkspace.open(project_path, read_only=False, load_all_geometry=False) as workspace:
                context = UnifiedApplicationContext(active_surface="production")
                context.attach_workspace(workspace)
                context.request_selection(("part-v9",), origin="u4-export-test")
                coordinator = ProductionWorkflowCoordinator(context)
                plan = coordinator.build_plan(("json", "review_pdf"), selection_only=True)
                self.assertTrue(plan.can_execute, plan.to_dict())
                receipt = coordinator.execute_plan(plan, output, user="u4-smoke")
                self.assertEqual(plan.plan_sha256, receipt.plan_sha256)
                self.assertEqual(64, len(receipt.manifest_sha256))
                self.assertEqual(64, len(receipt.receipt_sha256))
                self.assertTrue(Path(receipt.output_root, "CWS_U4_WORKFLOW_RECEIPT.json").is_file())
                self.assertTrue(receipt.project_save_required)
                self.assertFalse(any(receipt.to_dict()["safety"].values()))
                context.assert_consistent()


if __name__ == "__main__":
    unittest.main(verbosity=2)
