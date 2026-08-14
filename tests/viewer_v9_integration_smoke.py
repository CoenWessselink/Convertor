from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.integration import (
    IntegratedProjectWorkspace,
    create_synthetic_integration_project,
    run_integration_self_test,
)


class ViewerV9IntegrationTests(unittest.TestCase):
    def test_integrated_selftest_passes_all_contracts(self) -> None:
        report = run_integration_self_test()
        self.assertTrue(report.passed, report.to_dict())
        self.assertEqual(6, len(report.checks))

    def test_one_project_instance_binds_scene_grid_bom_pdf_and_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-v9-test-") as directory:
            path = create_synthetic_integration_project(Path(directory) / "project.cwscproj")
            with IntegratedProjectWorkspace.open(path, read_only=True, load_all_geometry=False) as workspace:
                self.assertIs(workspace.load_result.project, workspace.session.project)
                self.assertTrue(workspace.identity_audit.passed)
                self.assertEqual(5, workspace.identity_audit.canonical_entity_count)
                part_id = "part-v9"
                workspace.select_entities((part_id,), origin="unit-test")
                self.assertEqual(part_id, workspace.selection_bus.selection.primary_entity_id)
                self.assertEqual(part_id, workspace.interaction.selection.primary_entity_id)
                group_id = workspace.bom_index.group_for_entity(part_id)
                self.assertTrue(group_id)
                self.assertIn(part_id, workspace.select_bom_group(group_id or ""))
                workspace.highlight_pdf_feature(part_id, "hole:1")
                self.assertEqual("hole:1", workspace.selection_bus.selection.feature_id)
                gate = workspace.readiness_for_part(part_id)
                self.assertFalse(gate["viewer_can_override"])
                self.assertFalse(gate["allowed"]["nc1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
