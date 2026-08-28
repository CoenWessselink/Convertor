from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.quality import InspectionCharacteristic, InspectionPlan, QualityLedger


class Phase3QualityInspectionTests(unittest.TestCase):
    def plan(self) -> InspectionPlan:
        return InspectionPlan(
            plan_id="plan-P120-A", project_id="project-quality", revision="A",
            characteristics=(
                InspectionCharacteristic("length", "part-P120", "overall", 1200.0, -0.5, 0.5),
                InspectionCharacteristic("hole-x", "part-P120", "hole-1", 100.0, -0.2, 0.2),
            ),
            source_release_hash="a" * 64, created_by="planner", approved_by="quality-engineer",
            heat_certificate_required=True,
        )

    def test_release_is_hash_bound_and_persists_losslessly(self) -> None:
        ledger = QualityLedger("project-quality", self.plan())
        for identifier, characteristic, value in (("m-length", "length", 1200.1), ("m-hole", "hole-x", 99.9)):
            self.assertTrue(ledger.record_measurement(
                measurement_id=identifier, characteristic_id=characteristic, measured_value=value,
                measured_at="2026-08-27T10:00:00Z", operator="inspector", tool_id="caliper-7",
                tool_calibration_id="cal-2026-08",
            ).passed)
        ledger.add_heat_certificate("HEAT-42", "b" * 64)
        approval = ledger.approve_final_release(
            source_release_hash="a" * 64, approved_by="quality-manager", approved_at="2026-08-27T10:05:00Z",
        )
        with tempfile.TemporaryDirectory(prefix="cws-quality-") as folder:
            path = Path(folder) / "quality.json"
            ledger.save(path)
            reopened = QualityLedger.load(path)
        self.assertEqual(ledger.quality_sha256, reopened.quality_sha256)
        self.assertTrue(reopened.final_release_allowed)
        self.assertEqual(approval, reopened.final_release_hash)

    def test_ncr_rework_and_reinspection_fail_closed(self) -> None:
        ledger = QualityLedger("project-quality", self.plan())
        failed = ledger.record_measurement(
            measurement_id="m-fail", characteristic_id="length", measured_value=1202.0,
            measured_at="2026-08-27T11:00:00Z", operator="inspector", tool_id="caliper-7",
            tool_calibration_id="cal-2026-08",
        )
        self.assertFalse(failed.passed)
        passing = ledger.record_measurement(
            measurement_id="m-reinspect", characteristic_id="length", measured_value=1200.0,
            measured_at="2026-08-27T11:30:00Z", operator="inspector-2", tool_id="caliper-8",
            tool_calibration_id="cal-2026-08-b",
        )
        self.assertTrue(passing.passed)
        ledger.close_nonconformance("ncr-m-fail", rework_reference="RW-001",
                                    reinspection_measurement_id="m-reinspect", closed_by="quality-manager")
        self.assertNotIn("open_nonconformance", ledger.release_blockers("a" * 64))
        with self.assertRaises(ValueError):
            ledger.approve_final_release(source_release_hash="c" * 64, approved_by="quality-manager",
                                         approved_at="2026-08-27T12:00:00Z")


if __name__ == "__main__":
    unittest.main(verbosity=2)
