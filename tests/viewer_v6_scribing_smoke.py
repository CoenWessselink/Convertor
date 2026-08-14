from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq

from cws_viewer.exact import (
    ScribeOperation,
    ScribeStatus,
    ScribingReviewService,
    build_exact_runtime,
    propose_contact_lines,
)


class ViewerV6ScribingTests(unittest.TestCase):
    @staticmethod
    def pair():
        target = build_exact_runtime(cq.Solid.makeBox(100, 100, 10), part_id="TARGET")
        partner = build_exact_runtime(
            cq.Solid.makeBox(10, 60, 50, cq.Vector(40, 20, 10)),
            part_id="PARTNER",
        )
        return target, partner

    def test_exact_contact_lines_are_deterministic_and_not_cuts(self):
        target, partner = self.pair()
        first = propose_contact_lines(target, partner)
        second = propose_contact_lines(target, partner)
        self.assertEqual(4, len(first))
        self.assertEqual([item.proposal.proposal_id for item in first], [item.proposal.proposal_id for item in second])
        self.assertEqual([10.0, 10.0, 60.0, 60.0], sorted(round(item.proposal.length_mm, 6) for item in first))
        self.assertTrue(all(item.proposal.operation == ScribeOperation.SCRIBE for item in first))
        self.assertTrue(all(item.proposal.evidence.value == "source_brep" for item in first))

    def test_review_is_audited_and_geometry_is_not_mutated(self):
        target, partner = self.pair()
        target_hash = target.snapshot.exact_geometry_hash
        target_volume = float(target.shape.Volume())
        service = ScribingReviewService(target, partner)
        first = service.proposals[0]
        second = service.proposals[1]
        service.confirm(first.proposal_id, user="tester", reason="Contactlijn gecontroleerd")
        service.reject(second.proposal_id, user="tester", reason="Niet markeren op deze zijde")
        self.assertEqual(ScribeStatus.CONFIRMED, service.proposals[0].status)
        self.assertEqual(1, len(service.confirmed))
        self.assertEqual(target_hash, target.snapshot.exact_geometry_hash)
        self.assertAlmostEqual(target_volume, float(target.shape.Volume()), places=9)
        with tempfile.TemporaryDirectory(prefix="viewer-v6-scribe-") as temp:
            output = service.export_json(Path(temp) / "scribes.json")
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(payload["production_release_allowed"])
            self.assertEqual(4, len(payload["proposals"]))
            self.assertTrue(output.with_suffix(output.suffix + ".sha256").is_file())

    def test_no_contact_and_ambiguous_sources_do_not_guess(self):
        target, _ = self.pair()
        separated = build_exact_runtime(
            cq.Solid.makeBox(10, 60, 50, cq.Vector(140, 20, 10)), part_id="SEPARATED"
        )
        self.assertEqual((), propose_contact_lines(target, separated))
        ambiguous = build_exact_runtime(
            cq.Compound.makeCompound([
                cq.Solid.makeBox(10, 10, 10),
                cq.Solid.makeBox(10, 10, 10, cq.Vector(30, 0, 0)),
            ]),
            part_id="AMBIGUOUS",
        )
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS-MULTI-SOLID"):
            propose_contact_lines(ambiguous, separated)


if __name__ == "__main__":
    unittest.main(verbosity=2)
