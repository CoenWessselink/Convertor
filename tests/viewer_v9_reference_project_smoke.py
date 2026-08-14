from __future__ import annotations

from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.integration import IntegratedProjectWorkspace

DEFAULT_PROJECT = Path(
    "/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/"
    "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
)


class ViewerV9ReferenceProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = Path(os.environ.get("CWS_V9_REFERENCE_PROJECT", DEFAULT_PROJECT))
        if not path.is_file():
            raise unittest.SkipTest(f"V9 referentieproject ontbreekt: {path}")
        cls.workspace = IntegratedProjectWorkspace.open(path, read_only=True, load_all_geometry=False)

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "workspace"):
            cls.workspace.close()

    def test_complete_canonical_identity_counts(self) -> None:
        report = self.workspace.report
        self.assertTrue(report.identity_audit.passed, report.to_dict())
        self.assertEqual(6162, report.identity_audit.canonical_entity_count)
        self.assertEqual(6162, report.grid_rows)
        self.assertEqual(6162, report.bom_traceability_rows)
        self.assertEqual(6168, report.scene_nodes)

    def test_mlo4_lo4_syncs_tree_grid_viewer_bom_and_workbench_gate(self) -> None:
        rows = [row for row in self.workspace.interaction.grid_model.rows if row.get("part_position") == "LO4"]
        self.assertEqual(4, len(rows))
        self.assertTrue(all(row.get("profile") == "STRIP5*120" for row in rows))
        self.assertTrue(all(row.get("material") == "S235JR" for row in rows))
        entity_ids = tuple(row.entity_id for row in rows)
        self.workspace.select_entities(entity_ids, origin="reference-test")
        self.assertEqual(set(entity_ids), set(self.workspace.interaction.selection.entity_ids))
        self.assertEqual(set(entity_ids), set(self.workspace.selection_bus.selection.entity_ids))
        for entity_id in entity_ids:
            self.assertTrue(self.workspace.bom_index.group_for_entity(entity_id))
            exact = self.workspace.open_exact_part(entity_id)
            self.assertFalse(exact.available)
            self.assertIn("CWS-V9-EXACT-IFC-BREP-ISOLATION-PENDING", exact.blocking_codes)
            gate = self.workspace.readiness_for_part(entity_id)
            self.assertFalse(gate["viewer_can_override"])
            self.assertFalse(gate["allowed"]["nc1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
