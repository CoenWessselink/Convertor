from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.integration import (
    U3_CONTEXT_SCHEMA,
    U3_SAFETY_FLAGS,
    IntegratedProjectWorkspace,
    UnifiedApplicationContext,
    create_synthetic_integration_project,
)


class UnifiedUiContextU3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="cws-u3-context-")
        self.project_path = create_synthetic_integration_project(
            Path(self.temp.name) / "u3-context.cwscproj"
        )
        self.workspace = IntegratedProjectWorkspace.open(
            self.project_path,
            read_only=True,
            load_all_geometry=False,
            allow_proxy=True,
        )
        self.context = UnifiedApplicationContext(active_surface="viewer")
        self.events = []
        self.unsubscribe = self.context.subscribe(self.events.append, emit_current=False)

    def tearDown(self) -> None:
        self.unsubscribe()
        self.context.detach_workspace()
        self.workspace.close()
        self.temp.cleanup()

    def test_workspace_is_exact_same_canonical_project_truth(self) -> None:
        snapshot = self.context.attach_workspace(self.workspace)
        self.assertEqual(U3_CONTEXT_SCHEMA, snapshot.to_dict()["schema"])
        self.assertTrue(snapshot.project_attached)
        self.assertEqual("2.25", snapshot.project_schema)
        self.assertIs(self.context.workspace, self.workspace)
        self.assertIs(self.workspace.project, self.workspace.session.project)
        self.assertIs(self.workspace.load_result.project, self.workspace.project)
        self.assertEqual((), snapshot.integrity_blocking_codes)
        self.context.assert_consistent()

    def test_viewer_selection_is_the_same_selection_seen_by_all_surfaces(self) -> None:
        self.context.attach_workspace(self.workspace)
        self.workspace.interaction.select_entities(("part-v9",), origin="viewer_pick")
        self.assertEqual("part-v9", self.context.selection.primary_entity_id)
        for surface in ("viewer", "workbench", "scribing", "bom", "export"):
            snapshot = self.context.set_active_surface(surface)
            self.assertEqual(surface, snapshot.active_surface)
            self.assertEqual(("part-v9",), snapshot.selection.entity_ids)
            self.assertEqual("part-v9", snapshot.selection.primary_entity_id)
        self.context.assert_consistent()

    def test_pdf_bus_intent_is_mirrored_back_into_viewer_without_losing_feature_identity(self) -> None:
        self.context.attach_workspace(self.workspace)
        self.context.request_selection(("assembly-v9",), origin="bom")
        self.assertEqual(("assembly-v9",), self.workspace.interaction.selection.entity_ids)

        # V9's PDF bridge publishes identity on the application bus.  U3 must
        # make that same canonical selection visible in the viewer interaction.
        self.workspace.pdf_bridge.highlight_from_pdf("part-v9", "feature:u3-pdf")
        self.assertEqual(("part-v9",), self.workspace.interaction.selection.entity_ids)
        self.assertEqual("part-v9", self.context.selection.primary_entity_id)
        self.assertEqual("feature:u3-pdf", self.context.selection.feature_id)
        self.assertEqual("pdf", self.context.selection.origin)
        self.assertEqual(
            "feature:u3-pdf",
            self.workspace.selection_bus.selection.feature_id,
        )
        self.context.assert_consistent()

    def test_noncanonical_selection_fails_closed_and_never_reaches_renderer(self) -> None:
        self.context.attach_workspace(self.workspace)
        self.context.request_selection(("part-v9",), origin="u3-test")
        with self.assertRaises(KeyError):
            self.context.request_selection(("not-a-canonical-id",), origin="invalid")
        self.assertEqual(("part-v9",), self.workspace.interaction.selection.entity_ids)

        # Also prove a direct legacy bus tamper does not get mirrored into the
        # renderer and becomes visible as an integrity blocker.
        self.workspace.selection_bus.publish(("not-a-canonical-id",), origin="legacy-tamper")
        self.assertEqual(("part-v9",), self.workspace.interaction.selection.entity_ids)
        self.assertIn("U3_SELECTION_NON_CANONICAL", self.context.snapshot.integrity_blocking_codes)

        # A normal canonical request repairs the context without touching
        # project/manufacturing truth.
        self.context.request_selection(("part-v9",), origin="repair")
        self.assertEqual((), self.context.snapshot.integrity_blocking_codes)
        self.context.assert_consistent()

    def test_machine_transport_boundary_remains_closed(self) -> None:
        self.context.attach_workspace(self.workspace)
        self.assertEqual(
            {
                "machine_observed_by_cws": False,
                "deployment_transport_authorized": False,
                "direct_machine_transfer": False,
                "machine_transfer_allowed": False,
            },
            U3_SAFETY_FLAGS,
        )
        self.assertTrue(all(value is False for value in self.context.snapshot.to_dict()["safety"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
