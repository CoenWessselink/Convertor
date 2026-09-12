"""Routing revision/identity contracts; declared reports are not machine qualification."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cws_convertor.machine_routing import MachineRoutingService
from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.workspace import BOMWorkspaceReadModel
from cws_convertor.project import Part, ProjectModel


class MachineBindingTests(unittest.TestCase):
    def setUp(self):
        self.project = ProjectModel.new("synthetic routing identity controls")
        for key, length in (("P1", 3000), ("P2", 2000)):
            part = Part(internal_id=key, part_position=key, profile="HEA200", normalized_profile="HEA200",
                        material="S355J2", length_mm=length, quantity_total=1,
                        classification_status="confirmed", classification_confidence=1)
            part.recompute_hashes()
            self.project.add_entity(part)
        self.service = MachineRoutingService()

    def report(self, key="P1", **changes):
        report = {"part_id": key, "machine_id": "M1", "production_ready": True,
                  "manufacturing_hash": self.project.parts[key].manufacturing_hash,
                  "blocking_codes": [], "machine_transfer_allowed": False}
        report.update(changes)
        self.project.settings.setdefault("machine_capability_reports", {}).setdefault(key, {})["M1"] = report
        return report

    def test_unbound_stale_wrong_identity_and_negative_reports_cannot_assign_ready(self):
        for changes in ({"manufacturing_hash": ""}, {"manufacturing_hash": "stale"},
                        {"part_id": "P2"}, {"machine_id": "M2"}, {"status": "stale"},
                        {"status": "review_required"}, {"review_required": True}, {"blocking_codes": ["NO_TOOL"]}):
            with self.subTest(changes=changes):
                self.report(**changes)
                result = self.service.assign_automatic(self.project, ("P1",), user="test")
                self.assertEqual("blocked", result[0].routing_status)
                self.assertFalse(result[0].assigned_machine_id)

    def test_report_cannot_move_between_canonical_entity_or_machine_buckets(self):
        self.project.parts["P2"].length_mm = self.project.parts["P1"].length_mm
        self.project.parts["P2"].recompute_hashes()
        self.report(part_id="P2")
        self.assertEqual({}, self.service.current_capabilities(self.project, "P2"))
        self.report(machine_id="M2")
        self.assertEqual({}, self.service.current_capabilities(self.project, "P1"))

    def test_current_selected_assignment_survives_reopen_without_touching_sibling(self):
        self.report("P1")
        self.service.assign(self.project, ("P2",), "M2", user="test", reason="manual fixture")
        before = deepcopy(self.project.settings["machine_routing"]["assignments"]["P2"])
        assigned = self.service.assign_automatic(self.project, ("P1",), user="test")[0]
        self.assertEqual("ready", assigned.routing_status)
        self.assertEqual(self.project.parts["P1"].manufacturing_hash, assigned.manufacturing_hash)
        self.assertTrue(assigned.capability_report_sha256)
        self.assertEqual(before, self.project.settings["machine_routing"]["assignments"]["P2"])
        restored = ProjectModel.from_dict(self.project.to_dict())
        self.assertEqual(assigned, self.service.assignments(restored)["P1"])

    def test_part_revision_and_report_change_invalidate_cached_ready_in_bom(self):
        self.report()
        self.service.assign_automatic(self.project, ("P1",), user="test")
        self.project.parts["P1"].length_mm += 500
        self.project.parts["P1"].recompute_hashes()
        snapshot = build_bom_snapshot(self.project, classify_if_needed=False)
        before = self.project.to_dict()
        model = BOMWorkspaceReadModel(snapshot, self.project)
        row = next(row for row in model.family_rows("parts") if "P1" in row.entity_ids)
        self.assertNotEqual("Gereed", row.machine_status)
        self.assertEqual("stale", self.service.assignments(self.project)["P1"].capability_status)
        self.assertEqual(before, self.project.to_dict(), "Projection must not mutate canonical state")
        self.report()
        self.service.assign_automatic(self.project, ("P1",), user="test")
        self.project.settings["machine_capability_reports"]["P1"]["M1"]["blocking_codes"] = ["TOOL_REMOVED"]
        self.assertEqual("blocked", self.service.assignments(self.project)["P1"].routing_status)

    def test_legacy_ready_without_binding_is_review_required(self):
        self.report()
        self.service.assign_automatic(self.project, ("P1",), user="test")
        stored = self.project.settings["machine_routing"]["assignments"]["P1"]
        stored.pop("manufacturing_hash")
        stored.pop("capability_report_sha256")
        self.assertEqual("blocked", self.service.assignments(self.project)["P1"].routing_status)

    def test_mutating_one_assignment_does_not_persist_other_stale_projections(self):
        for key in ("P1", "P2"):
            self.report(key)
        self.service.assign_automatic(self.project, ("P1", "P2"), user="test")
        self.project.parts["P2"].length_mm += 50
        self.project.parts["P2"].recompute_hashes()
        before = deepcopy(self.project.settings["machine_routing"]["assignments"]["P2"])
        self.service.reset(self.project, ("P1",), user="test", reason="selected reset")
        self.assertEqual(before, self.project.settings["machine_routing"]["assignments"]["P2"])
        self.assertEqual("blocked", self.service.assignments(self.project)["P2"].routing_status)


if __name__ == "__main__":
    unittest.main(verbosity=2)
