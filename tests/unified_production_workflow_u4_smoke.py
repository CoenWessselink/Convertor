from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from cws_convertor.integration.production_workflow import (
    U4_SAFETY_FLAGS,
    U4_WORKFLOW_SCHEMA,
    build_production_workflow_snapshot,
)
from cws_convertor.integration.selftest import create_synthetic_integration_project
from cws_convertor.integration.workspace import IntegratedProjectWorkspace


class UnifiedProductionWorkflowU4Tests(unittest.TestCase):
    def test_project_and_selection_workflow_use_existing_readiness_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-u4-") as directory:
            project_path = create_synthetic_integration_project(Path(directory) / "u4.cwscproj")
            with IntegratedProjectWorkspace.open(project_path, read_only=True, load_all_geometry=False) as workspace:
                whole = build_production_workflow_snapshot(workspace)
                self.assertEqual(whole.to_dict()["schema"], U4_WORKFLOW_SCHEMA)
                self.assertEqual(whole.part_count, len(workspace.project.parts))
                self.assertFalse(whole.to_dict()["production_release_allowed_from_workflow"])
                self.assertFalse(whole.to_dict()["machine_transfer_allowed"])
                self.assertFalse(any(U4_SAFETY_FLAGS.values()))

                part_id = next(iter(workspace.project.parts))
                selected = build_production_workflow_snapshot(workspace, (part_id,))
                self.assertEqual(selected.scope, "selection")
                self.assertEqual(tuple(item.entity_id for item in selected.part_statuses), (part_id,))
                readiness = workspace.readiness_for_part(part_id)
                self.assertEqual(
                    set(selected.part_statuses[0].blocking_codes),
                    set(readiness.get("blocking_codes", ())),
                )

    def test_non_part_selection_never_widens_to_whole_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-u4-") as directory:
            project_path = create_synthetic_integration_project(Path(directory) / "u4.cwscproj")
            with IntegratedProjectWorkspace.open(project_path, read_only=True, load_all_geometry=False) as workspace:
                assembly_id = next(iter(workspace.project.assemblies))
                report = build_production_workflow_snapshot(workspace, (assembly_id,))
                self.assertEqual(report.scope, "selection")
                self.assertEqual(report.part_count, 0)
                self.assertEqual(report.next_action, "select_or_import_parts")


if __name__ == "__main__":
    unittest.main(verbosity=2)
